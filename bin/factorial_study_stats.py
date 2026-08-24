"""Pairing and contrast statistics for the AgentWars factorial study."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from factorial_study_core import *  # noqa: F401,F403

def _pair_key(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))  # type: ignore[return-value]


def pairing_summaries(observations: list[dict[str, Any]], confidence_level: float) -> dict[tuple[str, str], dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for observation in observations:
        grouped[_pair_key(observation["seat0"], observation["seat1"])].append(observation)
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for key, rows in grouped.items():
        a, b = key
        wins_a = sum(row.get("winner_treatment") == a for row in rows)
        wins_b = sum(row.get("winner_treatment") == b for row in rows)
        decisive = wins_a + wins_b
        interval = wilson_interval(wins_a, decisive, confidence_level) if decisive else (0.0, 0.0)
        out[key] = {
            "treatment_a": a,
            "treatment_b": b,
            "fixtures": len(rows),
            "wins_a": wins_a,
            "wins_b": wins_b,
            "non_decisive": len(rows) - decisive,
            "win_rate_a": wins_a / decisive if decisive else None,
            "win_rate_a_wilson95": list(interval) if decisive else None,
            "seat0_counts": {
                a: sum(row["seat0"] == a for row in rows),
                b: sum(row["seat0"] == b for row in rows),
            },
        }
    return out


def directional_contrast(
    summaries: dict[tuple[str, str], dict[str, Any]],
    preferred: str,
    opponent: str,
    label: str,
    confidence_level: float,
) -> dict[str, Any]:
    key = _pair_key(preferred, opponent)
    summary = summaries.get(key)
    if summary is None:
        return {"label": label, "preferred": preferred, "opponent": opponent, "status": "missing"}
    if summary["treatment_a"] == preferred:
        wins = summary["wins_a"]
    else:
        wins = summary["wins_b"]
    total = summary["wins_a"] + summary["wins_b"]
    low, high = wilson_interval(wins, total, confidence_level) if total else (0.0, 0.0)
    return {
        "label": label,
        "preferred": preferred,
        "opponent": opponent,
        "status": "complete" if total == summary["fixtures"] else "non_decisive",
        "wins": wins,
        "losses": total - wins,
        "fixtures": summary["fixtures"],
        "win_rate": wins / total if total else None,
        "win_rate_wilson95": [low, high] if total else None,
        "advantage_over_even_percentage_points": ((wins / total) - 0.5) * 100 if total else None,
    }


def comparison_analysis(
    plan: dict[str, Any],
    comparison: dict[str, Any],
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    confidence = float(plan["publication_gate"].get("confidence_level", 0.95))
    summaries = pairing_summaries(observations, confidence)
    structured = harness_by_role(plan, "structured")["id"]
    naive = harness_by_role(plan, "naive")["id"]

    def tid(model: str, harness: str) -> str:
        return treatment_id(comparison["id"], model, harness)

    contrasts = {
        "harness_effect_small": directional_contrast(
            summaries, tid("small", structured), tid("small", naive),
            "structured vs naive, small model held constant", confidence,
        ),
        "harness_effect_large": directional_contrast(
            summaries, tid("large", structured), tid("large", naive),
            "structured vs naive, large model held constant", confidence,
        ),
        "model_effect_structured": directional_contrast(
            summaries, tid("large", structured), tid("small", structured),
            "large vs small, structured harness held constant", confidence,
        ),
        "model_effect_naive": directional_contrast(
            summaries, tid("large", naive), tid("small", naive),
            "large vs small, naive harness held constant", confidence,
        ),
        "headline_small_structured_vs_large_naive": directional_contrast(
            summaries, tid("small", structured), tid("large", naive),
            "small model on structured harness vs large model on naive harness", confidence,
        ),
        "opposite_corner_large_structured_vs_small_naive": directional_contrast(
            summaries, tid("large", structured), tid("small", naive),
            "large model on structured harness vs small model on naive harness", confidence,
        ),
    }

    harness_rates = [
        contrasts[key].get("win_rate")
        for key in ("harness_effect_small", "harness_effect_large")
        if contrasts[key].get("win_rate") is not None
    ]
    model_rates = [
        contrasts[key].get("win_rate")
        for key in ("model_effect_structured", "model_effect_naive")
        if contrasts[key].get("win_rate") is not None
    ]
    main_effects = {
        "descriptive_structured_harness_win_rate_across_held_model_contrasts":
            sum(harness_rates) / len(harness_rates) if len(harness_rates) == 2 else None,
        "descriptive_large_model_win_rate_across_held_harness_contrasts":
            sum(model_rates) / len(model_rates) if len(model_rates) == 2 else None,
    }
    if len(harness_rates) == 2:
        main_effects["descriptive_harness_interaction_percentage_points"] = (
            (harness_rates[0] - 0.5) - (harness_rates[1] - 0.5)
        ) * 100

    return {
        "comparison_id": comparison["id"],
        "kind": comparison["kind"],
        "models": comparison["models"],
        "pairings": [summaries[key] for key in sorted(summaries)],
        "contrasts": contrasts,
        "main_effects": main_effects,
    }


