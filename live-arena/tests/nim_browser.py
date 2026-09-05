"""Nim + declared-builder acceptance with synthetic harnesses. Zero provider calls."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.environ.get("BUILDERWARS_TEST_URL", "http://127.0.0.1:5178")
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors, requests = [], []
    page.on("pageerror", lambda error: errors.append(str(error)))
    # Block external traffic; the two fake endpoints below are in-process fixtures.
    page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(BASE + "/") else route.abort())
    page.goto(BASE)
    page.locator("[data-game=nim]").click()
    assert page.locator(".nim-heap").count() == 3
    for seat in (0, 1):
        page.locator(f'[data-seat="{seat}"]').click()
        page.locator("#agent-kind").select_option("human")
        page.locator("#agent-form button[type=submit]").click()
    for heap, take in ((1, 3), (2, 5), (3, 7)):
        page.get_by_role("button", name=f"Heap {heap}: take {take}", exact=True).click()
    assert "wins" in page.locator("#match-status").inner_text()
    assert "took_last_object" in page.locator("#notice").inner_text()
    page.locator("#reset").click()

    def harness(route):
        req = route.request.post_data_json
        assert req["game"]["kind"] == "nim"
        assert "heaps" in req["position"]
        requests.append(req)
        route.fulfill(json={"move": req["legalMoves"][-1], "model": "synthetic/harness"},
                      headers={"Access-Control-Allow-Origin": "*"})
    page.route("https://nim-fixture.invalid/move", harness)
    for seat, name in enumerate(("alice", "bob")):
        page.locator(f'[data-seat="{seat}"]').click()
        page.locator("#agent-kind").select_option("harness")
        page.locator("#agent-name").fill(name)
        page.locator("#harness-url").fill("https://nim-fixture.invalid/move")
        page.locator("#harness-model").fill("synthetic/harness")
        page.locator("#agent-key").fill("synthetic-secret")
        page.locator("#builder-id").fill("studio/" + name)
        page.locator("#harness-id").fill(name + "/nim")
        page.locator("#harness-revision").fill("a" * 40)
        page.locator("#agent-form button[type=submit]").click()
    assert page.locator("#seats").inner_text().count("self-declared") == 2
    page.locator(".match-settings summary").click()
    page.locator("#pace").select_option("100")
    page.locator("nav [data-tab=evals]").click()
    page.locator("#run-series").click()
    page.wait_for_function("() => document.querySelector('#series-results').textContent.includes('2 / 2')", timeout=20000)
    assert len(requests) == 6
    page.locator("nav [data-tab=evals]").click()
    with page.expect_download() as download:
        page.locator("#export-series").click()
    series = json.loads(Path(download.value.path()).read_text())
    first, second = series["games"]
    assert [a["provenance"]["builderId"] for a in first["agents"]] == ["studio/alice", "studio/bob"]
    assert [a["provenance"]["builderId"] for a in second["agents"]] == ["studio/bob", "studio/alice"]
    assert all(r["schema"] == "builderwars.exhibition.v2" and len(r["digest"]) == 64 for r in series["games"])
    assert "synthetic-secret" not in json.dumps(series) and "nim-fixture.invalid" not in json.dumps(series)
    page.locator("nav [data-tab=arena]").click()
    def import_record(record):
        page.locator("#import").set_input_files({"name": "nim.json", "mimeType": "application/json", "buffer": json.dumps(record).encode()})
    import_record(first)
    assert "content binding checked" in page.locator("#notice").inner_text()
    page.locator("#replay-position").fill("0")
    assert "Heap 1 · 3 objects" in page.locator("#board").inner_text()
    page.locator("#replay-next").click()
    assert page.locator("#ply").inner_text() == "PLY 01"
    first["agents"][0]["provenance"]["builderId"] = "imposter"
    import_record(first)
    assert "binding mismatch" in page.locator("#notice").inner_text()
    assert "imposter" not in page.locator("#seats").inner_text()
    for width in (320, 390, 768, 1440):
        page.set_viewport_size({"width": width, "height": 900})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
    # A backend error never switches to a built-in opponent.
    page.locator("nav [data-tab=watch]").click()
    page.locator("#leave-watch").click()
    page.route("https://nim-fixture.invalid/move", lambda route: route.fulfill(status=503, body="synthetic failure"))
    page.locator("#step").click()
    page.wait_for_function("() => document.querySelector('#notice').textContent.includes('503')")
    assert page.locator("#metric-moves").inner_text() == "0"
    assert page.evaluate("JSON.stringify(localStorage)") == "{}"
    assert not errors, errors
    browser.close()
    print(json.dumps({"status": "PASS", "syntheticHarnessMoves": 6, "actualProviderCalls": 0,
                      "journeys": ["human Nim win", "two declared builders", "seat-swapped series", "bound replay", "tamper refusal", "zero replacement on error", "four widths"]}))
