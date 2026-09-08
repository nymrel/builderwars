"""Regression coverage for the September 6 priority UX/runtime audit fixes."""
import os
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get("BUILDERWARS_TEST_URL", "http://127.0.0.1:5178").rstrip("/")

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={"width": 390, "height": 844})
    context.add_init_script("""
      window.__builderwarsWorkerUrls = [];
      const NativeWorker = window.Worker;
      window.Worker = new Proxy(NativeWorker, {
        construct(target, args) {
          window.__builderwarsWorkerUrls.push(String(args[0]));
          return Reflect.construct(target, args);
        }
      });
    """)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(BASE)
    page.locator("#board .cell").first.wait_for()

    # First play is explicit: human play, bot exhibition, or own contender.
    expect(page.locator("#play-human")).to_have_text("Play against a bot ↗")
    expect(page.locator("#quickplay")).to_have_text("Watch bots play")
    expect(page.locator("#connect-first")).to_have_text("Connect my agent")

    # Human helper is game-specific; Tactician work is offloaded to a Worker.
    page.locator('[data-game="tictactoe"]').click()
    page.locator("#play-human").click()
    expect(page.locator("#notice")).to_contain_text("choose an open cell")
    page.locator('[data-cell="0"]').click()
    page.wait_for_function("() => window.__builderwarsWorkerUrls.length > 0")
    page.wait_for_function("() => document.querySelector('#notice').textContent.includes('choose an open cell')")
    worker_urls = page.evaluate("window.__builderwarsWorkerUrls")
    assert any("bot-worker" in url for url in worker_urls), worker_urls

    # A rejected human move must not remain as stale status after a valid move.
    page.locator('[data-cell="0"]').click()
    expect(page.locator("#notice")).to_contain_text("highlighted legal moves")
    page.locator("#board .cell.target").first.click()
    page.wait_for_function("() => !document.querySelector('#notice').textContent.includes('highlighted legal moves')")

    # Invalid Watch input stays on Watch and never leaks the browser's raw URL exception.
    page.locator('nav [data-tab="watch"]').click()
    page.locator("#join-link").fill("not-a-watch-link")
    page.locator("#join").click()
    assert page.locator("#watch").is_visible()
    expect(page.locator("#watch-join-status")).to_have_text("Paste a complete BuilderWars watch link.")
    assert "Failed to construct" not in page.locator("#watch-join-status").inner_text()

    # Forge validation failures stay in Forge and render next to the controls.
    page.locator('nav [data-tab="forge"]').click()
    page.locator("#creator-name").fill("")
    page.locator("#export-rules").click()
    assert page.locator("#forge").is_visible()
    expect(page.locator("#forge-status")).not_to_have_text("Create or import rules here.")
    assert not errors, errors
    browser.close()

print("PASS: September 6 priority UX/runtime regressions are covered.")
