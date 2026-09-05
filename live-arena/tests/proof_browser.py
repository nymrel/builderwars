"""Browser-produced proof, clean-context import, free routing and SRI failure. No paid calls."""
import json
import os
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parents[1]
BASE = os.environ.get("BUILDERWARS_TEST_URL", "http://127.0.0.1:5178").rstrip("/")
OUT = ROOT / "output" / "playwright"
OUT.mkdir(parents=True, exist_ok=True)
CSP = next(h["value"] for h in json.loads((ROOT / "vercel.json").read_text())["headers"][0]["headers"] if h["key"] == "Content-Security-Policy")

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    def with_csp(route):
        response = route.fetch()
        route.fulfill(response=response, headers={**response.headers, "content-security-policy": CSP})
    context.route(BASE + "/", with_csp)
    page.goto(BASE)
    page.locator("#board .cell").first.wait_for()
    engine_script = page.locator("script[integrity]")
    assert engine_script.count() == 1
    assert engine_script.get_attribute("integrity").startswith("sha256-")
    assert page.locator("#quickplay").inner_text() == "Play free ↗"
    page.locator("[data-game=connect4]").click()
    for seat in [0, 1]:
        page.locator(f'[data-seat="{seat}"]').click()
        page.locator("#agent-kind").select_option("human")
        page.locator("#agent-name").fill(f"Synthetic human {seat}")
        page.locator("#strategy").fill("private-strategy-sentinel")
        page.locator("#agent-form button[type=submit]").click()
    for cell in [0, 1, 0, 1, 0, 1, 0]:
        page.locator(f'[data-cell="{cell}"]').click()
    assert "wins" in page.locator("#match-status").inner_text()
    page.locator("#match-proof summary").click()
    with page.expect_download() as proof_download:
        page.locator("#export-proof").click()
    proof_path = OUT / "browser-match.jsonl"
    proof_download.value.save_as(proof_path)
    assert "private-strategy-sentinel" not in proof_path.read_text()
    with page.expect_download() as verifier_download:
        page.locator("#download-verifier").click()
    verifier_path = OUT / "browser-verifier.mjs"
    verifier_download.value.save_as(verifier_path)
    result = json.loads(subprocess.check_output(["node", str(verifier_path), str(proof_path)], text=True, timeout=10))
    assert result["verified"] and result["complete"] and result["winner"] == 0
    assert not result["model_attested"] and not result["execution_attested"]
    assert result["origin_declaration"] == "browser_session"
    # Fresh browser context: no account, keys, storage or state inherited.
    second_context = browser.new_context(viewport={"width": 320, "height": 780})
    second = second_context.new_page()
    second.on("pageerror", lambda e: errors.append(str(e)))
    second.goto(BASE)
    second.locator("#board .cell").first.wait_for()
    second.locator("#match-proof summary").click()
    second.locator("#import-proof").set_input_files(proof_path)
    second.wait_for_function("() => document.querySelector('#proof-status').textContent.includes('7 plies reproduced')")
    assert second.locator("#start").is_disabled()
    second.locator("#replay-prev").click()
    assert second.locator("#ply").inner_text() == "PLY 06"
    with second.expect_download() as reexport:
        second.locator("#export-proof").click()
    rows = [json.loads(line) for line in Path(reexport.value.path()).read_text().splitlines()]
    assert rows[0]["body"]["origin"] == "reverified_import"
    assert second.evaluate("document.documentElement.scrollWidth <= innerWidth")
    second.screenshot(path=str(OUT / "proof-mobile.png"), full_page=True)
    # Tampered result must not replace the current replay.
    corrupt = proof_path.read_text().replace('"winner":0', '"winner":1')
    second.locator("#import-proof").set_input_files({"name": "tampered.jsonl", "mimeType": "application/x-ndjson", "buffer": corrupt.encode()})
    second.wait_for_function("() => document.querySelector('#proof-status').textContent.includes('mismatch')")
    assert second.locator("#ply").inner_text() == "PLY 06"
    # Free play must discard paid connection settings and never hit inference.
    page.locator("#reset").click()
    calls = []
    page.route("https://openrouter.ai/api/v1/models", lambda route: route.fulfill(json={"data": [{"id": "synthetic/model", "name": "Synthetic", "supported_parameters": []}]}))
    page.route("https://openrouter.ai/api/v1/chat/completions", lambda route: (calls.append(route.request.url), route.abort()))
    page.locator("#connections").click()
    page.locator("#agent-kind").select_option("openrouter")
    page.locator("#model-id option").first.wait_for(state="attached")
    page.locator("#agent-key").fill("synthetic-private-key")
    page.locator("#agent-form button[type=submit]").click()
    page.locator("#quickplay").click()
    page.wait_for_function("() => Number(document.querySelector('#metric-moves').textContent) >= 2")
    page.locator("#start").click()
    assert not calls
    assert page.locator("#seats").inner_text().count("Built-in · free") == 2
    assert "synthetic-private-key" not in page.evaluate("JSON.stringify(localStorage)")
    # A modified executable is rejected by browser SRI before any gameplay starts.
    broken_context = browser.new_context()
    broken_context.route("**/referee/*.mjs", lambda route: route.fulfill(body="globalThis.__builderwarsReferee = {};", content_type="text/javascript"))
    broken = broken_context.new_page()
    broken.goto(BASE)
    broken.wait_for_function("() => document.querySelector('#app').textContent.includes('could not load its verified game engine')")
    assert broken.locator("#board").count() == 0
    assert not errors, errors
    browser.close()
print("PASS: browser proof -> standalone verifier -> clean import; free routing; CSP/SRI; 320px layout; tamper rejection")
