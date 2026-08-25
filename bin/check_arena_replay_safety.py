#!/usr/bin/env python3
"""Hostile regression checks for transcript, replay, and match fault safety.

Stdlib-only. Every byte the checker touches lives in one temporary root that is
removed when the run ends. No network, provider, credential, or model access;
the referee-fault scenario mocks the entrant handshake locally.
"""

import argparse
import copy
import faulthandler
import hashlib
import importlib.util
import json
import os
import random
import subprocess
import sys
import tempfile
import time
import unittest.mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.dont_write_bytecode = True

from arena import transcript as transcript_module  # noqa: E402
from arena import match as match_module  # noqa: E402
from arena.canonical import GENESIS, chain, digest  # noqa: E402
from arena.games import load as load_game  # noqa: E402
from arena.integrity import engine_digest, engine_files  # noqa: E402
from arena.match import _Sidecar, match_id_for, run_match  # noqa: E402
from arena.replay import verify  # noqa: E402
from arena.sandbox import POLICY, Entrant, EntrantFailure  # noqa: E402
from arena.scoring import referee_projection, score  # noqa: E402
from arena.transcript import ChainBroken, TranscriptWriter, load  # noqa: E402

PROOF_RUNNER = os.path.join(ROOT, "bin", "run_fantasy_plan_proof.py")
VERIFY_ROOT = os.path.join(ROOT, "verify.py")
VERIFY_REPLAY = os.path.join(ROOT, "bin", "verify_replay.py")
GAME_NAME = "fantasy_redraft"
SEED = 9300
CHECKS = 0
CHILDREN = []


def ok(name, condition, detail=""):
    global CHECKS
    if not condition:
        raise AssertionError(f"{name}: {detail or 'contract violated'}")
    CHECKS += 1
    print(f"  [ok] {name}")


def run_child(argv, timeout_s):
    process = subprocess.Popen(
        argv,
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    CHILDREN.append(process)
    try:
        out, err = process.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        raise AssertionError(f"child hung past deadline: {argv[1:]}") from None
    return process.returncode, out, err


def manifest(name):
    return {
        "name": name,
        "cmd": [sys.executable, "-c", "pass"],
        "env": [],
        "claimed_model": None,
        "execution_claim": "scripted",
    }


def read_bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


def write_raw(path, payload):
    with open(path, "wb") as handle:
        handle.write(payload)


def write_records(path, records):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(
                json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
            )


def rechain(records):
    prev = GENESIS
    out = []
    for position, record in enumerate(records):
        line = {
            "kind": record["kind"],
            "seq": position,
            "body": copy.deepcopy(record["body"]),
        }
        hashed = {"kind": line["kind"], "seq": position, "body": line["body"]}
        line["prev"] = prev
        line["hash"] = chain(prev, hashed)
        out.append(line)
        prev = line["hash"]
    return out


def build_valid_transcript(directory):
    game = load_game(GAME_NAME)
    state = game.setup(random.Random(SEED))
    path = os.path.join(directory, "valid.jsonl")
    with TranscriptWriter(path) as tw:
        tw.append(
            "header",
            {
                "protocol": "arena/1",
                "match_id": "replaysafety01",
                "game": {"name": game.NAME, "version": game.VERSION, "summary": game.SUMMARY},
                "seed": SEED,
                "engine": {"digest": engine_digest(), "files": engine_files()},
                "entrants": [
                    {
                        "seat": seat,
                        "name": f"Seat {seat}",
                        "manifest_digest": digest(manifest(f"Seat {seat}")),
                        "script": {"sha256": digest("entrant-script"), "bytes": 14},
                        "declared_env": [],
                        "claimed_model": None,
                        "execution_claim": "scripted",
                    }
                    for seat in (0, 1)
                ],
                "sandbox_policy": POLICY,
                "attestation": {"model_attested": False, "execution_claims_attested": False},
                "limits": {"move_timeout_ms": 15000},
            },
        )
        tw.append("state", {"state": state, "state_digest": digest(state), "turn": 0})
        scored = score(referee_projection(tw.records), game)
        tw.append(
            "result",
            {
                "winner": scored["winner"],
                "reason": scored["reason"],
                "moves": scored["moves"],
                "points": scored["points"],
                "decisive": scored["decisive"],
                "seats": {"0": "Seat 0", "1": "Seat 1"},
                "scored_from": "referee_state_only",
                "self_report_excluded": True,
            },
        )
    return path


def check_sentinel_refusals(tmp):
    print("exclusive creation refuses existing entries byte-for-byte")
    payload = b'{"kind":"sentinel","bytes":"do-not-touch"}\n'
    transcript_sentinel = os.path.join(tmp, "occupied.jsonl")
    write_raw(transcript_sentinel, payload)
    try:
        TranscriptWriter(transcript_sentinel)
        raise AssertionError("existing transcript was opened for truncate")
    except FileExistsError:
        pass
    ok("transcript sentinel refused untouched", read_bytes(transcript_sentinel) == payload)

    sidecar_sentinel = os.path.join(tmp, "occupied.diagnostics.jsonl")
    write_raw(sidecar_sentinel, payload)
    try:
        _Sidecar(sidecar_sentinel)
        raise AssertionError("existing sidecar was opened for truncate")
    except FileExistsError:
        pass
    ok("sidecar sentinel refused untouched", read_bytes(sidecar_sentinel) == payload)

    match_dir = os.path.join(tmp, "occupied-match")
    os.makedirs(match_dir)
    pair = [manifest("Occupied Zero"), manifest("Occupied One")]
    match_id = match_id_for(GAME_NAME, SEED, [row["name"] for row in pair])
    occupied_sidecar = os.path.join(match_dir, f"{match_id}.diagnostics.jsonl")
    write_raw(occupied_sidecar, payload)
    try:
        run_match(
            game_name=GAME_NAME,
            seed=SEED,
            entrants=pair,
            out_dir=match_dir,
            move_timeout_s=5.0,
        )
        raise AssertionError("sidecar collision created a partial match")
    except FileExistsError:
        pass
    ok("match-level sidecar collision preserves sentinel", read_bytes(occupied_sidecar) == payload)
    ok(
        "match-level sidecar collision creates no transcript counterpart",
        not os.path.lexists(os.path.join(match_dir, f"{match_id}.jsonl")),
    )

    scratch_match_dir = os.path.join(tmp, "occupied-scratch-match")
    scratch_pair = [manifest("Scratch Zero"), manifest("Scratch One")]
    scratch_mid = match_id_for(GAME_NAME, SEED, [row["name"] for row in scratch_pair])
    occupied_scratch = os.path.join(scratch_match_dir, f".scratch-{scratch_mid}")
    os.makedirs(occupied_scratch)
    scratch_marker = os.path.join(occupied_scratch, "sentinel.bin")
    write_raw(scratch_marker, payload)
    try:
        run_match(
            game_name=GAME_NAME,
            seed=SEED,
            entrants=scratch_pair,
            out_dir=scratch_match_dir,
            move_timeout_s=5.0,
        )
        raise AssertionError("existing scratch entry was reused")
    except FileExistsError:
        pass
    ok("match-level scratch collision preserves sentinel", read_bytes(scratch_marker) == payload)
    ok(
        "scratch collision creates no transcript or sidecar",
        not os.path.lexists(os.path.join(scratch_match_dir, f"{scratch_mid}.jsonl"))
        and not os.path.lexists(
            os.path.join(scratch_match_dir, f"{scratch_mid}.diagnostics.jsonl")
        ),
    )

    race_target = os.path.join(tmp, "race.jsonl")
    real_open = os.open

    def racing_open(path, flags, mode=0o666):
        if flags & os.O_CREAT and flags & os.O_EXCL:
            winner = real_open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
            try:
                os.write(winner, b"winner-writes-first")
            finally:
                os.close(winner)
            raise FileExistsError(17, "loser arrives second")
        return real_open(path, flags, mode)

    with unittest.mock.patch.object(transcript_module.os, "open", racing_open):
        try:
            TranscriptWriter(race_target)
            raise AssertionError("creation race loser replaced the winner's file")
        except FileExistsError:
            pass
    ok(
        "creation race loser never touches the winner's bytes",
        read_bytes(race_target) == b"winner-writes-first",
    )

    detached_path = os.path.join(tmp, "retained-records.jsonl")
    nested = {"nested": {"value": 1}}
    with TranscriptWriter(detached_path) as writer:
        returned = writer.append("probe", nested)
        nested["nested"]["value"] = 999
        returned["body"]["nested"]["value"] = 777
        first_snapshot = writer.records
        first_snapshot[0]["body"]["nested"]["value"] = 555
        ok(
            "retained records detach from caller-owned nested values",
            writer.records[0]["body"]["nested"]["value"] == 1,
        )
        ok(
            "append return value detaches from retained records",
            writer.records[0]["body"]["nested"]["value"] == 1,
        )
        ok(
            "retained-record snapshots detach from their consumers",
            writer.records[0]["body"]["nested"]["value"] == 1,
        )


def check_hostile_transcripts(tmp, valid_path):
    print("hostile transcripts fail closed without tracebacks")
    base = load(valid_path)
    ok("baseline transcript verifies PASS", verify(valid_path)["verdict"] == "PASS")

    scalar = os.path.join(tmp, "scalar.jsonl")
    write_raw(scalar, b"5\n")
    report = verify(scalar)
    ok(
        "scalar transcript returns controlled FAIL",
        report["verdict"] == "FAIL" and report["chain_ok"] is False,
    )

    array = os.path.join(tmp, "array.jsonl")
    write_raw(array, b"[1,2]\n")
    ok("array transcript returns controlled FAIL", verify(array)["verdict"] == "FAIL")

    oversized = os.path.join(tmp, "oversized_integer.jsonl")
    write_raw(oversized, ('{"seq":' + ('9' * 5000) + '}\n').encode("ascii"))
    try:
        load(oversized)
        raise AssertionError("oversized integer escaped ChainBroken normalization")
    except ChainBroken:
        pass
    ok("oversized JSON integer normalizes to ChainBroken", True)
    ok("oversized JSON integer returns controlled FAIL", verify(oversized)["verdict"] == "FAIL")

    extra = rechain(base)
    extra[1]["extra"] = "unhashed-smuggled"
    extra_path = os.path.join(tmp, "extra_key.jsonl")
    write_records(extra_path, extra)
    report = verify(extra_path)
    ok(
        "extra unhashed key rejected",
        report["verdict"] == "FAIL" and report["chain_ok"] is False,
    )

    gossip = rechain(
        base[:2]
        + [{"kind": "gossip", "seq": 99, "body": {"note": "x"}, "prev": "", "hash": ""}]
        + base[2:]
    )
    gossip_path = os.path.join(tmp, "unknown_kind.jsonl")
    write_records(gossip_path, gossip)
    report = verify(gossip_path)
    ok(
        "unknown record kind rejected on a valid chain",
        report["verdict"] == "FAIL" and report["chain_ok"] is True,
    )

    malformed = rechain(
        base[:1]
        + [{"kind": "forfeit", "seq": 99, "body": {}, "prev": "", "hash": ""}]
        + base[1:]
    )
    malformed_path = os.path.join(tmp, "malformed_forfeit.jsonl")
    write_records(malformed_path, malformed)
    report = verify(malformed_path)
    ok(
        "malformed empty-body forfeit rejected by forfeit semantics",
        report["verdict"] == "FAIL"
        and report["chain_ok"] is True
        and report["forfeit_evidence_replayable"] is False,
    )

    conflicting = rechain(
        base[:1]
        + [
            {
                "kind": "forfeit",
                "seq": 99,
                "body": {"player": seat, "reason": "timeout", "phase": "handshake"},
                "prev": "",
                "hash": "",
            }
            for seat in (0, 1)
        ]
        + base[1:]
    )
    conflicting_path = os.path.join(tmp, "conflicting_forfeits.jsonl")
    write_records(conflicting_path, conflicting)
    report = verify(conflicting_path)
    ok(
        "conflicting forfeits rejected by forfeit semantics",
        report["verdict"] == "FAIL"
        and report["chain_ok"] is True
        and report["forfeit_evidence_replayable"] is False,
    )

    foreign = rechain(base)
    header_body = copy.deepcopy(foreign[0]["body"])
    header_body["engine"]["digest"] = "0" * 64
    foreign[0]["body"] = header_body
    foreign = rechain(foreign)
    foreign_path = os.path.join(tmp, "foreign_engine.jsonl")
    write_records(foreign_path, foreign)
    report = verify(foreign_path)
    ok(
        "correctly rechained foreign engine digest fails",
        report["verdict"] == "FAIL"
        and report["chain_ok"] is True
        and report["engine_digest_match"] is False,
    )
    for verifier in (VERIFY_ROOT, VERIFY_REPLAY):
        code, out, err = run_child([sys.executable, verifier, foreign_path], 60)
        ok(
            f"{os.path.basename(verifier)} fails closed on a foreign engine",
            code != 0 and "VERDICT: FAIL" in (out + err),
            (err or out)[-200:],
        )

    bool_points = copy.deepcopy(base)
    bool_points[-1]["body"]["points"]["0"] = False
    bool_points = rechain(bool_points)
    bool_points_path = os.path.join(tmp, "boolean_result_points.jsonl")
    write_records(bool_points_path, bool_points)
    report = verify(bool_points_path)
    ok(
        "boolean score values cannot impersonate integer zero",
        report["verdict"] == "FAIL"
        and report["chain_ok"] is True
        and report["result_matches_recomputation"] is False,
    )

    for label, hostile_attestation in (
        ("null", None),
        ("scalar", "not-an-object"),
        ("array", []),
    ):
        hostile = copy.deepcopy(base)
        hostile[0]["body"]["attestation"] = hostile_attestation
        hostile = rechain(hostile)
        hostile_path = os.path.join(tmp, f"attestation_{label}.jsonl")
        write_records(hostile_path, hostile)
        report = verify(hostile_path)
        ok(
            f"{label} attestation returns controlled FAIL",
            report["verdict"] == "FAIL"
            and report["chain_ok"] is True
            and report["attestation_ok"] is False,
        )

    bool_seats = copy.deepcopy(base)
    bool_seats[0]["body"]["entrants"][0]["seat"] = False
    bool_seats[0]["body"]["entrants"][1]["seat"] = True
    bool_seats = rechain(bool_seats)
    bool_seats_path = os.path.join(tmp, "boolean_seats.jsonl")
    write_records(bool_seats_path, bool_seats)
    report = verify(bool_seats_path)
    ok(
        "boolean seats cannot impersonate integer seats",
        report["verdict"] == "FAIL" and report.get("identity_status") == "invalid",
    )

    state_mismatch = copy.deepcopy(base)
    state_record = next(record for record in state_mismatch if record["kind"] == "state")
    state_record["body"]["state"]["turn"] = 999
    state_mismatch = rechain(state_mismatch)
    state_mismatch_path = os.path.join(tmp, "state_body_digest_mismatch.jsonl")
    write_records(state_mismatch_path, state_mismatch)
    report = verify(state_mismatch_path)
    ok(
        "recorded state bytes cannot diverge from their committed digest",
        report["verdict"] == "FAIL" and report["states_ok"] is False,
    )

    timeout_result = copy.deepcopy(base[-1])
    timeout_result["body"].update(
        {
            "winner": 0,
            "reason": "forfeit:timeout",
            "moves": 0,
            "points": {"0": 1, "1": 0},
            "decisive": True,
        }
    )
    forged_timeout = rechain(
        base[:-1]
        + [
            {
                "kind": "forfeit",
                "seq": 99,
                "body": {
                    "player": 1,
                    "reason": "timeout",
                    "detail": "no response within 5s",
                    "phase": "move",
                    "turn": 0,
                },
                "prev": "",
                "hash": "",
            },
            timeout_result,
        ]
    )
    forged_timeout_path = os.path.join(tmp, "forged_timeout_forfeit.jsonl")
    write_records(forged_timeout_path, forged_timeout)
    report = verify(forged_timeout_path)
    ok(
        "correctly re-chained runtime forfeit cannot self-award a competitive PASS",
        report["verdict"] == "FAIL"
        and report["chain_ok"] is True
        and report["result_matches_recomputation"] is True
        and report["forfeit_evidence_replayable"] is False
        and report["forfeit_evidence_class"] == "runtime_observation_unattested",
    )

    aborted = rechain(
        base[:-1]
        + [
            {
                "kind": "abort",
                "seq": 99,
                "body": {"reason": "move_bound_exceeded", "bound": 1},
                "prev": "",
                "hash": "",
            }
        ]
        + base[-1:]
    )
    aborted_path = os.path.join(tmp, "aborted.jsonl")
    write_records(aborted_path, aborted)
    report = verify(aborted_path)
    ok(
        "abort record blocks replay PASS",
        report["verdict"] == "FAIL" and report["abort_free"] is False,
    )

    malformed_error_result = copy.deepcopy(base[-1])
    malformed_error_result["body"].update(
        {
            "winner": None,
            "reason": "engine_error",
            "moves": 0,
            "points": {"0": 0, "1": 0},
            "decisive": False,
        }
    )
    malformed_error = rechain(
        base[:-1]
        + [
            {
                "kind": "engine_error",
                "seq": 99,
                "body": {"detail": "synthetic"},
                "prev": "",
                "hash": "",
            },
            malformed_error_result,
        ]
    )
    malformed_error_path = os.path.join(tmp, "malformed_engine_error.jsonl")
    write_records(malformed_error_path, malformed_error)
    report = verify(malformed_error_path)
    ok(
        "malformed engine error cannot self-bless a void",
        report["verdict"] == "FAIL" and report["engine_error_integrity"] is False,
    )


def check_engine_fault_void(tmp):
    print("referee-side handshake fault becomes a replayable void")
    fault_dir = os.path.join(tmp, "fault")
    marker = "zz9-private-marker"
    with unittest.mock.patch.object(
        Entrant, "start", side_effect=OSError(f"hidden path under {fault_dir} [{marker}]")
    ):
        result = run_match(
            game_name=GAME_NAME,
            seed=SEED,
            entrants=[manifest("Fault Zero"), manifest("Fault One")],
            out_dir=fault_dir,
            move_timeout_s=5.0,
        )
    ok(
        "engine fault returns a voided non-decisive match",
        result["winner"] is None
        and result["reason"] == "engine_error"
        and result["decisive"] is False,
    )
    raw = read_bytes(result["transcript"]).decode("utf-8", errors="replace")
    ok(
        "published records expose only the bounded class, no internals",
        marker not in raw
        and fault_dir not in raw
        and "No such file" not in raw
        and "OSError" in raw,
    )
    report = verify(result["transcript"])
    ok(
        "fault transcript independently replays only as a valid void",
        report["verdict"] == "PASS"
        and report["engine_error_integrity"] is True
        and report["abort_free"] is True
        and report["recomputed"]["winner"] is None
        and report["recomputed"]["reason"] == "engine_error"
        and report["recomputed"]["decisive"] is False,
    )
    code, out, err = run_child([sys.executable, VERIFY_REPLAY, result["transcript"]], 60)
    ok(
        "standalone replay verifier agrees PASS",
        code == 0 and "VERDICT: PASS" in out,
        (err or out)[-200:],
    )
    ok("diagnostics sidecar created", os.path.isfile(result["diagnostics"]))
    with open(result["diagnostics"], "r", encoding="utf-8") as handle:
        diagnostics_notice = json.loads(handle.readline())
    ok(
        "diagnostics sidecar is explicitly non-authoritative and private",
        diagnostics_notice.get("authoritative") is False
        and "diagnostics only" in diagnostics_notice.get("note", ""),
    )
    ok(
        "scratch removed",
        not os.path.exists(os.path.join(fault_dir, f".scratch-{result['match_id']}")),
    )


def check_explicit_environment_custody(tmp):
    print("manifest names never authorize ambient environment reads")
    env_name = "AGENTWARS_SYNTHETIC_TOKEN"
    declared = manifest("Env Declared")
    declared["env"] = [env_name]
    ambient_value = "synthetic-ambient-must-not-pass"
    explicit_value = "synthetic-explicit-value"

    with unittest.mock.patch.dict(os.environ, {env_name: ambient_value}, clear=False):
        try:
            Entrant(declared, os.path.join(tmp, "env-direct"))
            raise AssertionError("declared name inherited an ambient value")
        except ValueError:
            pass
        entrant = Entrant(
            declared,
            os.path.join(tmp, "env-explicit"),
            provisioned_env={env_name: explicit_value},
        )
        child_env = entrant._child_env()
    ok(
        "ambient value is never inherited by declaration alone",
        child_env.get(env_name) == explicit_value and ambient_value not in child_env.values(),
    )

    missing_out = os.path.join(tmp, "env-missing-match")
    try:
        run_match(
            game_name=GAME_NAME,
            seed=SEED,
            entrants=[declared, manifest("Env Plain")],
            out_dir=missing_out,
            move_timeout_s=5.0,
        )
        raise AssertionError("missing explicit per-seat environment was accepted")
    except ValueError:
        pass
    ok(
        "missing explicit provisioning refuses before output creation",
        not os.path.lexists(missing_out),
    )

    extra_out = os.path.join(tmp, "env-extra-match")
    try:
        run_match(
            game_name=GAME_NAME,
            seed=SEED,
            entrants=[declared, manifest("Env Other")],
            out_dir=extra_out,
            move_timeout_s=5.0,
            provisioned_envs=[
                {env_name: explicit_value, "AGENTWARS_UNDECLARED": "synthetic"},
                {},
            ],
        )
        raise AssertionError("undeclared explicit environment value was accepted")
    except ValueError:
        pass
    ok(
        "extra provisioned names refuse before output creation",
        not os.path.lexists(extra_out),
    )


def check_teardown_fault_isolation(tmp):
    print("teardown faults cannot skip entrant or scratch cleanup")
    out_dir = os.path.join(tmp, "teardown-fault")
    pair = [manifest("Cleanup Zero"), manifest("Cleanup One")]
    mid = match_id_for(GAME_NAME, SEED, [row["name"] for row in pair])
    scratch = os.path.join(out_dir, f".scratch-{mid}")
    close_attempts = []
    final_write_attempts = []
    original_close = Entrant.close
    original_write = _Sidecar.write

    def tracked_close(entrant, *args, **kwargs):
        close_attempts.append(entrant.name)
        return original_close(entrant, *args, **kwargs)

    def failing_final_write(sidecar, kind, **fields):
        if kind == "stderr_final":
            final_write_attempts.append(fields.get("entrant"))
            raise OSError("synthetic diagnostics close-path fault")
        return original_write(sidecar, kind, **fields)

    raised = False
    with unittest.mock.patch.object(Entrant, "start", side_effect=OSError("synthetic")), \
            unittest.mock.patch.object(Entrant, "close", tracked_close), \
            unittest.mock.patch.object(_Sidecar, "write", failing_final_write):
        try:
            run_match(
                game_name=GAME_NAME,
                seed=SEED,
                entrants=pair,
                out_dir=out_dir,
                move_timeout_s=5.0,
            )
        except OSError:
            raised = True
    ok("cleanup failure is surfaced after all attempts", raised)
    ok(
        "both entrants close before diagnostics can fail",
        close_attempts == ["Cleanup Zero", "Cleanup One"]
        and final_write_attempts == ["Cleanup Zero", "Cleanup One"],
    )
    ok("scratch removal still runs after cleanup faults", not os.path.lexists(scratch))


def check_sandbox_lifecycle(tmp):
    print("sandbox I/O limits and lifecycle deadlines are enforced mid-stream")

    oversized_manifest = manifest("Oversized Stdout")
    oversized_manifest["cmd"] = [
        sys.executable,
        "-c",
        "import os,time; os.write(1,b'A'*262144); time.sleep(30)",
    ]
    oversized = Entrant(
        oversized_manifest,
        os.path.join(tmp, "sandbox-oversized"),
        move_timeout_s=1.0,
        max_line_bytes=1024,
        max_total_bytes=8192,
        max_stderr_bytes=1024,
    )
    oversized_failure = None
    oversized_proc = None
    try:
        oversized.start()
        oversized_proc = oversized._proc
        oversized.recv(timeout_s=1.0)
    except EntrantFailure as error:
        oversized_failure = error
    finally:
        oversized.close(grace_s=0.5)
    ok(
        "unterminated stdout is rejected before unbounded buffering",
        oversized_failure is not None
        and oversized_failure.reason == "protocol_violation"
        and oversized._bytes_seen <= 1025,
    )
    ok("oversized-output entrant is reaped", oversized_proc.poll() is not None)

    stderr_manifest = manifest("Stderr Flood")
    stderr_manifest["cmd"] = [
        sys.executable,
        "-c",
        (
            "import os,time; "
            "os.write(2,b'E'*262144); "
            "os.write(1,b'{\"type\":\"ready\"}\\n'); "
            "time.sleep(0.2)"
        ),
    ]
    stderr_entrant = Entrant(
        stderr_manifest,
        os.path.join(tmp, "sandbox-stderr"),
        move_timeout_s=2.0,
        max_stderr_bytes=1024,
    )
    stderr_entrant.start()
    stderr_proc = stderr_entrant._proc
    stderr_reply = stderr_entrant.recv(timeout_s=2.0)
    stderr_entrant.close(grace_s=0.5)
    ok(
        "stderr is continuously drained while retained bytes stay capped",
        stderr_reply == {"type": "ready"}
        and len(stderr_entrant._stderr_buf) == 1024
        and stderr_proc.poll() is not None,
    )

    blocked_manifest = manifest("Blocked Stdin")
    blocked_manifest["cmd"] = [sys.executable, "-c", "import time; time.sleep(30)"]
    blocked = Entrant(
        blocked_manifest,
        os.path.join(tmp, "sandbox-blocked-stdin"),
        move_timeout_s=0.2,
    )
    blocked.start()
    blocked_proc = blocked._proc
    reentry_refused = False
    try:
        blocked.start()
    except RuntimeError:
        reentry_refused = True
    started = time.monotonic()
    blocked_failure = None
    try:
        blocked.send({"blob": "x" * (8 * 1024 * 1024)}, timeout_s=0.2)
    except EntrantFailure as error:
        blocked_failure = error
    finally:
        blocked.close(grace_s=0.5)
    elapsed = time.monotonic() - started
    ok("entrant process object rejects a second start", reentry_refused)
    ok(
        "non-draining stdin is killed at the bounded write deadline",
        blocked_failure is not None
        and blocked_failure.reason == "timeout"
        and elapsed < 3.0
        and blocked_proc.poll() is not None,
        f"elapsed={elapsed:.3f}s reason={getattr(blocked_failure, 'reason', None)}",
    )

    rejected_timeouts = 0
    for bad_timeout in (True, 0, float("nan"), float("inf"), 3600.1):
        try:
            Entrant(manifest("Bad Timeout"), os.path.join(tmp, "bad-timeout"), bad_timeout)
        except ValueError:
            rejected_timeouts += 1
    ok(
        "non-finite, boolean, zero, and excessive timeouts are rejected",
        rejected_timeouts == 5,
    )


def check_match_tail_faults(tmp):
    print("match tail faults void safely or remove incomplete owned outputs")

    script = os.path.join(ROOT, "entrants", "fantasy_gm_harness.py")
    playable = [
        {
            "name": "Tail Zero",
            "cmd": [sys.executable, script, "--name", "Tail Zero", "--strategy", "win-now"],
            "env": [],
            "claimed_model": "scripted-baseline:v1",
            "execution_claim": "scripted",
        },
        {
            "name": "Tail One",
            "cmd": [sys.executable, script, "--name", "Tail One", "--strategy", "long-game"],
            "env": [],
            "claimed_model": "scripted-baseline:v1",
            "execution_claim": "scripted",
        },
    ]
    scoring_out = os.path.join(tmp, "score-tail-fault")
    with unittest.mock.patch.object(
        match_module, "score", side_effect=RuntimeError("synthetic score fault")
    ):
        score_fault = run_match(
            game_name=GAME_NAME,
            seed=SEED + 7,
            entrants=playable,
            out_dir=scoring_out,
            move_timeout_s=5.0,
        )
    score_records = load(score_fault["transcript"])
    ok(
        "scoring fault becomes a durable zero-point void",
        score_fault["winner"] is None
        and score_fault["reason"] == "engine_error"
        and score_records[-2]["kind"] == "engine_error"
        and score_records[-1]["kind"] == "result"
        and verify(score_fault["transcript"])["verdict"] == "PASS",
    )

    malformed_out = os.path.join(tmp, "malformed-reply")
    with unittest.mock.patch.object(Entrant, "start", return_value=None), \
            unittest.mock.patch.object(Entrant, "ask", return_value=[]):
        malformed = run_match(
            game_name=GAME_NAME,
            seed=SEED + 8,
            entrants=[manifest("Malformed Zero"), manifest("Malformed One")],
            out_dir=malformed_out,
            move_timeout_s=5.0,
        )
    ok(
        "non-object entrant reply is charged as a protocol forfeit, not referee fault",
        malformed["winner"] == 1 and malformed["reason"] == "forfeit:malformed_message",
    )

    failed_out = os.path.join(tmp, "result-append-fault")
    failed_pair = [manifest("Append Zero"), manifest("Append One")]
    failed_mid = match_id_for(GAME_NAME, SEED + 9, [row["name"] for row in failed_pair])
    real_append = TranscriptWriter.append

    def fail_after_result_append(writer, kind, body):
        record = real_append(writer, kind, body)
        if kind == "result":
            raise OSError("synthetic durable-tail failure")
        return record

    append_failed = False
    with unittest.mock.patch.object(Entrant, "start", side_effect=OSError("synthetic start fault")), \
            unittest.mock.patch.object(TranscriptWriter, "append", fail_after_result_append):
        try:
            run_match(
                game_name=GAME_NAME,
                seed=SEED + 9,
                entrants=failed_pair,
                out_dir=failed_out,
                move_timeout_s=5.0,
            )
        except OSError:
            append_failed = True
    ok("result append failure propagates", append_failed)
    ok(
        "failed result commit leaves no half transcript, sidecar, or scratch collision",
        not os.path.lexists(os.path.join(failed_out, f"{failed_mid}.jsonl"))
        and not os.path.lexists(os.path.join(failed_out, f"{failed_mid}.diagnostics.jsonl"))
        and not os.path.lexists(os.path.join(failed_out, f".scratch-{failed_mid}")),
    )


def check_proof_pipeline(tmp):
    print("genuine committed two-plan proof stays green under both verifiers")
    proof_out = os.path.join(tmp, "proof-out")
    summary_path = os.path.join(tmp, "proof-summary.json")
    code, out, err = run_child(
        [sys.executable, PROOF_RUNNER, "--out", proof_out, "--json-out", summary_path],
        300,
    )
    ok("proof runner exits clean", code == 0, (err or out)[-400:])
    with open(summary_path, "r", encoding="utf-8") as handle:
        doc = json.load(handle)
    matches = doc["matches"]
    ok("exactly two audited matches", len(matches) == 2)
    ok(
        "two distinct transcript digests, both PASS",
        len({row["transcriptSha256"] for row in matches}) == 2
        and all(row["replayVerdict"] == "PASS" for row in matches),
    )
    transcripts = []
    for current, _dirs, names in os.walk(proof_out):
        for name in names:
            if name.endswith(".jsonl") and not name.endswith(".diagnostics.jsonl"):
                transcripts.append(os.path.join(current, name))
    ok("exactly two transcripts on disk", len(transcripts) == 2, str(sorted(transcripts)))
    on_disk = {path: hashlib.sha256(read_bytes(path)).hexdigest() for path in transcripts}
    ok(
        "disk digests bind the summary",
        set(on_disk.values()) == {row["transcriptSha256"] for row in matches},
    )
    for path in sorted(on_disk):
        for verifier in (VERIFY_ROOT, VERIFY_REPLAY):
            code, out, err = run_child([sys.executable, verifier, path], 60)
            tag = os.path.basename(path)[:12]
            ok(
                f"{os.path.basename(verifier)} PASS [{tag}]",
                code == 0 and "VERDICT: PASS" in out,
                (err or out)[-200:],
            )

    source = sorted(on_disk)[0]
    forged_result = load(source)
    result_record = next(record for record in forged_result if record["kind"] == "result")
    winner = result_record["body"].get("winner")
    result_record["body"]["winner"] = 1 - winner if winner in (0, 1) else 0
    forged_result = rechain(forged_result)
    forged_result_path = os.path.join(tmp, "proof_forged_result.jsonl")
    write_records(forged_result_path, forged_result)
    report = verify(forged_result_path)
    ok(
        "move-bearing re-chained winner forgery fails at result derivation",
        report["verdict"] == "FAIL"
        and report["chain_ok"] is True
        and report["result_matches_recomputation"] is False,
    )

    duplicate_move = load(source)
    accepted = next(
        record
        for record in duplicate_move
        if record["kind"] == "move" and record["body"].get("legal") is True
    )
    result_position = next(
        index for index, record in enumerate(duplicate_move) if record["kind"] == "result"
    )
    duplicate_move.insert(result_position, copy.deepcopy(accepted))
    duplicate_move = rechain(duplicate_move)
    duplicate_move_path = os.path.join(tmp, "proof_duplicate_move.jsonl")
    write_records(duplicate_move_path, duplicate_move)
    report = verify(duplicate_move_path)
    ok(
        "move-bearing duplicate accepted action fails replay semantics",
        report["verdict"] == "FAIL"
        and report["chain_ok"] is True
        and report["moves_ok"] is False,
    )


def proof_namespace(proof, out, json_out, timeout=15.0):
    return argparse.Namespace(
        plan_a=proof.DEFAULT_PLAN_A,
        plan_b=proof.DEFAULT_PLAN_B,
        out=out,
        json_out=json_out,
        timeout=timeout,
    )


def expect_blocked(proof, namespace, wanted):
    try:
        proof.execute(namespace)
    except proof.ProofBlocked as error:
        ok(f"blocked cleanly: {wanted}", error.code == wanted)
        return
    raise AssertionError(f"wanted {wanted}, proof executed cleanly")


def check_output_collision_and_cleanup(tmp):
    print("output collisions and refusals leave no partial public output")
    spec = importlib.util.spec_from_file_location("proof_under_test", PROOF_RUNNER)
    proof = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(proof)

    collide_out = os.path.join(tmp, "collide-out")
    sentinel = b"occupied-out-root\n"
    write_raw(collide_out, sentinel)
    fresh_summary = os.path.join(tmp, "collide-summary.json")
    expect_blocked(proof, proof_namespace(proof, collide_out, fresh_summary), "out_root_exists")
    ok("out-root sentinel untouched", read_bytes(collide_out) == sentinel)
    ok("no summary written on collision", not os.path.lexists(fresh_summary))

    fresh_out = os.path.join(tmp, "collide-run")
    collide_summary = os.path.join(tmp, "occupied-summary.json")
    write_raw(collide_summary, sentinel)
    expect_blocked(
        proof, proof_namespace(proof, fresh_out, collide_summary), "summary_target_exists"
    )
    ok("no out-root created on summary collision", not os.path.lexists(fresh_out))
    ok("summary sentinel untouched", read_bytes(collide_summary) == sentinel)

    for hostile_timeout in (0.5, 33.0):
        expect_blocked(
            proof,
            proof_namespace(
                proof,
                os.path.join(tmp, "timeout-out"),
                os.path.join(tmp, "timeout-summary.json"),
                timeout=hostile_timeout,
            ),
            "timeout_out_of_bounds",
        )
    ok(
        "out-of-bounds timeouts create nothing",
        not os.path.lexists(os.path.join(tmp, "timeout-out"))
        and not os.path.lexists(os.path.join(tmp, "timeout-summary.json")),
    )

    with open(proof.DEFAULT_PLAN_A, "r", encoding="utf-8") as handle:
        valid_source = json.load(handle)["source"]
    validated_source = proof._validated_public_source(valid_source)
    ok(
        "public source fields are strictly typed before projection",
        validated_source["runId"] == valid_source["runId"]
        and validated_source["maxTokens"] == 131072,
    )
    hostile_source = dict(valid_source)
    hostile_source["modelClaim"] = r"C:\synthetic-private\model"
    try:
        proof._validated_public_source(hostile_source)
        raise AssertionError("path-shaped model claim entered public summary")
    except proof.ProofBlocked as error:
        ok("path-shaped public source value is rejected", error.code == "model_claim_type")

    slash_path_source = dict(valid_source)
    slash_path_source["modelClaim"] = "C:/Users/synthetic/private/model"
    try:
        proof._validated_public_source(slash_path_source)
        raise AssertionError("forward-slash drive path entered public summary")
    except proof.ProofBlocked as error:
        ok("forward-slash drive path is rejected", error.code == "model_claim_type")

    ok(
        "model-plan source note requires an exact token boundary",
        proof._is_model_plan_note("source=model_plan;artifact_sha256=abc")
        and not proof._is_model_plan_note("source=model_plan_anything"),
    )

    mixed_rendered = r'{"leak":"C:\\/synthetic\\private/proof"}'
    try:
        proof._assert_no_paths(mixed_rendered, {r"C:\synthetic/private\proof"})
        raise AssertionError("mixed-separator path escaped summary hygiene")
    except proof.ProofBlocked as error:
        ok("mixed-separator JSON path is detected", error.code == "path_in_summary")

    original_loader = proof._load_module
    cleanup_out = os.path.join(tmp, "cleanup-out")
    cleanup_summary = os.path.join(tmp, "cleanup-summary.json")
    post_creation_observed = []

    def refusing_loader(name, path):
        module = original_loader(name, path)
        if name == "run_agentwars_league":
            def refusing_run_league(*_args, **_kwargs):
                post_creation_observed.append(os.path.isdir(cleanup_out))
                raise proof.ProofBlocked("simulated_league_refusal")

            module.run_league = refusing_run_league
        return module

    proof._load_module = refusing_loader
    try:
        expect_blocked(
            proof,
            proof_namespace(proof, cleanup_out, cleanup_summary),
            "simulated_league_refusal",
        )
    finally:
        proof._load_module = original_loader
    ok("cleanup refusal occurs after output-root creation", post_creation_observed == [True])
    ok(
        "failed run removes its own out-root and writes no summary",
        not os.path.lexists(cleanup_out) and not os.path.lexists(cleanup_summary),
    )

    code, out, err = run_child(
        [
            sys.executable,
            PROOF_RUNNER,
            "--out",
            collide_out,
            "--json-out",
            os.path.join(tmp, "cli-summary.json"),
            "--timeout",
            "15",
        ],
        60,
    )
    ok(
        "CLI maps collision to a clean refusal code",
        code == 2 and "out_root_exists" in err,
        (err or out)[-160:],
    )
    ok("CLI collision leaves sentinel untouched", read_bytes(collide_out) == sentinel)


def check_no_stale_children():
    print("child process hygiene")
    ok(
        "every checker-owned child has exited",
        bool(CHILDREN) and all(process.poll() is not None for process in CHILDREN),
    )


def main():
    faulthandler.dump_traceback_later(420, exit=True)
    try:
        with tempfile.TemporaryDirectory(prefix="check-arena-replay-safety-") as tmp:
            valid_path = build_valid_transcript(tmp)
            check_sentinel_refusals(tmp)
            check_hostile_transcripts(tmp, valid_path)
            check_engine_fault_void(tmp)
            check_explicit_environment_custody(tmp)
            check_teardown_fault_isolation(tmp)
            check_sandbox_lifecycle(tmp)
            check_match_tail_faults(tmp)
            check_proof_pipeline(tmp)
            check_output_collision_and_cleanup(tmp)
            check_no_stale_children()
        print(f"PASS: {CHECKS} arena replay safety checks")
        return 0
    finally:
        faulthandler.cancel_dump_traceback_later()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as failure:
        print(f"FAIL - {failure}", file=sys.stderr)
        raise SystemExit(1)
