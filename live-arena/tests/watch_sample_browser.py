"""Watch sample replay onboarding stays provenance-bounded and provider-free."""
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get("BUILDERWARS_TEST_URL", os.environ.get("BASE_URL", "http://127.0.0.1:5178"))
SAMPLE_PATH = "/competition/launch-ttt-v1/matches/launch-ttt-v1-01-0-0.json"

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
    origin = urlsplit(BASE)
    external, requests, errors = [], [], []

    def contain(route):
        target = urlsplit(route.request.url)
        if (target.scheme, target.netloc) == (origin.scheme, origin.netloc):
            requests.append(route.request.url)
            route.continue_()
        else:
            external.append(route.request.url)
            route.abort("blockedbyclient")

    context.route("**/*", contain)
    context.route_web_socket("**/*", lambda socket: socket.close())
    page = context.new_page()
    page.on("pageerror", lambda error: errors.append(str(error)))

    try:
        page.goto(BASE)
        page.locator("nav [data-tab=watch]").click()

        sample = page.locator("#watch-sample")
        expect(sample).to_be_visible()
        expect(sample).to_have_text("Open sample replay · Launch Circuit")
        expect(page.locator("#watch-sample-status")).to_contain_text("retained public match package")
        expect(page.locator("#watch-sample-status")).to_contain_text("not attested")

        # Existing import and live-broadcast entry points remain present and distinct.
        expect(page.locator("#import-exhibition")).to_be_visible()
        expect(page.locator("#import-exhibition")).to_have_text("Import exhibition file")
        expect(page.locator("#watch-broadcast")).to_be_visible()
        expect(page.locator("#watch-broadcast")).to_have_text("Broadcast my match ↗")

        requests.clear()
        sample.click()

        expect(page.locator("#game-title")).to_have_text("Tic-tac-toe")
        expect(page.locator("#metric-moves")).to_have_text("8")
        expect(page.locator("#feed-count")).to_have_text("RECORDED MOVES")
        expect(page.locator("#seats")).to_contain_text("Seeded Wildcard")
        expect(page.locator("#seats")).to_contain_text("Tactician")
        expect(page.locator("#proof-status")).to_contain_text("reverified snapshot")
        expect(page.locator("#proof-status")).to_contain_text("not original engine or model provenance")
        expect(page.locator("#notice")).to_contain_text("No provider or model request was made")
        expect(page.locator("#exhibition-evidence")).not_to_be_visible()
        expect(page.locator("#start")).to_be_disabled()

        sample_requests = [urlsplit(url).path for url in requests if urlsplit(url).path == SAMPLE_PATH]
        assert sample_requests == [SAMPLE_PATH], requests
        assert not external, external

        # Re-export the opened package to prove declarations/resources survive the normal replay path.
        settings = page.locator(".match-settings").filter(has=page.locator("#move-limit"))
        if not settings.evaluate("el => el.open"):
            settings.locator("summary").click()
        with page.expect_download() as pending:
            page.locator("#export-package").click()
        download = pending.value
        assert download.failure() is None
        package = json.loads(Path(download.path()).read_text(encoding="utf-8"))
        assert package["record"]["id"] == "launch-ttt-v1-01-0-0"
        assert package["resources"] == {"moveLimit": 9, "maxTokens": None, "moveLimitKnown": True}
        assert package["declarations"][0]["providerId"] == "bundled-local"
        assert package["declarations"][1]["providerId"] == "bundled-local"
        assert package["verification"]["identityAttested"] is False
        assert package["verification"]["modelAttested"] is False
        assert package["verification"]["resourcesAttested"] is False

        assert not errors, errors
        assert not external, external
        print(json.dumps({
            "status": "PASS",
            "sample": "launch-ttt-v1-01-0-0",
            "acceptedPlies": 8,
            "actualProviderCalls": 0,
            "network": "same-origin retained replay only",
            "provenance": "match declarations/resources retained; identity/model execution unattested",
        }))
    finally:
        context.close()
        browser.close()
