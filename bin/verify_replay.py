#!/usr/bin/env python3
"""Verify a match transcript. Exit 0 on PASS, 1 on FAIL.

Needs nothing but this repository and a stock Python 3 interpreter — no
dependencies, no network, no accounts. That is deliberate: a result anyone can
check is the only kind worth publishing.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arena.replay import verify  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Independently verify an arena transcript.")
    ap.add_argument("transcript")
    ap.add_argument("--json", action="store_true", help="emit the full report as JSON")
    args = ap.parse_args()

    report = verify(args.transcript)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"transcript : {os.path.basename(report['transcript'])}")
        print(f"match      : {report.get('game')} seed={report.get('seed')} id={report.get('match_id')}")
        print(f"chain head : {report.get('chain_head', '-')}")
        isolation = report.get("isolation")
        if isinstance(isolation, dict):
            capability = "yes" if isolation.get("capability_isolation") else "no"
            source = isolation.get("source", "current-profile")
            print(
                f"isolation  : {isolation.get('mode', 'unknown')} "
                f"capability={capability} source={source}"
            )
        else:
            print("isolation  : invalid or missing")
        print()
        for c in report["checks"]:
            mark = "PASS" if c["ok"] else "FAIL"
            line = f"  [{mark}] {c['check']}"
            if c.get("detail"):
                line += f" — {c['detail']}"
            print(line)
        print()
        if report.get("recorded"):
            print(f"recorded   : {json.dumps(report['recorded'])}")
            print(f"recomputed : {json.dumps(report['recomputed'])}")
            print()
        print(f"VERDICT: {report['verdict']}")
        if report["verdict"] == "PASS":
            print("\nproves:")
            for p in report["proves"]:
                print(f"  + {p}")
            print("\ndoes not prove:")
            for p in report["does_not_prove"]:
                print(f"  - {p}")

    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
