"""Random, non-enumerable public identifiers.

Every BuildWars envelope id is 128 bits of CSPRNG output behind a short type
prefix, so ids cannot be enumerated, sequenced, or mined for meaning. Only the
id travels; nothing about the holder is encoded in it.
"""

import re
import secrets

ID_PREFIXES = {
    "identity": "bwid",
    "provider_link": "bwpl",
    "runner_pairing": "bwrp",
    "runner": "bwrun",
    "match_job": "bwmj",
    "result_attestation": "bwra",
}

_RANDOM_CHARS = 22  # secrets.token_urlsafe(16) is exactly 22 url-safe chars

_RES = {
    kind: re.compile(r"^" + re.escape(prefix) + r"_[A-Za-z0-9_-]{%d}$" % _RANDOM_CHARS)
    for kind, prefix in ID_PREFIXES.items()
}


def new_id(kind):
    """Return a fresh public id for an envelope kind, e.g. ``bwid_A3...``."""
    try:
        prefix = ID_PREFIXES[kind]
    except KeyError:
        raise ValueError(f"unknown id kind {kind!r}") from None
    return prefix + "_" + secrets.token_urlsafe(16)


def id_is_valid(kind, value):
    """Strict shape check; no other id format is accepted anywhere."""
    if not isinstance(value, str):
        return False
    res = _RES.get(kind)
    if res is None:
        raise ValueError(f"unknown id kind {kind!r}")
    return res.fullmatch(value) is not None


def new_key_id(fingerprint_hex32):
    """Pairing-key ids are 128-bit public fingerprints: ``bpk_`` + 32 hex."""
    if not isinstance(fingerprint_hex32, str) or not re.fullmatch(
        r"[0-9a-f]{32}", fingerprint_hex32
    ):
        raise ValueError("key fingerprint must be 32 lowercase hex chars")
    return "bpk_" + fingerprint_hex32


KEY_ID_RE = re.compile(r"^bpk_[0-9a-f]{32}$")


def key_id_is_valid(value):
    return isinstance(value, str) and KEY_ID_RE.fullmatch(value) is not None
