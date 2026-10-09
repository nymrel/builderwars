"""Regression coverage for the September 6 and October 4 priority UX audits."""
import base64
import gzip
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get("BUILDERWARS_TEST_URL", "http://127.0.0.1:5178").rstrip("/")


def download_record(page):
    settings = page.locator(".match-settings").filter(has=page.locator("#export"))
    if not settings.evaluate("el => el.open"):
        settings.locator("summary").click()
    with page.expect_download() as exported:
        page.locator("#export").click()
    return json.loads(Path(exported.value.path()).read_text())


def check_pause(browser, errors):
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(BASE)
        page.locator('[data-game="tictactoe"]').click()
        page.locator("#play-human").click()
        page.locator("#start").click()
        page.locator('[data-cell="0"]').click()
        expect(page.locator("#metric-moves")).to_have_text("1")
        expect(page.locator("#match-status")).to_have_text("Auto-play paused · Tactician to move")
        expect(page.locator("#start")).to_have_text("▶ Resume auto-play")
        expect(page.locator("#step")).to_be_enabled()
        assert "pulsing" not in page.locator("#match-dot").get_attribute("class")
        page.wait_for_timeout(750)  # Longer than the default 500 ms auto-play pace.
        expect(page.locator("#metric-moves")).to_have_text("1")

        page.locator("#step").click()
        expect(page.locator("#metric-moves")).to_have_text("2")
        expect(page.locator("#match-status")).to_have_text("Auto-play paused · You to move")
        expect(page.locator("#start")).to_have_text("▶ Resume auto-play")
        paused_record = download_record(page)
        assert len(paused_record["events"]) == 2
        assert paused_record["status"] == "Auto-play paused"
        page.wait_for_timeout(750)
        expect(page.locator("#metric-moves")).to_have_text("2")

        page.locator("#board .cell.target").first.click()
        expect(page.locator("#metric-moves")).to_have_text("3")
        expect(page.locator("#match-status")).to_have_text("Auto-play paused · Tactician to move")
        page.locator("#start").click()
        expect(page.locator("#metric-moves")).to_have_text("4")
        expect(page.locator("#match-status")).to_have_text("You to move")
        expect(page.locator("#start")).to_have_text("Ⅱ Pause auto-play")
        expect(page.locator("#step")).to_be_disabled()

        page.locator("#reset").click()
        expect(page.locator("#metric-moves")).to_have_text("0")
        expect(page.locator("#match-status")).to_have_text("Ready")
        expect(page.locator("#start")).to_have_text("▶ Start match")
        expect(page.locator("#step")).to_be_enabled()
        page.wait_for_timeout(750)
        expect(page.locator("#metric-moves")).to_have_text("0")
    finally:
        page.close()


def check_replay_positions(browser, errors):
    page = browser.new_page()
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(BASE)
        page.locator('[data-game="tictactoe"]').click()
        for seat in (0, 1):
            page.locator(f'[data-seat="{seat}"]').click()
            page.locator("#agent-kind").select_option("human")
            page.locator("#agent-name").fill(f"Replay human {seat + 1}")
            page.locator('#agent-form button[type="submit"]').click()
        for move in (0, 1, 2, 4, 3, 5, 7, 6, 8):
            page.locator(f'[data-cell="{move}"]').click()
        expect(page.locator("#match-status")).to_have_text("Draw")
        recorded = download_record(page)
        assert len(recorded["events"]) == 9 and recorded["status"] == "Board full"
    finally:
        page.close()

    encoded = base64.urlsafe_b64encode(gzip.compress(json.dumps(recorded).encode())).decode().rstrip("=")
    for width in (390, 1280):
        page = browser.new_page(viewport={"width": width, "height": 900})
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(BASE + "/#replay=" + encoded)
            expect(page.locator("#result-title")).to_have_text("Draw")
            for ply in (0, 7, 8, 9):
                page.locator("#replay-position").fill(str(ply))
                expect(page.locator("#ply")).to_have_text(f"PLY {ply:02}")
                expect(page.locator("#board .disc")).to_have_count(ply)
                expected_status = "Draw" if ply == 9 else f"Replay human {ply % 2 + 1} to move"
                expect(page.locator("#match-status")).to_have_text(expected_status)
                expect(page.locator("#seats .on-turn")).to_have_count(0 if ply == 9 else 1)
                if ply < 9:
                    expect(page.locator("#seats .on-turn")).to_have_attribute("data-seat", str(ply % 2))
                expect(page.locator("#result-label")).to_have_text("RECORDED MATCH RESULT · EXHIBITION")
                expect(page.locator("#result-title")).to_have_text("Draw")
                expect(page.locator("#result-detail")).to_contain_text("9 plies · Board full")
                for control in ("start", "step", "reset"):
                    expect(page.locator(f"#{control}")).to_be_disabled()
                assert "pulsing" not in page.locator("#match-dot").get_attribute("class")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                if ply == 7:
                    assert download_record(page) == recorded, "Seeking must not truncate or rewrite the recorded result"
        finally:
            page.close()


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
    expect(page.locator("#play-human")).to_have_text("Play yourself ↗")
    expect(page.locator("#quickplay")).to_have_text("Watch bots play")
    expect(page.locator("#connect-first")).to_have_text("Enter your agent")

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
    downloads = []
    page.on("download", lambda download: downloads.append(download.suggested_filename))
    forge_url = page.url
    expect(page.locator("#forge-status")).to_have_attribute("role", "status")
    expect(page.locator("#forge-status")).to_have_attribute("aria-live", "polite")
    for name in ("", "   ", "x" * 49):
        # Programmatic assignment also exercises values beyond HTML maxlength.
        page.locator("#creator-name").evaluate("(el, name) => el.value = name", name)
        for action in ("export", "create"):
            if action == "export":
                page.locator("#export-rules").click()
            else:
                # Exercise the submit handler independently of native required validation.
                page.locator("#creator").evaluate("el => el.dispatchEvent(new Event('submit', {bubbles: true, cancelable: true}))")
            expect(page.locator("#forge-status")).to_have_text("Game name must contain 1–48 characters and cannot be blank.")
            assert page.locator("#forge").is_visible()
            assert page.url == forge_url
            assert not downloads
    page.locator("#creator-name").fill("Valid game")
    page.locator("#creator-connect").fill("9")
    page.locator("#export-rules").click()
    expect(page.locator("#forge-status")).to_have_text("Use a 3–10 square board and a valid connect length.")
    assert page.url == forge_url and not downloads
    page.locator("#creator-connect").fill("5")
    with page.expect_download() as exported:
        page.locator("#export-rules").click()
    assert json.loads(Path(exported.value.path()).read_text())["name"] == "Valid game"
    expect(page.locator("#forge-status")).to_have_text("Game rules downloaded.")
    check_pause(browser, errors)
    check_replay_positions(browser, errors)
    assert not errors, errors
    browser.close()

print("PASS: priority UX regressions; pause/manual move/Step/resume/reset; replay plies 0/7/8/9 at 390/1280px.")
