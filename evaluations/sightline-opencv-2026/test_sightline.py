from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np


MODULE_PATH = Path(__file__).with_name("sightline.py")
SPEC = importlib.util.spec_from_file_location("sightline_stage1", MODULE_PATH)
assert SPEC and SPEC.loader
sightline = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sightline
SPEC.loader.exec_module(sightline)


class FakeCV2:
    __version__ = "5.0.0-test-double"
    IMREAD_COLOR = 1
    COLOR_BGR2GRAY = 6
    THRESH_BINARY = 0
    CC_STAT_LEFT = 0
    CC_STAT_TOP = 1
    CC_STAT_WIDTH = 2
    CC_STAT_HEIGHT = 3
    CC_STAT_AREA = 4

    def __init__(self, images: dict[str, np.ndarray]) -> None:
        self.images = images

    def imread(self, path: str, _: int) -> np.ndarray | None:
        image = self.images.get(path)
        return None if image is None else image.copy()

    @staticmethod
    def absdiff(left: np.ndarray, right: np.ndarray) -> np.ndarray:
        return np.abs(left.astype(np.int16) - right.astype(np.int16)).astype(np.uint8)

    @staticmethod
    def cvtColor(image: np.ndarray, _: int) -> np.ndarray:
        return image.max(axis=2)

    @staticmethod
    def threshold(image: np.ndarray, threshold: int, maximum: int, _: int):
        return threshold, np.where(image > threshold, maximum, 0).astype(np.uint8)

    @classmethod
    def connectedComponentsWithStats(cls, mask: np.ndarray, _: int):
        height, width = mask.shape
        labels = np.zeros((height, width), dtype=np.int32)
        stats = [[0, 0, width, height, int((mask == 0).sum())]]
        centroids = [[0.0, 0.0]]
        next_label = 1
        for start_y in range(height):
            for start_x in range(width):
                if mask[start_y, start_x] == 0 or labels[start_y, start_x] != 0:
                    continue
                stack = [(start_x, start_y)]
                pixels = []
                labels[start_y, start_x] = next_label
                while stack:
                    x, y = stack.pop()
                    pixels.append((x, y))
                    for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                        if (
                            0 <= nx < width
                            and 0 <= ny < height
                            and mask[ny, nx] != 0
                            and labels[ny, nx] == 0
                        ):
                            labels[ny, nx] = next_label
                            stack.append((nx, ny))
                xs = [pixel[0] for pixel in pixels]
                ys = [pixel[1] for pixel in pixels]
                stats.append(
                    [min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1, len(pixels)]
                )
                centroids.append([sum(xs) / len(xs), sum(ys) / len(ys)])
                next_label += 1
        return next_label, labels, np.asarray(stats), np.asarray(centroids)


class OldCV2:
    __version__ = "4.99.0"


def canvas() -> np.ndarray:
    return np.zeros((20, 20, 3), dtype=np.uint8)


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
            sightline.OpenCV5Perception(OldCV2())

    def test_invalid_finding_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            sightline.VisualFinding("visual_change", "low", (0, 0, 1, 1), 11, 10)

    def test_generated_missing_region_fixture(self) -> None:
        baseline = canvas()
        baseline[4:8, 4:8] = 255
        adapter = sightline.OpenCV5Perception(FakeCV2({"base": baseline, "candidate": canvas()}))
        findings = adapter.analyze_files("base", "candidate")
        self.assertEqual([finding.kind for finding in findings], ["missing_region"])
        self.assertEqual(findings[0].bbox_xywh, (4, 4, 4, 4))

    def test_generated_unexpected_region_fixture(self) -> None:
        candidate = canvas()
        candidate[4:8, 4:8] = 255
        adapter = sightline.OpenCV5Perception(FakeCV2({"base": canvas(), "candidate": candidate}))
        findings = adapter.analyze_files("base", "candidate")
        self.assertEqual([finding.kind for finding in findings], ["unexpected_region"])

    def test_generated_layout_shift_fixture_requires_approval(self) -> None:
        baseline = canvas()
        candidate = canvas()
        baseline[3:7, 3:7] = 255
        candidate[12:16, 12:16] = 255
        adapter = sightline.OpenCV5Perception(FakeCV2({"base": baseline, "candidate": candidate}))
        findings = adapter.analyze_files("base", "candidate")
        self.assertEqual({finding.kind for finding in findings}, {"layout_shift"})
        trace = sightline.SightlineAgent().plan(findings)
        self.assertEqual(trace.action, "request_human_approval")
        self.assertFalse(trace.execution_authorized)
        self.assertFalse(trace.aws_invoked)


if __name__ == "__main__":
    unittest.main()
