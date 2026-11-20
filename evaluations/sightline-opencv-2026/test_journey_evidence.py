"""Offline tests for the local walkthrough's evidence boundaries."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from demo_approval import DEMO_ACTION, DemoApprovalGate
from record_journey_demo import Diagnostics, Journey, reserve_output


class JourneyEvidenceTests(unittest.TestCase):
    def test_output_reservation_preserves_old_artifacts_and_is_atomic(self):
        from concurrent.futures import ThreadPoolExecutor
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            def reserve():
                try:
                    reserve_output(output)
                    return True
                except FileExistsError:
                    return False
            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertEqual(sorted(pool.map(lambda _: reserve(), range(2))), [False, True])
            stale = output / "journey-receipt.json"
            stale.write_text("old evidence")
            with self.assertRaises(FileExistsError):
                reserve_output(output)
            self.assertEqual(stale.read_text(), "old evidence")

    def test_unverified_source_mode_reports_only_sanitized_state(self):
        import asyncio
        for mode, expected in (("demo_fixture_fallback", "demo_fixture_fallback"), ("secret-token", "missing_or_unrecognized")):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                app = Mock()
                app.goto = AsyncMock(return_value=Mock(ok=True))
                app.wait_for_function = AsyncMock()
                app.get_attribute = AsyncMock(return_value=mode)
                with self.assertRaises(RuntimeError) as raised:
                    asyncio.run(Journey(Path(directory), app, {}).prepare("http://127.0.0.1/"))
                self.assertIn(expected, str(raised.exception))
                self.assertNotIn("secret-token", str(raised.exception))

    def test_synthetic_failure_controls_use_expected_rejections(self):
        import asyncio
        with tempfile.TemporaryDirectory() as directory:
            journey = Journey(Path(directory), None, {})
            journey.stage = 5
            result = asyncio.run(journey.perform("failures"))
            self.assertEqual(result["step"], 6)
            self.assertEqual([x["name"] for x in journey.failure_controls], ["Malformed PNG", "Dimension mismatch", "Oversized declared IHDR"])
            self.assertTrue(all(x["passed"] for x in journey.failure_controls))

    def test_unavailable_loopback_shell_fails_before_waiting(self):
        import asyncio
        for response in (None, Mock(ok=False)):
            with self.subTest(response=response), tempfile.TemporaryDirectory() as directory:
                app = Mock()
                app.goto = AsyncMock(return_value=response)
                app.wait_for_function = AsyncMock()
                with self.assertRaisesRegex(RuntimeError, "did not return HTTP success"):
                    asyncio.run(Journey(Path(directory), app, {}).prepare("http://127.0.0.1/"))
                app.wait_for_function.assert_not_awaited()

    def test_current_capture_findings_can_invalidate_prior_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            journey = Journey(Path(directory), None, {})
            journey.perception = Mock()
            journey.perception.analyze_files.return_value = ["fresh"]
            journey.agent = Mock()
            journey.agent.plan.return_value.findings_sha256 = "c" * 64
            journey.findings = ["stale"]
            gate = DemoApprovalGate(findings_sha256="a" * 64, candidate_sha256="b" * 64)
            gate.record_demo_operator_event()
            current = journey.current_findings_digest("before-approved-restore.png")
            with self.assertRaisesRegex(PermissionError, "findings changed"):
                gate.consume(action=DEMO_ACTION, current_candidate_sha256="b" * 64, current_findings_sha256=current)
            journey.perception.analyze_files.assert_called_once_with(Path(directory) / "baseline.png", Path(directory) / "before-approved-restore.png", threshold=24, min_component_pixels=64)
            journey.agent.plan.assert_called_once_with(["fresh"])

    def test_diagnostics_bounded_and_reject_untrusted_text(self):
        with tempfile.TemporaryDirectory() as directory:
            diag = Diagnostics(Path(directory))
            for _ in range(25):
                diag.record("demo", "blocked_external_request")
            diag.record("app", "pageerror")
            with self.assertRaises(ValueError):
                diag.record("demo", "https://example.invalid/?token=secret")
            data = json.loads(diag.path.read_text())
            self.assertEqual(len(data["events"]), 20)
            self.assertEqual(data["counts"]["demo.blocked_external_request"], 25)
            self.assertNotIn("token", diag.path.read_text())


if __name__ == "__main__":
    unittest.main()
