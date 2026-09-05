#!/usr/bin/env python3
"""Adversarial self-check for the declarative BuildWars build-off kernel."""

from __future__ import annotations

import copy
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from buildwars.contracts import (  # noqa: E402
    BuildWarsContractError,
    candidate_projection,
    canonical_bytes,
    decode_strict,
    digest,
    seal_buildoff,
    validate_challenge,
    validate_entry,
    validate_judgment,
    validate_receipt,
    verify_receipt,
)


CHECKS = 0


def check(condition, label):
    global CHECKS
    if not condition:
        raise AssertionError(label)
    CHECKS += 1
    print(f"PASS {label}")


def expect_refusal(fn, label, fragment=None):
    global CHECKS
    try:
        fn()
    except BuildWarsContractError as error:
        if fragment is not None and fragment.lower() not in str(error).lower():
            raise AssertionError(f"{label}: unexpected refusal {error}") from error
        CHECKS += 1
        print(f"PASS {label}")
        return
    raise AssertionError(f"{label}: hostile input was accepted")


def with_digest(core, field):
    return {**core, field: digest(core)}


def fixture():
    rubric_core = {
        "schema": "buildwars.rubric.v1",
        "version": "1.0.0",
        "criteria": [
            {"criterionId": "correctness", "label": "Correctness", "maxPoints": 60},
            {"criterionId": "quality", "label": "Quality", "maxPoints": 40},
        ],
    }
    challenge_core = {
        "schema": "buildwars.challenge.v1",
        "challengeId": "bwc1_" + "1" * 24,
        "version": "1.0.0",
        "title": "Deterministic landing page build-off",
        "brief": {
            "mediaType": "text/markdown",
            "canonicalization": "sha256-bytes.v1",
            "sha256": "a" * 64,
        },
        "fixture": {
            "mediaType": "application/zip",
            "canonicalization": "zip-store-path-sorted.v1",
            "sha256": "b" * 64,
        },
        "matchupClasses": ["builder_vs_agent", "builder_vs_builder"],
        "entryLimit": 8,
        "rubric": with_digest(rubric_core, "rubricDigest"),
        "executionPolicy": "declarative_evidence_only",
        "publicationStatus": "reviewed_candidate_not_public",
    }
    challenge = with_digest(challenge_core, "challengeDigest")

    def entry(index, kind, participant_ref, points_seed):
        core = {
            "schema": "buildwars.entry.v1",
            "entryId": "bwe1_" + str(index) * 24,
            "challengeId": challenge["challengeId"],
            "challengeVersion": challenge["version"],
            "participant": {"kind": kind, "ref": participant_ref, "version": "1.0.0"},
            "source": {
                "mediaType": "application/vnd.git-tree",
                "canonicalization": "git-tree.v1",
                "sha256": format(points_seed, "064x"),
            },
            "artifact": {
                "mediaType": "application/zip",
                "canonicalization": "zip-store-path-sorted.v1",
                "sha256": format(points_seed + 10, "064x"),
            },
            "declarations": {
                "agentRefs": [f"agent:{index}"],
                "harnessRefs": [f"harness:{index}"],
                "modelClaims": [f"model:declared-{index}"],
                "providerClaims": [f"provider:declared-{index}"],
                "toolIds": ["tool:builderwars"],
            },
            "evidence": {
                "artifactManifestSha256": format(points_seed + 20, "064x"),
                "buildReceiptSha256": format(points_seed + 30, "064x"),
                "environmentSha256": format(points_seed + 40, "064x"),
                "testReceiptSha256": format(points_seed + 50, "064x"),
                "reproductionStatus": "customer_supplied_unverified",
            },
            "submissionStatus": "submitted_unreviewed",
            "publicationStatus": "not_reviewed_not_public",
        }
        return with_digest(core, "entryDigest")

    entries = [
        entry(2, "agent", "agent:alpha", 101),
        entry(3, "builder", "builder:beta", 202),
    ]

    def judgment(index, entry_value, correctness, quality):
        scores = [
            {
                "criterionId": "correctness",
                "points": correctness,
                "evidenceDigests": [entry_value["evidence"]["testReceiptSha256"]],
            },
            {
                "criterionId": "quality",
                "points": quality,
                "evidenceDigests": [entry_value["artifact"]["sha256"]],
            },
        ]
        core = {
            "schema": "buildwars.judgment.v1",
            "judgmentId": "bwj1_" + str(index) * 24,
            "challengeDigest": challenge["challengeDigest"],
            "entryDigest": entry_value["entryDigest"],
            "rubricDigest": challenge["rubric"]["rubricDigest"],
            "reviewerRef": "reviewer:offline-candidate",
            "reviewerVersion": "1.0.0",
            "reviewEvidenceClass": "unattested_offline_review",
            "criteria": scores,
            "totalPoints": correctness + quality,
            "decisionStatus": "scored_candidate_not_public",
        }
        return with_digest(core, "judgmentDigest")

    judgments = [judgment(4, entries[0], 55, 35), judgment(5, entries[1], 50, 30)]
    return challenge, entries, judgments


def main():
    challenge, entries, judgments = fixture()
    check(validate_challenge(challenge) == challenge, "challenge validates exactly")
    check(validate_entry(entries[0], challenge=challenge) == entries[0], "entry validates exactly")
    check(
        validate_judgment(judgments[0], challenge=challenge, entry=entries[0]) == judgments[0],
        "judgment validates exactly",
    )
    receipt = seal_buildoff(challenge, entries, judgments)
    check(receipt["candidateWinnerEntryIds"] == [entries[0]["entryId"]], "scores derive one candidate leader")
    check(receipt["evidenceClass"] == "artifact_review", "receipt names artifact-review evidence")
    check(
        receipt["rankingEligible"] is receipt["titleEligible"] is receipt["agentWarsRatingEligible"] is False,
        "artifact judgment cannot create a rank, title, or AgentWars rating",
    )
    check(
        all(
            receipt[field] is False
            for field in (
                "modelAttested",
                "providerAttested",
                "executionAttested",
                "reviewerIdentityAttested",
            )
        ),
        "declarations never become attestations",
    )
    check(verify_receipt(receipt, challenge=challenge, entries=entries, judgments=judgments) == receipt, "receipt recomputes from exact inputs")
    check(validate_receipt(receipt) == receipt, "standalone receipt shape and outcome validate")
    check(
        seal_buildoff(challenge, list(reversed(entries)), list(reversed(judgments))) == receipt,
        "receipt is input-order independent",
    )
    tied_judgments = copy.deepcopy(judgments)
    tied_judgments[1]["criteria"][0]["points"] = 55
    tied_judgments[1]["criteria"][1]["points"] = 35
    tied_judgments[1]["totalPoints"] = 90
    tied_judgments[1]["judgmentDigest"] = digest(
        {key: value for key, value in tied_judgments[1].items() if key != "judgmentDigest"}
    )
    tied_receipt = seal_buildoff(challenge, entries, tied_judgments)
    check(tied_receipt["tie"] is True, "equal top scores derive a tie")
    check(
        tied_receipt["candidateWinnerEntryIds"] == sorted(entry["entryId"] for entry in entries),
        "tied receipt preserves every candidate winner deterministically",
    )
    tied_projection = candidate_projection(tied_receipt)
    check(
        tied_projection["tie"] is True
        and tied_projection["candidateWinnerEntryIds"] == tied_receipt["candidateWinnerEntryIds"],
        "private candidate projection preserves the derived tie",
    )
    projection = candidate_projection(receipt)
    check(projection["projectionStatus"] == "private_candidate_not_public", "projection stays private candidate")
    check(projection["shareEligible"] is False, "candidate projection cannot be shared as a result")
    check(
        not any(key in projection for key in ("source", "artifact", "modelClaims", "providerClaims")),
        "candidate projection omits private or unverified entry claims",
    )
    check(
        decode_strict(canonical_bytes(challenge)) == challenge,
        "canonical challenge bytes round-trip through strict JSON",
    )

    hostile = copy.deepcopy(challenge)
    hostile["command"] = "python untrusted.py"
    expect_refusal(lambda: validate_challenge(hostile), "arbitrary command field is rejected", "unknown")
    hostile = copy.deepcopy(challenge)
    hostile["executionPolicy"] = "run_submitted_code"
    hostile["challengeDigest"] = digest({k: v for k, v in hostile.items() if k != "challengeDigest"})
    expect_refusal(lambda: validate_challenge(hostile), "executing challenge policy is rejected", "non-executing")
    hostile = copy.deepcopy(challenge)
    hostile["publicationStatus"] = "public"
    hostile["challengeDigest"] = digest({k: v for k, v in hostile.items() if k != "challengeDigest"})
    expect_refusal(lambda: validate_challenge(hostile), "challenge cannot self-publish", "authority")
    hostile = copy.deepcopy(entries[0])
    hostile["artifact"]["sha256"] = "f" * 64
    expect_refusal(lambda: validate_entry(hostile, challenge=challenge), "entry digest binds artifact bytes", "digest")
    hostile = copy.deepcopy(entries[0])
    hostile["challengeVersion"] = "2.0.0"
    hostile["entryDigest"] = digest({k: v for k, v in hostile.items() if k != "entryDigest"})
    expect_refusal(lambda: validate_entry(hostile, challenge=challenge), "entry cannot cross challenge version", "bound")
    hostile = copy.deepcopy(entries[0])
    hostile["challengeId"] = "bwc1_" + "9" * 24
    hostile["entryDigest"] = digest({k: v for k, v in hostile.items() if k != "entryDigest"})
    expect_refusal(lambda: validate_entry(hostile, challenge=challenge), "entry cannot cross challenge id", "bound")
    hostile = copy.deepcopy(entries[0])
    hostile["title"] = "extra"
    expect_refusal(lambda: validate_entry(hostile, challenge=challenge), "entry rejects unexplained fields", "unknown")
    hostile = copy.deepcopy(judgments[0])
    hostile["criteria"][0]["points"] = 61
    hostile["totalPoints"] = 96
    hostile["judgmentDigest"] = digest({k: v for k, v in hostile.items() if k != "judgmentDigest"})
    expect_refusal(lambda: validate_judgment(hostile, challenge=challenge, entry=entries[0]), "rubric maximum is enforced", "integer")
    hostile = copy.deepcopy(judgments[0])
    hostile["totalPoints"] += 1
    hostile["judgmentDigest"] = digest({k: v for k, v in hostile.items() if k != "judgmentDigest"})
    expect_refusal(lambda: validate_judgment(hostile, challenge=challenge, entry=entries[0]), "editable total is rejected", "derived")
    hostile = copy.deepcopy(judgments[0])
    hostile["criteria"][0]["evidenceDigests"] = ["f" * 64]
    hostile["judgmentDigest"] = digest({k: v for k, v in hostile.items() if k != "judgmentDigest"})
    expect_refusal(lambda: validate_judgment(hostile, challenge=challenge, entry=entries[0]), "judgment evidence must belong to entry", "bound entry")
    hostile = copy.deepcopy(judgments[0])
    hostile["criteria"][0]["evidenceDigests"] = [format(item, "064x") for item in range(33)]
    hostile["judgmentDigest"] = digest({k: v for k, v in hostile.items() if k != "judgmentDigest"})
    expect_refusal(lambda: validate_judgment(hostile, challenge=challenge, entry=entries[0]), "judgment evidence list is bounded", "bounded")
    expect_refusal(
        lambda: seal_buildoff(challenge, entries, [judgments[0], judgments[0]]),
        "duplicate judgment cannot replace complete review",
        "distinct",
    )
    expect_refusal(
        lambda: seal_buildoff(challenge, entries[:1], judgments[:1]),
        "build-off requires at least two entries",
        "count",
    )
    expect_refusal(
        lambda: seal_buildoff(
            challenge,
            entries,
            [judgments[0], {**judgments[1], "entryDigest": "f" * 64}],
        ),
        "judgment cannot reference an unknown entry",
        "unknown",
    )
    duplicate_participant = copy.deepcopy(entries[1])
    duplicate_participant["participant"] = copy.deepcopy(entries[0]["participant"])
    duplicate_participant["entryDigest"] = digest({k: v for k, v in duplicate_participant.items() if k != "entryDigest"})
    duplicate_judgment = copy.deepcopy(judgments[1])
    duplicate_judgment["entryDigest"] = duplicate_participant["entryDigest"]
    duplicate_judgment["judgmentDigest"] = digest({k: v for k, v in duplicate_judgment.items() if k != "judgmentDigest"})
    expect_refusal(
        lambda: seal_buildoff(challenge, [entries[0], duplicate_participant], [judgments[0], duplicate_judgment]),
        "one participant version cannot occupy two entries",
        "participant",
    )
    hostile_receipt = copy.deepcopy(receipt)
    hostile_receipt["scores"][0]["totalPoints"] += 1
    expect_refusal(
        lambda: verify_receipt(hostile_receipt, challenge=challenge, entries=entries, judgments=judgments),
        "summary score tampering is rejected",
    )
    hostile_receipt = copy.deepcopy(receipt)
    hostile_receipt["rankingEligible"] = True
    core = {key: value for key, value in hostile_receipt.items() if key != "receiptId"}
    hostile_receipt["receiptId"] = digest(core)
    expect_refusal(lambda: candidate_projection(hostile_receipt), "projection rejects ranking escalation", "overstates")
    hostile_receipt = copy.deepcopy(receipt)
    hostile_receipt["scores"] = "editable-summary"
    core = {key: value for key, value in hostile_receipt.items() if key != "receiptId"}
    hostile_receipt["receiptId"] = digest(core)
    expect_refusal(lambda: candidate_projection(hostile_receipt), "projection rejects malformed score table", "table")
    hostile_receipt = copy.deepcopy(receipt)
    hostile_receipt["candidateWinnerEntryIds"] = [entries[1]["entryId"]]
    core = {key: value for key, value in hostile_receipt.items() if key != "receiptId"}
    hostile_receipt["receiptId"] = digest(core)
    expect_refusal(lambda: candidate_projection(hostile_receipt), "projection recomputes candidate leader", "follow")
    hostile_receipt = copy.deepcopy(receipt)
    hostile_receipt["tie"] = True
    core = {key: value for key, value in hostile_receipt.items() if key != "receiptId"}
    hostile_receipt["receiptId"] = digest(core)
    expect_refusal(lambda: candidate_projection(hostile_receipt), "projection recomputes tie status", "tie")
    hostile_receipt = copy.deepcopy(receipt)
    hostile_receipt["scores"] = list(reversed(hostile_receipt["scores"]))
    core = {key: value for key, value in hostile_receipt.items() if key != "receiptId"}
    hostile_receipt["receiptId"] = digest(core)
    expect_refusal(lambda: candidate_projection(hostile_receipt), "projection rejects unsorted score table", "sorted")
    hostile_receipt = copy.deepcopy(receipt)
    for field in (
        "rankingEligible",
        "titleEligible",
        "agentWarsRatingEligible",
        "modelAttested",
        "providerAttested",
        "executionAttested",
        "reviewerIdentityAttested",
    ):
        hostile_receipt[field] = 1
    core = {key: value for key, value in hostile_receipt.items() if key != "receiptId"}
    hostile_receipt["receiptId"] = digest(core)
    expect_refusal(lambda: validate_receipt(hostile_receipt), "integer one cannot impersonate boolean authority", "overstates")
    expect_refusal(lambda: validate_receipt(None), "non-object receipt is rejected")
    expect_refusal(
        lambda: decode_strict('{"schema":"x","schema":"y"}'),
        "duplicate JSON keys are rejected",
        "duplicate",
    )
    expect_refusal(lambda: decode_strict('{"score":1.5}'), "floating scores are rejected", "float")
    expect_refusal(
        lambda: decode_strict('{"padding":"' + ('x' * (256 * 1024)) + '"}'),
        "oversized encoded document is rejected",
        "oversized",
    )
    hostile = copy.deepcopy(challenge)
    hostile["title"] = "password=super-secret"
    hostile["challengeDigest"] = digest({k: v for k, v in hostile.items() if k != "challengeDigest"})
    expect_refusal(lambda: validate_challenge(hostile), "credential-shaped challenge text is rejected", "credential")
    hostile = copy.deepcopy(challenge)
    hostile["title"] = "surrogate-\ud800"
    expect_refusal(lambda: validate_challenge(hostile), "lone Unicode surrogate is rejected", "control")
    hostile = copy.deepcopy(challenge)
    hostile["matchupClasses"] = ["builder_vs_builder"]
    hostile["challengeDigest"] = digest({k: v for k, v in hostile.items() if k != "challengeDigest"})
    expect_refusal(
        lambda: seal_buildoff(hostile, entries, judgments),
        "participant kinds must match an admitted matchup class",
        "matchup",
    )

    print(f"BuildWars format: ALL CHECKS PASS ({CHECKS})")
    print("declarative only / artifact review / no execution / no publication / no cross-mode rating")
    print(json.dumps(projection, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
