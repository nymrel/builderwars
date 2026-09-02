#!/usr/bin/env python3
"""Adversarial checks for the local AgentWars support-readiness contract."""

from __future__ import annotations

import ast
import copy
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publishing import league_operations
from publishing import observability
from publishing import support_readiness as support


CHECKS = 0
SOURCE_COMMIT = "a" * 40
OPENED_AT = "2026-09-01T00:00:00Z"


def check(condition: bool, label: str) -> None:
    global CHECKS
    if not condition:
        raise AssertionError(label)
    CHECKS += 1


def reseal(candidate: dict[str, object], digest_field: str) -> dict[str, object]:
    result = copy.deepcopy(candidate)
    result.pop(digest_field, None)
    result[digest_field] = league_operations.digest(result)
    return result


def refuses_contract(candidate: object, label: str) -> None:
    try:
        support.verify_support_readiness_contract(candidate)
    except support.SupportReadinessError:
        check(True, label)
    else:
        raise AssertionError(label)


def refuses_case(candidate: object, label: str) -> None:
    try:
        support.verify_case_candidate(candidate)
    except support.SupportReadinessError:
        check(True, label)
    else:
        raise AssertionError(label)


def main() -> int:
    contract = support.support_readiness_contract()
    league_contract = league_operations.finite_league_contract()
    obs_contract = observability.observability_contract()

    check(contract == support.support_readiness_contract(), "support contract is deterministic")
    check(support.verify_support_readiness_contract(contract) == contract, "support contract verifies")
    check(contract["schemaVersion"] == support.CONTRACT_SCHEMA, "support schema is pinned")
    check(contract["status"] == support.STATUS, "support remains local and unstaffed")
    check(contract["sourceBindings"]["leagueContractDigest"] == league_contract["contractDigest"], "support binds exact league contract")
    check(contract["sourceBindings"]["supportPolicyDigest"] == league_operations.digest(league_contract["supportPolicy"]), "support binds exact league support policy")
    check(contract["sourceBindings"]["observabilityContractDigest"] == obs_contract["contractDigest"], "support binds exact observability contract")
    check(len(contract["routes"]) == 11, "all eleven issue classes have exact routes")
    check(len({route["issueClass"] for route in contract["routes"]}) == 11, "support issue classes are unique")
    check({route["severity"] for route in contract["routes"]} == {"sev1", "sev2", "sev3"}, "support preserves all three severities")
    check(all(route["responseTimePromise"] is None for route in contract["routes"]), "unstaffed support promises no response time")
    check(contract["intakePolicy"]["allowedFields"] == ["schemaVersion", "caseId", "openedAt", "sourceCommit", "issueClass", "resourceRefs"], "intake fields are exact and bounded")
    check(contract["intakePolicy"]["maxResourceRefs"] == 8, "intake reference count is bounded")
    check(contract["intakePolicy"]["freeTextAccepted"] is False and contract["intakePolicy"]["attachmentsAccepted"] is False, "intake accepts no free text or attachment")
    check(contract["intakePolicy"]["transportConfigured"] is False, "support transport remains unconfigured")
    check(contract["intakePolicy"]["identityAttestationAccepted"] is False, "intake cannot attest identity")
    check(set(contract["prohibitedFields"]) == set(support.PROHIBITED_FIELDS), "secret, PII, prompt, output, and token fields are prohibited")
    check(contract["activationBlockers"] == list(support.ACTIVATION_BLOCKERS), "activation blockers are exact")
    check(contract["incidentBridge"]["sev1EventName"] == "support_case_opened", "sev1 bridge names the reviewed event")
    check(contract["incidentBridge"]["sev1IncidentCode"] == "SUPPORT_SEV1", "sev1 bridge names the reviewed incident")
    check(contract["incidentBridge"]["bridgeStatus"] == "schema_only_not_instrumented", "incident bridge remains uninstrumented")
    check(contract["incidentBridge"]["eventEmitted"] is False and contract["incidentBridge"]["incidentCreated"] is False, "support emits no event or incident")
    check(contract["authority"] == support.AUTHORITY and all(value is False for value in contract["authority"].values()), "all support authority flags are false")
    check(contract["contractDigest"] == league_operations.digest({key: value for key, value in contract.items() if key != "contractDigest"}), "support contract digest verifies")

    case_args = {
        "case_id": "awsupp_" + "b" * 32,
        "opened_at": OPENED_AT,
        "source_commit": SOURCE_COMMIT,
        "issue_class": "receipt_integrity",
        "resource_refs": ["awref_" + "d" * 32, "awref_" + "c" * 32],
    }
    case = support.build_case_candidate(**case_args)
    check(case == support.build_case_candidate(**case_args), "support case is deterministic")
    check(support.verify_case_candidate(case) == case, "support case verifies")
    check(case["schemaVersion"] == support.CASE_SCHEMA and case["status"] == support.CASE_STATUS, "case is local and unsubmitted")
    check(case["sourceCommit"] == SOURCE_COMMIT, "case binds exact source commit")
    check(case["resourceRefs"] == sorted(case_args["resource_refs"]), "opaque references canonicalize to sorted order")
    check(case["route"]["severity"] == "sev1", "receipt-integrity case derives sev1")
    check(case["route"]["releasePosture"] == "hold_release_and_new_admissions", "sev1 derives the exact release hold")
    check(case["route"]["responseTimePromise"] is None and case["responseTimePromise"] is None, "case makes no response-time promise")
    check(case["submissionTransport"] == "not_configured" and case["humanReview"] == "not_performed", "case is neither submitted nor reviewed")
    check(case["actionsExecuted"] is False and all(value is False for value in case["authority"].values()), "case executes nothing and grants no authority")
    check(case["supportContractDigest"] == contract["contractDigest"], "case binds exact support contract")
    check(case["caseDigest"] == league_operations.digest({key: value for key, value in case.items() if key != "caseDigest"}), "case digest verifies")

    sev3 = support.build_case_candidate(**{**case_args, "issue_class": "orientation_confusion", "resource_refs": []})
    check(sev3["route"]["severity"] == "sev3", "orientation confusion derives sev3")
    check(sev3["route"]["releasePosture"] == "continue_local_validation_only", "sev3 permits local validation only")

    hostile = copy.deepcopy(contract)
    hostile["status"] = "live_staffed"
    refuses_contract(reseal(hostile, "contractDigest"), "resealed staffed status is refused")
    hostile = copy.deepcopy(contract)
    hostile["intakePolicy"]["freeTextAccepted"] = True
    refuses_contract(reseal(hostile, "contractDigest"), "resealed free-text intake is refused")
    hostile = copy.deepcopy(contract)
    hostile["routes"][0]["responseTimePromise"] = "one_hour"
    refuses_contract(reseal(hostile, "contractDigest"), "resealed response-time promise is refused")
    hostile = copy.deepcopy(contract)
    hostile["incidentBridge"]["eventEmitted"] = True
    refuses_contract(reseal(hostile, "contractDigest"), "resealed incident emission is refused")
    hostile = copy.deepcopy(contract)
    hostile["authority"]["supportQueueStaffed"] = True
    refuses_contract(reseal(hostile, "contractDigest"), "resealed staffing authority is refused")
    hostile = copy.deepcopy(contract)
    hostile["unexpected"] = False
    refuses_contract(reseal(hostile, "contractDigest"), "unknown support-contract field is refused")
    refuses_contract([], "non-object support contract is refused")

    hostile_case = copy.deepcopy(case)
    hostile_case["status"] = "submitted"
    refuses_case(reseal(hostile_case, "caseDigest"), "resealed submitted case is refused")
    hostile_case = copy.deepcopy(case)
    hostile_case["route"]["severity"] = "sev3"
    refuses_case(reseal(hostile_case, "caseDigest"), "resealed severity downgrade is refused")
    hostile_case = copy.deepcopy(case)
    hostile_case["humanReview"] = "approved"
    refuses_case(reseal(hostile_case, "caseDigest"), "resealed human review is refused")
    hostile_case = copy.deepcopy(case)
    hostile_case["authority"]["moderationActionExecuted"] = True
    refuses_case(reseal(hostile_case, "caseDigest"), "resealed moderation authority is refused")
    hostile_case = copy.deepcopy(case)
    hostile_case["freeText"] = "raw customer content"
    refuses_case(reseal(hostile_case, "caseDigest"), "unknown free-text case field is refused")
    refuses_case([], "non-object support case is refused")

    bad_calls = (
        ({**case_args, "case_id": "bad"}, "malformed case id is refused"),
        ({**case_args, "opened_at": "soon"}, "malformed timestamp is refused"),
        ({**case_args, "source_commit": "short"}, "malformed source commit is refused"),
        ({**case_args, "issue_class": "make_everything_public"}, "unknown issue class is refused"),
        ({**case_args, "resource_refs": ["bad"]}, "malformed resource reference is refused"),
        ({**case_args, "resource_refs": ["awref_" + "c" * 32] * 2}, "duplicate resource references are refused"),
        ({**case_args, "resource_refs": [f"awref_{index:032x}" for index in range(9)]}, "more than eight resource references are refused"),
    )
    for args, label in bad_calls:
        try:
            support.build_case_candidate(**args)
        except support.SupportReadinessError:
            check(True, label)
        else:
            raise AssertionError(label)

    cli = subprocess.run(
        [sys.executable, "-B", str(ROOT / "bin" / "agentwars_support.py")],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    check(json.loads(cli.stdout) == contract, "support CLI emits the exact verified contract")
    check(cli.stderr == "", "support CLI emits no warning or hidden action")

    source = (ROOT / "publishing" / "support_readiness.py").read_text(encoding="utf-8")
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
    check(not (imported & {"os", "pathlib", "socket", "subprocess", "urllib", "requests"}), "support contract imports no environment, filesystem, network, or process authority")
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    check(not (called_names & {"eval", "exec", "compile", "open"}), "support contract performs no dynamic execution or file open")

    print(f"AgentWars support readiness: PASS ({CHECKS} checks)")
    print("opaque intake / exact severity routing / no PII or free text / unstaffed / no transport / zero authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
