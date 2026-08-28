#!/usr/bin/env python3
"""Adversarial self-check: prove the guards fire, not just that they exist.

A verifier that returns PASS on a good transcript has demonstrated nothing. The
question is whether it returns FAIL on a bad one, and this file answers it by
attacking the engine and asserting each attack is caught.

Every check below states what would happen if the guard were absent, so a
future reader can tell a live guard from decoration. Each attack is run against
the real engine — no mocks, no fixtures hand-built to the shape I expected.

    python bin/selfcheck.py

Exit 0 only if every attack is caught.
"""

import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from arena.canonical import GENESIS, chain  # noqa: E402
from arena.games import load as load_game  # noqa: E402
from arena.match import run_match  # noqa: E402
from arena.replay import verify  # noqa: E402
from arena.scoring import NotAProjection, referee_projection, score  # noqa: E402
from arena.transcript import load  # noqa: E402
from entrants.backends import execution_claim_for_backend  # noqa: E402

RESULTS = []


def check(name, ok, expect_if_absent, detail=""):
    RESULTS.append((name, bool(ok), expect_if_absent, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    return ok


def entrant(script, backend="stub:v1", mode=None, name=None):
    cmd = [sys.executable, os.path.join(ROOT, "entrants", script), "--backend", backend]
    if mode:
        cmd += ["--mode", mode]
    return {
        "name": name or os.path.splitext(script)[0].replace("_", "-") + (f"-{mode}" if mode else ""),
        "cmd": cmd,
        "env": [],
        "claimed_model": backend,
        "execution_claim": execution_claim_for_backend(backend),
    }


def rechain(path, mutate):
    """An attacker who understands the format: edit a record, then repair every
    hash after it so the chain is internally consistent again.

    This is the capability the hash chain alone does NOT defeat, which is why
    replay recomputes the game rather than trusting the recorded result.
    """
    records = load(path)
    mutate(records)
    prev = GENESIS
    out = []
    for i, rec in enumerate(records):
        body = {"kind": rec["kind"], "seq": i, "body": rec["body"]}
        h = chain(prev, body)
        line = dict(body)
        line["prev"] = prev
        line["hash"] = h
        out.append(line)
        prev = h
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for line in out:
            fh.write(json.dumps(line, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")


def main():
    work = tempfile.mkdtemp(prefix="arena-selfcheck-")
    try:
        print("\n=== 1. a clean match verifies ===")
        good = run_match(
            game_name="nim", seed=7,
            entrants=[entrant("solver_harness.py"), entrant("naive_harness.py")],
            out_dir=os.path.join(work, "good"),
        )
        r = verify(good["transcript"])
        check("clean transcript verifies", r["verdict"] == "PASS",
              "a broken verifier would fail here and every check below is meaningless",
              f"winner=seat{good['winner']} ({good['reason']})")

        print("\n=== 2. determinism: same seed, same entrants, same chain head ===")
        again = run_match(
            game_name="nim", seed=7,
            entrants=[entrant("solver_harness.py"), entrant("naive_harness.py")],
            out_dir=os.path.join(work, "again"),
        )
        same_head = good["chain_head"] == again["chain_head"]
        check("re-run reproduces the chain head exactly", same_head,
              "without it, no third party could confirm a result by re-running it",
              f"{good['chain_head'][:16]}… vs {again['chain_head'][:16]}…")
        with open(good["transcript"], "rb") as a, open(again["transcript"], "rb") as b:
            byte_same = a.read() == b.read()
        check("re-run reproduces the transcript byte for byte", byte_same,
              "a differing byte means something non-deterministic leaked into the record")

        print("\n=== 2b. custom match ids fail before output path construction ===")
        rejected_paths = []
        hostile_ids = (
            "../escape", "C:/absolute", "a/b", "a\\b", "é", "bad\ncontrol", "", "a" * 81,
            "CON", "nul", "PrN", "aux", "COM1", "com9", "LPT1", "lpt9"
        )
        for index, hostile_id in enumerate(hostile_ids):
            rejected_out = os.path.join(work, f"rejected-id-{index}")
            try:
                run_match(
                    game_name="nim", seed=7,
                    entrants=[entrant("solver_harness.py"), entrant("naive_harness.py")],
                    out_dir=rejected_out, match_id=hostile_id,
                )
            except ValueError:
                pass
            else:
                rejected_paths.append(repr(hostile_id))
            if os.path.exists(rejected_out):
                rejected_paths.append(f"created:{hostile_id!r}")
        check("hostile custom ids create no output or scratch path", not rejected_paths,
              "a traversal id could write a transcript outside the requested match directory",
              f"{len(hostile_ids)} rejected forms; failures={rejected_paths or 'none'}")
        custom = run_match(
            game_name="nim", seed=8,
            entrants=[entrant("solver_harness.py"), entrant("naive_harness.py")],
            out_dir=os.path.join(work, "safe-custom-id"), match_id="Safe_match-01",
        )
        check("a bounded safe custom id is retained", custom["match_id"] == "Safe_match-01"
              and os.path.basename(custom["transcript"]) == "Safe_match-01.jsonl",
              "an overbroad guard would make legitimate explicit fixture ids unusable")

        print("\n=== 3. a single altered byte breaks the chain ===")
        tampered = os.path.join(work, "tampered.jsonl")
        shutil.copy(good["transcript"], tampered)
        recs = load(tampered)
        move_idx = next(i for i, x in enumerate(recs) if x["kind"] == "move")
        with open(tampered, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        obj = json.loads(lines[move_idx])
        obj["body"]["move"]["take"] += 1  # change one move, leave hashes alone
        lines[move_idx] = json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n"
        with open(tampered, "w", encoding="utf-8", newline="\n") as fh:
            fh.writelines(lines)
        r = verify(tampered)
        check("edited move is caught", r["verdict"] == "FAIL" and not r["chain_ok"],
              "without the chain, a transcript could be rewritten after the fact",
              r["errors"][0] if r["errors"] else "")

        print("\n=== 4. an attacker who repairs the chain still cannot change the winner ===")
        forged = os.path.join(work, "forged.jsonl")
        shutil.copy(good["transcript"], forged)

        def flip_winner(records):
            for rec in records:
                if rec["kind"] == "result":
                    rec["body"]["winner"] = 1 - rec["body"]["winner"]
                    rec["body"]["points"] = {"0": 0, "1": 1} if rec["body"]["winner"] == 1 else {"0": 1, "1": 0}

        rechain(forged, flip_winner)
        r = verify(forged)
        check("re-chained forgery still fails", r["verdict"] == "FAIL",
              "this is the attack a hash chain alone does not stop; replay recomputation does",
              "chain_ok=%s, result_matches_recomputation=%s" % (r["chain_ok"], r["result_matches_recomputation"]))
        check("the forgery is caught specifically at the result",
              r["chain_ok"] and not r["result_matches_recomputation"],
              "if it were caught only by the chain, a careful forger would get through")

        print("\n=== 5. an illegal move is caught by the referee, not the harness ===")
        cheat = run_match(
            game_name="nim", seed=11,
            entrants=[entrant("cheater_harness.py", mode="illegal"), entrant("solver_harness.py")],
            out_dir=os.path.join(work, "cheat"),
        )
        check("illegal move forfeits", cheat["winner"] == 1 and "illegal_move" in cheat["reason"],
              "an entrant could otherwise play moves the rules do not allow",
              f"reason={cheat['reason']}")
        check("the cheating match still verifies", verify(cheat["transcript"])["verdict"] == "PASS",
              "the record of a forfeit must itself be checkable")

        print("\n=== 6. a competitor's self-report changes nothing ===")
        honest = run_match(
            game_name="nim", seed=23,
            entrants=[entrant("cheater_harness.py", mode="honest", name="c"), entrant("solver_harness.py")],
            out_dir=os.path.join(work, "honest"),
        )
        liar = run_match(
            game_name="nim", seed=23,
            entrants=[entrant("cheater_harness.py", mode="liar", name="c"), entrant("solver_harness.py")],
            out_dir=os.path.join(work, "liar"),
        )
        identical = (
            honest["winner"] == liar["winner"]
            and honest["points"] == liar["points"]
            and honest["reason"] == liar["reason"]
            and honest["moves"] == liar["moves"]
        )
        check("a liar and an honest twin score identically", identical,
              "if a self-report reached the scorer, the liar would win 999 to -999",
              f"both: winner=seat{honest['winner']} points={honest['points']}")
        raw = load(liar["transcript"])
        blob = json.dumps(raw)
        check("the false claim IS in the transcript (recorded, for audit)", "9999" in blob,
              "we record what an entrant said; we just refuse to score it")
        proj = json.dumps(referee_projection(raw))
        check("the false claim is NOT in the scored projection", "9999" not in proj,
              "the exclusion is structural — the value does not exist by the time scoring runs")

        print("\n=== 7. the projection guard is reachable, not dead code ===")
        try:
            score(raw, load_game("nim"))
            guard_fired = False
        except NotAProjection:
            guard_fired = True
        check("scoring raw records raises", guard_fired,
              "a guard that cannot be reached is decoration; this proves the path executes")

        print("\n=== 8. a swapped engine digest is reported, not ignored ===")
        swapped = os.path.join(work, "swapped.jsonl")
        shutil.copy(good["transcript"], swapped)
        rechain(swapped, lambda rs: rs[0]["body"]["engine"].__setitem__("digest", "de" * 32))
        r = verify(swapped)
        check("mismatched engine digest is surfaced", r["engine_digest_match"] is False,
              "a competitor could otherwise referee with edited rules and no one would see it")
        check("mismatched engine digest makes the replay verdict FAIL", r["verdict"] == "FAIL",
              "a foreign referee must never receive a PASS-with-warning verdict")
        check("and it is named in what the result does NOT prove",
              any("engine digests differ" in s for s in r["does_not_prove"]),
              "the caveat has to travel with the result, not sit in a doc")

        print("\n=== 9. the harness is the variable, not the seat ===")
        seats = []
        for seed in (101, 202, 303):
            for order in (0, 1):
                pair = [entrant("solver_harness.py"), entrant("naive_harness.py")]
                if order:
                    pair.reverse()
                m = run_match(game_name="nim", seed=seed, entrants=pair,
                              out_dir=os.path.join(work, f"s{seed}{order}"))
                solver_seat = order  # after the reverse, solver sits in seat `order`
                seats.append((seed, order, m["winner"] == solver_seat, m["reason"]))
        solver_wins = sum(1 for _, _, won, _ in seats)
        check("solver beats naive from both seats, same model behind both",
              solver_wins == len(seats),
              "if it only won from seat 0, the result would be about the seat",
              f"{solver_wins}/{len(seats)} across 3 seeds x 2 seat orders")

        print("\n=== 10. a fault in the referee voids the match instead of crashing ===")
        # Inject a fault into the rules code mid-match. Found by mutation-testing
        # this suite: before the boundary existed, this killed the runner and left
        # a transcript with no ending.
        nim = load_game("nim")
        real_apply = nim.apply

        def exploding_apply(state, move):
            if state["turn"] >= 2:
                raise RuntimeError("injected referee fault")
            return real_apply(state, move)

        nim.apply = exploding_apply
        try:
            faulted = run_match(
                game_name="nim", seed=31,
                entrants=[entrant("solver_harness.py"), entrant("naive_harness.py")],
                out_dir=os.path.join(work, "faulted"),
            )
        finally:
            nim.apply = real_apply

        check("a referee fault voids the match", faulted["reason"] == "engine_error",
              "the runner would crash and the match would end with no record at all",
              f"winner={faulted['winner']} reason={faulted['reason']}")
        check("the void is charged to neither player",
              faulted["winner"] is None and faulted["points"] == {"0": 0, "1": 0},
              "awarding the win to the other seat would let a rules bug decide a contest")
        faulted_records = load(faulted["transcript"])
        check("the faulted transcript still ends with a result record",
              faulted_records[-1]["kind"] == "result",
              "a transcript that just stops is indistinguishable from one still running")
        check("the faulted transcript still verifies",
              verify(faulted["transcript"])["verdict"] == "PASS",
              "even a void match has to be checkable by a third party")

        print("\n=== 11. the verifier never raises, whatever it is fed ===")
        # The verifier is what a third party runs. If it can be made to throw,
        # a crafted transcript becomes a denial-of-verification, and a crash
        # reads as "inconclusive" rather than "FAIL".
        hostile = {}
        hostile["empty"] = ""
        hostile["not_json"] = "this is not a transcript\n"
        hostile["half_a_record"] = '{"kind":"header","seq":0,'
        with open(good["transcript"], encoding="utf-8") as fh:
            good_lines = fh.readlines()
        hostile["truncated"] = "".join(good_lines[:3])
        hostile["header_only"] = good_lines[0]
        moved = load(good["transcript"])
        hostile["move_before_state"] = "".join(
            json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n"
            for r in moved
            if r["kind"] != "state"
        )

        crashed = []
        no_verdict = []
        for label, content in hostile.items():
            path = os.path.join(work, f"hostile-{label}.jsonl")
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(content)
            try:
                rep = verify(path)
                if rep.get("verdict") != "FAIL":
                    no_verdict.append(f"{label}={rep.get('verdict')}")
            except Exception as e:
                crashed.append(f"{label}: {e.__class__.__name__}")

        check("no malformed transcript makes the verifier raise", not crashed,
              "a crafted transcript would crash anyone trying to check a result",
              f"{len(hostile)} hostile inputs, crashes: {crashed or 'none'}")
        check("every malformed transcript returns FAIL, never PASS", not no_verdict,
              "an unparseable transcript that returns anything but FAIL is worse than a crash",
              f"non-FAIL verdicts: {no_verdict or 'none'}")

    finally:
        shutil.rmtree(work, ignore_errors=True)

    passed = sum(1 for _, ok, _, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"\n{'=' * 62}\n{passed}/{total} checks passed")
    if passed != total:
        print("\nFAILED:")
        for name, ok, expect, _ in RESULTS:
            if not ok:
                print(f"  - {name}\n      absent-guard consequence: {expect}")
        return 1
    print("every attack above was caught by the engine.")
    return 0


if __name__ == "__main__":
    # A crash must not read as silence. Without this, a fault inside the engine
    # ends the suite with a traceback and no verdict line — which in a scheduled
    # run is indistinguishable from a pass that nobody looked at.
    try:
        sys.exit(main())
    except Exception:
        import traceback

        traceback.print_exc()
        print(f"\n{'=' * 62}\nSELFCHECK CRASHED before reaching a verdict — treat as FAIL.")
        print(f"{len([r for r in RESULTS if r[1]])} checks had passed before the crash.")
        sys.exit(2)
