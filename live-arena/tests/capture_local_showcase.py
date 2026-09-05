"""Render an existing completed local exhibition on canonical BuilderWars; no inference."""
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(sys.argv[1]).resolve()
if not SOURCE.is_relative_to(ROOT / "output" / "playwright") or SOURCE.name != "receipt.json":
    raise ValueError("Use the retained local experiment receipt inside output/playwright")
receipt = json.loads(SOURCE.read_text(encoding="utf-8"))
if receipt["completedGames"] != 2 or receipt["failedGames"] or receipt["cappedGames"]:
    raise ValueError("Both actual games must have completed; no synthetic replacement")
OUT = SOURCE.parent / "canonical-replays"
OUT.mkdir()  # Never replace earlier evidence.
BASE = "https://builderwars.com"
local_html = (ROOT / "dist" / "index.html").read_text(encoding="utf-8")
asset = re.search(r'type="module"[^>]*src="([^"]+)"', local_html).group(1)
expected_asset = (ROOT / "dist" / asset.lstrip("/")).read_bytes()
errors, blocked, results = [], [], []

with sync_playwright() as p:
    browser = p.chromium.launch()
    try:
        for game in receipt["games"]:
            replay_url = game["replayUrl"]
            parsed = urlparse(replay_url)
            if parsed.scheme != "https" or parsed.netloc != "builderwars.com" or not parsed.fragment.startswith("replay="):
                raise ValueError("Expected sanitized canonical replay URL")
            if game["exit"] != "complete" or not game["record"]["events"]:
                raise ValueError("Missing completed original game")
            context = browser.new_context(viewport={"width": 390, "height": 844},
                record_video_dir=str(OUT), record_video_size={"width": 390, "height": 844},
                service_workers="block")
            video = None
            try:
                def contain(route):
                    target = urlparse(route.request.url)
                    if target.scheme == "https" and target.netloc == "builderwars.com" and route.request.method == "GET":
                        route.continue_()
                    else:
                        blocked.append({"host": target.netloc, "method": route.request.method})
                        route.abort()
                context.route("**/*", contain)
                context.route_web_socket("**/*", lambda socket: socket.close())
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                video = page.video
                with page.expect_response(lambda response: urlparse(response.url).path == asset) as response:
                    page.goto(replay_url)
                assert response.value.body() == expected_asset, "Canonical asset differs; no capture claim"
                page.locator("#match-result:not([hidden]) #result-title").wait_for()
                title = page.locator("#result-title").inner_text()
                winner = game["winnerHarness"]
                expected_title = "Draw" if winner is None else next(
                    a["name"] for a in game["record"]["agents"] if f"{winner} harness" in a["name"]) + " wins"
                assert title == expected_title, (title, expected_title)
                plies = len(game["record"]["events"])
                assert int(page.locator("#metric-moves").inner_text()) == plies
                assert page.locator("#start").is_disabled()
                evidence = page.locator("#result-evidence").inner_text()
                assert "not attested" in evidence
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                page.screenshot(path=str(OUT / f"game-{game['game']}-mobile.png"), full_page=True)
                with page.expect_download() as download:
                    page.locator("#result-image").click()
                download.value.save_as(OUT / f"game-{game['game']}-result.png")
                for _ in range(plies):
                    page.locator("#replay-prev").click()
                assert page.locator("#ply").inner_text() == "PLY 00"
                for step in range(1, plies + 1):
                    page.locator("#replay-next").click()
                    assert page.locator("#ply").inner_text() == f"PLY {step:02d}"
                    page.wait_for_timeout(450)  # Presentation pacing, not original inference latency.
                results.append({"game": game["game"], "title": title, "plies": plies,
                    "replayUrl": replay_url, "evidence": evidence, "cleanContext": True,
                    "executionDisabled": True, "stepping": True, "viewport": "390x844"})
            finally:
                context.close()
            assert video is not None
            video.save_as(OUT / f"game-{game['game']}-replay.webm")
            original = Path(video.path()).resolve()
            if original.parent == OUT.resolve() and original.name != f"game-{game['game']}-replay.webm":
                original.unlink()  # Exact redundant task-owned recording only.
    finally:
        browser.close()

assert not errors, errors
assert not blocked, blocked
result = {"classification": "Replay of actual local model games; automated capture, not live inference or external users",
    "originalReceiptSha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    "canonicalAsset": asset, "canonicalAssetSha256": hashlib.sha256(expected_asset).hexdigest(),
    "providerRequests": 0, "blockedRequests": blocked, "pageErrors": errors, "games": results,
    "replayPacingMs": 450, "timingMeaning": "Edited replay pacing is not model inference latency",
    "artifacts": {file.name: hashlib.sha256(file.read_bytes()).hexdigest() for file in OUT.iterdir() if file.is_file()}}
(OUT / "capture-receipt.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps({"output": str(OUT), "games": [{"title": r["title"], "plies": r["plies"]} for r in results],
    "providerRequests": 0, "pageErrors": errors}))
