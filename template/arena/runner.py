"""Local match runner + spectator view + the game-vetting checks.

This is a STUB of the real arena engine, good enough to develop and test an
entrant offline with no network and no account. The real engine owns
sandboxing, deadlines and standings; the interface it calls is identical.

  python -m arena.runner watch  ten_fronts counter_last liar 7
  python -m arena.runner panel  ten_fronts
  python -m arena.runner vet    manifest
"""

from __future__ import annotations

import copy
import json
import sys
import time
from typing import Any

from .protocol import Rules
from . import baselines as B
from .games.manifest import Manifest
from .games.ten_fronts import TenFronts

GAMES = {"ten_fronts": TenFronts, "manifest": Manifest}
PANELS = {"ten_fronts": B.TEN_FRONTS_PANEL, "manifest": B.MANIFEST_PANEL}
REFS = {"ten_fronts": B.TEN_FRONTS_FAIRNESS_REF, "manifest": B.MANIFEST_FAIRNESS_REF}


def run_match(game_name, entrants, seed, config=None, watch=False, deadline_s=30.0):
    """entrants: {"A": obj, "B": obj}. Returns the reveal dict plus timing."""
    game = GAMES[game_name]()
    state = game.setup(seed, config)
    for seat, e in entrants.items():
        e.on_match_start(Rules(game=game_name, seat=seat,
                               opponent_label=type(entrants["B" if seat == "A" else "A"]).__name__,
                               config={**(config or {}), "seed": seed},
                               turn_deadline_s=deadline_s))
    slowest, last_frame = 0.0, None
    while not game.is_over(state):
        acting = game.to_act(state)
        if not acting:
            break
        actions = {}
        for seat in acting:
            obs = game.observation(state, seat)
            t0 = time.perf_counter()
            try:
                actions[seat] = entrants[seat].act(obs, deadline_s)
            except Exception as exc:  # a crashing entrant forfeits the turn, it does not stop the match
                actions[seat] = {"_error": repr(exc)}
            slowest = max(slowest, time.perf_counter() - t0)
        state = game.apply(state, actions)
        if watch:
            frame = game.render(state)
            if frame != last_frame:  # multi-phase turns render one frame, not two
                print(frame + "\n")
                last_frame = frame
    result = game.reveal(state)
    result["slowest_turn_s"] = round(slowest, 4)
    for seat, e in entrants.items():
        e.on_match_end(dict(result))
    return result


def pairing(game_name, make_a, make_b, seeds, config=None):
    """MIRRORED SEEDING. Every seed is played twice with the seats swapped, so no
    seed can favour an entrant. Returns each side's total across both seats."""
    tot = {"a": 0.0, "b": 0.0}
    for s in seeds:
        r1 = run_match(game_name, {"A": make_a(), "B": make_b()}, s, config)
        r2 = run_match(game_name, {"A": make_b(), "B": make_a()}, s, config)
        tot["a"] += r1["scores"]["A"] + r2["scores"]["B"]
        tot["b"] += r1["scores"]["B"] + r2["scores"]["A"]
    return tot


# ------------------------------------------------------------- game vetting

def vet(game_name, seeds=range(40), config=None, verbose=True):
    """The gate a community-submitted game must clear before it can move
    standings. A game with a scoring bug is a match-fixing vector."""
    panel = PANELS[game_name]
    report: dict[str, Any] = {"game": game_name, "checks": {}}

    # 1. DETERMINISM -- same seed + same actors must replay byte-identical.
    a = run_match(game_name, {"A": list(panel.values())[0](), "B": list(panel.values())[-1]()}, 1, config)
    b = run_match(game_name, {"A": list(panel.values())[0](), "B": list(panel.values())[-1]()}, 1, config)
    a.pop("slowest_turn_s"); b.pop("slowest_turn_s")
    report["checks"]["deterministic"] = json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)

    # 2. SEAT FAIRNESS -- one strategy against itself must not favour a seat.
    # Must use a STOCHASTIC reference bot: two identical deterministic bots in a
    # simultaneous game tie every contest and score 0-0, which passes vacuously.
    ref = REFS[game_name]
    tot = {"A": 0.0, "B": 0.0}
    for s in seeds:
        r = run_match(game_name, {"A": ref(), "B": ref()}, s, config)
        tot["A"] += r["scores"]["A"]; tot["B"] += r["scores"]["B"]
    denom = abs(tot["A"]) + abs(tot["B"])
    report["checks"]["seat_bias"] = round(abs(tot["A"] - tot["B"]) / denom, 4) if denom else None
    report["checks"]["seat_fair"] = denom > 0 and report["checks"]["seat_bias"] < 0.05

    # 3. DEGENERACY -- the panel must separate. All-ties or one-bot-dominates fails.
    names = list(panel)
    table = {n: {"score": 0.0, "wins": 0, "losses": 0, "draws": 0} for n in names}
    for i, na in enumerate(names):
        for nb in names[i + 1:]:
            t = pairing(game_name, panel[na], panel[nb], seeds, config)
            table[na]["score"] += t["a"]; table[nb]["score"] += t["b"]
            if t["a"] > t["b"]:
                table[na]["wins"] += 1; table[nb]["losses"] += 1
            elif t["b"] > t["a"]:
                table[nb]["wins"] += 1; table[na]["losses"] += 1
            else:
                table[na]["draws"] += 1; table[nb]["draws"] += 1
    report["standings"] = dict(sorted(table.items(), key=lambda kv: -kv[1]["score"]))
    spread = [v["wins"] for v in table.values()]
    report["checks"]["separates"] = len(set(spread)) > 1
    report["checks"]["no_dominant_baseline"] = max(spread) < len(names) - 1

    if verbose:
        print(json.dumps(report, indent=2))
    return report


def main(argv):
    cmd = argv[0] if argv else "panel"
    if cmd == "watch":
        g, a, b, seed = argv[1], argv[2], argv[3], int(argv[4] if len(argv) > 4 else 1)
        panel = PANELS[g]
        r = run_match(g, {"A": panel[a](), "B": panel[b]()}, seed, watch=True)
        print(json.dumps(r, indent=2))
    elif cmd == "vet":
        vet(argv[1])
    elif cmd == "panel":
        vet(argv[1] if len(argv) > 1 else "ten_fronts")
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
