#!/usr/bin/env python3
"""Adversarial, repository-grounded checks for the BuilderWars threat model."""

from __future__ import annotations

import ast
import copy
import hashlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publishing import threat_model as tm


CHECKS = 0
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
    except tm.ThreatModelError:
        check(True, label)
    else:
        raise AssertionError(label)


def reseal(value: dict[str, object], field: str) -> dict[str, object]:
    row = copy.deepcopy(value)
    row.pop(field, None)
    row[field] = tm.digest(row)
    return row


def evidence_observations() -> list[dict[str, object]]:
    observations: list[dict[str, object]] = []
    for anchor in tm.EVIDENCE_ANCHORS:
        path = ROOT / str(anchor["path"])
        raw = path.read_bytes()
        text = raw.decode("utf-8")
        observations.append({
            "anchorId": anchor["anchorId"],
            "path": anchor["path"],
            "symbol": anchor["symbol"],
            "fileSha256": hashlib.sha256(raw).hexdigest(),
            "anchorFound": str(anchor["symbol"]) in text,
            "productionObserved": False,
        })
    return observations


def assert_false_authority(value: object, label: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "productionAuthority":
                check(item == tm.PRODUCTION_AUTHORITY, f"{label}: production authority is exact")
                check(all(type(flag) is bool and flag is False for flag in item.values()), f"{label}: production authority is false")
            if key in {"productionSecurityApproved", "productionObserved"}:
                check(item is False, f"{label}: {key} remains false")
            assert_false_authority(item, label)
    elif isinstance(value, list):
        for item in value:
            assert_false_authority(item, label)


def main() -> int:
    model = tm.threat_model_contract()
    check(model["schemaVersion"] == tm.THREAT_MODEL_SCHEMA, "threat model schema is pinned")
    check(model["modelStatus"] == "REPOSITORY_GROUNDED_LOCAL_MODEL_PROTECTED_GAPS_HELD", "model status keeps protected gaps held")
    check(tm.verify_threat_model(model) == model, "canonical threat model verifies")
    unsigned_model = dict(model)
    supplied_digest = unsigned_model.pop("contractDigest")
    check(tm.digest(unsigned_model) == supplied_digest, "threat model digest verifies")
    check(len(model["components"]) == 10, "ten primary components are modeled")
    check(len(model["boundaries"]) == 8, "eight trust boundaries are modeled")
    check(len(model["assets"]) == 9, "nine security-driving assets are modeled")
    check(len(model["entryPoints"]) == 8, "eight concrete entry points are modeled")
    check(len(model["evidenceAnchors"]) == 16, "sixteen source anchors ground the model")
    check(len(model["threats"]) == 10, "ten concrete threats are prioritized")
    check(len(model["focusPaths"]) == 12, "twelve manual-review focus paths are named")
    check(len(model["assumptions"]) == 5 and len(model["openQuestions"]) == 3, "assumptions and open questions are bounded")
    check(model["context"] == tm.CONTEXT, "service context is exact")
    check("beta_scale_unknown" in model["context"]["riskQualifier"], "unknown scale remains an explicit qualifier")
    check("unimplemented_production_infrastructure" in model["context"]["outOfScope"], "unimplemented infrastructure is not invented")
    check(len(model["residualProtectedGates"]) == 9, "nine residual production security gates remain")
    check(model["residualProtectedGates"] == list(tm.RESIDUAL_PROTECTED_GATES), "residual gates are exact")
    assert_false_authority(model, "threat model")

    component_ids = [row["componentId"] for row in model["components"]]
    boundary_ids = [row["boundaryId"] for row in model["boundaries"]]
    asset_ids = [row["assetId"] for row in model["assets"]]
    entry_ids = [row["entryPointId"] for row in model["entryPoints"]]
    anchor_ids = [row["anchorId"] for row in model["evidenceAnchors"]]
    threat_ids = [row["threatId"] for row in model["threats"]]
    check(component_ids == [f"C-{index:03d}" for index in range(1, 11)], "component ids are stable and contiguous")
    check(boundary_ids == [f"B-{index:03d}" for index in range(1, 9)], "boundary ids are stable and contiguous")
    check(asset_ids == [f"A-{index:03d}" for index in range(1, 10)], "asset ids are stable and contiguous")
    check(entry_ids == [f"EP-{index:03d}" for index in range(1, 9)], "entry-point ids are stable and contiguous")
    check(anchor_ids == [f"EA-{index:03d}" for index in range(1, 17)], "anchor ids are stable and contiguous")
    check(threat_ids == [f"TM-{index:03d}" for index in range(1, 11)], "threat ids are stable and contiguous")
    for ids, label in ((component_ids, "component"), (boundary_ids, "boundary"), (asset_ids, "asset"), (entry_ids, "entry"), (anchor_ids, "anchor"), (threat_ids, "threat")):
        check(len(ids) == len(set(ids)), f"{label} ids are unique")

    known_boundaries = set(boundary_ids)
    known_assets = set(asset_ids)
    known_entries = set(entry_ids)
    known_anchors = set(anchor_ids)
    covered_boundaries: set[str] = set()
    covered_assets: set[str] = set()
    covered_entries: set[str] = set()
    used_anchors: set[str] = set()
    high_critical: list[str] = []
    for threat in model["threats"]:
        check(set(threat) == {
            "threatId", "title", "threatSource", "prerequisites", "threatAction", "impact",
            "assetIds", "boundaryIds", "entryPointIds", "existingControlAnchorIds", "gaps",
            "recommendedMitigations", "detectionIdeas", "likelihood", "impactSeverity",
            "priority", "protectedHoldRequired",
        }, f"{threat['threatId']} has the exact threat fields")
        check(threat["priority"] in {"critical", "high", "medium", "low"}, f"{threat['threatId']} priority is closed")
        check(threat["likelihood"]["rating"] in {"low", "medium", "high"}, f"{threat['threatId']} likelihood is closed")
        check(threat["impactSeverity"]["rating"] in {"low", "medium", "high"}, f"{threat['threatId']} impact is closed")
        check(set(threat["assetIds"]) <= known_assets and bool(threat["assetIds"]), f"{threat['threatId']} references known assets")
        check(set(threat["boundaryIds"]) <= known_boundaries and bool(threat["boundaryIds"]), f"{threat['threatId']} references known boundaries")
        check(set(threat["entryPointIds"]) <= known_entries and bool(threat["entryPointIds"]), f"{threat['threatId']} references known entry points")
        check(set(threat["existingControlAnchorIds"]) <= known_anchors and bool(threat["existingControlAnchorIds"]), f"{threat['threatId']} references known controls")
        check(bool(threat["gaps"]) and bool(threat["recommendedMitigations"]) and bool(threat["detectionIdeas"]), f"{threat['threatId']} has gaps mitigations and detection")
        check(bool(threat["likelihood"]["reason"]) and bool(threat["impactSeverity"]["reason"]), f"{threat['threatId']} ratings are reasoned")
        if threat["priority"] in {"critical", "high"}:
            high_critical.append(threat["threatId"])
            check(threat["protectedHoldRequired"] is True, f"{threat['threatId']} remains a protected hold")
        else:
            check(threat["protectedHoldRequired"] is False, f"{threat['threatId']} does not overstate the hold class")
        covered_boundaries.update(threat["boundaryIds"])
        covered_assets.update(threat["assetIds"])
        covered_entries.update(threat["entryPointIds"])
        used_anchors.update(threat["existingControlAnchorIds"])
    check(covered_boundaries == known_boundaries, "every trust boundary appears in a threat")
    check(covered_assets == known_assets, "every asset appears in a threat")
    check(covered_entries == known_entries, "every entry point appears in a threat")
    check(high_critical == ["TM-001", "TM-002", "TM-005", "TM-006", "TM-007", "TM-008", "TM-010"], "high and critical threat set is exact")
    check(model["threats"][0]["priority"] == "critical", "missing browser auth is launch-critical")
    check(model["threats"][4]["priority"] == "high", "unenforced OS isolation remains high priority")
    check(model["threats"][4]["likelihood"]["rating"] == "low", "disabled public arbitrary execution reduces current reachability")
    check("customer-local" in model["threats"][5]["likelihood"]["reason"], "provider risk remains customer-endpoint aware")

    referenced_anchors = set()
    for collection in (model["components"], model["boundaries"], model["entryPoints"]):
        for row in collection:
            referenced_anchors.update(row["evidenceAnchorIds"])
    referenced_anchors.update(used_anchors)
    check(referenced_anchors == known_anchors, "every evidence anchor supports an architectural or threat claim")
    for anchor in model["evidenceAnchors"]:
        check(not Path(anchor["path"]).is_absolute() and ".." not in Path(anchor["path"]).parts, f"{anchor['anchorId']} path is repo relative")
        check((ROOT / anchor["path"]).is_file(), f"{anchor['anchorId']} path exists")
    for focus in model["focusPaths"]:
        check(not Path(focus["path"]).is_absolute() and ".." not in Path(focus["path"]).parts, f"focus path {focus['path']} is repo relative")
        check((ROOT / focus["path"]).exists(), f"focus path {focus['path']} exists")
        check(set(focus["threatIds"]) <= set(threat_ids) and bool(focus["threatIds"]), f"focus path {focus['path']} references threats")

    observations = evidence_observations()
    check(len(observations) == 16, "all source observations are constructed")
    check(all(row["anchorFound"] is True for row in observations), "every source anchor is present")
    check(all(row["productionObserved"] is False for row in observations), "source observations make no production claim")
    check(len({row["fileSha256"] for row in observations}) >= 10, "source observations bind distinct files")
    assessment = tm.build_local_security_assessment(source_commit=COMMIT, source_tree=TREE, observations=observations)
    check(assessment["schemaVersion"] == tm.ASSESSMENT_SCHEMA, "assessment schema is pinned")
    check(assessment["sourceCommit"] == COMMIT and assessment["sourceTree"] == TREE, "assessment binds the checked source identity")
    check(assessment["status"] == "LOCAL_THREAT_MODEL_PASS_PROTECTED_HELD", "assessment status keeps protected hold")
    check(assessment["evidenceObservationCount"] == 16, "assessment records all evidence anchors")
    check(assessment["highCriticalThreatIds"] == high_critical, "assessment binds high and critical threats")
    check(assessment["protectedThreatIds"] == high_critical, "assessment holds every high and critical threat")
    check(assessment["residualProtectedGates"] == list(tm.RESIDUAL_PROTECTED_GATES), "assessment binds residual gates")
    check(assessment["allEvidenceAnchorsFound"] is True, "assessment records local anchor success")
    check(assessment["productionSecurityApproved"] is False, "assessment cannot approve production security")
    check(tm.verify_local_security_assessment(assessment) == assessment, "assessment verifies canonically")
    check(assessment == tm.build_local_security_assessment(source_commit=COMMIT, source_tree=TREE, observations=observations), "assessment is deterministic")
    assert_false_authority(assessment, "local assessment")

    hostile_models: list[tuple[dict[str, object], str]] = []
    hostile = copy.deepcopy(model); hostile["productionAuthority"]["securityLaunchApproved"] = True; hostile_models.append((reseal(hostile, "contractDigest"), "threat model refuses launch approval"))
    hostile = copy.deepcopy(model); hostile["threats"] = hostile["threats"][:-1]; hostile_models.append((reseal(hostile, "contractDigest"), "threat model refuses missing threat"))
    hostile = copy.deepcopy(model); hostile["boundaries"][0], hostile["boundaries"][1] = hostile["boundaries"][1], hostile["boundaries"][0]; hostile_models.append((reseal(hostile, "contractDigest"), "threat model refuses boundary reordering"))
    hostile = copy.deepcopy(model); hostile["threats"][0]["priority"] = "low"; hostile_models.append((reseal(hostile, "contractDigest"), "threat model refuses risk downgrade"))
    hostile = copy.deepcopy(model); hostile["threats"][4]["protectedHoldRequired"] = False; hostile_models.append((reseal(hostile, "contractDigest"), "threat model refuses removed isolation hold"))
    hostile = copy.deepcopy(model); hostile["threats"][5]["recommendedMitigations"] = []; hostile_models.append((reseal(hostile, "contractDigest"), "threat model refuses removed mitigations"))
    hostile = copy.deepcopy(model); hostile["evidenceAnchors"][0]["symbol"] = "trust request owner"; hostile_models.append((reseal(hostile, "contractDigest"), "threat model refuses anchor drift"))
    hostile = copy.deepcopy(model); hostile["openQuestions"] = []; hostile_models.append((reseal(hostile, "contractDigest"), "threat model refuses hidden uncertainty"))
    for hostile_model, label in hostile_models:
        refuses(lambda hostile_model=hostile_model: tm.verify_threat_model(hostile_model), label)

    refuses(lambda: tm.build_local_security_assessment(source_commit=COMMIT[:-1], source_tree=TREE, observations=observations), "assessment refuses malformed source commit")
    refuses(lambda: tm.build_local_security_assessment(source_commit=COMMIT, source_tree=TREE, observations=observations[:-1]), "assessment refuses missing anchor")
    hostile_rows = copy.deepcopy(observations); hostile_rows[0], hostile_rows[1] = hostile_rows[1], hostile_rows[0]
    refuses(lambda: tm.build_local_security_assessment(source_commit=COMMIT, source_tree=TREE, observations=hostile_rows), "assessment refuses anchor reordering")
    hostile_rows = copy.deepcopy(observations); hostile_rows[0]["anchorFound"] = False
    refuses(lambda: tm.build_local_security_assessment(source_commit=COMMIT, source_tree=TREE, observations=hostile_rows), "assessment refuses missing source anchor")
    hostile_rows = copy.deepcopy(observations); hostile_rows[0]["productionObserved"] = True
    refuses(lambda: tm.build_local_security_assessment(source_commit=COMMIT, source_tree=TREE, observations=hostile_rows), "assessment refuses production observation")
    hostile_rows = copy.deepcopy(observations); hostile_rows[0]["fileSha256"] = "bad"
    refuses(lambda: tm.build_local_security_assessment(source_commit=COMMIT, source_tree=TREE, observations=hostile_rows), "assessment refuses malformed file digest")
    hostile_assessment = copy.deepcopy(assessment); hostile_assessment["productionSecurityApproved"] = True; hostile_assessment = reseal(hostile_assessment, "assessmentDigest")
    refuses(lambda: tm.verify_local_security_assessment(hostile_assessment), "assessment refuses production security approval")
    hostile_assessment = copy.deepcopy(assessment); hostile_assessment["productionAuthority"]["publicLaunch"] = True; hostile_assessment = reseal(hostile_assessment, "assessmentDigest")
    refuses(lambda: tm.verify_local_security_assessment(hostile_assessment), "assessment refuses public launch authority")
    hostile_assessment = copy.deepcopy(assessment); hostile_assessment["protectedThreatIds"] = []; hostile_assessment = reseal(hostile_assessment, "assessmentDigest")
    refuses(lambda: tm.verify_local_security_assessment(hostile_assessment), "assessment refuses removed threat holds")
    source_path = ROOT / "publishing" / "threat_model.py"
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
    check(imports <= {"__future__", "hashlib", "json", "re", "collections"}, "threat model imports only pure standard-library modules")
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    check(not (called_names & {"open", "exec", "eval", "compile", "__import__"}), "threat model performs no dynamic execution or file I/O")
    check(not (called_attributes & {"unlink", "remove", "rmtree", "connect", "request", "run", "Popen"}), "threat model performs no filesystem network or process integration")
    for forbidden in ('"browserAuthenticationIntegrated": True', '"osIsolationEnforced": True', '"securityLaunchApproved": True', '"publicLaunch": True'):
        check(forbidden not in source, f"source contains no authority literal {forbidden}")

    markdown_path = ROOT / "docs" / "BUILDERWARS_THREAT_MODEL.md"
    markdown = markdown_path.read_text(encoding="utf-8")
    required_headings = (
        "## Executive summary", "## Scope and assumptions", "## System model",
        "### Primary components", "### Data flows and trust boundaries", "#### Diagram",
        "## Assets and security objectives", "## Attacker model", "### Capabilities",
        "### Non-capabilities", "## Entry points and attack surfaces", "## Top abuse paths",
        "## Threat model table", "## Criticality calibration", "## Focus paths for security review",
        "## Production gates and evidence boundary", "## Quality check",
    )
    check(all(heading in markdown for heading in required_headings), "Markdown threat model has the required section contract")
    check("```mermaid\nflowchart LR" in markdown and markdown.count("```mermaid") == 1, "Markdown has one conservative Mermaid diagram")
    for threat_id in threat_ids:
        check(threat_id in markdown, f"Markdown includes {threat_id}")
    for boundary_id in boundary_ids:
        check(boundary_id in markdown, f"Markdown includes {boundary_id}")
    for focus in model["focusPaths"]:
        check(f"`{focus['path']}`" in markdown, f"Markdown includes focus path {focus['path']}")
    check("no customer has completed" in markdown.lower(), "Markdown refuses customer proof")
    check("not a production security approval" in markdown.lower(), "Markdown refuses production approval")
    check("BuilderWars.com apex" in markdown, "Markdown keeps apex outside local authority")
    check(all(question in markdown for question in tm.OPEN_QUESTIONS), "Markdown carries every open service question")

    print(f"BuilderWars threat model: PASS ({CHECKS} checks)")
    print("10 threats / 8 boundaries / 16 source anchors / auth and OS-isolation gaps held / zero production security authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
