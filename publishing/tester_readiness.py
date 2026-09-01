"""Pure tester-ceremony readiness contracts for AgentWars.

The module builds a synthetic local rehearsal, an uncollected feedback
placeholder, a cleanup simulation, a readiness decision, and a protected
operator packet. It performs no I/O and cannot attest a human, consent,
identity, authentication, provider use, deployment, deletion, rollback,
independent review, or launch authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Iterable, Mapping


CONTRACT_SCHEMA = "agentwars.tester-ceremony-contract/1"
REHEARSAL_SCHEMA = "agentwars.synthetic-tester-rehearsal/1"
FEEDBACK_SCHEMA = "agentwars.tester-feedback-rubric/1"
FEEDBACK_PLACEHOLDER_SCHEMA = "agentwars.tester-feedback-placeholder/1"
CLEANUP_SCHEMA = "agentwars.tester-cleanup-rehearsal/1"
READINESS_SCHEMA = "agentwars.tester-readiness-decision/1"
OPERATOR_PACKET_SCHEMA = "agentwars.tester-operator-packet/1"

UTC_SECOND_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
PACKET_ID_RE = re.compile(r"^awtest_[0-9a-f]{32}$")

PRODUCTION_AUTHORITY = {
    "humanConsentAttested": False,
    "humanIdentityAttested": False,
    "authenticatedJourneyCompleted": False,
    "providerMatchCompleted": False,
    "independentReviewCompleted": False,
    "boundedPublicationCompleted": False,
    "accountDeletionCompleted": False,
    "productionRollbackCompleted": False,
    "operatorActionExecuted": False,
    "launchAuthorized": False,
    "publicLaunch": False,
}

JOURNEY_STEPS: tuple[dict[str, object], ...] = (
    {
        "order": 1,
        "stepId": "truth_boundary_disclosure",
        "label": "Read the local, provider, identity, ranking, publication, and launch boundaries",
        "localRehearsal": "required",
        "productionEvidenceRequired": ["fresh_customer_acknowledgement", "served_disclosure_digest"],
    },
    {
        "order": 2,
        "stepId": "exact_release_target",
        "label": "Bind the ceremony to the exact reviewed deployment and rollback target",
        "localRehearsal": "not_applicable_protected",
        "productionEvidenceRequired": ["deployment_id", "served_byte_digest", "rollback_target_digest"],
    },
    {
        "order": 3,
        "stepId": "mobile_desktop_access",
        "label": "Open the Arena on supported mobile and desktop viewports",
        "localRehearsal": "required",
        "productionEvidenceRequired": ["mobile_session_receipt", "desktop_session_receipt"],
    },
    {
        "order": 4,
        "stepId": "authentication_lifecycle",
        "label": "Sign up, sign out, and sign back in",
        "localRehearsal": "not_applicable_protected",
        "productionEvidenceRequired": ["redacted_signup_receipt", "signout_receipt", "signin_receipt"],
    },
    {
        "order": 5,
        "stepId": "runner_pair_and_recover",
        "label": "Pair a customer-owned runner and recover after deliberate disconnect",
        "localRehearsal": "not_applicable_protected",
        "productionEvidenceRequired": ["pairing_receipt", "disconnect_receipt", "recovery_receipt"],
    },
    {
        "order": 6,
        "stepId": "two_distinct_passports",
        "label": "Create two encrypted agent and harness passports with truthful declarations",
        "localRehearsal": "not_applicable_protected",
        "productionEvidenceRequired": ["passport_a_digest", "passport_b_digest", "custody_receipt"],
    },
    {
        "order": 7,
        "stepId": "local_build_qualify_learn",
        "label": "Build a local blueprint, inspect qualification, and reach a receipt-linked learning action",
        "localRehearsal": "required",
        "productionEvidenceRequired": ["builder_flow_receipt", "qualification_receipt", "learning_receipt"],
    },
    {
        "order": 8,
        "stepId": "genuine_provider_match",
        "label": "Complete one sanctioned model-and-harness versus model-and-harness match",
        "localRehearsal": "not_applicable_protected",
        "productionEvidenceRequired": ["fresh_provider_consent", "match_receipt", "cost_receipt"],
    },
    {
        "order": 9,
        "stepId": "deterministic_replay_and_proof",
        "label": "Replay the result and inspect the truthful proof projection",
        "localRehearsal": "required",
        "productionEvidenceRequired": ["replay_receipt", "proof_projection_digest"],
    },
    {
        "order": 10,
        "stepId": "private_review_bounded_publication",
        "label": "Submit privately, obtain independent review, and publish only the bounded projection",
        "localRehearsal": "not_applicable_protected",
        "productionEvidenceRequired": ["private_submission_receipt", "independent_review_signature", "publication_receipt"],
    },
    {
        "order": 11,
        "stepId": "spectator_share_and_runback",
        "label": "Open the spectator proof share and launch an exact runback",
        "localRehearsal": "required",
        "productionEvidenceRequired": ["share_transport_receipt", "spectator_probe", "runback_receipt"],
    },
    {
        "order": 12,
        "stepId": "failure_accessibility_offline",
        "label": "Exercise error, storage-denial, offline, reduced-motion, and accessibility paths",
        "localRehearsal": "required",
        "productionEvidenceRequired": ["supported_device_receipts", "accessibility_receipt", "offline_error_receipt"],
    },
    {
        "order": 13,
        "stepId": "runner_revocation_artifact_cleanup",
        "label": "Revoke the runner and remove customer-local and provider artifacts",
        "localRehearsal": "not_applicable_protected",
        "productionEvidenceRequired": ["revocation_receipt", "local_cleanup_receipt", "provider_cleanup_receipt"],
    },
    {
        "order": 14,
        "stepId": "account_deletion_hosted_cleanup",
        "label": "Delete the account and prove tenant-scoped hosted cleanup",
        "localRehearsal": "not_applicable_protected",
        "productionEvidenceRequired": ["account_deletion_receipt", "webhook_receipt", "hosted_cleanup_receipt"],
    },
    {
        "order": 15,
        "stepId": "rollback_preserve_evidence",
        "label": "Execute rollback and preserve the signed evidence trail",
        "localRehearsal": "not_applicable_protected",
        "productionEvidenceRequired": ["rollback_receipt", "post_rollback_probe", "evidence_chain_verification"],
    },
    {
        "order": 16,
        "stepId": "structured_feedback",
        "label": "Collect consented structured feedback and triage severe confusion",
        "localRehearsal": "not_applicable_protected",
        "productionEvidenceRequired": ["feedback_receipt", "blocker_triage_receipt"],
    },
)

FEEDBACK_CATEGORIES: tuple[dict[str, str], ...] = (
    {"categoryId": "orientation_clarity", "prompt": "I knew what to do next."},
    {"categoryId": "truth_boundary_comprehension", "prompt": "I understood what was live, local, verified, and unattested."},
    {"categoryId": "receipt_replay_trust", "prompt": "The proof and replay made the result understandable and trustworthy."},
    {"categoryId": "build_compete_clarity", "prompt": "Building, qualifying, and competing felt coherent."},
    {"categoryId": "share_runback_clarity", "prompt": "Sharing and starting a runback were understandable."},
    {"categoryId": "recovery_cleanup_confidence", "prompt": "Revocation, deletion, cleanup, and recovery were clear."},
    {"categoryId": "accessibility_usability", "prompt": "The experience was usable on my device and access needs."},
    {"categoryId": "return_intent", "prompt": "I would return for another eligible competition."},
)

BLOCKER_CLASSES = (
    "access", "authentication", "pairing", "passport", "build", "qualification", "match",
    "proof", "replay", "review", "publication", "share", "runback", "cleanup", "deletion",
    "rollback", "accessibility", "safety", "provider_boundary", "none",
)

CLEANUP_RESOURCES: tuple[dict[str, str], ...] = (
    {"resourceClass": "browser_local_blueprint", "localRehearsal": "required"},
    {"resourceClass": "browser_storage", "localRehearsal": "required"},
    {"resourceClass": "service_worker_cache", "localRehearsal": "required"},
    {"resourceClass": "synthetic_rehearsal_state", "localRehearsal": "required"},
    {"resourceClass": "runner_pairing", "localRehearsal": "not_applicable_protected"},
    {"resourceClass": "encrypted_passports", "localRehearsal": "not_applicable_protected"},
    {"resourceClass": "provider_artifacts", "localRehearsal": "not_applicable_protected"},
    {"resourceClass": "private_submission", "localRehearsal": "not_applicable_protected"},
    {"resourceClass": "hosted_tenant_records", "localRehearsal": "not_applicable_protected"},
    {"resourceClass": "customer_account", "localRehearsal": "not_applicable_protected"},
    {"resourceClass": "production_test_release", "localRehearsal": "not_applicable_protected"},
)

PROHIBITED_SHORTCUTS = (
    "internal_operator_account_as_customer_proof",
    "fixture_or_mock_as_provider_proof",
    "self_declared_model_label_as_attestation",
    "deployment_dashboard_as_served_byte_proof",
    "synthetic_feedback_as_human_feedback",
    "logical_tombstone_as_physical_deletion_proof",
    "local_recovery_drill_as_production_rollback_proof",
)


class TesterReadinessError(ValueError):
    """Raised when a tester-readiness input drifts or overclaims."""


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _exact(value: object, fields: set[str], label: str) -> dict[str, object]:
    if type(value) is not dict or set(value) != fields:
        raise TesterReadinessError(f"{label} fields drift")
    return value


def _match(value: object, pattern: re.Pattern[str], label: str) -> str:
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise TesterReadinessError(f"{label} is malformed")
    return value


def _timestamp(value: object, label: str) -> datetime:
    if type(value) is not str or UTC_SECOND_RE.fullmatch(value) is None:
        raise TesterReadinessError(f"{label} must be a UTC whole-second timestamp")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise TesterReadinessError(f"{label} is not a valid timestamp") from error


def _authority(value: object, label: str) -> dict[str, bool]:
    if (
        type(value) is not dict
        or set(value) != set(PRODUCTION_AUTHORITY)
        or any(type(flag) is not bool or flag is not False for flag in value.values())
    ):
        raise TesterReadinessError(f"{label} production authority drift")
    return dict(PRODUCTION_AUTHORITY)


def _verify_digest(value: dict[str, object], field: str, label: str) -> None:
    supplied = value.get(field)
    if type(supplied) is not str or HEX64_RE.fullmatch(supplied) is None:
        raise TesterReadinessError(f"{label} digest is malformed")
    unsigned = dict(value)
    unsigned.pop(field)
    if digest(unsigned) != supplied:
        raise TesterReadinessError(f"{label} digest mismatch")


def feedback_rubric() -> dict[str, object]:
    rubric: dict[str, object] = {
        "schemaVersion": FEEDBACK_SCHEMA,
        "rubricStatus": "template_only_no_human_response",
        "categories": [dict(item) for item in FEEDBACK_CATEGORIES],
        "ratingScale": {
            "1": "strongly_disagree_or_blocked",
            "2": "disagree_or_major_confusion",
            "3": "mixed_or_recoverable_confusion",
            "4": "agree_or_minor_friction",
            "5": "strongly_agree_or_clear",
        },
        "blockerClasses": list(BLOCKER_CLASSES),
        "severeIssueClasses": ["security", "privacy", "uncontained_execution", "unreplayable_result", "unbounded_cost", "accessibility_blocker", "truth_overclaim", "none"],
        "freeTextPolicy": "redacted_bounded_private_artifact_not_in_public_receipt",
        "identityFieldsAllowed": [],
        "humanFeedbackCollected": False,
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    rubric["rubricDigest"] = digest(rubric)
    return rubric


def tester_ceremony_contract() -> dict[str, object]:
    contract: dict[str, object] = {
        "schemaVersion": CONTRACT_SCHEMA,
        "contractStatus": "local_rehearsal_template_protected_ceremony_held",
        "journeySteps": [dict(item) for item in JOURNEY_STEPS],
        "feedbackRubricDigest": feedback_rubric()["rubricDigest"],
        "cleanupResources": [dict(item) for item in CLEANUP_RESOURCES],
        "prohibitedShortcuts": list(PROHIBITED_SHORTCUTS),
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    contract["contractDigest"] = digest(contract)
    return contract


def build_synthetic_rehearsal(
    *, observed_at: str, source_commit: str, source_tree: str,
    observations: Iterable[Mapping[str, object]],
) -> dict[str, object]:
    _timestamp(observed_at, "observedAt")
    _match(source_commit, HEX40_RE, "sourceCommit")
    _match(source_tree, HEX40_RE, "sourceTree")
    rows = list(observations)
    if len(rows) != len(JOURNEY_STEPS):
        raise TesterReadinessError("synthetic rehearsal must cover every journey step exactly once")
    normalized: list[dict[str, object]] = []
    local_passes = 0
    for expected, candidate in zip(JOURNEY_STEPS, rows, strict=True):
        row = _exact(
            candidate,
            {"stepId", "localStatus", "evidenceDigest", "humanObserved", "protectedCompletionStatus"},
            "rehearsal observation",
        )
        if row["stepId"] != expected["stepId"]:
            raise TesterReadinessError("synthetic rehearsal step order or identity drift")
        required = expected["localRehearsal"] == "required"
        expected_status = "LOCAL_PASS" if required else "NOT_APPLICABLE_PROTECTED"
        if row["localStatus"] != expected_status:
            raise TesterReadinessError("synthetic rehearsal local status drift")
        if required:
            _match(row["evidenceDigest"], HEX64_RE, "rehearsal evidenceDigest")
            local_passes += 1
        elif row["evidenceDigest"] is not None:
            raise TesterReadinessError("protected-only step cannot carry synthetic completion evidence")
        if row["humanObserved"] is not False or row["protectedCompletionStatus"] != "HELD_PROTECTED":
            raise TesterReadinessError("synthetic rehearsal cannot attest human or protected completion")
        normalized.append(dict(row))
    rehearsal: dict[str, object] = {
        "schemaVersion": REHEARSAL_SCHEMA,
        "observedAt": observed_at,
        "sourceCommit": source_commit,
        "sourceTree": source_tree,
        "rehearsalClass": "synthetic_local_only",
        "observations": normalized,
        "localRequiredCount": sum(item["localRehearsal"] == "required" for item in JOURNEY_STEPS),
        "localPassCount": local_passes,
        "protectedHeldCount": len(JOURNEY_STEPS),
        "humanTesterCompleted": False,
        "productionJourneyCompleted": False,
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    rehearsal["rehearsalDigest"] = digest(rehearsal)
    return rehearsal


def _validate_rehearsal(value: object) -> dict[str, object]:
    row = _exact(
        value,
        {
            "schemaVersion", "observedAt", "sourceCommit", "sourceTree", "rehearsalClass",
            "observations", "localRequiredCount", "localPassCount", "protectedHeldCount",
            "humanTesterCompleted", "productionJourneyCompleted", "productionAuthority", "rehearsalDigest",
        },
        "synthetic rehearsal",
    )
    if row["schemaVersion"] != REHEARSAL_SCHEMA or row["rehearsalClass"] != "synthetic_local_only":
        raise TesterReadinessError("synthetic rehearsal schema or class drift")
    if row["humanTesterCompleted"] is not False or row["productionJourneyCompleted"] is not False:
        raise TesterReadinessError("synthetic rehearsal cannot claim a real journey")
    _authority(row["productionAuthority"], "synthetic rehearsal")
    observations = row["observations"] if type(row["observations"]) is list else []
    rebuilt = build_synthetic_rehearsal(
        observed_at=str(row["observedAt"]),
        source_commit=str(row["sourceCommit"]),
        source_tree=str(row["sourceTree"]),
        observations=observations,
    )
    if rebuilt != row:
        raise TesterReadinessError("synthetic rehearsal does not match canonical reconstruction")
    return row


def build_feedback_placeholder(*, rehearsal: object) -> dict[str, object]:
    source = _validate_rehearsal(rehearsal)
    placeholder: dict[str, object] = {
        "schemaVersion": FEEDBACK_PLACEHOLDER_SCHEMA,
        "rehearsalDigest": source["rehearsalDigest"],
        "rubricDigest": feedback_rubric()["rubricDigest"],
        "feedbackStatus": "NOT_COLLECTED_SYNTHETIC_REHEARSAL",
        "ratings": [],
        "blockerClasses": [],
        "severeIssueClasses": [],
        "redactedNotes": None,
        "humanFeedbackCollected": False,
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    placeholder["feedbackDigest"] = digest(placeholder)
    return placeholder


def _validate_feedback_placeholder(value: object) -> dict[str, object]:
    row = _exact(
        value,
        {
            "schemaVersion", "rehearsalDigest", "rubricDigest", "feedbackStatus", "ratings",
            "blockerClasses", "severeIssueClasses", "redactedNotes", "humanFeedbackCollected",
            "productionAuthority", "feedbackDigest",
        },
        "feedback placeholder",
    )
    if row["schemaVersion"] != FEEDBACK_PLACEHOLDER_SCHEMA or row["feedbackStatus"] != "NOT_COLLECTED_SYNTHETIC_REHEARSAL":
        raise TesterReadinessError("feedback placeholder status drift")
    if row["rubricDigest"] != feedback_rubric()["rubricDigest"]:
        raise TesterReadinessError("feedback placeholder rubric drift")
    if row["ratings"] != [] or row["blockerClasses"] != [] or row["severeIssueClasses"] != [] or row["redactedNotes"] is not None:
        raise TesterReadinessError("synthetic rehearsal cannot fabricate feedback")
    if row["humanFeedbackCollected"] is not False:
        raise TesterReadinessError("feedback placeholder cannot claim a human response")
    _match(row["rehearsalDigest"], HEX64_RE, "feedback rehearsalDigest")
    _authority(row["productionAuthority"], "feedback placeholder")
    _verify_digest(row, "feedbackDigest", "feedback placeholder")
    return row


def build_cleanup_rehearsal(
    *, rehearsal: object, observations: Iterable[Mapping[str, object]],
) -> dict[str, object]:
    source = _validate_rehearsal(rehearsal)
    rows = list(observations)
    if len(rows) != len(CLEANUP_RESOURCES):
        raise TesterReadinessError("cleanup rehearsal must cover every resource class")
    normalized: list[dict[str, object]] = []
    local_passes = 0
    for expected, candidate in zip(CLEANUP_RESOURCES, rows, strict=True):
        row = _exact(
            candidate,
            {"resourceClass", "localStatus", "evidenceDigest", "protectedCompletionStatus"},
            "cleanup observation",
        )
        if row["resourceClass"] != expected["resourceClass"]:
            raise TesterReadinessError("cleanup resource order or identity drift")
        required = expected["localRehearsal"] == "required"
        expected_status = "LOCAL_CLEANUP_SIMULATED" if required else "NOT_APPLICABLE_PROTECTED"
        if row["localStatus"] != expected_status:
            raise TesterReadinessError("cleanup local status drift")
        if required:
            _match(row["evidenceDigest"], HEX64_RE, "cleanup evidenceDigest")
            local_passes += 1
        elif row["evidenceDigest"] is not None:
            raise TesterReadinessError("protected cleanup cannot carry synthetic completion evidence")
        if row["protectedCompletionStatus"] != "HELD_PROTECTED":
            raise TesterReadinessError("cleanup rehearsal cannot claim protected completion")
        normalized.append(dict(row))
    cleanup: dict[str, object] = {
        "schemaVersion": CLEANUP_SCHEMA,
        "rehearsalDigest": source["rehearsalDigest"],
        "observations": normalized,
        "localRequiredCount": sum(item["localRehearsal"] == "required" for item in CLEANUP_RESOURCES),
        "localPassCount": local_passes,
        "protectedHeldCount": len(CLEANUP_RESOURCES),
        "productionCleanupCompleted": False,
        "accountDeletionCompleted": False,
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    cleanup["cleanupDigest"] = digest(cleanup)
    return cleanup


def _validate_cleanup(value: object) -> dict[str, object]:
    row = _exact(
        value,
        {
            "schemaVersion", "rehearsalDigest", "observations", "localRequiredCount", "localPassCount",
            "protectedHeldCount", "productionCleanupCompleted", "accountDeletionCompleted",
            "productionAuthority", "cleanupDigest",
        },
        "cleanup rehearsal",
    )
    if row["schemaVersion"] != CLEANUP_SCHEMA:
        raise TesterReadinessError("cleanup rehearsal schema drift")
    if row["productionCleanupCompleted"] is not False or row["accountDeletionCompleted"] is not False:
        raise TesterReadinessError("cleanup rehearsal cannot claim production cleanup")
    _authority(row["productionAuthority"], "cleanup rehearsal")
    _verify_digest(row, "cleanupDigest", "cleanup rehearsal")
    return row


def evaluate_tester_readiness(*, rehearsal: object, feedback: object, cleanup: object) -> dict[str, object]:
    source = _validate_rehearsal(rehearsal)
    feedback_row = _validate_feedback_placeholder(feedback)
    cleanup_row = _validate_cleanup(cleanup)
    if feedback_row["rehearsalDigest"] != source["rehearsalDigest"] or cleanup_row["rehearsalDigest"] != source["rehearsalDigest"]:
        raise TesterReadinessError("tester readiness inputs bind different rehearsals")
    expected_cleanup = build_cleanup_rehearsal(
        rehearsal=source,
        observations=cleanup_row["observations"] if type(cleanup_row["observations"]) is list else [],
    )
    if expected_cleanup != cleanup_row:
        raise TesterReadinessError("cleanup rehearsal does not match canonical reconstruction")
    decision: dict[str, object] = {
        "schemaVersion": READINESS_SCHEMA,
        "sourceCommit": source["sourceCommit"],
        "sourceTree": source["sourceTree"],
        "rehearsalDigest": source["rehearsalDigest"],
        "feedbackDigest": feedback_row["feedbackDigest"],
        "cleanupDigest": cleanup_row["cleanupDigest"],
        "status": "LOCAL_REHEARSAL_PASS_PROTECTED_HELD",
        "localRehearsalPassed": True,
        "humanFeedbackCollected": False,
        "consentedHumanJourneyCompleted": False,
        "readyForOperatorCeremony": False,
        "operatorPacketStatus": "NOT_ACTIONABLE_STAGE_11_12_HELD",
        "heldJourneyStepIds": [str(item["stepId"]) for item in JOURNEY_STEPS],
        "heldCleanupResourceClasses": [str(item["resourceClass"]) for item in CLEANUP_RESOURCES],
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    decision["decisionDigest"] = digest(decision)
    return decision


def _validate_readiness(value: object) -> dict[str, object]:
    row = _exact(
        value,
        {
            "schemaVersion", "sourceCommit", "sourceTree", "rehearsalDigest", "feedbackDigest",
            "cleanupDigest", "status", "localRehearsalPassed", "humanFeedbackCollected",
            "consentedHumanJourneyCompleted", "readyForOperatorCeremony", "operatorPacketStatus",
            "heldJourneyStepIds", "heldCleanupResourceClasses", "productionAuthority", "decisionDigest",
        },
        "tester readiness decision",
    )
    if row["schemaVersion"] != READINESS_SCHEMA or row["status"] != "LOCAL_REHEARSAL_PASS_PROTECTED_HELD":
        raise TesterReadinessError("tester readiness decision status drift")
    if row["localRehearsalPassed"] is not True:
        raise TesterReadinessError("tester readiness decision lost local pass")
    for field in ("humanFeedbackCollected", "consentedHumanJourneyCompleted", "readyForOperatorCeremony"):
        if row[field] is not False:
            raise TesterReadinessError("tester readiness decision cannot claim protected readiness")
    if row["operatorPacketStatus"] != "NOT_ACTIONABLE_STAGE_11_12_HELD":
        raise TesterReadinessError("tester readiness operator status drift")
    if row["heldJourneyStepIds"] != [item["stepId"] for item in JOURNEY_STEPS]:
        raise TesterReadinessError("tester readiness held journey set drift")
    if row["heldCleanupResourceClasses"] != [item["resourceClass"] for item in CLEANUP_RESOURCES]:
        raise TesterReadinessError("tester readiness held cleanup set drift")
    for field, pattern in (("sourceCommit", HEX40_RE), ("sourceTree", HEX40_RE), ("rehearsalDigest", HEX64_RE),
                           ("feedbackDigest", HEX64_RE), ("cleanupDigest", HEX64_RE)):
        _match(row[field], pattern, field)
    _authority(row["productionAuthority"], "tester readiness decision")
    _verify_digest(row, "decisionDigest", "tester readiness decision")
    return row


def build_operator_packet(*, packet_id: str, observed_at: str, readiness: object) -> dict[str, object]:
    _match(packet_id, PACKET_ID_RE, "packetId")
    _timestamp(observed_at, "observedAt")
    decision = _validate_readiness(readiness)
    packet: dict[str, object] = {
        "schemaVersion": OPERATOR_PACKET_SCHEMA,
        "packetId": packet_id,
        "observedAt": observed_at,
        "sourceCommit": decision["sourceCommit"],
        "sourceTree": decision["sourceTree"],
        "readinessDecisionDigest": decision["decisionDigest"],
        "status": "NOT_ACTIONABLE_PROTECTED_GATES_HELD",
        "prerequisites": {
            "stage11ProtectedRuntimeVerified": False,
            "stage12SourceBoundDeploymentVerified": False,
            "rollbackTargetExternallyVerified": False,
            "testerConsentProtocolApproved": False,
            "supportAndIncidentCoverageConfirmed": False,
        },
        "smallestHumanAction": "After every prerequisite is independently true for this exact source and target, authorize one fresh consented tester ceremony; do not provide secrets in this packet.",
        "journeyStepIds": [str(item["stepId"]) for item in JOURNEY_STEPS],
        "feedbackRubricDigest": feedback_rubric()["rubricDigest"],
        "cleanupResourceClasses": [str(item["resourceClass"]) for item in CLEANUP_RESOURCES],
        "prohibitedShortcuts": list(PROHIBITED_SHORTCUTS),
        "operatorActionExecuted": False,
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    packet["packetDigest"] = digest(packet)
    return packet


def _validate_operator_packet(value: object) -> dict[str, object]:
    row = _exact(
        value,
        {
            "schemaVersion", "packetId", "observedAt", "sourceCommit", "sourceTree",
            "readinessDecisionDigest", "status", "prerequisites", "smallestHumanAction",
            "journeyStepIds", "feedbackRubricDigest", "cleanupResourceClasses",
            "prohibitedShortcuts", "operatorActionExecuted", "productionAuthority", "packetDigest",
        },
        "operator packet",
    )
    if row["schemaVersion"] != OPERATOR_PACKET_SCHEMA or row["status"] != "NOT_ACTIONABLE_PROTECTED_GATES_HELD":
        raise TesterReadinessError("operator packet status drift")
    _match(row["packetId"], PACKET_ID_RE, "packetId")
    _timestamp(row["observedAt"], "observedAt")
    prerequisites = _exact(
        row["prerequisites"],
        {
            "stage11ProtectedRuntimeVerified", "stage12SourceBoundDeploymentVerified",
            "rollbackTargetExternallyVerified", "testerConsentProtocolApproved",
            "supportAndIncidentCoverageConfirmed",
        },
        "operator packet prerequisites",
    )
    if any(type(value) is not bool or value is not False for value in prerequisites.values()):
        raise TesterReadinessError("operator packet cannot infer a satisfied prerequisite")
    if row["operatorActionExecuted"] is not False:
        raise TesterReadinessError("operator packet cannot claim action")
    if row["journeyStepIds"] != [item["stepId"] for item in JOURNEY_STEPS]:
        raise TesterReadinessError("operator packet journey drift")
    if row["cleanupResourceClasses"] != [item["resourceClass"] for item in CLEANUP_RESOURCES]:
        raise TesterReadinessError("operator packet cleanup drift")
    if row["prohibitedShortcuts"] != list(PROHIBITED_SHORTCUTS):
        raise TesterReadinessError("operator packet shortcut boundary drift")
    if row["feedbackRubricDigest"] != feedback_rubric()["rubricDigest"]:
        raise TesterReadinessError("operator packet feedback rubric drift")
    for field, pattern in (("sourceCommit", HEX40_RE), ("sourceTree", HEX40_RE), ("readinessDecisionDigest", HEX64_RE)):
        _match(row[field], pattern, field)
    _authority(row["productionAuthority"], "operator packet")
    _verify_digest(row, "packetDigest", "operator packet")
    return row


def verify_operator_packet(value: object, *, readiness: object) -> dict[str, object]:
    packet = _validate_operator_packet(value)
    decision = _validate_readiness(readiness)
    expected = build_operator_packet(
        packet_id=str(packet["packetId"]),
        observed_at=str(packet["observedAt"]),
        readiness=decision,
    )
    if expected != packet:
        raise TesterReadinessError("operator packet does not match the readiness decision")
    return packet
