#!/usr/bin/env python3
"""Adversarial beta-capacity planning and local correctness checks."""

from __future__ import annotations

import ast
import concurrent.futures
import copy
import datetime as dt
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from provider_hub.local_runner import base64url_no_pad
from provider_hub_hosted import browser_gateway
from provider_hub_hosted.store import HostedControlPlaneStore
from publishing import capacity_readiness as capacity


CHECKS = 0
NOW = dt.datetime(2026, 9, 1, 12, 0, 0, tzinfo=dt.timezone.utc)


def check(condition: bool, label: str) -> None:
    global CHECKS
    if not condition:
        raise AssertionError(label)
    CHECKS += 1


def refuses(callable_, label: str) -> None:
    try:
        callable_()
    except capacity.CapacityReadinessError:
        check(True, label)
    else:
        raise AssertionError(label)


def reseal(value: dict[str, object], field: str) -> dict[str, object]:
    result = copy.deepcopy(value)
    result.pop(field, None)
    result[field] = capacity.digest(result)
    return result


def scenario(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "scenario_id": "bwcap_closed_beta_candidate",
        "candidate_label": "Operator-supplied closed beta candidate",
        "observation_window_seconds": 300,
        "authenticated_active_users": 100,
        "connected_runners": 20,
        "public_spectators": 500,
        "browser_operations_per_active_user_window": {
            "confirm_pairing": 1,
            "create_fixture_job": 3,
            "create_pairing": 1,
            "delete_owner": 0,
            "delete_runner": 0,
            "revoke_runner": 0,
        },
        "runner_polls_per_runner_window": 60,
        "runner_results_per_runner_window": 3,
        "public_replay_reads_per_spectator_window": 20,
        "peak_queued_jobs": 400,
        "peak_concurrent_attempts": 40,
        "public_creator_execution_enabled": False,
        "paid_compute_authorized": False,
    }
    values.update(overrides)
    return capacity.build_capacity_scenario(**values)


def local_correctness_probe() -> dict[str, object]:
    plan = capacity.LOCAL_CORRECTNESS_PROBE
    limiter = browser_gateway.InMemoryAccountRateLimiter()
    owners = ["awu1_" + base64url_no_pad(index.to_bytes(16, "big")) for index in range(1, plan["syntheticOwnerCount"] + 1)]
    calls = [owner for owner in owners for _ in range(plan["requestsPerOwner"])]

    def check_limiter(owner_id: str) -> tuple[str, bool]:
        return owner_id, limiter.check(owner_id, plan["limiterOperation"], now=NOW).allowed

    with concurrent.futures.ThreadPoolExecutor(max_workers=plan["concurrencyWorkers"]) as executor:
        decisions = list(executor.map(check_limiter, calls))
    allowed_by_owner = {owner: 0 for owner in owners}
    refused_by_owner = {owner: 0 for owner in owners}
    for owner, allowed in decisions:
        allowed_by_owner[owner] += int(allowed)
        refused_by_owner[owner] += int(not allowed)

    with HostedControlPlaneStore(":memory:") as reference_store:
        before = dict(reference_store.row_counts())
        job_ids = ["awj1_" + base64url_no_pad(index.to_bytes(16, "big")) for index in range(1, 65)]
        lookups = [job_ids[index % len(job_ids)] for index in range(plan["publicReplayLookupCount"])]
        with concurrent.futures.ThreadPoolExecutor(max_workers=plan["concurrencyWorkers"]) as executor:
            results = list(executor.map(reference_store.get_public_projection, lookups))
        after = dict(reference_store.row_counts())

    return capacity.build_local_correctness_observation(
        limiter_allowed=sum(allowed for _, allowed in decisions),
        limiter_refused=sum(not allowed for _, allowed in decisions),
        owners_with_exact_allowance=sum(
            count == plan["expectedAllowedPerOwner"] for count in allowed_by_owner.values()
        ),
        owners_with_exact_refusal=sum(
            count == plan["expectedRefusedPerOwner"] for count in refused_by_owner.values()
        ),
        public_replay_misses=sum(result is None for result in results),
        row_counts_before=before,
        row_counts_after=after,
    )


def main() -> int:
    contract = capacity.capacity_contract()
    check(contract["schemaVersion"] == capacity.CONTRACT_SCHEMA, "capacity schema is pinned")
    check(contract["contractStatus"] == "OPERATOR_INPUT_REQUIRED_LOCAL_CORRECTNESS_ONLY_PRODUCTION_HELD", "capacity contract requires operator input and holds production")
    check(capacity.verify_capacity_contract(contract) == contract, "canonical capacity contract verifies")
    unsigned = dict(contract)
    supplied_digest = unsigned.pop("contractDigest")
    check(capacity.digest(unsigned) == supplied_digest, "capacity contract digest verifies")
    check(contract["productionAuthority"] == capacity.PRODUCTION_AUTHORITY, "capacity authority fields are exact")
    check(all(type(flag) is bool and flag is False for flag in contract["productionAuthority"].values()), "every capacity authority flag is false")

    expected_policies = {
        "confirm_pairing": {"limit": 12, "windowSeconds": 60},
        "create_fixture_job": {"limit": 12, "windowSeconds": 60},
        "create_pairing": {"limit": 6, "windowSeconds": 60},
        "delete_owner": {"limit": 2, "windowSeconds": 300},
        "delete_runner": {"limit": 6, "windowSeconds": 60},
        "revoke_runner": {"limit": 6, "windowSeconds": 60},
    }
    limits = contract["referenceLimits"]
    check(limits["browserOperationRatePolicies"] == expected_policies, "capacity contract binds exact browser operation policies")
    check(
        limits["browserOperationRatePolicies"] == {
            operation: {"limit": policy[0], "windowSeconds": policy[1]}
            for operation, policy in sorted(browser_gateway.OPERATION_RATE_POLICIES.items())
        },
        "capacity policies match the gateway mapping",
    )
    check(limits["browserMaxBodyBytes"] == 16_384, "browser body cap is source bound")
    check(limits["runnerMaxBodyBytes"] == 65_536 and limits["runnerMaxHttpResponseBytes"] == 65_536, "runner request and response caps are source bound")
    check(limits["jsonMaxDepth"] == 32, "JSON depth cap is source bound")
    check(limits["pairingTtlSeconds"] == 600 and limits["pairingMaxClaimAttempts"] == 8, "pairing TTL and attempt cap are source bound")
    check(limits["defaultLeaseSeconds"] == 60 and limits["maximumLeaseSeconds"] == 300, "lease bounds are source bound")
    check(limits["nonceRetentionSeconds"] == 900, "nonce retention is source bound")
    check(limits["browserIdempotencyTtlSeconds"] == 86_400, "idempotency TTL is source bound")
    check(limits["browserMaxSealedResponseBytes"] == 131_072, "sealed response cap is source bound")
    check(limits["matchMaxAttempts"] == 3 and limits["matchMaxRenews"] == 5, "attempt and renewal caps are source bound")

    fields = contract["operatorInputFields"]
    template = contract["operatorInputTemplate"]
    check(set(fields) == set(template) == set(capacity.OPERATOR_INPUT_FIELDS), "operator input field and template sets are exact")
    check(all(value == "operator_required_not_recorded" or value is False for value in template.values()), "operator template invents no numeric target")
    check(template["publicCreatorExecutionEnabled"] is False and template["paidComputeAuthorized"] is False, "unsafe and paid execution remain disabled in the template")
    check(len(contract["unresolvedProductionEvidence"]) == 9, "nine production evidence classes remain unresolved")
    check(contract["unresolvedProductionEvidence"] == list(capacity.UNRESOLVED_PRODUCTION_EVIDENCE), "production evidence list is exact")
    check(len(contract["claimsBoundary"]) == 5, "five anti-overclaim boundaries are explicit")
    check("correctness_counts_are_not_latency_or_throughput_measurements" in contract["claimsBoundary"], "local correctness is not presented as throughput")

    candidate = scenario()
    check(candidate["schemaVersion"] == capacity.SCENARIO_SCHEMA, "candidate scenario schema is pinned")
    check(capacity.verify_capacity_scenario(candidate) == candidate, "candidate scenario verifies")
    check(candidate == scenario(), "candidate scenario is deterministic")
    derived = candidate["derivedRequestEnvelope"]
    check(derived["browserRequestsPerUserWindow"] == 5, "browser requests per user are derived")
    check(derived["browserRequestsAggregate"] == 500, "aggregate browser requests are derived")
    check(derived["runnerSignedRequestsAggregate"] == 1_260, "aggregate signed runner requests are derived")
    check(derived["publicReplayReadsAggregate"] == 10_000, "aggregate public replay reads are derived")
    check(derived["totalRequestsAggregate"] == 11_760, "total request envelope is exact")
    check(derived["rateRational"] == {"numerator": 11_760, "denominatorSeconds": 300}, "request rate is an exact rational without float drift")
    check(candidate["browserReferencePolicyFit"] is True, "candidate fits local per-owner browser policies")
    check(candidate["outcome"] == "READY_FOR_PROTECTED_PRODUCTION_CAPACITY_TEST_NOT_LAUNCH", "fit candidate advances only to a protected capacity test")
    check(candidate["productionCapacityVerified"] is False and candidate["performanceSloApproved"] is False, "candidate proves no production capacity or SLO")
    check(all(flag is False for flag in candidate["productionAuthority"].values()), "candidate grants zero production authority")

    overloaded_operations = dict(candidate["operatorInputs"]["browserOperationsPerActiveUserWindow"])
    overloaded_operations["create_pairing"] = 31
    overloaded = scenario(browser_operations_per_active_user_window=overloaded_operations)
    check(overloaded["browserReferencePolicyFit"] is False, "over-policy candidate fails the local policy fit")
    check(overloaded["outcome"] == "REFUSED_LOCAL_BROWSER_POLICY_EXCEEDED", "over-policy candidate is refused")
    check(capacity.verify_capacity_scenario(overloaded) == overloaded, "refused candidate remains verifiable evidence")

    refuses(lambda: scenario(public_creator_execution_enabled=True), "capacity planning refuses public creator execution")
    refuses(lambda: scenario(paid_compute_authorized=True), "capacity planning refuses paid compute authority")
    refuses(lambda: scenario(observation_window_seconds=301), "capacity planning refuses a non-aligned window")
    refuses(lambda: scenario(authenticated_active_users=0), "capacity planning refuses zero active users")
    refuses(lambda: scenario(candidate_label=" x"), "capacity planning refuses malformed labels")
    refuses(lambda: scenario(scenario_id="bad"), "capacity planning refuses malformed scenario ids")
    missing_operation = dict(candidate["operatorInputs"]["browserOperationsPerActiveUserWindow"]); missing_operation.pop("delete_owner")
    refuses(lambda: scenario(browser_operations_per_active_user_window=missing_operation), "capacity planning refuses incomplete operation mixes")
    extra_operation = dict(candidate["operatorInputs"]["browserOperationsPerActiveUserWindow"]); extra_operation["unknown"] = 1
    refuses(lambda: scenario(browser_operations_per_active_user_window=extra_operation), "capacity planning refuses unknown browser operations")

    observation = local_correctness_probe()
    check(observation["schemaVersion"] == capacity.OBSERVATION_SCHEMA, "local observation schema is pinned")
    check(capacity.verify_local_correctness_observation(observation) == observation, "local correctness observation verifies")
    check(observation == local_correctness_probe(), "local correctness observation is deterministic")
    check(observation["status"] == "LOCAL_CORRECTNESS_PASS", "local correctness probe passes")
    check(observation["observedCounts"]["limiterAllowed"] == 192, "32 owners receive exactly six allowed mutations")
    check(observation["observedCounts"]["limiterRefused"] == 32, "32 owners receive exactly one rate refusal")
    check(observation["observedCounts"]["ownersWithExactAllowance"] == 32, "every owner receives exactly six allowances")
    check(observation["observedCounts"]["ownersWithExactRefusal"] == 32, "every owner receives exactly one refusal")
    check(observation["observedCounts"]["publicReplayMisses"] == 1_024, "all bounded spectator misses remain non-mutating")
    check(all(observation["checks"].values()), "every local correctness invariant passes")
    check(observation["observedCounts"]["rowCountsBefore"] == observation["observedCounts"]["rowCountsAfter"], "spectator misses preserve store state")
    check(all(count == 0 for count in observation["observedCounts"]["rowCountsAfter"].values()), "ephemeral store remains empty")
    for field in ("performanceThresholdApplied", "throughputClaimed", "productionTargetObserved", "networkUsed", "providerCalled"):
        check(observation[field] is False, f"local observation keeps {field} false")
    check(all(flag is False for flag in observation["productionAuthority"].values()), "local observation grants zero production authority")

    hostile_contracts: list[tuple[dict[str, object], str]] = []
    hostile = copy.deepcopy(contract); hostile["productionAuthority"]["betaTargetApproved"] = True; hostile_contracts.append((reseal(hostile, "contractDigest"), "capacity contract refuses beta approval"))
    hostile = copy.deepcopy(contract); hostile["operatorInputTemplate"]["authenticatedActiveUsers"] = 100; hostile_contracts.append((reseal(hostile, "contractDigest"), "capacity contract refuses invented population"))
    hostile = copy.deepcopy(contract); hostile["referenceLimits"]["browserOperationRatePolicies"]["create_pairing"]["limit"] = 100; hostile_contracts.append((reseal(hostile, "contractDigest"), "capacity contract refuses policy drift"))
    hostile = copy.deepcopy(contract); hostile["unresolvedProductionEvidence"] = []; hostile_contracts.append((reseal(hostile, "contractDigest"), "capacity contract refuses hidden production evidence"))
    for hostile_contract, label in hostile_contracts:
        refuses(lambda item=hostile_contract: capacity.verify_capacity_contract(item), label)

    hostile_scenarios: list[tuple[dict[str, object], str]] = []
    hostile = copy.deepcopy(candidate); hostile["productionCapacityVerified"] = True; hostile_scenarios.append((reseal(hostile, "scenarioDigest"), "scenario refuses production capacity proof"))
    hostile = copy.deepcopy(candidate); hostile["productionAuthority"]["launchable"] = True; hostile_scenarios.append((reseal(hostile, "scenarioDigest"), "scenario refuses launch authority"))
    hostile = copy.deepcopy(candidate); hostile["derivedRequestEnvelope"]["totalRequestsAggregate"] += 1; hostile_scenarios.append((reseal(hostile, "scenarioDigest"), "scenario refuses derived-count drift"))
    hostile = copy.deepcopy(candidate); hostile["outcome"] = "LAUNCH"; hostile_scenarios.append((reseal(hostile, "scenarioDigest"), "scenario refuses invented launch outcome"))
    hostile = copy.deepcopy(candidate); hostile["productionEvidenceRequired"] = []; hostile_scenarios.append((reseal(hostile, "scenarioDigest"), "scenario refuses removed production evidence"))
    for hostile_scenario, label in hostile_scenarios:
        refuses(lambda item=hostile_scenario: capacity.verify_capacity_scenario(item), label)

    hostile_observations: list[tuple[dict[str, object], str]] = []
    hostile = copy.deepcopy(observation); hostile["throughputClaimed"] = True; hostile_observations.append((reseal(hostile, "observationDigest"), "observation refuses throughput claim"))
    hostile = copy.deepcopy(observation); hostile["productionTargetObserved"] = True; hostile_observations.append((reseal(hostile, "observationDigest"), "observation refuses production target claim"))
    hostile = copy.deepcopy(observation); hostile["observedCounts"]["limiterAllowed"] -= 1; hostile_observations.append((reseal(hostile, "observationDigest"), "observation refuses failed limiter count"))
    hostile = copy.deepcopy(observation); hostile["observedCounts"]["ownersWithExactAllowance"] -= 1; hostile_observations.append((reseal(hostile, "observationDigest"), "observation refuses owner-distribution drift"))
    hostile = copy.deepcopy(observation); hostile["productionAuthority"]["productionCapacityVerified"] = True; hostile_observations.append((reseal(hostile, "observationDigest"), "observation refuses production authority"))
    for hostile_observation, label in hostile_observations:
        refuses(lambda item=hostile_observation: capacity.verify_local_correctness_observation(item), label)

    source_path = ROOT / "publishing" / "capacity_readiness.py"
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
    check(imports <= {"__future__", "hashlib", "json", "re", "provider_hub", "provider_hub_hosted"}, "capacity contract imports only pure or reviewed local modules")
    called_names = {
        node.func.id for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    for forbidden_call in ("open", "exec", "eval", "compile", "input", "breakpoint"):
        check(forbidden_call not in called_names, f"capacity contract excludes {forbidden_call}")
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    for forbidden_attribute in ("system", "popen", "run", "urlopen", "connect", "unlink", "remove", "rmtree", "write_text", "write_bytes"):
        check(forbidden_attribute not in attributes, f"capacity contract excludes side-effect attribute {forbidden_attribute}")

    print(f"BuilderWars beta capacity readiness: PASS ({CHECKS} checks)")
    print("operator-fill target / exact request envelope / 32-owner limiter concurrency / 1024 non-mutating spectator misses / no throughput or production claim / zero authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
