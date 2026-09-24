from __future__ import annotations

from hashlib import sha256
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from zipfile import ZipFile


MODULE_PATH = Path(__file__).with_name("build_aws_artifact.py")
SPEC = importlib.util.spec_from_file_location("sightline_build_artifact", MODULE_PATH)
assert SPEC and SPEC.loader
build = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = build
SPEC.loader.exec_module(build)


class BuildAWSArtifactTests(unittest.TestCase):
    def test_build_is_deterministic_and_non_executable(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            left = build.build_artifact(Path(first), environment={})
            right = build.build_artifact(Path(second), environment={})
            left_path = Path(left["artifact_path"])
            right_path = Path(right["artifact_path"])
            self.assertEqual(left_path.read_bytes(), right_path.read_bytes())
            self.assertEqual(
                sha256(left_path.read_bytes()).hexdigest(),
                left["plan"]["artifact_sha256"],
            )
            self.assertEqual(left["files"], list(build.FILES))
            self.assertFalse(left["plan"]["execute"])
            self.assertFalse(left["plan"]["credentials_available"])
            self.assertFalse(left["plan"]["deployment_authorized"])
            self.assertFalse(left["plan"]["spend_authorized"])
            self.assertFalse(left["network_invoked"])
            self.assertFalse(left["artifact_uploaded"])
            with ZipFile(left_path) as archive:
                self.assertEqual(archive.namelist(), list(build.FILES))
                self.assertTrue(
                    all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist())
                )

    def test_build_rejects_credential_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(PermissionError, "AWS_ACCESS_KEY_ID"):
                build.build_artifact(
                    Path(directory),
                    environment={"AWS_ACCESS_KEY_ID": "not-disclosed"},
                )


if __name__ == "__main__":
    unittest.main()
