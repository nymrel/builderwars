#!/usr/bin/env python3
"""Run durable real-browser acceptance for the local BuilderWars Mobile Arena.

This check deliberately uses only a loopback HTTP server and tracked local
fixtures. It proves browser behavior, not hosting, authentication, provider
access, live competition, identity, publication, or production readiness.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
MOBILE_ARENA = ROOT / "mobile-arena"
READ_MODEL_PATH = "**/data/arena-read-model.v1.json"
DEMO_FIXTURE_PATH = "**/data/demo-state.json"
VIEW_NAMES = ("arena", "watch", "compete", "learn", "build")
VIEWPORTS = (
    {"width": 320, "height": 720},
    {"width": 390, "height": 844},
    {"width": 768, "height": 1024},
    {"width": 1040, "height": 900},
)


class AcceptanceFailure(AssertionError):
    """Raised when a browser contract is not satisfied."""


class Evidence:
    def __init__(self) -> None:
        self.checks: list[str] = []
        self.journeys: list[str] = []

    def require(self, condition: bool, label: str) -> None:
        if not condition:
            raise AcceptanceFailure(label)
        self.checks.append(label)

    def journey(self, label: str) -> None:
        self.journeys.append(label)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


@contextmanager
def loopback_server() -> Iterator[str]:
    handler = partial(QuietHandler, directory=str(MOBILE_ARENA))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, name="builderwars-mobile-arena-http", daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield f"http://{host}:{port}/index.html?browser-acceptance=1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        if thread.is_alive():
            raise AcceptanceFailure("loopback HTTP server stopped cleanly")


def locator_visible(page: Any, selector: str) -> bool:
    locator = page.locator(selector)
    return locator.count() > 0 and locator.first.is_visible()


def wait_for_source(page: Any, source_mode: str) -> None:
    page.wait_for_selector(f'body[data-source-mode="{source_mode}"]', state="attached")
    page.wait_for_function(
        "mode => document.body.dataset.sourceMode === mode && "
        "document.querySelector('#connection-status')?.dataset.state !== 'loading'",
        arg=source_mode,
    )


def install_observers(page: Any, origin: str, label: str) -> dict[str, list[str]]:
    observed: dict[str, list[str]] = {
        "console": [],
        "page_errors": [],
        "external_requests": [],
    }

    def on_console(message: Any) -> None:
        if message.type in {"error", "warning"}:
            observed["console"].append(f"{label}:{message.type}:{message.text}")

    def on_request(request: Any) -> None:
        if urlparse(request.url).scheme in {"http", "https"} and urlparse(request.url).netloc != urlparse(origin).netloc:
            observed["external_requests"].append(f"{label}:{request.method}:{request.url}")

    page.on("console", on_console)
    page.on("pageerror", lambda error: observed["page_errors"].append(f"{label}:{error}"))
    page.on("request", on_request)
    return observed


def assert_observers_clean(evidence: Evidence, observed: dict[str, list[str]], label: str) -> None:
    evidence.require(not observed["console"], f"{label}: zero console warnings or errors ({observed['console']})")
    evidence.require(not observed["page_errors"], f"{label}: zero uncaught page errors ({observed['page_errors']})")
    evidence.require(not observed["external_requests"], f"{label}: zero cross-origin requests ({observed['external_requests']})")


def assert_view(evidence: Evidence, page: Any, view: str) -> None:
    visible_views = page.locator(".view:visible")
    evidence.require(visible_views.count() == 1, f"{view}: exactly one workspace view is visible")
    evidence.require(locator_visible(page, f"#view-{view}"), f"{view}: requested view is visible")
    evidence.require(page.locator(f'.bottom-nav [data-nav="{view}"]').get_attribute("aria-current") == "page", f"{view}: primary navigation exposes aria-current")
    evidence.require(page.url.endswith(f"#{view}"), f"{view}: address is history-safe")


def normal_journey(browser: Any, base_url: str, evidence: Evidence, headed: bool) -> None:
    del headed
    context = browser.new_context(viewport=VIEWPORTS[1], service_workers="allow")
    page = context.new_page()
    observed = install_observers(page, base_url, "normal")
    try:
        response = page.goto(base_url, wait_until="domcontentloaded")
        evidence.require(response is not None and response.ok, "normal: loopback shell returns HTTP success")
        wait_for_source(page, "verified_corpus")
        evidence.require(page.locator("#source-badge").inner_text() == "LOCAL CORPUS", "normal: reviewed local corpus is explicitly labeled")
        evidence.require("verified corpus ready" in page.locator("#connection-copy").inner_text().lower(), "normal: connection rail names the verified corpus")
        evidence.require("No provider is connected" in (page.locator("#connection-status").get_attribute("aria-label") or ""), "normal: connection rail denies provider linkage")
        evidence.require(page.locator("#standings-title").inner_text() == "Receipt board", "normal: reviewed receipts are not presented as a rating leaderboard")
        evidence.require("not a ranking" in page.locator("#standings-help").inner_text().lower(), "normal: ranking boundary stays visible")

        for view in ("watch", "compete", "learn", "build", "arena"):
            page.locator(f'.bottom-nav [data-nav="{view}"]').click()
            assert_view(evidence, page, view)
        evidence.journey("five-destination navigation")

        page.locator('.bottom-nav [data-nav="watch"]').click()
        page.locator('.bottom-nav [data-nav="compete"]').click()
        page.go_back(wait_until="domcontentloaded")
        page.wait_for_function("location.hash === '#watch'")
        assert_view(evidence, page, "watch")
        page.go_forward(wait_until="domcontentloaded")
        page.wait_for_function("location.hash === '#compete'")
        assert_view(evidence, page, "compete")
        evidence.journey("browser back and forward")

        page.locator('.bottom-nav [data-nav="arena"]').click()
        proof_trigger = page.locator("#featured-match [data-proof-open]").first
        receipt_id = proof_trigger.get_attribute("data-proof-open")
        evidence.require(bool(receipt_id and len(receipt_id) == 64), "proof: featured receipt address is content-shaped")
        proof_trigger.click()
        evidence.require(locator_visible(page, "#proof-sheet"), "proof: inspector opens")
        evidence.require(f"#arena/receipt/{receipt_id}" in page.url, "proof: inspector has a receipt-specific local address")
        evidence.require(page.locator("#app-shell").evaluate("node => node.inert === true"), "proof: background is inert while dialog is open")
        evidence.require(page.locator("#proof-sheet").evaluate("node => node.contains(document.activeElement)"), "proof: focus enters the dialog")
        proof_text = page.locator("#proof-content").inner_text()
        evidence.require("No authoritative commit" in proof_text, "proof: registry authority remains absent")
        evidence.require("Model attested\nNo" in proof_text and "Provider attested\nNo" in proof_text and "Runtime attested\nNo" in proof_text, "proof: model, provider, and runtime attestations remain false")
        page.keyboard.press("Shift+Tab")
        evidence.require(page.locator("#proof-sheet").evaluate("node => node.contains(document.activeElement)"), "proof: reverse tab stays inside dialog")
        page.keyboard.press("Escape")
        page.wait_for_function("document.querySelector('#proof-sheet').hidden === true")
        evidence.require(page.url.endswith("#arena"), "proof: Escape restores the containing route")
        evidence.require(page.evaluate("document.activeElement?.hasAttribute('data-proof-open')") is True, "proof: close restores trigger focus")
        evidence.journey("receipt proof dialog and focus lifecycle")

        unknown_receipt = "f" * 64
        page.goto(f"{base_url}#watch/receipt/{unknown_receipt}", wait_until="domcontentloaded")
        wait_for_source(page, "verified_corpus")
        page.wait_for_function("location.hash === '#watch'")
        evidence.require(page.url.endswith("#watch"), "unknown proof: route fails closed to its containing view")
        evidence.require(page.locator("#proof-sheet").is_hidden(), "unknown proof: no substitute receipt is opened")
        evidence.journey("unknown proof fail-closed routing")

        page.locator('.bottom-nav [data-nav="compete"]').click()
        preview = page.locator("[data-qualification-preview]").first
        evidence.require(preview.count() == 1, "qualification: a bounded proposed fixture is available")
        preview.click()
        qualification_text = page.locator("#qualification-sheet").inner_text()
        evidence.require(locator_visible(page, "#qualification-sheet"), "qualification: local preview dialog opens")
        evidence.require("Qualification\nNot run" in qualification_text, "qualification: result remains not run")
        evidence.require("Execution\nDisabled" in qualification_text, "qualification: execution remains disabled")
        evidence.require("all false" in qualification_text, "qualification: every authority attestation remains false")
        page.keyboard.press("Escape")
        evidence.journey("proposed fixture qualification preview")

        page.locator('.bottom-nav [data-nav="build"]').click()
        page.locator("#agent-name").fill("Browser Proof")
        page.locator("#builder-form button[type=submit]").click()
        evidence.require("saved locally" in page.locator("#toast").inner_text().lower(), "persistence: blueprint save is disclosed as browser-local")
        page.reload(wait_until="domcontentloaded")
        wait_for_source(page, "verified_corpus")
        page.locator('.bottom-nav [data-nav="build"]').click()
        evidence.require(page.locator("#agent-name").input_value() == "Browser Proof", "persistence: local blueprint survives reload")
        evidence.journey("local blueprint persistence")

        missing_names = page.evaluate(
            """() => [...document.querySelectorAll('button')]
              .filter((node) => node.offsetParent !== null)
              .filter((node) => !(node.getAttribute('aria-label') || node.innerText || '').trim())
              .map((node) => node.outerHTML)"""
        )
        evidence.require(not missing_names, f"accessibility: every visible button has an accessible name ({missing_names})")
        broken_dialog_labels = page.evaluate(
            """() => [...document.querySelectorAll('[role=dialog]')]
              .filter((node) => !node.getAttribute('aria-modal') || !document.getElementById(node.getAttribute('aria-labelledby') || ''))
              .map((node) => node.id)"""
        )
        evidence.require(not broken_dialog_labels, f"accessibility: every dialog is modal and label-bound ({broken_dialog_labels})")
        evidence.journey("semantic accessibility")

        for viewport in VIEWPORTS:
            page.set_viewport_size(viewport)
            for view in VIEW_NAMES:
                page.locator(f'.bottom-nav [data-nav="{view}"]').click()
                no_document_overflow = page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
                evidence.require(no_document_overflow, f"responsive: {view} has no document overflow at {viewport['width']}px")
        evidence.journey("responsive widths 320, 390, 768, and 1040")
        assert_observers_clean(evidence, observed, "normal")
    finally:
        context.close()


def fallback_journey(browser: Any, base_url: str, evidence: Evidence) -> None:
    context = browser.new_context(viewport=VIEWPORTS[0], service_workers="allow")
    page = context.new_page()
    observed = install_observers(page, base_url, "fallback")
    try:
        page.route(READ_MODEL_PATH, lambda route: route.fulfill(status=200, content_type="application/json", body="{}"))
        page.goto(base_url, wait_until="domcontentloaded")
        wait_for_source(page, "demo_fixture_fallback")
        evidence.require(page.locator("#source-badge").inner_text() == "DEMO FALLBACK", "fallback: invalid read model is visibly disclosed")
        evidence.require("demo fallback ready" in page.locator("#connection-copy").inner_text().lower(), "fallback: connection rail names the bounded fallback")
        evidence.require("Harness board" == page.locator("#standings-title").inner_text(), "fallback: demo-only board label is restored")
        evidence.require("simulated fixture" in page.locator("#featured-match").inner_text().lower(), "fallback: featured content is labeled simulated")
        assert_observers_clean(evidence, observed, "fallback")
        evidence.journey("verified-read-model failure with bounded demo fallback")
    finally:
        context.close()


def fatal_source_journey(browser: Any, base_url: str, evidence: Evidence) -> None:
    context = browser.new_context(viewport=VIEWPORTS[0], service_workers="allow")
    page = context.new_page()
    observed = install_observers(page, base_url, "fatal-source")
    try:
        page.route(DEMO_FIXTURE_PATH, lambda route: route.fulfill(status=200, content_type="application/json", body="{}"))
        page.goto(base_url, wait_until="domcontentloaded")
        page.wait_for_function("document.querySelector('#connection-status')?.dataset.state === 'error'")
        connection_copy = page.locator("#connection-copy").inner_text().strip()
        evidence.require(connection_copy.lower() == "local sources unavailable", f"fatal source: status reports local source failure ({connection_copy!r})")
        evidence.require(locator_visible(page, "text=Local sources could not load."), "fatal source: workspace exposes an explicit error state")
        evidence.require("No live service fallback was attempted" in (page.locator("#connection-status").get_attribute("aria-label") or ""), "fatal source: no live fallback is claimed")
        assert_observers_clean(evidence, observed, "fatal-source")
        evidence.journey("both local sources unavailable fail closed")
    finally:
        context.close()


def storage_denial_journey(browser: Any, base_url: str, evidence: Evidence) -> None:
    context = browser.new_context(viewport=VIEWPORTS[0], service_workers="allow")
    context.add_init_script(
        """for (const method of ['getItem', 'setItem', 'removeItem']) {
          Object.defineProperty(Storage.prototype, method, {
            configurable: true,
            value() { throw new DOMException('Storage denied by acceptance harness', 'SecurityError'); }
          });
        }"""
    )
    page = context.new_page()
    observed = install_observers(page, base_url, "storage-denied")
    try:
        page.goto(base_url, wait_until="domcontentloaded")
        wait_for_source(page, "verified_corpus")
        page.locator('.bottom-nav [data-nav="build"]').click()
        page.locator("#agent-name").fill("Denied Storage")
        page.locator("#builder-form button[type=submit]").click()
        evidence.require("could not be saved" in page.locator("#toast").inner_text().lower(), "storage denial: save failure is explicit")
        evidence.require("nothing was uploaded or executed" in page.locator("#toast").inner_text().lower(), "storage denial: failure does not imply remote fallback")
        assert_observers_clean(evidence, observed, "storage-denied")
        evidence.journey("storage-denied local blueprint")
    finally:
        context.close()


def reduced_motion_journey(browser: Any, base_url: str, evidence: Evidence) -> None:
    context = browser.new_context(viewport=VIEWPORTS[1], reduced_motion="reduce", service_workers="allow")
    page = context.new_page()
    observed = install_observers(page, base_url, "reduced-motion")
    try:
        page.goto(base_url, wait_until="domcontentloaded")
        wait_for_source(page, "verified_corpus")
        evidence.require(page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches") is True, "reduced motion: browser preference is active")
        motion = page.locator("#featured-match").evaluate(
            "node => ({animation: getComputedStyle(node).animationName, transition: getComputedStyle(node).transitionDuration, scroll: getComputedStyle(document.documentElement).scrollBehavior})"
        )
        evidence.require(motion["animation"] == "none", "reduced motion: animation is disabled")
        transition_seconds = [float(duration.strip().removesuffix("s")) for duration in motion["transition"].split(",")]
        evidence.require(all(duration <= 0.00001 for duration in transition_seconds), f"reduced motion: transitions collapse to at most 0.01ms ({motion['transition']!r})")
        evidence.require(motion["scroll"] == "auto", "reduced motion: smooth scrolling is disabled")
        assert_observers_clean(evidence, observed, "reduced-motion")
        evidence.journey("reduced-motion rendering")
    finally:
        context.close()


def offline_journey(browser: Any, base_url: str, evidence: Evidence) -> None:
    context = browser.new_context(viewport=VIEWPORTS[1], service_workers="allow")
    page = context.new_page()
    observed = install_observers(page, base_url, "offline")
    try:
        page.goto(base_url, wait_until="domcontentloaded")
        wait_for_source(page, "verified_corpus")
        page.evaluate("navigator.serviceWorker.ready")
        page.reload(wait_until="domcontentloaded")
        wait_for_source(page, "verified_corpus")
        evidence.require(page.evaluate("navigator.serviceWorker.controller !== null") is True, "offline: service worker controls the warmed shell")
        context.set_offline(True)
        page.reload(wait_until="domcontentloaded")
        wait_for_source(page, "verified_corpus")
        page.wait_for_function("document.querySelector('#connection-status')?.dataset.state === 'offline'")
        offline_copy = page.locator("#connection-copy").inner_text().strip()
        evidence.require("offline · verified corpus ready" == offline_copy.lower(), f"offline: local verified corpus remains available ({offline_copy!r})")
        evidence.require("Browser reports offline" in (page.locator("#connection-status").get_attribute("aria-label") or ""), "offline: browser connectivity is disclosed")
        page.locator('.bottom-nav [data-nav="learn"]').click()
        assert_view(evidence, page, "learn")
        evidence.require(not observed["external_requests"], f"offline: zero cross-origin requests ({observed['external_requests']})")
        evidence.require(not observed["console"], f"offline: zero console warnings or errors ({observed['console']})")
        evidence.require(not observed["page_errors"], f"offline: zero uncaught page errors ({observed['page_errors']})")
        evidence.journey("service-worker offline reload and navigation")
    finally:
        context.set_offline(False)
        context.close()


def run(args: argparse.Namespace) -> dict[str, Any]:
    if not MOBILE_ARENA.is_dir():
        raise AcceptanceFailure(f"mobile Arena directory is missing: {MOBILE_ARENA}")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise RuntimeError("Python Playwright is required: install it in the QA environment, not the production bundle") from error

    evidence = Evidence()
    browser_path = ""
    with loopback_server() as base_url, sync_playwright() as playwright:
        browser_path = playwright.chromium.executable_path
        evidence.require(Path(browser_path).is_file(), "environment: managed Chromium executable exists")
        browser = playwright.chromium.launch(headless=not args.headed)
        try:
            normal_journey(browser, base_url, evidence, args.headed)
            fallback_journey(browser, base_url, evidence)
            fatal_source_journey(browser, base_url, evidence)
            storage_denial_journey(browser, base_url, evidence)
            reduced_motion_journey(browser, base_url, evidence)
            offline_journey(browser, base_url, evidence)
        finally:
            browser.close()

    evidence.require(not any(thread.name == "builderwars-mobile-arena-http" and thread.is_alive() for thread in threading.enumerate()), "cleanup: loopback server thread stopped")
    return {
        "status": "PASS",
        "scope": "local browser evidence only",
        "browser": "chromium",
        "browserExecutable": browser_path,
        "checks": len(evidence.checks),
        "journeys": evidence.journeys,
        "viewports": [viewport["width"] for viewport in VIEWPORTS],
        "truthBoundary": {
            "hosted": False,
            "authenticated": False,
            "providerConnected": False,
            "liveCompetition": False,
            "productionReady": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headed", action="store_true", help="Show Chromium while retaining the same assertions.")
    args = parser.parse_args()
    try:
        result = run(args)
    except RuntimeError as error:
        print(json.dumps({"status": "BLOCKED_ENV", "message": str(error)}, indent=2))
        return 2
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error": type(error).__name__, "message": str(error)}, indent=2))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
