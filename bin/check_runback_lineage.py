#!/usr/bin/env python3
"""Adversarial checks for replay-bound AgentBattles runback lineage v1.

Positive acceptances come from real arena transcripts. Hand-authored
receipt-shaped JSON appears only as hostile input and must never enter lineage.
"""

from __future__ import annotations

import copy
import glob
import json
import os
import shutil
import sys
import tempfile
from types import SimpleNamespace
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from arena.canonical import digest
from arena.match import run_match
from entrants.backends import execution_claim_for_backend
from publishing.product import _runback as public_runback
from publishing.projection import project_receipt
from publishing import runback as runback_module
from publishing.runback import (
    RunbackError,
    accept_runback,
    build_lineage,
    compile_runback_surface_admission,
    empty_lineage_state,
    issue_runback,
    validate_acceptance,
    validate_challenge,
    validate_lineage_state,
    validate_surface_shape,
)

PACKAGE_ROOT = os.path.join(ROOT, "publishing", "agentwars-public-v1")
PUBLIC_ROOT = os.path.join(PACKAGE_ROOT, "public")
RECEIPT_GLOB = os.path.join(PUBLIC_ROOT, "receipts", "*.json")
MAX_SEED = 2_147_483_647
checks = 0


def require(condition, message):
    global checks
    checks += 1
    if not condition:
        raise AssertionError(message)


def refuses(callback, contains=None):
    global checks
    checks += 1
    try:
        callback()
    except RunbackError as error:
        if contains is not None and contains not in str(error):
            raise AssertionError(f"expected {contains!r} in {error!r}") from error
        return
    raise AssertionError("expected RunbackError")


def manifest(name, script):
    backend = "stub:v1"
    return {
        "name": name,
        "cmd": [sys.executable, os.path.join(ROOT, "entrants", script), "--backend", backend],
        "env": [],
        "claimed_model": backend,
        "execution_claim": execution_claim_for_backend(backend),
    }


NAIVE = manifest("naive", "naive_harness.py")
SOLVER = manifest("solver", "solver_harness.py")


def real_receipt(work, *, seed, entrants, label):
    result = run_match(
        game_name="nim",
        seed=seed,
        entrants=entrants,
        out_dir=os.path.join(work, label),
        match_id=f"runback-{label}-{seed}",
    )
    receipt, _records = project_receipt(result["transcript"])
    return receipt, result["transcript"]


def proof(acceptance, challenge, parent, parent_path, child, child_path):
    return {
        "acceptance": acceptance,
        "challenge": challenge,
        "parentReceipt": parent,
        "parentTranscriptPath": parent_path,
        "childReceipt": child,
        "childTranscriptPath": child_path,
    }


def reseal_receipt(receipt):
    receipt["shareManifestHash"] = digest(
        {
            "schemaVersion": "agentwars.share-manifest.v1",
            "receiptId": receipt["receiptId"],
            "fixtureId": receipt["fixtureId"],
            "entrants": receipt["entrants"],
            "outcome": receipt["outcome"],
            "story": receipt["story"],
            "truth": receipt["truth"],
            "sourceParity": receipt["sourceParity"],
        }
    )
    receipt.pop("projectionDigest", None)
    receipt["projectionDigest"] = digest(receipt)
    return receipt


def reseal_acceptance(acceptance):
    acceptance.pop("acceptanceDigest", None)
    acceptance["acceptanceDigest"] = digest(acceptance)
    return acceptance


class HostileReceipt(dict):
    """Container subclasses must not execute behavior inside the trust boundary."""

    def __getitem__(self, key):
        if key == "game":
            return {"name": "fantasy_redraft", "version": "hostile", "format": "redraft"}
        return super().__getitem__(key)


def load_public_receipts():
    rows = []
    for path in sorted(glob.glob(RECEIPT_GLOB)):
        with open(path, "r", encoding="utf-8") as handle:
            receipt = json.load(handle)
        transcript = os.path.join(
            PACKAGE_ROOT, *receipt["transcript"]["relativePath"].split("/")
        )
        rows.append((receipt, transcript))
    return rows


def main():
    public = load_public_receipts()
    require(len(public) == 8, "the reviewed public corpus still contains eight receipts")

    print("[1] public challenges replay independently and preserve product compatibility")
    for receipt, transcript in public:
        challenge = issue_runback(receipt, transcript_path=transcript)
        require(
            challenge == issue_runback(copy.deepcopy(receipt), transcript_path=transcript),
            "challenge derivation is deterministic",
        )
        require(
            validate_challenge(challenge, receipt, transcript_path=transcript) == challenge,
            "challenge revalidates from exact transcript bytes",
        )
        descriptor = public_runback(receipt)
        require(challenge["challengeId"] == descriptor["challengeId"], "public short id preserved")
        require(challenge["fixtureId"] == descriptor["fixtureId"], "public fixture id preserved")
        require(challenge["status"] == "unplayed_challenge", "challenge remains unplayed")
        require(challenge["truth"]["resultClaimed"] is False, "challenge claims no result")
        require(
            challenge["challengeDigest"]
            == digest({key: value for key, value in challenge.items() if key != "challengeDigest"}),
            "full challenge digest binds exact challenge bytes",
        )

    work = tempfile.mkdtemp(prefix="agentbattles-runback-check-")
    try:
        print("[2] real parent, child, and grandchild transcripts form one rivalry")
        parent, parent_path = real_receipt(
            work, seed=1000, entrants=[NAIVE, SOLVER], label="parent"
        )
        child, child_path = real_receipt(
            work, seed=1001, entrants=[SOLVER, NAIVE], label="child"
        )
        grandchild, grandchild_path = real_receipt(
            work, seed=1002, entrants=[NAIVE, SOLVER], label="grandchild"
        )
        challenge = issue_runback(parent, transcript_path=parent_path)
        acceptance = accept_runback(
            challenge,
            parent,
            child,
            parent_transcript_path=parent_path,
            child_transcript_path=child_path,
        )
        require(validate_acceptance(acceptance) == acceptance, "acceptance validates")
        require(acceptance["evidence"]["method"] == "independent_transcript_reprojection", "replay evidence named")
        require(acceptance["truth"]["modelAttested"] is False, "no model attestation")
        first_proof = proof(acceptance, challenge, parent, parent_path, child, child_path)
        default_surface = compile_runback_surface_admission(parent)
        require(default_surface["status"] == "unplayed_challenge", "surface defaults unplayed")
        pending_surface = compile_runback_surface_admission(
            parent,
            parent_transcript_path=parent_path,
            proof=first_proof,
            previous_state=empty_lineage_state(),
        )
        require(
            pending_surface["status"]
            == "completed_runback_pending_registry_commit",
            "replay proof remains pending an authoritative registry commit",
        )
        require(
            validate_surface_shape(pending_surface) == pending_surface,
            "pending surface shape validates after exact proof replay",
        )
        require(
            pending_surface["acceptedEdge"]["childReceiptId"] == child["receiptId"],
            "pending surface binds the exact child",
        )

        next_challenge = issue_runback(child, transcript_path=child_path)
        second = accept_runback(
            next_challenge,
            child,
            grandchild,
            parent_transcript_path=child_path,
            child_transcript_path=grandchild_path,
        )
        second_proof = proof(
            second, next_challenge, child, child_path, grandchild, grandchild_path
        )
        lineage = build_lineage(
            [first_proof, second_proof], previous_state=empty_lineage_state()
        )
        require(
            lineage
            == build_lineage(
                [second_proof, first_proof], previous_state=empty_lineage_state()
            ),
            "proof ordering cannot change lineage",
        )
        require(lineage["basis"]["acceptanceCount"] == 2, "two edges counted")
        require(lineage["basis"]["receiptCount"] == 3, "three receipts counted")
        require(lineage["basis"]["chains"][0]["completedRunbacks"] == 2, "two-edge chain")
        require(
            lineage["basis"]["replayWorkload"]["independentReplayCount"] == 3,
            "shared child transcript is replayed once per lineage build",
        )
        require(lineage["basis"]["ratingEmitted"] is False, "no rating emitted")

        print("[3] receipt labels and self-digests cannot replace transcript replay")
        refuses(
            lambda: issue_runback(parent, transcript_path=os.path.join(work, "missing.jsonl")),
            "could not be read",
        )
        refuses(
            lambda: issue_runback(HostileReceipt(parent), transcript_path=parent_path),
            "exact built-in JSON values",
        )
        parent_entry = os.lstat(parent_path)
        raced_entry = SimpleNamespace(
            st_mode=parent_entry.st_mode,
            st_dev=parent_entry.st_dev,
            st_ino=parent_entry.st_ino + 1,
            st_size=parent_entry.st_size,
            st_mtime_ns=parent_entry.st_mtime_ns,
        )
        with mock.patch.object(runback_module.os, "lstat", return_value=raced_entry):
            refuses(
                lambda: issue_runback(parent, transcript_path=parent_path),
                "changed before",
            )
        leaked_roots = []

        def cleanup_failure(path):
            leaked_roots.append(path)
            raise OSError("synthetic cleanup refusal")

        with mock.patch.object(runback_module.shutil, "rmtree", side_effect=cleanup_failure):
            refuses(
                lambda: issue_runback(parent, transcript_path=parent_path),
                "temporary transcript cleanup failed",
            )
        for leaked_root in leaked_roots:
            shutil.rmtree(leaked_root, ignore_errors=True)
        with mock.patch.object(runback_module, "MAX_TRANSCRIPT_BYTES", 1):
            refuses(
                lambda: issue_runback(parent, transcript_path=parent_path),
                "transcript exceeds its byte limit",
            )
        altered_path = os.path.join(work, "altered.jsonl")
        shutil.copyfile(parent_path, altered_path)
        with open(altered_path, "ab") as handle:
            handle.write(b"\n")
        refuses(
            lambda: issue_runback(parent, transcript_path=altered_path),
            "differs from independent",
        )
        self_authored = copy.deepcopy(parent)
        self_authored["story"]["headline"] = "Self-authored PASS is not replay authority"
        reseal_receipt(self_authored)
        refuses(
            lambda: issue_runback(self_authored, transcript_path=parent_path),
            "differs from independent",
        )
        failed_label = copy.deepcopy(parent)
        failed_label["verification"]["replayVerdict"] = "FAIL"
        reseal_receipt(failed_label)
        refuses(lambda: issue_runback(failed_label, transcript_path=parent_path), "replayVerdict")
        unknown = copy.deepcopy(parent)
        unknown["hostileFloat"] = 0.1
        refuses(
            lambda: issue_runback(unknown, transcript_path=parent_path),
            "exact built-in JSON values",
        )

        print("[4] a stored acceptance is data; proof-bundle replay is authority")
        forged = copy.deepcopy(acceptance)
        current = {
            forged["comparison"]["parent"]["winnerEntrantId"],
            forged["comparison"]["child"]["winnerEntrantId"],
        }
        replacement = None if current != {None} else forged["seats"][0]["entrantId"]
        forged["comparison"]["parent"]["winnerEntrantId"] = replacement
        forged["comparison"]["child"]["winnerEntrantId"] = replacement
        forged["comparison"]["winnerChanged"] = False
        reseal_acceptance(forged)
        require(validate_acceptance(forged) == forged, "self-consistent stored shape validates")
        forged_proof = proof(forged, challenge, parent, parent_path, child, child_path)
        refuses(
            lambda: build_lineage(
                [forged_proof], previous_state=empty_lineage_state()
            ),
            "differs from transcript-derived",
        )
        hostile_acceptance = copy.deepcopy(acceptance)
        hostile_acceptance["unexpected"] = True
        refuses(lambda: validate_acceptance(hostile_acceptance), "unknown")
        hostile_acceptance = copy.deepcopy(acceptance)
        hostile_acceptance["truth"]["modelAttested"] = True
        reseal_acceptance(hostile_acceptance)
        refuses(lambda: validate_acceptance(hostile_acceptance), "modelAttested")

        print("[5] exact fixture and rivalry boundaries reject laundering")
        wrong_challenge = copy.deepcopy(challenge)
        wrong_challenge["seed"] += 1
        wrong_challenge["challengeDigest"] = digest(
            {key: value for key, value in wrong_challenge.items() if key != "challengeDigest"}
        )
        refuses(
            lambda: accept_runback(
                wrong_challenge,
                parent,
                child,
                parent_transcript_path=parent_path,
                child_transcript_path=child_path,
            ),
            "parent-derived",
        )
        unrelated_child = copy.deepcopy(child)
        unrelated_child["game"]["name"] = "fantasy_redraft"
        reseal_receipt(unrelated_child)
        refuses(
            lambda: accept_runback(
                challenge,
                parent,
                unrelated_child,
                parent_transcript_path=parent_path,
                child_transcript_path=child_path,
            ),
            "fixture id",
        )
        swapped_proof = copy.deepcopy(first_proof)
        swapped_proof["childReceipt"] = grandchild
        swapped_proof["childTranscriptPath"] = grandchild_path
        refuses(
            lambda: build_lineage(
                [swapped_proof], previous_state=empty_lineage_state()
            ),
            "proposed fixture",
        )

        print("[6] full-digest consumption, duplication, and bounds fail closed")
        one = build_lineage([first_proof], previous_state=empty_lineage_state())
        require(one["basis"]["acceptanceCount"] == 1, "one valid proof admitted")
        next_state = one["basis"]["nextState"]
        require(validate_lineage_state(next_state) == next_state, "next state validates")
        incremental = build_lineage([second_proof], previous_state=next_state)
        require(
            incremental["basis"]["chains"][0]["previousHeadReceiptId"]
            == child["receiptId"],
            "next delta extends the prior head",
        )
        require(
            incremental["basis"]["chains"][0]["completedRunbacks"] == 2,
            "cumulative runback count advances",
        )
        refuses(
            lambda: build_lineage(
                [first_proof, first_proof], previous_state=empty_lineage_state()
            ),
            "repeats",
        )
        refuses(
            lambda: build_lineage(
                [first_proof],
                previous_state=next_state,
            ),
            "already consumed",
        )
        wrong_head_state = empty_lineage_state()
        wrong_head_state["consumedChallenges"] = [
            {
                "challengeId": "challenge_dddddddddddddddd",
                "challengeDigest": "d" * 64,
            }
        ]
        wrong_head_state["rivalries"] = [
            {
                "rivalryId": acceptance["rivalryId"],
                "rootReceiptId": "e" * 64,
                "headReceiptId": "f" * 64,
                "receiptIds": ["e" * 64, "f" * 64],
                "challengeDigests": ["d" * 64],
                "completedRunbacks": 1,
            }
        ]
        wrong_head_state["receiptProjections"] = [
            {"receiptId": "e" * 64, "projectionDigest": "a" * 64},
            {"receiptId": "f" * 64, "projectionDigest": "b" * 64},
        ]
        refuses(
            lambda: build_lineage([first_proof], previous_state=wrong_head_state),
            "prior rivalry head",
        )
        short_collision_state = empty_lineage_state()
        short_collision_state["consumedChallenges"] = [
            {
                "challengeId": challenge["challengeId"],
                "challengeDigest": "f" * 64,
            }
        ]
        short_collision_state["rivalries"] = [
            {
                "rivalryId": "c" * 64,
                "rootReceiptId": "a" * 64,
                "headReceiptId": "b" * 64,
                "receiptIds": ["a" * 64, "b" * 64],
                "challengeDigests": ["f" * 64],
                "completedRunbacks": 1,
            }
        ]
        short_collision_state["receiptProjections"] = [
            {"receiptId": "a" * 64, "projectionDigest": "c" * 64},
            {"receiptId": "b" * 64, "projectionDigest": "d" * 64},
        ]
        refuses(
            lambda: build_lineage([first_proof], previous_state=short_collision_state),
            "short challenge id collides",
        )
        unsorted_state = empty_lineage_state()
        unsorted_state["consumedChallenges"] = [
            {"challengeId": "challenge_2222222222222222", "challengeDigest": "2" * 64},
            {"challengeId": "challenge_1111111111111111", "challengeDigest": "1" * 64},
        ]
        refuses(
            lambda: build_lineage([], previous_state=unsorted_state),
            "unique and sorted by full digest",
        )
        duplicate_digest_state = empty_lineage_state()
        duplicate_digest_state["consumedChallenges"] = [
            {"challengeId": "challenge_1111111111111111", "challengeDigest": "1" * 64},
            {"challengeId": "challenge_2222222222222222", "challengeDigest": "1" * 64},
        ]
        refuses(
            lambda: validate_lineage_state(duplicate_digest_state),
            "unique and sorted by full digest",
        )
        orphan_state = copy.deepcopy(short_collision_state)
        orphan_state["receiptProjections"] = []
        refuses(
            lambda: validate_lineage_state(orphan_state),
            "equal the rivalry history receipts exactly",
        )
        extra_projection_state = empty_lineage_state()
        extra_projection_state["receiptProjections"] = [
            {"receiptId": "a" * 64, "projectionDigest": "b" * 64}
        ]
        refuses(
            lambda: validate_lineage_state(extra_projection_state),
            "equal the rivalry history receipts exactly",
        )
        impossible_count_state = copy.deepcopy(short_collision_state)
        impossible_count_state["rivalries"][0]["completedRunbacks"] = 2
        refuses(
            lambda: validate_lineage_state(impossible_count_state),
            "receipt chain length is inconsistent",
        )
        deeply_nested_state = empty_lineage_state()
        deeply_nested_state["nested"] = cursor = []
        for _ in range(70):
            child_list = []
            cursor.append(child_list)
            cursor = child_list
        refuses(
            lambda: validate_lineage_state(deeply_nested_state),
            "maximum JSON nesting depth",
        )
        refuses(
            lambda: build_lineage(
                [first_proof] * 129, previous_state=empty_lineage_state()
            ),
            "bounded lineage",
        )
        with mock.patch.object(runback_module, "MAX_LINEAGE_REPLAY_BYTES", 1):
            refuses(
                lambda: build_lineage(
                    [first_proof], previous_state=empty_lineage_state()
                ),
                "replay-byte budget",
            )

        max_parent, max_parent_path = real_receipt(
            work, seed=MAX_SEED, entrants=[NAIVE, SOLVER], label="max-seed"
        )
        refuses(
            lambda: issue_runback(max_parent, transcript_path=max_parent_path),
            "bounded next-seed",
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)

    print(f"PASS: {checks} replay-bound AgentBattles runback-lineage checks")
    print("8 public receipts / real two-edge chain / forged receipts and acceptances rejected")


if __name__ == "__main__":
    main()
