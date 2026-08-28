"""Framework-neutral AgentWars hosted control-plane handlers.

Callers are responsible for authenticating browser/account requests before
passing an owner id.  Runner requests are authenticated here by Ed25519 and a
durable nonce.  No method accepts or executes provider credentials or entrant
code.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import json
from collections.abc import Mapping

from provider_hub.local_runner import (
    PAIRING_PROTOCOL,
    REQUEST_PROTOCOL,
    RUNNER_PROBE_BODY,
    RUNNER_PROBE_EVIDENCE_CLASS,
    RUNNER_PROBE_FALSE_ATTESTATIONS,
    RUNNER_PROBE_PATH,
    validate_json_body,
)
from provider_hub.match_worker import (
    MATCH_JOB_ABANDON_PATH,
    MATCH_JOB_EVIDENCE_CLASS,
    MATCH_JOB_FALSE_ATTESTATIONS,
    MATCH_JOB_KIND,
    MATCH_JOB_MAX_ATTEMPTS,
    MATCH_JOB_POLL_BODY,
    MATCH_JOB_POLL_PATH,
    MATCH_JOB_PROTOCOL,
    MATCH_JOB_RENEW_PATH,
    MATCH_JOB_RESULT_PATH,
)
from provider_hub_hosted.store import (
    FixtureJobRecord,
    HostedControlPlaneStore,
    HostedStoreError,
    LeaseGrant,
    validate_attempt_id,
    validate_job_id,
    validate_owner_id,
    validate_sha256_digest,
)
from provider_hub_hosted.verify import (
    IncomingSignedRequest,
    SignedRequestError,
    VerifiedRunnerRequest,
    verify_signed_request,
)


MAX_JSON_DEPTH = 32


@dataclasses.dataclass(frozen=True)
class HandlerResponse:
    status_code: int
    payload: Mapping[str, object]


def _decode_exact_object(body: bytes, expected_keys: set[str], label: str) -> dict[str, object]:
    try:
        body = validate_json_body(body)
    except (TypeError, ValueError, RecursionError) as error:
        raise HostedStoreError("invalid_json", f"{label} body is invalid") from error

    def reject_float(_value: str):
        raise HostedStoreError("invalid_json", f"{label} body must not contain floats")

    def reject_constant(_value: str):
        raise HostedStoreError("invalid_json", f"{label} body must not contain non-finite values")

    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise HostedStoreError("invalid_json", f"{label} body contains duplicate keys")
            result[key] = value
        return result

    try:
        value = json.loads(
            body.decode("utf-8"),
            parse_float=reject_float,
            parse_constant=reject_constant,
            object_pairs_hook=reject_duplicates,
        )
    except HostedStoreError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError, RecursionError) as error:
        raise HostedStoreError("invalid_json", f"{label} body is invalid") from error
    if not isinstance(value, dict) or set(value) != expected_keys:
        raise HostedStoreError("invalid_schema", f"{label} body has an invalid exact schema")
    stack = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        if depth > MAX_JSON_DEPTH:
            raise HostedStoreError("invalid_json", f"{label} body exceeds the nesting limit")
        if isinstance(current, dict):
            stack.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, list):
            stack.extend((item, depth + 1) for item in current)
    return value


def _require_signed_envelope(request: IncomingSignedRequest) -> IncomingSignedRequest:
    if not isinstance(request, IncomingSignedRequest):
        raise SignedRequestError("invalid_request", "signed request envelope is invalid")
    text_fields = (
        request.method,
        request.path,
        request.protocol_version,
        request.runner_id,
        request.timestamp,
        request.nonce,
        request.signature,
    )
    if any(type(value) is not str for value in text_fields) or type(request.body) is not bytes:
        raise SignedRequestError("invalid_request", "signed request envelope is invalid")
    return request


def _validate_attempt_payload(
    payload: Mapping[str, object],
    label: str,
    *,
    result_digests: bool = False,
) -> dict[str, object]:
    try:
        job_id = validate_job_id(payload["jobId"])
        attempt_id = validate_attempt_id(payload["attemptId"])
        lease_epoch = payload["leaseEpoch"]
        if type(lease_epoch) is not int or not 1 <= lease_epoch <= MATCH_JOB_MAX_ATTEMPTS:
            raise HostedStoreError("invalid_epoch", "lease epoch is invalid")
        validated: dict[str, object] = {
            "jobId": job_id,
            "attemptId": attempt_id,
            "leaseEpoch": lease_epoch,
        }
        if result_digests:
            validated.update({
                "engineSha256": validate_sha256_digest(payload["engineSha256"], "engine digest"),
                "outputSha256": validate_sha256_digest(payload["outputSha256"], "output digest"),
                "transcriptSha256": validate_sha256_digest(
                    payload["transcriptSha256"], "transcript digest"
                ),
            })
        return validated
    except (KeyError, TypeError, HostedStoreError) as error:
        raise HostedStoreError("invalid_schema", f"{label} body has invalid field values") from error


class HostedControlPlane:
    """Small reference service over :class:`HostedControlPlaneStore`."""

    def __init__(self, store: HostedControlPlaneStore):
        if not isinstance(store, HostedControlPlaneStore):
            raise TypeError("store must be HostedControlPlaneStore")
        self.store = store

    def create_pairing(
        self,
        owner_id: str,
        *,
        now: dt.datetime | None = None,
    ) -> HandlerResponse:
        challenge = self.store.create_pairing_challenge(owner_id, now=now)
        return HandlerResponse(201, {
            "schemaVersion": 1,
            "protocolVersion": PAIRING_PROTOCOL,
            "challengeId": challenge.challenge_id,
            "pairingSecret": challenge.pairing_secret,
            "expiresAt": challenge.expires_at,
        })

    def claim_pairing(
        self,
        body: bytes,
        *,
        now: dt.datetime | None = None,
    ) -> HandlerResponse:
        payload = _decode_exact_object(
            body,
            {
                "pairingSecret", "providerId", "connectionMode", "displayLabel",
                "harnessId", "harnessVersion", "harnessDigest", "publicKey",
            },
            "pairing claim",
        )
        claim = self.store.claim_pairing(payload, now=now)
        return HandlerResponse(202 if claim.status == "claimed" else 200, {
            "schemaVersion": 1,
            "protocolVersion": PAIRING_PROTOCOL,
            "status": claim.status,
            "challengeId": claim.challenge_id,
            "state": claim.state,
            "fingerprint": claim.fingerprint,
        })

    def confirm_pairing(
        self,
        owner_id: str,
        challenge_id: str,
        *,
        approved: bool,
        now: dt.datetime | None = None,
    ) -> HandlerResponse:
        confirmation = self.store.confirm_pairing(
            owner_id, challenge_id, approved=approved, now=now
        )
        return HandlerResponse(200, {
            "schemaVersion": 1,
            "protocolVersion": PAIRING_PROTOCOL,
            "challengeId": confirmation.challenge_id,
            "state": confirmation.state,
            "runnerId": confirmation.runner_id,
            "fingerprint": confirmation.fingerprint,
        })

    def revoke_runner(
        self,
        owner_id: str,
        runner_id: str,
        *,
        now: dt.datetime | None = None,
    ) -> HandlerResponse:
        runner = self.store.revoke_runner(owner_id, runner_id, now=now)
        return HandlerResponse(200, {
            "schemaVersion": 1,
            "status": "revoked",
            "runnerId": runner.runner_id,
            "revokedAt": runner.revoked_at,
        })

    def delete_runner(self, owner_id: str, runner_id: str) -> HandlerResponse:
        self.store.delete_runner(owner_id, runner_id)
        return HandlerResponse(200, {
            "schemaVersion": 1,
            "status": "deleted",
            "runnerId": runner_id,
        })

    def delete_owner(self, owner_id: str) -> HandlerResponse:
        owner_id = validate_owner_id(owner_id)
        deleted = self.store.delete_owner(owner_id)
        return HandlerResponse(200, {
            "schemaVersion": 1,
            "status": "deleted" if deleted else "not_found",
            "ownerId": owner_id,
        })

    def create_fixture_job(
        self,
        owner_id: str,
        runner_id: str,
        *,
        seed: str | None = None,
        now: dt.datetime | None = None,
    ) -> HandlerResponse:
        job = self.store.create_fixture_job(owner_id, runner_id, seed=seed, now=now)
        return HandlerResponse(201, {
            "schemaVersion": 1,
            "protocolVersion": MATCH_JOB_PROTOCOL,
            "status": "queued",
            "jobId": job.job_id,
            "runnerId": job.runner_id,
            "kind": job.kind,
            "evidenceClass": MATCH_JOB_EVIDENCE_CLASS,
            **{field: False for field in MATCH_JOB_FALSE_ATTESTATIONS},
        })

    def _verify(
        self,
        request: IncomingSignedRequest,
        *,
        path: str,
        now: dt.datetime | None,
    ) -> VerifiedRunnerRequest:
        return verify_signed_request(self.store, request, now=now, expected_path=path)

    @staticmethod
    def _runner_base(verified: VerifiedRunnerRequest, *, protocol: str) -> dict[str, object]:
        false_fields = (
            RUNNER_PROBE_FALSE_ATTESTATIONS
            if protocol == REQUEST_PROTOCOL
            else MATCH_JOB_FALSE_ATTESTATIONS
        )
        return {
            "schemaVersion": 1,
            "protocolVersion": protocol,
            "runnerId": verified.runner.runner_id,
            "fingerprint": verified.runner.fingerprint,
            "requestBodySha256": verified.body_sha256,
            "evidenceClass": (
                RUNNER_PROBE_EVIDENCE_CLASS
                if protocol == REQUEST_PROTOCOL
                else MATCH_JOB_EVIDENCE_CLASS
            ),
            **{field: False for field in false_fields},
        }

    def probe(
        self,
        request: IncomingSignedRequest,
        *,
        now: dt.datetime | None = None,
    ) -> HandlerResponse:
        request = _require_signed_envelope(request)
        if request.method != "POST" or request.body != RUNNER_PROBE_BODY:
            raise HostedStoreError("invalid_probe", "runner probe bytes are invalid")
        verified = self._verify(request, path=RUNNER_PROBE_PATH, now=now)
        return HandlerResponse(200, {
            **self._runner_base(verified, protocol=REQUEST_PROTOCOL),
            "status": "accepted",
        })

    def poll(
        self,
        request: IncomingSignedRequest,
        *,
        now: dt.datetime | None = None,
    ) -> HandlerResponse:
        request = _require_signed_envelope(request)
        if request.method != "POST" or request.body != MATCH_JOB_POLL_BODY:
            raise HostedStoreError("invalid_poll", "match-job poll bytes are invalid")
        verified = self._verify(request, path=MATCH_JOB_POLL_PATH, now=now)
        state = self.store.poll_job(verified.runner.runner_id, now=now)
        base = self._runner_base(verified, protocol=MATCH_JOB_PROTOCOL)
        if isinstance(state, LeaseGrant):
            return HandlerResponse(200, {
                **base,
                "status": "granted",
                "recovery": state.recovery,
                "attempt": self._attempt_payload(state),
                "job": self._job_payload(state.job),
            })
        if state.status == "completed":
            return HandlerResponse(200, {**base, "status": "completed", "result": dict(state.result)})
        if state.status == "exhausted":
            return HandlerResponse(200, {
                **base,
                "status": "exhausted",
                "job": {
                    "jobId": state.job_id,
                    "kind": MATCH_JOB_KIND,
                    "attemptsUsed": state.attempts_used,
                    "maxAttempts": state.max_attempts,
                },
            })
        raise HostedStoreError("invalid_job_state", "match job returned an unsupported state")

    def renew(
        self,
        request: IncomingSignedRequest,
        *,
        now: dt.datetime | None = None,
    ) -> HandlerResponse:
        request = _require_signed_envelope(request)
        if request.method != "POST":
            raise HostedStoreError("invalid_renew", "match-job renew method is invalid")
        payload = _decode_exact_object(
            request.body, {"jobId", "attemptId", "leaseEpoch"}, "match-job renew"
        )
        payload = _validate_attempt_payload(payload, "match-job renew")
        verified = self._verify(request, path=MATCH_JOB_RENEW_PATH, now=now)
        grant = self.store.renew_attempt(
            verified.runner.runner_id,
            payload["jobId"],
            payload["attemptId"],
            payload["leaseEpoch"],
            now=now,
        )
        return HandlerResponse(200, {
            **self._runner_base(verified, protocol=MATCH_JOB_PROTOCOL),
            "status": "renewed",
            "attempt": self._attempt_payload(grant),
        })

    def abandon(
        self,
        request: IncomingSignedRequest,
        *,
        now: dt.datetime | None = None,
    ) -> HandlerResponse:
        request = _require_signed_envelope(request)
        if request.method != "POST":
            raise HostedStoreError("invalid_abandon", "match-job abandon method is invalid")
        payload = _decode_exact_object(
            request.body, {"jobId", "attemptId", "leaseEpoch"}, "match-job abandon"
        )
        payload = _validate_attempt_payload(payload, "match-job abandon")
        verified = self._verify(request, path=MATCH_JOB_ABANDON_PATH, now=now)
        terminal = self.store.abandon_attempt(
            verified.runner.runner_id,
            payload["jobId"],
            payload["attemptId"],
            payload["leaseEpoch"],
            now=now,
        )
        return HandlerResponse(200, {
            **self._runner_base(verified, protocol=MATCH_JOB_PROTOCOL),
            "status": "abandoned",
            "job": {
                "jobId": terminal.job_id,
                "kind": MATCH_JOB_KIND,
                "attemptsUsed": terminal.attempts_used,
                "maxAttempts": terminal.max_attempts,
                "nextState": terminal.status,
            },
        })

    def result(
        self,
        request: IncomingSignedRequest,
        *,
        now: dt.datetime | None = None,
    ) -> HandlerResponse:
        request = _require_signed_envelope(request)
        if request.method != "POST":
            raise HostedStoreError("invalid_result", "match-job result method is invalid")
        payload = _decode_exact_object(
            request.body,
            {
                "jobId", "attemptId", "leaseEpoch", "engineSha256",
                "outputSha256", "transcriptSha256",
            },
            "match-job result",
        )
        payload = _validate_attempt_payload(payload, "match-job result", result_digests=True)
        verified = self._verify(request, path=MATCH_JOB_RESULT_PATH, now=now)
        recorded = self.store.record_result(
            verified.runner.runner_id,
            job_id=payload["jobId"],
            attempt_id=payload["attemptId"],
            lease_epoch=payload["leaseEpoch"],
            engine_sha256=payload["engineSha256"],
            output_sha256=payload["outputSha256"],
            transcript_sha256=payload["transcriptSha256"],
            now=now,
        )
        return HandlerResponse(200, {
            **self._runner_base(verified, protocol=MATCH_JOB_PROTOCOL),
            "status": "recorded",
            "duplicate": recorded.duplicate,
            "result": dict(recorded.result),
        })

    def public_replay(self, job_id: str) -> HandlerResponse:
        projection = self.store.get_public_projection(job_id)
        if projection is None:
            return HandlerResponse(404, {"schemaVersion": 1, "status": "not_found"})
        return HandlerResponse(200, projection)

    @staticmethod
    def _attempt_payload(grant: LeaseGrant) -> Mapping[str, object]:
        return {
            "attemptId": grant.attempt_id,
            "leaseEpoch": grant.lease_epoch,
            "attemptNumber": grant.attempt_number,
            "renewCount": grant.renew_count,
            "renewalsRemaining": grant.renewals_remaining,
            "leaseExpiresAt": grant.lease_expires_at,
        }

    @staticmethod
    def _job_payload(job: FixtureJobRecord) -> Mapping[str, object]:
        return {
            "jobId": job.job_id,
            "kind": job.kind,
            "requiredHarnessId": job.required_harness_id,
            "requiredHarnessDigest": job.required_harness_digest,
            "engineId": job.engine_id,
            "engineSha256": job.engine_sha256,
            "rulesetId": job.ruleset_id,
            "rulesSha256": job.rules_sha256,
            "seed": job.seed,
            "inputSha256": job.input_sha256,
            "inputBytesBase64url": job.input_bytes_base64url,
            "maxAttempts": job.max_attempts,
        }
