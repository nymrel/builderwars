"""Real local worker, durable evidence, clean public routes and zero-provider launch journeys."""
import os, json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
BASE=os.environ.get('BUILDERWARS_TEST_URL','http://127.0.0.1:5189')
KEY='builderwars.browser-lab.archive.v1'
OUT=Path(os.environ.get('BUILDERWARS_LAUNCH_ARTIFACTS','output/playwright/launch'));OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':1000});errors=[];calls=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('request',lambda r:calls.append(r.url) if '/api/v1/chat/completions' in r.url or r.url.endswith('/move') else None)
 page.goto(BASE+'/#compete');expect(page.locator('#compete')).to_be_visible();page.locator('#compete [data-hub-tab="evals"]').click();assert page.url.endswith('#evals');page.reload();expect(page.locator('#evals')).to_be_visible();assert page.evaluate('document.activeElement.tagName') in ('H1','H2')
 page.go_back();expect(page.locator('#compete')).to_be_visible();page.go_forward();expect(page.locator('#evals')).to_be_visible()
 page.locator('nav [data-tab="compete"]').click();page.locator('#prepare-oracle').click();expect(page.locator('#series-length')).to_have_value('4');page.locator('nav [data-tab="arena"]').click();expect(page.locator('#game-title')).to_have_text('Tic-tac-toe');expect(page.locator('#metric-moves')).to_have_text('0')
 page.locator('#connect-first').click();expect(page.locator('#agent-kind')).to_have_value('harness');page.locator('#close-dialog').click()
 page.locator('#quickplay').click();rect=page.locator('#board').bounding_box();assert rect['y']<1000 and rect['y']+rect['height']>0;page.locator('#start').click() if page.locator('#start').inner_text().find('Pause')>=0 else None
 page.goto(BASE+'/#lab');page.locator('#lab-form summary').click();page.locator('#lab-seed').fill('20261006');page.locator('#lab-start').click()
 page.wait_for_function("key => JSON.parse(localStorage.getItem(key)||'{}').runs?.at(-1)?.status==='completed'",arg=KEY,timeout=90000)
 expect(page.locator('#lab-status')).to_contain_text('Comparison completed');archive=page.evaluate('key => JSON.parse(localStorage.getItem(key))',KEY);run=archive['runs'][-1];assert len(run['blocks'])==16 and run['summary']['completedGames']==128 and archive['selected']==run['parent']['digest']
 page.screenshot(path=str(OUT/'lab-desktop.png'),full_page=True)
 page.reload();expect(page.locator('#lab-status')).to_contain_text('Saved comparison restored');assert page.locator('#lab-start').is_enabled()
 candidate=run['candidate']['digest'];page.locator(f'[data-lab-select="{candidate}"]').click();expect(page.locator('#lab-status')).to_contain_text('Version selected');page.locator('#lab-rollback').click();expect(page.locator('#lab-status')).to_contain_text('Prior selection restored')
 # Lab recordings share recovery and consent with files, links and saved results.
 page.locator('nav [data-tab="arena"]').click();page.locator('[data-game="tictactoe"]').click();page.locator('#step').click()
 expect(page.locator('#metric-moves')).to_have_text('1');seats=page.locator('#seats').text_content()
 page.locator('nav [data-tab="lab"]').click();page.locator('[data-lab-replay]').click()
 expect(page.locator('#recording-dialog')).to_be_visible();expect(page.locator('#recording-recovery')).to_contain_text('Saved in Recent matches')
 expect(page.locator('#metric-moves')).to_have_text('1');assert page.locator('#seats').text_content()==seats
 page.locator('#keep-current-match').click();expect(page.locator('#recording-dialog')).not_to_be_visible();expect(page.locator('#lab')).to_be_visible()
 expect(page.locator('#metric-moves')).to_have_text('1');assert page.locator('#seats').text_content()==seats
 page.locator('[data-lab-replay]').click();expect(page.locator('#recording-dialog')).to_be_visible();expect(page.locator('#metric-moves')).to_have_text('1')
 page.locator('#open-recording').click();expect(page.locator('#arena')).to_be_visible();expect(page.locator('#start')).to_be_disabled();assert int(page.locator('#metric-moves').inner_text())>1
 page.locator('nav [data-tab="lab"]').click()
 page.locator(f'[data-lab-use="{candidate}"]').click();expect(page.locator('#arena')).to_be_visible();expect(page.locator('#metric-moves')).to_have_text('0');page.locator('#step').click();expect(page.locator('#metric-moves')).to_have_text('1');page.locator('#start').click();expect(page.locator('#postgame-review')).to_be_visible(timeout=45000);assert '90 seconds' not in page.locator('#notice').inner_text() or page.locator('#metric-moves').inner_text() != '1'
 page.once('dialog',lambda d:d.accept());page.locator('nav [data-tab="lab"]').click();page.locator('#lab-trials').select_option('64');page.locator('#lab-form summary').click();page.locator('#lab-seed').fill('20261007');page.locator('#lab-start').click();page.wait_for_function("key => JSON.parse(localStorage.getItem(key)||'{}').runs?.at(-1)?.status==='evaluating'",arg=KEY,timeout=60000);page.locator('#lab-cancel').click();expect(page.locator('#lab-status')).to_contain_text('Cancelled');cancelled=page.evaluate('key => JSON.parse(localStorage.getItem(key)).runs.at(-1)',KEY);assert cancelled['status']=='cancelled';page.reload();assert page.locator('#lab-start').is_enabled();assert page.evaluate('key=>JSON.parse(localStorage.getItem(key)).runs.at(-1).status',KEY)=='cancelled'
 with page.expect_download() as download:page.locator('#lab-archive-export').click()
 assert download.value.suggested_filename=='builderwars-lab-archive.json'
 # A failed plan save must preserve bytes and must not start a worker.
 previous=page.evaluate('key=>localStorage.getItem(key)',KEY)
 page.evaluate("""key=>{window.labOriginalSet=Storage.prototype.setItem; window.labWorkerCount=0; window.labOriginalWorker=Worker; window.Worker=class extends window.labOriginalWorker{constructor(...args){window.labWorkerCount++;super(...args)}}; Storage.prototype.setItem=function(k,v){if(k===key)throw Error('Synthetic full storage');return window.labOriginalSet.call(this,k,v)};}""",KEY)
 page.locator('#lab-start').click();expect(page.locator('#lab-status')).to_contain_text('Synthetic full storage');assert page.evaluate('window.labWorkerCount')==0;assert page.evaluate('key=>localStorage.getItem(key)',KEY)==previous
 page.evaluate('() => { Storage.prototype.setItem=window.labOriginalSet;window.Worker=window.labOriginalWorker; }')
 # Historical source updates preserve readable/exportable evidence and permit fresh current-source work.
 page.evaluate("""async key=>{const a=JSON.parse(localStorage.getItem(key));const sha=async x=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(x))))].map(b=>b.toString(16).padStart(2,'0')).join('');const prior=a.selected;for(const v of a.versions){v.config.harness.source='1'.repeat(64);v.config.referee='2'.repeat(64);const {digest,...body}=v;v.digest=await sha(body);}a.selected=a.versions[0].digest;a.selections=[a.selected];for(const r of a.runs){r.parent=a.versions[0];r.candidate=a.versions[1];r.plan.source='1'.repeat(64);r.plan.referee='2'.repeat(64);const {digest,...body}=r.plan;r.plan.digest=await sha(body);}localStorage.setItem(key,JSON.stringify(a));}""",KEY)
 page.reload();expect(page.locator('#lab-summary')).to_contain_text('Historical build');assert page.locator('#lab-start').is_enabled();assert page.locator('[data-lab-use]').first.is_disabled()
 page.locator('#lab-trials').select_option('16');page.locator('#lab-form summary').click();page.locator('#lab-seed').fill('20261006');page.locator('#lab-start').click();page.wait_for_function("key=>JSON.parse(localStorage.getItem(key)).runs.at(-1).status==='completed'",arg=KEY,timeout=90000);assert page.evaluate('key=>JSON.parse(localStorage.getItem(key)).runs.length',KEY)==3
 # Native-style asynchronous flush locks all mutation controls through commit and cancellation drain.
 page.evaluate("""()=>{window.labPending=[];window.labHold=true;Storage.prototype.flush=async function(){if(window.labHold)await new Promise(resolve=>window.labPending.push(resolve));};}""")
 current_candidate=page.evaluate('key=>JSON.parse(localStorage.getItem(key)).runs.at(-1).candidate.digest',KEY)
 page.locator(f'[data-lab-select="{current_candidate}"]').click();page.wait_for_function('window.labPending.length===1');assert page.locator('#lab-start').is_disabled();page.locator('#lab-form').evaluate("form=>form.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))")
 page.evaluate('()=>{window.labHold=false;window.labPending.splice(0).forEach(resolve=>resolve());}')
 expect(page.locator('#lab-status')).to_contain_text('Version selected');expect(page.locator('#lab-start')).to_be_enabled();assert page.evaluate('key=>JSON.parse(localStorage.getItem(key)).runs.length',KEY)==3
 page.locator('#lab-rollback').click();expect(page.locator('#lab-start')).to_be_enabled()
 page.evaluate('()=>{window.labHold=true;window.labPending=[];}');page.locator('#lab-start').click();page.wait_for_function('window.labPending.length===1');page.locator('#lab-cancel').click();assert page.locator('#lab-start').is_disabled();page.locator('#lab-form').evaluate("form=>form.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))")
 page.evaluate('()=>{window.labHold=false;window.labPending.splice(0).forEach(resolve=>resolve());}');expect(page.locator('#lab-start')).to_be_enabled();assert page.evaluate('key=>JSON.parse(localStorage.getItem(key)).runs.length',KEY)==4;assert page.evaluate('key=>JSON.parse(localStorage.getItem(key)).runs.at(-1).status',KEY)=='cancelled'
 page.evaluate('()=>{delete Storage.prototype.flush;}')
 page.locator('#lab-import').click();page.locator('#lab-file').set_input_files({'name':'bad.json','mimeType':'application/json','buffer':b'{"digest":"wrong"}'});expect(page.locator('#lab-status')).to_contain_text('version')
 page.goto(BASE+'/circuits');expect(page.locator('h1')).to_have_text('The games end. The evidence stays.');page.locator('a[href="/circuits/launch-ttt-v1"]').first.click();expect(page.locator('.results-table tbody tr')).to_have_count(3,timeout=30000);expect(page.locator('.public-match-list a')).to_have_count(24);assert page.locator('.results-table tbody tr').first.inner_text().find('15.5')>=0
 page.screenshot(path=str(OUT/'circuit-desktop.png'),full_page=True);page.locator('.public-match-list a').first.click();expect(page.locator('#public-board span')).to_have_count(9);page.locator('#public-seek').fill('0');expect(page.locator('#public-outcome')).to_contain_text('to move');page.locator('#public-next').click();expect(page.locator('#public-ply')).to_contain_text('1 /');page.reload();expect(page.locator('#public-board span')).to_have_count(9);page.screenshot(path=str(OUT/'match-desktop.png'),full_page=True)
 page.locator('#public-arena').click();expect(page.locator('#arena')).to_be_visible();expect(page.locator('#start')).to_be_disabled();assert int(page.locator('#metric-moves').inner_text()) > 0
 for path in ['/developers','/circuits','/circuits/launch-ttt-v1','/agents/launch-ttt-v1/perfect-ttt-v1','/matches/launch-ttt-v1-01-0-0']:
  page.goto(BASE+path);expect(page.locator('h1')).to_be_visible();assert not page.locator('.public-error').count();assert page.locator('link[rel="canonical"]').get_attribute('href')=='https://builderwars.com'+path
  page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(250);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),path
  if path=='/circuits/launch-ttt-v1':expect(page.locator('.results-table tbody tr')).to_have_count(3);page.screenshot(path=str(OUT/'circuit-mobile.png'),full_page=True)
  if path.startswith('/matches/'):expect(page.locator('#public-board span')).to_have_count(9);page.screenshot(path=str(OUT/'match-mobile.png'),full_page=True)
 page.goto(BASE+'/developers');page.locator('[name="builder"]').fill('Test builder');page.locator('[name="agent"]').fill('Test starter');page.locator('[name="version"]').fill('v1');page.locator('[name="source"]').fill('https://github.com/nymrel/builderwars');page.locator('[name="assistance"]').fill('Legal moves; immediate tactics; no model calls')
 with page.expect_download() as download:page.locator('#contribution-form button').click()
 assert download.value.suggested_filename=='builderwars-contribution-draft.json';assert not calls,calls;assert not errors,errors
 static=browser.new_context(java_script_enabled=False,viewport={'width':320,'height':844});static_page=static.new_page()
 for path in ['/circuits/launch-ttt-v1','/agents/launch-ttt-v1/perfect-ttt-v1','/matches/launch-ttt-v1-01-0-0']:
  static_page.goto(BASE+path);expect(static_page.locator('h1')).to_be_visible();assert static_page.evaluate('document.documentElement.scrollWidth<=innerWidth'),path
 static.close()
 result={'status':'PASS','origin':BASE,'labGames':128,'seedBlocks':16,'incumbentRetained':True,'cancellation':'saved, no automatic restart','publicMatches':24,'publicContenders':3,'providerCalls':0,'browserErrors':errors}
 (OUT/'launch-verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));browser.close()
