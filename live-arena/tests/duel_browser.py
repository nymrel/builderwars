"""Two real browser contexts and PeerJS signaling; free agents, no model calls."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get("BUILDERWARS_TEST_URL", "http://127.0.0.1:5196")
with sync_playwright() as p:
    browser = p.chromium.launch()
    host = browser.new_context(viewport={"width": 1440, "height": 1100}, permissions=["clipboard-read", "clipboard-write"])
    guest = browser.new_context(viewport={"width": 390, "height": 844})
    errors, inference = [], []
    for context in [host, guest]:
        def contain(route):
            url = route.request.url
            if "openrouter.ai" in url or ":8765" in url:
                inference.append(url)
                route.abort()
            else:
                route.continue_()
        context.route("**/*", contain)
    h, g = host.new_page(), guest.new_page()
    for page in [h, g]:
        page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        h.goto(BASE)
        h.locator("#duel-first").click()
        h.locator("#duel-game").select_option("tictactoe")
        h.locator("#duel-create").click()
        expect(h.locator("#duel-link")).to_have_value(__import__("re").compile(".*#duel=.+"), timeout=30000)
        link = h.locator("#duel-link").input_value()
        g.goto(link)
        expect(g.locator("#duel-join")).to_be_visible()
        expect(g.locator("#duel-ready")).to_be_disabled()
        g.locator("#duel-join").click()
        expect(g.locator("#duel-ready")).to_be_enabled(timeout=30000)
        # A duplicate/forwarded invitation cannot evict the admitted opponent.
        extra = browser.new_page()
        extra.goto(link)
        extra.locator("#duel-join").click()
        expect(extra.locator("#duel-status")).to_contain_text(__import__("re").compile("left|closed|unavailable|interrupted|connect"), timeout=30000)
        extra.close()
        expect(h.locator("#duel-ready")).to_be_enabled()
        g.locator("#duel-ready").click()
        expect(h.locator("#duel-status")).to_contain_text("Your friend is ready", timeout=15000)
        expect(h.locator("#duel-replay")).to_be_disabled()
        h.locator("#duel-ready").click()
        expect(g.locator("#duel-status")).to_contain_text(__import__("re").compile("wins|Draw"), timeout=30000)
        assert h.locator("#duel-score").inner_text() == g.locator("#duel-score").inner_text()
        expect(g.locator("#duel-board .cell")).to_have_count(9)
        assert g.evaluate("document.documentElement.scrollWidth <= innerWidth"), "mobile overflow"
        Path("output/duels").mkdir(parents=True, exist_ok=True)
        h.screenshot(path="output/duels/desktop.png", full_page=True)
        g.screenshot(path="output/duels/mobile.png", full_page=True)
        h.locator("#duel-replay").click()
        expect(h.locator("#duel-status")).to_have_text("Replay link copied.")
        replay_link = h.evaluate("navigator.clipboard.readText()")
        replay_page = host.new_page()
        replay_page.goto(replay_link)
        expect(replay_page.locator("#metric-moves")).not_to_have_text("0")
        g.locator("#duel-leave").click()
        expect(h.locator("#duel-create")).to_be_visible(timeout=10000)
        expect(h.locator("#duel-download")).to_be_enabled()
        # Header connection editing must revoke the frozen agent/key in the room.
        h.locator("#duel-create").click()
        expect(h.locator("#duel-link")).not_to_have_value(link)
        g.locator("#duel-incoming").fill(h.locator("#duel-link").input_value())
        g.locator("#duel-join").click()
        expect(g.locator("#duel-ready")).to_be_enabled(timeout=30000)
        h.locator("#duel-ready").click()
        g.locator("#duel-ready").click()
        expect(h.locator("#duel-score")).to_contain_text("0 moves")
        h.locator("#connections").click()
        expect(h.locator("#duel-status")).to_contain_text("change or remove")
        expect(g.locator("#duel-create")).to_be_visible(timeout=10000)
        expect(h.locator("#duel-ready")).to_be_disabled()
        assert not errors, errors
        assert not inference, inference
        print(json.dumps({"status": "PASS", "realPeerSignaling": True, "independentContexts": 2,
            "bothReadyRequired": True, "matchingReplay": True, "mobileOverflow": False, "inferenceRequests": 0}))
    finally:
        browser.close()
