#!/usr/bin/env python3
"""Adversarial, provider-free checks for the offline promotion bridge."""

from __future__ import annotations

import copy
import faulthandler
import json
import os
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.dont_write_bytecode = True

from arena.match import run_match  # noqa: E402
from publishing.projection import project_receipt  # noqa: E402
from publishing.promotion import (  # noqa: E402
    APPROVAL_DECISION,
    APPROVAL_EVIDENCE_CLASS,
    APPROVAL_REASON,
    APPROVAL_STATUS,
    DECISION_PROTOCOL,
    ENGINE_SHA256,
    FALSE_ATTESTATION_KEYS,
    JOB_PROTOCOL,
    TRUTH_BOUNDARY,
    TRUTH_STATUS,
    PromotionCandidateError,
    _tree_digest,
    _validate_transcript_content,
    canonical_digest,
    canonical_json,
    prepare_publication_candidate,
    sha256_hex,
)

faulthandler.dump_traceback_later(90, exit=True)

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


def token(prefix: str, fill: int) -> str:
    import base64

    return prefix + base64.urlsafe_b64encode(bytes([fill]) * 16).decode("ascii").rstrip("=")


HARNESS_SOURCE = r'''#!/usr/bin/env python3
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
'''


def _write(path: str, data: str | bytes) -> None:
    mode = "wb" if isinstance(data, bytes) else "w"
    kwargs = {} if isinstance(data, bytes) else {"encoding": "utf-8", "newline": ""}
    with open(path, mode, **kwargs) as handle:
        handle.write(data)


def _build_transcript(work: str) -> str:
    harness = os.path.join(work, "model_claim_fixture.py")
    _write(harness, HARNESS_SOURCE)
    out = os.path.join(work, "match")
    entrants = [
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
    ]
    match = run_match(
        game_name="fantasy_redraft",
        seed=9_400,
        entrants=entrants,
        out_dir=out,
        move_timeout_s=5.0,
    )
    ok("fixture match is decisive", match["decisive"] is True and match["winner"] in (0, 1))
    ok("fixture engine is the fixed competition snapshot", match["engine_digest"] == ENGINE_SHA256)
    return match["transcript"]


def _false_flags() -> dict[str, bool]:
    return {key: False for key in FALSE_ATTESTATION_KEYS}


def _build_export(transcript_path: str) -> dict:
    transcript = Path(transcript_path).read_bytes()
    receipt, records = project_receipt(transcript_path)
    header = records[0]["body"]
    harness_digest = header["entrants"][0]["script"]["sha256"]
    ok(
        "both fixture seats bind one fixed harness digest",
        header["entrants"][1]["script"]["sha256"] == harness_digest,
    )
    job = {
        "jobId": token("awj1_", 31),
        "kind": "closed_fantasy_evidence_submission",
        "competitionId": token("awc1_", 32),
        "requiredHarnessId": "agentwars-cli",
        "requiredHarnessDigest": harness_digest,
        "game": "fantasy_redraft",
        "seed": 9_400,
        "engineSha256": ENGINE_SHA256,
        "seats": [
            {
                "seat": 0,
                "entrant": "Codex Redraft",
                "providerClaim": "chatgpt_codex",
                "selectedModelClaim": None,
                "variantClaim": None,
                "backendClaim": "chatgpt_codex:codex exec",
                "strategy": "win-now",
                "agentId": None,
                "versionId": None,
            },
            {
                "seat": 1,
                "entrant": "OpenCode Dynasty",
                "providerClaim": "opencode",
                "selectedModelClaim": "opencode-go/ox-alpha-free",
                "variantClaim": "max",
                "backendClaim": "opencode-provider:opencode-go/ox-alpha-free@max",
                "strategy": "long-game",
                "agentId": None,
                "versionId": None,
            },
        ],
        "requireSignedPassports": False,
        "requiredTruthStatus": TRUTH_STATUS,
        "publicationMode": "private_review_only",
        "maxAttempts": 3,
    }
    job_commitment = canonical_digest({"schemaVersion": 1, "protocolVersion": JOB_PROTOCOL, **job})
    counts = receipt["moveSourceClaims"]
    outcome = receipt["outcome"]
    summary_core = {
        "schemaVersion": "agentwars.cross_provider_match_summary.v1",
        "status": TRUTH_STATUS,
        "evidenceClass": "customer_local_provider_claims_with_replay",
        "publicationDecision": "not_reviewed_not_published",
        "truthBoundary": TRUTH_BOUNDARY,
        "game": "fantasy_redraft",
        "seed": 9_400,
        "matchId": header["match_id"],
        "chainHead": receipt["receiptId"],
        "transcriptSha256": sha256_hex(transcript),
        "winnerSeat": outcome["winnerSeat"],
        "winnerEntrant": job["seats"][outcome["winnerSeat"]]["entrant"],
        "seats": [
            {
                "seat": 0,
                "entrant": "Codex Redraft",
                "providerClaim": "chatgpt_codex",
                "selectedModelClaim": None,
                "variantClaim": None,
                "connectionModeClaim": "local_subscription_session",
                "providerClass": "official_local_client_delegation",
                "harnessClass": "official_first_party_cli",
                "backendClaim": "chatgpt_codex:codex exec",
                "strategy": "win-now",
                "score": outcome["scores"][0],
                "moveSourceClaims": {key: counts[0][key] for key in ("model", "fallback", "scripted", "other")},
            },
            {
                "seat": 1,
                "entrant": "OpenCode Dynasty",
                "providerClaim": "opencode",
                "selectedModelClaim": "opencode-go/ox-alpha-free",
                "variantClaim": "max",
                "connectionModeClaim": "local_provider_session",
                "providerClass": "route_dependent_harness",
                "harnessClass": "third_party_local_harness",
                "backendClaim": "opencode-provider:opencode-go/ox-alpha-free@max",
                "strategy": "long-game",
                "score": outcome["scores"][1],
                "moveSourceClaims": {key: counts[1][key] for key in ("model", "fallback", "scripted", "other")},
            },
        ],
        "providerClaimsDiffer": True,
        "allAcceptedMovesModelClaimed": True,
        "universalProviderOrModelRankingEligible": False,
        "verification": {
            "replayVerdict": "PASS",
            "effectiveVerdict": "PASS",
            "engineDigest": ENGINE_SHA256,
            "engineDigestMatch": True,
            "verifierSnapshotMatch": True,
            "identityStatus": "self_declared_legacy",
            "signedHarnessVersionsVerified": False,
        },
        **_false_flags(),
    }
    summary = {**summary_core, "summaryDigest": canonical_digest(summary_core)}
    compressed = zlib.compress(transcript)
    body = {
        "schemaVersion": 1,
        "protocolVersion": JOB_PROTOCOL,
        "jobId": job["jobId"],
        "attemptId": token("awa1_", 4),
        "leaseEpoch": 1,
        "competitionId": job["competitionId"],
        "jobCommitmentSha256": job_commitment,
        "engineSha256": ENGINE_SHA256,
        "summarySha256": canonical_digest(summary),
        "summaryDigest": summary["summaryDigest"],
        "transcriptSha256": sha256_hex(transcript),
        "compressedTranscriptSha256": sha256_hex(compressed),
        "projectionDigest": receipt["projectionDigest"],
        "matchId": header["match_id"],
        "chainHead": receipt["receiptId"],
        "truthStatus": TRUTH_STATUS,
        "transcriptEncoding": "zlib+base64url",
        "publicationDecision": "not_reviewed_not_published",
        "rankingEligible": False,
        **_false_flags(),
        "evidenceBundleSha256": "0" * 64,
        "transcriptEncoded": __import__("base64").urlsafe_b64encode(compressed).decode("ascii").rstrip("="),
        "summary": summary,
    }
    body["evidenceBundleSha256"] = canonical_digest(
        {key: value for key, value in body.items() if key not in {"evidenceBundleSha256", "transcriptEncoded", "summary"}}
    )
    body_text = canonical_json(body, ensure_ascii=True)
    result_body_sha = sha256_hex(body_text)
    verified_at = "2026-08-26T16:55:00.000Z"
    requested_at = "2026-08-26T17:00:00.000Z"
    decided_at = "2026-08-26T17:05:00.000Z"
    private_result = {
        "jobId": body["jobId"],
        "attemptId": body["attemptId"],
        "leaseEpoch": body["leaseEpoch"],
        "competitionId": body["competitionId"],
        "jobCommitmentSha256": body["jobCommitmentSha256"],
        "evidenceBundleSha256": body["evidenceBundleSha256"],
        "engineSha256": body["engineSha256"],
        "summarySha256": body["summarySha256"],
        "summaryDigest": body["summaryDigest"],
        "transcriptSha256": body["transcriptSha256"],
        "compressedTranscriptSha256": body["compressedTranscriptSha256"],
        "projectionDigest": body["projectionDigest"],
        "matchId": body["matchId"],
        "chainHead": body["chainHead"],
        "truthStatus": TRUTH_STATUS,
        "publicationDecision": "not_reviewed_not_published",
        "rankingEligible": False,
        "verificationStatus": "verified_private",
        "verifiedAt": verified_at,
    }
    request_id = token("awpr1_", 2)
    request = {
        "requestId": request_id,
        "consent": {
            "manualApprovalRequiredV1": True,
            "publicProjectionReviewV1": True,
            "replayTranscriptReviewV1": True,
            "selfDeclaredLabelsReviewV1": True,
        },
        "requestedAt": requested_at,
        "jobCommitmentSha256": body["jobCommitmentSha256"],
        "evidenceBundleSha256": body["evidenceBundleSha256"],
        "resultBodySha256": result_body_sha,
        "projectionDigest": body["projectionDigest"],
        "transcriptSha256": body["transcriptSha256"],
        "chainHead": body["chainHead"],
        "truthStatus": TRUTH_STATUS,
        "verificationStatus": "verified_private",
    }
    decision = {
        "decisionId": token("awpd1_", 3),
        "requestId": request_id,
        "decision": "approved",
        "reasonCode": APPROVAL_REASON,
        "decidedAt": decided_at,
        "publicationDecision": APPROVAL_DECISION,
        "promotionStatus": APPROVAL_STATUS,
        "publicPromotionAuthorized": False,
        "rankingEligible": False,
    }
    case = {
        "schemaVersion": 1,
        "protocolVersion": DECISION_PROTOCOL,
        "status": "approved",
        "runnerId": token("awr1_", 1),
        "fingerprint": "1" * 64,
        "job": job,
        "request": request,
        "result": private_result,
        "privateEvidence": {"included": True, "bytes": len(body_text.encode("utf-8")), "body": body_text},
        "decision": decision,
        "publicationDecision": APPROVAL_DECISION,
        "promotionStatus": APPROVAL_STATUS,
        "publicPromotionAuthorized": False,
        "rankingEligible": False,
        "evidenceClass": APPROVAL_EVIDENCE_CLASS,
        **_false_flags(),
    }
    return {"reviewerAccess": "authorized_reviewer", "case": case}


def _rebind(wrapper: dict, body: dict) -> dict:
    body["evidenceBundleSha256"] = canonical_digest(
        {key: value for key, value in body.items() if key not in {"evidenceBundleSha256", "transcriptEncoded", "summary"}}
    )
    body_text = canonical_json(body, ensure_ascii=True)
    case = wrapper["case"]
    case["privateEvidence"] = {
        "included": True,
        "bytes": len(body_text.encode("utf-8")),
        "body": body_text,
    }
    result = case["result"]
    request = case["request"]
    for key in (
        "jobCommitmentSha256",
        "evidenceBundleSha256",
        "projectionDigest",
        "transcriptSha256",
        "chainHead",
    ):
        result[key] = body[key]
        request[key] = body[key]
    for key in ("summarySha256", "summaryDigest", "compressedTranscriptSha256", "matchId"):
        result[key] = body[key]
    request["resultBodySha256"] = sha256_hex(body_text)
    return wrapper


def _write_export(path: str, wrapper: dict) -> None:
    _write(path, json.dumps(wrapper, separators=(",", ":"), ensure_ascii=False))


def expect_refusal(name: str, root: str, work: str, wrapper: dict, phrase: str | None = None) -> None:
    export_path = os.path.join(work, name.replace(" ", "_") + ".json")
    out_path = os.path.join(work, name.replace(" ", "_") + "-out")
    _write_export(export_path, wrapper)
    try:
        prepare_publication_candidate(root, export_path, out_path)
    except PromotionCandidateError as error:
        ok(name, phrase is None or phrase in str(error), repr(str(error)))
        ok(name + " leaves no output", not os.path.lexists(out_path))
        return
    raise AssertionError(f"{name}: hostile export was accepted")


def _directory_bytes(path: str) -> dict[str, bytes]:
    return {
        os.path.relpath(os.path.join(current, name), path).replace(os.sep, "/"): Path(os.path.join(current, name)).read_bytes()
        for current, directories, files in os.walk(path)
        for name in sorted(files)
        for _ in [directories.sort()]
    }


def main() -> int:
    manifest_path = os.path.join(ROOT, "docs", "AGENTWARS_PUBLICATION_MANIFEST.v1.json")
    artifact_path = os.path.join(ROOT, "publishing", "agentwars-public-v1")
    manifest_before = sha256_hex(Path(manifest_path).read_bytes())
    artifact_before = _tree_digest(artifact_path)
    with tempfile.TemporaryDirectory(prefix="agentwars-promotion-check-") as work:
        transcript = _build_transcript(work)
        valid = _build_export(transcript)
        _valid_receipt, valid_records = project_receipt(transcript)
        private_field_records = copy.deepcopy(valid_records)
        private_field_records[1]["body"]["entrant_message"]["rawOutput"] = "provider text"
        try:
            _validate_transcript_content(private_field_records, Path(transcript).read_bytes())
        except PromotionCandidateError as error:
            ok("private provider-output field is refused", "forbidden" in str(error))
        else:
            raise AssertionError("private provider-output field was accepted")
        export_path = os.path.join(work, "approved-export.json")
        _write_export(export_path, valid)
        repo_output_probe = os.path.join(ROOT, ".agentwars-promotion-output-probe")
        ok("repository output probe starts absent", not os.path.lexists(repo_output_probe))
        try:
            prepare_publication_candidate(ROOT, export_path, repo_output_probe)
        except PromotionCandidateError as error:
            ok("repository-local candidate output is refused", "outside the source repository" in str(error))
            ok("repository-local refusal writes nothing", not os.path.lexists(repo_output_probe))
        else:
            raise AssertionError("repository-local candidate output was accepted")
        out_a, out_b = os.path.join(work, "candidate-a"), os.path.join(work, "candidate-b")
        result_a = prepare_publication_candidate(ROOT, export_path, out_a)
        result_b = prepare_publication_candidate(ROOT, export_path, out_b)
        ok("valid reviewer export prepares a candidate", result_a["status"] == "candidate_prepared_not_published")
        ok("same exact export is deterministic", _directory_bytes(out_a) == _directory_bytes(out_b))
        ok("candidate id and digest are deterministic", result_a["candidateId"] == result_b["candidateId"] and result_a["candidateDigest"] == result_b["candidateDigest"])
        candidate = json.loads(Path(out_a, "candidate.json").read_text(encoding="utf-8"))
        entry = json.loads(Path(out_a, "manifest-entry-candidate.json").read_text(encoding="utf-8"))
        preview = json.loads(Path(out_a, "public-receipt-preview.json").read_text(encoding="utf-8"))
        ok("candidate keeps every mutation authority false", all(candidate["authorizations"][key] is False for key in ("manifestMutationAuthorized", "generatedArtifactMutationAuthorized", "publicationAuthorized", "deploymentAuthorized", "rankingAuthorized", "providerOrModelAttested")))
        ok("candidate requires source-control review", candidate["authorizations"]["sourceControlReviewRequired"] is True and entry["candidateStatus"] == "source_control_review_required")
        ok("offline export origin is not attested", candidate["sourceExport"]["reviewerExportOriginAttested"] is False and candidate["sourceExport"]["serverSignatureVerified"] is False)
        ok("manifest candidate is held at eligible-for-review", entry["entryWithoutSequence"]["decision"] == "eligible_for_review" and entry["sequenceAssignmentRequired"] is True)
        ok("public preview retains false model attestation", preview["truth"]["modelAttested"] is False and preview["verification"]["effectiveVerdict"] == "PASS")
        ok("candidate transcript is byte exact", Path(out_a, "transcript.jsonl").read_bytes() == Path(transcript).read_bytes())
        try:
            prepare_publication_candidate(ROOT, export_path, out_a)
        except PromotionCandidateError as error:
            ok("existing output cannot be overwritten", "already exists" in str(error))
        else:
            raise AssertionError("existing output was overwritten")

        rejected = copy.deepcopy(valid)
        rejected["case"].update({
            "status": "rejected",
            "publicationDecision": "reviewer_rejected_not_published",
            "promotionStatus": "blocked",
            "evidenceClass": "reviewer_rejected_private_result",
        })
        rejected["case"]["decision"].update({
            "decision": "rejected",
            "reasonCode": "unsupported_public_claim",
            "publicationDecision": "reviewer_rejected_not_published",
            "promotionStatus": "blocked",
        })
        expect_refusal("rejected decision is not promotable", ROOT, work, rejected, "not an approved")

        attested = copy.deepcopy(valid)
        attested["case"]["modelAttested"] = True
        expect_refusal("true attestation is refused", ROOT, work, attested, "overstates")

        disabled_provider = copy.deepcopy(valid)
        disabled_provider["case"]["job"]["seats"][1].update(
            {
                "providerClaim": "claude_code",
                "selectedModelClaim": None,
                "variantClaim": None,
                "backendClaim": "claude_code:claude -p",
            }
        )
        expect_refusal(
            "disabled provider claim is refused",
            ROOT,
            work,
            disabled_provider,
            "unsupported",
        )

        projection_swap = copy.deepcopy(valid)
        projection_body = json.loads(projection_swap["case"]["privateEvidence"]["body"])
        projection_body["projectionDigest"] = "2" * 64
        _rebind(projection_swap, projection_body)
        expect_refusal("fully re-bound projection swap is refused", ROOT, work, projection_swap, "projection disagrees")

        concatenated = copy.deepcopy(valid)
        concatenated_body = json.loads(concatenated["case"]["privateEvidence"]["body"])
        import base64

        original_compressed = base64.urlsafe_b64decode(concatenated_body["transcriptEncoded"] + "=" * (-len(concatenated_body["transcriptEncoded"]) % 4))
        bad_compressed = original_compressed + zlib.compress(b"ignored")
        concatenated_body["transcriptEncoded"] = base64.urlsafe_b64encode(bad_compressed).decode("ascii").rstrip("=")
        concatenated_body["compressedTranscriptSha256"] = sha256_hex(bad_compressed)
        _rebind(concatenated, concatenated_body)
        expect_refusal("concatenated zlib frame is refused", ROOT, work, concatenated, "zlib frame")

        request_swap = copy.deepcopy(valid)
        request_swap["case"]["decision"]["requestId"] = token("awpr1_", 9)
        expect_refusal("decision request swap is refused", ROOT, work, request_swap, "still-private approval")

        duplicate_path = os.path.join(work, "duplicate-key.json")
        exact = Path(export_path).read_text(encoding="utf-8")
        _write(duplicate_path, exact.replace('{"reviewerAccess":', '{"reviewerAccess":"authorized_reviewer","reviewerAccess":', 1))
        try:
            prepare_publication_candidate(ROOT, duplicate_path, os.path.join(work, "duplicate-out"))
        except PromotionCandidateError as error:
            ok("duplicate JSON key is refused", "duplicate" in str(error))
        else:
            raise AssertionError("duplicate JSON key was accepted")

        symlink_path = os.path.join(work, "export-link.json")
        try:
            os.symlink(export_path, symlink_path)
        except OSError as error:
            skip("symlink export is refused", error.__class__.__name__)
        else:
            try:
                prepare_publication_candidate(ROOT, symlink_path, os.path.join(work, "symlink-out"))
            except PromotionCandidateError as error:
                ok("symlink export is refused", "reparse" in str(error) or "regular" in str(error))
            else:
                raise AssertionError("symlink export was accepted")

        cli_out = os.path.join(work, "cli-candidate")
        cli = subprocess.run(
            [
                sys.executable,
                os.path.join(ROOT, "bin", "prepare_publication_candidate.py"),
                "--reviewer-export",
                export_path,
                "--out",
                cli_out,
                "--reviewer-approved-export-v1",
                "--candidate-only-v1",
                "--no-publication-v1",
                "--source-control-review-required-v1",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            check=False,
        )
        ok("CLI requires and accepts all four acknowledgements", cli.returncode == 0, cli.stderr[-500:])
        cli_payload = json.loads(cli.stdout)
        ok("CLI reports candidate-only status", cli_payload["status"] == "candidate_prepared_not_published" and cli_payload["publicationAuthorized"] is False)
        missing_out = os.path.join(work, "missing-ack-candidate")
        missing = subprocess.run(
            [
                sys.executable,
                os.path.join(ROOT, "bin", "prepare_publication_candidate.py"),
                "--reviewer-export",
                export_path,
                "--out",
                missing_out,
                "--reviewer-approved-export-v1",
                "--candidate-only-v1",
                "--no-publication-v1",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
            check=False,
        )
        ok("CLI refuses a missing source-control acknowledgement", missing.returncode != 0 and not os.path.lexists(missing_out))
        ok(
            "failed candidates leave no staging directories",
            not any(name.startswith(".agentwars-promotion-candidate-") for name in os.listdir(work)),
        )

    ok("publication manifest remains byte exact", sha256_hex(Path(manifest_path).read_bytes()) == manifest_before)
    ok("generated public artifact remains byte exact", _tree_digest(artifact_path) == artifact_before)
    faulthandler.cancel_dump_traceback_later()
    print(f"AgentWars promotion candidate contracts: PASS ({PASSED} checks, {SKIPPED} skipped)")
    print("candidate-only / no manifest write / no publication / no provider / no network")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
