"""Supplemental Agentworld acceptance. Default: real loopback origin, never fixture fallback.

--controller-fixture explicitly tests exact engine/ledger/app JS on a minimal in-memory DOM.
That mode does NOT test index.html, CSP, persistence, cross-tab events, or deployment.
--portable-preview builds and tests the self-contained HTML on a real loopback origin.
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
import subprocess
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
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--controller-fixture', action='store_true')
    mode.add_argument('--portable-preview', action='store_true')
    p.add_argument('--browser', choices=['chromium', 'firefox', 'webkit'], default='chromium')
    p.add_argument('--executable', help='Optional already-installed, authorized browser path.')
    return p.parse_args()

def main():
    args = arguments()
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'schema': 'builderwars.agentworld.supplemental-review.v1',
              'started_at': datetime.now(timezone.utc).isoformat(),
              'scope': ('controller-only in-memory fixture; NOT index/CSP/origin/storage/cross-tab acceptance'
                        if args.controller_fixture else 'standalone generated preview on loopback; NOT file-viewer/deployment acceptance'
                        if args.portable_preview else 'loopback supplemental browser acceptance; NOT deployed/lab-integrated/independently approved'),
              'browser': args.browser, 'executable': args.executable,
              'playwright': importlib.metadata.version('playwright'),
              'harness_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'source_files': {}, 'checks': [], 'page_errors': [], 'external_requests': [],
              'csp_violations': [], 'preview_subresource_requests': [],
              'status': 'NOT_RUN', 'policy_changes': False}
    server = thread = browser = None
    failures = 0
    names = []
    try:
        for name in ['engine.js', 'ledger.js', 'app.js'] + ([] if args.controller_fixture else ['index.html']):
            raw = (args.root / name).read_bytes()
            report['source_files'][name] = {'sha256': hashlib.sha256(raw).hexdigest(),
                'git_blob_sha1': hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()}
        engine = (args.root/'engine.js').read_text()
        ledger = (args.root/'ledger.js').read_text()
        app = (args.root/'app.js').read_text()
        # Deliberately minimal DOM. Do not report fixture results as whole-page tests.
        controls = {'import': '<input id="import" type="file">',
                    'ledger-import': '<input id="ledger-import" type="file" multiple>',
                    'seed': '<input id="seed" value="20260920">',
                    'mode': '<select id="mode"><option value="cooperative">cooperative</option><option value="crew-race">crew-race</option></select>',
                    'autosave': '<input id="autosave" type="checkbox" checked>',
                    'action-json': '<textarea id="action-json"></textarea>'}
        buttons = {'play','step','batch','new','verify','export','clear','sample-action','apply-action','observation','ledger-build','ledger-export'}
        ids = sorted(set(re.findall(r"\$\('([^']+)'\)", app)) | buttons)
        fixture = '<!doctype html><html lang="en"><title>Controller fixture only</title><body>' + ''.join(
            controls.get(i, f'<button id="{i}">{i}</button>' if i in buttons else f'<div id="{i}"></div>') for i in ids) + '</body></html>'
        class Quiet(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *_): pass
        if args.portable_preview:
            preview = args.output/'BuilderWars-Agentworld-Preview.html'
            subprocess.run([sys.executable, str(args.root/'build_preview.py'), '--output', str(preview)], check=True)
            report['preview_sha256'] = hashlib.sha256(preview.read_bytes()).hexdigest()
            report['source_files']['build_preview.py'] = {'sha256': hashlib.sha256((args.root/'build_preview.py').read_bytes()).hexdigest()}
        if not args.controller_fixture:
            served = args.output if args.portable_preview else args.root
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(served)))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            origin = f'http://127.0.0.1:{server.server_port}/'
            url = origin + ('BuilderWars-Agentworld-Preview.html' if args.portable_preview else '')
            report['origin'] = origin
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
                        if r.url.startswith(('http:', 'https:')) and (url is None or not r.url.startswith(origin)) else None)
                if args.portable_preview:
                    page.on('request', lambda r: report['preview_subresource_requests'].append(r.url)
                            if r.resource_type != 'document' and not r.url.startswith('blob:') else None)
                if args.controller_fixture:
                    page.set_content(fixture)
                    page.add_script_tag(content=engine)
                    page.add_script_tag(content=ledger)
                    page.add_script_tag(content=app)
                else:
                    page.add_init_script('''window.cspViolations=[]; document.addEventListener('securitypolicyviolation', event => {
                        window.cspViolations.push({directive:event.effectiveDirective, blocked:event.blockedURI});
                    });''')
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
                assert page.locator('#proof').inner_text().strip().lower()=='local replay pass'
            def corrupt_checkpoint(page):
                page.evaluate('(key) => localStorage.setItem(key,"{broken")',KEY); page.reload()
                assert not page.locator('#autosave').is_checked()
                page.locator('#step').click()
                assert page.evaluate('(key) => localStorage.getItem(key)',KEY)=='{broken'
            def tabs(page):
                page.locator('#step').click(); second=page.context.new_page(); second.goto(url)
                second.locator('#step').click()
                for _ in range(50):
                    if not page.locator('#autosave').is_checked():
                        break
                    page.wait_for_timeout(100)
                assert not page.locator('#autosave').is_checked(), 'Cross-tab storage change must disable autosave'
                saved=page.evaluate('(key) => localStorage.getItem(key)',KEY)
                page.locator('#step').click()
                assert page.evaluate('(key) => localStorage.getItem(key)',KEY)==saved
                second.close()
            def hive_ledger(page):
                def packet(seed):
                    return page.evaluate('(seed) => JSON.stringify(Agentworld.pack({seed, mode:"cooperative"}, (() => { let s = Agentworld.create({seed, mode:"cooperative"}); const a = []; while (s.status === "running") { const x = Agentworld.scripted(s); a.push(x); s = Agentworld.step(s, x); } return a; })()))',seed)
                open_ledger(page)
                first = packet(5)
                page.locator('#ledger-import').set_input_files(files=[
                    {'name':'seed-5.json','mimeType':'application/json','buffer':first.encode('utf-8')},
                    {'name':'seed-9.json','mimeType':'application/json','buffer':packet(9).encode('utf-8')},
                    {'name':'z-copy.json','mimeType':'application/json','buffer':first.encode('utf-8')},
                    {'name':'broken.json','mimeType':'application/json','buffer':b'{broken'},
                ])
                page.locator('#ledger-build').click()
                wait_ledger(page)
                assert '2 verified runs' in page.locator('#ledger-status').inner_text()
                out=page.locator('#ledger-out').inner_text()
                assert 'Refused: broken.json' in out
                assert 'Refused: z-copy.json' in out and 'Duplicate verified replay' in out
                assert 'not a ranking' in out.lower()
                assert 'seed-9.json' in out
                exported = export_ledger(page)
                assert exported['totals']['runs'] == 2 and exported['totals']['refused'] == 2
                assert [r['label'] for r in exported['runs']] == ['seed-5.json','seed-9.json']
            def open_ledger(page):
                if not args.controller_fixture:
                    page.locator('details:has(#ledger-import) summary').click()
            def wait_ledger(page):
                for _ in range(50):
                    if page.locator('#ledger-export').is_enabled():
                        return
                    page.wait_for_timeout(100)
                raise AssertionError('Ledger did not publish a completed snapshot')
            def export_ledger(page):
                with page.expect_download() as event:
                    page.locator('#ledger-export').click()
                return json.loads(Path(event.value.path()).read_text())
            def ledger_file(page, name, text):
                page.locator('#ledger-import').set_input_files({'name':name,'mimeType':'application/json','buffer':text.encode()})
            def queue_ledger_reads(page):
                page.evaluate('''() => {
                    window.pendingLedgerReads = [];
                    File.prototype.text = function () {
                        return new Promise((resolve,reject) => window.pendingLedgerReads.push({name:this.name,resolve,reject}));
                    };
                }''')
            def release_ledger(page, index, text=None, reject=False):
                page.evaluate('''({index,text,reject}) => {
                    const pending=window.pendingLedgerReads[index];
                    if (reject) pending.reject(new Error('Synthetic read failure'));
                    else pending.resolve(text);
                }''', {'index':index,'text':text,'reject':reject})
                page.evaluate('() => new Promise(resolve => setTimeout(resolve, 0))')
            def ledger_file_bounds(page):
                open_ledger(page)
                text=make_packet(page,5)
                page.evaluate('''() => {
                    window.ledgerReads=[];
                    const read=File.prototype.text;
                    File.prototype.text=function () {
                        window.ledgerReads.push(this.name);
                        if (this.name==='unreadable.json') return Promise.reject(new Error('Synthetic read failure'));
                        return read.call(this);
                    };
                }''')
                page.locator('#ledger-import').set_input_files(files=[
                    {'name':'large.json','mimeType':'application/json','buffer':b' ' * 131073},
                    {'name':'unreadable.json','mimeType':'application/json','buffer':b'{}'},
                    {'name':'good.json','mimeType':'application/json','buffer':text.encode()},
                ])
                page.locator('#ledger-build').click(); wait_ledger(page)
                assert page.evaluate('window.ledgerReads') == ['unreadable.json','good.json'], 'Oversized file must never be read'
                exported=export_ledger(page)
                assert exported['totals']['runs']==1 and exported['totals']['refused']==2
                reasons={r['label']:r['reason'] for r in exported['refused']}
                assert '128 KiB' in reasons['large.json'] and 'not read' in reasons['large.json']
                assert 'could not be read' in reasons['unreadable.json']
                page.locator('#ledger-import').set_input_files(files=[
                    {'name':f'{i}.json','mimeType':'application/json','buffer':text.encode()} for i in range(65)
                ])
                page.locator('#ledger-build').click()
                assert 'at most 64' in page.locator('#message').inner_text()
                assert page.evaluate('window.ledgerReads') == ['unreadable.json','good.json'], 'Over-bound selection must read no additional files'
                assert page.locator('#ledger-export').is_disabled() and not page.locator('#ledger-out').inner_text()
            def ledger_selection_cancels(page):
                open_ledger(page); queue_ledger_reads(page)
                text=make_packet(page,5); ledger_file(page,'old.json',text); page.locator('#ledger-build').click()
                page.locator('#ledger-import').set_input_files([])
                status=page.locator('#ledger-status').inner_text()
                release_ledger(page,0,text)
                assert page.locator('#ledger-status').inner_text()==status and 'selection changed' in status
                assert not page.locator('#ledger-out').inner_text() and page.locator('#ledger-export').is_disabled()
            def ledger_newest_build(page):
                open_ledger(page); queue_ledger_reads(page)
                text=make_packet(page,5); ledger_file(page,'same.json',text)
                page.locator('#ledger-build').click(); page.locator('#ledger-build').click()
                release_ledger(page,1,text); wait_ledger(page)
                status=page.locator('#ledger-status').inner_text(); message=page.locator('#message').inner_text()
                expected=export_ledger(page)
                release_ledger(page,0,reject=True)
                assert page.locator('#ledger-status').inner_text()==status and page.locator('#message').inner_text()==message
                assert export_ledger(page)==expected, 'Late older read error must not replace newer displayed/exported snapshot'
            def ledger_newest_selection(page):
                open_ledger(page); queue_ledger_reads(page)
                a=make_packet(page,5); b=make_packet(page,7)
                ledger_file(page,'old.json',a); page.locator('#ledger-build').click()
                ledger_file(page,'new.json',b); page.locator('#ledger-build').click()
                release_ledger(page,1,b); wait_ledger(page)
                status=page.locator('#ledger-status').inner_text(); message=page.locator('#message').inner_text()
                expected=export_ledger(page)
                release_ledger(page,0,a)
                assert page.locator('#ledger-status').inner_text()==status and page.locator('#message').inner_text()==message
                assert 'new.json' in page.locator('#ledger-out').inner_text() and 'old.json' not in page.locator('#ledger-out').inner_text()
                assert expected['runs'][0]['seed']==7 and export_ledger(page)==expected
            def portable_scripts(page):
                assert page.locator('script[src]').count()==0 and page.locator('script').count()==3
                policy=page.locator('meta[http-equiv="Content-Security-Policy"]').get_attribute('content')
                script_policy=next(p.strip() for p in policy.split(';') if p.strip().startswith('script-src '))
                assert script_policy.count("'sha256-")==3
                assert "'self'" not in script_policy and 'unsafe-' not in script_policy
                assert "connect-src 'none'" in policy
                assert page.evaluate('typeof AgentworldLedger.tallyRuns')=='function'
            cases=[('pending import refuses intervening turn',step_race),('pending import refuses same-turn reset',reset_race),
                   ('latest file selection wins: older resolves first',oldest_first),('newer success survives late older read',newest_first),
                   ('invalid latest selection does not resurrect older import',newest_invalid),
                   ('replacement cancellation preserves run',cancelled_replace),('oversized file leaves run unchanged',oversized),
                   ('manual keyboard action retains useful focus',keyboard_focus),
                   ('hive ledger deduplicates verified contents and exports refusals',hive_ledger),
                   ('hive file bounds prevent reads and preserve per-file refusals',ledger_file_bounds),
                   ('hive input change cancels pending build without exporting stale results',ledger_selection_cancels),
                   ('hive newer build survives older read error',ledger_newest_build),
                   ('hive newer selection survives older success with matching export',ledger_newest_selection)]
            if not args.controller_fixture:
                cases += [('checkpoint reload verified',reload_checkpoint),('corrupt checkpoint not overwritten',corrupt_checkpoint),('real same-origin tabs preserve checkpoint on conflict',tabs)]
            if args.portable_preview:
                cases += [('standalone preview embeds all scripts under hash-only script CSP',portable_scripts)]
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
                    if not args.controller_fixture:
                        report['csp_violations'] += page.evaluate('window.cspViolations || []')
                    context.close()
            if report['status']!='BLOCKED':
                report['status']='FAIL' if failures or report['page_errors'] or report['external_requests'] or report['csp_violations'] or report['preview_subresource_requests'] else 'PASS'
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
