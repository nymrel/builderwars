"""Canonical AgentBattles Agent Passport verification.

This module lives inside ``arena`` deliberately: every byte is covered by the
referee engine digest and embedded in the matching standalone verifier
snapshot. It has no dependency on an external identity package.

``cryptography`` is imported only when a signed passport is created or
verified. Unsigned legacy replay therefore remains stdlib-only. A signed
transcript without that optional dependency fails closed; it never falls back
to legacy identity.
"""

import base64
import binascii
import hashlib
import json
import re
import unicodedata
from types import MappingProxyType

from .canonical import canonical_bytes

PASSPORT_SCHEMA = "agentbattles.agent-version.v1"
AGENT_ID_DOMAIN = b"agentbattles.agent-id.v1\0"
VERSION_DOMAIN = b"agentbattles.agent-version.v1\0"

RAW_PUBLIC_KEY_BYTES = 32
SIGNATURE_BYTES = 64
DISPLAY_NAME_MAX = 64
VERSION_LABEL_MAX = 80
CLAIMED_MODEL_MAX = 120

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_B64_RE = re.compile(r"^[A-Za-z0-9+/]+={0,2}$")
_TOP_LEVEL_KEYS = frozenset(
    {
        "schema",
        "agentId",
        "displayName",
        "versionId",
        "versionLabel",
        "parentVersionId",
        "harnessSha256",
        "claimedModel",
        "publicKey",
        "signature",
        "proofScope",
    }
)


class PassportError(ValueError):
    """A passport is malformed, ambiguous, or cryptographically invalid."""


class PassportDependencyError(PassportError):
    """A signed passport was supplied without the maintained crypto backend."""


def _proof_scope():
    return {
        "signedStatement": "key-holder-signed-this-version-declaration",
        "keyBoundAgentId": True,
        "entrantIdentityAttested": False,
        "modelAttested": False,
        "runtimeAttested": False,
        "personAttested": False,
        "executionClaimsAttested": False,
    }


PROOF_SCOPE = MappingProxyType(_proof_scope())

BOUNDARY = (
    "A valid passport signature proves only that the holder of the private key "
    "signed this tamper-evident agent-version declaration. It does not attest "
    "which model produced a move, which runtime executed the harness, who the "
    "person or legal owner behind the key is, immutable post-preflight bytes, "
    "or that execution was fair."
)


def _crypto():
    """Load maintained Ed25519 primitives only for signed-passport operations."""
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
            Ed25519PublicKey,
        )
    except (ImportError, OSError) as error:
        raise PassportDependencyError(
            "signed Agent Passport verification requires the optional "
            "'cryptography' dependency declared by BuilderWars"
        ) from error
    return InvalidSignature, serialization, Ed25519PrivateKey, Ed25519PublicKey


def _text_field(value, name, max_len):
    if not isinstance(value, str):
        raise PassportError(f"{name} must be a string")
    if not value or len(value) > max_len:
        raise PassportError(f"{name} must be 1 to {max_len} characters")
    if value != value.strip():
        raise PassportError(f"{name} must not have leading or trailing whitespace")
    if any(unicodedata.category(ch) in ("Cc", "Cf", "Cs") for ch in value):
        raise PassportError(f"{name} must not contain control or invisible characters")
    if unicodedata.normalize("NFC", value) != value:
        raise PassportError(f"{name} must be NFC-normalized")
    return value


def _hex_digest(value, name):
    if not isinstance(value, str) or _HEX64_RE.fullmatch(value) is None:
        raise PassportError(f"{name} must be exact lowercase sha256 hex")
    return value


def _strict_b64(value, expected_len, name):
    if not isinstance(value, str) or len(value) % 4 != 0 or _B64_RE.fullmatch(value) is None:
        raise PassportError(f"{name} must be standard base64")
    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as error:
        raise PassportError(f"{name} is not decodable base64") from error
    if len(raw) != expected_len:
        raise PassportError(f"{name} must decode to exactly {expected_len} bytes")
    if base64.b64encode(raw).decode("ascii") != value:
        raise PassportError(f"{name} must use canonical base64 padding")
    return raw


def _private_to_public_raw(private_key):
    _invalid, serialization, private_type, _public_type = _crypto()
    if not isinstance(private_key, private_type):
        raise PassportError("expected an Ed25519 private key")
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def _public_key_from_raw(raw):
    _invalid, _serialization, _private_type, public_type = _crypto()
    if not isinstance(raw, (bytes, bytearray)) or len(raw) != RAW_PUBLIC_KEY_BYTES:
        raise PassportError("raw Ed25519 public key must be exactly 32 bytes")
    try:
        return public_type.from_public_bytes(bytes(raw))
    except (ValueError, TypeError) as error:
        raise PassportError("raw Ed25519 public key is invalid") from error


def agent_id_for_public_key(raw_public_key):
    if not isinstance(raw_public_key, (bytes, bytearray)) or len(raw_public_key) != RAW_PUBLIC_KEY_BYTES:
        raise PassportError("raw public key must be exactly 32 bytes")
    return hashlib.sha256(AGENT_ID_DOMAIN + bytes(raw_public_key)).hexdigest()


def unsigned_declaration(
    *,
    display_name,
    version_label,
    parent_version_id,
    harness_sha256,
    claimed_model,
    raw_public_key,
):
    if parent_version_id is not None:
        parent_version_id = _hex_digest(parent_version_id, "parentVersionId")
    return {
        "schema": PASSPORT_SCHEMA,
        "agentId": agent_id_for_public_key(raw_public_key),
        "displayName": _text_field(display_name, "displayName", DISPLAY_NAME_MAX),
        "versionLabel": _text_field(version_label, "versionLabel", VERSION_LABEL_MAX),
        "parentVersionId": parent_version_id,
        "harnessSha256": _hex_digest(harness_sha256, "harnessSha256"),
        "claimedModel": (
            None
            if claimed_model is None
            else _text_field(claimed_model, "claimedModel", CLAIMED_MODEL_MAX)
        ),
        "publicKey": base64.b64encode(bytes(raw_public_key)).decode("ascii"),
        "proofScope": dict(PROOF_SCOPE),
    }


def signing_bytes(declaration):
    try:
        return VERSION_DOMAIN + canonical_bytes(declaration)
    except ValueError as error:
        raise PassportError(f"declaration is not canonically encodable: {error}") from error


def version_id_for(declaration):
    return hashlib.sha256(signing_bytes(declaration)).hexdigest()


def sign_passport(
    private_key,
    *,
    display_name,
    version_label,
    harness_sha256,
    claimed_model=None,
    parent_version_id=None,
):
    raw_public = _private_to_public_raw(private_key)
    declaration = unsigned_declaration(
        display_name=display_name,
        version_label=version_label,
        parent_version_id=parent_version_id,
        harness_sha256=harness_sha256,
        claimed_model=claimed_model,
        raw_public_key=raw_public,
    )
    message = signing_bytes(declaration)
    passport = dict(declaration)
    passport["versionId"] = hashlib.sha256(message).hexdigest()
    passport["signature"] = base64.b64encode(private_key.sign(message)).decode("ascii")
    return passport


def normalized_public_dict(passport):
    return {
        "schema": passport["schema"],
        "agentId": passport["agentId"],
        "displayName": passport["displayName"],
        "versionId": passport["versionId"],
        "versionLabel": passport["versionLabel"],
        "parentVersionId": passport["parentVersionId"],
        "harnessSha256": passport["harnessSha256"],
        "claimedModel": passport["claimedModel"],
        "publicKey": passport["publicKey"],
        "signature": passport["signature"],
        "proofScope": dict(passport["proofScope"]),
    }


def verify_passport(passport):
    if not isinstance(passport, dict):
        raise PassportError("passport must be a JSON object")
    unexpected = set(passport) - _TOP_LEVEL_KEYS
    if unexpected:
        raise PassportError(f"passport has unexpected keys: {sorted(unexpected)}")
    missing = _TOP_LEVEL_KEYS - set(passport)
    if missing:
        raise PassportError(f"passport is missing keys: {sorted(missing)}")
    if passport["schema"] != PASSPORT_SCHEMA:
        raise PassportError("unsupported passport schema")
    if passport["proofScope"] != PROOF_SCOPE:
        raise PassportError("proof scope must equal the fixed non-attestation statement")

    raw_public = _strict_b64(passport["publicKey"], RAW_PUBLIC_KEY_BYTES, "publicKey")
    signature = _strict_b64(passport["signature"], SIGNATURE_BYTES, "signature")
    declaration = {
        "schema": passport["schema"],
        "agentId": _hex_digest(passport["agentId"], "agentId"),
        "displayName": _text_field(passport["displayName"], "displayName", DISPLAY_NAME_MAX),
        "versionLabel": _text_field(passport["versionLabel"], "versionLabel", VERSION_LABEL_MAX),
        "parentVersionId": (
            None
            if passport["parentVersionId"] is None
            else _hex_digest(passport["parentVersionId"], "parentVersionId")
        ),
        "harnessSha256": _hex_digest(passport["harnessSha256"], "harnessSha256"),
        "claimedModel": (
            None
            if passport["claimedModel"] is None
            else _text_field(passport["claimedModel"], "claimedModel", CLAIMED_MODEL_MAX)
        ),
        "publicKey": passport["publicKey"],
        "proofScope": passport["proofScope"],
    }
    if declaration["agentId"] != agent_id_for_public_key(raw_public):
        raise PassportError("agentId does not match the embedded public key")
    message = signing_bytes(declaration)
    if _hex_digest(passport["versionId"], "versionId") != hashlib.sha256(message).hexdigest():
        raise PassportError("versionId does not match the canonical declaration")

    invalid_signature, _serialization, _private_type, _public_type = _crypto()
    try:
        _public_key_from_raw(raw_public).verify(signature, message)
    except invalid_signature as error:
        raise PassportError("signature verification failed") from error
    return normalized_public_dict(passport)


def _object_without_duplicate_keys(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise PassportError(f"passport JSON repeats object key: {key}")
        obj[key] = value
    return obj


def loads(text):
    if not isinstance(text, str):
        raise PassportError("passport JSON must be text")
    if len(text) > 64 * 1024:
        raise PassportError("passport JSON exceeds 64 KiB")
    try:
        obj = json.loads(text, object_pairs_hook=_object_without_duplicate_keys)
    except (json.JSONDecodeError, RecursionError) as error:
        raise PassportError("passport JSON is not valid JSON") from error
    return verify_passport(obj)


def verify_passport_file(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read(64 * 1024 + 1)
    except (OSError, UnicodeError) as error:
        raise PassportError("passport file could not be read") from error
    return loads(text)


def dumps(passport):
    try:
        verify_passport(passport)
    except PassportError as error:
        raise PassportError(f"refusing to serialize an invalid passport: {error}") from error
    return json.dumps(passport, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


__all__ = [
    "PASSPORT_SCHEMA",
    "AGENT_ID_DOMAIN",
    "VERSION_DOMAIN",
    "PROOF_SCOPE",
    "BOUNDARY",
    "PassportError",
    "PassportDependencyError",
    "unsigned_declaration",
    "version_id_for",
    "signing_bytes",
    "sign_passport",
    "dumps",
    "loads",
    "verify_passport",
    "verify_passport_file",
    "normalized_public_dict",
    "agent_id_for_public_key",
]
