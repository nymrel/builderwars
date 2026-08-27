#!/usr/bin/env python3
"""Offline checks for the OpenRouter entrant backend; no network or key needed."""

from __future__ import annotations

import io
import json
import os
import sys
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from entrants.openrouter_backend import OpenRouterBackend  # noqa: E402


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, _limit):
        return self.payload


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    captured = {}

    def fake_urlopen(request, timeout):
        captured["timeout"] = timeout
        captured["authorization"] = request.headers.get("Authorization")
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(
            {
                "id": "gen-test-1",
                "model": "z-ai/glm-5.3-flash",
                "provider": "Z.AI",
                "choices": [{"message": {"content": "{\"player_id\":12}"}}],
                "usage": {"prompt_tokens": 41, "completion_tokens": 8, "total_tokens": 49},
            }
        )

    os.environ["TEST_OPENROUTER_KEY"] = "not-a-real-key"
    backend = OpenRouterBackend(
        model="z-ai/glm-5.3-flash",
        provider_only=["Z.AI"],
        api_key_env="TEST_OPENROUTER_KEY",
        timeout_s=45,
        max_tokens=128,
        urlopen=fake_urlopen,
    )
    require(backend.complete("pick") == '{"player_id":12}', "text extraction failed")
    provider = captured["body"]["provider"]
    require(provider["only"] == ["Z.AI"], "provider allowlist drifted")
    require(provider["allow_fallbacks"] is False, "fallbacks must be disabled")
    require(provider["require_parameters"] is True, "parameters must be enforced")
    require(provider["data_collection"] == "deny", "data collection must be denied")
    require(provider["zdr"] is True, "ZDR must be required")
    require(captured["authorization"] == "Bearer not-a-real-key", "authorization header failed")
    require("or_reported_provider=Z.AI" in backend.receipt_note(), "receipt provider missing")
    require("or_total_tokens=49" in backend.receipt_note(), "receipt usage missing")
    require("pick" not in json.dumps(backend.last_receipt), "receipt leaked prompt")
    require("player_id" not in json.dumps(backend.last_receipt), "receipt leaked completion")

    os.environ.pop("TEST_OPENROUTER_KEY")
    try:
        backend.complete("pick")
    except RuntimeError as error:
        require("TEST_OPENROUTER_KEY is not set" in str(error), "missing-key error drifted")
    else:
        raise AssertionError("missing key did not fail closed")

    try:
        OpenRouterBackend(model="glm", provider_only=["Z.AI"])
    except ValueError:
        pass
    else:
        raise AssertionError("non-slug model was accepted")

    try:
        OpenRouterBackend(model="z-ai/glm-5.3-flash", provider_only=[])
    except ValueError:
        pass
    else:
        raise AssertionError("empty provider allowlist was accepted")

    def http_failure(_request, timeout):
        del timeout
        raise urllib.error.HTTPError("https://openrouter.ai", 401, "unauthorized", {}, io.BytesIO(b"secret"))

    os.environ["TEST_OPENROUTER_KEY"] = "secret-do-not-print"
    failing = OpenRouterBackend(
        model="z-ai/glm-5.3-flash",
        provider_only=["Z.AI"],
        api_key_env="TEST_OPENROUTER_KEY",
        urlopen=http_failure,
    )
    try:
        failing.complete("sensitive prompt")
    except RuntimeError as error:
        rendered = str(error)
        require(rendered == "OpenRouter returned HTTP 401", "HTTP error was not redacted")
        require("secret" not in rendered and "sensitive" not in rendered, "HTTP error leaked data")
    else:
        raise AssertionError("HTTP failure did not fail closed")

    print("openrouter backend checks: PASS (routing, privacy, receipts, negative cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
