"""Append-only, source-bound corrections for reviewed public receipts.

Corrections never rewrite or delete a receipt.  They only project whether a
reviewed receipt remains eligible for current scoped proof-point snapshots.
The tracked ledger is identity-unattested and grants no moderation,
publication, ranking, production, or launch authority.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Iterable

from arena.canonical import digest


LEDGER_SCHEMA = "agentwars.public-correction-ledger.v1"
ENTRY_SCHEMA = "agentwars.public-receipt-correction.v1"
LEDGER_VERSION = "1"
ENTRY_VERSION = "1"
EMPTY_STATUS = "TRACKED_APPEND_ONLY_NO_CORRECTIONS"
CORRECTED_STATUS = "TRACKED_APPEND_ONLY_CORRECTIONS_IDENTITY_UNATTESTED"
ENTRY_STATUS = "TRACKED_LOCAL_SOURCE_DECISION_IDENTITY_UNATTESTED"
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_RECEIPTS = 10_000
MAX_CORRECTIONS = 10_000
ALLOWED_ACTIONS = frozenset(("supersede", "void"))
ALLOWED_REASON_CODES = frozenset(
    (
        "duplicate_receipt",
        "evidence_integrity_failure",
        "invalid_result",
        "source_superseded",
    )
)
ENTRY_AUTHORITY = {
    "humanDecisionAttested": False,
    "identityAttested": False,
    "launchable": False,
    "moderationAuthority": False,
    "productionMutation": False,
    "publication": False,
    "ranking": False,
}
LEDGER_AUTHORITY = {
    "humanDecisionAttested": False,
    "identityAttested": False,
    "launchable": False,
    "moderationAuthority": False,
    "productionApplied": False,
    "productionMutation": False,
    "publication": False,
    "ranking": False,
}
ENTRY_BOUNDARY = (
    "This append-only source record changes only current local proof-point eligibility. "
    "It preserves the immutable reviewed receipt and replay, carries no reviewer identity "
    "or moderation authority, and cannot mutate production, publish, rank, or launch."
)
LEDGER_BOUNDARY = (
    "All reviewed receipts remain historical evidence. A void or supersession excludes only "
    "the corrected receipt from current exact-scope proof points; source records are append-only, "
    "identity-unattested, local, and grant no production, publication, ranking, or launch authority."
)


class CorrectionLedgerError(ValueError):
    """Raised when correction lineage is malformed or overclaims authority."""


def _require(predicate: bool, message: str) -> None:
    if not predicate:
        raise CorrectionLedgerError(message)


def _hex64(value: Any, label: str) -> str:
    _require(type(value) is str and HEX64_RE.fullmatch(value) is not None, f"{label} must be lowercase hex64")
    return value


def _exact_object(value: Any, keys: Iterable[str], label: str) -> dict[str, Any]:
    _require(type(value) is dict, f"{label} must be an object")
    expected = set(keys)
    _require(set(value) == expected, f"{label} fields drift")
    return value


def _receipt_ids(values: Any) -> list[str]:
    _require(type(values) is list and 0 < len(values) <= MAX_RECEIPTS, "approved receipt IDs must be a non-empty bounded list")
    receipt_ids = [_hex64(value, "approved receipt ID") for value in values]
    _require(len(receipt_ids) == len(set(receipt_ids)), "approved receipt IDs contain duplicates")
    return receipt_ids


def build_correction_entry(
    *,
    sequence: int,
    previous_correction_id: str | None,
    target_receipt_id: str,
    action: str,
    successor_receipt_id: str | None,
    reason_code: str,
) -> dict[str, Any]:
    """Create one deterministic correction candidate without granting authority."""

    _require(type(sequence) is int and sequence > 0, "correction sequence must be positive")
    if previous_correction_id is not None:
        _hex64(previous_correction_id, "previous correction ID")
    target_receipt_id = _hex64(target_receipt_id, "target receipt ID")
    _require(action in ALLOWED_ACTIONS, "correction action is not allowlisted")
    _require(reason_code in ALLOWED_REASON_CODES, "correction reason is not allowlisted")
    if action == "supersede":
        successor_receipt_id = _hex64(successor_receipt_id, "successor receipt ID")
        _require(successor_receipt_id != target_receipt_id, "a receipt cannot supersede itself")
    else:
        _require(successor_receipt_id is None, "void corrections cannot name a successor")
    core = {
        "action": action,
        "authority": dict(ENTRY_AUTHORITY),
        "boundary": ENTRY_BOUNDARY,
        "correctionVersion": ENTRY_VERSION,
        "previousCorrectionId": previous_correction_id,
        "reasonCode": reason_code,
        "schemaVersion": ENTRY_SCHEMA,
        "sequence": sequence,
        "status": ENTRY_STATUS,
        "successorReceiptId": successor_receipt_id,
        "targetReceiptId": target_receipt_id,
    }
    return {**core, "correctionId": digest(core)}


def _evaluate_entries(
    entries: Any,
    approved_receipt_ids: list[str],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, int]]:
    _require(type(entries) is list and len(entries) <= MAX_CORRECTIONS, "correction entries must be a bounded list")
    approved = set(approved_receipt_ids)
    state = {
        receipt_id: {
            "correctionIds": [],
            "eligibleForScopedRating": True,
            "state": "active",
            "successorReceiptId": None,
        }
        for receipt_id in approved_receipt_ids
    }
    normalized: list[dict[str, Any]] = []
    previous_id: str | None = None
    corrected_targets: set[str] = set()
    for index, value in enumerate(entries):
        entry = _exact_object(
            value,
            (
                "action", "authority", "boundary", "correctionId", "correctionVersion",
                "previousCorrectionId", "reasonCode", "schemaVersion", "sequence", "status",
                "successorReceiptId", "targetReceiptId",
            ),
            f"correction entries[{index}]",
        )
        expected = build_correction_entry(
            sequence=index + 1,
            previous_correction_id=previous_id,
            target_receipt_id=entry.get("targetReceiptId"),
            action=entry.get("action"),
            successor_receipt_id=entry.get("successorReceiptId"),
            reason_code=entry.get("reasonCode"),
        )
        _require(entry == expected, f"correction entries[{index}] digest, chain, or boundary drift")
        target = entry["targetReceiptId"]
        successor = entry["successorReceiptId"]
        _require(target in approved, f"correction target {target} is not an approved receipt")
        _require(target not in corrected_targets, f"correction target {target} is repeated")
        _require(state[target]["state"] == "active", f"correction target {target} is no longer active")
        if entry["action"] == "supersede":
            _require(successor in approved, f"correction successor {successor} is not an approved receipt")
            _require(state[successor]["state"] == "active", f"correction successor {successor} is not active")
        state[target] = {
            "correctionIds": [entry["correctionId"]],
            "eligibleForScopedRating": False,
            "state": "superseded" if entry["action"] == "supersede" else "voided",
            "successorReceiptId": successor,
        }
        corrected_targets.add(target)
        normalized.append(entry)
        previous_id = entry["correctionId"]

    counts = Counter(row["state"] for row in state.values())
    summary = {
        "activeReceiptCount": counts["active"],
        "approvedReceiptCount": len(approved_receipt_ids),
        "correctionCount": len(normalized),
        "scopedRatingExcludedReceiptCount": counts["superseded"] + counts["voided"],
        "supersededReceiptCount": counts["superseded"],
        "voidedReceiptCount": counts["voided"],
    }
    return normalized, state, summary


def build_correction_ledger(
    *,
    dataset_digest: str,
    source_manifest_digest: str,
    approved_receipt_ids: list[str],
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a canonical source-bound ledger from an ordered entry journal."""

    dataset_digest = _hex64(dataset_digest, "dataset digest")
    source_manifest_digest = _hex64(source_manifest_digest, "source manifest digest")
    receipt_ids = _receipt_ids(approved_receipt_ids)
    normalized, _, summary = _evaluate_entries(entries, receipt_ids)
    core = {
        "authority": dict(LEDGER_AUTHORITY),
        "boundary": {"statement": LEDGER_BOUNDARY},
        "entries": normalized,
        "ledgerVersion": LEDGER_VERSION,
        "schemaVersion": LEDGER_SCHEMA,
        "sourceBindings": {
            "approvedReceiptIdsDigest": digest(sorted(receipt_ids)),
            "datasetDigest": dataset_digest,
            "sourceManifestDigest": source_manifest_digest,
        },
        "status": EMPTY_STATUS if not normalized else CORRECTED_STATUS,
        "summary": summary,
    }
    return {**core, "ledgerDigest": digest(core)}


def verify_correction_ledger(
    ledger: Any,
    *,
    dataset_digest: str,
    source_manifest_digest: str,
    approved_receipt_ids: list[str],
) -> dict[str, Any]:
    """Fail closed unless a supplied ledger equals its deterministic rebuild."""

    ledger = _exact_object(
        ledger,
        (
            "authority", "boundary", "entries", "ledgerDigest", "ledgerVersion",
            "schemaVersion", "sourceBindings", "status", "summary",
        ),
        "correction ledger",
    )
    expected = build_correction_ledger(
        dataset_digest=dataset_digest,
        source_manifest_digest=source_manifest_digest,
        approved_receipt_ids=approved_receipt_ids,
        entries=ledger.get("entries"),
    )
    _require(ledger == expected, "correction ledger does not match its source-bound deterministic rebuild")
    return expected


def project_receipt_corrections(
    ledger: Any,
    *,
    dataset_digest: str,
    source_manifest_digest: str,
    approved_receipt_ids: list[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Return immutable-history receipt states and the verified ledger."""

    verified = verify_correction_ledger(
        ledger,
        dataset_digest=dataset_digest,
        source_manifest_digest=source_manifest_digest,
        approved_receipt_ids=approved_receipt_ids,
    )
    _, state, _ = _evaluate_entries(verified["entries"], _receipt_ids(approved_receipt_ids))
    return state, verified


__all__ = [
    "ALLOWED_ACTIONS",
    "ALLOWED_REASON_CODES",
    "CORRECTED_STATUS",
    "CorrectionLedgerError",
    "EMPTY_STATUS",
    "ENTRY_SCHEMA",
    "LEDGER_SCHEMA",
    "build_correction_entry",
    "build_correction_ledger",
    "project_receipt_corrections",
    "verify_correction_ledger",
]
