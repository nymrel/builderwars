"""Chromium checks for source and bundled HTML on an authorized loopback origin."""
import argparse
import functools
import hashlib
import http.server
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import time

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path(tempfile.gettempdir()) / 'builderwars-agency-evidence')
    parser.add_argument('--chromium', default='/usr/bin/chromium')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    preview = args.out / 'BuilderWars-AgentWorld.html'
    subprocess.run(['python', str(ROOT / 'build_preview.py'), '--output', str(preview)], check=True)
    class PreviewHandler(Quiet):
        def do_GET(self):
            if self.path == '/portable.html':
                body = preview.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                super().do_GET()

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(PreviewHandler, directory=str(ROOT.parent)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}/'
    checks = []

    def check(mode, name, condition):
        if not condition:
            raise AssertionError(f'{mode}: {name}')
        checks.append({'mode': mode, 'name': name, 'passed': True})

    def settle(predicate):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(.03)
        raise AssertionError('Timed out waiting for browser state')

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=args.chromium, headless=True, args=['--no-sandbox'])
            version = browser.version
            for mode, url in [('origin', origin + 'agency/'), ('portable-origin', origin + 'portable.html')]:
                context = browser.new_context(viewport={'width': 1280, 'height': 1000}, accept_downloads=True)
                page = context.new_page()
                errors, external = [], []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('request', lambda request: external.append(request.url) if not request.url.startswith((origin, 'file:', 'blob:', 'data:')) else None)
                page.goto(url)
                page.locator('#card-amber-1').wait_for()

                def turn():
                    return int(page.locator('#turn-count').inner_text().split('/')[0].strip())

                def reset(seed=1):
                    page.locator('#new-world').click()
                    page.locator('#new-seed').fill(str(seed))
                    page.locator('#dialog-confirm').click()
                    assert turn() == 0

                def export():
                    with page.expect_download() as pending:
                        page.locator('#export-visit').click()
                    return json.loads(Path(pending.value.path()).read_text())

                def choose_file(packet, name='visit.json'):
                    text = packet if isinstance(packet, str) else json.dumps(packet)
                    page.locator('#import-file').set_input_files({'name': name, 'mimeType': 'application/json', 'buffer': text.encode()})

                check(mode, 'Four companions and four map actors render', page.locator('#agent-cards button').count() == 4 and page.locator('.map-agent').count() == 4)
                check(mode, 'Rule-based simulation disclosed before controls', page.locator('.intro').inner_text().lower().find('rule-based') >= 0)
                for width in [320, 390, 768, 1280]:
                    page.set_viewport_size({'width': width, 'height': 900})
                    check(mode, f'No horizontal overflow at {width}px', page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                page.set_viewport_size({'width': 390, 'height': 844})
                page.evaluate('scrollTo(0, 0)')
                check(mode, 'Primary choice is reachable in first phone viewport', page.locator('#next-choice').bounding_box()['y'] + page.locator('#next-choice').bounding_box()['height'] <= 844)
                page.set_viewport_size({'width': 1280, 'height': 1000})
                reset()
                page.locator('#next-choice').click()
                baseline = export()
                check(mode, 'Self-directed step advances exactly once', turn() == 1 and baseline['requests'] == [None])
                reset()
                page.locator('#suggestion').select_option('rest')
                page.locator('#suggest-step').click()
                rested = export()
                check(mode, 'Accepted recovery changes material action from baseline', rested['requests'] == ['rest'] and rested['finalWorld']['agents'][0]['x'] != baseline['finalWorld']['agents'][0]['x'])
                reset()
                page.locator('#suggestion').select_option('explore')
                page.locator('#suggest-step').click()
                check(mode, 'Mara refuses exploration visibly', 'Declined suggestion' in page.locator('#decision-log li').first.inner_text())
                page.locator('#suggest-step').click()
                check(mode, 'Kite accepts the same exploration suggestion', 'Kite' in page.locator('#decision-log li').first.inner_text() and 'Accepted suggestion' in page.locator('#decision-log li').first.inner_text())
                saved = export()
                saved_turn = turn()
                page.locator('#autoplay').click()
                settle(lambda: turn() > saved_turn)
                page.locator('#stop').click()
                stopped = turn()
                page.wait_for_timeout(1250)
                check(mode, 'Stop cancels automatic advancement', turn() == stopped)
                check(mode, 'Stop retains useful keyboard focus', page.evaluate("document.activeElement.id") in ['autoplay', 'stop'])
                check(mode, 'Suggestion selection survives renders', page.locator('#suggestion').input_value() == 'explore')

                bad = json.loads(json.dumps(saved))
                bad['finalWorld']['scores']['amber'] += 1
                choose_file(bad)
                settle(lambda: 'Could not open' in page.locator('#notice').inner_text())
                check(mode, 'Tampered import leaves current visit intact', turn() == stopped and not page.locator('#replace-dialog').evaluate('(node) => node.open'))
                choose_file('{"schema":1,"schema":2}')
                settle(lambda: 'Duplicate' in page.locator('#notice').inner_text())
                check(mode, 'Duplicate-key import refused', turn() == stopped)
                choose_file(saved)
                page.locator('#dialog-cancel').click()
                check(mode, 'Cancel import preserves current visit', turn() == stopped)
                choose_file(saved)
                page.locator('#dialog-confirm').click()
                check(mode, 'Confirmed import restores exact checkpoint', turn() == saved_turn and export() == saved)

                page.evaluate("""() => {
                  window.originalFileText = File.prototype.text;
                  window.pendingFileReads = [];
                  File.prototype.text = function() { return new Promise(resolve => pendingFileReads.push(resolve)); };
                }""")
                choose_file(saved)
                settle(lambda: page.evaluate('pendingFileReads.length') == 1)
                page.locator('#next-choice').click()
                new_turn = turn()
                page.evaluate('(text) => pendingFileReads[0](text)', json.dumps(saved))
                settle(lambda: 'world changed' in page.locator('#notice').inner_text())
                check(mode, 'Pending import cannot replace a newer world step', turn() == new_turn and not page.locator('#replace-dialog').evaluate('(node) => node.open'))
                page.evaluate('pendingFileReads = []')
                choose_file(saved, 'older.json')
                choose_file(saved, 'newer.json')
                settle(lambda: page.evaluate('pendingFileReads.length') == 2)
                newer = page.evaluate('AgentworldAgency.pack(AgentworldAgency.create({seed:12,mode:"cooperative"}))')
                page.evaluate('(text) => pendingFileReads[1](text)', json.dumps(newer))
                page.locator('#dialog-confirm').wait_for()
                page.evaluate('pendingFileReads[0]("malformed old read")')
                page.wait_for_timeout(100)
                check(mode, 'Newest import owns dialog and late old failure is ignored', 'seed 12,' in page.locator('#dialog-description').inner_text() and 'malformed' not in page.locator('#notice').inner_text())
                page.locator('#dialog-confirm').click()
                check(mode, 'Newest selected file becomes current only on confirmation', export()['config']['seed'] == 12)
                page.evaluate('() => { File.prototype.text = originalFileText; }')

                # Simulates the browser visibility event; this is not physical-device background acceptance.
                page.locator('#autoplay').click()
                page.evaluate("Object.defineProperty(document, 'hidden', {configurable:true,get:()=>true}); document.dispatchEvent(new Event('visibilitychange'))")
                hidden_turn = turn()
                page.wait_for_timeout(1250)
                check(mode, 'Simulated hidden-page event pauses automatic turns', turn() == hidden_turn and page.locator('#autoplay').is_visible())
                page.evaluate('delete document.hidden')

                terminal = page.evaluate("""() => {
                  let s = AgentworldAgency.create({seed:5,mode:'cooperative'});
                  while(s.world.status === 'running') s = AgentworldAgency.advance(s);
                  return AgentworldAgency.pack(s);
                }""")
                choose_file(terminal)
                page.locator('#dialog-confirm').click()
                check(mode, 'Capped visit is incomplete and cannot advance', turn() == 240 and 'limit' in page.locator('#status-label').inner_text().lower() and page.locator('#next-choice').is_disabled() and terminal['finalWorld']['status'] == 'capped')
                reset(1)
                page.locator('#suggestion').select_option('explore')
                for _ in range(4):
                    page.locator('#suggest-step').click()
                key = 'builderwars.agency.return.v1'
                check(mode, 'No device checkpoint before explicit saving', page.evaluate('(key) => localStorage.getItem(key)', key) is None)
                kept = export()
                page.locator('#save-visit').check()
                check(mode, 'Opt-in saves a verified checkpoint and acknowledges its choice', page.evaluate('(key) => JSON.parse(localStorage.getItem(key)).requests.length', key) == 4 and 'Saved through choice 4' in page.locator('#save-status').inner_text())
                page.locator('#save-visit').uncheck()
                page.locator('#next-choice').click()
                check(mode, 'Opt-out preserves earlier checkpoint without saving new choices', turn() == 5 and page.evaluate('(key) => JSON.parse(localStorage.getItem(key)).requests.length', key) == 4)
                page.locator('#save-visit').click()
                check(mode, 'A different unsaved visit cannot silently replace the checkpoint', not page.locator('#save-visit').is_checked() and page.evaluate('(key) => JSON.parse(localStorage.getItem(key)).requests.length', key) == 4)
                page.reload()
                page.locator('#resume-visit').wait_for()
                check(mode, 'Reload offers a recap without starting the world', turn() == 0 and '4 choices' in page.locator('#return-recap').inner_text() and page.locator('#stop').is_hidden())
                for width in [320, 390, 430]:
                    page.set_viewport_size({'width': width, 'height': 844})
                    page.evaluate('scrollTo(0, 0)')
                    box = page.locator('#resume-visit').bounding_box()
                    check(mode, f'Return action visible without overflow at {width}px', box['y'] + box['height'] <= 844 and page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                page.screenshot(path=str(args.out / f'{mode}-return-mobile.png'), full_page=True)
                page.set_viewport_size({'width': 1280, 'height': 1000})
                page.locator('#next-choice').click()
                check(mode, 'Unresumed checkpoint survives new unsaved play', turn() == 1 and page.evaluate('(key) => JSON.parse(localStorage.getItem(key)).requests.length', key) == 4)
                page.locator('#resume-visit').click()
                page.locator('#dialog-cancel').click()
                check(mode, 'Cancelling resume preserves the current visit', turn() == 1)
                page.locator('#resume-visit').click()
                page.locator('#dialog-confirm').click()
                page.wait_for_timeout(1250)
                check(mode, 'Explicit resume restores exact plans and memory paused', turn() == 4 and export() == kept and page.locator('#save-visit').is_checked() and page.locator('#stop').is_hidden())
                page.locator('#next-choice').click()
                check(mode, 'Resumed choices advance and save only after user action', turn() == 5 and page.evaluate('(key) => JSON.parse(localStorage.getItem(key)).requests.length', key) == 5)
                other = context.new_page()
                other.goto(url)
                other.locator('#resume-visit').click()
                other.locator('#dialog-confirm').click()
                other.locator('#next-choice').click()
                settle(lambda: 'another tab' in page.locator('#notice').inner_text())
                check(mode, 'Other-tab save pauses local saving without replacing the current world', turn() == 5 and not page.locator('#save-visit').is_checked() and '6 choices' in page.locator('#return-recap').inner_text())
                other.close()
                page.locator('#resume-visit').click()
                page.locator('#dialog-confirm').click()
                page.evaluate("""(key) => {
                  window.originalSetItem = Storage.prototype.setItem;
                  Storage.prototype.setItem = function(k, v) { if(k === key) throw new DOMException('Synthetic quota failure', 'QuotaExceededError'); return originalSetItem.call(this, k, v); };
                }""", key)
                page.locator('#next-choice').click()
                check(mode, 'Quota failure preserves the earlier save and explains unsaved progress', turn() == 7 and not page.locator('#save-visit').is_checked() and 'could not be saved' in page.locator('#notice').inner_text() and page.evaluate('(key) => JSON.parse(localStorage.getItem(key)).requests.length', key) == 6)
                page.evaluate('() => { Storage.prototype.setItem = originalSetItem; }')
                page.locator('#forget-visit').click()
                page.locator('#next-choice').click()
                check(mode, 'Forget keeps this visit and prevents silent resaving', turn() == 8 and page.evaluate('(key) => localStorage.getItem(key)', key) is None)
                page.evaluate('(key) => localStorage.setItem(key, "corrupt checkpoint")', key)
                page.reload()
                page.locator('#card-amber-1').wait_for()
                check(mode, 'Corrupt checkpoint is retained without restoring it', turn() == 0 and page.locator('#return-banner').is_hidden() and 'could not be verified' in page.locator('#save-status').inner_text() and page.evaluate('(key) => localStorage.getItem(key)', key) == 'corrupt checkpoint')
                page.locator('#save-visit').click()
                check(mode, 'Opt-in cannot overwrite an unverified saved visit', not page.locator('#save-visit').is_checked() and page.evaluate('(key) => localStorage.getItem(key)', key) == 'corrupt checkpoint')
                page.locator('#forget-visit').click()
                check(mode, 'Explicit forget can clear a corrupt checkpoint', page.evaluate('(key) => localStorage.getItem(key)', key) is None)
                reset(1)
                for _ in range(4):
                    page.locator('#suggest-step').click()
                page.evaluate('scrollTo(0, 0)')
                page.screenshot(path=str(args.out / f'{mode}-desktop.png'), full_page=True)
                page.set_viewport_size({'width': 390, 'height': 844})
                page.screenshot(path=str(args.out / f'{mode}-mobile.png'), full_page=True)
                check(mode, 'No JavaScript errors', not errors)
                check(mode, 'No external requests', not external)
                context.close()
            nojs = browser.new_context(java_script_enabled=False)
            page = nojs.new_page()
            page.goto(origin + 'agency/')
            check('origin', 'No-JavaScript recovery text is visible', page.locator('noscript').is_visible())
            nojs.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    files = ['../engine.js', 'policy.js', 'return-visit.js', 'app.js', 'index.html', 'build_preview.py', 'browser_test.py']
    receipt = {'browser': version, 'checks': checks, 'sourceSha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files}, 'limitations': ['Chromium only', 'No physical phone or screen-reader acceptance', 'Visibility event is simulated', 'Portable HTML tested over loopback; file navigation is blocked by this host policy', 'Local deterministic companions; zero provider calls']}
    (args.out / 'browser-results.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'passed': len(checks), 'browser': version, 'output': str(args.out)}))


if __name__ == '__main__':
    main()
