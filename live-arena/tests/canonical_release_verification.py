"""One-off HTTPS verification of the exact merged app; no deploy or provider calls."""
import concurrent.futures
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

SOURCE = "1745c0a0cc8aaa31aaf8f67edc7765f32de6b547"
SOURCE_TREE = "ed6656541535881578bb51164d44a475197eb5cd"
PREVIEW_HOST = "builderwars-632bfkr0w-jalens-projects-0ade4450.vercel.app"
PREVIEW_DEPLOYMENT = "dpl_7j7mkZdW8fQEZfTRqhqhwXRmBA3s"
APPROVED_HOSTS = {"builderwars.com", PREVIEW_HOST}
PREVIEW_SUFFIX = (f'<script async data-explicit-opt-in="true" data-deployment-id="{PREVIEW_DEPLOYMENT}" '
                  'src="https://vercel.live/_next-live/feedback/feedback.js"></script>').encode()
SAMPLE = "/competition/launch-ttt-v1/matches/launch-ttt-v1-01-0-0.json"
LAB_KEY = "builderwars.browser-lab.archive.v1"
CLEAN_PATHS = ["/", "/about", "/games", "/verify", "/guide", "/developers", "/circuits",
               "/circuits/launch-ttt-v1", "/matches/launch-ttt-v1-01-0-0",
               "/agents/launch-ttt-v1/perfect-ttt-v1", "/evals", "/rankings", "/compete", "/duels"]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def target_origin(raw):
    parsed = urlsplit(raw)
    if (parsed.scheme != "https" or parsed.hostname not in APPROVED_HOSTS
            or parsed.netloc != parsed.hostname or parsed.path not in ("", "/")
            or parsed.query or parsed.fragment):
        raise ValueError("Target must be the exact approved HTTPS preview or canonical origin.")
    return "https://" + parsed.hostname


class SameOriginRedirect(HTTPRedirectHandler):
    def __init__(self, origin):
        self.origin = origin

    def redirect_request(self, request, response, code, message, headers, new_url):
        parsed = urlsplit(new_url)
        if parsed.scheme + "://" + parsed.netloc != self.origin:
            raise ValueError("Refusing cross-origin HTTP redirect.")
        return super().redirect_request(request, response, code, message, headers, new_url)


def fetch(origin, path):
    # Independent TLS-verified network GET; no cached/fabricated response or credential.
    request = Request(origin + quote(path, safe="/"), headers={"Accept-Encoding": "identity", "Cache-Control": "no-cache"})
    with build_opener(SameOriginRedirect(origin)).open(request, timeout=30) as response:
        body = response.read(2_000_001)
        if response.status != 200 or len(body) > 2_000_000:
            raise ValueError("Unexpected HTTP status or oversized public response.")
        return body, {k.lower(): v for k, v in response.headers.items()}, response.url


def required_headers(headers, expected):
    for key, value in expected.items():
        if headers.get(key) != value:
            raise ValueError(f"Security header differs: {key}")


def content_evidence(body, expected, origin, path):
    evidence = {"actualSha256": sha(body), "bytes": len(body), "applicationSha256": sha(expected)}
    if body == expected:
        return {**evidence, "rawByteParity": True}
    # The provider's exact, separately identified preview-only suffix is not app code.
    # Canonical verification always requires raw byte parity. No other normalization.
    if (origin == "https://" + PREVIEW_HOST and path.endswith(".html")
            and body == expected + PREVIEW_SUFFIX):
        return {**evidence, "rawByteParity": False, "exactApplicationPrefixParity": True,
                "platformSuffix": {"deployment": PREVIEW_DEPLOYMENT, "bytes": len(PREVIEW_SUFFIX),
                                   "sha256": sha(PREVIEW_SUFFIX), "kind": "Vercel preview toolbar"}}
    raise ValueError("Deployed bytes differ from exact-source build")


class Canonical(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "link" and values.get("rel") == "canonical":
            self.links.append(values.get("href"))


def verify_files(origin, app, receipt):
    dist = app / "dist"
    config = json.loads((app / "vercel.json").read_text())
    expected_headers = {item["key"].lower(): item["value"] for rule in config["headers"]
                        if rule["source"] == "/(.*)" for item in rule["headers"]}
    files = sorted(path for path in dist.rglob("*") if path.is_file())
    assert len(files) == 202, f"Unexpected exact-source build inventory: {len(files)}"

    def check(path):
        rel = path.relative_to(dist).as_posix()
        entry = {"path": rel, "expectedSha256": sha(path.read_bytes())}
        try:
            body, headers, final = fetch(origin, "/" + rel)
            entry.update(finalUrl=final, **content_evidence(body, path.read_bytes(), origin, rel))
            required_headers(headers, expected_headers)
            if rel.endswith(".md"):
                assert headers.get("content-type", "").split(";")[0].strip() == "text/markdown", "Markdown MIME mismatch"
            entry["status"] = "PASS"
        except Exception as error:
            entry.update(status="FAIL", error=str(error))
        return entry

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        receipt["files"] = list(pool.map(check, files))
    receipt["buildInventorySha256"] = sha(json.dumps(
        [{"path": x["path"], "sha256": x["expectedSha256"]} for x in receipt["files"]],
        sort_keys=True, separators=(",", ":")).encode())
    receipt["routes"] = []
    for path in CLEAN_PATHS:
        entry = {"path": path}
        try:
            body, headers, final = fetch(origin, path)
            required_headers(headers, expected_headers)
            parser = Canonical(); parser.feed(body.decode("utf-8"))
            assert parser.links == ["https://builderwars.com" + path], "Canonical link mismatch"
            local = dist / ("index.html" if path == "/" else path.lstrip("/") + ".html")
            evidence = content_evidence(body, local.read_bytes(), origin, local.name)
            entry.update(status="PASS", canonical=parser.links[0], finalUrl=final, **evidence)
        except Exception as error:
            entry.update(status="FAIL", error=str(error))
        receipt["routes"].append(entry)
    assert all(x["status"] == "PASS" for x in receipt["files"] + receipt["routes"]), "Public file or route verification failed"


def browser_journeys(origin, app, out, receipt, executable_path=None):
    from playwright.sync_api import expect, sync_playwright
    config = json.loads((app / "vercel.json").read_text())
    allowed_paths = {"/"} | {"/" + p.relative_to(app / "dist").as_posix()
                              for p in (app / "dist").rglob("*") if p.is_file()}
    allowed_paths.update(rule["source"] for rule in config["rewrites"])
    manifest = json.loads((app / "src/referee-manifest.ts").read_text().split("export default ")[1].split(" as const;")[0])
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({"executable_path": executable_path} if executable_path else {}))
        try:
            for width in (390, 1280):
                run = {"width": width, "status": "RUNNING", "blockedRequests": [], "pageErrors": []}
                receipt.setdefault("browser", []).append(run)
                context = browser.new_context(viewport={"width": width, "height": 900}, service_workers="block")
                requests = []

                def contain(route):
                    request = route.request
                    parsed = urlsplit(request.url)
                    if (parsed.scheme + "://" + parsed.netloc == origin and request.method == "GET"
                            and parsed.path in allowed_paths):
                        requests.append((request.url, request.method, request.resource_type))
                        route.continue_()
                    else:
                        run["blockedRequests"].append({"url": request.url, "method": request.method})
                        route.abort("blockedbyclient")

                def block_socket(socket):
                    run["blockedRequests"].append({"url": socket.url, "method": "WEBSOCKET"})
                    socket.close()

                context.route("**/*", contain)
                context.route_web_socket("**/*", block_socket)
                page = context.new_page()
                page.on("pageerror", lambda error: run["pageErrors"].append(str(error)))
                try:
                    page.goto(origin)
                    expect(page.locator("#board .cell")).to_have_count(64)
                    script = page.locator(f'script[src="/{manifest["file"]}"]')
                    assert script.get_attribute("integrity") == manifest["integrity"], "Pinned referee SRI missing"
                    page.locator("nav [data-tab=watch]").click()
                    expect(page.locator("#watch-sample")).to_have_text("Open sample replay · Launch Circuit")
                    expect(page.locator("#watch-sample-status")).to_contain_text("not attested")
                    page.wait_for_load_state("networkidle")
                    requests.clear()
                    page.locator("#watch-sample").click()
                    expect(page.locator("#game-title")).to_have_text("Tic-tac-toe")
                    expect(page.locator("#metric-moves")).to_have_text("8")
                    expect(page.locator("#feed-count")).to_have_text("RECORDED MOVES")
                    expect(page.locator("#seats")).to_contain_text("Seeded Wildcard")
                    expect(page.locator("#seats")).to_contain_text("Tactician")
                    expect(page.locator("#proof-status")).to_contain_text("reverified snapshot")
                    expect(page.locator("#proof-status")).to_contain_text("not original engine or model provenance")
                    expect(page.locator("#notice")).to_contain_text("No provider or model request was made")
                    expect(page.locator("#exhibition-evidence")).not_to_be_visible()
                    expect(page.locator("#start")).to_be_disabled()
                    page.wait_for_load_state("networkidle")
                    assert [url for url, _, kind in requests if kind in ("fetch", "xhr")] == [origin + SAMPLE]
                    assert all(method == "GET" and ((url == origin + SAMPLE and kind in ("fetch", "xhr"))
                               or (url == origin + "/mark.svg" and kind in ("image", "other")))
                               for url, method, kind in requests), requests
                    settings = page.locator(".match-settings").filter(has=page.locator("#move-limit"))
                    if not settings.evaluate("el => el.open"):
                        settings.locator("summary").click()
                    with page.expect_download() as pending:
                        page.locator("#export-package").click()
                    download = pending.value
                    assert download.failure() is None
                    package = json.loads(Path(download.path()).read_text())
                    original = json.loads((app / "public" / SAMPLE.lstrip("/")).read_text())
                    assert package["record"] == original["record"]
                    assert package["declarations"] == original["declarations"]
                    assert package["resources"] == original["resources"]
                    assert package["verification"]["verifierDigest"] == manifest["digest"]
                    assert all(package["verification"][key] is False for key in ("identityAttested", "modelAttested", "resourcesAttested"))
                    (out / f"watch-export-{width}.json").write_text(json.dumps(package, indent=2) + "\n")
                    page.locator("#replay-position").fill("0")
                    expect(page.locator("#ply")).to_have_text("PLY 00")
                    page.locator("#replay-next").click()
                    expect(page.locator("#ply")).to_have_text("PLY 01")
                    page.screenshot(path=str(out / f"watch-{width}.png"), full_page=True)
                    run["watch"] = {"plies": 8, "currentReferee": manifest["digest"], "exportPreserved": True, "scrubber": "PASS"}

                    # Fresh context has no retained credentials or running provider-backed setup.
                    page.goto(origin)
                    page.locator("[data-game=tictactoe]").click()
                    page.locator("#step").click()
                    expect(page.locator("#metric-moves")).to_have_text("1")
                    page.locator("#start").click()
                    expect(page.locator("#postgame-review")).to_be_visible(timeout=30000)
                    page.screenshot(path=str(out / f"free-play-{width}.png"), full_page=True)
                    run["freePlay"] = {"completed": True, "postGameReview": True}

                    page.goto(origin + "/#lab")
                    page.locator("#lab-form summary").click()
                    page.locator("#lab-seed").fill("20261022")
                    page.locator("#lab-start").click()
                    page.wait_for_function("key => JSON.parse(localStorage.getItem(key)||'{}').runs?.at(-1)?.status==='completed'", arg=LAB_KEY, timeout=90000)
                    expect(page.locator("#lab-status")).to_contain_text("Comparison completed")
                    archive = page.evaluate("key => JSON.parse(localStorage.getItem(key))", LAB_KEY)
                    completed = archive["runs"][-1]
                    assert len(completed["blocks"]) == 16 and completed["summary"]["completedGames"] == 128
                    assert archive["selected"] == completed["parent"]["digest"]
                    page.screenshot(path=str(out / f"lab-{width}.png"), full_page=True)
                    page.reload()
                    expect(page.locator("#lab-status")).to_contain_text("Saved comparison restored")
                    page.locator("#lab-start").click()
                    expect(page.locator("#lab-cancel")).to_be_enabled()
                    page.locator("#lab-cancel").click()
                    expect(page.locator("#lab-status")).to_contain_text("Cancelled")
                    page.reload()
                    assert page.evaluate("key => JSON.parse(localStorage.getItem(key)).runs.at(-1).status", LAB_KEY) == "cancelled"
                    run["lab"] = {"completedGames": 128, "seedBlocks": 16, "workerExecuted": True, "savedRestored": True, "cancelledRestored": True}

                    page.goto(origin + "/matches/launch-ttt-v1-01-0-0")
                    expect(page.locator("#public-board span")).to_have_count(9)
                    assert page.locator('link[rel="canonical"]').get_attribute("href") == "https://builderwars.com/matches/launch-ttt-v1-01-0-0"
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                    page.screenshot(path=str(out / f"public-match-{width}.png"), full_page=True)
                    assert not run["blockedRequests"], run["blockedRequests"]
                    assert not run["pageErrors"], run["pageErrors"]
                    run.update(status="PASS", actualProviderCalls=0)
                except Exception as error:
                    run.update(status="FAIL", error=str(error))
                    page.screenshot(path=str(out / f"failure-{width}.png"), full_page=True)
                    raise
                finally:
                    context.close()
        finally:
            browser.close()


def main():
    out = Path(os.environ["RECEIPT_DIR"]); out.mkdir(parents=True, exist_ok=True)
    app = Path(os.environ["APP_ROOT"]).resolve()
    receipt = {"schema": "builderwars.live-verification.v1", "status": "RUNNING", "source": SOURCE,
               "sourceTree": SOURCE_TREE, "verifierCommit": os.environ.get("VERIFIER_COMMIT"),
               "verifierSha256": sha(Path(__file__).read_bytes()), "startedAt": datetime.now(timezone.utc).isoformat(),
               "scope": "Actual HTTPS bytes and local browser journeys; no provider, identity or physical-device attestation."}
    try:
        origin = target_origin(os.environ["TARGET_URL"]); receipt["origin"] = origin
        assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=app, text=True).strip() == SOURCE
        assert subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=app, text=True).strip() == SOURCE_TREE
        verify_files(origin, app, receipt)
        browser_journeys(origin, app, out, receipt)
        receipt.update(status="PASS", actualProviderCalls=0)
    except Exception as error:
        receipt.update(status="FAIL", error=str(error))
        raise
    finally:
        receipt["finishedAt"] = datetime.now(timezone.utc).isoformat()
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps({"status": receipt["status"], "source": SOURCE, "origin": receipt.get("origin"),
                          "files": len(receipt.get("files", [])), "error": receipt.get("error")}))


if __name__ == "__main__":
    main()
