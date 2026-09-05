"""Record one actual free built-in match, without selecting or replacing its outcome.

Optional manual artifact capture, not a CI requirement. No model credentials/calls.
Run against the built local preview. Outputs are QA/demo, not external user evidence.
"""
import hashlib
import json
import os
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parents[1]
BASE = os.environ.get("BUILDERWARS_TEST_URL", "http://127.0.0.1:5178").rstrip("/")
OUT = ROOT / "output" / "playwright" / "free-demo"
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(
        viewport={"width": 1440, "height": 1080},
        record_video_dir=str(OUT), record_video_size={"width": 1440, "height": 1080},
        permissions=["clipboard-read", "clipboard-write"],
    )
    page = context.new_page()
    video = page.video
    requests = []
    context.route("https://openrouter.ai/**", lambda route: (requests.append(route.request.url), route.abort()))
    page.goto(BASE)
    page.locator("#board .cell").first.wait_for()
    page.locator("[data-game=connect4]").click()
    page.locator("#quickplay").click()
    page.wait_for_function("() => /wins|draw/i.test(document.querySelector('#match-status').textContent)", timeout=60000)
    page.locator("#match-result:not([hidden]) #result-title").wait_for()
    title = page.locator("#result-title").inner_text()
    assert "wins" in title.lower() or title == "Draw", title
    assert page.locator("#seats").inner_text().count("Built-in · free") == 2
    page.locator("#copy-caption").click()
    page.wait_for_function("() => document.querySelector('#notice').textContent.includes('caption and replay link copied')")
    caption = page.evaluate("navigator.clipboard.readText()")
    page.screenshot(path=str(OUT / "completed-free-match.png"), full_page=True)
    with page.expect_download() as image_download:
        page.locator("#result-image").click()
    image_download.value.save_as(OUT / "result.png")
    page.locator("#match-proof summary").click()
    with page.expect_download() as proof_download:
        page.locator("#export-proof").click()
    proof_download.value.save_as(OUT / "match.jsonl")
    with page.expect_download() as verifier_download:
        page.locator("#download-verifier").click()
    verifier_download.value.save_as(OUT / "verify.mjs")
    verified = json.loads(subprocess.check_output(["node", str(OUT / "verify.mjs"), str(OUT / "match.jsonl")], text=True, timeout=15))
    assert verified["verified"] and verified["complete"]
    assert not requests, requests
    context.close()
    assert video is not None
    video.save_as(OUT / "free-match.webm")
    original_video = Path(video.path())
    if original_video != OUT / "free-match.webm":
        original_video.unlink()  # Exact duplicate created by this recording only.
    browser.close()

receipt = {
    "classification": "actual built-in exhibition recorded through automated studio demonstration; not an external user or frontier-model result",
    "source_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "source_files": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in ["src/sharing.ts", "src/main.ts", "src/style.css"]},
    "title": title, "verifier_result": verified, "provider_request_count": len(requests),
    "caption_with_local_replay": caption,
    "deployment": "local preview only; do not announce the candidate as live",
}
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print(json.dumps({"result": title, "verification": verified, "video": str(OUT / "free-match.webm"), "image": str(OUT / "result.png"), "provider_requests": len(requests)}))
