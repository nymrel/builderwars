"""Fail-closed offline bridge from a private reviewer export to a review candidate.

This module deliberately cannot publish.  It accepts the exact JSON returned by
the protected Nymrel reviewer-detail endpoint, independently verifies the
embedded receipt with BuilderWars, and writes a new candidate directory outside
the repository.  The output is evidence for a later source-control decision;
it never edits the publication manifest, generated product, Git state, or a
deployment surface.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from provider_hub.catalog import EXECUTABLE_PROVIDER_IDS, get_provider

from .product import load_publication_manifest
from .projection import PublicationError, project_receipt, source_kind


class PromotionCandidateError(ValueError):
    """A bounded, non-sensitive promotion-candidate refusal."""


EXPORT_MAX_BYTES = 256 * 1024
RESULT_MAX_BYTES = 65_536
COMPRESSED_TRANSCRIPT_MAX_BYTES = 48 * 1024
TRANSCRIPT_MAX_BYTES = 256 * 1_024
SAFE_INTEGER_MAX = 9_007_199_254_740_991

JOB_PROTOCOL = "agentwars.competition_job.v1"
DECISION_PROTOCOL = "agentwars.competition_publication_decision.v1"
ENGINE_SHA256 = "2cd2cce0b186c3aeb9845ff06d75fd580f281c3e04281af001ccd34645300f8a"
TRUTH_STATUS = "model_influenced_unattested"
PUBLICATION_MODE = "private_review_only"
TRANSCRIPT_ENCODING = "zlib+base64url"
APPROVAL_REASON = "evidence_verified_for_separate_manual_promotion"
APPROVAL_DECISION = "reviewer_approved_not_published"
APPROVAL_STATUS = "eligible_for_separate_manual_promotion"
APPROVAL_EVIDENCE_CLASS = "reviewer_approved_private_result"
REVIEW_EVIDENCE_CLASS = "owner_requested_manual_publication_review"
TRUTH_BOUNDARY = (
    "The customer-local runner observed the declared provider adapters and the replay "
    "verifier proved the accepted moves, deterministic state, scoring, and result. "
    "Provider, account, plan, billing route, model, person, runtime, and causal "
    "execution identity remain unattested."
)

FALSE_ATTESTATION_KEYS = (
    "providerAccountAttested",
    "planEntitlementAttested",
    "billingRouteAttested",
    "modelAttested",
    "personAttested",
    "runtimeAttested",
    "harnessExecutionAttested",
    "matchExecutionAttested",
)
CONSENT_KEYS = (
    "manualApprovalRequiredV1",
    "publicProjectionReviewV1",
    "replayTranscriptReviewV1",
    "selfDeclaredLabelsReviewV1",
)
WRAPPER_KEYS = frozenset({"reviewerAccess", "case"})
CASE_KEYS = frozenset(
    {
        "schemaVersion",
        "protocolVersion",
        "status",
        "runnerId",
        "fingerprint",
        "job",
        "request",
        "result",
        "privateEvidence",
        "decision",
        "publicationDecision",
        "promotionStatus",
        "publicPromotionAuthorized",
        "rankingEligible",
        "evidenceClass",
        *FALSE_ATTESTATION_KEYS,
    }
)
JOB_KEYS = frozenset(
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
    }
)
SEAT_KEYS = frozenset(
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
    }
)
REQUEST_KEYS = frozenset(
    {
        "requestId",
        "consent",
        "requestedAt",
        "jobCommitmentSha256",
        "evidenceBundleSha256",
        "resultBodySha256",
        "projectionDigest",
        "transcriptSha256",
        "chainHead",
        "truthStatus",
        "verificationStatus",
    }
)
PRIVATE_EVIDENCE_KEYS = frozenset({"included", "bytes", "body"})
DECISION_KEYS = frozenset(
    {
        "decisionId",
        "requestId",
        "decision",
        "reasonCode",
        "decidedAt",
        "publicationDecision",
        "promotionStatus",
        "publicPromotionAuthorized",
        "rankingEligible",
    }
)
PRIVATE_RESULT_KEYS = frozenset(
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
    }
)
EVIDENCE_BODY_KEYS = frozenset(
    {
        "schemaVersion",
        "protocolVersion",
        "jobId",
        "attemptId",
        "leaseEpoch",
        "competitionId",
        "jobCommitmentSha256",
        "engineSha256",
        "summarySha256",
        "summaryDigest",
        "transcriptSha256",
        "compressedTranscriptSha256",
        "projectionDigest",
        "matchId",
        "chainHead",
        "truthStatus",
        "transcriptEncoding",
        "publicationDecision",
        "rankingEligible",
        *FALSE_ATTESTATION_KEYS,
        "evidenceBundleSha256",
        "transcriptEncoded",
        "summary",
    }
)
SUMMARY_KEYS = frozenset(
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
        *FALSE_ATTESTATION_KEYS,
    }
)
SUMMARY_SEAT_KEYS = frozenset(
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
SUMMARY_VERIFICATION_KEYS = frozenset(
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
SOURCE_COUNT_KEYS = frozenset({"model", "fallback", "scripted", "other"})

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{22}$")
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
PROVIDER_OPTION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+@-]{0,239}$")
INSTANT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
MODEL_NOTE_RE = re.compile(
    r"^source=model(?:;attempts=[12])?"
    r"(?:;response_sha256=[0-9a-f]{16})?"
    r"(?:;prior_response_sha256=[0-9a-f]{16})?$"
)
FORBIDDEN_TRANSCRIPT_KEYS = frozenset(
    {
        "apikey",
        "accesstoken",
        "refreshtoken",
        "password",
        "privatekey",
        "prompt",
        "rawoutput",
        "rawprovideroutput",
        "secret",
        "stderr",
        "stdout",
        "systemprompt",
        "diagnostics",
    }
)
SECRET_PATTERNS = (
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----"),
    re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{16,})\b"),
    re.compile(rb"\bsk-(?:live-|test-)[A-Za-z0-9_-]{16,}\b"),
    re.compile(rb"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^\s:/]+:[^\s/@]{4,}@", re.I),
)

PROVIDERS = {
    provider_id: {
        "connectionModeClaim": get_provider(provider_id)["connection_mode"],
        "providerClass": get_provider(provider_id)["provider_class"],
        "harnessClass": get_provider(provider_id)["harness_class"],
        "modelRequired": get_provider(provider_id)["model_required"],
    }
    for provider_id in EXECUTABLE_PROVIDER_IDS
    if provider_id != "custom_agent"
}


def sha256_hex(value: bytes | str) -> str:
    data = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any, *, ensure_ascii: bool = False) -> str:
    _validate_canonical_value(value, "$")
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=ensure_ascii,
        allow_nan=False,
    )


def canonical_digest(value: Any) -> str:
    return sha256_hex(canonical_json(value).encode("utf-8"))


def _validate_canonical_value(value: Any, path: str) -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, str):
        if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
            raise PromotionCandidateError(f"{path}: unpaired surrogate is forbidden")
        return
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > SAFE_INTEGER_MAX:
            raise PromotionCandidateError(f"{path}: integer exceeds the canonical safe range")
        return
    if isinstance(value, float):
        raise PromotionCandidateError(f"{path}: floats are forbidden")
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_canonical_value(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or not key or not all(0x20 <= ord(ch) <= 0x7E for ch in key):
                raise PromotionCandidateError(f"{path}: object keys must be printable ASCII")
            _validate_canonical_value(item, f"{path}.{key}")
        return
    raise PromotionCandidateError(f"{path}: value is not canonical JSON")


def _pairs_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PromotionCandidateError("JSON contains a duplicate object key")
        result[key] = value
    return result


def _reject_number(_value: str) -> Any:
    raise PromotionCandidateError("JSON floats and non-finite numbers are forbidden")


def _parse_strict_json(text: str, label: str) -> Any:
    if not text or text.startswith("\ufeff"):
        raise PromotionCandidateError(f"{label} is empty or has a byte-order mark")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_pairs_without_duplicates,
            parse_float=_reject_number,
            parse_constant=_reject_number,
        )
    except PromotionCandidateError:
        raise
    except (RecursionError, ValueError, json.JSONDecodeError) as error:
        raise PromotionCandidateError(f"{label} is malformed JSON") from error
    _validate_canonical_value(value, "$")
    return value


def _expect_row(value: Any, keys: frozenset[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise PromotionCandidateError(f"{label} has an invalid exact schema")
    return value


def _hex64(value: Any, label: str) -> str:
    if not isinstance(value, str) or HEX64_RE.fullmatch(value) is None:
        raise PromotionCandidateError(f"{label} must be lowercase SHA-256")
    return value


def _token(value: Any, prefix: str, label: str) -> str:
    if not isinstance(value, str) or not value.startswith(prefix):
        raise PromotionCandidateError(f"{label} is invalid")
    encoded = value[len(prefix):]
    if TOKEN_RE.fullmatch(encoded) is None:
        raise PromotionCandidateError(f"{label} is invalid")
    try:
        decoded = base64.urlsafe_b64decode(encoded + "==")
    except (ValueError, TypeError) as error:
        raise PromotionCandidateError(f"{label} is invalid") from error
    if len(decoded) != 16 or base64.urlsafe_b64encode(decoded).decode("ascii").rstrip("=") != encoded:
        raise PromotionCandidateError(f"{label} is not canonical base64url")
    return value


def _instant(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or INSTANT_RE.fullmatch(value) is None:
        raise PromotionCandidateError(f"{label} is not a canonical instant")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise PromotionCandidateError(f"{label} is not a valid instant") from error
    if parsed.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z" != value:
        raise PromotionCandidateError(f"{label} is not a canonical instant")
    return parsed


def _bounded_text(value: Any, maximum: int, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > maximum
        or any(ord(ch) < 0x20 or ord(ch) == 0x7F or 0xD800 <= ord(ch) <= 0xDFFF for ch in value)
    ):
        raise PromotionCandidateError(f"{label} is invalid")
    return value


def _integer(value: Any, minimum: int, maximum: int, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        raise PromotionCandidateError(f"{label} is invalid")
    return value


def _assert_false_attestations(row: dict[str, Any], label: str) -> None:
    if any(row.get(key) is not False for key in FALSE_ATTESTATION_KEYS):
        raise PromotionCandidateError(f"{label} overstates an attestation")


def _provider_option(value: Any, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or PROVIDER_OPTION_RE.fullmatch(value) is None:
        raise PromotionCandidateError(f"{label} is invalid")
    return value


def _backend_claim(provider: str, model: str | None, variant: str | None) -> str:
    catalog = PROVIDERS[provider]
    if catalog["modelRequired"] != (model is not None) or (provider != "opencode" and variant is not None):
        raise PromotionCandidateError("provider options are contradictory")
    if provider == "chatgpt_codex":
        return "chatgpt_codex:codex exec"
    if provider == "openrouter":
        return f"openrouter:{model}"
    assert model is not None
    if "/" not in model:
        raise PromotionCandidateError("routed model claim must include provider/model")
    provider_name, model_name = model.split("/", 1)
    if not provider_name or not model_name or (provider == "opencode" and "@" in model):
        raise PromotionCandidateError("routed model claim is invalid")
    if provider == "opencode" and (len(provider_name) > 80 or len(model_name) > 160):
        raise PromotionCandidateError("OpenCode model claim is oversized")
    if provider == "hermes" and (len(provider_name) > 80 or len(model_name) > 120):
        raise PromotionCandidateError("Hermes model claim is oversized")
    return f"opencode-provider:{model}@{variant or 'max'}" if provider == "opencode" else f"hermes:{model}"


def _validate_job(job_value: Any) -> tuple[dict[str, Any], str]:
    job = _expect_row(job_value, JOB_KEYS, "competition job")
    _token(job["jobId"], "awj1_", "job id")
    _token(job["competitionId"], "awc1_", "competition id")
    if job["kind"] != "closed_fantasy_evidence_submission":
        raise PromotionCandidateError("competition job kind is invalid")
    if not isinstance(job["requiredHarnessId"], str) or SAFE_ID_RE.fullmatch(job["requiredHarnessId"]) is None:
        raise PromotionCandidateError("required harness id is invalid")
    _hex64(job["requiredHarnessDigest"], "required harness digest")
    if job["game"] not in {"fantasy_redraft", "fantasy_dynasty", "fantasy_qb_surge"}:
        raise PromotionCandidateError("competition game is unsupported")
    _integer(job["seed"], 0, 2_147_483_647, "competition seed")
    if job["engineSha256"] != ENGINE_SHA256:
        raise PromotionCandidateError("competition engine snapshot is stale")
    if (
        job["requiredTruthStatus"] != TRUTH_STATUS
        or job["publicationMode"] != PUBLICATION_MODE
        or job["maxAttempts"] != 3
        or not isinstance(job["requireSignedPassports"], bool)
    ):
        raise PromotionCandidateError("competition job truth, publication, or retry contract is invalid")
    seats = job["seats"]
    if not isinstance(seats, list) or len(seats) != 2:
        raise PromotionCandidateError("competition job must contain exactly two seats")
    signed: list[bool] = []
    for expected_seat, value in enumerate(seats):
        seat = _expect_row(value, SEAT_KEYS, "competition seat")
        if seat["seat"] != expected_seat:
            raise PromotionCandidateError("competition seats are out of order")
        _bounded_text(seat["entrant"], 80, "entrant name")
        provider = seat["providerClaim"]
        if provider not in PROVIDERS:
            raise PromotionCandidateError("competition provider claim is unsupported")
        model = _provider_option(seat["selectedModelClaim"], "selected model claim")
        variant = _provider_option(seat["variantClaim"], "variant claim")
        if seat["backendClaim"] != _backend_claim(provider, model, variant):
            raise PromotionCandidateError("backend claim does not match provider options")
        if seat["strategy"] not in {"win-now", "long-game"}:
            raise PromotionCandidateError("competition strategy is invalid")
        agent_id, version_id = seat["agentId"], seat["versionId"]
        if (agent_id is None) != (version_id is None):
            raise PromotionCandidateError("competition passport binding is incomplete")
        if agent_id is not None:
            _hex64(agent_id, "agent id")
            _hex64(version_id, "agent version id")
        signed.append(agent_id is not None)
    if seats[0]["providerClaim"] == seats[1]["providerClaim"]:
        raise PromotionCandidateError("competition provider claims must differ")
    if seats[0]["entrant"].casefold() == seats[1]["entrant"].casefold():
        raise PromotionCandidateError("competition entrant names must differ")
    if signed[0] != signed[1] or (job["requireSignedPassports"] and not all(signed)):
        raise PromotionCandidateError("competition passport requirement is invalid")
    if all(signed) and (
        seats[0]["agentId"] == seats[1]["agentId"]
        or seats[0]["versionId"] == seats[1]["versionId"]
    ):
        raise PromotionCandidateError("competition signed agent versions must be distinct")
    commitment = canonical_digest({"schemaVersion": 1, "protocolVersion": JOB_PROTOCOL, **job})
    return job, commitment


def _decode_transcript(body: dict[str, Any]) -> bytes:
    encoded = body["transcriptEncoded"]
    if not isinstance(encoded, str) or not encoded or re.fullmatch(r"[A-Za-z0-9_-]+", encoded) is None:
        raise PromotionCandidateError("competition transcript encoding is invalid")
    try:
        compressed = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
    except (ValueError, TypeError) as error:
        raise PromotionCandidateError("competition transcript encoding is invalid") from error
    if (
        not compressed
        or len(compressed) > COMPRESSED_TRANSCRIPT_MAX_BYTES
        or base64.urlsafe_b64encode(compressed).decode("ascii").rstrip("=") != encoded
    ):
        raise PromotionCandidateError("competition transcript encoding is not canonical or is oversized")
    if sha256_hex(compressed) != body["compressedTranscriptSha256"]:
        raise PromotionCandidateError("compressed transcript digest is invalid")
    try:
        inflater = zlib.decompressobj()
        transcript = inflater.decompress(compressed, TRANSCRIPT_MAX_BYTES + 1)
        transcript += inflater.flush()
    except zlib.error as error:
        raise PromotionCandidateError("competition transcript has an invalid exact zlib frame") from error
    if (
        not inflater.eof
        or inflater.unused_data
        or inflater.unconsumed_tail
        or not transcript
        or len(transcript) > TRANSCRIPT_MAX_BYTES
        or not transcript.endswith(b"\n")
    ):
        raise PromotionCandidateError("competition transcript has an invalid exact zlib frame")
    if sha256_hex(transcript) != body["transcriptSha256"]:
        raise PromotionCandidateError("competition transcript digest is invalid")
    return transcript


def _validate_export(raw: bytes) -> dict[str, Any]:
    if not raw or len(raw) > EXPORT_MAX_BYTES or raw.startswith(b"\xef\xbb\xbf"):
        raise PromotionCandidateError("reviewer export is empty, oversized, or has a byte-order mark")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise PromotionCandidateError("reviewer export is not strict UTF-8") from error
    payload = _parse_strict_json(text, "reviewer export")
    wrapper = _expect_row(payload, WRAPPER_KEYS, "reviewer export")
    if wrapper["reviewerAccess"] != "authorized_reviewer":
        raise PromotionCandidateError("reviewer export does not claim the protected reviewer detail response")
    case = _expect_row(wrapper["case"], CASE_KEYS, "reviewer case")
    _assert_false_attestations(case, "reviewer case")
    if (
        case["schemaVersion"] != 1
        or case["protocolVersion"] != DECISION_PROTOCOL
        or case["status"] != "approved"
        or case["publicationDecision"] != APPROVAL_DECISION
        or case["promotionStatus"] != APPROVAL_STATUS
        or case["publicPromotionAuthorized"] is not False
        or case["rankingEligible"] is not False
        or case["evidenceClass"] != APPROVAL_EVIDENCE_CLASS
    ):
        raise PromotionCandidateError("reviewer case is not an approved, still-private promotion candidate")
    _token(case["runnerId"], "awr1_", "runner id")
    _hex64(case["fingerprint"], "runner fingerprint")

    job, job_commitment = _validate_job(case["job"])
    request = _expect_row(case["request"], REQUEST_KEYS, "review request")
    _token(request["requestId"], "awpr1_", "review request id")
    consent = request["consent"]
    if not isinstance(consent, dict) or set(consent) != set(CONSENT_KEYS) or any(consent[key] is not True for key in CONSENT_KEYS):
        raise PromotionCandidateError("review request lacks an exact consent acknowledgement")
    requested_at = _instant(request["requestedAt"], "review requestedAt")
    for key in (
        "jobCommitmentSha256",
        "evidenceBundleSha256",
        "resultBodySha256",
        "projectionDigest",
        "transcriptSha256",
        "chainHead",
    ):
        _hex64(request[key], f"review request {key}")
    if (
        request["jobCommitmentSha256"] != job_commitment
        or request["truthStatus"] != TRUTH_STATUS
        or request["verificationStatus"] != "verified_private"
    ):
        raise PromotionCandidateError("review request changed its job or verification boundary")

    result = _expect_row(case["result"], PRIVATE_RESULT_KEYS, "private result")
    for key in (
        "jobCommitmentSha256",
        "evidenceBundleSha256",
        "engineSha256",
        "summarySha256",
        "summaryDigest",
        "transcriptSha256",
        "compressedTranscriptSha256",
        "projectionDigest",
        "chainHead",
    ):
        _hex64(result[key], f"private result {key}")
    _token(result["jobId"], "awj1_", "result job id")
    _token(result["attemptId"], "awa1_", "result attempt id")
    _token(result["competitionId"], "awc1_", "result competition id")
    _integer(result["leaseEpoch"], 1, 3, "result lease epoch")
    _bounded_text(result["matchId"], 80, "result match id")
    verified_at = _instant(result["verifiedAt"], "result verifiedAt")
    if (
        result["jobId"] != job["jobId"]
        or result["competitionId"] != job["competitionId"]
        or result["jobCommitmentSha256"] != job_commitment
        or result["engineSha256"] != ENGINE_SHA256
        or result["truthStatus"] != TRUTH_STATUS
        or result["publicationDecision"] != "not_reviewed_not_published"
        or result["rankingEligible"] is not False
        or result["verificationStatus"] != "verified_private"
        or verified_at > requested_at
    ):
        raise PromotionCandidateError("private result changed its job, truth, time, or publication boundary")

    private_evidence = _expect_row(case["privateEvidence"], PRIVATE_EVIDENCE_KEYS, "private evidence")
    body_text = private_evidence["body"]
    if private_evidence["included"] is not True or not isinstance(body_text, str):
        raise PromotionCandidateError("reviewer export does not include the exact private evidence body")
    body_bytes = body_text.encode("utf-8")
    if (
        not body_bytes
        or len(body_bytes) > RESULT_MAX_BYTES
        or private_evidence["bytes"] != len(body_bytes)
        or sha256_hex(body_bytes) != request["resultBodySha256"]
    ):
        raise PromotionCandidateError("private evidence byte commitment is invalid")
    body = _parse_strict_json(body_text, "private evidence body")
    if canonical_json(body, ensure_ascii=True) != body_text:
        raise PromotionCandidateError("private evidence body is not exact canonical ASCII JSON")
    body = _expect_row(body, EVIDENCE_BODY_KEYS, "private evidence body")
    _assert_false_attestations(body, "private evidence body")
    for key in (
        "jobCommitmentSha256",
        "engineSha256",
        "summarySha256",
        "summaryDigest",
        "transcriptSha256",
        "compressedTranscriptSha256",
        "projectionDigest",
        "chainHead",
        "evidenceBundleSha256",
    ):
        _hex64(body[key], f"private evidence {key}")
    if (
        body["schemaVersion"] != 1
        or body["protocolVersion"] != JOB_PROTOCOL
        or body["jobId"] != result["jobId"]
        or body["attemptId"] != result["attemptId"]
        or body["leaseEpoch"] != result["leaseEpoch"]
        or body["competitionId"] != result["competitionId"]
        or body["jobCommitmentSha256"] != job_commitment
        or body["engineSha256"] != ENGINE_SHA256
        or body["truthStatus"] != TRUTH_STATUS
        or body["transcriptEncoding"] != TRANSCRIPT_ENCODING
        or body["publicationDecision"] != "not_reviewed_not_published"
        or body["rankingEligible"] is not False
    ):
        raise PromotionCandidateError("private evidence changed its assigned job or truth boundary")
    bundle_core = {
        key: value
        for key, value in body.items()
        if key not in {"evidenceBundleSha256", "transcriptEncoded", "summary"}
    }
    if canonical_digest(bundle_core) != body["evidenceBundleSha256"]:
        raise PromotionCandidateError("private evidence bundle commitment is invalid")

    transcript = _decode_transcript(body)
    summary = _expect_row(body["summary"], SUMMARY_KEYS, "competition summary")
    _assert_false_attestations(summary, "competition summary")
    summary_core = {key: value for key, value in summary.items() if key != "summaryDigest"}
    if (
        summary["schemaVersion"] != "agentwars.cross_provider_match_summary.v1"
        or summary["status"] != TRUTH_STATUS
        or summary["evidenceClass"] != "customer_local_provider_claims_with_replay"
        or summary["publicationDecision"] != "not_reviewed_not_published"
        or summary["truthBoundary"] != TRUTH_BOUNDARY
        or summary["providerClaimsDiffer"] is not True
        or summary["allAcceptedMovesModelClaimed"] is not True
        or summary["universalProviderOrModelRankingEligible"] is not False
        or canonical_digest(summary_core) != summary["summaryDigest"]
        or canonical_digest(summary) != body["summarySha256"]
        or summary["summaryDigest"] != body["summaryDigest"]
        or summary["game"] != job["game"]
        or summary["seed"] != job["seed"]
        or summary["matchId"] != body["matchId"]
        or summary["chainHead"] != body["chainHead"]
        or summary["transcriptSha256"] != body["transcriptSha256"]
    ):
        raise PromotionCandidateError("competition summary truth or integrity contract is invalid")

    decision = _expect_row(case["decision"], DECISION_KEYS, "review decision")
    _token(decision["decisionId"], "awpd1_", "decision id")
    decided_at = _instant(decision["decidedAt"], "decision decidedAt")
    if (
        decision["requestId"] != request["requestId"]
        or decision["decision"] != "approved"
        or decision["reasonCode"] != APPROVAL_REASON
        or decided_at < requested_at
        or decision["publicationDecision"] != APPROVAL_DECISION
        or decision["promotionStatus"] != APPROVAL_STATUS
        or decision["publicPromotionAuthorized"] is not False
        or decision["rankingEligible"] is not False
    ):
        raise PromotionCandidateError("review decision is not the exact still-private approval")

    aligned = {
        "jobCommitmentSha256": job_commitment,
        "evidenceBundleSha256": body["evidenceBundleSha256"],
        "resultBodySha256": sha256_hex(body_bytes),
        "projectionDigest": body["projectionDigest"],
        "transcriptSha256": body["transcriptSha256"],
        "chainHead": body["chainHead"],
    }
    for key, expected in aligned.items():
        if request[key] != expected or (
            key != "resultBodySha256" and result[key] != expected
        ):
            raise PromotionCandidateError(f"review, result, and evidence disagree on {key}")
    for key in (
        "summarySha256",
        "summaryDigest",
        "compressedTranscriptSha256",
        "matchId",
    ):
        if result[key] != body[key]:
            raise PromotionCandidateError(f"private result and evidence disagree on {key}")

    return {
        "payload": payload,
        "case": case,
        "job": job,
        "request": request,
        "result": result,
        "decision": decision,
        "body": body,
        "summary": summary,
        "transcript": transcript,
        "rawSha256": sha256_hex(raw),
        "rawBytes": len(raw),
        "canonicalPayloadSha256": canonical_digest(payload),
    }


def _validate_projection(validated: dict[str, Any], transcript_path: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        receipt, records = project_receipt(transcript_path)
    except PublicationError as error:
        raise PromotionCandidateError(f"BuilderWars independently refused the transcript: {error}") from error
    job, body, summary = validated["job"], validated["body"], validated["summary"]
    _validate_transcript_content(records, validated["transcript"])
    if (
        receipt.get("schemaVersion") != "agentwars.public-receipt.v1"
        or receipt.get("receiptId") != body["chainHead"]
        or receipt.get("projectionDigest") != body["projectionDigest"]
        or receipt.get("game", {}).get("name") != job["game"]
        or receipt.get("seed") != job["seed"]
        or receipt.get("transcript", {}).get("sha256") != body["transcriptSha256"]
        or receipt.get("transcript", {}).get("bytes") != len(validated["transcript"])
        or receipt.get("truth", {}).get("status") != TRUTH_STATUS
        or receipt.get("truth", {}).get("modelAttested") is not False
        or receipt.get("verification", {}).get("replayVerdict") != "PASS"
        or receipt.get("verification", {}).get("effectiveVerdict") != "PASS"
        or receipt.get("verification", {}).get("engineDigest") != ENGINE_SHA256
        or receipt.get("verification", {}).get("engineDigestMatch") is not True
        or receipt.get("verification", {}).get("verifierSnapshotMatch") is not True
    ):
        raise PromotionCandidateError("BuilderWars projection disagrees with the private evidence commitment")
    header = next((row.get("body") for row in records if row.get("kind") == "header"), None)
    raw_entrants = header.get("entrants") if isinstance(header, dict) else None
    projected_entrants = receipt.get("entrants")
    counts = receipt.get("moveSourceClaims")
    outcome = receipt.get("outcome")
    if (
        not isinstance(raw_entrants, list)
        or len(raw_entrants) != 2
        or not isinstance(projected_entrants, list)
        or len(projected_entrants) != 2
        or not isinstance(counts, list)
        or len(counts) != 2
        or not isinstance(outcome, dict)
        or outcome.get("status") != "final"
        or not isinstance(outcome.get("scores"), list)
        or len(outcome["scores"]) != 2
    ):
        raise PromotionCandidateError("BuilderWars projection lacks a complete competitive result")
    accepted_moves = [row for row in records if row.get("kind") == "move" and row.get("body", {}).get("legal") is True]
    if not accepted_moves or any(
        source_kind(
            row.get("body", {}).get("entrant_message", {}).get("note")
            if isinstance(row.get("body", {}).get("entrant_message"), dict)
            else None
        ) != "model"
        for row in accepted_moves
    ):
        raise PromotionCandidateError("candidate is not an all-accepted-moves model-claimed result")
    summary_seats = summary.get("seats")
    if not isinstance(summary_seats, list) or len(summary_seats) != 2:
        raise PromotionCandidateError("competition summary must contain exactly two seats")
    signed_expected = all(seat["agentId"] is not None for seat in job["seats"])
    for seat_index in (0, 1):
        assigned = job["seats"][seat_index]
        raw = raw_entrants[seat_index]
        projected = projected_entrants[seat_index]
        projected_counts = counts[seat_index]
        summary_seat = _expect_row(summary_seats[seat_index], SUMMARY_SEAT_KEYS, "competition summary seat")
        if not isinstance(raw, dict) or not isinstance(projected, dict) or not isinstance(projected_counts, dict):
            raise PromotionCandidateError("competition transcript entrant projection is malformed")
        script = raw.get("script")
        if (
            raw.get("seat") != seat_index
            or raw.get("name") != assigned["entrant"]
            or raw.get("claimed_model") != assigned["backendClaim"]
            or not isinstance(script, dict)
            or script.get("sha256") != job["requiredHarnessDigest"]
            or projected.get("name") != assigned["entrant"]
        ):
            raise PromotionCandidateError("competition transcript changed an assigned entrant")
        catalog = PROVIDERS[assigned["providerClaim"]]
        expected_summary = {
            "seat": seat_index,
            "entrant": assigned["entrant"],
            "providerClaim": assigned["providerClaim"],
            "selectedModelClaim": assigned["selectedModelClaim"],
            "variantClaim": assigned["variantClaim"],
            "connectionModeClaim": catalog["connectionModeClaim"],
            "providerClass": catalog["providerClass"],
            "harnessClass": catalog["harnessClass"],
            "backendClaim": assigned["backendClaim"],
            "strategy": assigned["strategy"],
            "score": outcome["scores"][seat_index],
            "moveSourceClaims": {key: projected_counts[key] for key in SOURCE_COUNT_KEYS},
        }
        if canonical_json(summary_seat) != canonical_json(expected_summary):
            raise PromotionCandidateError("competition summary changed an assigned seat or replay count")
        if signed_expected:
            if (
                projected.get("identityStatus") != "verified_signed"
                or projected.get("entrantId") != assigned["agentId"]
                or projected.get("agentVersionId") != assigned["versionId"]
            ):
                raise PromotionCandidateError("competition passport changed an assigned agent version")
        elif projected.get("identityStatus") == "verified_signed" or "agent_passport" in raw:
            raise PromotionCandidateError("competition transcript added an unassigned passport")
    verification = _expect_row(summary["verification"], SUMMARY_VERIFICATION_KEYS, "competition summary verification")
    expected_identity = "verified_signed" if signed_expected else "self_declared_legacy"
    if (
        verification["replayVerdict"] != "PASS"
        or verification["effectiveVerdict"] != "PASS"
        or verification["engineDigest"] != ENGINE_SHA256
        or verification["engineDigestMatch"] is not True
        or verification["verifierSnapshotMatch"] is not True
        or verification["identityStatus"] != expected_identity
        or verification["signedHarnessVersionsVerified"] is not signed_expected
        or summary["winnerSeat"] not in (0, 1)
        or summary["winnerSeat"] != outcome.get("winnerSeat")
        or summary["winnerEntrant"] != job["seats"][summary["winnerSeat"]]["entrant"]
    ):
        raise PromotionCandidateError("competition summary verification or winner differs from replay")
    return receipt, records


def _validate_transcript_content(records: list[dict[str, Any]], transcript: bytes) -> None:
    """Reject private/provider payloads before a byte-exact transcript is staged.

    The fixed customer-local harness emits only the ready tuple and the accepted
    move plus a bounded source/digest note.  Unknown reply keys would turn the
    public transcript into an accidental provider-output or prompt channel, so
    this bridge is intentionally stricter than historical replay compatibility.
    """

    if any(pattern.search(transcript) for pattern in SECRET_PATTERNS):
        raise PromotionCandidateError("candidate transcript contains a high-confidence credential pattern")

    def inspect_keys(value: Any) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                normalized = re.sub(r"[^a-z0-9]", "", key.casefold())
                if normalized in FORBIDDEN_TRANSCRIPT_KEYS:
                    raise PromotionCandidateError("candidate transcript contains a forbidden private-data field")
                inspect_keys(nested)
        elif isinstance(value, list):
            for nested in value:
                inspect_keys(nested)

    inspect_keys(records)
    for record in records:
        kind = record.get("kind")
        body = record.get("body")
        if not isinstance(body, dict):
            raise PromotionCandidateError("candidate transcript record body is malformed")
        if kind == "ready":
            message = body.get("entrant_message")
            if (
                not isinstance(message, dict)
                or set(message) != {"type", "entrant", "version", "backend"}
                or message.get("type") != "ready"
                or message.get("version") != "1"
            ):
                raise PromotionCandidateError("candidate ready message exposes an unexpected field")
        elif kind == "move":
            message = body.get("entrant_message")
            if (
                not isinstance(message, dict)
                or set(message) != {"type", "move", "note"}
                or message.get("type") != "move"
                or canonical_json(message.get("move")) != canonical_json(body.get("move"))
                or not isinstance(message.get("note"), str)
                or MODEL_NOTE_RE.fullmatch(message["note"]) is None
            ):
                raise PromotionCandidateError("candidate move message is not the fixed sanitized model-source shape")


def _is_reparse(path: str) -> bool:
    try:
        metadata = os.lstat(path)
    except OSError:
        return True
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def _assert_direct_ancestors(path: str, *, include_leaf: bool) -> None:
    absolute = os.path.abspath(path)
    if absolute.startswith("\\\\"):
        raise PromotionCandidateError("UNC paths are not accepted")
    candidate = Path(absolute)
    parts = candidate.parts if include_leaf else candidate.parent.parts
    if not parts:
        raise PromotionCandidateError("path has no local parent")
    current = Path(parts[0])
    for part in parts[1:]:
        current /= part
        if not os.path.exists(current) or _is_reparse(str(current)):
            raise PromotionCandidateError("path traverses a missing or reparse component")


def _read_regular_file(path: str) -> bytes:
    absolute = os.path.abspath(path)
    _assert_direct_ancestors(absolute, include_leaf=True)
    before = os.lstat(absolute)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > EXPORT_MAX_BYTES:
        raise PromotionCandidateError("reviewer export must be one bounded regular file")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(absolute, flags)
    except OSError as error:
        raise PromotionCandidateError("reviewer export could not be opened safely") from error
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or (opened.st_dev, opened.st_ino, opened.st_size)
            != (before.st_dev, before.st_ino, before.st_size)
        ):
            raise PromotionCandidateError("reviewer export identity changed during open")
        chunks: list[bytes] = []
        total = 0
        while True:
            block = os.read(descriptor, 65_536)
            if not block:
                break
            total += len(block)
            if total > EXPORT_MAX_BYTES:
                raise PromotionCandidateError("reviewer export is oversized")
            chunks.append(block)
    finally:
        os.close(descriptor)
    after = os.lstat(absolute)
    if (after.st_dev, after.st_ino, after.st_size) != (before.st_dev, before.st_ino, before.st_size):
        raise PromotionCandidateError("reviewer export changed during read")
    return b"".join(chunks)


def _assert_output_target(
    repo_root: str,
    destination: str,
) -> tuple[str, str, tuple[int, int]]:
    root = os.path.abspath(repo_root)
    target = os.path.abspath(destination)
    if os.path.lexists(target):
        raise PromotionCandidateError("candidate output already exists; overwrite is forbidden")
    try:
        shared_path = os.path.commonpath([root, target])
    except ValueError:
        shared_path = None
    if shared_path == root:
        raise PromotionCandidateError("candidate output must remain outside the source repository")
    parent = os.path.dirname(target)
    _assert_direct_ancestors(parent, include_leaf=True)
    if not os.path.isdir(parent) or _is_reparse(parent):
        raise PromotionCandidateError("candidate output parent is not a direct local directory")
    parent_metadata = os.lstat(parent)
    return target, parent, (parent_metadata.st_dev, parent_metadata.st_ino)


def _write_new(path: str, data: bytes) -> None:
    with open(path, "xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _json_bytes(value: Any) -> bytes:
    return (canonical_json(value) + "\n").encode("utf-8")


def _tree_digest(path: str) -> str:
    entries: list[dict[str, Any]] = []
    if not os.path.isdir(path):
        return canonical_digest(entries)
    for current, directories, files in os.walk(path, followlinks=False):
        if _is_reparse(current):
            raise PromotionCandidateError("protected artifact tree contains a reparse point")
        directories.sort()
        files.sort()
        for name in directories:
            if _is_reparse(os.path.join(current, name)):
                raise PromotionCandidateError("protected artifact tree contains a reparse point")
        for name in files:
            absolute = os.path.join(current, name)
            relative = os.path.relpath(absolute, path).replace(os.sep, "/")
            if _is_reparse(absolute):
                raise PromotionCandidateError("protected artifact tree contains a reparse point")
            entries.append({"path": relative, "sha256": sha256_hex(Path(absolute).read_bytes())})
    return canonical_digest(entries)


def prepare_publication_candidate(repo_root: str, export_path: str, destination: str) -> dict[str, Any]:
    """Verify one export and atomically write a candidate-only directory."""

    root = os.path.abspath(repo_root)
    manifest_path = os.path.join(root, "docs", "AGENTWARS_PUBLICATION_MANIFEST.v1.json")
    artifact_path = os.path.join(root, "publishing", "agentwars-public-v1")
    if not os.path.isfile(manifest_path):
        raise PromotionCandidateError("BuilderWars publication manifest is unavailable")
    target, parent, parent_identity = _assert_output_target(root, destination)
    raw = _read_regular_file(export_path)
    validated = _validate_export(raw)
    manifest_before = sha256_hex(Path(manifest_path).read_bytes())
    artifact_before = _tree_digest(artifact_path)
    current_manifest = load_publication_manifest(root, manifest_path)
    chain_head = validated["body"]["chainHead"]
    transcript_sha = validated["body"]["transcriptSha256"]
    if any(
        row["sourceChainHead"] == chain_head or row["sourceFileSha256"] == transcript_sha
        for row in current_manifest["entries"]
    ):
        raise PromotionCandidateError("reviewed receipt is already represented in the publication manifest")

    stage = tempfile.mkdtemp(prefix=".agentwars-promotion-candidate-", dir=parent)
    moved = False
    try:
        transcript_name = "transcript.jsonl"
        transcript_path = os.path.join(stage, transcript_name)
        _write_new(transcript_path, validated["transcript"])
        receipt, _records = _validate_projection(validated, transcript_path)
        game = validated["job"]["game"]
        seed = validated["job"]["seed"]
        match_id = validated["body"]["matchId"]
        source_path = f"matches/agentwars-review-candidates/{game}/{seed}-{match_id}/{chain_head}.jsonl"
        totals = {
            key: sum(row[key] for row in receipt["moveSourceClaims"])
            for key in ("model", "fallback", "scripted", "other")
        }
        candidate_id = "candidate_" + canonical_digest(
            {
                "sourceExportSha256": validated["rawSha256"],
                "decisionId": validated["decision"]["decisionId"],
                "requestId": validated["request"]["requestId"],
                "receiptId": chain_head,
            }
        )[:24]
        authorizations = {
            "manifestMutationAuthorized": False,
            "generatedArtifactMutationAuthorized": False,
            "publicationAuthorized": False,
            "deploymentAuthorized": False,
            "rankingAuthorized": False,
            "providerOrModelAttested": False,
            "sourceControlReviewRequired": True,
        }
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
                "sourceChainHead": chain_head,
                "sourceCounts": totals,
                "decision": "eligible_for_review",
                "titleEligible": False,
                "label": f"Private {game} reviewer-approval claim; source-control review required",
            },
            "authorizations": authorizations,
        }
        preview_bytes = _json_bytes(receipt)
        manifest_candidate_bytes = _json_bytes(manifest_candidate)
        _write_new(os.path.join(stage, "public-receipt-preview.json"), preview_bytes)
        _write_new(os.path.join(stage, "manifest-entry-candidate.json"), manifest_candidate_bytes)
        files = {
            transcript_name: {
                "sha256": sha256_hex(validated["transcript"]),
                "bytes": len(validated["transcript"]),
            },
            "public-receipt-preview.json": {
                "sha256": sha256_hex(preview_bytes),
                "bytes": len(preview_bytes),
            },
            "manifest-entry-candidate.json": {
                "sha256": sha256_hex(manifest_candidate_bytes),
                "bytes": len(manifest_candidate_bytes),
            },
        }
        candidate_core = {
            "schemaVersion": "agentwars.publication-candidate.v1",
            "candidateId": candidate_id,
            "candidateStatus": "offline_export_verified_candidate_only",
            "sourceContract": "nymrel_reviewer_case_response_shape.v1",
            "sourceExport": {
                "exactFileSha256": validated["rawSha256"],
                "canonicalPayloadSha256": validated["canonicalPayloadSha256"],
                "exactBytes": validated["rawBytes"],
                "reviewerAccessClaim": "authorized_reviewer",
                "reviewerExportOriginAttested": False,
                "reviewerIdentityAttested": False,
                "serverSignatureVerified": False,
                "authenticatedTransportVerifiedOffline": False,
            },
            "reviewDecisionClaim": {
                "status": "approved",
                "reasonCode": APPROVAL_REASON,
                "publicationDecision": APPROVAL_DECISION,
                "promotionStatus": APPROVAL_STATUS,
                "decisionReceiptCommitment": canonical_digest(validated["decision"]),
                "requestCommitment": canonical_digest(validated["request"]),
            },
            "evidenceBindings": {
                "jobCommitmentSha256": validated["body"]["jobCommitmentSha256"],
                "evidenceBundleSha256": validated["body"]["evidenceBundleSha256"],
                "resultBodySha256": validated["request"]["resultBodySha256"],
                "summarySha256": validated["body"]["summarySha256"],
                "summaryDigest": validated["body"]["summaryDigest"],
                "compressedTranscriptSha256": validated["body"]["compressedTranscriptSha256"],
                "transcriptSha256": transcript_sha,
                "projectionDigest": receipt["projectionDigest"],
                "chainHead": chain_head,
                "engineSha256": ENGINE_SHA256,
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
            "authorizations": authorizations,
            "truthBoundary": (
                "The export's internal commitments and embedded replay verify, but the offline file "
                "does not cryptographically prove its Nymrel server origin or reviewer identity. "
                "Only a separate reviewed source commit may choose a publication decision."
            ),
        }
        candidate = {**candidate_core, "candidateDigest": canonical_digest(candidate_core)}
        _write_new(os.path.join(stage, "candidate.json"), _json_bytes(candidate))

        if sha256_hex(Path(manifest_path).read_bytes()) != manifest_before:
            raise PromotionCandidateError("publication manifest changed during candidate preparation")
        if _tree_digest(artifact_path) != artifact_before:
            raise PromotionCandidateError("generated publication artifact changed during candidate preparation")
        _assert_direct_ancestors(parent, include_leaf=True)
        parent_after = os.lstat(parent)
        if (parent_after.st_dev, parent_after.st_ino) != parent_identity or _is_reparse(parent):
            raise PromotionCandidateError("candidate output parent changed during preparation")
        if os.path.lexists(target):
            raise PromotionCandidateError("candidate output appeared before atomic install")
        if sorted(os.listdir(stage)) != [
            "candidate.json",
            "manifest-entry-candidate.json",
            "public-receipt-preview.json",
            "transcript.jsonl",
        ]:
            raise PromotionCandidateError("candidate staging tree contains unexpected files")
        os.rename(stage, target)
        moved = True
        return {
            "status": "candidate_prepared_not_published",
            "candidateId": candidate_id,
            "candidateDigest": candidate["candidateDigest"],
            "receiptId": chain_head,
            "output": target,
            "manifestMutationAuthorized": False,
            "publicationAuthorized": False,
            "deploymentAuthorized": False,
            "rankingAuthorized": False,
            "reviewerExportOriginAttested": False,
            "sourceControlReviewRequired": True,
        }
    finally:
        if (
            not moved
            and os.path.lexists(stage)
            and not _is_reparse(stage)
            and stat.S_ISDIR(os.lstat(stage).st_mode)
        ):
            absolute_stage = os.path.abspath(stage)
            if os.path.commonpath([parent, absolute_stage]) == parent and os.path.basename(absolute_stage).startswith(
                ".agentwars-promotion-candidate-"
            ):
                shutil.rmtree(absolute_stage)
