"""Nebius Token Factory backend for the 2026 NVIDIA hackathon lane.

This module is intentionally separate from BuilderWars' general provider catalog.
It exists to produce competition-period evidence against Nebius Token Factory
without claiming that Nebius is an admitted long-lived BuilderWars provider yet.

The caller owns the Token Factory account and NEBIUS_API_KEY. The key is read
only at request time, sent only to the pinned Nebius endpoint, never logged, and
never returned in errors. Redirects are refused so Authorization cannot move to
another origin.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


class NebiusTokenFactoryBackend:
    """Bounded OpenAI-compatible chat completion on Nebius Token Factory."""

    ENDPOINT = "https://api.tokenfactory.nebius.com/v1/chat/completions"
    PINNED_ENDPOINT = ENDPOINT
    ENV_VAR = "NEBIUS_API_KEY"
    DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b"
    MAX_PROMPT_BYTES = 65536
    MAX_RESPONSE_BYTES = 2 * 1024 * 1024
    MAX_TOKENS = 512

    class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    _OPENER = urllib.request.build_opener(_NoRedirectHandler)

    def __init__(self, model=DEFAULT_MODEL, timeout_s=110, transport=None):
        if (
            not isinstance(model, str)
            or not model.startswith("nvidia/")
            or len(model) > 200
            or any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in model)
        ):
            raise ValueError(
                "Nebius hackathon backend requires one explicit nvidia/<model> identifier"
            )
        if (
            isinstance(timeout_s, bool)
            or not isinstance(timeout_s, (int, float))
            or not 1 <= timeout_s <= 3600
        ):
            raise ValueError("timeout_s must be a number in [1, 3600]")
        self.model = model
        self.timeout_s = timeout_s
        self._transport = transport
        self.label = f"nebius-token-factory:{model}"

    @classmethod
    def _default_transport(cls, request, timeout_s):
        try:
            with cls._OPENER.open(request, timeout=timeout_s) as response:
                if response.geturl() != cls.PINNED_ENDPOINT:
                    raise RuntimeError("Nebius response origin/path drifted")
                return response.read(cls.MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as error:
            if 300 <= error.code < 400:
                raise RuntimeError(
                    f"Nebius refused redirect (HTTP {error.code}); "
                    "authorization is never forwarded off-origin"
                ) from None
            raise RuntimeError(f"Nebius HTTP {error.code}") from None

    def complete(self, prompt):
        if not isinstance(prompt, str):
            raise TypeError("provider prompt must be a string")
        prompt_bytes = prompt.encode("utf-8")
        if not prompt_bytes or len(prompt_bytes) > self.MAX_PROMPT_BYTES:
            raise ValueError(
                f"provider prompt must contain 1..{self.MAX_PROMPT_BYTES} UTF-8 bytes"
            )

        key = os.environ.get(self.ENV_VAR)
        if not key:
            raise RuntimeError(
                f"{self.ENV_VAR} is not set; create a Token Factory API key in "
                "your own Nebius project and export it only in this runner environment"
            )
        if (
            not isinstance(key, str)
            or not 16 <= len(key) <= 2048
            or any(ord(ch) < 33 or ord(ch) > 126 for ch in key)
        ):
            raise RuntimeError(f"{self.ENV_VAR} has an unsafe shape")
        if self.ENDPOINT != self.PINNED_ENDPOINT:
            raise RuntimeError("Nebius endpoint does not match the pinned URL")

        body = json.dumps(
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": self.MAX_TOKENS,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self.ENDPOINT,
            data=body,
            headers={
                "content-type": "application/json",
                "authorization": f"Bearer {key}",
            },
            method="POST",
        )

        transport = self._transport or self._default_transport
        try:
            raw = transport(request, self.timeout_s)
        except RuntimeError:
            raise
        except urllib.error.HTTPError as error:
            if 300 <= error.code < 400:
                raise RuntimeError(
                    f"{self.label} refused redirect (HTTP {error.code}); "
                    "authorization is never forwarded off-origin"
                ) from None
            raise RuntimeError(f"{self.label} HTTP {error.code}") from None
        except Exception as error:
            raise RuntimeError(
                f"{self.label} transport failed: {error.__class__.__name__}"
            ) from None

        if not isinstance(raw, (bytes, bytearray)):
            raise RuntimeError(f"{self.label} transport returned non-bytes")
        raw = bytes(raw)
        if len(raw) > self.MAX_RESPONSE_BYTES:
            raise RuntimeError(f"{self.label} response exceeded size cap")

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise RuntimeError(f"{self.label} returned malformed JSON") from None

        choices = payload.get("choices") if isinstance(payload, dict) else None
        content = None
        if isinstance(choices, list) and choices:
            message = choices[0].get("message") if isinstance(choices[0], dict) else None
            if isinstance(message, dict):
                content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(f"{self.label} response missing assistant content")
        return content.strip()
