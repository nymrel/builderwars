#!/usr/bin/env python3
"""Run one match and print the result."""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arena.isolation import IsolationRequirementError  # noqa: E402
from arena.match import run_match  # noqa: E402


def manifest(script, backend, claimed_model=None):
    name = os.path.splitext(os.path.basename(script))[0].replace("_", "-")
    return {
        "name": name,
        "cmd": [sys.executable, os.path.abspath(script), "--backend", backend],
        "env": [],
        # An entrant's own statement about what is behind it. Recorded as a
        # claim, never verified — the engine has no way to witness a model.
        "claimed_model": claimed_model or backend,
    }


def main():
    ap = argparse.ArgumentParser(description="Run one arena match.")
    ap.add_argument("--game", default="nim")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--entrant", action="append", required=True,
                    help="path to an entrant script; pass exactly twice")
    ap.add_argument("--backend", default="stub:v1", help="backend spec handed to both entrants")
    ap.add_argument("--out", default="matches")
    ap.add_argument("--timeout", type=float, default=15.0)
    ap.add_argument(
        "--isolation",
        default="process",
        choices=["process"],
        help="implemented execution profile; process mode is capability-unconfined",
    )
    ap.add_argument(
        "--require-capability-isolation",
        action="store_true",
        help="refuse before all match side effects unless an OS capability boundary is available",
    )
    args = ap.parse_args()

    if len(args.entrant) != 2:
        ap.error("pass --entrant exactly twice")

    try:
        result = run_match(
            game_name=args.game,
            seed=args.seed,
            entrants=[manifest(p, args.backend) for p in args.entrant],
            out_dir=args.out,
            move_timeout_s=args.timeout,
            isolation_mode=args.isolation,
            require_capability_isolation=args.require_capability_isolation,
        )
    except IsolationRequirementError as exc:
        print(json.dumps(exc.to_json(), sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
