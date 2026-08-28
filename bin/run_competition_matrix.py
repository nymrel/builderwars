#!/usr/bin/env python3
"""Run one explicit AgentWars Competition Matrix declaration."""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from competitions.matrix import (  # noqa: E402
    CompetitionConfigError,
    load_config,
    run_competition,
    write_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a balanced, replay-verified AgentWars competition matrix."
    )
    parser.add_argument("--config", required=True, help="strict matrix v1 JSON declaration")
    parser.add_argument("--matches-dir", required=True, help="explicit transcript output directory")
    parser.add_argument("--report", required=True, help="explicit public report JSON path")
    parser.add_argument("--timeout", type=float, default=15.0, help="per-move timeout in seconds")
    parser.add_argument(
        "--max-matches",
        type=int,
        default=512,
        help="explicit schedule ceiling; raise it deliberately for larger leagues",
    )
    args = parser.parse_args()

    try:
        report = run_competition(
            load_config(args.config),
            matches_dir=args.matches_dir,
            repo_root=ROOT,
            move_timeout_s=args.timeout,
            max_matches=args.max_matches,
        )
        write_report(report, args.report)
    except (CompetitionConfigError, RuntimeError) as exc:
        print(f"competition failed: {exc}", file=sys.stderr)
        return 2
    except OSError:
        print("competition failed: runtime I/O error", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "competitionId": report["competitionId"],
                "status": report["status"],
                "completedMatches": report["schedule"]["completedMatches"],
                "verifiedMatches": report["schedule"]["verifiedMatches"],
                "moveTimeoutMs": report["executionPolicy"]["moveTimeoutMs"],
                "report": os.path.basename(os.path.abspath(args.report)),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
