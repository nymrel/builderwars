"""Official JS plugin dispatch with synthetic cache/share responses, NOT device proof."""
import base64
import json
import os
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = os.environ["BUILDERWARS_TEST_URL"]
OUT = Path(__file__).parents[1] / "output" / "playwright" / "native-files"
OUT.mkdir(parents=True, exist_ok=True)
BRIDGE = """(() => {
  const listeners = new Map(), cache = new Map(), checkpoints = new Map();
  window.androidBridge = {};
  window.__files = { ready:false, calls:[], shares:[], outcome:'closed', cache,
    emit:(event,value)=>listeners.get(event)?.(value) };
  window.Capacitor = {
    PluginHeaders: [
      {name:'App',methods:[{name:'addListener',rtype:'callback'},
        {name:'removeListener',rtype:'promise'},{name:'getState',rtype:'promise'}]},
      {name:'Filesystem',methods:['mkdir','readdir','readFile','writeFile','rename','deleteFile'].map(name=>({name,rtype:'promise'}))},
      {name:'Share',methods:[{name:'share',rtype:'promise'}]}],
    nativeCallback:(plugin,method,options,callback)=>{
      if(plugin!=='App'||method!=='addListener') throw Error('Unexpected callback');
      listeners.set(options.eventName,callback); return options.eventName;
    },
    nativePromise:async(plugin,method,options)=>{
      __files.calls.push({plugin,method,options});
      if(plugin==='App') {
        if(method==='getState'){__files.ready=true;return {isActive:true};}
        if(method==='removeListener'){listeners.delete(options.eventName);return;}
      }
      if(plugin==='Filesystem') {
        if(options.directory==='DATA') {
          const name=options.path?.split('/').at(-1);
          if(method==='mkdir') return {};
          if(method==='readdir') return {files:[...checkpoints].map(([name,data])=>({name,type:'file',size:new TextEncoder().encode(data).byteLength}))};
          if(method==='readFile') {if(!checkpoints.has(name)) throw Error('Missing'); return {data:checkpoints.get(name)};}
          if(method==='writeFile') {checkpoints.set(name,options.data);return {};}
          if(method==='deleteFile') {checkpoints.delete(name);return {};}
          if(method==='rename') {const from=options.from.split('/').at(-1);checkpoints.set(options.to.split('/').at(-1),checkpoints.get(from));checkpoints.delete(from);return {};}
          throw Error('Unexpected checkpoint operation');
        }
        if(options.directory!=='CACHE') throw Error('Unexpected directory');
        if(method==='mkdir') return;
        if(method==='readdir') return {files:[...cache].map(([path,data])=>({
          name:path.split('/').pop(),type:'file',size:atob(data).length,mtime:Date.now()}))};
        if(method==='writeFile'){
          if(__files.outcome==='write-error') throw Error('Synthetic write failure');
          cache.set(options.path,options.data);
          if(__files.outcome==='hold-write') await new Promise(resolve=>__files.finishWrite=resolve);
          return {uri:'file:///cache/'+options.path};
        }
        if(method==='deleteFile'){cache.delete(options.path);return;}
      }
      if(plugin==='Share'&&method==='share') {
        __files.shares.push(options);
        if(__files.outcome==='cancel') throw Error('Share canceled');
        if(__files.outcome==='error') throw Error('Ambiguous synthetic share error');
        if(__files.outcome==='hold') await new Promise(resolve=>__files.release=resolve);
        return {};
      }
      throw Error('Unexpected native call '+plugin+'/'+method);
    }
  };
})()"""

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={"width": 390, "height": 844})
    context.add_init_script(BRIDGE)
    page = context.new_page()
    errors, downloads = [], []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("download", lambda d: downloads.append(d))
    page.goto(BASE)
    page.wait_for_function("() => __files.ready")
    expect(page.locator("#library-status")).to_contain_text("Games save after each accepted move")

    def share(selector):
        count = page.evaluate("__files.shares.length")
        page.locator(selector).click()
        page.wait_for_function("count=>__files.shares.length>count", arg=count)
        expect(page.locator("#notice")).to_contain_text("Share sheet closed")
        return page.evaluate("__files.shares.at(-1)")

    def contents(receipt):
        path = receipt["files"][0].removeprefix("file:///cache/")
        return base64.b64decode(page.evaluate("path=>__files.cache.get(path)", path))

    page.locator("[data-game=connect4]").click()
    for seat in (0, 1):
        page.locator(f"[data-seat='{seat}']").click()
        page.locator("#agent-kind").select_option("human")
        if not page.locator("#connection-advanced").evaluate("el => el.open"):
            page.locator("#connection-advanced > summary").click()
        page.locator("#strategy").fill("PRIVATE_STRATEGY")
        page.locator("#agent-form button[type=submit]").click()
    for ply, cell in enumerate((0, 1, 0, 1, 0, 1, 0), 1):
        page.locator(f"[data-cell='{cell}']").click()
        expect(page.locator("#metric-moves")).to_have_text(str(ply))
    expect(page.locator("#match-status")).to_contain_text("wins")
    page.locator("#match-proof summary").click()
    proof = contents(share("#export-proof"))
    assert b"PRIVATE_STRATEGY" not in proof
    verifier = contents(share("#download-verifier"))
    proof_path, verifier_path = OUT / "match.jsonl", OUT / "verifier.mjs"
    proof_path.write_bytes(proof)
    verifier_path.write_bytes(verifier)
    checked = json.loads(subprocess.check_output(["node", str(verifier_path), str(proof_path)], text=True, timeout=10))
    assert checked["verified"] and checked["complete"] and checked["winner"] == 0
    assert not checked["model_attested"] and not checked["execution_attested"]
    summary = page.locator(".match-settings summary").filter(has_text="Match settings")
    summary.click()
    package = contents(share("#export-package"))
    assert b"PRIVATE_STRATEGY" not in package
    legacy = json.loads(contents(share("#export")))
    assert len(legacy["events"]) == 7
    assert contents(share("#result-image")).startswith(b"\x89PNG\r\n\x1a\n")
    assert "#replay=" in share("#copy-caption")["text"]
    assert "PRIVATE_STRATEGY" not in page.evaluate("__files.shares.at(-1).text")
    page.locator("#connections").click()
    if not page.locator("#connection-advanced").evaluate("el => el.open"):
        page.locator("#connection-advanced > summary").click()
    profile = contents(share("#export-agent"))
    assert json.loads(profile)["agent"]["strategy"] == "PRIVATE_STRATEGY"
    page.locator("#close-dialog").click()
    page.locator("nav [data-tab=forge]").click()
    rules = json.loads(contents(share("#export-rules")))
    assert rules["kind"] == "custom"
    page.locator("nav [data-tab=evals]").click()
    evaluation = json.loads(contents(share("#export-series")))
    assert "matchPackages" in evaluation
    page.locator("nav [data-tab=arena]").click()

    # Cancellation removes only its file. Ambiguous native failure retains handoff bytes.
    before = page.evaluate("__files.cache.size")
    page.evaluate("__files.outcome='cancel'")
    page.locator("#export-package").click()
    expect(page.locator("#notice")).to_contain_text("Sharing cancelled")
    assert page.evaluate("__files.cache.size") == before
    page.evaluate("__files.outcome='error'")
    page.locator("#export-package").click()
    expect(page.locator("#notice")).to_contain_text("could not confirm a handoff")
    assert page.evaluate("__files.cache.size") == before + 1
    page.evaluate("__files.outcome='write-error'")
    share_count = page.evaluate("__files.shares.length")
    page.locator("#export-package").click()
    expect(page.locator("#notice")).to_contain_text("Could not prepare")
    assert page.evaluate("__files.shares.length") == share_count
    page.evaluate("__files.outcome='hold'")
    page.locator("#export-package").click()
    page.wait_for_function("() => typeof __files.release==='function'")
    page.locator("#export").click()
    expect(page.locator("#notice")).to_contain_text("Finish the current export")
    assert page.evaluate("__files.shares.length") == share_count + 1
    page.evaluate("__files.release(); __files.outcome='closed'")
    expect(page.locator("#notice")).to_contain_text("Share sheet closed")
    before = page.evaluate("__files.cache.size")
    share_count = page.evaluate("__files.shares.length")
    page.evaluate("__files.outcome='hold-write'")
    page.locator("#export-package").click()
    page.wait_for_function("() => typeof __files.finishWrite==='function'")
    page.evaluate("__files.emit('pause'); __files.emit('appStateChange',{isActive:true}); __files.finishWrite()")
    expect(page.locator("#notice")).to_contain_text("backgrounded during preparation")
    assert page.evaluate("__files.shares.length") == share_count
    assert page.evaluate("__files.cache.size") == before
    assert not downloads, "Native exports must not fall back to browser anchor downloads"

    # Native-produced bytes import in a clean web context and round-trip unchanged.
    web_context = browser.new_context(viewport={"width": 320, "height": 780})
    web = web_context.new_page()
    web.goto(BASE)
    web.locator("#import").set_input_files({"name":"match.json", "mimeType":"application/json", "buffer":package})
    expect(web.locator("#notice")).to_contain_text("Every move verified")
    web.locator(".match-settings summary").filter(has_text="Match settings").click()
    with web.expect_download() as exported:
        web.locator("#export-package").click()
    assert json.loads(Path(exported.value.path()).read_bytes()) == json.loads(package)
    web.locator("#match-proof summary").click()
    web.locator("#import-proof").set_input_files(proof_path)
    expect(web.locator("#proof-status")).to_contain_text("7 plies reproduced")
    assert not errors, errors
    browser.close()
print("PASS: synthetic native profile/replay/package/proof/verifier/PNG/rules/eval/text sharing, failure/concurrency, clean web import. Not OS share-sheet or physical-device acceptance.")
