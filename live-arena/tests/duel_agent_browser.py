"""Published discovery-to-play contract with real PeerJS and synthetic local model replies."""
import json
import os
import re
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get("BUILDERWARS_TEST_URL", "http://127.0.0.1:5196")
with sync_playwright() as p:
    browser = p.chromium.launch()
    host, guest = browser.new_context(), browser.new_context()
    h, g = host.new_page(), guest.new_page()
    probes, moves, errors = [], [], []
    for page in [h, g]:
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.route("https://openrouter.ai/**", lambda r: r.fulfill(json={"data": []}))
    def synthetic_bridge(route):
        if route.request.url.endswith("/health"):
            probes.append(route.request.method)
            route.fulfill(json={"schema": "builderwars.bridge.health.v1", "remainingCalls": 2, "busy": False})
        else:
            body = route.request.post_data_json
            moves.append(body)
            route.fulfill(json={"move": body["legalMoves"][0], "model": "synthetic/local-fixture"})
    h.route("http://127.0.0.1:8765/**", synthetic_bridge)
    try:
        manifest = host.request.get(BASE + "/builderwars-agent-workflow.json").json()
        c, a = manifest["controls"], manifest["connection_controls"]
        h.goto(manifest["entry_url"].replace("https://builderwars.com", BASE))
        h.locator(c["configure"]).click()
        h.locator(a["harness_url"]).fill("http://127.0.0.1:8765/move")
        h.locator(a["credential"]).fill("SYNTHETIC_PRIVATE_TOKEN")
        h.locator(a["check_connection"]).click()
        expect(h.locator("#dialog-status")).to_contain_text("No model invoked")
        h.locator(a["use_contender"]).click()
        h.locator(c["game"]).select_option("tictactoe")
        h.locator(c["advanced"] + " summary").click()
        h.locator(c["move_limit"]).fill("2")
        h.locator(c["max_tokens"]).fill("256")
        h.locator(c["create"]).click()
        expect(h.locator(c["invitation"])).to_have_value(re.compile(".*#duel=.+"), timeout=30000)
        link = h.locator(c["invitation"]).input_value()
        g.goto(link)
        g.locator(c["use_free"]).click()
        g.locator(c["join"]).click()
        expect(g.locator(c["ready"])).to_be_enabled(timeout=30000)
        guest_state = json.loads(g.locator(manifest["state_selector"]).text_content())
        assert guest_state["game"] == "tictactoe" and guest_state["limits"] == {"moveLimit": 2, "maxTokens": 256}
        assert probes == ["GET"] and not moves
        h.locator(c["ready"]).click()
        expect(g.locator("#duel-friend")).to_contain_text("Your friend is ready")
        assert not moves, "host Ready alone must not start inference"
        g.locator(c["ready"]).click()
        expect(g.locator(c["status"])).to_contain_text("Move limit reached", timeout=30000)
        for page in [h, g]:
            state = json.loads(page.locator(manifest["state_selector"]).text_content())
            assert state["phase"] == "finished" and state["moves"] == 2
            assert "SYNTHETIC_PRIVATE_TOKEN" not in json.dumps(state)
        assert len(moves) == 1 and moves[0]["maxTokens"] == 256
        assert h.locator("#duel-score").inner_text() == g.locator("#duel-score").inner_text()
        h.locator(c["stop"]).click()
        assert not errors, errors
        print(json.dumps({"status": "PASS", "publishedContract": True, "realPeerSignaling": True,
            "syntheticModelMoves": len(moves), "realModelCalls": 0, "bothReadyRequired": True, "boundedGame": True}))
    finally:
        browser.close()
