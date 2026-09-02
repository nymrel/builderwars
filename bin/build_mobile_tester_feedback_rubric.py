#!/usr/bin/env python3
"""Build or verify the mobile copy of the canonical tester feedback rubric."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "mobile-arena" / "data" / "tester-feedback-rubric.v1.json"
sys.path.insert(0, str(ROOT))

from publishing.tester_readiness import feedback_rubric  # noqa: E402


def rendered_rubric() -> str:
    return json.dumps(
        feedback_rubric(),
        ensure_ascii=True,
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the browser-readable tester rubric from the pure launch contract."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the tracked mobile artifact is absent or differs from the canonical contract.",
    )
    args = parser.parse_args()
    expected = rendered_rubric()
    if args.check:
        if not TARGET.is_file() or TARGET.read_text(encoding="utf-8") != expected:
            raise SystemExit("mobile tester feedback rubric is stale; rebuild it from the canonical contract")
        print(f"PASS mobile tester feedback rubric matches {feedback_rubric()['rubricDigest']}")
        return 0
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(expected, encoding="utf-8", newline="\n")
    print(f"wrote {TARGET.relative_to(ROOT)} ({feedback_rubric()['rubricDigest']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
