"""Discover and configure through the published assistant contract; synthetic bridge only."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get("BUILDERWARS_TEST_URL", "http://127.0.0.1:5196")
with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={"width": 390, "height": 844})
    context.add_init_script("""Object.defineProperty(navigator, 'clipboard', {value:{writeText:async () => {throw Error('Clipboard denied')}}});""")
    page = context.new_page()
    errors, probes, moves = [], [], []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.route("https://openrouter.ai/**", lambda r: r.fulfill(json={"data": []}))
    def bridge(route):
        if route.request.url.endswith("/health"):
            probes.append(route.request.method)
            route.fulfill(json={"schema": "builderwars.bridge.health.v1", "remainingCalls": 20, "busy": False})
        else:
            moves.append(route.request.method)
            route.abort()
    page.route("http://127.0.0.1:8765/**", bridge)
    try:
        discovery = context.request.get(BASE + "/llms.txt")
        assert "/.well-known/builderwars-agent-workflow.json" in discovery.text() and "/duel-agent.md" in discovery.text()
        manifest = context.request.get(BASE + "/.well-known/builderwars-agent-workflow.json").json()
        controls, connections = manifest["controls"], manifest["connection_controls"]
        assert manifest["interface"] == "website-browser-automation"
        guide = context.request.get(BASE + "/duel-agent.md").text()
        assert "same device" in guide and "without inference" in guide
        no_js = browser.new_context(java_script_enabled=False)
        introduction = no_js.new_page()
        introduction.goto(BASE + "/duels")
        expect(introduction.locator('a[href="/#duel"]').first).to_be_visible()
        no_js.close()
        page.goto(BASE)
        arena_agent = page.locator('[data-seat="0"]').text_content()
        page.locator("#step").click()
        expect(page.locator("#metric-moves")).to_have_text("1")
        page.goto(manifest["entry_url"].replace("https://builderwars.com", BASE))
        for selector in [*controls.values(), *connections.values()]:
            expect(page.locator(selector)).to_have_count(1)
        def state():
            return json.loads(page.locator(manifest["state_selector"]).text_content())
        assert state()["phase"] == "setup"
        expect(page.locator(controls["ready"])).to_be_disabled()
        page.locator(controls["configure"]).click()
        expect(page.locator(connections["kind"])).to_have_value("harness")
        page.locator(connections["harness_url"]).fill("http://127.0.0.1:8765/move")
        page.locator(connections["credential"]).fill("PRIVATE_TOKEN_SENTINEL")
        page.locator(connections["check_connection"]).click()
        expect(page.locator("#dialog-status")).to_contain_text("No model invoked")
        assert probes == ["GET"] and not moves
        page.locator(connections["use_contender"]).click()
        expect(page.locator("#agent-dialog")).not_to_be_visible()
        expect(page.locator("#duel-agent")).not_to_contain_text("Free built-in")
        page.locator('[data-tab="arena"]').click()
        assert page.locator('[data-seat="0"]').text_content() == arena_agent
        expect(page.locator("#metric-moves")).to_have_text("1")
        page.locator('[data-tab="duel"]').click()
        page.locator(controls["configure"]).click()
        expect(page.locator(connections["credential"])).to_have_value("PRIVATE_TOKEN_SENTINEL")
        page.locator("#forget-key").click()
        page.locator("#close-dialog").click()
        page.locator(controls["configure"]).click()
        expect(page.locator(connections["credential"])).to_have_value("")
        page.locator("#close-dialog").click()
        for width in [320, 390, 768, 1440]:
            page.set_viewport_size({"width": width, "height": 900})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
            page.locator("#duel-assistant").click()
            expect(page.locator("#duel-help-dialog")).to_be_visible()
            brief = page.locator("#duel-help-text").input_value()
            assert "PRIVATE_TOKEN_SENTINEL" not in brief
            assert "PRIVATE_TOKEN_SENTINEL" not in json.dumps(state())
            assert "127.0.0.1:8765" not in brief
            assert "Click Ready only within my explicit play authorization" in brief
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
            page.locator("#duel-help-copy").click()
            expect(page.locator("#duel-help-status")).to_contain_text("copy it manually")
            assert page.locator("#duel-help-text").evaluate("el => el.selectionEnd - el.selectionStart") == len(brief)
            page.locator("#duel-help-close").click()
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator(controls["join_url"]).fill("https://other.example/#duel=room")
        page.locator(controls["join"]).click()
        expect(page.locator(controls["status"])).to_contain_text("Use a BuilderWars invitation")
        expect(page.locator(controls["status"])).to_be_in_viewport(ratio=0.99)
        assert state()["active"] is False
        page.goto(BASE + "/#duel=test-invitation")
        expect(page.locator("#duel-incoming-card")).to_be_visible()
        expect(page.locator(controls["create"])).not_to_be_visible()
        page.locator("#duel-assistant").click()
        assert "https://builderwars.com/#duel=test-invitation" in page.locator("#duel-help-text").input_value()
        page.locator("#duel-help-close").click()
        page.locator("#duel-new").click()
        expect(page.locator(controls["create"])).to_be_visible()
        page.locator(controls["use_free"]).click()
        expect(page.locator("#duel-agent")).to_contain_text("Free built-in")
        page.locator("#duel-name").fill("Renamed duel agent")
        page.locator("#duel-name").press("Tab")
        page.locator('[data-tab="arena"]').click()
        assert page.locator('[data-seat="0"]').text_content() == arena_agent
        page.locator('[data-tab="duel"]').click()
        Path("output/duels").mkdir(parents=True, exist_ok=True)
        page.set_viewport_size({"width": 390, "height": 844})
        page.screenshot(path="output/duels/onboarding-mobile.png", full_page=True)
        page.set_viewport_size({"width": 1440, "height": 1100})
        page.screenshot(path="output/duels/onboarding-desktop.png", full_page=True)
        assert not errors, errors
        assert not moves, moves
        print(json.dumps({"status": "PASS", "manifestDrivenSetup": True, "nonInferenceHealthChecks": len(probes),
            "modelCalls": 0, "widths": [320, 390, 768, 1440], "clipboardFallback": True, "secretLeak": False}))
    finally:
        browser.close()
