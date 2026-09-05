#!/usr/bin/env python3
"""Prove bounded static contrast contracts for the Mobile Arena palette.

This gate reads tracked CSS only. It verifies that every referenced custom
property exists, every literal or token used as a text foreground is covered by
the contract, and critical committed foreground/background pairs meet the
declared WCAG contrast threshold. It does not emulate the cascade, alpha
compositing, gradients, images, forced-colors mode, zoom, or a real display.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
CSS_PATH = ROOT / "mobile-arena" / "styles.css"
SCHEMA_VERSION = "agentwars.mobile-arena-static-contrast/1"
HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}\Z")
CUSTOM_PROPERTY = re.compile(r"--[a-zA-Z0-9-]+")
VAR_REFERENCE = re.compile(r"var\(\s*(--[a-zA-Z0-9-]+)\s*\)")


class ContrastContractError(ValueError):
    """Raised when tracked CSS cannot satisfy the bounded contrast contract."""


@dataclass(frozen=True)
class PairSpec:
    label: str
    foreground: str
    background: str
    minimum: float
    role: str


PAIR_SPECS = (
    PairSpec("body text / canvas", "--text", "--bg", 4.5, "normal_text"),
    PairSpec("body text / surface", "--text", "--surface", 4.5, "normal_text"),
    PairSpec("body text / raised surface", "--text", "--surface-2", 4.5, "normal_text"),
    PairSpec("muted text / canvas", "--muted", "--bg", 4.5, "normal_text"),
    PairSpec("muted text / surface", "--muted", "--surface", 4.5, "normal_text"),
    PairSpec("muted text / raised surface", "--muted", "--surface-2", 4.5, "normal_text"),
    PairSpec("accent text / canvas", "--lime", "--bg", 4.5, "normal_text"),
    PairSpec("accent text / surface", "--lime", "--surface", 4.5, "normal_text"),
    PairSpec("accent text / raised surface", "--lime", "--surface-2", 4.5, "normal_text"),
    PairSpec("risk text / canvas", "--risk", "--bg", 4.5, "normal_text"),
    PairSpec("risk text / surface", "--risk", "--surface", 4.5, "normal_text"),
    PairSpec("risk text / raised surface", "--risk", "--surface-2", 4.5, "normal_text"),
    PairSpec("avatar canvas text / light fill", "--bg", "--text", 4.5, "normal_text"),
    PairSpec("primary button text / accent", "#0b0d0c", "--lime", 4.5, "normal_text"),
    PairSpec("primary button text / hover fill", "#0b0d0c", "#dbff7c", 4.5, "normal_text"),
    PairSpec("starter boundary / surface", "#bdc7bd", "--surface", 4.5, "normal_text"),
    PairSpec("starter boundary / dark accent", "#bdc7bd", "--lime-dark", 4.5, "normal_text"),
    PairSpec("creator status / surface", "#f4bb72", "--surface", 4.5, "normal_text"),
    PairSpec("creator authority / surface", "#f0b874", "--surface", 4.5, "normal_text"),
    PairSpec("creator admission / surface", "#c9d0c7", "--surface", 4.5, "normal_text"),
    PairSpec("creator unavailable / surface", "#f1b873", "--surface", 4.5, "normal_text"),
    PairSpec("boundary copy / dark accent", "#c7d4b6", "--lime-dark", 4.5, "normal_text"),
    PairSpec("portable control text / input fill", "--text", "#050706", 4.5, "normal_text"),
    PairSpec("portable readonly text / input fill", "#b8c89f", "#050706", 4.5, "normal_text"),
    PairSpec("invalid detail / input fill", "#ff9b8c", "#050706", 4.5, "normal_text"),
    PairSpec("armed danger text / surface", "#ffd4ce", "--surface", 4.5, "normal_text"),
    PairSpec("ready feedback text / surface", "#d8f6ac", "--surface", 4.5, "normal_text"),
    PairSpec("error feedback text / surface", "#ffb0a4", "--surface", 4.5, "normal_text"),
    PairSpec("feedback output text / canvas", "#d6e3c7", "--bg", 4.5, "normal_text"),
    PairSpec("pending proof text / sheet", "#ffd36b", "#111411", 4.5, "normal_text"),
    PairSpec("toast text / toast fill", "--text", "#151c11", 4.5, "normal_text"),
    PairSpec("focus indicator / canvas", "--focus", "--bg", 3.0, "focus_indicator"),
    PairSpec("focus indicator / surface", "--focus", "--surface", 3.0, "focus_indicator"),
    PairSpec("focus indicator / raised surface", "--focus", "--surface-2", 3.0, "focus_indicator"),
    PairSpec("focus indicator / sheet", "--focus", "#111411", 3.0, "focus_indicator"),
)

REQUIRED_TOKENS = frozenset(
    ("--bg", "--surface", "--surface-2", "--text", "--muted", "--lime", "--lime-dark", "--risk", "--focus")
)

BOUNDARY = {
    "trackedCssRead": True,
    "customPropertyReferencesResolved": True,
    "declaredForegroundsCovered": True,
    "staticOpaquePairsMeasured": True,
    "cascadeRendered": False,
    "alphaOrGradientCompositingRendered": False,
    "forcedColorsRendered": False,
    "zoomOrDisplayHardwareTested": False,
    "productionAccessibilityProven": False,
    "launchable": False,
}


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def parse_root_tokens(css: str) -> dict[str, str]:
    match = re.search(r":root\s*\{(?P<body>.*?)\}", css, flags=re.DOTALL)
    if match is None:
        raise ContrastContractError("missing :root palette")
    rows = re.findall(r"(--[a-zA-Z0-9-]+)\s*:\s*([^;{}]+?)\s*;", match.group("body"))
    tokens: dict[str, str] = {}
    for name, value in rows:
        if name in tokens:
            raise ContrastContractError(f"duplicate :root token: {name}")
        tokens[name] = value.strip()
    missing = sorted(REQUIRED_TOKENS - set(tokens))
    if missing:
        raise ContrastContractError(f"missing required palette tokens: {missing}")
    return tokens


def unresolved_custom_properties(css: str) -> list[str]:
    definitions = set(re.findall(r"(--[a-zA-Z0-9-]+)\s*:", css))
    references = set(re.findall(r"var\(\s*(--[a-zA-Z0-9-]+)", css))
    return sorted(references - definitions)


def resolve_color(reference: str, tokens: Mapping[str, str], stack: tuple[str, ...] = ()) -> str:
    if HEX_COLOR.fullmatch(reference):
        return reference.lower()
    if not CUSTOM_PROPERTY.fullmatch(reference):
        raise ContrastContractError(f"unsupported color reference: {reference}")
    if reference in stack:
        raise ContrastContractError(f"cyclic color token: {' -> '.join(stack + (reference,))}")
    if reference not in tokens:
        raise ContrastContractError(f"unknown color token: {reference}")
    value = tokens[reference].strip()
    alias = VAR_REFERENCE.fullmatch(value)
    if alias:
        return resolve_color(alias.group(1), tokens, stack + (reference,))
    if not HEX_COLOR.fullmatch(value):
        raise ContrastContractError(f"color token must resolve to opaque six-digit hex: {reference}={value}")
    return value.lower()


def rgb(color: str) -> tuple[float, float, float]:
    if not HEX_COLOR.fullmatch(color):
        raise ContrastContractError(f"invalid opaque six-digit hex: {color}")
    return tuple(int(color[index:index + 2], 16) / 255.0 for index in (1, 3, 5))  # type: ignore[return-value]


def relative_luminance(color: str) -> float:
    channels = tuple(
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in rgb(color)
    )
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(foreground: str, background: str) -> float:
    lighter, darker = sorted((relative_luminance(foreground), relative_luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def declared_foregrounds(css: str) -> set[str]:
    values = re.findall(
        r"(?<![-\w])color\s*:\s*(#[0-9a-fA-F]{6}|var\(\s*--[a-zA-Z0-9-]+\s*\))\s*;",
        css,
    )
    return {VAR_REFERENCE.fullmatch(value).group(1) if VAR_REFERENCE.fullmatch(value) else value.lower() for value in values}


def assert_css_routes(css: str) -> None:
    requirements = {
        "body palette route": r"body\s*\{[^}]*background\s*:\s*var\(--bg\)[^}]*color\s*:\s*var\(--text\)",
        "primary button palette route": r"\.primary-button\s*\{[^}]*background\s*:\s*var\(--lime\)[^}]*color\s*:\s*#0b0d0c",
        "primary hover route": r"\.primary-button:hover\s*\{[^}]*background\s*:\s*#dbff7c",
        "focus route": r"focus-visible[^{}]*\{[^}]*outline\s*:\s*2px\s+solid\s+var\(--focus\)[^}]*outline-offset\s*:\s*3px",
        "portable textarea palette route": r"\.portable-textarea\s*\{[^}]*background\s*:\s*#050706[^}]*color\s*:\s*var\(--text\)",
        "portable review palette route": r"\.portable-review-form input[^{}]*\{[^}]*background\s*:\s*#050706[^}]*color\s*:\s*var\(--text\)",
    }
    for label, pattern in requirements.items():
        if re.search(pattern, css, flags=re.DOTALL) is None:
            raise ContrastContractError(f"missing {label}")


def build_receipt(css: str) -> dict[str, object]:
    if not css.strip():
        raise ContrastContractError("tracked CSS is empty")
    unresolved = unresolved_custom_properties(css)
    if unresolved:
        raise ContrastContractError(f"unresolved CSS custom properties: {unresolved}")
    assert_css_routes(css)
    tokens = parse_root_tokens(css)

    covered_foregrounds = {spec.foreground for spec in PAIR_SPECS}
    uncovered = sorted(declared_foregrounds(css) - covered_foregrounds)
    if uncovered:
        raise ContrastContractError(f"declared text foregrounds lack a contrast pair: {uncovered}")

    rows: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    for spec in PAIR_SPECS:
        foreground = resolve_color(spec.foreground, tokens)
        background = resolve_color(spec.background, tokens)
        ratio = contrast_ratio(foreground, background)
        row: dict[str, object] = {
            "label": spec.label,
            "role": spec.role,
            "foregroundRef": spec.foreground,
            "foreground": foreground,
            "backgroundRef": spec.background,
            "background": background,
            "minimum": spec.minimum,
            "ratio": round(ratio, 6),
            "status": "PASS" if ratio + 1e-12 >= spec.minimum else "FAIL",
        }
        rows.append(row)
        if row["status"] == "FAIL":
            failures.append(row)

    contract = {
        "schemaVersion": SCHEMA_VERSION,
        "sourceClass": "tracked_static_css_only",
        "pairSpecs": [spec.__dict__ for spec in PAIR_SPECS],
        "boundary": BOUNDARY,
    }
    receipt: dict[str, object] = {
        "schemaVersion": SCHEMA_VERSION,
        "sourceStatus": "tracked_local_source",
        "sourcePath": "mobile-arena/styles.css",
        "sourceSha256": hashlib.sha256(css.encode("utf-8")).hexdigest(),
        "contractDigest": digest(contract),
        "pairCount": len(rows),
        "unresolvedCustomProperties": unresolved,
        "uncoveredForegrounds": uncovered,
        "pairs": rows,
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
        "boundary": dict(BOUNDARY),
    }
    receipt["receiptDigest"] = digest(receipt)
    return receipt


def run_self_checks() -> int:
    checks = 0

    def check(condition: bool, label: str) -> None:
        nonlocal checks
        if not condition:
            raise AssertionError(label)
        checks += 1

    check(math.isclose(contrast_ratio("#000000", "#ffffff"), 21.0, rel_tol=0, abs_tol=1e-12), "black/white ratio")
    check(contrast_ratio("#777777", "#ffffff") < 4.5, "near-threshold normal text fails closed")
    check(contrast_ratio("#ffffff", "#ffffff") < 3.0, "identical focus colors fail closed")
    try:
        rgb("#fff")
    except ContrastContractError:
        checks += 1
    else:
        raise AssertionError("short hex was accepted")
    check(unresolved_custom_properties(":root{--a:#000000}.x{color:var(--b);}") == ["--b"], "undefined variable detected")
    try:
        resolve_color("--a", {"--a": "var(--b)", "--b": "var(--a)"})
    except ContrastContractError as exc:
        check("cyclic" in str(exc), "cyclic token rejected")
    else:
        raise AssertionError("cyclic token was accepted")
    check(resolve_color("--a", {"--a": "var(--b)", "--b": "#ABCDEF"}) == "#abcdef", "token alias resolution")
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print the deterministic receipt as JSON")
    args = parser.parse_args()

    self_checks = run_self_checks()
    receipt = build_receipt(CSS_PATH.read_text(encoding="utf-8"))
    if receipt["status"] != "PASS":
        raise SystemExit(json.dumps(receipt["failures"], sort_keys=True))
    if args.json:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    else:
        print(
            "BuilderWars mobile Arena static contrast: PASS "
            f"({receipt['pairCount']} pairs; {self_checks} adversarial checks; 0 unresolved variables)"
        )
        print("tracked opaque CSS pairs only / rendered compositing and production accessibility remain unproven")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
