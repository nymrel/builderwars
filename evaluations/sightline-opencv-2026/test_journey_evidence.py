"""Offline tests for the local walkthrough's evidence boundaries."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from demo_approval import DEMO_ACTION, DemoApprovalGate
from record_journey_demo import Diagnostics, Journey


class JourneyEvidenceTests(unittest.TestCase):
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
