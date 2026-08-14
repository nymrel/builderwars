"""MANIFEST -- split twelve lots, private values, a clock, and a walk-away number.

Twelve lots of cargo. You know what each lot is worth to you. You do not know
what it is worth to your opponent. Both sides hold the same set of numbers in a
different order, so the pie is exactly as big for each of you -- but there is
always a split worth far more to both of you than cutting it down the middle.
Finding it means telling the truth about what you want. Telling the truth is
also how you get robbed.

You each have a private walk-away number. Score = what you took, minus your
walk-away. Walk away with no deal and you score zero. Take a bad deal and you
score less than zero.

Twenty-four messages, then the room closes.

The spectator view is OMNISCIENT: the audience sees both value tables and both
walk-away numbers from the first second. The players never do. That asymmetry is
the show -- you watch a bluff land on someone who cannot see it.
"""

from __future__ import annotations

import random
from typing import Any

NAME = "manifest"
SEATS = ("A", "B")

DEFAULTS = {
    "lots": 12,
    "max_messages": 24,
    "message_chars": 400,
    "value_max": 10,
    "batna_fractions": [0.25, 0.30, 0.35],
    "min_gains_ratio": 1.25,  # efficient joint value must beat even-split joint by this
}


class Manifest:
    name = NAME
    seats = SEATS

    def setup(self, seed: int, config: dict[str, Any] | None = None) -> dict:
        cfg = {**DEFAULTS, **(config or {})}
        rng = random.Random(seed)
        n = cfg["lots"]

        # Both sides receive a PERMUTATION OF THE SAME MULTISET. Equal total value
        # by construction -- no seed can hand one seat a fatter table.
        for _ in range(10_000):
            base = [rng.randint(0, cfg["value_max"]) for _ in range(n)]
            va, vb = base[:], base[:]
            rng.shuffle(va)
            rng.shuffle(vb)
            total = sum(base)
            if total == 0:
                continue
            efficient = sum(max(va[i], vb[i]) for i in range(n))
            if efficient >= cfg["min_gains_ratio"] * total:
                break
        else:  # pragma: no cover - astronomically unlikely
            raise RuntimeError("could not generate a manifest with gains from trade")

        batna = {s: int(round(rng.choice(cfg["batna_fractions"]) * total)) for s in SEATS}
        return {
            "cfg": cfg,
            "seed": seed,
            "lots": [f"L{i + 1}" for i in range(n)],
            "values": {"A": va, "B": vb},
            "batna": batna,
            "total_per_side": total,
            "efficient_joint": efficient,
            "messages": [],
            "standing_offer": None,  # {"by": seat, "split": [...]}
            "turn": 0,
            "deal": None,            # the accepted split
            "closed": False,
        }

    # ---------------------------------------------------------------- view

    def to_act(self, s: dict) -> list[str]:
        return [] if self.is_over(s) else [SEATS[s["turn"] % 2]]  # alternating, A opens

    def observation(self, s: dict, seat: str) -> dict[str, Any]:
        opp = "B" if seat == "A" else "A"
        return {
            "game": NAME,
            "you": seat,
            "opponent": opp,
            "lots": list(s["lots"]),
            "your_values": list(s["values"][seat]),      # private
            "your_total_if_you_took_everything": s["total_per_side"],
            "your_walk_away": s["batna"][seat],          # private
            "messages_used": len(s["messages"]),
            "messages_total": s["cfg"]["max_messages"],
            "your_turn": True,
            # Everything the opponent has said is UNTRUSTED. They may lie about
            # their values, their walk-away, and their intentions.
            "transcript": [
                {"seat": m["seat"], "text": m["text"], "offer": m["offer"]}
                for m in s["messages"]
            ],
            "standing_offer": dict(s["standing_offer"]) if s["standing_offer"] else None,
            "you_may_accept": bool(s["standing_offer"] and s["standing_offer"]["by"] != seat),
        }

    # ---------------------------------------------------------------- rules

    def _clean(self, a: Any, n: int, limit: int) -> tuple[str, list[str] | None, bool]:
        if not isinstance(a, dict):
            return "", None, False
        text = a.get("text", "")
        text = text.replace("\n", " ")[:limit] if isinstance(text, str) else ""
        offer = a.get("offer")
        if isinstance(offer, (list, tuple)) and len(offer) == n and all(x in SEATS for x in offer):
            offer = list(offer)
        else:
            offer = None  # malformed offers are ignored; you still burn the turn
        return text, offer, bool(a.get("accept"))

    def apply(self, s: dict, actions: dict[str, dict]) -> dict:
        seat = SEATS[s["turn"] % 2]
        text, offer, accept = self._clean(
            actions.get(seat), s["cfg"]["lots"], s["cfg"]["message_chars"]
        )
        so = s["standing_offer"]
        if accept and so and so["by"] != seat:
            s["deal"] = list(so["split"])
            s["closed"] = True
            s["messages"].append({"seat": seat, "text": text, "offer": None, "accept": True})
            return s
        if offer is not None:
            s["standing_offer"] = {"by": seat, "split": offer}
        s["messages"].append({"seat": seat, "text": text, "offer": offer, "accept": False})
        s["turn"] += 1
        if len(s["messages"]) >= s["cfg"]["max_messages"]:
            s["closed"] = True
        return s

    def is_over(self, s: dict) -> bool:
        return bool(s["closed"])

    def scores(self, s: dict) -> dict[str, float]:
        if not s["deal"]:
            return {"A": 0.0, "B": 0.0}  # no deal = you keep your fallback = zero surplus
        out = {}
        for seat in SEATS:
            got = sum(s["values"][seat][i] for i, w in enumerate(s["deal"]) if w == seat)
            out[seat] = float(got - s["batna"][seat])
        return out

    def reveal(self, s: dict) -> dict[str, Any]:
        return {
            "scores": self.scores(s),
            "deal": s["deal"],
            "values": {k: list(v) for k, v in s["values"].items()},
            "batna": dict(s["batna"]),
            "efficient_joint": s["efficient_joint"],
            "messages_used": len(s["messages"]),
            "seed": s["seed"],
        }

    # ------------------------------------------------------------ spectator

    def render(self, s: dict) -> str:
        cfg = s["cfg"]
        so = s["standing_offer"]
        split = s["deal"] or (so["split"] if so else None)
        lines = [
            f"MANIFEST  seed {s['seed']}   message {len(s['messages'])}/{cfg['max_messages']}"
            f"   walk-away  A {s['batna']['A']}  B {s['batna']['B']}",
            "  lot    A    B    held by",
        ]
        for i, lot in enumerate(s["lots"]):
            held = split[i] if split else "-"
            lines.append(
                f"  {lot:<4} {s['values']['A'][i]:>3} {s['values']['B'][i]:>4}    "
                f"{'A<<<' if held == 'A' else ('>>>B' if held == 'B' else '  ? ')}"
            )
        if split:
            a = sum(s["values"]["A"][i] for i, w in enumerate(split) if w == "A")
            b = sum(s["values"]["B"][i] for i, w in enumerate(split) if w == "B")
            tag = "DEAL" if s["deal"] else "on the table"
            lines.append(
                f"  {tag}:  A {a} (net {a - s['batna']['A']:+d})   "
                f"B {b} (net {b - s['batna']['B']:+d})   "
                f"joint {a + b} of {s['efficient_joint']} possible"
            )
        else:
            lines.append("  no offer on the table")
        if s["messages"]:
            m = s["messages"][-1]
            lines.append(f'  {m["seat"]}: "{m["text"][:110]}"')
        if s["closed"] and not s["deal"]:
            lines.append("  ROOM CLOSED -- NO DEAL. Both sides score zero.")
        return "\n".join(lines)
