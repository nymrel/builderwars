#!/usr/bin/env python3
"""Adversarial checks for the AgentWars commissioner starter packet."""

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

from publishing import league_operations as league_ops
from publishing import commissioner


CHECKS = 0


def check(condition: bool, label: str) -> None:
    global CHECKS
    if not condition:
        raise AssertionError(label)
    CHECKS += 1


def refuses(candidate: object, label: str) -> None:
    try:
        commissioner.verify_commissioner_starter(candidate)
    except commissioner.CommissionerStarterError:
        check(True, label)
    else:
        raise AssertionError(label)


def reseal(candidate: dict[str, object]) -> dict[str, object]:
    result = copy.deepcopy(candidate)
    result.pop("packetDigest", None)
    result["packetDigest"] = league_ops.digest(result)
    return result


def main() -> int:
    packet = commissioner.commissioner_starter()
    contract = league_ops.finite_league_contract()
    formats = {item["formatId"]: item for item in contract["formats"]}

    check(packet == commissioner.commissioner_starter(), "commissioner starter is deterministic")
    check(commissioner.verify_commissioner_starter(packet) == packet, "commissioner starter verifies")
    check(packet["schemaVersion"] == commissioner.SCHEMA_VERSION, "schema is pinned")
    check(packet["status"] == commissioner.STATUS, "status stays local and unscheduled")
    check(packet["leagueContractDigest"] == contract["contractDigest"], "packet binds exact league contract")
    active = packet["activeSeasonCandidate"]
    check(active["formatId"] == "redraft" and active["gameName"] == "fantasy_redraft", "redraft is the only active season candidate")
    check(active["rulesDigest"] == formats["redraft"]["rulesDigest"], "active season binds exact redraft rules")
    check(active["fixturePlan"] == contract["fixturePlan"], "active season binds exact finite fixture plan")
    check(active["fixturePlan"]["activationStatus"] == "not_activated", "fixtures remain inactive")
    check(active["fixturePlan"]["expectedFixtureCount"] == 8, "redraft season remains finite at eight candidate fixtures")
    check(len(packet["inactiveCohorts"]) == 1, "exactly one inactive cohort is declared")
    dynasty = packet["inactiveCohorts"][0]
    check(dynasty["formatId"] == "dynasty" and dynasty["gameName"] == "fantasy_dynasty", "dynasty is explicit and separate")
    check(dynasty["seasonStatus"] == "separate_future_cohort_not_scheduled", "dynasty remains unscheduled")
    check(dynasty["standingsScope"] != active["standingsScope"], "dynasty and redraft standings never merge")
    check(dynasty["rulesDigest"] != active["rulesDigest"], "dynasty and redraft rules never merge")
    check(dynasty["rosterCarryoverAuthorized"] is False and dynasty["ratingCarryoverAuthorized"] is False, "dynasty carries no roster or rating authority")

    bindings = packet["operationsBindings"]
    check(bindings["supportPolicyDigest"] == league_ops.digest(contract["supportPolicy"]), "support policy is digest-bound")
    check(bindings["moderationPolicyDigest"] == league_ops.digest(contract["moderationPolicy"]), "moderation policy is digest-bound")
    check(bindings["correctionPolicyDigest"] == league_ops.digest(contract["correctionPolicy"]), "correction policy is digest-bound")
    check(bindings["rollbackPolicyDigest"] == league_ops.digest(contract["rollbackPolicy"]), "rollback policy is digest-bound")
    check(bindings["standingsPolicyDigest"] == league_ops.digest(contract["standingsPolicy"]), "standings policy is digest-bound")
    check(packet["creatorBoundary"] == contract["creatorAdmissionBoundary"], "held creator boundary is exact")
    check(packet["creatorBoundary"]["includedInLeague"] is False, "creator game is not in the league")
    check(packet["localActionsAvailable"] == list(commissioner.LOCAL_ACTIONS), "only bounded local actions are offered")
    check(packet["forbiddenActions"] == list(commissioner.FORBIDDEN_ACTIONS), "all unsafe commissioner actions are explicit")
    check([stage["stageId"] for stage in packet["protectedLaunchStages"]] == [11, 12, 13], "protected stages preserve exact order")
    check(all(stage["status"] == "HELD_PROTECTED" for stage in packet["protectedLaunchStages"]), "all protected stages remain held")
    check(all(stage["requiredReceipt"] and stage["operatorAction"] for stage in packet["protectedLaunchStages"]), "protected stages name receipt and smallest operator action")
    check(len(packet["operatorBlockers"]) == 4, "operator blockers are finite and explicit")
    check(all(value is False for value in packet["authority"].values()), "every commissioner authority flag is false")
    check(packet["authority"] == commissioner.AUTHORITY, "authority object is exact")
    check(packet["packetDigest"] == league_ops.digest({key: value for key, value in packet.items() if key != "packetDigest"}), "packet digest verifies")
    check(set(packet["documentation"]) == {"starterKit", "leagueOperations", "creatorSdk", "testerCeremony"}, "packet points to the four exact operator documents")
    check(len(packet["evidenceLimits"]) == 6 and "no_launch_authority" in packet["evidenceLimits"], "evidence limits forbid launch overclaim")

    hostile = copy.deepcopy(packet)
    hostile["status"] = "live"
    refuses(reseal(hostile), "resealed live status is refused")
    hostile = copy.deepcopy(packet)
    hostile["activeSeasonCandidate"]["formatId"] = "dynasty"
    refuses(reseal(hostile), "resealed dynasty activation is refused")
    hostile = copy.deepcopy(packet)
    hostile["activeSeasonCandidate"]["rulesDigest"] = "0" * 64
    refuses(reseal(hostile), "resealed rules drift is refused")
    hostile = copy.deepcopy(packet)
    hostile["activeSeasonCandidate"]["fixturePlan"]["activationStatus"] = "active"
    refuses(reseal(hostile), "resealed fixture activation is refused")
    hostile = copy.deepcopy(packet)
    hostile["inactiveCohorts"][0]["seasonStatus"] = "active"
    refuses(reseal(hostile), "resealed dynasty scheduling is refused")
    hostile = copy.deepcopy(packet)
    hostile["operationsBindings"]["supportPolicyDigest"] = "1" * 64
    refuses(reseal(hostile), "resealed support-policy drift is refused")
    hostile = copy.deepcopy(packet)
    hostile["creatorBoundary"]["includedInLeague"] = True
    refuses(reseal(hostile), "resealed creator admission is refused")
    hostile = copy.deepcopy(packet)
    hostile["protectedLaunchStages"][0]["status"] = "PASS"
    refuses(reseal(hostile), "resealed protected-stage pass is refused")
    hostile = copy.deepcopy(packet)
    hostile["protectedLaunchStages"].pop()
    refuses(reseal(hostile), "truncated protected-stage list is refused")
    hostile = copy.deepcopy(packet)
    hostile["authority"]["launchApproved"] = True
    refuses(reseal(hostile), "resealed launch authority is refused")
    hostile = copy.deepcopy(packet)
    hostile["forbiddenActions"].remove("publish_rankings_or_claim_launch")
    refuses(reseal(hostile), "weakened forbidden-action list is refused")
    hostile = copy.deepcopy(packet)
    hostile["unexpected"] = False
    refuses(reseal(hostile), "unknown packet field is refused")
    refuses([], "non-object packet is refused")

    compact = subprocess.run(
        [sys.executable, "-B", str(ROOT / "bin" / "agentwars_commissioner.py"), "--compact"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    cli_packet = json.loads(compact.stdout)
    check(cli_packet == packet, "commissioner CLI emits the exact verified packet")
    check(compact.stderr == "", "commissioner CLI emits no warning or hidden action")

    source = (ROOT / "publishing" / "commissioner.py").read_text(encoding="utf-8")
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
    check(not (imported & {"os", "pathlib", "socket", "subprocess", "urllib", "requests"}), "commissioner contract imports no environment, filesystem, network, or process authority")
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    check(not (called_names & {"eval", "exec", "compile", "open"}), "commissioner contract performs no dynamic execution or file open")

    print(f"AgentWars commissioner starter: PASS ({CHECKS} checks)")
    print("redraft finite / dynasty separate / operations digest-bound / stages 11-13 held / zero authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
