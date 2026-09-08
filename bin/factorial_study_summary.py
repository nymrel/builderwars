"""Fail-closed summary assembly for the AgentWars factorial study."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from factorial_study_core import *  # noqa: F401,F403
from factorial_study_stats import comparison_analysis

def build_summary(
    *,
    plan: dict[str, Any],
    profile_name: str,
    expected_fixtures: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    missing_fixture_ids: list[str],
) -> dict[str, Any]:
    profile = plan["profiles"][profile_name]
    gate = plan["publication_gate"]
    all_violations: list[str] = []
    for observation in observations:
        all_violations.extend(f"{observation['fixture_id']}: {item}" for item in observation["violations"])
    if missing_fixture_ids:
        all_violations.append(f"missing {len(missing_fixture_ids)} planned fixtures")

    source_totals: dict[str, Counter[str]] = defaultdict(Counter)
    for observation in observations:
        for treatment, counts in observation["source_counts"].items():
            source_totals[treatment].update(counts)

    expected_treatments = sorted(
        {
            treatment["id"]
            for comparison in plan["comparisons"]
            for treatment in treatments_for(plan, comparison)
        }
    )
    if gate["require_every_treatment_model_move"]:
        for treatment in expected_treatments:
            if source_totals[treatment]["model"] <= 0:
                all_violations.append(f"{treatment}: no model-sourced move observed")

    expected_by_comparison = Counter(fixture["comparison_id"] for fixture in expected_fixtures)
    observed_by_comparison = Counter(observation["comparison_id"] for observation in observations)
    analyses = []
    for comparison in plan["comparisons"]:
        rows = [row for row in observations if row["comparison_id"] == comparison["id"]]
        analysis = comparison_analysis(plan, comparison, rows)
        analysis["expected_fixtures"] = expected_by_comparison[comparison["id"]]
        analysis["observed_fixtures"] = observed_by_comparison[comparison["id"]]
        analyses.append(analysis)

    if profile["publishable"]:
        gate_status = "PASS" if not all_violations else "HOLD"
    else:
        gate_status = "NOT_PUBLISHABLE" if not all_violations else "HOLD"

    summary = {
        "schema": RESULT_SCHEMA,
        "study_id": plan["study_id"],
        "plan_digest": plan_digest(plan),
        "profile": profile_name,
        "profile_publishable": profile["publishable"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "expected_fixtures": len(expected_fixtures),
        "observed_fixtures": len(observations),
        "missing_fixture_ids": sorted(missing_fixture_ids),
        "publication_gate": {
            "status": gate_status,
            "contract": gate,
            "violations": sorted(set(all_violations)),
        },
        "attestation_boundary": {
            "replay_proves": [
                "transcript integrity",
                "game reconstruction from the seed",
                "move legality rulings",
                "winner recomputation from referee state",
                "referee engine digest selection",
            ],
            "model_identity_attested": False,
            "execution_claims_attested": False,
            "note": (
                "The arena never contacts the model. Backends and execution classes are "
                "entrant-declared and hash-bound, not independently authenticated."
            ),
        },
        "move_sources": {name: dict(counts) for name, counts in sorted(source_totals.items())},
        "comparisons": analyses,
        "fixtures": sorted(observations, key=lambda row: row["fixture_id"]),
    }
    summary["summary_digest"] = value_digest({key: value for key, value in summary.items() if key != "generated_at_utc"})
    return summary


