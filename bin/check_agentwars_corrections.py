#!/usr/bin/env python3
"""Adversarial checks for append-only public-receipt correction lineage."""

from __future__ import annotations

import ast
import copy
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bin.build_mobile_arena_read_model import build_read_model  # noqa: E402
from publishing import corrections  # noqa: E402


CHECKS = 0


def check(condition: bool, label: str) -> None:
    global CHECKS
    if not condition:
        raise AssertionError(label)
    CHECKS += 1


def refuses(callable_, label: str, needle: str = "") -> None:
    try:
        callable_()
    except corrections.CorrectionLedgerError as exc:
        check(not needle or needle in str(exc), label)
    else:
        raise AssertionError(label)


def reseal(value: dict) -> dict:
    changed = copy.deepcopy(value)
    changed["ledgerDigest"] = corrections.digest(
        {key: item for key, item in changed.items() if key != "ledgerDigest"}
    )
    return changed


def main() -> int:
    package = ROOT / "publishing" / "agentwars-public-v1"
    ledger_path = ROOT / "publishing" / "agentwars-public-correction-ledger.v1.json"
    dataset = json.loads((package / "dataset.json").read_text(encoding="utf-8"))
    manifest = json.loads((package / "source-manifest.json").read_text(encoding="utf-8"))
    tracked = json.loads(ledger_path.read_text(encoding="utf-8"))
    approved = dataset["publication"]["approvedReceiptIds"]
    bindings = {
        "dataset_digest": dataset["datasetDigest"],
        "source_manifest_digest": manifest["manifestDigest"],
        "approved_receipt_ids": approved,
    }

    print("[1] tracked ledger binds the exact reviewed source and records zero corrections")
    verified = corrections.verify_correction_ledger(tracked, **bindings)
    check(verified == tracked, "tracked correction ledger verifies exactly")
    check(tracked["schemaVersion"] == corrections.LEDGER_SCHEMA, "ledger schema is pinned")
    check(tracked["status"] == corrections.EMPTY_STATUS, "empty tracked status is explicit")
    check(tracked["entries"] == [], "tracked ledger fabricates no corrections")
    check(tracked["summary"]["activeReceiptCount"] == 8, "all tracked receipts remain active")
    check(tracked["summary"]["scopedRatingExcludedReceiptCount"] == 0, "tracked corpus excludes no ratings")
    check(all(value is False for value in tracked["authority"].values()), "tracked ledger grants zero authority")
    check(ledger_path.parent == ROOT / "publishing", "correction ledger is a downstream publishing overlay")
    check(package not in ledger_path.parents, "public corpus replacement cannot erase correction history")

    print("[2] synthetic append-only void and supersession preserve history but re-project ratings")
    first = corrections.build_correction_entry(
        sequence=1,
        previous_correction_id=None,
        target_receipt_id=approved[0],
        action="void",
        successor_receipt_id=None,
        reason_code="evidence_integrity_failure",
    )
    second = corrections.build_correction_entry(
        sequence=2,
        previous_correction_id=first["correctionId"],
        target_receipt_id=approved[1],
        action="supersede",
        successor_receipt_id=approved[2],
        reason_code="source_superseded",
    )
    synthetic = corrections.build_correction_ledger(entries=[first, second], **bindings)
    states, verified_synthetic = corrections.project_receipt_corrections(synthetic, **bindings)
    check(verified_synthetic == synthetic, "synthetic source-bound ledger verifies")
    check(synthetic["status"] == corrections.CORRECTED_STATUS, "non-empty status remains identity-unattested")
    check(synthetic["summary"]["activeReceiptCount"] == 6, "two corrected receipts leave six active")
    check(synthetic["summary"]["voidedReceiptCount"] == 1, "void is counted once")
    check(synthetic["summary"]["supersededReceiptCount"] == 1, "supersession is counted once")
    check(states[approved[0]]["state"] == "voided", "voided receipt state is explicit")
    check(states[approved[1]]["state"] == "superseded", "superseded receipt state is explicit")
    check(states[approved[1]]["successorReceiptId"] == approved[2], "successor lineage is explicit")
    check(states[approved[2]]["state"] == "active", "successor remains independently active")

    model = build_read_model(dataset, manifest, synthetic)
    check(len(model["receipts"]) == 8, "corrections never remove historical receipts")
    check(model["summary"]["activeScopedRatingReceiptCount"] == 6, "current rating projection uses active receipts")
    check(model["summary"]["scopedRatingExcludedReceiptCount"] == 2, "current rating projection reports exclusions")
    covered = {receipt_id for board in model["scopedRatingBoards"] for receipt_id in board["receiptIds"]}
    check(approved[0] not in covered and approved[1] not in covered, "corrected receipts cannot influence proof points")
    check(covered == set(approved[2:]), "every other reviewed receipt remains in its exact scope")
    check(model["receipts"][0]["outcome"] == build_read_model(dataset, manifest, tracked)["receipts"][0]["outcome"], "historical outcome bytes remain projected")
    check(model["corrections"]["ledgerDigest"] == synthetic["ledgerDigest"], "read model binds the exact correction ledger")

    print("[3] chain, target, successor, authority, and source tampering fail closed")
    tampered = copy.deepcopy(synthetic); tampered["ledgerDigest"] = "0" * 64
    refuses(lambda: corrections.verify_correction_ledger(tampered, **bindings), "ledger digest tamper is refused")
    tampered = copy.deepcopy(synthetic); tampered["authority"]["ranking"] = True; tampered = reseal(tampered)
    refuses(lambda: corrections.verify_correction_ledger(tampered, **bindings), "ranking authority is refused")
    tampered = copy.deepcopy(synthetic); tampered["entries"][1]["previousCorrectionId"] = None; tampered = reseal(tampered)
    refuses(lambda: corrections.verify_correction_ledger(tampered, **bindings), "broken append-only chain is refused")
    tampered = copy.deepcopy(synthetic); tampered["entries"].reverse(); tampered = reseal(tampered)
    refuses(lambda: corrections.verify_correction_ledger(tampered, **bindings), "reordered correction history is refused")
    unknown = corrections.build_correction_entry(
        sequence=1, previous_correction_id=None, target_receipt_id="0" * 64,
        action="void", successor_receipt_id=None, reason_code="invalid_result",
    )
    refuses(lambda: corrections.build_correction_ledger(entries=[unknown], **bindings), "unknown correction target is refused", "not an approved receipt")
    repeated = corrections.build_correction_entry(
        sequence=2, previous_correction_id=first["correctionId"], target_receipt_id=approved[0],
        action="void", successor_receipt_id=None, reason_code="duplicate_receipt",
    )
    refuses(lambda: corrections.build_correction_ledger(entries=[first, repeated], **bindings), "repeated correction target is refused")
    refuses(
        lambda: corrections.build_correction_entry(
            sequence=1, previous_correction_id=None, target_receipt_id=approved[0],
            action="void", successor_receipt_id=approved[1], reason_code="invalid_result",
        ),
        "void successor is refused",
    )
    refuses(
        lambda: corrections.build_correction_entry(
            sequence=1, previous_correction_id=None, target_receipt_id=approved[0],
            action="supersede", successor_receipt_id=None, reason_code="source_superseded",
        ),
        "missing supersession successor is refused",
    )
    refuses(
        lambda: corrections.verify_correction_ledger(tracked, **{**bindings, "dataset_digest": "0" * 64}),
        "source-digest mismatch is refused",
    )
    tampered = copy.deepcopy(synthetic); tampered["entries"][0]["extra"] = True; tampered = reseal(tampered)
    refuses(lambda: corrections.verify_correction_ledger(tampered, **bindings), "unknown correction fields are refused")

    print("[4] correction contract remains pure and bounded")
    source_path = ROOT / "publishing" / "corrections.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imports = {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    } | {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    check(imports <= {"__future__", "arena", "collections", "re", "typing"}, "correction contract imports only pure modules")
    check(not any(isinstance(node, (ast.With, ast.AsyncWith)) for node in tree.body), "correction contract has no import-time file access")
    check(not any(isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) for node in tree.body), "correction contract has no import-time calls")

    print(f"AgentWars append-only corrections: PASS ({CHECKS} checks)")
    print("8 historical receipts retained / synthetic void + supersession re-projected / zero production authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
