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


class Image:
    def __init__(self, height: int, width: int, pixels=None) -> None:
        self.pixels = pixels or [
            [[0, 0, 0] for _ in range(width)] for _ in range(height)
        ]

    @property
    def shape(self) -> tuple[int, int, int]:
        return (len(self.pixels), len(self.pixels[0]), 3)

    def copy(self):
        return Image(
            self.shape[0],
            self.shape[1],
            [[pixel[:] for pixel in row] for row in self.pixels],
        )

    def astype(self, _: str):
        return self.copy()

    def __getitem__(self, key):
        y_slice, x_slice = key
        rows = self.pixels[y_slice]
        cropped = [[pixel[:] for pixel in row[x_slice]] for row in rows]
        return Image(len(cropped), len(cropped[0]), cropped)

    def __setitem__(self, key, value: int) -> None:
        y_slice, x_slice = key
        y_range = range(*y_slice.indices(self.shape[0]))
        x_range = range(*x_slice.indices(self.shape[1]))
        for y in y_range:
            for x in x_range:
                self.pixels[y][x] = [value, value, value]

    def __sub__(self, other):
        pixels = []
        for left_row, right_row in zip(self.pixels, other.pixels, strict=True):
            pixels.append(
                [
                    [left - right for left, right in zip(left_pixel, right_pixel, strict=True)]
                    for left_pixel, right_pixel in zip(left_row, right_row, strict=True)
                ]
            )
        return Image(self.shape[0], self.shape[1], pixels)

    def mean(self) -> float:
        values = [value for row in self.pixels for pixel in row for value in pixel]
        return sum(values) / len(values)


class Mask:
    def __init__(self, pixels: list[list[int]]) -> None:
        self.pixels = pixels

    @property
    def shape(self) -> tuple[int, int]:
        return (len(self.pixels), len(self.pixels[0]))


class Stats:
    def __init__(self, rows: list[list[int]]) -> None:
        self.rows = rows

    def __getitem__(self, key) -> int:
        row, column = key
        return self.rows[row][column]


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

    def __init__(self, images: dict[str, Image]) -> None:
        self.images = images

    def imread(self, path: str, _: int):
        image = self.images.get(path)
        return None if image is None else image.copy()

    @staticmethod
    def absdiff(left: Image, right: Image) -> Image:
        pixels = []
        for left_row, right_row in zip(left.pixels, right.pixels, strict=True):
            pixels.append(
                [
                    [abs(a - b) for a, b in zip(x, y, strict=True)]
                    for x, y in zip(left_row, right_row, strict=True)
                ]
            )
        return Image(left.shape[0], left.shape[1], pixels)

    @staticmethod
    def cvtColor(image: Image, _: int) -> Mask:
        return Mask([[max(pixel) for pixel in row] for row in image.pixels])

    @staticmethod
    def threshold(image: Mask, threshold: int, maximum: int, _: int):
        mask = Mask(
            [[maximum if value > threshold else 0 for value in row] for row in image.pixels]
        )
        return threshold, mask

    @classmethod
    def connectedComponentsWithStats(cls, mask: Mask, _: int):
        height, width = mask.shape
        labels = [[0 for _ in range(width)] for _ in range(height)]
        rows = [[0, 0, width, height, sum(value == 0 for row in mask.pixels for value in row)]]
        centroids = [[0.0, 0.0]]
        next_label = 1
        for start_y in range(height):
            for start_x in range(width):
                if mask.pixels[start_y][start_x] == 0 or labels[start_y][start_x] != 0:
                    continue
                stack = [(start_x, start_y)]
                pixels = []
                labels[start_y][start_x] = next_label
                while stack:
                    x, y = stack.pop()
                    pixels.append((x, y))
                    for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                        if (
                            0 <= nx < width
                            and 0 <= ny < height
                            and mask.pixels[ny][nx] != 0
                            and labels[ny][nx] == 0
                        ):
                            labels[ny][nx] = next_label
                            stack.append((nx, ny))
                xs = [pixel[0] for pixel in pixels]
                ys = [pixel[1] for pixel in pixels]
                rows.append(
                    [min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1, len(pixels)]
                )
                centroids.append([sum(xs) / len(xs), sum(ys) / len(ys)])
                next_label += 1
        return next_label, labels, Stats(rows), centroids


class OldCV2:
    __version__ = "4.99.0"


def canvas() -> Image:
    return Image(20, 20)


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

    def test_fragmented_material_change_requires_human_approval(self) -> None:
        left = sightline.VisualFinding(
            "missing_region", "low", (0, 0, 4, 4), 11, 1000
        )
        right = sightline.VisualFinding(
            "missing_region", "low", (10, 0, 4, 4), 11, 1000
        )
        trace = sightline.SightlineAgent().plan([left, right])
        self.assertEqual(trace.action, "request_human_approval")
        self.assertTrue(trace.human_approval_required)

    def test_isolated_low_risk_change_remains_accepted(self) -> None:
        finding = sightline.VisualFinding(
            "visual_change", "low", (0, 0, 2, 2), 4, 1000
        )
        trace = sightline.SightlineAgent().plan([finding])
        self.assertEqual(trace.action, "accept_no_material_change")
        self.assertFalse(trace.human_approval_required)

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
