#!/usr/bin/env python3
"""Adversarial checks for the sole pending-runback surface proof compiler."""

from __future__ import annotations

import copy
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
BIN = os.path.join(ROOT, "bin")
if BIN not in sys.path:
    sys.path.insert(0, BIN)

from arena.canonical import digest  # noqa: E402
from arena.match import run_match  # noqa: E402
from build_share_bundle import BundleError, build_manifest, write_bundle  # noqa: E402
from build_agentwars_runner_bundle import (  # noqa: E402
    _TEST_SOURCE_POLICY,
    build_bundle,
)
from entrants.backends import execution_claim_for_backend  # noqa: E402
import publishing.runback as runback_module  # noqa: E402
from publishing.product import (  # noqa: E402
    PublicationError,
    _require_publishable_runback_surfaces,
    _runback_surface as product_runback_surface,
)
from publishing.projection import project_receipt  # noqa: E402
from publishing.runback import (  # noqa: E402
    RunbackError,
    accept_runback,
    build_lineage,
    compile_runback_surface_admission,
    empty_lineage_state,
    issue_runback,
    require_same_surface_bytes,
    validate_surface_shape,
    verify_runback_surface_admission,
)
from verify_agentwars_runner_bundle import BUNDLE_FILENAME, BUNDLE_ROOT  # noqa: E402

checks = 0


def require(condition, message):
    global checks
    checks += 1
    if not condition:
        raise AssertionError(message)


def refuses(callback, *, contains=None, base=None, parent=None):
    global checks
    checks += 1
    try:
        callback()
    except (RunbackError, PublicationError, BundleError) as error:
        if contains is not None and contains not in str(error):
            raise AssertionError(f"expected {contains!r} in {error!r}") from error
    else:
        raise AssertionError("expected fail-closed runback surface refusal")
    if base is not None:
        require(
            compile_runback_surface_admission(parent) == base,
            "a failed candidate must not mutate the deterministic unplayed surface",
        )


def manifest(name, script):
    backend = "stub:v1"
    return {
        "name": name,
        "cmd": [
            sys.executable,
            os.path.join(ROOT, "entrants", script),
            "--backend",
            backend,
        ],
        "env": [],
        "claimed_model": backend,
        "execution_claim": execution_claim_for_backend(backend),
    }


NAIVE = manifest("naive", "naive_harness.py")
SOLVER = manifest("solver", "solver_harness.py")
THIRD = manifest("third", "naive_harness.py")


def real_receipt(work, *, seed, entrants, label):
    result = run_match(
        game_name="nim",
        seed=seed,
        entrants=entrants,
        out_dir=os.path.join(work, label),
        match_id=f"surface-{label}-{seed}",
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


def reseal_acceptance(acceptance):
    acceptance.pop("acceptanceDigest", None)
    acceptance["acceptanceDigest"] = digest(acceptance)
    return acceptance


def reseal_receipt(receipt, *, fixture=False):
    if fixture:
        receipt["fixtureId"] = digest(
            {
                "schemaVersion": "agentwars.fixture-identity.v1",
                "game": {
                    "name": receipt["game"]["name"],
                    "version": receipt["game"]["version"],
                },
                "seed": receipt["seed"],
                "seats": [
                    {
                        "entrantId": row["entrantId"],
                        "harnessVersionId": row["harnessVersionId"],
                    }
                    for row in receipt["entrants"]
                ],
            }
        )
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


def reverse_objects(value):
    if type(value) is dict:
        return {key: reverse_objects(value[key]) for key in reversed(list(value))}
    if type(value) is list:
        return [reverse_objects(item) for item in value]
    return value


def synthetic_state(
    *, challenge_id, challenge_digest, rivalry_id, root_id, head_id, projections
):
    return {
        "schemaVersion": "agentbattles.runback-lineage-state.v1",
        "consumedChallenges": [
            {"challengeId": challenge_id, "challengeDigest": challenge_digest}
        ],
        "rivalries": [
            {
                "rivalryId": rivalry_id,
                "rootReceiptId": root_id,
                "headReceiptId": head_id,
                "receiptIds": [root_id, head_id],
                "challengeDigests": [challenge_digest],
                "completedRunbacks": 1,
            }
        ],
        "receiptProjections": [
            {"receiptId": receipt_id, "projectionDigest": projection_digest}
            for receipt_id, projection_digest in sorted(projections.items())
        ],
    }


def main():
    work = tempfile.mkdtemp(prefix="agentbattles-surface-check-")
    leaked_roots = []
    try:
        parent, parent_path = real_receipt(
            work, seed=3100, entrants=[NAIVE, SOLVER], label="parent"
        )
        child, child_path = real_receipt(
            work, seed=3101, entrants=[SOLVER, NAIVE], label="child"
        )
        grandchild, grandchild_path = real_receipt(
            work, seed=3102, entrants=[NAIVE, SOLVER], label="grandchild"
        )
        fork_child, fork_child_path = real_receipt(
            work, seed=3101, entrants=[SOLVER, NAIVE], label="fork-child"
        )
        foreign_parent, foreign_parent_path = real_receipt(
            work, seed=4100, entrants=[NAIVE, THIRD], label="foreign-parent"
        )
        foreign_child, foreign_child_path = real_receipt(
            work, seed=4101, entrants=[THIRD, NAIVE], label="foreign-child"
        )

        challenge = issue_runback(parent, transcript_path=parent_path)
        acceptance = accept_runback(
            challenge,
            parent,
            child,
            parent_transcript_path=parent_path,
            child_transcript_path=child_path,
        )
        first_proof = proof(
            acceptance, challenge, parent, parent_path, child, child_path
        )
        next_challenge = issue_runback(child, transcript_path=child_path)
        second_acceptance = accept_runback(
            next_challenge,
            child,
            grandchild,
            parent_transcript_path=child_path,
            child_transcript_path=grandchild_path,
        )
        second_proof = proof(
            second_acceptance,
            next_challenge,
            child,
            child_path,
            grandchild,
            grandchild_path,
        )
        fork_acceptance = accept_runback(
            challenge,
            parent,
            fork_child,
            parent_transcript_path=parent_path,
            child_transcript_path=fork_child_path,
        )
        fork_proof = proof(
            fork_acceptance,
            challenge,
            parent,
            parent_path,
            fork_child,
            fork_child_path,
        )
        foreign_challenge = issue_runback(
            foreign_parent, transcript_path=foreign_parent_path
        )
        foreign_acceptance = accept_runback(
            foreign_challenge,
            foreign_parent,
            foreign_child,
            parent_transcript_path=foreign_parent_path,
            child_transcript_path=foreign_child_path,
        )
        foreign_proof = proof(
            foreign_acceptance,
            foreign_challenge,
            foreign_parent,
            foreign_parent_path,
            foreign_child,
            foreign_child_path,
        )

        print("[1] default is deterministic unplayed; exact proof compiles one edge")
        base = compile_runback_surface_admission(parent)
        require(base["status"] == "unplayed_challenge", "default remains unplayed")
        require(base["acceptedEdge"] is None, "default contains no accepted edge")
        require(validate_surface_shape(base) == base, "default surface shape validates")
        pending = compile_runback_surface_admission(
            parent,
            parent_transcript_path=parent_path,
            proof=first_proof,
            previous_state=empty_lineage_state(),
        )
        require(
            pending["status"] == "completed_runback_pending_registry_commit",
            "exact replay proof remains pending registry commit",
        )
        require(
            pending["acceptedEdge"]["acceptanceDigest"]
            == acceptance["acceptanceDigest"],
            "surface pins the stored transcript-derived acceptance",
        )
        require(
            pending["lineage"]["headReceiptId"] == child["receiptId"],
            "surface pins the exact child head",
        )
        require(
            pending["lineage"]["externalCompareAndSwapRequired"] is True
            and pending["lineage"]["externalCompareAndSwapPerformed"] is False,
            "local compiler explicitly leaves external CAS to the publisher",
        )
        require(
            compile_runback_surface_admission(
                reverse_objects(parent),
                parent_transcript_path=parent_path,
                proof=reverse_objects(first_proof),
                previous_state=reverse_objects(empty_lineage_state()),
            )
            == pending,
            "input object ordering cannot change admission bytes",
        )
        require(
            verify_runback_surface_admission(
                pending,
                parent,
                parent_transcript_path=parent_path,
                proof=first_proof,
                previous_state=empty_lineage_state(),
            )
            == pending,
            "proof verifier recompiles and accepts exact candidate bytes",
        )

        resealed_candidate = copy.deepcopy(pending)
        resealed_candidate["lineage"]["nextStateDigest"] = "e" * 64
        resealed_candidate.pop("admissionDigest")
        resealed_candidate["admissionDigest"] = digest(resealed_candidate)
        require(
            validate_surface_shape(resealed_candidate) == resealed_candidate,
            "self-authored resealed candidate can satisfy shape and self-digest only",
        )
        refuses(
            lambda: verify_runback_surface_admission(
                resealed_candidate,
                parent,
                parent_transcript_path=parent_path,
                proof=first_proof,
                previous_state=empty_lineage_state(),
            ),
            contains="recompilation",
            base=base,
            parent=parent,
        )

        print("[2] product and share consume the same compiler projection")
        product = product_runback_surface(
            parent,
            transcript_path=parent_path,
            proof=first_proof,
            previous_state=empty_lineage_state(),
        )
        share = build_manifest(
            parent_path,
            runback_proof=first_proof,
            previous_lineage_state=empty_lineage_state(),
        )["rivalry"]["runbackSurface"]
        require(product == share == pending, "product/share proof projections are byte-equal")
        require_same_surface_bytes(product, share)
        fork_surface = product_runback_surface(
            parent,
            transcript_path=parent_path,
            proof=fork_proof,
            previous_state=empty_lineage_state(),
        )
        require(
            fork_surface["status"] == "completed_runback_pending_registry_commit"
            and fork_surface["lineage"]["previousStateDigest"]
            == pending["lineage"]["previousStateDigest"]
            and fork_surface["acceptedEdge"]["childReceiptId"]
            != pending["acceptedEdge"]["childReceiptId"],
            "sibling proofs from one prior state are distinct local pending candidates",
        )
        for sibling in (pending, fork_surface):
            refuses(
                lambda sibling=sibling: _require_publishable_runback_surfaces(
                    {"rivalries": [{"history": [{"runbackSurface": sibling}]}]}
                ),
                contains="cannot be published",
                base=base,
                parent=parent,
            )
        refuses(
            lambda: require_same_surface_bytes(product, fork_surface),
            contains="disagree",
            base=base,
            parent=parent,
        )

        print("[3] forged completion and stored acceptance bytes never self-authorize")
        forged_completion = copy.deepcopy(first_proof)
        forged_completion["acceptance"]["status"] = "unplayed_challenge"
        reseal_acceptance(forged_completion["acceptance"])
        refuses(
            lambda: compile_runback_surface_admission(
                parent,
                parent_transcript_path=parent_path,
                proof=forged_completion,
                previous_state=empty_lineage_state(),
            ),
            base=base,
            parent=parent,
        )
        self_authored = copy.deepcopy(first_proof)
        self_authored["acceptance"]["comparison"]["parent"]["winnerEntrantId"] = None
        self_authored["acceptance"]["comparison"]["child"]["winnerEntrantId"] = None
        self_authored["acceptance"]["comparison"]["winnerChanged"] = False
        reseal_acceptance(self_authored["acceptance"])
        refuses(
            lambda: compile_runback_surface_admission(
                parent,
                parent_transcript_path=parent_path,
                proof=self_authored,
                previous_state=empty_lineage_state(),
            ),
            contains="transcript-derived",
            base=base,
            parent=parent,
        )
        forged_digest = copy.deepcopy(first_proof)
        forged_digest["acceptance"]["acceptanceDigest"] = "f" * 64
        refuses(
            lambda: compile_runback_surface_admission(
                parent,
                parent_transcript_path=parent_path,
                proof=forged_digest,
                previous_state=empty_lineage_state(),
            ),
            base=base,
            parent=parent,
        )

        print("[4] transcript and exact identity substitutions fail closed")
        altered_path = os.path.join(work, "altered-parent.jsonl")
        shutil.copyfile(parent_path, altered_path)
        with open(altered_path, "ab") as handle:
            handle.write(b"\n")
        refuses(
            lambda: compile_runback_surface_admission(
                parent,
                parent_transcript_path=altered_path,
                proof=first_proof,
                previous_state=empty_lineage_state(),
            ),
            base=base,
            parent=parent,
        )
        swapped_child = copy.deepcopy(first_proof)
        swapped_child["childReceipt"] = grandchild
        swapped_child["childTranscriptPath"] = grandchild_path
        refuses(
            lambda: compile_runback_surface_admission(
                parent,
                parent_transcript_path=parent_path,
                proof=swapped_child,
                previous_state=empty_lineage_state(),
            ),
            base=base,
            parent=parent,
        )
        wrong_challenge = copy.deepcopy(first_proof)
        wrong_challenge["challenge"]["seed"] += 1
        wrong_challenge["challenge"]["challengeDigest"] = digest(
            {
                key: value
                for key, value in wrong_challenge["challenge"].items()
                if key != "challengeDigest"
            }
        )
        refuses(
            lambda: compile_runback_surface_admission(
                parent,
                parent_transcript_path=parent_path,
                proof=wrong_challenge,
                previous_state=empty_lineage_state(),
            ),
            contains="challenge",
            base=base,
            parent=parent,
        )

        substitutions = {}
        substitutions["projection"] = copy.deepcopy(first_proof)
        substitutions["projection"]["childReceipt"]["story"]["headline"] = "forged"
        reseal_receipt(substitutions["projection"]["childReceipt"])
        substitutions["game"] = copy.deepcopy(first_proof)
        substitutions["game"]["childReceipt"]["game"]["version"] = "foreign"
        reseal_receipt(substitutions["game"]["childReceipt"], fixture=True)
        substitutions["seed"] = copy.deepcopy(first_proof)
        substitutions["seed"]["childReceipt"]["seed"] += 7
        reseal_receipt(substitutions["seed"]["childReceipt"], fixture=True)
        substitutions["entrant"] = copy.deepcopy(first_proof)
        substitutions["entrant"]["childReceipt"]["entrants"][0]["entrantId"] = "a" * 64
        reseal_receipt(substitutions["entrant"]["childReceipt"], fixture=True)
        substitutions["harness"] = copy.deepcopy(first_proof)
        substitutions["harness"]["childReceipt"]["entrants"][0][
            "harnessVersionId"
        ] = "b" * 64
        reseal_receipt(substitutions["harness"]["childReceipt"], fixture=True)
        substitutions["receipt"] = copy.deepcopy(first_proof)
        substitutions["receipt"]["childReceipt"]["receiptId"] = "c" * 64
        substitutions["receipt"]["childReceipt"]["verification"]["chainHead"] = "c" * 64
        substitutions["receipt"]["childReceipt"]["sourceParity"]["chainHead"] = "c" * 64
        substitutions["receipt"]["childReceipt"]["transcript"]["chainHead"] = "c" * 64
        reseal_receipt(substitutions["receipt"]["childReceipt"])
        substitutions["projection_digest"] = copy.deepcopy(first_proof)
        substitutions["projection_digest"]["childReceipt"]["projectionDigest"] = "d" * 64
        substitutions["seats"] = copy.deepcopy(first_proof)
        substitutions["seats"]["childReceipt"]["entrants"].reverse()
        for seat, row in enumerate(substitutions["seats"]["childReceipt"]["entrants"]):
            row["seat"] = seat
        reseal_receipt(substitutions["seats"]["childReceipt"], fixture=True)
        for label, candidate in substitutions.items():
            refuses(
                lambda candidate=candidate: compile_runback_surface_admission(
                    parent,
                    parent_transcript_path=parent_path,
                    proof=candidate,
                    previous_state=empty_lineage_state(),
                ),
                base=base,
                parent=parent,
            )

        print("[5] reuse, forks, stale heads, cycles, and foreign rivalries refuse")
        one = build_lineage([first_proof], previous_state=empty_lineage_state())
        next_state = one["basis"]["nextState"]
        refuses(
            lambda: compile_runback_surface_admission(
                parent,
                parent_transcript_path=parent_path,
                proof=first_proof,
                previous_state=next_state,
            ),
            contains="already consumed",
            base=base,
            parent=parent,
        )
        refuses(
            lambda: build_lineage(
                [first_proof, fork_proof], previous_state=empty_lineage_state()
            ),
            base=base,
            parent=parent,
        )
        stale_state = synthetic_state(
            challenge_id="challenge_dddddddddddddddd",
            challenge_digest="d" * 64,
            rivalry_id=acceptance["rivalryId"],
            root_id="e" * 64,
            head_id="f" * 64,
            projections={"e" * 64: "a" * 64, "f" * 64: "b" * 64},
        )
        refuses(
            lambda: compile_runback_surface_admission(
                parent,
                parent_transcript_path=parent_path,
                proof=first_proof,
                previous_state=stale_state,
            ),
            contains="prior rivalry head",
            base=base,
            parent=parent,
        )
        cycle_state = synthetic_state(
            challenge_id="challenge_eeeeeeeeeeeeeeee",
            challenge_digest="e" * 64,
            rivalry_id=second_acceptance["rivalryId"],
            root_id=grandchild["receiptId"],
            head_id=child["receiptId"],
            projections={
                grandchild["receiptId"]: grandchild["projectionDigest"],
                child["receiptId"]: child["projectionDigest"],
            },
        )
        child_base = compile_runback_surface_admission(child)
        refuses(
            lambda: compile_runback_surface_admission(
                child,
                parent_transcript_path=child_path,
                proof=second_proof,
                previous_state=cycle_state,
            ),
            contains="repeats a receipt",
            base=child_base,
            parent=child,
        )
        refuses(
            lambda: compile_runback_surface_admission(
                parent,
                parent_transcript_path=parent_path,
                proof=foreign_proof,
                previous_state=empty_lineage_state(),
            ),
            contains="parent receipt bytes",
            base=base,
            parent=parent,
        )
        short_collision = synthetic_state(
            challenge_id=challenge["challengeId"],
            challenge_digest="f" * 64,
            rivalry_id="c" * 64,
            root_id="a" * 64,
            head_id="b" * 64,
            projections={"a" * 64: "c" * 64, "b" * 64: "d" * 64},
        )
        refuses(
            lambda: compile_runback_surface_admission(
                parent,
                parent_transcript_path=parent_path,
                proof=first_proof,
                previous_state=short_collision,
            ),
            contains="short challenge id collides",
            base=base,
            parent=parent,
        )

        print("[6] byte budgets, path races, cleanup, and atomic output stay closed")
        with mock.patch.object(runback_module, "MAX_PROOF_BYTES", 1):
            refuses(
                lambda: compile_runback_surface_admission(
                    parent,
                    parent_transcript_path=parent_path,
                    proof=first_proof,
                    previous_state=empty_lineage_state(),
                ),
                contains="byte limit",
                base=base,
                parent=parent,
            )
        with mock.patch.object(runback_module, "MAX_LINEAGE_REPLAY_BYTES", 1):
            refuses(
                lambda: compile_runback_surface_admission(
                    parent,
                    parent_transcript_path=parent_path,
                    proof=first_proof,
                    previous_state=empty_lineage_state(),
                ),
                contains="replay-byte budget",
                base=base,
                parent=parent,
            )
        with mock.patch.object(
            runback_module.os,
            "lstat",
            return_value=SimpleNamespace(st_mode=stat.S_IFLNK),
        ):
            refuses(
                lambda: compile_runback_surface_admission(
                    parent,
                    parent_transcript_path=parent_path,
                    proof=first_proof,
                    previous_state=empty_lineage_state(),
                ),
                contains="non-symlink",
                base=base,
                parent=parent,
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
                lambda: compile_runback_surface_admission(
                    parent,
                    parent_transcript_path=parent_path,
                    proof=first_proof,
                    previous_state=empty_lineage_state(),
                ),
                contains="changed before",
                base=base,
                parent=parent,
            )

        def cleanup_failure(path):
            leaked_roots.append(path)
            raise OSError("synthetic cleanup refusal")

        with mock.patch.object(
            runback_module.shutil, "rmtree", side_effect=cleanup_failure
        ):
            refuses(
                lambda: compile_runback_surface_admission(
                    parent,
                    parent_transcript_path=parent_path,
                    proof=first_proof,
                    previous_state=empty_lineage_state(),
                ),
                contains="cleanup failed",
                base=base,
                parent=parent,
            )
        for leaked_root in leaked_roots:
            shutil.rmtree(leaked_root, ignore_errors=True)
        leaked_roots.clear()
        bad_bundle_proof = copy.deepcopy(first_proof)
        bad_bundle_proof["acceptance"]["acceptanceDigest"] = "0" * 64
        destination = os.path.join(work, "must-not-exist")
        refuses(
            lambda: write_bundle(
                parent_path,
                destination,
                runback_proof=bad_bundle_proof,
                previous_lineage_state=empty_lineage_state(),
            ),
            base=base,
            parent=parent,
        )
        require(not os.path.exists(destination), "failed share admission writes no partial tree")

        print("[7] proof custody paths and secret canaries never enter public surfaces")
        canary = "SECRET_CANARY_OPENCODE_API_KEY_SESSION_ENV"
        canary_root = os.path.join(work, canary)
        os.makedirs(canary_root)
        canary_parent = os.path.join(canary_root, "parent.jsonl")
        canary_child = os.path.join(canary_root, "child.jsonl")
        shutil.copyfile(parent_path, canary_parent)
        shutil.copyfile(child_path, canary_child)
        canary_proof = copy.deepcopy(first_proof)
        canary_proof["parentTranscriptPath"] = canary_parent
        canary_proof["childTranscriptPath"] = canary_child
        private_path_surface = compile_runback_surface_admission(
            parent,
            parent_transcript_path=canary_parent,
            proof=canary_proof,
            previous_state=empty_lineage_state(),
        )
        rendered = json.dumps(private_path_surface, sort_keys=True)
        for fragment in (
            canary,
            os.path.abspath(work),
            "parentTranscriptPath",
            "childTranscriptPath",
            "prompt",
            "rawOutput",
            "sessionToken",
            "environmentVariable",
        ):
            require(fragment not in rendered, f"public surface leaked {fragment!r}")
        require(
            private_path_surface == pending,
            "custody path substitution cannot alter admitted public bytes",
        )

        print("[8] closed runner bundle imports every advertised publishing symbol")
        bundle_out = Path(work) / "closed-runner"
        build_bundle(bundle_out, _source_policy=_TEST_SOURCE_POLICY)
        extract = Path(work) / "closed-runner-extract"
        extract.mkdir()
        with zipfile.ZipFile(bundle_out / BUNDLE_FILENAME, "r") as archive:
            archive.extractall(extract)
        import_check = subprocess.run(
            [
                sys.executable,
                "-I",
                "-c",
                (
                    "import os, sys; sys.path.insert(0, os.getcwd()); "
                    "import publishing; "
                    "assert publishing.__all__ == ['PublicationError']; "
                    "from publishing import *; "
                    "assert PublicationError is publishing.PublicationError"
                ),
            ],
            cwd=extract / BUNDLE_ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
            check=False,
        )
        require(
            import_check.returncode == 0,
            "closed runner imports every advertised publishing.__all__ symbol",
        )

        print(f"PASS: {checks} runback surface-admission checks")
        print(
            "unplayed default / exact replay upgrade / product-share parity / "
            "adversarial lineage and custody refusals"
        )
        return 0
    finally:
        for leaked_root in leaked_roots:
            shutil.rmtree(leaked_root, ignore_errors=True)
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
