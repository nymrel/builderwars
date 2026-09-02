#!/usr/bin/env python3
"""Adversarial checks for the deterministic BuilderWars Arena read model."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bin"))

from arena.canonical import digest  # noqa: E402
from build_mobile_arena_read_model import (  # noqa: E402
    DEFAULT_DATASET,
    DEFAULT_CORRECTION_LEDGER,
    DEFAULT_OUTPUT,
    DEFAULT_SOURCE_MANIFEST,
    READ_MODEL_SCHEMA,
    ReadModelError,
    build_read_model,
)
from publishing.scoped_ratings import verify_scoped_rating_boards  # noqa: E402
from publishing.corrections import build_correction_ledger  # noqa: E402


def require(predicate: bool, message: str) -> None:
    if not predicate:
        raise AssertionError(message)


def expect_rejected(dataset: dict, manifest: dict, ledger: dict, needle: str) -> None:
    rebound_ledger = build_correction_ledger(
        dataset_digest=dataset["datasetDigest"],
        source_manifest_digest=manifest["manifestDigest"],
        approved_receipt_ids=dataset["publication"]["approvedReceiptIds"],
        entries=ledger["entries"],
    )
    try:
        build_read_model(dataset, manifest, rebound_ledger)
    except ReadModelError as exc:
        require(needle in str(exc), f"wrong rejection for {needle!r}: {exc}")
        return
    raise AssertionError(f"mutation should have been rejected: {needle}")


def rehash_dataset(dataset: dict) -> None:
    dataset["datasetDigest"] = digest({key: value for key, value in dataset.items() if key != "datasetDigest"})


def rehash_manifest(manifest: dict) -> None:
    manifest["manifestDigest"] = digest({key: value for key, value in manifest.items() if key != "manifestDigest"})


def manifest_for_dataset(manifest: dict, dataset: dict) -> dict:
    changed = copy.deepcopy(manifest)
    changed["datasetDigest"] = dataset["datasetDigest"]
    rehash_manifest(changed)
    return changed


def main() -> int:
    checks = 0
    dataset = json.loads(DEFAULT_DATASET.read_text(encoding="utf-8"))
    manifest = json.loads(DEFAULT_SOURCE_MANIFEST.read_text(encoding="utf-8"))
    ledger = json.loads(DEFAULT_CORRECTION_LEDGER.read_text(encoding="utf-8"))

    print("[1] tracked product compiles into the bounded read model")
    model = build_read_model(dataset, manifest, ledger)
    require(model["schemaVersion"] == READ_MODEL_SCHEMA, "read-model schema drift")
    require(model["projectionVersion"] == "3", "read-model projection drift")
    require(model["corrections"]["entries"] == [], "tracked corpus must not fabricate corrections")
    require(model["summary"]["correctionCount"] == 0, "tracked correction count drift")
    require(model["summary"]["activeScopedRatingReceiptCount"] == 8, "all tracked receipts should remain rating-active")
    require(model["summary"]["scopedRatingExcludedReceiptCount"] == 0, "tracked corpus should exclude no receipt")
    require(all(row["correction"]["state"] == "active" for row in model["receipts"]), "tracked receipt correction state drift")
    require(model["source"]["datasetDigest"] == dataset["datasetDigest"], "source digest not carried")
    require(model["summary"]["receiptCount"] == 8, "expected eight reviewed receipts")
    require(model["summary"]["verifiedReceiptCount"] == 8, "every projected receipt must be verified")
    require(model["summary"]["modelInfluencedUnattestedReceiptCount"] == 1, "model-influenced truth count drift")
    require(model["summary"]["scriptedReferenceReceiptCount"] == 6, "scripted truth count drift")
    require(model["summary"]["fallbackOnlyReferenceReceiptCount"] == 1, "fallback truth count drift")
    require(model["truthBoundary"]["live"] is False, "read model cannot imply live state")
    require(model["truthBoundary"]["hosted"] is False, "read model cannot imply hosted state")
    require(model["truthBoundary"]["authenticated"] is False, "read model cannot imply auth")
    require(all(row["proof"]["publicationApproved"] for row in model["receipts"]), "unapproved proof projected")
    require(all(row["proof"]["replayVerdict"] == "PASS" for row in model["receipts"]), "non-PASS replay projected")
    require(all(len(row["proof"]["engineDigest"]) == 64 for row in model["receipts"]), "exact engine digest missing")
    require(model["summary"]["scopedRatingBoardCount"] == 5, "expected five exact rating scopes")
    require(sum(row["receiptCount"] for row in model["scopedRatingBoards"]) == 8, "scoped boards do not cover eight receipts")
    require(
        verify_scoped_rating_boards(
            model["scopedRatingBoards"],
            model["receipts"],
            dataset_digest=model["source"]["datasetDigest"],
            source_manifest_digest=model["source"]["sourceManifestDigest"],
        ) == model["scopedRatingBoards"],
        "scoped boards do not verify",
    )
    require(model["readModelDigest"] == digest({key: value for key, value in model.items() if key != "readModelDigest"}), "read-model digest mismatch")
    checks += 23

    print("[2] stale generated output fails closed")
    command = [sys.executable, str(ROOT / "bin" / "build_mobile_arena_read_model.py"), "--check"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
    require(result.returncode == 0, result.stderr or result.stdout)
    tracked = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    require(tracked == model, "tracked output is not the compiled model")
    checks += 2

    print("[3] dataset and source-manifest integrity mutations are rejected")
    mutated_dataset = copy.deepcopy(dataset)
    mutated_dataset["datasetVersion"] = "tampered"
    expect_rejected(mutated_dataset, manifest, ledger, "dataset digest mismatch")
    checks += 1

    mutated_manifest = copy.deepcopy(manifest)
    mutated_manifest["entries"] = []
    expect_rejected(dataset, mutated_manifest, ledger, "source manifest digest mismatch")
    checks += 1

    mutated_manifest = copy.deepcopy(manifest)
    mutated_manifest["entries"][0]["publicTranscriptBytes"] += 1
    rehash_manifest(mutated_manifest)
    expect_rejected(dataset, mutated_manifest, ledger, "transcript byte count mismatch")
    checks += 1

    mutated_dataset = copy.deepcopy(dataset)
    mutated_dataset["receipts"][0]["verification"]["engineDigest"] = "0" * 64
    rehash_dataset(mutated_dataset)
    mutated_manifest = manifest_for_dataset(manifest, mutated_dataset)
    expect_rejected(mutated_dataset, mutated_manifest, ledger, "engine digest mismatch")
    checks += 1

    print("[4] a rehashed failed proof still cannot enter the read model")
    mutated_dataset = copy.deepcopy(dataset)
    mutated_dataset["receipts"][0]["verification"]["replayVerdict"] = "FAIL"
    rehash_dataset(mutated_dataset)
    mutated_manifest = copy.deepcopy(manifest)
    mutated_manifest["datasetDigest"] = mutated_dataset["datasetDigest"]
    rehash_manifest(mutated_manifest)
    expect_rejected(mutated_dataset, mutated_manifest, ledger, "verification replayVerdict mismatch")
    checks += 1

    print("[5] allowlist drift and evidence-label drift are rejected")
    mutated_dataset = copy.deepcopy(dataset)
    mutated_dataset["publication"]["approvedReceiptIds"] = mutated_dataset["publication"]["approvedReceiptIds"][:-1]
    mutated_dataset["publication"]["approvedReceiptCount"] -= 1
    rehash_dataset(mutated_dataset)
    mutated_manifest = copy.deepcopy(manifest)
    mutated_manifest["datasetDigest"] = mutated_dataset["datasetDigest"]
    mutated_manifest["approvedReceiptIds"] = mutated_dataset["publication"]["approvedReceiptIds"]
    mutated_manifest["approvedReceiptCount"] -= 1
    rehash_manifest(mutated_manifest)
    expect_rejected(mutated_dataset, mutated_manifest, ledger, "dataset receipt count must equal")
    checks += 1

    mutated_dataset = copy.deepcopy(dataset)
    mutated_dataset["receipts"][0]["truth"]["status"] = "scripted_reference"
    rehash_dataset(mutated_dataset)
    mutated_manifest = copy.deepcopy(manifest)
    mutated_manifest["datasetDigest"] = mutated_dataset["datasetDigest"]
    rehash_manifest(mutated_manifest)
    expect_rejected(mutated_dataset, mutated_manifest, ledger, "disagrees with move-source evidence")
    checks += 1

    print("[6] projection relationships fail closed after valid source rehashing")
    mutated_dataset = copy.deepcopy(dataset)
    mutated_dataset["futureFixtures"][0]["rulesDigest"] = "0" * 64
    rehash_dataset(mutated_dataset)
    expect_rejected(mutated_dataset, manifest_for_dataset(manifest, mutated_dataset), ledger, "rules binding drift")
    checks += 1

    mutated_dataset = copy.deepcopy(dataset)
    mutated_dataset["futureFixtures"][0]["matchup"][0]["entrantId"] = "0" * 64
    rehash_dataset(mutated_dataset)
    expect_rejected(mutated_dataset, manifest_for_dataset(manifest, mutated_dataset), ledger, "entrant is not receipt-backed")
    checks += 1

    mutated_dataset = copy.deepcopy(dataset)
    mutated_dataset["futureFixtures"][0]["matchup"][1]["seat"] = 0
    rehash_dataset(mutated_dataset)
    expect_rejected(mutated_dataset, manifest_for_dataset(manifest, mutated_dataset), ledger, "seats drift")
    checks += 1

    mutated_dataset = copy.deepcopy(dataset)
    mutated_dataset["futureFixtures"][0]["closeAt"] = "not-a-time"
    rehash_dataset(mutated_dataset)
    expect_rejected(mutated_dataset, manifest_for_dataset(manifest, mutated_dataset), ledger, "UTC second timestamp")
    checks += 1

    mutated_dataset = copy.deepcopy(dataset)
    mutated_dataset["rulesWeeks"][0]["rulesDigest"] = "0" * 64
    rehash_dataset(mutated_dataset)
    expect_rejected(mutated_dataset, manifest_for_dataset(manifest, mutated_dataset), ledger, "rules binding drift")
    checks += 1

    mutated_dataset = copy.deepcopy(dataset)
    mutated_dataset["futureFixtures"].append(copy.deepcopy(mutated_dataset["futureFixtures"][0]))
    rehash_dataset(mutated_dataset)
    expect_rejected(mutated_dataset, manifest_for_dataset(manifest, mutated_dataset), ledger, "duplicate future fixture")
    checks += 1

    mutated_dataset = copy.deepcopy(dataset)
    mutated_dataset["receipts"][0]["entrants"][1]["seat"] = 0
    rehash_dataset(mutated_dataset)
    expect_rejected(mutated_dataset, manifest_for_dataset(manifest, mutated_dataset), ledger, "entrant seats must be contiguous and unique")
    checks += 1

    print("[7] check mode detects a stale or missing output")
    with tempfile.TemporaryDirectory(prefix="builderwars-read-model-") as temp_dir:
        stale = Path(temp_dir) / "stale.json"
        stale.write_text("{}\n", encoding="utf-8")
        stale_result = subprocess.run(command + ["--out", str(stale)], cwd=ROOT, capture_output=True, text=True, timeout=30)
        require(stale_result.returncode != 0 and "stale" in stale_result.stderr, "stale output did not fail")
    checks += 1

    print(f"PASS: {checks} Arena read-model checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
