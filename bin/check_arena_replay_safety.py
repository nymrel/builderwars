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
import unittest.mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.dont_write_bytecode = True

from arena import transcript as transcript_module  # noqa: E402
from arena.canonical import GENESIS, chain, digest  # noqa: E402
from arena.games import load as load_game  # noqa: E402
from arena.integrity import engine_digest, engine_files  # noqa: E402
from arena.match import _Sidecar, match_id_for, run_match  # noqa: E402
from arena.replay import verify  # noqa: E402
from arena.sandbox import POLICY, Entrant  # noqa: E402
from arena.scoring import referee_projection, score  # noqa: E402
from arena.transcript import TranscriptWriter, load  # noqa: E402

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
        writer.append("probe", nested)
        nested["nested"]["value"] = 999
        first_snapshot = writer.records
        first_snapshot[0]["body"]["nested"]["value"] = 555
        ok(
            "retained records detach from caller-owned nested values",
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
    ok("malformed empty-body forfeit rejected", report["verdict"] == "FAIL")

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
    ok("conflicting forfeits rejected", report["verdict"] == "FAIL")

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
    ok("fault transcript independently replays PASS", report["verdict"] == "PASS")
    code, out, err = run_child([sys.executable, VERIFY_REPLAY, result["transcript"]], 60)
    ok(
        "standalone replay verifier agrees PASS",
        code == 0 and "VERDICT: PASS" in out,
        (err or out)[-200:],
    )
    ok("diagnostics sidecar created", os.path.isfile(result["diagnostics"]))
    ok(
        "scratch removed",
        not os.path.exists(os.path.join(fault_dir, f".scratch-{result['match_id']}")),
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

    original_loader = proof._load_module

    def refusing_loader(name, path):
        if name == "run_agentwars_league":
            raise proof.ProofBlocked("simulated_league_refusal")
        return original_loader(name, path)

    cleanup_out = os.path.join(tmp, "cleanup-out")
    cleanup_summary = os.path.join(tmp, "cleanup-summary.json")
    proof._load_module = refusing_loader
    try:
        expect_blocked(
            proof,
            proof_namespace(proof, cleanup_out, cleanup_summary),
            "simulated_league_refusal",
        )
    finally:
        proof._load_module = original_loader
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
