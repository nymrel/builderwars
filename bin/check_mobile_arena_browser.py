#!/usr/bin/env python3
"""Run durable real-browser acceptance for the local BuilderWars Mobile Arena.

This check deliberately uses only a loopback HTTP server and tracked local
fixtures. It proves browser behavior, not hosting, authentication, provider
access, live competition, identity, publication, or production readiness.
"""

from __future__ import annotations

import argparse
import json
import re
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
CREATOR_GAME_LAB_PATH = "**/data/creator-game-lab.v1.json"
SHELL_VERSION = "41"
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
        yield f"http://{host}:{port}/index.html?v={SHELL_VERSION}"
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
    page.wait_for_function(
        "() => document.body.dataset.sourceMode !== 'loading' && "
        "document.querySelector('#connection-status')?.dataset.state !== 'loading'",
    )
    actual = page.evaluate(
        "() => ({mode: document.body.dataset.sourceMode || null, "
        "state: document.querySelector('#connection-status')?.dataset.state || null, "
        "copy: document.querySelector('#connection-copy')?.textContent?.trim() || null})"
    )
    if actual["mode"] != source_mode:
        raise AcceptanceFailure(f"source resolved unexpectedly at {page.url}: expected {source_mode!r}, observed {actual!r}")


def wait_for_blitz_source(page: Any, source_mode: str) -> None:
    page.wait_for_function(
        "() => document.body.dataset.sourceMode !== 'loading' && "
        "document.querySelector('#blitz-source-status')?.dataset.state !== 'loading' && "
        "document.querySelector('#ten-fronts-blitz-root')?.getAttribute('aria-busy') === 'false'",
    )
    actual = page.evaluate(
        "() => ({mode: document.body.dataset.sourceMode || null, "
        "state: document.querySelector('#blitz-source-status')?.dataset.state || null, "
        "copy: document.querySelector('#blitz-source-status')?.textContent?.trim() || null})"
    )
    if actual["mode"] != source_mode:
        raise AcceptanceFailure(f"Blitz source resolved unexpectedly at {page.url}: expected {source_mode!r}, observed {actual!r}")


def install_observers(page: Any, origin: str, label: str) -> dict[str, list[str]]:
    observed: dict[str, list[str]] = {
        "console": [],
        "page_errors": [],
        "external_requests": [],
        "same_origin_requests": [],
    }

    def on_console(message: Any) -> None:
        if message.type in {"error", "warning"}:
            location = message.location.get("url", "") if isinstance(message.location, dict) else ""
            observed["console"].append(f"{label}:{message.type}:{message.text}:{location}")

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
        for resource in (f"/styles.css?v={SHELL_VERSION}", f"/data-adapter.js?v={SHELL_VERSION}", f"/app.js?v={SHELL_VERSION}", "/data/tester-feedback-rubric.v1.json", "/data/creator-game-lab.v1.json"):
            evidence.require(resource in requested_resources, f"normal: installed HTML requests current shell resource {resource}")
        evidence.require(not any("?v=30" in resource for resource in requested_resources), "normal: retired v30 shell URLs are not requested")
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
        evidence.require("not ranked" in page.locator("#standings-help").inner_text().lower(), "normal: ranking boundary stays visible")
        entry_boundary_text = page.locator("#entry-boundary").text_content() or ""
        evidence.require("Read-only proof" in entry_boundary_text and "Competition entry disabled" in entry_boundary_text, "normal: compete header exposes access boundary instead of credits")
        watch_metric_count = page.locator(".watch-item .watch-metric").count()
        receipt_tracks = [label.lower() for label in page.locator(".watch-item .receipt-track").all_inner_texts()]
        evidence.require(watch_metric_count == 5 and receipt_tracks.count("reviewed local corpus") == 5, f"normal: watch strip uses receipt counts without market deltas or charts (metrics={watch_metric_count}, tracks={receipt_tracks!r})")
        evidence.require(page.locator(".live-dot, .sparkline, .delta, .credit-readout").count() == 0, "normal: shell renders no live pulse, trend chart, delta, or credit widget")

        for view in ("watch", "compete", "learn", "build", "arena"):
            page.locator(f'.bottom-nav [data-nav="{view}"]').click()
            assert_view(evidence, page, view)
        evidence.journey("five-destination navigation")

        page.locator('.bottom-nav [data-nav="build"]').click()
        evidence.require(page.locator("#showcase-capabilities .showcase-capability").count() == 6, "builder showcase: all six craft surfaces are visible")
        evidence.require(page.locator("#showcase-draft-count").inner_text() == "2/6", "builder showcase: tracked default includes only agent and harness drafts")
        showcase_boundary = page.locator(".showcase-boundary").inner_text().lower()
        evidence.require(all(term in showcase_boundary for term in ("browser-local", "no builder identity", "ownership", "authorship", "ranking", "publication")), "builder showcase: identity, ownership, authorship, ranking, and publication boundaries are explicit")
        page.locator('[data-showcase-select="receipt"]').click()
        evidence.require("not builder-owned" in page.locator("#showcase-focus").inner_text().lower(), "builder showcase: Arena receipts cannot imply builder ownership")
        evidence.require(page.locator('[data-showcase-toggle="receipt"]').get_attribute("aria-pressed") == "false", "builder showcase: referenced proof is not included by default")
        page.locator('[data-showcase-select="agent"]').click()
        evidence.journey("six-surface local Builder Showcase and proof-ownership boundary")
        creator_lab = page.locator("#creator-game-lab")
        evidence.require(creator_lab.is_visible(), "creator game: reviewed candidate lab is visible in Build")
        creator_text = creator_lab.inner_text()
        evidence.require("signal siege" in creator_text.lower() and "not admitted" in creator_text.lower(), "creator game: exact candidate identity and held status are visible")
        evidence.require("Never imported or executed" in creator_text and creator_text.count("Not authorized") == 3, "creator game: code, runtime, ranking, and publication boundaries are visible")
        evidence.require(page.locator("#creator-game-lab .creator-fronts li").count() == 5, "creator game: five reviewed weighted fronts render")
        page.locator('#creator-game-lab [data-nav="learn"]').click()
        assert_view(evidence, page, "learn")
        evidence.require(page.locator("#creator-game-lesson .creator-admission-list li").count() == 8, "creator game: all eight admission gates remain visible")
        evidence.require("cannot complete, waive, or attest" in page.locator("#creator-game-lesson").inner_text(), "creator game: browser authority limit is explicit")
        evidence.journey("reviewed declarative creator-game candidate through Build and Learn")

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
        trust_chips = page.locator(".proof-trust-chip")
        evidence.require(trust_chips.count() == 3, "proof: exactly three first-glance trust signals render")
        replay_signal = page.locator('[data-proof-trust="replay"]').inner_text().splitlines()
        binding_signal = page.locator('[data-proof-trust="binding"]').inner_text().splitlines()
        attribution_signal = page.locator('[data-proof-trust="attribution"]').inner_text().splitlines()
        evidence.require(replay_signal == ["REPLAY", "PASS", "Receipt replay agrees"], f"proof: replay signal is concise and predicate-derived ({replay_signal!r})")
        evidence.require(binding_signal == ["BUILD BINDING", "BOUND", "Engine, verifier, harness"], f"proof: build-binding signal summarizes the exact three bindings ({binding_signal!r})")
        evidence.require(attribution_signal == ["ATTRIBUTION", "UNATTESTED", "0/3 model, provider, runtime"], f"proof: attribution signal cannot inflate current evidence ({attribution_signal!r})")
        proof_details = page.locator(".proof-predicates")
        evidence.require(proof_details.get_attribute("open") is None and not page.locator("#proof-content .proof-grid").is_visible(), "proof: detailed predicates start collapsed")
        proof_summary = proof_details.locator("summary")
        evidence.require(proof_summary.evaluate("node => node.getBoundingClientRect().height") >= 44, "proof: predicate disclosure has a touch-safe target")
        page.keyboard.press("Tab")
        evidence.require(proof_summary.evaluate("node => document.activeElement === node"), "proof: predicate disclosure follows the close control in keyboard order")
        evidence.require(proof_summary.evaluate("node => getComputedStyle(node).outlineStyle") != "none", "proof: predicate disclosure has visible keyboard focus")
        proof_summary.click()
        evidence.require(proof_details.get_attribute("open") is not None and page.locator("#proof-content .proof-grid").is_visible(), "proof: one action expands every detailed predicate")
        predicate_codes = page.locator(".proof-summary-predicates code").all_inner_texts()
        evidence.require(predicate_codes == ['replayVerdict === "PASS"', "engineDigestMatch && verifierSnapshotMatch && harnessVersionBound", "modelAttested && providerAttested && runtimeAttested"], "proof: all three summary predicates are inspectable verbatim")
        proof_text = page.locator("#proof-content").inner_text()
        evidence.require("No authoritative commit" in proof_text, "proof: registry authority remains absent")
        evidence.require("Correction status\nActive · no correction recorded" in proof_text, "proof: tracked receipt shows truthful active correction state")
        evidence.require("Model attested\nNo" in proof_text and "Provider attested\nNo" in proof_text and "Runtime attested\nNo" in proof_text, "proof: model, provider, and runtime attestations remain false")
        evidence.require("Not supplied · self-declared legacy identity" in proof_text, "proof: current legacy entrants disclose that no Agent Passport was supplied")
        evidence.require("Identity scope\nPerson, model, provider, and runtime unattested" in proof_text, "proof: passport scope cannot inflate person, model, provider, or runtime identity")
        storage_before_spectator = page.evaluate("Object.fromEntries(Object.keys(localStorage).sort().map(key => [key, localStorage.getItem(key)]))")
        evidence.require(page.locator("[data-spectator-choice]").count() == 3, "spectator rehearsal: exactly two receipt entrants and one runback choice are available")
        rehearsal_boundary = page.locator(".spectator-rehearsal").inner_text().lower()
        evidence.require(all(term in rehearsal_boundary for term in ("browser-memory", "already exists", "not a prediction", "not collected")), "spectator rehearsal: preexisting-result and non-collection boundaries are visible before choosing")
        page.locator('[data-spectator-choice="seat0"]').click()
        sealed_status = page.locator(".spectator-rehearsal-status").inner_text()
        evidence.require("Local choice sealed" in sealed_status and "no trusted timestamp" in sealed_status and "not collected" in sealed_status, "spectator rehearsal: local choice is sealed without prediction or collection claim")
        sealed_digest = page.locator(".spectator-rehearsal-status span").first.inner_text().split("SHA-256 ")[-1]
        evidence.require(len(sealed_digest) == 64 and all(character in "0123456789abcdef" for character in sealed_digest), "spectator rehearsal: local choice exposes a content-shaped digest")
        evidence.require(page.locator('[data-spectator-reveal]').count() == 1 and page.locator('[data-spectator-verify]').count() == 0, "spectator rehearsal: reveal precedes verification")
        page.locator("[data-spectator-reveal]").click()
        reveal_text = page.locator(".spectator-rehearsal-reveal").inner_text().lower()
        evidence.require("reviewed result" in reveal_text and "does not grade the local choice" in reveal_text, "spectator rehearsal: reveal shows reviewed evidence without grading the choice")
        evidence.require(page.locator('[data-spectator-verify]').count() == 1, "spectator rehearsal: exact verification becomes available only after reveal")
        page.locator("[data-spectator-verify]").click()
        page.wait_for_selector(".spectator-rehearsal-status.verified")
        verified_rehearsal = page.locator(".spectator-rehearsal").inner_text()
        evidence.require("Reviewed receipt binding verified" in verified_rehearsal and "Receipt binding PASS" in verified_rehearsal, "spectator rehearsal: exact reviewed receipt binding passes")
        evidence.require("Available as a separate unplayed proposal" in verified_rehearsal, "spectator rehearsal: runback remains a separate unplayed proposal")
        evidence.require(page.evaluate("Object.fromEntries(Object.keys(localStorage).sort().map(key => [key, localStorage.getItem(key)]))") == storage_before_spectator, "spectator rehearsal: choose, reveal, and verify do not touch browser storage")
        page.locator("#proof-learning-button").click()
        assert_view(evidence, page, "learn")
        evidence.require(page.locator("#receipt-learning").is_visible(), "spectator rehearsal: verified proof reaches receipt-linked learning")
        evidence.require(page.locator("[data-runback-delta]").count() == 3, "spectator rehearsal: learning exposes only the three bounded blueprint deltas")
        page.locator("[data-runback-delta]").first.click()
        evidence.require("Still unplayed" in page.locator("#runback-proposal").inner_text(), "spectator rehearsal: runback proposal remains explicitly unplayed")
        evidence.journey("reviewed receipt spectator rehearsal through choose, reveal, verify, and still-unplayed runback")

        page.locator('.bottom-nav [data-nav="arena"]').click()
        proof_trigger.click()
        evidence.require(locator_visible(page, "#proof-sheet"), "proof: inspector reopens after spectator rehearsal")
        page.keyboard.press("Shift+Tab")
        evidence.require(page.locator("#proof-sheet").evaluate("node => node.contains(document.activeElement)"), "proof: reverse tab stays inside dialog")
        page.keyboard.press("Escape")
        page.wait_for_function("document.querySelector('#proof-sheet').hidden === true")
        evidence.require(page.url.endswith("#arena"), "proof: Escape restores the containing route")
        evidence.require(page.evaluate("document.activeElement?.hasAttribute('data-proof-open')") is True, "proof: close restores trigger focus")
        evidence.journey("receipt proof dialog and focus lifecycle")

        proof_trigger.click()
        page.locator('[data-spectator-choice="seat1"]').click()
        evidence.require("Local choice sealed" in page.locator(".spectator-rehearsal-status").inner_text(), "spectator rehearsal cleanup: a second memory-only choice exists before reload")
        page.reload(wait_until="domcontentloaded")
        wait_for_source(page, "verified_corpus")
        page.wait_for_selector("#proof-sheet:not([hidden])")
        evidence.require("No local choice" in page.locator(".spectator-rehearsal-status").inner_text(), "spectator rehearsal cleanup: reload clears the uncollected choice")
        evidence.require(page.evaluate("Object.fromEntries(Object.keys(localStorage).sort().map(key => [key, localStorage.getItem(key)]))") == storage_before_spectator, "spectator rehearsal cleanup: reload leaves browser storage unchanged")
        page.keyboard.press("Escape")
        evidence.journey("spectator rehearsal reload cleanup")

        unknown_receipt = "f" * 64
        page.goto(f"{base_url}#watch/receipt/{unknown_receipt}", wait_until="domcontentloaded")
        wait_for_source(page, "verified_corpus")
        page.wait_for_function("location.hash === '#watch'")
        evidence.require(page.url.endswith("#watch"), "unknown proof: route fails closed to its containing view")
        evidence.require(page.locator("#proof-sheet").is_hidden(), "unknown proof: no substitute receipt is opened")
        evidence.journey("unknown proof fail-closed routing")

        page.locator('.bottom-nav [data-nav="compete"]').click()
        spotlight = page.locator("#local-play-spotlight")
        spotlight_text = spotlight.inner_text()
        evidence.require(spotlight.locator('[data-local-play-state="ready"]').count() == 1, "local play spotlight: safe default blueprint is visibly ready")
        evidence.require("Run a complete local proof loop" in spotlight_text and "zero provider calls" in spotlight_text, "local play spotlight: both deterministic local formats and provider boundary are first-class")
        evidence.require("No sign-in, model inference, provider access, persistence, ranking, registry, or publication" in spotlight_text, "local play spotlight: authority boundary is visible before entry")
        evidence.require(spotlight.locator("[data-qualification-preview]").count() == 1 and spotlight.locator("[data-ten-fronts-blitz-link]").count() == 1 and page.locator("#quick-matches").inner_text().count("Practice") == 0, "local play spotlight: Nim and Ten Fronts are promoted without a duplicate format row")
        evidence.require(page.locator("#quick-title").inner_text() == "Other proposed formats", "local play spotlight: inactive formats remain secondary")
        preview = page.locator("#quick-matches [data-qualification-preview]").first
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
        exhibition = page.locator('#local-play-spotlight [data-qualification-preview]')
        evidence.require(exhibition.count() == 1, "local exhibition: exactly one prominent deterministic practice fixture is available")
        exhibition.click()
        exhibition_text = page.locator("#qualification-sheet").inner_text()
        evidence.require("Local exhibition qualified" in exhibition_text, "local exhibition: safe default blueprint qualifies for bounded practice")
        evidence.require("Browser memory only · available" in exhibition_text, "local exhibition: execution scope is browser memory only")
        evidence.require("metadata only · unused" in exhibition_text, "local exhibition: declared demo base is explicitly unused")
        evidence.require("all false" in exhibition_text, "local exhibition: every authority attestation remains false")
        page.locator("[data-local-exhibition-run]").click()
        page.wait_for_selector("#local-exhibition-result-title")
        spotlight_state = page.locator("#local-play-spotlight [data-local-play-state]").get_attribute("data-local-play-state")
        spotlight_result_text = page.locator("#local-play-spotlight").inner_text()
        evidence.require(spotlight_state == "result" and "receipt in memory" in spotlight_result_text.lower(), f"local exhibition: spotlight reflects the memory-only result without claiming publication (state={spotlight_state!r}, text={spotlight_result_text!r})")
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
        page.keyboard.press("Escape")
        page.locator('.bottom-nav [data-nav="build"]').click()
        page.locator("#agent-name").fill("Revised Browser Proof")
        page.locator('.bottom-nav [data-nav="compete"]').click()
        evidence.require(page.locator('#local-play-spotlight [data-local-play-state="ready"]').count() == 1 and "Revised Browser Proof" in page.locator("#local-play-spotlight").inner_text(), "local exhibition: a changed blueprint cannot inherit the prior receipt status")
        page.locator('#local-play-spotlight [data-qualification-preview]').click()
        evidence.require(page.locator("#local-exhibition-result-title").count() == 0 and page.locator("[data-local-exhibition-run]").is_visible(), "local exhibition: opening the changed qualification clears the stale result chain")
        evidence.require(page.locator("#local-exhibition-proof-share-import").input_value() == "", "local exhibition: changed qualification clears stale private proof text")
        evidence.require(page.evaluate("Object.fromEntries(Object.keys(localStorage).sort().map(key => [key, localStorage.getItem(key)]))") == storage_before_exhibition, "local exhibition: unsaved blueprint revision and stale-result cleanup remain storage free")
        page.locator("[data-local-exhibition-run]").click()
        page.wait_for_selector("#local-exhibition-result-title")
        page.locator("[data-local-exhibition-discard]").click()
        evidence.require(page.locator("#local-exhibition-result-title").count() == 0, "local exhibition: explicit discard clears the memory-only result")
        evidence.require(page.locator('#local-play-spotlight [data-local-play-state="ready"]').count() == 1, "local exhibition: discard returns the spotlight to the locally ready state")
        evidence.require("tracked receipt or remote state was deleted" in page.locator("#toast").inner_text().lower(), "local exhibition: discard does not imply tracked or remote deletion")
        page.locator("[data-local-exhibition-run]").click()
        page.wait_for_selector("#local-exhibition-result-title")
        page.reload(wait_until="domcontentloaded")
        wait_for_source(page, "verified_corpus")
        page.locator('.bottom-nav [data-nav="compete"]').click()
        page.locator('#local-play-spotlight [data-qualification-preview]').click()
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
        page.locator("#builder-name").fill("Nymrel Studio")
        page.locator("#builder-focus").select_option("Competition design")
        page.locator('[data-showcase-select="game"]').click()
        page.locator('[data-showcase-toggle="game"]').click()
        evidence.require(page.locator("#showcase-draft-count").inner_text() == "3/6", "builder showcase: adding one capability updates only the local draft")
        evidence.require("nothing was published" in page.locator("#toast").inner_text().lower(), "builder showcase: draft mutation denies publication")
        page.locator("#agent-name").fill("Browser Proof")
        page.locator("#builder-form button[type=submit]").click()
        evidence.require("saved locally" in page.locator("#toast").inner_text().lower(), "persistence: blueprint save is disclosed as browser-local")
        page.reload(wait_until="domcontentloaded")
        wait_for_source(page, "verified_corpus")
        page.locator('.bottom-nav [data-nav="build"]').click()
        evidence.require(page.locator("#agent-name").input_value() == "Browser Proof", "persistence: local blueprint survives reload")
        evidence.require(page.locator("#builder-name").input_value() == "Nymrel Studio" and page.locator("#builder-focus").input_value() == "Competition design", "builder showcase: local builder identity draft survives explicit save and reload")
        evidence.require(page.locator("#showcase-draft-count").inner_text() == "3/6", "builder showcase: selected capability set survives explicit save and reload")
        page.locator('[data-showcase-select="game"]').click()
        evidence.require(page.locator('[data-showcase-toggle="game"]').get_attribute("aria-pressed") == "true", "builder showcase: restored capability is announced as included")
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
        evidence.require(page.locator("#builder-name").input_value() == "Local Builder" and page.locator("#showcase-draft-count").inner_text() == "2/6", "local cleanup: Builder Showcase returns to tracked defaults")
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
        evidence.require("Demo roster" == page.locator("#standings-title").inner_text(), "fallback: unranked demo roster label is restored")
        evidence.require("not ranked" in page.locator("#standings-help").inner_text().lower(), "fallback: ranking refusal remains visible")
        evidence.require("simulated fixture" in page.locator("#featured-match").inner_text().lower(), "fallback: featured content is labeled simulated")
        evidence.require(page.locator("#tape-title").inner_text() == "Demo walkthrough", "fallback: static guidance replaces fake current activity")
        evidence.require(page.locator(".fixture-dot").count() == 1 and page.locator(".fixture-dot").evaluate("node => getComputedStyle(node).animationName") == "none", "fallback: simulated fixture marker is static")
        page.locator('.bottom-nav [data-nav="watch"]').click()
        board_text = page.locator("#leaderboard").inner_text()
        evidence.require("no reviewed receipts" in board_text.lower() and board_text.lower().count("not ranked") == 4, "fallback: demo entrants carry zero receipt and no-ranking boundaries")
        evidence.require(not re.search(r"\b(?:1548|1512|1489|1461|8-2|7-3|6-4|5-5)\b", board_text), "fallback: invented ratings and records are absent")
        channels_text = page.locator("#channels").inner_text().lower()
        evidence.require(channels_text.count("no audience data") == 5 and "viewers" not in channels_text, "fallback: channels deny audience counts")
        page.locator('.bottom-nav [data-nav="compete"]').click()
        evidence.require(page.locator("#entry-boundary").inner_text().splitlines() == ["Static preview only", "No account, provider, or local execution"], "fallback: access denies account, provider, and local execution")
        fallback_spotlight = page.locator("#local-play-spotlight")
        evidence.require(fallback_spotlight.locator('[data-local-play-state="held"]').count() == 1, "fallback: local-play spotlight fails closed")
        evidence.require("No executable fixture loaded" in fallback_spotlight.inner_text() and "static previews" in fallback_spotlight.inner_text().lower(), "fallback: held spotlight explains why no substitute match exists")
        evidence.require(fallback_spotlight.locator("[data-qualification-preview], [data-local-exhibition-run]").count() == 0, "fallback: held spotlight exposes no execution control")
        evidence.require(page.locator("#quick-title").inner_text() == "Static format previews", "fallback: inactive demo formats are not labeled as live matches")
        evidence.require(page.locator("#quick-matches").inner_text().count("Local preview · no provider call") == 3, "fallback: every quick match denies provider execution")
        evidence.require(page.locator("#quick-matches [data-queue]").all_inner_texts() == ["Explore format", "Explore format", "Explore format"], "fallback: demo controls do not claim queue entry")
        model_text = page.locator("#free-models").inner_text()
        evidence.require(model_text.count("Mock response only") == 2 and "quota" not in model_text.lower(), "fallback: local stubs expose no invented provider quota")
        page.locator("#notifications-button").click()
        evidence.require(page.locator("#automations input:checked").count() == 0 and "streak" not in page.locator("#automations").inner_text().lower(), "fallback: reminders are off and no streak is claimed")
        page.locator("#automations-sheet [data-sheet-close]").click()
        page.locator('.bottom-nav [data-nav="arena"]').click()
        page.locator("#featured-match [data-proof-open]").first.click()
        fallback_chips = page.locator(".proof-trust-chip")
        evidence.require(fallback_chips.count() == 3, "fallback proof: exactly three first-glance trust signals render")
        evidence.require(page.locator('[data-proof-trust="replay"]').inner_text().splitlines() == ["REPLAY", "DEMO PASS", "Static fixture replay only"], "fallback proof: simulated replay status cannot masquerade as reviewed-corpus proof")
        evidence.require(page.locator('[data-proof-trust="binding"]').inner_text().splitlines() == ["BUILD BINDING", "BOUND", "Demo harness only"], "fallback proof: binding scope is limited to the demo harness")
        evidence.require(page.locator('[data-proof-trust="attribution"]').inner_text().splitlines() == ["ATTRIBUTION", "UNATTESTED", "0/3 model, provider, runtime"], "fallback proof: provider and model attribution remain unattested")
        page.locator(".proof-predicates > summary").click()
        fallback_predicates = page.locator(".proof-summary-predicates code").all_inner_texts()
        evidence.require(fallback_predicates[0] == 'replayVerdict === "PASS_DEMO_FIXTURE"', "fallback proof: expanded predicate names the demo-only replay verdict")
        evidence.require(fallback_predicates[1] == "harnessVersionBound", "fallback proof: expanded predicate names the narrower demo binding")
        page.locator("#proof-sheet [data-sheet-close]").click()
        page_text = page.locator("body").inner_text().lower()
        evidence.require(all(term not in page_text for term in ("simulated credits", "demo viewers", "learning streak", "how ranking works")), "fallback: finance and social theater copy stays absent")
        assert_observers_clean(evidence, observed, "fallback")
        evidence.journey("verified-read-model failure with bounded demo fallback and no unearned market or audience signals")
    finally:
        context.close()


def ten_fronts_blitz_journey(browser: Any, base_url: str, evidence: Evidence) -> None:
    blitz_url = base_url.replace(f"/index.html?v={SHELL_VERSION}", f"/ten-fronts.html?v={SHELL_VERSION}")
    context = browser.new_context(viewport=VIEWPORTS[1], service_workers="allow")
    page = context.new_page()
    observed = install_observers(page, base_url, "ten-fronts")

    def choose_and_commit(signal: str = "steady", check_invalid: bool = False) -> None:
        page.locator(f'label:has(input[name="blitz-signal"][value="{signal}"])').click()
        evidence.require(page.locator('[data-blitz-action="lock-signal"]').is_enabled(), "Ten Fronts: allowlisted signal enables the next phase")
        page.locator('[data-blitz-action="lock-signal"]').click()
        page.wait_for_selector('[data-blitz-state="allocation"]')
        inputs = page.locator("[data-blitz-front]")
        evidence.require(inputs.count() == 10, "Ten Fronts: all ten human allocation controls render")
        evidence.require(page.locator(".blitz-reveal-grid").count() == 0, "Ten Fronts: reference allocation remains hidden before human commit")
        if check_invalid:
            inputs.first.fill("9")
            evidence.require(page.locator('[data-blitz-action="commit-allocation"]').is_disabled(), "Ten Fronts: a 99-troop allocation is refused")
            evidence.require("99 allocated" in page.locator("#blitz-allocation-status").inner_text(), "Ten Fronts: wrong-sum feedback names the current total")
            inputs.first.fill("10")
            inputs.first.fill("110")
            inputs.nth(1).fill("-10")
            evidence.require(page.locator('[data-blitz-action="commit-allocation"]').is_disabled(), "Ten Fronts: offsetting out-of-range values cannot masquerade as a valid 100-troop allocation")
            inputs.first.fill("10")
            inputs.nth(1).fill("10")
        evidence.require(page.locator('[data-blitz-action="commit-allocation"]').is_enabled(), "Ten Fronts: an exact 100-troop allocation is committable")
        page.locator('[data-blitz-action="commit-allocation"]').click()
        page.wait_for_selector('[data-blitz-state="reveal"]')
        evidence.require(page.locator(".blitz-reveal-grid li").count() == 10, "Ten Fronts: commit reveals all ten exact allocation pairs")
        evidence.require("Exact allocation ties paid nobody" in page.locator(".blitz-command").inner_text(), "Ten Fronts: reveal discloses the exact-tie rule")

    def finish_game(check_invalid: bool = False) -> None:
        for round_index, signal in enumerate(("steady", "pressure", "feint")):
            choose_and_commit(signal, check_invalid and round_index == 0)
            page.locator('[data-blitz-action="next"]').click()
            expected = "complete" if round_index == 2 else "signal"
            page.wait_for_selector(f'[data-blitz-state="{expected}"]')

    try:
        page.goto(base_url, wait_until="domcontentloaded")
        wait_for_source(page, "verified_corpus")
        page.locator('.bottom-nav [data-nav="compete"]').click()
        link = page.locator("[data-ten-fronts-blitz-link]")
        evidence.require(link.count() == 1 and link.is_visible(), "Ten Fronts: verified Compete view exposes one local Blitz entry")
        storage_before = page.evaluate("Object.fromEntries(Object.keys(localStorage).sort().map(key => [key, localStorage.getItem(key)]))")
        link.click()
        page.wait_for_url(f"**/ten-fronts.html?v={SHELL_VERSION}")
        wait_for_blitz_source(page, "verified_corpus")
        evidence.require(page.locator("#blitz-source-status").inner_text() == "VERIFIED LOCAL CORPUS", "Ten Fronts: exact source status is visible before play")
        evidence.require(page.locator('[data-blitz-state="ready"]').count() == 1, "Ten Fronts: verified source unlocks the bounded exhibition")
        requested = set(observed["same_origin_requests"])
        for resource in (f"/ten-fronts.html?v={SHELL_VERSION}", f"/ten-fronts-blitz.css?v={SHELL_VERSION}", f"/ten-fronts-blitz.js?v={SHELL_VERSION}"):
            evidence.require(resource in requested, f"Ten Fronts: route requests current local asset {resource}")
        page.locator('[data-blitz-action="start"]').click()
        page.wait_for_selector('[data-blitz-state="signal"]')
        evidence.require(page.locator('input[name="blitz-signal"]').count() == 3, "Ten Fronts: exactly three allowlisted signal choices render")
        evidence.require(page.locator("textarea").count() == 0, "Ten Fronts: no free-text game input exists")
        finish_game(check_invalid=True)
        result_text = page.locator('[data-blitz-state="complete"]').inner_text()
        result_text_lower = result_text.lower()
        evidence.require("replay\npass" in result_text_lower and "local candidate" in result_text_lower, f"Ten Fronts: completion exposes independent replay PASS as a local candidate ({result_text!r})")
        evidence.require("Version 1 · unplayed" in result_text, "Ten Fronts: generated runback remains explicitly unplayed")
        locator_text = page.locator(".blitz-locator").inner_text()
        evidence.require(locator_text.startswith("builderwars-local-proof://ten-fronts-blitz/") and len(locator_text.rsplit("/", 1)[-1]) == 64, "Ten Fronts: receipt candidate has a content-shaped local locator")
        evidence.require(page.evaluate("Object.fromEntries(Object.keys(localStorage).sort().map(key => [key, localStorage.getItem(key)]))") == storage_before, "Ten Fronts: complete play does not touch browser storage")
        page.locator('[data-blitz-action="restart"]').click()
        page.wait_for_selector('[data-blitz-state="signal"]')
        evidence.require(page.locator(".blitz-locator").count() == 0, "Ten Fronts: restart clears the memory-only receipt")
        finish_game()
        page.locator('[data-blitz-action="discard"]').click()
        page.wait_for_selector('[data-blitz-state="signal"]')
        evidence.require(page.locator(".blitz-locator").count() == 0, "Ten Fronts: discard clears the memory-only result")
        page.locator('label:has(input[name="blitz-signal"][value="steady"])').click()
        page.locator('[data-blitz-action="lock-signal"]').click()
        page.wait_for_selector('[data-blitz-state="allocation"]')
        page.reload(wait_until="domcontentloaded")
        wait_for_blitz_source(page, "verified_corpus")
        evidence.require(page.locator('[data-blitz-state="ready"]').count() == 1, "Ten Fronts: reload clears unfinished browser-memory state")
        for viewport in VIEWPORTS:
            page.set_viewport_size(viewport)
            evidence.require(page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"), f"Ten Fronts: no document overflow at {viewport['width']}px")
        assert_observers_clean(evidence, observed, "ten-fronts")
        evidence.journey("human-controlled Ten Fronts Blitz through invalid allocation, three rounds, replay, restart, discard, reload, and responsive widths")
    finally:
        context.close()

    reduced_context = browser.new_context(viewport=VIEWPORTS[1], reduced_motion="reduce", service_workers="allow")
    reduced_page = reduced_context.new_page()
    reduced_observed = install_observers(reduced_page, base_url, "ten-fronts-reduced")
    try:
        reduced_page.goto(blitz_url, wait_until="domcontentloaded")
        wait_for_blitz_source(reduced_page, "verified_corpus")
        reduced_page.locator('[data-blitz-action="start"]').click()
        reduced_page.locator('label:has(input[name="blitz-signal"][value="steady"])').click()
        reduced_page.locator('[data-blitz-action="lock-signal"]').click()
        reduced_page.locator('[data-blitz-action="commit-allocation"]').click()
        reduced_page.wait_for_selector('[data-blitz-state="reveal"]')
        evidence.require(reduced_page.locator(".blitz-reveal-grid li").first.evaluate("node => getComputedStyle(node).animationName") == "none", "Ten Fronts: reduced motion removes reveal animation")
        assert_observers_clean(evidence, reduced_observed, "ten-fronts-reduced")
        evidence.journey("Ten Fronts reduced-motion reveal")
    finally:
        reduced_context.close()

    forced_context = browser.new_context(viewport=VIEWPORTS[1], forced_colors="active", service_workers="allow")
    forced_page = forced_context.new_page()
    forced_observed = install_observers(forced_page, base_url, "ten-fronts-forced")
    try:
        forced_page.goto(blitz_url, wait_until="domcontentloaded")
        wait_for_blitz_source(forced_page, "verified_corpus")
        start = forced_page.locator('[data-blitz-action="start"]')
        start.focus()
        outline = start.evaluate("node => ({style:getComputedStyle(node).outlineStyle,width:parseFloat(getComputedStyle(node).outlineWidth)})")
        evidence.require(outline["style"] != "none" and outline["width"] >= 3, f"Ten Fronts: forced-colors focus remains visible ({outline!r})")
        assert_observers_clean(evidence, forced_observed, "ten-fronts-forced")
        evidence.journey("Ten Fronts forced-colors focus")
    finally:
        forced_context.close()

    fallback_context = browser.new_context(viewport=VIEWPORTS[0], service_workers="allow")
    fallback_page = fallback_context.new_page()
    fallback_observed = install_observers(fallback_page, base_url, "ten-fronts-fallback")
    try:
        fallback_page.route(READ_MODEL_PATH, lambda route: route.fulfill(status=200, content_type="application/json", body="{}"))
        fallback_page.goto(blitz_url, wait_until="domcontentloaded")
        wait_for_blitz_source(fallback_page, "demo_fixture_fallback")
        evidence.require(fallback_page.locator("#blitz-source-status").inner_text() == "FALLBACK · EXECUTION HELD", "Ten Fronts: source fallback is explicitly labeled")
        evidence.require(fallback_page.locator('[data-blitz-state="held"]').count() == 1, "Ten Fronts: fallback withholds the executable fixture")
        evidence.require(fallback_page.locator("#ten-fronts-blitz-root button, #ten-fronts-blitz-root input").count() == 0, "Ten Fronts: held fallback exposes no execution controls")
        assert_observers_clean(evidence, fallback_observed, "ten-fronts-fallback")
        evidence.journey("Ten Fronts source fallback holds execution")
    finally:
        fallback_context.close()


def semantic_drift_fallback_journey(browser: Any, base_url: str, evidence: Evidence) -> None:
    context = browser.new_context(viewport=VIEWPORTS[0], service_workers="allow")
    page = context.new_page()
    observed = install_observers(page, base_url, "semantic-drift")
    model = json.loads((MOBILE_ARENA / "data" / "arena-read-model.v1.json").read_text(encoding="utf-8"))
    model["channels"][0]["publishedReceiptCount"] += 1
    try:
        page.route(
            READ_MODEL_PATH,
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(model, sort_keys=True),
            ),
        )
        page.goto(base_url, wait_until="domcontentloaded")
        wait_for_source(page, "demo_fixture_fallback")
        evidence.require(page.locator("#source-badge").inner_text() == "DEMO FALLBACK", "semantic drift: inconsistent channel evidence loses the verified label")
        evidence.require("demo fallback ready" in page.locator("#connection-copy").inner_text().lower(), "semantic drift: bounded fallback remains explicit")
        evidence.require(page.locator("#standings-title").inner_text() == "Demo roster", "semantic drift: receipt board is not rendered from inconsistent evidence")
        assert_observers_clean(evidence, observed, "semantic-drift")
        evidence.journey("semantically inconsistent read model fails closed")
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


def creator_game_failure_journey(browser: Any, base_url: str, evidence: Evidence) -> None:
    context = browser.new_context(viewport=VIEWPORTS[1], service_workers="allow")
    page = context.new_page()
    observed = install_observers(page, base_url, "creator-game-failure")
    try:
        page.route(CREATOR_GAME_LAB_PATH, lambda route: route.fulfill(status=200, content_type="application/json", body="{}"))
        page.goto(base_url, wait_until="domcontentloaded")
        wait_for_source(page, "verified_corpus")
        page.locator('.bottom-nav [data-nav="build"]').click()
        text = page.locator("#creator-game-lab").inner_text()
        evidence.require("Creator game unavailable" in text and "No fallback game" in text, "creator game failure: invalid source withholds the lab without fabrication")
        evidence.require(page.locator("#creator-game-lab .creator-game-card").count() == 0, "creator game failure: no candidate card survives failed verification")
        page.locator('.bottom-nav [data-nav="learn"]').click()
        evidence.require("Lesson held" in page.locator("#creator-game-lesson").inner_text(), "creator game failure: learning projection is also withheld")
        assert_observers_clean(evidence, observed, "creator-game-failure")
        evidence.journey("creator-game source failure and no fabricated fallback")
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


def forced_colors_journey(browser: Any, base_url: str, evidence: Evidence) -> None:
    context = browser.new_context(viewport=VIEWPORTS[1], forced_colors="active", service_workers="allow")
    page = context.new_page()
    observed = install_observers(page, base_url, "forced-colors")
    try:
        page.goto(base_url, wait_until="domcontentloaded")
        wait_for_source(page, "verified_corpus")
        evidence.require(page.evaluate("matchMedia('(forced-colors: active)').matches") is True, "forced colors: browser preference is active")
        focus_target = page.locator("#starter-guide-button")
        focus_target.focus()
        focus_style = focus_target.evaluate(
            "node => ({style: getComputedStyle(node).outlineStyle, width: parseFloat(getComputedStyle(node).outlineWidth), color: getComputedStyle(node).outlineColor})"
        )
        evidence.require(focus_style["style"] != "none" and focus_style["width"] >= 3, f"forced colors: focused control retains a three-pixel outline ({focus_style!r})")
        evidence.require(focus_style["color"] not in {"rgba(0, 0, 0, 0)", "transparent"}, f"forced colors: focus outline remains visible ({focus_style['color']!r})")
        for view in VIEW_NAMES:
            page.locator(f'.bottom-nav [data-nav="{view}"]').click()
            assert_view(evidence, page, view)
            evidence.require(page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"), f"forced colors: {view} has no document overflow")
        page.locator("#profile-button").click()
        evidence.require(locator_visible(page, "#session-sheet"), "forced colors: local-session dialog remains visible")
        sheet_fit = page.locator("#session-sheet").evaluate(
            "node => ({inside: node.getBoundingClientRect().left >= 0 && node.getBoundingClientRect().right <= innerWidth, noOverflow: node.scrollWidth <= node.clientWidth})"
        )
        evidence.require(sheet_fit["inside"] and sheet_fit["noOverflow"], f"forced colors: local-session dialog remains within the viewport ({sheet_fit!r})")
        page.keyboard.press("Escape")
        page.locator('.bottom-nav [data-nav="arena"]').click()
        page.locator("#featured-match [data-proof-open]").first.click()
        proof_summary = page.locator(".proof-predicates > summary")
        page.keyboard.press("Tab")
        evidence.require(proof_summary.evaluate("node => document.activeElement === node"), "forced colors: proof disclosure remains in keyboard order")
        proof_outline = proof_summary.evaluate("node => ({style: getComputedStyle(node).outlineStyle, width: parseFloat(getComputedStyle(node).outlineWidth)})")
        evidence.require(proof_outline["style"] != "none" and proof_outline["width"] >= 3, f"forced colors: proof disclosure retains a three-pixel outline ({proof_outline!r})")
        evidence.require(page.locator(".proof-trust-strip").evaluate("node => getComputedStyle(node).borderTopStyle") != "none", "forced colors: first-glance proof strip retains a visible boundary")
        page.keyboard.press("Escape")
        assert_observers_clean(evidence, observed, "forced-colors")
        evidence.journey("forced-colors navigation, focus, and dialog rendering")
    finally:
        context.close()


def reflow_journey(browser: Any, base_url: str, evidence: Evidence) -> None:
    context = browser.new_context(viewport=VIEWPORTS[0], service_workers="allow")
    page = context.new_page()
    observed = install_observers(page, base_url, "reflow")
    try:
        page.goto(base_url, wait_until="domcontentloaded")
        wait_for_source(page, "verified_corpus")
        evidence.require(page.evaluate("innerWidth") == 320, "reflow: CSS viewport is exactly 320 pixels")
        for view in VIEW_NAMES:
            page.locator(f'.bottom-nav [data-nav="{view}"]').click()
            assert_view(evidence, page, view)
            evidence.require(page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"), f"reflow: {view} has no horizontal document overflow at 320 CSS pixels")
        nav_fit = page.locator(".bottom-nav").evaluate(
            "node => [...node.querySelectorAll('.nav-item')].every(item => { const rect = item.getBoundingClientRect(); return rect.left >= 0 && rect.right <= innerWidth && rect.width >= 54 && rect.height >= 44; })"
        )
        evidence.require(nav_fit is True, "reflow: all five navigation targets remain inside the viewport and touch-sized")
        page.locator("#profile-button").click()
        evidence.require(locator_visible(page, "#session-sheet"), "reflow: local-session dialog opens at 320 CSS pixels")
        session_fit = page.locator("#session-sheet").evaluate(
            "node => ({inside: node.getBoundingClientRect().left >= 0 && node.getBoundingClientRect().right <= innerWidth, noOverflow: node.scrollWidth <= node.clientWidth})"
        )
        evidence.require(session_fit["inside"] and session_fit["noOverflow"], f"reflow: local-session dialog remains within the viewport ({session_fit!r})")
        page.locator("[data-session-open-feedback]").click()
        feedback_fit = page.locator("#tester-feedback-sheet").evaluate(
            "node => ({inside: node.getBoundingClientRect().left >= 0 && node.getBoundingClientRect().right <= innerWidth, noOverflow: node.scrollWidth <= node.clientWidth})"
        )
        evidence.require(feedback_fit["inside"] and feedback_fit["noOverflow"], f"reflow: feedback dialog remains within the viewport ({feedback_fit!r})")
        page.locator("#tester-feedback-sheet [data-sheet-close]").click()
        page.keyboard.press("Escape")
        page.locator('.bottom-nav [data-nav="arena"]').click()
        page.locator("#featured-match [data-proof-open]").first.click()
        page.locator(".proof-predicates > summary").click()
        evidence.require(page.locator(".proof-predicates").get_attribute("open") is not None, "reflow: expanded proof predicates remain operable at 320 CSS pixels")
        proof_fit = page.locator("#proof-sheet").evaluate(
            "node => ({inside: node.getBoundingClientRect().left >= 0 && node.getBoundingClientRect().right <= innerWidth, noOverflow: node.scrollWidth <= node.clientWidth})"
        )
        evidence.require(proof_fit["inside"] and proof_fit["noOverflow"], f"reflow: proof dialog remains within the viewport ({proof_fit!r})")
        page.keyboard.press("Escape")
        assert_observers_clean(evidence, observed, "reflow")
        evidence.journey("320-CSS-pixel reflow across navigation and dialogs")
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
              const cache = await caches.open('builderwars-mobile-arena-v41');
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
        for resource in (f"/ten-fronts.html?v={SHELL_VERSION}", f"/ten-fronts-blitz.css?v={SHELL_VERSION}", f"/ten-fronts-blitz.js?v={SHELL_VERSION}"):
            evidence.require(resource in cache_state["urls"], f"offline: current shell cache contains local game asset {resource}")
        evidence.require("/data/tester-feedback-rubric.v1.json" in cache_state["urls"], "offline: canonical tester rubric is cached with the current shell")
        evidence.require("/data/creator-game-lab.v1.json" in cache_state["urls"], "offline: reviewed creator-game lab is cached with the current shell")
        evidence.require(not any("?v=30" in resource for resource in cache_state["urls"]), "offline: current shell cache excludes retired v30 URLs")
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
        evidence.require(page.locator("#creator-game-lesson .creator-admission-list li").count() == 8, "offline: verified creator-game admission lesson remains available")
        page.locator('.bottom-nav [data-nav="compete"]').click()
        page.locator("[data-ten-fronts-blitz-link]").click()
        page.wait_for_url(f"**/ten-fronts.html?v={SHELL_VERSION}")
        wait_for_blitz_source(page, "verified_corpus")
        evidence.require(page.locator('[data-blitz-state="ready"]').count() == 1, "offline: cached Ten Fronts route remains qualified and playable")
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
            ten_fronts_blitz_journey(browser, base_url, evidence)
            fallback_journey(browser, base_url, evidence)
            semantic_drift_fallback_journey(browser, base_url, evidence)
            fatal_source_journey(browser, base_url, evidence)
            tester_rubric_failure_journey(browser, base_url, evidence)
            creator_game_failure_journey(browser, base_url, evidence)
            storage_denial_journey(browser, base_url, evidence)
            reduced_motion_journey(browser, base_url, evidence)
            forced_colors_journey(browser, base_url, evidence)
            reflow_journey(browser, base_url, evidence)
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
            "forcedColorsEmulated": True,
            "reflowAt320CssPixels": True,
            "actualBrowserZoom": False,
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
