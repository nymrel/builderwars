import subprocess
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from android_emulator_smoke import app_socket, run, wait_for, prepare_debug


class AndroidHarnessTests(unittest.TestCase):
    def test_overlay_is_debug_only_and_leaves_main_unchanged(self):
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                source = Path("android/app/src/main/assets/capacitor.config.json")
                source.parent.mkdir(parents=True)
                config = {"android": {"webContentsDebuggingEnabled": False}, "server": {"hostname": "localhost"}}
                source.write_text(json.dumps(config))
                before = source.read_bytes()
                prepare_debug()
                self.assertEqual(source.read_bytes(), before)
                debug = json.loads(Path("android/app/src/debug/assets/capacitor.config.json").read_text())
                self.assertTrue(debug["android"]["webContentsDebuggingEnabled"])
                self.assertFalse(Path("android/app/src/release").exists())
                config["server"]["url"] = "https://unexpected.example"
                source.write_text(json.dumps(config))
                with self.assertRaises(RuntimeError):
                    prepare_debug()
            finally:
                os.chdir(previous)

    def test_socket_is_bound_to_exact_app_pid(self):
        self.assertEqual(app_socket("123", "000 00 @webview_devtools_remote_123"), "webview_devtools_remote_123")
        self.assertIsNone(app_socket("123", "000 00 @webview_devtools_remote_1234"))
        for pid in ("", "123 456", "0", "123;kill"):
            with self.assertRaises(RuntimeError):
                app_socket(pid, "")

    def test_commands_never_answer_license_prompts(self):
        with patch("android_emulator_smoke.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "ok", "")) as command:
            self.assertEqual(run("sdkmanager", "--install", "emulator"), "ok")
        self.assertEqual(command.call_args.kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(command.call_args.kwargs["timeout"], 60)

    def test_readiness_timeout_is_failure_not_success(self):
        with patch("android_emulator_smoke.time.monotonic", side_effect=[0, 2]):
            with self.assertRaises(TimeoutError):
                wait_for(lambda: False, seconds=1)


if __name__ == "__main__":
    unittest.main()
