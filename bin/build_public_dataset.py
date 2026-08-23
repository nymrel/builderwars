#!/usr/bin/env python3
"""Build the exact, allowlist-selected AgentWars public artifact atomically."""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from publishing.product import write_public_artifact  # noqa: E402
from publishing.projection import PublicationError  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--publication-manifest",
        default=os.path.join(ROOT, "docs", "AGENTWARS_PUBLICATION_MANIFEST.v1.json"),
    )
    parser.add_argument(
        "--out",
        default=os.path.join(ROOT, "publishing", "agentwars-public-v1"),
    )
    args = parser.parse_args()
    try:
        report = write_public_artifact(ROOT, args.publication_manifest, args.out)
    except PublicationError as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
