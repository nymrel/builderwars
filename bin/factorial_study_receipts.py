"""Receipt inspection for the AgentWars factorial study."""

from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from typing import Any

from factorial_study_core import *  # noqa: F401,F403

def _records(path: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line_number, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise StudyError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            require(isinstance(record, dict), f"{path}:{line_number}: record must be an object")
            records.append(record)
    require(records, f"empty transcript: {path}")
    return records


def _kind(records: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [record for record in records if record.get("kind") == kind]


def analyze_transcript(
    *,
    fixture: dict[str, Any],
    transcript_path: str,
    replay_verify: Any,
    allowed_result_reasons: set[str],
    output_root: str,
) -> dict[str, Any]:
    violations: list[str] = []
    replay = replay_verify(transcript_path)
    replay_verdict = replay.get("verdict")
    if replay_verdict != "PASS":
        violations.append(f"replay verdict {replay_verdict!r}")

    records = _records(transcript_path)
    headers = _kind(records, "header")
    results = _kind(records, "result")
    if len(headers) != 1:
        violations.append(f"expected one header, found {len(headers)}")
    if len(results) != 1:
        violations.append(f"expected one result, found {len(results)}")
    header = headers[0].get("body", {}) if headers else {}
    result = results[-1].get("body", {}) if results else {}

    expected_seats = {"0": fixture["seat0"]["id"], "1": fixture["seat1"]["id"]}
    recorded_entrants = header.get("entrants") if isinstance(header, dict) else None
    if not isinstance(recorded_entrants, list) or len(recorded_entrants) != 2:
        violations.append("header does not contain exactly two entrants")
    else:
        for seat, treatment in enumerate((fixture["seat0"], fixture["seat1"])):
            entrant = recorded_entrants[seat]
            if entrant.get("name") != treatment["id"]:
                violations.append(f"seat {seat} entrant name mismatch")
            if entrant.get("claimed_model") != treatment["backend"]:
                violations.append(f"seat {seat} claimed_model mismatch")
            if entrant.get("execution_claim") != "model":
                violations.append(f"seat {seat} execution_claim is not model")

    recorded_seats = result.get("seats") if isinstance(result, dict) else None
    if recorded_seats != expected_seats:
        violations.append("result seat map does not match the preregistered fixture")
    reason = result.get("reason") if isinstance(result, dict) else None
    if reason not in allowed_result_reasons:
        violations.append(f"result reason {reason!r} is outside the publication allowlist")

    source_counts: dict[str, Counter[str]] = defaultdict(Counter)
    move_count = 0
    for record in _kind(records, "move"):
        body = record.get("body", {})
        player = body.get("player")
        if player not in (0, 1):
            violations.append("move record has invalid player")
            continue
        treatment = fixture[f"seat{player}"]["id"]
        note = body.get("entrant_message", {}).get("note") if isinstance(body.get("entrant_message"), dict) else None
        source = source_from_note(note)
        classification = source_class(source)
        source_counts[treatment][classification] += 1
        move_count += 1
        if classification != "model":
            violations.append(
                f"{treatment} move {body.get('turn')}: source={source!r} classified as {classification}"
            )

    winner = result.get("winner") if isinstance(result, dict) else None
    winner_treatment = None
    if winner in (0, 1):
        winner_treatment = fixture[f"seat{winner}"]["id"]
    elif winner is not None:
        violations.append(f"result winner {winner!r} is invalid")

    relative = os.path.relpath(transcript_path, output_root).replace(os.sep, "/")
    return {
        "fixture_id": fixture["fixture_id"],
        "comparison_id": fixture["comparison_id"],
        "pairing_id": fixture["pairing_id"],
        "replicate": fixture["replicate"],
        "seed": fixture["seed"],
        "order": fixture["order"],
        "seat0": fixture["seat0"]["id"],
        "seat1": fixture["seat1"]["id"],
        "winner": winner,
        "winner_treatment": winner_treatment,
        "reason": reason,
        "moves": result.get("moves") if isinstance(result, dict) else None,
        "transcript": relative,
        "transcript_sha256": file_digest(transcript_path),
        "chain_head": records[-1].get("hash"),
        "engine_digest": header.get("engine", {}).get("digest") if isinstance(header, dict) else None,
        "replay_verdict": replay_verdict,
        "source_counts": {name: dict(counts) for name, counts in sorted(source_counts.items())},
        "move_count": move_count,
        "violations": sorted(set(violations)),
    }


