"""Supplemental PR #66 acceptance. Default: real loopback origin, never fixture fallback.

--controller-fixture explicitly tests exact engine/app JS on a minimal in-memory DOM.
That mode does NOT test index.html, CSP, persistence, cross-tab events, or deployment.
Requires Python Playwright and an already-authorized browser. No browser policies
are modified. Each run writes a fresh receipt even when blocked or failing.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import functools
import hashlib
import http.server
import importlib.metadata
import json
from pathlib import Path
import re
import sys
import threading
import traceback
from playwright.sync_api import sync_playwright

KEY = 'builderwars.agentworld.experimental.v1'

def arguments():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    p.add_argument('--output', type=Path, required=True,
                   help='New directory: refuses to overwrite any earlier evidence.')
    p.add_argument('--controller-fixture', action='store_true')
    p.add_argument('--browser', choices=['chromium', 'firefox', 'webkit'], default='chromium')
    p.add_argument('--executable', help='Optional already-installed, authorized browser path.')
    return p.parse_args()

def main():
    args = arguments()
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'schema': 'builderwars.agentworld.supplemental-review.v1',
              'started_at': datetime.now(timezone.utc).isoformat(),
              'scope': ('controller-only in-memory fixture; NOT index/CSP/origin/storage/cross-tab acceptance'
                        if args.controller_fixture else 'loopback supplemental browser acceptance; NOT deployed/lab-integrated/independently approved'),
              'browser': args.browser, 'executable': args.executable,
              'playwright': importlib.metadata.version('playwright'),
              'harness_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'source_files': {}, 'checks': [], 'page_errors': [], 'external_requests': [],
              'status': 'NOT_RUN', 'policy_changes': False}
    server = thread = browser = None
    failures = 0
    names = []
    try:
        for name in ['engine.js', 'app.js'] + ([] if args.controller_fixture else ['index.html']):
            raw = (args.root / name).read_bytes()
            report['source_files'][name] = {'sha256': hashlib.sha256(raw).hexdigest(),
                'git_blob_sha1': hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()}
        engine = (args.root/'engine.js').read_text()
        app = (args.root/'app.js').read_text()
        # Deliberately minimal DOM. Do not report fixture results as whole-page tests.
        controls = {'import': '<input id="import" type="file">',
                    'seed': '<input id="seed" value="20260920">',
                    'mode': '<select id="mode"><option value="cooperative">cooperative</option><option value="crew-race">crew-race</option></select>',
                    'autosave': '<input id="autosave" type="checkbox" checked>',
                    'action-json': '<textarea id="action-json"></textarea>'}
        buttons = {'play','step','batch','new','verify','export','clear','sample-action','apply-action','observation'}
        ids = sorted(set(re.findall(r"\$\('([^']+)'\)", app)) | buttons)
        fixture = '<!doctype html><html lang="en"><title>Controller fixture only</title><body>' + ''.join(
            controls.get(i, f'<button id="{i}">{i}</button>' if i in buttons else f'<div id="{i}"></div>') for i in ids) + '</body></html>'
        class Quiet(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *_): pass
        if not args.controller_fixture:
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(args.root)))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            url = f'http://127.0.0.1:{server.server_port}/'
            report['origin'] = url
        else:
            url = None
        with sync_playwright() as p:
            options = {'headless': True}
            if args.executable: options['executable_path'] = args.executable
            browser = getattr(p, args.browser).launch(**options)
            report['browser_version'] = browser.version
            def load(page):
                page.set_default_timeout(4000)
                page.on('pageerror', lambda e: report['page_errors'].append(str(e)))
                page.on('request', lambda r: report['external_requests'].append(r.url)
                        if r.url.startswith(('http:', 'https:')) and (url is None or not r.url.startswith(url)) else None)
                if args.controller_fixture:
                    page.set_content(fixture)
                    page.add_script_tag(content=engine)
                    page.add_script_tag(content=app)
                else:
                    response = page.goto(url, wait_until='load', timeout=10000)
                    assert response and response.status == 200, 'Origin document must return HTTP 200'
                assert page.locator('#turn').inner_text() == '0 / 240'
            def make_packet(page, seed=5):
                return page.evaluate('(seed) => JSON.stringify(Agentworld.pack({seed, mode:"cooperative"}, []))', seed)
            def queue_reads(page):
                page.evaluate('''() => {
                    window.pendingReads = Object.create(null);
                    File.prototype.text = function () {
                        return new Promise(resolve => { window.pendingReads[this.name] = resolve; });
                    };
                }''')
            def select(page, name, text):
                page.locator('#import').set_input_files({'name': name, 'mimeType':'application/json', 'buffer':text.encode()})
                page.wait_for_function('(name) => !!window.pendingReads[name]', arg=name)
            def release(page, name, text):
                page.evaluate('([name,text]) => window.pendingReads[name](text)', [name, text])
                # Await async handler microtasks, not a simulated gameplay clock.
                page.evaluate('() => new Promise(resolve => setTimeout(resolve, 0))')
            def step_race(page):
                queue_reads(page); text=make_packet(page); select(page,'A.json',text)
                page.locator('#step').click(); release(page,'A.json',text)
                assert page.locator('#turn').inner_text()=='1 / 240'
                assert 'World changed' in page.locator('#message').inner_text()
            def reset_race(page):
                queue_reads(page); text=make_packet(page); select(page,'A.json',text)
                page.locator('#seed').fill('7'); page.locator('#new').click(); release(page,'A.json',text)
                assert page.locator('#seed').input_value()=='7'
                assert 'World changed' in page.locator('#message').inner_text()
            def oldest_first(page):
                queue_reads(page); a=make_packet(page,5); b=make_packet(page,7)
                select(page,'A.json',a); select(page,'B.json',b)
                release(page,'A.json',a)
                assert page.locator('#seed').input_value()=='20260920', 'Superseded import A must not adopt while latest B is pending'
                release(page,'B.json',b)
                assert page.locator('#seed').input_value()=='7'
                assert 'Imported after' in page.locator('#message').inner_text()
            def newest_first(page):
                queue_reads(page); a=make_packet(page,5); b=make_packet(page,7)
                select(page,'A.json',a); select(page,'B.json',b)
                release(page,'B.json',b); release(page,'A.json',a)
                assert page.locator('#seed').input_value()=='7'
                assert 'Imported after' in page.locator('#message').inner_text(), 'Superseded read must not replace newer success with an error'
            def newest_invalid(page):
                queue_reads(page); a=make_packet(page,5); b='{"seed":1,"seed":2}'
                select(page,'A.json',a); select(page,'B.json',b)
                release(page,'B.json',b); release(page,'A.json',a)
                assert page.locator('#seed').input_value()=='20260920', 'Invalid latest import must not resurrect superseded A'
                assert 'Duplicate JSON key' in page.locator('#message').inner_text()
            def cancelled_replace(page):
                page.locator('#step').click(); page.on('dialog', lambda d:d.dismiss())
                text=make_packet(page,5)
                page.locator('#import').set_input_files({'name':'valid.json','mimeType':'application/json','buffer':text.encode()})
                page.wait_for_function('document.querySelector("#import").value === ""')
                assert page.locator('#turn').inner_text()=='1 / 240'
                assert page.locator('#seed').input_value()=='20260920'
            def oversized(page):
                page.locator('#import').set_input_files({'name':'large.json','mimeType':'application/json','buffer':b' ' * 131073})
                page.wait_for_function('document.querySelector("#message").textContent.includes("128 KiB")')
                assert page.locator('#turn').inner_text()=='0 / 240'
            def keyboard_focus(page):
                if not args.controller_fixture:
                    page.locator('summary').filter(has_text='Take a manual turn').click()
                control=page.locator('#manual button').filter(has_text=re.compile('^wait$'))
                control.focus(); page.keyboard.press('Enter')
                assert page.locator('#turn').inner_text()=='1 / 240'
                assert page.evaluate('document.querySelector("#manual").contains(document.activeElement)'), 'Manual action rerender must not drop keyboard focus to body'
            def reload_checkpoint(page):
                page.locator('#batch').click(); page.reload()
                assert page.locator('#turn').inner_text()=='16 / 240'
                assert page.locator('#proof').inner_text()=='Local replay pass'
            def corrupt_checkpoint(page):
                page.evaluate('(key) => localStorage.setItem(key,"{broken")',KEY); page.reload()
                assert not page.locator('#autosave').is_checked()
                page.locator('#step').click()
                assert page.evaluate('(key) => localStorage.getItem(key)',KEY)=='{broken'
            def tabs(page):
                page.locator('#step').click(); second=page.context.new_page(); second.goto(url)
                second.locator('#step').click()
                page.wait_for_function('!document.querySelector("#autosave").checked')
                saved=page.evaluate('(key) => localStorage.getItem(key)',KEY)
                page.locator('#step').click()
                assert page.evaluate('(key) => localStorage.getItem(key)',KEY)==saved
                second.close()
            cases=[('pending import refuses intervening turn',step_race),('pending import refuses same-turn reset',reset_race),
                   ('latest file selection wins: older resolves first',oldest_first),('newer success survives late older read',newest_first),
                   ('invalid latest selection does not resurrect older import',newest_invalid),
                   ('replacement cancellation preserves run',cancelled_replace),('oversized file leaves run unchanged',oversized),
                   ('manual keyboard action retains useful focus',keyboard_focus)]
            if not args.controller_fixture:
                cases += [('checkpoint reload verified',reload_checkpoint),('corrupt checkpoint not overwritten',corrupt_checkpoint),('real same-origin tabs preserve checkpoint on conflict',tabs)]
            names=[name for name,_ in cases]
            for name, fn in cases:
                context=browser.new_context(viewport={'width':1280,'height':1000})
                page=context.new_page()
                try:
                    load(page); fn(page)
                    report['checks'].append({'name':name,'status':'PASS'})
                except Exception as e:
                    blocked='ERR_BLOCKED_BY_ADMINISTRATOR' in str(e)
                    report['checks'].append({'name':name,'status':'BLOCKED' if blocked else 'FAIL','error':str(e)})
                    failures += 1
                    if blocked:
                        report['status']='BLOCKED'; break
                finally:
                    context.close()
            if report['status']!='BLOCKED':
                report['status']='FAIL' if failures or report['page_errors'] or report['external_requests'] else 'PASS'
            browser.close(); browser=None
    except Exception as e:
        report['status']='BLOCKED' if 'ERR_BLOCKED_BY_ADMINISTRATOR' in str(e) else 'ERROR'
        report['error']=str(e)
        report['traceback']=traceback.format_exc()
    finally:
        if browser:
            try: browser.close()
            except Exception as cleanup_error: report['cleanup_error'] = str(cleanup_error)
        if server: server.shutdown(); server.server_close()
        if thread: thread.join(timeout=3)
        completed={item['name'] for item in report['checks']}
        report['checks'] += [{'name':name,'status':'NOT_RUN'} for name in names if name not in completed]
        report['finished_at']=datetime.now(timezone.utc).isoformat()
        report['counts']={status:sum(c['status']==status for c in report['checks']) for status in ['PASS','FAIL','BLOCKED','NOT_RUN']}
        (args.output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
    return 0 if report['status']=='PASS' else 2

if __name__=='__main__':
    sys.exit(main())
