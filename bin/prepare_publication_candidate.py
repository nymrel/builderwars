#!/usr/bin/env python3
"""Prepare, but never publish, one AgentWars source-control review candidate."""

from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from publishing.promotion import (  # noqa: E402
    PromotionCandidateError,
    prepare_publication_candidate,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify one protected reviewer-detail export and write an offline "
            "source-control review candidate outside this repository."
        )
    )
    parser.add_argument("--reviewer-export", required=True, help="exact saved reviewer-detail JSON response")
    parser.add_argument("--out", required=True, help="new, non-existing directory outside the repository")
    parser.add_argument("--reviewer-approved-export-v1", action="store_true", required=True)
    parser.add_argument("--candidate-only-v1", action="store_true", required=True)
    parser.add_argument("--no-publication-v1", action="store_true", required=True)
    parser.add_argument("--source-control-review-required-v1", action="store_true", required=True)
    args = parser.parse_args()
    try:
        result = prepare_publication_candidate(ROOT, args.reviewer_export, args.out)
    except PromotionCandidateError as error:
        print(json.dumps({"status": "refused", "error": str(error)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

