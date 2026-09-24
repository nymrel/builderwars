"""Build a deterministic, review-only Sightline Lambda source artifact."""

from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Mapping
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parent
FILES = (
    "aws_lambda_handler.py",
    "sightline.py",
    "aws_boundary.py",
    "requirements-opencv5-linux-x86_64-py312.txt",
)
ARTIFACT_NAME = "sightline-stage1-lambda.zip"


def _load_boundary():
    path = ROOT / "aws_boundary.py"
    spec = importlib.util.spec_from_file_location("sightline_build_boundary", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_artifact(
    output_dir: Path,
    *,
    environment: Mapping[str, str] | None = None,
) -> dict[str, object]:
    boundary_module = _load_boundary()
    boundary = boundary_module.InertAWSBoundary()
    boundary.assert_credential_free(os.environ if environment is None else environment)

    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / ARTIFACT_NAME
    with ZipFile(
        artifact,
        mode="w",
        compression=ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=True,
    ) as archive:
        for name in FILES:
            source = ROOT / name
            if not source.is_file():
                raise FileNotFoundError(f"required artifact source missing: {name}")
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes(), compress_type=ZIP_DEFLATED, compresslevel=9)

    digest = sha256(artifact.read_bytes()).hexdigest()
    plan = boundary.prepare_plan(
        artifact_name=ARTIFACT_NAME,
        artifact_sha256=digest,
        artifact_bytes=artifact.stat().st_size,
    )
    return {
        "schema": "sightline.aws-artifact-receipt.v1",
        "files": list(FILES),
        "artifact_path": str(artifact),
        "plan": plan.as_dict(),
        "network_invoked": False,
        "artifact_uploaded": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build_artifact(args.output_dir), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
