from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin"
sys.path.insert(0, str(BIN))

from entrant_admission import (  # noqa: E402
    EntrantAdmissionError,
    classify_entry,
    require_entry_admission,
    unconfined_warning,
)


class EntrantAdmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "repo"
        self.bundled = self.root / "entrants"
        self.bundled.mkdir(parents=True)
        self.bundled_script = self.bundled / "bundled.py"
        self.bundled_script.write_text("print('bundled')\n", encoding="utf-8")
        self.external_script = Path(self.temporary.name) / "external.py"
        self.external_script.write_text("print('external')\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_bundled_entry_is_admitted_without_override(self) -> None:
        records = require_entry_admission(
            [str(self.bundled_script)],
            repository_root=self.root,
        )
        self.assertEqual(records[0]["classification"], "bundled-first-party")
        self.assertEqual(records[0]["repository_path"], os.path.join("entrants", "bundled.py"))
        self.assertIsNone(unconfined_warning(records))

    def test_external_entry_is_refused_by_default(self) -> None:
        with self.assertRaisesRegex(
            EntrantAdmissionError,
            "--allow-unconfined-entrants",
        ):
            require_entry_admission(
                [str(self.external_script)],
                repository_root=self.root,
            )

    def test_external_entry_requires_explicit_owned_host_override(self) -> None:
        records = require_entry_admission(
            [str(self.external_script)],
            repository_root=self.root,
            allow_unconfined=True,
        )
        self.assertEqual(records[0]["classification"], "external-unconfined")
        warning = unconfined_warning(records)
        self.assertIsNotNone(warning)
        assert warning is not None
        self.assertIn("does not block", warning)

    def test_missing_and_directory_paths_are_refused(self) -> None:
        with self.assertRaisesRegex(EntrantAdmissionError, "existing file"):
            classify_entry(
                "missing.py",
                repository_root=self.root,
                working_directory=self.root,
            )
        with self.assertRaisesRegex(EntrantAdmissionError, "not a file"):
            classify_entry(
                str(self.bundled),
                repository_root=self.root,
            )

    def test_string_prefix_sibling_is_not_mistaken_for_bundled(self) -> None:
        sibling = self.root / "entrants-elsewhere" / "lookalike.py"
        sibling.parent.mkdir()
        sibling.write_text("print('outside')\n", encoding="utf-8")
        record = classify_entry(str(sibling), repository_root=self.root)
        self.assertEqual(record["classification"], "external-unconfined")

    def test_symlink_inside_bundled_tree_resolving_outside_is_untrusted(self) -> None:
        link = self.bundled / "outside-link.py"
        try:
            link.symlink_to(self.external_script)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation is unavailable on this platform")
        record = classify_entry(str(link), repository_root=self.root)
        self.assertEqual(record["classification"], "external-unconfined")

    def test_shipped_clis_wire_the_guard_and_override(self) -> None:
        for name in ("run_match.py", "run_series.py"):
            source = (BIN / name).read_text(encoding="utf-8")
            self.assertIn("require_entry_admission(", source)
            self.assertIn("--allow-unconfined-entrants", source)
            self.assertIn("unconfined_warning", source)

    def test_run_match_refuses_external_entries_before_execution(self) -> None:
        output_directory = Path(self.temporary.name) / "matches"
        completed = subprocess.run(
            [
                sys.executable,
                str(BIN / "run_match.py"),
                "--seed",
                "1",
                "--entrant",
                str(self.external_script),
                "--entrant",
                str(self.external_script),
                "--out",
                str(output_directory),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("--allow-unconfined-entrants", completed.stderr)
        self.assertFalse(output_directory.exists())


if __name__ == "__main__":
    unittest.main()
