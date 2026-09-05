"""Deterministic delayed-provider races; synthetic data, no inference."""
import json,os
from playwright.sync_api import sync_playwright
BASE=os.environ.get('BUILDERWARS_TEST_URL','http://127.0.0.1:5178')
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page()
    page.route('https://openrouter.ai/api/v1/key',lambda r:r.fulfill(json={'data':{'is_free_tier':True}}))
    page.route('https://openrouter.ai/api/v1/models',lambda r:r.fulfill(json={'data':[{'id':'test/model','name':'Test'}]}))
    page.goto(BASE);page.locator('[data-game=tictactoe]').click()
    page.locator('#connections').click();page.locator('#agent-kind').select_option('openrouter')
    page.locator('#model-id option[value="test/model"]').wait_for(state='attached')
    page.locator('#model-id').select_option('test/model')
    page.locator('#agent-key').fill('synthetic');page.locator('#agent-form button[type=submit]').click()
    page.evaluate('''() => { window.testCalls=0; const original=window.fetch; window.fetch=(url,opts)=>String(url).includes('/chat/completions') ? (window.testCalls++,new Promise(resolve=>window.resolveMove=()=>resolve(new Response(JSON.stringify({model:'test/model',choices:[{message:{content:'{"move":"0"}'}}]}),{headers:{'Content-Type':'application/json'}})))) : original(url,opts); }''')
    page.locator('#step').click()
    page.wait_for_function('() => window.testCalls===1')
    page.evaluate("document.querySelector('#step').dispatchEvent(new Event('click'));document.querySelector('#start').dispatchEvent(new Event('click'))")
    assert page.evaluate('window.testCalls')==1
    assert page.locator('#step').is_disabled()
    # Reset invalidates the provider result even if fetch ignores cancellation.
    page.locator('#reset').click();page.evaluate('window.resolveMove()')
    page.wait_for_timeout(150)
    assert page.locator('#metric-moves').inner_text()=='0'
    # A new step can succeed normally.
    page.locator('#step').click();page.wait_for_function('() => window.testCalls===2');page.evaluate('window.resolveMove()')
    page.wait_for_function("() => document.querySelector('#metric-moves').textContent==='1'")
    assert page.evaluate('window.testCalls')==2
    assert not page.locator('#step').is_disabled()
    browser.close()
    print(json.dumps({'status':'PASS','overlappingRequestsPrevented':True,'lateCancelledMoveDiscarded':True,'newRequestAfterReset':True,'actualProviderCalls':0}))
