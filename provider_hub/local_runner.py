"""Customer-local AgentWars Ed25519 runner pairing and request signing.

This module is additive to the historical BuildWars HMAC envelope contract in
``provider_hub.signing``.  It implements the account-approved local signing-key
wire protocol used by Nymrel without moving provider credentials, provider
sessions, or model output into Nymrel custody.

Pairing proves only that a high-entropy browser-created secret was claimed by
the holder of a local Ed25519 key and later approved by the signed-in account.
A signed request proves possession of that still-active key and integrity of
the exact request bytes.  Neither operation attests provider, subscription,
billing route, model, person, runtime, harness execution, or match execution.
"""

from __future__ import annotations

import base64
import datetime as _datetime
import hashlib
import hmac
import json
import os
import re
import ssl
import stat
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from provider_hub.catalog import PROVIDER_IDS, connection_mode_for


PAIRING_PROTOCOL = "agentwars.runner_pairing.v1"
REQUEST_PROTOCOL = "agentwars.runner_request.v1"
PRODUCTION_ORIGIN = "https://nymrel.com"
PAIRING_CLAIM_PATH = "/api/builderwars/runners/pairing/claim"
MAX_HTTP_BYTES = 65_536
MAX_BODY_BYTES = 65_536

_PAIRING_SECRET_RE = re.compile(
    r"^awp1_([A-Za-z0-9_-]{22})_([A-Za-z0-9_-]{32})$"
)
_CHALLENGE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{22}$")
_RUNNER_ID_RE = re.compile(r"^awr1_[A-Za-z0-9_-]{22}$")
_PUBLIC_KEY_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")
_FINGERPRINT_RE = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_SAFE_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+/-]{0,63}$")
_PATH_RE = re.compile(r"^/[A-Za-z0-9/_-]*$")
_NONCE_RE = re.compile(r"^[A-Za-z0-9_-]{22}$")
_SIGNATURE_RE = re.compile(r"^[A-Za-z0-9_-]{86}$")
_CANONICAL_INSTANT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$"
)


class RunnerClientError(ValueError):
    """A local contract, state, signing, or transport boundary was refused."""


class RunnerHttpError(RunnerClientError):
    """A bounded HTTP operation failed without reflecting a remote body."""

    def __init__(self, message: str, *, status: int | None = None):
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class PublicKeyMaterial:
    public_key: str
    fingerprint: str


@dataclass(frozen=True)
class ClaimResult:
    status: str
    challenge_id: str
    state: str
    fingerprint: str


@dataclass(frozen=True)
class SignedRunnerRequest:
    method: str
    path: str
    body: bytes
    body_sha256: str
    timestamp: str
    nonce: str
    runner_id: str
    signature: str
    canonical: str

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "agentwars-protocol": REQUEST_PROTOCOL,
            "agentwars-runner-id": self.runner_id,
            "agentwars-timestamp": self.timestamp,
            "agentwars-nonce": self.nonce,
            "agentwars-signature": self.signature,
        }


def base64url_no_pad(value: bytes) -> str:
    if not isinstance(value, bytes):
        raise RunnerClientError("base64url input must be bytes")
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def parse_pairing_secret(value: str) -> tuple[str, str]:
    if not isinstance(value, str):
        raise RunnerClientError("pairing secret must be entered as text")
    match = _PAIRING_SECRET_RE.fullmatch(value)
    if match is None:
        raise RunnerClientError("pairing secret has an invalid shape")
    return match.group(1), match.group(2)


def validate_challenge_id(value: str) -> str:
    if not isinstance(value, str) or _CHALLENGE_ID_RE.fullmatch(value) is None:
        raise RunnerClientError("challenge id has an invalid shape")
    return value


def validate_runner_id(value: str) -> str:
    if not isinstance(value, str) or _RUNNER_ID_RE.fullmatch(value) is None:
        raise RunnerClientError("runner id has an invalid shape")
    return value


def validate_origin(value: str) -> str:
    """Return one canonical allowed origin.

    Public pairing is pinned to the production Nymrel origin.  Test servers may
    use literal IPv4/IPv6 loopback origins; ``localhost`` is intentionally not
    accepted because name resolution is mutable.  Userinfo, path, query,
    fragment, and implicit cross-origin redirects are refused.
    """
    if not isinstance(value, str) or not value or len(value) > 512:
        raise RunnerClientError("runner endpoint origin is invalid")
    try:
        parsed = urllib.parse.urlsplit(value)
        port = parsed.port
    except ValueError as error:
        raise RunnerClientError("runner endpoint origin is invalid") from error
    if (
        parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/")
    ):
        raise RunnerClientError("runner endpoint must be an origin without credentials, path, query, or fragment")
    host = parsed.hostname
    scheme = parsed.scheme.lower()
    if host is None:
        raise RunnerClientError("runner endpoint origin needs a host")
    host = host.lower()
    if scheme == "https" and host == "nymrel.com" and port is None:
        if value != PRODUCTION_ORIGIN:
            raise RunnerClientError("production runner endpoint must use the exact canonical origin")
        return PRODUCTION_ORIGIN
    if host not in ("127.0.0.1", "::1") or scheme not in ("http", "https"):
        raise RunnerClientError(
            "runner endpoint is restricted to https://nymrel.com or a literal loopback test origin"
        )
    if port is not None and not 1 <= port <= 65_535:
        raise RunnerClientError("runner endpoint port is invalid")
    rendered_host = f"[{host}]" if host == "::1" else host
    rendered_port = "" if port is None else f":{port}"
    canonical = f"{scheme}://{rendered_host}{rendered_port}"
    if value != canonical:
        raise RunnerClientError("loopback runner endpoint must use one exact canonical spelling")
    return canonical


def validate_request_path(value: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) > 512
        or _PATH_RE.fullmatch(value) is None
        or "//" in value
    ):
        raise RunnerClientError("signed request path must be one exact pathname without query syntax")
    return value


def validate_display_label(value: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 80 or not value[0].isalnum():
        raise RunnerClientError("runner label must start with a letter or number and be at most 80 characters")
    allowed = " ._()/#&+:-"
    if any(not (character.isalnum() or character in allowed) for character in value):
        raise RunnerClientError("runner label contains an unsupported character")
    return value


def validate_harness_id(value: str) -> str:
    if not isinstance(value, str) or _SAFE_ID_RE.fullmatch(value) is None:
        raise RunnerClientError("harness id must be a safe 1-64 character identifier")
    return value


def validate_harness_version(value: str) -> str:
    if not isinstance(value, str) or _SAFE_VERSION_RE.fullmatch(value) is None:
        raise RunnerClientError("harness version must be a safe 1-64 character version")
    return value


def validate_fingerprint(value: str) -> str:
    if not isinstance(value, str) or _FINGERPRINT_RE.fullmatch(value) is None:
        raise RunnerClientError("runner fingerprint must be 64 lowercase hexadecimal characters")
    return value


def public_key_material(private_key: Ed25519PrivateKey) -> PublicKeyMaterial:
    if not isinstance(private_key, Ed25519PrivateKey):
        raise RunnerClientError("runner private key must be Ed25519")
    raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    public_key = base64url_no_pad(raw)
    if _PUBLIC_KEY_RE.fullmatch(public_key) is None:
        raise RunnerClientError("derived Ed25519 public key is not canonical")
    return PublicKeyMaterial(
        public_key=public_key,
        fingerprint=hashlib.sha256(raw).hexdigest(),
    )


def grouped_fingerprint(value: str) -> str:
    value = validate_fingerprint(value)
    return " ".join(value[index:index + 4] for index in range(0, 64, 4))


def digest_harness_file(path: str, *, maximum_bytes: int = 16 * 1024 * 1024) -> str:
    """Hash one regular non-symlink harness file with a bounded, stable read."""
    if isinstance(maximum_bytes, bool) or not isinstance(maximum_bytes, int) or maximum_bytes <= 0:
        raise RunnerClientError("harness size limit must be a positive integer")
    absolute = os.path.abspath(os.fspath(path))
    try:
        before = os.lstat(absolute)
    except OSError as error:
        raise RunnerClientError("harness file could not be inspected") from error
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise RunnerClientError("harness path must be one regular non-symlink file")
    if before.st_size > maximum_bytes:
        raise RunnerClientError("harness file exceeds the local pairing size limit")
    digest = hashlib.sha256()
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(absolute, flags)
    except OSError as error:
        raise RunnerClientError("harness file could not be opened safely") from error
    count = 0
    try:
        opened = os.fstat(descriptor)
        if before.st_dev != opened.st_dev or before.st_ino != opened.st_ino:
            raise RunnerClientError("harness file changed while it was opened")
        while True:
            block = os.read(descriptor, 65_536)
            if not block:
                break
            count += len(block)
            if count > maximum_bytes:
                raise RunnerClientError("harness file exceeds the local pairing size limit")
            digest.update(block)
    finally:
        os.close(descriptor)
    try:
        after = os.lstat(absolute)
    except OSError as error:
        raise RunnerClientError("harness file disappeared during hashing") from error
    if (
        after.st_dev != before.st_dev
        or after.st_ino != before.st_ino
        or after.st_size != before.st_size
        or after.st_mtime_ns != before.st_mtime_ns
    ):
        raise RunnerClientError("harness file changed during hashing")
    return digest.hexdigest()


def claim_payload(
    *,
    pairing_secret: str,
    provider_id: str,
    display_label: str,
    harness_id: str,
    harness_version: str,
    harness_digest: str,
    public_key: str,
) -> dict[str, object]:
    parse_pairing_secret(pairing_secret)
    if provider_id not in PROVIDER_IDS:
        raise RunnerClientError("provider id is not in the closed AgentWars catalog")
    if not isinstance(harness_digest, str) or _FINGERPRINT_RE.fullmatch(harness_digest) is None:
        raise RunnerClientError("harness digest must be 64 lowercase hexadecimal characters")
    if not isinstance(public_key, str) or _PUBLIC_KEY_RE.fullmatch(public_key) is None:
        raise RunnerClientError("Ed25519 public key must be canonical unpadded base64url")
    return {
        "pairingSecret": pairing_secret,
        "providerId": provider_id,
        "connectionMode": connection_mode_for(provider_id),
        "displayLabel": validate_display_label(display_label),
        "harnessId": validate_harness_id(harness_id),
        "harnessVersion": validate_harness_version(harness_version),
        "harnessDigest": harness_digest,
        "publicKey": public_key,
    }


def validate_claim_response(value: object, *, challenge_id: str, fingerprint: str) -> ClaimResult:
    expected = {
        "schemaVersion",
        "protocolVersion",
        "status",
        "challengeId",
        "state",
        "fingerprint",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise RunnerClientError("pairing claim returned an invalid response contract")
    if type(value["schemaVersion"]) is not int or value["schemaVersion"] != 1:
        raise RunnerClientError("pairing claim returned an unsupported schema version")
    if value["protocolVersion"] != PAIRING_PROTOCOL:
        raise RunnerClientError("pairing claim returned an unsupported protocol")
    if value["status"] not in ("claimed", "duplicate"):
        raise RunnerClientError("pairing claim returned an invalid status")
    if value["state"] != "pending_confirmation":
        raise RunnerClientError("pairing claim did not enter pending confirmation")
    expected_challenge = validate_challenge_id(challenge_id)
    if not isinstance(value["challengeId"], str) or not hmac.compare_digest(
        value["challengeId"], expected_challenge
    ):
        raise RunnerClientError("pairing claim response changed the challenge id")
    expected_fingerprint = validate_fingerprint(fingerprint)
    if not isinstance(value["fingerprint"], str) or not hmac.compare_digest(
        value["fingerprint"], expected_fingerprint
    ):
        raise RunnerClientError("pairing claim response fingerprint does not match the local key")
    return ClaimResult(
        status=value["status"],
        challenge_id=value["challengeId"],
        state=value["state"],
        fingerprint=value["fingerprint"],
    )


def canonical_instant(now: _datetime.datetime | None = None) -> str:
    current = now or _datetime.datetime.now(_datetime.timezone.utc)
    if not isinstance(current, _datetime.datetime) or current.tzinfo is None:
        raise RunnerClientError("runner request time must be timezone-aware")
    current = current.astimezone(_datetime.timezone.utc)
    current = current.replace(microsecond=(current.microsecond // 1000) * 1000)
    rendered = current.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    if _CANONICAL_INSTANT_RE.fullmatch(rendered) is None:
        raise RunnerClientError("runner request timestamp is not canonical")
    return rendered


def validate_canonical_instant(value: str) -> str:
    if not isinstance(value, str) or _CANONICAL_INSTANT_RE.fullmatch(value) is None:
        raise RunnerClientError("runner request timestamp is invalid")
    try:
        parsed = _datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise RunnerClientError("runner request timestamp is invalid") from error
    rendered = parsed.astimezone(_datetime.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    if rendered != value:
        raise RunnerClientError("runner request timestamp is not canonical")
    return value


def validate_nonce(value: str) -> str:
    if not isinstance(value, str) or _NONCE_RE.fullmatch(value) is None:
        raise RunnerClientError("signed request nonce is invalid")
    try:
        decoded = base64.urlsafe_b64decode(value + "==")
    except (ValueError, base64.binascii.Error) as error:
        raise RunnerClientError("signed request nonce is invalid") from error
    if len(decoded) != 16 or base64url_no_pad(decoded) != value:
        raise RunnerClientError("signed request nonce is not canonical")
    return value


def canonical_runner_request(
    *,
    method: str,
    path: str,
    body_sha256: str,
    timestamp: str,
    nonce: str,
    runner_id: str,
) -> str:
    if method not in ("POST", "PUT", "PATCH", "DELETE"):
        raise RunnerClientError("signed request method is unsupported")
    path = validate_request_path(path)
    if _FINGERPRINT_RE.fullmatch(body_sha256 or "") is None:
        raise RunnerClientError("signed request body digest is invalid")
    timestamp = validate_canonical_instant(timestamp)
    nonce = validate_nonce(nonce)
    runner_id = validate_runner_id(runner_id)
    return "\n".join(
        [
            REQUEST_PROTOCOL,
            f"method:{method}",
            f"path:{path}",
            f"body-sha256:{body_sha256}",
            f"timestamp:{timestamp}",
            f"nonce:{nonce}",
            f"runner-id:{runner_id}",
            "",
        ]
    )


def validate_json_body(body: bytes, *, maximum_bytes: int = MAX_BODY_BYTES) -> bytes:
    if not isinstance(body, bytes) or not body or len(body) > maximum_bytes:
        raise RunnerClientError("signed request body must be 1-65536 bytes")
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RunnerClientError("signed request body must be valid UTF-8 JSON") from error

    def reject_float(_value: str):
        raise RunnerClientError("signed request JSON must not contain floating-point values")

    def reject_constant(_value: str):
        raise RunnerClientError("signed request JSON must not contain non-finite values")

    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise RunnerClientError("signed request JSON contains a duplicate object key")
            result[key] = value
        return result

    try:
        value = json.loads(
            text,
            parse_float=reject_float,
            parse_constant=reject_constant,
            object_pairs_hook=reject_duplicates,
        )
    except RunnerClientError:
        raise
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise RunnerClientError("signed request body must be valid JSON") from error
    if not isinstance(value, dict):
        raise RunnerClientError("signed request JSON body must be an object")
    return body


def sign_runner_request(
    private_key: Ed25519PrivateKey,
    *,
    method: str,
    path: str,
    body: bytes,
    runner_id: str,
    timestamp: str | None = None,
    nonce_bytes: bytes | None = None,
) -> SignedRunnerRequest:
    if not isinstance(private_key, Ed25519PrivateKey):
        raise RunnerClientError("runner private key must be Ed25519")
    body = validate_json_body(body)
    method = method.upper() if isinstance(method, str) else method
    path = validate_request_path(path)
    runner_id = validate_runner_id(runner_id)
    stamp = canonical_instant() if timestamp is None else timestamp
    nonce_raw = os.urandom(16) if nonce_bytes is None else nonce_bytes
    if not isinstance(nonce_raw, bytes) or len(nonce_raw) != 16:
        raise RunnerClientError("runner request nonce source must provide exactly 16 bytes")
    nonce = base64url_no_pad(nonce_raw)
    body_sha256 = hashlib.sha256(body).hexdigest()
    canonical = canonical_runner_request(
        method=method,
        path=path,
        body_sha256=body_sha256,
        timestamp=stamp,
        nonce=nonce,
        runner_id=runner_id,
    )
    signature = base64url_no_pad(private_key.sign(canonical.encode("utf-8")))
    if _SIGNATURE_RE.fullmatch(signature) is None:
        raise RunnerClientError("runner request signature is not canonical")
    return SignedRunnerRequest(
        method=method,
        path=path,
        body=body,
        body_sha256=body_sha256,
        timestamp=stamp,
        nonce=nonce,
        runner_id=runner_id,
        signature=signature,
        canonical=canonical,
    )


class _RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: N802
        raise RunnerHttpError("runner endpoint redirect refused", status=code)


def _direct_opener():
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    return urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPSHandler(context=context),
        _RejectRedirects(),
    )


def _request_json(
    *,
    origin: str,
    path: str,
    method: str,
    body: bytes,
    headers: dict[str, str],
    timeout_seconds: int = 15,
    opener=None,
) -> tuple[int, dict[str, object], bytes]:
    origin = validate_origin(origin)
    path = validate_request_path(path)
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int) or not 1 <= timeout_seconds <= 60:
        raise RunnerClientError("runner HTTP timeout must be an integer from 1 to 60 seconds")
    request = urllib.request.Request(
        origin + path,
        data=body,
        headers=headers,
        method=method,
    )
    client = opener or _direct_opener()
    try:
        response = client.open(request, timeout=timeout_seconds)
    except RunnerHttpError:
        raise
    except urllib.error.HTTPError as error:
        try:
            error.read(MAX_HTTP_BYTES + 1)
        except Exception:
            pass
        raise RunnerHttpError(
            f"runner endpoint rejected the request with HTTP {error.code}",
            status=error.code,
        ) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise RunnerHttpError("runner endpoint could not be reached") from None
    with response:
        status = getattr(response, "status", response.getcode())
        if not isinstance(status, int) or not 200 <= status <= 299:
            raise RunnerHttpError("runner endpoint returned a non-success status", status=status)
        final_url = response.geturl()
        if final_url != origin + path:
            raise RunnerHttpError("runner endpoint changed the request URL")
        content_type = response.headers.get_content_type().lower()
        if content_type != "application/json":
            raise RunnerHttpError("runner endpoint returned a non-JSON response", status=status)
        declared = response.headers.get("Content-Length")
        if declared is not None:
            try:
                length = int(declared)
            except ValueError:
                raise RunnerHttpError("runner endpoint returned an invalid content length", status=status) from None
            if length < 0 or length > MAX_HTTP_BYTES:
                raise RunnerHttpError("runner endpoint response is too large", status=status)
        raw = response.read(MAX_HTTP_BYTES + 1)
        if len(raw) > MAX_HTTP_BYTES:
            raise RunnerHttpError("runner endpoint response is too large", status=status)
    try:
        decoded = raw.decode("utf-8")
        payload = json.loads(decoded, object_pairs_hook=_reject_duplicate_response_keys)
    except RunnerClientError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise RunnerHttpError("runner endpoint returned invalid JSON", status=status) from None
    if not isinstance(payload, dict):
        raise RunnerHttpError("runner endpoint returned a non-object JSON response", status=status)
    return status, payload, raw


def _reject_duplicate_response_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RunnerHttpError("runner endpoint returned duplicate JSON keys")
        result[key] = value
    return result


def claim_runner(
    *,
    origin: str,
    pairing_secret: str,
    provider_id: str,
    display_label: str,
    harness_id: str,
    harness_version: str,
    harness_digest: str,
    public_key: str,
    fingerprint: str,
    timeout_seconds: int = 15,
    opener=None,
) -> ClaimResult:
    challenge_id, _random_code = parse_pairing_secret(pairing_secret)
    payload = claim_payload(
        pairing_secret=pairing_secret,
        provider_id=provider_id,
        display_label=display_label,
        harness_id=harness_id,
        harness_version=harness_version,
        harness_digest=harness_digest,
        public_key=public_key,
    )
    body = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    http_status, response, _raw = _request_json(
        origin=origin,
        path=PAIRING_CLAIM_PATH,
        method="POST",
        body=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        timeout_seconds=timeout_seconds,
        opener=opener,
    )
    result = validate_claim_response(
        response,
        challenge_id=challenge_id,
        fingerprint=fingerprint,
    )
    if (http_status, result.status) not in ((202, "claimed"), (200, "duplicate")):
        raise RunnerClientError("pairing claim HTTP status contradicts its response state")
    return result


def send_signed_request(
    *,
    origin: str,
    signed: SignedRunnerRequest,
    timeout_seconds: int = 15,
    opener=None,
) -> tuple[int, dict[str, object], bytes]:
    if not isinstance(signed, SignedRunnerRequest):
        raise RunnerClientError("signed runner request object is invalid")
    return _request_json(
        origin=origin,
        path=signed.path,
        method=signed.method,
        body=signed.body,
        headers={**signed.headers, "Accept": "application/json"},
        timeout_seconds=timeout_seconds,
        opener=opener,
    )
