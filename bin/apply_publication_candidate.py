#!/usr/bin/env python3
"""Stage one reviewed AgentWars candidate as a source decision, never a release."""

from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.dont_write_bytecode = True

from publishing.source_decision import (  # noqa: E402
    SourceDecisionError,
    apply_source_decision,
    inspect_source_decision_state,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Independently validate one offline promotion candidate, then stage only "
            "its exact transcript and an explicit title-ineligible source manifest decision."
        )
    )
    parser.add_argument("--inspect-protected-state-v1", action="store_true")
    parser.add_argument(
        "--candidate-dir", help="exact external four-file candidate directory"
    )
    parser.add_argument(
        "--expected-candidate-digest", help="full reviewed candidate SHA-256"
    )
    parser.add_argument("--expected-head", help="full reviewed BuilderWars Git SHA")
    parser.add_argument(
        "--expected-manifest-sha256", help="full current publication-manifest SHA-256"
    )
    parser.add_argument(
        "--expected-generated-tree-digest",
        help="full current publishing/agentwars-public-v1 tree digest",
    )
    parser.add_argument(
        "--decision",
        choices=("approved_for_publication", "held"),
        help="explicit source-control decision; neither option builds or deploys",
    )
    parser.add_argument("--label", help="reviewed 1-120 character manifest label")
    parser.add_argument("--source-control-decision-v1", action="store_true")
    parser.add_argument("--title-ineligible-v1", action="store_true")
    parser.add_argument("--no-generated-artifact-mutation-v1", action="store_true")
    parser.add_argument("--no-deploy-v1", action="store_true")
    args = parser.parse_args()
    apply_values = (
        args.candidate_dir,
        args.expected_candidate_digest,
        args.expected_head,
        args.expected_manifest_sha256,
        args.expected_generated_tree_digest,
        args.decision,
        args.label,
        args.source_control_decision_v1,
        args.title_ineligible_v1,
        args.no_generated_artifact_mutation_v1,
        args.no_deploy_v1,
    )
    if args.inspect_protected_state_v1:
        if any(apply_values):
            parser.error(
                "--inspect-protected-state-v1 cannot be combined with apply arguments"
            )
        try:
            result = inspect_source_decision_state(ROOT)
        except SourceDecisionError as error:
            print(
                json.dumps({"status": "refused", "error": str(error)}, sort_keys=True),
                file=sys.stderr,
            )
            return 2
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    missing = [
        name
        for name, value in (
            ("--candidate-dir", args.candidate_dir),
            ("--expected-candidate-digest", args.expected_candidate_digest),
            ("--expected-head", args.expected_head),
            ("--expected-manifest-sha256", args.expected_manifest_sha256),
            ("--expected-generated-tree-digest", args.expected_generated_tree_digest),
            ("--decision", args.decision),
            ("--label", args.label),
            ("--source-control-decision-v1", args.source_control_decision_v1),
            ("--title-ineligible-v1", args.title_ineligible_v1),
            (
                "--no-generated-artifact-mutation-v1",
                args.no_generated_artifact_mutation_v1,
            ),
            ("--no-deploy-v1", args.no_deploy_v1),
        )
        if not value
    ]
    if missing:
        parser.error("apply mode requires " + ", ".join(missing))
    try:
        result = apply_source_decision(
            ROOT,
            args.candidate_dir,
            expected_candidate_digest=args.expected_candidate_digest,
            expected_head=args.expected_head,
            expected_manifest_sha256=args.expected_manifest_sha256,
            expected_generated_tree_digest=args.expected_generated_tree_digest,
            decision=args.decision,
            label=args.label,
        )
    except SourceDecisionError as error:
        print(
            json.dumps({"status": "refused", "error": str(error)}, sort_keys=True),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
