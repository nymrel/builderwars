"""Build a deterministic, synthetic-only Sightline demo review bundle."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parent
PACKET_ROOT = ROOT / "submission-packet"
BUNDLE_NAME = "sightline-demo-review.zip"
ZIP_TIMESTAMP = (2026, 1, 1, 0, 0, 0)


def _load_sightline():
    path = ROOT / "sightline.py"
    spec = importlib.util.spec_from_file_location("sightline_demo_core", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _png(image: np.ndarray) -> bytes:
    encoded, payload = cv2.imencode(".png", image, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    if not encoded:
        raise RuntimeError("failed to encode synthetic PNG")
    return payload.tobytes()


def _canvas() -> np.ndarray:
    image = np.full((360, 640, 3), (248, 250, 252), dtype=np.uint8)
    cv2.rectangle(image, (40, 36), (600, 324), (226, 232, 240), 2)
    cv2.putText(
        image,
        "SIGHTLINE SYNTHETIC FIXTURE",
        (70, 76),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.72,
        (30, 41, 59),
        2,
        cv2.LINE_8,
    )
    return image


def _fixtures() -> dict[str, tuple[np.ndarray, np.ndarray, tuple[str, ...]]]:
    missing_baseline = _canvas()
    missing_candidate = _canvas()
    cv2.rectangle(missing_baseline, (150, 125), (490, 255), (79, 70, 229), -1)

    unexpected_baseline = _canvas()
    unexpected_candidate = _canvas()
    cv2.rectangle(unexpected_candidate, (150, 125), (490, 255), (14, 165, 233), -1)

    shift_baseline = _canvas()
    shift_candidate = _canvas()
    cv2.rectangle(shift_baseline, (90, 130), (270, 250), (16, 185, 129), -1)
    cv2.rectangle(shift_candidate, (370, 130), (550, 250), (16, 185, 129), -1)

    return {
        "layout-shift": (shift_baseline, shift_candidate, ("layout_shift", "layout_shift")),
        "missing-region": (missing_baseline, missing_candidate, ("missing_region",)),
        "unexpected-region": (
            unexpected_baseline,
            unexpected_candidate,
            ("unexpected_region",),
        ),
    }


def _digest(payload: bytes) -> str:
    return sha256(payload).hexdigest()


def _json(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build_demo_bundle(output_dir: Path) -> dict[str, Any]:
    if cv2.__version__ != "5.0.0":
        raise RuntimeError(f"exact OpenCV 5.0.0 required; observed {cv2.__version__}")
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / BUNDLE_NAME
    sightline = _load_sightline()
    perception = sightline.OpenCV5Perception(cv2)
    files: dict[str, bytes] = {
        "architecture.svg": (PACKET_ROOT / "ARCHITECTURE.draft.svg").read_bytes(),
        "README.txt": (
            "Sightline Demo Review Bundle — Draft, Not Submitted\n"
            "Synthetic fixtures only. Private review use only.\n"
            "No browser data, credentials, AWS execution, publication, or submission authority.\n"
        ).encode("utf-8"),
    }
    case_receipts: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as directory:
        temp_root = Path(directory)
        for name, (baseline, candidate, expected_kinds) in _fixtures().items():
            baseline_bytes = _png(baseline)
            candidate_bytes = _png(candidate)
            baseline_name = f"fixtures/{name}-baseline.png"
            candidate_name = f"fixtures/{name}-candidate.png"
            files[baseline_name] = baseline_bytes
            files[candidate_name] = candidate_bytes
            baseline_path = temp_root / f"{name}-baseline.png"
            candidate_path = temp_root / f"{name}-candidate.png"
            baseline_path.write_bytes(baseline_bytes)
            candidate_path.write_bytes(candidate_bytes)
            findings = perception.analyze_files(baseline_path, candidate_path)
            trace = sightline.SightlineAgent().plan(findings)
            observed_kinds = tuple(finding.kind for finding in findings)
            passed = (
                observed_kinds == expected_kinds
                and trace.action == "request_human_approval"
                and trace.human_approval_required
                and not trace.execution_authorized
                and not trace.aws_invoked
            )
            case_receipts.append(
                {
                    "name": name,
                    "source": "generated_synthetic",
                    "baseline": {
                        "path": baseline_name,
                        "bytes": len(baseline_bytes),
                        "sha256": _digest(baseline_bytes),
                    },
                    "candidate": {
                        "path": candidate_name,
                        "bytes": len(candidate_bytes),
                        "sha256": _digest(candidate_bytes),
                    },
                    "expected_kinds": list(expected_kinds),
                    "observed_kinds": list(observed_kinds),
                    "decision": asdict(trace),
                    "passed": passed,
                }
            )

    evaluation = {
        "schema": "sightline.demo-evaluation.v1",
        "runtime": {"opencv": cv2.__version__, "numpy": np.__version__},
        "scope": "synthetic_private_demo_review_only",
        "cases": case_receipts,
        "all_passed": all(case["passed"] for case in case_receipts),
        "synthetic_only": True,
        "browser_data_included": False,
        "network_invoked": False,
        "aws_invoked": False,
        "execution_authorized": False,
        "publication_authorized": False,
        "submission_authorized": False,
    }
    if not evaluation["all_passed"]:
        raise RuntimeError("synthetic demo evaluation did not pass")
    files["evaluation.json"] = _json(evaluation)
    manifest = {
        "schema": "sightline.demo-manifest.v1",
        "status": "draft_not_submitted",
        "source_policy": "generated_synthetic_and_tracked_nymrel_asset_only",
        "files": [
            {"path": name, "bytes": len(payload), "sha256": _digest(payload)}
            for name, payload in sorted(files.items())
        ],
        "synthetic_only": True,
        "browser_data_included": False,
        "credentials_included": False,
        "publication_authorized": False,
        "submission_authorized": False,
    }
    files["manifest.json"] = _json(manifest)

    with ZipFile(archive_path, "w") as archive:
        for name, payload in sorted(files.items()):
            info = ZipInfo(name, ZIP_TIMESTAMP)
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payload, compress_type=ZIP_DEFLATED, compresslevel=9)

    archive_bytes = archive_path.read_bytes()
    return {
        "schema": "sightline.demo-bundle-receipt.v1",
        "status": "draft_not_submitted",
        "bundle_name": BUNDLE_NAME,
        "bundle_bytes": len(archive_bytes),
        "bundle_sha256": _digest(archive_bytes),
        "files": sorted(files),
        "case_count": len(case_receipts),
        "all_passed": True,
        "synthetic_only": True,
        "browser_data_included": False,
        "network_invoked": False,
        "aws_invoked": False,
        "execution_authorized": False,
        "artifact_uploaded": False,
        "publication_authorized": False,
        "submission_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build_demo_bundle(args.output_dir), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
