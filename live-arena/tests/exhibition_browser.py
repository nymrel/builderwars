"""Portable engine-assisted chess evidence, synthetic fixtures and blocked external traffic."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get("BUILDERWARS_TEST_URL", os.environ.get("BASE_URL", "http://127.0.0.1:5178"))
OUT = ROOT / "output" / "playwright"
FIXTURES = json.loads(subprocess.check_output(
    ["node", "--import", "tsx", str(ROOT / "tests" / "fixtures" / "exhibition-browser.ts")],
    cwd=ROOT, text=True, encoding="utf-8", timeout=30,
))


def reseal(value):
    """Rehash a deliberately invalid fixture so semantic checks must also reject it."""
    payload = {key: item for key, item in value.items() if key != "digest"}
    value["digest"] = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
        separators=(",", ":")).encode()).hexdigest()
    return value


with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
    context.add_init_script("""(() => {
      window.__exhibitionCopies = [];
      Object.defineProperty(navigator, 'clipboard', {configurable:true, value:{writeText:async text => {
        window.__exhibitionCopies.push(text);
      }}});
    })();""")
    origin = urlsplit(BASE)
    external, errors, downloads = [], [], []

    def contain(route):
        target = urlsplit(route.request.url)
        if (target.scheme, target.netloc) == (origin.scheme, origin.netloc):
            route.continue_()
        else:
            external.append(route.request.url)
            route.abort("blockedbyclient")

    context.route("**/*", contain)
    context.route_web_socket("**/*", lambda socket: socket.close())
    page = context.new_page()
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("download", lambda download: downloads.append(download.suggested_filename))
    try:
        page.goto(BASE)

        def settings():
            details = page.locator(".match-settings").filter(has=page.locator("#move-limit"))
            if not details.evaluate("el => el.open"):
                details.locator("summary").click()

        def library():
            details = page.locator("#match-library")
            if not details.evaluate("el => el.open"):
                details.locator("summary").click()

        def sources():
            details = page.locator("#exhibition-evidence details")
            if not details.evaluate("el => el.open"):
                details.locator("summary").click()

        def upload(value, watch=False):
            payload = {"name": "synthetic.exhibition.json", "mimeType": "application/json",
                "buffer": json.dumps(value).encode()}
            if watch:
                page.locator("nav [data-tab=watch]").click()
                with page.expect_file_chooser() as chooser:
                    page.locator("#import-exhibition").click()
                chooser.value.set_files(payload)
            else:
                page.locator("#import").set_input_files(payload)

        def export(selector="#export-exhibition", keyboard=False):
            if selector in ("#export", "#export-package"):
                settings()
            with page.expect_download() as pending:
                if keyboard:
                    page.locator(selector).press("Enter")
                else:
                    page.locator(selector).click()
            result = pending.value
            assert result.failure() is None
            return json.loads(Path(result.path()).read_text(encoding="utf-8"))

        def expect_package(value):
            expect(page.locator("#exhibition-evidence")).to_be_visible()
            expect(page.locator("#metric-moves")).to_have_text(str(len(value["record"]["events"])))
            sources()
            for digest in [*value["source"].values(), value["engine"]["binarySha256"], value["digest"]]:
                expect(page.locator("#exhibition-sources")).to_contain_text(digest)
            assert export() == value

        capped, failed, mate = (FIXTURES[key] for key in ("capped", "failed", "mate"))
        upload(capped, watch=True)
        expect_package(capped)
        expect(page.locator("#result-title")).to_have_text("Resource-capped exhibition · no winner")
        expect(page.locator("#feed-count")).to_have_text("RECORDED MOVES")
        expect(page.locator("#exhibition-description")).to_contain_text("Stockfish 19")
        expect(page.locator("#exhibition-description")).to_contain_text("20,000 nodes, 3 candidate lines")
        expect(page.locator("#exhibition-description")).to_contain_text("not independently attested")
        expect(page.locator("#exhibition-identities")).to_contain_text("gpt-6-astra")
        expect(page.locator("#exhibition-identities")).to_contain_text("Resolved identity unreported")
        expect(page.locator("#exhibition-identities")).to_contain_text("claude-fable-5-1 (provider-response)")
        expect(page.locator("#metric-cost")).to_have_text("Unknown")
        expect(page.locator("#start")).to_be_disabled()
        expect(page.locator("#step")).to_be_disabled()
        for selector in ("#export-exhibition", "#export", "#export-package", "#share"):
            assert export(selector) == capped, selector

        # Scrubbing changes the board only. Outcome, complete replay and evidence stay bound.
        page.locator("#replay-position").focus()
        page.keyboard.press("Home")
        expect(page.locator("#replay-position")).to_have_value("0")
        expect(page.locator("#result-title")).to_contain_text("no winner")
        assert export("#share") == capped
        page.locator("#replay-position").focus()
        page.keyboard.press("End")
        expect(page.locator("#replay-position")).to_have_value("2")
        sources()
        page.locator("#exhibition-evidence details > summary").focus()
        page.keyboard.press("Tab")
        expect(page.locator("#export-exhibition")).to_be_focused()
        assert export(keyboard=True) == capped

        # Thin exports cannot remove assistance even if a caller dispatches a disabled control.
        guarded = ("#result-image", "#copy-caption", "#copy-setup", "#go-live", "#watch-broadcast", "#export-proof")
        before_downloads = len(downloads)
        for selector in guarded:
            expect(page.locator(selector)).to_be_disabled()
            page.locator(selector).dispatch_event("click")
        settings()
        page.locator("#share-setup-settings").click()
        expect(page.locator("#notice")).to_contain_text("An exhibition file is not a provider connection")
        assert len(downloads) == before_downloads
        assert page.evaluate("__exhibitionCopies") == []
        assert not external, external

        # Explicit save and a fresh page load retain the full validated envelope.
        library()
        page.locator("#save-current-replay").click()
        page.wait_for_function("digest => Object.keys(localStorage).filter(k => k.startsWith('builderwars.match.v1:')).some(k => JSON.parse(localStorage[k]).exhibition?.digest === digest)", arg=capped["digest"])
        page.reload()
        library()
        expect(page.locator("[data-saved-resume]")).to_have_count(0)
        page.locator("[data-saved-replay]").first.click()
        expect_package(capped)

        # Saved records are structurally listed, then their content hash is checked again on open.
        saved = page.evaluate("""digest => {
          const key = Object.keys(localStorage).find(k => k.startsWith('builderwars.match.v1:') && JSON.parse(localStorage[k]).exhibition?.digest === digest);
          const original = localStorage[key], changed = JSON.parse(original);
          changed.exhibition.digest = '0'.repeat(64);
          localStorage.setItem(key, JSON.stringify(changed));
          return {key, original};
        }""", capped["digest"])
        page.reload()
        library()
        page.locator("[data-saved-replay]").first.click()
        expect(page.locator("#notice")).to_contain_text("digest mismatch")
        expect(page.locator("#exhibition-evidence")).not_to_be_visible()
        expect(page.locator("#metric-moves")).to_have_text("0")
        page.evaluate("saved => localStorage.setItem(saved.key, saved.original)", saved)
        page.reload()
        library()
        page.locator("[data-saved-replay]").first.click()
        expect_package(capped)

        # Bad hashes, rehashed illegal moves and unexpected fields cannot replace current evidence.
        bad_hash = copy.deepcopy(capped)
        bad_hash["digest"] = "0" * 64
        illegal = copy.deepcopy(capped)
        illegal["record"]["events"][0]["move"] = "e2e5"
        extra = copy.deepcopy(capped)
        extra["engine"]["privateKey"] = "PRIVATE_EXHIBITION_SENTINEL"
        for invalid, message in [(bad_hash, "digest mismatch"), (reseal(illegal), "illegal"), (reseal(extra), "Unexpected exhibition fields")]:
            upload(invalid)
            expect(page.locator("#notice")).to_contain_text(message)
            assert export() == capped
        assert "PRIVATE_EXHIBITION_SENTINEL" not in page.locator("body").inner_text()
        assert "PRIVATE_EXHIBITION_SENTINEL" not in page.evaluate("JSON.stringify(localStorage)")

        # A failed route with no accepted moves is still evidence worth saving.
        upload(failed, watch=True)
        expect_package(failed)
        expect(page.locator("#match-result")).to_be_visible()
        expect(page.locator("#result-title")).to_have_text("Failed exhibition · no winner")
        expect(page.locator("#exhibition-description")).to_contain_text("0 accepted moves / 1 attempted calls")
        expect(page.locator("#metric-cost")).to_have_text("Unknown")
        expect(page.locator("#exhibition-identities p")).to_have_count(2)
        assert page.locator("#exhibition-identities").inner_text().count("no accepted decision") == 2
        library()
        page.locator("#save-current-replay").click()
        page.reload()
        library()
        failed_entry = page.locator(".saved-match").filter(has_text="0 plies")
        expect(failed_entry).to_have_count(1)
        expect(failed_entry.locator("[data-saved-resume]")).to_have_count(0)
        failed_entry.locator("[data-saved-replay]").click()
        expect_package(failed)
        expect(page.locator("#result-title")).to_contain_text("no winner")

        # Only a referee-terminal game gets a winner, even while viewing an earlier board.
        upload(mate)
        expect_package(mate)
        expect(page.locator("#result-title")).to_have_text("Synthetic fable wins")
        expect(page.locator("#exhibition-description")).to_contain_text("Completed game")
        page.locator("#replay-position").focus()
        page.keyboard.press("Home")
        expect(page.locator("#result-title")).to_have_text("Synthetic fable wins")
        assert export() == mate

        OUT.mkdir(parents=True, exist_ok=True)
        for width in (320, 390, 768):
            page.set_viewport_size({"width": width, "height": 900})
            sources()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
            expect(page.locator("#export-exhibition")).to_be_visible()
            page.locator("#exhibition-evidence").scroll_into_view_if_needed()
            page.screenshot(path=str(OUT / f"exhibition-{width}.png"), full_page=True)

        # A normal replay import and leaving spectator mode both clear the extra context.
        upload(capped["record"])
        expect(page.locator("#exhibition-evidence")).not_to_be_visible()
        assert export("#export")["schema"] == "builderwars.exhibition.v1"
        assert export("#export-package")["schema"] == "builderwars.match-package.v1"
        expect(page.locator("#result-image")).to_be_enabled()
        upload(capped)
        # applySetup already calls reset; assert the explicit context guard too.
        page.locator("#runback-free").click()
        expect(page.locator("#exhibition-evidence")).not_to_be_visible()
        expect(page.locator("#share")).to_have_text("Share replay ↗")
        expect(page.locator("#seats")).to_contain_text("Tactician")
        page.locator("#start").click()  # Pause the new free game before importing.
        expect(page.locator("#step")).to_be_enabled()
        upload(capped)
        expect(page.locator("#exhibition-evidence")).to_be_visible()
        page.locator("nav [data-tab=watch]").click()
        page.locator("#leave-watch").click()
        expect(page.locator("#exhibition-evidence")).not_to_be_visible()
        expect(page.locator("#metric-moves")).to_have_text("0")
        expect(page.locator("#go-live")).to_be_enabled()
        expect(page.locator("#share")).to_have_text("Share replay ↗")
        assert not errors, errors
        assert not external, external
        assert page.evaluate("__exhibitionCopies") == []
        print(json.dumps({"status": "PASS", "actualProviderCalls": 0, "journeys": [
            "four full-envelope exports", "keyboard scrub and download", "guarded thin exports and broadcasts",
            "save/reload evidence binding", "tamper rejection", "zero-ply failure recovery", "mate versus cap",
            "plain replay and spectator-exit clearing", "320/390/768 evidence layout"]}))
    finally:
        context.close()
        browser.close()
