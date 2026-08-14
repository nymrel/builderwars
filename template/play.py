"""Run your entrant against the sparring panel. No network, no account, no key.

  python play.py                 # score against every baseline, both games
  python play.py watch           # watch one match, frame by frame
"""
from __future__ import annotations

import sys

from arena import baselines as B
from arena.runner import pairing, run_match
from entrant import ENTRANT_NAME, MyEntrant

PANELS = {"ten_fronts": B.TEN_FRONTS_PANEL, "manifest": B.MANIFEST_PANEL}
SEEDS = {"ten_fronts": range(3), "manifest": range(20)}  # see docs: measured, not guessed


def scoreboard():
    for game, panel in PANELS.items():
        print(f"\n{game.upper()}   ({len(SEEDS[game])} seeds, seats mirrored)")
        print(f"  {'opponent':<16}{'you':>10}{'them':>10}   result")
        w = l = d = 0
        for name, cls in panel.items():
            t = pairing(game, MyEntrant, cls, SEEDS[game])
            verdict = "WIN " if t["a"] > t["b"] else ("LOSS" if t["a"] < t["b"] else "draw")
            w += t["a"] > t["b"]; l += t["a"] < t["b"]; d += t["a"] == t["b"]
            print(f"  {name:<16}{t['a']:>10.0f}{t['b']:>10.0f}   {verdict}")
        print(f"  -> {ENTRANT_NAME}: {w}W {l}L {d}D")


def watch():
    game = sys.argv[2] if len(sys.argv) > 2 else "ten_fronts"
    opp = sys.argv[3] if len(sys.argv) > 3 else ("liar" if game == "ten_fronts" else "shader")
    r = run_match(game, {"A": MyEntrant(), "B": PANELS[game][opp]()}, 7, watch=True)
    print(r["scores"])


if __name__ == "__main__":
    watch() if len(sys.argv) > 1 and sys.argv[1] == "watch" else scoreboard()
