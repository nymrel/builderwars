"""Real-browser result artwork, private-field stripping and explicit safe runbacks."""
import base64
import gzip
import json
import os
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright

BASE = os.environ.get("BUILDERWARS_TEST_URL", "http://127.0.0.1:5178").rstrip("/")
OUT = Path(__file__).parents[1] / "output" / "playwright"
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, permissions=["clipboard-read", "clipboard-write"])
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(BASE)
    page.locator("#board .cell").first.wait_for()
    page.locator("[data-game=connect4]").click()
    for seat in [0, 1]:
        page.locator(f'[data-seat="{seat}"]').click()
        page.locator("#agent-kind").select_option("human")
        page.locator("#agent-name").fill(f"Scripted human {seat + 1}")
        page.locator("#strategy").fill("PRIVATE-PROMPT-SENTINEL")
        page.locator("#agent-form button[type=submit]").click()
    for cell in [0, 1, 0, 1, 0, 1, 0]:
        page.locator(f'[data-cell="{cell}"]').click()
    assert page.locator("#result-title").inner_text() == "Scripted human 1 wins"
    assert "not attested" in page.locator("#result-evidence").inner_text()
    with page.expect_download() as result_download:
        page.locator("#result-image").click()
    image_path = OUT / "scripted-human-result.png"
    result_download.value.save_as(image_path)
    header = image_path.read_bytes()
    assert header.startswith(b"\x89PNG\r\n\x1a\n")
    assert int.from_bytes(header[16:20], "big") == 1200
    assert int.from_bytes(header[20:24], "big") == 675
    page.locator("#copy-caption").click()
    page.wait_for_function("() => document.querySelector('#notice').textContent.includes('caption and replay link copied')")
    caption = page.evaluate("navigator.clipboard.readText()")
    replay_url = caption.split("rematch: ")[1]
    encoded = parse_qs(urlparse(replay_url).fragment)["replay"][0]
    replay_record = json.loads(gzip.decompress(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))))
    assert "PRIVATE-PROMPT-SENTINEL" not in json.dumps(replay_record)
    assert all(not a["strategy"] for a in replay_record["agents"])
    # Fresh recipient; no localStorage or original connections inherited.
    recipient_context = browser.new_context(viewport={"width": 320, "height": 780})
    recipient = recipient_context.new_page()
    recipient.on("pageerror", lambda e: errors.append(str(e)))
    recipient.goto(replay_url)
    recipient.locator("#result-title").filter(has_text="Scripted human 1 wins").wait_for()
    assert recipient.locator("#start").is_disabled()
    assert recipient.evaluate("document.documentElement.scrollWidth <= innerWidth")
    recipient.locator("#replay-prev").click()
    assert recipient.locator("#ply").inner_text() == "PLY 06"
    recipient.locator("#runback-free").click()
    recipient.wait_for_function("() => Number(document.querySelector('#metric-moves').textContent) >= 2")
    recipient.locator("#start").click()
    assert recipient.locator("#seats").inner_text().count("Built-in · free") == 2
    assert "Scripted human" not in recipient.locator("#seats").inner_text()
    recipient.locator("#play-yourself").click()
    assert "Human player" in recipient.locator("#seats").inner_text()
    recipient.locator('[data-cell="0"]').click()
    recipient.wait_for_function("() => Number(document.querySelector('#metric-moves').textContent) >= 2")
    recipient.locator("#start").click()
    # Original configured model is a declaration only. No key follows the setup link.
    page.locator("#reset").click()
    page.route("https://openrouter.ai/api/v1/models", lambda route: route.fulfill(json={"data": [{"id": "test/model", "name": "Test Model", "reasoning": {"supported_efforts": ["high"]}}]}))
    page.locator("#connections").click()
    page.locator("#agent-kind").select_option("openrouter")
    page.locator("#model-id option").first.wait_for(state="attached")
    page.locator("#effort").select_option("high")
    page.locator("#agent-key").fill("PRIVATE-KEY-SENTINEL")
    page.locator("#agent-form button[type=submit]").click()
    # Setup sharing is also accessible before a match has moves.
    page.locator(".match-settings").filter(has=page.locator("#move-limit")).locator("summary").click()
    page.locator("#share-setup-settings").click()
    page.wait_for_function("() => document.querySelector('#notice').textContent.includes('Setup link copied')")
    setup_url = page.evaluate("navigator.clipboard.readText()")
    setup_text = base64.urlsafe_b64decode(parse_qs(urlparse(setup_url).fragment)["setup"][0] + "==").decode()
    assert "PRIVATE" not in setup_text and "endpoint" not in setup_text and "strategy" not in setup_text
    attempts = []
    recipient.route("https://openrouter.ai/**", lambda route: (attempts.append(route.request.url), route.abort()))
    prior_moves = recipient.locator("#metric-moves").inner_text()
    recipient.goto(setup_url)
    recipient.locator("#setup-dialog").wait_for()
    # A link preview must not replace the recipient's recoverable paused match.
    assert recipient.locator("#metric-moves").inner_text() == prior_moves
    assert not attempts
    recipient.locator("#setup-configure").click()
    assert recipient.locator("#metric-moves").inner_text() == "0"
    assert "test/model" in recipient.locator("#seats").inner_text()
    assert not attempts
    recipient.locator("#step").click()
    recipient.wait_for_function("() => document.querySelector('#notice').textContent.toLowerCase().includes('key')")
    assert not attempts
    recipient.goto(setup_url)
    recipient.locator("#setup-dialog").wait_for()
    recipient.locator("#setup-free").click()
    recipient.wait_for_function("() => Number(document.querySelector('#metric-moves').textContent) >= 2")
    recipient.locator("#start").click()
    assert not attempts
    assert recipient.evaluate("document.documentElement.scrollWidth <= innerWidth")
    recipient.screenshot(path=str(OUT / "share-rematch-mobile.png"), full_page=True)
    # Clipboard failure is visible rather than silently claiming a copy succeeded.
    page.evaluate("Object.defineProperty(navigator.clipboard, 'writeText', {value: async () => {throw new Error('Clipboard denied')}})")
    page.locator("#share").click()
    page.wait_for_function("() => document.querySelector('#notice').textContent.includes('Clipboard denied')")
    assert not errors, errors
    browser.close()
print("PASS: PNG result, sanitized replay/caption, clean recipient replay/runback/human game, model setup with no execution, clipboard failure, 320px layout")
