"""Synthetic feedback-consumption proof, not a model improvement measurement."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.environ.get("BUILDERWARS_TEST_URL", "http://127.0.0.1:5178").rstrip("/")
KEY = "builderwars.practice-memory.v1"
with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    errors, requests = [], []
    page.on("pageerror", lambda e: errors.append(str(e)))
    # Fixed bad policy: seat zero misses its immediate win at ply 5.
    moves = ["0", "3", "1", "4", "8", "5"]
    def respond(route):
        body = route.request.post_data_json
        requests.append(body)
        route.fulfill(json={"move": moves[len(body["moves"])], "comment": "Synthetic fixture", "model": "synthetic/fixture"})
    page.route("https://synthetic.example/move", respond)
    page.goto(BASE)
    page.locator("#board .cell").first.wait_for()
    page.on("dialog", lambda d: d.accept())
    def configure():
        page.locator("[data-game=tictactoe]").click()
        for seat in [0, 1]:
            page.locator(f'[data-seat="{seat}"]').click()
            page.locator("#agent-kind").select_option("harness")
            page.locator("#agent-name").fill(f"Learner {seat}")
            page.locator("#harness-url").fill("https://synthetic.example/move")
            page.locator("#harness-model").fill("synthetic/fixture")
            page.locator("#harness-effort").fill("default")
            page.locator("#strategy").fill("PRIVATE_STRATEGY_SENTINEL")
            page.locator("#agent-form button[type=submit]").click()
        settings = page.locator(".match-settings").filter(has=page.locator("#pace"))
        if not settings.evaluate("e => e.open"):
            settings.locator("summary").click()
        page.locator("#pace").select_option("100")
    configure()
    page.locator("#start").click()
    page.wait_for_function("() => document.querySelector('#metric-moves').textContent === '6'")
    page.wait_for_function("key => JSON.parse(localStorage.getItem(key) || '{}').episodes?.length === 2", arg=KEY)
    assert not any("practiceMemory" in r for r in requests)
    before = page.evaluate("key => localStorage.getItem(key)", KEY)
    assert "PRIVATE_STRATEGY_SENTINEL" not in before and "synthetic.example" not in before
    assert any(m["kind"] == "missed-win" for e in json.loads(before)["episodes"] for m in e["mistakes"])
    page.locator("#reset").click()
    page.locator("#step").click()
    page.wait_for_function("() => document.querySelector('#metric-moves').textContent === '1'")
    assert "missed-win" in requests[-1]["practiceMemory"]
    # Device reload restores memory, while connections must be configured again.
    page.reload()
    page.locator("#board .cell").first.wait_for()
    configure()
    page.locator("#step").click()
    page.wait_for_function("() => document.querySelector('#metric-moves').textContent === '1'")
    assert "missed-win" in requests[-1]["practiceMemory"]
    # Frozen evaluation never adds episodes, and the snapshot follows each name after seat swap.
    page.locator("nav [data-tab=evals]").click()
    page.locator("#eval-memory").check()
    start = len(requests)
    page.locator("#run-series").click()
    page.wait_for_function("() => document.querySelector('#series-results').textContent.includes('2 / 2 attempts recorded')")
    assert page.evaluate("key => localStorage.getItem(key)", KEY) == before
    assert all("practiceMemory" in r for r in requests[start:])
    page.locator("nav [data-tab=evals]").click()
    with page.expect_download() as result:
        page.locator("#export-series").click()
    receipt = json.loads(Path(result.value.path()).read_text())
    assert receipt["learning"]["mode"] == "frozen-practice-memory"
    assert receipt["learning"]["updatesFromEvaluation"] is False
    assert len(receipt["learning"]["acceptedRequestContexts"]) == 12
    assert "PRIVATE_STRATEGY_SENTINEL" not in json.dumps(receipt["learning"])
    # A baseline explicitly omits memory and cannot train on its own outcomes.
    page.locator("#eval-memory").uncheck()
    start = len(requests)
    page.locator("#run-series").click()
    page.wait_for_function("() => document.querySelector('#series-results').textContent.includes('2 / 2 attempts recorded')")
    assert not any("practiceMemory" in r for r in requests[start:])
    assert page.evaluate("key => localStorage.getItem(key)", KEY) == before
    page.locator("nav [data-tab=academy]").click()
    page.screenshot(path=str(Path(__file__).parents[1] / "output/playwright/learning-mobile.png"), full_page=True)
    page.locator("#clear-learning").click()
    assert page.evaluate("key => localStorage.getItem(key)", KEY) is None
    assert not errors, errors
    context.close()
    browser.close()
print("PASS: practice -> replay-verified memory -> next request -> reload -> frozen eval -> baseline -> clear; synthetic only")
