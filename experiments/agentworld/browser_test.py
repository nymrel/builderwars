"""Dependency: Python Playwright + Chromium. Loopback-only prototype acceptance."""
from pathlib import Path
import functools, http.server, threading, json, sys
from playwright.sync_api import sync_playwright
MEMORY = '--memory' in sys.argv
ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'evidence'
OUT.mkdir(exist_ok=True)
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_): pass
server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(ROOT)))
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
url = f'http://127.0.0.1:{server.server_port}/'
def load(page):
    if MEMORY: page.set_content((ROOT/'BuilderWars-Agentworld-Preview.html').read_text())
    else: page.goto(url)
checks = []
def check(name, passed):
    assert passed, name
    checks.append(name)
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        context = browser.new_context(viewport={'width':1280,'height':1000}, accept_downloads=True)
        page = context.new_page()
        errors, external = [], []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('request', lambda r: external.append(r.url) if not r.url.startswith(url) and not r.url.startswith('blob:') else None)
        load(page)
        check('Initial world renders 64 cells and four actors', page.locator('.cell').count()==64 and page.locator('#agents .agent').count()==4)
        check('Synthetic and local-only boundary visible', 'not live AI' in page.locator('.notice').inner_text())
        for width in [320,390,768,1280]:
            page.set_viewport_size({'width':width,'height':1000})
            check(f'No horizontal overflow at {width}px', page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
        page.set_viewport_size({'width':1280,'height':1000})
        page.locator('#batch').click()
        check('Scripted batch accepts exactly 16 turns', page.locator('#turn').inner_text()=='16 / 240')
        if MEMORY:
            check('Unavailable storage disables autosave without blocking the world', not page.locator('#autosave').is_checked())
        else:
            page.reload()
            check('Local checkpoint restored after replay verification', page.locator('#turn').inner_text()=='16 / 240' and page.locator('#proof').text_content()=='Local replay pass')
        page.locator('#verify').click()
        check('Explicit replay verification passes', page.locator('#proof').text_content()=='Local replay pass')
        with page.expect_download() as info: page.locator('#export').click()
        packet=json.loads(Path(info.value.path()).read_text())
        check('Export contains exact rules-bound state and action count', len(packet['actions'])==16 and packet['finalState']['turn']==16 and packet['finalState']['rules'].startswith('builderwars.agentworld'))
        Path(OUT/'example-replay.json').write_text(json.dumps(packet,indent=2)+'\n')
        bad=json.loads(json.dumps(packet)); bad['finalState']['scores']['amber']+=1
        page.locator('#import').set_input_files({'name':'bad.json','mimeType':'application/json','buffer':json.dumps(bad).encode()})
        page.wait_for_function("document.querySelector('#message').textContent.includes('Import refused')")
        check('Tampered import refused without state change', page.locator('#turn').inner_text()=='16 / 240')
        page.locator('#import').set_input_files({'name':'duplicate.json','mimeType':'application/json','buffer':b'{"seed":1,"seed":2}'})
        page.wait_for_function("document.querySelector('#message').textContent.includes('Duplicate JSON key')")
        check('Duplicate-key replay refused', page.locator('#turn').inner_text()=='16 / 240')
        page.locator('summary').filter(has_text='Agent interface').click()
        page.locator('#sample-action').click()
        action=json.loads(page.locator('#action-json').input_value())
        action['provider']='fictional'
        page.locator('#action-json').fill(json.dumps(action))
        page.locator('#apply-action').click()
        check('Unknown action fields refused without mutation', page.locator('#turn').inner_text()=='16 / 240' and 'Unexpected' in page.locator('#message').inner_text())
        page.locator('#sample-action').click()
        page.locator('#action-json').fill(page.locator('#action-json').input_value())
        before=page.locator('#action-json').input_value()
        page.locator('#step').click()
        check('World updates preserve in-progress action edits', page.locator('#action-json').input_value()==before)
        page.locator('#apply-action').click()
        check('Stale action rejected', 'Stale' in page.locator('#message').inner_text() and page.locator('#turn').inner_text()=='17 / 240')
        page.locator('#sample-action').click(); page.locator('#apply-action').click()
        check('Manual JSON action accepted and disclosed in journal', page.locator('#turn').inner_text()=='18 / 240' and page.locator('#log .source').first.inner_text()=='manual')
        page.locator('summary').filter(has_text='Agent interface').click()
        page.locator('#play').click(); page.wait_for_timeout(550); page.locator('#play').click()
        paused=page.locator('#turn').inner_text(); page.wait_for_timeout(450)
        check('Pause stops automatic advancement', page.locator('#turn').inner_text()==paused)
        if not MEMORY:
            second=context.new_page(); second.goto(url); second.locator('#step').click()
            page.wait_for_function("document.querySelector('#message').textContent.includes('Cross-tab')")
            check('Other-tab writes pause local saving', not page.locator('#autosave').is_checked())
            saved=page.evaluate("localStorage.getItem('builderwars.agentworld.experimental.v1')")
            page.locator('#step').click()
            check('Conflicted tab does not overwrite saved checkpoint', page.evaluate("localStorage.getItem('builderwars.agentworld.experimental.v1')")==saved)
            second.close(); page.reload()
            check('Reload safely adopts latest saved checkpoint', int(page.locator('#turn').inner_text().split(' / ')[0])==json.loads(saved)['finalState']['turn'])
        page.on('dialog', lambda d: d.accept())
        page.locator('#import').set_input_files({'name':'valid.json','mimeType':'application/json','buffer':json.dumps(packet).encode()})
        page.wait_for_function("document.querySelector('#message').textContent.includes('Imported after')")
        check('Valid import verifies before adoption', page.locator('#turn').inner_text()=='16 / 240')
        for _ in range(5): page.locator('#batch').click()
        page.locator('#verify').click()
        page.screenshot(path=str(OUT/'desktop.png'),full_page=True)
        page.set_viewport_size({'width':390,'height':844})
        page.screenshot(path=str(OUT/'mobile.png'),full_page=True)
        check('No browser JavaScript errors', not errors)
        check('No external network requests', not external)
        if not MEMORY:
            page.locator('#clear').click()
            check('Erasure removes stored data and disables autosave', page.evaluate("localStorage.getItem('builderwars.agentworld.experimental.v1')") is None and not page.locator('#autosave').is_checked())
        nojs=browser.new_context(java_script_enabled=False)
        textpage=nojs.new_page(); load(textpage)
        check('Non-JavaScript rules remain readable', textpage.locator('noscript').is_visible() and '240 accepted turns' in textpage.locator('noscript').inner_text())
        nojs.close(); context.close(); browser.close()
finally:
    server.shutdown(); server.server_close(); thread.join(timeout=3)
report={'scope':('In-memory Chromium DOM validation; origin navigation, real storage persistence, cross-tab integration and deployed behavior NOT VERIFIED.' if MEMORY else 'Loopback Chromium validation; not deployment, provider, identity or independent review evidence.'),'browser_executable':'/usr/bin/chromium', 'navigation_blocker':'ERR_BLOCKED_BY_ADMINISTRATOR for loopback and file navigation; no browser policy was changed.' if MEMORY else None,'checks_passed':len(checks),'checks':checks}
(OUT/'browser-results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
