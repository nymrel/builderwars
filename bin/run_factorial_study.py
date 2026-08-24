#!/usr/bin/env python3
"""Execute or re-analyze the preregistered AgentWars factorial study."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

BIN = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BIN)
if BIN not in sys.path:
    sys.path.insert(0, BIN)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from factorial_study_core import *  # noqa: E402,F401,F403
from factorial_study_output import *  # noqa: E402,F401,F403
from factorial_study_receipts import *  # noqa: E402,F401,F403
from factorial_study_stats import *  # noqa: E402,F401,F403
from factorial_study_summary import *  # noqa: E402,F401,F403

def run(args: argparse.Namespace) -> int:
    plan_path = os.path.abspath(args.plan)
    plan = validate_plan(load_json(plan_path), root=ROOT, check_paths=True)
    if args.validate_plan:
        counts = {
            name: len(enumerate_fixtures(plan, name))
            for name in sorted(plan["profiles"])
        }
        print(json.dumps({"plan_digest": plan_digest(plan), "fixtures": counts}, indent=2, sort_keys=True))
        return 0

    require(args.profile is not None, "--profile is required unless --validate-plan is used")
    profile_name = args.profile
    require(profile_name in plan["profiles"], f"unknown profile {profile_name!r}")
    output_root = os.path.abspath(args.out)
    os.makedirs(output_root, exist_ok=True)
    ensure_lock(output_root, plan, profile_name)

    all_fixtures = enumerate_fixtures(plan, profile_name)
    selected_ids = args.comparison or [comparison["id"] for comparison in plan["comparisons"]]
    selected_fixtures = enumerate_fixtures(plan, profile_name, selected_ids)
    selected_set = {fixture["fixture_id"] for fixture in selected_fixtures}
    allowed_reasons = set(plan["publication_gate"]["allowed_result_reasons"])

    sys.path.insert(0, ROOT)
    from arena.match import run_match  # pylint: disable=import-outside-toplevel
    from arena.replay import verify  # pylint: disable=import-outside-toplevel
    from entrants.backends import execution_claim_for_backend  # pylint: disable=import-outside-toplevel

    by_fixture = {fixture["fixture_id"]: fixture for fixture in all_fixtures}
    observations_by_id: dict[str, dict[str, Any]] = {}

    # Always re-verify any existing receipts, including comparisons not selected
    # for this invocation. A stale summary can never become a publication input.
    for fixture in all_fixtures:
        transcript = expected_transcript_path(output_root, fixture)
        if os.path.isfile(transcript):
            observations_by_id[fixture["fixture_id"]] = analyze_transcript(
                fixture=fixture,
                transcript_path=transcript,
                replay_verify=verify,
                allowed_result_reasons=allowed_reasons,
                output_root=output_root,
            )

    for index, fixture in enumerate(selected_fixtures, 1):
        if fixture["fixture_id"] in observations_by_id:
            continue
        if args.analyze_only:
            continue
        out_dir = receipt_directory(output_root, fixture)
        os.makedirs(out_dir, exist_ok=True)
        manifests = [
            make_manifest(fixture["seat0"], plan["runtime"]["backend_timeout_s"], execution_claim_for_backend),
            make_manifest(fixture["seat1"], plan["runtime"]["backend_timeout_s"], execution_claim_for_backend),
        ]
        print(
            f"[{index}/{len(selected_fixtures)}] {fixture['comparison_id']} "
            f"seed={fixture['seed']} order={fixture['order']} "
            f"{fixture['seat0']['id']} vs {fixture['seat1']['id']}",
            flush=True,
        )
        result = run_match(
            game_name=plan["game"],
            seed=fixture["seed"],
            entrants=manifests,
            out_dir=out_dir,
            move_timeout_s=float(plan["runtime"]["move_timeout_s"]),
            match_id=fixture["match_id"],
        )
        transcript = result["transcript"]
        observation = analyze_transcript(
            fixture=fixture,
            transcript_path=transcript,
            replay_verify=verify,
            allowed_result_reasons=allowed_reasons,
            output_root=output_root,
        )
        observations_by_id[fixture["fixture_id"]] = observation
        missing = sorted(set(by_fixture) - set(observations_by_id))
        summary = build_summary(
            plan=plan,
            profile_name=profile_name,
            expected_fixtures=all_fixtures,
            observations=list(observations_by_id.values()),
            missing_fixture_ids=missing,
        )
        write_outputs(output_root, summary)
        if observation["violations"] and not args.continue_after_hold:
            print("Publication gate held; stopping after the first violating receipt.", file=sys.stderr)
            return 2

    missing = sorted(set(by_fixture) - set(observations_by_id))
    summary = build_summary(
        plan=plan,
        profile_name=profile_name,
        expected_fixtures=all_fixtures,
        observations=list(observations_by_id.values()),
        missing_fixture_ids=missing,
    )
    write_outputs(output_root, summary)
    print(f"publication gate: {summary['publication_gate']['status']}")
    print(f"summary: {os.path.join(output_root, 'summary.json')}")
    if args.analyze_only and any(fixture_id in selected_set for fixture_id in missing):
        return 2
    return 0 if summary["publication_gate"]["status"] in ("PASS", "NOT_PUBLISHABLE") else 2


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", default="docs/AGENTWARS_CROSS_MODEL_STUDY.v1.json")
    ap.add_argument("--profile", choices=("smoke", "publication"), default=None)
    ap.add_argument("--out", default="matches/studies/agentwars-cross-model-v1")
    ap.add_argument("--comparison", action="append", help="run one registered comparison; repeat as needed")
    ap.add_argument("--analyze-only", action="store_true", help="verify existing receipts without running entrants")
    ap.add_argument("--continue-after-hold", action="store_true", help="finish the matrix after a gate violation")
    ap.add_argument("--validate-plan", action="store_true", help="validate the preregistration and print fixture counts")
    return ap


def main() -> int:
    try:
        return run(parser().parse_args())
    except (OSError, StudyError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
