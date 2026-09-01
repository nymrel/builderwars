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
TESTER_RUBRIC_PATH = "**/data/tester-feedback-rubric.v1.json"
SHELL_VERSION = "30"
SHELL_CACHE_NAME = f"builderwars-mobile-arena-v{SHELL_VERSION}"
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
        "same_origin_requests": [],
    }

    def on_console(message: Any) -> None:
        if message.type in {"error", "warning"}:
            observed["console"].append(f"{label}:{message.type}:{message.text}")

    def on_request(request: Any) -> None:
        request_url = urlparse(request.url)
        if request_url.scheme in {"http", "https"} and request_url.netloc != urlparse(origin).netloc:
            observed["external_requests"].append(f"{label}:{request.method}:{request.url}")
        elif request_url.scheme in {"http", "https"}:
            query = f"?{request_url.query}" if request_url.query else ""
            observed["same_origin_requests"].append(f"{request_url.path}{query}")

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
        requested_resources = set(observed["same_origin_requests"])
        for resource in (f"/styles.css?v={SHELL_VERSION}", f"/data-adapter.js?v={SHELL_VERSION}", f"/app.js?v={SHELL_VERSION}", "/data/tester-feedback-rubric.v1.json"):
            evidence.require(resource in requested_resources, f"normal: installed HTML requests current shell resource {resource}")
        evidence.require(not any("?v=27" in resource for resource in requested_resources), "normal: retired v27 shell URLs are not requested")
        evidence.require(locator_visible(page, "#starter-panel"), "starter: first browser visit exposes the local starter guide")
        evidence.require(page.locator("[data-starter-action]").count() == 3, "starter: exactly three bounded first moves are available")
        starter_boundary = page.locator("#starter-boundary").inner_text().lower()
        evidence.require(all(term in starter_boundary for term in ("no account", "no provider", "no live match", "no publication")), "starter: protected boundaries are visible before any action")
        evidence.require(page.locator(".starter-grid").evaluate("node => node.scrollWidth > node.clientWidth"), "starter: phone layout exposes a horizontally scrollable action rail")
        page.locator(".starter-grid").evaluate("node => { node.scrollLeft = node.scrollWidth; }")
        evidence.require(page.locator(".starter-grid").evaluate("node => node.scrollLeft > 0"), "starter: later first moves remain reachable without document overflow")
        page.locator('[data-starter-action="proof"]').click()
        evidence.require(locator_visible(page, "#proof-sheet"), "starter: proof path opens the reviewed receipt inspector")
        evidence.require(page.locator("#starter-panel").is_hidden(), "starter: choosing a path closes the guide for this session")
        evidence.require(page.evaluate("localStorage.getItem('builderwars.mobile-arena.starter-guide.v1')") == "complete", "starter: completion persists only in the dedicated browser-local key")
        page.locator("#proof-sheet [data-sheet-close]").click()
        page.wait_for_function("document.querySelector('#proof-sheet').hidden === true")
        page.reload(wait_until="domcontentloaded")
        wait_for_source(page, "verified_corpus")
        evidence.require(page.locator("#starter-panel").is_hidden(), "starter: returning browser does not obscure the Arena")
        evidence.require(page.locator("#starter-guide-button").get_attribute("aria-expanded") == "false", "starter: returning state is announced as collapsed")
        page.locator("#starter-guide-button").click()
        evidence.require(locator_visible(page, "#starter-panel"), "starter: returning tester can reopen the guide")
        evidence.require(page.evaluate("document.activeElement?.id") == "starter-panel", "starter: reopened guide receives keyboard focus")
        page.locator('[data-starter-action="build"]').click()
        assert_view(evidence, page, "build")
        evidence.require(page.evaluate("document.activeElement?.id") == "agent-name", "starter: build path focuses the first local blueprint field")
        evidence.require(page.locator("#starter-panel").is_hidden(), "starter: reopened guide closes after the selected path")
        page.locator('.bottom-nav [data-nav="arena"]').click()
        evidence.journey("first-run starter, returning state, and re-open")
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

        storage_before_exhibition = page.evaluate("Object.fromEntries(Object.keys(localStorage).sort().map(key => [key, localStorage.getItem(key)]))")
        exhibition = page.locator('[data-qualification-preview]').filter(has_text="Practice")
        evidence.require(exhibition.count() == 1, "local exhibition: exactly one separate deterministic practice fixture is available")
        exhibition.click()
        exhibition_text = page.locator("#qualification-sheet").inner_text()
        evidence.require("Local exhibition qualified" in exhibition_text, "local exhibition: safe default blueprint qualifies for bounded practice")
        evidence.require("Browser memory only · available" in exhibition_text, "local exhibition: execution scope is browser memory only")
        evidence.require("metadata only · unused" in exhibition_text, "local exhibition: declared demo base is explicitly unused")
        evidence.require("all false" in exhibition_text, "local exhibition: every authority attestation remains false")
        page.locator("[data-local-exhibition-run]").click()
        page.wait_for_selector("#local-exhibition-result-title")
        result_text = page.locator("#qualification-content").inner_text()
        evidence.require("Replay verified" in result_text and "Receipt candidate\nVerified locally · unreviewed" in result_text, "local exhibition: receipt candidate is independently replay verified without review claim")
        evidence.require("Model/provider moves\n0 / 0" in result_text, "local exhibition: model and provider move counts remain zero")
        evidence.require("Version 1 · seat-swapped · unplayed" in result_text, "local exhibition: a versioned unplayed runback is prepared")
        evidence.require("Registry/ranking/publication\nNot requested / false / not requested" in result_text, "local exhibition: registry, ranking, and publication remain absent")
        candidate_digest = page.locator("#qualification-content .proof-row").filter(has_text="Candidate digest").locator("strong").inner_text()
        evidence.require(len(candidate_digest) == 64 and all(character in "0123456789abcdef" for character in candidate_digest), "local exhibition: receipt candidate exposes a content-shaped digest")
        page.locator("[data-local-exhibition-proof-share-prepare]").click()
        proof_share = page.locator("#local-exhibition-proof-share-export").input_value()
        proof_share_json = json.loads(proof_share)
        evidence.require(proof_share_json["schemaVersion"] == "builderwars.mobile-local-exhibition-proof-share.v1", "local exhibition share: output uses the versioned proof-share schema")
        evidence.require(proof_share_json["payload"]["proofRef"]["locator"] == f"builderwars-local-proof://receipt-candidate/{candidate_digest}", "local exhibition share: locator binds the exact embedded candidate")
        evidence.require(proof_share_json["payload"]["proofRef"]["publicUrl"] is None and proof_share_json["payload"]["publicationStatus"] == "not_requested", "local exhibition share: output creates no public URL or publication state")
        evidence.require(not any(proof_share_json["payload"]["attestations"].values()), "local exhibition share: output retains zero authority attestations")
        page.locator("#local-exhibition-proof-share-import").fill(proof_share)
        page.locator("[data-local-exhibition-proof-share-verify]").click()
        page.wait_for_selector(".local-exhibition-proof-share-status.verified, .local-exhibition-proof-share-status.invalid")
        imported_status = page.locator(".local-exhibition-proof-share-status").inner_text()
        evidence.require(page.locator(".local-exhibition-proof-share-status.verified").count() == 1 and "Embedded proof resolved" in imported_status and "all authority false" in imported_status, f"local exhibition share: same-page import independently resolves without authority ({imported_status})")
        page.locator("#local-exhibition-proof-share-import").fill(proof_share[:-1] + "x")
        page.locator("[data-local-exhibition-proof-share-verify]").click()
        evidence.require("Proof refused" in page.locator(".local-exhibition-proof-share-status.invalid").inner_text(), "local exhibition share: changed input fails closed")
        evidence.require(page.evaluate("Object.fromEntries(Object.keys(localStorage).sort().map(key => [key, localStorage.getItem(key)]))") == storage_before_exhibition, "local exhibition: qualification, play, proof, learning, and runback do not touch browser storage")
        page.locator("[data-local-exhibition-discard]").click()
        evidence.require(page.locator("#local-exhibition-result-title").count() == 0, "local exhibition: explicit discard clears the memory-only result")
        evidence.require("tracked receipt or remote state was deleted" in page.locator("#toast").inner_text().lower(), "local exhibition: discard does not imply tracked or remote deletion")
        page.locator("[data-local-exhibition-run]").click()
        page.wait_for_selector("#local-exhibition-result-title")
        page.reload(wait_until="domcontentloaded")
        wait_for_source(page, "verified_corpus")
        page.locator('.bottom-nav [data-nav="compete"]').click()
        page.locator('[data-qualification-preview]').filter(has_text="Practice").click()
        evidence.require(page.locator("#local-exhibition-result-title").count() == 0 and page.locator("[data-local-exhibition-run]").is_visible(), "local exhibition: reload clears the browser-memory receipt, learning, runback, and prepared share")
        evidence.require(page.locator("#local-exhibition-proof-share-import").input_value() == "", "local exhibition share: reload clears imported private proof text")
        page.locator("#local-exhibition-proof-share-import").fill(proof_share)
        page.locator("[data-local-exhibition-proof-share-verify]").click()
        page.wait_for_selector(".local-exhibition-proof-share-status.verified, .local-exhibition-proof-share-status.invalid")
        fresh_import_status = page.locator(".local-exhibition-proof-share-status").inner_text()
        evidence.require(page.locator(".local-exhibition-proof-share-status.verified").count() == 1 and candidate_digest in fresh_import_status and "replay PASS" in fresh_import_status, f"local exhibition share: fresh browser state resolves the embedded candidate and replay ({fresh_import_status})")
        evidence.require(page.locator("#local-exhibition-result-title").count() == 0, "local exhibition share: import does not promote the candidate into tracked local result state")
        evidence.require(page.evaluate("Object.fromEntries(Object.keys(localStorage).sort().map(key => [key, localStorage.getItem(key)]))") == storage_before_exhibition, "local exhibition share: prepare, verify, refusal, fresh import, and resolution remain storage free")
        page.keyboard.press("Escape")
        evidence.journey("deterministic local exhibition through receipt, learning, runback, portable proof resolution, discard, and reload cleanup")

        page.locator('.bottom-nav [data-nav="build"]').click()
        page.locator("#agent-name").fill("Browser Proof")
        page.locator("#builder-form button[type=submit]").click()
        evidence.require("saved locally" in page.locator("#toast").inner_text().lower(), "persistence: blueprint save is disclosed as browser-local")
        page.reload(wait_until="domcontentloaded")
        wait_for_source(page, "verified_corpus")
        page.locator('.bottom-nav [data-nav="build"]').click()
        evidence.require(page.locator("#agent-name").input_value() == "Browser Proof", "persistence: local blueprint survives reload")
        evidence.journey("local blueprint persistence")

        page.locator("#profile-button").click()
        evidence.require(locator_visible(page, "#session-sheet"), "local session: header control opens the browser-state dialog")
        evidence.require(page.locator("#session-sheet").evaluate("node => node.contains(document.activeElement)"), "local session: focus enters the dialog")
        session_boundary = page.locator("#session-boundary").inner_text().lower()
        evidence.require(all(term in session_boundary for term in ("no identity", "provider subscription", "credential", "remote profile", "live activity")), "local session: protected identity and provider boundaries are explicit")
        evidence.require(page.locator("#session-source-status").inner_text() == "Reviewed local corpus", "local session: exact bounded source is visible")
        evidence.require(page.locator("#session-blueprint-status").inner_text() == "Saved in this browser", "local session: saved browser blueprint is visible")
        evidence.require(page.locator("#session-starter-status").inner_text() == "Completed locally", "local session: starter completion is described as local")
        evidence.require(page.locator("#session-storage-status").inner_text() == "Available · browser only", "local session: storage scope is visible")
        evidence.require(page.locator("#session-account-status").inner_text() == "None" and page.locator("#session-provider-status").inner_text() == "None", "local session: account and provider remain absent")
        feedback_button = page.locator("[data-session-open-feedback]")
        evidence.require(feedback_button.is_enabled(), "tester feedback: verified canonical rubric enables the local worksheet")
        storage_before_feedback = page.evaluate("Object.fromEntries(Object.keys(localStorage).sort().map(key => [key, localStorage.getItem(key)]))")
        feedback_button.click()
        evidence.require(locator_visible(page, "#tester-feedback-sheet"), "tester feedback: local worksheet opens from session controls")
        evidence.require(page.locator("#tester-feedback-sheet").evaluate("node => node.contains(document.activeElement)"), "tester feedback: focus enters the worksheet dialog")
        feedback_boundary = page.locator("#tester-feedback-boundary").inner_text().lower()
        evidence.require(all(term in feedback_boundary for term in ("no name", "credential", "free text", "no feedback transport")), "tester feedback: identity, secret, free-text, and transport boundaries are explicit")
        rating_selects = page.locator("#tester-feedback-categories select")
        evidence.require(rating_selects.count() == 8, "tester feedback: canonical eight-category rubric is rendered exactly")
        for index in range(8):
            rating_selects.nth(index).select_option(str((index % 5) + 1))
        page.locator("#tester-feedback-blocker").select_option("provider_boundary")
        page.locator("#tester-feedback-severe").select_option("truth_overclaim")
        page.locator("[data-tester-feedback-generate]").click()
        evidence.require(locator_visible(page, "#tester-feedback-output"), "tester feedback: complete structured selections create a visible draft")
        feedback_serialized = page.locator("#tester-feedback-json").input_value()
        feedback_draft = json.loads(feedback_serialized)
        evidence.require(feedback_draft["draftStatus"] == "LOCAL_DRAFT_NOT_COLLECTED", "tester feedback: draft cannot be mistaken for collected feedback")
        evidence.require(len(feedback_draft["ratings"]) == 8 and [row["rating"] for row in feedback_draft["ratings"]] == [1, 2, 3, 4, 5, 1, 2, 3], "tester feedback: exact structured ratings survive canonicalization")
        evidence.require(feedback_draft["blockerClass"] == "provider_boundary" and feedback_draft["severeIssueClass"] == "truth_overclaim", "tester feedback: bounded triage classes survive canonicalization")
        evidence.require(feedback_draft["identityFieldsAllowed"] == [] and feedback_draft["freeTextIncluded"] is False, "tester feedback: identity and free text stay absent")
        evidence.require(feedback_draft["storageMode"] == "browser_memory_only" and feedback_draft["transportStatus"] == "not_configured" and feedback_draft["submissionStatus"] == "not_submitted", "tester feedback: storage, transport, and submission stay absent")
        evidence.require(feedback_draft["humanFeedbackCollected"] is False and not any(feedback_draft["productionAuthority"].values()), "tester feedback: human evidence and production authority stay false")
        evidence.require(len(feedback_draft["draftDigest"]) == 64, "tester feedback: canonical draft carries a content-shaped digest")
        evidence.require(page.evaluate("Object.fromEntries(Object.keys(localStorage).sort().map(key => [key, localStorage.getItem(key)]))") == storage_before_feedback, "tester feedback: draft generation does not touch browser storage")
        page.locator("#tester-feedback-sheet [data-sheet-close]").click()
        evidence.require(page.evaluate("document.activeElement?.id") == "profile-button", "tester feedback: close restores the local-session trigger focus")
        page.reload(wait_until="domcontentloaded")
        wait_for_source(page, "verified_corpus")
        page.locator("#profile-button").click()
        page.locator("[data-session-open-feedback]").click()
        evidence.require(page.locator("#tester-feedback-output").is_hidden() and page.locator("#tester-feedback-json").input_value() == "", "tester feedback: reload clears the browser-memory-only draft")
        evidence.require(page.locator("#tester-feedback-categories select").first.input_value() == "", "tester feedback: reload clears every structured selection")
        page.locator("#tester-feedback-sheet [data-sheet-close]").click()
        page.locator("#profile-button").click()
        evidence.journey("identity-free memory-only tester feedback draft and reload cleanup")
        remove_button = page.locator("[data-session-remove-blueprint]")
        remove_button.click()
        evidence.require(remove_button.inner_text() == "Confirm remove blueprint", "local cleanup: first press only arms blueprint removal")
        evidence.require(page.evaluate("localStorage.getItem('builderwars.mobile-arena.blueprint.v1') !== null") is True, "local cleanup: armed removal retains the blueprint")
        remove_button.click()
        evidence.require(page.evaluate("localStorage.getItem('builderwars.mobile-arena.blueprint.v1')") is None, "local cleanup: second press removes only the browser-local blueprint")
        evidence.require(page.locator("#session-blueprint-status").inner_text() == "Not saved", "local cleanup: session status reflects removal")
        evidence.require(remove_button.is_disabled(), "local cleanup: removal disables when no saved blueprint remains")
        evidence.require(page.locator("#agent-name").input_value() == "Fourth Quarter", "local cleanup: visible blueprint form returns to tracked defaults")
        cleanup_toast = page.locator("#toast").inner_text().lower()
        evidence.require("browser-only blueprint removed" in cleanup_toast and "tracked source files were not deleted" in cleanup_toast, "local cleanup: receipt and source preservation is explicit")
        page.locator("[data-session-restart-starter]").click()
        evidence.require(locator_visible(page, "#starter-panel"), "local session: starter guide can be restarted without an account")
        evidence.require(page.evaluate("document.activeElement?.id") == "starter-panel", "local session: restarted guide receives keyboard focus")
        evidence.require(page.evaluate("localStorage.getItem('builderwars.mobile-arena.starter-guide.v1')") is None, "local session: restart clears only the browser-local guide completion")
        page.locator("[data-starter-dismiss]").click()
        evidence.journey("local session inspection and two-step cleanup")

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


def tester_rubric_failure_journey(browser: Any, base_url: str, evidence: Evidence) -> None:
    context = browser.new_context(viewport=VIEWPORTS[0], service_workers="allow")
    page = context.new_page()
    observed = install_observers(page, base_url, "tester-rubric-failure")
    try:
        page.route(TESTER_RUBRIC_PATH, lambda route: route.fulfill(status=200, content_type="application/json", body="{}"))
        page.goto(base_url, wait_until="domcontentloaded")
        wait_for_source(page, "verified_corpus")
        evidence.require(page.locator("#source-badge").inner_text() == "LOCAL CORPUS", "tester rubric failure: the reviewed Arena remains available")
        page.locator("#profile-button").click()
        feedback_button = page.locator("[data-session-open-feedback]")
        evidence.require(feedback_button.is_disabled(), "tester rubric failure: worksheet trigger fails closed")
        evidence.require(feedback_button.inner_text() == "Tester worksheet unavailable", "tester rubric failure: unavailable state is explicit")
        evidence.require(not observed["external_requests"], f"tester rubric failure: no remote substitute is requested ({observed['external_requests']})")
        assert_observers_clean(evidence, observed, "tester-rubric-failure")
        evidence.journey("invalid tester rubric fails closed without hiding the Arena")
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
        evidence.require(locator_visible(page, "#starter-panel"), "storage denial: first-run guide remains usable")
        evidence.require(page.evaluate("document.documentElement.scrollWidth <= innerWidth") is True, "storage denial: visible starter guide fits the 320px viewport")
        evidence.require("storage is unavailable" in page.locator("#starter-persistence").inner_text().lower(), "storage denial: guide persistence limit is explicit")
        page.locator("[data-starter-dismiss]").click()
        evidence.require("hidden for this page" in page.locator("#toast").inner_text().lower(), "storage denial: guide dismissal is session-scoped")
        evidence.require("nothing was uploaded" in page.locator("#toast").inner_text().lower(), "storage denial: guide dismissal does not imply a remote fallback")
        page.reload(wait_until="domcontentloaded")
        wait_for_source(page, "verified_corpus")
        evidence.require(locator_visible(page, "#starter-panel"), "storage denial: guide returns after reload when completion cannot persist")
        page.locator('.bottom-nav [data-nav="build"]').click()
        page.locator("#agent-name").fill("Denied Storage")
        page.locator("#builder-form button[type=submit]").click()
        evidence.require("could not be saved" in page.locator("#toast").inner_text().lower(), "storage denial: save failure is explicit")
        evidence.require("nothing was uploaded or executed" in page.locator("#toast").inner_text().lower(), "storage denial: failure does not imply remote fallback")
        page.locator("#profile-button").click()
        evidence.require(locator_visible(page, "#session-sheet"), "storage denial: local-session dialog remains available")
        evidence.require(page.locator("#session-storage-status").inner_text() == "Unavailable · page session only", "storage denial: local-session storage limit is explicit")
        evidence.require(page.locator("#session-blueprint-status").inner_text() == "Unavailable to inspect", "storage denial: blueprint state is not guessed")
        evidence.require(page.locator("[data-session-remove-blueprint]").is_disabled(), "storage denial: destructive control stays disabled without inspectable local state")
        evidence.require(page.locator("#session-account-status").inner_text() == "None" and page.locator("#session-provider-status").inner_text() == "None", "storage denial: no account or provider fallback is implied")
        page.locator("[data-session-open-feedback]").click()
        evidence.require(locator_visible(page, "#tester-feedback-sheet"), "storage denial: memory-only tester worksheet remains available")
        rating_selects = page.locator("#tester-feedback-categories select")
        for index in range(8):
            rating_selects.nth(index).select_option("3")
        page.locator("#tester-feedback-blocker").select_option("none")
        page.locator("#tester-feedback-severe").select_option("none")
        page.locator("[data-tester-feedback-generate]").click()
        denied_feedback = json.loads(page.locator("#tester-feedback-json").input_value())
        evidence.require(denied_feedback["storageMode"] == "browser_memory_only" and denied_feedback["submissionStatus"] == "not_submitted", "storage denial: tester draft remains memory-only and unsubmitted")
        page.locator("#tester-feedback-sheet [data-sheet-close]").click()
        page.locator("#profile-button").click()
        page.locator("[data-session-restart-starter]").click()
        evidence.require(locator_visible(page, "#starter-panel"), "storage denial: starter restart remains usable in the page session")
        evidence.require(page.evaluate("document.activeElement?.id") == "starter-panel", "storage denial: restarted guide receives focus")
        evidence.require("nothing was uploaded" in page.locator("#toast").inner_text().lower(), "storage denial: starter restart does not imply a remote fallback")
        assert_observers_clean(evidence, observed, "storage-denied")
        evidence.journey("storage-denied local session and blueprint")
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
        cache_state = page.evaluate(
            """async () => {
              const keys = (await caches.keys()).sort();
              const cache = await caches.open('builderwars-mobile-arena-v30');
              const urls = (await cache.keys()).map((request) => {
                const url = new URL(request.url);
                return `${url.pathname}${url.search}`;
              }).sort();
              return { keys, urls };
            }"""
        )
        evidence.require(cache_state["keys"] == [SHELL_CACHE_NAME], f"offline: exactly the current shell cache is installed ({cache_state['keys']!r})")
        for resource in (f"/index.html?v={SHELL_VERSION}", f"/styles.css?v={SHELL_VERSION}", f"/data-adapter.js?v={SHELL_VERSION}", f"/app.js?v={SHELL_VERSION}"):
            evidence.require(resource in cache_state["urls"], f"offline: current shell cache contains {resource}")
        evidence.require("/data/tester-feedback-rubric.v1.json" in cache_state["urls"], "offline: canonical tester rubric is cached with the current shell")
        evidence.require(not any("?v=27" in resource for resource in cache_state["urls"]), "offline: current shell cache excludes retired v27 URLs")
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
            tester_rubric_failure_journey(browser, base_url, evidence)
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
