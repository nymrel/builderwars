"""Fail-closed browser authorization gateway reference for BuilderWars.

The gateway is deliberately framework-neutral.  A production HTTP adapter must
verify the Clerk session and return :class:`VerifiedBrowserPrincipal`; this
module never receives a session cookie or bearer token.  It then enforces one
exact browser origin, canonical CSRF tokens, strict route/body schemas, an
opaque owner-id derivation, and an injected account rate limiter before calling
the owner-scoped hosted control plane.

This is a local conformance reference, not live Clerk integration, a durable
edge limiter, a production store, or production security approval.
"""

from __future__ import annotations

import base64
import dataclasses
import datetime as dt
import hashlib
import hmac
import json
import os
import re
import threading
import urllib.parse
from collections.abc import Callable, Mapping
from typing import Protocol, runtime_checkable

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from provider_hub.local_runner import RunnerClientError, validate_challenge_id, validate_runner_id
from provider_hub_hosted.handlers import HandlerResponse, HostedControlPlane
from provider_hub_hosted.store import (
    BROWSER_IDEMPOTENCY_TTL_SECONDS,
    HostedStoreError,
    validate_idempotency_key,
    validate_owner_id,
)


BROWSER_GATEWAY_SCHEMA = "agentwars.browser_authorization_gateway/1"
BROWSER_GATEWAY_EVIDENCE_CLASS = "local_browser_authorization_reference"
OWNER_DERIVATION_CLASS = "hmac_sha256_truncated_128_v1"
MAX_BROWSER_BODY_BYTES = 16_384
MAX_PRINCIPAL_AGE_SECONDS = 300
MAX_PRINCIPAL_FUTURE_SECONDS = 30
CSRF_TOKEN_BYTES = 32
IDEMPOTENCY_RESPONSE_KEY_BYTES = 32
IDEMPOTENCY_NONCE_BYTES = 12

PRODUCTION_AUTHORITY = {
    "clerkTokenVerificationActive": False,
    "productionSessionCookieConfigured": False,
    "productionCsrfCookieConfigured": False,
    "durableEdgeRateLimitsActive": False,
    "durableAccountRateLimitsActive": False,
    "productionOwnerPepperProvisioned": False,
    "productionIdempotencyResponseKeyProvisioned": False,
    "productionStoreIntegrated": False,
    "productionSecurityApproved": False,
    "publicLaunch": False,
}

_SUBJECT_RE = re.compile(r"^[A-Za-z0-9_-]{1,256}$")
_SESSION_RE = re.compile(r"^[A-Za-z0-9_-]{1,256}$")
_CSRF_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")
_SEED_RE = re.compile(r"^[A-Za-z0-9_-]{22}$")
_PAIRING_CONFIRM_RE = re.compile(r"^/v1/browser/pairings/([A-Za-z0-9_-]{22})/confirm$")
_RUNNER_REVOKE_RE = re.compile(r"^/v1/browser/runners/(awr1_[A-Za-z0-9_-]{22})/revoke$")
_RUNNER_DELETE_RE = re.compile(r"^/v1/browser/runners/(awr1_[A-Za-z0-9_-]{22})$")
_FIXTURE_JOB_RE = re.compile(r"^/v1/browser/runners/(awr1_[A-Za-z0-9_-]{22})/fixture-jobs$")

_OPERATION_POLICIES = {
    "create_pairing": (6, 60),
    "confirm_pairing": (12, 60),
    "revoke_runner": (6, 60),
    "delete_runner": (6, 60),
    "create_fixture_job": (12, 60),
    "delete_owner": (2, 300),
}

_NOT_FOUND_CODES = {"not_found", "runner_not_found"}
_CONFLICT_CODES = {
    "pairing_conflict", "pairing_expired", "pairing_not_claimed",
    "pairing_rejected", "runner_conflict",
}


@dataclasses.dataclass(frozen=True)
class BrowserRequest:
    """Sanitized request facts; authentication material is intentionally absent."""

    method: str
    path: str
    body: bytes
    origin: str
    content_type: str | None
    csrf_cookie: str
    csrf_header: str
    idempotency_key: str = dataclasses.field(repr=False)


@dataclasses.dataclass(frozen=True)
class VerifiedBrowserPrincipal:
    """Result of an external, production-owned session verifier."""

    issuer: str
    subject: str = dataclasses.field(repr=False)
    session_id: str = dataclasses.field(repr=False)
    verified_at: dt.datetime
    authentication_class: str = "clerk_session"


@dataclasses.dataclass(frozen=True)
class BrowserGatewayResponse:
    status_code: int
    payload: Mapping[str, object]
    headers: Mapping[str, str] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    reset_after_seconds: int


class BrowserAuthenticationError(ValueError):
    """Expected authentication refusal without reflecting credential details."""


@runtime_checkable
class AccountRateLimiter(Protocol):
    """Injected owner-scoped limiter boundary; production must provide durability."""

    def check(
        self,
        owner_id: str,
        operation: str,
        *,
        now: dt.datetime,
    ) -> RateLimitDecision: ...


class InMemoryAccountRateLimiter:
    """Thread-safe local fixed-window reference; not a production perimeter."""

    def __init__(self, policies: Mapping[str, tuple[int, int]] | None = None):
        raw = dict(_OPERATION_POLICIES if policies is None else policies)
        if set(raw) != set(_OPERATION_POLICIES):
            raise ValueError("account rate-limit policy must cover every browser operation")
        normalized: dict[str, tuple[int, int]] = {}
        for operation, value in raw.items():
            if (
                type(value) is not tuple
                or len(value) != 2
                or type(value[0]) is not int
                or type(value[1]) is not int
                or not 1 <= value[0] <= 1_000
                or not 1 <= value[1] <= 86_400
            ):
                raise ValueError(f"account rate-limit policy for {operation} is invalid")
            normalized[operation] = value
        self._policies = normalized
        self._windows: dict[tuple[str, str, int], int] = {}
        self._lock = threading.Lock()

    def check(
        self,
        owner_id: str,
        operation: str,
        *,
        now: dt.datetime,
    ) -> RateLimitDecision:
        owner_id = validate_owner_id(owner_id)
        if operation not in self._policies:
            raise ValueError("browser operation has no rate-limit policy")
        current = _aware_utc(now)
        limit, window_seconds = self._policies[operation]
        epoch = int(current.timestamp())
        window_start = epoch - (epoch % window_seconds)
        key = (owner_id, operation, window_start)
        with self._lock:
            count = self._windows.get(key, 0)
            if count >= limit:
                remaining = 0
                allowed = False
            else:
                count += 1
                self._windows[key] = count
                remaining = limit - count
                allowed = True
            stale_before = window_start - max(seconds for _count, seconds in self._policies.values())
            for candidate in tuple(self._windows):
                if candidate[2] < stale_before:
                    del self._windows[candidate]
        reset_after = max(1, window_start + window_seconds - epoch)
        return RateLimitDecision(allowed, limit, remaining, reset_after)


class BrowserAuthorizationGateway:
    """Authorize exact browser commands before owner-scoped control-plane calls."""

    def __init__(
        self,
        control_plane: HostedControlPlane,
        *,
        allowed_origin: str,
        expected_issuer: str,
        owner_pepper: bytes,
        idempotency_response_key: bytes,
        rate_limiter: AccountRateLimiter,
    ):
        if not isinstance(control_plane, HostedControlPlane):
            raise TypeError("control_plane must be HostedControlPlane")
        if not isinstance(rate_limiter, AccountRateLimiter):
            raise TypeError("rate_limiter must implement AccountRateLimiter")
        if type(owner_pepper) is not bytes or len(owner_pepper) < 32:
            raise ValueError("owner pepper must contain at least 32 bytes")
        if (
            type(idempotency_response_key) is not bytes
            or len(idempotency_response_key) != IDEMPOTENCY_RESPONSE_KEY_BYTES
        ):
            raise ValueError("idempotency response key must contain exactly 32 bytes")
        self.control_plane = control_plane
        self.allowed_origin = _canonical_https_origin(allowed_origin, "browser origin")
        self.expected_issuer = _canonical_https_origin(expected_issuer, "principal issuer")
        self._owner_pepper = bytes(owner_pepper)
        self._idempotency_aead = AESGCM(bytes(idempotency_response_key))
        self._rate_limiter = rate_limiter

    def dispatch(
        self,
        request: BrowserRequest,
        *,
        resolve_principal: Callable[[], VerifiedBrowserPrincipal],
        now: dt.datetime | None = None,
    ) -> BrowserGatewayResponse:
        current = _aware_utc(now)
        try:
            request = self._preflight(request)
            operation, parameters, payload = self._route(request)
        except _BrowserRefusal as error:
            return _error_response(error.status_code, error.code)

        try:
            principal = resolve_principal()
        except BrowserAuthenticationError:
            return _error_response(401, "authentication_required")
        except Exception:
            return _error_response(503, "authentication_unavailable")
        try:
            owner_id = self.owner_id_for(principal, now=current)
        except _BrowserRefusal as error:
            return _error_response(error.status_code, error.code)

        try:
            decision = self._rate_limiter.check(owner_id, operation, now=current)
        except Exception:
            return _error_response(503, "rate_limit_unavailable")
        if type(decision) is not RateLimitDecision:
            return _error_response(503, "rate_limit_unavailable")
        rate_headers = {
            "RateLimit-Limit": str(decision.limit),
            "RateLimit-Remaining": str(decision.remaining),
            "RateLimit-Reset": str(decision.reset_after_seconds),
        }
        if not decision.allowed:
            return _error_response(
                429,
                "rate_limited",
                headers={**rate_headers, "Retry-After": str(decision.reset_after_seconds)},
            )

        request_digest = _browser_request_digest(request, operation)
        try:
            record = self.control_plane.store.run_browser_mutation_idempotent(
                owner_id,
                request.idempotency_key,
                operation,
                request_digest,
                execute=lambda: self._invoke_and_seal(
                    operation,
                    owner_id=owner_id,
                    idempotency_key=request.idempotency_key,
                    request_sha256=request_digest,
                    parameters=parameters,
                    payload=payload,
                    now=current,
                ),
                now=current,
            )
        except HostedStoreError as error:
            return self._store_error(error, headers=rate_headers)
        except Exception:
            return _error_response(503, "idempotency_unavailable", headers=rate_headers)
        try:
            response = self._unseal_response(
                record.status_code,
                record.sealed_response,
                owner_id=owner_id,
                idempotency_key=request.idempotency_key,
                operation=operation,
                request_sha256=request_digest,
            )
        except (InvalidTag, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
            return _error_response(503, "idempotency_unavailable", headers=rate_headers)
        return BrowserGatewayResponse(
            response.status_code,
            dict(response.payload),
            {
                **rate_headers,
                "Idempotency-Replayed": "true" if record.duplicate else "false",
                "Idempotency-Expires-At": record.expires_at,
            },
        )

    def owner_id_for(
        self,
        principal: VerifiedBrowserPrincipal,
        *,
        now: dt.datetime | None = None,
    ) -> str:
        current = _aware_utc(now)
        if type(principal) is not VerifiedBrowserPrincipal:
            raise _BrowserRefusal(401, "authentication_required")
        if principal.authentication_class != "clerk_session":
            raise _BrowserRefusal(401, "authentication_required")
        try:
            issuer = _canonical_https_origin(principal.issuer, "principal issuer")
        except (TypeError, ValueError):
            raise _BrowserRefusal(401, "authentication_required") from None
        if not hmac.compare_digest(issuer, self.expected_issuer):
            raise _BrowserRefusal(401, "authentication_required")
        if type(principal.subject) is not str or _SUBJECT_RE.fullmatch(principal.subject) is None:
            raise _BrowserRefusal(401, "authentication_required")
        if type(principal.session_id) is not str or _SESSION_RE.fullmatch(principal.session_id) is None:
            raise _BrowserRefusal(401, "authentication_required")
        try:
            verified_at = _aware_utc(principal.verified_at)
        except (TypeError, ValueError, HostedStoreError):
            raise _BrowserRefusal(401, "authentication_required") from None
        age_seconds = (current - verified_at).total_seconds()
        if age_seconds > MAX_PRINCIPAL_AGE_SECONDS or age_seconds < -MAX_PRINCIPAL_FUTURE_SECONDS:
            raise _BrowserRefusal(401, "authentication_required")
        material = (
            BROWSER_GATEWAY_SCHEMA.encode("ascii")
            + b"\x00"
            + issuer.encode("ascii")
            + b"\x00"
            + principal.subject.encode("ascii")
        )
        digest = hmac.new(self._owner_pepper, material, hashlib.sha256).digest()[:16]
        owner_id = "awu1_" + base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
        return validate_owner_id(owner_id)

    def contract(self) -> dict[str, object]:
        return {
            "schemaVersion": BROWSER_GATEWAY_SCHEMA,
            "evidenceClass": BROWSER_GATEWAY_EVIDENCE_CLASS,
            "ownerDerivationClass": OWNER_DERIVATION_CLASS,
            "operations": sorted(_OPERATION_POLICIES),
            "maxBodyBytes": MAX_BROWSER_BODY_BYTES,
            "principalMaxAgeSeconds": MAX_PRINCIPAL_AGE_SECONDS,
            "principalMaxFutureSeconds": MAX_PRINCIPAL_FUTURE_SECONDS,
            "csrfTokenBytes": CSRF_TOKEN_BYTES,
            "idempotencyKeyBytes": 16,
            "idempotencyTtlSeconds": BROWSER_IDEMPOTENCY_TTL_SECONDS,
            "idempotencyResponseProtection": "aes256gcm_authenticated_encryption",
            "idempotencyAtomicity": "same_sqlite_transaction_local_reference",
            "requestCarriesAuthenticationMaterial": False,
            "requestAcceptsOwnerId": False,
            "rateLimiterBoundary": "injected_owner_scoped_fail_closed",
            "localRateLimiterReference": "in_memory_account_fixed_window",
            "productionAuthority": dict(PRODUCTION_AUTHORITY),
        }

    def _preflight(self, request: BrowserRequest) -> BrowserRequest:
        if type(request) is not BrowserRequest:
            raise _BrowserRefusal(400, "invalid_request")
        if type(request.method) is not str or request.method not in {"POST", "DELETE"}:
            raise _BrowserRefusal(404, "not_found")
        if (
            type(request.path) is not str
            or not request.path.startswith("/v1/browser/")
            or len(request.path) > 512
            or "?" in request.path
            or "#" in request.path
            or "//" in request.path
        ):
            raise _BrowserRefusal(404, "not_found")
        if type(request.body) is not bytes or len(request.body) > MAX_BROWSER_BODY_BYTES:
            raise _BrowserRefusal(413, "request_too_large")
        if type(request.origin) is not str or request.origin != self.allowed_origin:
            raise _BrowserRefusal(403, "forbidden")
        if not _valid_csrf_pair(request.csrf_cookie, request.csrf_header):
            raise _BrowserRefusal(403, "forbidden")
        try:
            validate_idempotency_key(request.idempotency_key)
        except (HostedStoreError, TypeError, ValueError):
            raise _BrowserRefusal(400, "invalid_request") from None
        if request.method == "POST" and request.content_type != "application/json":
            raise _BrowserRefusal(415, "unsupported_media_type")
        if request.method == "DELETE" and request.content_type not in (None, "application/json"):
            raise _BrowserRefusal(415, "unsupported_media_type")
        return request

    def _route(
        self,
        request: BrowserRequest,
    ) -> tuple[str, dict[str, str], dict[str, object]]:
        if request.method == "POST" and request.path == "/v1/browser/pairings":
            return "create_pairing", {}, _decode_exact_object(request.body, set(), "create pairing")
        match = _PAIRING_CONFIRM_RE.fullmatch(request.path)
        if request.method == "POST" and match is not None:
            challenge_id = _challenge_id(match.group(1))
            payload = _decode_exact_object(request.body, {"approved"}, "confirm pairing")
            if type(payload["approved"]) is not bool:
                raise _BrowserRefusal(400, "invalid_request")
            return "confirm_pairing", {"challenge_id": challenge_id}, payload
        match = _RUNNER_REVOKE_RE.fullmatch(request.path)
        if request.method == "POST" and match is not None:
            runner_id = _runner_id(match.group(1))
            return "revoke_runner", {"runner_id": runner_id}, _decode_exact_object(request.body, set(), "revoke runner")
        match = _RUNNER_DELETE_RE.fullmatch(request.path)
        if request.method == "DELETE" and match is not None:
            runner_id = _runner_id(match.group(1))
            _require_empty_delete(request.body)
            return "delete_runner", {"runner_id": runner_id}, {}
        match = _FIXTURE_JOB_RE.fullmatch(request.path)
        if request.method == "POST" and match is not None:
            runner_id = _runner_id(match.group(1))
            payload = _decode_seed_object(request.body)
            return "create_fixture_job", {"runner_id": runner_id}, payload
        if request.method == "DELETE" and request.path == "/v1/browser/account":
            _require_empty_delete(request.body)
            return "delete_owner", {}, {}
        raise _BrowserRefusal(404, "not_found")

    def _invoke(
        self,
        operation: str,
        *,
        owner_id: str,
        parameters: Mapping[str, str],
        payload: Mapping[str, object],
        now: dt.datetime,
    ) -> HandlerResponse:
        if operation == "create_pairing":
            return self.control_plane.create_pairing(owner_id, now=now)
        if operation == "confirm_pairing":
            return self.control_plane.confirm_pairing(
                owner_id,
                parameters["challenge_id"],
                approved=bool(payload["approved"]),
                now=now,
            )
        if operation == "revoke_runner":
            return self.control_plane.revoke_runner(owner_id, parameters["runner_id"], now=now)
        if operation == "delete_runner":
            return self.control_plane.delete_runner(owner_id, parameters["runner_id"])
        if operation == "create_fixture_job":
            seed = payload.get("seed")
            return self.control_plane.create_fixture_job(
                owner_id,
                parameters["runner_id"],
                seed=seed if type(seed) is str else None,
                now=now,
            )
        if operation == "delete_owner":
            return self.control_plane.delete_owner(owner_id)
        raise RuntimeError("unsupported browser operation")

    def _invoke_and_seal(
        self,
        operation: str,
        *,
        owner_id: str,
        idempotency_key: str,
        request_sha256: str,
        parameters: Mapping[str, str],
        payload: Mapping[str, object],
        now: dt.datetime,
    ) -> tuple[int, bytes]:
        response = self._invoke(
            operation,
            owner_id=owner_id,
            parameters=parameters,
            payload=payload,
            now=now,
        )
        if type(response) is not HandlerResponse or not 200 <= response.status_code <= 299:
            raise HostedStoreError(
                "invalid_idempotency_response",
                "browser operation returned an invalid success response",
            )
        encoded = _canonical_response_bytes(response.status_code, response.payload)
        nonce = os.urandom(IDEMPOTENCY_NONCE_BYTES)
        aad = _idempotency_aad(
            owner_id,
            idempotency_key,
            operation,
            request_sha256,
            response.status_code,
        )
        return response.status_code, nonce + self._idempotency_aead.encrypt(nonce, encoded, aad)

    def _unseal_response(
        self,
        status_code: int,
        sealed: bytes,
        *,
        owner_id: str,
        idempotency_key: str,
        operation: str,
        request_sha256: str,
    ) -> HandlerResponse:
        if type(sealed) is not bytes or len(sealed) <= IDEMPOTENCY_NONCE_BYTES + 16:
            raise ValueError("sealed idempotency response is invalid")
        nonce = sealed[:IDEMPOTENCY_NONCE_BYTES]
        ciphertext = sealed[IDEMPOTENCY_NONCE_BYTES:]
        aad = _idempotency_aad(
            owner_id,
            idempotency_key,
            operation,
            request_sha256,
            status_code,
        )
        raw = self._idempotency_aead.decrypt(nonce, ciphertext, aad)
        value = json.loads(raw.decode("utf-8"))
        if (
            type(value) is not dict
            or set(value) != {"payload", "statusCode"}
            or type(value["statusCode"]) is not int
            or value["statusCode"] != status_code
            or type(value["payload"]) is not dict
            or _canonical_response_bytes(status_code, value["payload"]) != raw
        ):
            raise ValueError("sealed idempotency response is invalid")
        return HandlerResponse(status_code, value["payload"])

    @staticmethod
    def _store_error(
        error: HostedStoreError,
        *,
        headers: Mapping[str, str],
    ) -> BrowserGatewayResponse:
        if error.code in _NOT_FOUND_CODES:
            return _error_response(404, "not_found", headers=headers)
        if error.code == "idempotency_conflict":
            return _error_response(409, "idempotency_conflict", headers=headers)
        if error.code in {
            "idempotency_in_progress", "idempotency_corrupt",
            "invalid_idempotency_response",
        }:
            return _error_response(503, "idempotency_unavailable", headers=headers)
        if error.code in _CONFLICT_CODES:
            return _error_response(409, "conflict", headers=headers)
        if error.code.startswith("invalid_"):
            return _error_response(400, "invalid_request", headers=headers)
        return _error_response(409, "operation_refused", headers=headers)


@dataclasses.dataclass(frozen=True)
class _BrowserRefusal(Exception):
    status_code: int
    code: str


def _aware_utc(value: dt.datetime | None) -> dt.datetime:
    current = value or dt.datetime.now(dt.timezone.utc)
    if type(current) is not dt.datetime or current.tzinfo is None:
        raise ValueError("time must be timezone-aware")
    return current.astimezone(dt.timezone.utc)


def _canonical_https_origin(value: str, label: str) -> str:
    if type(value) is not str or not value or len(value) > 512:
        raise ValueError(f"{label} is invalid")
    try:
        value.encode("ascii")
    except UnicodeEncodeError as error:
        raise ValueError(f"{label} is invalid") from error
    try:
        parsed = urllib.parse.urlsplit(value)
        port = parsed.port
    except ValueError as error:
        raise ValueError(f"{label} is invalid") from error
    if (
        parsed.scheme != "https"
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
        or port is not None
    ):
        raise ValueError(f"{label} must be one canonical HTTPS origin")
    canonical = f"https://{parsed.hostname.lower()}"
    if value != canonical:
        raise ValueError(f"{label} must use one canonical spelling")
    return canonical


def _canonical_csrf(value: str) -> str:
    if type(value) is not str or _CSRF_RE.fullmatch(value) is None:
        raise ValueError("CSRF token is invalid")
    try:
        decoded = base64.b64decode(value + "=", altchars=b"-_", validate=True)
    except (TypeError, ValueError) as error:
        raise ValueError("CSRF token is invalid") from error
    canonical = base64.urlsafe_b64encode(decoded).decode("ascii").rstrip("=")
    if len(decoded) != CSRF_TOKEN_BYTES or canonical != value:
        raise ValueError("CSRF token is invalid")
    return value


def _valid_csrf_pair(cookie: str, header: str) -> bool:
    try:
        cookie = _canonical_csrf(cookie)
        header = _canonical_csrf(header)
    except ValueError:
        return False
    return hmac.compare_digest(cookie, header)


def _browser_request_digest(request: BrowserRequest, operation: str) -> str:
    material = (
        BROWSER_GATEWAY_SCHEMA.encode("ascii")
        + b"\x00request\x00"
        + operation.encode("ascii")
        + b"\x00"
        + request.method.encode("ascii")
        + b"\x00"
        + request.path.encode("ascii")
        + b"\x00"
        + request.body
    )
    return hashlib.sha256(material).hexdigest()


def _idempotency_aad(
    owner_id: str,
    idempotency_key: str,
    operation: str,
    request_sha256: str,
    status_code: int,
) -> bytes:
    return b"\x00".join((
        BROWSER_GATEWAY_SCHEMA.encode("ascii"),
        b"idempotency-response",
        owner_id.encode("ascii"),
        idempotency_key.encode("ascii"),
        operation.encode("ascii"),
        request_sha256.encode("ascii"),
        str(status_code).encode("ascii"),
    ))


def _canonical_response_bytes(status_code: int, payload: Mapping[str, object]) -> bytes:
    if type(status_code) is not int or not 200 <= status_code <= 299 or type(payload) is not dict:
        raise ValueError("browser response is invalid")
    try:
        return json.dumps(
            {"payload": payload, "statusCode": status_code},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError) as error:
        raise ValueError("browser response is invalid") from error


def _decode_exact_object(body: bytes, expected: set[str], label: str) -> dict[str, object]:
    if type(body) is not bytes or not body or len(body) > MAX_BROWSER_BODY_BYTES:
        raise _BrowserRefusal(400, "invalid_request")

    def reject_float(_value: str):
        raise _BrowserRefusal(400, "invalid_request")

    def reject_constant(_value: str):
        raise _BrowserRefusal(400, "invalid_request")

    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise _BrowserRefusal(400, "invalid_request")
            result[key] = value
        return result

    try:
        value = json.loads(
            body.decode("utf-8"),
            parse_float=reject_float,
            parse_constant=reject_constant,
            object_pairs_hook=reject_duplicates,
        )
    except _BrowserRefusal:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError, RecursionError):
        raise _BrowserRefusal(400, "invalid_request") from None
    if type(value) is not dict or set(value) != expected:
        raise _BrowserRefusal(400, "invalid_request")
    return value


def _decode_seed_object(body: bytes) -> dict[str, object]:
    try:
        value = _decode_exact_object(body, set(), "fixture job")
        return value
    except _BrowserRefusal:
        value = _decode_exact_object(body, {"seed"}, "fixture job")
        if type(value["seed"]) is not str or _SEED_RE.fullmatch(value["seed"]) is None:
            raise _BrowserRefusal(400, "invalid_request")
        try:
            decoded = base64.b64decode(value["seed"] + "==", altchars=b"-_", validate=True)
        except (TypeError, ValueError):
            raise _BrowserRefusal(400, "invalid_request") from None
        if len(decoded) != 16 or base64.urlsafe_b64encode(decoded).decode("ascii").rstrip("=") != value["seed"]:
            raise _BrowserRefusal(400, "invalid_request")
        return value


def _challenge_id(value: str) -> str:
    try:
        return validate_challenge_id(value)
    except (RunnerClientError, TypeError, ValueError):
        raise _BrowserRefusal(404, "not_found") from None


def _runner_id(value: str) -> str:
    try:
        return validate_runner_id(value)
    except (RunnerClientError, TypeError, ValueError):
        raise _BrowserRefusal(404, "not_found") from None


def _require_empty_delete(body: bytes) -> None:
    if body != b"":
        raise _BrowserRefusal(400, "invalid_request")


def _error_response(
    status_code: int,
    code: str,
    *,
    headers: Mapping[str, str] | None = None,
) -> BrowserGatewayResponse:
    return BrowserGatewayResponse(
        status_code,
        {"schemaVersion": 1, "status": "error", "error": {"code": code}},
        dict(headers or {}),
    )
