"""Real-browser acceptance. Synthetic remote responses never count as provider proof."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).parents[1]
BASE=os.environ.get('BUILDERWARS_TEST_URL','http://127.0.0.1:5178')

with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page(viewport={"width":1440,"height":1000})
    errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(BASE)
    page.locator('#board .cell').first.wait_for()
    assert page.locator('#board .cell').count()==64
    page.locator('#step').click()
    page.wait_for_function("() => document.querySelector('#metric-moves').textContent==='1'")
    page.locator('#reset').click()
    assert page.locator('#metric-moves').inner_text()=='0'
    for game in ['checkers','connect4','tictactoe']:
        page.locator(f'[data-game={game}]').click()
        page.locator('#step').click()
        page.wait_for_function("() => document.querySelector('#metric-moves').textContent==='1'")
        page.locator('#reset').click()
    # Human game through a win.
    for seat in [0,1]:
        page.locator(f'[data-seat="{seat}"]').click()
        page.locator('#agent-kind').select_option('human')
        page.locator('#agent-name').fill('Human '+str(seat+1))
        page.locator('#agent-form button[type=submit]').click()
    for move in [0,3,1,4,2]:
        page.locator(f'[data-cell="{move}"]').click()
    assert 'wins' in page.locator('#match-status').inner_text()
    # Actual replay export and import into a separate page.
    with page.expect_download() as info:
        page.locator('.match-settings summary').click()
        page.locator('#export').click()
    record=json.loads(Path(info.value.path()).read_text())
    assert len(record['events'])==5
    assert all('key' not in a and 'endpoint' not in a for a in record['agents'])
    page.locator('#import').set_input_files({"name":"match.json","mimeType":"application/json","buffer":json.dumps(record).encode()})
    assert page.locator('#start').is_disabled()
    page.locator('#replay-prev').click()
    assert page.locator('#ply').inner_text()=='PLY 04'
    page.locator('#replay-position').fill('0')
    assert page.locator('#ply').inner_text()=='PLY 00'
    page.locator('#replay-next').click()
    assert page.locator('#ply').inner_text()=='PLY 01'
    page.locator('nav [data-tab=watch]').click()
    page.locator('#leave-watch').click()
    # Creator game executes real custom rules.
    page.locator('nav [data-tab=forge]').click()
    page.locator('#creator-name').fill('Browser Test Five')
    page.locator('#creator button[type=submit]').click()
    assert page.locator('#game-title').inner_text()=='Browser Test Five'
    assert page.locator('#board .cell').count()==64
    # Choose built-ins for paired evaluation, small deterministic cap.
    for seat in [0,1]:
        page.locator(f'[data-seat="{seat}"]').click()
        page.locator('#agent-kind').select_option('bot')
        page.locator('#bot-model').select_option('random')
        page.locator('#agent-name').fill('Bot '+str(seat+1))
        page.locator('#agent-form button[type=submit]').click()
    page.locator('[data-game=tictactoe]').click()
    page.locator('#pace').select_option('100')
    page.locator('nav [data-tab=evals]').click()
    page.locator('#run-series').click()
    page.wait_for_function("() => document.querySelector('#series-results').textContent.includes('2 / 2')",timeout=20000)
    # A capped series must still complete both swapped games.
    page.locator('#move-limit').fill('2')
    page.locator('nav [data-tab=evals]').click()
    page.locator('#run-series').click()
    page.wait_for_function("() => document.querySelector('#series-results').textContent.includes('2 / 2')",timeout=20000)
    assert page.locator('#series-results').inner_text().count('Move limit')==2
    page.locator('#move-limit').fill('80')
    # Connection UI with synthetic provider catalog; no real key or inference.
    page.route('https://openrouter.ai/api/v1/models',lambda route:route.fulfill(json={"data":[{"id":"test/model","name":"Test Model","pricing":{"prompt":"0","completion":"0"},"reasoning":{"supported_efforts":["high","low"]}}]}))
    page.locator('#connections').click()
    page.locator('#agent-kind').select_option('openrouter')
    page.wait_for_function("() => document.querySelector('#model-id').options.length===1")
    assert page.locator('#effort option').all_text_contents()==['Provider default','high','low']
    page.locator('#agent-key').fill('synthetic-browser-test')
    page.locator('#agent-name').fill('Test model')
    page.locator('#agent-form button[type=submit]').click()
    page.route('https://openrouter.ai/api/v1/chat/completions',lambda route:route.fulfill(json={"choices":[{"message":{"content":"{\"move\":\"0\",\"comment\":\"Synthetic response\"}"}}],"model":"test/model","usage":{"total_tokens":5,"cost":0}}))
    page.locator('#step').click()
    page.wait_for_function("() => document.querySelector('#metric-moves').textContent==='1'")
    assert 'Synthetic response' in page.locator('#feed').inner_text()
    assert 'synthetic-browser-test' not in page.locator('body').inner_text()
    assert page.evaluate('JSON.stringify(localStorage)')=='{}'
    page.locator('#reset').click()
    page.route('https://openrouter.ai/api/v1/chat/completions',lambda route:route.fulfill(json={"choices":[{"message":{"content":"{\"move\":\"invalid\"}"}}],"model":"test/model"}))
    page.locator('#step').click()
    page.wait_for_function("() => document.querySelector('#notice').textContent.includes('Illegal')")
    assert page.locator('#metric-moves').inner_text()=='0'
    # Credentials never follow a change of connection type or endpoint.
    page.locator('#connections').click()
    assert page.locator('#agent-key').input_value()=='synthetic-browser-test'
    page.locator('#agent-kind').select_option('harness')
    assert page.locator('#agent-key').input_value()==''
    page.locator('#agent-key').fill('synthetic-harness-token')
    page.locator('#harness-url').fill('https://example.com/move')
    assert page.locator('#agent-key').input_value()==''
    page.locator('#close-dialog').click()
    # Every main destination at the smallest supported widths.
    for width in [320,390,768,1440]:
        page.set_viewport_size({"width":width,"height":900})
        for tab in ['arena','forge','evals','watch','academy']:
            page.locator(f'nav [data-tab={tab}]').click()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (
                f'overflow {width} {tab}: ' + json.dumps(page.evaluate("""() => [...document.querySelectorAll('body *')]
                .filter(e => e.getBoundingClientRect().width && e.getBoundingClientRect().right > innerWidth + 1)
                .map(e => ({tag:e.tagName, id:e.id, cls:e.className, width:e.getBoundingClientRect().width,
                           right:e.getBoundingClientRect().right, text:e.textContent.slice(0,80)})).slice(0,20)""")))
    page.locator('nav [data-tab=arena]').click()
    page.set_viewport_size({"width":1440,"height":1000})
    page.locator('[data-game=chess]').click()
    (ROOT/'test-results').mkdir(exist_ok=True)
    page.screenshot(path=str(ROOT/'test-results/desktop.png'),full_page=True)
    page.set_viewport_size({"width":390,"height":844})
    page.screenshot(path=str(ROOT/'test-results/mobile.png'),full_page=True)
    assert not errors,errors
    browser.close()
    print(json.dumps({"status":"PASS","journeys":["four games","human win","replay export/import","creator game","paired series","model picker","synthetic model move","invalid move rejection","secret non-persistence","responsive destinations"],"viewports":[320,390,768,1440],"actualProviderCalls":0}))
