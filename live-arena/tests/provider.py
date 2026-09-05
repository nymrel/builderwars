"""Explicit opt-in: exactly one browser-direct call to a catalog-priced-free route."""
import argparse,json,os,urllib.request
from playwright.sync_api import sync_playwright
parser=argparse.ArgumentParser()
parser.add_argument('--allow-one-free-call',action='store_true',required=True)
parser.add_argument('--model',required=True)
args=parser.parse_args()
models=json.load(urllib.request.urlopen('https://openrouter.ai/api/v1/models'))['data']
model=next(m for m in models if m['id']==args.model)
assert model['pricing']['prompt']=='0' and model['pricing']['completion']=='0','Only explicitly free routes'
key=os.environ['OPENROUTER_API_KEY']
base=os.environ.get('BUILDERWARS_TEST_URL','http://127.0.0.1:5178')
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page()
    calls=[]
    page.on('request',lambda req:calls.append(1) if req.url=='https://openrouter.ai/api/v1/chat/completions' else None)
    page.goto(base);page.locator('[data-game=tictactoe]').click()
    page.locator('#connections').click();page.locator('#agent-kind').select_option('openrouter')
    page.wait_for_function('() => document.querySelector("#model-id").options.length > 1',timeout=20000)
    page.locator('#model-id').select_option(args.model)
    page.locator('#agent-key').fill(key);page.locator('#agent-name').fill('Live free-route test')
    page.locator('#agent-form button[type=submit]').click()
    page.locator('.match-settings summary').filter(has_text='Match settings').click();page.locator('#max-tokens').fill('512')
    page.locator('#step').click()
    page.wait_for_function("() => document.querySelector('#metric-moves').textContent==='1' || /returned|Illegal|timed out|Failed|exceeds/.test(document.querySelector('#notice').textContent)",timeout=125000)
    assert len(calls)==1
    result={'surface':base,'requests':len(calls),'requestedModel':args.model,'catalogInputOutputPrice':0,'moves':page.locator('#metric-moves').inner_text(),'tokens':page.locator('#metric-tokens').inner_text(),'reportedCost':page.locator('#metric-cost').inner_text(),'status':page.locator('#notice').inner_text()}
    if result['moves']=='1':result['providerEvidence']=page.locator('#feed').inner_text()
    browser.close()
    print(json.dumps(result))
    assert result['moves']=='1','Provider did not produce a valid move; see sanitized result'
