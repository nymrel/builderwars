#!/usr/bin/env python3
"""Print or evaluate the non-authoritative BuilderWars beta-capacity packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publishing import capacity_readiness as capacity


def _template() -> dict[str, object]:
    contract = capacity.capacity_contract()
    return {
        "schemaVersion": "builderwars.beta-capacity-input-template/1",
        "contractDigest": contract["contractDigest"],
        "instructions": "Replace every operator_required_not_recorded value; keep both execution authority flags false.",
        "operatorInputs": contract["operatorInputTemplate"],
        "productionAuthority": dict(capacity.PRODUCTION_AUTHORITY),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--template", action="store_true", help="Print the exact operator-fill JSON template.")
    action.add_argument("--evaluate", type=Path, metavar="INPUT_JSON", help="Evaluate one filled operatorInputs JSON object.")
    args = parser.parse_args(argv)
    if args.template:
        print(json.dumps(_template(), indent=2, sort_keys=True))
        return 0
    try:
        raw = args.evaluate.read_bytes()
        if len(raw) > 65_536:
            raise capacity.CapacityReadinessError("capacity input exceeds 65536 bytes")
        value = json.loads(raw.decode("utf-8"))
        scenario = capacity.build_capacity_scenario_from_operator_inputs(value)
        capacity.verify_capacity_scenario(scenario)
    except (OSError, UnicodeError, json.JSONDecodeError, capacity.CapacityReadinessError) as error:
        print(json.dumps({"status": "REFUSED", "error": str(error)}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(scenario, indent=2, sort_keys=True))
    return 0 if scenario["browserReferencePolicyFit"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
