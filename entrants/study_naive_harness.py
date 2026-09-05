#!/usr/bin/env python3
"""Reference entrant: the harness that trusts its model.

It shows the model the board, reads back whatever prose comes out, pulls a move
from it with one regular expression, and forwards that to the referee. No
legality check, no retry, no fallback. If the model rambles instead of
answering, this harness has nothing to send.

That is the control arm. It exists so the other harness has something to beat
using the identical model behind it.

Deliberately does not import the `arena` package: an entrant is independent
software that speaks the protocol, not a plugin.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backends import acknowledge_customer_local_v1, get_backend  # noqa: E402
from parsing import parse_move  # noqa: E402  — identical parser in both arms

NAME = "study-naive-harness"
VERSION = "3"


def build_prompt(obs):
    return (
        f"{obs['rules']}\n\n"
        f"heaps: {obs['heaps']}\n"
        f"You are player {obs['you_are']}. It is your move.\n"
        f"Reply with your move."
    )


def send(msg):
    sys.stdout.write(json.dumps(msg, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="stub:v1")
    ap.add_argument(
        "--customer-local-v1",
        action="store_true",
        help="required for non-stub backends; records local intent only and "
             "is not an OS isolation boundary",
    )
    ap.add_argument("--backend-timeout", type=float, default=None,
                    help="seconds to wait for the model; raise it for cold local models")
    args = ap.parse_args()
    runtime_intent = (
        acknowledge_customer_local_v1() if args.customer_local_v1 else None
    )
    try:
        backend = get_backend(
            args.backend,
            args.backend_timeout,
            runtime_intent=runtime_intent,
        )
    except RuntimeError as error:
        ap.error(str(error))

    while True:
        line = sys.stdin.readline()
        if not line:
            return
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        kind = msg.get("type")

        if kind == "hello":
            send({"type": "ready", "entrant": NAME, "version": VERSION, "backend": backend.label})

        elif kind == "move_request":
            # Survives a backend error so the comparison against solver_harness
            # isolates one variable: validation and fallback, not crash safety.
            # The structured source marker lets a zero-fallback study distinguish
            # a real model answer from a null move caused by infrastructure.
            source = "model"
            try:
                text = backend.complete(build_prompt(msg["observation"]))
            except Exception as error:
                text = ""
                source = f"backend_error:{error.__class__.__name__}"
            move = parse_move(text)
            # Forwarded as-is. An unparseable or illegal model answer is still a
            # model-sourced experimental outcome; the referee will forfeit it.
            # Raw model text is deliberately not copied into the receipt.
            send({"type": "move", "move": move, "note": f"source={source}"})

        elif kind == "goodbye":
            return


if __name__ == "__main__":
    main()
