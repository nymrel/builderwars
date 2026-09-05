"""Runnable Academy and honest series accounting, free/synthetic traffic only."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.environ.get("BUILDERWARS_TEST_URL", "http://127.0.0.1:5178").rstrip("/")
OUT = Path(__file__).parents[1] / "output" / "playwright"
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    errors, provider_calls = [], []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.route("https://openrouter.ai/**", lambda route: (provider_calls.append(route.request.url), route.abort()))
    page.goto(BASE)
    page.locator("#board .cell").first.wait_for()
    page.locator(".match-settings").filter(has=page.locator("#pace")).locator("summary").click()
    page.locator("#pace").select_option("100")
    page.locator("nav [data-tab=academy]").click()
    page.screenshot(path=str(OUT / "academy-mobile.png"), full_page=True)
    page.locator("#academy-pair").click()
    assert page.locator("#game-title").inner_text() == "Connect Four"
    assert page.locator("#seats").inner_text().count("Built-in · free") == 2
    # Repeated exercise clicks must not restart a running series.
    page.locator("nav [data-tab=academy]").click()
    page.locator("#academy-pair").click()
    assert "Pause" in page.locator("#academy-status").inner_text()
    page.wait_for_function("() => document.querySelector('#series-results').textContent.includes('2 / 2 attempts recorded')", timeout=45000)
    page.locator("nav [data-tab=evals]").click()
    assert "2 rule-complete games" in page.locator("#series-results").inner_text()
    assert "1 complete pairs" in page.locator("#series-results").inner_text()
    with page.expect_download() as result:
        page.locator("#export-series").click()
    receipt = json.loads(Path(result.value.path()).read_text())
    assert receipt["limits"] == {"moveLimit": 80, "maxTokens": 2048}
    assert receipt["games"][0]["agents"] == list(reversed(receipt["games"][1]["agents"]))
    assert receipt["summary"]["completed"] == 2 and not receipt["inProgress"]
    assert "key" not in json.dumps(receipt) and "endpoint" not in json.dumps(receipt)
    assert not provider_calls
    # Creator recipe prepares, never auto-starts, and round-trips through Forge.
    page.locator("nav [data-tab=academy]").click()
    page.locator("#academy-variant").click()
    assert page.locator("#creator-rows").input_value() == "3"
    assert page.locator("#creator-cols").input_value() == "4"
    assert page.locator("#creator-gravity").is_checked()
    with page.expect_download() as result:
        page.locator("#export-rules").click()
    rules = json.loads(Path(result.value.path()).read_text())
    assert rules["kind"] == "custom" and rules["connect"] == 3
    page.locator("#creator button[type=submit]").click()
    assert page.locator("#board .cell").count() == 12
    assert page.locator("#metric-moves").inner_text() == "0"
    # Capped games must not be called complete or draws.
    page.locator("#move-limit").fill("2")
    page.locator("nav [data-tab=evals]").click()
    page.locator("#run-series").click()
    page.wait_for_function("() => document.querySelector('#series-results').textContent.includes('2 / 2 attempts recorded')")
    assert "0 rule-complete games" in page.locator("#series-results").inner_text()
    assert "2 capped" in page.locator("#series-results").inner_text()
    # Cancellation records the partial attempt; later play is not part of the series.
    page.locator("#move-limit").fill("80")
    page.locator("#pace").select_option("1200")
    page.locator("nav [data-tab=evals]").click()
    page.locator("#run-series").click()
    page.wait_for_function("() => document.querySelector('#metric-moves').textContent==='1'")
    page.locator("#start").click()
    assert "1 stopped" in page.locator("#series-results").inner_text()
    assert "1 / 2 attempts recorded" in page.locator("#series-results").inner_text()
    # A rejected synthetic model response records a failed attempt, not a win.
    page.unroute("https://openrouter.ai/**")
    page.route("https://openrouter.ai/api/v1/key", lambda route: route.fulfill(json={"data": {"is_free_tier": True}}))
    page.route("https://openrouter.ai/api/v1/models", lambda route: route.fulfill(json={"data": [{"id": "test/model", "name": "Synthetic model"}]}))
    page.route("https://openrouter.ai/api/v1/chat/completions", lambda route: route.fulfill(json={"choices": [{"message": {"content": '{"move":"illegal"}'}}]}))
    page.locator("#connections").click()
    page.locator("#agent-kind").select_option("openrouter")
    page.locator("#model-id option").first.wait_for(state="attached")
    page.locator("#agent-key").fill("synthetic-academy-sentinel")
    page.locator("#agent-form button[type=submit]").click()
    page.locator("nav [data-tab=evals]").click()
    page.locator("#run-series").click()
    page.wait_for_function("() => document.querySelector('#series-results').textContent.includes('1 failed')")
    assert "0 rule-complete games" in page.locator("#series-results").inner_text()
    page.locator("nav [data-tab=evals]").click()
    with page.expect_download() as result:
        page.locator("#export-series").click()
    failed = json.loads(Path(result.value.path()).read_text())
    assert failed["attempts"][0]["exit"] == "failed"
    assert len(failed["games"]) == 1 and not failed["games"][0]["events"]
    assert "synthetic-academy-sentinel" not in json.dumps(failed)
    # The Academy explicitly clears configured contenders; no synthetic inference needed.
    page.locator("nav [data-tab=academy]").click()
    page.locator("#academy-variant").click()
    page.locator("#creator button[type=submit]").click()
    assert page.locator("#seats").inner_text().count("Built-in · free") == 2
    page.locator("#connections").click()
    assert page.locator("#agent-key").input_value() == ""
    page.locator("#close-dialog").click()
    for width in [320, 390, 768, 1440]:
        page.set_viewport_size({"width": width, "height": 900})
        for section in ["academy", "forge", "evals"]:
            page.locator(f"nav [data-tab={section}]").click()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (width, section)
    assert not errors, errors
    context.close()
    browser.close()
    print(json.dumps({"status": "PASS", "actualProviderCalls": 0, "journeys": ["free paired lesson", "active-run guard", "creator recipe/export", "capped != complete", "pause accounting", "synthetic illegal move accounting", "secret stripping", "responsive lessons/evals"]}))
