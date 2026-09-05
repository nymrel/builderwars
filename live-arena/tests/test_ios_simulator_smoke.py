import subprocess
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ios_simulator_smoke import cleanup, select_device, main


class SimulatorHarnessTests(unittest.TestCase):
    def test_ocr_failure_retains_successful_stages_and_diagnostic_text(self):
        udid = "11111111-1111-1111-1111-111111111111"
        def simulated_run(*args, **kwargs):
            if args[:3] == ("xcrun", "simctl", "list"):
                return json.dumps({"devices": {"iOS-26": [{"name": "iPhone Test", "udid": udid, "isAvailable": True, "state": "Shutdown"}]}})
            if args[:3] == ("xcrun", "simctl", "launch"):
                return "com.nymrel.builderwars: 123"
            if args[0] == "swift":
                raise subprocess.CalledProcessError(1, args, output='["Your agent", "Your arena"]', stderr="OCR failed")
            return "test-source"
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                Path(".native-build/Build/Products/Debug-iphonesimulator/App.app").mkdir(parents=True)
                with patch("ios_simulator_smoke.run", side_effect=simulated_run), patch("ios_simulator_smoke.time.sleep"), patch("ios_simulator_smoke.cleanup") as shut_down:
                    with self.assertRaises(subprocess.CalledProcessError):
                        main()
                    shut_down.assert_called_once_with(udid)
                out = Path("output/playwright/native-ios")
                receipt = json.loads((out / "receipt.json").read_text())
                self.assertEqual(receipt["status"], "failed")
                self.assertEqual(receipt["launch"], "com.nymrel.builderwars: 123")
                self.assertEqual(receipt["screenshot"], "launch.png")
                self.assertEqual(receipt["settledScreenshot"], "settled.png")
                self.assertFalse(receipt["initialScreenTextVerified"])
                self.assertFalse(receipt["userFlowsTested"])
                self.assertEqual(json.loads((out / "screen-text.json").read_text()), ["Your agent", "Your arena"])
            finally:
                os.chdir(previous)

    def test_does_not_take_over_an_active_device_or_download_a_runtime(self):
        base = {"name": "iPhone Test", "udid": "11111111-1111-1111-1111-111111111111", "isAvailable": True}
        with self.assertRaisesRegex(RuntimeError, "No available shutdown"):
            select_device({"devices": {"iOS-26": [{**base, "state": "Booted"}]}})
        with self.assertRaisesRegex(RuntimeError, "No available shutdown"):
            select_device({"devices": {"iOS-26": [{**base, "state": "Shutdown", "isAvailable": False}]}})
        runtime, selected = select_device({"devices": {"iOS-26": [{**base, "state": "Shutdown"}]}})
        self.assertEqual((runtime, selected["udid"]), ("iOS-26", base["udid"]))

    def test_terminate_timeout_still_attempts_exact_shutdown(self):
        with patch("ios_simulator_smoke.subprocess.run", side_effect=subprocess.TimeoutExpired("terminate", 30)), patch("ios_simulator_smoke.run") as shutdown:
            with self.assertRaises(subprocess.TimeoutExpired):
                cleanup("11111111-1111-1111-1111-111111111111")
            shutdown.assert_called_once_with("xcrun", "simctl", "shutdown", "11111111-1111-1111-1111-111111111111", timeout=60)


if __name__ == "__main__":
    unittest.main()
