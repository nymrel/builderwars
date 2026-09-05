"""Redacted secret wrapper.

A ``SecretValue`` holds one credential-shaped value (a PKCE verifier, a one-time
callback code, an exchanged OpenRouter key, a BuildWars pairing key) and makes
accidental disclosure hard:

  * ``repr`` and ``str`` show only a length marker;
  * JSON serialization fails closed (``json.dumps`` raises TypeError);
  * iteration/format protocols are not implemented, so f-strings and loops
    fall back to the redacted ``__str__``.

The value is reachable only through ``reveal()``, whose name says what it does
at every call site.
"""

import os


class SecretValue:
    """A credential value that refuses to describe itself."""

    __slots__ = ("_value",)

    def __init__(self, value):
        if not isinstance(value, (str, bytes)):
            raise TypeError("SecretValue holds str or bytes only")
        if isinstance(value, str):
            if not value:
                raise ValueError("SecretValue rejects empty values")
            encoded = value.encode("utf-8")
        else:
            if not value:
                raise ValueError("SecretValue rejects empty values")
            encoded = value
        if len(encoded) > 65536:
            raise ValueError("SecretValue rejects oversized payloads")
        object.__setattr__(self, "_value", value)

    def reveal(self):
        """Return the raw value. Every call site reads as an explicit unwrap."""
        return self._value

    @property
    def byte_length(self):
        return len(self._value.encode("utf-8") if isinstance(self._value, str) else self._value)

    def __setattr__(self, name, value):
        raise AttributeError("SecretValue is immutable")

    def __delattr__(self, name):
        raise AttributeError("SecretValue is immutable")

    def __repr__(self):
        return f"SecretValue(<redacted:{self.byte_length} bytes>)"

    def __str__(self):
        return repr(self)

    def __reduce__(self):
        # Defeat pickle-based accidental persistence paths.
        raise TypeError("SecretValue must not be serialized")


def redact(text, *secrets):
    """Return ``text`` with every occurrence of each secret replaced.

    Used on error paths so a provider response body can be surfaced without a
    credential even if the remote side echoed one back.
    """
    out = text
    for secret in secrets:
        if secret is None:
            continue
        value = secret.reveal() if isinstance(secret, SecretValue) else secret
        if isinstance(value, bytes):
            value = value.decode("utf-8", "replace")
        if value:
            out = out.replace(value, "[redacted]")
    return out


def wipe(value):
    """Best-effort in-place overwrite for mutable byte buffers."""
    if isinstance(value, bytearray):
        for i in range(len(value)):
            value[i] = 0
    return value
