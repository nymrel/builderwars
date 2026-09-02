#!/usr/bin/env python3
"""Print the local, zero-authority AgentWars commissioner starter packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publishing.commissioner import commissioner_starter, verify_commissioner_starter


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect the local AgentWars commissioner starter; this grants no launch authority."
    )
    parser.add_argument("--compact", action="store_true", help="Emit canonical compact JSON.")
    args = parser.parse_args()
    packet = verify_commissioner_starter(commissioner_starter())
    if args.compact:
        print(json.dumps(packet, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
    else:
        print(json.dumps(packet, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
