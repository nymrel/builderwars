import subprocess
import unittest
from unittest.mock import patch

from ios_simulator_smoke import cleanup, select_device


class SimulatorHarnessTests(unittest.TestCase):
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
