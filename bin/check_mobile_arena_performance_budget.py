#!/usr/bin/env python3
"""Enforce deterministic local performance budgets for the Mobile Arena.

This gate reads only tracked source assets. It does not contact a host, observe
users, measure production timings, or establish a production performance SLO.
"""

from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
MOBILE_ARENA = ROOT / "mobile-arena"
SCHEMA_VERSION = "agentwars.mobile-arena-performance-budget/1"


class PerformanceBudgetError(ValueError):
    """Raised when the local budget input is incomplete or malformed."""


@dataclass(frozen=True)
class AssetBudget:
    path: str
    role: str
    raw_limit: int
    gzip_limit: int


ASSET_BUDGETS = (
    AssetBudget("index.html", "html", 20_000, 8_000),
    AssetBudget("styles.css", "style", 45_000, 12_000),
    AssetBudget("data-adapter.js", "script", 250_000, 40_000),
    AssetBudget("app.js", "script", 225_000, 40_000),
    AssetBudget("sw.js", "worker", 8_000, 4_000),
    AssetBudget("manifest.webmanifest", "manifest", 4_096, 2_048),
    AssetBudget("assets/arena-mark.svg", "image", 4_096, 2_048),
    AssetBudget("data/arena-read-model.v1.json", "data", 65_536, 12_000),
    AssetBudget("data/demo-state.json", "data", 16_384, 8_000),
)

AGGREGATE_LIMITS = {
    "trackedAssetCount": 9,
    "totalRawBytes": 625_000,
    "totalGzipBytes": 125_000,
    "coreShellRawBytes": 525_000,
    "coreShellGzipBytes": 90_000,
    "scriptRawBytes": 475_000,
    "scriptGzipBytes": 80_000,
    "dataRawBytes": 100_000,
    "dataGzipBytes": 20_000,
}

CORE_SHELL = frozenset(("index.html", "styles.css", "data-adapter.js", "app.js"))
PRODUCTION_CLAIMS = {
    "productionDataRead": False,
    "productionNetworkObserved": False,
    "productionTimingMeasured": False,
    "productionPerformanceProven": False,
    "realUserExperienceProven": False,
    "launchable": False,
}
ALLOWED_IMPORT_ROOTS = {
    "__future__",
    "argparse",
    "ast",
    "dataclasses",
    "gzip",
    "hashlib",
    "json",
    "pathlib",
    "sys",
    "typing",
}


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def deterministic_gzip_size(value: bytes) -> int:
    return len(gzip.compress(value, compresslevel=9, mtime=0))


def performance_contract() -> dict[str, object]:
    contract: dict[str, object] = {
        "schemaVersion": SCHEMA_VERSION,
        "sourceClass": "tracked_local_source_only",
        "assets": [
            {
                "path": budget.path,
                "role": budget.role,
                "rawLimitBytes": budget.raw_limit,
                "gzipLimitBytes": budget.gzip_limit,
            }
            for budget in ASSET_BUDGETS
        ],
        "aggregateLimits": dict(AGGREGATE_LIMITS),
        "compression": "gzip_level_9_mtime_0",
        "productionClaims": dict(PRODUCTION_CLAIMS),
    }
    contract["contractDigest"] = digest(contract)
    return contract


def load_tracked_assets(root: Path = MOBILE_ARENA) -> dict[str, bytes]:
    assets: dict[str, bytes] = {}
    for budget in ASSET_BUDGETS:
        path = root / Path(budget.path)
        if not path.is_file():
            raise PerformanceBudgetError(f"required tracked asset is missing: {budget.path}")
        assets[budget.path] = path.read_bytes()
    return assets


def _validate_asset_map(assets: Mapping[str, bytes]) -> None:
    expected = {budget.path for budget in ASSET_BUDGETS}
    observed = set(assets)
    missing = sorted(expected - observed)
    unknown = sorted(observed - expected)
    if missing or unknown:
        raise PerformanceBudgetError(f"asset set drift (missing={missing}, unknown={unknown})")
    for path, value in assets.items():
        if type(value) is not bytes:
            raise PerformanceBudgetError(f"asset must be exact bytes: {path}")
        if not value:
            raise PerformanceBudgetError(f"asset must not be empty: {path}")


def _totals(rows: list[dict[str, object]]) -> dict[str, int]:
    by_role = lambda role: [row for row in rows if row["role"] == role]
    by_path = lambda paths: [row for row in rows if row["path"] in paths]
    sum_key = lambda selected, key: sum(int(row[key]) for row in selected)
    scripts = by_role("script")
    data = by_role("data")
    core = by_path(CORE_SHELL)
    return {
        "trackedAssetCount": len(rows),
        "totalRawBytes": sum_key(rows, "rawBytes"),
        "totalGzipBytes": sum_key(rows, "gzipBytes"),
        "coreShellRawBytes": sum_key(core, "rawBytes"),
        "coreShellGzipBytes": sum_key(core, "gzipBytes"),
        "scriptRawBytes": sum_key(scripts, "rawBytes"),
        "scriptGzipBytes": sum_key(scripts, "gzipBytes"),
        "dataRawBytes": sum_key(data, "rawBytes"),
        "dataGzipBytes": sum_key(data, "gzipBytes"),
    }


def _failures(rows: list[dict[str, object]], totals: Mapping[str, int]) -> list[dict[str, object]]:
    failures: list[dict[str, object]] = []
    budget_by_path = {budget.path: budget for budget in ASSET_BUDGETS}
    for row in rows:
        budget = budget_by_path[str(row["path"])]
        if int(row["rawBytes"]) > budget.raw_limit:
            failures.append({
                "code": "ASSET_RAW_BUDGET",
                "path": budget.path,
                "actual": row["rawBytes"],
                "limit": budget.raw_limit,
            })
        if int(row["gzipBytes"]) > budget.gzip_limit:
            failures.append({
                "code": "ASSET_GZIP_BUDGET",
                "path": budget.path,
                "actual": row["gzipBytes"],
                "limit": budget.gzip_limit,
            })
    for name, limit in AGGREGATE_LIMITS.items():
        if totals[name] > limit:
            failures.append({
                "code": "AGGREGATE_BUDGET",
                "metric": name,
                "actual": totals[name],
                "limit": limit,
            })
    return failures


def build_receipt(assets: Mapping[str, bytes]) -> dict[str, object]:
    _validate_asset_map(assets)
    budget_by_path = {budget.path: budget for budget in ASSET_BUDGETS}
    rows: list[dict[str, object]] = []
    for path in sorted(assets):
        value = assets[path]
        rows.append({
            "path": path,
            "role": budget_by_path[path].role,
            "sha256": hashlib.sha256(value).hexdigest(),
            "rawBytes": len(value),
            "gzipBytes": deterministic_gzip_size(value),
        })
    totals = _totals(rows)
    failures = _failures(rows, totals)
    contract = performance_contract()
    receipt: dict[str, object] = {
        "schemaVersion": SCHEMA_VERSION,
        "sourceStatus": "tracked_local_source",
        "contractDigest": contract["contractDigest"],
        "assetSetDigest": digest(rows),
        "assets": rows,
        "totals": totals,
        "limits": dict(AGGREGATE_LIMITS),
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
        "localProof": {
            "trackedAssetBytesMeasured": True,
            "deterministicGzipMeasured": True,
            "browserTimingMeasured": False,
        },
        "productionClaims": dict(PRODUCTION_CLAIMS),
    }
    receipt["receiptDigest"] = digest(receipt)
    return receipt


def _deterministic_noise(size: int) -> bytes:
    chunks: list[bytes] = []
    counter = 0
    while sum(len(chunk) for chunk in chunks) < size:
        chunks.append(hashlib.sha256(f"agentwars-budget-{counter}".encode("ascii")).digest())
        counter += 1
    return b"".join(chunks)[:size]


def _import_roots(path: Path) -> set[str]:
    roots: set[str] = set()
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def run_checks() -> tuple[int, dict[str, object]]:
    checks = 0

    def check(condition: bool, label: str) -> None:
        nonlocal checks
        if not condition:
            raise AssertionError(label)
        checks += 1

    assets = load_tracked_assets()
    receipt = build_receipt(assets)
    check(receipt["status"] == "PASS", f"tracked mobile Arena fits its local budgets: {receipt['failures']}")
    check(receipt["failures"] == [], "passing receipt has no hidden budget failures")
    check(receipt["sourceStatus"] == "tracked_local_source", "receipt names its local source class")
    check(receipt["contractDigest"] == performance_contract()["contractDigest"], "receipt binds the exact budget contract")
    check(build_receipt(assets) == receipt, "receipt is deterministic")
    check(len(receipt["assets"]) == len(ASSET_BUDGETS), "every budgeted asset is measured once")
    check(receipt["totals"]["trackedAssetCount"] == len(ASSET_BUDGETS), "tracked asset count is exact")
    check(all(not value for value in receipt["productionClaims"].values()), "every production performance claim remains false")
    check(receipt["localProof"]["browserTimingMeasured"] is False, "static source proof does not claim browser timing")
    check(all(not Path(row["path"]).is_absolute() for row in receipt["assets"]), "receipt contains only relative asset paths")
    check(len(receipt["assetSetDigest"]) == 64 and len(receipt["receiptDigest"]) == 64, "receipt digests are content-shaped")

    contract = performance_contract()
    check(contract["sourceClass"] == "tracked_local_source_only", "contract refuses a live-source implication")
    check(all(not value for value in contract["productionClaims"].values()), "contract carries zero production authority")
    check(contract["contractDigest"] == performance_contract()["contractDigest"], "contract digest is deterministic")

    source_text = (MOBILE_ARENA / "index.html").read_text(encoding="utf-8")
    adapter_text = (MOBILE_ARENA / "data-adapter.js").read_text(encoding="utf-8")
    app_text = (MOBILE_ARENA / "app.js").read_text(encoding="utf-8")
    for reference in ("styles.css", "data-adapter.js", "app.js", "manifest.webmanifest", "assets/arena-mark.svg"):
        check(reference in source_text, f"HTML references the budgeted asset {reference}")
    for reference in ("data/demo-state.json", "data/arena-read-model.v1.json"):
        check(reference in adapter_text, f"read adapter references the budgeted data asset {reference}")
    check('register("sw.js")' in app_text, "runtime references the budgeted service worker")

    raw_over = dict(assets)
    app_budget = next(budget for budget in ASSET_BUDGETS if budget.path == "app.js")
    raw_over["app.js"] = assets["app.js"] + b"x" * (app_budget.raw_limit - len(assets["app.js"]) + 1)
    raw_receipt = build_receipt(raw_over)
    check(raw_receipt["status"] == "FAIL", "raw-size overage fails closed")
    check(any(row["code"] == "ASSET_RAW_BUDGET" and row["path"] == "app.js" for row in raw_receipt["failures"]), "raw-size failure is attributed")

    gzip_over = dict(assets)
    gzip_over["index.html"] = _deterministic_noise(12_000)
    gzip_receipt = build_receipt(gzip_over)
    check(gzip_receipt["status"] == "FAIL", "compressed-size overage fails closed")
    check(any(row["code"] == "ASSET_GZIP_BUDGET" and row["path"] == "index.html" for row in gzip_receipt["failures"]), "compressed-size failure is attributed")

    aggregate_over = dict(assets)
    aggregate_over["data/demo-state.json"] = _deterministic_noise(16_000)
    aggregate_over["data/arena-read-model.v1.json"] = _deterministic_noise(64_000)
    aggregate_receipt = build_receipt(aggregate_over)
    check(aggregate_receipt["status"] == "FAIL", "aggregate overage fails closed")
    check(any(row["code"] == "AGGREGATE_BUDGET" and row.get("metric") == "dataGzipBytes" for row in aggregate_receipt["failures"]), "aggregate failure is attributed")

    for mutation, label in (
        ({key: value for key, value in assets.items() if key != "sw.js"}, "missing asset"),
        ({**assets, "unknown.js": b"alert(1)"}, "unknown asset"),
        ({**assets, "sw.js": "not-bytes"}, "non-bytes asset"),
        ({**assets, "sw.js": b""}, "empty asset"),
    ):
        try:
            build_receipt(mutation)  # type: ignore[arg-type]
        except PerformanceBudgetError:
            check(True, f"{label} is refused")
        else:
            raise AssertionError(f"{label} should be refused")

    imports = _import_roots(Path(__file__))
    check(imports <= ALLOWED_IMPORT_ROOTS, f"checker remains filesystem-only: {sorted(imports - ALLOWED_IMPORT_ROOTS)}")
    compact = canonical_bytes(receipt).decode("ascii")
    for forbidden in ("productionPerformanceProven\":true", "productionTimingMeasured\":true", "launchable\":true"):
        check(forbidden not in compact, f"receipt cannot emit {forbidden}")
    return checks, receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print the deterministic local budget receipt.")
    args = parser.parse_args()
    checks, receipt = run_checks()
    if args.json:
        print(json.dumps({"selfChecks": checks, "receipt": receipt}, sort_keys=True, indent=2))
    else:
        totals = receipt["totals"]
        print(f"AgentWars Mobile Arena performance budget: PASS ({checks} checks)")
        print(
            f"tracked={totals['trackedAssetCount']} / raw={totals['totalRawBytes']} / "
            f"gzip={totals['totalGzipBytes']} / core-gzip={totals['coreShellGzipBytes']}"
        )
        print("deterministic local asset budget only / no production timing, user, or launch claim")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, PerformanceBudgetError) as error:
        print(f"AgentWars Mobile Arena performance budget: FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
