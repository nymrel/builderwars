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

from arena.isolation import IsolationRequirementError, resolve_isolation  # noqa: E402
from arena.match import run_match  # noqa: E402
from arena.replay import verify  # noqa: E402


def manifest(script, backend, backend_timeout=None):
    cmd = [sys.executable, os.path.abspath(script), "--backend", backend]
    if backend_timeout:
        cmd += ["--backend-timeout", str(backend_timeout)]
    return {
        "name": os.path.splitext(os.path.basename(script))[0].replace("_", "-"),
        "cmd": cmd,
        "env": [],
        "claimed_model": backend,
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
        "--isolation",
        default="process",
        choices=["process"],
        help="implemented execution profile; process mode is capability-unconfined",
    )
    ap.add_argument(
        "--require-capability-isolation",
        action="store_true",
        help="refuse the entire series before output or entrants unless an OS capability boundary exists",
    )
    args = ap.parse_args()

    try:
        resolve_isolation(
            mode=args.isolation,
            require_capability_isolation=args.require_capability_isolation,
        )
    except IsolationRequirementError as exc:
        print(json.dumps(exc.to_json(), sort_keys=True), file=sys.stderr)
        return 2

    backend_a = args.backend_a or args.backend
    backend_b = args.backend_b or args.backend
    a = manifest(args.a, backend_a, args.backend_timeout)
    b = manifest(args.b, backend_b, args.backend_timeout)
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
                game_name=args.game,
                seed=seed,
                entrants=pair,
                out_dir=os.path.join(args.out, f"{seed}-{order}"),
                move_timeout_s=args.timeout,
                isolation_mode=args.isolation,
                require_capability_isolation=args.require_capability_isolation,
            )
            rep = verify(m["transcript"])
            ok = rep["verdict"] == "PASS"
            if not ok:
                unverified.append((seed, order, rep["errors"][:1]))
                continue

            try:
                with open(m["transcript"], "r", encoding="utf-8") as fh:
                    for line in fh:
                        rec = json.loads(line)
                        if rec.get("kind") != "move":
                            continue
                        note = rec["body"].get("entrant_message", {}).get("note", "")
                        who = pair[rec["body"]["player"]]["name"]
                        if note.startswith("source="):
                            key = "model" if note == "source=model" else "fallback"
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
    for row in rows:
        print(f"{row['seed']:>6}  {row['seat0']:<16} {row['winner']:<16} {row['moves']:>5}  {row['reason']}")

    print(f"\n{'=' * 74}")
    print(f"game        : {args.game}")
    print("isolation   : process (capability isolation: no)")
    if backend_a == backend_b:
        print(f"backend     : {backend_a}  (identical behind both entrants)")
    else:
        print("backend     : SPLIT — the model is NOT held constant")
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
        fallback = move_source.get((name, "fallback"), 0)
        if model or fallback:
            total = model + fallback
            print(f"\n  {name}: {model}/{total} moves came from the model, {fallback} from fallback")
            if fallback and model == 0:
                print("  ^^ THE MODEL NEVER ANSWERED. This result is about the harness's "
                      "own solver, not the model. Do not report it as a model result.")

    print(f"\noutcomes    : {json.dumps(reasons)}")
    print("cost        : $0.00 — the engine makes no model calls")
    return 0 if not unverified else 1


if __name__ == "__main__":
    sys.exit(main())
