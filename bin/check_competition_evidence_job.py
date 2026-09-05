#!/usr/bin/env python3
"""Adversarial offline checks for signed competition evidence submission.

The checker uses only deterministic stub entrants and temporary Ed25519
passports.  It never contacts a provider or hosted service.
"""

from __future__ import annotations

import base64
import argparse
import contextlib
import copy
import hashlib
import json
import os
import socket
import sys
import tempfile
import zlib
from pathlib import Path
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "bin")
sys.path.insert(0, ROOT)
sys.path.insert(0, BIN)

from arena.canonical import GENESIS, chain, digest, file_digest  # noqa: E402
from arena.match import run_reference_match as run_match, validate_manifest  # noqa: E402
from arena.passport import sign_passport  # noqa: E402
from arena.transcript import load  # noqa: E402
from competitions import evidence_job as job  # noqa: E402
from provider_hub.catalog import get_provider  # noqa: E402
from provider_hub.local_runner import RunnerClientError  # noqa: E402
from publishing.projection import verify_with_snapshot  # noqa: E402
from run_agentwars_league import final_scores, move_source_counts  # noqa: E402
import agentwars as runner_cli  # noqa: E402
import run_agentwars_cross_provider_match as candidate  # noqa: E402


CHECKS = 0
SECRET_SENTINEL = "private-provider-value-must-not-render"


def check(condition, label):
    global CHECKS
    if not condition:
        raise AssertionError(label)
    CHECKS += 1


def expect_error(action, fragment):
    try:
        action()
    except RunnerClientError as error:
        check(fragment in str(error), f"exact refusal contains {fragment!r}")
        check(SECRET_SENTINEL not in str(error), "refusal never reflects a provider secret")
        return error
    raise AssertionError(f"expected RunnerClientError containing {fragment!r}")


def token(prefix, fill):
    raw = bytes([fill]) * 16
    return prefix + base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def stub_runtime(
    name,
    provider,
    strategy,
    label,
    passport_path=None,
    *,
    stub_backend,
    model=None,
    variant=None,
):
    harness = os.path.join(ROOT, "entrants", "fantasy_model_harness.py")
    manifest = {
        "name": name,
        "cmd": [
            sys.executable,
            harness,
            "--name",
            name,
            "--strategy",
            strategy,
            "--backend",
            stub_backend,
        ],
        "env": [],
        "claimed_model": label,
        "execution_claim": "hybrid",
    }
    if passport_path is not None:
        manifest["agent_passport"] = str(passport_path)
    validate_manifest(manifest)
    entry = get_provider(provider)
    return candidate.SeatRuntime(
        spec=candidate.SeatSpec(
            name,
            provider,
            strategy,
            model=model,
            variant=variant,
            passport_path=None if passport_path is None else str(passport_path),
        ),
        backend_label=label,
        connection_mode=entry["connection_mode"],
        provider_class=entry["provider_class"],
        harness_class=entry["harness_class"],
        manifest=manifest,
        provisioned_environment={},
    )


def force_model_source_claims(path, ready_labels):
    """Create deterministic claim-only test data without claiming real inference."""

    previous = GENESIS
    output = []
    for sequence, raw in enumerate(load(str(path))):
        record = {
            "kind": raw["kind"],
            "seq": sequence,
            "body": copy.deepcopy(raw["body"]),
        }
        if record["kind"] == "ready":
            seat = record["body"].get("player")
            message = record["body"].get("entrant_message")
            if type(seat) is int and seat in (0, 1) and isinstance(message, dict):
                message["backend"] = ready_labels[seat]
        if record["kind"] == "move":
            message = record["body"].get("entrant_message")
            if isinstance(message, dict):
                message["note"] = (
                    "source=model;attempts=1;response_sha256="
                    + hashlib.sha256(f"offline-{sequence}".encode("ascii")).hexdigest()[:16]
                )
        record_hash = chain(previous, record)
        output.append({**record, "prev": previous, "hash": record_hash})
        previous = record_hash
    Path(path).write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
            for row in output
        ),
        encoding="utf-8",
        newline="\n",
    )
    return previous


def generate_evidence(root, *, signed_passports):
    harness_digest = file_digest(os.path.join(ROOT, "entrants", "fantasy_model_harness.py"))
    names = ("Offline Codex", "Offline OpenCode")
    labels = (
        "chatgpt_codex:codex exec",
        "opencode-provider:opencode-go/ox-alpha-free@max",
    )
    passport_paths = [None, None]
    passports = [None, None]
    if signed_passports:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        for seat in (0, 1):
            passport = sign_passport(
                Ed25519PrivateKey.generate(),
                display_name=names[seat],
                version_label=f"offline-v{seat + 1}",
                harness_sha256=harness_digest,
                claimed_model=labels[seat],
            )
            path = root / f"seat{seat}-passport.json"
            path.write_text(json.dumps(passport, sort_keys=True) + "\n", encoding="utf-8")
            passport_paths[seat] = path
            passports[seat] = passport
    runtimes = [
        stub_runtime(
            names[0],
            "chatgpt_codex",
            "win-now",
            labels[0],
            passport_paths[0],
            stub_backend="stub:seat0",
        ),
        stub_runtime(
            names[1],
            "opencode",
            "long-game",
            labels[1],
            passport_paths[1],
            stub_backend="stub:seat1",
            model="opencode-go/ox-alpha-free",
            variant="max",
        ),
    ]
    match_root = root / ("signed-match" if signed_passports else "legacy-match")
    with (
        mock.patch.object(socket, "socket", side_effect=AssertionError("network forbidden")),
        mock.patch.object(socket, "create_connection", side_effect=AssertionError("network forbidden")),
    ):
        result = run_match(
            game_name="fantasy_redraft",
            seed=9400,
            entrants=[runtime.manifest for runtime in runtimes],
            provisioned_envs=[{}, {}],
            out_dir=str(match_root),
            move_timeout_s=30,
        )
        # The deterministic stub may deliberately exercise fallback parsing.
        # Rebind only the source-claim notes for protocol testing; these remain
        # self-declared and unattested, and no checker output calls them genuine.
        result["chain_head"] = force_model_source_claims(result["transcript"], labels)
        report = verify_with_snapshot(result["transcript"])
    candidate.audit_transcript(
        result=result,
        report=report,
        runtimes=runtimes,
        expected_game="fantasy_redraft",
        expected_seed=9400,
    )
    sources = move_source_counts(result["transcript"], [runtime.manifest for runtime in runtimes])
    summary = candidate.build_summary(
        result={**result, "game": "fantasy_redraft", "seed": 9400},
        report=report,
        runtimes=runtimes,
        source_counts=sources,
        scores=final_scores(result["transcript"]),
    )
    summary_path = root / ("signed-summary.json" if signed_passports else "legacy-summary.json")
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    return {
        "summary": summary,
        "summary_path": summary_path,
        "transcript_path": Path(result["transcript"]),
        "harness_digest": harness_digest,
        "passports": passports,
    }


def profile_for(harness_digest):
    return {
        "runnerId": token("awr1_", 1),
        "fingerprint": "12" * 32,
        "harnessId": "agentwars-cli",
        "harnessDigest": harness_digest,
    }


def response_base(profile, request_sha):
    return {
        "schemaVersion": job.COMPETITION_JOB_SCHEMA_VERSION,
        "protocolVersion": job.COMPETITION_JOB_PROTOCOL,
        "runnerId": profile["runnerId"],
        "fingerprint": profile["fingerprint"],
        "requestBodySha256": request_sha,
        "evidenceClass": job.COMPETITION_JOB_EVIDENCE_CLASS,
        **{field: False for field in job.FALSE_ATTESTATIONS},
    }


def job_payload(evidence, *, require_signed_passports):
    summary = evidence["summary"]
    rows = []
    for seat, row in enumerate(summary["seats"]):
        passport = evidence["passports"][seat]
        rows.append(
            {
                "seat": seat,
                "entrant": row["entrant"],
                "providerClaim": row["providerClaim"],
                "selectedModelClaim": row["selectedModelClaim"],
                "variantClaim": row["variantClaim"],
                "backendClaim": row["backendClaim"],
                "strategy": row["strategy"],
                "agentId": None if passport is None else passport["agentId"],
                "versionId": None if passport is None else passport["versionId"],
            }
        )
    return {
        "jobId": token("awj1_", 2),
        "kind": job.COMPETITION_JOB_KIND,
        "competitionId": token("awc1_", 3),
        "requiredHarnessId": "agentwars-cli",
        "requiredHarnessDigest": evidence["harness_digest"],
        "game": summary["game"],
        "seed": summary["seed"],
        "engineSha256": summary["verification"]["engineDigest"],
        "seats": rows,
        "requireSignedPassports": require_signed_passports,
        "requiredTruthStatus": job.COMPETITION_REQUIRED_TRUTH_STATUS,
        "publicationMode": job.COMPETITION_PUBLICATION_MODE,
        "maxAttempts": job.COMPETITION_JOB_MAX_ATTEMPTS,
    }


def grant_response(profile, payload):
    request_sha = hashlib.sha256(job.COMPETITION_JOB_POLL_BODY).hexdigest()
    return {
        **response_base(profile, request_sha),
        "status": "granted",
        "recovery": False,
        "attempt": {
            "attemptId": token("awa1_", 4),
            "leaseEpoch": 1,
            "attemptNumber": 1,
            "leaseExpiresAt": "2026-08-26T13:00:00.000Z",
        },
        "job": payload,
    }


def private_result_from_payload(payload):
    keys = {
        "jobId",
        "attemptId",
        "leaseEpoch",
        "competitionId",
        "jobCommitmentSha256",
        "evidenceBundleSha256",
        "engineSha256",
        "summarySha256",
        "summaryDigest",
        "transcriptSha256",
        "compressedTranscriptSha256",
        "projectionDigest",
        "matchId",
        "chainHead",
        "truthStatus",
        "publicationDecision",
        "rankingEligible",
    }
    return {
        **{key: payload[key] for key in keys},
        "verificationStatus": "verified_private",
        "verifiedAt": "2026-08-26T12:59:59.000Z",
    }


def rewrite_summary(path, summary, **changes):
    changed = copy.deepcopy(summary)
    changed.update(changes)
    core = {key: value for key, value in changed.items() if key != "summaryDigest"}
    changed["summaryDigest"] = digest(core)
    path.write_text(json.dumps(changed, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return changed


def check_signed_happy_path(root):
    evidence_files = generate_evidence(root, signed_passports=True)
    profile = profile_for(evidence_files["harness_digest"])
    payload = job_payload(evidence_files, require_signed_passports=True)
    poll = grant_response(profile, payload)
    request_sha = hashlib.sha256(job.COMPETITION_JOB_POLL_BODY).hexdigest()
    grant = job.validate_competition_poll_response(
        poll, profile=profile, request_body_sha256=request_sha
    )
    check(isinstance(grant, job.CompetitionGrant), "signed competition poll returns an exact grant")
    check(grant.job.require_signed_passports is True, "signed competition pins both passports")
    check(
        grant.job.engine_sha256 == job.COMPETITION_ENGINE_SHA256,
        "signed competition pins the current exact engine snapshot",
    )
    claude_poll = copy.deepcopy(poll)
    claude_poll["job"]["seats"][1].update(
        {
            "providerClaim": "claude_code",
            "selectedModelClaim": None,
            "variantClaim": None,
            "backendClaim": "claude_code:claude -p",
        }
    )
    expect_error(
        lambda: job.validate_competition_poll_response(
            claude_poll, profile=profile, request_body_sha256=request_sha
        ),
        "unsupported",
    )
    built = job.build_competition_evidence(
        grant,
        summary_path=str(evidence_files["summary_path"]),
        transcript_path=str(evidence_files["transcript_path"]),
    )
    check(len(built.result_body) <= 65536, "signed evidence fits the signed request cap")
    decoded = json.loads(built.result_body)
    check(set(decoded).issuperset(job.FALSE_ATTESTATIONS), "result carries all false attestations")
    check(all(decoded[field] is False for field in job.FALSE_ATTESTATIONS), "result never attests execution")
    check(decoded["publicationDecision"] == "not_reviewed_not_published", "result stays unpublished")
    check(decoded["rankingEligible"] is False, "result stays ranking-ineligible")
    check(decoded["truthStatus"] == "model_influenced_unattested", "result preserves truth status")
    check(SECRET_SENTINEL not in built.result_body.decode("utf-8"), "result contains no provider secret")
    check(str(root) not in built.result_body.decode("utf-8"), "result contains no local path")
    restored = job.decode_competition_transcript(
        decoded["transcriptEncoded"], expected_sha256=decoded["transcriptSha256"]
    )
    check(restored == evidence_files["transcript_path"].read_bytes(), "compressed transcript round-trips")

    result_request_sha = hashlib.sha256(built.result_body).hexdigest()
    response = {
        **response_base(profile, result_request_sha),
        "status": "recorded",
        "duplicate": False,
        "result": private_result_from_payload(decoded),
    }
    receipt = job.validate_competition_result_response(
        response,
        profile=profile,
        request_body_sha256=result_request_sha,
        grant=grant,
        evidence=built,
    )
    check(receipt.verification_status == "verified_private", "server echo remains private")
    check(receipt.truth_status == "model_influenced_unattested", "server echo remains unattested")

    duplicate = copy.deepcopy(response)
    duplicate["duplicate"] = True
    duplicate_receipt = job.validate_competition_result_response(
        duplicate,
        profile=profile,
        request_body_sha256=result_request_sha,
        grant=grant,
        evidence=built,
    )
    check(duplicate_receipt.duplicate is True, "exact duplicate result is idempotent")
    return evidence_files, profile, payload, poll, grant, built, response


def check_legacy_happy_path(root):
    evidence_files = generate_evidence(root, signed_passports=False)
    profile = profile_for(evidence_files["harness_digest"])
    payload = job_payload(evidence_files, require_signed_passports=False)
    grant = job.validate_competition_poll_response(
        grant_response(profile, payload),
        profile=profile,
        request_body_sha256=hashlib.sha256(job.COMPETITION_JOB_POLL_BODY).hexdigest(),
    )
    built = job.build_competition_evidence(
        grant,
        summary_path=str(evidence_files["summary_path"]),
        transcript_path=str(evidence_files["transcript_path"]),
    )
    check(
        built.summary["verification"]["signedHarnessVersionsVerified"] is False,
        "legacy evidence stays explicitly unsigned",
    )
    check(
        all(seat.agent_id is None for seat in grant.job.seats),
        "legacy private transport invents no agent identity",
    )


def check_hostile_contracts(root, state):
    evidence_files, profile, payload, poll, grant, built, response = state
    request_sha = hashlib.sha256(job.COMPETITION_JOB_POLL_BODY).hexdigest()

    unknown = copy.deepcopy(poll)
    unknown["job"]["serverCommand"] = ["powershell", "-Command", "whoami"]
    expect_error(
        lambda: job.validate_competition_poll_response(
            unknown, profile=profile, request_body_sha256=request_sha
        ),
        "invalid exact schema",
    )
    overclaim = copy.deepcopy(poll)
    overclaim["modelAttested"] = True
    expect_error(
        lambda: job.validate_competition_poll_response(
            overclaim, profile=profile, request_body_sha256=request_sha
        ),
        "modelAttested false",
    )
    same_provider = copy.deepcopy(poll)
    same_provider["job"]["seats"][1].update(
        {
            "providerClaim": same_provider["job"]["seats"][0]["providerClaim"],
            "selectedModelClaim": same_provider["job"]["seats"][0]["selectedModelClaim"],
            "variantClaim": same_provider["job"]["seats"][0]["variantClaim"],
            "backendClaim": same_provider["job"]["seats"][0]["backendClaim"],
        }
    )
    expect_error(
        lambda: job.validate_competition_poll_response(
            same_provider, profile=profile, request_body_sha256=request_sha
        ),
        "provider claims must differ",
    )
    arbitrary_provider = copy.deepcopy(poll)
    arbitrary_provider["job"]["seats"][1].update(
        {
            "providerClaim": "custom_agent",
            "selectedModelClaim": None,
            "variantClaim": None,
            "backendClaim": "custom_agent:customer command",
        }
    )
    expect_error(
        lambda: job.validate_competition_poll_response(
            arbitrary_provider, profile=profile, request_body_sha256=request_sha
        ),
        "provider claim is unsupported",
    )
    partial = copy.deepcopy(poll)
    partial["job"]["seats"][1]["agentId"] = None
    partial["job"]["seats"][1]["versionId"] = None
    expect_error(
        lambda: job.validate_competition_poll_response(
            partial, profile=profile, request_body_sha256=request_sha
        ),
        "partially bind signed passports",
    )
    command_field = copy.deepcopy(poll)
    command_field["job"]["seats"][0]["command"] = "unsafe"
    expect_error(
        lambda: job.validate_competition_poll_response(
            command_field, profile=profile, request_body_sha256=request_sha
        ),
        "invalid exact schema",
    )
    wrong_harness = copy.deepcopy(poll)
    wrong_harness["job"]["requiredHarnessDigest"] = "0" * 64
    expect_error(
        lambda: job.validate_competition_poll_response(
            wrong_harness, profile=profile, request_body_sha256=request_sha
        ),
        "paired harness commitment",
    )
    wrong_engine_poll = copy.deepcopy(poll)
    wrong_engine_poll["job"]["engineSha256"] = "0" * 64
    expect_error(
        lambda: job.validate_competition_poll_response(
            wrong_engine_poll, profile=profile, request_body_sha256=request_sha
        ),
        "engine snapshot is not current",
    )
    model_on_subscription = copy.deepcopy(poll)
    model_on_subscription["job"]["seats"][0]["selectedModelClaim"] = "vendor/model"
    expect_error(
        lambda: job.validate_competition_poll_response(
            model_on_subscription, profile=profile, request_body_sha256=request_sha
        ),
        "does not accept a model claim",
    )
    missing_model = copy.deepcopy(poll)
    missing_model["job"]["seats"][0].update(
        {
            "providerClaim": "opencode",
            "selectedModelClaim": None,
            "variantClaim": None,
            "backendClaim": "opencode-provider:vendor/model@max",
        }
    )
    expect_error(
        lambda: job.validate_competition_poll_response(
            missing_model, profile=profile, request_body_sha256=request_sha
        ),
        "model claim is required",
    )
    invalid_variant = copy.deepcopy(poll)
    invalid_variant["job"]["seats"][0]["variantClaim"] = "max"
    expect_error(
        lambda: job.validate_competition_poll_response(
            invalid_variant, profile=profile, request_body_sha256=request_sha
        ),
        "does not accept a variant claim",
    )
    invalid_model_shape = copy.deepcopy(poll)
    invalid_model_shape["job"]["seats"][0].update(
        {
            "providerClaim": "opencode",
            "selectedModelClaim": "model-without-provider",
            "variantClaim": "max",
            "backendClaim": "opencode-provider:model-without-provider@max",
        }
    )
    expect_error(
        lambda: job.validate_competition_poll_response(
            invalid_model_shape, profile=profile, request_body_sha256=request_sha
        ),
        "model claim is invalid",
    )
    changed_backend = copy.deepcopy(poll)
    changed_backend["job"]["seats"][0]["backendClaim"] = "chatgpt_codex:other"
    expect_error(
        lambda: job.validate_competition_poll_response(
            changed_backend, profile=profile, request_body_sha256=request_sha
        ),
        "backend claim does not match provider options",
    )
    wrong_version_poll = copy.deepcopy(poll)
    wrong_version_poll["job"]["seats"][0]["versionId"] = "0" * 64
    wrong_version_grant = job.validate_competition_poll_response(
        wrong_version_poll, profile=profile, request_body_sha256=request_sha
    )
    expect_error(
        lambda: job.build_competition_evidence(
            wrong_version_grant,
            summary_path=str(evidence_files["summary_path"]),
            transcript_path=str(evidence_files["transcript_path"]),
        ),
        "passport changed",
    )

    ranking_path = root / "ranking-summary.json"
    rewrite_summary(
        ranking_path,
        evidence_files["summary"],
        universalProviderOrModelRankingEligible=True,
    )
    expect_error(
        lambda: job.build_competition_evidence(
            grant,
            summary_path=str(ranking_path),
            transcript_path=str(evidence_files["transcript_path"]),
        ),
        "ranking eligibility",
    )
    published_path = root / "published-summary.json"
    rewrite_summary(
        published_path,
        evidence_files["summary"],
        publicationDecision="published",
    )
    expect_error(
        lambda: job.build_competition_evidence(
            grant,
            summary_path=str(published_path),
            transcript_path=str(evidence_files["transcript_path"]),
        ),
        "not private and unpublished",
    )
    attested_path = root / "attested-summary.json"
    rewrite_summary(attested_path, evidence_files["summary"], modelAttested=True)
    expect_error(
        lambda: job.build_competition_evidence(
            grant,
            summary_path=str(attested_path),
            transcript_path=str(evidence_files["transcript_path"]),
        ),
        "modelAttested false",
    )
    truth_boundary_path = root / "truth-boundary-summary.json"
    rewrite_summary(
        truth_boundary_path,
        evidence_files["summary"],
        truthBoundary="A replay attests the provider and model.",
    )
    expect_error(
        lambda: job.build_competition_evidence(
            grant,
            summary_path=str(truth_boundary_path),
            transcript_path=str(evidence_files["transcript_path"]),
        ),
        "truth boundary",
    )
    bool_seed_path = root / "bool-seed-summary.json"
    rewrite_summary(bool_seed_path, evidence_files["summary"], seed=True)
    expect_error(
        lambda: job.build_competition_evidence(
            grant,
            summary_path=str(bool_seed_path),
            transcript_path=str(evidence_files["transcript_path"]),
        ),
        "assigned game or seed",
    )
    bool_source_path = root / "bool-source-summary.json"
    bool_source_seats = copy.deepcopy(evidence_files["summary"]["seats"])
    bool_source_seats[0]["moveSourceClaims"]["model"] = True
    rewrite_summary(bool_source_path, evidence_files["summary"], seats=bool_source_seats)
    expect_error(
        lambda: job.build_competition_evidence(
            grant,
            summary_path=str(bool_source_path),
            transcript_path=str(evidence_files["transcript_path"]),
        ),
        "move-source claim type",
    )
    duplicate_json = root / "duplicate-summary.json"
    duplicate_json.write_text('{"schemaVersion":1,"schemaVersion":2}\n', encoding="utf-8")
    expect_error(
        lambda: job.build_competition_evidence(
            grant,
            summary_path=str(duplicate_json),
            transcript_path=str(evidence_files["transcript_path"]),
        ),
        "strict UTF-8 JSON",
    )
    transcript_tamper = root / "tampered.jsonl"
    raw = evidence_files["transcript_path"].read_bytes()
    transcript_tamper.write_bytes(raw[:-2] + b"x\n")
    expect_error(
        lambda: job.build_competition_evidence(
            grant,
            summary_path=str(evidence_files["summary_path"]),
            transcript_path=str(transcript_tamper),
        ),
        "does not bind",
    )
    expect_error(
        lambda: job.build_competition_evidence(
            grant,
            summary_path=str(evidence_files["summary_path"]),
            transcript_path=str(evidence_files["summary_path"]),
        ),
        "paths must differ",
    )
    summary_bytes = evidence_files["summary_path"].read_bytes()
    transcript_bytes = evidence_files["transcript_path"].read_bytes()
    with mock.patch.object(
        job,
        "_read_bounded",
        side_effect=[summary_bytes, transcript_bytes, transcript_bytes + b"changed"],
    ):
        expect_error(
            lambda: job.build_competition_evidence(
                grant,
                summary_path=str(evidence_files["summary_path"]),
                transcript_path=str(evidence_files["transcript_path"]),
            ),
            "changed during replay verification",
        )

    decoded = json.loads(built.result_body)
    corrupted = decoded["transcriptEncoded"][:-1] + (
        "A" if decoded["transcriptEncoded"][-1] != "A" else "B"
    )
    expect_error(
        lambda: job.decode_competition_transcript(
            corrupted, expected_sha256=decoded["transcriptSha256"]
        ),
        "transcript",
    )
    bomb = base64.urlsafe_b64encode(
        zlib.compress(b"x" * (job.MAX_TRANSCRIPT_BYTES + 1), level=9)
    ).decode("ascii").rstrip("=")
    expect_error(
        lambda: job.decode_competition_transcript(
            bomb, expected_sha256=hashlib.sha256(b"x").hexdigest()
        ),
        "exact frame",
    )
    first_stream = zlib.compress(b"safe\n")
    concatenated = base64.urlsafe_b64encode(first_stream + zlib.compress(b"extra\n")).decode("ascii").rstrip("=")
    expect_error(
        lambda: job.decode_competition_transcript(
            concatenated, expected_sha256=hashlib.sha256(b"safe\n").hexdigest()
        ),
        "exact frame",
    )

    result_request_sha = hashlib.sha256(built.result_body).hexdigest()
    response_overclaim = copy.deepcopy(response)
    response_overclaim["matchExecutionAttested"] = True
    expect_error(
        lambda: job.validate_competition_result_response(
            response_overclaim,
            profile=profile,
            request_body_sha256=result_request_sha,
            grant=grant,
            evidence=built,
        ),
        "matchExecutionAttested false",
    )
    response_ranked = copy.deepcopy(response)
    response_ranked["result"]["rankingEligible"] = True
    expect_error(
        lambda: job.validate_competition_result_response(
            response_ranked,
            profile=profile,
            request_body_sha256=result_request_sha,
            grant=grant,
            evidence=built,
        ),
        "release status",
    )
    response_bundle = copy.deepcopy(response)
    response_bundle["result"]["evidenceBundleSha256"] = "0" * 64
    expect_error(
        lambda: job.validate_competition_result_response(
            response_bundle,
            profile=profile,
            request_body_sha256=result_request_sha,
            grant=grant,
            evidence=built,
        ),
        "changed evidenceBundleSha256",
    )


def check_cli_contract():
    parser = runner_cli.build_parser()
    help_text = parser.format_help()
    check("customer-local" in help_text, "top-level runner help remains customer-local")
    submit = parser.parse_args(
        [
            "runner",
            "submit-match",
            "--challenge-id",
            "awc_ignored_by_parser",
            "--summary-file",
            "summary.json",
            "--transcript-file",
            "match.jsonl",
            "--once",
            "--customer-local-v1",
            "--provider-usage-v1",
            "--private-evidence-upload-v1",
        ]
    )
    check(submit.func is runner_cli.cmd_runner_submit_match, "submit-match routes to bounded command")
    check(submit.once is True, "submit-match requires one-job bound")
    for missing in (
        "--once",
        "--customer-local-v1",
        "--provider-usage-v1",
        "--private-evidence-upload-v1",
    ):
        argv = [
            "runner",
            "submit-match",
            "--challenge-id",
            "c",
            "--summary-file",
            "s",
            "--transcript-file",
            "t",
            "--once",
            "--customer-local-v1",
            "--provider-usage-v1",
            "--private-evidence-upload-v1",
        ]
        argv.remove(missing)
        with open(os.devnull, "w", encoding="utf-8") as sink, contextlib.redirect_stderr(sink):
            try:
                parser.parse_args(argv)
            except SystemExit as error:
                check(error.code == 2, f"missing {missing} fails before any request")
            else:
                raise AssertionError(f"parser accepted missing {missing}")


def check_retained_evidence(summary_path, transcript_path):
    summary_file = Path(summary_path)
    transcript_file = Path(transcript_path)
    summary = json.loads(summary_file.read_text(encoding="utf-8"))
    records = load(str(transcript_file))
    header = records[0]["body"]
    raw_seats = header["entrants"]
    harness_digests = {
        row.get("script", {}).get("sha256") for row in raw_seats if isinstance(row, dict)
    }
    check(len(harness_digests) == 1, "retained match uses one exact paired harness digest")
    harness_digest = next(iter(harness_digests))
    passports = [row.get("agent_passport") for row in raw_seats]
    signed = [isinstance(value, dict) for value in passports]
    check(not any(signed) or all(signed), "retained match has complete or zero passport coverage")
    profile = profile_for(harness_digest)
    payload = {
        "jobId": token("awj1_", 31),
        "kind": job.COMPETITION_JOB_KIND,
        "competitionId": token("awc1_", 32),
        "requiredHarnessId": "agentwars-cli",
        "requiredHarnessDigest": harness_digest,
        "game": summary["game"],
        "seed": summary["seed"],
        "engineSha256": summary["verification"]["engineDigest"],
        "seats": [
            {
                "seat": index,
                "entrant": row["entrant"],
                "providerClaim": row["providerClaim"],
                "selectedModelClaim": row["selectedModelClaim"],
                "variantClaim": row["variantClaim"],
                "backendClaim": row["backendClaim"],
                "strategy": row["strategy"],
                "agentId": passports[index].get("agentId") if signed[index] else None,
                "versionId": passports[index].get("versionId") if signed[index] else None,
            }
            for index, row in enumerate(summary["seats"])
        ],
        "requireSignedPassports": all(signed),
        "requiredTruthStatus": job.COMPETITION_REQUIRED_TRUTH_STATUS,
        "publicationMode": job.COMPETITION_PUBLICATION_MODE,
        "maxAttempts": job.COMPETITION_JOB_MAX_ATTEMPTS,
    }
    request_sha = hashlib.sha256(job.COMPETITION_JOB_POLL_BODY).hexdigest()
    grant = job.validate_competition_poll_response(
        grant_response(profile, payload), profile=profile, request_body_sha256=request_sha
    )
    built = job.build_competition_evidence(
        grant, summary_path=str(summary_file), transcript_path=str(transcript_file)
    )
    result = json.loads(built.result_body)
    restored = job.decode_competition_transcript(
        result["transcriptEncoded"], expected_sha256=result["transcriptSha256"]
    )
    check(restored == transcript_file.read_bytes(), "retained transcript round-trips exactly")
    check(result["truthStatus"] == "model_influenced_unattested", "retained truth stays unattested")
    check(result["publicationDecision"] == "not_reviewed_not_published", "retained match stays private")
    check(result["rankingEligible"] is False, "retained match stays ranking-ineligible")
    check(all(result[field] is False for field in job.FALSE_ATTESTATIONS), "retained attestations stay false")
    print(
        "[PASS] retained evidence "
        + json.dumps(
            {
                "matchId": summary["matchId"],
                "truthStatus": result["truthStatus"],
                "signedPassports": all(signed),
                "resultBodyBytes": len(built.result_body),
                "sourceTranscriptBytes": len(restored),
                "evidenceBundleSha256": built.evidence_bundle_sha256,
                "jobCommitmentSha256": result["jobCommitmentSha256"],
                "summarySha256": built.summary_sha256,
                "transcriptSha256": built.transcript_sha256,
                "compressedTranscriptSha256": built.compressed_transcript_sha256,
                "projectionDigest": built.projection_digest,
            },
            sort_keys=True,
        )
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Offline adversarial checker for AgentWars competition evidence jobs."
    )
    parser.add_argument("--retained-summary")
    parser.add_argument("--retained-transcript")
    args = parser.parse_args(argv)
    if bool(args.retained_summary) != bool(args.retained_transcript):
        parser.error("--retained-summary and --retained-transcript must be supplied together")
    with tempfile.TemporaryDirectory(prefix="agentwars-competition-job-") as temp:
        root = Path(temp)
        state = check_signed_happy_path(root)
        check_legacy_happy_path(root)
        check_hostile_contracts(root, state)
        check_cli_contract()
    if args.retained_summary:
        check_retained_evidence(args.retained_summary, args.retained_transcript)
    print(f"AgentWars competition evidence job: PASS ({CHECKS} checks)")
    print("offline stubs only / exact signed transport / replay-bound private evidence /")
    print("no provider calls / no arbitrary code / no publication or ranking overclaim")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
