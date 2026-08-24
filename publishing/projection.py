"""Central public projection for replay-verified AgentWars receipts.

Only this module translates raw transcripts into generated product JSON. Raw
commands, environment declarations, prompts, backend output, response hashes,
stderr, and claimed model names intentionally have no projection here.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata
from typing import Any

from arena.canonical import canonical_bytes, digest
from arena.transcript import load

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
LEGACY_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")
PUBLIC_RECEIPT_SCHEMA = "agentwars.public-receipt.v1"


class PublicationError(ValueError):
    """A receipt cannot cross the public projection boundary safely."""


def file_sha256(path: str) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            hasher.update(block)
    return hasher.hexdigest()


def json_text(value: Any) -> str:
    """Stable, human-reviewable generated JSON bytes represented as text."""
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def safe_text(value: Any, limit: int = 120) -> str:
    if not isinstance(value, str):
        value = str(value)
    value = "".join(
        char for char in value
        if unicodedata.category(char) not in ("Cc", "Cf", "Cs")
    )
    return " ".join(value.split())[:limit] or "unnamed"


def source_kind(note: Any) -> str:
    """Classify a self-declared move source without exposing its note tail."""
    if not isinstance(note, str):
        return "other"
    claim = re.split(r"[;:]", note, maxsplit=1)[0]
    return {
        "source=model": "model",
        "source=fallback": "fallback",
        "source=scripted": "scripted",
        "source=scripted_board": "scripted",
    }.get(claim, "other")


def _required(records: list[dict[str, Any]], kind: str) -> dict[str, Any]:
    row = next((item for item in records if item.get("kind") == kind), None)
    if row is None or not isinstance(row.get("body"), dict):
        raise PublicationError(f"verified transcript is missing {kind!r}")
    return row


def _exact_pass(report: dict[str, Any], returncode: int) -> bool:
    return (
        returncode == 0
        and report.get("verdict") == "PASS"
        and report.get("engine_digest_match") is True
        and report.get("verifier_snapshot_match") is True
    )


def verify_with_snapshot(path: str, *, verifier: str | None = None) -> dict[str, Any]:
    absolute = os.path.abspath(path)
    if not os.path.isfile(absolute):
        raise PublicationError("transcript path must name a local file")
    verifier_path = verifier or os.path.join(ROOT, "verify.py")
    try:
        completed = subprocess.run(
            [sys.executable, verifier_path, absolute, "--json"],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=90,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise PublicationError(
            f"standalone verifier failed safely: {error.__class__.__name__}"
        ) from error
    try:
        report = json.loads(completed.stdout)
    except (TypeError, json.JSONDecodeError) as error:
        raise PublicationError("standalone verifier returned invalid JSON") from error
    if not isinstance(report, dict):
        raise PublicationError("standalone verifier returned an invalid report")
    report["effective_verdict"] = "PASS" if _exact_pass(report, completed.returncode) else "FAIL"
    report["effective_exit_code"] = completed.returncode
    return report


def require_exact_verification(report: dict[str, Any]) -> dict[str, Any]:
    if report.get("effective_verdict") != "PASS":
        if report.get("verdict") == "PASS":
            raise PublicationError(
                "refusing receipt without an exact embedded verifier-engine match; "
                "replay, engine digest, and snapshot predicates are all required"
            )
        errors = report.get("errors") or []
        raise PublicationError(f"refusing unverified transcript: {errors[:1]}")
    return report


def _entrant_id(name: str) -> str:
    return digest({"identityScope": "agentwars-self-declared-name-v1", "name": name.casefold()})


def _verified_passport_row(raw):
    """Prefer a verified stable agentId for passport entrants; fail closed.

    The projection independently re-verifies the embedded signature rather than
    trusting that some upstream stage did it. A passport that does not verify
    cannot cross the public boundary at all.
    """
    record = raw.get("agent_passport")
    try:
        from arena import passport as passport_contract

        normalized = passport_contract.verify_passport(record)
        scope = dict(normalized["proofScope"])
    except ImportError as error:
        raise PublicationError(
            "passport entrant present but the in-engine passport verifier is unavailable"
        ) from error
    except Exception as error:
        raise PublicationError(f"entrant passport fails offline verification: {error}") from error
    script = raw.get("script")
    if not isinstance(script, dict) or script.get("sha256") != normalized["harnessSha256"]:
        raise PublicationError("entrant passport does not bind the recorded harness digest")
    if raw.get("name") != normalized["displayName"]:
        raise PublicationError("entrant passport displayName disagrees with the recorded name")
    if raw.get("claimed_model") != normalized["claimedModel"]:
        raise PublicationError("entrant passport claimedModel disagrees with the recorded claim")
    return {
        **record,
        "normalized": normalized,
        "scope": scope,
    }


def _harness_version_id(raw: Any) -> tuple[str | None, bool]:
    if not isinstance(raw, dict):
        return None, False
    script = raw.get("script")
    sha = script.get("sha256") if isinstance(script, dict) else None
    if not isinstance(sha, str) or HEX64_RE.fullmatch(sha) is None:
        return None, False
    return digest({"contentType": "entrant-script-sha256", "sha256": sha}), True


def public_entrants(header: dict[str, Any]) -> list[dict[str, Any]]:
    raw_rows = header.get("entrants")
    if not isinstance(raw_rows, list) or len(raw_rows) != 2:
        raise PublicationError("public receipts require exactly two entrants")
    rows = []
    for raw in sorted(raw_rows, key=lambda item: item.get("seat", -1)):
        if not isinstance(raw, dict) or raw.get("seat") not in (0, 1):
            raise PublicationError("entrant seats must be exactly 0 and 1")
        name = safe_text(raw.get("name", "unnamed"))
        execution_claim = raw.get("execution_claim", "unspecified")
        if execution_claim not in ("scripted", "model", "hybrid", "unspecified"):
            raise PublicationError("unsupported public execution claim")
        manifest_digest = raw.get("manifest_digest")
        if not isinstance(manifest_digest, str) or HEX64_RE.fullmatch(manifest_digest) is None:
            raise PublicationError("entrant manifestDigest must be exact lowercase sha256")
        harness_id, harness_proven = _harness_version_id(raw)
        if "agent_passport" in raw:
            passport = _verified_passport_row(raw)
            normalized = passport["normalized"]
            rows.append(
                {
                    "seat": raw["seat"],
                    # Key-derived stable identity replaces the name hash.
                    "entrantId": normalized["agentId"],
                    "name": name,
                    "executionClaim": execution_claim,
                    "harnessVersionId": harness_id,
                    "harnessVersionContentDerived": harness_proven,
                    "manifestDigest": manifest_digest,
                    "agentVersionId": normalized["versionId"],
                    "parentVersionId": normalized["parentVersionId"],
                    "identityStatus": "verified_signed",
                    "claimedModelSelfDeclared": normalized["claimedModel"],
                    "proofScope": {
                        "signatureProvesVersionDeclaration": True,
                        "keyBoundAgentId": True,
                        "recordedPreflightHarnessDigestBound": True,
                        "entrantIdentityAttested": False,
                        "modelAttested": False,
                        "runtimeAttested": False,
                        "personAttested": False,
                        "executionClaimsAttested": False,
                    },
                }
            )
        else:
            rows.append(
                {
                    "seat": raw["seat"],
                    "entrantId": _entrant_id(name),
                    "name": name,
                    "executionClaim": execution_claim,
                    "harnessVersionId": harness_id,
                    "harnessVersionContentDerived": harness_proven,
                    "manifestDigest": manifest_digest,
                }
            )
    if [row["seat"] for row in rows] != [0, 1]:
        raise PublicationError("transcript must contain one entrant in each seat")
    if len({row["entrantId"] for row in rows}) != 2:
        raise PublicationError("entrant identities collide after public normalization")
    return rows


def source_counts(records: list[dict[str, Any]], entrants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = {
        row["seat"]: {"model": 0, "fallback": 0, "scripted": 0, "other": 0}
        for row in entrants
    }
    for record in records:
        if record.get("kind") != "move":
            continue
        body = record.get("body")
        if not isinstance(body, dict) or body.get("player") not in counts:
            continue
        message = body.get("entrant_message")
        note = message.get("note") if isinstance(message, dict) else None
        counts[body["player"]][source_kind(note)] += 1
    return [
        {"entrantId": row["entrantId"], "seat": row["seat"], **counts[row["seat"]]}
        for row in entrants
    ]


def source_counts_digest(counts: list[dict[str, Any]]) -> str:
    return digest(counts)


def truth_status(entrants: list[dict[str, Any]], counts: list[dict[str, Any]]) -> str:
    if sum(row["model"] for row in counts):
        return "model_influenced_unattested"
    if {row["executionClaim"] for row in entrants} == {"scripted"}:
        return "scripted_preseason"
    if sum(row["fallback"] for row in counts):
        return "fallback_only_unattested"
    return "execution_claimed_unattested"


def _final_state(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    states = [
        row.get("body", {}).get("state")
        for row in records
        if row.get("kind") == "state"
    ]
    return states[-1] if states and isinstance(states[-1], dict) else None


def fantasy_scores(state: dict[str, Any] | None) -> list[int] | None:
    if not isinstance(state, dict) or state.get("format") not in (
        "redraft", "dynasty", "qb_surge"
    ):
        return None
    players, rosters = state.get("players"), state.get("rosters")
    if not isinstance(players, list) or not isinstance(rosters, list) or len(rosters) != 2:
        raise PublicationError("fantasy final state has malformed players or rosters")
    by_id = {row.get("id"): row for row in players if isinstance(row, dict)}
    metric = "dynasty_points" if state["format"] == "dynasty" else "redraft_points"
    try:
        scores = [sum(by_id[player_id][metric] for player_id in roster) for roster in rosters]
        if state["format"] == "qb_surge":
            for seat, roster in enumerate(rosters):
                scores[seat] += sum(
                    by_id[player_id]["redraft_points"]
                    for player_id in roster
                    if by_id[player_id]["position"] == "QB"
                )
    except (KeyError, TypeError) as error:
        raise PublicationError("fantasy score cannot be reproduced from public state") from error
    if any(not isinstance(value, int) or isinstance(value, bool) for value in scores):
        raise PublicationError("fantasy public scores must be integers")
    return scores


def _story(
    game_name: str,
    entrants: list[dict[str, Any]],
    outcome_status: str,
    winner: int | None,
    scores: list[int] | None,
    reason: str,
) -> dict[str, str]:
    game_label = game_name.removeprefix("fantasy_").replace("_", " ")
    if outcome_status == "void":
        return {
            "headline": f"{game_label.title()} fixture voided",
            "resultLine": "Replay verified the void; neither entrant receives a win.",
            "question": "Should this fixture be replayed?",
        }
    if winner is None:
        score_line = f"{scores[0]}-{scores[1]}" if scores is not None else reason
        return {
            "headline": f"{entrants[0]['name']} and {entrants[1]['name']} draw",
            "resultLine": safe_text(score_line, 160),
            "question": "Which side would you take in the runback?",
        }
    loser = 1 - winner
    score_line = (
        f"{scores[winner]}-{scores[loser]} over {entrants[loser]['name']}"
        if scores is not None
        else f"over {entrants[loser]['name']} ({reason})"
    )
    return {
        "headline": f"{entrants[winner]['name']} wins {game_label}",
        "resultLine": safe_text(score_line, 160),
        "question": "Would you take the other side in the runback?",
    }


def project_receipt(path: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    report = require_exact_verification(verify_with_snapshot(path))
    try:
        records = load(path)
    except Exception as error:
        raise PublicationError(f"could not load transcript: {error.__class__.__name__}") from error
    header = _required(records, "header")["body"]
    result = _required(records, "result")["body"]
    entrants = public_entrants(header)
    counts = source_counts(records, entrants)
    chain_head = report.get("chain_head")
    if (
        not isinstance(chain_head, str)
        or HEX64_RE.fullmatch(chain_head) is None
        or not records
        or records[-1].get("hash") != chain_head
    ):
        raise PublicationError("verified report and transcript chain head disagree")
    game = header.get("game")
    game_name = safe_text(game.get("name", "unknown"), 80) if isinstance(game, dict) else "unknown"
    game_version = safe_text(game.get("version", "unknown"), 40) if isinstance(game, dict) else "unknown"
    seed = header.get("seed")
    if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed <= 2_147_483_647:
        raise PublicationError("seed must be a bounded non-negative integer")
    legacy_match_id = header.get("match_id")
    if not isinstance(legacy_match_id, str) or LEGACY_ID_RE.fullmatch(legacy_match_id) is None:
        raise PublicationError("legacy match id is unsafe")
    fixture_core = {
        "schemaVersion": "agentwars.fixture-identity.v1",
        "game": {"name": game_name, "version": game_version},
        "seed": seed,
        "seats": [
            {
                "entrantId": row["entrantId"],
                "harnessVersionId": row["harnessVersionId"],
            }
            for row in entrants
        ],
    }
    fixture_id = digest(fixture_core)
    winner = result.get("winner")
    if winner not in (None, 0, 1):
        raise PublicationError("result winner must be seat 0, seat 1, or null")
    scores = fantasy_scores(_final_state(records))
    reason = safe_text(result.get("reason", "verified_result"), 160)
    outcome_status = (
        "void"
        if any(row.get("kind") == "engine_error" for row in records)
        else "final"
    )
    result_type = "void" if outcome_status == "void" else (
        "draw" if winner is None else "win"
    )
    signed_passport_count = sum(
        row.get("identityStatus") == "verified_signed" for row in entrants
    )
    passport_coverage = (
        "all"
        if signed_passport_count == len(entrants)
        else "partial" if signed_passport_count else "none"
    )
    truth_boundary = (
        "Replay proves accepted moves, deterministic state, scoring, and result. "
        "Entrant names, execution classes, and move-source labels remain hash-bound "
        "self-declarations; they do not prove provider or model identity."
    )
    if signed_passport_count:
        truth_boundary += (
            " Each entrant's signed passport was verified offline: it binds one "
            "tamper-evident version declaration to one public key. That is not "
            "an attestation of any model claim, runtime, or person."
        )
    receipt = {
        "schemaVersion": PUBLIC_RECEIPT_SCHEMA,
        "receiptId": chain_head,
        "fixtureId": fixture_id,
        "game": {
            "name": game_name,
            "version": game_version,
            "format": game_name.removeprefix("fantasy_") if game_name.startswith("fantasy_") else None,
        },
        "seed": seed,
        "entrants": entrants,
        "outcome": {
            "status": outcome_status,
            "resultType": result_type,
            "decisive": result.get("decisive") is True,
            "winnerSeat": winner,
            "winnerEntrantId": entrants[winner]["entrantId"] if winner in (0, 1) else None,
            "reason": reason,
            "scores": scores,
        },
        "story": _story(game_name, entrants, outcome_status, winner, scores, reason),
        "moveSourceClaims": counts,
        "truth": {
            "status": truth_status(entrants, counts),
            "modelAttested": False,
            "entrantIdentityAttested": False,
            "executionClaimsAttested": False,
            "boundary": truth_boundary,
            **(
                {
                    "agentVersionSignaturesVerified": True,
                    "keyBoundAgentIdsVerified": True,
                    "agentPassportCoverage": passport_coverage,
                }
                if signed_passport_count
                else {}
            ),
        },
        "verification": {
            "verdict": "PASS",
            "replayVerdict": "PASS",
            "effectiveVerdict": "PASS",
            "engineDigest": report.get("engine_digest_recorded"),
            "verifierSnapshotDigest": report.get("engine_digest_recorded"),
            "engineDigestMatch": True,
            "verifierSnapshotMatch": True,
            "chainHead": chain_head,
            "artifactPath": f"public/m/{chain_head}.jsonl",
            "requiredPredicates": [
                "replay_verdict=PASS",
                "engine_digest_match=true",
                "verifier_snapshot_match=true",
            ],
            "successExitCode": 0,
        },
        "sourceParity": {
            "fileSha256": file_sha256(path),
            "chainHead": chain_head,
            "moveSourceCountsDigest": source_counts_digest(counts),
        },
        "transcript": {
            "relativePath": f"public/m/{chain_head}.jsonl",
            "sha256": file_sha256(path),
            "bytes": os.path.getsize(path),
            "chainHead": chain_head,
        },
    }
    receipt["shareManifestHash"] = digest(
        {
            "schemaVersion": "agentwars.share-manifest.v1",
            "receiptId": receipt["receiptId"],
            "fixtureId": receipt["fixtureId"],
            "entrants": receipt["entrants"],
            "outcome": receipt["outcome"],
            "story": receipt["story"],
            "truth": receipt["truth"],
            "sourceParity": receipt["sourceParity"],
        }
    )
    receipt["projectionDigest"] = digest(receipt)
    return receipt, records


def public_clip(receipt: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    legal_moves = [
        row for row in records
        if row.get("kind") == "move" and row.get("body", {}).get("legal") is True
    ]
    if not legal_moves:
        terminal = next(
            (row for row in records if row.get("kind") in ("forfeit", "engine_error")),
            None,
        )
        if terminal is None:
            raise PublicationError("receipt has no bounded public clip candidate")
        selected, kind, label = terminal, "adjudication", "Replay-verified adjudication"
    else:
        selected, kind, label = legal_moves[-1], "final_accepted_move", "Final accepted move"
    body = selected.get("body", {})
    seat = body.get("player") if body.get("player") in (0, 1) else None
    internal_seed = {
        "receiptId": receipt["receiptId"],
        "seq": selected.get("seq"),
        "recordHash": selected.get("hash"),
    }
    clip_id = "clip_" + digest(internal_seed)[:16]
    return {
        "schemaVersion": "agentwars.clip-candidate.v1",
        "clipId": clip_id,
        "receiptId": receipt["receiptId"],
        "fixtureId": receipt["fixtureId"],
        "kind": kind,
        "label": label,
        "seqStart": selected.get("seq"),
        "seqEnd": selected.get("seq"),
        "seat": seat,
        "entrantId": receipt["entrants"][seat]["entrantId"] if seat in (0, 1) else None,
        "sourceClaim": source_kind(
            body.get("entrant_message", {}).get("note")
            if isinstance(body.get("entrant_message"), dict)
            else None
        ),
        "boundedRecordCount": 1,
        "rawMoveOmitted": True,
    }


def canonical_digest(value: Any) -> str:
    """Exported alias used by atomic installers without reimplementing hashing."""
    return hashlib.sha256(canonical_bytes(value)).hexdigest()
