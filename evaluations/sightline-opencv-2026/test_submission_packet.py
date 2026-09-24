from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile
import unittest


MODULE_PATH = Path(__file__).with_name("verify_submission_packet.py")
SPEC = importlib.util.spec_from_file_location("sightline_packet_verifier", MODULE_PATH)
assert SPEC and SPEC.loader
verifier = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = verifier
SPEC.loader.exec_module(verifier)


class SubmissionPacketVerifierTests(unittest.TestCase):
    def test_current_packet_is_allowlisted_and_draft_only(self) -> None:
        receipt = verifier.verify_packet()
        self.assertEqual(receipt["status"], "draft_not_submitted")
        self.assertEqual(
            [entry["path"] for entry in receipt["files"]],
            list(verifier.ALLOWED_FILES),
        )
        self.assertEqual(receipt["secret_pattern_matches"], 0)
        self.assertEqual(receipt["local_path_matches"], 0)
        self.assertFalse(receipt["publication_authorized"])
        self.assertFalse(receipt["submission_authorized"])

    def test_rejects_sensitive_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in verifier.ALLOWED_FILES:
                shutil.copy2(verifier.PACKET_ROOT / name, root / name)
            target = root / verifier.ALLOWED_FILES[0]
            target.write_text(
                target.read_text(encoding="utf-8")
                + "\n-----BEGIN PRIVATE KEY-----\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "sensitive pattern"):
                verifier.verify_packet(root)

    def test_rejects_unexpected_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in verifier.ALLOWED_FILES:
                shutil.copy2(verifier.PACKET_ROOT / name, root / name)
            (root / "private-notes.md").write_text(
                "# Draft, Not Submitted\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "allowlist mismatch"):
                verifier.verify_packet(root)


if __name__ == "__main__":
    unittest.main()
