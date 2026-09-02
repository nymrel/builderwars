"""Strict, privacy-bounded AgentWars share-funnel measurement contracts.

This module validates in-memory candidate events only. It has no transport,
storage, identity, cookie, account, provider, or production-data dependency.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping


MEASUREMENT_CONTRACT_VERSION = "agentwars.measurement-contract/1"
EVENT_SCHEMA_VERSION = "agentwars.measurement-event/1"
BASELINE_SCHEMA_VERSION = "agentwars.measurement-baseline/1"
AGGREGATE_SCHEMA_VERSION = "agentwars.measurement-aggregate/1"

EVENT_SCHEMA = {
    "share_intent_recorded": {
        "required": ["match_id", "clip_id", "share_method"],
        "optional": ["surface", "campaign_id", "creative_id"],
    },
    "share_landing_viewed": {
        "required": ["match_id", "clip_id", "source_label", "campaign_id", "creative_id"],
        "optional": ["surface"],
    },
    "replay_started": {
        "required": ["match_id", "clip_id"],
        "optional": ["surface"],
    },
    "replay_verified": {
        "required": ["match_id", "clip_id", "verdict"],
        "optional": ["surface"],
    },
    "spectator_vote_cast": {
        "required": ["match_id", "clip_id", "vote"],
        "optional": ["surface"],
    },
    "league_join_clicked": {
        "required": ["match_id", "clip_id"],
        "optional": ["surface"],
    },
}

EVENT_VALUE_ALLOWLISTS = {
    "share_method": ["native", "copy", "download"],
    "surface": ["receipt_card", "share_landing", "match_page"],
    "verdict": ["PASS", "FAIL"],
    "vote": ["seat0", "seat1", "runback"],
}

_EVENT_KEYS = frozenset({"schemaVersion", "eventId", "eventName", "occurredAt", "properties"})
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")
_LOWER_TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")
_EVENT_ID_RE = re.compile(r"^awmevt_[0-9a-f]{32}$")
_CLIP_ID_RE = re.compile(r"^clip_[0-9a-f]{16}$")
_CREATIVE_ID_RE = re.compile(r"^moment_[0-9a-f]{16}$")
_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_IDENTIFIER_FIELDS = frozenset({"match_id", "clip_id", "source_label", "campaign_id", "creative_id"})
_FORBIDDEN_FIELD_TOKENS = (
    "url",
    "href",
    "query",
    "user",
    "email",
    "phone",
    "ip",
    "cookie",
    "agent",
    "prompt",
    "output",
    "credential",
    "secret",
    "token",
    "key",
)


class MeasurementError(ValueError):
    """Raised when a candidate measurement record violates the contract."""


def _refuse(message: str) -> None:
    raise MeasurementError(message)


def _exact_object(value: Any, keys: frozenset[str], label: str) -> Mapping[str, Any]:
    if type(value) is not dict:
        _refuse(f"{label} must be an object")
    if frozenset(value) != keys:
        _refuse(f"{label} fields are not exact")
    return value


def _text(value: Any, label: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        _refuse(f"{label} is invalid")
    return value


def _utc(value: Any, label: str) -> tuple[str, datetime]:
    if not isinstance(value, str) or _UTC_RE.fullmatch(value) is None:
        _refuse(f"{label} must be a second-precision UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise MeasurementError(f"{label} is invalid") from error
    if parsed.tzinfo != timezone.utc:
        _refuse(f"{label} must be UTC")
    return value, parsed


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def measurement_contract() -> dict[str, Any]:
    return {
        "schemaVersion": MEASUREMENT_CONTRACT_VERSION,
        "status": "schema_only_not_instrumented",
        "events": {
            name: {
                "required": list(spec["required"]),
                "optional": list(spec["optional"]),
            }
            for name, spec in EVENT_SCHEMA.items()
        },
        "valueAllowlists": {name: list(values) for name, values in EVENT_VALUE_ALLOWLISTS.items()},
        "privacy": {
            "exactFieldsOnly": True,
            "rawUrlsAccepted": False,
            "queryStringsAccepted": False,
            "personIdentifiersAccepted": False,
            "networkIdentifiersAccepted": False,
            "promptsOrOutputsAccepted": False,
            "credentialsAccepted": False,
        },
        "authority": {
            "instrumented": False,
            "durableCounterProven": False,
            "productionDataRead": False,
            "audienceMeasured": False,
            "performanceMeasured": False,
            "builderIdentityAvailable": False,
            "retentionMeasured": False,
            "launchable": False,
        },
    }


def measurement_contract_digest() -> str:
    return digest(measurement_contract())


def _validate_property(name: str, value: Any) -> str:
    if name in EVENT_VALUE_ALLOWLISTS:
        if not isinstance(value, str) or value not in EVENT_VALUE_ALLOWLISTS[name]:
            _refuse(f"properties.{name} is outside its allowlist")
        return value
    if name not in _IDENTIFIER_FIELDS:
        _refuse(f"properties.{name} is unsupported")
    pattern = _TOKEN_RE
    if name == "clip_id":
        pattern = _CLIP_ID_RE
    elif name == "creative_id":
        pattern = _CREATIVE_ID_RE
    elif name in {"source_label", "campaign_id"}:
        pattern = _LOWER_TOKEN_RE
    return _text(value, f"properties.{name}", pattern)


def validate_event(value: Any) -> dict[str, Any]:
    event = _exact_object(value, _EVENT_KEYS, "event")
    if event["schemaVersion"] != EVENT_SCHEMA_VERSION:
        _refuse("event schemaVersion is unsupported")
    event_id = _text(event["eventId"], "eventId", _EVENT_ID_RE)
    event_name = event["eventName"]
    if not isinstance(event_name, str) or event_name not in EVENT_SCHEMA:
        _refuse("eventName is unsupported")
    occurred_at, _ = _utc(event["occurredAt"], "occurredAt")
    properties = event["properties"]
    if type(properties) is not dict:
        _refuse("properties must be an object")
    spec = EVENT_SCHEMA[event_name]
    required = frozenset(spec["required"])
    allowed = required | frozenset(spec["optional"])
    present = frozenset(properties)
    if not required.issubset(present):
        _refuse("event is missing required properties")
    if not present.issubset(allowed):
        _refuse("event contains unknown properties")
    normalized_properties = {
        name: _validate_property(name, properties[name])
        for name in (*spec["required"], *spec["optional"])
        if name in properties
    }
    return {
        "schemaVersion": EVENT_SCHEMA_VERSION,
        "eventId": event_id,
        "eventName": event_name,
        "occurredAt": occurred_at,
        "properties": normalized_properties,
    }


def build_zero_baseline(observed_at: str) -> dict[str, Any]:
    observed_at, _ = _utc(observed_at, "observedAt")
    return {
        "schemaVersion": BASELINE_SCHEMA_VERSION,
        "observedAt": observed_at,
        "contractDigest": measurement_contract_digest(),
        "sourceStatus": "no_source_configured",
        "instrumentationStatus": "schema_only_not_instrumented",
        "eventCounts": {name: 0 for name in sorted(EVENT_SCHEMA)},
        "totalEvents": 0,
        "productionDataRead": False,
        "durableCounterProven": False,
        "audienceMeasured": False,
        "performanceMeasured": False,
        "builderIdentityAvailable": False,
        "retentionMeasured": False,
        "launchable": False,
    }


def aggregate_in_memory(events: Iterable[Any], observed_at: str) -> dict[str, Any]:
    observed_at, observation = _utc(observed_at, "observedAt")
    counts = {name: 0 for name in sorted(EVENT_SCHEMA)}
    seen_ids: set[str] = set()
    for candidate in events:
        event = validate_event(candidate)
        if event["eventId"] in seen_ids:
            _refuse("duplicate eventId")
        seen_ids.add(event["eventId"])
        _, occurred_at = _utc(event["occurredAt"], "occurredAt")
        if occurred_at > observation:
            _refuse("event occurs after the observation boundary")
        counts[event["eventName"]] += 1
    return {
        "schemaVersion": AGGREGATE_SCHEMA_VERSION,
        "observedAt": observed_at,
        "contractDigest": measurement_contract_digest(),
        "sourceStatus": "in_memory_validation_only",
        "eventCounts": counts,
        "totalEvents": sum(counts.values()),
        "uniqueEventIds": len(seen_ids),
        "productionDataRead": False,
        "durableCounterProven": False,
        "audienceMeasured": False,
        "performanceMeasured": False,
        "builderIdentityAvailable": False,
        "retentionMeasured": False,
        "launchable": False,
    }


def forbidden_contract_fields() -> list[str]:
    fields = {
        field
        for spec in EVENT_SCHEMA.values()
        for field in (*spec["required"], *spec["optional"])
    }
    return sorted(
        field
        for field in fields
        if any(token in set(re.split(r"[_-]+", field.lower())) for token in _FORBIDDEN_FIELD_TOKENS)
    )
