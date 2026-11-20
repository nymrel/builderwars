"""Primary-source discovery, scoped rankings and free competition transitions."""
import json,os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
BASE=os.environ['BUILDERWARS_TEST_URL']
OUT=Path(os.environ.get('BUILDERWARS_EVAL_ARTIFACTS','output/playwright/evals'));OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch();context=browser.new_context(viewport={'width':1440,'height':1000});page=context.new_page();errors=[];provider=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('request',lambda r:provider.append(r.url) if 'chat/completions' in r.url or r.url.endswith('/move') else None)
 page.goto(BASE+'/evals');expect(page.locator('.eval-card')).to_have_count(50)
 page.screenshot(path=str(OUT/'directory-desktop.png'),full_page=True)
 page.locator('[data-eval-category]').select_option('tools');page.locator('[data-eval-search]').fill('function')
 expect(page.locator('.eval-card')).to_have_count(1);page.locator('[data-shortlist="bfcl"]').click()
 page.reload();expect(page.locator('[data-shortlist="bfcl"]')).to_have_attribute('aria-pressed','true')
 with page.expect_download() as dl:page.locator('[data-plan-export]').click()
 plan=json.loads(Path(dl.value.path()).read_bytes());assert plan['evaluations'][0]['id']=='bfcl';assert plan['model']['provider'] is None;assert 'Not executed' in plan['execution']
 page.locator('[data-plan-clear]').click();expect(page.locator('[data-plan-export]')).to_be_disabled()
 page.locator('[data-eval-search]').fill('not-an-eval');expect(page.locator('.eval-empty')).to_be_visible();page.locator('[data-eval-reset]').click();expect(page.locator('.eval-card')).to_have_count(50)
 for button in page.locator('[data-shortlist]').all()[:13]:button.click()
 expect(page.locator('[data-plan-count]')).to_have_text('12 in your plan');expect(page.locator('[data-plan-status]')).to_contain_text('up to 12')
 page.goto(BASE+'/evals/swe-bench-verified/');expect(page.locator('h1')).to_have_text('SWE-bench Verified');expect(page.locator('.eval-detail-rankings article')).to_have_count(2)
 page.goto(BASE+'/rankings?board=bfcl-v4');expect(page.locator('.eval-ranking-table tbody tr')).to_have_count(10)
 name=page.locator('.eval-ranking-table tbody tr').nth(2).locator('strong').first.inner_text();page.locator('[data-ranking-search]').fill(name)
 expect(page.locator('.eval-ranking-table tbody tr').first.locator('td').first).to_have_text('3')
 page.locator('[data-ranking-search]').fill('');page.locator('[data-ranking-more]').click();assert page.locator('.eval-ranking-table tbody tr').count()>100
 with page.expect_download() as dl:page.locator('[data-ranking-download]').click()
 snapshot=json.loads(Path(dl.value.path()).read_bytes());assert snapshot['id']=='bfcl-v4';assert snapshot['sourceSha256'];assert snapshot['rows'][2]['rank']==3
 page.locator('[data-ranking-board]').select_option('swe-mini');expect(page.locator('.eval-ranking-table')).to_contain_text('Harness version')
 page.locator('[data-ranking-board]').select_option('livecodebench');expect(page.locator('.ranking-context')).to_contain_text('placeholders');expect(page.locator('.eval-ranking-table')).not_to_contain_text('released before window')
 page.screenshot(path=str(OUT/'rankings-desktop.png'),full_page=True)
 for track in ('tau3-banking','tau3-voice','tau2-text'):page.locator('[data-ranking-board]').select_option(track);expect(page.locator('.eval-ranking-table tbody tr')).to_have_count(3)
 for width in (320,390,768):
  page.set_viewport_size({'width':width,'height':844})
  for path in ('/evals','/rankings','/compete','/evals/arc-agi-3'):
   page.goto(BASE+path);expect(page.locator('h1')).to_be_visible();assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(path,width)
   assert page.locator('.public-nav').bounding_box()['y']+page.locator('.public-nav').bounding_box()['height']<page.locator('h1').bounding_box()['y'],(path,width,'navigation overlaps heading')
   if width==390:page.screenshot(path=str(OUT/(path.replace('/','-').strip('-')+'-mobile.png')),full_page=True)
 page.set_viewport_size({'width':1440,'height':1000});page.goto(BASE+'/compete');expect(page.locator('.challenge-card')).to_have_count(8)
 for challenge,title in (('connect4-sprint','Connect Four'),('nim-duel','Nim'),('oracle-duel','Tic-tac-toe'),('daily-board',None)):
  page.goto(BASE+'/#challenge='+challenge);expect(page.locator('#arena')).to_be_visible();expect(page.locator('#metric-moves')).to_have_text('0')
  if title:expect(page.locator('#game-title')).to_have_text(title)
  else:expect(page.locator('#game-title')).to_contain_text('Daily board')
  assert page.url.endswith('#arena');assert page.locator('#board').bounding_box()['y']<1000
 # Actual legal move, then cancelled challenge must preserve match and route.
 page.goto(BASE+'/#challenge=nim-duel');page.locator('[data-cell="0"]').click()
 expect(page.locator('#metric-moves')).to_have_text('1');page.once('dialog',lambda d:d.dismiss());page.evaluate("location.hash='challenge=oracle-duel'")
 expect(page.locator('#metric-moves')).to_have_text('1');expect(page.locator('#game-title')).to_have_text('Nim');page.wait_for_function("location.hash==='#arena'")
 page.goto(BASE+'/#board-evaluation');expect(page.locator('#eval-discovery .eval-card')).to_have_count(50)
 page.wait_for_function("document.activeElement===document.querySelector('#board-evaluation h2')")
 assert page.locator('#board-evaluation').bounding_box()['y']<1000
 page.once('dialog',lambda d:d.accept());page.goto(BASE+'/#challenge=mirror-match');expect(page.locator('#series-length')).to_have_value('4');page.wait_for_function("document.activeElement===document.querySelector('#board-evaluation h2')")
 expect(page.locator('#metric-moves')).to_have_text('0');page.locator('#run-series').click();page.evaluate("location.hash='challenge=nim-duel'");expect(page.locator('#notice')).to_contain_text('Pause or finish');page.wait_for_function("location.hash==='#arena'");expect(page.locator('#series-length')).to_have_value('4')
 expect(page.locator('#series-results')).to_contain_text('4 / 4 attempts recorded',timeout=60000);expect(page.locator('#series-results')).to_contain_text('Series not running')
 page.locator('nav [data-tab=evals]').click();page.locator('[data-board-eval-scroll]').click()
 with page.expect_download() as dl:page.locator('#export-series').click()
 series=json.loads(Path(dl.value.path()).read_bytes());assert series['requestedGames']==4 and len(series['games'])==4 and not series['inProgress']
 assert not provider,provider;assert not errors,errors
 static=browser.new_context(java_script_enabled=False);s=static.new_page()
 for path in ('/evals','/rankings','/compete','/evals/swe-bench-verified'):
  s.goto(BASE+path);expect(s.locator('h1')).to_be_visible();assert s.locator('link[rel=canonical]').get_attribute('href')=='https://builderwars.com'+path
 s.goto(BASE+'/evals');expect(s.locator('.eval-card')).to_have_count(50)
 result={'status':'PASS','origin':BASE,'directoryEntries':50,'rankingTracks':14,'freeSeriesGames':4,'providerCalls':0,'browserErrors':errors}
 (OUT/'eval-verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));browser.close()
