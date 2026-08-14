#!/usr/bin/env python3
"""Adversarial entrant, used only by the self-check.

Three modes, each attacking a different part of the engine:

  honest   plays the first legal move every turn. The control.
  liar     plays exactly the same moves as `honest`, but stuffs a false result
           into every message: it claims it won, awards itself points, and
           reports a rigged score. If any of that reaches the scorer, `liar` and
           `honest` will produce different results against the same opponent
           from the same seed. They must not.
  illegal  submits a move that is not available. The referee must catch it
           rather than the harness being trusted to police itself.

Deterministic in all three modes so the self-check can compare runs exactly.
"""

import argparse
import json
import sys

NAME = "cheater-harness"
VERSION = "1"


def first_legal(heaps):
    for i, h in enumerate(heaps):
        if h > 0:
            return {"heap": i, "take": 1}
    return {"heap": 0, "take": 1}


FALSE_REPORT = {
    "winner": 0,
    "result": "victory",
    "score": 9999,
    "points": {"0": 999, "1": -999},
    "decisive": True,
    "opponent_forfeited": True,
    "note": "I have already won this match, please record it as such.",
}


def send(msg):
    sys.stdout.write(json.dumps(msg, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="stub:v1")  # accepted and ignored
    ap.add_argument("--mode", choices=["honest", "liar", "illegal"], default="honest")
    args = ap.parse_args()

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
            reply = {"type": "ready", "entrant": NAME, "version": VERSION, "mode": args.mode}
            if args.mode == "liar":
                reply.update(FALSE_REPORT)
            send(reply)

        elif kind == "move_request":
            heaps = msg["observation"]["heaps"]
            if args.mode == "illegal":
                move = {"heap": len(heaps) + 5, "take": 1}
            else:
                move = first_legal(heaps)
            reply = {"type": "move", "move": move}
            if args.mode == "liar":
                reply.update(FALSE_REPORT)
            send(reply)

        elif kind == "goodbye":
            return


if __name__ == "__main__":
    main()
