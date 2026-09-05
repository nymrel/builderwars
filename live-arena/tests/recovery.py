"""Real-browser device-library and offline spectator recovery acceptance."""
import json
import os
from playwright.sync_api import sync_playwright

BASE = os.environ.get("BUILDERWARS_TEST_URL", "http://127.0.0.1:5178")
with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(BASE)
    assert '30 days' in page.locator('#match-library').text_content()
    assert 'keys and endpoints are never saved' in page.locator('#match-library').text_content()
    page.locator('[data-game="tictactoe"]').click()
    page.locator('#step').click()
    page.wait_for_function("() => document.querySelector('#metric-moves').textContent === '1'")
    page.locator('#step').click()
    page.wait_for_function("() => document.querySelector('#metric-moves').textContent === '2'")
    page.locator('.match-settings').filter(has=page.locator('#move-limit')).locator('summary').click()
    page.locator('#move-limit').fill('6')
    # Force a paused checkpoint with the selected cap.
    page.locator('#start').click()
    page.locator('#start').click()
    page.reload()
    assert page.locator('#metric-moves').inner_text() == '0'  # Never auto-execute.
    page.locator('#match-library summary').click()
    assert page.locator('[data-saved-resume]').count() == 1
    page.locator('[data-saved-resume]').click()
    recovered = int(page.locator('#metric-moves').inner_text())
    assert recovered >= 2
    assert 'Recovered' in page.locator('#notice').inner_text()
    assert page.locator('#move-limit').input_value() == '6'
    assert page.locator('#start').inner_text() == '▶ Start match'
    page.locator('#step').click()
    page.wait_for_function(f"() => Number(document.querySelector('#metric-moves').textContent) === {recovered + 1}")
    page.wait_for_function(f"() => document.querySelector('.saved-match')?.textContent.includes('{recovered + 1} plies')")
    page.locator('[data-saved-replay]').first.click()
    assert page.locator('#start').is_disabled()
    page.locator('#replay-prev').click()
    assert page.locator('#ply').inner_text() == f'PLY {recovered:02}'
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    # Corrupt storage must not brick a page or erase a valid record.
    page.evaluate("localStorage.setItem('builderwars.match.v1:broken', 'bad JSON')")
    page.reload()
    page.locator('#match-library summary').click()
    assert page.locator('[data-saved-replay]').count() >= 1
    page.evaluate("localStorage.setItem('other-product', 'keep')")
    page.on('dialog', lambda dialog: dialog.accept())
    page.locator('#forget-matches').click()
    assert page.locator('[data-saved-replay]').count() == 0
    assert not page.locator('#save-matches').is_checked()
    page.locator('#step').click()
    assert page.evaluate("Object.keys(localStorage).filter(k => k.startsWith('builderwars.match.v1:')).length") == 0
    assert page.evaluate("localStorage.getItem('other-product')") == 'keep'
    # Storage-denied browsers retain gameplay and disclose that there is no save.
    blocked = browser.new_context()
    blocked.add_init_script("Object.defineProperty(window, 'localStorage', {get() {throw Error('Storage denied')}})")
    denied = blocked.new_page(); denied.goto(BASE)
    denied.locator('#step').click()
    denied.wait_for_function("() => document.querySelector('#metric-moves').textContent === '1'")
    assert 'unavailable' in denied.locator('#library-status').text_content(), denied.locator('#library-status').text_content()
    blocked.close()

    # Real WebRTC: receive, reload/rejoin, close host, reload cached spectator.
    host_context = browser.new_context(permissions=['clipboard-read', 'clipboard-write'])
    host = host_context.new_page(); host.goto(BASE)
    host.locator('[data-game="tictactoe"]').click()
    host.locator('#step').click()
    host.wait_for_function("() => document.querySelector('#metric-moves').textContent === '1'")
    host.locator('#go-live').click()
    host.wait_for_function("() => document.querySelector('#watch-link').textContent.includes('#watch=')", timeout=35000)
    link = host.locator('#watch-link').inner_text()
    viewer_context = browser.new_context()
    viewer = viewer_context.new_page(); viewer.goto(link)
    viewer.wait_for_function("() => document.querySelector('#metric-moves').textContent === '1'", timeout=35000)
    viewer.reload()
    viewer.wait_for_function("() => document.querySelector('#notice').textContent.includes('Watching live')", timeout=35000)
    host.locator('#step').click()
    viewer.wait_for_function("() => document.querySelector('#metric-moves').textContent === '2'", timeout=35000)
    host_context.close()
    viewer.wait_for_function("() => document.querySelector('#notice').textContent.includes('not a live board')", timeout=35000)
    viewer.reload()
    viewer.wait_for_function("() => document.querySelector('#metric-moves').textContent === '2'")
    viewer.wait_for_function("() => document.querySelector('#notice').textContent.includes('not a live board')", timeout=35000)
    assert viewer.locator('#replay-position').is_visible()
    viewer.locator('#replay-prev').click()
    assert viewer.locator('#ply').inner_text() == 'PLY 01'
    viewer.locator('nav [data-tab="watch"]').click()
    assert viewer.locator('#rejoin-watch').is_visible()
    viewer.locator('#leave-watch').click()
    assert viewer.locator('#start').is_enabled()
    assert '#watch=' not in viewer.url
    # Leave must not overwrite the saved snapshot's host association.
    saved_watch = viewer.evaluate("Object.entries(localStorage).filter(([key]) => key.startsWith('builderwars.match.v1:watch:')).map(([,value]) => JSON.parse(value))")
    assert any(item['watchId'] in link and len(item['record']['events']) == 2 for item in saved_watch), [(item['watchId'], len(item['record']['events'])) for item in saved_watch]
    viewer.goto(link)
    viewer.wait_for_function("() => document.querySelector('#metric-moves').textContent === '2'")
    assert 'Saved spectator position' in viewer.locator('#notice').text_content() or 'not a live board' in viewer.locator('#notice').text_content()
    assert not errors, errors
    browser.close()
    print(json.dumps({"device_reload_resume": "pass", "retained_move_cap": "pass", "deletion_opt_out": "pass", "storage_denied": "pass", "spectator_reload_rejoin_offline_cache": "pass", "mobile_no_overflow": "pass"}))
