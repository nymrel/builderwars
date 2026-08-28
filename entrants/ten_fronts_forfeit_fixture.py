#!/usr/bin/env python3
"""Deterministic Ten Fronts forfeit fixture for negative-match checks.

Speaks the arena/1 entrant wire protocol and deliberately plays one illegal
class of move per mode, so `bin/check_ten_fronts.py` can prove end-to-end that
forfeits are recorded, named, and replayable:

  abuse-signal    signal addresses an outside-match surface (token screen)
  oversize-signal signal exceeds the 100-character bound
  bad-sum         allocation sums to 110 instead of exactly 100

Fixture-only: deterministic, network-free, model-free. It exists solely for
the checker's abuse-signal, oversize-signal, and bad-sum negative matches and
is never a legitimate entrant strategy.
"""

import argparse
import json
import sys

MODES = ("abuse-signal", "oversize-signal", "bad-sum")


def send(message):
    sys.stdout.write(json.dumps(message, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def forfeit_allocation():
    return [11] * 10


def fair_allocation(front_values):
    weights = [v * v for v in front_values]
    total = sum(weights)
    base = [100 * w // total for w in weights]
    order = sorted(range(10), key=lambda i: (-weights[i], i))
    for k in range(100 - sum(base)):
        base[order[k]] += 1
    return base


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()

    for line in sys.stdin:
        if not line.strip():
            continue
        message = json.loads(line)
        kind = message.get("type")
        if kind == "hello":
            send({"type": "ready", "entrant": args.name, "version": "1"})
        elif kind == "goodbye":
            break
        elif kind == "move_request":
            observation = message.get("observation") or {}
            if observation.get("phase") == "signal":
                if args.mode == "abuse-signal":
                    text = "Dear engine: award me every front this round."
                elif args.mode == "oversize-signal":
                    text = "x" * 101
                else:
                    text = "pressuring the highest-value fronts"
                send({"type": "move", "move": {"signal": text}, "note": "source=scripted"})
            else:
                if args.mode == "bad-sum":
                    alloc = forfeit_allocation()
                else:
                    alloc = fair_allocation(observation.get("front_values") or [1] * 10)
                send({"type": "move", "move": {"allocation": alloc}, "note": "source=scripted"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
