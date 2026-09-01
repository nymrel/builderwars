#!/usr/bin/env python3
"""Compile the reviewed AgentWars publication into a bounded mobile read model.

This is deliberately a read-path compiler, not a live API. It accepts only the
tracked, integrity-bound public-product contract and emits a smaller projection
for Arena, Watch, and proof-inspector clients. Any receipt that fails replay,
engine, snapshot, allowlist, or cross-manifest checks rejects the whole build.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arena.canonical import digest  # noqa: E402


DATASET_SCHEMA = "agentwars.public-product.v1"
SOURCE_MANIFEST_SCHEMA = "agentwars.public-source-manifest.v1"
RECEIPT_SCHEMA = "agentwars.public-receipt.v1"
READ_MODEL_SCHEMA = "builderwars.arena-read-model.v1"
PROJECTION_VERSION = "1"
DEFAULT_DATASET = ROOT / "publishing" / "agentwars-public-v1" / "dataset.json"
DEFAULT_SOURCE_MANIFEST = (
    ROOT / "publishing" / "agentwars-public-v1" / "source-manifest.json"
)
DEFAULT_OUTPUT = ROOT / "mobile-arena" / "data" / "arena-read-model.v1.json"
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_COMMIT_RE = re.compile(r"^[0-9a-f]{40,64}$")
UTC_SECOND_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_RECEIPTS = 10_000
MAX_RIVALRIES = 10_000
MAX_FIXTURES = 10_000


class ReadModelError(ValueError):
    """Raised when source evidence cannot safely produce the read model."""


def _require(predicate: bool, message: str) -> None:
    if not predicate:
        raise ReadModelError(message)


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ReadModelError(f"{label} is unavailable: {path}") from exc
    _require(0 < size <= MAX_INPUT_BYTES, f"{label} has an unsafe size: {size}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReadModelError(f"{label} is not valid UTF-8 JSON: {path}") from exc
    _require(type(value) is dict, f"{label} must be a JSON object")
    return value


def _hex64(value: Any, label: str) -> str:
    _require(type(value) is str and HEX64_RE.fullmatch(value) is not None, f"{label} must be lowercase hex64")
    return value


def _git_commit(value: Any, label: str) -> str:
    _require(
        type(value) is str and GIT_COMMIT_RE.fullmatch(value) is not None,
        f"{label} must be a full lowercase Git commit id",
    )
    return value


def _string(value: Any, label: str) -> str:
    _require(type(value) is str and value != "", f"{label} must be a non-empty string")
    return value


def _integer(value: Any, label: str) -> int:
    _require(type(value) is int and value >= 0, f"{label} must be a non-negative integer")
    return value


def _list(value: Any, label: str, maximum: int) -> list[Any]:
    _require(type(value) is list, f"{label} must be a list")
    _require(len(value) <= maximum, f"{label} exceeds the bounded maximum of {maximum}")
    return value


def _object(value: Any, label: str) -> dict[str, Any]:
    _require(type(value) is dict, f"{label} must be an object")
    return value


def _without(value: dict[str, Any], key: str) -> dict[str, Any]:
    return {name: item for name, item in value.items() if name != key}


def _source_counts(receipt: dict[str, Any], index: int) -> dict[str, int]:
    totals: Counter[str] = Counter()
    claims = _list(receipt.get("moveSourceClaims"), f"receipts[{index}].moveSourceClaims", 256)
    for claim_index, raw_claim in enumerate(claims):
        claim = _object(raw_claim, f"receipts[{index}].moveSourceClaims[{claim_index}]")
        for source in ("model", "scripted", "fallback", "other"):
            totals[source] += _integer(
                claim.get(source),
                f"receipts[{index}].moveSourceClaims[{claim_index}].{source}",
            )
    return {source: totals[source] for source in ("model", "scripted", "fallback", "other")}


def _evidence_class(counts: dict[str, int], truth_status: str) -> str:
    if counts["model"] > 0:
        evidence_class = "model_influenced_unattested"
        expected_truth_status = "model_influenced_unattested"
    elif counts["scripted"] > 0:
        evidence_class = "scripted_reference"
        expected_truth_status = "scripted_preseason"
    elif counts["fallback"] > 0:
        evidence_class = "fallback_only_reference"
        expected_truth_status = "scripted_preseason"
    else:
        evidence_class = "other_unattested_reference"
        expected_truth_status = "unattested_reference"
    _require(
        truth_status == expected_truth_status,
        f"truth status {truth_status!r} disagrees with move-source evidence {evidence_class!r}",
    )
    return evidence_class


def _receipt_card(receipt: dict[str, Any], index: int, approved_ids: set[str]) -> dict[str, Any]:
    _require(receipt.get("schemaVersion") == RECEIPT_SCHEMA, f"receipts[{index}] schema drift")
    receipt_id = _hex64(receipt.get("receiptId"), f"receipts[{index}].receiptId")
    fixture_id = _hex64(receipt.get("fixtureId"), f"receipts[{index}].fixtureId")
    _require(receipt_id in approved_ids, f"receipt {receipt_id} is not publication-approved")

    verification = _object(receipt.get("verification"), f"receipts[{index}].verification")
    for key in ("verdict", "effectiveVerdict", "replayVerdict"):
        _require(verification.get(key) == "PASS", f"receipt {receipt_id} has non-PASS {key}")
    for key in ("engineDigestMatch", "verifierSnapshotMatch"):
        _require(verification.get(key) is True, f"receipt {receipt_id} has false {key}")
    artifact_path = _string(verification.get("artifactPath"), f"receipts[{index}].verification.artifactPath")
    _require(artifact_path.startswith("public/m/") and artifact_path.endswith(".jsonl"), f"receipt {receipt_id} has unsafe artifact path")
    _require(".." not in artifact_path and "\\" not in artifact_path, f"receipt {receipt_id} has unsafe artifact path")

    truth = _object(receipt.get("truth"), f"receipts[{index}].truth")
    for key in ("modelAttested", "entrantIdentityAttested", "executionClaimsAttested"):
        _require(truth.get(key) is False, f"receipt {receipt_id} unexpectedly attests {key}")
    truth_status = _string(truth.get("status"), f"receipts[{index}].truth.status")
    counts = _source_counts(receipt, index)
    evidence_class = _evidence_class(counts, truth_status)

    entrants = _list(receipt.get("entrants"), f"receipts[{index}].entrants", 32)
    _require(len(entrants) >= 2, f"receipt {receipt_id} needs at least two entrants")
    entrant_cards = []
    entrant_names: dict[str, str] = {}
    for entrant_index, raw_entrant in enumerate(entrants):
        entrant = _object(raw_entrant, f"receipts[{index}].entrants[{entrant_index}]")
        entrant_id = _hex64(entrant.get("entrantId"), f"receipts[{index}].entrants[{entrant_index}].entrantId")
        name = _string(entrant.get("name"), f"receipts[{index}].entrants[{entrant_index}].name")
        _require(entrant_id not in entrant_names, f"receipt {receipt_id} repeats entrant {entrant_id}")
        _require(
            entrant.get("harnessVersionContentDerived") is True,
            f"receipt {receipt_id} has a non-content-derived harness version",
        )
        entrant_names[entrant_id] = name
        entrant_cards.append(
            {
                "entrantId": entrant_id,
                "executionClaim": _string(
                    entrant.get("executionClaim"),
                    f"receipts[{index}].entrants[{entrant_index}].executionClaim",
                ),
                "harnessVersionContentDerived": True,
                "harnessVersionId": _hex64(
                    entrant.get("harnessVersionId"),
                    f"receipts[{index}].entrants[{entrant_index}].harnessVersionId",
                ),
                "name": name,
                "seat": _integer(entrant.get("seat"), f"receipts[{index}].entrants[{entrant_index}].seat"),
            }
        )

    game = _object(receipt.get("game"), f"receipts[{index}].game")
    outcome = _object(receipt.get("outcome"), f"receipts[{index}].outcome")
    winner_id = _hex64(outcome.get("winnerEntrantId"), f"receipts[{index}].outcome.winnerEntrantId")
    _require(winner_id in entrant_names, f"receipt {receipt_id} winner is not an entrant")
    story = _object(receipt.get("story"), f"receipts[{index}].story")

    return {
        "entrants": entrant_cards,
        "evidence": {
            "class": evidence_class,
            "modelAttested": False,
            "moveSourceCounts": counts,
            "providerAttested": False,
            "runtimeAttested": False,
        },
        "fixtureId": fixture_id,
        "game": {
            "format": game.get("format"),
            "name": _string(game.get("name"), f"receipts[{index}].game.name"),
            "version": _string(game.get("version"), f"receipts[{index}].game.version"),
        },
        "headline": _string(story.get("headline"), f"receipts[{index}].story.headline"),
        "outcome": {
            "reason": _string(outcome.get("reason"), f"receipts[{index}].outcome.reason"),
            "resultType": _string(outcome.get("resultType"), f"receipts[{index}].outcome.resultType"),
            "status": _string(outcome.get("status"), f"receipts[{index}].outcome.status"),
            "winnerEntrantId": winner_id,
            "winnerName": entrant_names[winner_id],
            "winnerSeat": _integer(outcome.get("winnerSeat"), f"receipts[{index}].outcome.winnerSeat"),
        },
        "proof": {
            "artifactPath": artifact_path,
            "engineDigestMatch": True,
            "publicationApproved": True,
            "replayVerdict": "PASS",
            "verifierSnapshotMatch": True,
        },
        "receiptId": receipt_id,
        "resultLine": _string(story.get("resultLine"), f"receipts[{index}].story.resultLine"),
    }


def _rivalry_card(raw: Any, index: int, receipt_ids: set[str]) -> dict[str, Any]:
    rivalry = _object(raw, f"rivalries[{index}]")
    rivalry_id = _hex64(rivalry.get("rivalryId"), f"rivalries[{index}].rivalryId")
    history = _list(rivalry.get("history"), f"rivalries[{index}].history", 10_000)
    _require(rivalry.get("meetingCount") == len(history), f"rivalry {rivalry_id} meeting count mismatch")
    meetings = []
    for meeting_index, raw_meeting in enumerate(history):
        meeting = _object(raw_meeting, f"rivalries[{index}].history[{meeting_index}]")
        receipt_id = _hex64(meeting.get("receiptId"), f"rivalries[{index}].history[{meeting_index}].receiptId")
        _require(receipt_id in receipt_ids, f"rivalry {rivalry_id} references unknown receipt {receipt_id}")
        runback = _object(meeting.get("runback"), f"rivalries[{index}].history[{meeting_index}].runback")
        _require(runback.get("status") == "unplayed_challenge", f"rivalry {rivalry_id} runback status drift")
        meetings.append(
            {
                "game": _string(meeting.get("game"), f"rivalries[{index}].history[{meeting_index}].game"),
                "meetingNumber": _integer(meeting.get("meetingNumber"), f"rivalries[{index}].history[{meeting_index}].meetingNumber"),
                "receiptId": receipt_id,
                "runback": {
                    "challengeId": _string(runback.get("challengeId"), f"rivalries[{index}].history[{meeting_index}].runback.challengeId"),
                    "fixtureId": _hex64(runback.get("fixtureId"), f"rivalries[{index}].history[{meeting_index}].runback.fixtureId"),
                    "parentReceiptId": _hex64(runback.get("parentReceiptId"), f"rivalries[{index}].history[{meeting_index}].runback.parentReceiptId"),
                    "status": "unplayed_challenge",
                },
                "winnerEntrantId": _hex64(meeting.get("winnerEntrantId"), f"rivalries[{index}].history[{meeting_index}].winnerEntrantId"),
            }
        )
    return {
        "competition": _string(rivalry.get("competition"), f"rivalries[{index}].competition"),
        "entrantIds": [
            _hex64(value, f"rivalries[{index}].entrantIds")
            for value in _list(rivalry.get("entrantIds"), f"rivalries[{index}].entrantIds", 32)
        ],
        "meetingCount": len(meetings),
        "meetings": meetings,
        "rivalryId": rivalry_id,
    }


def _fixture_card(raw: Any, index: int) -> dict[str, Any]:
    fixture = _object(raw, f"futureFixtures[{index}]")
    _require(fixture.get("activationStatus") == "proposed_not_activated", f"future fixture {index} activation drift")
    _require(fixture.get("status") == "unplayed", f"future fixture {index} status drift")
    game = _object(fixture.get("game"), f"futureFixtures[{index}].game")
    matchup = _list(fixture.get("matchup"), f"futureFixtures[{index}].matchup", 32)
    return {
        "activationStatus": "proposed_not_activated",
        "closeAt": _string(fixture.get("closeAt"), f"futureFixtures[{index}].closeAt"),
        "fixtureId": _hex64(fixture.get("fixtureId"), f"futureFixtures[{index}].fixtureId"),
        "format": _string(fixture.get("format"), f"futureFixtures[{index}].format"),
        "game": {
            "name": _string(game.get("name"), f"futureFixtures[{index}].game.name"),
            "version": _string(game.get("version"), f"futureFixtures[{index}].game.version"),
        },
        "matchup": [
            {
                "entrantId": _hex64(_object(row, "fixture matchup").get("entrantId"), "fixture matchup entrantId"),
                "name": _string(_object(row, "fixture matchup").get("name"), "fixture matchup name"),
                "seat": _integer(_object(row, "fixture matchup").get("seat"), "fixture matchup seat"),
            }
            for row in matchup
        ],
        "rulesDigest": _hex64(fixture.get("rulesDigest"), f"futureFixtures[{index}].rulesDigest"),
        "rulesWeekId": _string(fixture.get("rulesWeekId"), f"futureFixtures[{index}].rulesWeekId"),
        "status": "unplayed",
        "week": _integer(fixture.get("week"), f"futureFixtures[{index}].week"),
    }


def _validate_projection_relationships(
    receipts: list[dict[str, Any]],
    fixtures: list[dict[str, Any]],
    rules: list[dict[str, Any]],
) -> None:
    """Reject cross-card drift before the mobile projection is digest-bound."""

    known_entrants: dict[str, str] = {}
    for receipt in receipts:
        seats = [entrant["seat"] for entrant in receipt["entrants"]]
        _require(
            sorted(seats) == list(range(len(seats))) and len(seats) == len(set(seats)),
            f"receipt {receipt['receiptId']} entrant seats must be contiguous and unique",
        )
        for entrant in receipt["entrants"]:
            known_name = known_entrants.get(entrant["entrantId"])
            _require(
                known_name is None or known_name == entrant["name"],
                f"entrant {entrant['entrantId']} has inconsistent names",
            )
            known_entrants[entrant["entrantId"]] = entrant["name"]

    rules_by_id: dict[str, dict[str, Any]] = {}
    for rule in rules:
        rules_week_id = rule["rulesWeekId"]
        _require(rules_week_id not in rules_by_id, f"duplicate rules week {rules_week_id}")
        rules_by_id[rules_week_id] = rule

    fixture_ids: set[str] = set()
    for fixture in fixtures:
        fixture_id = fixture["fixtureId"]
        _require(fixture_id not in fixture_ids, f"duplicate future fixture {fixture_id}")
        fixture_ids.add(fixture_id)
        _require(
            UTC_SECOND_RE.fullmatch(fixture["closeAt"]) is not None,
            f"future fixture {fixture_id} closeAt must be a UTC second timestamp",
        )
        matchup = fixture["matchup"]
        _require(len(matchup) == 2, f"future fixture {fixture_id} must remain two-seat")
        seats = [entrant["seat"] for entrant in matchup]
        entrant_ids = [entrant["entrantId"] for entrant in matchup]
        _require(sorted(seats) == [0, 1] and len(set(seats)) == 2, f"future fixture {fixture_id} seats drift")
        _require(len(set(entrant_ids)) == 2, f"future fixture {fixture_id} repeats an entrant")
        for entrant in matchup:
            _require(
                known_entrants.get(entrant["entrantId"]) == entrant["name"],
                f"future fixture {fixture_id} entrant is not receipt-backed",
            )
        rule = rules_by_id.get(fixture["rulesWeekId"])
        _require(rule is not None, f"future fixture {fixture_id} references unknown rules week")
        _require(
            rule["game"] == fixture["game"]["name"]
            and rule["gameVersion"] == fixture["game"]["version"]
            and rule["rulesDigest"] == fixture["rulesDigest"]
            and rule["week"] == fixture["week"],
            f"future fixture {fixture_id} rules binding drift",
        )


def _validate_source_entries(
    raw_receipts: list[Any], source_manifest: dict[str, Any], approved_ids: set[str]
) -> None:
    receipt_by_id: dict[str, tuple[int, dict[str, Any]]] = {}
    for index, raw_receipt in enumerate(raw_receipts):
        receipt = _object(raw_receipt, f"receipts[{index}]")
        receipt_id = _hex64(receipt.get("receiptId"), f"receipts[{index}].receiptId")
        _require(receipt_id not in receipt_by_id, f"dataset repeats receipt {receipt_id}")
        receipt_by_id[receipt_id] = (index, receipt)

    entries = _list(source_manifest.get("entries"), "sourceManifest.entries", MAX_RECEIPTS)
    _require(len(entries) == len(approved_ids), "source manifest entry count mismatch")
    seen: set[str] = set()
    for entry_index, raw_entry in enumerate(entries):
        entry = _object(raw_entry, f"sourceManifest.entries[{entry_index}]")
        receipt_id = _hex64(entry.get("receiptId"), f"sourceManifest.entries[{entry_index}].receiptId")
        _require(receipt_id in approved_ids, f"source manifest entry {receipt_id} is not approved")
        _require(receipt_id not in seen, f"source manifest repeats receipt {receipt_id}")
        seen.add(receipt_id)
        receipt_index, receipt = receipt_by_id[receipt_id]
        verification = _object(receipt.get("verification"), f"receipts[{receipt_index}].verification")
        transcript = _object(receipt.get("transcript"), f"receipts[{receipt_index}].transcript")
        entry_verification = _object(
            entry.get("verification"), f"sourceManifest.entries[{entry_index}].verification"
        )
        _require(entry.get("fixtureId") == receipt.get("fixtureId"), f"source entry {receipt_id} fixture mismatch")
        _require(entry.get("publicTranscriptPath") == verification.get("artifactPath"), f"source entry {receipt_id} proof path mismatch")
        _require(entry.get("publicTranscriptSha256") == transcript.get("sha256"), f"source entry {receipt_id} transcript digest mismatch")
        _require(entry.get("publicTranscriptBytes") == transcript.get("bytes"), f"source entry {receipt_id} transcript byte count mismatch")
        _require(entry.get("sourceChainHead") == transcript.get("chainHead"), f"source entry {receipt_id} chain head mismatch")
        _require(entry.get("sourceCounts") == _source_counts(receipt, receipt_index), f"source entry {receipt_id} move-source counts mismatch")
        _require(entry.get("engineDigest") == verification.get("engineDigest"), f"source entry {receipt_id} engine digest mismatch")
        _require(
            entry.get("verifierSnapshotDigest") == verification.get("verifierSnapshotDigest"),
            f"source entry {receipt_id} verifier snapshot mismatch",
        )
        for key in ("effectiveVerdict", "replayVerdict", "engineDigestMatch", "verifierSnapshotMatch"):
            _require(
                entry_verification.get(key) == verification.get(key),
                f"source entry {receipt_id} verification {key} mismatch",
            )
    _require(seen == approved_ids, "source manifest entries do not equal the approved allowlist")


def build_read_model(dataset: dict[str, Any], source_manifest: dict[str, Any]) -> dict[str, Any]:
    _require(dataset.get("schemaVersion") == DATASET_SCHEMA, "dataset schema drift")
    dataset_digest = _hex64(dataset.get("datasetDigest"), "dataset.datasetDigest")
    _require(digest(_without(dataset, "datasetDigest")) == dataset_digest, "dataset digest mismatch")

    _require(source_manifest.get("schemaVersion") == SOURCE_MANIFEST_SCHEMA, "source manifest schema drift")
    manifest_digest = _hex64(source_manifest.get("manifestDigest"), "sourceManifest.manifestDigest")
    _require(digest(_without(source_manifest, "manifestDigest")) == manifest_digest, "source manifest digest mismatch")
    _require(source_manifest.get("datasetDigest") == dataset_digest, "source manifest points to another dataset")

    publication = _object(dataset.get("publication"), "dataset.publication")
    _require(publication.get("policy") == "explicit_reviewed_allowlist_only", "publication policy is not reviewed allowlist only")
    approved_list = _list(publication.get("approvedReceiptIds"), "dataset.publication.approvedReceiptIds", MAX_RECEIPTS)
    approved_ids = {_hex64(value, "approved receipt id") for value in approved_list}
    _require(len(approved_ids) == len(approved_list), "publication allowlist contains duplicates")
    _require(publication.get("approvedReceiptCount") == len(approved_ids), "publication approved count mismatch")
    _require(source_manifest.get("approvedReceiptIds") == approved_list, "source manifest approved IDs mismatch")
    _require(source_manifest.get("approvedReceiptCount") == len(approved_ids), "source manifest approved count mismatch")

    raw_receipts = _list(dataset.get("receipts"), "dataset.receipts", MAX_RECEIPTS)
    _require(len(raw_receipts) == len(approved_ids), "dataset receipt count must equal the approved allowlist")
    _validate_source_entries(raw_receipts, source_manifest, approved_ids)
    receipts = [_receipt_card(_object(row, "receipt"), index, approved_ids) for index, row in enumerate(raw_receipts)]
    receipt_ids = {row["receiptId"] for row in receipts}
    _require(receipt_ids == approved_ids, "dataset receipt IDs do not equal the approved allowlist")

    raw_rivalries = _list(dataset.get("rivalries"), "dataset.rivalries", MAX_RIVALRIES)
    rivalries = [_rivalry_card(row, index, receipt_ids) for index, row in enumerate(raw_rivalries)]
    raw_fixtures = _list(dataset.get("futureFixtures"), "dataset.futureFixtures", MAX_FIXTURES)
    fixtures = [_fixture_card(row, index) for index, row in enumerate(raw_fixtures)]

    raw_rules = _list(dataset.get("rulesWeeks"), "dataset.rulesWeeks", 10_000)
    rules = []
    for index, raw_rule in enumerate(raw_rules):
        rule = _object(raw_rule, f"rulesWeeks[{index}]")
        _require(rule.get("status") == "playable", f"rules week {index} is not playable")
        rules.append(
            {
                "game": _string(rule.get("game"), f"rulesWeeks[{index}].game"),
                "gameVersion": _string(rule.get("gameVersion"), f"rulesWeeks[{index}].gameVersion"),
                "label": _string(rule.get("label"), f"rulesWeeks[{index}].label"),
                "rulesDigest": _hex64(rule.get("rulesDigest"), f"rulesWeeks[{index}].rulesDigest"),
                "rulesWeekId": _string(rule.get("rulesWeekId"), f"rulesWeeks[{index}].rulesWeekId"),
                "status": "playable",
                "week": _integer(rule.get("week"), f"rulesWeeks[{index}].week"),
            }
        )

    _validate_projection_relationships(receipts, fixtures, rules)

    evidence_counts = Counter(row["evidence"]["class"] for row in receipts)
    game_counts = Counter(row["game"]["name"] for row in receipts)
    channels = [
        {
            "game": game,
            "publishedReceiptCount": game_counts[game],
            "rulesWeekIds": [row["rulesWeekId"] for row in rules if row["game"] == game],
            "status": "tracked_publication_read_only",
        }
        for game in sorted(game_counts)
    ]

    build_integrity = _object(dataset.get("buildIntegrity"), "dataset.buildIntegrity")
    truth_boundary = _object(dataset.get("truthBoundary"), "dataset.truthBoundary")
    core = {
        "channels": channels,
        "futureFixtures": fixtures,
        "projectionVersion": PROJECTION_VERSION,
        "receipts": receipts,
        "rivalries": rivalries,
        "rulesWeeks": rules,
        "schemaVersion": READ_MODEL_SCHEMA,
        "source": {
            "approvedReceiptCount": len(approved_ids),
            "datasetDigest": dataset_digest,
            "datasetSchemaVersion": DATASET_SCHEMA,
            "datasetVersion": _string(dataset.get("datasetVersion"), "dataset.datasetVersion"),
            "publicationPolicy": "explicit_reviewed_allowlist_only",
            "sourceCommit": _git_commit(build_integrity.get("sourceCommit"), "dataset.buildIntegrity.sourceCommit"),
            "sourceManifestDigest": manifest_digest,
            "status": "tracked_local_publication_artifact_not_hosted",
        },
        "summary": {
            "fallbackOnlyReferenceReceiptCount": evidence_counts["fallback_only_reference"],
            "modelAttestedReceiptCount": 0,
            "modelInfluencedUnattestedReceiptCount": evidence_counts["model_influenced_unattested"],
            "receiptCount": len(receipts),
            "rivalryCount": len(rivalries),
            "scriptedReferenceReceiptCount": evidence_counts["scripted_reference"],
            "unplayedFixtureCount": len(fixtures),
            "verifiedReceiptCount": len(receipts),
        },
        "truthBoundary": {
            "authenticated": False,
            "hosted": False,
            "live": False,
            "modelAttested": False,
            "providerAttested": False,
            "runtimeAttested": False,
            "statement": _string(truth_boundary.get("statement"), "dataset.truthBoundary.statement"),
        },
    }
    return {**core, "readModelDigest": digest(core)}


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="atomically write the compiled read model")
    mode.add_argument("--check", action="store_true", help="fail unless the tracked output is byte-identical")
    args = parser.parse_args(argv)

    try:
        model = build_read_model(
            _load_object(args.dataset, "dataset"),
            _load_object(args.source_manifest, "source manifest"),
        )
        expected = _json_bytes(model)
        if args.write:
            _atomic_write(args.out, expected)
            print(f"wrote {args.out} ({len(model['receipts'])} approved receipts, {model['readModelDigest']})")
            return 0
        try:
            actual = args.out.read_bytes()
        except OSError as exc:
            raise ReadModelError(f"compiled read model is unavailable: {args.out}") from exc
        _require(actual == expected, f"compiled read model is stale: run {Path(__file__).name} --write")
        print(f"PASS: {args.out} is current ({len(model['receipts'])} approved receipts, {model['readModelDigest']})")
        return 0
    except ReadModelError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
