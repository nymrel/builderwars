"""Slow file reads must not overwrite a new match, newer import or edited rules draft."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = os.environ["BUILDERWARS_TEST_URL"]
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.add_init_script("""(() => {
      const original = File.prototype.arrayBuffer;
      window.__reads = [];
      File.prototype.arrayBuffer = async function() {
        if (this.name.startsWith('slow')) await new Promise(resolve=>__reads.push(resolve));
        return original.call(this);
      };
    })()""")
    page.goto(BASE)
    page.locator("[data-game=connect4]").click()
    page.locator("#step").click()
    expect(page.locator("#metric-moves")).to_have_text("1")
    page.locator(".match-settings summary").filter(has_text="Match settings").click()
    with page.expect_download() as pending:
        page.locator("#export-package").click()
    package = Path(pending.value.path()).read_bytes()

    def upload(selector, name, payload):
        page.locator(selector).set_input_files({"name":name, "mimeType":"application/json", "buffer":payload})

    upload("#import", "slow-match.json", package)
    page.wait_for_function("() => __reads.length===1")
    page.locator("#reset").click()
    page.evaluate("__reads.shift()()")
    expect(page.locator("#notice")).to_contain_text("match changed during import")
    expect(page.locator("#metric-moves")).to_have_text("0")
    assert page.locator("#import").input_value() == ""

    upload("#import", "slow-old.json", package)
    page.wait_for_function("() => __reads.length===1")
    newer = json.loads(package)
    newer["record"]["id"] = "newer-import"
    upload("#import", "newer.json", json.dumps(newer).encode())
    expect(page.locator("#notice")).to_contain_text("Every move verified")
    page.evaluate("__reads.shift()()")
    expect(page.locator("#notice")).to_contain_text("match changed during import")
    with page.expect_download() as current:
        page.locator("#export-package").click()
    assert json.loads(Path(current.value.path()).read_bytes())["record"]["id"] == "newer-import"
    page.locator("#import").set_input_files([])
    expect(page.locator("#metric-moves")).to_have_text("1")

    page.locator("nav [data-tab=watch]").click()
    page.locator("#leave-watch").click()
    page.locator("nav [data-tab=forge]").click()
    rules = json.dumps({"kind":"custom","name":"Imported rules","rows":6,"cols":7,"connect":4,"gravity":True}).encode()
    upload("#import-rules", "slow-rules.json", rules)
    page.wait_for_function("() => __reads.length===1")
    page.locator("#creator-name").fill("Keep my edited draft")
    page.evaluate("__reads.shift()()")
    expect(page.locator("#notice")).to_contain_text("rules draft changed during import")
    expect(page.locator("#game-title")).to_have_text("Connect Four")
    expect(page.locator("#creator-name")).to_have_value("Keep my edited draft")
    upload("#import", "invalid-utf8.json", b'{"bad":"\xff"}')
    expect(page.locator("#notice")).to_contain_text("encoded data")
    expect(page.locator("#metric-moves")).to_have_text("0")
    browser.close()
print("PASS: delayed match/rules reads, superseding imports, cancelled picker, invalid UTF-8 preserve newer state.")
