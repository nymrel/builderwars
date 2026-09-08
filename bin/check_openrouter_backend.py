#!/usr/bin/env python3
"""Offline checks for the OpenRouter entrant path; no network or key needed."""

from __future__ import annotations

import io
import contextlib
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))

from entrants.openrouter_backend import OpenRouterBackend, _NoRedirectHandler  # noqa: E402
from entrants.openrouter_fantasy_harness import decide as decide_fantasy  # noqa: E402
import run_agentwars_openrouter_match as runner  # noqa: E402
from arena.match import run_customer_local_match, _normalize_provisioned_envs  # noqa: E402


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
                "usage": {
                    "prompt_tokens": 41,
                    "completion_tokens": 8,
                    "total_tokens": 49,
                    "completion_tokens_details": {"reasoning_tokens": 2},
                    "prompt_tokens_details": {
                        "cached_tokens": 7,
                        "cache_write_tokens": 3,
                    },
                    "cost": 0.0000123,
                    "cost_details": {"upstream_inference_cost": 0.0000105},
                },
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
    require(captured["body"]["temperature"] == 0, "benchmark temperature drifted")
    require(provider["order"] == ["Z.AI"], "provider order drifted")
    require(provider["only"] == ["Z.AI"], "provider allowlist drifted")
    require(provider["allow_fallbacks"] is False, "fallbacks must be disabled")
    require(provider["require_parameters"] is True, "parameters must be enforced")
    require(provider["data_collection"] == "deny", "data collection must be denied")
    require(provider["zdr"] is True, "ZDR must be required")
    require(captured["authorization"] == "Bearer not-a-real-key", "authorization header failed")
    require("or_reported_provider=Z.AI" in backend.receipt_note(), "receipt provider missing")
    require("or_total_tokens=49" in backend.receipt_note(), "receipt usage missing")
    require("or_reasoning_tokens=2" in backend.receipt_note(), "reasoning usage missing")
    require("or_cached_tokens=7" in backend.receipt_note(), "cached usage missing")
    require("or_cache_write_tokens=3" in backend.receipt_note(), "cache-write usage missing")
    require("or_cost_credits=1.23e-05" in backend.receipt_note(), "charged cost missing")
    require(
        "or_upstream_inference_cost=1.05e-05" in backend.receipt_note(),
        "upstream cost missing",
    )
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

    try:
        OpenRouterBackend(
            model="z-ai/glm-5.3-flash",
            provider_only=["Z.AI", "another-provider"],
        )
    except ValueError:
        pass
    else:
        raise AssertionError("multiple providers were accepted for one controlled run")

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

    observation = {
        "format": "redraft",
        "round": 1,
        "needs": {"QB": 1, "RB": 1},
        "your_roster": [],
        "opponent_roster": [],
        "available_players": [
            {
                "id": 12,
                "name": "Alpha QB",
                "position": "QB",
                "redraft_points": 300,
                "dynasty_points": 250,
                "age": 25,
            },
            {
                "id": 13,
                "name": "Beta RB",
                "position": "RB",
                "redraft_points": 250,
                "dynasty_points": 280,
                "age": 23,
            },
        ],
    }

    class GoodHarnessBackend:
        def complete(self, prompt):
            require("legal_players" in prompt, "harness prompt omitted the legal board")
            return '{"player_id":12}'

        def receipt_note(self):
            return "or_cost_credits=1e-05;or_total_tokens=40"

    move, note = decide_fantasy(observation, "win-now", GoodHarnessBackend())
    require(move == {"player_id": 12}, "harness rejected a legal model move")
    require(note.startswith("source=model;"), "harness did not record model source")
    require("or_cost_credits=1e-05" in note, "harness omitted the sanitized receipt")

    class BrokenHarnessBackend:
        def complete(self, _prompt):
            raise RuntimeError("blocked")

        def receipt_note(self):
            return ""

    move, note = decide_fantasy(observation, "win-now", BrokenHarnessBackend())
    require(move == {"player_id": 12}, "deterministic fallback changed")
    require(
        note.startswith("source=fallback;reason=backend_error:RuntimeError"),
        "harness did not record backend fallback",
    )

    # Reuse one process/backend as the real match does: success then failure.
    backend.complete("successful move")
    require(backend.receipt_note(), "successful request omitted its receipt")
    backend._urlopen = http_failure
    move, note = decide_fantasy(observation, "win-now", backend)
    require(note.startswith("source=fallback;"), "failed request did not fall back")
    require("or_" not in note, "failed move reused the preceding request's usage/cost")
    require(backend.last_receipt is None, "failed request retained a stale receipt")

    def empty_billed_response(_request, timeout):
        return FakeResponse({"choices": [{"message": {"content": ""}}],
                             "usage": {"total_tokens": 9, "cost": 0.001}})

    backend._urlopen = empty_billed_response
    _, note = decide_fantasy(observation, "win-now", backend)
    require("source=fallback;" in note, "empty output was accepted as model play")
    require("or_cost_credits=0.001" in note and "or_total_tokens=9" in note,
            "billed invalid-output response lost its own usage receipt")

    production = OpenRouterBackend(model="z-ai/glm-5.3-flash", provider_only=["Z.AI"])
    handlers = production._urlopen.__self__.handlers
    redirect = next(handler for handler in handlers if isinstance(handler, _NoRedirectHandler))
    request = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
                                     data=b"{}", headers={"Authorization": "Bearer fake"})
    with mock.patch.object(redirect.parent, "open", side_effect=AssertionError("redirect followed")):
        for code in (301, 302, 303, 307, 308):
            try:
                refused = redirect.http_error_302(request, io.BytesIO(), code, "redirect",
                                                  {"location": "https://example.invalid/steal"})
            except urllib.error.HTTPError as error:
                require(error.code == code, "redirect error status changed")
            else:
                require(refused is None, "credential-bearing redirect was allowed")

    require(runner.run_match is run_customer_local_match, "runner bypasses execution-scope wrapper")
    def fake_match(**kwargs):
        rows = _normalize_provisioned_envs(kwargs["entrants"], kwargs["provisioned_envs"])
        require(all(row == {"TEST_OPENROUTER_KEY": "secret-do-not-print"} for row in rows),
                "runner did not provision exactly the selected key to both entrants")
        return {"transcript": "fixture", "match_id": "fixture", "chain_head": "abc", "winner": 0}

    names = ("OpenRouter Sunday Machine", "OpenRouter Future Proof")
    with tempfile.TemporaryDirectory() as directory:
        summary_path = os.path.join(directory, "summary.json")
        arguments = ["--provider", "Z.AI", "--api-key-env", "TEST_OPENROUTER_KEY",
                     "--out", os.path.join(directory, "match"), "--json-out", summary_path]
        for model_counts, expected, exit_code in (
            ((6, 6), "model_influenced_unattested", 0),
            ((5, 6), "mixed_model_and_fallback_unattested", 2),
            ((0, 6), "partial_model_influence_unattested", 2),
            ((0, 0), "fallback_only_not_model_played", 2),
        ):
            sources = {name: {"model": count, "fallback": 6-count, "scripted": 0, "other": 0}
                       for name, count in zip(names, model_counts)}
            with mock.patch.object(runner, "run_match", side_effect=fake_match), \
                 mock.patch.object(runner, "verify", return_value={"verdict": "PASS"}), \
                 mock.patch.object(runner, "move_source_counts", return_value=sources), \
                 mock.patch.object(runner, "final_scores", return_value=[1, 0]), \
                 mock.patch.object(runner, "provider_receipts", return_value=[]), \
                 contextlib.redirect_stdout(io.StringIO()):
                require(runner.main(arguments) == exit_code, "runner completion status drifted")
            with open(summary_path, encoding="utf-8") as handle:
                summary = json.load(handle)
            require(summary["status"] == expected, "runner misrepresented mixed model/fallback play")
            require("secret-do-not-print" not in json.dumps(summary), "runner summary leaked key")
            with mock.patch.object(runner, "run_match") as no_match:
                try:
                    runner.main(arguments)
                except Exception as error:
                    require(getattr(error, "code", None) == "summary_output_exists",
                            "output collision failed for an unrelated reason")
                else:
                    raise AssertionError("existing summary was overwritten")
                no_match.assert_not_called()
            with open(summary_path, encoding="utf-8") as handle:
                require(json.load(handle) == summary, "collision modified existing summary")
            os.unlink(summary_path)

    print(
        "openrouter entrant checks: PASS "
        "(routing, privacy, receipts, cost, harness, fallback, negative cases)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
