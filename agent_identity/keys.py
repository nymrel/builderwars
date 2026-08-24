"""Strict Ed25519 key handling for AgentBattles passports.

Only the maintained `cryptography` implementation is used. No elliptic-curve
arithmetic lives here. Private keys are written as PKCS#8 PEM; encrypted with a
passphrase by default, unencrypted only through the explicitly named unsafe
test-only helper. Nothing in this module ever prints or logs key bytes.
"""

import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

RAW_PUBLIC_KEY_BYTES = 32
MIN_PASSPHRASE_CHARACTERS = 12
UNSAFE_KEY_SUFFIX = ".unsafe-test-only.key.pem"


class KeyMaterialError(ValueError):
    """A key file could not be read safely, or was not an Ed25519 key."""


def generate_private_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


def private_to_public_raw(private_key) -> bytes:
    if not isinstance(private_key, Ed25519PrivateKey):
        raise KeyMaterialError("expected an Ed25519 private key")
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def _serialize(private_key, encryption):
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption,
    )


def save_private_key_encrypted(path, private_key, passphrase: bytes, *, overwrite=False) -> str:
    """Write an encrypted PKCS#8 PEM. Best-effort restrictive file mode."""
    try:
        decoded_passphrase = bytes(passphrase).decode("utf-8")
    except (TypeError, UnicodeDecodeError) as error:
        raise KeyMaterialError("passphrase must be valid UTF-8 bytes") from error
    if len(decoded_passphrase) < MIN_PASSPHRASE_CHARACTERS:
        raise KeyMaterialError(
            f"passphrase must be at least {MIN_PASSPHRASE_CHARACTERS} characters"
        )
    pem = _serialize(private_key, serialization.BestAvailableEncryption(bytes(passphrase)))
    return _write_private(path, pem, overwrite=overwrite)


def save_private_key_unencrypted(path, private_key, *, overwrite=False) -> str:
    """UNSAFE test-only output. Callers must name the file accordingly."""
    if not os.fspath(path).endswith(UNSAFE_KEY_SUFFIX):
        raise KeyMaterialError(
            f"unencrypted test keys must end with {UNSAFE_KEY_SUFFIX}"
        )
    pem = _serialize(private_key, serialization.NoEncryption())
    return _write_private(path, pem, overwrite=overwrite)


def _write_private(path, pem: bytes, *, overwrite=False) -> str:
    path = os.fspath(path)
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | (os.O_TRUNC if overwrite else os.O_EXCL)
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError as error:
        raise KeyMaterialError("refusing to overwrite an existing private key") from error
    try:
        with os.fdopen(fd, "wb") as handle:
            fd = None
            handle.write(pem)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        if fd is not None:
            os.close(fd)
        try:
            os.unlink(path)
        except OSError:
            pass
        raise
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


def load_private_key_file(path, passphrase) -> Ed25519PrivateKey:
    """Load a PKCS#8 PEM private key.

    `passphrase=None` reads an explicitly unencrypted (unsafe test-only) file;
    anything else must decrypt an encrypted one. Wrong passphrase fails without
    detail so errors never leak structure.
    """
    try:
        with open(path, "rb") as fh:
            data = fh.read(64 * 1024 + 1)
    except OSError as e:
        raise KeyMaterialError(f"could not read key file: {os.path.basename(str(path))}") from e
    if len(data) > 64 * 1024:
        raise KeyMaterialError("private key file exceeds 64 KiB")
    password = None if passphrase is None else bytes(passphrase)
    try:
        key = serialization.load_pem_private_key(data, password=password)
    except (InvalidTag, TypeError, ValueError) as e:
        # InvalidTag means a wrong passphrase on an encrypted key; collapse every
        # failure into one non-secret message.
        raise KeyMaterialError(
            "could not load private key (wrong passphrase, or not a supported PKCS#8 PEM)"
        ) from e
    if not isinstance(key, Ed25519PrivateKey):
        raise KeyMaterialError("key file does not contain an Ed25519 private key")
    return key


def public_key_from_raw(raw: bytes) -> Ed25519PublicKey:
    if not isinstance(raw, (bytes, bytearray)) or len(raw) != RAW_PUBLIC_KEY_BYTES:
        raise KeyMaterialError("raw Ed25519 public key must be exactly 32 bytes")
    try:
        return Ed25519PublicKey.from_public_bytes(bytes(raw))
    except (ValueError, TypeError) as error:
        raise KeyMaterialError("raw Ed25519 public key is invalid") from error
