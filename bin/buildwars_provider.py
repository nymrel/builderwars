#!/usr/bin/env python3
"""buildwars-provider — read-only planning CLI for the customer provider hub.

This tool describes known provider routes and generates BuildWars pairing keys.
Known-but-disabled routes remain visible and explicitly non-executable. It never:
  * runs a login or opens a browser;
  * reads a credential file or inspects a secret value;
  * contacts the network;
  * claims an account is linked merely because a binary exists.

For executable routes, link state is established by YOU using the provider's
documented customer-side flow. Disabled routes provide no connection action.
Exit codes: 0 success, 2 unknown provider (fail closed).
"""

import argparse
import json
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from provider_hub.catalog import (  # noqa: E402
    PROVIDER_IDS,
    connect_plan,
    get_provider,
    public_catalog,
)
from provider_hub.signing import generate_pairing_key  # noqa: E402


def cmd_catalog(_args):
    for provider_id, entry in public_catalog():
        print(f"{provider_id}")
        print(f"  name        : {entry['display_name']}")
        print(f"  mode        : {entry['connection_mode']}")
        print(f"  transport   : {entry['connection_transport']}")
        print(f"  custody     : {entry['credential_custody']}")
        print(f"  model       : {'required' if entry['model_required'] else 'not required'}")
        print(f"  backend kind: {entry['backend_kind']}")
        print(f"  provider cls: {entry['provider_class']}")
        print(f"  harness cls : {entry['harness_class']}")
        print(f"  execution   : {'customer-local' if entry['local_execution'] else 'disabled'}")
        print(f"  hosted route: {entry['hosted_route_status']}")
        print(f"  evidence    : {entry['evidence_date']}")
    print()
    print("Facts only. Link state is whatever YOU verify locally; this tool")
    print("cannot and does not check it.")
    return 0


def cmd_catalog_json(_args):
    payload = {
        pid: {
            "display_name": entry["display_name"],
            "connection_mode": entry["connection_mode"],
            "connection_transport": entry["connection_transport"],
            "auth_plan": list(entry["auth_plan"]),
            "status_plan": entry["status_plan"],
            "credential_custody": entry["credential_custody"],
            "model_required": entry["model_required"],
            "backend_kind": entry["backend_kind"],
            "limitations": list(entry["limitations"]),
            "provider_class": entry["provider_class"],
            "harness_class": entry["harness_class"],
            "local_execution": entry["local_execution"],
            "hosted_route_status": entry["hosted_route_status"],
            "prohibited_routes": list(entry["prohibited_routes"]),
            "evidence_date": entry["evidence_date"],
            "official_sources": list(entry["official_sources"]),
        }
        for pid, entry in public_catalog()
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_connect_plan(args):
    plan = connect_plan(args.provider)
    entry = get_provider(args.provider)
    print(f"Provider route - {plan['provider']} ({plan['display_name']})")
    print(f"mode: {plan['connection_mode']}")
    print(f"transport: {entry['connection_transport']}")
    print(f"provider class: {entry['provider_class']}")
    print(f"harness class: {entry['harness_class']}")
    print(f"execution: {'customer-local' if entry['local_execution'] else 'disabled'}")
    print(f"hosted route: {entry['hosted_route_status']}")
    print(f"evidence date: {entry['evidence_date']}")
    print()
    for step in plan["steps"]:
        print(step)
    print()
    print(plan["custody"])
    print(f"Status: {plan['status']}")
    print()
    if plan["limitations"]:
        print("Limitations:")
        for line in plan["limitations"]:
            print(f"  - {line}")
    return 0


def cmd_pair_keygen(_args):
    key = generate_pairing_key()
    secret = key.secret.reveal().hex()
    print("Generated a fresh BuildWars runner pairing key.")
    print()
    print(f"key id (public) : {key.key_id}")
    print(f"pairing key     : {secret}")
    print()
    print("Store the pairing key yourself, now. It is shown exactly once.")
    print("It is a BuildWars-only key, generated fresh, distinct from every")
    print("provider credential you hold. Provision it over an authenticated")
    print("pairing channel to BOTH the verifier side and your runner; it is")
    print("not a provider credential and does not replace one. Only the key")
    print("id above ever enters a serialized envelope.")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="buildwars_provider",
        description="Read-only BuildWars provider route planner.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("catalog", help="list every known provider route and availability (read-only)")
    p.add_argument("--json", action="store_true", dest="as_json")
    p.set_defaults(func=cmd_catalog)

    p = sub.add_parser("connect-plan", help="show the current plan or disabled state for one known provider")
    p.add_argument("provider", choices=PROVIDER_IDS)
    p.set_defaults(func=cmd_connect_plan)

    p = sub.add_parser("pair-keygen", help="generate a BuildWars-only runner pairing key")
    p.set_defaults(func=cmd_pair_keygen)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "catalog" and args.as_json:
        return cmd_catalog_json(args)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
