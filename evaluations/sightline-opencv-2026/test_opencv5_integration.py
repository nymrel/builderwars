from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None


MODULE_PATH = Path(__file__).with_name("sightline.py")
SPEC = importlib.util.spec_from_file_location("sightline_opencv5_integration", MODULE_PATH)
assert SPEC and SPEC.loader
sightline = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sightline
SPEC.loader.exec_module(sightline)


def _canvas() -> np.ndarray:
    return np.zeros((20, 20, 3), dtype=np.uint8)


@unittest.skipUnless(cv2 is not None and np is not None, "pinned OpenCV 5 environment required")
class OfficialOpenCV5IntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertEqual(cv2.__version__, "5.0.0")
        self.perception = sightline.OpenCV5Perception(cv2)

    def _analyze(self, baseline: np.ndarray, candidate: np.ndarray):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline_path = root / "baseline.png"
            candidate_path = root / "candidate.png"
            self.assertTrue(cv2.imwrite(str(baseline_path), baseline))
            self.assertTrue(cv2.imwrite(str(candidate_path), candidate))
            return self.perception.analyze_files(baseline_path, candidate_path)

    def _assert_approval(self, findings) -> None:
        trace = sightline.SightlineAgent().plan(findings)
        self.assertEqual(trace.action, "request_human_approval")
        self.assertTrue(trace.human_approval_required)
        self.assertFalse(trace.execution_authorized)
        self.assertFalse(trace.aws_invoked)

    def test_missing_region(self) -> None:
        baseline = _canvas()
        candidate = _canvas()
        baseline[4:10, 4:10] = 255
        findings = self._analyze(baseline, candidate)
        self.assertEqual([finding.kind for finding in findings], ["missing_region"])
        self._assert_approval(findings)

    def test_unexpected_region(self) -> None:
        baseline = _canvas()
        candidate = _canvas()
        candidate[4:10, 4:10] = 255
        findings = self._analyze(baseline, candidate)
        self.assertEqual([finding.kind for finding in findings], ["unexpected_region"])
        self._assert_approval(findings)

    def test_layout_shift(self) -> None:
        baseline = _canvas()
        candidate = _canvas()
        baseline[4:10, 2:8] = 255
        candidate[4:10, 12:18] = 255
        findings = self._analyze(baseline, candidate)
        self.assertEqual(
            [finding.kind for finding in findings],
            ["layout_shift", "layout_shift"],
        )
        self._assert_approval(findings)


if __name__ == "__main__":
    unittest.main()
