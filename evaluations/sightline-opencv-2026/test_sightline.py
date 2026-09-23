from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = Path(__file__).with_name("sightline.py")
SPEC = importlib.util.spec_from_file_location("sightline_stage1", MODULE_PATH)
assert SPEC and SPEC.loader
sightline = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sightline
SPEC.loader.exec_module(sightline)


class FakeCV2:
    __version__ = "4.99.0"


class SightlineTests(unittest.TestCase):
    def test_empty_findings_are_accepted_without_execution_authority(self) -> None:
        trace = sightline.SightlineAgent().plan([])
        self.assertEqual(trace.action, "accept_no_material_change")
        self.assertFalse(trace.human_approval_required)
        self.assertFalse(trace.execution_authorized)
        self.assertFalse(trace.aws_invoked)

    def test_medium_finding_requires_human_approval(self) -> None:
        finding = sightline.VisualFinding(
            kind="visual_change",
            risk="medium",
            bbox_xywh=(2, 3, 8, 9),
            changed_pixels=72,
            image_pixels=1000,
        )
        trace = sightline.SightlineAgent().plan([finding])
        self.assertEqual(trace.action, "request_human_approval")
        self.assertTrue(trace.human_approval_required)

    def test_digest_is_order_independent(self) -> None:
        left = sightline.VisualFinding("visual_change", "low", (0, 0, 2, 2), 4, 100)
        right = sightline.VisualFinding("visual_change", "high", (8, 8, 2, 2), 4, 100)
        agent = sightline.SightlineAgent()
        self.assertEqual(
            agent.plan([left, right]).findings_sha256,
            agent.plan([right, left]).findings_sha256,
        )

    def test_unbounded_finding_set_fails_closed(self) -> None:
        finding = sightline.VisualFinding("visual_change", "low", (0, 0, 1, 1), 1, 10)
        trace = sightline.SightlineAgent(max_findings=1).plan([finding, finding])
        self.assertEqual(trace.action, "reject_unbounded_input")
        self.assertFalse(trace.human_approval_required)

    def test_non_opencv_5_runtime_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "OpenCV 5 required"):
            sightline.OpenCV5Perception(FakeCV2())

    def test_invalid_finding_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            sightline.VisualFinding("visual_change", "low", (0, 0, 1, 1), 11, 10)


if __name__ == "__main__":
    unittest.main()
