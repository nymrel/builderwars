#!/usr/bin/env python3
"""Deterministically validate the BuilderWars foundation acceptance chain."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FOUNDATION_PATH = ROOT / "docs" / "BUILDERWARS_FOUNDATION_COMPOSITE_ACCEPTANCE.v1.json"
LEDGER_PATH = ROOT / "docs" / "BUILDERWARS_COMPONENT_ACCEPTANCE_LEDGER.v1.json"
REVIEW_PATH = ROOT / "docs" / "BUILDERWARS_FINAL_FROZEN_FOUNDATION_REVIEW.md"

EXPECTED_CANDIDATE = "7ed78e1993b60359eb257299705e089acc701d1c"
EXPECTED_REMOTE_MAIN = "d0cb2b9fc4cba987eb421b6200efcdc9941cd909"
EXPECTED_NYMREL_CANDIDATE = "4f3b6270cee69f0465f0bfb458958e9bae0ba91c"
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

    slices = foundation["builderwarsCodeSliceReviews"]
    check(isinstance(slices, list) and len(slices) == 9, "nine historical code-slice reviews")
    check([item["order"] for item in slices] == list(range(1, 10)), "historical code-slice order is exact")
    check(all(item["liveVerdict"].startswith("PASS_P0_0_P1_0_") for item in slices), "historical code slices have zero P0/P1")
    check(all(HEX64.fullmatch(item["liveReceiptSha256"]) for item in slices), "historical code receipts are digest-bound")

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
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", EXPECTED_REMOTE_MAIN, EXPECTED_CANDIDATE],
        cwd=ROOT,
        check=False,
    )
    check(ancestor.returncode == 0, "recorded remote main is ancestor of candidate")
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
    check(ledger["status"] in {"review_candidate", "accepted_local_foundation_pending_integration"}, "ledger is not a launch state")
    check(ledger["publicBetaDependency"]["requiredCodeCandidates"] == ["builderwars-kernel", "nymrel-control-room"], "two required beta repositories")


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
    for key in ("runId", "receiptSha256", "assistantOutputSha256", "reviewedCommit", "reviewedFoundationSha256"):
        check(review[key] == external[key], f"external review {key} cross-binding")
    check(HEX64.fullmatch(external["receiptSha256"]) is not None, "external receipt digest format")
    check(HEX64.fullmatch(external["assistantOutputSha256"]) is not None, "external output digest format")
    check(HEX40.fullmatch(external["reviewedCommit"]) is not None, "reviewed commit format")
    check(REVIEW_PATH.is_file(), "durable foundation review record exists")
    review_text = REVIEW_PATH.read_text(encoding="utf-8")
    for value in (external["runId"], external["receiptSha256"], external["assistantOutputSha256"], external["reviewedCommit"], external["reviewedFoundationSha256"]):
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
