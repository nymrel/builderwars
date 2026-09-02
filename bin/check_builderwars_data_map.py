#!/usr/bin/env python3
"""Adversarial checks for the BuilderWars source-bound reference data map."""

from __future__ import annotations

import ast
import copy
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publishing import reference_data_map as dm
from publishing import retention_recovery as rr


CHECKS = 0


def check(condition: bool, label: str) -> None:
    global CHECKS
    if not condition:
        raise AssertionError(label)
    CHECKS += 1


def refuses(callable_, label: str) -> None:
    try:
        callable_()
    except dm.ReferenceDataMapError:
        check(True, label)
    else:
        raise AssertionError(label)


def reseal(value: dict[str, object]) -> dict[str, object]:
    result = copy.deepcopy(value)
    result.pop("contractDigest", None)
    result["contractDigest"] = dm.digest(result)
    return result


def main() -> int:
    contract = dm.reference_data_map_contract()
    check(contract["schemaVersion"] == dm.CONTRACT_SCHEMA, "data-map schema is pinned")
    check(contract["mapStatus"] == "SOURCE_BOUND_REFERENCE_CANDIDATE_PRODUCTION_FACTS_HELD", "data map is explicitly a held reference candidate")
    check(contract["scope"] == "repository_implemented_reference_surfaces_only", "data map scope is repository bounded")
    check(dm.verify_reference_data_map(contract) == contract, "canonical data map verifies")
    unsigned = dict(contract)
    supplied_digest = unsigned.pop("contractDigest")
    check(dm.digest(unsigned) == supplied_digest, "canonical data-map digest verifies")
    check(contract["retentionContractSchema"] == rr.CONTRACT_SCHEMA, "data map binds the retention schema")
    check(contract["retentionContractDigest"] == rr.retention_recovery_contract()["contractDigest"], "data map binds the exact retention contract")

    authority = contract["productionAuthority"]
    check(authority == dm.PRODUCTION_AUTHORITY, "production authority fields are exact")
    check(all(type(flag) is bool and flag is False for flag in authority.values()), "every production authority flag is false")
    check(authority["launchable"] is False and authority["publicLaunchApproved"] is False, "data map grants no launch authority")

    systems = contract["systems"]
    system_ids = [row["systemId"] for row in systems]
    check(len(system_ids) == 6 and len(set(system_ids)) == 6, "six unique reference systems are mapped")
    check(set(system_ids) == {
        "browser_local_arena", "browser_static_cache", "hosted_reference_store",
        "customer_local_runner", "reviewed_public_artifacts", "local_launch_evidence",
    }, "reference systems cover browser, hosted, runner, public, and evidence custody")
    check(all(row["subprocessors"] == [] for row in systems), "no subprocessor is invented")
    check(all("production" not in row["regionOrResidency"] or "not_a_production_region_claim" in row["regionOrResidency"] or row["regionOrResidency"] == "operator_required_not_recorded" for row in systems), "system locations do not claim production residency")
    hosted_system = next(row for row in systems if row["systemId"] == "hosted_reference_store")
    check(hosted_system["productionStatus"] == "sqlite_reference_only_not_a_production_store", "SQLite is not represented as a production store")
    check(hosted_system["regionOrResidency"] == "operator_required_not_recorded", "hosted region remains unknown")

    data_sets = contract["dataSets"]
    data_set_ids = [row["dataSetId"] for row in data_sets]
    check(len(data_sets) == 19 and len(set(data_set_ids)) == 19, "nineteen unique reference datasets are mapped")
    check(all(row["systemId"] in system_ids for row in data_sets), "every dataset belongs to a mapped system")
    check(all(type(row["dataClasses"]) is list and row["dataClasses"] for row in data_sets), "every dataset names non-empty data classes")
    check(all(type(row["containsDirectIdentifiers"]) is bool for row in data_sets), "identifier classification is explicit")
    check(all(type(row["containsSecrets"]) is bool for row in data_sets), "secret classification is explicit")
    check(all(type(row["customerLocalOnly"]) is bool for row in data_sets), "customer-local classification is explicit")
    check(all(type(row["publicEligible"]) is bool for row in data_sets), "public eligibility is explicit")

    expected_tables = {
        "owners", "pairing_challenges", "runners", "nonces", "jobs", "attempts",
        "results", "replay_projections", "browser_idempotency",
    }
    store_source = (ROOT / "provider_hub_hosted" / "store.py").read_text(encoding="utf-8")
    discovered_tables = set(re.findall(r"CREATE TABLE IF NOT EXISTS ([a-z_]+)", store_source))
    check(discovered_tables == expected_tables, "all and only current hosted reference tables are discovered")
    mapped_tables = {
        row["referenceLocation"].split(":", 1)[1]
        for row in data_sets if row["referenceLocation"].startswith("sqlite:")
    }
    check(mapped_tables == expected_tables, "all and only hosted reference tables are mapped")

    app_source = (ROOT / "mobile-arena" / "app.js").read_text(encoding="utf-8")
    expected_local_keys = {
        "builderwars.mobile-arena.blueprint.v1",
        "builderwars.mobile-arena.starter-guide.v1",
    }
    discovered_local_keys = set(re.findall(r'"(builderwars\.mobile-arena\.[a-z-]+\.v1)"', app_source))
    mapped_local_keys = {
        row["referenceLocation"].split(":", 1)[1]
        for row in data_sets if row["referenceLocation"].startswith("localStorage:")
    }
    check(discovered_local_keys == expected_local_keys, "all and only current browser storage keys are discovered")
    check(mapped_local_keys == expected_local_keys, "all and only browser storage keys are mapped")
    service_worker_source = (ROOT / "mobile-arena" / "sw.js").read_text(encoding="utf-8")
    cache_match = re.search(r'CACHE_NAME\s*=\s*"([^"]+)"', service_worker_source)
    check(cache_match is not None and cache_match.group(1) == "builderwars-mobile-arena-v38", "current service-worker cache is discovered")
    check(any(row["referenceLocation"] == "CacheStorage:builderwars-mobile-arena-v38" for row in data_sets), "current service-worker cache is mapped")

    mapped_resource_classes = {row["retentionResourceClass"] for row in data_sets}
    check(set(rr.RESOURCE_POLICIES) <= mapped_resource_classes, "every retention resource class appears in the data map")
    for row in data_sets:
        resource_class = row["retentionResourceClass"]
        if resource_class in rr.RESOURCE_POLICIES:
            policy = rr.RESOURCE_POLICIES[resource_class]
            check(row["retentionClass"] == policy["retentionClass"], f"{row['dataSetId']} binds the retention class")
            check(row["deletionDisposition"] == policy["disposition"], f"{row['dataSetId']} binds the deletion disposition")
        else:
            check(resource_class == "operator_required_not_recorded", f"{row['dataSetId']} uses only the explicit policy hold")
            check(row["retentionClass"] == "operator_required_not_recorded", f"{row['dataSetId']} invents no retention period")
            check(row["deletionDisposition"] == "operator_required_not_recorded", f"{row['dataSetId']} invents no deletion behavior")

    provider_authority = next(row for row in data_sets if row["dataSetId"] == "customer_provider_authority")
    check(provider_authority["customerLocalOnly"] is True, "provider authority stays customer-local")
    check(provider_authority["containsSecrets"] is True and provider_authority["publicEligible"] is False, "provider authority is secret and never public eligible")
    check(provider_authority["productionStatus"] == "must_never_enter_hosted_control_plane_or_public_artifacts", "provider secret boundary is explicit")
    blueprint = next(row for row in data_sets if row["dataSetId"] == "browser_private_blueprint")
    check(blueprint["customerLocalOnly"] is True and blueprint["publicEligible"] is False, "browser blueprint remains private and local")
    hosted = [row for row in data_sets if row["systemId"] == "hosted_reference_store"]
    check(all(row["publicEligible"] is False for row in hosted), "no hosted table is directly public eligible")
    check(all("provider_api_keys" not in row["dataClasses"] and "subscription_sessions" not in row["dataClasses"] for row in hosted), "hosted reference tables contain no raw provider authority class")
    public_sets = [row for row in data_sets if row["systemId"] == "reviewed_public_artifacts"]
    check(len(public_sets) == 2 and all(row["publicEligible"] is True for row in public_sets), "only reviewed receipt and replay datasets are publication candidates")
    check(all(row["containsDirectIdentifiers"] is False and row["containsSecrets"] is False for row in public_sets), "reviewed public datasets contain no classified identities or secrets")

    allowlist = contract["publicProjectionAllowlist"]
    denylist = contract["publicProjectionDenylist"]
    check(allowlist == sorted(allowlist) and len(set(allowlist)) == len(allowlist), "public allowlist is sorted and unique")
    check(denylist == sorted(denylist) and len(set(denylist)) == len(denylist), "public denylist is sorted and unique")
    check(set(allowlist).isdisjoint(denylist), "public allowlist and denylist do not overlap")
    for forbidden in (
        "raw_prompt", "raw_model_output", "provider_api_key", "provider_access_token",
        "provider_refresh_token", "subscription_cookie", "pairing_secret", "opaque_owner_id",
        "clerk_subject", "email_address", "ip_address", "sealed_response", "input_bytes_base64url",
    ):
        check(forbidden in denylist, f"public projection denies {forbidden}")

    flows = contract["dataFlows"]
    check([row["flowId"] for row in flows] == [f"DF-{index:03d}" for index in range(1, 6)], "five data flows have stable contiguous ids")
    check(all(row["sourceSystemId"] in system_ids and row["destinationSystemId"] in system_ids for row in flows), "every data flow stays within mapped systems")
    local_provider_flow = next(row for row in flows if row["flowId"] == "DF-003")
    check(local_provider_flow["sourceSystemId"] == local_provider_flow["destinationSystemId"] == "customer_local_runner", "provider authority does not flow to hosted systems")
    publication_flow = next(row for row in flows if row["flowId"] == "DF-004")
    check(publication_flow["referenceChannel"] == "explicit_reviewed_allowlist_only", "publication flow is reviewed and allowlisted")

    unresolved = contract["unresolvedProductionFacts"]
    check([row["factId"] for row in unresolved] == [f"UPF-{index:03d}" for index in range(1, 9)], "eight unresolved production facts have stable ids")
    check(all("required_not_recorded" in row["status"] for row in unresolved), "every production fact remains visibly unresolved")
    unresolved_names = {row["fact"] for row in unresolved}
    for expected in (
        "production_system_inventory_and_owners",
        "production_regions_residency_and_cross_border_transfers",
        "subprocessors_and_contractual_roles",
        "processing_purposes_legal_basis_privacy_notice_and_age_obligations",
        "exact_retention_periods_and_policy_owners",
        "deletion_propagation_targets_timing_and_dsar_process",
        "backup_destinations_encryption_access_retention_and_restore_rto_rpo",
        "production_observability_storage_sampling_and_support_access",
    ):
        check(expected in unresolved_names, f"unresolved production fact is retained: {expected}")

    anchors = contract["sourceAnchors"]
    check(len(anchors) == 10 and len({row["path"] for row in anchors}) == 10, "ten unique source files ground the data map")
    for anchor in anchors:
        source = (ROOT / anchor["path"]).read_text(encoding="utf-8")
        check(anchor["symbol"] in source, f"source anchor resolves: {anchor['path']}")

    hostile_contracts: list[tuple[dict[str, object], str]] = []
    hostile = copy.deepcopy(contract); hostile["productionAuthority"]["productionInventoryApproved"] = True; hostile_contracts.append((reseal(hostile), "data map refuses production inventory approval"))
    hostile = copy.deepcopy(contract); hostile["productionAuthority"]["launchable"] = True; hostile_contracts.append((reseal(hostile), "data map refuses launch authority"))
    hostile = copy.deepcopy(contract); hostile["systems"][2]["regionOrResidency"] = "us-west"; hostile_contracts.append((reseal(hostile), "data map refuses invented production region"))
    hostile = copy.deepcopy(contract); hostile["systems"][2]["subprocessors"] = ["invented_vendor"]; hostile_contracts.append((reseal(hostile), "data map refuses invented subprocessor"))
    hostile = copy.deepcopy(contract); hostile["dataSets"] = hostile["dataSets"][:-1]; hostile_contracts.append((reseal(hostile), "data map refuses missing dataset"))
    hostile = copy.deepcopy(contract); hostile["dataSets"][3]["publicEligible"] = True; hostile_contracts.append((reseal(hostile), "data map refuses direct publication of hosted owner state"))
    hostile = copy.deepcopy(contract); hostile["dataSets"][12]["publicEligible"] = True; hostile_contracts.append((reseal(hostile), "data map refuses public provider authority"))
    hostile = copy.deepcopy(contract); hostile["publicProjectionDenylist"].remove("raw_prompt"); hostile_contracts.append((reseal(hostile), "data map refuses removed prompt deny rule"))
    hostile = copy.deepcopy(contract); hostile["unresolvedProductionFacts"] = []; hostile_contracts.append((reseal(hostile), "data map refuses hidden production unknowns"))
    hostile = copy.deepcopy(contract); hostile["retentionContractDigest"] = "0" * 64; hostile_contracts.append((reseal(hostile), "data map refuses retention-contract drift"))
    hostile = copy.deepcopy(contract); hostile["extra"] = "field"; hostile_contracts.append((reseal(hostile), "data map refuses unknown fields"))
    for hostile_contract, label in hostile_contracts:
        refuses(lambda candidate=hostile_contract: dm.verify_reference_data_map(candidate), label)
    refuses(lambda: dm.verify_reference_data_map([]), "data map refuses non-object input")

    source_path = ROOT / "publishing" / "reference_data_map.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imports = {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    } | {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    check(imports <= {"__future__", "hashlib", "json", "publishing"}, "data-map contract imports only pure modules")
    called_names = {
        node.func.id for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    for forbidden_call in ("open", "exec", "eval", "compile", "input", "breakpoint"):
        check(forbidden_call not in called_names, f"data-map contract excludes {forbidden_call}")
    attributes = {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }
    for forbidden_attribute in ("system", "popen", "run", "urlopen", "connect", "unlink", "remove", "rmtree", "write_text", "write_bytes"):
        check(forbidden_attribute not in attributes, f"data-map contract excludes side-effect attribute {forbidden_attribute}")

    print(f"BuilderWars source-bound reference data map: PASS ({CHECKS} checks)")
    print("6 systems / 19 datasets / 9 hosted tables / 5 flows / 8 production facts held / zero authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
