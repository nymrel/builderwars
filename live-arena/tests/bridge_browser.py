"""Deployed HTTPS origin -> authenticated loopback; synthetic backend only."""
import importlib.util,json,os,threading
from pathlib import Path
from playwright.sync_api import sync_playwright
spec=importlib.util.spec_from_file_location('bridge',Path(__file__).parents[1]/'bridge.py')
bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)
BASE=os.environ.get('BUILDERWARS_TEST_URL','https://builderwars.vercel.app')
class SyntheticBackend:
    def complete(self,prompt):return '{"move":"0","comment":"Synthetic local bridge acceptance."}'
server=bridge.BridgeServer(('127.0.0.1',8765),bridge.handler_for(SyntheticBackend(),'synthetic-test-token',BASE,'synthetic/local-test',1))
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
try:
    with sync_playwright() as p:
        browser=p.chromium.launch()
        context=browser.new_context(permissions=['local-network-access'])
        page=context.new_page();page.goto(BASE)
        page.locator('[data-game=tictactoe]').click();page.locator('#connections').click()
        page.locator('#agent-kind').select_option('harness')
        page.locator('#harness-url').fill('http://127.0.0.1:8765/move')
        page.locator('#harness-model').fill('synthetic/local-test')
        page.locator('#agent-key').fill('synthetic-test-token')
        page.locator('#agent-form button[type=submit]').click();page.locator('#step').click()
        page.wait_for_function("() => document.querySelector('#metric-moves').textContent==='1'",timeout=15000)
        assert 'synthetic/local-test' in page.locator('#feed').inner_text()
        print(json.dumps({'status':'PASS','origin':BASE,'browser':browser.version,'localNetworkPermission':'explicit test grant','realLoopbackHTTP':True,'modelBackend':'synthetic','providerCalls':0}))
        browser.close()
finally:
    server.shutdown();server.server_close();thread.join(timeout=5)
