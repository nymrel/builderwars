#!/usr/bin/env python3
"""Adversarial checks for the offline BuildWars private lifecycle."""

from __future__ import annotations

import copy

from check_buildwars_format import fixture

from buildwars import digest, seal_buildoff
from buildwars.lifecycle import (
    BINDING_MISMATCH,
    CAPACITY_RESERVED,
    CHAIN_BROKEN,
    COUNT_OVERFLOW,
    ENUM_INVALID,
    FORK_DETECTED,
    IDEMPOTENCY_CONFLICT,
    KEY_INVALID,
    RECOMPUTE_FAILED,
    ROLE_COLLISION,
    SCHEMA_MALFORMED,
    SIZE_OVERFLOW,
    STALE_EVENT,
    TIMESTAMP_INVALID,
    TRANSITION_ILLEGAL,
    BuildWarsLifecycleError,
    append_lifecycle_event,
    assert_new_use_allowed,
    compare_lifecycle_logs,
    lifecycle_fingerprint,
    lifecycle_genesis_hash,
    make_lifecycle_event,
    replay_lifecycle,
    verify_suppression,
)


CHECKS = 0
LIFECYCLE = "bwl1_" + "a" * 24
TENANT = "ten1_" + "b" * 24
CREATOR = "act1_" + "c" * 24
REVIEWER = "act1_" + "d" * 24
APPEAL_AUTHOR = "act1_" + "e" * 24
APPEAL_RESOLVER = "act1_" + "f" * 24
STEWARD = "act1_" + "1" * 24


def check(condition: bool, label: str) -> None:
    global CHECKS
    if not condition:
        raise AssertionError(label)
    CHECKS += 1
    print(f"PASS {label}")


def expect_code(action, label: str, code: str) -> None:
    global CHECKS
    try:
        action()
    except BuildWarsLifecycleError as exc:
        if exc.code != code:
            raise AssertionError(f"{label}: expected {code}, got {exc.code}: {exc}") from exc
        CHECKS += 1
        print(f"PASS {label} [{code}]")
        return
    raise AssertionError(f"{label}: expected refusal {code}")


def idem(index: int) -> str:
    return f"bwi1_{index:024x}"


def core_pins() -> dict[str, str]:
    return {
        "challenge": "buildwars.challenge.v1",
        "entry": "buildwars.entry.v1",
        "judgment": "buildwars.judgment.v1",
        "receipt": "buildwars.buildoff_receipt.v1",
        "projection": "buildwars.candidate_projection.v1",
    }


def score_fixture():
    challenge, entries, judgments = fixture()
    normalized = []
    for judgment in judgments:
        item = copy.deepcopy(judgment)
        item["reviewerRef"] = REVIEWER
        item["judgmentDigest"] = digest({key: value for key, value in item.items() if key != "judgmentDigest"})
        normalized.append(item)
    receipt = seal_buildoff(challenge, entries, normalized)
    return challenge, entries, normalized, receipt


def binding(challenge, entries, judgments=None, receipt=None) -> dict:
    return {
        "challengeDigest": challenge["challengeDigest"],
        "rubricDigest": challenge["rubric"]["rubricDigest"],
        "entryDigests": sorted(item["entryDigest"] for item in entries),
        "judgmentDigests": sorted(item["judgmentDigest"] for item in (judgments or [])),
        "receiptId": receipt["receiptId"] if receipt is not None else None,
    }


def evidence_for(events, score_evidence):
    return {
        event["eventHash"]: score_evidence
        for event in events
        if event["eventType"] == "candidate_scored"
    }


def add(
    events,
    evidence_map,
    *,
    actor,
    role,
    timestamp,
    event_type,
    key_index,
    bindings,
    payload,
    score_evidence=None,
):
    event = make_lifecycle_event(
        events,
        lifecycle_id=LIFECYCLE,
        tenant_id=TENANT,
        actor_id=actor,
        actor_role=role,
        timestamp=timestamp,
        event_type=event_type,
        idempotency_key=idem(key_index),
        digest_bindings=bindings,
        payload=payload,
        score_evidence=score_evidence,
        score_evidence_by_event_hash=evidence_map,
    )
    updated = append_lifecycle_event(
        events,
        event,
        score_evidence=score_evidence,
        score_evidence_by_event_hash=evidence_map,
    )
    next_evidence = dict(evidence_map)
    if score_evidence is not None:
        next_evidence[event["eventHash"]] = score_evidence
    return updated, next_evidence, event


def rechain(events):
    result = copy.deepcopy(events)
    for index, event in enumerate(result):
        if index == 0:
            bindings = event["digestBindings"]
            event["priorEventHash"] = lifecycle_genesis_hash(
                event["lifecycleId"],
                event["tenantId"],
                bindings["challengeDigest"],
                bindings["rubricDigest"],
            )
        else:
            event["priorEventHash"] = result[index - 1]["eventHash"]
        event["eventHash"] = digest({key: value for key, value in event.items() if key != "eventHash"})
    return result


def main() -> None:
    challenge, entries, judgments, receipt = score_fixture()
    draft_binding = binding(challenge, entries)
    scored_binding = binding(challenge, entries, judgments, receipt)
    score_evidence = {
        "challenge": challenge,
        "entries": entries,
        "judgments": judgments,
        "receipt": receipt,
    }
    events = []
    evidence_map = {}

    events, evidence_map, opened = add(
        events,
        evidence_map,
        actor=CREATOR,
        role="creator",
        timestamp=100,
        event_type="creator_draft_opened",
        key_index=1,
        bindings=draft_binding,
        payload={"draftTitle": "Fixture build-off", "draftNote": "private draft", "coreSchemaPins": core_pins()},
    )
    check(opened["sequence"] == 0, "genesis draft starts at sequence zero")
    events, evidence_map, _ = add(
        events,
        evidence_map,
        actor=CREATOR,
        role="creator",
        timestamp=101,
        event_type="creator_draft_amended",
        key_index=2,
        bindings=draft_binding,
        payload={
            "draftTitle": "Fixture build-off v2",
            "draftNote": "exact entries frozen next",
            "entryDigests": draft_binding["entryDigests"],
        },
    )
    events, evidence_map, _ = add(
        events,
        evidence_map,
        actor=CREATOR,
        role="creator",
        timestamp=102,
        event_type="review_submitted",
        key_index=3,
        bindings=draft_binding,
        payload={"submissionSummary": "immutable private review submission"},
    )
    submitted_log = copy.deepcopy(events)
    events, evidence_map, _ = add(
        events,
        evidence_map,
        actor=REVIEWER,
        role="reviewer",
        timestamp=103,
        event_type="review_decision_recorded",
        key_index=4,
        bindings=draft_binding,
        payload={
            "decision": "accepted_for_scoring",
            "decisionSummary": "eligible for offline artifact scoring",
            "reviewerRef": REVIEWER,
            "reviewerVersion": "1.0.0",
            "coi": {"declaredRelationships": ["none_declared"], "coiStatus": "unattested_self_declared"},
        },
    )
    events, evidence_map, scored_event = add(
        events,
        evidence_map,
        actor=REVIEWER,
        role="reviewer",
        timestamp=104,
        event_type="candidate_scored",
        key_index=5,
        bindings=scored_binding,
        payload={
            "receiptSummary": {
                "receiptId": receipt["receiptId"],
                "candidateWinnerEntryIds": receipt["candidateWinnerEntryIds"],
                "tie": receipt["tie"],
            }
        },
        score_evidence=score_evidence,
    )
    scored_log = copy.deepcopy(events)
    scored_evidence_map = dict(evidence_map)
    projection = replay_lifecycle(events, score_evidence_by_event_hash=evidence_map)
    check(projection["stage"] == "scored" and projection["receiptId"] == receipt["receiptId"], "full documents seal candidate score")
    check(projection["newUseEligible"] is True and projection["useStatus"] == "private_candidate_only", "scored candidate permits private use only")
    check(
        all(
            projection[field] is False
            for field in (
                "publicEligible",
                "shareEligible",
                "rankingEligible",
                "titleEligible",
                "agentWarsRatingEligible",
                "modelAttested",
                "providerAttested",
                "executionAttested",
                "reviewerIdentityAttested",
                "reviewerIndependenceAttested",
                "authenticationAttested",
                "storageErasurePerformed",
            )
        ),
        "private lifecycle creates no public, rating, identity, provider, execution, auth, or erasure authority",
    )
    check(assert_new_use_allowed(events, score_evidence_by_event_hash=evidence_map) == projection, "new-use guard admits the private scored state")

    events, evidence_map, _ = add(
        events,
        evidence_map,
        actor=APPEAL_AUTHOR,
        role="appeal_author",
        timestamp=105,
        event_type="appeal_opened",
        key_index=6,
        bindings=scored_binding,
        payload={
            "appealGrounds": "review one criterion binding",
            "appealedJudgmentDigests": [judgments[0]["judgmentDigest"]],
        },
    )
    open_appeal_projection = replay_lifecycle(events, score_evidence_by_event_hash=evidence_map)
    check(
        open_appeal_projection["newUseEligible"] is False
        and open_appeal_projection["useStatus"] == "appeal_pending",
        "open appeal suspends private candidate use",
    )
    expect_code(
        lambda: assert_new_use_allowed(events, score_evidence_by_event_hash=evidence_map),
        "open appeal cannot seed new private use",
        TRANSITION_ILLEGAL,
    )
    events, evidence_map, _ = add(
        events,
        evidence_map,
        actor=APPEAL_RESOLVER,
        role="appeal_resolver",
        timestamp=106,
        event_type="appeal_resolved",
        key_index=7,
        bindings=scored_binding,
        payload={
            "outcome": "dismissed",
            "resolutionSummary": "receipt and evidence binding stand",
            "resolverRef": APPEAL_RESOLVER,
            "resolverVersion": "1.0.0",
            "coi": {"declaredRelationships": ["none_declared"], "coiStatus": "unattested_self_declared"},
        },
    )
    dismissed_projection = replay_lifecycle(events, score_evidence_by_event_hash=evidence_map)
    check(
        dismissed_projection["appealCount"] == 1 and dismissed_projection["newUseEligible"] is True,
        "dismissed appeal remains in history and restores private candidate use",
    )
    appeal_resolved_log = copy.deepcopy(events)
    appeal_resolved_evidence = dict(evidence_map)

    expect_code(
        lambda: make_lifecycle_event(
            appeal_resolved_log,
            lifecycle_id=LIFECYCLE,
            tenant_id=TENANT,
            actor_id=STEWARD,
            actor_role="steward",
            timestamp=107,
            event_type="candidate_revoked",
            idempotency_key=idem(74),
            digest_bindings=scored_binding,
            payload={"revocationReason": "appeal_upheld", "revocationSummary": "mislabeled reason"},
            score_evidence_by_event_hash=appeal_resolved_evidence,
        ),
        "appeal_upheld reason requires an upheld appeal",
        BINDING_MISMATCH,
    )

    events, evidence_map, revoked_event = add(
        events,
        evidence_map,
        actor=STEWARD,
        role="steward",
        timestamp=107,
        event_type="candidate_revoked",
        key_index=8,
        bindings=scored_binding,
        payload={"revocationReason": "integrity_concern", "revocationSummary": "private use stopped"},
    )
    revoked_projection = replay_lifecycle(events, score_evidence_by_event_hash=evidence_map)
    check(revoked_projection["stage"] == "revoked" and revoked_projection["newUseEligible"] is False, "revocation preserves history and blocks new use")
    expect_code(
        lambda: assert_new_use_allowed(events, score_evidence_by_event_hash=evidence_map),
        "revoked lifecycle cannot seed new use",
        TRANSITION_ILLEGAL,
    )
    events, evidence_map, _ = add(
        events,
        evidence_map,
        actor=STEWARD,
        role="steward",
        timestamp=108,
        event_type="lifecycle_retired",
        key_index=9,
        bindings=scored_binding,
        payload={
            "retentionClass": "retain_full_history_indefinitely",
            "retirementSummary": "historical receipt retained",
        },
    )
    pre_tombstone = replay_lifecycle(events, score_evidence_by_event_hash=evidence_map)
    events, evidence_map, _ = add(
        events,
        evidence_map,
        actor=STEWARD,
        role="steward",
        timestamp=109,
        event_type="privacy_tombstoned",
        key_index=10,
        bindings=scored_binding,
        payload={
            "suppressionScope": "whole_projection",
            "tombstoneReasonClass": "participant_privacy_request",
            "suppressedProjectionDigest": digest(pre_tombstone),
        },
    )
    tombstone_projection = verify_suppression(events, score_evidence_by_event_hash=evidence_map)
    check(
        tombstone_projection["stage"] == "tombstoned"
        and "storage erasure" in tombstone_projection["truth"],
        "tombstone proves logical suppression without claiming erasure",
    )
    check(len(events) == tombstone_projection["eventCount"], "tombstone leaves every hash-chained event present")

    hostile_evidence = copy.deepcopy(score_evidence)
    hostile_evidence["judgments"][0]["totalPoints"] += 1
    hostile_evidence["judgments"][0]["judgmentDigest"] = digest(
        {key: value for key, value in hostile_evidence["judgments"][0].items() if key != "judgmentDigest"}
    )
    expect_code(
        lambda: replay_lifecycle(
            scored_log,
            score_evidence_by_event_hash={scored_event["eventHash"]: hostile_evidence},
        ),
        "recomputed judgment with editable total cannot seal",
        RECOMPUTE_FAILED,
    )
    hostile_evidence = copy.deepcopy(score_evidence)
    hostile_receipt = hostile_evidence["receipt"]
    hostile_receipt["candidateWinnerEntryIds"] = [entries[1]["entryId"]]
    hostile_receipt["receiptId"] = digest({key: value for key, value in hostile_receipt.items() if key != "receiptId"})
    expect_code(
        lambda: replay_lifecycle(
            scored_log,
            score_evidence_by_event_hash={scored_event["eventHash"]: hostile_evidence},
        ),
        "recomputed receipt cannot replace derived winner",
        RECOMPUTE_FAILED,
    )
    hostile_evidence = copy.deepcopy(score_evidence)
    hostile_receipt = hostile_evidence["receipt"]
    hostile_receipt["rankingEligible"] = True
    hostile_receipt["receiptId"] = digest({key: value for key, value in hostile_receipt.items() if key != "receiptId"})
    expect_code(
        lambda: replay_lifecycle(
            scored_log,
            score_evidence_by_event_hash={scored_event["eventHash"]: hostile_evidence},
        ),
        "recomputed receipt cannot self-escalate ranking authority",
        RECOMPUTE_FAILED,
    )
    hostile_evidence = copy.deepcopy(score_evidence)
    hostile_judgment = hostile_evidence["judgments"][0]
    hostile_judgment["entryDigest"] = entries[1]["entryDigest"]
    hostile_judgment["judgmentDigest"] = digest(
        {key: value for key, value in hostile_judgment.items() if key != "judgmentDigest"}
    )
    expect_code(
        lambda: replay_lifecycle(
            scored_log,
            score_evidence_by_event_hash={scored_event["eventHash"]: hostile_evidence},
        ),
        "full-document sealing rejects semantically swapped judgment",
        RECOMPUTE_FAILED,
    )
    hostile_evidence = copy.deepcopy(score_evidence)
    hostile_evidence["entries"] = [copy.deepcopy(entries[0]) for _ in range(65)]
    expect_code(
        lambda: replay_lifecycle(
            scored_log,
            score_evidence_by_event_hash={scored_event["eventHash"]: hostile_evidence},
        ),
        "score sidecar count is bounded before core validation",
        COUNT_OVERFLOW,
    )
    hostile_evidence = copy.deepcopy(score_evidence)
    hostile_evidence["challenge"]["padding"] = "x" * (257 * 1024)
    expect_code(
        lambda: replay_lifecycle(
            scored_log,
            score_evidence_by_event_hash={scored_event["eventHash"]: hostile_evidence},
        ),
        "each score sidecar document is size-bounded before validation",
        SIZE_OVERFLOW,
    )
    hostile_evidence = copy.deepcopy(score_evidence)
    nested = {}
    cursor = nested
    for _ in range(1_100):
        cursor["nested"] = {}
        cursor = cursor["nested"]
    hostile_evidence["challenge"]["nested"] = nested
    expect_code(
        lambda: replay_lifecycle(
            scored_log,
            score_evidence_by_event_hash={scored_event["eventHash"]: hostile_evidence},
        ),
        "pathologically nested sidecar fails with a lifecycle code",
        SCHEMA_MALFORMED,
    )
    nested_payload = {}
    cursor = nested_payload
    for _ in range(1_100):
        cursor["nested"] = {}
        cursor = cursor["nested"]
    expect_code(
        lambda: make_lifecycle_event(
            scored_log,
            lifecycle_id=LIFECYCLE,
            tenant_id=TENANT,
            actor_id=APPEAL_AUTHOR,
            actor_role="appeal_author",
            timestamp=105,
            event_type="appeal_opened",
            idempotency_key=idem(75),
            digest_bindings=scored_binding,
            payload=nested_payload,
            score_evidence_by_event_hash=scored_evidence_map,
        ),
        "pathologically nested constructor payload fails with a lifecycle code",
        SCHEMA_MALFORMED,
    )

    hostile = copy.deepcopy(scored_log)
    hostile[2]["timestamp"] = 99
    hostile = rechain(hostile)
    expect_code(
        lambda: replay_lifecycle(hostile, score_evidence_by_event_hash=evidence_for(hostile, score_evidence)),
        "rebuilt chain still rejects decreasing caller timestamp",
        TIMESTAMP_INVALID,
    )
    hostile = copy.deepcopy(scored_log)
    hostile[3]["digestBindings"]["challengeDigest"] = "f" * 64
    hostile = rechain(hostile)
    expect_code(
        lambda: replay_lifecycle(hostile, score_evidence_by_event_hash=evidence_for(hostile, score_evidence)),
        "rebuilt chain cannot rewrite frozen challenge binding",
        BINDING_MISMATCH,
    )
    hostile = copy.deepcopy(scored_log)
    hostile[3]["payload"]["reviewerIndependenceAttested"] = True
    hostile = rechain(hostile)
    expect_code(
        lambda: replay_lifecycle(hostile, score_evidence_by_event_hash=evidence_for(hostile, score_evidence)),
        "review payload cannot launder independence attestation",
        KEY_INVALID,
    )
    hostile = copy.deepcopy(scored_log)
    hostile[4]["payload"]["agentWarsRating"] = 99
    hostile = rechain(hostile)
    expect_code(
        lambda: replay_lifecycle(hostile, score_evidence_by_event_hash=evidence_for(hostile, score_evidence)),
        "score payload cannot create an AgentWars rating",
        KEY_INVALID,
    )
    hostile = copy.deepcopy(events)
    hostile[-1]["payload"]["purgedDigests"] = [receipt["receiptId"]]
    hostile = rechain(hostile)
    expect_code(
        lambda: replay_lifecycle(hostile, score_evidence_by_event_hash=evidence_for(hostile, score_evidence)),
        "tombstone cannot claim purge or physical deletion",
        KEY_INVALID,
    )
    hostile = copy.deepcopy(scored_log)
    hostile[3]["actorId"] = CREATOR
    hostile[3]["payload"]["reviewerRef"] = CREATOR
    hostile = rechain(hostile)
    expect_code(
        lambda: replay_lifecycle(hostile, score_evidence_by_event_hash=evidence_for(hostile, score_evidence)),
        "creator cannot occupy structural reviewer role",
        ROLE_COLLISION,
    )

    rejected_log = copy.deepcopy(submitted_log)
    rejected_evidence = {}
    rejected_log, rejected_evidence, _ = add(
        rejected_log,
        rejected_evidence,
        actor=REVIEWER,
        role="reviewer",
        timestamp=103,
        event_type="review_decision_recorded",
        key_index=40,
        bindings=draft_binding,
        payload={
            "decision": "rejected_at_review",
            "decisionSummary": "not admitted",
            "reviewerRef": REVIEWER,
            "reviewerVersion": "1.0.0",
            "coi": {"declaredRelationships": ["none_declared"], "coiStatus": "unattested_self_declared"},
        },
    )
    expect_code(
        lambda: make_lifecycle_event(
            rejected_log,
            lifecycle_id=LIFECYCLE,
            tenant_id=TENANT,
            actor_id=REVIEWER,
            actor_role="reviewer",
            timestamp=104,
            event_type="candidate_scored",
            idempotency_key=idem(41),
            digest_bindings=scored_binding,
            payload={
                "receiptSummary": {
                    "receiptId": receipt["receiptId"],
                    "candidateWinnerEntryIds": receipt["candidateWinnerEntryIds"],
                    "tie": receipt["tie"],
                }
            },
            score_evidence=score_evidence,
            score_evidence_by_event_hash=rejected_evidence,
        ),
        "rejected review cannot become candidate score",
        TRANSITION_ILLEGAL,
    )

    two_appeals = copy.deepcopy(appeal_resolved_log)
    two_appeal_evidence = dict(appeal_resolved_evidence)
    two_appeals, two_appeal_evidence, _ = add(
        two_appeals,
        two_appeal_evidence,
        actor=APPEAL_AUTHOR,
        role="appeal_author",
        timestamp=107,
        event_type="appeal_opened",
        key_index=50,
        bindings=scored_binding,
        payload={"appealGrounds": "second and final cycle", "appealedJudgmentDigests": [judgments[1]["judgmentDigest"]]},
    )
    two_appeals, two_appeal_evidence, _ = add(
        two_appeals,
        two_appeal_evidence,
        actor=APPEAL_RESOLVER,
        role="appeal_resolver",
        timestamp=108,
        event_type="appeal_resolved",
        key_index=51,
        bindings=scored_binding,
        payload={
            "outcome": "dismissed",
            "resolutionSummary": "second cycle resolved",
            "resolverRef": APPEAL_RESOLVER,
            "resolverVersion": "1.0.0",
            "coi": {"declaredRelationships": ["none_declared"], "coiStatus": "unattested_self_declared"},
        },
    )
    expect_code(
        lambda: make_lifecycle_event(
            two_appeals,
            lifecycle_id=LIFECYCLE,
            tenant_id=TENANT,
            actor_id=APPEAL_AUTHOR,
            actor_role="appeal_author",
            timestamp=109,
            event_type="appeal_opened",
            idempotency_key=idem(52),
            digest_bindings=scored_binding,
            payload={"appealGrounds": "third cycle", "appealedJudgmentDigests": [judgments[0]["judgmentDigest"]]},
            score_evidence_by_event_hash=two_appeal_evidence,
        ),
        "appeal cycles are bounded",
        COUNT_OVERFLOW,
    )
    expect_code(
        lambda: make_lifecycle_event(
            scored_log,
            lifecycle_id=LIFECYCLE,
            tenant_id=TENANT,
            actor_id=APPEAL_RESOLVER,
            actor_role="appeal_resolver",
            timestamp=105,
            event_type="appeal_resolved",
            idempotency_key=idem(53),
            digest_bindings=scored_binding,
            payload={
                "outcome": "dismissed",
                "resolutionSummary": "no open appeal",
                "resolverRef": APPEAL_RESOLVER,
                "resolverVersion": "1.0.0",
                "coi": {"declaredRelationships": ["none_declared"], "coiStatus": "unattested_self_declared"},
            },
            score_evidence_by_event_hash=scored_evidence_map,
        ),
        "appeal cannot resolve when none is open",
        TRANSITION_ILLEGAL,
    )

    stale = make_lifecycle_event(
        scored_log,
        lifecycle_id=LIFECYCLE,
        tenant_id=TENANT,
        actor_id=APPEAL_AUTHOR,
        actor_role="appeal_author",
        timestamp=105,
        event_type="appeal_opened",
        idempotency_key=idem(60),
        digest_bindings=scored_binding,
        payload={"appealGrounds": "stale branch", "appealedJudgmentDigests": [judgments[0]["judgmentDigest"]]},
        score_evidence_by_event_hash=scored_evidence_map,
    )
    expect_code(
        lambda: append_lifecycle_event(
            appeal_resolved_log,
            stale,
            score_evidence_by_event_hash=appeal_resolved_evidence,
        ),
        "event built against an old head is stale",
        STALE_EVENT,
    )
    unchanged = append_lifecycle_event(events, revoked_event, score_evidence_by_event_hash=evidence_map)
    check(unchanged == events, "byte-identical idempotency replay is a no-op")
    disordered = copy.deepcopy(events)
    disordered[0], disordered[1] = disordered[1], disordered[0]
    expect_code(
        lambda: append_lifecycle_event(disordered, revoked_event, score_evidence_by_event_hash=evidence_map),
        "idempotent replay still validates the complete existing log",
        CHAIN_BROKEN,
    )
    conflicting = copy.deepcopy(revoked_event)
    conflicting["payload"]["revocationSummary"] = "different body"
    conflicting["eventHash"] = digest({key: value for key, value in conflicting.items() if key != "eventHash"})
    expect_code(
        lambda: append_lifecycle_event(events, conflicting, score_evidence_by_event_hash=evidence_map),
        "same idempotency key cannot name a different event",
        IDEMPOTENCY_CONFLICT,
    )

    fork_base = scored_log[:1]
    fork_left, _, _ = add(
        fork_base,
        {},
        actor=CREATOR,
        role="creator",
        timestamp=101,
        event_type="creator_draft_amended",
        key_index=70,
        bindings=draft_binding,
        payload={"draftTitle": "left", "draftNote": "fork left", "entryDigests": draft_binding["entryDigests"]},
    )
    fork_right, _, _ = add(
        fork_base,
        {},
        actor=CREATOR,
        role="creator",
        timestamp=101,
        event_type="creator_draft_amended",
        key_index=71,
        bindings=draft_binding,
        payload={"draftTitle": "right", "draftNote": "fork right", "entryDigests": draft_binding["entryDigests"]},
    )
    expect_code(lambda: compare_lifecycle_logs(fork_left, fork_right), "same-sequence divergent copies expose a fork", FORK_DETECTED)
    prefix_comparison = compare_lifecycle_logs(scored_log[:1], scored_log, right_score_evidence=scored_evidence_map)
    check(
        prefix_comparison["forkDetected"] is False
        and prefix_comparison["left"]["headEventHash"] != prefix_comparison["right"]["headEventHash"],
        "truncation is externally visible as a different count and head fingerprint",
    )

    hostile = copy.deepcopy(scored_log)
    hostile[1]["timestamp"] = 100.5
    expect_code(
        lambda: replay_lifecycle(hostile, score_evidence_by_event_hash=evidence_for(hostile, score_evidence)),
        "floating caller timestamp is rejected",
        SCHEMA_MALFORMED,
    )
    hostile = copy.deepcopy(scored_log)
    hostile[1]["payload"]["draftNote"] = "surrogate-\ud800"
    expect_code(
        lambda: replay_lifecycle(hostile, score_evidence_by_event_hash=evidence_for(hostile, score_evidence)),
        "lone Unicode surrogate is rejected",
        SCHEMA_MALFORMED,
    )
    try:
        make_lifecycle_event(
            scored_log,
            lifecycle_id=LIFECYCLE,
            tenant_id=TENANT,
            actor_id=APPEAL_AUTHOR,
            actor_role="appeal_author",
            timestamp=105,
            event_type="caller_secret_event",
            idempotency_key=idem(76),
            digest_bindings=scored_binding,
            payload={},
            score_evidence_by_event_hash=scored_evidence_map,
        )
    except BuildWarsLifecycleError as exc:
        check(
            exc.code == ENUM_INVALID and "caller_secret_event" not in str(exc),
            "unsupported event type is refused without echoing caller data",
        )
    else:
        raise AssertionError("unsupported event type must be refused")
    expect_code(
        lambda: make_lifecycle_event(
            scored_log,
            lifecycle_id=LIFECYCLE,
            tenant_id=TENANT,
            actor_id=STEWARD,
            actor_role="steward",
            timestamp=105,
            event_type="receipt_superseded",
            idempotency_key=idem(72),
            digest_bindings=scored_binding,
            payload={
                "supersedingLifecycleId": LIFECYCLE,
                "supersedingReceiptId": receipt["receiptId"],
                "supersedeSummary": "self",
            },
            score_evidence_by_event_hash=scored_evidence_map,
        ),
        "lifecycle cannot supersede itself",
        BINDING_MISMATCH,
    )
    expect_code(
        lambda: make_lifecycle_event(
            scored_log,
            lifecycle_id=LIFECYCLE,
            tenant_id=TENANT,
            actor_id=REVIEWER,
            actor_role="steward",
            timestamp=105,
            event_type="candidate_revoked",
            idempotency_key=idem(73),
            digest_bindings=scored_binding,
            payload={"revocationReason": "steward_action", "revocationSummary": "role collision"},
            score_evidence_by_event_hash=scored_evidence_map,
        ),
        "steward actor must differ from creator and reviewer actors",
        ROLE_COLLISION,
    )

    capacity_log = copy.deepcopy(scored_log[:1])
    for index in range(1, 62):
        capacity_log, _, _ = add(
            capacity_log,
            {},
            actor=CREATOR,
            role="creator",
            timestamp=100 + index,
            event_type="creator_draft_amended",
            key_index=100 + index,
            bindings=draft_binding,
            payload={
                "draftTitle": f"bounded draft {index}",
                "draftNote": "capacity fixture",
                "entryDigests": draft_binding["entryDigests"],
            },
        )
    check(len(capacity_log) == 62, "bounded log retains two terminal event slots")
    expect_code(
        lambda: make_lifecycle_event(
            capacity_log,
            lifecycle_id=LIFECYCLE,
            tenant_id=TENANT,
            actor_id=CREATOR,
            actor_role="creator",
            timestamp=200,
            event_type="creator_draft_amended",
            idempotency_key=idem(200),
            digest_bindings=draft_binding,
            payload={"draftTitle": "overflow", "draftNote": "no", "entryDigests": draft_binding["entryDigests"]},
        ),
        "nonterminal event cannot consume reserved terminal capacity",
        CAPACITY_RESERVED,
    )
    expect_code(
        lambda: replay_lifecycle([*capacity_log, *capacity_log[:3]]),
        "lifecycle event count is globally bounded",
        COUNT_OVERFLOW,
    )

    advisory = copy.deepcopy(scored_log)
    advisory[1]["timestamp"] = 100
    advisory = rechain(advisory)
    advisory_projection = replay_lifecycle(advisory, score_evidence_by_event_hash=evidence_for(advisory, score_evidence))
    check("caller-asserted" in advisory_projection["truth"], "monotonic timestamp edits remain explicitly unattested")
    fingerprint = lifecycle_fingerprint(events, score_evidence_by_event_hash=evidence_map)
    check(
        fingerprint == {
            "lifecycleId": LIFECYCLE,
            "eventCount": len(events),
            "headEventHash": events[-1]["eventHash"],
        },
        "lifecycle fingerprint binds exact event count and head",
    )

    print(f"BuildWars lifecycle: ALL CHECKS PASS ({CHECKS})")
    print("offline / append-only / full-document score sealing / no public authority / no erasure claim")


if __name__ == "__main__":
    main()
