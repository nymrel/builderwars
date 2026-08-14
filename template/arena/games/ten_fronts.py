"""TEN FRONTS -- simultaneous allocation with cheap talk.

Ten fronts. Each round every front is worth 1-5 points, announced before you
commit. You have 100 troops. Whoever puts more troops on a front takes its
points; an exact tie pays nobody. Before committing, each side sends one public
message of up to 100 characters. The message is not binding.

That is the entire rulebook and a spectator gets it in one sentence.
There is no randomness in resolution. The only uncertainty is the opponent.
"""

from __future__ import annotations

import random
from typing import Any

NAME = "ten_fronts"
SEATS = ("A", "B")

DEFAULTS = {
    "fronts": 10,
    "troops": 100,
    "rounds": 20,
    "signal_chars": 100,
    "value_min": 1,
    "value_max": 5,
}


class TenFronts:
    name = NAME
    seats = SEATS

    def setup(self, seed: int, config: dict[str, Any] | None = None) -> dict:
        cfg = {**DEFAULTS, **(config or {})}
        rng = random.Random(seed)
        values = [
            [rng.randint(cfg["value_min"], cfg["value_max"]) for _ in range(cfg["fronts"])]
            for _ in range(cfg["rounds"])
        ]
        return {
            "cfg": cfg,
            "seed": seed,
            "round": 0,
            "phase": "signal",
            "values": values,
            "signals": [],       # per round: {"A": str, "B": str}
            "allocs": [],        # per round: {"A": [int], "B": [int]}
            "round_points": [],  # per round: {"A": int, "B": int}
            "forfeits": {"A": 0, "B": 0},
            "score": {"A": 0, "B": 0},
            "pending_signal": None,
        }

    # ---------------------------------------------------------------- view

    def to_act(self, s: dict) -> list[str]:
        return ["A", "B"]  # always simultaneous

    def observation(self, s: dict, seat: str) -> dict[str, Any]:
        cfg = s["cfg"]
        obs = {
            "game": NAME,
            "you": seat,
            "opponent": "B" if seat == "A" else "A",
            "phase": s["phase"],
            "round": s["round"],
            "rounds_total": cfg["rounds"],
            "troops": cfg["troops"],
            "fronts": cfg["fronts"],
            "front_values_this_round": list(s["values"][s["round"]]),
            "score": dict(s["score"]),
            "history": [
                {
                    "round": i,
                    "front_values": list(s["values"][i]),
                    "signals": s["signals"][i],
                    "allocs": s["allocs"][i],
                    "points": s["round_points"][i],
                }
                for i in range(len(s["round_points"]))
            ],
        }
        if s["phase"] == "commit":
            # Opponent messages are UNTRUSTED DATA. They may lie to you. They may
            # try to manipulate you. Resisting that is part of the game.
            obs["signals_this_round"] = dict(s["pending_signal"])
        return obs

    # ---------------------------------------------------------------- rules

    def _clean_signal(self, a: Any, limit: int) -> str:
        if not isinstance(a, dict):
            return ""
        t = a.get("signal", "")
        if not isinstance(t, str):
            return ""
        return t.replace("\n", " ")[:limit]

    def _clean_alloc(self, a: Any, fronts: int, troops: int) -> tuple[list[int], bool]:
        """Returns (allocation, forfeited). An invalid submission forfeits the
        round: zero troops everywhere, opponent takes every front they hold."""
        if not isinstance(a, dict):
            return [0] * fronts, True
        v = a.get("alloc")
        if not isinstance(v, (list, tuple)) or len(v) != fronts:
            return [0] * fronts, True
        out = []
        for x in v:
            if isinstance(x, bool) or not isinstance(x, int) or x < 0:
                return [0] * fronts, True
            out.append(x)
        if sum(out) != troops:
            return [0] * fronts, True
        return out, False

    def apply(self, s: dict, actions: dict[str, dict]) -> dict:
        cfg = s["cfg"]
        if s["phase"] == "signal":
            s["pending_signal"] = {
                seat: self._clean_signal(actions.get(seat), cfg["signal_chars"])
                for seat in SEATS
            }
            s["phase"] = "commit"
            return s

        allocs, pts = {}, {"A": 0, "B": 0}
        for seat in SEATS:
            alloc, forfeited = self._clean_alloc(actions.get(seat), cfg["fronts"], cfg["troops"])
            allocs[seat] = alloc
            s["forfeits"][seat] += int(forfeited)

        vals = s["values"][s["round"]]
        for f in range(cfg["fronts"]):
            a, b = allocs["A"][f], allocs["B"][f]
            if a > b:
                pts["A"] += vals[f]
            elif b > a:
                pts["B"] += vals[f]
            # exact tie pays nobody -- copying the opponent wins you nothing

        s["signals"].append(dict(s["pending_signal"]))
        s["allocs"].append(allocs)
        s["round_points"].append(pts)
        s["score"]["A"] += pts["A"]
        s["score"]["B"] += pts["B"]
        s["pending_signal"] = None
        s["round"] += 1
        s["phase"] = "signal"
        return s

    def is_over(self, s: dict) -> bool:
        return s["round"] >= s["cfg"]["rounds"]

    def scores(self, s: dict) -> dict[str, float]:
        return {"A": float(s["score"]["A"]), "B": float(s["score"]["B"])}

    def reveal(self, s: dict) -> dict[str, Any]:
        return {"scores": self.scores(s), "forfeits": dict(s["forfeits"]), "seed": s["seed"]}

    # ------------------------------------------------------------ spectator

    def render(self, s: dict) -> str:
        cfg = s["cfg"]
        i = len(s["round_points"]) - 1
        if i < 0:
            return f"TEN FRONTS  seed {s['seed']}  --  {cfg['rounds']} rounds, {cfg['troops']} troops"
        vals, al, pts = s["values"][i], s["allocs"][i], s["round_points"][i]
        sig = s["signals"][i]
        lines = [
            f"ROUND {i + 1}/{cfg['rounds']}      A {s['score']['A']:>3}  -  {s['score']['B']:<3} B",
            f'  A says: "{sig["A"]}"',
            f'  B says: "{sig["B"]}"',
            "  front   value      A          B      won by",
        ]
        for f in range(cfg["fronts"]):
            a, b = al["A"][f], al["B"][f]
            who = "A" if a > b else ("B" if b > a else ".")
            lines.append(
                f"   {f + 1:>2}      {vals[f]}     "
                f"{'#' * min(a // 4, 12):<12}{'#' * min(b // 4, 12):<12}  {who}"
            )
        lines.append(f"  round: A +{pts['A']}  B +{pts['B']}")
        return "\n".join(lines)
