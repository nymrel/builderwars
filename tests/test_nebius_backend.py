import json
import os
import unittest
from unittest import mock
from urllib.error import HTTPError

from entrants.nebius_backend import NebiusTokenFactoryBackend


class NebiusTokenFactoryBackendTests(unittest.TestCase):
    def test_requires_nvidia_model_id(self):
        with self.assertRaisesRegex(ValueError, "nvidia/<model>"):
            NebiusTokenFactoryBackend("openai/gpt-oss-120b")
        with self.assertRaisesRegex(ValueError, "nvidia/<model>"):
            NebiusTokenFactoryBackend("nvidia/bad model")

    def test_requires_customer_key_without_echoing_it(self):
        backend = NebiusTokenFactoryBackend(transport=lambda *_: b"{}")
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "NEBIUS_API_KEY is not set"):
                backend.complete("hello")

    def test_builds_pinned_openai_compatible_request(self):
        seen = {}

        def transport(request, timeout_s):
            seen["url"] = request.full_url
            seen["headers"] = dict(request.header_items())
            seen["body"] = json.loads(request.data.decode("utf-8"))
            seen["timeout"] = timeout_s
            return json.dumps(
                {"choices": [{"message": {"content": "  model answer  "}}]}
            ).encode("utf-8")

        backend = NebiusTokenFactoryBackend(
            "nvidia/nemotron-3-super-120b-a12b",
            timeout_s=17,
            transport=transport,
        )
        with mock.patch.dict(
            os.environ,
            {"NEBIUS_API_KEY": "n" * 32},
            clear=True,
        ):
            self.assertEqual(backend.complete("hello"), "model answer")

        self.assertEqual(seen["url"], NebiusTokenFactoryBackend.PINNED_ENDPOINT)
        self.assertEqual(seen["timeout"], 17)
        self.assertEqual(
            seen["headers"]["Authorization"],
            "Bearer " + ("n" * 32),
        )
        self.assertEqual(
            seen["body"]["model"],
            "nvidia/nemotron-3-super-120b-a12b",
        )
        self.assertEqual(seen["body"]["messages"][0]["content"], "hello")
        self.assertEqual(
            seen["body"]["max_tokens"],
            NebiusTokenFactoryBackend.MAX_TOKENS,
        )

    def test_transport_failures_are_sanitized(self):
        secret = "n" * 32

        def transport(_request, _timeout):
            raise OSError("socket detail that must not escape")

        backend = NebiusTokenFactoryBackend(transport=transport)
        with mock.patch.dict(os.environ, {"NEBIUS_API_KEY": secret}, clear=True):
            with self.assertRaises(RuntimeError) as caught:
                backend.complete("hello")
        message = str(caught.exception)
        self.assertNotIn(secret, message)
        self.assertNotIn("socket detail", message)
        self.assertIn("OSError", message)

    def test_redirect_failure_does_not_echo_secret(self):
        secret = "n" * 32

        def transport(request, _timeout):
            raise HTTPError(
                request.full_url,
                302,
                "Found",
                {},
                None,
            )

        backend = NebiusTokenFactoryBackend(transport=transport)
        with mock.patch.dict(os.environ, {"NEBIUS_API_KEY": secret}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "refused redirect"):
                backend.complete("hello")

    def test_response_and_prompt_bounds_fail_closed(self):
        backend = NebiusTokenFactoryBackend(
            transport=lambda *_: b"x" * (NebiusTokenFactoryBackend.MAX_RESPONSE_BYTES + 1)
        )
        with mock.patch.dict(os.environ, {"NEBIUS_API_KEY": "n" * 32}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "response exceeded size cap"):
                backend.complete("hello")
            with self.assertRaisesRegex(ValueError, "provider prompt"):
                backend.complete("x" * (NebiusTokenFactoryBackend.MAX_PROMPT_BYTES + 1))

    def test_malformed_or_empty_content_rejected(self):
        with mock.patch.dict(os.environ, {"NEBIUS_API_KEY": "n" * 32}, clear=True):
            malformed = NebiusTokenFactoryBackend(transport=lambda *_: b"not-json")
            with self.assertRaisesRegex(RuntimeError, "malformed JSON"):
                malformed.complete("hello")

            empty = NebiusTokenFactoryBackend(
                transport=lambda *_: json.dumps(
                    {"choices": [{"message": {"content": "   "}}]}
                ).encode("utf-8")
            )
            with self.assertRaisesRegex(RuntimeError, "missing assistant content"):
                empty.complete("hello")


if __name__ == "__main__":
    unittest.main()
