#!/usr/bin/env python3
"""Run a series of matches, verify every one, and report.

Each seed is played twice with the seats swapped, so a win cannot be an artifact
of who moved first. Every transcript is independently replay-verified before it
counts, and any transcript that fails verification is excluded from the tally
and reported loudly — an unverified result is not a result.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arena.match import run_customer_local_match as run_match  # noqa: E402
from arena.replay import verify  # noqa: E402
from entrants.backends import execution_claim_for_backend  # noqa: E402


def manifest(script, backend, backend_timeout=None, customer_local_v1=False):
    cmd = [sys.executable, os.path.abspath(script), "--backend", backend]
    if customer_local_v1:
        cmd.append("--customer-local-v1")
    if backend_timeout:
        cmd += ["--backend-timeout", str(backend_timeout)]
    return {
        "name": os.path.splitext(os.path.basename(script))[0].replace("_", "-"),
        "cmd": cmd,
        "env": [],
        "claimed_model": backend,
        "execution_claim": execution_claim_for_backend(backend),
    }


def main():
    ap = argparse.ArgumentParser(description="Run and verify a match series.")
    ap.add_argument("--game", default="nim")
    ap.add_argument("--a", default="entrants/solver_harness.py")
    ap.add_argument("--b", default="entrants/naive_harness.py")
    ap.add_argument("--backend", default="stub:v1")
    ap.add_argument("--seeds", type=int, default=12)
    ap.add_argument("--start-seed", type=int, default=1000)
    ap.add_argument("--out", default="matches/series")
    ap.add_argument("--timeout", type=float, default=15.0,
                    help="per-move wall clock; raise it for slow local models")
    ap.add_argument("--backend-a", default=None,
                    help="backend for entrant A; defaults to --backend. Set A and B to "
                         "DIFFERENT models to test whether the harness or the model decides.")
    ap.add_argument("--backend-b", default=None,
                    help="backend for entrant B; defaults to --backend")
    ap.add_argument("--backend-timeout", type=float, default=None,
                    help="seconds an entrant waits for its model. Cold local models "
                         "exceed 60s routinely, and a timeout looks like a loss.")
    ap.add_argument(
        "--customer-local-v1",
        action="store_true",
        help="required when any selected backend is non-stub; records local "
             "intent only and is not OS isolation",
    )
    args = ap.parse_args()

    backend_a = args.backend_a or args.backend
    backend_b = args.backend_b or args.backend
    if any(
        not backend.startswith("stub:") for backend in (backend_a, backend_b)
    ) and not args.customer_local_v1:
        ap.error("non-stub backends require --customer-local-v1")
    a = manifest(
        args.a, backend_a, args.backend_timeout, args.customer_local_v1
    )
    b = manifest(
        args.b, backend_b, args.backend_timeout, args.customer_local_v1
    )
    tally = {a["name"]: 0, b["name"]: 0, "void": 0}
    move_source = {}
    reasons = {}
    rows = []
    unverified = []

    for n in range(args.seeds):
        seed = args.start_seed + n
        for order in (0, 1):
            pair = [a, b] if order == 0 else [b, a]
            m = run_match(
                game_name=args.game, seed=seed, entrants=pair,
                out_dir=os.path.join(args.out, f"{seed}-{order}"),
                move_timeout_s=args.timeout,
            )
            rep = verify(m["transcript"])
            ok = rep["verdict"] == "PASS"
            if not ok:
                unverified.append((seed, order, rep["errors"][:1]))
                continue

            # Where did each move actually come from? A harness that fell back to
            # its own computed move on every turn still wins matches, and the
            # scoreboard cannot tell you that the model never spoke. Count it.
            try:
                with open(m["transcript"], "r", encoding="utf-8") as fh:
                    for line in fh:
                        rec = json.loads(line)
                        if rec.get("kind") != "move":
                            continue
                        note = rec["body"].get("entrant_message", {}).get("note", "")
                        who = pair[rec["body"]["player"]]["name"]
                        if note.startswith("source="):
                            key = "model" if note.startswith("source=model") else "fallback"
                            move_source[(who, key)] = move_source.get((who, key), 0) + 1
            except Exception:
                pass

            winner_name = m["seats"][str(m["winner"])] if m["winner"] is not None else "void"
            tally[winner_name] = tally.get(winner_name, 0) + 1
            reasons[m["reason"]] = reasons.get(m["reason"], 0) + 1
            rows.append(
                {
                    "seed": seed,
                    "seat0": pair[0]["name"],
                    "winner": winner_name,
                    "reason": m["reason"],
                    "moves": m["moves"],
                    "verified": ok,
                }
            )

    counted = len(rows)
    print(f"\n{'seed':>6}  {'seat 0':<16} {'winner':<16} {'moves':>5}  reason")
    print("-" * 74)
    for r in rows:
        print(f"{r['seed']:>6}  {r['seat0']:<16} {r['winner']:<16} {r['moves']:>5}  {r['reason']}")

    print(f"\n{'=' * 74}")
    print(f"game        : {args.game}")
    if backend_a == backend_b:
        print(f"backend     : {backend_a}  (identical behind both entrants)")
    else:
        print(f"backend     : SPLIT — the model is NOT held constant")
        print(f"  {a['name']:<18} {backend_a}")
        print(f"  {b['name']:<18} {backend_b}")
    print(f"matches     : {counted} counted  ({args.seeds} seeds x 2 seat orders)")
    print(f"verified    : {counted}/{counted + len(unverified)} replay-verified")
    if unverified:
        print(f"UNVERIFIED  : {len(unverified)} excluded from the tally -> {unverified}")
    print()
    for name in (a["name"], b["name"]):
        wins = tally.get(name, 0)
        pct = (100 * wins // counted) if counted else 0
        print(f"  {name:<18} {wins:>3} / {counted}   {pct:>3}%")
    if tally.get("void"):
        print(f"  {'void':<18} {tally['void']:>3} / {counted}")
    for name in (a["name"], b["name"]):
        model = move_source.get((name, "model"), 0)
        fb = move_source.get((name, "fallback"), 0)
        if model or fb:
            total = model + fb
            print(f"\n  {name}: {model}/{total} moves came from the model, {fb} from fallback")
            if fb and model == 0:
                print("  ^^ THE MODEL NEVER ANSWERED. This result is about the harness's "
                      "own solver, not the model. Do not report it as a model result.")

    print(f"\noutcomes    : {json.dumps(reasons)}")
    print(f"cost        : $0.00 — the engine makes no model calls")
    return 0 if not unverified else 1


if __name__ == "__main__":
    sys.exit(main())
