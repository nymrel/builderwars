"""Connected-version workflow with synthetic harness responses; no provider spend."""
import json
import os
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get('BUILDERWARS_TEST_URL', 'http://127.0.0.1:5178')
OUT = Path('output/playwright/model-development')
OUT.mkdir(parents=True, exist_ok=True)
KEY = 'PRIVATE_DEVELOPMENT_KEY'
ENDPOINT = 'https://private-development-endpoint.example/move'

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={'width': 390, 'height': 844}, service_workers='block')
    page = context.new_page()
    errors, traffic, submitted, held = [], [], [], []
    mode = {'value': 'normal'}
    origin = urlparse(BASE)
    def contain(route):
        url = route.request.url
        target = urlparse(url)
        if url == ENDPOINT:
            payload = route.request.post_data_json
            submitted.append(payload)
            assert route.request.headers.get('authorization') == 'Bearer ' + KEY
            if mode['value'] == 'held':
                held.append(route)
                return
            route.fulfill(json={'move': payload['legalMoves'][0], 'model': 'fixture/resolved', 'tokens': 20, 'outputTokens': 5})
        elif (target.scheme, target.netloc) == (origin.scheme, origin.netloc):
            route.continue_()
        else:
            traffic.append(url)
            route.abort('blockedbyclient')
    context.route('**/*', contain)
    context.route_web_socket('**/*', lambda ws: ws.close())
    page.on('pageerror', lambda e: errors.append(str(e)))
    try:
        page.goto(BASE)
        page.locator('[data-tab="evals"]').click()
        expect(page.locator('#dev-probe')).to_be_disabled()
        expect(page.locator('#dev-status')).to_contain_text('No version yet')
        assert not submitted
        page.locator('#dev-connect').click()
        page.locator('#agent-kind').select_option('harness')
        page.locator('#harness-model').fill('fixture/requested')
        page.locator('#harness-effort').fill('high')
        page.locator('#harness-url').fill(ENDPOINT)
        page.locator('#agent-key').fill(KEY)
        if not page.locator('#connection-advanced').evaluate('el => el.open'):
            page.locator('#connection-advanced > summary').click()
        page.locator('#strategy').fill('Baseline strategy')
        page.locator('#agent-form button[type=submit]').click()
        page.locator('[data-tab="evals"]').click()
        page.locator('#dev-consent').check()
        page.locator('#dev-probe').click()
        expect(page.locator('#dev-status')).to_contain_text('Baseline frozen')
        assert len(submitted) == 1 and submitted[0]['strategy'] == 'Baseline strategy'
        expect(page.locator('#dev-consent')).not_to_be_checked()
        expect(page.locator('#dev-version-info')).to_contain_text('fixture/resolved (self-reported)')
        expect(page.locator('#dev-practice')).to_be_disabled()  # chess, no fake training
        with page.expect_download() as download:
            page.locator('#dev-download-version').click()
        baseline = json.loads(Path(download.value.path()).read_text())
        assert baseline['config']['prompt'] == 'Baseline strategy'
        assert baseline['config']['runtime']['requestedModel'] == 'fixture/requested'
        assert KEY not in json.dumps(baseline) and ENDPOINT not in json.dumps(baseline)
        page.locator('#dev-edit > summary').click()
        page.locator('#dev-strategy').fill('Candidate strategy')
        page.locator('#dev-memory').fill('Frozen manual reminder')
        page.locator('#dev-fork').click()
        expect(page.locator('#dev-status')).to_contain_text('not selected or promoted')
        expect(page.locator('#dev-version-info')).to_contain_text('Selected v0')
        assert len(submitted) == 1
        page.locator('#dev-versions').select_option(index=1)
        page.locator('#dev-select').click()
        expect(page.locator('#dev-version-info')).to_contain_text('Selected v1')
        page.locator('#dev-plies').select_option('8')
        page.locator('#dev-consent').check()
        page.locator('#dev-compare').click()
        expect(page.locator('#dev-status')).to_contain_text('comparison finished', timeout=30000)
        expect(page.locator('#dev-version-info')).to_contain_text('Selected v1')
        result_details = page.locator('#dev-results').locator('..')
        if not result_details.evaluate('el => el.open'):
            result_details.locator('summary').click()
        with page.expect_download() as download:
            page.locator('[data-dev-download="1"]').click()
        attempt = json.loads(Path(download.value.path()).read_text())
        assert len(attempt['games']) == 4
        assert [g['seat'] for g in attempt['games']] == [0, 0, 1, 1]
        assert all(g['exit'] == 'capped' for g in attempt['games'])
        assert attempt['candidate'] is None and attempt['kind'] == 'compare'
        assert attempt['versions'][0]['digest'] == baseline['digest']
        assert KEY not in json.dumps(attempt) and ENDPOINT not in json.dumps(attempt)
        assert all(r.get('practiceMemory') == 'Frozen manual reminder' for r in submitted if r['strategy'] == 'Candidate strategy')
        assert all('practiceMemory' not in r for r in submitted if r['strategy'] == 'Baseline strategy')
        count = len(submitted)
        page.locator('#dev-rollback').click()
        expect(page.locator('#dev-version-info')).to_contain_text('Selected v0')
        assert len(submitted) == count
        page.locator('#dev-versions').select_option(index=1)
        page.locator('#dev-select').click()
        mode['value'] = 'held'
        page.locator('#dev-consent').check()
        page.locator('#dev-compare').click()
        expect(page.locator('#dev-status')).to_contain_text('Comparing')
        page.wait_for_function('document.querySelector("#dev-cancel").disabled === false')
        # Ensure an actual intercepted request is pending before cancellation.
        for _ in range(100):
            if held:
                break
            page.wait_for_timeout(10)
        assert held
        expect(page.locator('#dev-select')).to_be_disabled()
        page.locator('#dev-cancel').click()
        expect(page.locator('#dev-status')).to_contain_text('Cancelled or timed out')
        with page.expect_download() as download:
            page.locator('[data-dev-download="2"]').click()
        cancelled = json.loads(Path(download.value.path()).read_text())
        assert cancelled['exit'] == 'cancelled'
        assert len(cancelled['calls']) == 1 and cancelled['calls'][0]['cost'] is None
        for route in held:
            try:
                payload = route.request.post_data_json
                route.fulfill(json={'move': payload['legalMoves'][0], 'model': 'fixture/resolved'})
            except Exception:
                pass  # The browser may already have closed the aborted request.
        assert len(submitted) == count + 1
        for width in [320, 390, 768, 1280]:
            page.set_viewport_size({'width': width, 'height': 900})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
            page.locator('#development-title').scroll_into_view_if_needed()
            page.screenshot(path=str(OUT / f'workspace-{width}.png'), full_page=True)
        page.reload()
        page.locator('[data-tab="evals"]').click()
        expect(page.locator('#dev-status')).to_contain_text('No version yet')
        page.locator('#dev-import').set_input_files({'name': 'version.json', 'mimeType': 'application/json', 'buffer': json.dumps(baseline).encode()})
        expect(page.locator('#dev-status')).to_contain_text('disconnected and not selected')
        page.locator('#dev-select').click()
        expect(page.locator('#dev-version-info')).to_contain_text('Selected v0')
        assert len(submitted) == count + 1  # Import/select never reconnects or calls.
        tampered = {**baseline, 'digest': '0' * 64}
        page.locator('#dev-import').set_input_files({'name': 'tampered.json', 'mimeType': 'application/json', 'buffer': json.dumps(tampered).encode()})
        expect(page.locator('#dev-status')).to_contain_text('digest mismatch')
        expect(page.locator('#dev-version-info')).to_contain_text('Selected v0')
        assert not errors, errors
        assert not traffic, traffic
    finally:
        context.close()
        browser.close()
print('PASS: consented freeze, exact strategy/memory execution, 4-game compare, no promotion, rollback, cancellation, import recovery and responsive layout')
