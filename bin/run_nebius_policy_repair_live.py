#!/usr/bin/env python3
"""Run exactly one authorized Nebius/NVIDIA policy-repair call."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from arena.canonical import canonical_bytes  # noqa: E402
from competitions.nebius_nvidia_2026.live_report import (  # noqa: E402
    render_live_receipt_report,
)
from competitions.nebius_nvidia_2026.live_run import run_live_once  # noqa: E402
from entrants.nebius_backend import NebiusTokenFactoryBackend  # noqa: E402


def _write(path, data, *, binary=False):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if binary:
        target.write_bytes(data)
    else:
        target.write_text(data, encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-billable-call",
        action="store_true",
        help="Explicitly authorize one call billed against the configured Nebius project",
    )
    parser.add_argument(
        "--model",
        default=NebiusTokenFactoryBackend.DEFAULT_MODEL,
        help="Exact NVIDIA model id from the current Token Factory catalog",
    )
    parser.add_argument("--receipt-file")
    parser.add_argument("--report-file")
    parser.add_argument(
        "--demo-dir",
        help="Write index.html and receipt.json as a static judgeable evidence bundle",
    )
    args = parser.parse_args()

    if not args.allow_billable_call:
        parser.error("live execution requires --allow-billable-call")

    try:
        receipt = run_live_once(model=args.model)
    except (RuntimeError, ValueError, TypeError) as error:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "error": error.__class__.__name__,
                    "detail": str(error),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2

    payload = canonical_bytes(receipt) + b"\n"
    report = render_live_receipt_report(receipt)

    if args.receipt_file:
        _write(args.receipt_file, payload, binary=True)
    if args.report_file:
        _write(args.report_file, report)
    if args.demo_dir:
        demo = Path(args.demo_dir)
        demo.mkdir(parents=True, exist_ok=True)
        _write(demo / "receipt.json", payload, binary=True)
        _write(demo / "index.html", report)

    sys.stdout.buffer.write(payload)
    return 0 if receipt["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
