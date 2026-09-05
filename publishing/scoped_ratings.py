"""Deterministic, non-ranking proof snapshots for reviewed AgentWars receipts.

The mobile Arena needs a useful competitive summary without collapsing unlike
games, rules, formats, or runtimes into a global leaderboard.  This module
groups only reviewed publication receipts by an exact evidence scope and emits
alphabetically ordered proof-point snapshots.  A point means one reviewed
final win in that exact scope; it is not a skill estimate or ranking.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from arena.canonical import digest


SCHEMA_VERSION = "agentwars.scoped-proof-rating-board/1"
RATING_METHOD = "reviewed_final_win_count_v1"
RATING_UNIT = "reviewed_final_win"
RESOURCE_CLASS = "reviewed_publication_receipt_v1"
STATUS = "LOCAL_SCOPED_PROOF_POINTS_NOT_RANKED"
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_RECEIPTS = 10_000
MAX_ENTRANTS = 256


class ScopedRatingError(ValueError):
    """Raised when receipts cannot safely produce a scoped proof snapshot."""


def _require(predicate: bool, message: str) -> None:
    if not predicate:
        raise ScopedRatingError(message)


def _object(value: Any, label: str) -> dict[str, Any]:
    _require(type(value) is dict, f"{label} must be an object")
    return value


def _list(value: Any, label: str, maximum: int) -> list[Any]:
    _require(type(value) is list, f"{label} must be a list")
    _require(len(value) <= maximum, f"{label} exceeds the bounded maximum of {maximum}")
    return value


def _string(value: Any, label: str) -> str:
    _require(type(value) is str and value != "", f"{label} must be a non-empty string")
    return value


def _hex64(value: Any, label: str) -> str:
    _require(type(value) is str and HEX64_RE.fullmatch(value) is not None, f"{label} must be lowercase hex64")
    return value


def _scope_for(receipt: dict[str, Any], index: int) -> dict[str, Any]:
    game = _object(receipt.get("game"), f"receipts[{index}].game")
    game_format = game.get("format")
    _require(game_format is None or (type(game_format) is str and game_format != ""), f"receipts[{index}].game.format must be null or a non-empty string")
    proof = _object(receipt.get("proof"), f"receipts[{index}].proof")
    return {
        "engineDigest": _hex64(proof.get("engineDigest"), f"receipts[{index}].proof.engineDigest"),
        "format": game_format,
        "gameName": _string(game.get("name"), f"receipts[{index}].game.name"),
        "gameVersion": _string(game.get("version"), f"receipts[{index}].game.version"),
        "ratingMethod": RATING_METHOD,
        "resourceClass": RESOURCE_CLASS,
    }


def _validated_receipt(receipt: dict[str, Any], index: int) -> dict[str, Any]:
    receipt_id = _hex64(receipt.get("receiptId"), f"receipts[{index}].receiptId")
    proof = _object(receipt.get("proof"), f"receipts[{index}].proof")
    _require(proof.get("publicationApproved") is True, f"receipt {receipt_id} is not publication-approved")
    _require(proof.get("replayVerdict") == "PASS", f"receipt {receipt_id} replay is not PASS")
    _require(proof.get("engineDigestMatch") is True, f"receipt {receipt_id} engine digest does not match")
    _require(proof.get("verifierSnapshotMatch") is True, f"receipt {receipt_id} verifier snapshot does not match")

    outcome = _object(receipt.get("outcome"), f"receipts[{index}].outcome")
    _require(outcome.get("status") == "final", f"receipt {receipt_id} is not final")
    _require(outcome.get("resultType") == "win", f"receipt {receipt_id} is not a reviewed win")
    winner_id = _hex64(outcome.get("winnerEntrantId"), f"receipts[{index}].outcome.winnerEntrantId")

    entrants = _list(receipt.get("entrants"), f"receipts[{index}].entrants", MAX_ENTRANTS)
    _require(len(entrants) >= 2, f"receipt {receipt_id} needs at least two entrants")
    rows = []
    entrant_ids: set[str] = set()
    seats: set[int] = set()
    for entrant_index, raw_entrant in enumerate(entrants):
        entrant = _object(raw_entrant, f"receipts[{index}].entrants[{entrant_index}]")
        entrant_id = _hex64(entrant.get("entrantId"), f"receipts[{index}].entrants[{entrant_index}].entrantId")
        _require(entrant_id not in entrant_ids, f"receipt {receipt_id} repeats entrant {entrant_id}")
        seat = entrant.get("seat")
        _require(type(seat) is int and seat >= 0 and seat not in seats, f"receipt {receipt_id} has an invalid or repeated seat")
        _require(entrant.get("harnessVersionContentDerived") is True, f"receipt {receipt_id} has a non-content-derived harness version")
        entrant_ids.add(entrant_id)
        seats.add(seat)
        rows.append(
            {
                "entrantId": entrant_id,
                "harnessVersionId": _hex64(
                    entrant.get("harnessVersionId"),
                    f"receipts[{index}].entrants[{entrant_index}].harnessVersionId",
                ),
                "name": _string(entrant.get("name"), f"receipts[{index}].entrants[{entrant_index}].name"),
                "seat": seat,
            }
        )
    _require(sorted(seats) == list(range(len(rows))), f"receipt {receipt_id} seats must be contiguous from zero")
    _require(winner_id in entrant_ids, f"receipt {receipt_id} winner is not an entrant")
    return {
        "entrants": rows,
        "receiptId": receipt_id,
        "scope": _scope_for(receipt, index),
        "winnerEntrantId": winner_id,
    }


def build_scoped_rating_boards(
    receipts: list[dict[str, Any]],
    *,
    dataset_digest: str,
    source_manifest_digest: str,
) -> list[dict[str, Any]]:
    """Build exact-scope proof-point snapshots from reviewed receipt cards."""

    _require(type(receipts) is list and 0 < len(receipts) <= MAX_RECEIPTS, "receipts must be a non-empty bounded list")
    dataset_digest = _hex64(dataset_digest, "datasetDigest")
    source_manifest_digest = _hex64(source_manifest_digest, "sourceManifestDigest")
    validated = [_validated_receipt(_object(row, f"receipts[{index}]"), index) for index, row in enumerate(receipts)]

    receipt_ids = [row["receiptId"] for row in validated]
    _require(len(receipt_ids) == len(set(receipt_ids)), "receipts contain duplicate receipt IDs")

    known_names: dict[str, str] = {}
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    scopes: dict[str, dict[str, Any]] = {}
    for row in validated:
        for entrant in row["entrants"]:
            known_name = known_names.get(entrant["entrantId"])
            _require(
                known_name is None or known_name == entrant["name"],
                f"entrant {entrant['entrantId']} has inconsistent names",
            )
            known_names[entrant["entrantId"]] = entrant["name"]
        scope_id = digest(row["scope"])
        scopes[scope_id] = row["scope"]
        groups[scope_id].append(row)

    boards = []
    for scope_id, scope_receipts in groups.items():
        entrant_stats: dict[str, dict[str, Any]] = {}
        for row in scope_receipts:
            winner_id = row["winnerEntrantId"]
            for entrant in row["entrants"]:
                stats = entrant_stats.setdefault(
                    entrant["entrantId"],
                    {
                        "entrantId": entrant["entrantId"],
                        "harnessVersionIds": set(),
                        "losses": 0,
                        "name": entrant["name"],
                        "receiptCount": 0,
                        "wins": 0,
                    },
                )
                _require(stats["name"] == entrant["name"], f"scope {scope_id} entrant name drift")
                stats["harnessVersionIds"].add(entrant["harnessVersionId"])
                stats["receiptCount"] += 1
                if entrant["entrantId"] == winner_id:
                    stats["wins"] += 1
                else:
                    stats["losses"] += 1

        entrants = []
        for entrant_id in sorted(entrant_stats):
            stats = entrant_stats[entrant_id]
            entrants.append(
                {
                    "eligibleForPublicRanking": False,
                    "entrantId": entrant_id,
                    "harnessVersionIds": sorted(stats["harnessVersionIds"]),
                    "losses": stats["losses"],
                    "name": stats["name"],
                    "ratingPoints": stats["wins"],
                    "ratingUnit": RATING_UNIT,
                    "receiptCount": stats["receiptCount"],
                    "status": "not_ranked",
                    "wins": stats["wins"],
                }
            )

        board_core = {
            "authority": {
                "crossScopeComparison": False,
                "globalSkill": False,
                "hosted": False,
                "identityAttested": False,
                "modelAttested": False,
                "providerAttested": False,
                "publication": False,
                "ranking": False,
                "runtimeAttested": False,
            },
            "boundary": {
                "statement": "One point is one reviewed final win in this exact evidence scope; rows are alphabetic and not ranked.",
            },
            "entrants": entrants,
            "receiptCount": len(scope_receipts),
            "receiptIds": sorted(row["receiptId"] for row in scope_receipts),
            "schemaVersion": SCHEMA_VERSION,
            "scope": scopes[scope_id],
            "scopeId": scope_id,
            "sourceBindings": {
                "datasetDigest": dataset_digest,
                "sourceManifestDigest": source_manifest_digest,
            },
            "status": STATUS,
        }
        boards.append({**board_core, "boardDigest": digest(board_core)})

    return sorted(
        boards,
        key=lambda board: (
            board["scope"]["gameName"],
            board["scope"]["gameVersion"],
            board["scope"]["format"] or "",
            board["scopeId"],
        ),
    )


def verify_scoped_rating_boards(
    boards: Any,
    receipts: list[dict[str, Any]],
    *,
    dataset_digest: str,
    source_manifest_digest: str,
) -> list[dict[str, Any]]:
    """Fail closed unless a supplied board set equals deterministic rebuild."""

    _require(type(boards) is list, "scoped rating boards must be a list")
    expected = build_scoped_rating_boards(
        receipts,
        dataset_digest=dataset_digest,
        source_manifest_digest=source_manifest_digest,
    )
    _require(boards == expected, "scoped rating boards do not match the reviewed receipts")
    return expected


__all__ = [
    "RATING_METHOD",
    "RATING_UNIT",
    "RESOURCE_CLASS",
    "SCHEMA_VERSION",
    "STATUS",
    "ScopedRatingError",
    "build_scoped_rating_boards",
    "verify_scoped_rating_boards",
]
