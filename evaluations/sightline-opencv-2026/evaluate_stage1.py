"""Deterministic, offline quality baseline for the Sightline Stage 1 adapter."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from typing import Any, Literal

import cv2
import numpy as np


MODULE_PATH = Path(__file__).with_name("sightline.py")
SPEC = importlib.util.spec_from_file_location("sightline_evaluation_core", MODULE_PATH)
assert SPEC and SPEC.loader
sightline = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sightline
SPEC.loader.exec_module(sightline)


@dataclass(frozen=True)
class CaseResult:
    name: str
    expected_kinds: tuple[str, ...]
    observed_kinds: tuple[str, ...]
    action: str
    human_approval_required: bool
    findings_sha256: str
    passed: bool


@dataclass(frozen=True)
class FailureControl:
    name: str
    expected_error: str
    observed_error: str
    passed: bool


def _canvas(height: int = 20, width: int = 20) -> np.ndarray:
    return np.zeros((height, width, 3), dtype=np.uint8)


def _write(path: Path, image: np.ndarray) -> None:
    if not cv2.imwrite(str(path), image):
        raise RuntimeError(f"failed to write generated fixture: {path.name}")


def _evaluate_case(
    root: Path,
    perception: Any,
    name: str,
    baseline: np.ndarray,
    candidate: np.ndarray,
    expected_kinds: tuple[str, ...],
) -> CaseResult:
    baseline_path = root / f"{name}-baseline.png"
    candidate_path = root / f"{name}-candidate.png"
    _write(baseline_path, baseline)
    _write(candidate_path, candidate)
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
    return CaseResult(
        name=name,
        expected_kinds=expected_kinds,
        observed_kinds=observed_kinds,
        action=trace.action,
        human_approval_required=trace.human_approval_required,
        findings_sha256=trace.findings_sha256,
        passed=passed,
    )


def _expect_failure(name: str, expected_error: str, callback: Any) -> FailureControl:
    try:
        callback()
    except ValueError as exc:
        observed_error = str(exc)
        return FailureControl(
            name=name,
            expected_error=expected_error,
            observed_error=observed_error,
            passed=observed_error == expected_error,
        )
    return FailureControl(name, expected_error, "no error", False)


def evaluate() -> dict[str, Any]:
    if cv2.__version__ != "5.0.0":
        raise RuntimeError(f"exact OpenCV 5.0.0 required; observed {cv2.__version__}")

    perception = sightline.OpenCV5Perception(cv2)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)

        missing_baseline = _canvas()
        missing_baseline[4:10, 4:10] = 255
        missing_candidate = _canvas()

        unexpected_baseline = _canvas()
        unexpected_candidate = _canvas()
        unexpected_candidate[4:10, 4:10] = 255

        shift_baseline = _canvas()
        shift_candidate = _canvas()
        shift_baseline[4:10, 2:8] = 255
        shift_candidate[4:10, 12:18] = 255

        cases = [
            _evaluate_case(
                root,
                perception,
                "missing_region",
                missing_baseline,
                missing_candidate,
                ("missing_region",),
            ),
            _evaluate_case(
                root,
                perception,
                "unexpected_region",
                unexpected_baseline,
                unexpected_candidate,
                ("unexpected_region",),
            ),
            _evaluate_case(
                root,
                perception,
                "layout_shift",
                shift_baseline,
                shift_candidate,
                ("layout_shift", "layout_shift"),
            ),
        ]

        readable = root / "readable.png"
        mismatched = root / "mismatched.png"
        _write(readable, _canvas())
        _write(mismatched, _canvas(21, 20))
        failures = [
            _expect_failure(
                "unreadable_input",
                "both images must be readable",
                lambda: perception.analyze_files(root / "absent.png", readable),
            ),
            _expect_failure(
                "dimension_mismatch",
                "images must have identical dimensions",
                lambda: perception.analyze_files(readable, mismatched),
            ),
        ]

    task_passes = sum(case.passed for case in cases)
    failure_passes = sum(control.passed for control in failures)
    all_passed = task_passes == len(cases) and failure_passes == len(failures)
    return {
        "schema": "sightline.evaluation.v1",
        "runtime": {"opencv": cv2.__version__, "numpy": np.__version__},
        "scope": "generated_offline_stage1_only",
        "task_success": {
            "passed": task_passes,
            "total": len(cases),
            "rate": task_passes / len(cases),
        },
        "failure_controls": {
            "passed": failure_passes,
            "total": len(failures),
            "rate": failure_passes / len(failures),
        },
        "cases": [asdict(case) for case in cases],
        "failures": [asdict(control) for control in failures],
        "all_passed": all_passed,
        "execution_authorized": False,
        "aws_invoked": False,
    }


def main() -> int:
    result = evaluate()
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
