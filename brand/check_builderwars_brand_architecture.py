#!/usr/bin/env python3
"""Validate the owner-adopted BuilderWars public brand contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CONTRACT_PATH = DOCS / "BUILDERWARS_BRAND_ARCHITECTURE.v1.json"
ARCHITECTURE_PATH = DOCS / "BUILDERWARS_BRAND_ARCHITECTURE.md"
ADDENDUM_PATH = DOCS / "BUILDERWARS_BRAND_FOUNDATION_ADDENDUM_2026-09-04.md"
RESEARCH_PATH = DOCS / "BUILDERWARS_BRAND_RESEARCH_2026-09-04.md"
PLAN_PATH = DOCS / "BUILDERWARS_BRAND_EXECUTION_PLAN_2026-09-04.md"
NORTH_STAR_PATH = DOCS / "AGENTWARS_NORTH_STAR.md"
NORTH_STAR_MACHINE_PATH = DOCS / "AGENTWARS_NORTH_STAR.v1.json"

EXPECTED_CATEGORIES = [
    ("arena", "Arena", "/arena"),
    ("forge", "Forge", "/forge"),
    ("games", "Games", "/games"),
    ("evals", "Evals", "/evals"),
    ("leagues", "Leagues", "/leagues"),
    ("studio", "Studio", "/studio"),
    ("watch", "Watch", "/watch"),
    ("academy", "Academy", "/academy"),
    ("passport", "Passport", "/passport"),
]
EXPECTED_LEGACY = ["AgentWars", "BuildWars", "AgentBattles", "AgentGames"]
CHECKS = 0


def check(condition: bool, label: str) -> None:
    global CHECKS
    if not condition:
        raise AssertionError(label)
    CHECKS += 1
    print(f"PASS {label}")


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def load_contract() -> dict[str, Any]:
    value = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"), object_pairs_hook=strict_object)
    check(isinstance(value, dict), "contract top level is an object")
    return value


def main() -> None:
    contract = load_contract()
    check(contract["schema_version"] == "builderwars.brand-architecture.v1", "schema version")
    check(contract["status"] == "owner_adopted", "owner-adopted status")
    check(contract["adopted_at"] == "2026-09-04", "adoption date")
    check(contract["ruling_owner"] == "Jalen", "ruling owner")
    check(contract["public_brand"]["name"] == "BuilderWars", "sole public brand spelling")
    check(contract["public_brand"]["role"] == "sole_public_umbrella", "sole public umbrella role")

    categories = contract["categories"]
    observed = [(item["id"], item["name"], item["route"]) for item in categories]
    check(observed == EXPECTED_CATEGORIES, "exact ordered category architecture")
    check(len({item["route"] for item in categories}) == 9, "category routes are unique")
    check(all(item["qualified_name"] == f"BuilderWars {item['name']}" for item in categories), "qualified category names")
    check(all(isinstance(item["job"], str) and item["job"].endswith(".") for item in categories), "category jobs are complete statements")

    legacy = contract["legacy_names"]
    check([item["name"] for item in legacy] == EXPECTED_LEGACY, "exact legacy name set and order")
    check(all(item["mode"] == "historical_or_compatibility_only" for item in legacy), "legacy names cannot become public sub-brands")

    domains = contract["domains"]
    check(domains["canonical"]["origin"] == "https://builderwars.com", "canonical singular origin")
    check(domains["defensive_plural"]["origins"] == ["https://builderswars.com", "https://www.builderswars.com"], "exact defensive plural origins")
    check(domains["defensive_plural"]["behavior"] == "single_permanent_redirect_to_equivalent_canonical_path_and_query", "path-and-query-preserving redirect contract")
    check(contract["current_evidence"]["redirect_active"] is False, "redirect is not falsely marked active")
    check("public_launch" in contract["non_implications"], "brand adoption does not imply launch")
    check("revenue" in contract["non_implications"], "brand adoption does not imply revenue")

    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    addendum = ADDENDUM_PATH.read_text(encoding="utf-8")
    research = RESEARCH_PATH.read_text(encoding="utf-8")
    plan = PLAN_PATH.read_text(encoding="utf-8")
    north_star = NORTH_STAR_PATH.read_text(encoding="utf-8")
    north_star_machine = json.loads(
        NORTH_STAR_MACHINE_PATH.read_text(encoding="utf-8"),
        object_pairs_hook=strict_object,
    )
    for _id, name, route in EXPECTED_CATEGORIES:
        check(f"**{name}**" in architecture, f"architecture names {name}")
        check(f"`{route}`" in architecture, f"architecture reserves {route}")
    check("ADOPTED — owner ruling, 2026-09-04" in architecture, "human contract adoption label")
    check("historical or compatibility terminology only" in architecture, "human contract legacy boundary")
    check("byte digests" in addendum and "historical bytes" in addendum, "foundation addendum preserves accepted bytes")
    check("not legal clearance" in research, "research disclaims trademark clearance")
    check("Current status: **blocked**" in plan, "execution plan records canonical-host blocker")
    check("Pull Request #24" in plan, "execution plan sequences the existing showcase branch")
    check("# BuilderWars North Star (legacy filename)" in north_star, "North Star public title reconciled")
    check("The full strategy remains a draft" in north_star, "brand ruling does not self-adopt the full North Star")
    check(north_star_machine["project_id"] == "builderwars", "North Star machine project id")
    check(north_star_machine["project_name"] == "BuilderWars", "North Star machine project name")
    check(north_star_machine["brand_architecture_ref"] == "docs/BUILDERWARS_BRAND_ARCHITECTURE.v1.json", "North Star machine brand reference")
    check(north_star_machine["review"]["final_ruling"] is None, "full North Star remains without a final ruling")
    check(
        any(item["source"] == "Owner ruling 2026-09-04" for item in north_star_machine["governing_rulings"]),
        "North Star machine records owner brand ruling",
    )

    print(f"PASS BuilderWars brand architecture ({CHECKS} checks); BRAND ADOPTED, NOT LAUNCHED")


if __name__ == "__main__":
    main()
