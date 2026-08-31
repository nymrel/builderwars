#!/usr/bin/env python3
"""Fail-closed local checks for the BuilderWars mobile Arena Exchange demo."""

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
    "manifest.webmanifest",
    "sw.js",
    "assets/arena-mark.svg",
    "data/demo-state.json",
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
    sw = read("sw.js")
    webmanifest = json.loads(read("manifest.webmanifest"))
    fixture = json.loads(read("data/demo-state.json"))

    print("[2] demo truth boundary is explicit and machine-readable")
    require(fixture.get("schemaVersion") == "builderwars.mobile-arena-demo.v1", "fixture schema drift")
    require(fixture.get("demoOnly") is True, "fixture must stay demo-only")
    require(fixture.get("sourceStatus") == "local_fixture_not_live", "fixture cannot imply live state")
    require('data-demo-only="true"' in html and "LOCAL DEMO" in html, "visible demo boundary missing")
    require("No provider is connected" in html, "provider boundary missing")
    require(fixture["featured"]["proof"]["modelAttested"] is False, "model attestation must stay false")
    require(fixture["featured"]["proof"]["providerAttested"] is False, "provider attestation must stay false")
    require(fixture["featured"]["proof"]["runtimeAttested"] is False, "runtime attestation must stay false")
    require(fixture["featured"]["proof"]["registryState"] == "pending_registry_commit", "registry must remain pending")
    checks += 9

    print("[3] five mobile destinations and proof inspector are wired")
    for destination in ("arena", "watch", "compete", "learn", "build"):
        require(f'id="view-{destination}"' in html, f"missing {destination} view")
        require(f'data-nav="{destination}"' in html, f"missing {destination} navigation")
        checks += 2
    for required in ("proof-sheet", "automations-sheet", "builder-form", "featured-match", "quick-matches"):
        require(f'id="{required}"' in html, f"missing interactive surface: {required}")
        checks += 1

    print("[4] local-only network and execution boundary")
    combined = "\n".join((html, css, js, sw, json.dumps(fixture), json.dumps(webmanifest)))
    require(re.search(r"https?://", combined, re.IGNORECASE) is None, "mobile shell contains an external URL")
    for forbidden in ("eval(", "new Function", "WebSocket(", "EventSource(", "postMessage(", "document.cookie", "Authorization", "Bearer "):
        require(forbidden not in combined, f"forbidden active capability: {forbidden}")
        checks += 1
    require('fetch("data/demo-state.json"' in js, "app must load the bounded local fixture")
    require("requestURL.origin !== self.location.origin" in sw, "service worker must reject cross-origin caching")
    require("localStorage.setItem" in js and "localStorage.getItem" in js, "local blueprint persistence missing")
    require("raw.length > 2048" in js and "never executed" in html, "local blueprint boundary missing")
    checks += 5

    print("[5] accessibility, offline, and reduced-motion contracts")
    for marker in (
        'href="#workspace"',
        'aria-label="Primary navigation"',
        'aria-modal="true"',
        'role="status"',
        "prefers-reduced-motion",
        "serviceWorker",
        "Demo unavailable",
    ):
        require(marker in combined, f"missing product-quality marker: {marker}")
        checks += 1
    require('$("#app-shell").inert = true' in js, "modal open must inert the app shell")
    require('$("#app-shell").inert = false' in js, "modal close must restore the app shell")
    require('event.key !== "Tab"' in js and "nextModalFocusIndex" in js, "modal focus loop missing")
    require('id="connection-status"' in html and "updateConnectionStatus" in js, "local connection status rail missing")
    require('window.addEventListener("online"' in js and 'window.addEventListener("offline"' in js, "connection status events missing")
    require('.lesson-copy' in css and 'background: transparent' in css, "lesson controls must reset native button presentation")
    require('aria-current="step"' in js, "active learning step semantics missing")
    require('@media (max-width: 359px)' in css and '.avatar-button { display: none; }' in css, "320px header overflow guard missing")
    checks += 8

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
    require(webmanifest.get("start_url") == "./index.html?v=5", "web manifest start URL drift")
    for offline_asset in (
        "./index.html?v=5",
        "./styles.css?v=5",
        "./app.js?v=5",
        "./manifest.webmanifest",
        "./assets/arena-mark.svg",
        "./data/demo-state.json",
    ):
        require(f'"{offline_asset}"' in sw, f"service-worker cache misses {offline_asset}")
        checks += 1
    require('new Request(asset, { cache: "reload" })' in sw, "service-worker install must bypass stale HTTP cache")
    require('caches.match("./index.html?v=5")' in sw, "offline navigation fallback must be versioned")
    checks += 2
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
    print("local fixture / five-tab shell / proof inspector / no provider or publication authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
