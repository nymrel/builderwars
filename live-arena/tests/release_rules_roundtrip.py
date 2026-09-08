"""Release evidence for a successful Forge rules export -> clean-browser import roundtrip."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get("BUILDERWARS_TEST_URL", "http://127.0.0.1:5178")

with sync_playwright() as p:
    browser = p.chromium.launch()
    maker_context = browser.new_context(viewport={"width": 390, "height": 844})
    maker = maker_context.new_page()
    errors = []
    maker.on("pageerror", lambda error: errors.append(str(error)))
    maker.goto(BASE)
    maker.locator("nav [data-tab=forge]").click()
    maker.locator("#creator-name").fill("Release Evidence Four")
    maker.locator("#creator-rows").fill("6")
    maker.locator("#creator-cols").fill("7")
    maker.locator("#creator-connect").fill("4")
    maker.locator("#creator-gravity").check()

    with maker.expect_download() as download:
        maker.locator("#export-rules").click()
    exported = Path(download.value.path()).read_bytes()
    rules = json.loads(exported)
    assert rules == {
        "kind": "custom",
        "name": "Release Evidence Four",
        "rows": 6,
        "cols": 7,
        "connect": 4,
        "gravity": True,
    }

    # Import into a clean context so the receiving page inherits no creator state.
    receiver_context = browser.new_context(viewport={"width": 320, "height": 780})
    receiver = receiver_context.new_page()
    receiver.on("pageerror", lambda error: errors.append(str(error)))
    receiver.goto(BASE)
    receiver.locator("nav [data-tab=forge]").click()
    receiver.locator("#import-rules").set_input_files({
        "name": "builderwars-game.json",
        "mimeType": "application/json",
        "buffer": exported,
    })
    expect(receiver.locator("#game-title")).to_have_text("Release Evidence Four")
    expect(receiver.locator("#board .cell")).to_have_count(42)
    assert receiver.locator("#arena").is_visible()
    assert receiver.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")

    # The imported rules must be executable, not merely parsed/displayed.
    receiver.locator("#step").click()
    expect(receiver.locator("#metric-moves")).to_have_text("1")
    assert not errors, errors
    browser.close()

print("PASS: Forge rules export -> clean-browser import -> executable custom game roundtrip.")
