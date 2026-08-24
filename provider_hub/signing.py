"""HMAC-SHA256 runner pairing signatures for BuildWars v1 envelopes.

Pairing-key truth: a BuildWars pairing secret is a random 256-bit value that is
distinct from every provider credential. It is NOT confined to one machine by
design — it must be provisioned over an authenticated pairing channel to BOTH
the BuildWars verifier side and the customer runner. What keeps it out of
serialized envelopes is that only its 128-bit public fingerprint
(``bpk_<32 hex>``) is ever signed or transmitted; raw provider credentials and the raw pairing
secret never enter envelope bytes.

Signatures bind the canonical JSON bytes of an envelope plus its schema kind,
so a signature made for one envelope kind cannot be replayed onto another
(wrong-kind rejection), and any altered field fails verification. Verification
is constant-time (``hmac.compare_digest``) and additionally rejects stale,
future-dated, wrong-user, wrong-runner, unknown-key, and malformed-signature
envelopes, bool/float/coerced signing timestamps, and invalid max-age values.

Replay: HMAC possession alone cannot distinguish the SECOND presentation of an
envelope that is still inside its freshness window. Callers that need
single-use semantics pass a ``replay_guard``; after a valid MAC is confirmed,
the guard registers the signature and rejects its re-presentation.
``InMemoryReplayGuard`` is a thread-safe bounded REFERENCE implementation for
local use only. Production deployments require durable, atomic,
single-use/replay storage (for example one-time job ids committed server-side
before first acceptance); an in-memory set does not survive restarts or scale.
"""

import collections
import hashlib
import hmac
import threading
import time

from provider_hub.ids import new_key_id
from provider_hub.schemas import SchemaError, encode_canonical, validate_envelope
from provider_hub.secrets import SecretValue

_DOMAIN_SEPARATOR = b"buildwars.runner-pairing.v1\x00"
DEFAULT_MAX_AGE_S = 600
FUTURE_ALLOWANCE_S = 60
_SIGNABLE_SCHEMAS = frozenset(
    {
        "buildwars.runner_pairing.v1",
        "buildwars.runner_capabilities.v1",
        "buildwars.result_attestation.v1",
    }
)


class PairingKey:
    """A BuildWars-only pairing key held by both sides of the pairing channel."""

    __slots__ = ("_secret", "key_id")

    def __init__(self, secret_bytes):
        if not isinstance(secret_bytes, bytes):
            raise TypeError("pairing key secret must be bytes")
        if len(secret_bytes) != 32:
            raise ValueError("pairing key secret must be exactly 32 bytes")
        object.__setattr__(self, "_secret", SecretValue(secret_bytes))
        object.__setattr__(
            self, "key_id", new_key_id(hashlib.sha256(secret_bytes).hexdigest()[:32])
        )

    def __setattr__(self, name, value):
        raise AttributeError("PairingKey is immutable")

    def __delattr__(self, name):
        raise AttributeError("PairingKey is immutable")

    @property
    def secret(self):
        return self._secret


class SigningError(ValueError):
    """Signature generation/verification failure with a precise reason."""


def generate_pairing_key():
    """Fresh random pairing key. Distinct from every provider credential."""
    import secrets as _secrets

    return PairingKey(_secrets.token_bytes(32))


class InMemoryReplayGuard:
    """Thread-safe bounded in-memory replay guard — reference ONLY.

    ``check_and_register(fingerprint)`` returns True on first presentation and
    False afterwards. Oldest fingerprints are evicted once ``capacity`` is
    exceeded, so this guard bounds memory but cannot provide long-horizon
    single-use guarantees. Production needs durable atomic replay/single-use
    storage; this class documents the interface such storage must expose.
    """

    def __init__(self, capacity=65536):
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        self._capacity = capacity
        self._seen = collections.OrderedDict()
        self._lock = threading.Lock()

    def check_and_register(self, fingerprint):
        if not isinstance(fingerprint, str) or not 1 <= len(fingerprint) <= 256:
            raise ValueError("fingerprint must be a non-empty string of at most 256 chars")
        with self._lock:
            if fingerprint in self._seen:
                return False
            self._seen[fingerprint] = None
            while len(self._seen) > self._capacity:
                self._seen.popitem(last=False)
            return True


def _strict_timestamp(value, what):
    """Accept exact integers only; bool and float spellings reject."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise SigningError(f"{what} must be an integer timestamp")
    return value


def sign_payload(payload, key, *, signed_at=None):
    """Return a signed copy of ``payload`` with a detached signature block.

    ``payload`` must carry a ``schema`` discriminator and must not already
    contain ``signed_at`` or ``signature``. ``signed_at`` accepts exact
    integers only — floats and bools are rejected rather than coerced.
    """
    if not isinstance(payload, dict):
        raise SigningError("payload must be a dict")
    if not isinstance(key, PairingKey):
        raise SigningError("key must be a PairingKey")
    schema = payload.get("schema")
    if schema not in _SIGNABLE_SCHEMAS:
        raise SigningError("payload needs a supported signable schema discriminator")
    if "signature" in payload or "signed_at" in payload:
        raise SigningError("payload already carries signature material")
    stamp = (
        int(time.time()) if signed_at is None else _strict_timestamp(signed_at, "signed_at")
    )
    body = dict(payload)
    body["signed_at"] = stamp
    try:
        body = validate_envelope(body)
    except SchemaError:
        raise SigningError("payload does not satisfy its signable envelope schema") from None
    mac = hmac.new(
        key.secret.reveal(),
        _DOMAIN_SEPARATOR + encode_canonical(body),
        hashlib.sha256,
    ).hexdigest()
    body["signature"] = {"kind": schema, "key_id": key.key_id, "value": mac}
    return body


def verify_signature(
    envelope,
    key_lookup,
    *,
    now=None,
    max_age_s=DEFAULT_MAX_AGE_S,
    expect_schema=None,
    expect_identity_id=None,
    expect_runner_id=None,
    replay_guard=None,
):
    """Verify a signed envelope and return the unsigned payload copy.

    Fails closed on: missing/extra signature fields, wrong signature kind,
    unknown key id, malformed hex, any altered byte of the covered payload,
    staleness beyond ``max_age_s``, future timestamps beyond the allowance,
    identity/runner binding mismatches when expected values are given,
    non-integer timestamps, invalid max-age values, and — when a
    ``replay_guard`` is supplied — a second presentation of the same valid
    signature.
    """
    if not isinstance(envelope, dict):
        raise SigningError("envelope must be a dict")
    if isinstance(max_age_s, bool) or not isinstance(max_age_s, int) or max_age_s <= 0:
        raise SigningError("max_age_s must be a positive integer number of seconds")

    signature = envelope.get("signature")
    if not isinstance(signature, dict):
        raise SigningError("missing signature block")
    if set(signature) != {"kind", "key_id", "value"}:
        raise SigningError(
            f"signature block must have exactly kind/key_id/value, got {sorted(signature)}"
        )
    schema = envelope.get("schema")
    if not isinstance(schema, str) or not schema:
        raise SigningError("envelope needs a schema discriminator")
    if schema not in _SIGNABLE_SCHEMAS:
        raise SigningError("envelope schema is not signable")
    if signature["kind"] != schema:
        raise SigningError(
            f"wrong-kind signature {signature['kind']!r} on {schema!r} envelope"
        )
    if expect_schema is not None and schema != expect_schema:
        raise SigningError(f"expected {expect_schema!r} envelope, got {schema!r}")

    key_id = signature["key_id"]
    if not isinstance(key_id, str):
        raise SigningError("signature key_id must be a string")
    key = key_lookup(key_id)
    if key is None:
        raise SigningError(f"unknown pairing key id {key_id!r}")
    if not isinstance(key, PairingKey):
        raise SigningError("key_lookup returned something that is not a PairingKey")

    sig_hex = signature["value"]
    if (
        not isinstance(sig_hex, str)
        or len(sig_hex) != 64
        or any(ch not in "0123456789abcdef" for ch in sig_hex)
    ):
        raise SigningError("malformed signature value")

    body = {k: v for k, v in envelope.items() if k != "signature"}
    signed_at = body.get("signed_at")
    _strict_timestamp(signed_at, "signed_at")

    now_i = int(time.time()) if now is None else _strict_timestamp(now, "now")
    if signed_at > now_i + FUTURE_ALLOWANCE_S:
        raise SigningError("signature timestamp is too far in the future")
    if signed_at < now_i - int(max_age_s):
        raise SigningError(
            f"stale signature: signed_at {signed_at} is older than {int(max_age_s)}s"
        )

    expected_mac = hmac.new(
        key.secret.reveal(),
        _DOMAIN_SEPARATOR + encode_canonical(body),
        hashlib.sha256,
    ).digest()
    actual_mac = bytes.fromhex(sig_hex)
    # Constant-time comparison; length equality is checked implicitly because
    # both are SHA-256 digests.
    if not hmac.compare_digest(expected_mac, actual_mac):
        raise SigningError("signature does not cover this payload (altered or foreign)")

    # A valid MAC proves possession and byte integrity, not schema validity.
    # Validate only after authentication so a malformed but correctly signed
    # body cannot cross the protocol boundary.
    try:
        validated = validate_envelope(body)
    except SchemaError:
        raise SigningError("signed payload does not satisfy its envelope schema") from None

    if expect_identity_id is not None:
        if not isinstance(expect_identity_id, str):
            raise SigningError("expected identity id must be a string")
        presented = validated.get("identity_id")
        if not isinstance(presented, str) or not hmac.compare_digest(
            presented.encode("utf-8"), expect_identity_id.encode("utf-8")
        ):
            raise SigningError("wrong-user envelope: identity_id mismatch")
    if expect_runner_id is not None:
        if not isinstance(expect_runner_id, str):
            raise SigningError("expected runner id must be a string")
        presented = validated.get("runner_id")
        if not isinstance(presented, str) or not hmac.compare_digest(
            presented.encode("utf-8"), expect_runner_id.encode("utf-8")
        ):
            raise SigningError("wrong-runner envelope: runner_id mismatch")

    # Register only after the MAC AND endpoint-specific identity/runner binding
    # pass. A valid envelope presented to the wrong endpoint must not burn its
    # replay slot before its intended verifier sees it.
    if replay_guard is not None:
        if not hasattr(replay_guard, "check_and_register"):
            raise SigningError("replay_guard must implement check_and_register")
        fingerprint = f"{key.key_id}:{sig_hex}"
        if not replay_guard.check_and_register(fingerprint):
            raise SigningError("replay rejected: this signature was already presented")

    return validated
