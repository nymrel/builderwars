"""Replay-bound AgentBattles runback and rivalry-lineage contracts.

Public receipt digests and embedded ``PASS`` labels are not independent
authority. This module admits a runback only after re-projecting exact
transcript bytes with the standalone replay verifier. Lineage accepts proof
bundles rather than bare self-digested acceptances, binds every chain to one
exact rivalry, and keys challenge consumption by the full challenge digest.

These hashes are deterministic commitments, not signatures, provider or model
attestations, runtime attestations, or proof of hosted execution.
"""

from __future__ import annotations

import copy
import hashlib
import os
import re
import shutil
import stat
import tempfile
from typing import Any

from arena.canonical import NonCanonical, canonical_bytes, digest
from publishing.projection import PublicationError, project_receipt

CHALLENGE_SCHEMA = "agentbattles.runback-challenge.v1"
ACCEPTANCE_SCHEMA = "agentbattles.runback-acceptance.v1"
LINEAGE_SCHEMA = "agentbattles.runback-lineage.v1"
LINEAGE_STATE_SCHEMA = "agentbattles.runback-lineage-state.v1"
RIVALRY_SCHEMA = "agentbattles.rivalry-identity.v1"
MAX_SEED = 2_147_483_647
MAX_PUBLIC_RECEIPT_BYTES = 512 * 1024
MAX_TRANSCRIPT_BYTES = 8 * 1024 * 1024
MAX_ACCEPTANCE_BYTES = 64 * 1024
MAX_PROOF_BYTES = 2 * 1024 * 1024
MAX_LINEAGE_INPUT_BYTES = 32 * 1024 * 1024
MAX_LINEAGE_ACCEPTANCES = 128
MAX_LINEAGE_REPLAYS = MAX_LINEAGE_ACCEPTANCES + 1
MAX_LINEAGE_REPLAY_BYTES = 64 * 1024 * 1024

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_CHALLENGE_ID = re.compile(r"^challenge_[0-9a-f]{16}$")

CHALLENGE_BOUNDARY = (
    "This is a deterministic public-fixture projection derived from a receipt whose exact "
    "transcript bytes passed independent local replay. It is not a played runback, result, "
    "provider claim, model claim, runtime attestation, or hosted-execution claim."
)
ACCEPTANCE_BOUNDARY = (
    "The exact parent and child transcript bytes independently replay to these public "
    "projections, and the child matches the proposed seat-swapped next-seed public fixture. "
    "This does not attest a provider, model, runtime, person, or live hosted execution."
)
LINEAGE_BOUNDARY = (
    "This deterministic snapshot counts only proof bundles re-derived from exact transcript "
    "bytes. The caller must atomically compare-and-swap the exact previous lineage state for "
    "the returned next state; this pure function is not a global registry, signature, rating, "
    "or append-only store."
)


class RunbackError(ValueError):
    """A runback document cannot be admitted without weakening its binding."""


def _freeze_json(value: Any, label: str, depth: int = 0) -> Any:
    """Copy exact built-in JSON values and reject dynamic container subclasses."""

    if depth > 64:
        raise RunbackError(f"{label} exceeds the maximum JSON nesting depth")
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is list:
        return [_freeze_json(item, label, depth + 1) for item in value]
    if type(value) is dict:
        frozen = {}
        for key, item in value.items():
            if type(key) is not str:
                raise RunbackError(f"{label} object keys must be exact strings")
            frozen[key] = _freeze_json(item, label, depth + 1)
        return frozen
    raise RunbackError(f"{label} must contain only exact built-in JSON values")


def _bounded_canonical(value: Any, label: str, limit: int) -> bytes:
    try:
        encoded = canonical_bytes(value)
    except (NonCanonical, UnicodeError, ValueError, TypeError, RecursionError) as error:
        raise RunbackError(f"{label} is not canonically encodable") from error
    if len(encoded) > limit:
        raise RunbackError(f"{label} exceeds its canonical byte limit")
    return encoded


def _exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RunbackError(f"{label} must be an object")
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise RunbackError(f"{label} keys disagree; missing={missing}, unknown={unknown}")
    return value


def _hex64(value: Any, label: str) -> str:
    if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
        raise RunbackError(f"{label} must be an exact lowercase sha256 digest")
    return value


def _seed(value: Any, label: str) -> int:
    if type(value) is not int or not 0 <= value <= MAX_SEED:
        raise RunbackError(f"{label} must be a bounded non-negative integer")
    return value


def _game(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise RunbackError("receipt game must be an object")
    name, version = value.get("name"), value.get("version")
    if not isinstance(name, str) or not name or len(name) > 80:
        raise RunbackError("receipt game name must be a bounded non-empty string")
    if not isinstance(version, str) or not version or len(version) > 40:
        raise RunbackError("receipt game version must be a bounded non-empty string")
    return {"name": name, "version": version}


def _seat_rows(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    rows = receipt.get("entrants")
    if not isinstance(rows, list) or len(rows) != 2:
        raise RunbackError("receipt must contain exactly two entrant seats")
    normalized = []
    for expected_seat, row in enumerate(rows):
        if not isinstance(row, dict) or row.get("seat") != expected_seat:
            raise RunbackError("receipt entrants must be ordered exact seats 0 and 1")
        normalized.append(
            {
                "seat": expected_seat,
                "entrantId": _hex64(row.get("entrantId"), "entrantId"),
                "harnessVersionId": _hex64(
                    row.get("harnessVersionId"), "harnessVersionId"
                ),
            }
        )
    if normalized[0]["entrantId"] == normalized[1]["entrantId"]:
        raise RunbackError("a competitive receipt cannot seat one entrant twice")
    return normalized


def _fixture_id(game: dict[str, str], seed: int, seats: list[dict[str, Any]]) -> str:
    return digest(
        {
            "schemaVersion": "agentwars.fixture-identity.v1",
            "game": game,
            "seed": seed,
            "seats": [
                {
                    "entrantId": row["entrantId"],
                    "harnessVersionId": row["harnessVersionId"],
                }
                for row in seats
            ],
        }
    )


def _rivalry_core(game: dict[str, str], seats: list[dict[str, Any]]) -> dict[str, Any]:
    entrants = sorted(
        (
            {
                "entrantId": row["entrantId"],
                "harnessVersionId": row["harnessVersionId"],
            }
            for row in seats
        ),
        key=lambda row: (row["entrantId"], row["harnessVersionId"]),
    )
    return {"schemaVersion": RIVALRY_SCHEMA, "game": game, "entrants": entrants}


def _rivalry_id(game: dict[str, str], seats: list[dict[str, Any]]) -> str:
    return digest(_rivalry_core(game, seats))


def _receipt_identity(receipt: Any) -> dict[str, Any]:
    """Validate public projection fields consumed by the runback contract."""

    if not isinstance(receipt, dict):
        raise RunbackError("public receipt must be an object")
    if receipt.get("schemaVersion") != "agentwars.public-receipt.v1":
        raise RunbackError("runbacks require an AgentWars public receipt v1")
    _bounded_canonical(receipt, "public receipt", MAX_PUBLIC_RECEIPT_BYTES)

    projection_digest = _hex64(receipt.get("projectionDigest"), "projectionDigest")
    projection = copy.deepcopy(receipt)
    projection.pop("projectionDigest", None)
    if digest(projection) != projection_digest:
        raise RunbackError("public receipt projection digest does not match its bytes")

    receipt_id = _hex64(receipt.get("receiptId"), "receiptId")
    fixture_id = _hex64(receipt.get("fixtureId"), "fixtureId")
    game = _game(receipt.get("game"))
    seed = _seed(receipt.get("seed"), "receipt seed")
    seats = _seat_rows(receipt)
    if _fixture_id(game, seed, seats) != fixture_id:
        raise RunbackError("receipt fixture id does not bind game, seed, and seats")

    verification = receipt.get("verification")
    if not isinstance(verification, dict):
        raise RunbackError("receipt verification evidence is missing")
    required = {
        "verdict": "PASS",
        "replayVerdict": "PASS",
        "effectiveVerdict": "PASS",
        "engineDigestMatch": True,
        "verifierSnapshotMatch": True,
        "successExitCode": 0,
        "chainHead": receipt_id,
    }
    for key, expected in required.items():
        if verification.get(key) != expected:
            raise RunbackError(f"receipt verification predicate {key!r} is not exact")
    engine_digest = _hex64(verification.get("engineDigest"), "engineDigest")
    verifier_snapshot = _hex64(
        verification.get("verifierSnapshotDigest"), "verifierSnapshotDigest"
    )

    source = receipt.get("sourceParity")
    transcript = receipt.get("transcript")
    if not isinstance(source, dict) or not isinstance(transcript, dict):
        raise RunbackError("receipt source/transcript parity evidence is missing")
    if source.get("chainHead") != receipt_id or transcript.get("chainHead") != receipt_id:
        raise RunbackError("receipt, verification, source, and transcript chain heads disagree")
    source_sha = _hex64(source.get("fileSha256"), "source fileSha256")
    if transcript.get("sha256") != source_sha:
        raise RunbackError("receipt source and transcript file digests disagree")

    outcome = receipt.get("outcome")
    if not isinstance(outcome, dict) or outcome.get("status") != "final":
        raise RunbackError("only final replay-PASS receipts may issue or complete runbacks")
    winner = outcome.get("winnerEntrantId")
    if winner is not None and winner not in {row["entrantId"] for row in seats}:
        raise RunbackError("receipt winner is not one of its entrants")

    share_core = {
        "schemaVersion": "agentwars.share-manifest.v1",
        "receiptId": receipt_id,
        "fixtureId": fixture_id,
        "entrants": receipt["entrants"],
        "outcome": outcome,
        "story": receipt.get("story"),
        "truth": receipt.get("truth"),
        "sourceParity": source,
    }
    if receipt.get("shareManifestHash") != digest(share_core):
        raise RunbackError("receipt share-manifest hash does not match its public fields")

    return {
        "receiptId": receipt_id,
        "fixtureId": fixture_id,
        "game": game,
        "seed": seed,
        "seats": seats,
        "winnerEntrantId": winner,
        "projectionDigest": projection_digest,
        "transcriptSha256": source_sha,
        "engineDigest": engine_digest,
        "verifierSnapshotDigest": verifier_snapshot,
        "rivalryId": _rivalry_id(game, seats),
    }


def _snapshot_transcript(path: Any) -> tuple[bytes, str]:
    if not isinstance(path, (str, os.PathLike)):
        raise RunbackError("transcript path must be a local filesystem path")
    raw_path = os.fspath(path)
    if not raw_path or "\x00" in raw_path:
        raise RunbackError("transcript path is invalid")
    try:
        entry = os.lstat(raw_path)
        if stat.S_ISLNK(entry.st_mode) or not stat.S_ISREG(entry.st_mode):
            raise RunbackError("transcript must be a regular non-symlink file")
        descriptor = os.open(
            raw_path,
            os.O_RDONLY
            | getattr(os, "O_BINARY", 0)
            | getattr(os, "O_NOFOLLOW", 0),
        )
        with os.fdopen(descriptor, "rb") as handle:
            before = os.fstat(handle.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise RunbackError("transcript must remain a regular file when opened")
            data = handle.read(MAX_TRANSCRIPT_BYTES + 1)
            after = os.fstat(handle.fileno())
    except RunbackError:
        raise
    except (OSError, ValueError) as error:
        raise RunbackError("transcript could not be read") from error
    if len(data) > MAX_TRANSCRIPT_BYTES:
        raise RunbackError("transcript exceeds its byte limit")
    stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
    if any(getattr(entry, field, None) != getattr(before, field, None) for field in stable_fields):
        raise RunbackError("transcript path changed before its bounded read")
    if any(getattr(before, field, None) != getattr(after, field, None) for field in stable_fields):
        raise RunbackError("transcript changed during its bounded read")
    if before.st_size != len(data):
        raise RunbackError("transcript size changed during its bounded read")
    return data, hashlib.sha256(data).hexdigest()


def _independently_verified_receipt(
    receipt: dict[str, Any],
    transcript_path: Any,
    verification_cache: dict[tuple[str, str, str], tuple[dict[str, Any], dict[str, Any]]] | None = None,
    replay_budget: dict[str, int] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    frozen_receipt = _freeze_json(receipt, "public receipt")
    claimed = _receipt_identity(frozen_receipt)
    if type(transcript_path) is not str:
        raise RunbackError("transcript path must be an exact local path string")
    cache_key = (
        os.path.abspath(transcript_path),
        claimed["projectionDigest"],
        claimed["transcriptSha256"],
    )
    if verification_cache is not None and cache_key in verification_cache:
        cached_identity, cached_receipt = verification_cache[cache_key]
        if cached_receipt != frozen_receipt:
            raise RunbackError("one replay cache key maps to conflicting receipt bytes")
        return copy.deepcopy(cached_identity), copy.deepcopy(cached_receipt)

    transcript_bytes, transcript_sha = _snapshot_transcript(transcript_path)
    if replay_budget is not None:
        next_replays = replay_budget["replays"] + 1
        next_bytes = replay_budget["bytes"] + len(transcript_bytes)
        if next_replays > MAX_LINEAGE_REPLAYS:
            raise RunbackError("lineage exceeds its independent replay-count budget")
        if next_bytes > MAX_LINEAGE_REPLAY_BYTES:
            raise RunbackError("lineage exceeds its aggregate transcript replay-byte budget")
        replay_budget["replays"] = next_replays
        replay_budget["bytes"] = next_bytes
    temporary_root = None
    projection_error = None
    cleanup_error = None
    projected = None
    try:
        temporary_root = tempfile.mkdtemp(prefix="agentbattles-runback-")
        temporary_path = os.path.join(temporary_root, "transcript.jsonl")
        with open(temporary_path, "xb") as handle:
            handle.write(transcript_bytes)
        projected, _records = project_receipt(temporary_path)
    except (OSError, PublicationError, ValueError, TypeError) as error:
        projection_error = error
    finally:
        if temporary_root is not None:
            try:
                shutil.rmtree(temporary_root)
            except OSError as error:
                cleanup_error = error
    if cleanup_error is not None:
        raise RunbackError("private temporary transcript cleanup failed") from cleanup_error
    if projection_error is not None:
        raise RunbackError("transcript failed independent replay projection") from projection_error
    if _bounded_canonical(projected, "independent receipt projection", MAX_PUBLIC_RECEIPT_BYTES) != (
        _bounded_canonical(frozen_receipt, "public receipt", MAX_PUBLIC_RECEIPT_BYTES)
    ):
        raise RunbackError("public receipt differs from independent transcript projection")
    if transcript_sha != claimed["transcriptSha256"]:
        raise RunbackError("transcript bytes differ from the receipt commitment")
    if verification_cache is not None:
        verification_cache[cache_key] = (
            copy.deepcopy(claimed),
            copy.deepcopy(frozen_receipt),
        )
    return claimed, frozen_receipt


def _challenge_from_verified(
    parent_receipt: dict[str, Any], parent: dict[str, Any]
) -> dict[str, Any]:
    if parent["seed"] == MAX_SEED:
        raise RunbackError("cannot derive a bounded next-seed runback")
    seats = [{**row, "seat": seat} for seat, row in enumerate(reversed(parent["seats"]))]
    seed = parent["seed"] + 1
    fixture_id = _fixture_id(parent["game"], seed, seats)
    public_core = {
        "parentReceiptId": parent["receiptId"],
        "fixtureId": fixture_id,
        "game": copy.deepcopy(parent_receipt["game"]),
        "seed": seed,
        "entrantIdsBySeat": [row["entrantId"] for row in seats],
    }
    payload = {
        "schemaVersion": CHALLENGE_SCHEMA,
        "status": "unplayed_challenge",
        "challengeId": "challenge_" + digest(public_core)[:16],
        "rivalryId": parent["rivalryId"],
        "parentReceiptId": parent["receiptId"],
        "parentProjectionDigest": parent["projectionDigest"],
        "parentFixtureId": parent["fixtureId"],
        "fixtureId": fixture_id,
        "game": parent["game"],
        "seed": seed,
        "seats": seats,
        "rules": {
            "seedPolicy": "parent_plus_one",
            "seatPolicy": "reverse_parent_seats",
            "harnessPolicy": "exact_parent_versions",
            "fixturePolicy": "exact_public_projection",
            "attemptPolicy": "one_accepted_child_per_full_challenge_digest",
        },
        "truth": {
            "parentTranscriptIndependentlyReprojected": True,
            "played": False,
            "resultClaimed": False,
            "modelAttested": False,
            "runtimeAttested": False,
            "boundary": CHALLENGE_BOUNDARY,
        },
    }
    payload["challengeDigest"] = digest(payload)
    return payload


def issue_runback(
    parent_receipt: dict[str, Any], *, transcript_path: Any
) -> dict[str, Any]:
    """Derive one unplayed runback after independently replaying its parent."""

    parent, frozen_receipt = _independently_verified_receipt(
        parent_receipt, transcript_path
    )
    return _challenge_from_verified(frozen_receipt, parent)


def validate_challenge(
    challenge: dict[str, Any], parent_receipt: dict[str, Any], *, transcript_path: Any
) -> dict[str, Any]:
    """Require a challenge to equal the independently parent-derived document."""

    expected = issue_runback(parent_receipt, transcript_path=transcript_path)
    if _freeze_json(challenge, "challenge") != expected:
        raise RunbackError("challenge does not equal the exact parent-derived runback")
    return copy.deepcopy(expected)


def _outcome(identity: dict[str, Any]) -> dict[str, Any]:
    return {"winnerEntrantId": identity["winnerEntrantId"]}


def _evidence_row(identity: dict[str, Any]) -> dict[str, Any]:
    return {
        "receiptId": identity["receiptId"],
        "projectionDigest": identity["projectionDigest"],
        "transcriptSha256": identity["transcriptSha256"],
        "engineDigest": identity["engineDigest"],
        "verifierSnapshotDigest": identity["verifierSnapshotDigest"],
        "replayVerdict": "PASS",
    }


def _derive_acceptance(
    challenge: dict[str, Any],
    parent_receipt: dict[str, Any],
    child_receipt: dict[str, Any],
    *,
    parent_transcript_path: Any,
    child_transcript_path: Any,
    verification_cache: dict[tuple[str, str, str], tuple[dict[str, Any], dict[str, Any]]] | None,
    replay_budget: dict[str, int] | None,
) -> dict[str, Any]:
    frozen_challenge = _freeze_json(challenge, "challenge")
    parent, frozen_parent = _independently_verified_receipt(
        parent_receipt, parent_transcript_path, verification_cache, replay_budget
    )
    expected_challenge = _challenge_from_verified(frozen_parent, parent)
    if frozen_challenge != expected_challenge:
        raise RunbackError("challenge does not equal the exact parent-derived runback")
    child, _frozen_child = _independently_verified_receipt(
        child_receipt, child_transcript_path, verification_cache, replay_budget
    )
    if child["receiptId"] == parent["receiptId"]:
        raise RunbackError("a runback child must be a distinct receipt")
    if child["rivalryId"] != parent["rivalryId"]:
        raise RunbackError("child receipt changed the exact rivalry identity")
    if child["fixtureId"] != frozen_challenge["fixtureId"]:
        raise RunbackError("child receipt does not prove the proposed fixture")
    if child["game"] != frozen_challenge["game"]:
        raise RunbackError("child receipt changed the proposed game")
    if child["seed"] != frozen_challenge["seed"]:
        raise RunbackError("child receipt changed the proposed seed")
    if child["seats"] != frozen_challenge["seats"]:
        raise RunbackError("child receipt changed the proposed entrants or harness versions")

    payload = {
        "schemaVersion": ACCEPTANCE_SCHEMA,
        "status": "completed_runback",
        "challengeId": frozen_challenge["challengeId"],
        "challengeDigest": frozen_challenge["challengeDigest"],
        "rivalryId": parent["rivalryId"],
        "parentReceiptId": parent["receiptId"],
        "childReceiptId": child["receiptId"],
        "parentFixtureId": parent["fixtureId"],
        "childFixtureId": child["fixtureId"],
        "game": child["game"],
        "seed": child["seed"],
        "seats": child["seats"],
        "comparison": {
            "parent": _outcome(parent),
            "child": _outcome(child),
            "winnerChanged": parent["winnerEntrantId"] != child["winnerEntrantId"],
        },
        "evidence": {
            "method": "independent_transcript_reprojection",
            "parent": _evidence_row(parent),
            "child": _evidence_row(child),
            "fixtureBindingVerified": True,
        },
        "truth": {
            "runbackCompleted": True,
            "providerAttested": False,
            "modelAttested": False,
            "runtimeAttested": False,
            "ratingEmitted": False,
            "boundary": ACCEPTANCE_BOUNDARY,
        },
    }
    payload["acceptanceDigest"] = digest(payload)
    return payload


def accept_runback(
    challenge: dict[str, Any],
    parent_receipt: dict[str, Any],
    child_receipt: dict[str, Any],
    *,
    parent_transcript_path: Any,
    child_transcript_path: Any,
) -> dict[str, Any]:
    """Bind independently replayed parent and child transcripts to one runback."""

    return _derive_acceptance(
        challenge,
        parent_receipt,
        child_receipt,
        parent_transcript_path=parent_transcript_path,
        child_transcript_path=child_transcript_path,
        verification_cache=None,
        replay_budget=None,
    )


_ACCEPTANCE_KEYS = {
    "schemaVersion",
    "status",
    "challengeId",
    "challengeDigest",
    "rivalryId",
    "parentReceiptId",
    "childReceiptId",
    "parentFixtureId",
    "childFixtureId",
    "game",
    "seed",
    "seats",
    "comparison",
    "evidence",
    "truth",
    "acceptanceDigest",
}
_EVIDENCE_ROW_KEYS = {
    "receiptId",
    "projectionDigest",
    "transcriptSha256",
    "engineDigest",
    "verifierSnapshotDigest",
    "replayVerdict",
}


def _validate_evidence_row(
    value: Any, label: str, expected_receipt_id: str
) -> dict[str, Any]:
    row = _exact_keys(value, _EVIDENCE_ROW_KEYS, label)
    if row["receiptId"] != expected_receipt_id:
        raise RunbackError(f"{label} receipt id disagrees with acceptance")
    for key in (
        "receiptId",
        "projectionDigest",
        "transcriptSha256",
        "engineDigest",
        "verifierSnapshotDigest",
    ):
        _hex64(row[key], f"{label} {key}")
    if row["replayVerdict"] != "PASS":
        raise RunbackError(f"{label} replay verdict must remain PASS")
    return row


def validate_acceptance(acceptance: dict[str, Any]) -> dict[str, Any]:
    """Validate shape and self-digest only; this is not lineage admission."""

    row = _exact_keys(
        _freeze_json(acceptance, "acceptance"), _ACCEPTANCE_KEYS, "acceptance"
    )
    _bounded_canonical(row, "acceptance", MAX_ACCEPTANCE_BYTES)
    if row["schemaVersion"] != ACCEPTANCE_SCHEMA or row["status"] != "completed_runback":
        raise RunbackError("acceptance schema or status is unsupported")
    if not isinstance(row["challengeId"], str) or _CHALLENGE_ID.fullmatch(row["challengeId"]) is None:
        raise RunbackError("acceptance challenge id is malformed")
    for key in (
        "challengeDigest",
        "rivalryId",
        "parentReceiptId",
        "childReceiptId",
        "parentFixtureId",
        "childFixtureId",
        "acceptanceDigest",
    ):
        _hex64(row[key], key)
    if row["parentReceiptId"] == row["childReceiptId"]:
        raise RunbackError("acceptance cannot point a receipt to itself")
    _exact_keys(row["game"], {"name", "version"}, "acceptance game")
    game = _game(row["game"])
    _seed(row["seed"], "acceptance seed")
    if not isinstance(row["seats"], list) or len(row["seats"]) != 2:
        raise RunbackError("acceptance must bind exactly two seats")
    for expected, seat in enumerate(row["seats"]):
        _exact_keys(seat, {"seat", "entrantId", "harnessVersionId"}, "acceptance seat")
        if seat["seat"] != expected:
            raise RunbackError("acceptance seats must be ordered 0 and 1")
        _hex64(seat["entrantId"], "acceptance entrantId")
        _hex64(seat["harnessVersionId"], "acceptance harnessVersionId")
    if row["seats"][0]["entrantId"] == row["seats"][1]["entrantId"]:
        raise RunbackError("acceptance cannot seat one entrant twice")
    if _fixture_id(game, row["seed"], row["seats"]) != row["childFixtureId"]:
        raise RunbackError("acceptance child fixture does not bind game, seed, and seats")
    if _rivalry_id(game, row["seats"]) != row["rivalryId"]:
        raise RunbackError("acceptance rivalry id does not bind game and entrant versions")

    comparison = _exact_keys(
        row["comparison"], {"parent", "child", "winnerChanged"}, "acceptance comparison"
    )
    entrants = {seat["entrantId"] for seat in row["seats"]}
    for label in ("parent", "child"):
        outcome = _exact_keys(
            comparison[label], {"winnerEntrantId"}, f"acceptance {label} outcome"
        )
        winner = outcome["winnerEntrantId"]
        if winner is not None:
            _hex64(winner, f"acceptance {label} winnerEntrantId")
            if winner not in entrants:
                raise RunbackError(f"acceptance {label} winner is not an entrant")
    if type(comparison["winnerChanged"]) is not bool:
        raise RunbackError("acceptance winnerChanged must be boolean")
    if comparison["winnerChanged"] != (
        comparison["parent"]["winnerEntrantId"]
        != comparison["child"]["winnerEntrantId"]
    ):
        raise RunbackError("acceptance winner comparison is inconsistent")

    evidence = _exact_keys(
        row["evidence"],
        {"method", "parent", "child", "fixtureBindingVerified"},
        "acceptance evidence",
    )
    if evidence["method"] != "independent_transcript_reprojection":
        raise RunbackError("acceptance verification method is unsupported")
    _validate_evidence_row(evidence["parent"], "parent evidence", row["parentReceiptId"])
    _validate_evidence_row(evidence["child"], "child evidence", row["childReceiptId"])
    if evidence["fixtureBindingVerified"] is not True:
        raise RunbackError("acceptance fixture binding must remain verified")

    truth = _exact_keys(
        row["truth"],
        {
            "runbackCompleted",
            "providerAttested",
            "modelAttested",
            "runtimeAttested",
            "ratingEmitted",
            "boundary",
        },
        "acceptance truth",
    )
    if truth["runbackCompleted"] is not True:
        raise RunbackError("accepted runback must remain completed")
    for key in ("providerAttested", "modelAttested", "runtimeAttested", "ratingEmitted"):
        if truth[key] is not False:
            raise RunbackError(f"acceptance truth predicate {key!r} must remain false")
    if truth["boundary"] != ACCEPTANCE_BOUNDARY:
        raise RunbackError("acceptance truth boundary is not exact")
    unsigned = copy.deepcopy(row)
    claimed = unsigned.pop("acceptanceDigest")
    if digest(unsigned) != claimed:
        raise RunbackError("acceptance digest does not match its bytes")
    return copy.deepcopy(row)


_PROOF_KEYS = {
    "acceptance",
    "challenge",
    "parentReceipt",
    "parentTranscriptPath",
    "childReceipt",
    "childTranscriptPath",
}


def _admit_proof(
    proof: Any,
    verification_cache: dict[tuple[str, str, str], tuple[dict[str, Any], dict[str, Any]]],
    replay_budget: dict[str, int],
) -> dict[str, Any]:
    bundle = _exact_keys(proof, _PROOF_KEYS, "runback proof")
    stored = validate_acceptance(bundle["acceptance"])
    derived = _derive_acceptance(
        bundle["challenge"],
        bundle["parentReceipt"],
        bundle["childReceipt"],
        parent_transcript_path=bundle["parentTranscriptPath"],
        child_transcript_path=bundle["childTranscriptPath"],
        verification_cache=verification_cache,
        replay_budget=replay_budget,
    )
    if stored != derived:
        raise RunbackError("stored acceptance differs from transcript-derived acceptance")
    return derived


def empty_lineage_state() -> dict[str, Any]:
    """Return the exact empty state a transactional registry must persist."""

    return {
        "schemaVersion": LINEAGE_STATE_SCHEMA,
        "consumedChallenges": [],
        "rivalries": [],
        "receiptProjections": [],
    }


def validate_lineage_state(state: Any) -> dict[str, Any]:
    """Validate the complete cumulative state needed for cross-call continuity."""

    frozen = _freeze_json(state, "lineage state")
    row = _exact_keys(
        frozen,
        {"schemaVersion", "consumedChallenges", "rivalries", "receiptProjections"},
        "lineage state",
    )
    _bounded_canonical(row, "lineage state", MAX_LINEAGE_INPUT_BYTES)
    if row["schemaVersion"] != LINEAGE_STATE_SCHEMA:
        raise RunbackError("lineage state schema is unsupported")

    consumed = row["consumedChallenges"]
    if type(consumed) is not list:
        raise RunbackError("lineage consumed challenges must be a list")
    consumed_digests = []
    short_ids = {}
    for item in consumed:
        entry = _exact_keys(
            item, {"challengeId", "challengeDigest"}, "consumed challenge"
        )
        if type(entry["challengeId"]) is not str or _CHALLENGE_ID.fullmatch(entry["challengeId"]) is None:
            raise RunbackError("consumed challenge short id is malformed")
        _hex64(entry["challengeDigest"], "consumed challenge digest")
        known = short_ids.get(entry["challengeId"])
        if known is not None and known != entry["challengeDigest"]:
            raise RunbackError("lineage state contains a short challenge-id collision")
        short_ids[entry["challengeId"]] = entry["challengeDigest"]
        consumed_digests.append(entry["challengeDigest"])
    if consumed_digests != sorted(set(consumed_digests)):
        raise RunbackError("consumed challenges must be unique and sorted by full digest")

    rivalries = row["rivalries"]
    if type(rivalries) is not list:
        raise RunbackError("lineage rivalry state must be a list")
    rivalry_ids = []
    rivalry_challenges = []
    rivalry_receipts = []
    for item in rivalries:
        entry = _exact_keys(
            item,
            {
                "rivalryId",
                "rootReceiptId",
                "headReceiptId",
                "receiptIds",
                "challengeDigests",
                "completedRunbacks",
            },
            "lineage rivalry",
        )
        for key in ("rivalryId", "rootReceiptId", "headReceiptId"):
            _hex64(entry[key], f"lineage rivalry {key}")
        if type(entry["completedRunbacks"]) is not int or entry["completedRunbacks"] < 1:
            raise RunbackError("lineage rivalry completedRunbacks must be a positive integer")
        if type(entry["receiptIds"]) is not list:
            raise RunbackError("lineage rivalry receiptIds must be a list")
        if type(entry["challengeDigests"]) is not list:
            raise RunbackError("lineage rivalry challengeDigests must be a list")
        for receipt_id in entry["receiptIds"]:
            _hex64(receipt_id, "lineage rivalry receipt id")
        for challenge_digest in entry["challengeDigests"]:
            _hex64(challenge_digest, "lineage rivalry challenge digest")
        if len(entry["receiptIds"]) != entry["completedRunbacks"] + 1:
            raise RunbackError("lineage rivalry receipt chain length is inconsistent")
        if len(entry["challengeDigests"]) != entry["completedRunbacks"]:
            raise RunbackError("lineage rivalry challenge count is inconsistent")
        if len(entry["receiptIds"]) != len(set(entry["receiptIds"])):
            raise RunbackError("lineage rivalry receipt chain repeats a receipt")
        if len(entry["challengeDigests"]) != len(set(entry["challengeDigests"])):
            raise RunbackError("lineage rivalry repeats a challenge digest")
        if entry["receiptIds"][0] != entry["rootReceiptId"]:
            raise RunbackError("lineage rivalry root does not match its receipt chain")
        if entry["receiptIds"][-1] != entry["headReceiptId"]:
            raise RunbackError("lineage rivalry head does not match its receipt chain")
        rivalry_challenges.extend(entry["challengeDigests"])
        rivalry_receipts.extend(entry["receiptIds"])
        rivalry_ids.append(entry["rivalryId"])
    if rivalry_ids != sorted(set(rivalry_ids)):
        raise RunbackError("lineage rivalries must be unique and sorted")

    projections = row["receiptProjections"]
    if type(projections) is not list:
        raise RunbackError("lineage receipt projections must be a list")
    receipt_ids = []
    for item in projections:
        entry = _exact_keys(
            item, {"receiptId", "projectionDigest"}, "lineage receipt projection"
        )
        _hex64(entry["receiptId"], "lineage receipt id")
        _hex64(entry["projectionDigest"], "lineage receipt projection digest")
        receipt_ids.append(entry["receiptId"])
    if receipt_ids != sorted(set(receipt_ids)):
        raise RunbackError("lineage receipt projections must be unique and sorted")
    if len(rivalry_challenges) != len(set(rivalry_challenges)):
        raise RunbackError("one consumed challenge cannot belong to multiple rivalries")
    if sorted(rivalry_challenges) != consumed_digests:
        raise RunbackError("consumed challenges do not equal the rivalry histories")
    if len(rivalry_receipts) != len(set(rivalry_receipts)):
        raise RunbackError("one receipt cannot belong to multiple rivalry histories")
    if sorted(rivalry_receipts) != receipt_ids:
        raise RunbackError(
            "receipt projections must equal the rivalry history receipts exactly"
        )
    return row


def _preflight_replay_workload(proofs: list[dict[str, Any]]) -> None:
    unique = set()
    total_bytes = 0
    for proof in proofs:
        bundle = _exact_keys(proof, _PROOF_KEYS, "runback proof")
        for receipt_key, path_key in (
            ("parentReceipt", "parentTranscriptPath"),
            ("childReceipt", "childTranscriptPath"),
        ):
            receipt = bundle[receipt_key]
            path = bundle[path_key]
            if type(path) is not str or not path or "\x00" in path:
                raise RunbackError("proof transcript path must be an exact local path string")
            if type(receipt) is not dict:
                raise RunbackError("proof public receipt must be an exact object")
            key = (
                os.path.abspath(path),
                _hex64(receipt.get("projectionDigest"), "proof projection digest"),
                _hex64(
                    receipt.get("transcript", {}).get("sha256")
                    if type(receipt.get("transcript")) is dict
                    else None,
                    "proof transcript digest",
                ),
            )
            if key in unique:
                continue
            unique.add(key)
            try:
                entry = os.lstat(path)
            except OSError as error:
                raise RunbackError("proof transcript could not be preflighted") from error
            if stat.S_ISLNK(entry.st_mode) or not stat.S_ISREG(entry.st_mode):
                raise RunbackError("proof transcript must be a regular non-symlink file")
            if entry.st_size > MAX_TRANSCRIPT_BYTES:
                raise RunbackError("proof transcript exceeds its byte limit")
            total_bytes += entry.st_size
            if len(unique) > MAX_LINEAGE_REPLAYS:
                raise RunbackError("lineage exceeds its independent replay-count budget")
            if total_bytes > MAX_LINEAGE_REPLAY_BYTES:
                raise RunbackError("lineage exceeds its aggregate transcript replay-byte budget")


def build_lineage(
    proofs: list[dict[str, Any]], *, previous_state: dict[str, Any]
) -> dict[str, Any]:
    """Project replay-bound deltas and the exact next transactional state."""

    frozen_proofs = _freeze_json(proofs, "runback proofs")
    if type(frozen_proofs) is not list:
        raise RunbackError("runback proofs must be an exact list")
    if len(frozen_proofs) > MAX_LINEAGE_ACCEPTANCES:
        raise RunbackError("runback proof corpus exceeds the bounded lineage limit")
    prior = validate_lineage_state(previous_state)
    total_bytes = 0
    for item in frozen_proofs:
        total_bytes += len(_bounded_canonical(item, "runback proof", MAX_PROOF_BYTES))
        if total_bytes > MAX_LINEAGE_INPUT_BYTES:
            raise RunbackError("runback proof corpus exceeds the aggregate byte limit")
    _preflight_replay_workload(frozen_proofs)
    verification_cache = {}
    replay_budget = {"replays": 0, "bytes": 0}
    rows = [
        _admit_proof(item, verification_cache, replay_budget)
        for item in frozen_proofs
    ]

    prior_challenges = {
        entry["challengeDigest"]: entry for entry in prior["consumedChallenges"]
    }
    challenge_ids = {
        entry["challengeId"]: entry["challengeDigest"]
        for entry in prior["consumedChallenges"]
    }
    prior_rivalries = {entry["rivalryId"]: entry for entry in prior["rivalries"]}
    next_rivalries = copy.deepcopy(prior_rivalries)
    receipt_projection_digests = {
        entry["receiptId"]: entry["projectionDigest"]
        for entry in prior["receiptProjections"]
    }
    by_parent: dict[str, dict[str, Any]] = {}
    child_to_parent: dict[str, str] = {}
    challenge_digests: set[str] = set()
    acceptance_digests: set[str] = set()
    for row in rows:
        parent, child = row["parentReceiptId"], row["childReceiptId"]
        acceptance_digest = row["acceptanceDigest"]
        challenge_digest = row["challengeDigest"]
        if acceptance_digest in acceptance_digests:
            raise RunbackError("lineage repeats the same acceptance")
        acceptance_digests.add(acceptance_digest)
        if challenge_digest in prior_challenges:
            raise RunbackError("challenge was already consumed by prior authoritative state")
        if challenge_digest in challenge_digests:
            raise RunbackError("one full challenge digest cannot accept multiple children")
        challenge_digests.add(challenge_digest)
        known = challenge_ids.get(row["challengeId"])
        if known is not None and known != challenge_digest:
            raise RunbackError("short challenge id collides with a different full digest")
        challenge_ids[row["challengeId"]] = challenge_digest
        if parent in by_parent:
            raise RunbackError("one parent receipt cannot fork into multiple accepted runbacks")
        if child in child_to_parent:
            raise RunbackError("one child receipt cannot satisfy multiple parents")
        by_parent[parent] = row
        child_to_parent[child] = parent
        for label in ("parent", "child"):
            evidence = row["evidence"][label]
            receipt_id = evidence["receiptId"]
            projection_digest = evidence["projectionDigest"]
            existing = receipt_projection_digests.get(receipt_id)
            if existing is not None and existing != projection_digest:
                raise RunbackError("one receipt id maps to conflicting public projections")
            receipt_projection_digests[receipt_id] = projection_digest

    roots = sorted(parent for parent in by_parent if parent not in child_to_parent)
    chains = []
    covered: set[str] = set()
    rivalry_roots: set[str] = set()
    for root in roots:
        delta_receipt_ids = [root]
        challenge_ids_chain = []
        challenge_digests_chain = []
        cursor = root
        rivalry_id = None
        game = None
        entrants = None
        while cursor in by_parent:
            edge = by_parent[cursor]
            if rivalry_id is None:
                rivalry_id = edge["rivalryId"]
                game = edge["game"]
                entrants = _rivalry_core(edge["game"], edge["seats"])["entrants"]
            elif edge["rivalryId"] != rivalry_id:
                raise RunbackError("chained runback changed rivalry identity")
            covered.add(edge["acceptanceDigest"])
            challenge_ids_chain.append(edge["challengeId"])
            challenge_digests_chain.append(edge["challengeDigest"])
            cursor = edge["childReceiptId"]
            delta_receipt_ids.append(cursor)
        if rivalry_id in rivalry_roots:
            raise RunbackError("one lineage delta cannot open multiple roots for one rivalry")
        rivalry_roots.add(rivalry_id)
        previous = prior_rivalries.get(rivalry_id)
        if previous is not None and root != previous["headReceiptId"]:
            raise RunbackError("lineage delta does not extend the prior rivalry head")
        global_root = previous["rootReceiptId"] if previous is not None else root
        prior_count = previous["completedRunbacks"] if previous is not None else 0
        completed = prior_count + len(challenge_digests_chain)
        cumulative_receipts = (
            previous["receiptIds"] + delta_receipt_ids[1:]
            if previous is not None
            else delta_receipt_ids
        )
        cumulative_challenges = (
            previous["challengeDigests"] + challenge_digests_chain
            if previous is not None
            else challenge_digests_chain
        )
        next_rivalries[rivalry_id] = {
            "rivalryId": rivalry_id,
            "rootReceiptId": global_root,
            "headReceiptId": delta_receipt_ids[-1],
            "receiptIds": cumulative_receipts,
            "challengeDigests": cumulative_challenges,
            "completedRunbacks": completed,
        }
        chains.append(
            {
                "rivalryId": rivalry_id,
                "game": game,
                "entrants": entrants,
                "rootReceiptId": global_root,
                "previousHeadReceiptId": previous["headReceiptId"] if previous is not None else None,
                "headReceiptId": delta_receipt_ids[-1],
                "deltaReceiptIds": delta_receipt_ids,
                "challengeIds": challenge_ids_chain,
                "challengeDigests": challenge_digests_chain,
                "deltaCompletedRunbacks": len(challenge_digests_chain),
                "completedRunbacks": completed,
            }
        )
    if len(covered) != len(rows):
        raise RunbackError("runback lineage contains a receipt cycle")

    edges = [
        {
            "acceptanceDigest": row["acceptanceDigest"],
            "challengeId": row["challengeId"],
            "challengeDigest": row["challengeDigest"],
            "rivalryId": row["rivalryId"],
            "parentReceiptId": row["parentReceiptId"],
            "parentProjectionDigest": row["evidence"]["parent"]["projectionDigest"],
            "childReceiptId": row["childReceiptId"],
            "childProjectionDigest": row["evidence"]["child"]["projectionDigest"],
            "childFixtureId": row["childFixtureId"],
        }
        for row in sorted(
            rows,
            key=lambda value: (
                value["rivalryId"],
                value["parentReceiptId"],
                value["childReceiptId"],
                value["challengeDigest"],
            ),
        )
    ]
    receipt_ids = sorted(
        {edge["parentReceiptId"] for edge in edges}
        | {edge["childReceiptId"] for edge in edges}
    )
    consumed_by_digest = copy.deepcopy(prior_challenges)
    for row in rows:
        consumed_by_digest[row["challengeDigest"]] = {
            "challengeId": row["challengeId"],
            "challengeDigest": row["challengeDigest"],
        }
    next_state = {
        "schemaVersion": LINEAGE_STATE_SCHEMA,
        "consumedChallenges": [
            consumed_by_digest[key] for key in sorted(consumed_by_digest)
        ],
        "rivalries": [next_rivalries[key] for key in sorted(next_rivalries)],
        "receiptProjections": [
            {"receiptId": key, "projectionDigest": receipt_projection_digests[key]}
            for key in sorted(receipt_projection_digests)
        ],
    }
    validate_lineage_state(next_state)
    basis = {
        "acceptanceCount": len(edges),
        "receiptCount": len(receipt_ids),
        "receiptIds": receipt_ids,
        "edges": edges,
        "chains": chains,
        "previousStateDigest": digest(prior),
        "nextState": next_state,
        "nextStateDigest": digest(next_state),
        "newChallengeDigests": sorted(challenge_digests),
        "replayWorkload": {
            "independentReplayCount": replay_budget["replays"],
            "transcriptBytes": replay_budget["bytes"],
            "cacheEntries": len(verification_cache),
        },
        "forksAllowed": False,
        "cyclesAllowed": False,
        "multipleRootsPerRivalryAllowed": False,
        "ratingEmitted": False,
        "boundary": LINEAGE_BOUNDARY,
    }
    return {
        "schemaVersion": LINEAGE_SCHEMA,
        "lineageId": digest(basis),
        "basis": basis,
    }


__all__ = [
    "ACCEPTANCE_SCHEMA",
    "CHALLENGE_SCHEMA",
    "LINEAGE_SCHEMA",
    "LINEAGE_STATE_SCHEMA",
    "RIVALRY_SCHEMA",
    "RunbackError",
    "accept_runback",
    "build_lineage",
    "empty_lineage_state",
    "issue_runback",
    "validate_acceptance",
    "validate_challenge",
    "validate_lineage_state",
]
