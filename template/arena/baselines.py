"""Sparring partners.

These are the bots your entrant practises against, and the bots the arena uses
to prove a submitted game is not degenerate. None of them call a model. They are
deliberately simple and deliberately beatable -- if your harness cannot beat
`counter_last` at Ten Fronts or `shader` at Manifest, it is not ready.

They also serve as the DEGENERACY PANEL. A game where every baseline ties, or
where one dumb baseline dominates, is a broken game.
"""

from __future__ import annotations

import random
import re
import zlib
from typing import Any


# ---------------------------------------------------------------- utilities

def proportional(weights: list[float], total: int) -> list[int]:
    """Largest-remainder apportionment. Always sums to exactly `total`."""
    s = sum(weights)
    if s <= 0:
        weights = [1.0] * len(weights)
        s = float(len(weights))
    raw = [w / s * total for w in weights]
    out = [int(x) for x in raw]
    rem = total - sum(out)
    order = sorted(range(len(raw)), key=lambda i: raw[i] - out[i], reverse=True)
    for i in range(rem):
        out[order[i % len(order)]] += 1
    return out


def buy_greedy(values: list[int], costs: list[int], troops: int) -> list[int]:
    """Buy the best value-per-troop fronts you can afford; dump the rest on the
    most valuable front you already hold."""
    n = len(values)
    order = sorted(range(n), key=lambda f: values[f] / max(costs[f], 1), reverse=True)
    alloc, budget, bought = [0] * n, troops, []
    for f in order:
        if costs[f] <= budget:
            alloc[f] = costs[f]
            budget -= costs[f]
            bought.append(f)
    if budget:
        target = max(bought, key=lambda f: values[f]) if bought else 0
        alloc[target] += budget
    return alloc


CLAIM_RE = re.compile(r"CLAIM:\[([0-9,\s]+)\]")


def parse_claim(text: str, n: int) -> list[int] | None:
    m = CLAIM_RE.search(text or "")
    if not m:
        return None
    try:
        vals = [int(x) for x in m.group(1).split(",")]
    except ValueError:
        return None
    return vals if len(vals) == n else None


# ------------------------------------------------------------- TEN FRONTS

class _TF:
    def on_match_start(self, rules) -> None:
        # The match seed is PUBLIC and handed to both seats, so a stochastic
        # entrant can still be replayed exactly when debugging.
        # NB: never seed from hash() -- Python salts it per process, so your bot
        # would be irreproducible across runs. crc32 of a string is stable.
        key = f"{rules.config.get('seed', 0)}|{rules.seat}|{type(self).__name__}"
        self.rng = random.Random(zlib.crc32(key.encode()))

    def on_match_end(self, result) -> None:
        pass


class Uniform(_TF):
    """Spreads evenly. Should LOSE to anything that concentrates."""

    def act(self, obs, deadline_s):
        if obs["phase"] == "signal":
            return {"signal": "even across the board"}
        return {"alloc": proportional([1.0] * obs["fronts"], obs["troops"])}


class ValueWeighted(_TF):
    """Troops proportional to what each front is worth."""

    def act(self, obs, deadline_s):
        if obs["phase"] == "signal":
            return {"signal": "value first"}
        return {"alloc": proportional([float(v) for v in obs["front_values_this_round"]], obs["troops"])}


class Concentrate(_TF):
    """Abandons the cheap half, overwhelms the expensive half."""

    def act(self, obs, deadline_s):
        if obs["phase"] == "signal":
            return {"signal": "taking the big ones"}
        vals = obs["front_values_this_round"]
        keep = sorted(range(len(vals)), key=lambda f: vals[f], reverse=True)[: len(vals) // 2]
        w = [1.0 if f in keep else 0.0 for f in range(len(vals))]
        return {"alloc": proportional(w, obs["troops"])}


class CounterLast(_TF):
    """Assumes you will repeat yourself, and buys every front you left cheap.
    The reference opponent. If you cannot beat this, you are predictable."""

    def act(self, obs, deadline_s):
        if obs["phase"] == "signal":
            return {"signal": "reading your last move"}
        vals = obs["front_values_this_round"]
        n = len(vals)
        hist = obs["history"]
        last = hist[-1]["allocs"][obs["opponent"]] if hist else [obs["troops"] // n] * n
        return {"alloc": buy_greedy(vals, [x + 1 for x in last], obs["troops"])}


class Liar(_TF):
    """Announces an all-in on a front it intends to nearly abandon, then takes it
    with one troop if you believe the announcement."""

    def act(self, obs, deadline_s):
        vals = obs["front_values_this_round"]
        n = len(vals)
        self.mark = max(range(n), key=lambda f: vals[f])
        if obs["phase"] == "signal":
            return {"signal": f"everything on front {self.mark + 1}. do not bother contesting it."}
        w = [0.0 if f == self.mark else float(vals[f]) for f in range(n)]
        alloc = proportional(w, obs["troops"] - 1)
        alloc[self.mark] += 1
        return {"alloc": alloc}


class Gullible(_TF):
    """Takes the opponent at their word and concedes whatever they claim."""

    def act(self, obs, deadline_s):
        vals = obs["front_values_this_round"]
        n = len(vals)
        if obs["phase"] == "signal":
            return {"signal": "playing it straight"}
        said = obs.get("signals_this_round", {}).get(obs["opponent"], "")
        avoid = set()
        for m in re.finditer(r"front (\d+)", said.lower()):
            f = int(m.group(1)) - 1
            if 0 <= f < n:
                avoid.add(f)
        w = [0.0 if f in avoid else float(vals[f]) for f in range(n)]
        return {"alloc": proportional(w, obs["troops"])}


class Jitter(_TF):
    """Value-weighted with independent per-seat noise. The reference bot for the
    SEAT-FAIRNESS check: two deterministic bots mirrored against each other tie
    every front and score 0-0, which makes the check vacuous. A stochastic bot
    actually exercises both seats."""

    def act(self, obs, deadline_s):
        if obs["phase"] == "signal":
            return {"signal": "no comment"}
        w = [v + self.rng.random() * 2.5 for v in obs["front_values_this_round"]]
        return {"alloc": proportional(w, obs["troops"])}


class Broken(_TF):
    """Submits garbage. Exists to prove the forfeit rule bites."""

    def act(self, obs, deadline_s):
        return {"alloc": [1, 2, 3]} if obs["phase"] == "commit" else {"signal": "..."}


# --------------------------------------------------------------- MANIFEST

class _MF:
    inflate = 0

    def on_match_start(self, rules) -> None:
        self.n = 12

    def on_match_end(self, result) -> None:
        pass

    def _claimed(self, obs):
        vals = list(obs["your_values"])
        if self.inflate:
            top = sorted(range(len(vals)), key=lambda i: vals[i], reverse=True)[: len(vals) // 3]
            for i in top:
                vals[i] = min(10, vals[i] + self.inflate)
        return vals

    def _their_claim(self, obs):
        for m in reversed(obs["transcript"]):
            if m["seat"] == obs["opponent"]:
                c = parse_claim(m["text"], len(obs["your_values"]))
                if c:
                    return c
        return None

    def _efficient_split(self, obs, tilt: int):
        """Give each lot to whoever values it more; break near-ties toward self."""
        me, them = obs["you"], obs["opponent"]
        mine, theirs = obs["your_values"], self._their_claim(obs) or [5] * len(obs["your_values"])
        return [me if mine[i] + tilt >= theirs[i] else them for i in range(len(mine))]

    def _net(self, obs, split):
        return sum(obs["your_values"][i] for i, w in enumerate(split) if w == obs["you"]) - obs["your_walk_away"]

    def _should_accept(self, obs):
        so = obs["standing_offer"]
        if not (so and obs["you_may_accept"]):
            return False
        net = self._net(obs, so["split"])
        if net <= 0:
            return False
        left = obs["messages_total"] - obs["messages_used"]
        if left <= 2:
            return True  # buzzer: any surplus beats no deal
        # Patience decays linearly. Demand a lot early, take crumbs at the close.
        return net >= 0.45 * obs["your_total_if_you_took_everything"] * left / obs["messages_total"]


class EvenSplit(_MF):
    """Alternates the lots and calls it fair. Efficient? No. Fair? Also no."""

    def act(self, obs, deadline_s):
        if self._should_accept(obs):
            return {"accept": True, "text": "done."}
        me, them = obs["you"], obs["opponent"]
        return {"text": "straight down the middle.", "offer": [me if i % 2 == 0 else them for i in range(len(obs["your_values"]))]}


class Stonewall(_MF):
    """Demands everything, accepts nothing. The classic degeneracy probe: it can
    never lose money, only forgo it. The scoring must still rank it last."""

    def act(self, obs, deadline_s):
        return {"text": "all of it or nothing.", "offer": [obs["you"]] * len(obs["your_values"])}


class AcceptFirst(_MF):
    """Takes the first thing offered."""

    def act(self, obs, deadline_s):
        if obs["you_may_accept"]:
            return {"accept": True, "text": "fine."}
        return {"text": "make me an offer.", "offer": [obs["you"] if i % 2 else obs["opponent"] for i in range(len(obs["your_values"]))]}


class Honest(_MF):
    """States its true values and proposes the split that maximises joint value.
    Cooperative, efficient, and exploitable."""

    inflate = 0

    def act(self, obs, deadline_s):
        if self._should_accept(obs):
            return {"accept": True, "text": "agreed."}
        c = ",".join(str(v) for v in self._claimed(obs))
        return {"text": f"my true numbers. CLAIM:[{c}] -- best joint split attached.", "offer": self._efficient_split(obs, tilt=0)}


class Shader(_MF):
    """Same as Honest, but quietly inflates its top third and tilts ties its own
    way. The reference opponent for Manifest."""

    inflate = 3

    def act(self, obs, deadline_s):
        if self._should_accept(obs):
            return {"accept": True, "text": "acceptable."}
        c = ",".join(str(v) for v in self._claimed(obs))
        return {"text": f"here is where I actually am. CLAIM:[{c}]", "offer": self._efficient_split(obs, tilt=2)}


TEN_FRONTS_PANEL = {
    "uniform": Uniform, "value_weighted": ValueWeighted, "concentrate": Concentrate,
    "counter_last": CounterLast, "liar": Liar, "gullible": Gullible,
    "jitter": Jitter,
}
TEN_FRONTS_FAIRNESS_REF = Jitter
MANIFEST_FAIRNESS_REF = Shader
MANIFEST_PANEL = {
    "even_split": EvenSplit, "stonewall": Stonewall, "accept_first": AcceptFirst,
    "honest": Honest, "shader": Shader,
}
