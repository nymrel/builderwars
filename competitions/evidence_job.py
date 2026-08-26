"""Signed customer-local competition evidence transport.

This is deliberately narrower than remote match execution.  A paired runner
may claim one exact, owner-created competition submission job, validate an
already completed customer-local fantasy match with the embedded replay
verifier, and sign a bounded private evidence bundle.  It never launches a
provider, accepts server-selected code, publishes a result, or promotes a
provider/model/harness declaration into an attestation.

Keeping evidence transport separate from provider execution avoids pretending
that a short queue lease can safely supervise a multi-minute model match.  A
future execution protocol needs its own heartbeat, cancellation, and process-
tree containment review.
"""

from __future__ import annotations

import base64
import dataclasses
import hashlib
import hmac
import json
import os
import re
import zlib
from pathlib import Path
from typing import Mapping

from arena.canonical import canonical_bytes, digest
from arena.passport import PassportError, verify_passport
from provider_hub.catalog import get_provider
from provider_hub.local_runner import (
    MAX_BODY_BYTES,
    RunnerClientError,
    validate_canonical_instant,
    validate_fingerprint,
    validate_harness_id,
    validate_json_body,
    validate_runner_id,
)
from publishing.projection import PublicationError, project_receipt


COMPETITION_JOB_SCHEMA_VERSION = 1
COMPETITION_JOB_PROTOCOL = "agentwars.competition_job.v1"
COMPETITION_JOB_KIND = "closed_fantasy_evidence_submission"
COMPETITION_JOB_EVIDENCE_CLASS = "active_local_signing_key_possession"
COMPETITION_JOB_POLL_PATH = "/api/builderwars/competitions/poll"
COMPETITION_JOB_RESULT_PATH = "/api/builderwars/competitions/result"
COMPETITION_JOB_POLL_BODY = (
    b'{"poll":1,"protocolVersion":"agentwars.competition_job.v1"}'
)
COMPETITION_JOB_MAX_ATTEMPTS = 3

CROSS_PROVIDER_SUMMARY_SCHEMA = "agentwars.cross_provider_match_summary.v1"
CROSS_PROVIDER_EVIDENCE_CLASS = "customer_local_provider_claims_with_replay"
COMPETITION_REQUIRED_TRUTH_STATUS = "model_influenced_unattested"
COMPETITION_PUBLICATION_MODE = "private_review_only"
COMPETITION_TRANSCRIPT_ENCODING = "zlib+base64url"
CROSS_PROVIDER_TRUTH_BOUNDARY = (
    "The customer-local runner observed the declared provider adapters and the replay verifier "
    "proved the accepted moves, deterministic state, scoring, and result. Provider, account, "
    "plan, billing route, model, person, runtime, and causal execution identity remain unattested."
)

FANTASY_GAMES = ("fantasy_redraft", "fantasy_dynasty", "fantasy_qb_surge")
STRATEGIES = ("win-now", "long-game")
SUPPORTED_PROVIDERS = (
    "chatgpt_codex",
    "claude_code",
    "opencode",
    "openrouter",
    "hermes",
)
FALSE_ATTESTATIONS = (
    "providerAccountAttested",
    "planEntitlementAttested",
    "billingRouteAttested",
    "modelAttested",
    "personAttested",
    "runtimeAttested",
    "harnessExecutionAttested",
    "matchExecutionAttested",
)

MAX_SUMMARY_BYTES = 16 * 1024
MAX_TRANSCRIPT_BYTES = 256 * 1024
MAX_COMPRESSED_TRANSCRIPT_BYTES = 48 * 1024

_JOB_ID_RE = re.compile(r"^awj1_[A-Za-z0-9_-]{22}$")
_ATTEMPT_ID_RE = re.compile(r"^awa1_[A-Za-z0-9_-]{22}$")
_COMPETITION_ID_RE = re.compile(r"^awc1_[A-Za-z0-9_-]{22}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_PROVIDER_OPTION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+@-]{0,239}$")

_BASE_RESPONSE_KEYS = frozenset(
    {
        "schemaVersion",
        "protocolVersion",
        "runnerId",
        "fingerprint",
        "requestBodySha256",
        "evidenceClass",
        *FALSE_ATTESTATIONS,
    }
)

_SUMMARY_KEYS = frozenset(
    {
        "schemaVersion",
        "status",
        "evidenceClass",
        "publicationDecision",
        "truthBoundary",
        "game",
        "seed",
        "matchId",
        "chainHead",
        "transcriptSha256",
        "winnerSeat",
        "winnerEntrant",
        "seats",
        "providerClaimsDiffer",
        "allAcceptedMovesModelClaimed",
        "universalProviderOrModelRankingEligible",
        "verification",
        "summaryDigest",
        *FALSE_ATTESTATIONS,
    }
)

_SUMMARY_SEAT_KEYS = frozenset(
    {
        "seat",
        "entrant",
        "providerClaim",
        "selectedModelClaim",
        "variantClaim",
        "connectionModeClaim",
        "providerClass",
        "harnessClass",
        "backendClaim",
        "strategy",
        "score",
        "moveSourceClaims",
    }
)

_SUMMARY_VERIFICATION_KEYS = frozenset(
    {
        "replayVerdict",
        "effectiveVerdict",
        "engineDigest",
        "engineDigestMatch",
        "verifierSnapshotMatch",
        "identityStatus",
        "signedHarnessVersionsVerified",
    }
)


@dataclasses.dataclass(frozen=True)
class CompetitionSeat:
    seat: int
    entrant: str
    provider_claim: str
    selected_model_claim: str | None
    variant_claim: str | None
    backend_claim: str
    strategy: str
    agent_id: str | None
    version_id: str | None


@dataclasses.dataclass(frozen=True)
class CompetitionJob:
    job_id: str
    competition_id: str
    required_harness_id: str
    required_harness_digest: str
    game: str
    seed: int
    engine_sha256: str
    seats: tuple[CompetitionSeat, CompetitionSeat]
    require_signed_passports: bool
    required_truth_status: str
    publication_mode: str
    max_attempts: int


@dataclasses.dataclass(frozen=True)
class CompetitionGrant:
    recovery: bool
    request_body_sha256: str
    attempt_id: str
    lease_epoch: int
    attempt_number: int
    lease_expires_at: str
    job: CompetitionJob


@dataclasses.dataclass(frozen=True)
class CompetitionPollTerminal:
    status: str
    request_body_sha256: str
    truth_status: str | None


@dataclasses.dataclass(frozen=True)
class CompetitionEvidence:
    summary: Mapping[str, object]
    public_projection: Mapping[str, object]
    result_body: bytes
    evidence_bundle_sha256: str
    summary_sha256: str
    transcript_sha256: str
    compressed_transcript_sha256: str
    projection_digest: str


@dataclasses.dataclass(frozen=True)
class CompetitionResultReceipt:
    duplicate: bool
    verification_status: str
    truth_status: str
    verified_at: str
    request_body_sha256: str


def validate_competition_poll_response(value, *, profile, request_body_sha256):
    if not isinstance(value, dict):
        raise RunnerClientError("competition-job poll returned an invalid response contract")
    status = value.get("status")
    if status == "granted":
        _validate_response_base(
            value,
            profile=profile,
            request_body_sha256=request_body_sha256,
            extra_keys={"status", "recovery", "attempt", "job"},
        )
        if type(value["recovery"]) is not bool:
            raise RunnerClientError("competition-job poll recovery marker is invalid")
        attempt = _exact_dict(
            value["attempt"],
            {"attemptId", "leaseEpoch", "attemptNumber", "leaseExpiresAt"},
            "competition-job attempt",
        )
        attempt_id = _canonical_token(
            attempt["attemptId"], _ATTEMPT_ID_RE, 16, "attempt id", prefix="awa1_"
        )
        lease_epoch = _integer(
            attempt["leaseEpoch"], "lease epoch", 1, COMPETITION_JOB_MAX_ATTEMPTS
        )
        attempt_number = _integer(
            attempt["attemptNumber"], "attempt number", 1, COMPETITION_JOB_MAX_ATTEMPTS
        )
        if attempt_number != lease_epoch:
            raise RunnerClientError("competition-job attempt counters are contradictory")
        return CompetitionGrant(
            recovery=value["recovery"],
            request_body_sha256=_digest(request_body_sha256, "request body digest"),
            attempt_id=attempt_id,
            lease_epoch=lease_epoch,
            attempt_number=attempt_number,
            lease_expires_at=validate_canonical_instant(attempt["leaseExpiresAt"]),
            job=_validate_job(value["job"], profile=profile),
        )
    if status == "completed":
        _validate_response_base(
            value,
            profile=profile,
            request_body_sha256=request_body_sha256,
            extra_keys={"status", "result"},
        )
        result = _validate_private_result(value["result"])
        return CompetitionPollTerminal("completed", request_body_sha256, result["truthStatus"])
    if status == "exhausted":
        _validate_response_base(
            value,
            profile=profile,
            request_body_sha256=request_body_sha256,
            extra_keys={"status", "job"},
        )
        exhausted = _exact_dict(
            value["job"], {"jobId", "kind", "attemptsUsed", "maxAttempts"}, "exhausted job"
        )
        _canonical_token(exhausted["jobId"], _JOB_ID_RE, 16, "job id", prefix="awj1_")
        if exhausted["kind"] != COMPETITION_JOB_KIND:
            raise RunnerClientError("exhausted competition-job kind is unsupported")
        used = _integer(
            exhausted["attemptsUsed"], "attempts used", 1, COMPETITION_JOB_MAX_ATTEMPTS
        )
        maximum = _integer(
            exhausted["maxAttempts"], "maximum attempts", 1, COMPETITION_JOB_MAX_ATTEMPTS
        )
        if used != COMPETITION_JOB_MAX_ATTEMPTS or maximum != COMPETITION_JOB_MAX_ATTEMPTS:
            raise RunnerClientError("exhausted competition-job attempt count is contradictory")
        return CompetitionPollTerminal("exhausted", request_body_sha256, None)
    raise RunnerClientError("competition-job poll returned an unsupported status")


def build_competition_evidence(
    grant: CompetitionGrant,
    *,
    summary_path: str,
    transcript_path: str,
) -> CompetitionEvidence:
    if not isinstance(grant, CompetitionGrant):
        raise RunnerClientError("competition evidence requires an exact grant")
    summary_file = _regular_file(summary_path, "competition summary")
    transcript_file = _regular_file(transcript_path, "competition transcript")
    if os.path.normcase(str(summary_file)) == os.path.normcase(str(transcript_file)):
        raise RunnerClientError("competition summary and transcript paths must differ")

    summary_bytes = _read_bounded(summary_file, MAX_SUMMARY_BYTES, "competition summary")
    transcript_bytes = _read_bounded(
        transcript_file, MAX_TRANSCRIPT_BYTES, "competition transcript"
    )
    if not transcript_bytes.endswith(b"\n"):
        raise RunnerClientError("competition transcript must end with one complete JSONL record")
    summary = _decode_summary(summary_bytes)
    projection = _verify_evidence_bindings(
        grant.job,
        summary=summary,
        transcript_path=str(transcript_file),
        transcript_bytes=transcript_bytes,
    )
    if not hmac.compare_digest(
        transcript_bytes,
        _read_bounded(transcript_file, MAX_TRANSCRIPT_BYTES, "competition transcript"),
    ):
        raise RunnerClientError("competition transcript changed during replay verification")

    compressed = zlib.compress(transcript_bytes, level=9)
    if not compressed or len(compressed) > MAX_COMPRESSED_TRANSCRIPT_BYTES:
        raise RunnerClientError("competition transcript cannot fit the signed result envelope")
    encoded_transcript = _base64url(compressed)
    transcript_sha256 = hashlib.sha256(transcript_bytes).hexdigest()
    compressed_sha256 = hashlib.sha256(compressed).hexdigest()
    summary_sha256 = hashlib.sha256(canonical_bytes(summary)).hexdigest()
    projection_digest = _digest(projection.get("projectionDigest"), "projection digest")
    job_commitment_sha256 = _job_commitment_sha256(grant.job)
    bundle_core = {
        "schemaVersion": COMPETITION_JOB_SCHEMA_VERSION,
        "protocolVersion": COMPETITION_JOB_PROTOCOL,
        "jobId": grant.job.job_id,
        "attemptId": grant.attempt_id,
        "leaseEpoch": grant.lease_epoch,
        "competitionId": grant.job.competition_id,
        "jobCommitmentSha256": job_commitment_sha256,
        "engineSha256": grant.job.engine_sha256,
        "summarySha256": summary_sha256,
        "summaryDigest": summary["summaryDigest"],
        "transcriptSha256": transcript_sha256,
        "compressedTranscriptSha256": compressed_sha256,
        "projectionDigest": projection_digest,
        "matchId": summary["matchId"],
        "chainHead": summary["chainHead"],
        "truthStatus": summary["status"],
        "transcriptEncoding": COMPETITION_TRANSCRIPT_ENCODING,
        "publicationDecision": "not_reviewed_not_published",
        "rankingEligible": False,
        **{field: False for field in FALSE_ATTESTATIONS},
    }
    evidence_bundle_sha256 = digest(bundle_core)
    payload = {
        **bundle_core,
        "evidenceBundleSha256": evidence_bundle_sha256,
        "transcriptEncoded": encoded_transcript,
        "summary": summary,
    }
    result_body = json.dumps(
        payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    validate_json_body(result_body, maximum_bytes=MAX_BODY_BYTES)
    return CompetitionEvidence(
        summary=summary,
        public_projection=projection,
        result_body=result_body,
        evidence_bundle_sha256=evidence_bundle_sha256,
        summary_sha256=summary_sha256,
        transcript_sha256=transcript_sha256,
        compressed_transcript_sha256=compressed_sha256,
        projection_digest=projection_digest,
    )


def decode_competition_transcript(value, *, expected_sha256: str) -> bytes:
    expected_sha256 = _digest(expected_sha256, "transcript digest")
    compressed = _decode_canonical_base64url(value, None, "compressed transcript")
    if not compressed or len(compressed) > MAX_COMPRESSED_TRANSCRIPT_BYTES:
        raise RunnerClientError("compressed competition transcript is oversized")
    inflater = zlib.decompressobj()
    try:
        raw = inflater.decompress(compressed, MAX_TRANSCRIPT_BYTES + 1)
    except zlib.error as error:
        raise RunnerClientError("compressed competition transcript is invalid") from error
    if (
        len(raw) > MAX_TRANSCRIPT_BYTES
        or inflater.unconsumed_tail
        or inflater.unused_data
        or not inflater.eof
    ):
        raise RunnerClientError("compressed competition transcript exceeds its exact frame")
    if not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), expected_sha256):
        raise RunnerClientError("competition transcript digest does not match its envelope")
    return raw


def validate_competition_result_response(
    value,
    *,
    profile,
    request_body_sha256,
    grant: CompetitionGrant,
    evidence: CompetitionEvidence,
) -> CompetitionResultReceipt:
    if not isinstance(grant, CompetitionGrant) or not isinstance(evidence, CompetitionEvidence):
        raise RunnerClientError("competition result validation inputs are invalid")
    _validate_response_base(
        value,
        profile=profile,
        request_body_sha256=request_body_sha256,
        extra_keys={"status", "duplicate", "result"},
    )
    if value["status"] != "recorded" or type(value["duplicate"]) is not bool:
        raise RunnerClientError("competition result returned an invalid status")
    result = _validate_private_result(value["result"])
    expected = {
        "jobId": grant.job.job_id,
        "attemptId": grant.attempt_id,
        "leaseEpoch": grant.lease_epoch,
        "competitionId": grant.job.competition_id,
        "jobCommitmentSha256": _job_commitment_sha256(grant.job),
        "evidenceBundleSha256": evidence.evidence_bundle_sha256,
        "engineSha256": grant.job.engine_sha256,
        "summarySha256": evidence.summary_sha256,
        "summaryDigest": evidence.summary["summaryDigest"],
        "transcriptSha256": evidence.transcript_sha256,
        "compressedTranscriptSha256": evidence.compressed_transcript_sha256,
        "projectionDigest": evidence.projection_digest,
        "matchId": evidence.summary["matchId"],
        "chainHead": evidence.summary["chainHead"],
        "truthStatus": evidence.summary["status"],
        "publicationDecision": "not_reviewed_not_published",
        "rankingEligible": False,
        "verificationStatus": "verified_private",
    }
    for key, expected_value in expected.items():
        if result[key] != expected_value:
            raise RunnerClientError(f"competition result changed {key}")
    return CompetitionResultReceipt(
        duplicate=value["duplicate"],
        verification_status=result["verificationStatus"],
        truth_status=result["truthStatus"],
        verified_at=result["verifiedAt"],
        request_body_sha256=_digest(request_body_sha256, "request body digest"),
    )


def _validate_job(value, *, profile) -> CompetitionJob:
    job = _exact_dict(
        value,
        {
            "jobId",
            "kind",
            "competitionId",
            "requiredHarnessId",
            "requiredHarnessDigest",
            "game",
            "seed",
            "engineSha256",
            "seats",
            "requireSignedPassports",
            "requiredTruthStatus",
            "publicationMode",
            "maxAttempts",
        },
        "competition job",
    )
    job_id = _canonical_token(job["jobId"], _JOB_ID_RE, 16, "job id", prefix="awj1_")
    if job["kind"] != COMPETITION_JOB_KIND:
        raise RunnerClientError("competition job kind is unsupported")
    competition_id = _canonical_token(
        job["competitionId"], _COMPETITION_ID_RE, 16, "competition id", prefix="awc1_"
    )
    harness_id = validate_harness_id(job["requiredHarnessId"])
    harness_digest = _digest(job["requiredHarnessDigest"], "required harness digest")
    paired_digest = _digest(profile.get("harnessDigest"), "paired harness digest")
    if harness_id != profile.get("harnessId") or not hmac.compare_digest(
        harness_digest, paired_digest
    ):
        raise RunnerClientError("competition job changed the paired harness commitment")
    if job["game"] not in FANTASY_GAMES:
        raise RunnerClientError("competition job game is unsupported")
    seed = _integer(job["seed"], "competition seed", 0, 2_147_483_647)
    engine_sha256 = _digest(job["engineSha256"], "engine digest")
    if type(job["requireSignedPassports"]) is not bool:
        raise RunnerClientError("competition passport requirement is invalid")
    if job["requiredTruthStatus"] != COMPETITION_REQUIRED_TRUTH_STATUS:
        raise RunnerClientError("competition required truth status is unsupported")
    if job["publicationMode"] != COMPETITION_PUBLICATION_MODE:
        raise RunnerClientError("competition publication mode must remain private review only")
    maximum = _integer(
        job["maxAttempts"], "maximum attempts", 1, COMPETITION_JOB_MAX_ATTEMPTS
    )
    if maximum != COMPETITION_JOB_MAX_ATTEMPTS:
        raise RunnerClientError("competition maximum attempts is unsupported")
    if not isinstance(job["seats"], list) or len(job["seats"]) != 2:
        raise RunnerClientError("competition job must contain exactly two seats")
    seats = tuple(_validate_seat(row, expected_seat=index) for index, row in enumerate(job["seats"]))
    if seats[0].provider_claim == seats[1].provider_claim:
        raise RunnerClientError("competition job provider claims must differ")
    if seats[0].entrant.casefold() == seats[1].entrant.casefold():
        raise RunnerClientError("competition entrant names must be unique")
    signed = [seat.agent_id is not None for seat in seats]
    if any(signed) and not all(signed):
        raise RunnerClientError("competition job cannot partially bind signed passports")
    if job["requireSignedPassports"] and not all(signed):
        raise RunnerClientError("competition job requires two signed passport commitments")
    if all(signed) and (
        seats[0].agent_id == seats[1].agent_id or seats[0].version_id == seats[1].version_id
    ):
        raise RunnerClientError("competition job requires distinct signed agent versions")
    return CompetitionJob(
        job_id=job_id,
        competition_id=competition_id,
        required_harness_id=harness_id,
        required_harness_digest=harness_digest,
        game=job["game"],
        seed=seed,
        engine_sha256=engine_sha256,
        seats=(seats[0], seats[1]),
        require_signed_passports=job["requireSignedPassports"],
        required_truth_status=job["requiredTruthStatus"],
        publication_mode=job["publicationMode"],
        max_attempts=maximum,
    )


def _validate_seat(value, *, expected_seat: int) -> CompetitionSeat:
    seat = _exact_dict(
        value,
        {
            "seat",
            "entrant",
            "providerClaim",
            "selectedModelClaim",
            "variantClaim",
            "backendClaim",
            "strategy",
            "agentId",
            "versionId",
        },
        "competition seat",
    )
    if type(seat["seat"]) is not int or seat["seat"] != expected_seat:
        raise RunnerClientError("competition seat order is invalid")
    entrant = _bounded_text(seat["entrant"], "entrant name", 80)
    if seat["providerClaim"] not in SUPPORTED_PROVIDERS:
        raise RunnerClientError("competition provider claim is unsupported")
    model = _provider_option(seat["selectedModelClaim"], "selected model claim")
    variant = _provider_option(seat["variantClaim"], "variant claim")
    backend = _bounded_text(seat["backendClaim"], "backend claim", 240)
    if seat["strategy"] not in STRATEGIES:
        raise RunnerClientError("competition strategy is unsupported")
    agent_id = _optional_digest(seat["agentId"], "agent id")
    version_id = _optional_digest(seat["versionId"], "version id")
    if (agent_id is None) != (version_id is None):
        raise RunnerClientError("competition agent and version commitments must be paired")
    return CompetitionSeat(
        seat=expected_seat,
        entrant=entrant,
        provider_claim=seat["providerClaim"],
        selected_model_claim=model,
        variant_claim=variant,
        backend_claim=backend,
        strategy=seat["strategy"],
        agent_id=agent_id,
        version_id=version_id,
    )


def _verify_evidence_bindings(job, *, summary, transcript_path, transcript_bytes):
    if set(summary) != _SUMMARY_KEYS:
        raise RunnerClientError("competition summary has an unsupported exact schema")
    if summary["schemaVersion"] != CROSS_PROVIDER_SUMMARY_SCHEMA:
        raise RunnerClientError("competition summary schema is unsupported")
    if summary["evidenceClass"] != CROSS_PROVIDER_EVIDENCE_CLASS:
        raise RunnerClientError("competition summary evidence class is unsupported")
    if summary["truthBoundary"] != CROSS_PROVIDER_TRUTH_BOUNDARY:
        raise RunnerClientError("competition summary truth boundary is unsupported")
    if summary["status"] != job.required_truth_status:
        raise RunnerClientError("competition summary does not meet the required truth status")
    if summary["publicationDecision"] != "not_reviewed_not_published":
        raise RunnerClientError("competition summary is not private and unpublished")
    if summary["universalProviderOrModelRankingEligible"] is not False:
        raise RunnerClientError("competition summary cannot claim universal ranking eligibility")
    if summary["allAcceptedMovesModelClaimed"] is not True:
        raise RunnerClientError("competition summary is not an all-model-claimed match")
    if summary["providerClaimsDiffer"] is not True:
        raise RunnerClientError("competition summary does not retain distinct provider claims")
    for field in FALSE_ATTESTATIONS:
        if summary[field] is not False:
            raise RunnerClientError(f"competition summary must keep {field} false")
    core = {key: value for key, value in summary.items() if key != "summaryDigest"}
    if not hmac.compare_digest(_digest(summary["summaryDigest"], "summary digest"), digest(core)):
        raise RunnerClientError("competition summary digest does not cover its exact body")
    if summary["game"] != job.game or summary["seed"] != job.seed:
        raise RunnerClientError("competition summary changed the assigned game or seed")
    transcript_sha256 = hashlib.sha256(transcript_bytes).hexdigest()
    if not hmac.compare_digest(
        _digest(summary["transcriptSha256"], "summary transcript digest"), transcript_sha256
    ):
        raise RunnerClientError("competition summary does not bind the submitted transcript")
    verification = _exact_dict(
        summary["verification"], _SUMMARY_VERIFICATION_KEYS, "summary verification"
    )
    if (
        verification["replayVerdict"] != "PASS"
        or verification["effectiveVerdict"] != "PASS"
        or verification["engineDigestMatch"] is not True
        or verification["verifierSnapshotMatch"] is not True
        or verification["engineDigest"] != job.engine_sha256
    ):
        raise RunnerClientError("competition summary verification is not exact")

    try:
        projection, records = project_receipt(transcript_path)
    except (PublicationError, OSError, ValueError, TypeError, RecursionError) as error:
        raise RunnerClientError("competition transcript fails the public replay boundary") from error
    if not records or records[0].get("kind") != "header":
        raise RunnerClientError("competition transcript has no exact header")
    header = records[0].get("body")
    if not isinstance(header, dict):
        raise RunnerClientError("competition transcript header is malformed")
    engine = header.get("engine")
    if not isinstance(engine, dict) or engine.get("digest") != job.engine_sha256:
        raise RunnerClientError("competition transcript changed the assigned engine")
    if (
        projection.get("receiptId") != summary["chainHead"]
        or projection.get("game", {}).get("name") != job.game
        or projection.get("seed") != job.seed
        or projection.get("truth", {}).get("status") != job.required_truth_status
        or projection.get("truth", {}).get("modelAttested") is not False
        or projection.get("truth", {}).get("executionClaimsAttested") is not False
        or projection.get("truth", {}).get("entrantIdentityAttested") is not False
    ):
        raise RunnerClientError("competition public projection contradicts the private summary")
    if summary["matchId"] != header.get("match_id"):
        raise RunnerClientError("competition summary changed the transcript match id")

    summary_seats = summary["seats"]
    projected_seats = projection.get("entrants")
    transcript_seats = header.get("entrants")
    if (
        not isinstance(summary_seats, list)
        or len(summary_seats) != 2
        or not isinstance(projected_seats, list)
        or len(projected_seats) != 2
        or not isinstance(transcript_seats, list)
        or len(transcript_seats) != 2
    ):
        raise RunnerClientError("competition evidence must contain exactly two seats")
    projected_scores = projection.get("outcome", {}).get("scores")
    if not isinstance(projected_scores, list) or len(projected_scores) != 2:
        raise RunnerClientError("competition projection has no exact score pair")
    for index, assigned in enumerate(job.seats):
        row = _exact_dict(summary_seats[index], _SUMMARY_SEAT_KEYS, "competition summary seat")
        raw = transcript_seats[index]
        projected = projected_seats[index]
        if not isinstance(raw, dict) or not isinstance(projected, dict):
            raise RunnerClientError("competition entrant evidence is malformed")
        expected_catalog = get_provider(assigned.provider_claim)
        expected = {
            "seat": index,
            "entrant": assigned.entrant,
            "providerClaim": assigned.provider_claim,
            "selectedModelClaim": assigned.selected_model_claim,
            "variantClaim": assigned.variant_claim,
            "backendClaim": assigned.backend_claim,
            "strategy": assigned.strategy,
            "connectionModeClaim": expected_catalog["connection_mode"],
            "providerClass": expected_catalog["provider_class"],
            "harnessClass": expected_catalog["harness_class"],
        }
        if type(row["seat"]) is not int or row["seat"] != index:
            raise RunnerClientError("competition summary seat type is invalid")
        if type(row["score"]) is not int:
            raise RunnerClientError("competition summary score type is invalid")
        for key, expected_value in expected.items():
            if row[key] != expected_value:
                raise RunnerClientError(f"competition summary changed seat {index} {key}")
        if row["score"] != projected_scores[index] or projected.get("name") != assigned.entrant:
            raise RunnerClientError("competition summary score or entrant differs from replay")
        projected_counts = next(
            (
                counts
                for counts in projection.get("moveSourceClaims", [])
                if isinstance(counts, dict) and counts.get("seat") == index
            ),
            None,
        )
        if not isinstance(projected_counts, dict) or row["moveSourceClaims"] != {
            key: projected_counts.get(key) for key in ("model", "fallback", "scripted", "other")
        }:
            raise RunnerClientError("competition summary move-source claims differ from replay")
        script = raw.get("script")
        if (
            not isinstance(script, dict)
            or not hmac.compare_digest(
                _digest(script.get("sha256"), "entrant harness digest"),
                job.required_harness_digest,
            )
            or raw.get("claimed_model") != assigned.backend_claim
            or raw.get("name") != assigned.entrant
            or raw.get("seat") != index
        ):
            raise RunnerClientError("competition transcript changed an assigned entrant commitment")
        passport = raw.get("agent_passport")
        if assigned.agent_id is None:
            if passport is not None:
                raise RunnerClientError("competition transcript added an unassigned passport")
            if projected.get("identityStatus") == "verified_signed":
                raise RunnerClientError("competition projection invented signed identity")
        else:
            if not isinstance(passport, dict):
                raise RunnerClientError("competition transcript omitted an assigned passport")
            try:
                normalized = verify_passport(passport)
            except PassportError as error:
                raise RunnerClientError("competition passport fails offline verification") from error
            if (
                normalized["agentId"] != assigned.agent_id
                or normalized["versionId"] != assigned.version_id
                or normalized["displayName"] != assigned.entrant
                or normalized["claimedModel"] != assigned.backend_claim
                or normalized["harnessSha256"] != job.required_harness_digest
                or projected.get("agentVersionId") != assigned.version_id
                or projected.get("entrantId") != assigned.agent_id
                or projected.get("identityStatus") != "verified_signed"
            ):
                raise RunnerClientError("competition passport changed an assigned agent version")

    if (
        type(summary["winnerSeat"]) is not int
        or summary["winnerSeat"] not in (0, 1)
        or summary["winnerSeat"] != projection.get("outcome", {}).get("winnerSeat")
        or summary["winnerEntrant"] != job.seats[summary["winnerSeat"]].entrant
    ):
        raise RunnerClientError("competition summary winner differs from replay")
    signed_expected = all(seat.agent_id is not None for seat in job.seats)
    if (
        verification["signedHarnessVersionsVerified"] is not signed_expected
        or verification["identityStatus"]
        != ("verified_signed" if signed_expected else "self_declared_legacy")
    ):
        raise RunnerClientError("competition signed-passport coverage is contradictory")
    return projection


def _validate_private_result(value):
    result = _exact_dict(
        value,
        {
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
            "verificationStatus",
            "verifiedAt",
        },
        "competition private result",
    )
    out = {
        "jobId": _canonical_token(result["jobId"], _JOB_ID_RE, 16, "job id", prefix="awj1_"),
        "attemptId": _canonical_token(
            result["attemptId"], _ATTEMPT_ID_RE, 16, "attempt id", prefix="awa1_"
        ),
        "leaseEpoch": _integer(
            result["leaseEpoch"], "lease epoch", 1, COMPETITION_JOB_MAX_ATTEMPTS
        ),
        "competitionId": _canonical_token(
            result["competitionId"],
            _COMPETITION_ID_RE,
            16,
            "competition id",
            prefix="awc1_",
        ),
        "jobCommitmentSha256": _digest(result["jobCommitmentSha256"], "job commitment"),
        "evidenceBundleSha256": _digest(result["evidenceBundleSha256"], "bundle digest"),
        "engineSha256": _digest(result["engineSha256"], "engine digest"),
        "summarySha256": _digest(result["summarySha256"], "summary object digest"),
        "summaryDigest": _digest(result["summaryDigest"], "summary digest"),
        "transcriptSha256": _digest(result["transcriptSha256"], "transcript digest"),
        "compressedTranscriptSha256": _digest(
            result["compressedTranscriptSha256"], "compressed transcript digest"
        ),
        "projectionDigest": _digest(result["projectionDigest"], "projection digest"),
        "matchId": _bounded_text(result["matchId"], "match id", 80),
        "chainHead": _digest(result["chainHead"], "chain head"),
        "truthStatus": result["truthStatus"],
        "publicationDecision": result["publicationDecision"],
        "rankingEligible": result["rankingEligible"],
        "verificationStatus": result["verificationStatus"],
        "verifiedAt": validate_canonical_instant(result["verifiedAt"]),
    }
    if (
        out["truthStatus"] != COMPETITION_REQUIRED_TRUTH_STATUS
        or out["publicationDecision"] != "not_reviewed_not_published"
        or out["rankingEligible"] is not False
        or out["verificationStatus"] != "verified_private"
    ):
        raise RunnerClientError("competition private result overstates its release status")
    return out


def _job_commitment_sha256(job: CompetitionJob) -> str:
    if not isinstance(job, CompetitionJob):
        raise RunnerClientError("competition job commitment input is invalid")
    return digest(
        {
            "schemaVersion": COMPETITION_JOB_SCHEMA_VERSION,
            "protocolVersion": COMPETITION_JOB_PROTOCOL,
            "jobId": job.job_id,
            "kind": COMPETITION_JOB_KIND,
            "competitionId": job.competition_id,
            "requiredHarnessId": job.required_harness_id,
            "requiredHarnessDigest": job.required_harness_digest,
            "game": job.game,
            "seed": job.seed,
            "engineSha256": job.engine_sha256,
            "seats": [
                {
                    "seat": seat.seat,
                    "entrant": seat.entrant,
                    "providerClaim": seat.provider_claim,
                    "selectedModelClaim": seat.selected_model_claim,
                    "variantClaim": seat.variant_claim,
                    "backendClaim": seat.backend_claim,
                    "strategy": seat.strategy,
                    "agentId": seat.agent_id,
                    "versionId": seat.version_id,
                }
                for seat in job.seats
            ],
            "requireSignedPassports": job.require_signed_passports,
            "requiredTruthStatus": job.required_truth_status,
            "publicationMode": job.publication_mode,
            "maxAttempts": job.max_attempts,
        }
    )


def _validate_response_base(value, *, profile, request_body_sha256, extra_keys):
    if not isinstance(value, dict) or set(value) != _BASE_RESPONSE_KEYS | set(extra_keys):
        raise RunnerClientError("competition-job response has an invalid exact schema")
    if (
        type(value["schemaVersion"]) is not int
        or value["schemaVersion"] != COMPETITION_JOB_SCHEMA_VERSION
        or value["protocolVersion"] != COMPETITION_JOB_PROTOCOL
    ):
        raise RunnerClientError("competition-job response protocol is unsupported")
    runner_id = validate_runner_id(profile.get("runnerId"))
    if not hmac.compare_digest(validate_runner_id(value["runnerId"]), runner_id):
        raise RunnerClientError("competition-job response changed the runner id")
    fingerprint = validate_fingerprint(profile.get("fingerprint"))
    if not hmac.compare_digest(validate_fingerprint(value["fingerprint"]), fingerprint):
        raise RunnerClientError("competition-job response changed the runner fingerprint")
    request_digest = _digest(request_body_sha256, "request body digest")
    if not hmac.compare_digest(
        _digest(value["requestBodySha256"], "response request body digest"), request_digest
    ):
        raise RunnerClientError("competition-job response changed the request body digest")
    if value["evidenceClass"] != COMPETITION_JOB_EVIDENCE_CLASS:
        raise RunnerClientError("competition-job transport evidence class is unsupported")
    for field in FALSE_ATTESTATIONS:
        if value[field] is not False:
            raise RunnerClientError(f"competition-job response must keep {field} false")


def _decode_summary(raw: bytes):
    try:
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_float=_reject_number,
            parse_constant=_reject_number,
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
        TypeError,
        RecursionError,
    ) as error:
        raise RunnerClientError("competition summary is not strict UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise RunnerClientError("competition summary must be one JSON object")
    return value


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_number(_value):
    raise ValueError("non-integer JSON number")


def _regular_file(value: str, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise RunnerClientError(f"{label} path is invalid")
    path = Path(value)
    if path.is_symlink() or not path.is_file():
        raise RunnerClientError(f"{label} path must be one regular non-symlink file")
    return Path(os.path.realpath(os.path.abspath(path)))


def _read_bounded(path: Path, maximum: int, label: str) -> bytes:
    try:
        with path.open("rb") as handle:
            raw = handle.read(maximum + 1)
    except OSError as error:
        raise RunnerClientError(f"{label} could not be read") from error
    if not raw or len(raw) > maximum:
        raise RunnerClientError(f"{label} is empty or oversized")
    return raw


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


def _optional_digest(value, label):
    return None if value is None else _digest(value, label)


def _bounded_text(value, label, maximum):
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > maximum
        or any(ord(ch) < 0x20 or ord(ch) == 0x7F or 0xD800 <= ord(ch) <= 0xDFFF for ch in value)
    ):
        raise RunnerClientError(f"{label} is invalid")
    return value


def _provider_option(value, label):
    if value is None:
        return None
    if not isinstance(value, str) or _PROVIDER_OPTION_RE.fullmatch(value) is None:
        raise RunnerClientError(f"{label} is invalid")
    return value


def _canonical_token(value, pattern, expected_bytes, label, prefix=""):
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise RunnerClientError(f"{label} is invalid")
    token = value[len(prefix) :] if prefix else value
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
    if (
        (expected_bytes is not None and len(decoded) != expected_bytes)
        or _base64url(decoded) != value
    ):
        raise RunnerClientError(f"{label} is not canonical base64url")
    return decoded


def _base64url(value):
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")
