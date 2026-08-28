"""Offline, append-only lifecycle contracts for private BuildWars candidates.

The hash chain in this module proves deterministic consistency, not identity,
authenticity, timestamp provenance, storage erasure, or public authority.  A
holder can rewrite an unanchored log and recompute every hash.  Candidate score
events therefore require the full challenge, entry, judgment, and receipt
documents to be revalidated through :mod:`buildwars.contracts`; digest-only
score sealing is intentionally unsupported.

This module performs no I/O, execution, authentication, signing, persistence,
publication, provider access, or deletion.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from typing import Any

from . import contracts as core


EVENT_SCHEMA = "buildwars.lifecycle.event.v1"
PROJECTION_SCHEMA = "buildwars.lifecycle.projection.v1"
GENESIS_SCHEMA = "buildwars.lifecycle.genesis.v1"
MAX_EVENTS = 64
MAX_APPEALS = 2
MAX_RELATIONSHIPS = 32

_LIFECYCLE_RE = re.compile(r"^bwl1_[0-9a-f]{24}$")
_TENANT_RE = re.compile(r"^ten1_[0-9a-f]{24}$")
_ACTOR_RE = re.compile(r"^act1_[0-9a-f]{24}$")
_IDEMPOTENCY_RE = re.compile(r"^bwi1_[0-9a-f]{24}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_ENTRY_RE = re.compile(r"^bwe1_[0-9a-f]{24}$")
_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:-[a-z0-9][a-z0-9.-]{0,31})?$")
_RELATIONSHIP_RE = re.compile(r"^[a-z_]+$")

_EVENT_KEYS = frozenset(
    {
        "schema",
        "lifecycleId",
        "tenantId",
        "actorId",
        "actorRole",
        "sequence",
        "timestamp",
        "eventType",
        "idempotencyKey",
        "digestBindings",
        "payload",
        "priorEventHash",
        "eventHash",
    }
)
_BINDING_KEYS = frozenset(
    {"challengeDigest", "rubricDigest", "entryDigests", "judgmentDigests", "receiptId"}
)
_CORE_PIN_KEYS = frozenset({"challenge", "entry", "judgment", "receipt", "projection"})
_COI_KEYS = frozenset({"declaredRelationships", "coiStatus"})
_RECEIPT_SUMMARY_KEYS = frozenset({"receiptId", "candidateWinnerEntryIds", "tie"})
_SCORE_EVIDENCE_KEYS = frozenset({"challenge", "entries", "judgments", "receipt"})

ACTOR_ROLES = frozenset({"creator", "reviewer", "appeal_author", "appeal_resolver", "steward"})
EVENT_TYPES = frozenset(
    {
        "creator_draft_opened",
        "creator_draft_amended",
        "review_submitted",
        "review_decision_recorded",
        "candidate_scored",
        "appeal_opened",
        "appeal_resolved",
        "receipt_superseded",
        "candidate_revoked",
        "lifecycle_retired",
        "privacy_tombstoned",
    }
)
RELATIONSHIPS = frozenset(
    {
        "none_declared",
        "same_organization",
        "prior_collaboration",
        "financial_interest",
        "personal_relationship",
    }
)

_ROLE_BY_EVENT = {
    "creator_draft_opened": "creator",
    "creator_draft_amended": "creator",
    "review_submitted": "creator",
    "review_decision_recorded": "reviewer",
    "candidate_scored": "reviewer",
    "appeal_opened": "appeal_author",
    "appeal_resolved": "appeal_resolver",
    "receipt_superseded": "steward",
    "candidate_revoked": "steward",
    "lifecycle_retired": "steward",
    "privacy_tombstoned": "steward",
}

TRUTH = (
    "Offline append-only integrity projection; tenant, actor, role, conflict, and timestamp values "
    "are caller-asserted and unattested; no public authority is created."
)
TOMBSTONE_TRUTH = (
    "Logical suppression recorded in an append-only log; no storage erasure was performed or "
    "claimed; underlying events remain present and hash-verifiable."
)
UNATTESTED_FIELDS = (
    "actorId",
    "actorRole",
    "payload.coi.coiStatus",
    "payload.coi.declaredRelationships",
    "payload.resolverRef",
    "payload.reviewerRef",
    "tenantId",
    "timestamp",
)

SCHEMA_MALFORMED = "SCHEMA_MALFORMED"
KEY_INVALID = "KEY_INVALID"
SIZE_OVERFLOW = "SIZE_OVERFLOW"
COUNT_OVERFLOW = "COUNT_OVERFLOW"
TIMESTAMP_INVALID = "TIMESTAMP_INVALID"
CHAIN_BROKEN = "CHAIN_BROKEN"
GENESIS_INVALID = "GENESIS_INVALID"
STALE_EVENT = "STALE_EVENT"
FORK_DETECTED = "FORK_DETECTED"
IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
TRANSITION_ILLEGAL = "TRANSITION_ILLEGAL"
TERMINAL_LOCKED = "TERMINAL_LOCKED"
BINDING_MISMATCH = "BINDING_MISMATCH"
RECOMPUTE_FAILED = "RECOMPUTE_FAILED"
CAPACITY_RESERVED = "CAPACITY_RESERVED"
ROLE_COLLISION = "ROLE_COLLISION"
ENUM_INVALID = "ENUM_INVALID"


class BuildWarsLifecycleError(ValueError):
    """A stable-code refusal from the offline lifecycle contract."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


def _refuse(code: str, message: str) -> None:
    raise BuildWarsLifecycleError(code, message)


def _exact(value: Any, keys: frozenset[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _refuse(SCHEMA_MALFORMED, f"{label} must be an object")
    unknown = set(value) - keys
    missing = keys - set(value)
    if unknown or missing:
        _refuse(
            KEY_INVALID,
            f"{label} exact keys required; missing_count={len(missing)}, unknown_count={len(unknown)}",
        )
    return value


def _bounded(value: Any, label: str) -> None:
    try:
        size = len(core.canonical_bytes(value))
    except (core.BuildWarsContractError, UnicodeError, ValueError, TypeError, RecursionError) as exc:
        _refuse(SCHEMA_MALFORMED, f"{label} is not canonically encodable: {exc}")
    if size > core.MAX_DOCUMENT_BYTES:
        _refuse(SIZE_OVERFLOW, f"{label} exceeds {core.MAX_DOCUMENT_BYTES} canonical bytes")


def _match(value: Any, pattern: re.Pattern[str], label: str) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        _refuse(SCHEMA_MALFORMED, f"{label} has an invalid identifier")
    return value


def _hex(value: Any, label: str) -> str:
    return _match(value, _HEX64_RE, label)


def _integer(value: Any, label: str, minimum: int, maximum: int, *, code: str = SCHEMA_MALFORMED) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        _refuse(code, f"{label} must be an integer in [{minimum}, {maximum}]")
    return value


def _text(value: Any, label: str, *, minimum: int = 0, maximum: int = 320) -> str:
    try:
        return core._text(value, label, minimum=minimum, maximum=maximum)
    except (core.BuildWarsContractError, UnicodeError, ValueError, TypeError) as exc:
        _refuse(SCHEMA_MALFORMED, str(exc))


def _sorted_unique(values: Any, label: str, pattern: re.Pattern[str], *, maximum: int) -> list[str]:
    if not isinstance(values, list) or len(values) > maximum:
        _refuse(COUNT_OVERFLOW, f"{label} must be a list with at most {maximum} values")
    normalized = [_match(value, pattern, f"{label}[{index}]") for index, value in enumerate(values)]
    if normalized != sorted(set(normalized)):
        _refuse(SCHEMA_MALFORMED, f"{label} must be sorted and unique")
    return normalized


def _core_pins(value: Any) -> dict[str, str]:
    row = _exact(value, _CORE_PIN_KEYS, "payload.coreSchemaPins")
    expected = {
        "challenge": core.CHALLENGE_SCHEMA,
        "entry": core.ENTRY_SCHEMA,
        "judgment": core.JUDGMENT_SCHEMA,
        "receipt": core.RECEIPT_SCHEMA,
        "projection": core.PROJECTION_SCHEMA,
    }
    if row != expected:
        _refuse(BINDING_MISMATCH, "core schema pins must match the accepted BuildWars contract exactly")
    return dict(row)


def _coi(value: Any, label: str) -> dict[str, Any]:
    row = _exact(value, _COI_KEYS, label)
    relationships = _sorted_unique(
        row["declaredRelationships"],
        f"{label}.declaredRelationships",
        _RELATIONSHIP_RE,
        maximum=MAX_RELATIONSHIPS,
    )
    if not relationships or any(item not in RELATIONSHIPS for item in relationships):
        _refuse(ENUM_INVALID, f"{label}.declaredRelationships contains an unsupported value")
    if "none_declared" in relationships and len(relationships) != 1:
        _refuse(ENUM_INVALID, "none_declared cannot be combined with a relationship")
    if row["coiStatus"] != "unattested_self_declared":
        _refuse(ENUM_INVALID, f"{label}.coiStatus must remain unattested_self_declared")
    return {"declaredRelationships": relationships, "coiStatus": "unattested_self_declared"}


def _bindings(value: Any) -> dict[str, Any]:
    row = _exact(value, _BINDING_KEYS, "event.digestBindings")
    receipt_id = row["receiptId"]
    if receipt_id is not None:
        receipt_id = _hex(receipt_id, "event.digestBindings.receiptId")
    return {
        "challengeDigest": _hex(row["challengeDigest"], "event.digestBindings.challengeDigest"),
        "rubricDigest": _hex(row["rubricDigest"], "event.digestBindings.rubricDigest"),
        "entryDigests": _sorted_unique(
            row["entryDigests"], "event.digestBindings.entryDigests", _HEX64_RE, maximum=core.MAX_ENTRIES
        ),
        "judgmentDigests": _sorted_unique(
            row["judgmentDigests"], "event.digestBindings.judgmentDigests", _HEX64_RE, maximum=core.MAX_ENTRIES
        ),
        "receiptId": receipt_id,
    }


def _receipt_summary(value: Any) -> dict[str, Any]:
    row = _exact(value, _RECEIPT_SUMMARY_KEYS, "payload.receiptSummary")
    winners = _sorted_unique(
        row["candidateWinnerEntryIds"],
        "payload.receiptSummary.candidateWinnerEntryIds",
        _ENTRY_RE,
        maximum=core.MAX_ENTRIES,
    )
    if not winners:
        _refuse(COUNT_OVERFLOW, "payload.receiptSummary.candidateWinnerEntryIds cannot be empty")
    if not isinstance(row["tie"], bool) or row["tie"] is not (len(winners) > 1):
        _refuse(SCHEMA_MALFORMED, "payload.receiptSummary.tie must follow from candidate winners")
    return {
        "receiptId": _hex(row["receiptId"], "payload.receiptSummary.receiptId"),
        "candidateWinnerEntryIds": winners,
        "tie": row["tie"],
    }


def _payload(event_type: str, value: Any) -> dict[str, Any]:
    label = f"payload[{event_type}]"
    if event_type == "creator_draft_opened":
        row = _exact(value, frozenset({"draftTitle", "draftNote", "coreSchemaPins"}), label)
        return {
            "draftTitle": _text(row["draftTitle"], f"{label}.draftTitle", minimum=1, maximum=160),
            "draftNote": _text(row["draftNote"], f"{label}.draftNote"),
            "coreSchemaPins": _core_pins(row["coreSchemaPins"]),
        }
    if event_type == "creator_draft_amended":
        row = _exact(value, frozenset({"draftTitle", "draftNote", "entryDigests"}), label)
        return {
            "draftTitle": _text(row["draftTitle"], f"{label}.draftTitle", minimum=1, maximum=160),
            "draftNote": _text(row["draftNote"], f"{label}.draftNote"),
            "entryDigests": _sorted_unique(
                row["entryDigests"], f"{label}.entryDigests", _HEX64_RE, maximum=core.MAX_ENTRIES
            ),
        }
    if event_type == "review_submitted":
        row = _exact(value, frozenset({"submissionSummary"}), label)
        return {"submissionSummary": _text(row["submissionSummary"], f"{label}.submissionSummary")}
    if event_type == "review_decision_recorded":
        row = _exact(
            value,
            frozenset({"decision", "decisionSummary", "reviewerRef", "reviewerVersion", "coi"}),
            label,
        )
        if row["decision"] not in {"accepted_for_scoring", "rejected_at_review"}:
            _refuse(ENUM_INVALID, f"{label}.decision is unsupported")
        return {
            "decision": row["decision"],
            "decisionSummary": _text(row["decisionSummary"], f"{label}.decisionSummary"),
            "reviewerRef": _match(row["reviewerRef"], _ACTOR_RE, f"{label}.reviewerRef"),
            "reviewerVersion": _match(row["reviewerVersion"], _VERSION_RE, f"{label}.reviewerVersion"),
            "coi": _coi(row["coi"], f"{label}.coi"),
        }
    if event_type == "candidate_scored":
        row = _exact(value, frozenset({"receiptSummary"}), label)
        return {"receiptSummary": _receipt_summary(row["receiptSummary"])}
    if event_type == "appeal_opened":
        row = _exact(value, frozenset({"appealGrounds", "appealedJudgmentDigests"}), label)
        return {
            "appealGrounds": _text(row["appealGrounds"], f"{label}.appealGrounds", minimum=1),
            "appealedJudgmentDigests": _sorted_unique(
                row["appealedJudgmentDigests"],
                f"{label}.appealedJudgmentDigests",
                _HEX64_RE,
                maximum=core.MAX_ENTRIES,
            ),
        }
    if event_type == "appeal_resolved":
        row = _exact(
            value,
            frozenset({"outcome", "resolutionSummary", "resolverRef", "resolverVersion", "coi"}),
            label,
        )
        if row["outcome"] not in {"dismissed", "upheld"}:
            _refuse(ENUM_INVALID, f"{label}.outcome is unsupported")
        return {
            "outcome": row["outcome"],
            "resolutionSummary": _text(row["resolutionSummary"], f"{label}.resolutionSummary"),
            "resolverRef": _match(row["resolverRef"], _ACTOR_RE, f"{label}.resolverRef"),
            "resolverVersion": _match(row["resolverVersion"], _VERSION_RE, f"{label}.resolverVersion"),
            "coi": _coi(row["coi"], f"{label}.coi"),
        }
    if event_type == "receipt_superseded":
        row = _exact(value, frozenset({"supersedingLifecycleId", "supersedingReceiptId", "supersedeSummary"}), label)
        return {
            "supersedingLifecycleId": _match(
                row["supersedingLifecycleId"], _LIFECYCLE_RE, f"{label}.supersedingLifecycleId"
            ),
            "supersedingReceiptId": _hex(row["supersedingReceiptId"], f"{label}.supersedingReceiptId"),
            "supersedeSummary": _text(row["supersedeSummary"], f"{label}.supersedeSummary"),
        }
    if event_type == "candidate_revoked":
        row = _exact(value, frozenset({"revocationReason", "revocationSummary"}), label)
        allowed = {
            "creator_withdrawal",
            "appeal_upheld",
            "reviewer_referral",
            "integrity_concern",
            "steward_action",
        }
        if row["revocationReason"] not in allowed:
            _refuse(ENUM_INVALID, f"{label}.revocationReason is unsupported")
        return {
            "revocationReason": row["revocationReason"],
            "revocationSummary": _text(row["revocationSummary"], f"{label}.revocationSummary"),
        }
    if event_type == "lifecycle_retired":
        row = _exact(value, frozenset({"retentionClass", "retirementSummary"}), label)
        if row["retentionClass"] not in {
            "retain_full_history_indefinitely",
            "retain_full_history_until_policy_change",
        }:
            _refuse(ENUM_INVALID, f"{label}.retentionClass is unsupported")
        return {
            "retentionClass": row["retentionClass"],
            "retirementSummary": _text(row["retirementSummary"], f"{label}.retirementSummary"),
        }
    if event_type == "privacy_tombstoned":
        row = _exact(
            value,
            frozenset({"suppressionScope", "tombstoneReasonClass", "suppressedProjectionDigest"}),
            label,
        )
        if row["suppressionScope"] not in {
            "whole_projection",
            "score_rows",
            "participant_refs",
            "judgment_summaries",
        }:
            _refuse(ENUM_INVALID, f"{label}.suppressionScope is unsupported")
        if row["tombstoneReasonClass"] not in {
            "participant_privacy_request",
            "data_minimization_policy",
            "erroneous_disclosure_risk",
        }:
            _refuse(ENUM_INVALID, f"{label}.tombstoneReasonClass is unsupported")
        return {
            "suppressionScope": row["suppressionScope"],
            "tombstoneReasonClass": row["tombstoneReasonClass"],
            "suppressedProjectionDigest": _hex(
                row["suppressedProjectionDigest"], f"{label}.suppressedProjectionDigest"
            ),
        }
    _refuse(ENUM_INVALID, "eventType is unsupported")


def lifecycle_genesis_hash(
    lifecycle_id: str,
    tenant_id: str,
    challenge_digest: str,
    rubric_digest: str,
) -> str:
    return core.digest(
        {
            "schema": GENESIS_SCHEMA,
            "lifecycleId": _match(lifecycle_id, _LIFECYCLE_RE, "lifecycleId"),
            "tenantId": _match(tenant_id, _TENANT_RE, "tenantId"),
            "challengeDigest": _hex(challenge_digest, "challengeDigest"),
            "rubricDigest": _hex(rubric_digest, "rubricDigest"),
        }
    )


def _event(value: Any) -> dict[str, Any]:
    _bounded(value, "lifecycle event")
    row = _exact(value, _EVENT_KEYS, "lifecycle event")
    event_type = row["eventType"]
    if event_type not in EVENT_TYPES:
        _refuse(ENUM_INVALID, "eventType is unsupported")
    actor_role = row["actorRole"]
    if actor_role not in ACTOR_ROLES or actor_role != _ROLE_BY_EVENT[event_type]:
        _refuse(ENUM_INVALID, "actorRole is not admitted for eventType")
    normalized = {
        "schema": row["schema"],
        "lifecycleId": _match(row["lifecycleId"], _LIFECYCLE_RE, "event.lifecycleId"),
        "tenantId": _match(row["tenantId"], _TENANT_RE, "event.tenantId"),
        "actorId": _match(row["actorId"], _ACTOR_RE, "event.actorId"),
        "actorRole": actor_role,
        "sequence": _integer(row["sequence"], "event.sequence", 0, MAX_EVENTS - 1),
        "timestamp": _integer(
            row["timestamp"], "event.timestamp", 0, 4_102_444_800, code=TIMESTAMP_INVALID
        ),
        "eventType": event_type,
        "idempotencyKey": _match(row["idempotencyKey"], _IDEMPOTENCY_RE, "event.idempotencyKey"),
        "digestBindings": _bindings(row["digestBindings"]),
        "payload": _payload(event_type, row["payload"]),
        "priorEventHash": _hex(row["priorEventHash"], "event.priorEventHash"),
        "eventHash": _hex(row["eventHash"], "event.eventHash"),
    }
    if normalized["schema"] != EVENT_SCHEMA:
        _refuse(SCHEMA_MALFORMED, f"event.schema must be {EVENT_SCHEMA}")
    expected_hash = core.digest({key: item for key, item in normalized.items() if key != "eventHash"})
    if normalized["eventHash"] != expected_hash:
        _refuse(CHAIN_BROKEN, "eventHash does not bind the canonical event body")
    return normalized


def _same_binding(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return core.canonical_bytes(left) == core.canonical_bytes(right)


def _score_evidence(value: Any, event: dict[str, Any]) -> tuple[dict[str, Any], int, int]:
    row = _exact(value, _SCORE_EVIDENCE_KEYS, "score evidence")
    if not isinstance(row["entries"], list) or not isinstance(row["judgments"], list):
        _refuse(RECOMPUTE_FAILED, "score evidence entries and judgments must be lists")
    expected_entries = len(event["digestBindings"]["entryDigests"])
    expected_judgments = len(event["digestBindings"]["judgmentDigests"])
    if (
        len(row["entries"]) != expected_entries
        or len(row["entries"]) > core.MAX_ENTRIES
        or len(row["judgments"]) != expected_judgments
        or len(row["judgments"]) > core.MAX_ENTRIES
    ):
        _refuse(
            COUNT_OVERFLOW,
            "score evidence list counts must equal the bounded event bindings",
        )
    _bounded(row["challenge"], "score evidence challenge")
    _bounded(row["receipt"], "score evidence receipt")
    for index, item in enumerate(row["entries"]):
        _bounded(item, f"score evidence entry[{index}]")
    for index, item in enumerate(row["judgments"]):
        _bounded(item, f"score evidence judgment[{index}]")
    try:
        challenge = core.validate_challenge(row["challenge"])
        entries = [core.validate_entry(item, challenge=challenge) for item in row["entries"]]
        entry_by_digest = {item["entryDigest"]: item for item in entries}
        judgments = []
        for item in row["judgments"]:
            if not isinstance(item, dict) or item.get("entryDigest") not in entry_by_digest:
                _refuse(BINDING_MISMATCH, "judgment does not name one supplied entry digest")
            judgments.append(
                core.validate_judgment(
                    item,
                    challenge=challenge,
                    entry=entry_by_digest[item["entryDigest"]],
                )
            )
        receipt = core.verify_receipt(
            row["receipt"], challenge=challenge, entries=entries, judgments=judgments
        )
    except BuildWarsLifecycleError:
        raise
    except (core.BuildWarsContractError, UnicodeError, ValueError, TypeError, KeyError, RecursionError):
        _refuse(RECOMPUTE_FAILED, "full score evidence failed BuildWars recomputation")

    expected_binding = {
        "challengeDigest": challenge["challengeDigest"],
        "rubricDigest": challenge["rubric"]["rubricDigest"],
        "entryDigests": sorted(item["entryDigest"] for item in entries),
        "judgmentDigests": sorted(item["judgmentDigest"] for item in judgments),
        "receiptId": receipt["receiptId"],
    }
    if not _same_binding(event["digestBindings"], expected_binding):
        _refuse(BINDING_MISMATCH, "candidate score event does not bind the fully recomputed documents")
    summary = event["payload"]["receiptSummary"]
    expected_summary = {
        "receiptId": receipt["receiptId"],
        "candidateWinnerEntryIds": receipt["candidateWinnerEntryIds"],
        "tie": receipt["tie"],
    }
    if summary != expected_summary:
        _refuse(BINDING_MISMATCH, "candidate score summary does not match the recomputed receipt")
    if any(item["reviewerRef"] != event["actorId"] for item in judgments):
        _refuse(BINDING_MISMATCH, "judgment reviewerRef must equal the event's unattested reviewer actorId")
    return receipt, len(entries), len(judgments)


def _new_use_eligible(state: dict[str, Any]) -> bool:
    if state["stage"] not in {"scored", "appeal_resolved"}:
        return False
    return state["lastAppealOutcome"] != "upheld"


def _projection(state: dict[str, Any], *, event_count: int, head_event_hash: str) -> dict[str, Any]:
    if state["stage"] == "tombstoned":
        return {
            "schema": PROJECTION_SCHEMA,
            "lifecycleId": state["lifecycleId"],
            "stage": "tombstoned",
            "tombstone": copy.deepcopy(state["tombstone"]),
            "eventCount": event_count,
            "headEventHash": head_event_hash,
            "truth": TOMBSTONE_TRUTH,
        }
    eligible = _new_use_eligible(state)
    if eligible:
        use_status = "private_candidate_only"
    elif state["appealOpen"]:
        use_status = "appeal_pending"
    elif state["receiptId"] is not None:
        use_status = "historical_reference_only"
    else:
        use_status = "not_scored"
    return {
        "schema": PROJECTION_SCHEMA,
        "lifecycleId": state["lifecycleId"],
        "tenantId": state["tenantId"],
        "stage": state["stage"],
        "eventCount": event_count,
        "headEventHash": head_event_hash,
        "firstTimestamp": state["firstTimestamp"],
        "lastTimestamp": state["lastTimestamp"],
        "challengeDigest": state["binding"]["challengeDigest"],
        "rubricDigest": state["binding"]["rubricDigest"],
        "receiptId": state["receiptId"],
        "entryCount": state["entryCount"],
        "judgmentCount": state["judgmentCount"],
        "draftTitle": state["draftTitle"],
        "decision": state["decision"],
        "appealOpen": state["appealOpen"],
        "appealCount": state["appealCount"],
        "lastAppealOutcome": state["lastAppealOutcome"],
        "supersededBy": state["supersededBy"],
        "revocation": copy.deepcopy(state["revocation"]),
        "tombstone": None,
        "coreSchemaPins": copy.deepcopy(state["coreSchemaPins"]),
        "unattestedFields": list(UNATTESTED_FIELDS),
        "truth": TRUTH,
        "newUseEligible": eligible,
        "useStatus": use_status,
        "publicEligible": False,
        "shareEligible": False,
        "rankingEligible": False,
        "titleEligible": False,
        "agentWarsRatingEligible": False,
        "modelAttested": False,
        "providerAttested": False,
        "executionAttested": False,
        "reviewerIdentityAttested": False,
        "reviewerIndependenceAttested": False,
        "authenticationAttested": False,
        "storageErasurePerformed": False,
    }


def _transition_allowed(state: dict[str, Any], event_type: str) -> None:
    stage = state["stage"]
    if stage == "tombstoned":
        _refuse(TERMINAL_LOCKED, "a tombstoned lifecycle is absolute terminal")
    if event_type == "privacy_tombstoned":
        return
    if stage == "draft" and event_type in {"creator_draft_amended", "review_submitted"}:
        return
    if stage == "submitted" and event_type == "review_decision_recorded":
        return
    if stage == "decided":
        allowed = {"lifecycle_retired"}
        if state["decision"] == "accepted_for_scoring":
            allowed |= {"candidate_scored", "candidate_revoked"}
        if event_type in allowed:
            return
    if stage == "scored" and event_type in {
        "appeal_opened",
        "receipt_superseded",
        "candidate_revoked",
        "lifecycle_retired",
    }:
        return
    if stage == "appeal_open" and event_type == "appeal_resolved":
        return
    if stage == "appeal_resolved":
        allowed = {"candidate_revoked", "lifecycle_retired"}
        if state["lastAppealOutcome"] == "dismissed":
            allowed |= {"appeal_opened", "receipt_superseded"}
        if event_type in allowed:
            return
    if stage in {"superseded", "revoked"} and event_type == "lifecycle_retired":
        return
    if stage == "retired":
        _refuse(TERMINAL_LOCKED, "a retired lifecycle admits only a privacy tombstone")
    _refuse(TRANSITION_ILLEGAL, f"event {event_type!r} is illegal from stage {stage!r}")


def _capacity(index: int, event_type: str) -> None:
    remaining_after = MAX_EVENTS - (index + 1)
    if event_type == "privacy_tombstoned":
        return
    if event_type == "lifecycle_retired":
        if remaining_after < 1:
            _refuse(CAPACITY_RESERVED, "one event slot is reserved for a privacy tombstone")
        return
    if remaining_after < 2:
        _refuse(CAPACITY_RESERVED, "two event slots are reserved for retirement and privacy tombstone")


def replay_lifecycle(
    events: Sequence[dict[str, Any]],
    *,
    score_evidence_by_event_hash: Mapping[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate and deterministically fold one complete lifecycle log."""

    if not isinstance(events, Sequence) or isinstance(events, (str, bytes, bytearray)):
        _refuse(SCHEMA_MALFORMED, "events must be a sequence")
    if not events:
        _refuse(COUNT_OVERFLOW, "a lifecycle requires one genesis event")
    if len(events) > MAX_EVENTS:
        _refuse(COUNT_OVERFLOW, f"a lifecycle cannot exceed {MAX_EVENTS} events")
    evidence = score_evidence_by_event_hash or {}
    state: dict[str, Any] | None = None
    prior: str | None = None
    seen_idempotency: dict[str, bytes] = {}
    seen_hashes: set[str] = set()

    for index, raw in enumerate(events):
        event = _event(raw)
        if event["sequence"] != index:
            _refuse(CHAIN_BROKEN, "event sequence must be consecutive from zero")
        _capacity(index, event["eventType"])
        event_bytes = core.canonical_bytes(event)
        if event["idempotencyKey"] in seen_idempotency:
            if seen_idempotency[event["idempotencyKey"]] == event_bytes:
                _refuse(CHAIN_BROKEN, "a byte-identical event cannot occupy two sequence slots")
            _refuse(IDEMPOTENCY_CONFLICT, "one idempotency key names different event bodies")
        seen_idempotency[event["idempotencyKey"]] = event_bytes
        if event["eventHash"] in seen_hashes:
            _refuse(CHAIN_BROKEN, "event hashes must be unique inside a lifecycle")
        seen_hashes.add(event["eventHash"])

        if index == 0:
            if event["eventType"] != "creator_draft_opened":
                _refuse(GENESIS_INVALID, "the first event must be creator_draft_opened")
            expected_prior = lifecycle_genesis_hash(
                event["lifecycleId"],
                event["tenantId"],
                event["digestBindings"]["challengeDigest"],
                event["digestBindings"]["rubricDigest"],
            )
            if event["priorEventHash"] != expected_prior:
                _refuse(GENESIS_INVALID, "the first event does not bind the lifecycle genesis")
            binding = event["digestBindings"]
            if binding["judgmentDigests"] or binding["receiptId"] is not None:
                _refuse(BINDING_MISMATCH, "a draft cannot begin with judgments or a receipt")
            state = {
                "lifecycleId": event["lifecycleId"],
                "tenantId": event["tenantId"],
                "stage": "draft",
                "firstTimestamp": event["timestamp"],
                "lastTimestamp": event["timestamp"],
                "binding": copy.deepcopy(binding),
                "frozenBinding": None,
                "receiptId": None,
                "entryCount": len(binding["entryDigests"]),
                "judgmentCount": 0,
                "draftTitle": event["payload"]["draftTitle"],
                "decision": None,
                "reviewerActor": None,
                "appealOpen": False,
                "appealCount": 0,
                "lastAppealOutcome": None,
                "lastAppealAuthor": None,
                "supersededBy": None,
                "revocation": None,
                "tombstone": None,
                "coreSchemaPins": event["payload"]["coreSchemaPins"],
                "creatorActor": event["actorId"],
            }
            prior = event["eventHash"]
            continue

        assert state is not None and prior is not None
        if event["lifecycleId"] != state["lifecycleId"] or event["tenantId"] != state["tenantId"]:
            _refuse(BINDING_MISMATCH, "event cannot cross lifecycle or tenant")
        if event["priorEventHash"] != prior:
            _refuse(CHAIN_BROKEN, "event priorEventHash does not match the previous event")
        if event["timestamp"] < state["lastTimestamp"]:
            _refuse(TIMESTAMP_INVALID, "caller-given timestamps must be non-decreasing")
        if event["actorRole"] == "creator" and event["actorId"] != state["creatorActor"]:
            _refuse(ROLE_COLLISION, "one lifecycle cannot silently change its creator actor")
        if event["actorRole"] == "steward" and event["actorId"] in {
            state["creatorActor"],
            state["reviewerActor"],
        }:
            _refuse(ROLE_COLLISION, "steward actor must differ from creator and reviewer actors")
        _transition_allowed(state, event["eventType"])

        current = state["binding"]
        incoming = event["digestBindings"]
        if incoming["challengeDigest"] != current["challengeDigest"] or incoming["rubricDigest"] != current["rubricDigest"]:
            _refuse(BINDING_MISMATCH, "challenge and rubric bindings are immutable")
        if event["eventType"] == "creator_draft_amended":
            if incoming["judgmentDigests"] or incoming["receiptId"] is not None:
                _refuse(BINDING_MISMATCH, "a draft amendment cannot introduce judgments or a receipt")
            if incoming["entryDigests"] != event["payload"]["entryDigests"]:
                _refuse(BINDING_MISMATCH, "draft amendment payload and event bindings disagree")
            state["binding"] = copy.deepcopy(incoming)
            state["entryCount"] = len(incoming["entryDigests"])
            state["draftTitle"] = event["payload"]["draftTitle"]
        elif event["eventType"] == "review_submitted":
            if not incoming["entryDigests"] or incoming["judgmentDigests"] or incoming["receiptId"] is not None:
                _refuse(BINDING_MISMATCH, "review submission freezes entries but cannot contain judgments or receipt")
            if not _same_binding(incoming, current):
                _refuse(BINDING_MISMATCH, "review submission must freeze the current draft bindings")
            state["frozenBinding"] = copy.deepcopy(incoming)
            state["stage"] = "submitted"
        elif event["eventType"] == "review_decision_recorded":
            if not _same_binding(incoming, state["frozenBinding"]):
                _refuse(BINDING_MISMATCH, "review decision must retain the submitted bindings")
            if event["actorId"] == state["creatorActor"]:
                _refuse(ROLE_COLLISION, "creator and reviewer actor IDs must differ structurally")
            if event["payload"]["reviewerRef"] != event["actorId"]:
                _refuse(BINDING_MISMATCH, "reviewerRef must equal the event reviewer actorId")
            state["decision"] = event["payload"]["decision"]
            state["reviewerActor"] = event["actorId"]
            state["stage"] = "decided"
        elif event["eventType"] == "candidate_scored":
            frozen = state["frozenBinding"]
            if incoming["entryDigests"] != frozen["entryDigests"]:
                _refuse(BINDING_MISMATCH, "candidate score cannot replace submitted entries")
            if not incoming["judgmentDigests"] or incoming["receiptId"] is None:
                _refuse(BINDING_MISMATCH, "candidate score requires judgments and a receipt")
            if event["actorId"] != state["reviewerActor"]:
                _refuse(ROLE_COLLISION, "candidate score actor must be the recorded reviewer actor")
            if event["eventHash"] not in evidence:
                _refuse(RECOMPUTE_FAILED, "candidate score requires full sidecar documents during replay")
            receipt, entry_count, judgment_count = _score_evidence(evidence[event["eventHash"]], event)
            state["binding"] = copy.deepcopy(incoming)
            state["receiptId"] = receipt["receiptId"]
            state["entryCount"] = entry_count
            state["judgmentCount"] = judgment_count
            state["stage"] = "scored"
        else:
            if not _same_binding(incoming, current):
                _refuse(BINDING_MISMATCH, "post-submission event cannot rewrite the active evidence bindings")
            if event["eventType"] == "appeal_opened":
                if state["appealCount"] >= MAX_APPEALS:
                    _refuse(COUNT_OVERFLOW, f"a lifecycle cannot exceed {MAX_APPEALS} appeal cycles")
                appealed = event["payload"]["appealedJudgmentDigests"]
                if not appealed or not set(appealed).issubset(current["judgmentDigests"]):
                    _refuse(BINDING_MISMATCH, "appeal judgment digests must be a non-empty subset of scored judgments")
                if event["actorId"] == state["reviewerActor"]:
                    _refuse(ROLE_COLLISION, "reviewer actor cannot also be the appeal author")
                state["appealCount"] += 1
                state["appealOpen"] = True
                state["lastAppealAuthor"] = event["actorId"]
                state["lastAppealOutcome"] = None
                state["stage"] = "appeal_open"
            elif event["eventType"] == "appeal_resolved":
                if event["actorId"] in {state["reviewerActor"], state["lastAppealAuthor"]}:
                    _refuse(ROLE_COLLISION, "appeal resolver must differ from reviewer and appeal author actors")
                if event["payload"]["resolverRef"] != event["actorId"]:
                    _refuse(BINDING_MISMATCH, "resolverRef must equal the event resolver actorId")
                state["appealOpen"] = False
                state["lastAppealOutcome"] = event["payload"]["outcome"]
                state["stage"] = "appeal_resolved"
            elif event["eventType"] == "receipt_superseded":
                target = event["payload"]["supersedingLifecycleId"]
                if target == state["lifecycleId"]:
                    _refuse(BINDING_MISMATCH, "a lifecycle cannot supersede itself")
                state["supersededBy"] = target
                state["stage"] = "superseded"
            elif event["eventType"] == "candidate_revoked":
                appeal_upheld = state["lastAppealOutcome"] == "upheld"
                reason_is_appeal_upheld = event["payload"]["revocationReason"] == "appeal_upheld"
                if appeal_upheld != reason_is_appeal_upheld:
                    _refuse(
                        BINDING_MISMATCH,
                        "appeal_upheld is valid exactly when the latest appeal outcome is upheld",
                    )
                state["revocation"] = copy.deepcopy(event["payload"])
                state["stage"] = "revoked"
            elif event["eventType"] == "lifecycle_retired":
                state["stage"] = "retired"
            elif event["eventType"] == "privacy_tombstoned":
                pre_projection = _projection(state, event_count=index, head_event_hash=prior)
                if event["payload"]["suppressedProjectionDigest"] != core.digest(pre_projection):
                    _refuse(BINDING_MISMATCH, "tombstone must bind the exact pre-suppression projection")
                state["tombstone"] = copy.deepcopy(event["payload"])
                state["stage"] = "tombstoned"

        state["lastTimestamp"] = event["timestamp"]
        prior = event["eventHash"]

    assert state is not None and prior is not None
    return _projection(state, event_count=len(events), head_event_hash=prior)


def make_lifecycle_event(
    events: Sequence[dict[str, Any]],
    *,
    lifecycle_id: str,
    tenant_id: str,
    actor_id: str,
    actor_role: str,
    timestamp: int,
    event_type: str,
    idempotency_key: str,
    digest_bindings: dict[str, Any],
    payload: dict[str, Any],
    score_evidence: dict[str, Any] | None = None,
    score_evidence_by_event_hash: Mapping[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create and preflight one event against the supplied current log."""

    if event_type not in EVENT_TYPES:
        _refuse(ENUM_INVALID, "eventType is unsupported")
    _bounded(digest_bindings, "event.digestBindings")
    _bounded(payload, f"payload[{event_type}]")
    normalized_bindings = _bindings(digest_bindings)
    normalized_payload = _payload(event_type, payload)
    if events:
        replay_lifecycle(events, score_evidence_by_event_hash=score_evidence_by_event_hash)
        prior = _event(events[-1])["eventHash"]
        sequence = len(events)
    else:
        prior = lifecycle_genesis_hash(
            lifecycle_id,
            tenant_id,
            normalized_bindings["challengeDigest"],
            normalized_bindings["rubricDigest"],
        )
        sequence = 0
    body = {
        "schema": EVENT_SCHEMA,
        "lifecycleId": lifecycle_id,
        "tenantId": tenant_id,
        "actorId": actor_id,
        "actorRole": actor_role,
        "sequence": sequence,
        "timestamp": timestamp,
        "eventType": event_type,
        "idempotencyKey": idempotency_key,
        "digestBindings": normalized_bindings,
        "payload": normalized_payload,
        "priorEventHash": prior,
    }
    event = {**body, "eventHash": core.digest(body)}
    normalized = _event(event)
    evidence = dict(score_evidence_by_event_hash or {})
    if score_evidence is not None:
        evidence[normalized["eventHash"]] = score_evidence
    replay_lifecycle([*events, normalized], score_evidence_by_event_hash=evidence)
    return normalized


def append_lifecycle_event(
    events: Sequence[dict[str, Any]],
    event: dict[str, Any],
    *,
    score_evidence: dict[str, Any] | None = None,
    score_evidence_by_event_hash: Mapping[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Append one event, or return an unchanged log for an exact idempotent replay."""

    normalized = _event(event)
    evidence = dict(score_evidence_by_event_hash or {})
    if score_evidence is not None:
        evidence[normalized["eventHash"]] = score_evidence
    if events:
        replay_lifecycle(events, score_evidence_by_event_hash=evidence)
    for existing_raw in events:
        existing = _event(existing_raw)
        if existing["idempotencyKey"] != normalized["idempotencyKey"]:
            continue
        if core.canonical_bytes(existing) == core.canonical_bytes(normalized):
            return [copy.deepcopy(item) for item in events]
        _refuse(IDEMPOTENCY_CONFLICT, "one idempotency key names different event bodies")
    if events:
        head = _event(events[-1])
        if normalized["sequence"] != len(events) or normalized["priorEventHash"] != head["eventHash"]:
            _refuse(STALE_EVENT, "event was not built against the current lifecycle head")
    combined = [copy.deepcopy(item) for item in events] + [normalized]
    replay_lifecycle(combined, score_evidence_by_event_hash=evidence)
    return combined


def lifecycle_fingerprint(
    events: Sequence[dict[str, Any]],
    *,
    score_evidence_by_event_hash: Mapping[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    projection = replay_lifecycle(events, score_evidence_by_event_hash=score_evidence_by_event_hash)
    return {
        "lifecycleId": projection["lifecycleId"],
        "eventCount": projection["eventCount"],
        "headEventHash": projection["headEventHash"],
    }


def compare_lifecycle_logs(
    left: Sequence[dict[str, Any]],
    right: Sequence[dict[str, Any]],
    *,
    left_score_evidence: Mapping[str, dict[str, Any]] | None = None,
    right_score_evidence: Mapping[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Detect a divergent event at the same sequence slot across two valid copies."""

    left_fingerprint = lifecycle_fingerprint(left, score_evidence_by_event_hash=left_score_evidence)
    right_fingerprint = lifecycle_fingerprint(right, score_evidence_by_event_hash=right_score_evidence)
    if left_fingerprint["lifecycleId"] != right_fingerprint["lifecycleId"]:
        _refuse(BINDING_MISMATCH, "comparative logs name different lifecycle IDs")
    for index in range(min(len(left), len(right))):
        if _event(left[index])["eventHash"] != _event(right[index])["eventHash"]:
            _refuse(FORK_DETECTED, f"lifecycle copies diverge at sequence {index}")
    return {"left": left_fingerprint, "right": right_fingerprint, "forkDetected": False}


def assert_new_use_allowed(
    events: Sequence[dict[str, Any]],
    *,
    score_evidence_by_event_hash: Mapping[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    projection = replay_lifecycle(events, score_evidence_by_event_hash=score_evidence_by_event_hash)
    if not projection.get("newUseEligible", False):
        _refuse(TRANSITION_ILLEGAL, "lifecycle is not eligible for any new private use")
    return projection


def verify_suppression(
    events: Sequence[dict[str, Any]],
    *,
    score_evidence_by_event_hash: Mapping[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    projection = replay_lifecycle(events, score_evidence_by_event_hash=score_evidence_by_event_hash)
    if projection["stage"] != "tombstoned":
        _refuse(TRANSITION_ILLEGAL, "lifecycle has no suppression tombstone")
    return projection
