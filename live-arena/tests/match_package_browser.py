"""Public attribution survives export, recovery and seat swaps; no provider calls."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get("BUILDERWARS_TEST_URL", "http://127.0.0.1:5178")
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 390, "height": 844})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(BASE)

    def settings():
        summary = page.locator(".match-settings summary").filter(has_text="Match settings")
        if not summary.evaluate("el => el.parentElement.open"):
            summary.click()

    def export(selector="#export-package"):
        if selector == "#export-package":
            settings()
        with page.expect_download() as pending:
            page.locator(selector).click()
        return json.loads(Path(pending.value.path()).read_text())

    def upload(value):
        page.locator("#import").set_input_files({"name": "match.package.json", "mimeType": "application/json", "buffer": json.dumps(value).encode()})

    for seat, name in [(0, "alpha"), (1, "beta")]:
        page.locator(f"[data-seat='{seat}']").click()
        if not page.locator("#connection-advanced").evaluate("el => el.open"):
            page.locator("#connection-advanced > summary").click()
        page.locator("#declaration-fields").evaluate("el => el.open = true")
        page.locator("#declaration-builderId").fill("our-builder")
        page.locator("#declaration-agentId").fill(name)
        page.locator("#declaration-agentRevision").fill("r1")
        page.locator("#declaration-harnessId").fill(f"harness-{name}")
        page.locator("#declaration-harnessRevision").fill("abc123")
        page.locator("#strategy").fill("PRIVATE_STRATEGY")
        page.locator("#agent-form button[type=submit]").click()
    page.locator("[data-game=connect4]").click()
    settings()
    page.locator("#move-limit").fill("4")
    page.locator("#max-tokens").fill("512")
    page.locator("#step").click()
    expect(page.locator("#metric-moves")).to_have_text("1")
    # Closed dialog edits are drafts, not retrospective metadata changes.
    page.locator("#connections").click()
    if not page.locator("#connection-advanced").evaluate("el => el.open"):
        page.locator("#connection-advanced > summary").click()
    if not page.locator("#declaration-fields").evaluate("el => el.open"):
        page.locator("#declaration-fields > summary").click()
    page.locator("#declaration-agentRevision").fill("r2")
    page.locator("#close-dialog").click()
    pkg = export()
    assert pkg["declarations"][0]["agentRevision"] == "r1"
    assert pkg["declarations"][0]["providerId"] is None
    assert pkg["resources"] == {"moveLimit": 4, "maxTokens": 512, "moveLimitKnown": True}
    assert "PRIVATE" not in json.dumps(pkg)
    assert pkg["verification"]["identityAttested"] is False
    # Recovery retains frozen declarations and limits, and remains paused.
    page.reload()
    page.locator("#match-library summary").click()
    page.locator("[data-saved-resume]").first.click()
    expect(page.locator("#metric-moves")).to_have_text("1")
    recovered = export()
    assert recovered["declarations"] == pkg["declarations"]
    assert recovered["resources"] == pkg["resources"]
    # Paired series swaps attribution with its contender and captures each game.
    settings()
    page.locator("#move-limit").fill("2")
    page.locator("#pace").select_option("100")
    page.locator("nav [data-tab=evals]").click()
    page.locator("#run-series").click()
    page.wait_for_function("() => document.querySelector('#series-results').textContent.includes('2 / 2 attempts recorded')")
    page.locator("nav [data-tab=evals]").click()
    series = export("#export-series")
    assert [[d["agentId"] for d in game["declarations"]] for game in series["matchPackages"]] == [["alpha", "beta"], ["beta", "alpha"]]
    # Imported package and saved replay preserve metadata without connecting agents.
    page.locator("nav [data-tab=arena]").click()
    upload(pkg)
    expect(page.locator("#notice")).to_contain_text("Every move verified")
    assert export()["declarations"] == pkg["declarations"]
    # Explicit unknown recovery limits are distinct from absent legacy metadata.
    unknown = {**pkg, "resources": {"moveLimit": 80, "maxTokens": None, "moveLimitKnown": False}}
    upload(unknown)
    page.reload()
    page.locator("#match-library summary").click()
    page.locator("[data-saved-replay]").first.click()
    assert export()["resources"] == unknown["resources"]
    page.reload()
    page.locator("#match-library summary").click()
    page.locator("[data-saved-replay]").first.click()
    assert export()["declarations"] == pkg["declarations"]
    # Legacy import does not inherit a previous contender's attribution or budgets.
    upload(pkg["record"])
    legacy = export()
    assert legacy["resources"] is None
    assert all(v is None for d in legacy["declarations"] for v in d.values())
    # Invalid claim cannot replace the current replay.
    upload({**pkg, "verification": {**pkg["verification"], "modelAttested": True}})
    expect(page.locator("#notice")).to_contain_text("Unsupported verifier or attestation")
    assert export()["resources"] is None
    assert not errors, errors
    browser.close()
print("Match package browser journey passed")
