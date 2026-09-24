from __future__ import annotations

import base64
import importlib.util
from pathlib import Path
import sys
import unittest

import cv2
import numpy as np


MODULE_PATH = Path(__file__).with_name("aws_lambda_handler.py")
SPEC = importlib.util.spec_from_file_location("sightline_lambda_handler", MODULE_PATH)
assert SPEC and SPEC.loader
handler = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = handler
SPEC.loader.exec_module(handler)


def _png(image: np.ndarray) -> str:
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise RuntimeError("fixture encoding failed")
    return base64.b64encode(encoded.tobytes()).decode("ascii")


class LambdaHandlerTests(unittest.TestCase):
    def test_missing_region_returns_bounded_approval_trace(self) -> None:
        baseline = np.zeros((20, 20, 3), dtype=np.uint8)
        baseline[4:10, 4:10] = 255
        candidate = np.zeros((20, 20, 3), dtype=np.uint8)
        result = handler.lambda_handler(
            {
                "baseline_png_base64": _png(baseline),
                "candidate_png_base64": _png(candidate),
            }
        )
        self.assertEqual(result["schema"], "sightline.lambda-response.v1")
        self.assertEqual(
            [finding["kind"] for finding in result["findings"]],
            ["missing_region"],
        )
        self.assertEqual(result["decision"]["action"], "request_human_approval")
        self.assertTrue(result["decision"]["human_approval_required"])
        self.assertFalse(result["decision"]["execution_authorized"])
        self.assertFalse(result["decision"]["aws_invoked"])
        self.assertFalse(result["network_invoked"])
        self.assertFalse(result["storage_invoked"])
        self.assertFalse(result["mutation_invoked"])

    def test_rejects_invalid_base64(self) -> None:
        with self.assertRaisesRegex(ValueError, "valid base64"):
            handler.lambda_handler(
                {
                    "baseline_png_base64": "not-base64!",
                    "candidate_png_base64": "not-base64!",
                }
            )

    def test_rejects_oversized_input_before_decode(self) -> None:
        oversized = "A" * (handler.MAX_ENCODED_CHARS + 1)
        with self.assertRaisesRegex(ValueError, "1 MiB"):
            handler.lambda_handler(
                {
                    "baseline_png_base64": oversized,
                    "candidate_png_base64": oversized,
                }
            )


if __name__ == "__main__":
    unittest.main()
