"""Guided connection drafts and safe agent handoff; no real provider/clipboard calls."""
import json
import os
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get("BUILDERWARS_TEST_URL", "http://127.0.0.1:5178")
MODEL = "private-model-sentinel/fixture"
MODEL_B = "private-second-model-sentinel/fixture"
SENTINELS = [MODEL, "PRIVATE_NAME_SENTINEL", "PRIVATE_KEY_SENTINEL",
             "private-endpoint-sentinel.example", "PRIVATE_STRATEGY_SENTINEL"]
CLIENTS = ["chatgpt_codex", "opencode", "openrouter", "hermes", "custom_agent"]

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
    context.add_init_script("""(() => {
      window.__setupCopies = []; window.__rejectSetupCopy = false;
      Object.defineProperty(navigator, 'clipboard', {configurable:true, value:{writeText:async text => {
        if (window.__rejectSetupCopy) throw Error('Synthetic clipboard refusal');
        window.__setupCopies.push(text);
      }}});
    })();""")
    origin = urlparse(BASE)
    external, catalogs, errors = [], [], []
    def contain(route):
        target = urlparse(route.request.url)
        if route.request.url == "https://openrouter.ai/api/v1/models":
            catalogs.append(route.request.method)
            route.fulfill(json={"data": [{"id": MODEL, "name": "Synthetic paid fixture",
                "pricing": {"prompt": "0.000002", "completion": "0.000004"},
                "reasoning": {"supported_efforts": ["high"]}},
                {"id": MODEL_B, "name": "Synthetic second model"}]})
        elif (target.scheme, target.netloc) == (origin.scheme, origin.netloc):
            route.continue_()
        else:
            external.append(route.request.url)
            route.abort()
    context.route("**/*", contain)
    context.route_web_socket("**/*", lambda socket: socket.close())
    page = context.new_page()
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(BASE)
        saved_seat = page.locator('[data-seat="0"]').text_content()
        def tab_to(selector):
            target = page.locator(selector)
            for _ in range(180):
                if target.evaluate("el => el === document.activeElement"):
                    return
                page.keyboard.press("Tab")
            raise AssertionError(f"Keyboard could not reach {selector}")
        def activate(selector):
            tab_to(selector)
            page.keyboard.press("Enter")
        def safe_brief():
            text = page.locator("#agent-setup-text").input_value()
            assert all(sentinel not in text for sentinel in SENTINELS), text
            assert "https://builderwars.com/agent-setup.md" in text
            assert "builderwars.agent-profile.v1" in text
            return text

        activate("#connections")
        expect(page.locator("#agent-name")).to_be_visible()
        expect(page.locator("#import-agent")).to_be_visible()
        expect(page.locator("#connection-advanced > summary")).to_contain_text("Strategy and profile")
        assert not page.locator("#connection-advanced").evaluate("el => el.open")
        expect(page.locator("#strategy")).not_to_be_visible()
        expect(page.locator("#copy-agent-setup")).not_to_be_visible()
        expect(page.locator("#connection-summary")).to_contain_text("No account needed")
        expect(page.locator("#connection-summary")).to_contain_text("Use contender")

        page.locator("#agent-kind").select_option("openrouter")
        page.locator(f'#model-id option[value="{MODEL}"]').wait_for(state="attached")
        expect(page.locator("#model-id")).to_have_value("")
        expect(page.locator('#model-id option[value=""]')).to_have_attribute("disabled", "")
        assert "$" not in page.locator("#model-price").inner_text(), "Blank selection must not quote an automatically selected paid model"
        assert not page.locator("#model-options").evaluate("el => el.open")
        expect(page.locator("#copy-agent-setup")).to_be_visible()
        page.locator("#agent-name").fill(SENTINELS[1])
        page.locator("#agent-key").fill(SENTINELS[2])
        page.locator("#agent-form button[type=submit]").click()
        assert page.locator("#agent-dialog").evaluate("el => el.open"), "A blank model cannot save a paid contender"
        assert not external
        page.locator("#model-id").select_option(MODEL)
        expect(page.locator("#model-id")).to_have_value(MODEL)
        expect(page.locator("#model-price")).to_contain_text("$")
        activate("#model-options > summary")
        expect(page.locator("#effort")).to_be_visible()
        page.locator("#effort").select_option("high")
        activate("#connection-advanced > summary")
        page.locator("#strategy").fill(SENTINELS[4])
        page.locator("#harness-url").evaluate("(el, value) => el.value = value", "https://" + SENTINELS[3] + "/move")
        activate("#connection-advanced > summary")

        expect(page.locator("#agent-setup-preview")).not_to_be_visible()
        activate("#show-agent-setup")
        expect(page.locator("#show-agent-setup")).to_have_attribute("aria-expanded", "true")
        expect(page.locator("#agent-setup-text")).to_be_visible()
        assert page.locator("#agent-setup-text").get_attribute("readonly") is not None
        assert not page.locator("#agent-setup-text").is_editable()
        brief = safe_brief()
        assert "OpenRouter API key in the browser" in brief
        activate("#copy-agent-setup")
        expect(page.locator("#agent-setup-status")).not_to_be_empty()
        assert page.evaluate("__setupCopies.at(-1)") == brief
        activate("#show-agent-setup")
        expect(page.locator("#agent-setup-preview")).not_to_be_visible()

        page.locator("#agent-kind").select_option("harness")
        expect(page.locator("#connection-summary")).to_contain_text("Start a match separately")
        expect(page.locator("#copy-agent-setup")).to_be_visible()
        expect(page.locator("#local-client")).to_be_visible()
        assert page.locator("#local-client option").evaluate_all("options => options.map(o => o.value)") == CLIENTS
        page.locator("#harness-url").fill("https://" + SENTINELS[3] + "/move")
        page.locator("#harness-model").fill(MODEL)
        page.locator("#agent-key").fill(SENTINELS[2])
        page.locator("#use-local-address").click()
        expect(page.locator("#harness-url")).to_have_value("http://127.0.0.1:8765/move")
        expect(page.locator("#agent-key")).to_have_value("")
        expect(page.locator("#harness-model")).to_have_value(MODEL)
        assert not external, "Restoring the local address must not contact any endpoint"
        page.locator("#harness-url").fill("https://" + SENTINELS[3] + "/move")
        page.locator("#agent-key").fill(SENTINELS[2])
        page.locator("#check-connection").click()
        expect(page.locator("#dialog-status")).to_contain_text("unchecked")
        checked_status = page.locator("#dialog-status").inner_text()
        for client in CLIENTS:
            page.locator("#local-client").select_option(client)
            expect(page.locator("#dialog-status")).to_have_text(checked_status)
            expect(page.locator("#agent-key")).to_have_value(SENTINELS[2])
            page.locator("#copy-agent-setup").click()
            text = page.evaluate("__setupCopies.at(-1)")
            assert all(sentinel not in text for sentinel in SENTINELS)
            assert f"customer-local bridge; client {client}" in text
            assert "127.0.0.1:8765" in text and "--max-calls" in text
            assert "stop the bridge" in text and "Do not expose the port publicly" in text
        page.evaluate("__rejectSetupCopy = true")
        if page.locator("#agent-setup-preview").is_visible():
            page.locator("#show-agent-setup").click()
        page.locator("#copy-agent-setup").click()
        expect(page.locator("#agent-setup-preview")).to_be_visible()
        expect(page.locator("#agent-setup-status")).not_to_be_empty()
        safe_brief()
        screenshot_dir = Path(__file__).parents[1] / "output" / "playwright"
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        for width in [320, 390, 768]:
            page.set_viewport_size({"width": width, "height": 900})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
            assert page.locator("#agent-dialog").evaluate("el => el.scrollWidth <= el.clientWidth + 1"), width
            expect(page.locator("#copy-agent-setup")).to_be_visible()
            expect(page.locator("#connection-summary")).to_be_visible()
            page.locator("#agent-dialog").evaluate("el => el.scrollTop = 0")
            page.screenshot(path=str(screenshot_dir / f"connection-guide-{width}.png"), full_page=True)
        activate("#close-dialog")
        assert page.locator('[data-seat="0"]').text_content() == saved_seat
        expect(page.locator("#metric-moves")).to_have_text("0")
        activate("#connections")
        expect(page.locator("#agent-kind")).to_have_value("bot")
        assert page.locator("#agent-name").input_value() != SENTINELS[1]
        activate("#close-dialog")
        # Reopening each seat restores its saved model, never the other seat's draft.
        for seat, model in [(0, MODEL), (1, MODEL_B)]:
            page.locator(f'[data-seat="{seat}"]').click()
            page.locator("#agent-kind").select_option("openrouter")
            page.locator(f'#model-id option[value="{model}"]').wait_for(state="attached")
            expect(page.locator("#model-id")).to_have_value("")
            page.locator("#model-id").select_option(model)
            page.locator("#agent-key").fill(SENTINELS[2])
            page.locator("#agent-form button[type=submit]").click()
        for seat, saved, draft in [(0, MODEL, MODEL_B), (1, MODEL_B, MODEL), (0, MODEL, MODEL_B)]:
            page.locator(f'[data-seat="{seat}"]').click()
            expect(page.locator("#model-id")).to_have_value(saved)
            page.locator("#model-id").select_option(draft)
            page.locator("#close-dialog").click()
        expect(page.locator("#metric-moves")).to_have_text("0")
        assert catalogs and not external, external
        assert not errors, errors
        print(json.dumps({"status": "PASS", "actualProviderCalls": 0, "journeys": [
            "explicit model selection", "safe enum-only setup brief", "clipboard fallback", "keyboard disclosure controls",
            "320/390/768 dialog overflow", "cancel preserves contender", "local address clears credential",
            "separate saved seat models", "no automatic model or auth calls"]}))
    finally:
        context.close()
        browser.close()
