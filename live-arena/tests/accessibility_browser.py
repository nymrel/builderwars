"""Keyboard-only setup and board play, focus continuity, and a touch finish."""
import os
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get("BUILDERWARS_TEST_URL", "http://127.0.0.1:5178")
with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True, reduced_motion="reduce")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(BASE)
    def tab_to(selector):
        target = page.locator(selector)
        for _ in range(160):
            if target.evaluate("el => el === document.activeElement"):
                return
            page.keyboard.press("Tab")
        raise AssertionError(f"Keyboard could not reach {selector}")
    def activate(selector):
        tab_to(selector)
        page.keyboard.press("Enter")
    activate("[data-game=tictactoe]")
    for seat in (0, 1):
        activate(f'[data-seat="{seat}"]')
        tab_to("#agent-kind")
        page.keyboard.press("ArrowDown")  # Built-in -> human; no programmatic selection.
        expect(page.locator("#agent-kind")).to_have_value("human")
        activate("#agent-form button[type=submit]")
    activate('[data-cell="0"]')
    expect(page.locator("#metric-moves")).to_have_text("1")
    assert page.locator('[data-cell="0"]').evaluate("el => el === document.activeElement"), "Board rerender lost keyboard focus"
    assert page.locator('[data-cell="0"]').evaluate("el => getComputedStyle(el).outlineStyle !== 'none'")
    page.keyboard.press("ArrowDown")
    expect(page.locator('[data-cell="3"]')).to_be_focused()
    page.keyboard.press("Enter")
    page.keyboard.press("ArrowUp")
    page.keyboard.press("ArrowRight")
    expect(page.locator('[data-cell="1"]')).to_be_focused()
    page.keyboard.press("Enter")
    page.keyboard.press("ArrowDown")
    expect(page.locator('[data-cell="4"]')).to_be_focused()
    page.keyboard.press("Enter")
    expect(page.locator("#metric-moves")).to_have_text("4")
    page.keyboard.press("Home")
    expect(page.locator('[data-cell="3"]')).to_be_focused()
    page.keyboard.press("End")
    expect(page.locator('[data-cell="5"]')).to_be_focused()
    assert page.locator('#board [tabindex="0"]').count() == 1
    page.locator('[data-cell="2"]').tap()
    expect(page.locator("#match-status")).to_contain_text("wins")
    assert page.locator("#agent-dialog").get_attribute("aria-labelledby") == "agent-title"
    assert page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
    assert page.locator("#board button").evaluate_all("buttons => buttons.every(b => b.getAttribute('aria-label') && b.getBoundingClientRect().width >= 44 && b.getBoundingClientRect().height >= 44)")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert not errors
    # Human-versus-bot rendering must preserve focus while input is temporarily unavailable.
    page = context.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(BASE)
    activate("[data-game=tictactoe]")
    activate('[data-seat="0"]')
    tab_to("#agent-kind")
    page.keyboard.press("ArrowDown")
    activate("#agent-form button[type=submit]")
    activate("#start")
    activate('[data-cell="0"]')
    expect(page.locator("#metric-moves")).to_have_text("2")
    expect(page.locator('[data-cell="0"]')).to_be_focused()
    expect(page.locator('[data-cell="0"]')).to_have_attribute("aria-disabled", "false")
    activate("#start")  # Pause before checking flipped visual navigation.
    activate("#flip")
    tab_to('[data-cell="0"]')
    page.keyboard.press("ArrowUp")
    expect(page.locator('[data-cell="3"]')).to_be_focused()
    page.keyboard.press("ArrowLeft")
    expect(page.locator('[data-cell="4"]')).to_be_focused()
    assert not errors
    context.close()
    browser.close()
print("PASS: keyboard-only configuration, roving board focus, arrow/Home/End controls, touch win, reduced-motion preference")
