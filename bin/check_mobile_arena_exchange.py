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
EXPECTED_SHELL_VERSION = "35"
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
    "data/tester-feedback-rubric.v1.json",
    "data/creator-game-lab.v1.json",
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
    feedback_rubric = json.loads(read("data/tester-feedback-rubric.v1.json"))
    creator_game_lab = json.loads(read("data/creator-game-lab.v1.json"))

    creator_game_check = subprocess.run(
        [str(Path(shutil.which("python") or "python")), str(ROOT / "bin" / "check_mobile_arena_creator_game.py")],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
        check=False,
    )
    require(creator_game_check.returncode == 0, f"mobile creator-game lab drift: {creator_game_check.stderr.strip()}")
    checks += 1

    rubric_check = subprocess.run(
        [str(Path(shutil.which("python") or "python")), str(ROOT / "bin" / "build_mobile_tester_feedback_rubric.py"), "--check"],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
    )
    require(rubric_check.returncode == 0, f"mobile tester rubric drift: {rubric_check.stderr.strip()}")
    checks += 1

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
    require(read_model.get("projectionVersion") == "4", "read-model identity projection drift")
    require(read_model.get("source", {}).get("status") == "tracked_local_publication_artifact_not_hosted", "read-model source boundary drift")
    require(read_model.get("summary", {}).get("receiptCount") == len(read_model.get("receipts", [])) == 8, "reviewed receipt count drift")
    require(read_model.get("summary", {}).get("signedAgentPassportEntrantCount") == 0, "current signed Agent Passport count drift")
    require(read_model.get("summary", {}).get("legacySelfDeclaredEntrantCount") == 16, "current legacy identity count drift")
    require(read_model.get("summary", {}).get("signedAgentPassportReceiptCount") == 0, "current signed receipt coverage drift")
    require(all(entrant.get("identityEvidence", {}).get("status") == "self_declared_legacy" for receipt in read_model.get("receipts", []) for entrant in receipt.get("entrants", [])), "current legacy identity evidence drift")
    for boundary in ("live", "hosted", "authenticated", "modelAttested", "providerAttested", "runtimeAttested"):
        require(read_model.get("truthBoundary", {}).get(boundary) is False, f"read-model {boundary} boundary drift")
        checks += 1
    checks += 8

    print("[3] five mobile destinations and proof inspector are wired")
    for destination in ("arena", "watch", "compete", "learn", "build"):
        require(f'id="view-{destination}"' in html, f"missing {destination} view")
        require(f'data-nav="{destination}"' in html, f"missing {destination} navigation")
        checks += 2
    for required in ("proof-sheet", "automations-sheet", "qualification-sheet", "session-sheet", "tester-feedback-sheet", "tester-feedback-form", "tester-feedback-categories", "tester-feedback-output", "tester-feedback-json", "builder-form", "featured-match", "quick-matches", "rivalries", "receipt-learning", "proof-learning-button"):
        require(f'id="{required}"' in html, f"missing interactive surface: {required}")
        checks += 1
    for required in ("starter-panel", "starter-title", "starter-boundary", "starter-guide-button", "starter-persistence"):
        require(f'id="{required}"' in html, f"missing first-run starter surface: {required}")
        checks += 1
    require(all(f'data-starter-action="{action}"' in html for action in ("proof", "compete", "build")), "starter path must expose proof, compete, and build actions")
    require("No account · no provider · no live match · no publication" in html, "starter path truth boundary missing")
    require('aria-controls="starter-panel"' in html and 'aria-describedby="starter-boundary"' in html, "starter path accessible relationships missing")
    checks += 3
    for required in ("session-boundary", "session-source-status", "session-account-status", "session-provider-status", "session-blueprint-status", "session-starter-status", "session-storage-status"):
        require(f'id="{required}"' in html, f"missing local-session surface: {required}")
        checks += 1
    require('id="profile-button"' in html and 'aria-controls="session-sheet"' in html and 'aria-haspopup="dialog"' in html, "local-session trigger semantics missing")
    require("No identity, provider subscription, credential, remote profile, or live activity is connected." in html, "local-session protected boundary missing")
    require("data-session-open-feedback" in html and "data-session-restart-starter" in html and "data-session-remove-blueprint" in html, "local-session lifecycle controls missing")
    require("requires two presses" in html and "only this browser origin" in html and "never deleted" in html, "browser-only deletion boundary missing")
    checks += 4

    print("[4] local-only network and execution boundary")
    combined = "\n".join((html, css, js, adapter, sw, json.dumps(fixture), json.dumps(read_model), json.dumps(feedback_rubric), json.dumps(creator_game_lab), json.dumps(webmanifest)))
    require(re.search(r"https?://", combined, re.IGNORECASE) is None, "mobile shell contains an external URL")
    for forbidden in ("eval(", "new Function", "WebSocket(", "EventSource(", "postMessage(", "document.cookie", "Authorization", "Bearer "):
        require(forbidden not in combined, f"forbidden active capability: {forbidden}")
        checks += 1
    require("dataAdapter.loadArenaData(fetch)" in js, "app must load sources through the fail-closed adapter")
    require('"data/demo-state.json"' in adapter and '"data/arena-read-model.v1.json"' in adapter and '"data/tester-feedback-rubric.v1.json"' in adapter and '"data/creator-game-lab.v1.json"' in adapter, "adapter must load only the four bounded local sources")
    require('sourceMode = "verified_corpus"' in adapter and 'sourceMode = "demo_fixture_fallback"' in adapter, "adapter source modes must remain explicit")
    require("requestURL.origin !== self.location.origin" in sw, "service worker must reject cross-origin caching")
    require("localStorage.setItem" in js and "localStorage.getItem" in js, "local blueprint persistence missing")
    require("BLUEPRINT_MAX_LENGTH = 2048" in js and "raw.length > BLUEPRINT_MAX_LENGTH" in js and "never executed" in html, "local blueprint boundary missing")
    require("for (const key of BLUEPRINT_GUARD_KEYS)" in js, "saved blueprint guards must hydrate from the bounded key list")
    require("localStorage.removeItem(BLUEPRINT_STORAGE_KEY)" in js, "invalid local blueprint state must be discarded")
    require('STARTER_GUIDE_STORAGE_KEY = "builderwars.mobile-arena.starter-guide.v1"' in js, "starter guide must use its own bounded browser-local key")
    require("hydrateStarterGuide" in js and "completeStarterGuide" in js and "showStarterGuide" in js, "starter guide lifecycle missing")
    require("starterGuidePersistenceAvailable = false" in js and "dismissal lasts only until refresh" in js, "starter guide storage-denial disclosure missing")
    require("No account or remote preference was created" in js and "nothing was uploaded" in js, "starter guide persistence truth boundary missing")
    checks += 4
    require("renderSessionSheet" in js and "restartStarterGuideFromSession" in js and "armOrRemoveLocalBlueprint" in js, "local-session lifecycle implementation missing")
    require("Not supplied · self-declared legacy identity" in js and "Person, model, provider, and runtime unattested" in js, "Agent Passport disclosure copy missing")
    require("identity evidence drift" in adapter and "identity attestation inflation" in adapter and "legacy identity drift" in adapter, "Agent Passport adapter boundary missing")
    require('"Confirm remove blueprint"' in js and "blueprintRemovalArmed" in js, "two-step local blueprint removal is not enforced")
    require("localStorage.removeItem(BLUEPRINT_STORAGE_KEY)" in js and '$("#builder-form").reset()' in js, "browser-only blueprint cleanup implementation missing")
    require("Unavailable to inspect" in js and "Unavailable · page session only" in js, "storage-denial session disclosure missing")
    require("Nothing remote was changed" in js and "tracked source files were not deleted" in js, "local cleanup truth boundary missing")
    checks += 7
    require(feedback_rubric.get("schemaVersion") == "agentwars.tester-feedback-rubric/1", "tester feedback rubric schema drift")
    require(feedback_rubric.get("rubricStatus") == "template_only_no_human_response", "tester feedback rubric status drift")
    require(len(feedback_rubric.get("categories", [])) == 8, "tester feedback rubric must retain all eight categories")
    require(feedback_rubric.get("identityFieldsAllowed") == [] and feedback_rubric.get("humanFeedbackCollected") is False, "tester feedback identity or collection boundary drift")
    require(all(value is False for value in feedback_rubric.get("productionAuthority", {}).values()), "tester feedback rubric must retain zero production authority")
    require('id="tester-feedback-boundary"' in html and "No name, email, account, prompt, output, URL, credential, or free text is requested" in html, "tester feedback identity boundary missing")
    require("no feedback transport" in html.lower() and "no staffed support inbox is configured" in html.lower(), "tester feedback transport or triage boundary missing")
    require("createTesterFeedbackDraft" in adapter and "verifyTesterFeedbackDraft" in adapter and "loadTesterFeedbackRubric" in adapter, "tester feedback draft adapter contract missing")
    require('draftStatus: "LOCAL_DRAFT_NOT_COLLECTED"' in adapter and 'storageMode: "browser_memory_only"' in adapter and 'transportStatus: "not_configured"' in adapter and 'submissionStatus: "not_submitted"' in adapter, "tester feedback draft boundary drift")
    require("renderTesterFeedbackWorksheet" in js and "prepareTesterFeedbackDraft" in js and "resetTesterFeedbackWorksheet" in js, "tester feedback worksheet lifecycle missing")
    require("data-tester-feedback-generate" in html and "data-tester-feedback-reset" in html and 'readonly spellcheck="false"' in html, "tester feedback worksheet controls missing")
    require("localStorage" not in "\n".join(line for line in js.splitlines() if "TesterFeedback" in line), "tester feedback lifecycle must not use browser storage")
    require("navigator.clipboard" not in combined and "FileReader" not in combined, "tester feedback flow must not request clipboard or file authority")
    checks += 13
    require(creator_game_lab.get("schemaVersion") == "builderwars.mobile-creator-game-lab.v1", "creator-game lab schema drift")
    require(creator_game_lab.get("candidateStatus") == "candidate_not_admitted" and creator_game_lab.get("decision") == "held_exhibition_candidate", "creator-game admission boundary drift")
    require(all(value is False for value in creator_game_lab.get("authority", {}).values()), "creator-game authority must remain false")
    require('id="creator-game-lab"' in html and 'id="creator-game-lesson"' in html, "creator-game Build and Learn surfaces missing")
    require("renderCreatorGameLab" in js and "loadCreatorGameLab" in js, "creator-game mobile lifecycle missing")
    require("No fallback game, replay, creator adoption, or admission claim was fabricated." in js, "creator-game fail-closed disclosure missing")
    require("executes no creator code" in adapter and "authority inflation" in adapter, "creator-game execution boundary missing")
    checks += 7
    require("buildQualificationPreview" in adapter and 'qualificationStatus: "not_run"' in adapter, "deterministic qualification preview missing")
    require('executionStatus: "disabled"' in adapter and "computeAllowed: false" in adapter and "networkAllowed: false" in adapter, "qualification execution boundary missing")
    require("buildLocalExhibitionQualification" in adapter and "createLocalExhibitionReceipt" in adapter and "verifyLocalExhibitionReceipt" in adapter, "deterministic local exhibition loop missing")
    require('LOCAL_EXHIBITION_RESOURCE_CLASS = "browser-memory-deterministic-no-model-v1"' in adapter, "local exhibition resource boundary missing")
    require('receiptStatus: "local_receipt_candidate_unreviewed"' in adapter and 'verificationStatus: "verified_local_receipt_candidate"' in adapter, "local receipt candidate or replay boundary missing")
    require("createLocalExhibitionLearning" in adapter and "createLocalExhibitionRunback" in adapter and 'runbackStatus: "versioned_local_runback_unplayed"' in adapter, "local learning or versioned runback contract missing")
    require("data-local-exhibition-run" in js and "data-local-exhibition-discard" in js, "local exhibition browser lifecycle missing")
    require("metadata only · unused" in js and "Model/provider moves" in js, "local exhibition no-model disclosure missing")
    checks += 6
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
    require("createPortableRunbackReviewExchange" in adapter and "verifyPortableRunbackReviewExchange" in adapter, "portable review exchange verifier missing")
    require('PORTABLE_REVIEW_EXCHANGE_SCHEMA = "builderwars.mobile-runback-review-exchange.v1"' in adapter, "portable review exchange schema drift")
    require("PORTABLE_REVIEW_EXCHANGE_MAX_LENGTH = 262144" in adapter and 'maxlength="262144"' in js, "portable review exchange length boundary missing")
    require("data-portable-review-exchange-prepare" in js and "data-portable-review-exchange-verify" in js, "portable review exchange controls missing")
    require("independent local inspection" in adapter and "No blueprint was applied" in js, "portable review exchange truth boundary missing")
    require("appendPortableRunbackReviewCorrection" in adapter and "verifyPortableRunbackReviewCorrectionJournal" in adapter, "portable review correction verifier missing")
    require('PORTABLE_REVIEW_CORRECTION_SCHEMA = "builderwars.mobile-runback-review-correction.v1"' in adapter, "portable review correction schema drift")
    require("PORTABLE_REVIEW_CORRECTION_MAX_RECORDS = 64" in adapter and "data-portable-review-correction-submit" in js, "portable review correction controls or record cap missing")
    require("createPortableRunbackReviewCorrectionExchange" in adapter and "verifyPortableRunbackReviewCorrectionExchange" in adapter, "portable review correction exchange verifier missing")
    require('PORTABLE_REVIEW_CORRECTION_EXCHANGE_SCHEMA = "builderwars.mobile-runback-review-correction-exchange.v1"' in adapter, "portable review correction exchange schema drift")
    require("PORTABLE_REVIEW_CORRECTION_EXCHANGE_MAX_LENGTH = 524288" in adapter and 'maxlength="524288"' in js, "portable review correction exchange length boundary missing")
    require("data-portable-review-correction-exchange-prepare" in js and "data-portable-review-correction-exchange-verify" in js, "portable review correction exchange controls missing")
    require("preserves its immutable target review" in adapter and "No review was rewritten" in js, "portable review correction truth boundary missing")
    require("createPortablePrivateReviewComparison" in adapter and "verifyPortablePrivateReviewComparison" in adapter, "private review comparison verifier missing")
    require('PORTABLE_REVIEW_COMPARISON_SCHEMA = "builderwars.mobile-private-review-comparison.v1"' in adapter, "private review comparison schema drift")
    require("PORTABLE_REVIEW_COMPARISON_MAX_ENTRIES = PORTABLE_REVIEW_MAX_RECORDS * 2" in adapter, "private review comparison entry cap missing")
    require("PORTABLE_REVIEW_COMPARISON_MAX_LENGTH = 1572864" in adapter and 'maxlength="1572864"' in js, "private review comparison length boundary missing")
    require("data-portable-review-comparison-create" in js and "data-portable-review-comparison-verify" in js, "private review comparison controls missing")
    require("portable-review-comparison-left" in js and "portable-review-comparison-right" in js, "private review comparison source inputs missing")
    require("without choosing a winner" in adapter and "No packet won" in js, "private review comparison winner boundary missing")
    require("merging histories" in adapter and "no histories merged" in js, "private review comparison merge boundary missing")
    require("createPortablePrivateReviewLearning" in adapter and "verifyPortablePrivateReviewLearning" in adapter, "private review inspection learning verifier missing")
    require('PRIVATE_REVIEW_LEARNING_SCHEMA = "builderwars.mobile-private-review-learning.v1"' in adapter, "private review inspection learning schema drift")
    require("PRIVATE_REVIEW_LEARNING_MAX_ENTRIES = PORTABLE_REVIEW_COMPARISON_MAX_ENTRIES" in adapter, "private review inspection learning entry cap missing")
    require("PRIVATE_REVIEW_LEARNING_MAX_LENGTH = 2097152" in adapter and 'maxlength="2097152"' in js, "private review inspection learning length boundary missing")
    require("data-private-review-learning-create" in js and "data-private-review-learning-verify" in js, "private review inspection learning controls missing")
    require("inspect_evidence" in adapter and "inspect_rules_binding" in adapter and "inspect_correction_lineage" in adapter, "bounded inspection lesson allowlist missing")
    require("without choosing a correct state" in adapter and "Neither packet was declared correct" in js, "private review inspection correctness boundary missing")
    require("granting consensus, approval" in adapter and "no progress awarded" in js, "private review inspection progress boundary missing")
    require("createPortablePrivateBlueprintDelta" in adapter and "verifyPortablePrivateBlueprintDelta" in adapter, "private guard proposal verifier missing")
    require('PRIVATE_BLUEPRINT_DELTA_SCHEMA = "builderwars.mobile-private-inspection-blueprint-delta.v1"' in adapter, "private guard proposal schema drift")
    require("PRIVATE_BLUEPRINT_DELTA_MAX_LENGTH = 2621440" in adapter and 'maxlength="2621440"' in js, "private guard proposal length boundary missing")
    require("data-private-blueprint-delta-create" in js and "data-private-blueprint-delta-verify" in js, "private guard proposal controls missing")
    require("PRIVATE_REVIEW_LESSON_DELTA" in adapter and "require_strict_validation" in adapter and "require_fallback_disclosure" in adapter and "require_human_checkpoints" in adapter, "fixed lesson-to-guard mapping missing")
    require("proposed_uncommitted_guard_delta" in adapter and "uncommitted and unplayed" in js, "private guard proposal state boundary missing")
    require("not_carried_by_parent_proposal" in adapter and "not carried by parent proposal" in js, "private guard proposal unknown-current disclosure missing")
    require("chooses no correct packet" in adapter and "cannot create correctness" in js, "private guard proposal correctness boundary missing")
    require("createPortablePrivateBlueprintDeltaReview" in adapter and "verifyPortablePrivateBlueprintDeltaReview" in adapter, "private guard-review verifier missing")
    require('PRIVATE_BLUEPRINT_DELTA_REVIEW_SCHEMA = "builderwars.mobile-private-inspection-blueprint-delta-review.v1"' in adapter, "private guard-review schema drift")
    require("PRIVATE_BLUEPRINT_DELTA_REVIEW_MAX_LENGTH = 3145728" in adapter and 'maxlength="3145728"' in js, "private guard-review length boundary missing")
    require("data-private-blueprint-delta-review-create" in js and "data-private-blueprint-delta-review-verify" in js, "private guard-review controls missing")
    require("accept_for_revision" in adapter and "needs_operator_revision_review" in adapter and "lesson_guard_mismatch" in adapter, "private guard-review decisions or reasons missing")
    require("proposed_uncommitted_local_revision_candidate" in adapter and "uncommitted local revision candidate proposed" in js, "private guard-review candidate boundary missing")
    require("adopted: false" in adapter and "played: false" in adapter and "No guard was adopted" in js, "private guard-review adoption boundary missing")
    require("records one immutable local review" in adapter and "Record one decision. Adopt nothing." in js, "private guard-review immutable-decision boundary missing")
    require("createPortablePrivateBlueprintRevisionDraft" in adapter and "verifyPortablePrivateBlueprintRevisionDraft" in adapter, "private blueprint revision-draft verifier missing")
    require('PRIVATE_BLUEPRINT_REVISION_DRAFT_SCHEMA = "builderwars.mobile-private-blueprint-revision-draft.v1"' in adapter, "private blueprint revision-draft schema drift")
    require("PRIVATE_BLUEPRINT_REVISION_DRAFT_MAX_LENGTH = 4194304" in adapter and 'maxlength="4194304"' in js, "private blueprint revision-draft length boundary missing")
    require("data-private-blueprint-revision-draft-create" in js and "data-private-blueprint-revision-draft-verify" in js, "private blueprint revision-draft controls missing")
    require("unreviewed_guard_values_not_carried" in adapter and "Unknown guard values preserved" in js, "private blueprint revision-draft unknown guard boundary missing")
    require("accepted review required" in adapter and "Defer and reject reviews fail closed" in js, "private blueprint revision-draft accepted-review gate missing")
    require("applies only the reviewed allowlisted guard" in adapter and "Local blueprint revision draft verified · never adopted" in js, "private blueprint revision-draft exact application boundary missing")
    require("createPortablePrivateBlueprintDraftReview" in adapter and "verifyPortablePrivateBlueprintDraftReview" in adapter, "private blueprint draft-review verifier missing")
    require('PRIVATE_BLUEPRINT_DRAFT_REVIEW_SCHEMA = "builderwars.mobile-private-blueprint-revision-draft-review.v1"' in adapter, "private blueprint draft-review schema drift")
    require("PRIVATE_BLUEPRINT_DRAFT_REVIEW_MAX_LENGTH = 5242880" in adapter and 'maxlength="5242880"' in js, "private blueprint draft-review length boundary missing")
    require("data-private-blueprint-draft-review-create" in js and "data-private-blueprint-draft-review-verify" in js, "private blueprint draft-review controls missing")
    require("accept_for_commit_candidate" in adapter and "required_guard_values_unknown" in adapter and "guard_change_not_approved" in adapter, "private blueprint draft-review decisions or reasons missing")
    require("blocked_unknown_guard_values" in adapter and "Unknown guard values remain explicit and block commit readiness" in js, "private blueprint draft-review unknown-guard readiness boundary missing")
    require("commitReady: false" in adapter and "Review the draft. Commit nothing." in js, "private blueprint draft-review commit boundary missing")
    require("createPortablePrivateBlueprintGuardCompletion" in adapter and "verifyPortablePrivateBlueprintGuardCompletion" in adapter, "private blueprint guard-completion verifier missing")
    require('PRIVATE_BLUEPRINT_GUARD_COMPLETION_SCHEMA = "builderwars.mobile-private-blueprint-guard-completion-proposal.v1"' in adapter, "private blueprint guard-completion schema drift")
    require("PRIVATE_BLUEPRINT_GUARD_COMPLETION_MAX_LENGTH = 6291456" in adapter and 'maxlength="6291456"' in js, "private blueprint guard-completion length boundary missing")
    require("data-private-blueprint-guard-completion-create" in js and "data-private-blueprint-guard-completion-verify" in js, "private blueprint guard-completion controls missing")
    require("complete_explicit_unknown_guards" in adapter and "fixture_specific_requirement" in adapter and "private_evidence_reviewed_locally" in adapter, "private blueprint guard-completion reasons or provenance missing")
    require("exact unknown guard set required" in adapter and "Complete exactly the candidate's unknown guard set" in js, "private blueprint guard-completion exact-set boundary missing")
    require("boolean guard value required" in adapter and "Choose true or false" in js, "private blueprint guard-completion boolean boundary missing")
    require("preserves every known or applied guard" in adapter and "Known and applied guards cannot change" in js, "private blueprint guard-completion preservation boundary missing")
    require("requires_guard_completion_review" in adapter and "review still required" in js and "not commit-ready" in js, "private blueprint guard-completion readiness boundary missing")
    require("createPortablePrivateBlueprintGuardCompletionReview" in adapter and "verifyPortablePrivateBlueprintGuardCompletionReview" in adapter, "private guard-completion review verifier missing")
    require('PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_SCHEMA = "builderwars.mobile-private-blueprint-guard-completion-review.v1"' in adapter, "private guard-completion review schema drift")
    require("PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_MAX_LENGTH = 7340032" in adapter and 'maxlength="7340032"' in js, "private guard-completion review length boundary missing")
    require("data-private-blueprint-guard-completion-review-create" in js and "data-private-blueprint-guard-completion-review-verify" in js, "private guard-completion review controls missing")
    require("accept_for_commit_review" in adapter and "guard_value_provenance_unattested" in adapter and "known_guard_preservation_failed" in adapter, "private guard-completion review decisions or reasons missing")
    require("proposed_local_blueprint_candidate_for_operator_commit_review" in adapter and "reviewed for operator commit decision · not commit-ready" in js, "private guard-completion review candidate boundary missing")
    require("requires_operator_commit_review" in adapter and "operator review" in js and "Commit nothing." in js, "private guard-completion operator hold missing")
    require("The verified upstream completion remains available" in js, "private guard-completion review refusal must preserve upstream completion")
    require("records one immutable local review" in adapter and "immutable private decision" in js, "private guard-completion review immutability boundary missing")
    require("createPortablePrivateBlueprintOperatorReviewPacket" in adapter and "verifyPortablePrivateBlueprintOperatorReviewPacket" in adapter, "private operator-review packet verifier missing")
    require('PRIVATE_BLUEPRINT_OPERATOR_REVIEW_PACKET_SCHEMA = "builderwars.mobile-private-blueprint-operator-review-packet.v1"' in adapter, "private operator-review packet schema drift")
    require("PRIVATE_BLUEPRINT_OPERATOR_REVIEW_PACKET_MAX_LENGTH = 8388608" in adapter and 'maxlength="8388608"' in js, "private operator-review packet length boundary missing")
    require("data-private-blueprint-operator-review-packet-create" in js and "data-private-blueprint-operator-review-packet-verify" in js, "private operator-review packet controls missing")
    require("accepted completion review required" in adapter and "Defer and reject fail closed" in js, "private operator-review packet accepted-review gate missing")
    require("original-to-candidate guard diff" in adapter and "exact original-to-candidate guard diff" in js, "private operator-review packet exact-diff boundary missing")
    require('status: "not_run"' in adapter and "all evidence not run" in js, "private operator-review packet validation boundary missing")
    require("discard_only_uncommitted_state" in adapter and "rollback discard-only" in js, "private operator-review packet rollback boundary missing")
    require("Operator packet verified · decision not run" in js and 'operatorReviewStatus: "not_run"' in adapter, "private operator-review packet decision hold missing")
    require("The verified upstream completion review remains available" in js, "private operator-review packet refusal must preserve upstream review")
    require("Preparation is not an operator review" in adapter and "Prepare one packet. Decide nothing." in js, "private operator-review packet authority boundary missing")
    checks += 117

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
    require(
        '@media (max-width: 359px)' in css
        and '.demo-badge { display: none; }' in css
        and '.topbar-actions { gap: 4px; }' in css
        and '.avatar-button { display: none; }' not in css,
        "320px header must preserve both local action controls without overflow",
    )
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
    html_asset_version_pairs = re.findall(
        r'(?:href|src)="(styles\.css|data-adapter\.js|app\.js)\?v=(\d+)"', html
    )
    require(
        sorted(name for name, _version in html_asset_version_pairs) == ["app.js", "data-adapter.js", "styles.css"],
        "HTML must address every versioned executable shell asset exactly once",
    )
    html_asset_versions = dict(html_asset_version_pairs)
    require(
        set(html_asset_versions.values()) == {EXPECTED_SHELL_VERSION},
        "HTML executable shell assets must share the current cache generation",
    )
    require(
        webmanifest.get("start_url") == f"./index.html?v={EXPECTED_SHELL_VERSION}",
        "web manifest start URL must share the current cache generation",
    )
    cache_name_match = re.search(r'CACHE_NAME = "builderwars-mobile-arena-v(\d+)"', sw)
    navigation_match = re.search(r'NAVIGATION_FALLBACK = "\./index\.html\?v=(\d+)"', sw)
    require(cache_name_match is not None, "service-worker cache generation declaration missing")
    require(navigation_match is not None, "service-worker navigation generation declaration missing")
    require(
        {cache_name_match.group(1), navigation_match.group(1), *html_asset_versions.values()} == {EXPECTED_SHELL_VERSION},
        "HTML, manifest, cache, and navigation generations must remain coherent",
    )
    for offline_asset in (
        f"./index.html?v={EXPECTED_SHELL_VERSION}",
        f"./styles.css?v={EXPECTED_SHELL_VERSION}",
        f"./data-adapter.js?v={EXPECTED_SHELL_VERSION}",
        f"./app.js?v={EXPECTED_SHELL_VERSION}",
        "./manifest.webmanifest",
        "./assets/arena-mark.svg",
        "./data/demo-state.json",
        "./data/arena-read-model.v1.json",
        "./data/tester-feedback-rubric.v1.json",
        "./data/creator-game-lab.v1.json",
    ):
        require(f'"{offline_asset}"' in sw, f"service-worker cache misses {offline_asset}")
        checks += 1
    require('new Request(asset, { cache: "reload" })' in sw, "service-worker install must bypass stale HTTP cache")
    require('event.request.mode === "navigate"' in sw, "HTML fallback must be limited to navigation requests")
    require("return Response.error()" in sw, "uncached offline resources must fail instead of masquerading as HTML")
    addressed_versions = set(re.findall(r"\?v=(\d+)", "\n".join((html, sw, json.dumps(webmanifest)))))
    require(addressed_versions == {EXPECTED_SHELL_VERSION}, "only the current shell generation may remain addressable")
    checks += 3
    checks += 7

    tester_feedback_check = subprocess.run(
        [
            node,
            "-e",
            (
                "const fs=require('fs');const a=require(" + json.dumps(str(MOBILE / "data-adapter.js")) + ");"
                "const r=JSON.parse(fs.readFileSync(" + json.dumps(str(MOBILE / "data" / "tester-feedback-rubric.v1.json")) + ",'utf8'));"
                "(async()=>{await a.validateTesterFeedbackRubric(r);"
                "const ratings=Object.fromEntries(r.categories.map((c,i)=>[c.categoryId,(i%5)+1]));"
                "const out=await a.createTesterFeedbackDraft(r,ratings,'provider_boundary','truth_overclaim');"
                "const verified=await a.verifyTesterFeedbackDraft(out.serialized,r);"
                "if(verified.draftStatus!=='LOCAL_DRAFT_NOT_COLLECTED'||verified.ratings.length!==8||verified.identityFieldsAllowed.length!==0||verified.freeTextIncluded!==false||verified.storageMode!=='browser_memory_only'||verified.transportStatus!=='not_configured'||verified.humanFeedbackCollected!==false)process.exit(2);"
                "if(Object.values(verified.productionAuthority).some(Boolean))process.exit(3);"
                "let refused=0;try{await a.createTesterFeedbackDraft(r,{...ratings,orientation_clarity:0},'none','none')}catch{refused++}"
                "try{await a.verifyTesterFeedbackDraft(out.serialized.replace('not_submitted','submitted'),r)}catch{refused++}"
                "if(refused!==2)process.exit(4);console.log('PASS');})().catch(e=>{console.error(e);process.exit(1)})"
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
    require(tester_feedback_check.returncode == 0, f"tester feedback adapter check failed: {tester_feedback_check.stderr.strip()}")
    require("PASS" in tester_feedback_check.stdout, "tester feedback adapter check did not report PASS")
    checks += 2

    scoped_ratings_check = subprocess.run(
        [str(Path(shutil.which("python") or "python")), str(ROOT / "bin" / "check_agentwars_scoped_ratings.py")],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
    )
    require(scoped_ratings_check.returncode == 0, f"scoped proof-rating regression failed: {scoped_ratings_check.stderr.strip()}")
    require("PASS" in scoped_ratings_check.stdout, "scoped proof-rating regression did not report PASS")
    checks += 2

    corrections_check = subprocess.run(
        [str(Path(shutil.which("python") or "python")), str(ROOT / "bin" / "check_agentwars_corrections.py")],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
    )
    require(corrections_check.returncode == 0, f"append-only correction regression failed: {corrections_check.stderr.strip()}")
    require("PASS" in corrections_check.stdout, "append-only correction regression did not report PASS")
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

    local_exhibition_check = subprocess.run(
        [str(Path(shutil.which("python") or "python")), str(ROOT / "bin" / "check_mobile_arena_local_exhibition.py")],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
    )
    require(local_exhibition_check.returncode == 0, f"local exhibition regression failed: {local_exhibition_check.stderr.strip()}")
    require("PASS" in local_exhibition_check.stdout, "local exhibition regression did not report PASS")
    checks += 2

    spectator_rehearsal_check = subprocess.run(
        [str(Path(shutil.which("python") or "python")), str(ROOT / "bin" / "check_mobile_arena_spectator_rehearsal.py")],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
    )
    require(spectator_rehearsal_check.returncode == 0, f"spectator rehearsal regression failed: {spectator_rehearsal_check.stderr.strip()}")
    require("PASS" in spectator_rehearsal_check.stdout, "spectator rehearsal regression did not report PASS")
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

    portable_review_exchange_check = subprocess.run(
        [str(Path(shutil.which("python") or "python")), str(ROOT / "bin" / "check_mobile_arena_portable_review_exchange.py")],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=90,
        check=False,
    )
    require(portable_review_exchange_check.returncode == 0, f"portable review exchange regression failed: {portable_review_exchange_check.stderr.strip()}")
    require("PASS" in portable_review_exchange_check.stdout, "portable review exchange regression did not report PASS")
    checks += 2

    portable_review_correction_check = subprocess.run(
        [str(Path(shutil.which("python") or "python")), str(ROOT / "bin" / "check_mobile_arena_portable_review_correction.py")],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=120,
        check=False,
    )
    require(portable_review_correction_check.returncode == 0, f"portable review correction regression failed: {portable_review_correction_check.stderr.strip()}")
    require("PASS" in portable_review_correction_check.stdout, "portable review correction regression did not report PASS")
    checks += 2

    private_review_comparison_check = subprocess.run(
        [str(Path(shutil.which("python") or "python")), str(ROOT / "bin" / "check_mobile_arena_private_review_comparison.py")],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=120,
        check=False,
    )
    require(private_review_comparison_check.returncode == 0, f"private review comparison regression failed: {private_review_comparison_check.stderr.strip()}")
    require("PASS" in private_review_comparison_check.stdout, "private review comparison regression did not report PASS")
    checks += 2

    private_review_learning_check = subprocess.run(
        [str(Path(shutil.which("python") or "python")), str(ROOT / "bin" / "check_mobile_arena_private_review_learning.py")],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=120,
        check=False,
    )
    require(private_review_learning_check.returncode == 0, f"private review inspection learning regression failed: {private_review_learning_check.stderr.strip()}")
    require("PASS" in private_review_learning_check.stdout, "private review inspection learning regression did not report PASS")
    checks += 2

    private_blueprint_delta_check = subprocess.run(
        [str(Path(shutil.which("python") or "python")), str(ROOT / "bin" / "check_mobile_arena_private_blueprint_delta.py")],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=180,
        check=False,
    )
    require(private_blueprint_delta_check.returncode == 0, f"private blueprint-delta regression failed: {private_blueprint_delta_check.stderr.strip()}")
    require("PASS" in private_blueprint_delta_check.stdout, "private blueprint-delta regression did not report PASS")
    checks += 2

    private_blueprint_delta_review_check = subprocess.run(
        [str(Path(shutil.which("python") or "python")), str(ROOT / "bin" / "check_mobile_arena_private_blueprint_delta_review.py")],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=180,
        check=False,
    )
    require(private_blueprint_delta_review_check.returncode == 0, f"private blueprint-delta review regression failed: {private_blueprint_delta_review_check.stderr.strip()}")
    require("PASS" in private_blueprint_delta_review_check.stdout, "private blueprint-delta review regression did not report PASS")
    checks += 2

    private_blueprint_revision_check = subprocess.run(
        [str(Path(shutil.which("python") or "python")), str(ROOT / "bin" / "check_mobile_arena_private_blueprint_revision.py")],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=180,
        check=False,
    )
    require(private_blueprint_revision_check.returncode == 0, f"private blueprint revision-draft regression failed: {private_blueprint_revision_check.stderr.strip()}")
    require("PASS" in private_blueprint_revision_check.stdout, "private blueprint revision-draft regression did not report PASS")
    checks += 2

    private_blueprint_draft_review_check = subprocess.run(
        [str(Path(shutil.which("python") or "python")), str(ROOT / "bin" / "check_mobile_arena_private_blueprint_draft_review.py")],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=180,
        check=False,
    )
    require(private_blueprint_draft_review_check.returncode == 0, f"private blueprint draft-review regression failed: {private_blueprint_draft_review_check.stderr.strip()}")
    require("PASS" in private_blueprint_draft_review_check.stdout, "private blueprint draft-review regression did not report PASS")
    checks += 2

    private_blueprint_guard_completion_check = subprocess.run(
        [str(Path(shutil.which("python") or "python")), str(ROOT / "bin" / "check_mobile_arena_private_blueprint_guard_completion.py")],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=180,
        check=False,
    )
    require(private_blueprint_guard_completion_check.returncode == 0, f"private blueprint guard-completion regression failed: {private_blueprint_guard_completion_check.stderr.strip()}")
    require("PASS" in private_blueprint_guard_completion_check.stdout, "private blueprint guard-completion regression did not report PASS")
    checks += 2

    private_blueprint_guard_completion_review_check = subprocess.run(
        [str(Path(shutil.which("python") or "python")), str(ROOT / "bin" / "check_mobile_arena_private_blueprint_guard_completion_review.py")],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=240,
        check=False,
    )
    require(private_blueprint_guard_completion_review_check.returncode == 0, f"private guard-completion review regression failed: {private_blueprint_guard_completion_review_check.stderr.strip()}")
    require("PASS" in private_blueprint_guard_completion_review_check.stdout, "private guard-completion review regression did not report PASS")
    checks += 2

    private_blueprint_operator_review_packet_check = subprocess.run(
        [str(Path(shutil.which("python") or "python")), str(ROOT / "bin" / "check_mobile_arena_private_blueprint_operator_review_packet.py")],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=240,
        check=False,
    )
    require(private_blueprint_operator_review_packet_check.returncode == 0, f"private operator-review packet regression failed: {private_blueprint_operator_review_packet_check.stderr.strip()}")
    require("PASS" in private_blueprint_operator_review_packet_check.stdout, "private operator-review packet regression did not report PASS")
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
