"""Deterministic BuilderWars beta-capacity planning contract.

This module turns explicit operator inputs into a source-bound capacity-test
candidate. It never selects a beta target, runs a benchmark, observes a
deployment, activates a limiter, authorizes provider spend, or grants launch
authority. The fixed local probe described here tests concurrency correctness
only; it is intentionally not a throughput benchmark.
"""

from __future__ import annotations

import hashlib
import json
import re

from provider_hub import local_runner, match_worker
from provider_hub_hosted import browser_gateway, handlers, store


CONTRACT_SCHEMA = "builderwars.beta-capacity-contract/1"
SCENARIO_SCHEMA = "builderwars.beta-capacity-scenario/1"
OBSERVATION_SCHEMA = "builderwars.local-capacity-correctness-observation/1"
SCENARIO_ID_RE = re.compile(r"^bwcap_[a-z0-9][a-z0-9_-]{2,47}$")

PRODUCTION_AUTHORITY = {
    "betaTargetApproved": False,
    "productionLoadTestExecuted": False,
    "productionCapacityVerified": False,
    "durableEdgeLimitsActive": False,
    "durableServiceLimitsActive": False,
    "durableTenantLimitsActive": False,
    "productionBackpressureVerified": False,
    "productionAlertingVerified": False,
    "providerSpendAuthorized": False,
    "publicCreatorExecutionAuthorized": False,
    "launchable": False,
}

OPERATOR_INPUT_FIELDS = {
    "scenarioId": {"type": "string", "constraint": "bwcap_[a-z0-9][a-z0-9_-]{2,47}"},
    "candidateLabel": {"type": "string", "minimumLength": 3, "maximumLength": 80},
    "observationWindowSeconds": {"type": "integer", "minimum": 300, "maximum": 86_400, "multipleOf": 300},
    "authenticatedActiveUsers": {"type": "integer", "minimum": 1, "maximum": 1_000_000},
    "connectedRunners": {"type": "integer", "minimum": 0, "maximum": 1_000_000},
    "publicSpectators": {"type": "integer", "minimum": 0, "maximum": 10_000_000},
    "browserOperationsPerActiveUserWindow": {
        "type": "exact_operation_integer_map", "minimum": 0, "maximum": 100_000,
    },
    "runnerPollsPerRunnerWindow": {"type": "integer", "minimum": 0, "maximum": 100_000},
    "runnerResultsPerRunnerWindow": {"type": "integer", "minimum": 0, "maximum": 100_000},
    "publicReplayReadsPerSpectatorWindow": {"type": "integer", "minimum": 0, "maximum": 100_000},
    "peakQueuedJobs": {"type": "integer", "minimum": 0, "maximum": 100_000_000},
    "peakConcurrentAttempts": {"type": "integer", "minimum": 0, "maximum": 10_000_000},
    "publicCreatorExecutionEnabled": {"type": "boolean", "const": False},
    "paidComputeAuthorized": {"type": "boolean", "const": False},
}

OPERATOR_INPUT_TEMPLATE = {
    field: False if specification.get("const") is False else "operator_required_not_recorded"
    for field, specification in OPERATOR_INPUT_FIELDS.items()
}

LOCAL_CORRECTNESS_PROBE = {
    "probeClass": "local_correctness_probe_not_throughput_benchmark",
    "limiterOperation": "create_pairing",
    "syntheticOwnerCount": 32,
    "requestsPerOwner": 7,
    "concurrencyWorkers": 16,
    "expectedAllowedPerOwner": 6,
    "expectedRefusedPerOwner": 1,
    "publicReplayLookupCount": 1_024,
    "expectedPublicReplayMissCount": 1_024,
    "networkUsed": False,
    "providerCalled": False,
    "performanceThresholdApplied": False,
    "throughputClaimed": False,
    "productionTargetObserved": False,
}

UNRESOLVED_PRODUCTION_EVIDENCE = (
    "operator_approved_beta_population_and_request_mix",
    "production_edge_service_tenant_and_global_limit_configuration",
    "production_store_queue_cache_and_connection_pool_topology",
    "source_bound_load_generator_and_sanitized_test_tenants",
    "production_latency_saturation_error_and_queue_thresholds",
    "production_cost_budget_and_paid_provider_authority",
    "production_observability_alert_delivery_and_staffed_response",
    "backpressure_degradation_recovery_and_rollback_rehearsal",
    "post_test_cleanup_and_capacity_acceptance_receipt",
)


class CapacityReadinessError(ValueError):
    """Raised when a capacity input, candidate, or observation drifts."""


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _clone(value: object) -> object:
    return json.loads(canonical_bytes(value).decode("ascii"))


def _exact(value: object, fields: set[str], label: str) -> dict[str, object]:
    if type(value) is not dict or set(value) != fields:
        raise CapacityReadinessError(f"{label} fields drift")
    return value


def _bounded_integer(value: object, field: str) -> int:
    specification = OPERATOR_INPUT_FIELDS[field]
    if (
        type(value) is not int
        or value < specification["minimum"]
        or value > specification["maximum"]
    ):
        raise CapacityReadinessError(f"{field} is outside the planning bounds")
    multiple = specification.get("multipleOf")
    if type(multiple) is int and value % multiple != 0:
        raise CapacityReadinessError(f"{field} must be a multiple of {multiple}")
    return value


def _false_authority(value: object, label: str) -> dict[str, bool]:
    if type(value) is not dict or set(value) != set(PRODUCTION_AUTHORITY):
        raise CapacityReadinessError(f"{label} production authority fields drift")
    if any(type(flag) is not bool or flag is not False for flag in value.values()):
        raise CapacityReadinessError(f"{label} cannot claim production authority")
    return dict(PRODUCTION_AUTHORITY)


def _verify_digest(value: dict[str, object], field: str, label: str) -> None:
    supplied = value.get(field)
    if type(supplied) is not str or re.fullmatch(r"[0-9a-f]{64}", supplied) is None:
        raise CapacityReadinessError(f"{label} digest is malformed")
    unsigned = dict(value)
    unsigned.pop(field)
    if digest(unsigned) != supplied:
        raise CapacityReadinessError(f"{label} digest mismatch")


def _reference_limits() -> dict[str, object]:
    return {
        "browserMaxBodyBytes": browser_gateway.MAX_BROWSER_BODY_BYTES,
        "runnerMaxBodyBytes": local_runner.MAX_BODY_BYTES,
        "runnerMaxHttpResponseBytes": local_runner.MAX_HTTP_BYTES,
        "jsonMaxDepth": handlers.MAX_JSON_DEPTH,
        "pairingTtlSeconds": store.PAIRING_TTL_SECONDS,
        "pairingMaxClaimAttempts": store.PAIRING_MAX_CLAIM_ATTEMPTS,
        "defaultLeaseSeconds": store.LEASE_SECONDS,
        "maximumLeaseSeconds": 300,
        "nonceRetentionSeconds": store.NONCE_RETENTION_SECONDS,
        "signedRequestMaxAgeSeconds": store.MAX_REQUEST_AGE_SECONDS,
        "signedRequestMaxFutureSeconds": store.MAX_REQUEST_FUTURE_SECONDS,
        "browserIdempotencyTtlSeconds": store.BROWSER_IDEMPOTENCY_TTL_SECONDS,
        "browserMaxSealedResponseBytes": store.MAX_SEALED_BROWSER_RESPONSE_BYTES,
        "matchMaxAttempts": match_worker.MATCH_JOB_MAX_ATTEMPTS,
        "matchMaxRenews": match_worker.MATCH_JOB_MAX_RENEWS,
        "browserOperationRatePolicies": {
            operation: {"limit": limit, "windowSeconds": window_seconds}
            for operation, (limit, window_seconds) in sorted(browser_gateway.OPERATION_RATE_POLICIES.items())
        },
    }


def capacity_contract() -> dict[str, object]:
    contract: dict[str, object] = {
        "schemaVersion": CONTRACT_SCHEMA,
        "contractStatus": "OPERATOR_INPUT_REQUIRED_LOCAL_CORRECTNESS_ONLY_PRODUCTION_HELD",
        "referenceLimits": _reference_limits(),
        "operatorInputFields": _clone(OPERATOR_INPUT_FIELDS),
        "operatorInputTemplate": _clone(OPERATOR_INPUT_TEMPLATE),
        "localCorrectnessProbe": _clone(LOCAL_CORRECTNESS_PROBE),
        "candidateOutcomes": [
            "READY_FOR_PROTECTED_PRODUCTION_CAPACITY_TEST_NOT_LAUNCH",
            "REFUSED_LOCAL_BROWSER_POLICY_EXCEEDED",
        ],
        "unresolvedProductionEvidence": list(UNRESOLVED_PRODUCTION_EVIDENCE),
        "claimsBoundary": [
            "local_fixed_window_atomicity_is_not_durable_rate_limit_proof",
            "ephemeral_sqlite_concurrency_is_not_production_store_capacity",
            "correctness_counts_are_not_latency_or_throughput_measurements",
            "no_default_population_request_mix_cost_budget_or_slo_is_invented",
            "a_candidate_is_only_an_input_to_a_protected_load_test",
        ],
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    contract["contractDigest"] = digest(contract)
    return contract


def verify_capacity_contract(value: object) -> dict[str, object]:
    if value != capacity_contract():
        raise CapacityReadinessError("capacity contract does not match reviewed source")
    _false_authority(value.get("productionAuthority") if type(value) is dict else None, "capacity contract")
    return dict(value)


def build_capacity_scenario(
    *,
    scenario_id: str,
    candidate_label: str,
    observation_window_seconds: int,
    authenticated_active_users: int,
    connected_runners: int,
    public_spectators: int,
    browser_operations_per_active_user_window: object,
    runner_polls_per_runner_window: int,
    runner_results_per_runner_window: int,
    public_replay_reads_per_spectator_window: int,
    peak_queued_jobs: int,
    peak_concurrent_attempts: int,
    public_creator_execution_enabled: bool,
    paid_compute_authorized: bool,
) -> dict[str, object]:
    if type(scenario_id) is not str or SCENARIO_ID_RE.fullmatch(scenario_id) is None:
        raise CapacityReadinessError("scenarioId is malformed")
    if type(candidate_label) is not str or not 3 <= len(candidate_label) <= 80 or candidate_label != candidate_label.strip():
        raise CapacityReadinessError("candidateLabel is malformed")
    window = _bounded_integer(observation_window_seconds, "observationWindowSeconds")
    users = _bounded_integer(authenticated_active_users, "authenticatedActiveUsers")
    runners = _bounded_integer(connected_runners, "connectedRunners")
    spectators = _bounded_integer(public_spectators, "publicSpectators")
    runner_polls = _bounded_integer(runner_polls_per_runner_window, "runnerPollsPerRunnerWindow")
    runner_results = _bounded_integer(runner_results_per_runner_window, "runnerResultsPerRunnerWindow")
    replay_reads = _bounded_integer(public_replay_reads_per_spectator_window, "publicReplayReadsPerSpectatorWindow")
    queued_jobs = _bounded_integer(peak_queued_jobs, "peakQueuedJobs")
    concurrent_attempts = _bounded_integer(peak_concurrent_attempts, "peakConcurrentAttempts")
    if public_creator_execution_enabled is not False:
        raise CapacityReadinessError("public creator execution must remain disabled")
    if paid_compute_authorized is not False:
        raise CapacityReadinessError("capacity planning cannot authorize paid compute")

    policies = browser_gateway.OPERATION_RATE_POLICIES
    operations = _exact(
        browser_operations_per_active_user_window,
        set(policies),
        "browserOperationsPerActiveUserWindow",
    )
    operation_budgets: list[dict[str, object]] = []
    browser_per_user = 0
    browser_aggregate = 0
    for operation, (limit, policy_window) in sorted(policies.items()):
        requested = operations[operation]
        if type(requested) is not int or not 0 <= requested <= 100_000:
            raise CapacityReadinessError(f"browser operation {operation} is outside the planning bounds")
        allowed_per_user = limit * (window // policy_window)
        aggregate = users * requested
        browser_per_user += requested
        browser_aggregate += aggregate
        operation_budgets.append({
            "operation": operation,
            "requestedPerUserWindow": requested,
            "localPolicyLimit": limit,
            "localPolicyWindowSeconds": policy_window,
            "allowedPerUserObservationWindow": allowed_per_user,
            "aggregateRequested": aggregate,
            "fitsLocalReferencePolicy": requested <= allowed_per_user,
        })

    runner_signed_requests = runners * (runner_polls + runner_results)
    spectator_reads = spectators * replay_reads
    total_requests = browser_aggregate + runner_signed_requests + spectator_reads
    browser_policy_fit = all(row["fitsLocalReferencePolicy"] is True for row in operation_budgets)
    outcome = (
        "READY_FOR_PROTECTED_PRODUCTION_CAPACITY_TEST_NOT_LAUNCH"
        if browser_policy_fit
        else "REFUSED_LOCAL_BROWSER_POLICY_EXCEEDED"
    )
    inputs = {
        "scenarioId": scenario_id,
        "candidateLabel": candidate_label,
        "observationWindowSeconds": window,
        "authenticatedActiveUsers": users,
        "connectedRunners": runners,
        "publicSpectators": spectators,
        "browserOperationsPerActiveUserWindow": {
            operation: operations[operation] for operation in sorted(operations)
        },
        "runnerPollsPerRunnerWindow": runner_polls,
        "runnerResultsPerRunnerWindow": runner_results,
        "publicReplayReadsPerSpectatorWindow": replay_reads,
        "peakQueuedJobs": queued_jobs,
        "peakConcurrentAttempts": concurrent_attempts,
        "publicCreatorExecutionEnabled": False,
        "paidComputeAuthorized": False,
    }
    scenario: dict[str, object] = {
        "schemaVersion": SCENARIO_SCHEMA,
        "contractDigest": capacity_contract()["contractDigest"],
        "operatorInputs": inputs,
        "derivedRequestEnvelope": {
            "browserRequestsPerUserWindow": browser_per_user,
            "browserRequestsAggregate": browser_aggregate,
            "runnerSignedRequestsAggregate": runner_signed_requests,
            "publicReplayReadsAggregate": spectator_reads,
            "totalRequestsAggregate": total_requests,
            "rateRational": {
                "numerator": total_requests,
                "denominatorSeconds": window,
            },
            "peakQueuedJobs": queued_jobs,
            "peakConcurrentAttempts": concurrent_attempts,
            "operationBudgets": operation_budgets,
        },
        "browserReferencePolicyFit": browser_policy_fit,
        "outcome": outcome,
        "productionEvidenceRequired": list(UNRESOLVED_PRODUCTION_EVIDENCE),
        "productionCapacityVerified": False,
        "performanceSloApproved": False,
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    scenario["scenarioDigest"] = digest(scenario)
    return scenario


def build_capacity_scenario_from_operator_inputs(value: object) -> dict[str, object]:
    inputs = _exact(value, set(OPERATOR_INPUT_FIELDS), "capacity operator inputs")
    return build_capacity_scenario(
        scenario_id=inputs["scenarioId"],
        candidate_label=inputs["candidateLabel"],
        observation_window_seconds=inputs["observationWindowSeconds"],
        authenticated_active_users=inputs["authenticatedActiveUsers"],
        connected_runners=inputs["connectedRunners"],
        public_spectators=inputs["publicSpectators"],
        browser_operations_per_active_user_window=inputs["browserOperationsPerActiveUserWindow"],
        runner_polls_per_runner_window=inputs["runnerPollsPerRunnerWindow"],
        runner_results_per_runner_window=inputs["runnerResultsPerRunnerWindow"],
        public_replay_reads_per_spectator_window=inputs["publicReplayReadsPerSpectatorWindow"],
        peak_queued_jobs=inputs["peakQueuedJobs"],
        peak_concurrent_attempts=inputs["peakConcurrentAttempts"],
        public_creator_execution_enabled=inputs["publicCreatorExecutionEnabled"],
        paid_compute_authorized=inputs["paidComputeAuthorized"],
    )


def verify_capacity_scenario(value: object) -> dict[str, object]:
    row = _exact(
        value,
        {
            "schemaVersion", "contractDigest", "operatorInputs", "derivedRequestEnvelope",
            "browserReferencePolicyFit", "outcome", "productionEvidenceRequired",
            "productionCapacityVerified", "performanceSloApproved", "productionAuthority",
            "scenarioDigest",
        },
        "capacity scenario",
    )
    if row["schemaVersion"] != SCENARIO_SCHEMA or row["contractDigest"] != capacity_contract()["contractDigest"]:
        raise CapacityReadinessError("capacity scenario contract binding drift")
    if row["productionCapacityVerified"] is not False or row["performanceSloApproved"] is not False:
        raise CapacityReadinessError("capacity scenario cannot claim production proof")
    _false_authority(row["productionAuthority"], "capacity scenario")
    _verify_digest(row, "scenarioDigest", "capacity scenario")
    inputs = _exact(row["operatorInputs"], set(OPERATOR_INPUT_FIELDS), "capacity scenario operator inputs")
    rebuilt = build_capacity_scenario_from_operator_inputs(inputs)
    if rebuilt != row:
        raise CapacityReadinessError("capacity scenario does not match canonical reconstruction")
    return dict(row)


def build_local_correctness_observation(
    *,
    limiter_allowed: int,
    limiter_refused: int,
    owners_with_exact_allowance: int,
    owners_with_exact_refusal: int,
    public_replay_misses: int,
    row_counts_before: object,
    row_counts_after: object,
) -> dict[str, object]:
    before = _exact(
        row_counts_before,
        {"owners", "pairing_challenges", "runners", "nonces", "jobs", "attempts", "results", "replay_projections"},
        "rowCountsBefore",
    )
    after = _exact(row_counts_after, set(before), "rowCountsAfter")
    if any(type(count) is not int or count < 0 for count in list(before.values()) + list(after.values())):
        raise CapacityReadinessError("local observation row counts are malformed")
    plan = LOCAL_CORRECTNESS_PROBE
    expected_allowed = plan["syntheticOwnerCount"] * plan["expectedAllowedPerOwner"]
    expected_refused = plan["syntheticOwnerCount"] * plan["expectedRefusedPerOwner"]
    if any(type(value) is not int for value in (
        limiter_allowed,
        limiter_refused,
        owners_with_exact_allowance,
        owners_with_exact_refusal,
        public_replay_misses,
    )):
        raise CapacityReadinessError("local observation counts must be integers")
    checks = {
        "limiterAllowedCountExact": limiter_allowed == expected_allowed,
        "limiterRefusedCountExact": limiter_refused == expected_refused,
        "everyOwnerAllowanceExact": owners_with_exact_allowance == plan["syntheticOwnerCount"],
        "everyOwnerRefusalExact": owners_with_exact_refusal == plan["syntheticOwnerCount"],
        "allPublicReplayLookupsMissed": public_replay_misses == plan["expectedPublicReplayMissCount"],
        "referenceStoreStateUnchanged": before == after,
    }
    observation: dict[str, object] = {
        "schemaVersion": OBSERVATION_SCHEMA,
        "contractDigest": capacity_contract()["contractDigest"],
        "observationClass": plan["probeClass"],
        "probePlan": _clone(plan),
        "observedCounts": {
            "limiterAllowed": limiter_allowed,
            "limiterRefused": limiter_refused,
            "ownersWithExactAllowance": owners_with_exact_allowance,
            "ownersWithExactRefusal": owners_with_exact_refusal,
            "publicReplayMisses": public_replay_misses,
            "rowCountsBefore": {field: before[field] for field in sorted(before)},
            "rowCountsAfter": {field: after[field] for field in sorted(after)},
        },
        "checks": checks,
        "status": "LOCAL_CORRECTNESS_PASS" if all(checks.values()) else "LOCAL_CORRECTNESS_FAIL",
        "performanceThresholdApplied": False,
        "throughputClaimed": False,
        "productionTargetObserved": False,
        "networkUsed": False,
        "providerCalled": False,
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    observation["observationDigest"] = digest(observation)
    return observation


def verify_local_correctness_observation(value: object) -> dict[str, object]:
    row = _exact(
        value,
        {
            "schemaVersion", "contractDigest", "observationClass", "probePlan",
            "observedCounts", "checks", "status", "performanceThresholdApplied",
            "throughputClaimed", "productionTargetObserved", "networkUsed",
            "providerCalled", "productionAuthority", "observationDigest",
        },
        "local capacity observation",
    )
    if row["schemaVersion"] != OBSERVATION_SCHEMA or row["contractDigest"] != capacity_contract()["contractDigest"]:
        raise CapacityReadinessError("local capacity observation contract binding drift")
    if row["probePlan"] != LOCAL_CORRECTNESS_PROBE:
        raise CapacityReadinessError("local capacity observation probe plan drift")
    if any(row[field] is not False for field in (
        "performanceThresholdApplied", "throughputClaimed", "productionTargetObserved",
        "networkUsed", "providerCalled",
    )):
        raise CapacityReadinessError("local capacity observation overclaims its scope")
    _false_authority(row["productionAuthority"], "local capacity observation")
    _verify_digest(row, "observationDigest", "local capacity observation")
    observed = _exact(
        row["observedCounts"],
        {
            "limiterAllowed", "limiterRefused", "ownersWithExactAllowance",
            "ownersWithExactRefusal", "publicReplayMisses", "rowCountsBefore",
            "rowCountsAfter",
        },
        "local capacity observation counts",
    )
    rebuilt = build_local_correctness_observation(
        limiter_allowed=observed["limiterAllowed"],
        limiter_refused=observed["limiterRefused"],
        owners_with_exact_allowance=observed["ownersWithExactAllowance"],
        owners_with_exact_refusal=observed["ownersWithExactRefusal"],
        public_replay_misses=observed["publicReplayMisses"],
        row_counts_before=observed["rowCountsBefore"],
        row_counts_after=observed["rowCountsAfter"],
    )
    if rebuilt != row:
        raise CapacityReadinessError("local capacity observation does not match canonical reconstruction")
    if row["status"] != "LOCAL_CORRECTNESS_PASS":
        raise CapacityReadinessError("local capacity observation did not pass")
    return dict(row)
