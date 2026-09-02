#!/usr/bin/env python3
"""Inspect the local unstaffed AgentWars support-readiness contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publishing.support_readiness import support_readiness_contract, verify_support_readiness_contract


def main() -> int:
    contract = verify_support_readiness_contract(support_readiness_contract())
    print(json.dumps(contract, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
