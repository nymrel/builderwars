#!/usr/bin/env python3
"""Adversarial checks for the AgentWars tester-ceremony readiness contract."""

from __future__ import annotations

import ast
import copy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publishing import tester_readiness as tr


CHECKS = 0
OBSERVED_AT = "2026-09-01T00:00:00Z"
COMMIT = "1" * 40
TREE = "2" * 40


def check(condition: bool, label: str) -> None:
    global CHECKS
    if not condition:
        raise AssertionError(label)
    CHECKS += 1


def refuses(callable_, label: str) -> None:
    try:
        callable_()
    except tr.TesterReadinessError:
        check(True, label)
    else:
        raise AssertionError(label)


def reseal(value: dict[str, object], field: str) -> dict[str, object]:
    result = copy.deepcopy(value)
    result.pop(field, None)
    result[field] = tr.digest(result)
    return result


def journey_observations() -> list[dict[str, object]]:
    return [
        {
            "stepId": step["stepId"],
            "localStatus": "LOCAL_PASS" if step["localRehearsal"] == "required" else "NOT_APPLICABLE_PROTECTED",
            "evidenceDigest": tr.digest({"fixture": step["stepId"]}) if step["localRehearsal"] == "required" else None,
            "humanObserved": False,
            "protectedCompletionStatus": "HELD_PROTECTED",
        }
        for step in tr.JOURNEY_STEPS
    ]


def cleanup_observations() -> list[dict[str, object]]:
    return [
        {
            "resourceClass": resource["resourceClass"],
            "localStatus": "LOCAL_CLEANUP_SIMULATED" if resource["localRehearsal"] == "required" else "NOT_APPLICABLE_PROTECTED",
            "evidenceDigest": tr.digest({"cleanupFixture": resource["resourceClass"]}) if resource["localRehearsal"] == "required" else None,
            "protectedCompletionStatus": "HELD_PROTECTED",
        }
        for resource in tr.CLEANUP_RESOURCES
    ]


def assert_authority_false(value: object, label: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "productionAuthority":
                check(item == tr.PRODUCTION_AUTHORITY, f"{label}: production authority is exact")
                check(all(type(flag) is bool and flag is False for flag in item.values()), f"{label}: authority flags are false booleans")
            if key in {
                "humanFeedbackCollected", "humanTesterCompleted", "productionJourneyCompleted",
                "productionCleanupCompleted", "accountDeletionCompleted", "consentedHumanJourneyCompleted",
                "readyForOperatorCeremony", "operatorActionExecuted",
            }:
                check(item is False, f"{label}: {key} remains false")
            assert_authority_false(item, label)
    elif isinstance(value, list):
        for item in value:
            assert_authority_false(item, label)


def main() -> int:
    rubric = tr.feedback_rubric()
    check(rubric["schemaVersion"] == tr.FEEDBACK_SCHEMA, "feedback rubric schema is pinned")
    check(rubric["rubricStatus"] == "template_only_no_human_response", "feedback rubric is template only")
    check(rubric["categories"] == [dict(item) for item in tr.FEEDBACK_CATEGORIES], "feedback categories are exact")
    check(len(rubric["categories"]) == 8, "feedback rubric has eight bounded categories")
    category_ids = [item["categoryId"] for item in rubric["categories"]]
    check(len(category_ids) == len(set(category_ids)) == 8, "feedback categories are unique")
    check(set(rubric["ratingScale"]) == {"1", "2", "3", "4", "5"}, "feedback rating scale is closed")
    check(rubric["blockerClasses"] == list(tr.BLOCKER_CLASSES), "feedback blocker classes are exact")
    check(rubric["identityFieldsAllowed"] == [], "feedback rubric admits no identity fields")
    check(rubric["humanFeedbackCollected"] is False, "feedback rubric cannot claim collection")
    unsigned_rubric = dict(rubric)
    supplied_rubric_digest = unsigned_rubric.pop("rubricDigest")
    check(tr.digest(unsigned_rubric) == supplied_rubric_digest, "feedback rubric digest verifies")
    assert_authority_false(rubric, "feedback rubric")

    contract = tr.tester_ceremony_contract()
    check(contract["schemaVersion"] == tr.CONTRACT_SCHEMA, "ceremony contract schema is pinned")
    check(contract["contractStatus"] == "local_rehearsal_template_protected_ceremony_held", "ceremony contract reports protected hold")
    check(contract["journeySteps"] == [dict(item) for item in tr.JOURNEY_STEPS], "ceremony contract publishes exact journey")
    check(len(contract["journeySteps"]) == 16, "ceremony contract has sixteen ordered steps")
    check([step["order"] for step in contract["journeySteps"]] == list(range(1, 17)), "journey order is contiguous")
    check(len({step["stepId"] for step in contract["journeySteps"]}) == 16, "journey step ids are unique")
    check(sum(step["localRehearsal"] == "required" for step in contract["journeySteps"]) == 6, "exactly six journey steps have local rehearsal")
    check(contract["feedbackRubricDigest"] == rubric["rubricDigest"], "ceremony binds feedback rubric")
    check(contract["cleanupResources"] == [dict(item) for item in tr.CLEANUP_RESOURCES], "ceremony contract publishes exact cleanup set")
    check(contract["prohibitedShortcuts"] == list(tr.PROHIBITED_SHORTCUTS), "ceremony contract publishes exact shortcut refusals")
    unsigned_contract = dict(contract)
    supplied_contract_digest = unsigned_contract.pop("contractDigest")
    check(tr.digest(unsigned_contract) == supplied_contract_digest, "ceremony contract digest verifies")
    assert_authority_false(contract, "ceremony contract")

    observations = journey_observations()
    rehearsal = tr.build_synthetic_rehearsal(
        observed_at=OBSERVED_AT,
        source_commit=COMMIT,
        source_tree=TREE,
        observations=observations,
    )
    check(rehearsal["schemaVersion"] == tr.REHEARSAL_SCHEMA, "rehearsal schema is pinned")
    check(rehearsal["rehearsalClass"] == "synthetic_local_only", "rehearsal class is synthetic only")
    check(rehearsal["observations"] == observations, "rehearsal retains exact observations")
    check(rehearsal["localRequiredCount"] == 6 and rehearsal["localPassCount"] == 6, "all six local rehearsal steps pass")
    check(rehearsal["protectedHeldCount"] == 16, "every journey step remains protected-held")
    check(all(item["protectedCompletionStatus"] == "HELD_PROTECTED" for item in rehearsal["observations"]), "no journey step claims protected completion")
    check(sum(item["evidenceDigest"] is not None for item in rehearsal["observations"]) == 6, "only local steps carry synthetic evidence")
    check(rehearsal["humanTesterCompleted"] is False, "synthetic rehearsal does not claim human tester")
    check(rehearsal["productionJourneyCompleted"] is False, "synthetic rehearsal does not claim production journey")
    check(rehearsal == tr.build_synthetic_rehearsal(observed_at=OBSERVED_AT, source_commit=COMMIT, source_tree=TREE, observations=observations), "synthetic rehearsal is deterministic")
    check(tr.digest({key: value for key, value in rehearsal.items() if key != "rehearsalDigest"}) == rehearsal["rehearsalDigest"], "rehearsal digest verifies")
    assert_authority_false(rehearsal, "synthetic rehearsal")

    refuses(lambda: tr.build_synthetic_rehearsal(observed_at="soon", source_commit=COMMIT, source_tree=TREE, observations=observations), "rehearsal refuses malformed time")
    refuses(lambda: tr.build_synthetic_rehearsal(observed_at=OBSERVED_AT, source_commit=COMMIT[:-1], source_tree=TREE, observations=observations), "rehearsal refuses malformed source commit")
    refuses(lambda: tr.build_synthetic_rehearsal(observed_at=OBSERVED_AT, source_commit=COMMIT, source_tree=TREE, observations=observations[:-1]), "rehearsal refuses missing step")
    hostile = copy.deepcopy(observations)
    hostile[0], hostile[1] = hostile[1], hostile[0]
    refuses(lambda: tr.build_synthetic_rehearsal(observed_at=OBSERVED_AT, source_commit=COMMIT, source_tree=TREE, observations=hostile), "rehearsal refuses step reordering")
    hostile = copy.deepcopy(observations)
    hostile[0]["stepId"] = hostile[1]["stepId"]
    refuses(lambda: tr.build_synthetic_rehearsal(observed_at=OBSERVED_AT, source_commit=COMMIT, source_tree=TREE, observations=hostile), "rehearsal refuses duplicate step id")
    hostile = copy.deepcopy(observations)
    hostile[0]["localStatus"] = "LOCAL_FAIL"
    refuses(lambda: tr.build_synthetic_rehearsal(observed_at=OBSERVED_AT, source_commit=COMMIT, source_tree=TREE, observations=hostile), "rehearsal refuses local status drift")
    hostile = copy.deepcopy(observations)
    hostile[1]["evidenceDigest"] = "a" * 64
    refuses(lambda: tr.build_synthetic_rehearsal(observed_at=OBSERVED_AT, source_commit=COMMIT, source_tree=TREE, observations=hostile), "protected step refuses synthetic completion evidence")
    hostile = copy.deepcopy(observations)
    hostile[0]["evidenceDigest"] = None
    refuses(lambda: tr.build_synthetic_rehearsal(observed_at=OBSERVED_AT, source_commit=COMMIT, source_tree=TREE, observations=hostile), "local step requires evidence digest")
    hostile = copy.deepcopy(observations)
    hostile[0]["humanObserved"] = True
    refuses(lambda: tr.build_synthetic_rehearsal(observed_at=OBSERVED_AT, source_commit=COMMIT, source_tree=TREE, observations=hostile), "rehearsal refuses human observation claim")
    hostile = copy.deepcopy(observations)
    hostile[0]["protectedCompletionStatus"] = "PASS"
    refuses(lambda: tr.build_synthetic_rehearsal(observed_at=OBSERVED_AT, source_commit=COMMIT, source_tree=TREE, observations=hostile), "rehearsal refuses protected completion claim")
    hostile = copy.deepcopy(observations)
    hostile[0]["unexpected"] = False
    refuses(lambda: tr.build_synthetic_rehearsal(observed_at=OBSERVED_AT, source_commit=COMMIT, source_tree=TREE, observations=hostile), "rehearsal refuses unknown observation field")

    for field in ("humanTesterCompleted", "productionJourneyCompleted"):
        hostile_rehearsal = copy.deepcopy(rehearsal)
        hostile_rehearsal[field] = True
        hostile_rehearsal = reseal(hostile_rehearsal, "rehearsalDigest")
        refuses(lambda hostile_rehearsal=hostile_rehearsal: tr.build_feedback_placeholder(rehearsal=hostile_rehearsal), f"feedback refuses resealed {field} claim")
    hostile_rehearsal = copy.deepcopy(rehearsal)
    hostile_rehearsal["productionAuthority"]["humanConsentAttested"] = True
    hostile_rehearsal = reseal(hostile_rehearsal, "rehearsalDigest")
    refuses(lambda: tr.build_feedback_placeholder(rehearsal=hostile_rehearsal), "feedback refuses consent authority escalation")

    feedback = tr.build_feedback_placeholder(rehearsal=rehearsal)
    check(feedback["schemaVersion"] == tr.FEEDBACK_PLACEHOLDER_SCHEMA, "feedback placeholder schema is pinned")
    check(feedback["feedbackStatus"] == "NOT_COLLECTED_SYNTHETIC_REHEARSAL", "synthetic feedback is uncollected")
    check(feedback["ratings"] == [] and feedback["blockerClasses"] == [], "synthetic feedback contains no scores or blockers")
    check(feedback["severeIssueClasses"] == [] and feedback["redactedNotes"] is None, "synthetic feedback contains no issue or prose")
    check(feedback["humanFeedbackCollected"] is False, "synthetic feedback cannot claim human collection")
    check(feedback["rubricDigest"] == rubric["rubricDigest"], "feedback placeholder binds rubric")
    check(feedback == tr.build_feedback_placeholder(rehearsal=rehearsal), "feedback placeholder is deterministic")
    assert_authority_false(feedback, "feedback placeholder")

    cleanup_rows = cleanup_observations()
    cleanup = tr.build_cleanup_rehearsal(rehearsal=rehearsal, observations=cleanup_rows)
    check(cleanup["schemaVersion"] == tr.CLEANUP_SCHEMA, "cleanup schema is pinned")
    check(cleanup["observations"] == cleanup_rows, "cleanup retains exact resource observations")
    check(cleanup["localRequiredCount"] == 4 and cleanup["localPassCount"] == 4, "all four local cleanup simulations pass")
    check(cleanup["protectedHeldCount"] == len(tr.CLEANUP_RESOURCES), "every cleanup resource remains protected-held")
    check(sum(item["evidenceDigest"] is not None for item in cleanup["observations"]) == 4, "only local cleanup steps carry synthetic evidence")
    check(cleanup["productionCleanupCompleted"] is False, "cleanup does not claim production cleanup")
    check(cleanup["accountDeletionCompleted"] is False, "cleanup does not claim account deletion")
    check(cleanup == tr.build_cleanup_rehearsal(rehearsal=rehearsal, observations=cleanup_rows), "cleanup rehearsal is deterministic")
    assert_authority_false(cleanup, "cleanup rehearsal")

    refuses(lambda: tr.build_cleanup_rehearsal(rehearsal=rehearsal, observations=cleanup_rows[:-1]), "cleanup refuses missing resource class")
    hostile_cleanup_rows = copy.deepcopy(cleanup_rows)
    hostile_cleanup_rows[0], hostile_cleanup_rows[1] = hostile_cleanup_rows[1], hostile_cleanup_rows[0]
    refuses(lambda: tr.build_cleanup_rehearsal(rehearsal=rehearsal, observations=hostile_cleanup_rows), "cleanup refuses resource reordering")
    hostile_cleanup_rows = copy.deepcopy(cleanup_rows)
    hostile_cleanup_rows[0]["localStatus"] = "DELETED"
    refuses(lambda: tr.build_cleanup_rehearsal(rehearsal=rehearsal, observations=hostile_cleanup_rows), "cleanup refuses deletion claim")
    hostile_cleanup_rows = copy.deepcopy(cleanup_rows)
    hostile_cleanup_rows[4]["evidenceDigest"] = "b" * 64
    refuses(lambda: tr.build_cleanup_rehearsal(rehearsal=rehearsal, observations=hostile_cleanup_rows), "protected cleanup refuses synthetic evidence")
    hostile_cleanup_rows = copy.deepcopy(cleanup_rows)
    hostile_cleanup_rows[0]["protectedCompletionStatus"] = "PASS"
    refuses(lambda: tr.build_cleanup_rehearsal(rehearsal=rehearsal, observations=hostile_cleanup_rows), "cleanup refuses protected completion")

    decision = tr.evaluate_tester_readiness(rehearsal=rehearsal, feedback=feedback, cleanup=cleanup)
    check(decision["schemaVersion"] == tr.READINESS_SCHEMA, "readiness schema is pinned")
    check(decision["status"] == "LOCAL_REHEARSAL_PASS_PROTECTED_HELD", "readiness reports local pass and protected hold")
    check(decision["localRehearsalPassed"] is True, "readiness records local rehearsal pass")
    check(decision["humanFeedbackCollected"] is False, "readiness does not claim feedback")
    check(decision["consentedHumanJourneyCompleted"] is False, "readiness does not claim consented journey")
    check(decision["readyForOperatorCeremony"] is False, "readiness is not ready for operator ceremony")
    check(decision["operatorPacketStatus"] == "NOT_ACTIONABLE_STAGE_11_12_HELD", "operator packet remains non-actionable")
    check(decision["heldJourneyStepIds"] == [item["stepId"] for item in tr.JOURNEY_STEPS], "all journey steps remain held for real proof")
    check(decision["heldCleanupResourceClasses"] == [item["resourceClass"] for item in tr.CLEANUP_RESOURCES], "all cleanup resources remain held for real proof")
    check(decision["rehearsalDigest"] == rehearsal["rehearsalDigest"], "readiness binds rehearsal")
    check(decision["feedbackDigest"] == feedback["feedbackDigest"], "readiness binds feedback placeholder")
    check(decision["cleanupDigest"] == cleanup["cleanupDigest"], "readiness binds cleanup")
    check(tr.digest({key: value for key, value in decision.items() if key != "decisionDigest"}) == decision["decisionDigest"], "readiness digest verifies")
    assert_authority_false(decision, "readiness decision")

    hostile_feedback = copy.deepcopy(feedback)
    hostile_feedback["ratings"] = [{"categoryId": "return_intent", "rating": 5}]
    hostile_feedback["humanFeedbackCollected"] = True
    hostile_feedback = reseal(hostile_feedback, "feedbackDigest")
    refuses(lambda: tr.evaluate_tester_readiness(rehearsal=rehearsal, feedback=hostile_feedback, cleanup=cleanup), "readiness refuses fabricated human feedback")
    hostile_feedback = copy.deepcopy(feedback)
    hostile_feedback["redactedNotes"] = "Loved it"
    hostile_feedback = reseal(hostile_feedback, "feedbackDigest")
    refuses(lambda: tr.evaluate_tester_readiness(rehearsal=rehearsal, feedback=hostile_feedback, cleanup=cleanup), "readiness refuses synthetic prose")
    hostile_cleanup = copy.deepcopy(cleanup)
    hostile_cleanup["productionCleanupCompleted"] = True
    hostile_cleanup = reseal(hostile_cleanup, "cleanupDigest")
    refuses(lambda: tr.evaluate_tester_readiness(rehearsal=rehearsal, feedback=feedback, cleanup=hostile_cleanup), "readiness refuses production cleanup claim")
    hostile_cleanup = copy.deepcopy(cleanup)
    hostile_cleanup["observations"] = hostile_cleanup["observations"][:-1]
    hostile_cleanup = reseal(hostile_cleanup, "cleanupDigest")
    refuses(lambda: tr.evaluate_tester_readiness(rehearsal=rehearsal, feedback=feedback, cleanup=hostile_cleanup), "readiness refuses resealed incomplete cleanup")
    other_rehearsal = tr.build_synthetic_rehearsal(observed_at=OBSERVED_AT, source_commit="3" * 40, source_tree=TREE, observations=observations)
    other_feedback = tr.build_feedback_placeholder(rehearsal=other_rehearsal)
    refuses(lambda: tr.evaluate_tester_readiness(rehearsal=rehearsal, feedback=other_feedback, cleanup=cleanup), "readiness refuses cross-source feedback binding")

    packet = tr.build_operator_packet(
        packet_id="awtest_" + "a" * 32,
        observed_at=OBSERVED_AT,
        readiness=decision,
    )
    check(packet["schemaVersion"] == tr.OPERATOR_PACKET_SCHEMA, "operator packet schema is pinned")
    check(packet["status"] == "NOT_ACTIONABLE_PROTECTED_GATES_HELD", "operator packet is not actionable")
    check(all(value is False for value in packet["prerequisites"].values()), "every operator prerequisite remains false")
    check("After every prerequisite" in packet["smallestHumanAction"], "operator action is conditional on every prerequisite")
    check("do not provide secrets" in packet["smallestHumanAction"], "operator packet refuses secret transfer")
    check(packet["journeyStepIds"] == [item["stepId"] for item in tr.JOURNEY_STEPS], "operator packet carries exact journey")
    check(packet["feedbackRubricDigest"] == rubric["rubricDigest"], "operator packet binds feedback rubric")
    check(packet["cleanupResourceClasses"] == [item["resourceClass"] for item in tr.CLEANUP_RESOURCES], "operator packet carries exact cleanup set")
    check(packet["prohibitedShortcuts"] == list(tr.PROHIBITED_SHORTCUTS), "operator packet carries shortcut refusals")
    check(packet["operatorActionExecuted"] is False, "operator packet executes no action")
    check(packet == tr.build_operator_packet(packet_id="awtest_" + "a" * 32, observed_at=OBSERVED_AT, readiness=decision), "operator packet is deterministic")
    check(tr.verify_operator_packet(packet, readiness=decision) == packet, "operator packet verifies against readiness")
    assert_authority_false(packet, "operator packet")

    refuses(lambda: tr.build_operator_packet(packet_id="bad", observed_at=OBSERVED_AT, readiness=decision), "operator packet refuses malformed id")
    refuses(lambda: tr.build_operator_packet(packet_id="awtest_" + "b" * 32, observed_at="today", readiness=decision), "operator packet refuses malformed time")
    for prerequisite in packet["prerequisites"]:
        hostile_packet = copy.deepcopy(packet)
        hostile_packet["prerequisites"][prerequisite] = True
        hostile_packet = reseal(hostile_packet, "packetDigest")
        refuses(lambda hostile_packet=hostile_packet: tr.verify_operator_packet(hostile_packet, readiness=decision), f"operator packet refuses inferred prerequisite {prerequisite}")
    hostile_packet = copy.deepcopy(packet)
    hostile_packet["status"] = "READY"
    hostile_packet = reseal(hostile_packet, "packetDigest")
    refuses(lambda: tr.verify_operator_packet(hostile_packet, readiness=decision), "operator packet refuses ready claim")
    hostile_packet = copy.deepcopy(packet)
    hostile_packet["operatorActionExecuted"] = True
    hostile_packet = reseal(hostile_packet, "packetDigest")
    refuses(lambda: tr.verify_operator_packet(hostile_packet, readiness=decision), "operator packet refuses operator-action claim")
    hostile_packet = copy.deepcopy(packet)
    hostile_packet["journeyStepIds"] = hostile_packet["journeyStepIds"][:-1]
    hostile_packet = reseal(hostile_packet, "packetDigest")
    refuses(lambda: tr.verify_operator_packet(hostile_packet, readiness=decision), "operator packet refuses truncated journey")
    hostile_packet = copy.deepcopy(packet)
    hostile_packet["prohibitedShortcuts"] = []
    hostile_packet = reseal(hostile_packet, "packetDigest")
    refuses(lambda: tr.verify_operator_packet(hostile_packet, readiness=decision), "operator packet refuses removed shortcuts")
    hostile_packet = copy.deepcopy(packet)
    hostile_packet["productionAuthority"]["launchAuthorized"] = True
    hostile_packet = reseal(hostile_packet, "packetDigest")
    refuses(lambda: tr.verify_operator_packet(hostile_packet, readiness=decision), "operator packet refuses launch authority escalation")
    other_decision = tr.evaluate_tester_readiness(
        rehearsal=other_rehearsal,
        feedback=other_feedback,
        cleanup=tr.build_cleanup_rehearsal(rehearsal=other_rehearsal, observations=cleanup_rows),
    )
    refuses(lambda: tr.verify_operator_packet(packet, readiness=other_decision), "operator packet refuses cross-source readiness")

    source_path = ROOT / "publishing" / "tester_readiness.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    imports.discard("")
    check(imports <= {"__future__", "hashlib", "json", "re", "datetime", "typing"}, "tester contract imports only pure standard-library modules")
    for forbidden in ("subprocess", "socket", "requests", "urllib", "pathlib", "sqlite", "redis", "open(", "unlink(", "remove(", "rmtree("):
        check(forbidden not in source.lower(), f"tester contract contains no {forbidden} integration")
    check('"humanConsentAttested": True' not in source, "source contains no human-consent attestation")
    check('"humanIdentityAttested": True' not in source, "source contains no human-identity attestation")
    check('"launchAuthorized": True' not in source, "source contains no launch authorization")

    print(f"AgentWars tester ceremony and synthetic rehearsal: PASS ({CHECKS} checks)")
    print("16 journey steps / 8-category feedback rubric / 11 cleanup classes / exact protected operator packet / zero human or launch attestation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
