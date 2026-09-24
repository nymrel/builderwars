from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from zipfile import ZipFile

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None


MODULE_PATH = Path(__file__).with_name("build_demo_bundle.py")
SPEC = importlib.util.spec_from_file_location("sightline_demo_bundle", MODULE_PATH)
assert SPEC and SPEC.loader
builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = builder
SPEC.loader.exec_module(builder)


@unittest.skipUnless(cv2 is not None and np is not None, "pinned OpenCV 5 environment required")
class DemoBundleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertEqual(cv2.__version__, "5.0.0")

    def test_receipt_is_synthetic_and_non_authorizing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = builder.build_demo_bundle(root)
            self.assertTrue(receipt["all_passed"])
            self.assertTrue(receipt["synthetic_only"])
            self.assertFalse(receipt["browser_data_included"])
            self.assertFalse(receipt["network_invoked"])
            self.assertFalse(receipt["aws_invoked"])
            self.assertFalse(receipt["execution_authorized"])
            self.assertFalse(receipt["artifact_uploaded"])
            self.assertFalse(receipt["publication_authorized"])
            self.assertFalse(receipt["submission_authorized"])
            self.assertNotIn(str(root), json.dumps(receipt))

    def test_bundle_contains_only_allowlisted_review_assets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            builder.build_demo_bundle(root)
            with ZipFile(root / builder.BUNDLE_NAME) as archive:
                names = archive.namelist()
                self.assertEqual(names, sorted(names))
                self.assertEqual(len(names), 10)
                self.assertEqual(
                    set(names),
                    {
                        "README.txt",
                        "architecture.svg",
                        "evaluation.json",
                        "fixtures/layout-shift-baseline.png",
                        "fixtures/layout-shift-candidate.png",
                        "fixtures/missing-region-baseline.png",
                        "fixtures/missing-region-candidate.png",
                        "fixtures/unexpected-region-baseline.png",
                        "fixtures/unexpected-region-candidate.png",
                        "manifest.json",
                    },
                )
                manifest = json.loads(archive.read("manifest.json"))
                self.assertEqual(manifest["status"], "draft_not_submitted")
                self.assertTrue(manifest["synthetic_only"])
                self.assertFalse(manifest["credentials_included"])
                self.assertFalse(manifest["publication_authorized"])
                self.assertFalse(manifest["submission_authorized"])

    def test_bundle_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_receipt = builder.build_demo_bundle(Path(first))
            second_receipt = builder.build_demo_bundle(Path(second))
            self.assertEqual(first_receipt["bundle_bytes"], second_receipt["bundle_bytes"])
            self.assertEqual(first_receipt["bundle_sha256"], second_receipt["bundle_sha256"])


if __name__ == "__main__":
    unittest.main()
