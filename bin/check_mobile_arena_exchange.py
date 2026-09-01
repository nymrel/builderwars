#!/usr/bin/env python3
"""Fail-closed local checks for the BuilderWars mobile Arena Exchange."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOBILE = ROOT / "mobile-arena"
EXPECTED = {
    "index.html",
    "styles.css",
    "app.js",
    "data-adapter.js",
    "manifest.webmanifest",
    "sw.js",
    "assets/arena-mark.svg",
    "data/demo-state.json",
    "data/arena-read-model.v1.json",
}


def require(predicate: bool, message: str) -> None:
    if not predicate:
        raise AssertionError(message)


def read(relative: str) -> str:
    return (MOBILE / relative).read_text(encoding="utf-8")


def main() -> int:
    checks = 0

    print("[1] exact local shell exists")
    for relative in sorted(EXPECTED):
        path = MOBILE / relative
        require(path.is_file(), f"missing mobile arena asset: {relative}")
        require(path.stat().st_size > 20, f"empty mobile arena asset: {relative}")
        checks += 2

    html = read("index.html")
    css = read("styles.css")
    js = read("app.js")
    adapter = read("data-adapter.js")
    sw = read("sw.js")
    webmanifest = json.loads(read("manifest.webmanifest"))
    fixture = json.loads(read("data/demo-state.json"))
    read_model = json.loads(read("data/arena-read-model.v1.json"))

    print("[2] demo truth boundary is explicit and machine-readable")
    require(fixture.get("schemaVersion") == "builderwars.mobile-arena-demo.v1", "fixture schema drift")
    require(fixture.get("demoOnly") is True, "fixture must stay demo-only")
    require(fixture.get("sourceStatus") == "local_fixture_not_live", "fixture cannot imply live state")
    require('data-local-only="true"' in html and 'id="source-badge"' in html, "visible local-source boundary missing")
    require("No provider is connected" in html, "provider boundary missing")
    require(fixture["featured"]["proof"]["modelAttested"] is False, "model attestation must stay false")
    require(fixture["featured"]["proof"]["providerAttested"] is False, "provider attestation must stay false")
    require(fixture["featured"]["proof"]["runtimeAttested"] is False, "runtime attestation must stay false")
    require(fixture["featured"]["proof"]["registryState"] == "pending_registry_commit", "registry must remain pending")
    checks += 9

    require(read_model.get("schemaVersion") == "builderwars.arena-read-model.v1", "read-model schema drift")
    require(read_model.get("source", {}).get("status") == "tracked_local_publication_artifact_not_hosted", "read-model source boundary drift")
    require(read_model.get("summary", {}).get("receiptCount") == len(read_model.get("receipts", [])) == 8, "reviewed receipt count drift")
    for boundary in ("live", "hosted", "authenticated", "modelAttested", "providerAttested", "runtimeAttested"):
        require(read_model.get("truthBoundary", {}).get(boundary) is False, f"read-model {boundary} boundary drift")
        checks += 1
    checks += 3

    print("[3] five mobile destinations and proof inspector are wired")
    for destination in ("arena", "watch", "compete", "learn", "build"):
        require(f'id="view-{destination}"' in html, f"missing {destination} view")
        require(f'data-nav="{destination}"' in html, f"missing {destination} navigation")
        checks += 2
    for required in ("proof-sheet", "automations-sheet", "qualification-sheet", "builder-form", "featured-match", "quick-matches", "rivalries", "receipt-learning", "proof-learning-button"):
        require(f'id="{required}"' in html, f"missing interactive surface: {required}")
        checks += 1

    print("[4] local-only network and execution boundary")
    combined = "\n".join((html, css, js, adapter, sw, json.dumps(fixture), json.dumps(read_model), json.dumps(webmanifest)))
    require(re.search(r"https?://", combined, re.IGNORECASE) is None, "mobile shell contains an external URL")
    for forbidden in ("eval(", "new Function", "WebSocket(", "EventSource(", "postMessage(", "document.cookie", "Authorization", "Bearer "):
        require(forbidden not in combined, f"forbidden active capability: {forbidden}")
        checks += 1
    require("dataAdapter.loadArenaData(fetch)" in js, "app must load sources through the fail-closed adapter")
    require('"data/demo-state.json"' in adapter and '"data/arena-read-model.v1.json"' in adapter, "adapter must load only the two bounded local sources")
    require('sourceMode = "verified_corpus"' in adapter and 'sourceMode = "demo_fixture_fallback"' in adapter, "adapter source modes must remain explicit")
    require("requestURL.origin !== self.location.origin" in sw, "service worker must reject cross-origin caching")
    require("localStorage.setItem" in js and "localStorage.getItem" in js, "local blueprint persistence missing")
    require("BLUEPRINT_MAX_LENGTH = 2048" in js and "raw.length > BLUEPRINT_MAX_LENGTH" in js and "never executed" in html, "local blueprint boundary missing")
    require("for (const key of BLUEPRINT_GUARD_KEYS)" in js, "saved blueprint guards must hydrate from the bounded key list")
    require("localStorage.removeItem(BLUEPRINT_STORAGE_KEY)" in js, "invalid local blueprint state must be discarded")
    require("buildQualificationPreview" in adapter and 'qualificationStatus: "not_run"' in adapter, "deterministic qualification preview missing")
    require('executionStatus: "disabled"' in adapter and "computeAllowed: false" in adapter and "networkAllowed: false" in adapter, "qualification execution boundary missing")
    require("formatArenaRoute" in js and "parseArenaRoute" in js and "/receipt/" in js, "receipt-addressable route contract missing")
    require("unknown rivalry receipt" in adapter and "rivalry outcome drift" in adapter, "rivalry cross-reference checks missing")
    require("buildReceiptLearningAction" in adapter and 'status: "review_only"' in adapter, "proof-linked learning contract missing")
    require("buildRunbackProposal" in adapter and 'runbackStatus: "unplayed_proposal"' in adapter, "versioned unplayed runback contract missing")
    require('status: "blocked_missing_explicit_rules_digest"' in adapter and "explicit_rules_digest_not_bound" in adapter, "runback rules blocker missing")
    require("does not infer hidden reasoning" in adapter and "does not qualify, execute, attest, rank, publish, or spend" in adapter, "learning/runback truth boundary missing")
    require("createPortableRunbackEnvelope" in adapter and "verifyPortableRunbackEnvelope" in adapter, "portable runback verifier missing")
    require('PORTABLE_RUNBACK_SCHEMA = "builderwars.mobile-runback-portable.v1"' in adapter, "portable runback schema drift")
    require("PORTABLE_RUNBACK_MAX_LENGTH = 32768" in adapter and 'maxlength="32768"' in js, "portable import length boundary missing")
    require("globalThis.crypto.subtle.digest" in adapter and 'algorithm: "sha256"' in adapter, "portable checksum contract missing")
    require("not a signature" in adapter and "cannot authenticate origin" in js, "portable authenticity boundary missing")
    require("data-portable-prepare" in js and "data-portable-verify" in js and "portable-runback-import" in js, "portable mobile controls missing")
    require("navigator.clipboard" not in combined and "FileReader" not in combined, "portable flow must not request clipboard or file authority")
    require("appendPortableRunbackReview" in adapter and "verifyPortableRunbackReviewJournal" in adapter, "private portable review verifier missing")
    require('PORTABLE_REVIEW_SCHEMA = "builderwars.mobile-runback-review.v1"' in adapter, "portable review schema drift")
    require('reviewStatus: "private_local_review"' in adapter and 'status: "proposed_uncommitted_revision"' in adapter, "private review or proposed revision boundary missing")
    require("data-portable-review-submit" in js and "portable-reviewer-label" in js and "portable-review-journal" in js, "portable review mobile controls missing")
    require("not a signature or identity claim" in adapter and "grants no rules" in js, "portable review authenticity or authority boundary missing")
    checks += 27
    checks += 2

    print("[5] accessibility, offline, and reduced-motion contracts")
    for marker in (
        'href="#workspace"',
        'aria-label="Primary navigation"',
        'aria-modal="true"',
        'role="status"',
        "prefers-reduced-motion",
        "serviceWorker",
        "Arena unavailable",
    ):
        require(marker in combined, f"missing product-quality marker: {marker}")
        checks += 1
    require('$("#app-shell").inert = true' in js, "modal open must inert the app shell")
    require('$("#app-shell").inert = false' in js, "modal close must restore the app shell")
    require('event.key !== "Tab"' in js and "nextModalFocusIndex" in js, "modal focus loop missing")
    require('id="connection-status"' in html and "updateConnectionStatus" in js, "local connection status rail missing")
    require('window.addEventListener("online"' in js and 'window.addEventListener("offline"' in js, "connection status events missing")
    require("history.pushState" in js and 'window.addEventListener("popstate"' in js, "tab history navigation missing")
    require('window.addEventListener("hashchange"' in js and "syncViewFromLocation" in js, "same-document hash routing missing")
    require('.lesson-copy' in css and 'background: transparent' in css, "lesson controls must reset native button presentation")
    require('aria-current="step"' in js, "active learning step semantics missing")
    require('@media (max-width: 359px)' in css and '.avatar-button { display: none; }' in css, "320px header overflow guard missing")
    checks += 10

    node = shutil.which("node")
    require(node is not None, "Node.js is required to exercise mobile focus helpers")
    focus_check = subprocess.run(
        [
            node,
            "-e",
            (
                "const h=require(" + json.dumps(str(MOBILE / "app.js")) + ");"
                "if(h.nextModalFocusIndex(0,1,false)!==0)process.exit(2);"
                "if(h.nextModalFocusIndex(0,3,true)!==2)process.exit(3);"
                "if(h.nextModalFocusIndex(2,3,false)!==0)process.exit(4);"
                "let calls=0;const target={focus(){calls++;}};"
                "if(!h.restoreModalFocus(target,()=>true)||calls!==1)process.exit(5);"
                "if(h.restoreModalFocus(target,()=>false)||calls!==1)process.exit(6);"
            ),
        ],
        cwd=MOBILE,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
    )
    require(focus_check.returncode == 0, f"modal focus helper check failed: {focus_check.stderr.strip()}")
    checks += 2
    require(webmanifest.get("display") == "standalone", "web manifest must declare standalone display")
    require(webmanifest.get("start_url") == "./index.html?v=13", "web manifest start URL drift")
    for offline_asset in (
        "./index.html?v=13",
        "./styles.css?v=13",
        "./data-adapter.js?v=13",
        "./app.js?v=13",
        "./manifest.webmanifest",
        "./assets/arena-mark.svg",
        "./data/demo-state.json",
        "./data/arena-read-model.v1.json",
    ):
        require(f'"{offline_asset}"' in sw, f"service-worker cache misses {offline_asset}")
        checks += 1
    require('new Request(asset, { cache: "reload" })' in sw, "service-worker install must bypass stale HTTP cache")
    require('NAVIGATION_FALLBACK = "./index.html?v=13"' in sw, "offline navigation fallback must be versioned")
    require('event.request.mode === "navigate"' in sw, "HTML fallback must be limited to navigation requests")
    require("return Response.error()" in sw, "uncached offline resources must fail instead of masquerading as HTML")
    checks += 4
    checks += 2

    adapter_check = subprocess.run(
        [str(Path(shutil.which("python") or "python")), str(ROOT / "bin" / "check_mobile_arena_read_adapter.py")],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
    )
    require(adapter_check.returncode == 0, f"read-adapter regression failed: {adapter_check.stderr.strip()}")
    require("PASS" in adapter_check.stdout, "read-adapter regression did not report PASS")
    checks += 2

    qualification_check = subprocess.run(
        [str(Path(shutil.which("python") or "python")), str(ROOT / "bin" / "check_mobile_arena_qualification.py")],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
    )
    require(qualification_check.returncode == 0, f"qualification regression failed: {qualification_check.stderr.strip()}")
    require("PASS" in qualification_check.stdout, "qualification regression did not report PASS")
    checks += 2

    learning_runback_check = subprocess.run(
        [str(Path(shutil.which("python") or "python")), str(ROOT / "bin" / "check_mobile_arena_learning_runback.py")],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
    )
    require(learning_runback_check.returncode == 0, f"learning/runback regression failed: {learning_runback_check.stderr.strip()}")
    require("PASS" in learning_runback_check.stdout, "learning/runback regression did not report PASS")
    checks += 2

    portable_runback_check = subprocess.run(
        [str(Path(shutil.which("python") or "python")), str(ROOT / "bin" / "check_mobile_arena_portable_runback.py")],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
    )
    require(portable_runback_check.returncode == 0, f"portable runback regression failed: {portable_runback_check.stderr.strip()}")
    require("PASS" in portable_runback_check.stdout, "portable runback regression did not report PASS")
    checks += 2

    portable_review_check = subprocess.run(
        [str(Path(shutil.which("python") or "python")), str(ROOT / "bin" / "check_mobile_arena_portable_review.py")],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=45,
        check=False,
    )
    require(portable_review_check.returncode == 0, f"portable review regression failed: {portable_review_check.stderr.strip()}")
    require("PASS" in portable_review_check.stdout, "portable review regression did not report PASS")
    checks += 2

    print("[6] anti-casino and privacy language is durable")
    strategy = (ROOT / "docs" / "BUILDERWARS_MOBILE_ARENA_EXCHANGE.md").read_text(encoding="utf-8")
    require(strategy.startswith("# BuilderWars Mobile Arena Exchange"), "strategy title drift")
    require("HYPOTHESIS - NOT ADOPTED" in strategy, "governance status missing")
    for phrase in (
        "cash wagering",
        "private chain-of-thought",
        "permissionless creator code",
        "fake streams",
        "Weekly Verified Builder-Competitors",
    ):
        require(phrase in strategy, f"missing strategy guard or metric: {phrase}")
        checks += 1

    print(f"BuilderWars mobile Arena Exchange: PASS ({checks} checks)")
    print("verified corpus / disclosed demo fallback / five-tab shell / no provider or publication authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
