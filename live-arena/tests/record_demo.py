"""Record one actual free built-in match, without selecting or replacing its outcome.

Optional manual artifact capture, not a CI requirement. No model credentials/calls.
BUILDERWARS_TEST_URL selects a preview or public target; BUILDERWARS_DEMO_OUTPUT_DIR
selects a fresh output directory. Outputs are QA/demo, not external user evidence.
"""
import hashlib
import json
import os
import re
import subprocess
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parents[1]
BASE = os.environ.get("BUILDERWARS_TEST_URL", "http://127.0.0.1:5178").rstrip("/")
OUT = Path(os.environ.get("BUILDERWARS_DEMO_OUTPUT_DIR", str(ROOT / "output" / "playwright" / "free-demo"))).resolve()
if OUT.exists() and any(OUT.iterdir()):
    raise RuntimeError("Choose an empty demo output directory; historical captures are never overwritten")
OUT.mkdir(parents=True, exist_ok=True)
local_index = (ROOT / "dist" / "index.html").read_text(encoding="utf-8")
main_asset = re.search(r'<script\b[^>]*\bsrc="([^\"]+)"', local_index).group(1)
local_asset = (ROOT / "dist" / main_asset.lstrip("/")).read_bytes()
origin = urlparse(BASE)
blocked_requests, requests, errors = [], [], []


def contain_network(context):
    def route_request(route):
        target = urlparse(route.request.url)
        if target.netloc == "openrouter.ai":
            requests.append(route.request.url)
        if (target.scheme, target.netloc) != (origin.scheme, origin.netloc):
            blocked_requests.append(route.request.url)
            route.abort()
        else:
            route.continue_()
    context.route("**/*", route_request)
    context.route_web_socket("**/*", lambda socket: socket.close())

with sync_playwright() as p, ExitStack() as cleanup:
    browser = p.chromium.launch()
    cleanup.callback(browser.close)
    context = browser.new_context(
        viewport={"width": 1440, "height": 1080},
        record_video_dir=str(OUT), record_video_size={"width": 1440, "height": 1080},
        permissions=["clipboard-read", "clipboard-write"],
        service_workers="block",
    )
    contain_network(context)
    page = context.new_page()
    page.on("pageerror", lambda error: errors.append(str(error)))
    video = page.video
    with page.expect_response(lambda response: urlparse(response.url).path == main_asset) as main_response:
        document = page.goto(BASE)
    assert document is not None and document.status == 200
    served_html = document.body()
    served_asset = main_response.value.body()
    assert served_asset == local_asset, "Served main asset differs from the local build; no match started"
    assert urlparse(page.url).netloc == origin.netloc, page.url
    asset_evidence = {
        "target_url": BASE, "document_url": document.url, "document_status": document.status,
        "document_sha256": hashlib.sha256(served_html).hexdigest(),
        "main_asset_url": main_response.value.url,
        "main_asset_sha256": hashlib.sha256(served_asset).hexdigest(),
        "local_build_asset": str(ROOT / "dist" / main_asset.lstrip("/")),
        "local_build_asset_equal": True,
        "vercel_request_id": document.headers.get("x-vercel-id"),
        "deployment_id_owner_declared": os.environ.get("BUILDERWARS_DEMO_DEPLOYMENT_ID"),
        "release_source_owner_declared": os.environ.get("BUILDERWARS_DEMO_RELEASE_SOURCE"),
        "source_custody_limit": "Asset bytes are observed; release source and deployment ID require the integrator's independent release receipt.",
    }
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
    replay_url = caption.split("rematch: ", 1)[1].strip()
    assert (urlparse(replay_url).scheme, urlparse(replay_url).netloc) == (origin.scheme, origin.netloc)
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
    recipient_context = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
    contain_network(recipient_context)
    recipient = recipient_context.new_page()
    recipient.on("pageerror", lambda error: errors.append(str(error)))
    recipient.goto(replay_url)
    recipient.locator("#match-result:not([hidden]) #result-title").wait_for()
    assert recipient.locator("#result-title").inner_text() == title
    assert "not attested" in recipient.locator("#result-evidence").inner_text()
    assert recipient.locator("#start").is_disabled()
    assert int(recipient.locator("#metric-moves").inner_text()) == verified["plies"]
    recipient.locator("#replay-prev").click()
    assert recipient.locator("#ply").inner_text() == f"PLY {verified['plies'] - 1:02d}"
    recipient.locator("#replay-next").click()
    assert recipient.locator("#ply").inner_text() == f"PLY {verified['plies']:02d}"
    assert recipient.evaluate("document.documentElement.scrollWidth <= innerWidth")
    recipient.screenshot(path=str(OUT / "clean-recipient-replay.png"), full_page=True)
    recipient_context.close()
    clean_replay = {"verified": True, "url": replay_url, "title": title, "plies": verified["plies"], "stepping": True, "execution_disabled": True, "viewport": "390x844"}
    assert not errors, errors
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
    "captured_at_utc": datetime.now(timezone.utc).isoformat(),
    "local_checkout_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "source_files": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in ["src/sharing.ts", "src/main.ts", "src/style.css"]},
    "title": title, "verifier_result": verified, "provider_request_count": len(requests),
    "caption_with_replay": caption,
    "target_asset_evidence": asset_evidence,
    "clean_browser_replay": clean_replay,
    "blocked_external_requests": blocked_requests,
    "page_errors": errors,
    "deployment": "Observed target and asset bytes above; demonstration is not customer adoption or model identity evidence",
    "capture_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "artifacts": {name: hashlib.sha256((OUT / name).read_bytes()).hexdigest() for name in ["result.png", "free-match.webm", "match.jsonl", "verify.mjs", "completed-free-match.png", "clean-recipient-replay.png"]},
}
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print(json.dumps({"result": title, "verification": verified, "video": str(OUT / "free-match.webm"), "image": str(OUT / "result.png"), "provider_requests": len(requests)}))
