#!/usr/bin/env python3
"""Adversarial, network-free checks for prelaunch BuilderWars discoverability."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MOBILE = ROOT / "mobile-arena"
DOCS = ROOT / "docs"
CONTRACT_PATH = DOCS / "AGENTWARS_DISCOVERABILITY_CONTRACT.v1.json"
COPY_PATH = DOCS / "AGENTWARS_DISCOVERABILITY_LAUNCH_COPY.md"
EXPECTED_REQUIREMENTS = [
    "protected_runtime_configuration_pass",
    "source_bound_deployment_and_rollback_pass",
    "consented_tester_review_and_launch_authority_pass",
    "canonical_origin_verified",
    "served_byte_parity_verified",
    "robots_and_sitemap_rebuilt_for_exact_origin",
    "structured_data_validated_against_served_content",
]
EXPECTED_AUTHORITY = {
    "canonicalOrigin": False,
    "indexing": False,
    "launchCopyPublication": False,
    "publicLaunch": False,
    "sitemapPublication": False,
    "structuredDataPublication": False,
}
EXPECTED_TRUTH = {
    "audienceMeasured": False,
    "canonicalOriginConfigured": False,
    "indexingAuthorized": False,
    "rankingOrCitationProven": False,
    "sitemapPublished": False,
    "structuredDataPublished": False,
}
EXPECTED_ROBOTS = (
    "User-agent: *\n"
    "Disallow: /\n\n"
    "# BuilderWars Mobile Arena is a local launch candidate.\n"
    "# Indexing stays disabled until protected stages 11-13 pass.\n"
)
CHECKS = 0


class DiscoverabilityContractError(ValueError):
    """Fail-closed prelaunch discoverability refusal."""


def check(condition: bool, label: str) -> None:
    global CHECKS
    if not condition:
        raise AssertionError(label)
    CHECKS += 1
    print(f"[PASS] {label}")


def _exact_object(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise DiscoverabilityContractError(f"{label} fields are not exact")
    return value


def validate_contract(value: Any) -> dict[str, Any]:
    contract = _exact_object(
        value,
        {"schemaVersion", "status", "surface", "currentSource", "draftLaunchCopy", "activationRequirements", "authority", "truth"},
        "discoverability contract",
    )
    if contract["schemaVersion"] != "agentwars.discoverability-contract.v1":
        raise DiscoverabilityContractError("discoverability schema drift")
    if contract["status"] != "prelaunch_indexing_disabled" or contract["surface"] != "mobile-arena":
        raise DiscoverabilityContractError("discoverability status or surface drift")
    source = _exact_object(
        contract["currentSource"],
        {"title", "description", "robotsPolicy", "llmsStatus", "sitemapStatus", "canonicalOrigin", "structuredDataStatus"},
        "current source",
    )
    if source != {
        "title": "BuilderWars — Mobile Arena Exchange",
        "description": "BuilderWars local mobile Arena Exchange with reviewed competition receipts and a bounded demo fallback. No live providers, accounts, inference, rankings, or publication.",
        "robotsPolicy": "disallow_all",
        "llmsStatus": "prelaunch_orientation_only",
        "sitemapStatus": "withheld_until_source_bound_deployment",
        "canonicalOrigin": None,
        "structuredDataStatus": "withheld_until_served_content_is_verified",
    }:
        raise DiscoverabilityContractError("current source truth drift")
    launch_copy = _exact_object(
        contract["draftLaunchCopy"],
        {"status", "headline", "description", "evidenceBoundary"},
        "draft launch copy",
    )
    if launch_copy != {
        "status": "draft_not_published",
        "headline": "Watch agents compete. Verify every claim.",
        "description": "BuilderWars turns agent games into replayable competitions with evidence-linked receipts, harness-aware records, and versioned runbacks.",
        "evidenceBoundary": "Every public result must resolve to its scoped receipt and replay. A reviewed record is not a universal model ranking, provider attestation, identity claim, or production-execution claim.",
    }:
        raise DiscoverabilityContractError("draft launch copy drift")
    if contract["activationRequirements"] != EXPECTED_REQUIREMENTS:
        raise DiscoverabilityContractError("activation requirements drift")
    if contract["authority"] != EXPECTED_AUTHORITY or contract["truth"] != EXPECTED_TRUTH:
        raise DiscoverabilityContractError("discoverability authority or truth drift")
    return contract


def load_contract() -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise DiscoverabilityContractError(f"duplicate key {key}")
            result[key] = value
        return result

    return validate_contract(json.loads(CONTRACT_PATH.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates))


def refuses(candidate: dict[str, Any], label: str) -> None:
    try:
        validate_contract(candidate)
    except DiscoverabilityContractError:
        check(True, label)
    else:
        raise AssertionError(label)


def main() -> int:
    contract = load_contract()
    check(contract["status"] == "prelaunch_indexing_disabled", "contract keeps indexing disabled")
    check(all(value is False for value in contract["authority"].values()), "contract grants no publication or launch authority")
    check(all(value is False for value in contract["truth"].values()), "contract makes no audience, indexing, citation, or publication claim")

    html = (MOBILE / "index.html").read_text(encoding="utf-8")
    title = re.search(r"<title>([^<]+)</title>", html)
    description = re.search(r'<meta name="description" content="([^"]+)">', html)
    check(title is not None and title.group(1) == contract["currentSource"]["title"], "page title matches the truth contract")
    check(description is not None and description.group(1) == contract["currentSource"]["description"], "page description matches the truth contract")
    check('data-local-only="true"' in html, "page remains explicitly local-only")
    lowered = html.lower()
    check('rel="canonical"' not in lowered and "og:url" not in lowered, "unverified canonical and social URLs remain absent")
    check("application/ld+json" not in lowered, "structured data remains withheld before served-content proof")

    manifest = json.loads((MOBILE / "manifest.webmanifest").read_text(encoding="utf-8"))
    check(manifest["start_url"].startswith("./") and manifest["scope"] == "./", "manifest navigation remains origin-relative")
    check("Local Arena shell" in manifest["description"] and "live" not in manifest["description"].lower(), "manifest copy remains local and non-live")

    robots = (MOBILE / "robots.txt").read_text(encoding="utf-8")
    check(robots == EXPECTED_ROBOTS, "robots policy disallows every crawler before launch authority")
    llms = (MOBILE / "llms.txt").read_text(encoding="utf-8")
    check("Status: local prelaunch candidate. Indexing and publication are disabled." in llms, "llms orientation names prelaunch status")
    check("Canonical public origin: not configured." in llms, "llms orientation refuses a canonical-origin claim")
    check("explicitly not ranked" in llms and "No live provider" in llms, "llms orientation preserves ranking and provider boundaries")
    check(not (MOBILE / "sitemap.xml").exists(), "sitemap remains withheld before source-bound deployment")

    local_surfaces = "\n".join((html, json.dumps(manifest), robots, llms))
    check(re.search(r"https?://", local_surfaces, flags=re.IGNORECASE) is None, "prelaunch surfaces contain no unverified absolute origin")
    check("builderwars.com" not in local_surfaces.lower(), "prelaunch surfaces do not imply BuilderWars.com activation")

    copy_contract = COPY_PATH.read_text(encoding="utf-8")
    normalized_copy = " ".join(copy_contract.split())
    check("DRAFT ONLY — INDEXING AND PUBLICATION DISABLED" in copy_contract, "launch copy is visibly draft-only")
    check(contract["draftLaunchCopy"]["headline"] in normalized_copy and contract["draftLaunchCopy"]["description"] in normalized_copy, "human launch copy matches the machine contract")
    check(contract["draftLaunchCopy"]["evidenceBoundary"] in normalized_copy, "human copy preserves the exact evidence boundary")
    check("does not prove crawling" in normalized_copy and "traffic, leads, or revenue" in normalized_copy, "discoverability docs refuse outcome overclaims")
    check("stages 11–13 pass" in copy_contract, "copy activation is gated on every protected stage")

    hostile = copy.deepcopy(contract)
    hostile["unexpected"] = True
    refuses(hostile, "validator refuses unknown contract fields")
    hostile = copy.deepcopy(contract)
    hostile["currentSource"]["canonicalOrigin"] = "https://builderwars.com"
    refuses(hostile, "validator refuses an unverified canonical origin")
    hostile = copy.deepcopy(contract)
    hostile["authority"]["indexing"] = True
    refuses(hostile, "validator refuses indexing authority escalation")
    hostile = copy.deepcopy(contract)
    hostile["draftLaunchCopy"]["status"] = "published"
    refuses(hostile, "validator refuses launch-copy publication drift")
    hostile = copy.deepcopy(contract)
    hostile["activationRequirements"] = hostile["activationRequirements"][:-1]
    refuses(hostile, "validator refuses truncated activation requirements")

    print(f"AgentWars discoverability contract: PASS ({CHECKS} checks)")
    print("indexing disabled / no canonical origin / no sitemap / draft copy only / zero audience claim")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
