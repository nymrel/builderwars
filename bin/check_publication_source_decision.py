#!/usr/bin/env python3
"""Adversarial, provider-free checks for AgentWars source-decision staging."""

from __future__ import annotations

import faulthandler
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.dont_write_bytecode = True
GIT_EXECUTABLE = shutil.which("git")
if GIT_EXECUTABLE is None:
    raise RuntimeError("Git is required for the source-decision checker")
GIT_EXECUTABLE = os.path.realpath(GIT_EXECUTABLE)

from arena.match import run_customer_local_match as run_match  # noqa: E402
from publishing.projection import project_receipt  # noqa: E402
from publishing.promotion import (  # noqa: E402
    ENGINE_SHA256,
    _tree_digest,
    canonical_digest,
    canonical_json,
    prepare_publication_candidate,
    sha256_hex,
)
from publishing.source_decision import (  # noqa: E402
    EXPECTED_AUTHORIZATIONS,
    EXPECTED_CANDIDATE_TRUTH_BOUNDARY,
    SourceDecisionError,
    apply_source_decision,
)

faulthandler.dump_traceback_later(120, exit=True)

PASSED = 0
SKIPPED = 0


def ok(name: str, condition: bool, detail: str = "") -> None:
    global PASSED
    if not condition:
        raise AssertionError(f"{name}: {detail or 'contract violated'}")
    PASSED += 1
    print(f"  [ok] {name}")


def skip(name: str, reason: str) -> None:
    global SKIPPED
    SKIPPED += 1
    print(f"  [SKIP] {name}: {reason}")


def _write(path: str, data: str | bytes) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mode = "wb" if isinstance(data, bytes) else "w"
    kwargs = {} if isinstance(data, bytes) else {"encoding": "utf-8", "newline": ""}
    with open(path, mode, **kwargs) as handle:
        handle.write(data)


def _json_bytes(value: object) -> bytes:
    return (canonical_json(value) + "\n").encode("utf-8")


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _git(repo: str, *args: str) -> str:
    completed = subprocess.run(
        [GIT_EXECUTABLE, "-C", repo, *args],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=20,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {completed.stderr[-500:]}")
    return completed.stdout.strip()


HARNESS_SOURCE = r"""#!/usr/bin/env python3
import argparse
import json
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--name", required=True)
parser.add_argument("--backend", required=True)
parser.add_argument("--strategy", choices=("win-now", "long-game"), required=True)
args = parser.parse_args()

def send(value):
    sys.stdout.write(json.dumps(value, separators=(",", ":")) + "\n")
    sys.stdout.flush()

for line in sys.stdin:
    if not line.strip():
        continue
    message = json.loads(line)
    if message.get("type") == "hello":
        send({"type":"ready","entrant":args.name,"version":"1","backend":args.backend})
    elif message.get("type") == "move_request":
        observation = message.get("observation") or {}
        needs = observation.get("needs") or {}
        players = [
            row for row in (observation.get("available_players") or [])
            if isinstance(row, dict)
            and isinstance(row.get("id"), int)
            and isinstance(row.get("position"), str)
            and isinstance(needs.get(row.get("position")), int)
            and needs[row.get("position")] > 0
        ]
        key = "redraft_points" if args.strategy == "win-now" else "dynasty_points"
        choice = max(players, key=lambda row: (row.get(key, -1), -row["id"]))
        send({"type":"move","move":{"player_id":choice["id"]},"note":"source=model"})
    elif message.get("type") == "goodbye":
        break
"""


def _build_transcript(work: str) -> str:
    harness = os.path.join(work, "model_claim_fixture.py")
    _write(harness, HARNESS_SOURCE)
    match = run_match(
        game_name="fantasy_redraft",
        seed=9_400,
        entrants=[
            {
                "name": "Codex Redraft",
                "cmd": [
                    sys.executable,
                    harness,
                    "--name",
                    "Codex Redraft",
                    "--backend",
                    "chatgpt_codex:codex exec",
                    "--strategy",
                    "win-now",
                ],
                "env": [],
                "claimed_model": "chatgpt_codex:codex exec",
                "execution_claim": "model",
            },
            {
                "name": "OpenCode Dynasty",
                "cmd": [
                    sys.executable,
                    harness,
                    "--name",
                    "OpenCode Dynasty",
                    "--backend",
                    "opencode-provider:opencode-go/ox-alpha-free@max",
                    "--strategy",
                    "long-game",
                ],
                "env": [],
                "claimed_model": "opencode-provider:opencode-go/ox-alpha-free@max",
                "execution_claim": "model",
            },
        ],
        out_dir=os.path.join(work, "match"),
        move_timeout_s=5.0,
    )
    ok(
        "source-decision fixture is decisive",
        match["decisive"] is True and match["winner"] in (0, 1),
    )
    ok(
        "source-decision fixture uses fixed engine",
        match["engine_digest"] == ENGINE_SHA256,
    )
    return match["transcript"]


def _build_candidate(work: str, transcript_path: str) -> tuple[str, str, dict]:
    receipt, _records = project_receipt(transcript_path)
    transcript = Path(transcript_path).read_bytes()
    transcript_sha = sha256_hex(transcript)
    match_id = Path(transcript_path).stem
    source_path = (
        f"matches/agentwars-review-candidates/{receipt['game']['name']}/"
        f"{receipt['seed']}-{match_id}/{receipt['receiptId']}.jsonl"
    )
    totals = {
        key: sum(row[key] for row in receipt["moveSourceClaims"])
        for key in ("model", "fallback", "scripted", "other")
    }
    candidate_id = "candidate_" + "a" * 24
    manifest_candidate = {
        "schemaVersion": "agentwars.publication-manifest-entry-candidate.v1",
        "candidateId": candidate_id,
        "candidateStatus": "source_control_review_required",
        "sequenceAssignmentRequired": True,
        "requiredDecision": "independently_choose_approved_for_publication_or_held",
        "suggestedSourcePath": source_path,
        "entryWithoutSequence": {
            "sourcePath": source_path,
            "sourceFileSha256": transcript_sha,
            "sourceChainHead": receipt["receiptId"],
            "sourceCounts": totals,
            "decision": "eligible_for_review",
            "titleEligible": False,
            "label": "Private fantasy_redraft reviewer-approval claim; source-control review required",
        },
        "authorizations": dict(EXPECTED_AUTHORIZATIONS),
    }
    preview_bytes = _json_bytes(receipt)
    manifest_bytes = _json_bytes(manifest_candidate)
    candidate_dir = os.path.join(work, "candidate")
    os.mkdir(candidate_dir)
    _write(os.path.join(candidate_dir, "transcript.jsonl"), transcript)
    _write(os.path.join(candidate_dir, "public-receipt-preview.json"), preview_bytes)
    _write(os.path.join(candidate_dir, "manifest-entry-candidate.json"), manifest_bytes)
    files = {
        "transcript.jsonl": {"sha256": transcript_sha, "bytes": len(transcript)},
        "public-receipt-preview.json": {
            "sha256": sha256_hex(preview_bytes),
            "bytes": len(preview_bytes),
        },
        "manifest-entry-candidate.json": {
            "sha256": sha256_hex(manifest_bytes),
            "bytes": len(manifest_bytes),
        },
    }
    candidate_core = {
        "schemaVersion": "agentwars.publication-candidate.v1",
        "candidateId": candidate_id,
        "candidateStatus": "offline_export_verified_candidate_only",
        "sourceContract": "nymrel_reviewer_case_response_shape.v1",
        "sourceExport": {
            "exactFileSha256": "1" * 64,
            "canonicalPayloadSha256": "2" * 64,
            "exactBytes": 1_024,
            "reviewerAccessClaim": "authorized_reviewer",
            "reviewerExportOriginAttested": False,
            "reviewerIdentityAttested": False,
            "serverSignatureVerified": False,
            "authenticatedTransportVerifiedOffline": False,
        },
        "reviewDecisionClaim": {
            "status": "approved",
            "reasonCode": "evidence_verified_for_separate_manual_promotion",
            "publicationDecision": "reviewer_approved_not_published",
            "promotionStatus": "eligible_for_separate_manual_promotion",
            "decisionReceiptCommitment": "3" * 64,
            "requestCommitment": "4" * 64,
        },
        "evidenceBindings": {
            "jobCommitmentSha256": "5" * 64,
            "evidenceBundleSha256": "6" * 64,
            "resultBodySha256": "7" * 64,
            "summarySha256": "8" * 64,
            "summaryDigest": "9" * 64,
            "compressedTranscriptSha256": "a" * 64,
            "transcriptSha256": transcript_sha,
            "projectionDigest": receipt["projectionDigest"],
            "chainHead": receipt["receiptId"],
            "engineSha256": receipt["verification"]["engineDigest"],
        },
        "verification": {
            "builderWarsReplayVerdict": "PASS",
            "builderWarsEffectiveVerdict": "PASS",
            "engineDigestMatch": True,
            "verifierSnapshotMatch": True,
            "crossImplementationProjectionMatch": True,
            "allAcceptedMovesModelClaimed": True,
            "modelAttested": False,
            "publicationManifestUnchanged": True,
            "generatedArtifactUnchanged": True,
        },
        "suggestedSourcePath": source_path,
        "files": files,
        "authorizations": dict(EXPECTED_AUTHORIZATIONS),
        "truthBoundary": EXPECTED_CANDIDATE_TRUTH_BOUNDARY,
    }
    candidate = {**candidate_core, "candidateDigest": canonical_digest(candidate_core)}
    _write(os.path.join(candidate_dir, "candidate.json"), _json_bytes(candidate))
    return candidate_dir, candidate["candidateDigest"], receipt


def _build_repo(work: str) -> dict[str, str]:
    repo = os.path.join(work, "repo")
    os.makedirs(os.path.join(repo, "docs"))
    os.makedirs(os.path.join(repo, "publishing", "agentwars-public-v1"))
    shutil.copyfile(
        os.path.join(ROOT, "docs", "AGENTWARS_PUBLICATION_MANIFEST.v1.json"),
        os.path.join(repo, "docs", "AGENTWARS_PUBLICATION_MANIFEST.v1.json"),
    )
    _write(
        os.path.join(repo, "publishing", "agentwars-public-v1", "sentinel.txt"),
        b"protected\n",
    )
    _git(repo, "init", "--initial-branch=main")
    _git(repo, "config", "user.name", "AgentWars Source Decision Check")
    _git(repo, "config", "user.email", "checks@invalid.example")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(
        repo,
        "add",
        "docs/AGENTWARS_PUBLICATION_MANIFEST.v1.json",
        "publishing/agentwars-public-v1/sentinel.txt",
    )
    _git(repo, "commit", "-m", "fixture")
    return _repo_state(repo)


def _repo_state(repo: str) -> dict[str, str]:
    manifest = os.path.join(repo, "docs", "AGENTWARS_PUBLICATION_MANIFEST.v1.json")
    artifact = os.path.join(repo, "publishing", "agentwars-public-v1")
    return {
        "repo": repo,
        "head": _git(repo, "rev-parse", "HEAD"),
        "manifest": manifest,
        "manifestSha256": sha256_hex(Path(manifest).read_bytes()),
        "artifact": artifact,
        "artifactDigest": _tree_digest(artifact),
    }


def _apply(state: dict[str, str], candidate_dir: str, digest: str, **overrides) -> dict:
    arguments = {
        "expected_candidate_digest": digest,
        "expected_head": state["head"],
        "expected_manifest_sha256": state["manifestSha256"],
        "expected_generated_tree_digest": state["artifactDigest"],
        "decision": "approved_for_publication",
        "label": "Reviewed customer-local fantasy result; provider and model identity unattested",
    }
    arguments.update(overrides)
    return apply_source_decision(state["repo"], candidate_dir, **arguments)


def _rebind_candidate(candidate_dir: str) -> str:
    candidate_path = os.path.join(candidate_dir, "candidate.json")
    candidate = _load(candidate_path)
    core = dict(candidate)
    core.pop("candidateDigest", None)
    candidate = {**core, "candidateDigest": canonical_digest(core)}
    _write(candidate_path, _json_bytes(candidate))
    return candidate["candidateDigest"]


def _rebind_inventory(candidate_dir: str, name: str) -> str:
    candidate_path = os.path.join(candidate_dir, "candidate.json")
    candidate = _load(candidate_path)
    raw = Path(candidate_dir, name).read_bytes()
    candidate["files"][name] = {"sha256": sha256_hex(raw), "bytes": len(raw)}
    _write(candidate_path, _json_bytes(candidate))
    return _rebind_candidate(candidate_dir)


def _snapshot(state: dict[str, str]) -> tuple[bytes, str, str]:
    return (
        Path(state["manifest"]).read_bytes(),
        _tree_digest(state["artifact"]),
        _git(state["repo"], "status", "--porcelain=v1", "--untracked-files=all"),
    )


def _expect_refusal(
    name: str,
    state: dict[str, str],
    candidate_dir: str,
    digest: str,
    *,
    phrase: str | None = None,
    **overrides,
) -> None:
    before = _snapshot(state)
    try:
        _apply(state, candidate_dir, digest, **overrides)
    except SourceDecisionError as error:
        ok(name, phrase is None or phrase in str(error), repr(str(error)))
        ok(name + " leaves protected state unchanged", _snapshot(state) == before)
        return
    raise AssertionError(f"{name}: hostile decision was accepted")


def main() -> int:
    live_manifest = os.path.join(ROOT, "docs", "AGENTWARS_PUBLICATION_MANIFEST.v1.json")
    live_artifact = os.path.join(ROOT, "publishing", "agentwars-public-v1")
    live_manifest_before = Path(live_manifest).read_bytes()
    live_artifact_before = _tree_digest(live_artifact)
    with tempfile.TemporaryDirectory(
        prefix="agentwars-source-decision-check-"
    ) as temporary_root:
        work = os.path.realpath(temporary_root)
        transcript = _build_transcript(work)

        bridge_work = os.path.join(work, "real-bridge")
        os.mkdir(bridge_work)
        checker_path = os.path.join(ROOT, "bin", "check_publication_candidate.py")
        checker_spec = importlib.util.spec_from_file_location(
            "agentwars_candidate_fixture", checker_path
        )
        if checker_spec is None or checker_spec.loader is None:
            raise AssertionError(
                "could not load the existing promotion-candidate fixture builder"
            )
        checker_module = importlib.util.module_from_spec(checker_spec)
        checker_spec.loader.exec_module(checker_module)
        faulthandler.dump_traceback_later(120, exit=True)
        bridge_export = checker_module._build_export(transcript)
        bridge_export_path = os.path.join(bridge_work, "reviewer-export.json")
        checker_module._write_export(bridge_export_path, bridge_export)
        bridge_candidate = os.path.join(bridge_work, "candidate")
        bridge_result = prepare_publication_candidate(
            ROOT, bridge_export_path, bridge_candidate
        )
        bridge_state = _build_repo(bridge_work)
        bridge_decision = _apply(
            bridge_state,
            bridge_candidate,
            bridge_result["candidateDigest"],
        )
        ok(
            "real promotion-bridge candidate reaches source staging",
            bridge_decision["candidateId"] == bridge_result["candidateId"]
            and bridge_decision["status"] == "source_decision_staged_not_built",
        )

        happy_work = os.path.join(work, "happy")
        os.mkdir(happy_work)
        candidate_dir, digest, receipt = _build_candidate(happy_work, transcript)
        state = _build_repo(happy_work)
        manifest_mode_before = stat.S_IMODE(os.stat(state["manifest"]).st_mode)
        result = _apply(state, candidate_dir, digest)
        source = os.path.join(state["repo"], *result["sourcePath"].split("/"))
        ok(
            "source decision stages exact transcript",
            Path(source).read_bytes() == Path(transcript).read_bytes(),
        )
        ok(
            "source decision appends exact reviewed identity",
            result["receiptId"] == receipt["receiptId"] and result["sequence"] == 10,
        )
        ok("source decision remains title-ineligible", result["titleEligible"] is False)
        ok(
            "source decision does not build or deploy",
            result["publicArtifactBuilt"] is False and result["deployed"] is False,
        )
        ok(
            "source decision preserves false identity authority",
            result["providerOrModelAttested"] is False
            and result["rankingAuthorized"] is False,
        )
        ok(
            "source decision preserves generated artifact bytes",
            _tree_digest(state["artifact"]) == state["artifactDigest"],
        )
        ok(
            "source decision preserves manifest file mode",
            stat.S_IMODE(os.stat(state["manifest"]).st_mode) == manifest_mode_before,
        )
        decided_manifest = _load(state["manifest"])
        row = decided_manifest["entries"][-1]
        ok(
            "manifest decision is explicit",
            row["decision"] == "approved_for_publication"
            and row["sourceChainHead"] == receipt["receiptId"],
        )
        rerun_state = _repo_state(state["repo"])
        rerun = _apply(rerun_state, candidate_dir, digest)
        ok(
            "response-loss rerun is idempotent",
            rerun["status"] == "source_decision_already_staged_not_built",
        )
        ok(
            "idempotent rerun leaves one manifest row",
            len(_load(state["manifest"])["entries"]) == 11,
        )

        resume_work = os.path.join(work, "resume")
        os.mkdir(resume_work)
        resume_candidate, resume_digest, _ = _build_candidate(resume_work, transcript)
        resume_state = _build_repo(resume_work)
        source_path = _load(
            os.path.join(resume_candidate, "manifest-entry-candidate.json")
        )["suggestedSourcePath"]
        resume_source = os.path.join(resume_state["repo"], *source_path.split("/"))
        _write(resume_source, Path(transcript).read_bytes())
        resumed = _apply(resume_state, resume_candidate, resume_digest)
        ok(
            "exact orphan transcript resumes safely",
            resumed["status"] == "source_decision_staged_not_built",
        )

        held_work = os.path.join(work, "held")
        os.mkdir(held_work)
        held_candidate, held_digest, _ = _build_candidate(held_work, transcript)
        held_state = _build_repo(held_work)
        held = _apply(
            held_state,
            held_candidate,
            held_digest,
            decision="held",
            label="Held pending a separate public-claims decision",
        )
        ok(
            "held decision is explicit and still not built",
            held["decision"] == "held" and held["publicArtifactBuilt"] is False,
        )

        dirty_work = os.path.join(work, "dirty")
        os.mkdir(dirty_work)
        dirty_candidate, dirty_digest, _ = _build_candidate(dirty_work, transcript)
        dirty_state = _build_repo(dirty_work)
        _write(os.path.join(dirty_state["repo"], "unrelated.txt"), "do not accept")
        _expect_refusal(
            "unrelated dirty worktree is refused",
            dirty_state,
            dirty_candidate,
            dirty_digest,
            phrase="unrelated",
        )

        lock_work = os.path.join(work, "lock")
        os.mkdir(lock_work)
        lock_candidate, lock_digest, _ = _build_candidate(lock_work, transcript)
        lock_state = _build_repo(lock_work)
        common_dir = _git(lock_state["repo"], "rev-parse", "--git-common-dir")
        if not os.path.isabs(common_dir):
            common_dir = os.path.abspath(os.path.join(lock_state["repo"], common_dir))
        lock_path = os.path.join(common_dir, "agentwars-source-decision.lock")
        _write(lock_path, "foreign lock\n")
        try:
            _expect_refusal(
                "concurrent source-decision lock is refused",
                lock_state,
                lock_candidate,
                lock_digest,
                phrase="holds the repository lock",
            )
        finally:
            os.unlink(lock_path)

        ignored_work = os.path.join(work, "ignored")
        os.mkdir(ignored_work)
        ignored_candidate, ignored_digest, _ = _build_candidate(
            ignored_work, transcript
        )
        ignored_state = _build_repo(ignored_work)
        _write(
            os.path.join(ignored_state["repo"], ".gitignore"),
            "matches/agentwars-review-candidates/\n",
        )
        _git(ignored_state["repo"], "add", ".gitignore")
        _git(ignored_state["repo"], "commit", "-m", "ignored source fixture")
        ignored_state = _repo_state(ignored_state["repo"])
        _expect_refusal(
            "ignored source path is refused",
            ignored_state,
            ignored_candidate,
            ignored_digest,
            phrase="ignored by repository policy",
        )

        wrong_head_work = os.path.join(work, "wrong-head")
        os.mkdir(wrong_head_work)
        wrong_head_candidate, wrong_head_digest, _ = _build_candidate(
            wrong_head_work, transcript
        )
        wrong_head_state = _build_repo(wrong_head_work)
        _expect_refusal(
            "wrong reviewed head is refused",
            wrong_head_state,
            wrong_head_candidate,
            wrong_head_digest,
            phrase="HEAD differs",
            expected_head="f" * 40,
        )
        _expect_refusal(
            "wrong manifest hash is refused",
            wrong_head_state,
            wrong_head_candidate,
            wrong_head_digest,
            phrase="manifest differs",
            expected_manifest_sha256="e" * 64,
        )
        _expect_refusal(
            "wrong generated tree digest is refused",
            wrong_head_state,
            wrong_head_candidate,
            wrong_head_digest,
            phrase="artifact tree differs",
            expected_generated_tree_digest="d" * 64,
        )

        transcript_work = os.path.join(work, "transcript")
        os.mkdir(transcript_work)
        transcript_candidate, transcript_digest, _ = _build_candidate(
            transcript_work, transcript
        )
        transcript_state = _build_repo(transcript_work)
        with open(
            os.path.join(transcript_candidate, "transcript.jsonl"), "ab"
        ) as handle:
            handle.write(b"\n")
        _expect_refusal(
            "transcript byte drift is refused",
            transcript_state,
            transcript_candidate,
            transcript_digest,
            phrase="inventory",
        )

        digest_work = os.path.join(work, "digest")
        os.mkdir(digest_work)
        digest_candidate, digest_value, _ = _build_candidate(digest_work, transcript)
        digest_state = _build_repo(digest_work)
        _expect_refusal(
            "wrong candidate digest is refused",
            digest_state,
            digest_candidate,
            "c" * 64,
            phrase="digest",
        )
        candidate = _load(os.path.join(digest_candidate, "candidate.json"))
        candidate["sourceExport"]["reviewerExportOriginAttested"] = True
        _write(os.path.join(digest_candidate, "candidate.json"), _json_bytes(candidate))
        digest_value = _rebind_candidate(digest_candidate)
        _expect_refusal(
            "offline origin attestation is refused",
            digest_state,
            digest_candidate,
            digest_value,
            phrase="overstates",
        )

        attestation_work = os.path.join(work, "attestation")
        os.mkdir(attestation_work)
        attestation_candidate, attestation_digest, _ = _build_candidate(
            attestation_work, transcript
        )
        attestation_state = _build_repo(attestation_work)
        candidate = _load(os.path.join(attestation_candidate, "candidate.json"))
        candidate["verification"]["modelAttested"] = True
        _write(
            os.path.join(attestation_candidate, "candidate.json"),
            _json_bytes(candidate),
        )
        attestation_digest = _rebind_candidate(attestation_candidate)
        _expect_refusal(
            "model attestation upgrade is refused",
            attestation_state,
            attestation_candidate,
            attestation_digest,
            phrase="verification state",
        )

        preview_work = os.path.join(work, "preview")
        os.mkdir(preview_work)
        preview_candidate, preview_digest, _ = _build_candidate(
            preview_work, transcript
        )
        preview_state = _build_repo(preview_work)
        preview = _load(os.path.join(preview_candidate, "public-receipt-preview.json"))
        preview["story"]["headline"] = "tampered headline"
        _write(
            os.path.join(preview_candidate, "public-receipt-preview.json"),
            _json_bytes(preview),
        )
        preview_digest = _rebind_inventory(
            preview_candidate, "public-receipt-preview.json"
        )
        _expect_refusal(
            "projection drift is refused",
            preview_state,
            preview_candidate,
            preview_digest,
            phrase="preview differs",
        )

        path_work = os.path.join(work, "path")
        os.mkdir(path_work)
        path_candidate, path_digest, _ = _build_candidate(path_work, transcript)
        path_state = _build_repo(path_work)
        manifest_candidate = _load(
            os.path.join(path_candidate, "manifest-entry-candidate.json")
        )
        manifest_candidate["suggestedSourcePath"] = "matches/../escape.jsonl"
        manifest_candidate["entryWithoutSequence"]["sourcePath"] = (
            "matches/../escape.jsonl"
        )
        candidate = _load(os.path.join(path_candidate, "candidate.json"))
        candidate["suggestedSourcePath"] = "matches/../escape.jsonl"
        _write(
            os.path.join(path_candidate, "manifest-entry-candidate.json"),
            _json_bytes(manifest_candidate),
        )
        _write(os.path.join(path_candidate, "candidate.json"), _json_bytes(candidate))
        path_digest = _rebind_inventory(path_candidate, "manifest-entry-candidate.json")
        _expect_refusal(
            "path traversal is refused",
            path_state,
            path_candidate,
            path_digest,
            phrase="path contract",
        )

        count_work = os.path.join(work, "counts")
        os.mkdir(count_work)
        count_candidate, count_digest, _ = _build_candidate(count_work, transcript)
        count_state = _build_repo(count_work)
        manifest_candidate = _load(
            os.path.join(count_candidate, "manifest-entry-candidate.json")
        )
        manifest_candidate["entryWithoutSequence"]["sourceCounts"]["model"] += 1
        _write(
            os.path.join(count_candidate, "manifest-entry-candidate.json"),
            _json_bytes(manifest_candidate),
        )
        count_digest = _rebind_inventory(
            count_candidate, "manifest-entry-candidate.json"
        )
        _expect_refusal(
            "source-count drift is refused",
            count_state,
            count_candidate,
            count_digest,
            phrase="model moves",
        )

        extra_work = os.path.join(work, "extra")
        os.mkdir(extra_work)
        extra_candidate, extra_digest, _ = _build_candidate(extra_work, transcript)
        extra_state = _build_repo(extra_work)
        _write(os.path.join(extra_candidate, "private-export.json"), "{}")
        _expect_refusal(
            "unexpected candidate file is refused",
            extra_state,
            extra_candidate,
            extra_digest,
            phrase="exactly the four",
        )

        inside_work = os.path.join(work, "inside")
        os.mkdir(inside_work)
        outside_candidate, inside_digest, _ = _build_candidate(inside_work, transcript)
        inside_state = _build_repo(inside_work)
        inside_candidate = os.path.join(inside_state["repo"], "candidate")
        shutil.copytree(outside_candidate, inside_candidate)
        _expect_refusal(
            "repository-local candidate is refused",
            inside_state,
            inside_candidate,
            inside_digest,
            phrase="outside",
        )

        collision_work = os.path.join(work, "collision")
        os.mkdir(collision_work)
        collision_candidate, collision_digest, collision_receipt = _build_candidate(
            collision_work, transcript
        )
        collision_state = _build_repo(collision_work)
        manifest = _load(collision_state["manifest"])
        manifest["entries"].append(
            {
                "decision": "held",
                "label": "Conflicting pre-existing identity",
                "sequence": len(manifest["entries"]),
                "sourceChainHead": collision_receipt["receiptId"],
                "sourceCounts": {"model": 0, "fallback": 0, "scripted": 0, "other": 0},
                "sourceFileSha256": "b" * 64,
                "sourcePath": "matches/agentwars-review-candidates/fantasy_redraft/1-1111111111111111/"
                + "b" * 64
                + ".jsonl",
                "titleEligible": False,
            }
        )
        _write(collision_state["manifest"], json.dumps(manifest, indent=2) + "\n")
        _git(
            collision_state["repo"],
            "add",
            "docs/AGENTWARS_PUBLICATION_MANIFEST.v1.json",
        )
        _git(collision_state["repo"], "commit", "-m", "collision fixture")
        collision_state = _repo_state(collision_state["repo"])
        _expect_refusal(
            "chain-head collision is refused",
            collision_state,
            collision_candidate,
            collision_digest,
            phrase="differently",
        )

        target_work = os.path.join(work, "target")
        os.mkdir(target_work)
        target_candidate, target_digest, _ = _build_candidate(target_work, transcript)
        target_state = _build_repo(target_work)
        target_path = _load(
            os.path.join(target_candidate, "manifest-entry-candidate.json")
        )["suggestedSourcePath"]
        _write(
            os.path.join(target_state["repo"], *target_path.split("/")), b"different\n"
        )
        _expect_refusal(
            "different pre-existing source is refused",
            target_state,
            target_candidate,
            target_digest,
            phrase="different bytes",
        )

        label_work = os.path.join(work, "label")
        os.mkdir(label_work)
        label_candidate, label_digest, _ = _build_candidate(label_work, transcript)
        label_state = _build_repo(label_work)
        _expect_refusal(
            "control-character label is refused",
            label_state,
            label_candidate,
            label_digest,
            phrase="printable",
            label="bad\nlabel",
        )
        _expect_refusal(
            "eligible-for-review cannot be selected",
            label_state,
            label_candidate,
            label_digest,
            phrase="approved_for_publication or held",
            decision="eligible_for_review",
        )

        symlink_work = os.path.join(work, "symlink")
        os.mkdir(symlink_work)
        symlink_candidate, symlink_digest, _ = _build_candidate(
            symlink_work, transcript
        )
        symlink_state = _build_repo(symlink_work)
        link = os.path.join(symlink_work, "candidate-link")
        try:
            os.symlink(symlink_candidate, link, target_is_directory=True)
        except OSError as error:
            skip("candidate directory symlink is refused", error.__class__.__name__)
        else:
            _expect_refusal(
                "candidate directory symlink is refused",
                symlink_state,
                link,
                symlink_digest,
                phrase="reparse",
            )

        missing_ack = subprocess.run(
            [
                sys.executable,
                os.path.join(ROOT, "bin", "apply_publication_candidate.py"),
                "--candidate-dir",
                label_candidate,
                "--expected-candidate-digest",
                label_digest,
                "--expected-head",
                label_state["head"],
                "--expected-manifest-sha256",
                label_state["manifestSha256"],
                "--expected-generated-tree-digest",
                label_state["artifactDigest"],
                "--decision",
                "held",
                "--label",
                "Held test",
                "--source-control-decision-v1",
                "--title-ineligible-v1",
                "--no-generated-artifact-mutation-v1",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
            check=False,
        )
        ok(
            "CLI requires all four acknowledgements",
            missing_ack.returncode == 2 and "--no-deploy-v1" in missing_ack.stderr,
        )

    ok(
        "live publication manifest remains byte-identical",
        Path(live_manifest).read_bytes() == live_manifest_before,
    )
    ok(
        "live generated artifact tree remains byte-identical",
        _tree_digest(live_artifact) == live_artifact_before,
    )
    print(f"AgentWars source-decision checks: {PASSED} passed, {SKIPPED} skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
