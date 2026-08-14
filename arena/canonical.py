"""Canonical encoding and hashing.

Every integrity property in this engine rests on this module producing identical
bytes on any machine, for any equal value. It is deliberately strict: anything
whose textual form could vary across platforms or interpreter versions is
rejected at encode time rather than silently producing a different hash later.

Floats are the notable ban. `0.1 + 0.2` and a JSON round-trip of it do not
reliably agree across languages, and a scoring path that admits floats admits a
replay that disagrees with the match it is supposed to reproduce. Scores and
game state are integers.
"""

import hashlib
import json

GENESIS = "0" * 64
_SEP = b"\x1f"  # ASCII unit separator; keeps prev-hash and body from ever running together


class NonCanonical(ValueError):
    """Raised when a value cannot be encoded to stable bytes."""


def _check(obj, path="$"):
    # bool must be tested before int: bool is a subclass of int in Python.
    if obj is None or isinstance(obj, (bool, str)):
        return
    if isinstance(obj, float):
        raise NonCanonical(
            f"{path}: float is not canonically encodable. Use an int, or a string "
            f"if the value is genuinely fractional."
        )
    if isinstance(obj, int):
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if not isinstance(k, str):
                raise NonCanonical(f"{path}: object keys must be strings, got {type(k).__name__}")
            _check(v, f"{path}.{k}")
        return
    if isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            _check(v, f"{path}[{i}]")
        return
    raise NonCanonical(f"{path}: {type(obj).__name__} is not canonically encodable")


def canonical_bytes(obj) -> bytes:
    """Deterministic UTF-8 JSON: sorted keys, no insignificant whitespace."""
    _check(obj)
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def digest(obj) -> str:
    """sha256 of the canonical encoding of a value."""
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def chain(prev_hex: str, body) -> str:
    """Hash one transcript record onto the chain.

    Including the previous hash in the preimage is what makes an edit anywhere in
    the transcript invalidate every record after it.
    """
    h = hashlib.sha256()
    h.update(prev_hex.encode("ascii"))
    h.update(_SEP)
    h.update(canonical_bytes(body))
    return h.hexdigest()


def file_digest(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            h.update(block)
    return h.hexdigest()
