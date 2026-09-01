#!/usr/bin/env python3
"""Adversarial checks for the finite AgentWars fantasy league contract."""

from __future__ import annotations

import ast
import copy
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publishing import league_operations as lo


CHECKS = 0
OBSERVED_AT = "2026-09-01T00:00:00Z"


def check(condition: bool, label: str) -> None:
    global CHECKS
    if not condition:
        raise AssertionError(label)
    CHECKS += 1


def refuses(callable_, label: str) -> None:
    try:
        callable_()
    except lo.LeagueOperationsError:
        check(True, label)
    else:
        raise AssertionError(label)


def reseal(value: dict[str, object], field: str) -> dict[str, object]:
    result = copy.deepcopy(value)
    result.pop(field, None)
    result[field] = lo.digest(result)
    return result


def assert_authority_false(value: object, label: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "productionAuthority":
                check(item == lo.PRODUCTION_AUTHORITY, f"{label}: exact false production authority")
                check(all(type(flag) is bool and flag is False for flag in item.values()), f"{label}: authority flags false")
            if key in {
                "externalEntrantsAdmitted", "universalModelRankingAuthorized", "silentRewriteAuthorized",
                "rollbackExecuted", "includedInLeague", "arbitraryCreatorCodeAccepted", "actionsExecuted",
                "operatorDecisionRecorded", "standingsMutationExecuted", "publicationMutationExecuted",
            }:
                check(item is False, f"{label}: {key} remains false")
            assert_authority_false(item, label)
    elif isinstance(value, list):
        for item in value:
            assert_authority_false(item, label)


def main() -> int:
    contract = lo.finite_league_contract()
    check(contract == lo.finite_league_contract(), "finite league contract is deterministic")
    check(lo.verify_finite_league_contract(contract) == contract, "finite league contract verifies")
    check(contract["schemaVersion"] == lo.CONTRACT_SCHEMA, "contract schema is pinned")
    check(contract["contractStatus"] == "local_contract_only_not_scheduled", "season remains unscheduled")
    check(contract["activeFormatId"] == "redraft", "redraft is the only active contract format")
    formats = {item["formatId"]: item for item in contract["formats"]}
    check(set(formats) == {"redraft", "dynasty"}, "redraft and dynasty are explicit")
    check(formats["redraft"]["gameName"] == "fantasy_redraft", "redraft binds its exact game")
    check(formats["dynasty"]["gameName"] == "fantasy_dynasty", "dynasty binds its exact game")
    check(formats["redraft"]["scoringHorizon"] == "one_season_score", "redraft horizon is one season")
    check(formats["dynasty"]["scoringHorizon"] == "three_year_value", "dynasty horizon is three years")
    check(formats["redraft"]["standingsScope"] != formats["dynasty"]["standingsScope"], "format standings never merge")
    check(formats["redraft"]["rulesDigest"] != formats["dynasty"]["rulesDigest"], "format rules remain distinct")
    check(formats["dynasty"]["seasonStatus"] == "separate_future_cohort_not_scheduled", "dynasty cohort remains separate and inactive")
    fixture = contract["fixturePlan"]
    check(fixture["seedSet"] == [9100, 9101, 9102, 9103], "season pins four exact seeds")
    check(fixture["seatPolicy"] == "every_seed_both_seat_orders", "every seed mirrors seats")
    check(fixture["expectedFixtureCount"] == len(fixture["seedSet"]) * 2, "fixture count matches mirrored plan")
    check(fixture["activationStatus"] == "not_activated", "fixtures remain inactive")
    check(contract["standingsPolicy"]["ratingScope"] == "league_plus_season_plus_game_plus_rules_plus_resource_class", "ratings are narrowly scoped")
    check(contract["standingsPolicy"]["scriptedPreseasonExcludedFromPublicRank"] is True, "scripted preseason cannot rank publicly")
    check(len(contract["supportPolicy"]) == 3, "support has three bounded severity classes")
    check(all(item["responseTimePromise"] is None for item in contract["supportPolicy"]), "unstaffed support promises no response time")
    check(len(contract["moderationPolicy"]) == 4, "moderation has four bounded case classes")
    check(contract["correctionPolicy"]["originalReceiptPolicy"] == "immutable", "original receipts remain immutable")
    check(contract["correctionPolicy"]["journalPolicy"] == "append_only_digest_bound", "corrections are append-only")
    check(contract["creatorAdmissionBoundary"]["registryDecision"] == "held_exhibition_candidate", "creator game remains held")
    check(contract["creatorAdmissionBoundary"]["admissionStatus"] == "held_not_runtime_admission", "creator registry is not runtime admission")
    check(set(contract["prohibitedClaims"]) == set(lo.PROHIBITED_CLAIMS), "all prohibited claims are explicit")
    assert_authority_false(contract, "contract")

    registry = json.loads((ROOT / "creator_games" / "registry.v1.json").read_text(encoding="utf-8"))
    check(registry["status"] == "candidate_registry_not_runtime_admission", "source creator registry remains non-admitting")
    check(len(registry["entries"]) == 1, "source creator registry has one reviewed candidate")
    entry = registry["entries"][0]
    boundary = contract["creatorAdmissionBoundary"]
    check(entry["gameId"] == boundary["candidateGameId"], "contract binds exact creator game")
    check(entry["version"] == boundary["candidateVersion"], "contract binds creator version")
    check(entry["manifestSha256"] == boundary["candidateManifestDigest"], "contract binds creator manifest digest")
    check(entry["decision"] == boundary["registryDecision"], "contract binds held creator decision")
    check(all(entry[field] is False for field in ("authorEntrantRankingAuthorized", "executionAuthorized", "publicationAuthorized")), "creator authority stays false")

    hostile = copy.deepcopy(contract)
    hostile["contractStatus"] = "live"
    hostile = reseal(hostile, "contractDigest")
    refuses(lambda: lo.verify_finite_league_contract(hostile), "resealed live season claim is refused")
    hostile = copy.deepcopy(contract)
    hostile["productionAuthority"]["seasonScheduled"] = True
    hostile = reseal(hostile, "contractDigest")
    refuses(lambda: lo.verify_finite_league_contract(hostile), "resealed scheduling authority is refused")
    hostile = copy.deepcopy(contract)
    hostile["formats"][1]["standingsScope"] = hostile["formats"][0]["standingsScope"]
    hostile = reseal(hostile, "contractDigest")
    refuses(lambda: lo.verify_finite_league_contract(hostile), "resealed format-scope collapse is refused")
    hostile = copy.deepcopy(contract)
    hostile["fixturePlan"]["expectedFixtureCount"] = 7
    hostile = reseal(hostile, "contractDigest")
    refuses(lambda: lo.verify_finite_league_contract(hostile), "resealed fixture-count drift is refused")
    hostile = copy.deepcopy(contract)
    hostile["creatorAdmissionBoundary"]["includedInLeague"] = True
    hostile = reseal(hostile, "contractDigest")
    refuses(lambda: lo.verify_finite_league_contract(hostile), "resealed creator admission is refused")
    hostile = copy.deepcopy(contract)
    hostile["unexpected"] = False
    hostile = reseal(hostile, "contractDigest")
    refuses(lambda: lo.verify_finite_league_contract(hostile), "unknown contract field is refused")

    for case_id in lo.CASE_IDS:
        decision = lo.evaluate_operations_case(case_id=case_id, observed_at=OBSERVED_AT)
        check(decision == lo.evaluate_operations_case(case_id=case_id, observed_at=OBSERVED_AT), f"{case_id}: decision deterministic")
        check(lo.verify_operations_decision(decision) == decision, f"{case_id}: decision verifies")
        check(decision["leagueContractDigest"] == contract["contractDigest"], f"{case_id}: decision binds league contract")
        check(decision["actionsExecuted"] is False and decision["operatorDecisionRecorded"] is False, f"{case_id}: decision executes nothing")
        check(lo.digest({key: value for key, value in decision.items() if key != "decisionDigest"}) == decision["decisionDigest"], f"{case_id}: decision digest verifies")
        assert_authority_false(decision, f"decision {case_id}")
    hostile_decision = lo.evaluate_operations_case(case_id="ordinary_support_confusion", observed_at=OBSERVED_AT)
    hostile_decision["releaseDecision"] = "PUBLIC_LAUNCH"
    hostile_decision = reseal(hostile_decision, "decisionDigest")
    refuses(lambda: lo.verify_operations_decision(hostile_decision), "resealed release escalation is refused")
    hostile_decision = lo.evaluate_operations_case(case_id="ordinary_support_confusion", observed_at=OBSERVED_AT)
    hostile_decision["productionAuthority"]["moderationActionExecuted"] = True
    hostile_decision = reseal(hostile_decision, "decisionDigest")
    refuses(lambda: lo.verify_operations_decision(hostile_decision), "resealed moderation authority is refused")
    hostile_decision = lo.evaluate_operations_case(case_id="ordinary_support_confusion", observed_at=OBSERVED_AT)
    hostile_decision["unexpected"] = False
    hostile_decision = reseal(hostile_decision, "decisionDigest")
    refuses(lambda: lo.verify_operations_decision(hostile_decision), "unknown decision field is refused")
    refuses(lambda: lo.evaluate_operations_case(case_id="approve_everything", observed_at=OBSERVED_AT), "unknown operations case is refused")
    refuses(lambda: lo.evaluate_operations_case(case_id="ordinary_support_confusion", observed_at="soon"), "malformed case timestamp is refused")

    correction_args = {
        "correction_id": "awlcorr_" + "a" * 32,
        "proposed_at": OBSERVED_AT,
        "fixture_id": "awfix_" + "b" * 32,
        "original_receipt_digest": "c" * 64,
        "correction_class": "replace_receipt_after_verified_replay",
        "replacement_receipt_digest": "d" * 64,
    }
    correction = lo.build_correction_candidate(**correction_args)
    check(correction == lo.build_correction_candidate(**correction_args), "correction candidate is deterministic")
    check(lo.verify_correction_candidate(correction) == correction, "correction candidate verifies")
    check(correction["leagueContractDigest"] == contract["contractDigest"], "correction binds exact league contract")
    check(correction["status"] == "proposed_uncommitted", "correction remains uncommitted")
    check(correction["originalReceiptImmutable"] is True, "correction preserves original receipt")
    assert_authority_false(correction, "correction")

    refuses(lambda: lo.build_correction_candidate(**{**correction_args, "correction_id": "bad"}), "malformed correction id is refused")
    refuses(lambda: lo.build_correction_candidate(**{**correction_args, "fixture_id": "bad"}), "malformed fixture id is refused")
    refuses(lambda: lo.build_correction_candidate(**{**correction_args, "original_receipt_digest": "short"}), "malformed original digest is refused")
    refuses(lambda: lo.build_correction_candidate(**{**correction_args, "replacement_receipt_digest": "c" * 64}), "same replacement receipt is refused")
    refuses(lambda: lo.build_correction_candidate(**{**correction_args, "replacement_receipt_digest": None}), "missing replacement receipt is refused")
    refuses(lambda: lo.build_correction_candidate(**{**correction_args, "correction_class": "erase_history", "replacement_receipt_digest": None}), "unknown correction class is refused")
    refuses(lambda: lo.build_correction_candidate(**{**correction_args, "correction_class": "void_fixture"}), "replacement receipt on void is refused")
    hostile = copy.deepcopy(correction)
    hostile["status"] = "committed"
    hostile = reseal(hostile, "candidateDigest")
    refuses(lambda: lo.verify_correction_candidate(hostile), "resealed committed correction is refused")
    hostile = copy.deepcopy(correction)
    hostile["productionAuthority"]["correctionCommitted"] = True
    hostile = reseal(hostile, "candidateDigest")
    refuses(lambda: lo.verify_correction_candidate(hostile), "resealed correction authority is refused")
    hostile = copy.deepcopy(correction)
    hostile["leagueContractDigest"] = "e" * 64
    hostile = reseal(hostile, "candidateDigest")
    refuses(lambda: lo.verify_correction_candidate(hostile), "cross-contract correction is refused")

    source_path = ROOT / "publishing" / "league_operations.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    check(not (imported & {"os", "pathlib", "socket", "subprocess", "urllib", "requests"}), "contract imports no network, process, environment, or filesystem authority")
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    check(not (called_names & {"eval", "exec", "compile", "open"}), "contract has no dynamic execution or file-open call")

    print(f"AgentWars finite league operations: PASS ({CHECKS} checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
