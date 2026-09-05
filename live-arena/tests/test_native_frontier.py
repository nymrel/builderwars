"""No provider inference: fixtures and short-lived Python child processes only."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("native_frontier", Path(__file__).parents[1] / "scripts/native-frontier.py")
native = importlib.util.module_from_spec(spec); spec.loader.exec_module(native)


class NativeTests(unittest.TestCase):
    def parse(self, data, family="fable"):
        return native.parse_output(json.dumps(data).encode(), family, 12)

    def test_fable_metadata_and_public_answer_only(self):
        result = self.parse({"type": "result", "subtype": "success", "result": '{"move":"e2e4","comment":"Center."}', "modelUsage": {"claude-fable-5-1": {}}, "usage": {"input_tokens": 9, "output_tokens": 4}, "total_cost_usd": .001, "private_reasoning": "DO NOT RETAIN"})
        self.assertEqual(result["resolvedModel"], "claude-fable-5-1")
        self.assertEqual(result["identityEvidence"], "provider-response")
        self.assertNotIn("DO NOT RETAIN", json.dumps(result))
        self.assertEqual(result["inputTokens"], 9)

    def test_absent_model_not_alias(self):
        for family in ("fable", "grok", "gemini"):
            result = self.parse({"result": "a7a8q"}, family)
            self.assertIsNone(result["resolvedModel"])
            self.assertIsNone(result["inputTokens"])

    def test_fable_helper_identity_retains_total_usage(self):
        data = {"result": "e2e4", "modelUsage": {"claude-haiku-4-5-20251001": {"inputTokens": 1}, "claude-fable-5-1": {"inputTokens": 20}}, "usage": {"input_tokens": 21, "output_tokens": 5}, "total_cost_usd": .02}
        result = self.parse(data)
        self.assertEqual(result["resolvedModel"], "claude-fable-5-1")
        self.assertEqual(result["inputTokens"], 21)
        self.assertEqual(result["listCostUsd"], .02)
        data["modelUsage"]["unknown-other-model"] = {}
        self.assertIsNone(self.parse(data)["resolvedModel"])

    def test_codex_final_and_usage(self):
        events = [{"type": "item.completed", "item": {"type": "reasoning", "text": "private"}}, {"type": "item.completed", "item": {"type": "agent_message", "text": "e2e4"}}, {"type": "turn.completed", "usage": {"input_tokens": 5, "output_tokens": 2}}]
        result = native.parse_output("\n".join(map(json.dumps, events)).encode(), "astra", 1)
        self.assertEqual(result["move"], "e2e4")
        self.assertIsNone(result["resolvedModel"])

    def test_reject_tools_errors_and_malformed(self):
        for value in ({"result": "e2e4", "tool_calls": [1]}, {"result": "e2e4", "usage": {"server_tool_use": {"web_search_requests": 1}}}, {"is_error": True, "result": "quota"}, {"result": "e2e4", "usage": {"input_tokens": -1}}, {"result": "e2e9"}, {"result": '{"move":"e2e4","comment":"' + "x" * 181 + '"}'}):
            with self.assertRaises(native.Failure): self.parse(value)
        with self.assertRaises(native.Failure): native.parse_output(b"private raw output", "fable", 1)

    def test_routes_and_input_bounds(self):
        with patch.object(native, "executable", return_value=["official-client"]):
            argv, payload = native.route("fable", "public", 100)
            self.assertEqual(argv[argv.index("--tools") + 1], "")
            self.assertEqual(payload, b"public")
            self.assertIn("--ignore-user-config", native.route("astra", "x", 100)[0])
            self.assertIn("100ms", native.route("gemini", "x", 100)[0])
            with self.assertRaises(native.Failure): native.route("shell", "x", 100)
        for data in ({"prompt": "x", "milliseconds": 120001}, {"prompt": "", "milliseconds": 1}, {"prompt": "x", "milliseconds": True}):
            with self.assertRaises(native.Failure): native.request(json.dumps(data).encode())
        with self.assertRaises(native.Failure): native.request(b"x" * 16385)
        self.assertIsNone(native.child_env("fable"))
        with patch.dict(os.environ, {"EXAMPLE_SECRET": "never", "LANG": "C"}):
            self.assertNotIn("EXAMPLE_SECRET", native.child_env("astra"))

    def test_fake_process_success_output_bound_and_timeout(self):
        # Real cleanup mechanism, fake local producer; never any native provider.
        out, elapsed = native.run_child([sys.executable, "-c", "import sys; print(sys.stdin.read())"], b"public", 3000, "astra")
        self.assertEqual(out.strip(), b"public")
        self.assertLess(elapsed, 3000)
        with self.assertRaisesRegex(native.Failure, "1 MiB"):
            native.run_child([sys.executable, "-c", "import sys; sys.stdout.write('x'*1100000)"], b"", 3000, "astra")
        with self.assertRaisesRegex(native.Failure, "timeout"):
            native.run_child([sys.executable, "-c", "import time; time.sleep(60)"], b"", 80, "astra")
        with self.assertRaisesRegex(native.Failure, "unsuccessfully"):
            native.run_child([sys.executable, "-c", "raise SystemExit(2)"], b"", 3000, "astra")

    @unittest.skipUnless(os.name == "nt", "Windows Job Object assertion")
    def test_job_kills_descendant_after_root_exit(self):
        import ctypes
        from ctypes import wintypes
        code = "import subprocess,sys; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); print(p.pid)"
        out, _ = native.run_child([sys.executable, "-c", code], b"", 3000, "astra")
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        api.OpenProcess.restype = wintypes.HANDLE
        api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        api.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = api.OpenProcess(0x100000, False, int(out.strip()))
        if handle:
            try: self.assertEqual(api.WaitForSingleObject(handle, 2000), 0)
            finally: api.CloseHandle(handle)


if __name__ == "__main__": unittest.main()
