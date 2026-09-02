#!/usr/bin/env python3
"""Adversarially verify AgentWars local observability and incident contracts."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publishing import observability


OBSERVED_AT = "2026-09-01T00:10:00Z"
EVENT_AT = "2026-09-01T00:05:00Z"
ALLOWED_IMPORT_ROOTS = {"__future__", "ast", "hashlib", "json", "re", "datetime", "typing"}
checks = 0


def check(condition: bool, label: str) -> None:
    global checks
    if not condition:
        raise AssertionError(label)
    checks += 1


def make_event(event_name: str, index: int, **overrides: str) -> dict[str, Any]:
    rules = observability.EVENT_RULES[event_name]
    properties = {field: sorted(values)[0] for field, values in rules.items()}
    properties.update(overrides)
    return {
        "schemaVersion": observability.EVENT_SCHEMA,
        "eventId": f"awops_{index:032x}",
        "eventName": event_name,
        "occurredAt": EVENT_AT,
        "properties": properties,
    }


def clone(value: object) -> Any:
    return json.loads(json.dumps(value))


def expect_event_error(mutator: Callable[[dict[str, Any]], None], expected: str) -> None:
    event = make_event("request_failed", 900)
    mutator(event)
    try:
        observability.validate_event(event)
    except observability.ObservabilityContractError as error:
        check(expected in str(error), f"event failure is attributed: {expected}")
    else:
        raise AssertionError(f"event mutation should fail: {expected}")


def expect_window_error(mutator: Callable[[dict[str, Any]], None], expected: str) -> None:
    window = observability.aggregate_in_memory([], OBSERVED_AT)
    mutator(window)
    try:
        observability.evaluate_incident(window)
    except observability.ObservabilityContractError as error:
        check(expected in str(error), f"window failure is attributed: {expected}")
    else:
        raise AssertionError(f"window mutation should fail: {expected}")


def decision_for(events: list[dict[str, Any]]) -> dict[str, object]:
    return observability.evaluate_incident(observability.aggregate_in_memory(events, OBSERVED_AT))


def repeated(event_name: str, count: int, start: int, **overrides: str) -> list[dict[str, Any]]:
    return [make_event(event_name, start + index, **overrides) for index in range(count)]


def import_roots(path: Path) -> set[str]:
    roots: set[str] = set()
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def main() -> int:
    contract = observability.observability_contract()
    check(contract["schemaVersion"] == observability.CONTRACT_SCHEMA, "contract schema is exact")
    check(contract["instrumentationStatus"] == "contract_only_not_instrumented", "contract denies instrumentation")
    check(contract["eventNames"] == list(observability.EVENT_NAMES), "contract names every event in stable order")
    check(len(contract["eventNames"]) == 10, "contract exposes ten bounded operational events")
    check(contract["forbiddenContractFields"] == [], "event property schemas admit no forbidden person or secret fields")
    check(all(value is False for value in contract["productionAuthority"].values()), "contract has zero production authority")
    check(contract["contractDigest"] == observability.observability_contract()["contractDigest"], "contract digest is deterministic")

    events: list[dict[str, Any]] = []
    for index, event_name in enumerate(observability.EVENT_NAMES, start=1):
        event = make_event(event_name, index)
        validated = observability.validate_event(event)
        check(validated == event, f"{event_name}: valid exact event round-trips")
        check(set(validated["properties"]) == set(observability.EVENT_RULES[event_name]), f"{event_name}: property set is exact")
        events.append(event)

    baseline = observability.build_zero_baseline(OBSERVED_AT)
    check(baseline["schemaVersion"] == observability.BASELINE_SCHEMA, "zero baseline schema is exact")
    check(baseline["sourceStatus"] == "no_source_configured", "zero baseline denies a source")
    check(baseline["instrumentationStatus"] == "contract_only_not_instrumented", "zero baseline denies instrumentation")
    check(set(baseline["eventCounts"]) == set(observability.EVENT_NAMES), "zero baseline covers every event")
    check(all(value == 0 for value in baseline["eventCounts"].values()), "zero baseline counts are all zero")
    check(all(value is False for value in baseline["productionAuthority"].values()), "zero baseline has zero production authority")
    check(baseline == observability.build_zero_baseline(OBSERVED_AT), "zero baseline is deterministic")

    window = observability.aggregate_in_memory(events, OBSERVED_AT)
    check(window["schemaVersion"] == observability.WINDOW_SCHEMA, "window schema is exact")
    check(window["sourceStatus"] == "in_memory_validation_only", "window declares its synthetic source")
    check(window["eventCount"] == len(events), "window counts exact events")
    check(all(value == 1 for value in window["eventCounts"].values()), "window counts every event once")
    check(window["derivedCounts"]["abuseRefusals"] == 1, "window derives refusal count")
    check(all(value is False for value in window["productionAuthority"].values()), "window has zero production authority")
    check(window == observability.aggregate_in_memory(events, OBSERVED_AT), "window is deterministic")

    try:
        observability.aggregate_in_memory([events[0], events[0]], OBSERVED_AT)
    except observability.ObservabilityContractError as error:
        check("duplicate" in str(error), "duplicate event ids fail closed")
    else:
        raise AssertionError("duplicate event ids should fail")
    future = make_event("health_probe_failed", 700)
    future["occurredAt"] = "2026-09-01T00:11:00Z"
    try:
        observability.aggregate_in_memory([future], OBSERVED_AT)
    except observability.ObservabilityContractError as error:
        check("after the observation" in str(error), "future event fails closed")
    else:
        raise AssertionError("future event should fail")

    expect_event_error(lambda value: value.pop("eventName"), "fields drift")
    expect_event_error(lambda value: value.update({"extra": True}), "fields drift")
    expect_event_error(lambda value: value.update({"schemaVersion": "agentwars.operational-event/2"}), "unsupported")
    expect_event_error(lambda value: value.update({"eventId": "awops_bad"}), "malformed")
    expect_event_error(lambda value: value.update({"eventName": "arbitrary_log"}), "not allowlisted")
    expect_event_error(lambda value: value.update({"occurredAt": "2026-09-01T00:05:00+00:00"}), "whole-second")
    expect_event_error(lambda value: value.update({"occurredAt": "2026-09-01T00:05:00.000Z"}), "whole-second")
    expect_event_error(lambda value: value.update({"occurredAt": "2026-02-30T00:05:00Z"}), "valid UTC")
    expect_event_error(lambda value: value.update({"properties": []}), "exact object")
    expect_event_error(lambda value: value["properties"].pop("route_class"), "property fields drift")
    expect_event_error(lambda value: value["properties"].update({"url": "https://example.test"}), "property fields drift")
    expect_event_error(lambda value: value["properties"].update({"user_id": "user_1"}), "property fields drift")
    expect_event_error(lambda value: value["properties"].update({"failure_class": "raw exception text"}), "not allowlisted")
    expect_event_error(lambda value: value["properties"].update({"status_class": 500}), "not allowlisted")
    expect_event_error(lambda value: value["properties"].update({"latency_bucket": True}), "not allowlisted")

    scenarios = {
        "NO_INCIDENT": decision_for([]),
        "SECRET_EXPOSURE_SUSPECTED": decision_for([make_event("secret_exposure_suspected", 100)]),
        "INTEGRITY_FAILURE": decision_for([make_event("integrity_check_failed", 101)]),
        "DELETION_FAILURE": decision_for([make_event("deletion_failed", 102)]),
        "ROLLBACK_REQUESTED": decision_for([make_event("rollback_requested", 103)]),
        "SUPPORT_SEV1": decision_for([make_event("support_case_opened", 104, severity="sev1")]),
        "HEALTH_FAILURE": decision_for([make_event("health_probe_failed", 105)]),
        "ERROR_BUDGET_BREACH": decision_for(repeated("request_failed", 5, 110, status_class="5xx")),
        "QUEUE_PRESSURE": decision_for([make_event("queue_saturation_observed", 120, saturation_bucket="full")]),
        "ABUSE_SURGE": decision_for(repeated("abuse_refused", 25, 130)),
    }
    for expected, decision in scenarios.items():
        check(decision["incidentCode"] == expected, f"{expected}: drill selects exact incident")
        check(decision["actionsExecuted"] is False, f"{expected}: drill executes no action")
        check(all(value is False for value in decision["productionAuthority"].values()), f"{expected}: drill has zero production authority")
        check(bool(decision["evidenceRequired"]), f"{expected}: drill names required evidence")
        check(len(decision["decisionDigest"]) == 64, f"{expected}: drill is digest-bound")
        check(decision["schemaVersion"] == observability.INCIDENT_SCHEMA, f"{expected}: incident schema stays stable")

    check(scenarios["NO_INCIDENT"]["releaseDecision"] == "CONTINUE_LOCAL_VALIDATION", "healthy drill permits local validation only")
    check(scenarios["NO_INCIDENT"]["operatorReviewRequired"] is False, "healthy drill needs no incident operator")
    for expected in ("SECRET_EXPOSURE_SUSPECTED", "INTEGRITY_FAILURE", "DELETION_FAILURE", "ROLLBACK_REQUESTED"):
        check(scenarios[expected]["releaseDecision"] == "HOLD_RELEASE", f"{expected}: release is held")
        check(scenarios[expected]["operatorReviewRequired"] is True, f"{expected}: operator review is required")
    check(scenarios["SECRET_EXPOSURE_SUSPECTED"]["protectedFlagsRecommendation"] == "DISABLE_PROTECTED_FLOWS", "secret drill recommends protected-flow disablement")
    check(scenarios["DELETION_FAILURE"]["supportAction"] == "OPEN_PRIVACY_INCIDENT", "deletion drill routes privacy support")
    check(scenarios["QUEUE_PRESSURE"]["releaseDecision"] == "HOLD_NEW_ADMISSIONS", "queue drill stops new admissions")
    check(scenarios["ABUSE_SURGE"]["supportAction"] == "OPEN_TRUST_SAFETY_INCIDENT", "abuse drill routes trust and safety")

    check(decision_for(repeated("request_failed", 4, 200, status_class="5xx"))["incidentCode"] == "NO_INCIDENT", "synthetic server threshold is exact")
    check(decision_for(repeated("queue_saturation_observed", 2, 210, saturation_bucket="80_99"))["incidentCode"] == "NO_INCIDENT", "synthetic queue threshold is exact")
    check(decision_for(repeated("queue_saturation_observed", 3, 220, saturation_bucket="80_99"))["incidentCode"] == "QUEUE_PRESSURE", "three high queue observations trigger the drill")
    check(decision_for(repeated("abuse_refused", 24, 230))["incidentCode"] == "NO_INCIDENT", "synthetic abuse threshold is exact")
    priority = decision_for([make_event("integrity_check_failed", 300), make_event("secret_exposure_suspected", 301)])
    check(priority["incidentCode"] == "SECRET_EXPOSURE_SUSPECTED", "secret suspicion wins incident priority")

    expect_window_error(lambda value: value.pop("sourceStatus"), "fields drift")
    expect_window_error(lambda value: value.update({"sourceStatus": "production"}), "unsupported")
    expect_window_error(lambda value: value.update({"contractDigest": "0" * 64}), "contract digest drift")
    expect_window_error(lambda value: value.update({"eventCounts": []}), "event counts drift")
    expect_window_error(lambda value: value["eventCounts"].pop("request_failed"), "event counts drift")
    expect_window_error(lambda value: value["eventCounts"].update({"request_failed": -1}), "non-negative")
    expect_window_error(lambda value: value["eventCounts"].update({"request_failed": True}), "non-negative")
    expect_window_error(lambda value: value.update({"eventCount": 1}), "event total")
    expect_window_error(lambda value: value["derivedCounts"].update({"serverFailures": 1}), "server-failure total")
    expect_window_error(lambda value: value["derivedCounts"].update({"queueFull": 1}), "queue total")
    expect_window_error(lambda value: value["derivedCounts"].update({"supportSev1": 1}), "support total")
    expect_window_error(lambda value: value["derivedCounts"].update({"abuseRefusals": 1}), "abuse total")
    expect_window_error(lambda value: value.update({"eventSetDigest": "bad"}), "event-set digest")
    expect_window_error(lambda value: value["productionAuthority"].update({"launchable": True}), "production authority drift")
    expect_window_error(lambda value: value.update({"windowDigest": "0" * 64}), "digest mismatch")

    module_path = ROOT / "publishing" / "observability.py"
    imports = import_roots(module_path)
    check(imports <= ALLOWED_IMPORT_ROOTS, f"observability module stays pure: {sorted(imports - ALLOWED_IMPORT_ROOTS)}")
    compact = module_path.read_text(encoding="utf-8").lower()
    for forbidden in ("requests", "urllib", "socket", "sqlite", "subprocess", "analytics sdk", "alert delivery client"):
        check(forbidden not in compact, f"observability module contains no {forbidden} integration")
    rendered = observability.canonical_bytes({"baseline": baseline, "scenarios": scenarios}).decode("ascii")
    for forbidden_claim in (
        '"durableSinkConfigured":true', '"alertDeliveryConfigured":true',
        '"statusPageConfigured":true', '"onCallConfirmed":true',
        '"productionThresholdsValidated":true', '"supportQueueConfigured":true',
        '"rollbackExecuted":true', '"protectedFlagsMutated":true', '"launchable":true',
    ):
        check(forbidden_claim not in rendered, f"local receipts cannot emit {forbidden_claim}")

    print(f"AgentWars observability and incident contract: PASS ({checks} checks)")
    print("10 events / strict privacy / zero baseline / 10 incident drills / no telemetry or action execution")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, observability.ObservabilityContractError) as error:
        print(f"AgentWars observability and incident contract: FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
