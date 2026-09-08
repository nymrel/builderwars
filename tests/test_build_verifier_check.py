import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_verifier_check', ROOT / 'bin' / 'build_verifier.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class VerifierCheckTests(unittest.TestCase):
    def test_check_rejects_stale_without_overwriting(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'verify.py'
            output.write_bytes(b'stale artifact\n')
            with patch.object(builder, 'OUT', str(output)):
                with self.assertRaisesRegex(SystemExit, 'stale'):
                    builder.build(builder.DEFAULT_BASE, check_only=True)
            self.assertEqual(output.read_bytes(), b'stale artifact\n')

    def test_check_accepts_generated_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'verify.py'
            with patch.object(builder, 'OUT', str(output)):
                builder.build(builder.DEFAULT_BASE)
                before = output.read_bytes()
                with patch.object(builder.os, 'replace', side_effect=AssertionError('check wrote output')):
                    builder.build(builder.DEFAULT_BASE, check_only=True)
            self.assertEqual(output.read_bytes(), before)

    def test_check_missing_does_not_create_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'verify.py'
            with patch.object(builder, 'OUT', str(output)):
                with self.assertRaisesRegex(SystemExit, 'stale'):
                    builder.build(builder.DEFAULT_BASE, check_only=True)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
