"""Real PeerJS signaling + two independent Chromium contexts; no model API calls."""
import json,os
from playwright.sync_api import sync_playwright
BASE=os.environ.get('BUILDERWARS_TEST_URL','http://127.0.0.1:5178')
with sync_playwright() as p:
    browser=p.chromium.launch()
    host=browser.new_context(permissions=['clipboard-read','clipboard-write'])
    viewer=browser.new_context()
    h=host.new_page();v=viewer.new_page()
    h.goto(BASE);h.locator('[data-game=tictactoe]').click()
    h.locator('#go-live').click()
    h.wait_for_function("() => document.querySelector('#watch-link').textContent.includes('#watch=')",timeout=30000)
    link=h.locator('#watch-link').text_content()
    v.goto(link)
    v.wait_for_function("() => document.querySelector('#notice').textContent.includes('Watching live ·')",timeout=30000)
    assert v.locator('#board .cell').count()==9
    h.locator('#step').click()
    v.wait_for_function("() => document.querySelector('#metric-moves').textContent==='1'",timeout=15000)
    assert v.locator('#start').is_disabled()
    h.locator('nav [data-tab=watch]').click();h.locator('#stop-broadcast').click()
    v.wait_for_function("() => document.querySelector('#notice').textContent.includes('Host disconnected')",timeout=15000)
    browser.close()
    print(json.dumps({'status':'PASS','surface':BASE,'realPeerSignaling':True,'independentBrowserContexts':2,'movesReceived':1,'disconnectVerified':True}))
