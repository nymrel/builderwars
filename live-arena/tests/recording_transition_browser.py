"""Real UI regression coverage. Synthetic recordings only; no provider calls.

Run against an owned web preview via run_browser_ci.py. Not physical-device proof.
"""
import copy
import json
import os
from pathlib import Path
import subprocess
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ["BUILDERWARS_TEST_URL"].rstrip("/") + "/"
FIXTURES = json.loads(subprocess.check_output(
    ["node", "--import", "tsx", "tests/fixtures/recording-browser.ts"], cwd=ROOT))

with sync_playwright() as p:
    browser = p.chromium.launch()
    errors = []

    def current(context):
        page = context.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(BASE)
        page.locator("[data-game=tictactoe]").click()
        page.locator("#step").click()
        expect(page.locator("#metric-moves")).to_have_text("1")
        page.locator(".match-settings summary").filter(has_text="Match settings").click()
        return page

    def upload(page, value, selector="#import", name="recording.json"):
        payload = value.encode() if isinstance(value, str) else json.dumps(value).encode()
        page.locator(selector).set_input_files({"name": name, "mimeType": "application/json", "buffer": payload})

    def open_route(page, route):
        if route == "link":
            page.goto(BASE + "#replay=" + FIXTURES["link"])
        elif route == "proof":
            page.locator("#match-proof summary").click()
            upload(page, FIXTURES["proof"], "#import-proof", "recording.jsonl")
        else:
            upload(page, FIXTURES[route])

    # All routes preserve the current game until explicit acceptance, including
    # keyboard dismissal, and share a download-before-replacement affordance.
    for route in ("record", "package", "link", "proof", "exhibition"):
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = current(context)
        seats = page.locator("#seats").inner_text()
        open_route(page, route)
        expect(page.locator("#recording-dialog")).to_be_visible()
        expect(page.locator("#recording-recovery")).to_contain_text("Saved in Recent matches")
        expect(page.locator("#metric-moves")).to_have_text("1")
        expect(page.locator("#keep-current-match")).to_be_focused()
        with page.expect_download() as download:
            page.locator("#download-current-match").click()
        preserved = json.loads(Path(download.value.path()).read_bytes())
        assert preserved["record"]["rules"]["kind"] == "tictactoe"
        assert len(preserved["record"]["events"]) == 1
        page.keyboard.press("Escape")
        expect(page.locator("#recording-dialog")).not_to_be_visible()
        expect(page.locator("#notice")).to_contain_text("Your current match is unchanged")
        assert page.locator("#seats").inner_text() == seats
        open_route(page, route)
        page.locator("#open-recording").click()
        expect(page.locator("#start")).to_be_disabled()
        expect(page.locator("#metric-moves")).to_have_text("2" if route == "exhibition" else "7")
        context.close()

    # Neither a storage opt-out nor storage denial may silently replace work or
    # imply that a recovery checkpoint exists.
    for mode in ("off", "denied"):
        context = browser.new_context(viewport={"width": 320, "height": 780})
        if mode == "denied":
            context.add_init_script("Object.defineProperty(window, 'localStorage', {get() {throw Error('Storage denied')}})")
        page = current(context)
        if mode == "off":
            page.locator("#match-library summary").click()
            page.locator("#save-matches").uncheck()
            expect(page.locator("#save-disclosure")).to_contain_text("Automatic saving is off")
        upload(page, FIXTURES["record"])
        expect(page.locator("#recording-recovery")).to_contain_text("Device saving is off, unavailable")
        assert page.evaluate("document.querySelector('#recording-dialog').scrollWidth <= document.querySelector('#recording-dialog').clientWidth")
        page.locator("#keep-current-match").click()
        expect(page.locator("#metric-moves")).to_have_text("1")
        context.close()

    context = browser.new_context()
    context.add_init_script("""(() => {
      const read = File.prototype.arrayBuffer;
      window.releaseRead = null;
      File.prototype.arrayBuffer = async function() {
        if (this.name.startsWith('slow')) await new Promise(resolve => window.releaseRead = resolve);
        return read.call(this);
      };
    })()""")
    page = current(context)
    invalid = copy.deepcopy(FIXTURES["record"])
    invalid["events"][0]["move"] = "99"
    upload(page, invalid)
    expect(page.locator("#notice")).to_contain_text("Recording import rejected: The recording contains an illegal move")
    expect(page.locator("#recording-dialog")).not_to_be_visible()
    expect(page.locator("#metric-moves")).to_have_text("1")

    upload(page, FIXTURES["record"], name="slow-recording.json")
    page.wait_for_function("() => typeof releaseRead === 'function'")
    page.locator("#max-tokens").fill("4096")
    page.evaluate("releaseRead()")
    expect(page.locator("#notice")).to_contain_text("match changed during import")
    expect(page.locator("#metric-moves")).to_have_text("1")
    expect(page.locator("#max-tokens")).to_have_value("4096")

    # A superseded modal must settle before the next prompt installs handlers.
    upload(page, FIXTURES["record"])
    expect(page.locator("#recording-dialog")).to_be_visible()
    upload(page, FIXTURES["exhibition"])
    page.wait_for_function("() => document.querySelector('#recording-dialog').open && document.querySelector('#import').value !== ''")
    # The newer recording, not the older one, is committed.
    page.locator("#open-recording").click()
    expect(page.locator("#metric-moves")).to_have_text("2")
    expect(page.locator("#exhibition-evidence")).to_be_visible()
    context.close()

    # Recent-match replay and resume also use the shared replacement policy.
    context = browser.new_context()
    page = current(context)
    page.locator("#match-library summary").click()
    for action in ("replay", "resume"):
        page.locator(f"[data-saved-{action}]").first.click()
        expect(page.locator("#recording-dialog")).to_be_visible()
        page.locator("#keep-current-match").click()
        expect(page.locator("#metric-moves")).to_have_text("1")
    page.locator("[data-saved-replay]").first.click()
    page.locator("#open-recording").click()
    expect(page.locator("#start")).to_be_disabled()
    context.close()
    assert not errors, errors
    browser.close()
print("PASS: five recording routes; consent, dismissal, recovery download, opt-out/denial, invalid moves, settings race, superseding prompt, saved replay/resume.")
