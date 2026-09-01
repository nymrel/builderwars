"""Strict local observability and incident-decision contracts for AgentWars.

The module is intentionally uninstrumented and in-memory. It opens no network,
storage, process, account, provider, alert, or feature-flag surface. Its output
is a candidate operations contract, never evidence of production monitoring.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Iterable, Mapping


CONTRACT_SCHEMA = "agentwars.observability-contract/1"
EVENT_SCHEMA = "agentwars.operational-event/1"
BASELINE_SCHEMA = "agentwars.observability-baseline/1"
WINDOW_SCHEMA = "agentwars.observability-window/1"
INCIDENT_SCHEMA = "agentwars.incident-decision/1"

EVENT_ID_RE = re.compile(r"^awops_[0-9a-f]{32}$")
UTC_SECOND_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

EVENT_RULES: dict[str, dict[str, frozenset[str]]] = {
    "health_probe_failed": {
        "component": frozenset(("public_shell", "control_plane", "runner_pairing", "fixture_queue", "publication", "deletion", "measurement")),
        "failure_class": frozenset(("availability", "integrity", "authorization", "timeout", "cleanup")),
    },
    "request_failed": {
        "route_class": frozenset(("public_read", "account_private", "runner_signed_write", "publication_write", "deletion_write", "support_private")),
        "status_class": frozenset(("4xx", "5xx")),
        "latency_bucket": frozenset(("under_250ms", "250_999ms", "1_4s", "over_4s")),
        "failure_class": frozenset(("availability", "integrity", "authorization", "timeout", "cleanup")),
    },
    "abuse_refused": {
        "control": frozenset(("origin", "signature", "nonce", "rate_limit", "schema", "tenant")),
        "reason": frozenset(("bad_origin", "bad_signature", "replay_nonce", "rate_limited", "invalid_schema", "tenant_mismatch")),
    },
    "queue_saturation_observed": {
        "queue": frozenset(("fixture_jobs", "review_jobs", "publication_jobs", "deletion_jobs")),
        "saturation_bucket": frozenset(("under_50", "50_79", "80_99", "full")),
    },
    "publication_refused": {
        "reason": frozenset(("unverified_replay", "private_material", "missing_review", "correction_pending", "unattested_claim")),
    },
    "deletion_failed": {
        "resource": frozenset(("account", "runner", "private_submission", "temporary_transcript", "synthetic_probe")),
        "failure_class": frozenset(("availability", "integrity", "authorization", "timeout", "cleanup")),
    },
    "integrity_check_failed": {
        "artifact_class": frozenset(("runner_bundle", "dependency_lock", "verifier", "read_model", "receipt", "release_pack")),
    },
    "secret_exposure_suspected": {
        "surface": frozenset(("logs", "receipt", "analytics", "support", "derivative")),
    },
    "rollback_requested": {
        "trigger": frozenset(("integrity_failure", "secret_exposure", "deletion_failure", "error_budget_breach", "source_mismatch", "operator_request")),
    },
    "support_case_opened": {
        "issue_class": frozenset(("access", "pairing", "match", "publication", "deletion", "safety", "provider_boundary", "accessibility")),
        "severity": frozenset(("sev1", "sev2", "sev3")),
    },
}
EVENT_NAMES = tuple(EVENT_RULES)

PRODUCTION_AUTHORITY = {
    "productionDataRead": False,
    "durableSinkConfigured": False,
    "alertDeliveryConfigured": False,
    "statusPageConfigured": False,
    "onCallConfirmed": False,
    "productionThresholdsValidated": False,
    "supportQueueConfigured": False,
    "rollbackExecuted": False,
    "protectedFlagsMutated": False,
    "launchable": False,
}

_FORBIDDEN_FIELD_COMPONENTS = frozenset((
    "authorization", "cookie", "credential", "email", "href", "ip", "name",
    "password", "phone", "prompt", "query", "secret", "signature", "token",
    "url", "user", "output", "session", "account", "runner", "owner",
))


class ObservabilityContractError(ValueError):
    """Raised when an operational event or incident input fails closed."""


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _parse_timestamp(value: object, label: str) -> datetime:
    if type(value) is not str or not UTC_SECOND_RE.fullmatch(value):
        raise ObservabilityContractError(f"{label} must be a UTC whole-second timestamp")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise ObservabilityContractError(f"{label} must be a valid UTC timestamp") from error
    return parsed


def _field_components(value: str) -> frozenset[str]:
    return frozenset(part for part in re.split(r"[^a-z0-9]+", re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value).lower()) if part)


def forbidden_contract_fields() -> tuple[str, ...]:
    found: set[str] = set()
    for rules in EVENT_RULES.values():
        for field in rules:
            if _field_components(field) & _FORBIDDEN_FIELD_COMPONENTS:
                found.add(field)
    return tuple(sorted(found))


def observability_contract() -> dict[str, object]:
    contract: dict[str, object] = {
        "schemaVersion": CONTRACT_SCHEMA,
        "instrumentationStatus": "contract_only_not_instrumented",
        "eventSchemaVersion": EVENT_SCHEMA,
        "eventNames": list(EVENT_NAMES),
        "events": {
            name: {field: sorted(values) for field, values in rules.items()}
            for name, rules in EVENT_RULES.items()
        },
        "forbiddenContractFields": list(forbidden_contract_fields()),
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    contract["contractDigest"] = digest(contract)
    return contract


def validate_event(event: object) -> dict[str, object]:
    if type(event) is not dict:
        raise ObservabilityContractError("operational event must be an exact object")
    required = {"schemaVersion", "eventId", "eventName", "occurredAt", "properties"}
    if set(event) != required:
        raise ObservabilityContractError("operational event fields drift")
    if event["schemaVersion"] != EVENT_SCHEMA:
        raise ObservabilityContractError("operational event schema is unsupported")
    if type(event["eventId"]) is not str or not EVENT_ID_RE.fullmatch(event["eventId"]):
        raise ObservabilityContractError("operational event id is malformed")
    if type(event["eventName"]) is not str or event["eventName"] not in EVENT_RULES:
        raise ObservabilityContractError("operational event name is not allowlisted")
    _parse_timestamp(event["occurredAt"], "occurredAt")
    if type(event["properties"]) is not dict:
        raise ObservabilityContractError("operational event properties must be an exact object")
    rules = EVENT_RULES[event["eventName"]]
    if set(event["properties"]) != set(rules):
        raise ObservabilityContractError("operational event property fields drift")
    for field, allowlist in rules.items():
        value = event["properties"][field]
        if type(value) is not str or value not in allowlist:
            raise ObservabilityContractError(f"operational event property is not allowlisted: {field}")
    return {
        "schemaVersion": EVENT_SCHEMA,
        "eventId": event["eventId"],
        "eventName": event["eventName"],
        "occurredAt": event["occurredAt"],
        "properties": dict(event["properties"]),
    }


def build_zero_baseline(observed_at: str) -> dict[str, object]:
    _parse_timestamp(observed_at, "observedAt")
    baseline: dict[str, object] = {
        "schemaVersion": BASELINE_SCHEMA,
        "observedAt": observed_at,
        "sourceStatus": "no_source_configured",
        "instrumentationStatus": "contract_only_not_instrumented",
        "contractDigest": observability_contract()["contractDigest"],
        "eventCounts": {name: 0 for name in EVENT_NAMES},
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    baseline["baselineDigest"] = digest(baseline)
    return baseline


def aggregate_in_memory(events: Iterable[object], observed_at: str) -> dict[str, object]:
    cutoff = _parse_timestamp(observed_at, "observedAt")
    validated: list[dict[str, object]] = []
    seen: set[str] = set()
    for candidate in events:
        event = validate_event(candidate)
        if event["eventId"] in seen:
            raise ObservabilityContractError("duplicate operational event id")
        if _parse_timestamp(event["occurredAt"], "occurredAt") > cutoff:
            raise ObservabilityContractError("operational event occurs after the observation cutoff")
        seen.add(str(event["eventId"]))
        validated.append(event)

    counts = {name: 0 for name in EVENT_NAMES}
    derived = {
        "serverFailures": 0,
        "queueHigh": 0,
        "queueFull": 0,
        "supportSev1": 0,
        "abuseRefusals": 0,
    }
    for event in validated:
        name = str(event["eventName"])
        properties = event["properties"]
        counts[name] += 1
        if name == "request_failed" and properties["status_class"] == "5xx":
            derived["serverFailures"] += 1
        elif name == "queue_saturation_observed":
            if properties["saturation_bucket"] == "80_99":
                derived["queueHigh"] += 1
            elif properties["saturation_bucket"] == "full":
                derived["queueFull"] += 1
        elif name == "support_case_opened" and properties["severity"] == "sev1":
            derived["supportSev1"] += 1
        elif name == "abuse_refused":
            derived["abuseRefusals"] += 1

    window: dict[str, object] = {
        "schemaVersion": WINDOW_SCHEMA,
        "observedAt": observed_at,
        "sourceStatus": "in_memory_validation_only",
        "contractDigest": observability_contract()["contractDigest"],
        "eventCount": len(validated),
        "eventCounts": counts,
        "derivedCounts": derived,
        "eventSetDigest": digest(validated),
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    window["windowDigest"] = digest(window)
    return window


_DECISIONS: dict[str, dict[str, object]] = {
    "NO_INCIDENT": {
        "severity": "NONE",
        "releaseDecision": "CONTINUE_LOCAL_VALIDATION",
        "protectedFlagsRecommendation": "NO_CHANGE",
        "rollbackRecommendation": "NOT_RECOMMENDED",
        "supportAction": "NO_ACTION",
        "publicCommunication": "NONE",
        "evidenceRequired": ["retain_local_drill_receipt"],
        "operatorReviewRequired": False,
    },
    "SECRET_EXPOSURE_SUSPECTED": {
        "severity": "SEV1",
        "releaseDecision": "HOLD_RELEASE",
        "protectedFlagsRecommendation": "DISABLE_PROTECTED_FLOWS",
        "rollbackRecommendation": "ROLLBACK_CANDIDATE",
        "supportAction": "OPEN_SECURITY_INCIDENT",
        "publicCommunication": "STATUS_PAGE_CANDIDATE",
        "evidenceRequired": ["redacted_finding", "scope_assessment", "rotation_receipt", "cleanup_receipt"],
        "operatorReviewRequired": True,
    },
    "INTEGRITY_FAILURE": {
        "severity": "SEV1",
        "releaseDecision": "HOLD_RELEASE",
        "protectedFlagsRecommendation": "DISABLE_PROTECTED_FLOWS",
        "rollbackRecommendation": "ROLLBACK_CANDIDATE",
        "supportAction": "OPEN_RELEASE_INCIDENT",
        "publicCommunication": "INTERNAL_UNTIL_SCOPE_CONFIRMED",
        "evidenceRequired": ["failing_artifact_digest", "last_known_good_digest", "source_binding", "reverification"],
        "operatorReviewRequired": True,
    },
    "DELETION_FAILURE": {
        "severity": "SEV1",
        "releaseDecision": "HOLD_RELEASE",
        "protectedFlagsRecommendation": "DISABLE_PRIVATE_WRITES",
        "rollbackRecommendation": "ROLLBACK_CANDIDATE",
        "supportAction": "OPEN_PRIVACY_INCIDENT",
        "publicCommunication": "STATUS_PAGE_CANDIDATE",
        "evidenceRequired": ["redacted_resource_class", "retry_receipt", "cleanup_receipt", "tenant_isolation_check"],
        "operatorReviewRequired": True,
    },
    "ROLLBACK_REQUESTED": {
        "severity": "SEV1",
        "releaseDecision": "HOLD_RELEASE",
        "protectedFlagsRecommendation": "DISABLE_PROTECTED_FLOWS",
        "rollbackRecommendation": "ROLLBACK_CANDIDATE",
        "supportAction": "OPEN_RELEASE_INCIDENT",
        "publicCommunication": "STATUS_PAGE_CANDIDATE",
        "evidenceRequired": ["trigger_receipt", "last_known_good_digest", "rollback_receipt", "post_rollback_verification"],
        "operatorReviewRequired": True,
    },
    "SUPPORT_SEV1": {
        "severity": "SEV1",
        "releaseDecision": "HOLD_RELEASE",
        "protectedFlagsRecommendation": "DISABLE_AFFECTED_FLOW",
        "rollbackRecommendation": "ASSESS_ROLLBACK",
        "supportAction": "ACKNOWLEDGE_AND_TRIAGE",
        "publicCommunication": "STATUS_PAGE_CANDIDATE",
        "evidenceRequired": ["redacted_case_class", "reproduction", "impact_scope", "resolution_receipt"],
        "operatorReviewRequired": True,
    },
    "HEALTH_FAILURE": {
        "severity": "SEV2",
        "releaseDecision": "HOLD_RELEASE",
        "protectedFlagsRecommendation": "DISABLE_AFFECTED_FLOW",
        "rollbackRecommendation": "ASSESS_ROLLBACK",
        "supportAction": "OPEN_OPERATIONS_INCIDENT",
        "publicCommunication": "INTERNAL_UNTIL_SCOPE_CONFIRMED",
        "evidenceRequired": ["component_class", "probe_receipt", "dependency_status", "recovery_receipt"],
        "operatorReviewRequired": True,
    },
    "ERROR_BUDGET_BREACH": {
        "severity": "SEV2",
        "releaseDecision": "HOLD_RELEASE",
        "protectedFlagsRecommendation": "DISABLE_AFFECTED_FLOW",
        "rollbackRecommendation": "ASSESS_ROLLBACK",
        "supportAction": "OPEN_OPERATIONS_INCIDENT",
        "publicCommunication": "INTERNAL_UNTIL_SCOPE_CONFIRMED",
        "evidenceRequired": ["redacted_route_class", "error_window", "source_binding", "recovery_receipt"],
        "operatorReviewRequired": True,
    },
    "QUEUE_PRESSURE": {
        "severity": "SEV2",
        "releaseDecision": "HOLD_NEW_ADMISSIONS",
        "protectedFlagsRecommendation": "CLOSE_NEW_JOB_ADMISSION",
        "rollbackRecommendation": "NOT_RECOMMENDED",
        "supportAction": "OPEN_CAPACITY_INCIDENT",
        "publicCommunication": "STATUS_PAGE_CANDIDATE",
        "evidenceRequired": ["queue_class", "saturation_window", "drain_receipt", "capacity_decision"],
        "operatorReviewRequired": True,
    },
    "ABUSE_SURGE": {
        "severity": "SEV2",
        "releaseDecision": "HOLD_NEW_ADMISSIONS",
        "protectedFlagsRecommendation": "TIGHTEN_OR_CLOSE_AFFECTED_FLOW",
        "rollbackRecommendation": "NOT_RECOMMENDED",
        "supportAction": "OPEN_TRUST_SAFETY_INCIDENT",
        "publicCommunication": "INTERNAL_UNTIL_SCOPE_CONFIRMED",
        "evidenceRequired": ["control_class_counts", "rate_limit_receipt", "false_positive_review", "recovery_decision"],
        "operatorReviewRequired": True,
    },
}


def _validate_window(window: object) -> dict[str, object]:
    if type(window) is not dict or window.get("schemaVersion") != WINDOW_SCHEMA:
        raise ObservabilityContractError("incident input must be a validated observability window")
    required = {
        "schemaVersion", "observedAt", "sourceStatus", "contractDigest", "eventCount",
        "eventCounts", "derivedCounts", "eventSetDigest", "productionAuthority", "windowDigest",
    }
    if set(window) != required:
        raise ObservabilityContractError("incident input fields drift")
    _parse_timestamp(window["observedAt"], "observedAt")
    if window["sourceStatus"] != "in_memory_validation_only":
        raise ObservabilityContractError("incident input source status is unsupported")
    if window["contractDigest"] != observability_contract()["contractDigest"]:
        raise ObservabilityContractError("incident input contract digest drift")
    event_counts = window.get("eventCounts")
    if type(event_counts) is not dict or set(event_counts) != set(EVENT_NAMES):
        raise ObservabilityContractError("incident input event counts drift")
    derived = window.get("derivedCounts")
    if type(derived) is not dict or set(derived) != {"serverFailures", "queueHigh", "queueFull", "supportSev1", "abuseRefusals"}:
        raise ObservabilityContractError("incident input derived counts drift")
    for value in list(event_counts.values()) + list(derived.values()):
        if type(value) is not int or value < 0:
            raise ObservabilityContractError("incident input counts must be non-negative integers")
    if type(window["eventCount"]) is not int or window["eventCount"] < 0 or sum(event_counts.values()) != window["eventCount"]:
        raise ObservabilityContractError("incident input event total is inconsistent")
    if derived["serverFailures"] > event_counts["request_failed"]:
        raise ObservabilityContractError("incident input server-failure total is inconsistent")
    if derived["queueHigh"] + derived["queueFull"] > event_counts["queue_saturation_observed"]:
        raise ObservabilityContractError("incident input queue total is inconsistent")
    if derived["supportSev1"] > event_counts["support_case_opened"]:
        raise ObservabilityContractError("incident input support total is inconsistent")
    if derived["abuseRefusals"] != event_counts["abuse_refused"]:
        raise ObservabilityContractError("incident input abuse total is inconsistent")
    if type(window["eventSetDigest"]) is not str or not re.fullmatch(r"[0-9a-f]{64}", window["eventSetDigest"]):
        raise ObservabilityContractError("incident input event-set digest is malformed")
    if window["productionAuthority"] != PRODUCTION_AUTHORITY:
        raise ObservabilityContractError("incident input production authority drift")
    if type(window.get("windowDigest")) is not str or len(window["windowDigest"]) != 64:
        raise ObservabilityContractError("incident input digest is malformed")
    unsigned = dict(window)
    unsigned.pop("windowDigest")
    if digest(unsigned) != window["windowDigest"]:
        raise ObservabilityContractError("incident input digest mismatch")
    return window


def evaluate_incident(window: object) -> dict[str, object]:
    validated = _validate_window(window)
    counts = validated["eventCounts"]
    derived = validated["derivedCounts"]
    if counts["secret_exposure_suspected"]:
        code = "SECRET_EXPOSURE_SUSPECTED"
    elif counts["integrity_check_failed"]:
        code = "INTEGRITY_FAILURE"
    elif counts["deletion_failed"]:
        code = "DELETION_FAILURE"
    elif counts["rollback_requested"]:
        code = "ROLLBACK_REQUESTED"
    elif derived["supportSev1"]:
        code = "SUPPORT_SEV1"
    elif counts["health_probe_failed"]:
        code = "HEALTH_FAILURE"
    elif derived["serverFailures"] >= 5:
        code = "ERROR_BUDGET_BREACH"
    elif derived["queueFull"] or derived["queueHigh"] >= 3:
        code = "QUEUE_PRESSURE"
    elif derived["abuseRefusals"] >= 25:
        code = "ABUSE_SURGE"
    else:
        code = "NO_INCIDENT"
    decision: dict[str, object] = {
        "schemaVersion": INCIDENT_SCHEMA,
        "observedAt": validated["observedAt"],
        "windowDigest": validated["windowDigest"],
        "incidentCode": code,
        **_DECISIONS[code],
        "actionsExecuted": False,
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    decision["decisionDigest"] = digest(decision)
    return decision
