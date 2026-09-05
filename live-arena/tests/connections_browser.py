"""Explicit connection checks and before-move failure gates; synthetic traffic only."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.environ.get("BUILDERWARS_TEST_URL", "http://127.0.0.1:5178")
OUT = Path(__file__).parents[1] / "output" / "playwright"
OUT.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    errors, moves, probes = [], [], []
    page.on("pageerror", lambda e: errors.append(str(e)))
    status = [200]
    page.route("https://openrouter.ai/api/v1/models", lambda r: r.fulfill(json={"data": [{"id": "test/model", "name": "Synthetic", "reasoning": {"supported_efforts": ["high"]}}]}))
    def key_info(route):
        probes.append(route.request.method)
        route.fulfill(status=status[0], json={"data": {"is_free_tier": True, "label": "PRIVATE_ACCOUNT_SENTINEL", "creator_user_id": "PRIVATE_ACCOUNT_SENTINEL"}})
    page.route("https://openrouter.ai/api/v1/key", key_info)
    page.route("https://openrouter.ai/api/v1/chat/completions", lambda r: (moves.append(r.request.method), r.fulfill(json={"choices": [{"message": {"content": '{"move":"0"}'}}]})))
    page.goto(BASE)
    page.locator("[data-game=connect4]").click()
    page.locator("#connections").click()
    page.locator("#agent-kind").select_option("openrouter")
    page.locator('#model-id option[value="test/model"]').wait_for(state="attached")
    page.locator("#model-id").select_option("test/model")
    page.locator("#agent-key").fill("synthetic-connection-sentinel")
    page.locator("#check-connection").click()
    page.wait_for_function("() => document.querySelector('#dialog-status').textContent.includes('API key recognized')")
    assert probes == ["GET"] and not moves
    assert "PRIVATE_ACCOUNT_SENTINEL" not in page.locator("body").inner_text()
    assert "PRIVATE_ACCOUNT_SENTINEL" not in page.evaluate("JSON.stringify(localStorage)")
    page.screenshot(path=str(OUT / "connection-check-mobile.png"), full_page=True)
    # Input changes invalidate prior success; late replies do not restore it.
    page.evaluate('''() => { const original = window.fetch; window.restoreProbeFetch = () => window.fetch = original;
      window.fetch = (url, opts) => String(url).endsWith('/key') ? new Promise(resolve => window.resolveProbe = () => resolve(new Response(JSON.stringify({data:{is_free_tier:true}})))) : original(url, opts); }''')
    page.locator("#check-connection").click()
    page.locator("#agent-key").fill("changed-synthetic")
    page.evaluate("window.resolveProbe()")
    page.wait_for_timeout(100)
    assert page.locator("#dialog-status").inner_text() == ""
    assert page.locator("#check-connection").is_enabled()
    page.evaluate("window.restoreProbeFetch()")
    # Saving a contender performs local validation only. The first move must pass auth.
    page.locator("#agent-form button[type=submit]").click()
    status[0] = 401
    page.locator("#step").click()
    page.wait_for_function("() => document.querySelector('#notice').textContent.includes('401')")
    assert not moves and page.locator("#metric-moves").inner_text() == "0"
    for error_status in [429, 500]:
        status[0] = error_status
        page.locator("#step").click()
        page.wait_for_function(f"() => document.querySelector('#notice').textContent.includes('{error_status}')")
        assert not moves
    status[0] = 200
    # Accelerated synthetic preflight deadline must not claim a 120s model timeout.
    page.evaluate('''() => { const fetchBefore = window.fetch, timeoutBefore = AbortSignal.timeout;
      window.restoreDeadline = () => { window.fetch = fetchBefore; AbortSignal.timeout = timeoutBefore; };
      AbortSignal.timeout = ms => timeoutBefore.call(AbortSignal, ms === 15000 ? 20 : ms);
      window.fetch = (url, opts) => String(url).endsWith('/key') ? new Promise((resolve, reject) => {
        if(opts.signal.aborted) reject(opts.signal.reason);
        else opts.signal.addEventListener('abort', () => reject(opts.signal.reason), {once:true});
      }) : fetchBefore(url, opts); }''')
    page.locator("#start").click()
    page.wait_for_function("() => document.querySelector('#notice').textContent.includes('Connection check timed out after 15 seconds')")
    assert "No model invoked" in page.locator("#notice").inner_text()
    assert not moves
    page.evaluate("window.restoreDeadline()")
    page.locator("#step").click()
    page.wait_for_function("() => document.querySelector('#metric-moves').textContent==='1'")
    assert moves == ["POST"]
    assert "provider/unreported" in page.locator("#feed").inner_text()
    # An arbitrary HTTPS harness is not probed or falsely reported connected.
    page.locator("#reset").click()
    page.locator("#connections").click()
    page.locator("#agent-kind").select_option("harness")
    page.locator("#harness-url").fill("https://harness.example/move")
    arbitrary = []
    page.route("https://harness.example/**", lambda r: (arbitrary.append(r.request.url), r.abort()))
    page.locator("#check-connection").click()
    page.wait_for_function("() => document.querySelector('#dialog-status').textContent.includes('unchecked')")
    assert not arbitrary
    for width in [320, 390, 768]:
        page.set_viewport_size({"width": width, "height": 900})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert page.locator("#check-connection").is_visible()
    page.locator("#close-dialog").click()
    assert not errors, errors
    context.close()
    browser.close()
    print(json.dumps({"status": "PASS", "actualProviderCalls": 0, "journeys": ["non-inference check", "account-data stripping", "stale check cancellation", "401/429/500 before inference", "unreported identity", "custom HTTPS unchecked", "mobile connection dialog"]}))
