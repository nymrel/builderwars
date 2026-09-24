"""Offline, fail-closed Sightline Stage 1 evaluation core."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable, Literal


Risk = Literal["low", "medium", "high"]
Action = Literal[
    "accept_no_material_change",
    "request_human_approval",
    "reject_unbounded_input",
]


@dataclass(frozen=True)
class VisualFinding:
    kind: Literal["missing_region", "unexpected_region", "layout_shift", "visual_change"]
    risk: Risk
    bbox_xywh: tuple[int, int, int, int]
    changed_pixels: int
    image_pixels: int

    def __post_init__(self) -> None:
        if self.changed_pixels <= 0 or self.image_pixels <= 0:
            raise ValueError("pixel counts must be positive")
        if self.changed_pixels > self.image_pixels:
            raise ValueError("changed_pixels cannot exceed image_pixels")
        if len(self.bbox_xywh) != 4 or any(value < 0 for value in self.bbox_xywh):
            raise ValueError("bbox_xywh must contain four non-negative integers")

    @property
    def changed_fraction(self) -> float:
        return self.changed_pixels / self.image_pixels


@dataclass(frozen=True)
class DecisionTrace:
    schema: Literal["sightline.decision.v1"]
    action: Action
    human_approval_required: bool
    finding_count: int
    findings_sha256: str
    execution_authorized: Literal[False] = False
    aws_invoked: Literal[False] = False


def _normalized_findings(findings: Iterable[VisualFinding]) -> list[dict[str, Any]]:
    normalized = [asdict(finding) for finding in findings]
    normalized.sort(
        key=lambda row: (
            row["risk"], row["bbox_xywh"], row["changed_pixels"], row["image_pixels"]
        )
    )
    return normalized


class SightlineAgent:
    """Deterministic proposal engine. It never performs the proposed action."""

    def __init__(
        self,
        *,
        max_findings: int = 100,
        material_changed_fraction: float = 0.02,
        material_component_count: int = 8,
    ) -> None:
        if max_findings < 1:
            raise ValueError("max_findings must be positive")
        if not 0 < material_changed_fraction <= 1:
            raise ValueError("material_changed_fraction must be between zero and one")
        if not 1 <= material_component_count <= max_findings:
            raise ValueError(
                "material_component_count must be positive and within max_findings"
            )
        self.max_findings = max_findings
        self.material_changed_fraction = material_changed_fraction
        self.material_component_count = material_component_count

    def plan(self, findings: Iterable[VisualFinding]) -> DecisionTrace:
        normalized = _normalized_findings(findings)
        digest = sha256(
            json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        if len(normalized) > self.max_findings:
            action: Action = "reject_unbounded_input"
            approval_required = False
        elif (
            any(row["risk"] in {"medium", "high"} for row in normalized)
            or sum(
                row["changed_pixels"] / row["image_pixels"] for row in normalized
            )
            >= self.material_changed_fraction
            or len(normalized) >= self.material_component_count
        ):
            action = "request_human_approval"
            approval_required = True
        else:
            action = "accept_no_material_change"
            approval_required = False

        return DecisionTrace(
            schema="sightline.decision.v1",
            action=action,
            human_approval_required=approval_required,
            finding_count=len(normalized),
            findings_sha256=digest,
        )


class OpenCV5Perception:
    """Small OpenCV 5 adapter with an explicit runtime/version boundary."""

    def __init__(self, cv2_module: Any | None = None) -> None:
        if cv2_module is None:
            try:
                import cv2 as cv2_module  # type: ignore[import-not-found]
            except ImportError as exc:
                raise RuntimeError("OpenCV 5 is required for perception") from exc

        version = str(getattr(cv2_module, "__version__", ""))
        try:
            major = int(version.split(".", 1)[0])
        except (TypeError, ValueError) as exc:
            raise RuntimeError("OpenCV runtime did not report a valid version") from exc
        if major != 5:
            raise RuntimeError(f"OpenCV 5 required; observed {version or 'unknown'}")
        self.cv2 = cv2_module

    def analyze_files(
        self,
        baseline_path: str | Path,
        candidate_path: str | Path,
        *,
        threshold: int = 24,
        min_component_pixels: int = 16,
    ) -> list[VisualFinding]:
        if not 0 <= threshold <= 255:
            raise ValueError("threshold must be between 0 and 255")
        if min_component_pixels < 1:
            raise ValueError("min_component_pixels must be positive")

        baseline = self.cv2.imread(str(baseline_path), self.cv2.IMREAD_COLOR)
        candidate = self.cv2.imread(str(candidate_path), self.cv2.IMREAD_COLOR)
        if baseline is None or candidate is None:
            raise ValueError("both images must be readable")
        if baseline.shape != candidate.shape or len(baseline.shape) < 2:
            raise ValueError("images must have identical dimensions")

        delta = self.cv2.absdiff(baseline, candidate)
        gray = self.cv2.cvtColor(delta, self.cv2.COLOR_BGR2GRAY)
        _, mask = self.cv2.threshold(gray, threshold, 255, self.cv2.THRESH_BINARY)
        label_count, _, stats, _ = self.cv2.connectedComponentsWithStats(mask, 8)
        image_pixels = int(mask.shape[0] * mask.shape[1])
        findings: list[VisualFinding] = []

        for label in range(1, int(label_count)):
            area = int(stats[label, self.cv2.CC_STAT_AREA])
            if area < min_component_pixels:
                continue
            fraction = area / image_pixels
            risk: Risk = "high" if fraction >= 0.15 else "medium" if fraction >= 0.02 else "low"
            bbox = (
                int(stats[label, self.cv2.CC_STAT_LEFT]),
                int(stats[label, self.cv2.CC_STAT_TOP]),
                int(stats[label, self.cv2.CC_STAT_WIDTH]),
                int(stats[label, self.cv2.CC_STAT_HEIGHT]),
            )
            x, y, width, height = bbox
            signed_delta = (
                candidate[y : y + height, x : x + width].astype("int16")
                - baseline[y : y + height, x : x + width].astype("int16")
            )
            mean_delta = float(signed_delta.mean())
            kind: Literal["missing_region", "unexpected_region", "visual_change"]
            if mean_delta <= -threshold:
                kind = "missing_region"
            elif mean_delta >= threshold:
                kind = "unexpected_region"
            else:
                kind = "visual_change"
            findings.append(
                VisualFinding(
                    kind=kind,
                    risk=risk,
                    bbox_xywh=bbox,
                    changed_pixels=area,
                    image_pixels=image_pixels,
                )
            )
        kinds = {finding.kind for finding in findings}
        if "missing_region" in kinds and "unexpected_region" in kinds:
            findings = [replace(finding, kind="layout_shift") for finding in findings]
        return findings
