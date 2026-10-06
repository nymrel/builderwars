"""Competition discovery and actual device results; no provider inference or fixture standings."""
import os
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get("BUILDERWARS_TEST_URL", "http://127.0.0.1:5178")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(BASE)
    page.locator("#board .cell").first.wait_for()
    page.locator("#connect-first").click()
    expect(page.locator("#agent-dialog")).to_be_visible()
    page.locator("#close-dialog").click()

    page.locator('nav [data-tab="compete"]').click()
    expect(page.locator('nav [data-tab="compete"]')).to_have_attribute("aria-current", "page")
    page.locator('#compete [data-hub-tab="duel"]').click()
    expect(page.locator("#duel")).to_be_visible()
    page.locator('nav [data-tab="compete"]').click()
    page.locator('#compete [data-hub-tab="evals"]').click()
    expect(page.locator("#series-length")).to_be_visible()
    page.locator('nav [data-tab="compete"]').click()
    page.locator('#compete [data-hub-tab="forge"]').click()
    expect(page.locator("#creator-name")).to_be_visible()

    page.locator('nav [data-tab="results"]').click()
    expect(page.locator("#results-total")).to_have_text("0")
    expect(page.locator("#results-complete")).to_have_text("0")
    expect(page.locator("#results-moves")).to_have_text("0")
    page.locator("#results-go-arena").click()
    expect(page.locator("#arena")).to_be_visible()

    # Complete an actual legal game. The first contender's literal markup must remain text.
    page.locator('[data-game="tictactoe"]').click()
    for seat, name in [(0, "Builder <b>one</b>"), (1, "Builder two")]:
        page.locator(f'[data-seat="{seat}"]').click()
        page.locator("#agent-kind").select_option("human")
        page.locator("#agent-name").fill(name)
        page.locator('#agent-form button[type="submit"]').click()
    for move in [0, 3, 1, 4, 2]:
        page.locator(f'[data-cell="{move}"]').click()
    expect(page.locator("#match-status")).to_contain_text("wins")
    page.locator('nav [data-tab="results"]').click()
    expect(page.locator("#results-total")).to_have_text("1")
    expect(page.locator("#results-complete")).to_have_text("1")
    expect(page.locator("#results-moves")).to_have_text("5")
    expect(page.locator("#results-list")).to_contain_text("Builder <b>one</b> wins")
    assert page.locator("#results-list b").count() == 0
    page.locator("#results-filter").select_option("replay")
    expect(page.locator("#results-list")).to_contain_text("No matches in this view yet.")
    expect(page.locator("#results-total")).to_have_text("1")
    page.locator("#results-filter").select_option("complete")
    page.locator("[data-result-key]").click()
    expect(page.locator("#arena")).to_be_visible()
    expect(page.locator("#start")).to_be_disabled()
    expect(page.locator("#metric-moves")).to_have_text("5")

    # Counts are durable device records, not an animated or synthetic population.
    page.reload()
    page.locator('nav [data-tab="results"]').click()
    expect(page.locator("#results-total")).to_have_text("1")
    expect(page.locator("#results-complete")).to_have_text("1")
    page.locator('nav [data-tab="arena"]').click()
    page.locator('[data-game="connect4"]').click()
    page.locator('#step').click()
    expect(page.locator("#metric-moves")).to_have_text("1")
    page.locator('nav [data-tab="results"]').click()
    expect(page.locator("#results-total")).to_have_text("2")
    expect(page.locator("#results-complete")).to_have_text("1")
    expect(page.locator("#results-moves")).to_have_text("6")
    page.locator("#results-filter").select_option("complete")
    page.once("dialog", lambda dialog: dialog.dismiss())
    page.locator("[data-result-key]").click()
    expect(page.locator("#results")).to_be_visible()
    page.locator('nav [data-tab="arena"]').click()
    expect(page.locator("#game-title")).to_have_text("Connect Four")
    expect(page.locator("#metric-moves")).to_have_text("1")

    for width in [320, 390, 768]:
        page.set_viewport_size({"width": width, "height": 844})
        for tab in ["arena", "compete", "results"]:
            page.locator(f'nav [data-tab="{tab}"]').click()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (width, tab)
            expect(page.locator(f'nav [data-tab="{tab}"]')).to_have_attribute("aria-current", "page")
    assert not errors, errors
    browser.close()

print("PASS: competition entry paths, real replay-derived results, filtering, literal contender names, persistence, unfinished-match consent and responsive navigation")
