"""Server-side verification for customer-local AgentWars runner requests."""

from __future__ import annotations

import base64
import dataclasses
import datetime as dt
import hashlib
import hmac
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from provider_hub.local_runner import (
    REQUEST_PROTOCOL,
    base64url_no_pad,
    canonical_runner_request,
    validate_canonical_instant,
    validate_json_body,
    validate_nonce,
    validate_request_path,
    validate_runner_id,
)
from provider_hub_hosted.store import (
    HostedControlPlaneStore,
    HostedStoreError,
    RunnerRecord,
    validate_owner_id,
)


MAX_REQUEST_AGE_SECONDS = 300
MAX_REQUEST_FUTURE_SECONDS = 60
_SIGNATURE_RE = re.compile(r"^[A-Za-z0-9_-]{86}$")


class SignedRequestError(ValueError):
    """A signed request failed its transport-authentication boundary."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclasses.dataclass(frozen=True)
class IncomingSignedRequest:
    method: str
    path: str
    body: bytes
    protocol_version: str
    runner_id: str
    timestamp: str
    nonce: str
    signature: str = dataclasses.field(repr=False)


@dataclasses.dataclass(frozen=True)
class VerifiedRunnerRequest:
    method: str
    path: str
    body: bytes
    body_sha256: str
    timestamp: str
    nonce: str
    runner: RunnerRecord


def _decode_canonical_base64url(value: str, expected_bytes: int, label: str) -> bytes:
    if not isinstance(value, str):
        raise SignedRequestError("invalid_encoding", f"{label} is invalid")
    try:
        padded = value + "=" * ((4 - len(value) % 4) % 4)
        decoded = base64.b64decode(padded, altchars=b"-_", validate=True)
    except (ValueError, TypeError) as error:
        raise SignedRequestError("invalid_encoding", f"{label} is invalid") from error
    if len(decoded) != expected_bytes or base64url_no_pad(decoded) != value:
        raise SignedRequestError("invalid_encoding", f"{label} is not canonical")
    return decoded


def _aware_utc(value: dt.datetime | None) -> dt.datetime:
    current = value or dt.datetime.now(dt.timezone.utc)
    if not isinstance(current, dt.datetime) or current.tzinfo is None:
        raise SignedRequestError("invalid_time", "verification time must be timezone-aware")
    return current.astimezone(dt.timezone.utc)


def verify_signed_request(
    store: HostedControlPlaneStore,
    request: IncomingSignedRequest,
    *,
    now: dt.datetime | None = None,
    expected_path: str | None = None,
    expected_owner_id: str | None = None,
) -> VerifiedRunnerRequest:
    """Verify exact bytes and durably consume a runner nonce.

    Signature verification occurs before nonce insertion so an unauthenticated
    caller cannot burn a legitimate nonce.  The store rechecks runner state and
    ownership in the nonce transaction to close the verify/use race.
    """
    if not isinstance(store, HostedControlPlaneStore):
        raise TypeError("store must be HostedControlPlaneStore")
    if not isinstance(request, IncomingSignedRequest):
        raise SignedRequestError("invalid_request", "signed request envelope is invalid")
    if request.protocol_version != REQUEST_PROTOCOL:
        raise SignedRequestError("invalid_protocol", "runner request protocol is unsupported")
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        raise SignedRequestError("invalid_method", "runner request method is unsupported")
    try:
        path = validate_request_path(request.path)
        runner_id = validate_runner_id(request.runner_id)
        timestamp = validate_canonical_instant(request.timestamp)
        nonce = validate_nonce(request.nonce)
        body = validate_json_body(request.body)
    except ValueError as error:
        raise SignedRequestError("invalid_request", "signed request contract is invalid") from error
    if expected_path is not None:
        try:
            expected_path = validate_request_path(expected_path)
        except ValueError as error:
            raise SignedRequestError("invalid_path", "expected request path is invalid") from error
        if not hmac.compare_digest(path, expected_path):
            raise SignedRequestError("wrong_path", "signed request path is not accepted here")
    if expected_owner_id is not None:
        try:
            expected_owner_id = validate_owner_id(expected_owner_id)
        except HostedStoreError as error:
            raise SignedRequestError("invalid_owner", "expected owner is invalid") from error

    current = _aware_utc(now)
    signed_at = dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    age_seconds = (current - signed_at).total_seconds()
    if age_seconds > MAX_REQUEST_AGE_SECONDS:
        raise SignedRequestError("stale_request", "signed request is stale")
    if age_seconds < -MAX_REQUEST_FUTURE_SECONDS:
        raise SignedRequestError("future_request", "signed request is too far in the future")

    body_sha256 = hashlib.sha256(body).hexdigest()
    try:
        canonical = canonical_runner_request(
            method=request.method,
            path=path,
            body_sha256=body_sha256,
            timestamp=timestamp,
            nonce=nonce,
            runner_id=runner_id,
        )
        runner = store.get_runner(runner_id)
    except (ValueError, HostedStoreError) as error:
        raise SignedRequestError("runner_refused", "runner request was refused") from error
    if runner.state != "active":
        raise SignedRequestError("runner_refused", "runner request was refused")
    if expected_owner_id is not None and not hmac.compare_digest(runner.owner_id, expected_owner_id):
        raise SignedRequestError("owner_mismatch", "runner request was refused")
    if not isinstance(request.signature, str) or _SIGNATURE_RE.fullmatch(request.signature) is None:
        raise SignedRequestError("invalid_signature", "runner signature is invalid")
    signature = _decode_canonical_base64url(request.signature, 64, "runner signature")
    public_key = _decode_canonical_base64url(runner.public_key, 32, "runner public key")
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(
            signature, canonical.encode("utf-8")
        )
    except (InvalidSignature, ValueError) as error:
        raise SignedRequestError("invalid_signature", "runner signature is invalid") from error

    try:
        store.consume_nonce(
            runner_id=runner.runner_id,
            fingerprint=runner.fingerprint,
            nonce=nonce,
            request_timestamp_ms=int(signed_at.timestamp() * 1000),
            body_sha256=body_sha256,
            observed_at_ms=int(current.timestamp() * 1000),
            expected_owner_id=expected_owner_id,
        )
    except HostedStoreError as error:
        if error.code == "replayed_request":
            raise SignedRequestError("replayed_request", "signed request was already used") from error
        raise SignedRequestError("runner_refused", "runner request was refused") from error
    return VerifiedRunnerRequest(
        method=request.method,
        path=path,
        body=body,
        body_sha256=body_sha256,
        timestamp=timestamp,
        nonce=nonce,
        runner=runner,
    )
