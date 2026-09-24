"""Locally testable Lambda-compatible handler for Sightline.

The handler accepts two base64-encoded PNG images and returns a bounded decision trace.
It performs no network, storage, repository, or deployment operation.
"""

from __future__ import annotations

from dataclasses import asdict
import base64
import binascii
from pathlib import Path
import tempfile
from typing import Any, Mapping

try:
    from sightline import OpenCV5Perception, SightlineAgent
except ModuleNotFoundError:
    import importlib.util
    import sys

    module_path = Path(__file__).with_name("sightline.py")
    spec = importlib.util.spec_from_file_location("sightline_lambda_core", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    OpenCV5Perception = module.OpenCV5Perception
    SightlineAgent = module.SightlineAgent


MAX_IMAGE_BYTES = 1024 * 1024
MAX_ENCODED_CHARS = ((MAX_IMAGE_BYTES + 2) // 3) * 4


def _decode_png(event: Mapping[str, Any], key: str) -> bytes:
    encoded = event.get(key)
    if not isinstance(encoded, str) or not encoded:
        raise ValueError(f"{key} must be a non-empty base64 string")
    if len(encoded) > MAX_ENCODED_CHARS:
        raise ValueError(f"{key} exceeds the 1 MiB encoded-image limit")
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"{key} must contain valid base64") from exc
    if not decoded or len(decoded) > MAX_IMAGE_BYTES:
        raise ValueError(f"{key} must decode to 1..1048576 bytes")
    if not decoded.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"{key} must be a PNG image")
    return decoded


def lambda_handler(event: Mapping[str, Any], context: Any = None) -> dict[str, Any]:
    if not isinstance(event, Mapping):
        raise ValueError("event must be a mapping")

    baseline = _decode_png(event, "baseline_png_base64")
    candidate = _decode_png(event, "candidate_png_base64")

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        baseline_path = root / "baseline.png"
        candidate_path = root / "candidate.png"
        baseline_path.write_bytes(baseline)
        candidate_path.write_bytes(candidate)
        findings = OpenCV5Perception().analyze_files(baseline_path, candidate_path)

    trace = SightlineAgent().plan(findings)
    return {
        "schema": "sightline.lambda-response.v1",
        "findings": [asdict(finding) for finding in findings],
        "decision": asdict(trace),
        "network_invoked": False,
        "storage_invoked": False,
        "mutation_invoked": False,
    }
