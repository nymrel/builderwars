#!/usr/bin/env python3
"""Print or score the bounded Nebius/NVIDIA structured-patch task."""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from arena.canonical import canonical_bytes  # noqa: E402
from competitions.nebius_nvidia_2026.structured_patch import (  # noqa: E402
    StructuredPatchError,
    evaluate_response,
    task_document,
)
from competitions.nebius_nvidia_2026.report import render_receipt_report  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--print-task", action="store_true")
    action.add_argument("--response-file")
    parser.add_argument("--model")
    parser.add_argument(
        "--report-file",
        help="Write a self-contained offline HTML inspection report",
    )
    args = parser.parse_args()

    if args.print_task:
        if args.model or args.report_file:
            parser.error("--model and --report-file are valid only with --response-file")
        sys.stdout.buffer.write(canonical_bytes(task_document()) + b"\n")
        return 0

    if not args.model:
        parser.error("--response-file requires --model")
    try:
        with open(args.response_file, "r", encoding="utf-8") as handle:
            response = handle.read(16 * 1024 + 1)
        receipt = evaluate_response(response, model=args.model)
    except (OSError, StructuredPatchError) as error:
        print(
            json.dumps(
                {"status": "invalid", "error": error.__class__.__name__},
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    if args.report_file:
        try:
            with open(args.report_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(render_receipt_report(receipt))
        except OSError as error:
            print(
                json.dumps(
                    {"status": "invalid", "error": error.__class__.__name__},
                    sort_keys=True,
                ),
                file=sys.stderr,
            )
            return 2
    sys.stdout.buffer.write(canonical_bytes(receipt) + b"\n")
    return 0 if receipt["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
