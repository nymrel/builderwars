"""Finite, truth-bounded fantasy league operations contracts for AgentWars.

This module describes one private-alpha redraft season and the operational
decisions around it.  It schedules nothing, admits nobody, mutates no standing,
and grants no moderation, publication, provider, or production authority.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime, timezone

from arena.games import load


CONTRACT_SCHEMA = "agentwars.finite-league-contract/1"
DECISION_SCHEMA = "agentwars.league-operations-decision/1"
CORRECTION_SCHEMA = "agentwars.league-correction-candidate/1"

UTC_SECOND_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
CORRECTION_ID_RE = re.compile(r"^awlcorr_[0-9a-f]{32}$")
FIXTURE_ID_RE = re.compile(r"^awfix_[0-9a-f]{32}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

PRODUCTION_AUTHORITY = {
    "seasonScheduled": False,
    "entrantsAdmitted": False,
    "fixturesActivated": False,
    "rankingsPublished": False,
    "supportQueueStaffed": False,
    "moderationActionExecuted": False,
    "correctionCommitted": False,
    "creatorGameAdmitted": False,
    "publicExecutionEnabled": False,
    "launchable": False,
}

SUPPORT_CLASSES = (
    {
        "severity": "sev1",
        "issueClasses": ["receipt_integrity", "secret_exposure", "provider_boundary", "deletion_or_cleanup"],
        "releasePosture": "hold_release_and_new_admissions",
        "requiredEvidence": ["redacted_case_class", "source_binding", "impact_scope", "resolution_receipt"],
        "responseTimePromise": None,
    },
    {
        "severity": "sev2",
        "issueClasses": ["rules_or_seed_drift", "accessibility_blocker", "fixture_availability", "correction_dispute"],
        "releasePosture": "hold_affected_flow",
        "requiredEvidence": ["redacted_case_class", "reproduction", "affected_fixture_ids", "reverification_receipt"],
        "responseTimePromise": None,
    },
    {
        "severity": "sev3",
        "issueClasses": ["orientation_confusion", "receipt_explanation", "runback_explanation"],
        "releasePosture": "continue_local_validation_only",
        "requiredEvidence": ["redacted_case_class", "bounded_reproduction", "documentation_decision"],
        "responseTimePromise": None,
    },
)

MODERATION_RULES = (
    {
        "caseClass": "collusion_or_common_control_ambiguity",
        "defaultPosture": "hold_fixture_and_exclude_from_standings",
        "requiredEvidence": ["fixture_id", "entrant_version_digests", "control_review_receipt"],
    },
    {
        "caseClass": "abusive_or_deceptive_public_label",
        "defaultPosture": "hold_public_derivative_only",
        "requiredEvidence": ["derivative_digest", "bounded_policy_class", "review_receipt"],
    },
    {
        "caseClass": "receipt_or_rules_integrity_mismatch",
        "defaultPosture": "freeze_standings_and_require_correction_candidate",
        "requiredEvidence": ["fixture_id", "original_receipt_digest", "replay_report", "rules_digest"],
    },
    {
        "caseClass": "provider_or_execution_boundary_breach",
        "defaultPosture": "hold_release_and_new_admissions",
        "requiredEvidence": ["redacted_boundary_class", "source_binding", "containment_receipt", "cleanup_receipt"],
    },
)

CORRECTION_CLASSES = (
    "void_fixture",
    "replace_receipt_after_verified_replay",
    "correct_public_label",
    "amend_standings_after_committed_source",
)

PROHIBITED_CLAIMS = (
    "live_league",
    "external_participation",
    "model_or_provider_identity_attested",
    "public_or_universal_ranking",
    "staffed_support",
    "moderation_action_completed",
    "correction_committed",
    "creator_game_admitted",
    "retention_or_audience_measured",
)

_CASE_DECISIONS = {
    "receipt_integrity_mismatch": {
        "severity": "sev1",
        "releaseDecision": "HOLD_RELEASE_AND_STANDINGS",
        "fixtureDecision": "HOLD_AFFECTED_FIXTURE",
        "supportAction": "OPEN_INTEGRITY_CASE_CANDIDATE",
        "moderationAction": "NO_EXECUTION_REVIEW_REQUIRED",
        "correctionAction": "BUILD_APPEND_ONLY_CORRECTION_CANDIDATE",
        "rollbackRecommendation": "ASSESS_LAST_KNOWN_GOOD",
    },
    "secret_exposure_suspected": {
        "severity": "sev1",
        "releaseDecision": "HOLD_RELEASE_AND_NEW_ADMISSIONS",
        "fixtureDecision": "HOLD_ALL_UNPUBLISHED_FIXTURES",
        "supportAction": "OPEN_SECURITY_CASE_CANDIDATE",
        "moderationAction": "NO_EXECUTION_SECURITY_REVIEW_REQUIRED",
        "correctionAction": "NO_CORRECTION_UNTIL_SCOPE_CONFIRMED",
        "rollbackRecommendation": "ROLLBACK_CANDIDATE",
    },
    "provider_boundary_breach": {
        "severity": "sev1",
        "releaseDecision": "HOLD_RELEASE_AND_NEW_ADMISSIONS",
        "fixtureDecision": "HOLD_AFFECTED_FIXTURE",
        "supportAction": "OPEN_PROVIDER_BOUNDARY_CASE_CANDIDATE",
        "moderationAction": "NO_EXECUTION_BOUNDARY_REVIEW_REQUIRED",
        "correctionAction": "VOID_CANDIDATE_AFTER_REVIEW",
        "rollbackRecommendation": "ASSESS_LAST_KNOWN_GOOD",
    },
    "collusion_or_common_control_ambiguity": {
        "severity": "sev2",
        "releaseDecision": "HOLD_AFFECTED_STANDINGS",
        "fixtureDecision": "EXCLUDE_PENDING_REVIEW",
        "supportAction": "OPEN_COMPETITIVE_INTEGRITY_CASE_CANDIDATE",
        "moderationAction": "NO_EXECUTION_CONTROL_REVIEW_REQUIRED",
        "correctionAction": "VOID_CANDIDATE_AFTER_REVIEW",
        "rollbackRecommendation": "NOT_RECOMMENDED",
    },
    "rules_or_seed_drift": {
        "severity": "sev2",
        "releaseDecision": "HOLD_AFFECTED_FORMAT",
        "fixtureDecision": "HOLD_AFFECTED_FIXTURE",
        "supportAction": "OPEN_RULES_CASE_CANDIDATE",
        "moderationAction": "NO_EXECUTION_REVIEW_REQUIRED",
        "correctionAction": "REPLAY_THEN_BUILD_CORRECTION_CANDIDATE",
        "rollbackRecommendation": "ASSESS_LAST_KNOWN_GOOD",
    },
    "abusive_public_label": {
        "severity": "sev2",
        "releaseDecision": "HOLD_PUBLIC_DERIVATIVE",
        "fixtureDecision": "RETAIN_IMMUTABLE_PRIVATE_RECEIPT",
        "supportAction": "OPEN_CONTENT_CASE_CANDIDATE",
        "moderationAction": "NO_EXECUTION_LABEL_REVIEW_REQUIRED",
        "correctionAction": "CORRECT_LABEL_CANDIDATE_AFTER_REVIEW",
        "rollbackRecommendation": "NOT_RECOMMENDED",
    },
    "accessibility_blocker": {
        "severity": "sev2",
        "releaseDecision": "HOLD_AFFECTED_FLOW",
        "fixtureDecision": "NO_CHANGE",
        "supportAction": "OPEN_ACCESSIBILITY_CASE_CANDIDATE",
        "moderationAction": "NO_ACTION",
        "correctionAction": "NO_CORRECTION",
        "rollbackRecommendation": "ASSESS_AFFECTED_SURFACE",
    },
    "ordinary_support_confusion": {
        "severity": "sev3",
        "releaseDecision": "CONTINUE_LOCAL_VALIDATION_ONLY",
        "fixtureDecision": "NO_CHANGE",
        "supportAction": "DOCUMENTATION_REVIEW_CANDIDATE",
        "moderationAction": "NO_ACTION",
        "correctionAction": "NO_CORRECTION",
        "rollbackRecommendation": "NOT_RECOMMENDED",
    },
}
CASE_IDS = tuple(_CASE_DECISIONS)


class LeagueOperationsError(ValueError):
    """Raised when a finite-league or operations candidate fails closed."""


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _parse_timestamp(value: object, label: str) -> None:
    if type(value) is not str or not UTC_SECOND_RE.fullmatch(value):
        raise LeagueOperationsError(f"{label} must be a UTC whole-second timestamp")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise LeagueOperationsError(f"{label} must be a valid UTC timestamp") from error


def _format_contract(
    *, game_name: str, format_id: str, scoring_horizon: str, season_status: str, standings_scope: str
) -> dict[str, object]:
    game = load(game_name)
    rules_identity = {
        "gameName": game.NAME,
        "gameVersion": game.VERSION,
        "rules": game.RULES,
    }
    return {
        "formatId": format_id,
        "gameName": game.NAME,
        "gameVersion": game.VERSION,
        "rulesDigest": digest(rules_identity),
        "scoringHorizon": scoring_horizon,
        "seasonStatus": season_status,
        "standingsScope": standings_scope,
        "rosterCarryoverAuthorized": False,
        "ratingCarryoverAuthorized": False,
    }


def finite_league_contract() -> dict[str, object]:
    redraft = _format_contract(
        game_name="fantasy_redraft",
        format_id="redraft",
        scoring_horizon="one_season_score",
        season_status="active_contract_only_not_scheduled",
        standings_scope="redraft_crown_private_alpha_v1",
    )
    dynasty = _format_contract(
        game_name="fantasy_dynasty",
        format_id="dynasty",
        scoring_horizon="three_year_value",
        season_status="separate_future_cohort_not_scheduled",
        standings_scope="dynasty_throne_separate_cohort_v1",
    )
    contract: dict[str, object] = {
        "schemaVersion": CONTRACT_SCHEMA,
        "contractStatus": "local_contract_only_not_scheduled",
        "leagueId": "agentwars-redraft-crown-private-alpha-v1",
        "competitionClass": "scripted_preseason_rules_and_operations_proof",
        "activeFormatId": "redraft",
        "formats": [redraft, dynasty],
        "fixturePlan": {
            "entrantVersionCount": 2,
            "seedSet": [9100, 9101, 9102, 9103],
            "seatPolicy": "every_seed_both_seat_orders",
            "expectedFixtureCount": 8,
            "receiptPolicy": "replay_pass_required_before_standings_candidate",
            "activationStatus": "not_activated",
        },
        "entrantPolicy": {
            "passportPolicy": "two_distinct_versioned_passports_required_for_real_alpha",
            "harnessPolicy": "exact_harness_digest_required",
            "modelClaimPolicy": "self_claim_separate_from_attestation",
            "executionClaimPolicy": "observed_source_claim_separate_from_identity_attestation",
            "providerPolicy": "sanctioned_customer_controlled_mode_required",
            "externalEntrantsAdmitted": False,
        },
        "standingsPolicy": {
            "sortOrder": ["wins_desc", "ties_desc", "aggregate_score_desc", "entrant_version_id_asc"],
            "ratingScope": "league_plus_season_plus_game_plus_rules_plus_resource_class",
            "universalModelRankingAuthorized": False,
            "scriptedPreseasonExcludedFromPublicRank": True,
            "correctionHistory": "append_only",
        },
        "supportPolicy": [copy.deepcopy(item) for item in SUPPORT_CLASSES],
        "moderationPolicy": [copy.deepcopy(item) for item in MODERATION_RULES],
        "correctionPolicy": {
            "allowedClasses": list(CORRECTION_CLASSES),
            "originalReceiptPolicy": "immutable",
            "journalPolicy": "append_only_digest_bound",
            "standingsMutationPolicy": "separate_reviewed_source_commit_required",
            "silentRewriteAuthorized": False,
        },
        "rollbackPolicy": {
            "triggers": [
                "receipt_integrity_mismatch",
                "secret_exposure_suspected",
                "provider_boundary_breach",
                "rules_or_seed_drift",
                "cleanup_failure",
            ],
            "targetPolicy": "exact_last_known_good_source_and_artifact_digests_required",
            "evidencePreservation": "retain_signed_receipts_and_append_correction_state",
            "rollbackExecuted": False,
        },
        "creatorAdmissionBoundary": {
            "candidateGameId": "creator.signal-siege",
            "candidateVersion": "1.0.0",
            "candidateManifestDigest": "691e7e77ff333f3ac64ae4e801c5b682bbcd755fb46a9aa138137be1e1d17504",
            "registryDecision": "held_exhibition_candidate",
            "includedInLeague": False,
            "arbitraryCreatorCodeAccepted": False,
            "admissionStatus": "held_not_runtime_admission",
        },
        "prohibitedClaims": list(PROHIBITED_CLAIMS),
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    contract["contractDigest"] = digest(contract)
    return contract


def verify_finite_league_contract(candidate: object) -> dict[str, object]:
    if type(candidate) is not dict:
        raise LeagueOperationsError("finite league contract must be an exact object")
    expected = finite_league_contract()
    if candidate != expected:
        raise LeagueOperationsError("finite league contract drift")
    unsigned = dict(candidate)
    supplied = unsigned.pop("contractDigest")
    if type(supplied) is not str or not HEX64_RE.fullmatch(supplied) or digest(unsigned) != supplied:
        raise LeagueOperationsError("finite league contract digest mismatch")
    return candidate


def evaluate_operations_case(*, case_id: str, observed_at: str) -> dict[str, object]:
    _parse_timestamp(observed_at, "observedAt")
    if type(case_id) is not str or case_id not in _CASE_DECISIONS:
        raise LeagueOperationsError("operations case is unsupported")
    decision: dict[str, object] = {
        "schemaVersion": DECISION_SCHEMA,
        "observedAt": observed_at,
        "leagueContractDigest": finite_league_contract()["contractDigest"],
        "caseId": case_id,
        **_CASE_DECISIONS[case_id],
        "actionsExecuted": False,
        "operatorDecisionRecorded": False,
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    decision["decisionDigest"] = digest(decision)
    return decision


def verify_operations_decision(candidate: object) -> dict[str, object]:
    if type(candidate) is not dict:
        raise LeagueOperationsError("operations decision must be an exact object")
    expected_fields = {
        "schemaVersion", "observedAt", "leagueContractDigest", "caseId", "severity",
        "releaseDecision", "fixtureDecision", "supportAction", "moderationAction",
        "correctionAction", "rollbackRecommendation", "actionsExecuted",
        "operatorDecisionRecorded", "productionAuthority", "decisionDigest",
    }
    if set(candidate) != expected_fields:
        raise LeagueOperationsError("operations decision fields drift")
    rebuilt = evaluate_operations_case(case_id=candidate["caseId"], observed_at=candidate["observedAt"])
    if candidate != rebuilt:
        raise LeagueOperationsError("operations decision drift")
    return candidate


def build_correction_candidate(
    *,
    correction_id: str,
    proposed_at: str,
    fixture_id: str,
    original_receipt_digest: str,
    correction_class: str,
    replacement_receipt_digest: str | None = None,
) -> dict[str, object]:
    _parse_timestamp(proposed_at, "proposedAt")
    if type(correction_id) is not str or not CORRECTION_ID_RE.fullmatch(correction_id):
        raise LeagueOperationsError("correction id is malformed")
    if type(fixture_id) is not str or not FIXTURE_ID_RE.fullmatch(fixture_id):
        raise LeagueOperationsError("fixture id is malformed")
    if type(original_receipt_digest) is not str or not HEX64_RE.fullmatch(original_receipt_digest):
        raise LeagueOperationsError("original receipt digest is malformed")
    if type(correction_class) is not str or correction_class not in CORRECTION_CLASSES:
        raise LeagueOperationsError("correction class is unsupported")
    replacement_required = correction_class == "replace_receipt_after_verified_replay"
    if replacement_required:
        if type(replacement_receipt_digest) is not str or not HEX64_RE.fullmatch(replacement_receipt_digest):
            raise LeagueOperationsError("replacement receipt digest is required")
        if replacement_receipt_digest == original_receipt_digest:
            raise LeagueOperationsError("replacement receipt must differ from the original")
    elif replacement_receipt_digest is not None:
        raise LeagueOperationsError("replacement receipt is not allowed for this correction class")
    candidate: dict[str, object] = {
        "schemaVersion": CORRECTION_SCHEMA,
        "correctionId": correction_id,
        "proposedAt": proposed_at,
        "leagueContractDigest": finite_league_contract()["contractDigest"],
        "fixtureId": fixture_id,
        "originalReceiptDigest": original_receipt_digest,
        "correctionClass": correction_class,
        "replacementReceiptDigest": replacement_receipt_digest,
        "status": "proposed_uncommitted",
        "originalReceiptImmutable": True,
        "standingsMutationExecuted": False,
        "publicationMutationExecuted": False,
        "operatorDecisionRecorded": False,
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    candidate["candidateDigest"] = digest(candidate)
    return candidate


def verify_correction_candidate(candidate: object) -> dict[str, object]:
    if type(candidate) is not dict:
        raise LeagueOperationsError("correction candidate must be an exact object")
    expected_fields = {
        "schemaVersion", "correctionId", "proposedAt", "leagueContractDigest", "fixtureId",
        "originalReceiptDigest", "correctionClass", "replacementReceiptDigest", "status",
        "originalReceiptImmutable", "standingsMutationExecuted", "publicationMutationExecuted",
        "operatorDecisionRecorded", "productionAuthority", "candidateDigest",
    }
    if set(candidate) != expected_fields:
        raise LeagueOperationsError("correction candidate fields drift")
    rebuilt = build_correction_candidate(
        correction_id=candidate["correctionId"],
        proposed_at=candidate["proposedAt"],
        fixture_id=candidate["fixtureId"],
        original_receipt_digest=candidate["originalReceiptDigest"],
        correction_class=candidate["correctionClass"],
        replacement_receipt_digest=candidate["replacementReceiptDigest"],
    )
    if candidate != rebuilt:
        raise LeagueOperationsError("correction candidate drift")
    return candidate
