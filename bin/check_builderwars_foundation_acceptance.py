#!/usr/bin/env python3
"""Deterministically validate the BuilderWars foundation acceptance chain."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FOUNDATION_PATH = ROOT / "docs" / "BUILDERWARS_FOUNDATION_COMPOSITE_ACCEPTANCE.v1.json"
LEDGER_PATH = ROOT / "docs" / "BUILDERWARS_COMPONENT_ACCEPTANCE_LEDGER.v1.json"
REVIEW_PATH = ROOT / "docs" / "BUILDERWARS_FINAL_FROZEN_FOUNDATION_REVIEW.md"
RECEIPT_ROOT = Path(os.environ.get("LOCALAPPDATA", "")) / "JalenBuilds" / "receipts"

EXPECTED_CANDIDATE = "7ed78e1993b60359eb257299705e089acc701d1c"
EXPECTED_REMOTE_MAIN = "d0cb2b9fc4cba987eb421b6200efcdc9941cd909"
EXPECTED_NYMREL_CANDIDATE = "4f3b6270cee69f0465f0bfb458958e9bae0ba91c"
EXPECTED_HISTORICAL_SLICE_CANDIDATE = "3a58bd3b7f5189cd9b06a25bcfa078d2f1b92da2"
EXPECTED_FOUNDATION_DOCS = {
    "docs/BUILDERWARS_BRAND_DOMAIN_MIGRATION.md",
    "docs/BUILDERWARS_COM_DOMAIN_CUTOVER_CONTRACT.md",
    "docs/BUILDERWARS_COMPONENT_ACCEPTANCE_DECISIONS.md",
    "docs/BUILDERWARS_COMPONENT_ACCEPTANCE_LEDGER.v1.json",
    "docs/BUILDERWARS_DELIVERY_ROADMAP.md",
    "docs/BUILDERWARS_ENTITY_MODEL.v1.json",
    "docs/BUILDERWARS_PLATFORM_CHARTER.md",
    "docs/BUILDERWARS_REUSE_MATRIX.v1.json",
    "docs/BUILDERWARS_SUBMITTED_CONCEPTS_DECISION.md",
}
EXPECTED_NEVER_IMPLIED = {
    "merge",
    "release",
    "production configuration",
    "provider subscription use",
    "Cloudflare custody",
    "DNS state",
    "deployment",
    "customer journey",
    "public availability",
    "public beta launch",
}
EXPECTED_CLOSURE = {
    "candidate": EXPECTED_CANDIDATE,
    "base": "6330c5b673589eac69ffcb3fb00c16c6973baa61",
    "runId": "51119615-11ef-4962-b223-c368e1884485",
    "receiptSha256": "891107e08a1dfc300a6b4460fc8bba88b4f080e9318b3dfafba3afd17bbbe491",
    "assistantOutputSha256": "ac587924a22c1193d976a6086595d028995bdd0f6b3eace0536ade061d8c98d0",
    "verdict": "APPROVE_P0_0_P1_0_P2_0_P3_5",
}
EXPECTED_CLOSURE_FILES = {
    "provider_hub_hosted/store.py": "a08cd077035dd098e49b874f9a5e204109627d71c1742a683ee813513102f31f",
    "provider_hub_hosted/handlers.py": "63b698af1e045bfd07a0ebf5d3b46401799d0952f575299140d7336ad0424df1",
    "provider_hub_hosted/verify.py": "73c12ee810d7af9dd05353a815dc8cbc6407d442e0d27e4977a90607ea1079ce",
    "provider_hub_hosted/tests/test_control_plane.py": "4814e9116275caec55ba513ff814c456fdd61f24acafbd1605f2da40892d1ddc",
}
EXPECTED_HISTORICAL_STAGE_BINDINGS = {
    "docs/BUILDERWARS_SUBMITTED_CONCEPTS_DECISION.md": {
        "stageRunId": "df423f9b-2846-49e5-a89b-932f1ca4072b",
        "reviewedSha256": "e8c13b7e66dd31c4c192286d0d3c06e8cefef9478c45047f87878c9e7223c00d",
        "reviewedBytes": 17024,
    },
    "docs/BUILDERWARS_COMPONENT_ACCEPTANCE_DECISIONS.md": {
        "stageRunId": "288d5496-93b4-47cf-944f-f75ef4c1f743",
        "reviewedSha256": "9859675cf746e9614f1b82d06e69f03ef45b5daf94f6c68476dcd5c0bdd89002",
        "reviewedBytes": 17819,
    },
    "docs/BUILDERWARS_COMPONENT_ACCEPTANCE_LEDGER.v1.json": {
        "stageRunId": "3e6a6bbd-badd-4546-a22e-017453bcd482",
        "reviewedSha256": "8c84fe326e2b64a1fe5702b6e67e0eb6e20d92796de266304ddc5daa671c6011",
        "reviewedBytes": 39752,
    },
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
CHECKS = 0


def check(condition: bool, label: str) -> None:
    global CHECKS
    if not condition:
        raise AssertionError(label)
    CHECKS += 1
    print(f"PASS {label}")


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_object)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: top level must be an object")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def git_bytes(*args: str) -> bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return completed.stdout


def is_ancestor(older: str, newer: str) -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", older, newer],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    return completed.returncode == 0


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def validate_document_bindings(foundation: dict[str, Any]) -> None:
    bindings = foundation["foundationDocuments"]
    check(isinstance(bindings, list) and len(bindings) == 9, "nine foundation document bindings")
    paths = [item["path"] for item in bindings]
    check(set(paths) == EXPECTED_FOUNDATION_DOCS, "exact foundation document set")
    check(len(paths) == len(set(paths)), "foundation document paths are unique")
    for item in bindings:
        path = ROOT / item["path"]
        check(path.is_file(), f"foundation document exists: {item['path']}")
        check(item["sha256"] == sha256(path), f"foundation SHA-256 matches: {item['path']}")
        check(item["bytes"] == path.stat().st_size, f"foundation byte count matches: {item['path']}")


def validate_review_history(foundation: dict[str, Any]) -> None:
    stages = foundation["isolatedStageReviews"]
    check(isinstance(stages, list) and len(stages) == 5, "five isolated stage reviews")
    check(all(item["verdict"] == "PASS" for item in stages), "all isolated stages passed")
    check(all(item["p0Count"] == item["p1Count"] == 0 for item in stages), "isolated stages have zero P0/P1")
    check(all(HEX64.fullmatch(item["receiptSha256"]) for item in stages), "isolated receipts are digest-bound")

    current_bindings = {item["path"]: item for item in foundation["foundationDocuments"]}
    observed_historical: dict[str, dict[str, Any]] = {}
    for stage in stages:
        for digest_key in ("receiptSha256", "receiptFileSha256", "bundleSha256", "taskPacketSha256"):
            check(HEX64.fullmatch(stage[digest_key]) is not None, f"stage {stage['runId']} {digest_key} format")
        check(HEX40.fullmatch(stage["sourceHead"]) is not None, f"stage {stage['runId']} source-head format")
        receipt_path = RECEIPT_ROOT / stage["receiptPath"]
        check(receipt_path.is_file(), f"stage receipt exists: {stage['runId']}")
        check(sha256(receipt_path) == stage["receiptFileSha256"], f"stage receipt file SHA-256: {stage['runId']}")
        receipt = load_json(receipt_path)
        check(receipt["run_id"] == stage["runId"], f"stage receipt run id: {stage['runId']}")
        check(receipt["receipt_sha256"] == stage["receiptSha256"], f"stage controller receipt digest: {stage['runId']}")
        for document in stage["mandatoryDocuments"]:
            path = document["path"]
            check(path in current_bindings, f"stage document belongs to foundation: {path}")
            check(HEX64.fullmatch(document["sha256"]) is not None, f"stage document digest format: {path}")
            check(isinstance(document["bytes"], int) and document["bytes"] > 0, f"stage document byte count: {path}")
            current = current_bindings[path]
            if (document["sha256"], document["bytes"]) != (current["sha256"], current["bytes"]):
                check(path not in observed_historical, f"historical stage mismatch unique: {path}")
                observed_historical[path] = {
                    "stageRunId": stage["runId"],
                    "reviewedSha256": document["sha256"],
                    "reviewedBytes": document["bytes"],
                    "currentSha256": current["sha256"],
                    "currentBytes": current["bytes"],
                }

    rule = foundation["historicalStageBindingRule"]
    check(rule["currentCoverage"] == "external_foundation_review_slot_10_required", "current evolved bytes require review slot 10")
    declared_historical = {item["path"]: {key: value for key, value in item.items() if key != "path"} for item in rule["changedAfterStageReview"]}
    check(set(declared_historical) == set(EXPECTED_HISTORICAL_STAGE_BINDINGS), "exact historical/current mismatch path set")
    check(declared_historical == observed_historical, "historical/current mismatch map matches stage and current bindings")
    for path, expected in EXPECTED_HISTORICAL_STAGE_BINDINGS.items():
        for key, value in expected.items():
            check(declared_historical[path][key] == value, f"historical binding {path} {key}")

    slices = foundation["builderwarsCodeSliceReviews"]
    check(isinstance(slices, list) and len(slices) == 9, "nine historical code-slice reviews")
    check([item["order"] for item in slices] == list(range(1, 10)), "historical code-slice order is exact")
    check(all(item["liveVerdict"].startswith("PASS_P0_0_P1_0_") for item in slices), "historical code slices have zero P0/P1")
    check(all(HEX64.fullmatch(item["liveReceiptSha256"]) for item in slices), "historical code receipts are digest-bound")
    check(all(item["candidate"] == f"builderwars@{EXPECTED_HISTORICAL_SLICE_CANDIDATE}" for item in slices), "historical code-slice candidate is exact")
    for item in slices:
        for digest_key in ("taskSha256", "bundleSha256", "materialSignature", "preflightReceiptSha256", "liveReceiptSha256"):
            check(HEX64.fullmatch(item[digest_key]) is not None, f"code slice {item['order']} {digest_key} format")

    closure = foundation["currentCandidateClosureReview"]
    for key, expected in EXPECTED_CLOSURE.items():
        check(closure[key] == expected, f"current-candidate closure {key} binding")
    check(closure["hostedTests"] == "25/25", "current closure binds 25/25 hosted tests")
    check(closure["providerHubChecker"] == "10/10", "current closure binds provider-hub 10/10")
    file_bindings = {item["path"]: item["sha256"] for item in closure["sourceFiles"]}
    check(file_bindings == EXPECTED_CLOSURE_FILES, "current closure exact source set")
    for relative, expected in EXPECTED_CLOSURE_FILES.items():
        check(sha256(ROOT / relative) == expected, f"current closure source SHA-256 matches: {relative}")


def validate_git_custody(foundation: dict[str, Any], ledger: dict[str, Any]) -> None:
    check(HEX40.fullmatch(EXPECTED_CANDIDATE) is not None, "candidate identity format")
    check(git("cat-file", "-t", EXPECTED_CANDIDATE) == "commit", "candidate commit exists")
    check(git("cat-file", "-t", EXPECTED_REMOTE_MAIN) == "commit", "recorded remote-main commit exists")
    check(git("cat-file", "-t", EXPECTED_HISTORICAL_SLICE_CANDIDATE) == "commit", "historical slice candidate exists")
    check(git("cat-file", "-t", EXPECTED_CLOSURE["base"]) == "commit", "closure base exists")
    check(is_ancestor(EXPECTED_REMOTE_MAIN, EXPECTED_CANDIDATE), "recorded remote main is ancestor of candidate")
    check(is_ancestor(EXPECTED_HISTORICAL_SLICE_CANDIDATE, EXPECTED_CANDIDATE), "historical slice candidate is ancestor of current candidate")
    check(is_ancestor(EXPECTED_CLOSURE["base"], EXPECTED_CANDIDATE), "closure base is ancestor of current candidate")
    check(is_ancestor(EXPECTED_CANDIDATE, git("rev-parse", "HEAD")), "implementation candidate is ancestor of current foundation commit")
    check(foundation["custody"]["candidates"]["builderwars"]["head"] == EXPECTED_CANDIDATE, "foundation candidate pin")
    check(foundation["custody"]["candidates"]["nymrel"]["head"] == EXPECTED_NYMREL_CANDIDATE, "Nymrel candidate pin remains isolated")
    check(ledger["releaseCandidates"]["builderwars"]["head"] == EXPECTED_CANDIDATE, "ledger candidate pin")
    check(ledger["releaseCandidates"]["builderwars"]["remoteMain"] == EXPECTED_REMOTE_MAIN, "ledger remote-main pin")
    kernel = next(item for item in ledger["components"] if item["componentId"] == "builderwars-kernel")
    check(kernel["candidatePin"] == EXPECTED_CANDIDATE, "kernel component candidate pin")


def validate_truth_boundary(foundation: dict[str, Any], ledger: dict[str, Any]) -> None:
    boundary = foundation["truthBoundary"]
    check(set(boundary["neverImplied"]) == EXPECTED_NEVER_IMPLIED, "exact non-claim boundary")
    domain = boundary["domainAttestation"]
    check(domain["domain"] == "builderwars.com", "canonical domain spelling")
    check(domain["class"] == "operator_attestation_not_independent_proof", "domain purchase remains attestation-only")
    check(boundary["defensiveDomain"] == {"domain": "builderswars.com", "ownershipVerified": False, "includedInCutover": False}, "defensive domain remains excluded")
    check(boundary["selfAcceptanceForbidden"] is True, "self-acceptance forbidden")
    check(foundation["productAuthority"]["arbitraryHostedCodeExecution"] is False, "arbitrary hosted code remains disabled")
    assertions = foundation["consistencyAssertions"]
    check(assertions["noProtectedActionAuthorized"] is True, "no protected action authorized")
    check(len(foundation["heldProtectedActions"]) == assertions["heldActionCount"] == 10, "ten protected-action holds")
    check(len(foundation["foundationDocuments"]) == assertions["foundationDocumentCount"] == 9, "foundation document count assertion")
    check(len(foundation["isolatedStageReviews"]) == assertions["isolatedStageCount"] == 5, "isolated stage count assertion")
    check(len(foundation["builderwarsCodeSliceReviews"]) == assertions["codeSliceReviewCount"] == 9, "code-slice count assertion")
    check(assertions["currentCandidateClosureReviewCount"] == 1, "current closure count assertion")
    check(len(foundation["historicalStageBindingRule"]["changedAfterStageReview"]) == assertions["historicalStageBindingMismatchCount"] == 3, "historical mismatch count assertion")
    check(len(foundation["residualCatalog"]) == assertions["residualCount"] == foundation["residualCounts"]["total"], "residual total assertion")
    p2_count = sum(1 for item in foundation["residualCatalog"] if item["severity"] == "P2")
    p3_count = sum(1 for item in foundation["residualCatalog"] if item["severity"] == "P3")
    check(p2_count == foundation["residualCounts"]["p2"], "P2 residual count assertion")
    check(p3_count == foundation["residualCounts"]["p3"], "P3 residual count assertion")
    check(p2_count + p3_count == foundation["residualCounts"]["total"], "residual severity partition")
    check(len(foundation["nextGates"]) == assertions["nextGateCount"] == 7, "next-gate count assertion")
    check(assertions["allStagesPassZeroP0P1"] is True, "stage verdict assertion")
    check(assertions["allCodeSlicesPassZeroP0P1"] is True, "code-slice verdict assertion")
    check(assertions["currentCandidateClosurePassZeroP0P1"] is True, "closure verdict assertion")
    check(assertions["receiptBodiesNotEmbedded"] is True, "receipt-body boundary assertion")
    check(ledger["status"] in {"review_candidate", "accepted_local_foundation_pending_integration"}, "ledger is not a launch state")
    check(ledger["publicBetaDependency"]["requiredCodeCandidates"] == ["builderwars-kernel", "nymrel-control-room"], "two required beta repositories")


def normalized_foundation_transition(value: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(value)
    normalized["status"] = "<pending-or-accepted>"
    normalized.pop("externalFoundationReview", None)
    for item in normalized["foundationDocuments"]:
        if item["path"] == "docs/BUILDERWARS_COMPONENT_ACCEPTANCE_LEDGER.v1.json":
            item["sha256"] = "<ledger-transition-sha256>"
            item["bytes"] = "<ledger-transition-bytes>"
    for item in normalized["historicalStageBindingRule"]["changedAfterStageReview"]:
        if item["path"] == "docs/BUILDERWARS_COMPONENT_ACCEPTANCE_LEDGER.v1.json":
            item["currentSha256"] = "<ledger-transition-sha256>"
            item["currentBytes"] = "<ledger-transition-bytes>"
    return normalized


def normalized_ledger_transition(value: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(value)
    normalized["status"] = "<pending-or-accepted>"
    queue = normalized["independentReviewQueue"]
    queue["currentHold"] = "<pending-or-accepted-review-state>"
    for index, item in enumerate(queue["reviews"]):
        if item["order"] == 10:
            queue["reviews"][index] = {
                "order": item["order"],
                "reviewId": item["reviewId"],
                "candidate": item["candidate"],
                "evidenceMode": item["evidenceMode"],
                "transitionFields": "<pending-or-accepted>",
            }
            break
    return normalized


def validate_external_review(
    foundation: dict[str, Any], ledger: dict[str, Any], *, allow_pending: bool
) -> None:
    queue = ledger["independentReviewQueue"]
    review = next(item for item in queue["reviews"] if item["order"] == 10)
    check(review["reviewId"] == "builderwars-foundation-and-decisions", "foundation review occupies queue slot 10")
    check(review["candidate"].startswith(f"builderwars-foundation@{EXPECTED_CANDIDATE}+"), "foundation review candidate binding")
    if allow_pending:
        check(review["liveVerdict"] in {"pending_external_receipt", "PASS_P0_0_P1_0"}, "foundation review is pending or accepted")
        return

    external = foundation["externalFoundationReview"]
    check(foundation["status"] == "accepted_local_foundation_pending_integration", "foundation is locally accepted only")
    check(ledger["status"] == "accepted_local_foundation_pending_integration", "ledger is locally accepted only")
    check(review["liveVerdict"] == "PASS_P0_0_P1_0", "foundation review passed with zero P0/P1")
    binding_keys = (
        "runId",
        "receiptSha256",
        "receiptFileSha256",
        "assistantOutputSha256",
        "taskPacketSha256",
        "reviewedCommit",
        "reviewedFoundationSha256",
        "reviewedLedgerSha256",
        "reviewedCheckerSha256",
        "reviewedReviewRecordSha256",
    )
    for key in binding_keys:
        check(review[key] == external[key], f"external review {key} cross-binding")
    for key in binding_keys:
        if key not in {"runId", "reviewedCommit"}:
            check(HEX64.fullmatch(external[key]) is not None, f"external {key} digest format")
    check(HEX40.fullmatch(external["reviewedCommit"]) is not None, "reviewed commit format")
    check(git("cat-file", "-t", external["reviewedCommit"]) == "commit", "reviewed foundation commit exists")
    check(is_ancestor(external["reviewedCommit"], git("rev-parse", "HEAD")), "reviewed foundation commit is an ancestor of final record")

    frozen_foundation_bytes = git_bytes("show", f"{external['reviewedCommit']}:docs/BUILDERWARS_FOUNDATION_COMPOSITE_ACCEPTANCE.v1.json")
    frozen_ledger_bytes = git_bytes("show", f"{external['reviewedCommit']}:docs/BUILDERWARS_COMPONENT_ACCEPTANCE_LEDGER.v1.json")
    frozen_checker_bytes = git_bytes("show", f"{external['reviewedCommit']}:bin/check_builderwars_foundation_acceptance.py")
    frozen_review_bytes = git_bytes("show", f"{external['reviewedCommit']}:docs/BUILDERWARS_FINAL_FROZEN_FOUNDATION_REVIEW.md")
    check(digest_bytes(frozen_foundation_bytes) == external["reviewedFoundationSha256"], "reviewed foundation blob digest")
    check(digest_bytes(frozen_ledger_bytes) == external["reviewedLedgerSha256"], "reviewed ledger blob digest")
    check(digest_bytes(frozen_checker_bytes) == external["reviewedCheckerSha256"], "reviewed checker blob digest")
    check(digest_bytes(frozen_review_bytes) == external["reviewedReviewRecordSha256"], "reviewed pending record blob digest")
    check(sha256(Path(__file__).resolve()) == external["reviewedCheckerSha256"], "accepted checker bytes equal reviewed checker bytes")

    frozen_foundation = json.loads(frozen_foundation_bytes.decode("utf-8"), object_pairs_hook=strict_object)
    frozen_ledger = json.loads(frozen_ledger_bytes.decode("utf-8"), object_pairs_hook=strict_object)
    check(frozen_foundation["status"] == "candidate_frozen_for_external_max_acceptance", "reviewed foundation was pending")
    check("externalFoundationReview" not in frozen_foundation, "reviewed foundation did not self-accept")
    check(normalized_foundation_transition(foundation) == normalized_foundation_transition(frozen_foundation), "foundation transition changes only permitted receipt fields")
    check(normalized_ledger_transition(ledger) == normalized_ledger_transition(frozen_ledger), "ledger transition changes only permitted receipt fields")

    receipt_path = RECEIPT_ROOT / "ox-alpha-agent-runs" / f"{external['runId']}.json"
    check(receipt_path.is_file(), "external foundation receipt exists")
    check(sha256(receipt_path) == external["receiptFileSha256"], "external foundation receipt file digest")
    receipt = load_json(receipt_path)
    check(receipt["status"] == "completed", "external foundation receipt completed")
    check(receipt["receipt_sha256"] == external["receiptSha256"], "external foundation controller receipt digest")
    check(receipt["task_packet_sha256"] == external["taskPacketSha256"], "external foundation task packet digest")
    check(receipt["result"]["assistant_output"]["all_text_sha256"] == external["assistantOutputSha256"], "external foundation assistant output digest")
    check(receipt["result"]["runtime_identity_attestation"]["ok"] is True, "external foundation runtime identity attested")
    check(receipt["result"]["usage"]["tool_use_count"] == 0, "external foundation review used no tools")
    output = receipt["result"]["assistant_output"]["terminal_text"]
    check(output.startswith("VERDICT: PASS"), "external foundation verdict is PASS")
    check("SEVERITY COUNTS: P0 0, P1 0" in output, "external foundation verdict has zero P0/P1")
    check(REVIEW_PATH.is_file(), "durable foundation review record exists")
    review_text = REVIEW_PATH.read_text(encoding="utf-8")
    for value in (external[key] for key in binding_keys):
        check(value in review_text, f"durable review record contains {value[:12]}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--allow-pending-review",
        action="store_true",
        help="validate the immutable pre-review foundation candidate",
    )
    args = parser.parse_args()

    foundation = load_json(FOUNDATION_PATH)
    ledger = load_json(LEDGER_PATH)
    check(foundation["schemaVersion"] == "builderwars.foundation-composite-acceptance.v1", "foundation schema version")
    check(ledger["schemaVersion"] == "builderwars.component-acceptance-ledger.v1", "ledger schema version")
    validate_document_bindings(foundation)
    validate_review_history(foundation)
    validate_git_custody(foundation, ledger)
    validate_truth_boundary(foundation, ledger)
    validate_external_review(foundation, ledger, allow_pending=args.allow_pending_review)
    print(f"PASS BuilderWars foundation acceptance ({CHECKS} checks)")


if __name__ == "__main__":
    main()
