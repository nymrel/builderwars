#!/usr/bin/env python3
"""OpenRouter-backed fantasy GM with deterministic legal fallback.

The process owns inference. The referee receives only a legal move and a small,
provider-reported receipt summary; model identity and execution provenance stay
explicitly unattested.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

if __package__:
    from .fantasy_model_harness import (
        STRATEGIES,
        build_prompt,
        extract_strict_move,
        fallback_move,
        move_is_legal_for_observation,
        send,
    )
    from .openrouter_backend import OpenRouterBackend
else:
    HERE = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, HERE)
    from fantasy_model_harness import (  # noqa: E402
        STRATEGIES,
        build_prompt,
        extract_strict_move,
        fallback_move,
        move_is_legal_for_observation,
        send,
    )
    from openrouter_backend import OpenRouterBackend  # noqa: E402

VERSION = "1"


def _append_receipt(note: str, backend: OpenRouterBackend) -> str:
    receipt = backend.receipt_note()
    return f"{note};{receipt}" if receipt else note


def decide(observation, strategy, backend):
    prompt = build_prompt(observation, strategy)
    raw = None
    reason = "invalid_model_output"
    try:
        raw = backend.complete(prompt)
        move = extract_strict_move(raw)
        if move_is_legal_for_observation(observation, move):
            response_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
            return move, _append_receipt(
                f"source=model;response_sha256={response_hash}", backend
            )
    except Exception as error:
        reason = f"backend_error:{error.__class__.__name__}"

    move = fallback_move(observation, strategy)
    if raw is not None and isinstance(raw, str):
        response_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        return move, _append_receipt(
            f"source=fallback;reason={reason};response_sha256={response_hash}", backend
        )
    return move, _append_receipt(f"source=fallback;reason={reason}", backend)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--provider", action="append", required=True)
    parser.add_argument("--api-key-env", default="OPENROUTER_API_KEY")
    parser.add_argument("--backend-timeout", type=float, default=300.0)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--strategy", choices=STRATEGIES, required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    backend = OpenRouterBackend(
        model=args.model,
        provider_only=args.provider,
        api_key_env=args.api_key_env,
        timeout_s=args.backend_timeout,
        max_tokens=args.max_tokens,
    )

    for line in sys.stdin:
        if not line.strip():
            continue
        message = json.loads(line)
        if message.get("type") == "hello":
            send(
                {
                    "type": "ready",
                    "entrant": args.name,
                    "version": VERSION,
                    "backend": backend.label,
                }
            )
        elif message.get("type") == "move_request":
            move, note = decide(message.get("observation"), args.strategy, backend)
            send({"type": "move", "move": move, "note": note})
        elif message.get("type") == "goodbye":
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
