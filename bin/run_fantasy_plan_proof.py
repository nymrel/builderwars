#!/usr/bin/env python3
"""Bind two committed model-plan artifacts to replay-verified fantasy play.

Loads both plan artifacts through the production entrant harness, re-reads
their exact bytes, and refuses to continue unless the harness projection
matches. It then plays fantasy_redraft seed 9300 — one seed, both seat orders,
through the existing league scheduler — and fails closed unless every proof
condition holds: truth status, false attestation flags everywhere, decisive
non-forfeit matches, six model-plan moves per seat per match with zero
fallback/scripted/other moves, exact ready-payload projections, single
artifact occurrence per transcript, transcript identity binding, and
independent replay PASS verdicts. The public summary is written atomically
and only after every check passes; filesystem paths never appear in it.
"""

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS_PATH = os.path.join(ROOT, "entrants", "fantasy_plan_harness.py")
LEAGUE_RUNNER_PATH = os.path.join(ROOT, "bin", "run_agentwars_league.py")
DEFAULT_PLAN_A = os.path.join(
    ROOT, "matches", "agentwars-model-plan-proof", "plans", "win-now.json"
)
DEFAULT_PLAN_B = os.path.join(
    ROOT, "matches", "agentwars-model-plan-proof", "plans", "contrarian.json"
)

PROOF_SCHEMA = "agentwars.fantasy_model_plan_proof.v1"
GAME = "fantasy_redraft"
SEED = 9300
SEED_COUNT = 1
MATCHES_EXPECTED = 2
EXECUTION_CLAIM = "hybrid"
EXPECTED_STATUS = "model_influenced_unattested"
EXPECTED_TRUTH_BOUNDARY = (
    "Replay verifies rules, moves, state, and scoring. Entrant execution classes, "
    "claimed model names, and move-source notes are self-declared and hash-bound but "
    "not independently attested. Credentials remain inside entrant processes."
)
MOVES_PER_SEAT_PER_MATCH = 6
DEADLINE_SECONDS = 900.0
DEADLINE_RESERVE_SECONDS = 60.0
MAX_PROTOCOL_WAITS = MATCHES_EXPECTED * (2 + (2 * MOVES_PER_SEAT_PER_MATCH))
MIN_TIMEOUT_S = 1.0
MAX_TIMEOUT_S = (DEADLINE_SECONDS - DEADLINE_RESERVE_SECONDS) / MAX_PROTOCOL_WAITS

SOURCE_PUBLIC_KEYS = (
    "runId",
    "receiptSha256",
    "terminalTextSha256",
    "terminalTextExactPlan",
    "modelClaim",
    "reasoningEffort",
    "maxTokens",
    "fallbacksAllowed",
    "route",
)


class ProofBlocked(Exception):
    """Short, public rejection code; never carries a path or plan contents."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


class _Deadline:
    def __init__(self, seconds):
        self._end = time.monotonic() + seconds

    def check(self):
        if time.monotonic() >= self._end:
            raise ProofBlocked("deadline_exceeded")

    def cancel(self):
        self._end = float("inf")


def _load_module(name, path):
    if not os.path.isfile(path):
        raise ProofBlocked("module_not_found")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ProofBlocked("module_spec_failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _require(condition, code):
    if not condition:
        raise ProofBlocked(code)


def _load_plan(harness, raw_path):
    path = os.path.abspath(raw_path)
    _require(os.path.isfile(path), "artifact_not_found")
    with open(path, "rb") as handle:
        data = handle.read()
    _require(bool(data), "artifact_empty")
    artifact_sha = hashlib.sha256(data).hexdigest()
    projection = harness.load_artifact(path)
    _require(projection["artifact_sha256"] == artifact_sha, "artifact_bytes_mismatch")
    try:
        parsed = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise ProofBlocked("artifact_invalid_json") from None
    source = parsed.get("source") if isinstance(parsed, dict) else None
    _require(
        isinstance(source, dict) and all(key in source for key in SOURCE_PUBLIC_KEYS),
        "source_fields_missing",
    )
    _require(source["runId"] == projection["run_id"], "source_run_id_mismatch")
    _require(source["receiptSha256"] == projection["receipt_sha256"], "source_receipt_mismatch")
    public_source = {key: source[key] for key in SOURCE_PUBLIC_KEYS}
    _require(public_source["fallbacksAllowed"] is False, "fallbacks_allowed")
    _require(
        isinstance(public_source["terminalTextExactPlan"], bool),
        "terminal_exact_plan_type",
    )
    return {
        "abs_path": path,
        "name": "plan-" + artifact_sha[:12],
        "artifactSha256": artifact_sha,
        "planSha256": projection["plan_sha256"],
        "oxRunId": projection["run_id"],
        "oxReceiptSha256": projection["receipt_sha256"],
        "source": public_source,
    }


def _expected_ready(harness, plan):
    return {
        "type": "ready",
        "entrant": plan["name"],
        "version": harness.VERSION,
        "backend": harness.BACKEND_LABEL,
        "artifact_sha256": plan["artifactSha256"],
        "plan_sha256": plan["planSha256"],
        "ox_run_id": plan["oxRunId"],
        "ox_receipt_sha256": plan["oxReceiptSha256"],
    }


def _collect_transcripts(out_root):
    found = []
    for current, _dirs, names in os.walk(out_root):
        for name in names:
            if name.endswith(".jsonl") and not name.endswith(".diagnostics.jsonl"):
                found.append(os.path.join(current, name))
    return found


def _audit_transcript(harness, plans, path, league_row):
    from arena.replay import verify
    from arena.transcript import find, first, load

    with open(path, "rb") as handle:
        data = handle.read()
    transcript_sha = hashlib.sha256(data).hexdigest()
    stem = os.path.basename(path)[: -len(".jsonl")]
    records = load(path)

    header = first(records, "header")
    _require(header is not None, "transcript_header_missing")
    body = header["body"]
    _require(body.get("match_id") == stem, "filename_identity_mismatch")
    _require(body.get("seed") == SEED, "transcript_seed_mismatch")
    _require(body.get("game", {}).get("name") == GAME, "transcript_game_mismatch")
    attestation = body.get("attestation", {})
    _require(attestation.get("model_attested") is False, "header_model_attested")
    _require(attestation.get("execution_claims_attested") is False, "header_claims_attested")

    seats = [entrant.get("name") for entrant in body.get("entrants", [])]
    _require(len(seats) == 2 and all(seats), "transcript_seat_order_missing")
    _require(tuple(seats) == (league_row["seat0"], league_row["seat1"]), "summary_seats_mismatch")
    by_name = {plan["name"]: plan for plan in plans}
    _require(set(seats) == set(by_name), "unexpected_entrant_name")

    ready_records = find(records, "ready")
    _require(len(ready_records) == 2, "ready_record_count")
    _require(sorted(record["body"]["player"] for record in ready_records) == [0, 1], "ready_seat_count")
    for record in ready_records:
        seat = record["body"]["player"]
        observed = record["body"]["entrant_message"]
        _require(observed == _expected_ready(harness, by_name[seats[seat]]), "ready_projection_mismatch")

    _require(find(records, "forfeit") == [], "forfeit_record_present")
    _require(find(records, "engine_error") == [], "engine_error_present")
    _require(find(records, "abort") == [], "abort_record_present")

    result = first(records, "result")
    _require(result is not None, "result_missing")
    result_body = result["body"]
    _require(result_body.get("decisive") is True, "match_not_decisive")
    winner = result_body.get("winner")
    _require(winner in (0, 1), "winner_missing")
    reason = result_body.get("reason")
    _require(isinstance(reason, str) and not reason.startswith("forfeit"), "forfeit_reason")

    move_records = find(records, "move")
    _require(len(move_records) == 2 * MOVES_PER_SEAT_PER_MATCH, "move_count")
    per_seat = {0: 0, 1: 0}
    for record in move_records:
        seat = record["body"]["player"]
        _require(record["body"].get("legal") is True, "illegal_move_recorded")
        note = record["body"].get("entrant_message", {}).get("note", "")
        _require(note.startswith("source=model_plan"), "non_model_move_note")
        per_seat[seat] += 1
    _require(all(count == MOVES_PER_SEAT_PER_MATCH for count in per_seat.values()), "per_seat_move_count")

    for plan in plans:
        occurrences = data.count(plan["artifactSha256"].encode("utf-8"))
        _require(occurrences == 1, "artifact_occurrence_count")

    report = verify(path)
    _require(report.get("verdict") == "PASS", "replay_not_pass")

    _require(league_row.get("winner") == seats[winner], "summary_winner_mismatch")
    _require(league_row.get("reason") == reason, "summary_reason_mismatch")
    _require(league_row.get("chainHead") == records[-1]["hash"], "chain_head_mismatch")

    return {
        "matchId": stem,
        "seed": SEED,
        "seat0": seats[0],
        "seat1": seats[1],
        "winner": seats[winner],
        "reason": reason,
        "chainHead": records[-1]["hash"],
        "transcriptSha256": transcript_sha,
        "replayVerdict": "PASS",
        "verified": True,
        "decisive": True,
        "modelAttested": False,
        "executionClaimsAttested": False,
        "moveSourceClaims": {
            name: {"modelPlan": MOVES_PER_SEAT_PER_MATCH, "fallback": 0, "scripted": 0, "other": 0}
            for name in seats
        },
    }


def _build_plan_source(plan):
    entry = {
        "entrant": plan["name"],
        "artifactSha256": plan["artifactSha256"],
        "planSha256": plan["planSha256"],
        "oxRunId": plan["oxRunId"],
        "oxReceiptSha256": plan["oxReceiptSha256"],
        "executionClaim": EXECUTION_CLAIM,
        "modelAttested": False,
        "executionClaimsAttested": False,
    }
    entry.update(plan["source"])
    return entry


def _assert_no_paths(rendered, secrets):
    lowered = rendered.lower()
    for secret in secrets:
        base = secret.lower()
        for variant in (base, base.replace("\\", "\\\\"), base.replace("\\", "/")):
            if variant and variant in lowered:
                raise ProofBlocked("path_in_summary")


def execute(args):
    deadline = _Deadline(DEADLINE_SECONDS)
    out_root = os.path.abspath(args.out)
    summary_target = os.path.abspath(args.json_out)
    out_created = False
    try:
        _require(MIN_TIMEOUT_S <= args.timeout <= MAX_TIMEOUT_S, "timeout_out_of_bounds")
        _require(not os.path.lexists(out_root), "out_root_exists")
        _require(not os.path.lexists(summary_target), "summary_target_exists")

        harness = _load_module("fantasy_plan_harness", HARNESS_PATH)
        deadline.check()
        plan_a = _load_plan(harness, args.plan_a)
        plan_b = _load_plan(harness, args.plan_b)
        _require(plan_a["artifactSha256"] != plan_b["artifactSha256"], "duplicate_artifact")
        _require(plan_a["oxRunId"] != plan_b["oxRunId"], "duplicate_ox_run")
        plans = [plan_a, plan_b]

        league_module = _load_module("run_agentwars_league", LEAGUE_RUNNER_PATH)
        manifests = [
            {
                "name": plan["name"],
                "cmd": [
                    sys.executable,
                    HARNESS_PATH,
                    "--plan",
                    plan["abs_path"],
                    "--name",
                    plan["name"],
                ],
                "env": [],
                "claimed_model": plan["source"]["modelClaim"],
                "execution_claim": EXECUTION_CLAIM,
            }
            for plan in plans
        ]
        config = {
            "league": "model plan proof",
            "description": "Two committed model plans replay-verified across both seat orders.",
            "entrants": manifests,
        }

        os.makedirs(out_root)
        out_created = True
        deadline.check()
        league = league_module.run_league(
            config,
            formats=[GAME],
            seeds=SEED_COUNT,
            start_seed=SEED,
            out_dir=out_root,
            move_timeout_s=args.timeout,
        )
        deadline.check()

        _require(league.get("status") == EXPECTED_STATUS, "status_mismatch")
        _require(
            league.get("truthBoundary") == EXPECTED_TRUTH_BOUNDARY,
            "truth_boundary_mismatch",
        )
        _require(league.get("modelAttested") is False, "league_model_attested")
        _require(league.get("executionClaimsAttested") is False, "league_claims_attested")
        expected_entrants = [
            {
                "name": manifest["name"],
                "claimedModel": manifest["claimed_model"],
                "executionClaim": EXECUTION_CLAIM,
                "manifestDigest": league_module.digest(manifest),
            }
            for manifest in manifests
        ]
        _require(league.get("entrants") == expected_entrants, "league_entrants_mismatch")
        formats = league.get("formats", [])
        _require(len(formats) == 1 and formats[0].get("game") == GAME, "format_rows")
        rows = formats[0].get("matches", [])
        _require(len(rows) == MATCHES_EXPECTED, "match_count")
        _require(all(row.get("seed") == SEED for row in rows), "league_seed")
        _require(all(row.get("verified") is True for row in rows), "league_verified")
        _require(all(row.get("modelAttested") is False for row in rows), "match_model_attested")
        _require(all(row.get("executionClaimsAttested") is False for row in rows), "match_claims_attested")
        _require(all(row.get("winner") is not None for row in rows), "league_winner_missing")
        _require(
            all(not str(row.get("reason", "")).startswith("forfeit") for row in rows),
            "league_forfeit_reason",
        )
        identities = [(row.get("seat0"), row.get("seat1")) for row in rows]
        expected_orders = {
            (plans[0]["name"], plans[1]["name"]),
            (plans[1]["name"], plans[0]["name"]),
        }
        _require(set(identities) == expected_orders, "seat_orders")
        _require(len({row.get("matchId") for row in rows}) == MATCHES_EXPECTED, "duplicate_match_id")

        standings = formats[0].get("standings", [])
        _require(len(standings) == MATCHES_EXPECTED, "standings_rows")
        for row in standings:
            _require(row.get("modelMoveClaims") == MATCHES_EXPECTED * MOVES_PER_SEAT_PER_MATCH, "standings_model_moves")
            _require(row.get("fallbackMoves") == 0, "standings_fallback_moves")
            _require(row.get("scriptedMoves") == 0, "standings_scripted_moves")
            _require(row.get("otherMoves") == 0, "standings_other_moves")

        transcripts = _collect_transcripts(out_root)
        _require(len(transcripts) == MATCHES_EXPECTED, "transcript_file_count")
        rows_by_id = {row["matchId"]: row for row in rows}
        audits = []
        for path in sorted(transcripts):
            stem = os.path.basename(path)[: -len(".jsonl")]
            _require(stem in rows_by_id, "unplanned_transcript")
            audits.append(_audit_transcript(harness, plans, path, rows_by_id[stem]))
            deadline.check()
        _require(
            len({audit["transcriptSha256"] for audit in audits}) == MATCHES_EXPECTED,
            "transcript_hash_distinctness",
        )
        _require(
            sorted(audit["matchId"] for audit in audits) == sorted(rows_by_id),
            "summary_identity_binding",
        )

        doc = {
            "proofSchema": PROOF_SCHEMA,
            "game": GAME,
            "seed": SEED,
            "status": league["status"],
            "truthBoundary": league["truthBoundary"],
            "modelAttested": False,
            "executionClaimsAttested": False,
            "entrants": league["entrants"],
            "planSources": sorted(
                (_build_plan_source(plan) for plan in plans), key=lambda entry: entry["entrant"]
            ),
            "matches": sorted(audits, key=lambda match: (match["seat0"], match["seat1"])),
            "transcripts": {
                "count": len(audits),
                "distinctSha256": MATCHES_EXPECTED,
                "replayVerdicts": ["PASS", "PASS"],
            },
        }
        rendered = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
        _assert_no_paths(
            rendered,
            {
                ROOT,
                out_root,
                summary_target,
                HARNESS_PATH,
                LEAGUE_RUNNER_PATH,
                plan_a["abs_path"],
                plan_b["abs_path"],
            },
        )
        deadline.check()

        parent = os.path.dirname(summary_target)
        os.makedirs(parent, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", newline="\n", dir=parent, delete=False
        )
        tmp_name = handle.name
        try:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            handle.close()
        try:
            os.replace(tmp_name, summary_target)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
        return doc
    except BaseException:
        if out_created:
            shutil.rmtree(out_root, ignore_errors=True)
        raise
    finally:
        deadline.cancel()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Prove two committed model plans drove replay-verified fantasy play."
    )
    parser.add_argument("--plan-a", default=DEFAULT_PLAN_A)
    parser.add_argument("--plan-b", default=DEFAULT_PLAN_B)
    parser.add_argument("--out", required=True)
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args(argv)
    try:
        doc = execute(args)
    except ProofBlocked as error:
        sys.stderr.write(f"error: {error.code}\n")
        return 2
    except KeyboardInterrupt:
        sys.stderr.write("error: interrupted\n")
        return 130
    except OSError:
        sys.stderr.write("error: filesystem_failure\n")
        return 2
    except Exception:
        sys.stderr.write("error: internal_failure\n")
        return 2
    print(json.dumps(doc, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
