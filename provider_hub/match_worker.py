"""Strict customer-local execution for the closed AgentWars fixture job.

This module deliberately supports one built-in, deterministic SHA-256 fixture
only.  It never launches a subprocess, reads provider credentials or sessions,
calls a model, or treats digest conformance as model/harness/match execution
evidence.  The paired Ed25519 key authenticates transport; all eight execution
and provider attestations remain false.
"""

from __future__ import annotations

import base64
import dataclasses
import hashlib
import hmac
import json
import re

from provider_hub.local_runner import (
    RunnerClientError,
    validate_canonical_instant,
    validate_fingerprint,
    validate_harness_id,
    validate_runner_id,
)


MATCH_JOB_SCHEMA_VERSION = 1
MATCH_JOB_PROTOCOL = "agentwars.match_job.v1"
MATCH_JOB_EVIDENCE_CLASS = "active_local_signing_key_possession"
MATCH_JOB_KIND = "closed_deterministic_fixture"
MATCH_JOB_POLL_PATH = "/api/builderwars/jobs/poll"
MATCH_JOB_RENEW_PATH = "/api/builderwars/jobs/renew"
MATCH_JOB_RESULT_PATH = "/api/builderwars/jobs/result"
MATCH_JOB_ABANDON_PATH = "/api/builderwars/jobs/abandon"
MATCH_JOB_POLL_BODY = b'{"poll":1}'
MATCH_JOB_MAX_RENEWS = 5
MATCH_JOB_MAX_ATTEMPTS = 3
MATCH_JOB_ENGINE_ID = "agentwars.fixture.sha256.v1"
MATCH_JOB_RULESET_ID = "agentwars.fixture.rules.v1"
MATCH_JOB_ENGINE_MANIFEST = "\n".join((
    "agentwars.fixture.engine.v1",
    r'''input-domain=utf8("agentwars.fixture.input.v1\0")''',
    "input-frame=domain|utf8(runner-id)|0x00|utf8(harness-id)|0x00|ascii-lowerhex(harness-digest)|0x00|ascii-base64url(seed)|0x00",
    "input-output=sha256(frame):32-public-bytes",
    "input-commitment=sha256(input-bytes)",
    r'''output-domain=utf8("agentwars.fixture.output.v1\0")''',
    "output-frame=domain|input-bytes",
    "output-result=sha256(frame)",
    r'''transcript-frame=utf8("agentwars.fixture.transcript.v1\njob-id:<job-id>\nattempt-id:<attempt-id>\nlease-epoch:<base10-integer>\nengine-sha256:<ascii-lowerhex>\ninput-sha256:<ascii-lowerhex>\noutput-sha256:<ascii-lowerhex>\n")''',
    "transcript-result=sha256(utf8-frame)",
    "",
))
MATCH_JOB_RULES_MANIFEST = "\n".join((
    "agentwars.fixture.rules.v1",
    "kind=closed_deterministic_fixture",
    "expected-output-withheld=true",
    "execution-attestations=false",
    "",
))
MATCH_JOB_ENGINE_SHA256 = hashlib.sha256(MATCH_JOB_ENGINE_MANIFEST.encode("utf-8")).hexdigest()
MATCH_JOB_RULES_SHA256 = hashlib.sha256(MATCH_JOB_RULES_MANIFEST.encode("utf-8")).hexdigest()

if MATCH_JOB_ENGINE_SHA256 != "46a8ccd256d71235b0e59c5a14b5e14a8377b54a8ce9ccea6b62b81692b2e7bf":
    raise RuntimeError("AgentWars fixture engine manifest digest drifted")
if MATCH_JOB_RULES_SHA256 != "a811fa0a448e4fd9e06f1dcd37a5c8d0ffae663893971f0fffe08ab6e4d24443":
    raise RuntimeError("AgentWars fixture rules manifest digest drifted")

MATCH_JOB_FALSE_ATTESTATIONS = (
    "providerAccountAttested",
    "planEntitlementAttested",
    "billingRouteAttested",
    "modelAttested",
    "personAttested",
    "runtimeAttested",
    "harnessExecutionAttested",
    "matchExecutionAttested",
)

_JOB_ID_RE = re.compile(r"^awj1_[A-Za-z0-9_-]{22}$")
_ATTEMPT_ID_RE = re.compile(r"^awa1_[A-Za-z0-9_-]{22}$")
_SEED_RE = re.compile(r"^[A-Za-z0-9_-]{22}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_BASE_RESPONSE_KEYS = frozenset({
    "schemaVersion",
    "protocolVersion",
    "runnerId",
    "fingerprint",
    "requestBodySha256",
    "evidenceClass",
    *MATCH_JOB_FALSE_ATTESTATIONS,
})


@dataclasses.dataclass(frozen=True)
class FixtureJob:
    job_id: str
    required_harness_id: str
    required_harness_digest: str
    engine_id: str
    engine_sha256: str
    ruleset_id: str
    rules_sha256: str
    seed: str
    input_sha256: str
    input_bytes_base64url: str
    max_attempts: int


@dataclasses.dataclass(frozen=True)
class FixtureGrant:
    recovery: bool
    request_body_sha256: str
    attempt_id: str
    lease_epoch: int
    attempt_number: int
    renew_count: int
    renewals_remaining: int
    lease_expires_at: str
    job: FixtureJob


@dataclasses.dataclass(frozen=True)
class FixturePollTerminal:
    status: str
    request_body_sha256: str
    conformance: str | None


@dataclasses.dataclass(frozen=True)
class FixtureComputation:
    output_sha256: str
    transcript_sha256: str


@dataclasses.dataclass(frozen=True)
class FixtureResultReceipt:
    duplicate: bool
    conformance: str
    completed_at: str
    request_body_sha256: str


def derive_fixture_input(*, runner_id, harness_id, harness_digest, seed):
    runner_id = validate_runner_id(runner_id)
    harness_id = validate_harness_id(harness_id)
    harness_digest = _digest(harness_digest, "harness digest")
    seed = _canonical_token(seed, _SEED_RE, 16, "fixture seed")
    framed = b"".join((
        b"agentwars.fixture.input.v1\x00",
        runner_id.encode("utf-8"), b"\x00",
        harness_id.encode("utf-8"), b"\x00",
        harness_digest.encode("ascii"), b"\x00",
        seed.encode("ascii"), b"\x00",
    ))
    fixture_bytes = hashlib.sha256(framed).digest()
    return {
        "inputBytesBase64url": _base64url(fixture_bytes),
        "inputSha256": hashlib.sha256(fixture_bytes).hexdigest(),
    }


def expected_fixture_output_sha256(input_bytes_base64url):
    fixture_bytes = _decode_canonical_base64url(input_bytes_base64url, 32, "fixture input")
    return hashlib.sha256(b"agentwars.fixture.output.v1\x00" + fixture_bytes).hexdigest()


def fixture_transcript_sha256(*, job_id, attempt_id, lease_epoch, engine_sha256, input_sha256, output_sha256):
    job_id = _canonical_token(job_id, _JOB_ID_RE, 16, "job id", prefix="awj1_")
    attempt_id = _canonical_token(attempt_id, _ATTEMPT_ID_RE, 16, "attempt id", prefix="awa1_")
    lease_epoch = _integer(lease_epoch, "lease epoch", 1, MATCH_JOB_MAX_ATTEMPTS)
    engine_sha256 = _digest(engine_sha256, "engine digest")
    input_sha256 = _digest(input_sha256, "input digest")
    output_sha256 = _digest(output_sha256, "output digest")
    canonical = "\n".join((
        "agentwars.fixture.transcript.v1",
        f"job-id:{job_id}",
        f"attempt-id:{attempt_id}",
        f"lease-epoch:{lease_epoch}",
        f"engine-sha256:{engine_sha256}",
        f"input-sha256:{input_sha256}",
        f"output-sha256:{output_sha256}",
        "",
    ))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_poll_response(value, *, profile, request_body_sha256):
    if not isinstance(value, dict):
        raise RunnerClientError("match-job poll returned an invalid response contract")
    status = value.get("status")
    if status == "granted":
        _validate_response_base(
            value,
            profile=profile,
            request_body_sha256=request_body_sha256,
            extra_keys={"status", "recovery", "attempt", "job"},
        )
        if type(value["recovery"]) is not bool:
            raise RunnerClientError("match-job poll recovery marker is invalid")
        attempt = _exact_dict(
            value["attempt"],
            {"attemptId", "leaseEpoch", "attemptNumber", "renewCount", "renewalsRemaining", "leaseExpiresAt"},
            "match-job attempt",
        )
        attempt_id = _canonical_token(attempt["attemptId"], _ATTEMPT_ID_RE, 16, "attempt id", prefix="awa1_")
        lease_epoch = _integer(attempt["leaseEpoch"], "lease epoch", 1, MATCH_JOB_MAX_ATTEMPTS)
        attempt_number = _integer(attempt["attemptNumber"], "attempt number", 1, MATCH_JOB_MAX_ATTEMPTS)
        renew_count = _integer(attempt["renewCount"], "renew count", 0, MATCH_JOB_MAX_RENEWS)
        renewals_remaining = _integer(attempt["renewalsRemaining"], "renewals remaining", 0, MATCH_JOB_MAX_RENEWS)
        if attempt_number != lease_epoch or renew_count + renewals_remaining != MATCH_JOB_MAX_RENEWS:
            raise RunnerClientError("match-job attempt counters are contradictory")
        lease_expires_at = validate_canonical_instant(attempt["leaseExpiresAt"])
        job = _validate_job(value["job"], profile=profile)
        return FixtureGrant(
            recovery=value["recovery"],
            request_body_sha256=request_body_sha256,
            attempt_id=attempt_id,
            lease_epoch=lease_epoch,
            attempt_number=attempt_number,
            renew_count=renew_count,
            renewals_remaining=renewals_remaining,
            lease_expires_at=lease_expires_at,
            job=job,
        )
    if status == "completed":
        _validate_response_base(
            value,
            profile=profile,
            request_body_sha256=request_body_sha256,
            extra_keys={"status", "result"},
        )
        result = _validate_public_result(value["result"])
        return FixturePollTerminal("completed", request_body_sha256, result["conformance"])
    if status == "exhausted":
        _validate_response_base(
            value,
            profile=profile,
            request_body_sha256=request_body_sha256,
            extra_keys={"status", "job"},
        )
        summary = _exact_dict(value["job"], {"jobId", "kind", "attemptsUsed", "maxAttempts"}, "exhausted job")
        _canonical_token(summary["jobId"], _JOB_ID_RE, 16, "job id", prefix="awj1_")
        if summary["kind"] != MATCH_JOB_KIND:
            raise RunnerClientError("exhausted job kind is unsupported")
        if _integer(summary["attemptsUsed"], "attempts used", 1, MATCH_JOB_MAX_ATTEMPTS) != MATCH_JOB_MAX_ATTEMPTS:
            raise RunnerClientError("exhausted job attempt count is contradictory")
        if _integer(summary["maxAttempts"], "maximum attempts", 1, MATCH_JOB_MAX_ATTEMPTS) != MATCH_JOB_MAX_ATTEMPTS:
            raise RunnerClientError("exhausted job maximum is unsupported")
        return FixturePollTerminal("exhausted", request_body_sha256, None)
    raise RunnerClientError("match-job poll returned an unsupported status")


def compute_closed_fixture(grant):
    if not isinstance(grant, FixtureGrant):
        raise RunnerClientError("fixture grant object is invalid")
    output_sha256 = expected_fixture_output_sha256(grant.job.input_bytes_base64url)
    transcript_sha256 = fixture_transcript_sha256(
        job_id=grant.job.job_id,
        attempt_id=grant.attempt_id,
        lease_epoch=grant.lease_epoch,
        engine_sha256=grant.job.engine_sha256,
        input_sha256=grant.job.input_sha256,
        output_sha256=output_sha256,
    )
    return FixtureComputation(output_sha256=output_sha256, transcript_sha256=transcript_sha256)


def encode_result_request(grant, computation):
    if not isinstance(grant, FixtureGrant) or not isinstance(computation, FixtureComputation):
        raise RunnerClientError("fixture result inputs are invalid")
    payload = {
        "jobId": grant.job.job_id,
        "attemptId": grant.attempt_id,
        "leaseEpoch": grant.lease_epoch,
        "engineSha256": grant.job.engine_sha256,
        "outputSha256": computation.output_sha256,
        "transcriptSha256": computation.transcript_sha256,
    }
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def validate_result_response(value, *, profile, request_body_sha256, grant, computation):
    if not isinstance(grant, FixtureGrant) or not isinstance(computation, FixtureComputation):
        raise RunnerClientError("fixture result validation inputs are invalid")
    _validate_response_base(
        value,
        profile=profile,
        request_body_sha256=request_body_sha256,
        extra_keys={"status", "duplicate", "result"},
    )
    if value["status"] != "recorded" or type(value["duplicate"]) is not bool:
        raise RunnerClientError("match-job result returned an invalid status")
    result = _validate_public_result(value["result"])
    expected = {
        "jobId": grant.job.job_id,
        "attemptId": grant.attempt_id,
        "leaseEpoch": grant.lease_epoch,
        "engineSha256": grant.job.engine_sha256,
        "outputSha256": computation.output_sha256,
        "transcriptSha256": computation.transcript_sha256,
    }
    for key, expected_value in expected.items():
        if result[key] != expected_value:
            raise RunnerClientError(f"match-job result changed {key}")
    return FixtureResultReceipt(
        duplicate=value["duplicate"],
        conformance=result["conformance"],
        completed_at=result["completedAt"],
        request_body_sha256=request_body_sha256,
    )


def _validate_job(value, *, profile):
    job = _exact_dict(
        value,
        {
            "jobId", "kind", "requiredHarnessId", "requiredHarnessDigest", "engineId", "engineSha256",
            "rulesetId", "rulesSha256", "seed", "inputSha256", "inputBytesBase64url", "maxAttempts",
        },
        "fixture job",
    )
    job_id = _canonical_token(job["jobId"], _JOB_ID_RE, 16, "job id", prefix="awj1_")
    if job["kind"] != MATCH_JOB_KIND:
        raise RunnerClientError("fixture job kind is unsupported")
    required_harness_id = validate_harness_id(job["requiredHarnessId"])
    required_harness_digest = _digest(job["requiredHarnessDigest"], "required harness digest")
    paired_harness_digest = _digest(profile.get("harnessDigest"), "paired harness digest")
    if required_harness_id != profile.get("harnessId") or not hmac.compare_digest(
        required_harness_digest, paired_harness_digest
    ):
        raise RunnerClientError("fixture job changed the paired harness commitment")
    if job["engineId"] != MATCH_JOB_ENGINE_ID or job["engineSha256"] != MATCH_JOB_ENGINE_SHA256:
        raise RunnerClientError("fixture job engine is unsupported")
    if job["rulesetId"] != MATCH_JOB_RULESET_ID or job["rulesSha256"] != MATCH_JOB_RULES_SHA256:
        raise RunnerClientError("fixture job rules are unsupported")
    seed = _canonical_token(job["seed"], _SEED_RE, 16, "fixture seed")
    input_sha256 = _digest(job["inputSha256"], "fixture input digest")
    input_bytes_base64url = _base64url(_decode_canonical_base64url(job["inputBytesBase64url"], 32, "fixture input"))
    derived = derive_fixture_input(
        runner_id=profile.get("runnerId"),
        harness_id=required_harness_id,
        harness_digest=required_harness_digest,
        seed=seed,
    )
    if not hmac.compare_digest(input_sha256, derived["inputSha256"]) or not hmac.compare_digest(
        input_bytes_base64url, derived["inputBytesBase64url"]
    ):
        raise RunnerClientError("fixture job input does not match its paired commitments")
    if _integer(job["maxAttempts"], "maximum attempts", 1, MATCH_JOB_MAX_ATTEMPTS) != MATCH_JOB_MAX_ATTEMPTS:
        raise RunnerClientError("fixture job maximum attempts is unsupported")
    return FixtureJob(
        job_id=job_id,
        required_harness_id=required_harness_id,
        required_harness_digest=required_harness_digest,
        engine_id=MATCH_JOB_ENGINE_ID,
        engine_sha256=MATCH_JOB_ENGINE_SHA256,
        ruleset_id=MATCH_JOB_RULESET_ID,
        rules_sha256=MATCH_JOB_RULES_SHA256,
        seed=seed,
        input_sha256=input_sha256,
        input_bytes_base64url=input_bytes_base64url,
        max_attempts=MATCH_JOB_MAX_ATTEMPTS,
    )


def _validate_public_result(value):
    result = _exact_dict(
        value,
        {"jobId", "attemptId", "leaseEpoch", "engineSha256", "outputSha256", "transcriptSha256", "conformance", "completedAt"},
        "match-job result",
    )
    out = {
        "jobId": _canonical_token(result["jobId"], _JOB_ID_RE, 16, "job id", prefix="awj1_"),
        "attemptId": _canonical_token(result["attemptId"], _ATTEMPT_ID_RE, 16, "attempt id", prefix="awa1_"),
        "leaseEpoch": _integer(result["leaseEpoch"], "lease epoch", 1, MATCH_JOB_MAX_ATTEMPTS),
        "engineSha256": _digest(result["engineSha256"], "engine digest"),
        "outputSha256": _digest(result["outputSha256"], "output digest"),
        "transcriptSha256": _digest(result["transcriptSha256"], "transcript digest"),
        "conformance": result["conformance"],
        "completedAt": validate_canonical_instant(result["completedAt"]),
    }
    if out["engineSha256"] != MATCH_JOB_ENGINE_SHA256 or out["conformance"] not in ("match", "mismatch"):
        raise RunnerClientError("match-job result contract is unsupported")
    return out


def _validate_response_base(value, *, profile, request_body_sha256, extra_keys):
    if not isinstance(value, dict) or set(value) != _BASE_RESPONSE_KEYS | set(extra_keys):
        raise RunnerClientError("match-job response has an invalid exact schema")
    if type(value["schemaVersion"]) is not int or value["schemaVersion"] != MATCH_JOB_SCHEMA_VERSION:
        raise RunnerClientError("match-job response schema version is unsupported")
    if value["protocolVersion"] != MATCH_JOB_PROTOCOL:
        raise RunnerClientError("match-job response protocol is unsupported")
    runner_id = validate_runner_id(profile.get("runnerId"))
    response_runner_id = validate_runner_id(value["runnerId"])
    if not hmac.compare_digest(response_runner_id, runner_id):
        raise RunnerClientError("match-job response changed the runner id")
    fingerprint = validate_fingerprint(profile.get("fingerprint"))
    response_fingerprint = validate_fingerprint(value["fingerprint"])
    if not hmac.compare_digest(response_fingerprint, fingerprint):
        raise RunnerClientError("match-job response changed the runner fingerprint")
    request_body_sha256 = _digest(request_body_sha256, "request body digest")
    response_request_body_sha256 = _digest(value["requestBodySha256"], "response request body digest")
    if not hmac.compare_digest(response_request_body_sha256, request_body_sha256):
        raise RunnerClientError("match-job response changed the request body digest")
    if value["evidenceClass"] != MATCH_JOB_EVIDENCE_CLASS:
        raise RunnerClientError("match-job response evidence class is unsupported")
    for field in MATCH_JOB_FALSE_ATTESTATIONS:
        if value[field] is not False:
            raise RunnerClientError(f"match-job response must keep {field} false")


def _exact_dict(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise RunnerClientError(f"{label} has an invalid exact schema")
    return value


def _integer(value, label, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise RunnerClientError(f"{label} is invalid")
    return value


def _digest(value, label):
    if not isinstance(value, str) or _HEX64_RE.fullmatch(value) is None:
        raise RunnerClientError(f"{label} is invalid")
    return value


def _canonical_token(value, pattern, expected_bytes, label, prefix=""):
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise RunnerClientError(f"{label} is invalid")
    token = value[len(prefix):] if prefix else value
    _decode_canonical_base64url(token, expected_bytes, label)
    return value


def _decode_canonical_base64url(value, expected_bytes, label):
    if not isinstance(value, str):
        raise RunnerClientError(f"{label} is invalid")
    try:
        padded = value + "=" * ((4 - len(value) % 4) % 4)
        decoded = base64.b64decode(padded, altchars=b"-_", validate=True)
    except (ValueError, TypeError) as error:
        raise RunnerClientError(f"{label} is invalid") from error
    if len(decoded) != expected_bytes or _base64url(decoded) != value:
        raise RunnerClientError(f"{label} is not canonical base64url")
    return decoded


def _base64url(value):
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")
