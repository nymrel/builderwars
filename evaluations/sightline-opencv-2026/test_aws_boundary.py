from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = Path(__file__).with_name("aws_boundary.py")
SPEC = importlib.util.spec_from_file_location("sightline_aws_boundary", MODULE_PATH)
assert SPEC and SPEC.loader
aws_boundary = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = aws_boundary
SPEC.loader.exec_module(aws_boundary)


class InertAWSBoundaryTests(unittest.TestCase):
    def test_prepares_non_executable_lambda_plan(self) -> None:
        plan = aws_boundary.InertAWSBoundary().prepare_plan(
            artifact_name="sightline-stage1.zip",
            artifact_sha256="a" * 64,
            artifact_bytes=4096,
        )
        self.assertEqual(plan.schema, "sightline.aws-plan.v1")
        self.assertEqual(plan.service, "lambda")
        self.assertEqual(plan.operation, "prepare_only")
        self.assertFalse(plan.execute)
        self.assertFalse(plan.credentials_available)
        self.assertFalse(plan.deployment_authorized)
        self.assertFalse(plan.spend_authorized)

    def test_rejects_any_authority_flag(self) -> None:
        for field in (
            "credentials_available",
            "deployment_authorized",
            "spend_authorized",
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(PermissionError, "authority flags"):
                    aws_boundary.InertAWSBoundary(**{field: True})

    def test_rejects_credential_bearing_environment_without_value_disclosure(self) -> None:
        secret = "must-not-appear"
        with self.assertRaises(PermissionError) as caught:
            aws_boundary.InertAWSBoundary.assert_credential_free(
                {"AWS_SECRET_ACCESS_KEY": secret}
            )
        self.assertIn("AWS_SECRET_ACCESS_KEY", str(caught.exception))
        self.assertNotIn(secret, str(caught.exception))

    def test_accepts_credential_free_environment(self) -> None:
        aws_boundary.InertAWSBoundary.assert_credential_free(
            {"AWS_DEFAULT_REGION": "us-west-2", "CI": "true"}
        )

    def test_rejects_invalid_artifact_inputs(self) -> None:
        boundary = aws_boundary.InertAWSBoundary()
        cases = (
            {"artifact_name": "../escape.zip", "artifact_sha256": "a" * 64, "artifact_bytes": 1},
            {"artifact_name": "safe.zip", "artifact_sha256": "A" * 64, "artifact_bytes": 1},
            {"artifact_name": "safe.zip", "artifact_sha256": "a" * 64, "artifact_bytes": 0},
            {"artifact_name": "safe.zip", "artifact_sha256": "a" * 64, "artifact_bytes": 52428801},
        )
        for case in cases:
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    boundary.prepare_plan(**case)

    def test_rejects_region_outside_allowlist(self) -> None:
        with self.assertRaisesRegex(ValueError, "allowlist"):
            aws_boundary.InertAWSBoundary().prepare_plan(
                artifact_name="safe.zip",
                artifact_sha256="0" * 64,
                artifact_bytes=128,
                region="us-east-1",
            )


if __name__ == "__main__":
    unittest.main()
