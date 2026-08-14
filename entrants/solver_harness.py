#!/usr/bin/env python3
"""Reference entrant: the harness that does the work.

Same model behind it as the naive harness. The difference is entirely in the
scaffolding the entrant's author wrote:

  1. It computes the position's XOR itself and derives the set of moves that
     win, rather than hoping the model can see it.
  2. It narrows the model's job to choosing from a short candidate list.
  3. It validates the answer against that list.
  4. When the answer is unusable — rambling, or a heap that is not there — it
     falls back to its own computed move instead of forfeiting.

None of that is a better model. It is a better harness. That is the thesis the
arena is built to measure.

Deliberately does not import the `arena` package.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backends import get_backend  # noqa: E402
from parsing import parse_move  # noqa: E402  — identical parser in both arms

NAME = "solver-harness"
VERSION = "2"


def xor_all(heaps):
    x = 0
    for h in heaps:
        x ^= h
    return x


def legal_moves(heaps):
    return [{"heap": i, "take": t} for i, h in enumerate(heaps) for t in range(1, h + 1)]


def winning_moves(heaps):
    """Moves that leave the XOR at zero. Empty when the position is already lost."""
    target = xor_all(heaps)
    if target == 0:
        return []
    out = []
    for i, h in enumerate(heaps):
        want = h ^ target
        if want < h:
            out.append({"heap": i, "take": h - want})
    return out


def candidates(heaps):
    """Winning moves when one exists; otherwise every legal move.

    From a lost position there is no move that beats perfect play, so the
    harness keeps the game going and lets the opponent be the one to err.
    """
    return winning_moves(heaps) or legal_moves(heaps)


def build_prompt(obs, cands):
    listing = "\n".join(
        f"  {n}. take {c['take']} from heap {c['heap']}" for n, c in enumerate(cands, 1)
    )
    return (
        f"{obs['rules']}\n\n"
        f"heaps: {obs['heaps']}\n"
        f"You are player {obs['you_are']}. It is your move.\n\n"
        f"Every move below is a good one. Pick exactly one and say it back:\n"
        f"{listing}\n"
    )


def send(msg):
    sys.stdout.write(json.dumps(msg, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="stub:v1")
    ap.add_argument("--backend-timeout", type=float, default=None,
                    help="seconds to wait for the model; raise it for cold local models")
    args = ap.parse_args()
    backend = get_backend(args.backend, args.backend_timeout)

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
            obs = msg["observation"]
            heaps = obs["heaps"]
            cands = candidates(heaps)

            source = "model"
            try:
                chosen = parse_move(backend.complete(build_prompt(obs, cands)))
            except Exception as e:
                # Name the cause. "backend_error" alone once made a series where
                # the model never answered look like a series the model won: the
                # fallback is invisible in the result and only the note says so.
                chosen = None
                source = f"fallback:backend_error:{e.__class__.__name__}"

            if chosen not in cands:
                # Unusable answer. Take the harness's own best move rather than
                # forfeit. This single line is most of the win rate.
                chosen = cands[0]
                if source == "model":
                    source = "fallback:rejected_model_answer"

            send({"type": "move", "move": chosen, "note": f"source={source}"})

        elif kind == "goodbye":
            return


if __name__ == "__main__":
    main()
