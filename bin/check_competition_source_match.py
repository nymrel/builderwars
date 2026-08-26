#!/usr/bin/env python3
"""Offline adversarial checks for non-leasing source-match preparation.

These checks create temporary public Agent Passports and stub signed server
responses. They forbid network and subprocess execution and never call a model
or provider.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import copy
import hashlib
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "bin")
sys.path.insert(0, ROOT)
sys.path.insert(0, BIN)

from arena.passport import sign_passport  # noqa: E402
from competitions import evidence_job as job  # noqa: E402
from competitions import source_match  # noqa: E402
from provider_hub.local_runner import RunnerClientError, digest_harness_file  # noqa: E402
from provider_hub.secrets import SecretValue  # noqa: E402
import agentwars as runner_cli  # noqa: E402
import run_agentwars_cross_provider_match as match_cli  # noqa: E402


CHECKS = 0
SECRET_SENTINEL = "private-provider-secret-must-not-render"


def check(condition, label):
    global CHECKS
    if not condition:
        raise AssertionError(label)
    CHECKS += 1


def expect_error(action, fragment):
    try:
        action()
    except RunnerClientError as error:
        check(fragment in str(error), f"refusal contains {fragment!r}")
        check(
            SECRET_SENTINEL not in str(error), "refusal never reflects provider secret"
        )
        return error
    raise AssertionError(f"expected RunnerClientError containing {fragment!r}")


def token(prefix, fill):
    return prefix + base64.urlsafe_b64encode(bytes([fill]) * 16).decode("ascii").rstrip(
        "="
    )


def profile(harness_digest):
    return {
        "localState": "runner_id_recorded_unverified",
        "runnerId": token("awr1_", 1),
        "fingerprint": "12" * 32,
        "harnessId": "agentwars-cli",
        "harnessDigest": harness_digest,
        "endpointOrigin": "https://nymrel.com",
    }


def make_passports(root, harness_digest):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    rows = []
    paths = []
    for seat, (name, backend) in enumerate(
        (
            ("Codex Redraft", "chatgpt_codex:codex exec"),
            (
                "OpenCode Dynasty",
                "opencode-provider:opencode-go/ox-alpha-free@max",
            ),
        )
    ):
        passport = sign_passport(
            Ed25519PrivateKey.generate(),
            display_name=name,
            version_label=f"source-match-v{seat + 1}",
            harness_sha256=harness_digest,
            claimed_model=backend,
        )
        path = root / f"seat{seat}-passport.json"
        path.write_text(json.dumps(passport, sort_keys=True) + "\n", encoding="utf-8")
        rows.append(passport)
        paths.append(str(path))
    return rows, tuple(paths)


def job_payload(harness_digest, passports=None):
    passport_rows = passports or (None, None)
    seats = []
    for seat, (name, provider, model, variant, backend, strategy) in enumerate(
        (
            (
                "Codex Redraft",
                "chatgpt_codex",
                None,
                None,
                "chatgpt_codex:codex exec",
                "win-now",
            ),
            (
                "OpenCode Dynasty",
                "opencode",
                "opencode-go/ox-alpha-free",
                "max",
                "opencode-provider:opencode-go/ox-alpha-free@max",
                "long-game",
            ),
        )
    ):
        passport = passport_rows[seat]
        seats.append(
            {
                "seat": seat,
                "entrant": name,
                "providerClaim": provider,
                "selectedModelClaim": model,
                "variantClaim": variant,
                "backendClaim": backend,
                "strategy": strategy,
                "agentId": None if passport is None else passport["agentId"],
                "versionId": None if passport is None else passport["versionId"],
            }
        )
    return {
        "jobId": token("awj1_", 2),
        "kind": job.COMPETITION_JOB_KIND,
        "competitionId": token("awc1_", 3),
        "requiredHarnessId": "agentwars-cli",
        "requiredHarnessDigest": harness_digest,
        "game": "fantasy_redraft",
        "seed": 9400,
        "engineSha256": job.COMPETITION_ENGINE_SHA256,
        "seats": seats,
        "requireSignedPassports": passports is not None,
        "requiredTruthStatus": job.COMPETITION_REQUIRED_TRUTH_STATUS,
        "publicationMode": job.COMPETITION_PUBLICATION_MODE,
        "maxAttempts": job.COMPETITION_JOB_MAX_ATTEMPTS,
    }


def response_base(runner_profile, request_sha):
    return {
        "schemaVersion": job.COMPETITION_JOB_SCHEMA_VERSION,
        "protocolVersion": job.COMPETITION_JOB_PROTOCOL,
        "runnerId": runner_profile["runnerId"],
        "fingerprint": runner_profile["fingerprint"],
        "requestBodySha256": request_sha,
        "evidenceClass": job.COMPETITION_JOB_EVIDENCE_CLASS,
        **{field: False for field in job.FALSE_ATTESTATIONS},
    }


def ready_response(runner_profile, payload):
    request_sha = hashlib.sha256(job.COMPETITION_JOB_PREPARE_BODY).hexdigest()
    return {
        **response_base(runner_profile, request_sha),
        "status": "ready",
        "job": payload,
    }


def validate_ready(runner_profile, payload):
    request_sha = hashlib.sha256(job.COMPETITION_JOB_PREPARE_BODY).hexdigest()
    return job.validate_competition_prepare_response(
        ready_response(runner_profile, payload),
        profile=runner_profile,
        request_body_sha256=request_sha,
    )


def check_signed_plan(root):
    harness_digest = digest_harness_file(str(source_match.FANTASY_HARNESS_PATH))
    runner_profile = profile(harness_digest)
    passports, passport_paths = make_passports(root, harness_digest)
    preparation = validate_ready(runner_profile, job_payload(harness_digest, passports))
    check(
        isinstance(preparation, job.CompetitionPreparation),
        "ready response returns exact preparation",
    )

    plan_path = root / "source-plan.json"
    match_dir = root / "source-match"
    summary_path = root / "source-summary.json"
    with (
        mock.patch.object(
            socket, "create_connection", side_effect=AssertionError("network forbidden")
        ),
        mock.patch.object(
            subprocess, "Popen", side_effect=AssertionError("subprocess forbidden")
        ),
        mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": SECRET_SENTINEL}),
    ):
        plan = source_match.build_source_match_plan(
            preparation,
            profile=runner_profile,
            plan_path=str(plan_path),
            match_directory=str(match_dir),
            summary_path=str(summary_path),
            passport_paths=passport_paths,
            backend_timeout=180,
        )
    check(plan["sourceStatus"] == "ready", "plan preserves ready source status")
    check(plan["jobId"] == preparation.job.job_id, "plan pins exact job id")
    check(
        plan["competitionId"] == preparation.job.competition_id,
        "plan pins exact competition id",
    )
    check(
        plan["jobCommitmentSha256"]
        == job.competition_job_commitment_sha256(preparation.job),
        "plan pins exact job commitment",
    )
    check(
        plan["providerExecutionRequested"] is False,
        "preparation never requests provider execution",
    )
    check(
        plan["subprocessExecutionRequested"] is False,
        "preparation never requests subprocess execution",
    )
    check(
        plan["signedPassportsBound"] is True,
        "plan records complete signed passport binding",
    )
    check(
        all(plan[field] is False for field in job.FALSE_ATTESTATIONS),
        "plan keeps all attestations false",
    )
    check(
        SECRET_SENTINEL not in json.dumps(plan),
        "plan never serializes ambient provider secret",
    )
    check(
        "--customer-local-v1" not in plan["launch"]["argv"],
        "plan cannot silently assert fresh customer consent",
    )
    check(
        "--provider-usage-v1" not in plan["launch"]["argv"],
        "plan cannot silently assert fresh provider consent",
    )
    check(
        plan["launch"]["requiredFreshConsentFlags"]
        == ["--customer-local-v1", "--provider-usage-v1"],
        "plan names both fresh consent gates",
    )

    parsed = match_cli.parser().parse_args(
        [*plan["launch"]["argv"], "--customer-local-v1", "--provider-usage-v1"]
    )
    check(
        parsed.seat0_provider == "chatgpt_codex",
        "fixed match parser accepts exact seat zero",
    )
    check(
        parsed.seat1_provider == "opencode"
        and parsed.seat1_model == "opencode-go/ox-alpha-free"
        and parsed.seat1_variant == "max",
        "fixed match parser accepts exact seat one",
    )
    check(
        tuple(parsed.agent_passports) == passport_paths,
        "fixed match parser receives exact passports",
    )
    check(
        parsed.seed == 9400 and parsed.game == "fantasy_redraft",
        "fixed match parser receives exact game and seed",
    )

    written = source_match.write_source_match_plan(str(plan_path), plan)
    check(written == plan_path.resolve(), "plan writer returns exact target")
    retained = json.loads(plan_path.read_text(encoding="utf-8"))
    check(retained == plan, "plan bytes round-trip without drift")
    expect_error(
        lambda: source_match.write_source_match_plan(str(plan_path), plan),
        "already exists",
    )
    changed = copy.deepcopy(plan)
    changed["seed"] = 9401
    expect_error(
        lambda: source_match.write_source_match_plan(
            str(root / "tampered-plan.json"), changed
        ),
        "digest",
    )
    return runner_profile, passports, passport_paths, preparation


def check_legacy_and_hostile(root, runner_profile, passports, passport_paths):
    harness_digest = runner_profile["harnessDigest"]
    legacy = validate_ready(runner_profile, job_payload(harness_digest))
    plan = source_match.build_source_match_plan(
        legacy,
        profile=runner_profile,
        plan_path=str(root / "legacy-plan.json"),
        match_directory=str(root / "legacy-match"),
        summary_path=str(root / "legacy-summary.json"),
        passport_paths=None,
        backend_timeout=10.1254,
    )
    check(
        plan["launch"]["backendTimeoutMilliseconds"] == 10_125,
        "timeout is normalized once",
    )
    check(
        all(row["passportSha256"] is None for row in plan["seats"]),
        "legacy plan invents no passport",
    )
    expect_error(
        lambda: source_match.build_source_match_plan(
            legacy,
            profile=runner_profile,
            plan_path=str(root / "legacy-extra-plan.json"),
            match_directory=str(root / "legacy-extra-match"),
            summary_path=str(root / "legacy-extra-summary.json"),
            passport_paths=passport_paths,
            backend_timeout=180,
        ),
        "exactly match",
    )

    signed = validate_ready(runner_profile, job_payload(harness_digest, passports))
    wrong_passports, wrong_paths = make_passports(root / "wrong", harness_digest)
    check(
        wrong_passports[0]["agentId"] != passports[0]["agentId"],
        "hostile passport identity differs",
    )
    expect_error(
        lambda: source_match.build_source_match_plan(
            signed,
            profile=runner_profile,
            plan_path=str(root / "wrong-plan.json"),
            match_directory=str(root / "wrong-match"),
            summary_path=str(root / "wrong-summary.json"),
            passport_paths=wrong_paths,
            backend_timeout=180,
        ),
        "differs",
    )
    expect_error(
        lambda: source_match.build_source_match_plan(
            signed,
            profile=runner_profile,
            plan_path=str(root / "nested-match" / "plan.json"),
            match_directory=str(root / "nested-match"),
            summary_path=str(root / "nested-summary.json"),
            passport_paths=passport_paths,
            backend_timeout=180,
        ),
        "nested",
    )

    request_sha = hashlib.sha256(job.COMPETITION_JOB_PREPARE_BODY).hexdigest()
    overclaim = ready_response(runner_profile, job_payload(harness_digest, passports))
    overclaim["modelAttested"] = True
    expect_error(
        lambda: job.validate_competition_prepare_response(
            overclaim, profile=runner_profile, request_body_sha256=request_sha
        ),
        "must keep modelAttested false",
    )
    unknown = ready_response(runner_profile, job_payload(harness_digest, passports))
    unknown["leaseToken"] = "hidden"
    expect_error(
        lambda: job.validate_competition_prepare_response(
            unknown, profile=runner_profile, request_body_sha256=request_sha
        ),
        "exact schema",
    )
    stale = job_payload(harness_digest, passports)
    stale["engineSha256"] = "0" * 64
    expect_error(lambda: validate_ready(runner_profile, stale), "engine snapshot")
    same_provider = job_payload(harness_digest, passports)
    same_provider["seats"][1] = {
        **same_provider["seats"][1],
        "providerClaim": "chatgpt_codex",
        "selectedModelClaim": None,
        "variantClaim": None,
        "backendClaim": "chatgpt_codex:codex exec",
    }
    expect_error(lambda: validate_ready(runner_profile, same_provider), "must differ")
    disabled_provider = job_payload(harness_digest, passports)
    disabled_provider["seats"][1].update(
        {
            "providerClaim": "claude_code",
            "selectedModelClaim": None,
            "variantClaim": None,
            "backendClaim": "claude_code:claude -p",
        }
    )
    expect_error(lambda: validate_ready(runner_profile, disabled_provider), "unsupported")

    busy = {
        **response_base(runner_profile, request_sha),
        "status": "busy",
        "job": {
            "jobId": token("awj1_", 2),
            "competitionId": token("awc1_", 3),
            "attemptsUsed": 1,
            "maxAttempts": 3,
        },
    }
    terminal = job.validate_competition_prepare_response(
        busy, profile=runner_profile, request_body_sha256=request_sha
    )
    check(
        isinstance(terminal, job.CompetitionPrepareTerminal),
        "busy preparation is terminal",
    )
    check(
        terminal.status == "busy" and terminal.truth_status is None,
        "busy response exposes no result",
    )


def check_cli_contract(root, runner_profile, passports, passport_paths):
    parsed = runner_cli.build_parser().parse_args(
        [
            "runner",
            "prepare-match",
            "--challenge-id",
            "challenge",
            "--plan-out",
            str(root / "cli-plan.json"),
            "--match-dir",
            str(root / "cli-match"),
            "--summary-file",
            str(root / "cli-summary.json"),
            "--agent-passports",
            *passport_paths,
            "--once",
        ]
    )
    check(
        parsed.func is runner_cli.cmd_runner_prepare_match,
        "prepare-match routes to bounded command",
    )
    check(parsed.once is True, "prepare-match requires one-request bound")
    with contextlib.redirect_stderr(io.StringIO()):
        try:
            runner_cli.build_parser().parse_args(
                [
                    "runner",
                    "prepare-match",
                    "--challenge-id",
                    "challenge",
                    "--plan-out",
                    "plan.json",
                    "--match-dir",
                    "match",
                    "--summary-file",
                    "summary.json",
                ]
            )
        except SystemExit as error:
            check(error.code == 2, "prepare-match refuses missing explicit once flag")
        else:
            raise AssertionError("prepare-match accepted missing --once")

    payload = job_payload(runner_profile["harnessDigest"], passports)
    response = ready_response(runner_profile, payload)
    signed = SimpleNamespace(
        body_sha256=hashlib.sha256(job.COMPETITION_JOB_PREPARE_BODY).hexdigest()
    )
    store = mock.Mock()
    store.load_profile.return_value = runner_profile
    store.load_key.return_value = object()
    output = io.StringIO()
    with (
        mock.patch.object(runner_cli, "RunnerStateStore", return_value=store),
        mock.patch.object(
            runner_cli,
            "_existing_key_passphrase",
            return_value=SecretValue(b"passphrase"),
        ),
        mock.patch.object(
            runner_cli, "sign_runner_request", return_value=signed
        ) as sign_request,
        mock.patch.object(
            runner_cli, "send_signed_request", return_value=(200, response, b"{}")
        ) as send_request,
        mock.patch.object(
            socket, "create_connection", side_effect=AssertionError("network forbidden")
        ),
        mock.patch.object(
            subprocess, "Popen", side_effect=AssertionError("subprocess forbidden")
        ),
        contextlib.redirect_stdout(output),
    ):
        result = parsed.func(parsed)
    check(result == 0, "prepare-match CLI succeeds on exact stub response")
    check(
        sign_request.call_args.kwargs["path"] == job.COMPETITION_JOB_PREPARE_PATH,
        "CLI signs exact prepare path",
    )
    check(
        sign_request.call_args.kwargs["body"] == job.COMPETITION_JOB_PREPARE_BODY,
        "CLI signs exact canonical body",
    )
    check(send_request.call_count == 1, "CLI sends exactly one non-leasing request")
    check(
        "acquired no lease" in output.getvalue(), "CLI states the non-leasing boundary"
    )
    check(
        "launched no subprocess" in output.getvalue(),
        "CLI states the non-execution boundary",
    )
    check(
        SECRET_SENTINEL not in output.getvalue(),
        "CLI output contains no provider secret",
    )


def main():
    parser = argparse.ArgumentParser(
        description="Offline adversarial checker for AgentWars source-match preparation."
    )
    parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="agentwars-source-match-") as temporary:
        root = Path(temporary)
        runner_profile, passports, passport_paths, _preparation = check_signed_plan(
            root
        )
        wrong_root = root / "wrong"
        wrong_root.mkdir()
        check_legacy_and_hostile(root, runner_profile, passports, passport_paths)
        check_cli_contract(root, runner_profile, passports, passport_paths)
    print(f"AgentWars source-match preparation: PASS ({CHECKS} checks)")
    print(
        "No provider, model, hosted service, subprocess, publication, or ranking was invoked."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
