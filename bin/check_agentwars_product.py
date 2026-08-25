#!/usr/bin/env python3
"""Adversarial acceptance suite for the AgentWars public product contract."""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))

from arena.canonical import GENESIS, chain, digest  # noqa: E402
from arena.match import run_match  # noqa: E402
from build_share_bundle import build_manifest  # noqa: E402
from export_site import install_artifact  # noqa: E402
from publishing import projection as projection_module  # noqa: E402
from publishing.product import (  # noqa: E402
    RULES_WEEKS,
    _build_integrity,
    _title_state,
    assemble_dataset,
    build_product,
    verify_artifact,
    write_public_artifact,
)
from publishing.projection import (  # noqa: E402
    PublicationError,
    file_sha256,
    project_receipt,
    source_counts_digest,
    ten_fronts_scores,
)

PUBLICATION_MANIFEST = os.path.join(ROOT, "docs", "AGENTWARS_PUBLICATION_MANIFEST.v1.json")
TEN_FRONTS = os.path.join(
    ROOT,
    "matches",
    "agentwars-ten-fronts",
    "ten_fronts",
    "7000-0",
    "e16ac35d43eb3b47.jsonl",
)
REFERENCE = os.path.join(
    ROOT,
    "matches",
    "agentwars-fantasy",
    "fantasy_redraft",
    "9600-0",
    "8d161a470a12b0c3.jsonl",
)
MISSING_SNAPSHOT = os.path.join(ROOT, "matches", "e18c36c2f8903c1f.jsonl")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def expect_publication_error(fn, fragment):
    try:
        fn()
    except PublicationError as error:
        require(fragment in str(error), f"expected {fragment!r} in {error!r}")
        return
    raise AssertionError(f"expected PublicationError containing {fragment!r}")


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, value):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def file_map(root):
    rows = {}
    for directory, _dirs, names in os.walk(root):
        for name in names:
            path = os.path.join(directory, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            with open(path, "rb") as handle:
                rows[rel] = handle.read()
    return rows


def run_verifier(path):
    completed = subprocess.run(
        [sys.executable, os.path.join(ROOT, "verify.py"), path, "--json"],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    return completed, json.loads(completed.stdout)


def _scripted_manifest(name, strategy):
    script = os.path.join(ROOT, "entrants", "fantasy_gm_harness.py")
    return {
        "name": name,
        "cmd": [sys.executable, script, "--name", name, "--strategy", strategy],
        "env": [],
        "claimed_model": "scripted-baseline:v1",
        "execution_claim": "scripted",
    }


def check_match_ids_fail_before_paths():
    entrants = [
        _scripted_manifest("Sunday Machine", "win-now"),
        _scripted_manifest("Future Proof", "long-game"),
    ]
    hostile = (
        "../escape",
        "C:/absolute",
        "a/b",
        "a\\b",
        "\u00e9",
        "bad\ncontrol",
        "",
        "a" * 81,
        42,
        "CON",
        "nul",
        "PrN",
        "aux",
        "COM1",
        "com9",
        "LPT1",
        "lpt9",
    )
    with tempfile.TemporaryDirectory(prefix="agentwars-match-id-") as work:
        for index, match_id in enumerate(hostile):
            out = os.path.join(work, f"rejected-{index}")
            try:
                run_match(
                    game_name="fantasy_redraft",
                    seed=9800,
                    entrants=entrants,
                    out_dir=out,
                    match_id=match_id,
                )
            except ValueError as error:
                require("match_id" in str(error), "hostile custom id must fail through id validator")
            else:
                raise AssertionError(f"hostile custom match id was accepted: {match_id!r}")
            require(not os.path.exists(out), "invalid id must fail before output/scratch directory creation")
        require(not list(os.scandir(work)), "invalid ids must leave no files or scratch directories")

        safe_out = os.path.join(work, "safe")
        result = run_match(
            game_name="fantasy_redraft",
            seed=9800,
            entrants=entrants,
            out_dir=safe_out,
            match_id="Safe_match-01",
        )
        require(result["match_id"] == "Safe_match-01", "safe custom match id is retained")
        require(os.path.basename(result["transcript"]) == "Safe_match-01.jsonl", "safe id path")
        require(not any(name.startswith(".scratch-") for name in os.listdir(safe_out)),
                "completed safe match cleans scratch directory")


def check_verifier_exit_contract():
    exact, exact_report = run_verifier(REFERENCE)
    require(exact.returncode == 0, "exact snapshot replay must exit zero")
    require(exact_report["replay_verdict"] == "PASS", "exact replay diagnostic verdict")
    require(exact_report["effective_verdict"] == "PASS", "exact effective verdict")

    with tempfile.TemporaryDirectory(prefix="agentwars-verifier-tamper-") as work:
        tampered = os.path.join(work, "tampered.jsonl")
        shutil.copyfile(REFERENCE, tampered)
        with open(tampered, "r", encoding="utf-8") as handle:
            lines = handle.readlines()
        first = json.loads(lines[0])
        first["body"]["seed"] += 1
        lines[0] = json.dumps(first, sort_keys=True, separators=(",", ":")) + "\n"
        with open(tampered, "w", encoding="utf-8", newline="\n") as handle:
            handle.writelines(lines)
        failed, failed_report = run_verifier(tampered)
        require(failed.returncode == 1, "tampered replay must exit one")
        require(failed_report["replay_verdict"] == "FAIL", "tampered replay diagnostic")
        require(failed_report["effective_verdict"] == "FAIL", "tampered effective verdict")

    missing, missing_report = run_verifier(MISSING_SNAPSHOT)
    require(missing.returncode == 1, "missing snapshot must fail closed")
    require(missing_report["replay_verdict"] == "FAIL", "foreign-engine raw replay fails closed")
    require(missing_report["engine_digest_match"] is False, "foreign-engine diagnostic field")
    require(missing_report["effective_verdict"] == "FAIL", "missing snapshot effective verdict")
    require(missing_report["verifier_snapshot_match"] is False, "missing snapshot diagnostic field")


def check_deterministic_atomic_artifact():
    with tempfile.TemporaryDirectory(prefix="agentwars-product-determinism-") as work:
        first = os.path.join(work, "first")
        second = os.path.join(work, "second")
        report_a = write_public_artifact(ROOT, PUBLICATION_MANIFEST, first)
        report_b = write_public_artifact(ROOT, PUBLICATION_MANIFEST, second)
        require(report_a["datasetDigest"] == report_b["datasetDigest"], "dataset digest deterministic")
        require(file_map(first) == file_map(second), "two product builds must be byte-identical")

        stale = os.path.join(first, "public", "stale-orphan.json")
        with open(stale, "w", encoding="utf-8") as handle:
            handle.write("stale")
        write_public_artifact(ROOT, PUBLICATION_MANIFEST, first)
        require(not os.path.exists(stale), "atomic whole-tree replacement must prune stale orphans")
        verify_artifact(first)

        site = os.path.join(work, "site")
        os.makedirs(os.path.join(site, "src", "data"), exist_ok=True)
        with open(os.path.join(site, "src", "data", "agentwars.generated.json"), "w", encoding="utf-8") as handle:
            handle.write("stale unclaimed dataset")
        site_report = install_artifact(first, site)
        require(site_report["datasetDigest"] == report_a["datasetDigest"], "site pins staged digest")
        public_dest = os.path.join(site, "public", "builderwars")
        require(file_map(public_dest) == file_map(os.path.join(first, "public")), "site public tree exact")
        require(os.path.isfile(os.path.join(site, "src", "data", "builderwars.generated.json")),
                "site installs the exact owned dataset path")
        require(not os.path.exists(os.path.join(site, "src", "data", "agentwars.generated.json")),
                "site tombstones the unclaimed parallel dataset path")
        site_stale = os.path.join(public_dest, "stale.json")
        with open(site_stale, "w", encoding="utf-8") as handle:
            handle.write("stale")
        install_artifact(first, site)
        require(not os.path.exists(site_stale), "site reinstall prunes stale public files")


def check_allowlist_and_parity():
    dataset, source_manifest, _outputs = build_product(ROOT, PUBLICATION_MANIFEST)
    publication = read_json(PUBLICATION_MANIFEST)
    approved = [row for row in publication["entries"] if row["decision"] == "approved_for_publication"]
    require(len(dataset["receipts"]) == len(approved) == 8, "only explicitly approved receipts publish")
    approved_ids = {row["sourceChainHead"] for row in approved}
    require(set(dataset["publication"]["approvedReceiptIds"]) == approved_ids, "allowlist is sole selector")
    require(dataset["publication"]["verifiedDoesNotImplyPublished"] is True, "verification/publication split")
    require(dataset["publication"]["approvedReceiptIds"] == sorted(approved_ids), "receipt set sorted")
    require(dataset["publication"]["approvedReceiptCount"] == len(approved_ids), "receipt count exact")
    require(dataset["publication"]["approvedReceiptSetDigest"] == digest(sorted(approved_ids)),
            "receipt set digest exact")
    digest_payload = {key: value for key, value in dataset.items() if key != "datasetDigest"}
    require(dataset["datasetDigest"] == digest(digest_payload), "documented dataset digest recomputes")
    require(all("cheap-vs-expensive" not in row["sourcePath"] for row in source_manifest["entries"]),
            "held cross-model corpus must not publish")
    unallowlisted = os.path.join(ROOT, "matches", "ollama", "5000-1", "d3c2da7d9212a337.jsonl")
    unallowlisted_receipt, _ = project_receipt(unallowlisted)
    require(unallowlisted_receipt["receiptId"] not in approved_ids, "test fixture must be exact PASS but unallowlisted")
    require(unallowlisted_receipt["receiptId"] not in {row["receiptId"] for row in dataset["receipts"]},
            "unallowlisted exact PASS must not export")
    require(
        "18554c28bb2c05e6cea4256808e64910e0586b66e83a4d52f1b6cb680715c4d9"
        not in approved_ids,
        "missing-snapshot e18 corpus bug must remain excluded",
    )

    receipts = {row["receiptId"]: row for row in dataset["receipts"]}
    played = {row["receiptId"]: row for row in dataset["interactionManifest"]["playedArtifacts"]}
    for source in source_manifest["entries"]:
        receipt = receipts[source["receiptId"]]
        evidence = played[source["receiptId"]]["publicationEvidence"]
        require(receipt["sourceParity"]["fileSha256"] == source["sourceFileSha256"], "file hash parity")
        require(receipt["sourceParity"]["chainHead"] == source["sourceChainHead"], "chain parity")
        require(
            receipt["sourceParity"]["moveSourceCountsDigest"] == source["sourceCountsDigest"],
            "source-count parity",
        )
        require(evidence["sourceFileSha256"] == source["sourceFileSha256"], "interaction file parity")
        require(evidence["sourceChainHead"] == source["sourceChainHead"], "interaction chain parity")
        require(receipt["transcript"]["relativePath"] == source["publicTranscriptPath"], "public path parity")
        require(receipt["transcript"]["sha256"] == source["publicTranscriptSha256"], "public hash parity")
        require(receipt["transcript"]["bytes"] == source["publicTranscriptBytes"], "public bytes parity")
        require(receipt["shareManifestHash"] == source["shareManifestHash"], "share manifest parity")
        require(receipt["verification"]["verifierSnapshotDigest"] == source["verifierSnapshotDigest"],
                "verifier snapshot parity")
        raw_copy = os.path.join(
            ROOT, "publishing", "agentwars-public-v1", "public", "m", f"{source['receiptId']}.jsonl"
        )
        if os.path.exists(raw_copy):
            require(file_sha256(raw_copy) == source["sourceFileSha256"], "export raw bytes parity")

    share = build_manifest(REFERENCE)
    reference_receipt = receipts[share["match"]["receiptId"]]
    share_totals = {
        key: sum(row[key] for row in share["moveSourceClaims"].values())
        for key in ("model", "fallback", "scripted", "other")
    }
    dataset_totals = {
        key: sum(row[key] for row in reference_receipt["moveSourceClaims"])
        for key in ("model", "fallback", "scripted", "other")
    }
    require(share_totals == dataset_totals, "raw/share/product source-count parity")
    require(share["match"]["fixtureId"] == reference_receipt["fixtureId"], "share fixture parity")

    with tempfile.TemporaryDirectory(prefix="agentwars-product-parity-") as work:
        for field, fragment in (
            ("sourceFileSha256", "file hash parity"),
            ("sourceChainHead", "chain-head parity"),
        ):
            hostile = copy.deepcopy(publication)
            hostile["entries"][0][field] = "f" * 64
            path = os.path.join(work, f"bad-{field}.json")
            write_json(path, hostile)
            expect_publication_error(lambda path=path: build_product(ROOT, path), fragment)
        hostile = copy.deepcopy(publication)
        hostile["entries"][0]["sourceCounts"]["other"] += 1
        path = os.path.join(work, "bad-counts.json")
        write_json(path, hostile)
        expect_publication_error(lambda: build_product(ROOT, path), "move-source count parity")


def check_hostile_paths_no_outside_writes():
    publication = read_json(PUBLICATION_MANIFEST)
    with tempfile.TemporaryDirectory(prefix="agentwars-product-path-") as work:
        hostile = copy.deepcopy(publication)
        hostile["entries"][0]["sourcePath"] = "matches/../../outside.jsonl"
        manifest = os.path.join(work, "hostile.json")
        write_json(manifest, hostile)
        destination = os.path.join(work, "artifact")
        sentinel = os.path.join(work, "outside.jsonl")
        with open(sentinel, "w", encoding="utf-8") as handle:
            handle.write("sentinel")
        expect_publication_error(
            lambda: write_public_artifact(ROOT, manifest, destination),
            "sourcePath",
        )
        require(not os.path.exists(destination), "hostile id/path must not create artifact")
        with open(sentinel, "r", encoding="utf-8") as handle:
            require(handle.read() == "sentinel", "hostile path must not write outside destination")


def rewrite_variant(source, destination):
    with open(source, "r", encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle]
    move = next(row for row in records if row["kind"] == "move")
    note = move["body"]["entrant_message"].get("note", "source=scripted")
    move["body"]["entrant_message"]["note"] = note + ";variant=second_receipt"
    previous = GENESIS
    for record in records:
        body = {"kind": record["kind"], "seq": record["seq"], "body": record["body"]}
        record["prev"] = previous
        record["hash"] = chain(previous, body)
        previous = record["hash"]
    with open(destination, "w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


def _wrapper(receipt, records, path):
    return {
        "receipt": receipt,
        "records": records,
        "path": path,
        "source": {
            "sequence": 0,
            "sourcePath": "matches/test/reference.jsonl",
            "sourceFileSha256": file_sha256(path),
            "sourceChainHead": receipt["receiptId"],
            "sourceCounts": {
                key: sum(row[key] for row in receipt["moveSourceClaims"])
                for key in ("model", "fallback", "scripted", "other")
            },
            "sourceCountsDigest": source_counts_digest(receipt["moveSourceClaims"]),
            "receiptId": receipt["receiptId"],
            "fixtureId": receipt["fixtureId"],
            "publicTranscriptPath": receipt["transcript"]["relativePath"],
            "publicTranscriptSha256": receipt["transcript"]["sha256"],
            "publicTranscriptBytes": receipt["transcript"]["bytes"],
            "shareManifestHash": receipt["shareManifestHash"],
            "engineDigest": receipt["verification"]["engineDigest"],
            "verifierSnapshotDigest": receipt["verification"]["verifierSnapshotDigest"],
            "verification": {
                "replayVerdict": "PASS",
                "engineDigestMatch": True,
                "verifierSnapshotMatch": True,
                "effectiveVerdict": "PASS",
            },
            "label": "test",
        },
    }


def check_duplicate_fixture_distinct_receipts():
    with tempfile.TemporaryDirectory(prefix="agentwars-duplicate-fixture-") as work:
        variant = os.path.join(work, "variant.jsonl")
        rewrite_variant(REFERENCE, variant)
        first_receipt, first_records = project_receipt(REFERENCE)
        second_receipt, second_records = project_receipt(variant)
        dynasty_path = os.path.join(
            ROOT, "matches", "agentwars-fantasy", "fantasy_dynasty", "9600-0",
            "93f3a5f5d5ba31a0.jsonl",
        )
        surge_path = os.path.join(
            ROOT, "matches", "agentwars-fantasy", "fantasy_qb_surge", "9600-0",
            "40dd49fd6bbe5404.jsonl",
        )
        dynasty_receipt, dynasty_records = project_receipt(dynasty_path)
        surge_receipt, surge_records = project_receipt(surge_path)
        require(first_receipt["fixtureId"] == second_receipt["fixtureId"], "logical fixture id reusable")
        require(first_receipt["receiptId"] != second_receipt["receiptId"], "chain heads remain unique receipts")
        entrants = [row["entrantId"] for row in first_receipt["entrants"]]
        future = [{
            "leagueId": "agentwars_test_v1",
            "week": 1,
            "game": "fantasy_redraft",
            "gameVersion": "1",
            "rulesVersion": "1",
            "seed": 9990,
            "entrantIdsBySeat": entrants,
            "closeAt": "2026-09-30T16:00:00Z",
            "status": "unplayed",
            "activationStatus": "proposed_not_activated",
        }]
        dataset = assemble_dataset(
            [
                _wrapper(first_receipt, first_records, REFERENCE),
                _wrapper(second_receipt, second_records, variant),
                _wrapper(dynasty_receipt, dynasty_records, dynasty_path),
                _wrapper(surge_receipt, surge_records, surge_path),
            ],
            publication_manifest_digest="a" * 64,
            eligible_for_review=[],
            title_eligible=set(),
            future_fixtures=future,
            build_integrity=_build_integrity(ROOT, PUBLICATION_MANIFEST),
        )
        same_fixture = [
            row for row in dataset["receipts"] if row["fixtureId"] == first_receipt["fixtureId"]
        ]
        require(len(same_fixture) == 2, "duplicate fixture/different receipt is retained")
        require(any(row["meetingCount"] == 4 for row in dataset["rivalries"]),
                "both same-fixture receipts enter rivalry history")


def _walk(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def check_public_safety_and_product_mechanics():
    dataset, source_manifest, _outputs = build_product(ROOT, PUBLICATION_MANIFEST)
    banned_keys = {
        "claimedmodel", "claimed_model", "responsehash", "response_hash", "response_sha256",
        "command", "cmd", "env", "declared_env", "stderr", "backend", "prompt",
    }
    for key, _value in _walk(dataset):
        require(key.casefold() not in banned_keys, f"generated public JSON leaked unsafe key {key!r}")
        require("command" not in key.casefold(),
                f"generated public JSON leaked command-bearing key {key!r}")
    rendered = json.dumps(dataset, sort_keys=True)
    for fragment in ("scripted-baseline:v1", "python.exe", "OPENCODE_", "response_sha256"):
        require(fragment not in rendered, f"generated public JSON leaked raw value {fragment!r}")

    forbidden_teaser = ("result", "winner", "score", "margin", "outcome")
    for teaser in dataset["teasers"]:
        for key, _value in _walk(teaser):
            require(not any(word in key.casefold() for word in forbidden_teaser),
                    f"teaser leaks reveal field {key!r}")
    require(all(clip["boundedRecordCount"] == 1 and clip["rawMoveOmitted"] for clip in dataset["clips"]),
            "clip candidates are one-record bounded and omit raw moves")
    fantasy_rivalry = next(row for row in dataset["rivalries"] if row["competition"] == "agentwars-fantasy")
    require(fantasy_rivalry["meetingCount"] == 6, "six scripted fantasy receipts form rivalry history")
    require(all(row["runback"]["status"] == "unplayed_challenge" for row in fantasy_rivalry["history"]),
            "runbacks remain unplayed descriptors")
    require(dataset["titles"]["redraftCrown"]["holderEntrantId"] is not None, "Redraft Crown custody")
    require(dataset["titles"]["dynastyThrone"]["holderEntrantId"] is not None, "Dynasty Throne custody")
    require(any(row["rulesWeekId"] == "fantasy_qb_surge_v1" for row in dataset["rulesWeeks"]),
            "QB Surge registered as a versioned rules week")
    require(all(row["integerOnlyScoring"] for row in RULES_WEEKS), "weekly games use integer-only scoring")

    for fixture in dataset["futureFixtures"]:
        require(fixture["status"] == "unplayed", "future fixture discriminant")
        require(fixture["activationStatus"] == "proposed_not_activated", "honest prediction activation")
        require(fixture["prediction"]["status"] == "closed_proposed_not_activated", "prediction closed")
        require("server writes committedAt" in fixture["prediction"]["committedAtSemantics"],
                "server authoritative commitment timestamp")
        keys = {key for key, _value in _walk(fixture)}
        require("receiptId" not in keys and "clipId" not in keys, "future fixture invents no receipt/clip id")

    interaction = dataset["interactionManifest"]
    fingerprint_core = {key: value for key, value in interaction.items() if key != "fingerprint"}
    require(interaction["fingerprint"] == digest(fingerprint_core), "interaction fingerprint canonical")
    require(source_manifest["interactionManifestFingerprint"] == interaction["fingerprint"],
            "source manifest pins interaction fingerprint")
    require(interaction["campaignId"] == "agentwars_launch_v1", "fixed campaign id")
    require(interaction["sourceLabel"] == "agentwars_share", "fixed source label")
    require(all(row["sourceLabel"] == "agentwars_share" for row in interaction["playedArtifacts"]),
            "played share attribution is fixed")
    require(all(row["campaignId"] == "agentwars_launch_v1" and row["creativeId"].startswith("prediction_")
                for row in interaction["futureFixtures"]), "future prediction attribution fixed")
    require(all(row["format"] in ("redraft", "dynasty", "qb_surge")
                for row in interaction["futureFixtures"]), "future format enum bounded")
    require(all(row["rulesDigest"] and row["verifierSnapshotDigest"]
                for row in interaction["futureFixtures"]), "future fixtures pin published rules")
    require(all(row["basisReceiptIds"] and row["basisDigest"] for row in dataset["titles"].values()),
            "titles pin exact allowlisted basis")
    require(all(row["verifierSnapshotAvailable"] and row["verifierSnapshotDigest"]
                for row in dataset["rulesWeeks"]), "rules pin exact verifier snapshot")

    integrity = dataset["buildIntegrity"]
    completed = subprocess.run(
        ["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    )
    require(integrity["sourceCommit"] == completed.stdout.strip().lower(), "source commit envelope")
    require(integrity["verifierSha256"] == file_sha256(os.path.join(ROOT, "verify.py")),
            "verifier file hash envelope")
    require(integrity["publicationManifestFileSha256"] == file_sha256(PUBLICATION_MANIFEST),
            "publication manifest file hash envelope")

    base = next(row for row in dataset["receipts"] if row["game"]["name"] == "fantasy_redraft")
    voided = copy.deepcopy(base)
    voided["receiptId"] = "f" * 64
    voided["outcome"]["status"] = "void"
    voided["outcome"]["winnerEntrantId"] = voided["entrants"][1]["entrantId"]
    title = _title_state(
        [base, voided],
        {base["receiptId"], voided["receiptId"]},
        "fantasy_redraft",
        "Redraft Crown",
    )
    require(len(title["history"]) == 1, "void receipt cannot change title custody")
    require(sum(row["ties"] for row in title["leaderboard"]) == 0, "void receipt is not a tie")


def _rechained_copy(source, destination, mutate):
    """Copy a transcript, apply one hostile mutation, then repair its hash chain."""
    with open(source, "r", encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle]
    mutate(records)
    previous = GENESIS
    for record in records:
        body = {"kind": record["kind"], "seq": record["seq"], "body": record["body"]}
        record["prev"] = previous
        record["hash"] = chain(previous, body)
        previous = record["hash"]
    with open(destination, "w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


def check_ten_fronts_score_extractor():
    require(ten_fronts_scores({"scores": [319, 226]}) == [319, 226], "canonical scores accepted")
    for hostile in (
        None,
        {},
        {"scores": [319]},
        {"scores": [319, 226, 1]},
        {"scores": ["319", "226"]},
        {"scores": [319.0, 226]},
        {"scores": [True, 226]},
        {"scores": [-1, 226]},
    ):
        expect_publication_error(lambda hostile=hostile: ten_fronts_scores(hostile),
                                 "ten fronts")


def check_ten_fronts_public_source():
    publication = read_json(PUBLICATION_MANIFEST)
    approved = [row for row in publication["entries"]
                if row["decision"] == "approved_for_publication"]
    require(len(approved) == 8, "eight explicitly approved receipts after Ten Fronts")
    entry = next(row for row in publication["entries"] if row["sequence"] == 7)
    require(entry["titleEligible"] is False, "Ten Fronts reference stays title-ineligible")
    require(
        entry["sourcePath"] ==
        "matches/agentwars-ten-fronts/ten_fronts/7000-0/e16ac35d43eb3b47.jsonl",
        "exact reviewed Ten Fronts source path",
    )
    require(file_sha256(TEN_FRONTS) == entry["sourceFileSha256"], "reviewed source hash exact")
    require("fallback" in entry["label"] and "not model-played" in entry["label"],
            "label must state deterministic-fallback provenance")

    dataset, source_manifest, outputs = build_product(ROOT, PUBLICATION_MANIFEST)
    receipt = next(row for row in dataset["receipts"]
                   if row["receiptId"] == entry["sourceChainHead"])
    require(receipt["game"]["name"] == "ten_fronts", "projected game name")
    require(receipt["outcome"]["scores"] == [319, 226], "seat-order referee scores reproduce")
    require(receipt["outcome"]["winnerSeat"] == 0, "referee winner seat retained")
    require(receipt["story"]["headline"] == "Stub Iron Front wins ten fronts",
            "public headline is state-derived")
    require(receipt["story"]["resultLine"] == "319-226 over Stub Even Reserve",
            "public result line is state-derived")
    require(receipt["story"]["question"] == "Would you take the other side in the runback?",
            "honest runback question")
    counts = {row["seat"]: row for row in receipt["moveSourceClaims"]}
    require(all(counts[seat]["fallback"] == 40 for seat in (0, 1)), "per-seat fallbacks 40/40")
    require(all(
        counts[seat][key] == 0
        for seat in (0, 1)
        for key in ("model", "scripted", "other")
    ), "no model, scripted, or other move-source claims")
    truth = receipt["truth"]
    require(truth["status"] == "scripted_preseason", "scripted preseason truth status")
    require(truth["modelAttested"] is False, "model attestation stays false")
    require(truth["executionClaimsAttested"] is False, "execution claims stay unattested")
    require(truth["entrantIdentityAttested"] is False, "entrant identity stays self-declared")
    rendered_receipt = json.dumps(receipt, sort_keys=True)
    for fragment in ("stub:v1", "stub:v2", "response_sha256", "invalid_model_output"):
        require(fragment not in rendered_receipt, f"public receipt leaked raw value {fragment!r}")

    teaser = next(row for row in dataset["teasers"] if row["receiptId"] == receipt["receiptId"])
    teaser_keys = {key.casefold() for key, _value in _walk(teaser)}
    require(not any(word in key
                    for key in teaser_keys
                    for word in ("result", "winner", "score", "margin")),
            "Ten Fronts teaser omits reveal fields")
    clip = next(row for row in dataset["clips"] if row["receiptId"] == receipt["receiptId"])
    require(clip["kind"] == "final_accepted_move", "bounded final-move clip contract")
    require(clip["boundedRecordCount"] == 1 and clip["rawMoveOmitted"] is True,
            "clip stays one bounded record without the raw move")
    played = {row["receiptId"]: row for row in dataset["interactionManifest"]["playedArtifacts"]}
    evidence = played[receipt["receiptId"]]
    require(evidence["fixtureStatus"] == "played", "played interaction tuple present")
    require(evidence["publicationEvidence"]["sourceFileSha256"] == entry["sourceFileSha256"],
            "interaction file parity for Ten Fronts")
    require(evidence["publicationEvidence"]["sourceCountsDigest"] ==
            source_counts_digest(receipt["moveSourceClaims"]), "interaction count parity")
    parity_row = next(row for row in source_manifest["entries"]
                      if row["receiptId"] == receipt["receiptId"])
    require(parity_row["sourceChainHead"] == entry["sourceChainHead"], "chain-head parity")
    require(parity_row["sourceFileSha256"] == entry["sourceFileSha256"], "file-hash parity")
    require(parity_row["sourceCounts"]["fallback"] == 80, "aggregate fallback count parity")

    rivalry = next(row for row in dataset["rivalries"] if row["competition"] == "ten_fronts")
    require(rivalry["meetingCount"] == 1, "one Ten Fronts meeting forms its own rivalry")
    require(rivalry["history"][0]["runback"]["status"] == "unplayed_challenge",
            "Ten Fronts runback stays an unplayed descriptor")
    require(rivalry["history"][0]["runback"]["seed"] == 7001, "runback seed is parent+1")
    fantasy_rivalry = next(row for row in dataset["rivalries"]
                           if row["competition"] == "agentwars-fantasy")
    require(fantasy_rivalry["meetingCount"] == 6, "six-meeting fantasy rivalry unchanged")
    require(len(dataset["futureFixtures"]) == 3, "three closed future fixtures unchanged")
    require(all(row["prediction"]["status"] == "closed_proposed_not_activated"
                for row in dataset["futureFixtures"]), "predictions remain closed")
    for title_name in ("redraftCrown", "dynastyThrone"):
        title = dataset["titles"][title_name]
        require(title["holderEntrantId"] is not None, f"{title_name} custody unchanged")
        require(receipt["receiptId"] not in title["basisReceiptIds"],
                f"{title_name} basis excludes the Ten Fronts reference")

    with tempfile.TemporaryDirectory(prefix="agentwars-ten-fronts-refusal-") as work:
        bad = os.path.join(work, "malformed-scores.jsonl")

        def break_scores(records):
            states = [row for row in records if row.get("kind") == "state"]
            states[-1]["body"]["state"]["scores"] = [319]
            states[-1]["body"]["state_digest"] = digest(states[-1]["body"]["state"])

        _rechained_copy(TEN_FRONTS, bad, break_scores)
        try:
            project_receipt(bad)
        except PublicationError:
            pass
        else:
            raise AssertionError("malformed Ten Fronts scores must refuse publication")

        original_verifier = projection_module.verify_with_snapshot

        def bypass_replay(path):
            with open(path, "r", encoding="utf-8") as handle:
                records = [json.loads(line) for line in handle]
            return {
                "effective_verdict": "PASS",
                "verdict": "PASS",
                "engine_digest_match": True,
                "verifier_snapshot_match": True,
                "engine_digest_recorded": "a" * 64,
                "chain_head": records[-1]["hash"],
            }

        malformed_digest_report = bypass_replay(bad)
        malformed_digest_report["engine_digest_recorded"] = "not-a-digest"
        require(
            projection_module._exact_pass(malformed_digest_report, 0) is False,
            "publication gate rejects malformed verifier engine digests",
        )

        projection_module.verify_with_snapshot = bypass_replay
        try:
            expect_publication_error(lambda: project_receipt(bad), "exactly two non-negative")
        finally:
            projection_module.verify_with_snapshot = original_verifier


def main():
    check_match_ids_fail_before_paths()
    check_verifier_exit_contract()
    check_deterministic_atomic_artifact()
    check_allowlist_and_parity()
    check_hostile_paths_no_outside_writes()
    check_duplicate_fixture_distinct_receipts()
    check_ten_fronts_score_extractor()
    check_ten_fronts_public_source()
    check_public_safety_and_product_mechanics()
    print("AgentWars public product contracts: PASS")
    print("8 approved receipts / 3 closed future fixtures / fail-closed replay + publication gates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
