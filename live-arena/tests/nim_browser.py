"""Credential-free browser acceptance for normal-play Nim."""
from playwright.sync_api import sync_playwright
import os

BASE = os.environ.get("BUILDERWARS_TEST_URL", "http://127.0.0.1:5178")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 390, "height": 844})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(BASE)
    page.locator("[data-game=nim]").click()
    page.locator(".nim-heap").first.wait_for()
    assert page.locator(".nim-heap").count() == 3
    assert page.locator(".nim-heap").nth(0).inner_text().startswith("Heap 1 · 3 objects")
    page.locator("#play-human").click()
    page.locator('[data-cell="0"]').click()
    page.wait_for_function("() => document.querySelector('#metric-moves').textContent === '1'")
    assert page.locator(".nim-heap").nth(0).inner_text().startswith("Heap 1 · 2 objects")
    assert not errors, errors
    browser.close()
    print('{"status":"PASS","journey":"nim human move","actualProviderCalls":0}')
