"""Synthetic Capacitor event bridge against bundled assets; NOT device acceptance."""
import os
from playwright.sync_api import sync_playwright, expect
from android_emulator_smoke import recovery_snapshot

BASE = os.environ["BUILDERWARS_TEST_URL"]
BRIDGE = """() => {
  const listeners = new Map();
  const files = new Map(JSON.parse(sessionStorage.getItem('synthetic-checkpoint-files') || '[]'));
  const persist = () => sessionStorage.setItem('synthetic-checkpoint-files', JSON.stringify([...files]));
  window.androidBridge = {}; // Select actual Capacitor Android JS dispatch path.
  window.__native = { ready: false, files, holdSave: false, saveWaiting: false, failWrite: false,
    releaseSave: () => {}, emit: (name, value) => listeners.get(name)?.(value) };
  window.Capacitor = {
    PluginHeaders: [{ name: 'App', methods: [
      {name:'addListener',rtype:'callback'}, {name:'removeListener',rtype:'promise'},
      {name:'getState',rtype:'promise'}] }, {name:'Filesystem', methods:
      ['mkdir','readdir','readFile','writeFile','rename','deleteFile'].map(name => ({name,rtype:'promise'}))}],
    nativeCallback: (plugin, method, options, callback) => {
      if (plugin !== 'App' || method !== 'addListener') throw Error('Unexpected native call');
      listeners.set(options.eventName, callback); return options.eventName;
    },
    nativePromise: async (plugin, method, options) => {
      if (plugin === 'Filesystem') {
        if (options.directory !== 'DATA') throw Error('Unexpected storage directory');
        if (method === 'mkdir') return {};
        if (method === 'readdir') return {files:[...files].map(([name,data]) => ({name,type:'file',size:new TextEncoder().encode(data).byteLength}))};
        const name = options.path?.split('/').at(-1);
        if (method === 'readFile') { if (!files.has(name)) throw Error('Missing'); return {data:files.get(name)}; }
        if (method === 'writeFile') { if (__native.failWrite) throw Error('Synthetic disk full'); files.set(name,options.data); persist(); return {}; }
        if (method === 'deleteFile') { files.delete(name); persist(); return {}; }
        if (method === 'rename') {
          if (__native.holdSave) { __native.saveWaiting = true; await new Promise(resolve => { __native.releaseSave = resolve; }); __native.saveWaiting = false; }
          const from = options.from.split('/').at(-1), to = options.to.split('/').at(-1);
          files.set(to,files.get(from)); files.delete(from); persist(); return {};
        }
        throw Error('Unexpected filesystem method');
      }
      if (plugin !== 'App') throw Error('Unexpected native plugin');
      if (method === 'getState') { window.__native.ready = true; return {isActive:true}; }
      if (method === 'removeListener') { listeners.delete(options.eventName); return; }
      throw Error('Unexpected native method');
    }
  };
}"""
with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={"width": 390, "height": 844})
    context.add_init_script(f"({BRIDGE})()")
    page = context.new_page()
    errors, calls, held = [], [], []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.route("https://openrouter.ai/api/v1/models", lambda r: r.fulfill(json={"data": [{"id":"test/native", "name":"Synthetic native"}]}))
    page.route("https://openrouter.ai/api/v1/key", lambda r: r.fulfill(json={"data":{"is_free_tier":True}}))
    def move(route):
        calls.append(route.request.post_data_json)
        if len(calls) == 1: held.append(route)
        else: route.fulfill(json={"choices":[{"message":{"content":'{"move":"0"}'}}], "model":"test/native"})
    page.route("https://openrouter.ai/api/v1/chat/completions", move)
    page.goto(BASE)
    page.wait_for_function("window.__native.ready")
    policy = page.locator('meta[http-equiv="Content-Security-Policy"]').get_attribute("content")
    assert "script-src 'self'" in policy and "127.0.0.1" not in policy
    page.locator("[data-game=connect4]").click()
    page.locator("#connections").click()
    page.locator("#agent-kind").select_option("openrouter")
    page.locator("#model-id option").first.wait_for(state="attached")
    page.locator("#agent-key").fill("synthetic-native-key")
    page.locator("#agent-form button[type=submit]").click()
    with page.expect_request("**/chat/completions"):
        page.locator("#step").click()
    page.evaluate("__native.emit('pause'); __native.emit('appStateChange', {isActive:false})")
    expect(page.locator("#match-status")).to_have_text("Paused when app left foreground")
    expect(page.locator("#metric-moves")).to_have_text("0")
    if held:
        try: held[0].fulfill(json={"choices":[{"message":{"content":'{"move":"0"}'}}]})
        except Exception: pass  # The browser may already have completed the abort.
    page.locator("#step").click()
    expect(page.locator("#notice")).to_contain_text("lifecycle protection is not ready")
    assert len(calls) == 1
    page.evaluate("__native.emit('appStateChange', {isActive:true})")
    expect(page.locator("#notice")).to_contain_text("resumed paused")
    expect(page.locator("#metric-moves")).to_have_text("0")
    assert len(calls) == 1
    page.locator("#step").click()
    expect(page.locator("#metric-moves")).to_have_text("1")
    assert len(calls) == 2
    page.evaluate("__native.emit('pause')")
    assert page.evaluate("Object.values(localStorage).every(v => !v.includes('synthetic-native-key'))")
    page.evaluate("__native.emit('appStateChange', {isActive:true})")
    page.locator("#connections").click()
    page.locator("#agent-kind").select_option("harness")
    page.locator("#harness-url").fill("http://127.0.0.1:8765/move")
    page.locator("#harness-model").fill("test")
    page.locator("#check-connection").click()
    expect(page.locator("#dialog-status")).to_contain_text("desktop localhost bridge is not available")
    assert not errors
    context.close()

    # Held file promotion is deterministic: no timer/sleep or provider involved.
    context = browser.new_context(viewport={"width": 390, "height": 844})
    context.add_init_script(f"({BRIDGE})()")
    page = context.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(BASE)
    page.wait_for_function("window.__native.ready")
    page.locator("[data-game=tictactoe]").click()
    page.evaluate("__native.holdSave = true")
    page.locator("#step").click()
    page.wait_for_function("__native.saveWaiting")
    expect(page.locator("#metric-moves")).to_have_text("0")
    expect(page.locator("#step")).to_be_disabled()
    page.evaluate("__native.emit('pause'); __native.emit('appStateChange',{isActive:true})")
    expect(page.locator("#step")).to_be_disabled()
    page.evaluate("__native.holdSave = false; __native.releaseSave()")
    expect(page.locator("#metric-moves")).to_have_text("1")
    expect(page.locator("#match-status")).to_have_text("Paused when app left foreground")
    page.locator("#step").click()
    expect(page.locator("#metric-moves")).to_have_text("2")
    trace = recovery_snapshot(page)
    assert trace["storageBackend"] == "native-checkpoint" and trace["storedEntries"] == [{"plies": 2}]
    page.reload()
    page.wait_for_function("window.__native.ready")
    expect(page.locator("#metric-moves")).to_have_text("0")
    page.locator("#match-library").evaluate("el => el.open = true")
    page.locator("[data-saved-resume]").click()
    expect(page.locator("#metric-moves")).to_have_text("2")
    page.evaluate("__native.holdSave = true")
    page.locator("#step").click()
    page.wait_for_function("__native.saveWaiting")
    page.locator("#reset").click()
    page.evaluate("__native.holdSave = false; __native.releaseSave()")
    expect(page.locator("#step")).to_be_enabled()
    expect(page.locator("#metric-moves")).to_have_text("0")
    page.evaluate("__native.failWrite = true")
    page.locator("#step").click()
    expect(page.locator("#metric-moves")).to_have_text("1")
    expect(page.locator("#notice")).to_contain_text("device saving failed")
    page.evaluate("__native.failWrite = false")
    page.once("dialog", lambda dialog: dialog.accept())
    page.locator("#forget-matches").click()
    expect(page.locator("#save-matches")).not_to_be_checked()
    expect(page.locator("[data-saved-resume]")).to_have_count(0)
    assert recovery_snapshot(page)["storedEntries"] == []
    page.reload()
    page.wait_for_function("window.__native.ready")
    expect(page.locator("#save-matches")).not_to_be_checked()
    expect(page.locator("[data-saved-resume]")).to_have_count(0)
    assert not errors
    context.close()
    browser.close()
print("PASS: packaged CSP, synthetic native lifecycle, acknowledged saves, restart, stale-move isolation, disk failure and forget. No device or provider certified.")
