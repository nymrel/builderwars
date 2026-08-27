#!/usr/bin/env python3
"""Run one match and print the result."""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from arena.match import run_match  # noqa: E402
from entrant_admission import (  # noqa: E402
    EntrantAdmissionError,
    require_entry_admission,
    unconfined_warning,
)
from entrants.backends import execution_claim_for_backend  # noqa: E402


def manifest(script, backend, claimed_model=None):
    name = os.path.splitext(os.path.basename(script))[0].replace("_", "-")
    return {
        "name": name,
        "cmd": [sys.executable, os.path.abspath(script), "--backend", backend],
        "env": [],
        # An entrant's own statement about what is behind it. Recorded as a
        # claim, never verified — the engine has no way to witness a model.
        "claimed_model": claimed_model or backend,
        "execution_claim": execution_claim_for_backend(backend),
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
        "--allow-unconfined-entrants",
        action="store_true",
        help=(
            "explicitly admit entrant files outside the repository's entrants/ directory; "
            "v1 does not confine their network, filesystem, CPU, or memory access"
        ),
    )
    args = ap.parse_args()

    if len(args.entrant) != 2:
        ap.error("pass --entrant exactly twice")

    try:
        admission = require_entry_admission(
            args.entrant,
            repository_root=ROOT,
            allow_unconfined=args.allow_unconfined_entrants,
        )
    except EntrantAdmissionError as exc:
        ap.error(str(exc))

    warning = unconfined_warning(admission)
    if warning:
        print(warning, file=sys.stderr)

    entrant_paths = [record["path"] for record in admission]
    result = run_match(
        game_name=args.game,
        seed=args.seed,
        entrants=[manifest(path, args.backend) for path in entrant_paths],
        out_dir=args.out,
        move_timeout_s=args.timeout,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
