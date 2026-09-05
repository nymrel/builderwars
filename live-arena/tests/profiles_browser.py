"""Configuration import/export and one-change draft comparison; no real inference."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get("BUILDERWARS_TEST_URL", "http://127.0.0.1:5178")
with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    errors, traffic = [], []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.route("https://openrouter.ai/**", lambda r: (traffic.append(r.request.url), r.abort()))
    page.goto(BASE)
    page.locator("#connections").click()
    page.locator("#agent-kind").select_option("bot")
    page.locator("#agent-name").fill("Edited draft")
    if not page.locator("#connection-advanced").evaluate("el => el.open"):
        page.locator("#connection-advanced > summary").click()
    page.locator("#strategy").fill("Draft strategy")
    page.locator("#agent-key").evaluate("el => el.value = 'PRIVATE_KEY_SENTINEL'")
    page.locator("#harness-url").evaluate("el => el.value = 'https://PRIVATE_ENDPOINT.example'")
    with page.expect_download() as result:
        page.locator("#export-agent").click()
    exported = json.loads(Path(result.value.path()).read_text())
    assert exported["agent"]["name"] == "Edited draft"
    assert exported["agent"]["strategy"] == "Draft strategy"
    assert "PRIVATE" not in json.dumps(exported)
    # Import is a draft edit only; rejection and cancellation preserve existing fields.
    def upload(value):
        page.locator("#profile-file").set_input_files({"name": "profile.json", "mimeType": "application/json", "buffer": json.dumps(value).encode()})
    upload({**exported, "key": "UNTRUSTED"})
    expect(page.locator("#dialog-status")).to_contain_text("unexpected fields")
    expect(page.locator("#agent-name")).to_have_value("Edited draft")
    page.once("dialog", lambda d: d.dismiss())
    upload(exported)
    expect(page.locator("#agent-key")).to_have_value("PRIVATE_KEY_SENTINEL")
    page.once("dialog", lambda d: d.accept())
    upload(exported)
    expect(page.locator("#dialog-status")).to_contain_text("imported into this draft")
    expect(page.locator("#agent-key")).to_have_value("")
    expect(page.locator("#harness-url")).to_have_value("")
    assert page.locator("#metric-moves").inner_text() == "0"
    # Save the baseline; edit exactly one setting, then two. Comparison never prints strategy.
    page.locator("#agent-form button[type=submit]").click()
    page.locator("#connections").click()
    if not page.locator("#connection-advanced").evaluate("el => el.open"):
        page.locator("#connection-advanced > summary").click()
    expect(page.locator("#profile-comparison")).to_contain_text("No behavior settings changed")
    page.locator("#bot-model").select_option("random")
    expect(page.locator("#profile-comparison")).to_contain_text("1 setting changed")
    page.locator("#strategy").fill("PRIVATE_STRATEGY_SENTINEL")
    expect(page.locator("#profile-comparison")).to_contain_text("2 settings changed")
    assert "PRIVATE_STRATEGY" not in page.locator("#profile-comparison").inner_text()
    page.locator("#close-dialog").click()
    page.locator("#step").click()
    expect(page.locator("#metric-moves")).to_have_text("1")
    page.locator("#connections").click()
    page.locator("#bot-model").select_option("random")
    page.once("dialog", lambda d: d.dismiss())
    page.locator("#agent-form button[type=submit]").click()
    expect(page.locator("#metric-moves")).to_have_text("1")
    assert page.locator("#agent-dialog").evaluate("el => el.open")
    page.once("dialog", lambda d: d.accept())
    page.locator("#agent-form button[type=submit]").click()
    expect(page.locator("#metric-moves")).to_have_text("0")
    page.locator("#connections").click()
    # An imported unsupported model/effort remains visible, not silently mapped or connected.
    remote = {"schema": "builderwars.agent-profile.v1", "agent": {"name": "Remote draft", "kind": "openrouter", "model": "unknown/model", "effort": "unsupported", "strategy": ""}}
    page.once("dialog", lambda d: d.accept())
    upload(remote)
    expect(page.locator("#dialog-status")).to_contain_text("imported into this draft")
    expect(page.locator("#model-id")).to_have_value("unknown/model")
    if not page.locator("#model-options").evaluate("el => el.open"):
        page.locator("#model-options > summary").click()
    expect(page.locator("#effort")).to_have_value("unsupported")
    assert not traffic
    page.locator("#agent-form button[type=submit]").click()
    expect(page.locator("#dialog-status")).to_contain_text("Add your OpenRouter key")
    assert not traffic and not errors
    context.close()
    browser.close()
print("PASS: draft export, strict import, cancellation, secret clearing, comparison and no-request remote import")
