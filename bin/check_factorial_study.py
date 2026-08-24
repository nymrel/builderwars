#!/usr/bin/env python3
"""Adversarial contract checks for the AgentWars factorial study runner."""

import copy
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, "bin", "run_factorial_study.py")
PLAN = os.path.join(ROOT, "docs", "AGENTWARS_CROSS_MODEL_STUDY.v1.json")

spec = importlib.util.spec_from_file_location("agentwars_factorial", RUNNER)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

checks = 0


def check(condition, message):
    global checks
    checks += 1
    if not condition:
        raise AssertionError(message)
    print(f"PASS {checks:02d}: {message}")


def expect_error(fn, message):
    global checks
    checks += 1
    try:
        fn()
    except (module.StudyError, ValueError):
        print(f"PASS {checks:02d}: {message}")
        return
    raise AssertionError(message)


with open(PLAN, "r", encoding="utf-8") as fh:
    plan = json.load(fh)
module.validate_plan(plan, root=ROOT, check_paths=True)
check(module.plan_digest(plan) == module.plan_digest(copy.deepcopy(plan)), "plan digest is canonical")

smoke = module.enumerate_fixtures(plan, "smoke")
publication = module.enumerate_fixtures(plan, "publication")
check(len(smoke) == 48, "smoke profile fixes 48 matched receipts")
check(len(publication) == 384, "publication profile fixes 384 matched receipts")
check(len({fixture["fixture_id"] for fixture in publication}) == len(publication), "fixture ids are unique")
check(all(fixture["seat0"]["id"] != fixture["seat1"]["id"] for fixture in publication), "entrant names never collide")

pair_orders = {}
for fixture in publication:
    key = (fixture["comparison_id"], fixture["pairing_id"], fixture["replicate"], fixture["seed"])
    pair_orders.setdefault(key, set()).add(fixture["order"])
check(all(orders == {0, 1} for orders in pair_orders.values()), "every seed has both seat orders")

check(module.source_class(module.source_from_note("source=model")) == "model", "model source is accepted")
check(module.source_class(module.source_from_note("source=fallback:rejected_model_answer")) == "fallback", "fallback is classified")
check(module.source_class(module.source_from_note("source=backend_error:TimeoutExpired")) == "backend_error", "backend error is classified")
check(module.source_class(module.source_from_note("unstructured prose")) == "missing", "missing source fails closed")

low, high = module.wilson_interval(8, 8)
check(0.67 < low < high == 1.0, "Wilson interval handles an undefeated arm")
low, high = module.wilson_interval(0, 8)
check(low == 0.0 < high < 0.33, "Wilson interval handles a winless arm")

bad = copy.deepcopy(plan)
bad["publication_gate"]["require_zero_fallback"] = False
expect_error(lambda: module.validate_plan(bad, root=ROOT, check_paths=True), "zero-fallback cannot be relaxed in v1")

bad = copy.deepcopy(plan)
bad["comparisons"][1]["models"]["small"]["family"] = "not-qwen"
expect_error(lambda: module.validate_plan(bad, root=ROOT, check_paths=True), "same-family control rejects mixed families")

bad = copy.deepcopy(plan)
bad["comparisons"][0]["models"]["small"]["backend"] = "stub:v1"
expect_error(lambda: module.validate_plan(bad, root=ROOT, check_paths=True), "publication plan rejects scripted backends")

# Synthetic complete matrix: structured always beats naive; large always beats
# small when the harness is held constant. This checks directional orientation,
# including pairings whose canonical key puts the preferred arm second.
comparison = plan["comparisons"][0]
treatments = module.treatments_for(plan, comparison)
observations = []
for a, b in __import__("itertools").combinations(treatments, 2):
    preferred = None
    if a["harness_role"] != b["harness_role"] and a["model_id"] == b["model_id"]:
        preferred = a if a["harness_role"] == "structured" else b
    elif a["model_id"] != b["model_id"] and a["harness_role"] == b["harness_role"]:
        preferred = a if a["model_id"] == "large" else b
    else:
        preferred = a
    for order in (0, 1):
        observations.append(
            {
                "seat0": a["id"] if order == 0 else b["id"],
                "seat1": b["id"] if order == 0 else a["id"],
                "winner_treatment": preferred["id"],
            }
        )
analysis = module.comparison_analysis(plan, comparison, observations)
check(analysis["contrasts"]["harness_effect_small"]["win_rate"] == 1.0, "small-model harness contrast points the right way")
check(analysis["contrasts"]["harness_effect_large"]["win_rate"] == 1.0, "large-model harness contrast points the right way")
check(analysis["contrasts"]["model_effect_structured"]["win_rate"] == 1.0, "structured-harness model contrast points the right way")
check(analysis["contrasts"]["model_effect_naive"]["win_rate"] == 1.0, "naive-harness model contrast points the right way")

print(f"\n{checks}/{checks} factorial-study contract checks passed")
sys.exit(0)
