#!/usr/bin/env python3
"""Install one already-staged AgentWars artifact into a site worktree.

This command never discovers receipts. `build_public_dataset.py` performs the
exact replay and reviewed-allowlist gates first; this installer verifies that
artifact's complete file manifest, then atomically reconciles the public tree.
"""

import argparse
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from build_share_bundle import (  # noqa: E402
    BundleError,
    require_exact_verification,
    source_kind,
    truth_status,
    verify_with_snapshot,
)
from publishing.product import verify_artifact  # noqa: E402
from publishing.projection import PublicationError, file_sha256, project_receipt  # noqa: E402


def model_label(claimed):
    """'cli:ollama run llama3.2:3b' -> 'llama3.2:3b'; 'stub:v1' -> 'stub'."""
    if not claimed:
        return "unknown"
    kind, _, rest = claimed.partition(":")
    if kind == "stub":
        return "stub"
    if kind == "cli":
        return rest.split()[-1] if rest else "cli"
    return rest or kind


def series_of(path):
    rel = os.path.relpath(path, os.path.join(ROOT, "matches")).replace(os.sep, "/")
    parts = rel.split("/")
    return parts[0] if len(parts) > 2 else "single"


def summarise(path):
    report = None
    try:
        report = verify_with_snapshot(path)
        require_exact_verification(report)
        _public_receipt, records = project_receipt(path)
    except (BundleError, PublicationError) as error:
        if report is None:
            report = {"verdict": "FAIL", "errors": []}
        report = dict(report)
        report["replayVerdict"] = report.get("verdict")
        report["verdict"] = "FAIL"
        report["errors"] = list(report.get("errors") or []) + [str(error)]
        return None, report

    header = records[0]["body"]
    result = next((r["body"] for r in records if r["kind"] == "result"), None)
    if result is None:
        return None, report

    seats = []
    for e in header["entrants"]:
        seats.append({
            "seat": e["seat"],
            "name": e["name"],
            "model": model_label(e.get("claimed_model")),
            "backend": e.get("claimed_model"),
            "executionClaim": e.get("execution_claim", "unspecified"),
        })
    by_seat = {s["seat"]: s for s in seats}

    # provenance: did the model actually answer?
    for s in seats:
        s["modelMoves"] = 0
        s["fallbackMoves"] = 0
        s["scriptedMoves"] = 0
        s["otherMoves"] = 0
    for r in records:
        if r["kind"] != "move":
            continue
        note = r["body"].get("entrant_message", {}).get("note", "") or ""
        seat = r["body"].get("player")
        if seat in by_seat:
            key = {
                "model": "modelMoves",
                "fallback": "fallbackMoves",
                "scripted": "scriptedMoves",
                "other": "otherMoves",
            }[source_kind(note)]
            by_seat[seat][key] += 1

    source_claims = {
        seat["name"]: {
            "model": seat["modelMoves"],
            "fallback": seat["fallbackMoves"],
            "scripted": seat["scriptedMoves"],
            "other": seat["otherMoves"],
        }
        for seat in seats
    }

    winner = result.get("winner")
    return {
        "id": header["match_id"],
        "game": header["game"]["name"],
        "seed": header["seed"],
        "series": series_of(path),
        "moves": result.get("moves"),
        "reason": result.get("reason"),
        "decisive": result.get("decisive"),
        "winnerSeat": winner,
        "winner": by_seat[winner]["name"] if winner is not None else None,
        "winnerModel": by_seat[winner]["model"] if winner is not None else None,
        "loser": by_seat[1 - winner]["name"] if winner is not None else None,
        "loserModel": by_seat[1 - winner]["model"] if winner is not None else None,
        "seats": seats,
        "chainHead": report.get("chain_head"),
        "engineDigestMatch": report.get("engine_digest_match"),
        "modelAttested": header.get("attestation", {}).get("model_attested", False),
        "executionClaimsAttested": header.get("attestation", {}).get(
            "execution_claims_attested", False
        ),
        "truthStatus": truth_status(seats, source_claims),
        "moveSourceClaims": source_claims,
        "verified": True,
    }, report


def _assert_child(parent, child):
    if os.path.commonpath([os.path.abspath(parent), os.path.abspath(child)]) != os.path.abspath(parent):
        raise PublicationError("site install path escaped its parent")


def _atomic_public_install(source, destination):
    parent = os.path.dirname(destination)
    os.makedirs(parent, exist_ok=True)
    staging = tempfile.mkdtemp(prefix=".agentwars-site-stage-", dir=parent)
    backup = None
    _assert_child(parent, staging)
    source_files = _tree_manifest(source)
    try:
        shutil.rmtree(staging)
        shutil.copytree(source, staging)
        if _tree_manifest(staging) != source_files:
            raise PublicationError("staged public tree bytes disagree with artifact")
        if os.path.exists(destination):
            backup = tempfile.mkdtemp(prefix=".agentwars-site-backup-", dir=parent)
            os.rmdir(backup)
            _assert_child(parent, backup)
            os.replace(destination, backup)
        os.replace(staging, destination)
        staging = ""
        if _tree_manifest(destination) != source_files:
            rejected = tempfile.mkdtemp(prefix=".agentwars-site-rejected-", dir=parent)
            os.rmdir(rejected)
            os.replace(destination, rejected)
            if backup:
                os.replace(backup, destination)
                backup = None
            shutil.rmtree(rejected)
            raise PublicationError("installed public tree bytes disagree with artifact")
        if backup:
            shutil.rmtree(backup)
            backup = None
    finally:
        if staging and os.path.isdir(staging):
            _assert_child(parent, staging)
            shutil.rmtree(staging)
        if backup and os.path.isdir(backup):
            if not os.path.exists(destination):
                os.replace(backup, destination)
            else:
                shutil.rmtree(backup)


def _tree_manifest(root):
    rows = {}
    for directory, _dirs, names in os.walk(root):
        for name in names:
            path = os.path.join(directory, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            rows[rel] = {"sha256": file_sha256(path), "bytes": os.path.getsize(path)}
    return rows


def _atomic_file_install(source, destination):
    parent = os.path.dirname(destination)
    os.makedirs(parent, exist_ok=True)
    handle, staging = tempfile.mkstemp(prefix=".agentwars-data-stage-", dir=parent)
    os.close(handle)
    backup = None
    _assert_child(parent, staging)
    try:
        shutil.copyfile(source, staging)
        expected = file_sha256(source)
        if file_sha256(staging) != expected:
            raise PublicationError("staged site dataset bytes disagree with artifact")
        if os.path.exists(destination):
            handle, backup = tempfile.mkstemp(prefix=".agentwars-data-backup-", dir=parent)
            os.close(handle)
            os.unlink(backup)
            os.replace(destination, backup)
        os.replace(staging, destination)
        staging = ""
        if file_sha256(destination) != expected:
            if backup:
                os.replace(backup, destination)
                backup = None
            elif os.path.isfile(destination):
                os.unlink(destination)
            raise PublicationError("installed site dataset bytes disagree with artifact")
        if backup:
            os.unlink(backup)
            backup = None
    finally:
        if staging and os.path.isfile(staging):
            os.unlink(staging)
        if backup and os.path.isfile(backup):
            if not os.path.exists(destination):
                os.replace(backup, destination)
            else:
                os.unlink(backup)


def install_artifact(artifact, site):
    artifact = os.path.abspath(artifact)
    site = os.path.abspath(site)
    install = verify_artifact(artifact)
    if install.get("sitePublicPath") != "public/builderwars":
        raise PublicationError("artifact site public path is unsupported")
    if install.get("siteDatasetPath") != "src/data/builderwars.generated.json":
        raise PublicationError("artifact site dataset path is unsupported")
    dataset_path = os.path.join(artifact, "dataset.json")
    with open(dataset_path, "r", encoding="utf-8") as handle:
        dataset = json.load(handle)
    if dataset.get("datasetDigest") != install.get("datasetDigest"):
        raise PublicationError("site dataset digest disagrees with artifact install manifest")
    public_source = os.path.join(artifact, "public")
    public_destination = os.path.join(site, "public", "builderwars")
    _atomic_public_install(public_source, public_destination)

    data_destination = os.path.join(site, "src", "data", "builderwars.generated.json")
    _atomic_file_install(dataset_path, data_destination)
    if file_sha256(data_destination) != file_sha256(dataset_path):
        raise PublicationError("site dataset bytes disagree with staged artifact")
    unclaimed_path = os.path.join(site, "src", "data", "agentwars.generated.json")
    if os.path.isfile(unclaimed_path):
        os.unlink(unclaimed_path)
    return {
        "status": "PASS",
        "datasetDigest": dataset["datasetDigest"],
        "receiptCount": len(dataset["receipts"]),
        "publicPath": public_destination,
        "dataPath": data_destination,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--artifact", required=True, help="staged artifact from build_public_dataset.py")
    ap.add_argument("--out", required=True, help="path to the site worktree")
    args = ap.parse_args()
    try:
        report = install_artifact(args.artifact, args.out)
    except PublicationError as error:
        ap.error(str(error))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
