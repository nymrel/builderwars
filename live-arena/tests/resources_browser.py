"""Frozen resource limits through pause, recovery, proof import/export and series."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get("BUILDERWARS_TEST_URL", "http://127.0.0.1:5178")
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 390, "height": 844})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(BASE)
    page.locator("[data-game=connect4]").click()
    page.locator(".match-settings summary").filter(has_text="Match settings").click()
    page.locator("#move-limit").fill("4")
    page.locator("#max-tokens").fill("512")
    page.locator("#step").click()
    expect(page.locator("#metric-moves")).to_have_text("1")
    page.locator("#move-limit").fill("40")
    page.locator("#max-tokens").fill("4096")
    page.locator("#step").click()
    expect(page.locator("#metric-moves")).to_have_text("2")
    expect(page.locator("#resource-status")).to_contain_text("4 plies maximum · 512")
    saved = page.evaluate("Object.keys(localStorage).filter(k=>k.startsWith('builderwars.match.v1:own:')).map(k=>JSON.parse(localStorage[k]))")
    assert saved and saved[0]["moveLimit"] == 4 and saved[0]["maxTokens"] == 512
    page.reload()
    page.locator("#match-library summary").click()
    page.locator("[data-saved-resume]").first.click()
    page.locator(".match-settings summary").filter(has_text="Match settings").click()
    expect(page.locator("#max-tokens")).to_have_value("512")
    expect(page.locator("#metric-moves")).to_have_text("2")
    page.locator("#step").click()
    page.locator("#step").click()
    expect(page.locator("#metric-moves")).to_have_text("4")
    page.locator("#move-limit").fill("80")
    page.locator("#step").click()
    expect(page.locator("#notice")).to_contain_text("move limit reached")
    expect(page.locator("#metric-moves")).to_have_text("4")
    page.locator("#match-proof summary").click()
    with page.expect_download() as result:
        page.locator("#export-proof").click()
    proof = Path(result.value.path()).read_text()
    assert json.loads(proof.splitlines()[0])["body"]["maxPlies"] == 4
    page.locator("#import-proof").set_input_files({"name": "match.jsonl", "mimeType": "application/x-ndjson", "buffer": proof.encode()})
    expect(page.locator("#proof-status")).to_contain_text("reproduced by the matching referee")
    expect(page.locator("#resource-status")).to_contain_text("original token limit unknown")
    with page.expect_download() as again:
        page.locator("#export-proof").click()
    assert json.loads(Path(again.value.path()).read_text().splitlines()[0])["body"]["maxPlies"] == 4
    # Plain replay has no resource envelope: saving/reopening must not invent one.
    plain = browser.new_page()
    plain.goto(BASE)
    plain.locator("#import").set_input_files({"name": "match.json", "mimeType": "application/json", "buffer": json.dumps(saved[0]["record"]).encode()})
    plain.locator(".match-settings summary").filter(has_text="Match settings").click()
    expect(plain.locator("#resource-status")).to_contain_text("original resource limits are unavailable")
    plain.reload()
    plain.locator("#match-library summary").click()
    plain.locator("[data-saved-replay]").first.click()
    plain.locator(".match-settings summary").filter(has_text="Match settings").click()
    expect(plain.locator("#resource-status")).to_contain_text("original resource limits are unavailable")
    plain.close()
    # A new rematch/series adopts the newly chosen limits, not the prior match's.
    page.locator("nav [data-tab=watch]").click()
    page.locator("#leave-watch").click()
    page.locator("#move-limit").fill("2")
    page.locator("#max-tokens").fill("1024")
    page.locator("#pace").select_option("100")
    page.locator("nav [data-tab=evals]").click()
    page.locator("#run-series").click()
    # Bypass UI disabled state to prove the second game uses the frozen series settings.
    page.evaluate("document.querySelector('#move-limit').value='20'; document.querySelector('#max-tokens').value='8192'")
    page.wait_for_function("() => document.querySelector('#series-results').textContent.includes('2 / 2 attempts recorded')")
    expect(page.locator("#series-conditions")).to_contain_text("2 plies maximum · 1024")
    expect(page.locator("#series-conditions")).to_contain_text("unseeded")
    page.locator("nav [data-tab=evals]").click()
    # A rejected next setup cannot rewrite the conditions of completed evidence.
    page.evaluate("document.querySelector('#series-length').add(new Option('invalid', '3')); document.querySelector('#series-length').value='3'")
    page.locator("#run-series").click()
    expect(page.locator("#notice")).to_contain_text("Choose 2, 4 or 10")
    page.locator("nav [data-tab=evals]").click()
    with page.expect_download() as series_file:
        page.locator("#export-series").click()
    series = json.loads(Path(series_file.value.path()).read_text())
    assert series["limits"] == {"moveLimit": 2, "maxTokens": 1024}
    assert series["requestedGames"] == 2
    assert all(len(g["events"]) == 2 for g in series["games"])
    assert series["rules"]["kind"] == "connect4"
    assert series["fixture"] == "standard-initial-position"
    assert series["randomness"] == "unseeded-and-not-controlled"
    # An explicit new runback adopts edited limits instead of silently discarding them.
    page.locator("nav [data-tab=arena]").click()
    page.locator("#move-limit").fill("6")
    page.locator("#max-tokens").fill("768")
    page.locator("#runback-free").click()
    expect(page.locator("#resource-status")).to_contain_text("6 plies maximum · 768")
    page.wait_for_function("() => document.querySelector('#metric-moves').textContent === '6'")
    assert not errors
    # Verify actual request parameters at the synthetic provider boundary.
    remote = browser.new_page()
    requests = []
    remote.route("https://openrouter.ai/api/v1/models", lambda r: r.fulfill(json={"data": [{"id": "test/model", "name": "Synthetic"}]}))
    remote.route("https://openrouter.ai/api/v1/key", lambda r: r.fulfill(json={"data": {"is_free_tier": True}}))
    def move(route):
        requests.append(route.request.post_data_json)
        route.fulfill(json={"choices": [{"message": {"content": '{"move":"0"}'}}], "model": "test/model"})
    remote.route("https://openrouter.ai/api/v1/chat/completions", move)
    remote.goto(BASE)
    remote.locator("[data-game=connect4]").click()
    remote.locator("#connections").click()
    remote.locator("#agent-kind").select_option("openrouter")
    remote.locator('#model-id option[value="test/model"]').wait_for(state="attached")
    remote.locator("#model-id").select_option("test/model")
    remote.locator("#agent-key").fill("synthetic-resource-sentinel")
    remote.locator("#agent-form button[type=submit]").click()
    remote.locator(".match-settings summary").filter(has_text="Match settings").click()
    remote.locator("#max-tokens").fill("512")
    remote.locator("#step").click()
    expect(remote.locator("#metric-moves")).to_have_text("1")
    remote.locator("#max-tokens").fill("4096")
    remote.locator("#step").click()
    expect(remote.locator("#metric-moves")).to_have_text("2")
    remote.locator("#step").click()
    expect(remote.locator("#metric-moves")).to_have_text("3")
    assert len(requests) == 2 and all(r["max_tokens"] == 512 for r in requests)
    browser.close()
print("PASS: locked limits, device recovery, original proof cap, new-series isolation and explicit conditions")
