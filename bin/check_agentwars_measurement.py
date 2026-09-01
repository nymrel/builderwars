#!/usr/bin/env python3
"""Adversarial checks for the schema-only AgentWars measurement contract."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publishing import measurement


checks = 0


def check(condition: bool, label: str) -> None:
    global checks
    if not condition:
        raise AssertionError(label)
    checks += 1


def expect_error(mutator: Callable[[dict[str, Any]], None], expected: str, *, event_name: str = "share_landing_viewed") -> None:
    candidate = make_event(event_name, 90)
    mutator(candidate)
    try:
        measurement.validate_event(candidate)
    except measurement.MeasurementError as error:
        check(expected.lower() in str(error).lower(), f"refusal names {expected!r}: {error}")
    else:
        raise AssertionError(f"unsafe event was accepted; expected {expected!r}")


def make_event(event_name: str, index: int) -> dict[str, Any]:
    properties: dict[str, str] = {
        "match_id": "match_alpha_01",
        "clip_id": "clip_0123456789abcdef",
    }
    if event_name == "share_intent_recorded":
        properties.update(
            share_method="native",
            surface="receipt_card",
            campaign_id="agentwars_verified_moments_v1",
            creative_id="moment_0123456789abcdef",
        )
    elif event_name == "share_landing_viewed":
        properties.update(
            source_label="agentwars_share_bundle",
            campaign_id="agentwars_verified_moments_v1",
            creative_id="moment_0123456789abcdef",
            surface="share_landing",
        )
    elif event_name == "replay_started":
        properties["surface"] = "match_page"
    elif event_name == "replay_verified":
        properties.update(verdict="PASS", surface="match_page")
    elif event_name == "spectator_vote_cast":
        properties.update(vote="runback", surface="match_page")
    elif event_name == "league_join_clicked":
        properties["surface"] = "match_page"
    else:
        raise AssertionError(f"test fixture does not support {event_name}")
    return {
        "schemaVersion": measurement.EVENT_SCHEMA_VERSION,
        "eventId": "awmevt_" + format(index, "032x"),
        "eventName": event_name,
        "occurredAt": "2026-09-01T12:00:00Z",
        "properties": properties,
    }


def main() -> int:
    contract = measurement.measurement_contract()
    check(contract["schemaVersion"] == measurement.MEASUREMENT_CONTRACT_VERSION, "contract version is pinned")
    check(contract["status"] == "schema_only_not_instrumented", "contract refuses instrumentation overclaim")
    check(set(contract["events"]) == set(measurement.EVENT_SCHEMA), "contract exports every exact event")
    check(measurement.forbidden_contract_fields() == [], "contract contains no privacy-forbidden field")
    check(all(value is False for value in contract["authority"].values()), "contract grants no measurement or launch authority")
    check(contract["privacy"]["exactFieldsOnly"] is True, "contract requires exact fields")
    check(all(
        value is False
        for key, value in contract["privacy"].items()
        if key != "exactFieldsOnly"
    ), "contract accepts no raw, personal, network, prompt, output, or credential material")

    contract_digest = measurement.measurement_contract_digest()
    check(len(contract_digest) == 64, "contract digest is SHA-256 shaped")
    check(contract_digest == measurement.digest(measurement.measurement_contract()), "contract digest is reproducible")
    reordered = json.loads(json.dumps(contract, sort_keys=True))
    check(measurement.digest(reordered) == contract_digest, "contract digest ignores object key order")

    events = []
    for index, event_name in enumerate(measurement.EVENT_SCHEMA, 1):
        candidate = make_event(event_name, index)
        validated = measurement.validate_event(candidate)
        check(validated == candidate, f"{event_name} valid event is stable")
        check(len(measurement.digest(validated)) == 64, f"{event_name} has deterministic digest")
        events.append(candidate)

    aggregate = measurement.aggregate_in_memory(events, "2026-09-01T12:00:01Z")
    check(aggregate["schemaVersion"] == measurement.AGGREGATE_SCHEMA_VERSION, "aggregate schema is pinned")
    check(aggregate["sourceStatus"] == "in_memory_validation_only", "aggregate discloses memory-only source")
    check(aggregate["totalEvents"] == len(events), "aggregate counts every candidate once")
    check(aggregate["uniqueEventIds"] == len(events), "aggregate proves event-id uniqueness")
    check(all(count == 1 for count in aggregate["eventCounts"].values()), "aggregate preserves exact per-event counts")
    for flag in (
        "productionDataRead",
        "durableCounterProven",
        "audienceMeasured",
        "performanceMeasured",
        "builderIdentityAvailable",
        "retentionMeasured",
        "launchable",
    ):
        check(aggregate[flag] is False, f"aggregate keeps {flag} false")

    baseline = measurement.build_zero_baseline("2026-09-01T12:00:01Z")
    check(baseline["schemaVersion"] == measurement.BASELINE_SCHEMA_VERSION, "baseline schema is pinned")
    check(baseline["contractDigest"] == contract_digest, "baseline binds the exact contract")
    check(baseline["sourceStatus"] == "no_source_configured", "baseline discloses absent source")
    check(baseline["instrumentationStatus"] == "schema_only_not_instrumented", "baseline discloses absent instrumentation")
    check(baseline["totalEvents"] == 0, "zero baseline has zero total events")
    check(set(baseline["eventCounts"]) == set(measurement.EVENT_SCHEMA), "zero baseline names every event")
    check(all(count == 0 for count in baseline["eventCounts"].values()), "zero baseline has no fabricated counts")
    for flag in (
        "productionDataRead",
        "durableCounterProven",
        "audienceMeasured",
        "performanceMeasured",
        "builderIdentityAvailable",
        "retentionMeasured",
        "launchable",
    ):
        check(baseline[flag] is False, f"baseline keeps {flag} false")

    expect_error(lambda row: row.__setitem__("schemaVersion", "agentwars.measurement-event/2"), "schemaVersion")
    expect_error(lambda row: row.__setitem__("extra", "value"), "fields")
    expect_error(lambda row: row.__setitem__("eventId", "awmevt_bad"), "eventId")
    expect_error(lambda row: row.__setitem__("eventName", "account_created"), "eventName")
    expect_error(lambda row: row.__setitem__("occurredAt", "2026-09-01T05:00:00-07:00"), "UTC timestamp")
    expect_error(lambda row: row.__setitem__("occurredAt", "2026-02-31T12:00:00Z"), "invalid")
    expect_error(lambda row: row.__setitem__("properties", []), "object")
    expect_error(lambda row: row["properties"].pop("match_id"), "required")
    expect_error(lambda row: row["properties"].__setitem__("href", "https://example.com"), "unknown")
    expect_error(lambda row: row["properties"].__setitem__("user_id", "person_1"), "unknown")
    expect_error(lambda row: row["properties"].__setitem__("match_id", "https://example.com/path?q=secret"), "match_id")
    expect_error(lambda row: row["properties"].__setitem__("clip_id", "clip_not-a-digest"), "clip_id")
    expect_error(lambda row: row["properties"].__setitem__("source_label", "AgentWars Share"), "source_label")
    expect_error(lambda row: row["properties"].__setitem__("creative_id", "moment_unknown"), "creative_id")
    expect_error(lambda row: row["properties"].__setitem__("surface", "account_page"), "allowlist")
    expect_error(
        lambda row: row["properties"].__setitem__("share_method", "auto_post"),
        "allowlist",
        event_name="share_intent_recorded",
    )
    expect_error(
        lambda row: row["properties"].__setitem__("verdict", "UNKNOWN"),
        "allowlist",
        event_name="replay_verified",
    )
    expect_error(
        lambda row: row["properties"].__setitem__("vote", "winner"),
        "allowlist",
        event_name="spectator_vote_cast",
    )

    duplicate = [make_event("replay_started", 1), make_event("replay_verified", 1)]
    try:
        measurement.aggregate_in_memory(duplicate, "2026-09-01T12:00:01Z")
    except measurement.MeasurementError as error:
        check("duplicate eventId" in str(error), "aggregate refuses duplicate event ids")
    else:
        raise AssertionError("aggregate accepted duplicate event ids")

    future = make_event("replay_started", 77)
    future["occurredAt"] = "2026-09-01T12:00:02Z"
    try:
        measurement.aggregate_in_memory([future], "2026-09-01T12:00:01Z")
    except measurement.MeasurementError as error:
        check("after the observation" in str(error), "aggregate refuses future event")
    else:
        raise AssertionError("aggregate accepted future event")

    module_path = ROOT / "publishing" / "measurement.py"
    module_source = module_path.read_text(encoding="utf-8")
    module_tree = ast.parse(module_source)
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(module_tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(module_tree)
        if isinstance(node, ast.ImportFrom) and node.level == 0
    }
    check(imports.issubset({"__future__", "datetime", "hashlib", "json", "re", "typing"}), "measurement module has no network, storage, or provider import")
    check("open(" not in module_source and "subprocess" not in module_source, "measurement module performs no file or process operation")

    serialized = json.dumps({"contract": contract, "baseline": baseline, "aggregate": aggregate}, sort_keys=True)
    for forbidden in (
        '"launchable": true',
        '"audienceMeasured": true',
        '"performanceMeasured": true',
        '"retentionMeasured": true',
        "https://",
        "OPENROUTER_API_KEY",
    ):
        check(forbidden not in serialized, f"evidence omits unsafe claim or material {forbidden!r}")

    print(f"AgentWars measurement contract: PASS ({checks} checks)")
    print("six allowlisted events / strict privacy / zero baseline / no transport or live claims")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
