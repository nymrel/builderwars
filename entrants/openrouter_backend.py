"""Entrant-side OpenRouter backend with benchmark-safe routing controls.

This module never belongs in the referee. It reads one operator-owned API key
inside the entrant process, sends one text-only request, and retains only a
sanitized provider/usage receipt. Prompt and completion text are never included
in the receipt.
"""

from __future__ import annotations

import json
import math
import os
import re
import urllib.error
import urllib.request
from typing import Callable, Iterable, Optional

DEFAULT_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_KEY_ENV = "OPENROUTER_API_KEY"
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SAFE_RECEIPT_TEXT = re.compile(r"[^A-Za-z0-9._:/@+-]")


def _require_nonempty_token(value: str, field: str) -> str:
    if not isinstance(value, str) or not value or any(char.isspace() for char in value):
        raise ValueError(f"{field} must be one non-empty token")
    return value


def _safe_receipt_text(value: object, limit: int = 120) -> Optional[str]:
    if not isinstance(value, str) or not value:
        return None
    return _SAFE_RECEIPT_TEXT.sub("_", value)[:limit]


def _usage_int(usage: object, key: str) -> Optional[int]:
    if not isinstance(usage, dict):
        return None
    value = usage.get(key)
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None


def _usage_number(usage: object, key: str) -> Optional[float]:
    if not isinstance(usage, dict):
        return None
    value = usage.get(key)
    if (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
    ):
        return float(value)
    return None


def _usage_detail_int(usage: object, group: str, key: str) -> Optional[int]:
    if not isinstance(usage, dict):
        return None
    details = usage.get(group)
    return _usage_int(details, key)


def _usage_detail_number(usage: object, group: str, key: str) -> Optional[float]:
    if not isinstance(usage, dict):
        return None
    details = usage.get(group)
    return _usage_number(details, key)


def _extract_text(payload: object) -> str:
    if not isinstance(payload, dict):
        raise RuntimeError("OpenRouter response was not a JSON object")
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise RuntimeError("OpenRouter response did not contain a choice")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise RuntimeError("OpenRouter response did not contain a message")
    content = message.get("content")
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") in (None, "text"):
                value = part.get("text")
                if isinstance(value, str):
                    parts.append(value)
        text = "".join(parts)
    else:
        text = ""
    if not text.strip():
        raise RuntimeError("OpenRouter response contained no assistant text")
    return text.strip()


class OpenRouterBackend:
    """Call exactly one OpenRouter model under explicit privacy/routing rules."""

    kind = "openrouter"

    def __init__(
        self,
        *,
        model: str,
        provider_only: Iterable[str],
        api_key_env: str = DEFAULT_KEY_ENV,
        timeout_s: float = 300.0,
        max_tokens: int = 256,
        endpoint: str = DEFAULT_ENDPOINT,
        urlopen: Optional[Callable[..., object]] = None,
    ) -> None:
        self.model = _require_nonempty_token(model, "model")
        if "/" not in self.model:
            raise ValueError("model must use the OpenRouter provider/model slug form")
        providers = tuple(_require_nonempty_token(value, "provider") for value in provider_only)
        if not providers or len(providers) != len(set(providers)):
            raise ValueError("provider_only must contain one or more unique provider slugs")
        if not isinstance(api_key_env, str) or _ENV_NAME.fullmatch(api_key_env) is None:
            raise ValueError("api_key_env must be a valid environment-variable name")
        if not isinstance(timeout_s, (int, float)) or isinstance(timeout_s, bool) or not 10 <= timeout_s <= 900:
            raise ValueError("timeout_s must be between 10 and 900 seconds")
        if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or not 16 <= max_tokens <= 4096:
            raise ValueError("max_tokens must be an integer from 16 through 4096")
        if endpoint != DEFAULT_ENDPOINT:
            raise ValueError("benchmark backend endpoint is pinned to OpenRouter")

        self.provider_only = providers
        self.api_key_env = api_key_env
        self.timeout_s = float(timeout_s)
        self.max_tokens = max_tokens
        self.endpoint = endpoint
        self._urlopen = urlopen or urllib.request.urlopen
        self.label = f"openrouter:{self.model}"
        self.last_receipt: Optional[dict] = None

    def request_payload(self, prompt: str) -> dict:
        if not isinstance(prompt, str) or not prompt:
            raise ValueError("prompt must be a non-empty string")
        return {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens,
            "temperature": 0,
            "provider": {
                "only": list(self.provider_only),
                "allow_fallbacks": False,
                "require_parameters": True,
                "data_collection": "deny",
                "zdr": True,
            },
        }

    def _receipt_from_payload(self, payload: dict) -> dict:
        usage = payload.get("usage")
        return {
            "request_id": _safe_receipt_text(payload.get("id")),
            "requested_model": self.model,
            "resolved_model": _safe_receipt_text(payload.get("model")),
            "reported_provider": _safe_receipt_text(payload.get("provider")),
            "prompt_tokens": _usage_int(usage, "prompt_tokens"),
            "completion_tokens": _usage_int(usage, "completion_tokens"),
            "total_tokens": _usage_int(usage, "total_tokens"),
            "reasoning_tokens": _usage_detail_int(
                usage, "completion_tokens_details", "reasoning_tokens"
            ),
            "cached_tokens": _usage_detail_int(
                usage, "prompt_tokens_details", "cached_tokens"
            ),
            "cache_write_tokens": _usage_detail_int(
                usage, "prompt_tokens_details", "cache_write_tokens"
            ),
            "cost_credits": _usage_number(usage, "cost"),
            "upstream_inference_cost": _usage_detail_number(
                usage, "cost_details", "upstream_inference_cost"
            ),
            "provider_only": list(self.provider_only),
            "allow_fallbacks": False,
            "temperature": 0,
            "data_collection": "deny",
            "zdr": True,
        }

    def receipt_note(self) -> str:
        receipt = self.last_receipt
        if not isinstance(receipt, dict):
            return ""
        fields = []
        for key in (
            "resolved_model",
            "reported_provider",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "reasoning_tokens",
            "cached_tokens",
            "cache_write_tokens",
            "cost_credits",
            "upstream_inference_cost",
        ):
            value = receipt.get(key)
            if value is not None:
                fields.append(f"or_{key}={value}")
        return ";".join(fields)

    def complete(self, prompt: str) -> str:
        key = os.environ.get(self.api_key_env)
        if not key:
            raise RuntimeError(f"{self.api_key_env} is not set in this entrant's environment")
        body = json.dumps(self.request_payload(prompt), separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "X-Title": "Nymrel BuilderWars",
            },
            method="POST",
        )
        try:
            with self._urlopen(request, timeout=self.timeout_s) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as error:
            raise RuntimeError(f"OpenRouter returned HTTP {error.code}") from None
        except urllib.error.URLError as error:
            reason = error.reason
            raise RuntimeError(f"OpenRouter transport failed: {reason.__class__.__name__}") from None
        if len(raw) > MAX_RESPONSE_BYTES:
            raise RuntimeError("OpenRouter response exceeded the size limit")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise RuntimeError("OpenRouter response was not valid UTF-8 JSON") from None
        if not isinstance(payload, dict):
            raise RuntimeError("OpenRouter response was not a JSON object")
        text = _extract_text(payload)
        self.last_receipt = self._receipt_from_payload(payload)
        return text
