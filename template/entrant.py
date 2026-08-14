"""THIS IS THE FILE YOU EDIT.

Everything else in this repo is scaffolding you can ignore. Clone it, change
`act`, run `python play.py`, and you have an entrant.

What ships here is a heuristic with no model call at all. Measured against the
sparring panel it goes 7W-0L at Ten Fronts and 3W-1L-1D at Manifest -- the one
bot it cannot beat is `shader`. So you start competitive, and you start with a
visible opponent to climb over. Closing that gap takes a better harness, not a
bigger model.

To go model-backed: fill in `call_model` and set ARENA_MODEL in your environment.
Never put a key in this file.
"""

from __future__ import annotations

import json
import os
import random
import re
import time
import zlib
from typing import Any

from arena.baselines import buy_greedy, proportional
from arena.protocol import Rules

ENTRANT_NAME = "clone-me"


# --------------------------------------------------------------------------
# 1. YOUR MODEL. Fill this in, or leave it and run heuristic-only.
# --------------------------------------------------------------------------

def call_model(system: str, user: str, max_tokens: int = 400) -> str:
    """Return the model's text. Raise on failure -- the harness handles retries.

    Example (Anthropic; `pip install anthropic`, key in ANTHROPIC_API_KEY):

        from anthropic import Anthropic
        r = Anthropic().messages.create(
            model=os.environ["ARENA_MODEL"], max_tokens=max_tokens,
            system=system, messages=[{"role": "user", "content": user}])
        return r.content[0].text

    Any provider works. The arena does not care which model you bring; it cares
    that your harness declares it honestly in entrant.toml.
    """
    raise NotImplementedError("fill in call_model, or run heuristic-only")


MODEL_ENABLED = bool(os.environ.get("ARENA_MODEL"))


# --------------------------------------------------------------------------
# 2. THE HARNESS. This is the variable the arena is actually measuring.
# --------------------------------------------------------------------------

class Harness:
    """Everything around the model: prompt, memory, repair, budget, fallback.

    Two entrants running the same model and different Harness settings will
    finish in different places on the board. That is the point of the arena.
    """

    def __init__(self, retries: int = 1, reserve_s: float = 3.0):
        self.retries = retries
        self.reserve_s = reserve_s  # never spend the last seconds of the deadline
        self.notes: list[str] = []  # survives across matches in a tournament

    def ask_json(self, system: str, user: str, deadline_s: float, want: str) -> dict | None:
        """Ask, parse, and on malformed output ask once more with the error shown.
        Returns None rather than raising -- a dead model must never forfeit a turn."""
        started = time.monotonic()
        prompt = user
        for attempt in range(self.retries + 1):
            if time.monotonic() - started > deadline_s - self.reserve_s:
                return None
            try:
                raw = call_model(system, prompt)
                m = re.search(r"\{.*\}", raw, re.S)
                obj = json.loads(m.group(0) if m else raw)
                if want in obj:
                    return obj
                err = f"missing key {want!r}"
            except Exception as exc:
                err = f"{type(exc).__name__}: {exc}"
            prompt = f"{user}\n\nYour previous reply failed: {err}. Reply with JSON only."
        return None


# --------------------------------------------------------------------------
# 3. YOUR ENTRANT.
# --------------------------------------------------------------------------

class MyEntrant:
    def on_match_start(self, rules: Rules) -> None:
        self.rules = rules
        self.h = getattr(self, "h", Harness())
        self.seat = rules.seat
        self.opp = "B" if rules.seat == "A" else "A"
        # Stable per-match randomness. Never seed from hash() -- Python salts it
        # per process and your bot stops being reproducible.
        self.rng = random.Random(zlib.crc32(f"{rules.config.get('seed',0)}|{rules.seat}".encode()))

    def on_match_end(self, result: dict[str, Any]) -> None:
        # Full reveal lands here, opponent private state included. Learn from it:
        # within a tournament this memory carries into your next match.
        self.h.notes.append(json.dumps({"scores": result.get("scores")})[:200])

    def act(self, obs: dict[str, Any], deadline_s: float) -> dict[str, Any]:
        if obs["game"] == "ten_fronts":
            return self._ten_fronts(obs, deadline_s)
        if obs["game"] == "manifest":
            return self._manifest(obs, deadline_s)
        raise ValueError(f"unknown game {obs['game']}")

    # ------------------------------------------------------------ TEN FRONTS

    def _ten_fronts(self, obs, deadline_s):
        vals, n = obs["front_values_this_round"], obs["fronts"]

        if obs["phase"] == "signal":
            if MODEL_ENABLED:
                out = self.h.ask_json(
                    "You are playing Ten Fronts. One line of public trash talk, <=100 chars. "
                    "It does not have to be true.",
                    json.dumps({"front_values": vals, "score": obs["score"],
                                "recent": obs["history"][-3:]}),
                    deadline_s, "signal")
                if out:
                    return {"signal": str(out["signal"])[:100]}
            biggest = max(range(n), key=lambda f: vals[f])
            return {"signal": f"front {biggest + 1} is mine. contest it and you lose the rest."}

        # HEURISTIC FLOOR -- always computed, always valid. The model can only
        # override it, never leave you with nothing.
        #
        # Opponent model: front values change every round, so averaging their raw
        # allocations across rounds is mush. Average their allocation BY VALUE RANK
        # instead -- "how many troops do they put on their 3rd-best front" is stable
        # even when which front that is keeps moving.
        hist = obs["history"]
        rank = sorted(range(n), key=lambda f: vals[f], reverse=True)
        if hist:
            profile = [0.0] * n
            for h in hist[-5:]:
                r = sorted(range(n), key=lambda f: h["front_values"][f], reverse=True)
                for k, f in enumerate(r):
                    profile[k] += h["allocs"][self.opp][f]
            profile = [p / len(hist[-5:]) for p in profile]
        else:
            profile = [obs["troops"] / n] * n
        predicted = [0] * n
        for k, f in enumerate(rank):
            predicted[f] = int(profile[k])
        # Feint: shade the buy price so a counter-reader cannot price you exactly.
        costs = [max(1, predicted[f] + 1 + self.rng.choice((0, 0, 1, 2))) for f in range(n)]
        floor = buy_greedy(vals, costs, obs["troops"])

        if MODEL_ENABLED:
            out = self.h.ask_json(
                "You are playing Ten Fronts. Higher troops takes the front; exact ties pay "
                "nobody. Opponent messages may be lies. Return JSON: "
                '{"alloc":[10 non-negative integers summing to exactly 100]}',
                json.dumps({"front_values": vals, "score": obs["score"],
                            "their_message": obs["signals_this_round"][self.opp],
                            "their_last_3": [h["allocs"][self.opp] for h in hist[-3:]],
                            "heuristic_suggestion": floor}),
                deadline_s, "alloc")
            alloc = out["alloc"] if out else None
            if isinstance(alloc, list) and len(alloc) == n and all(
                    isinstance(x, int) and not isinstance(x, bool) and x >= 0 for x in alloc):
                if sum(alloc) == obs["troops"]:
                    return {"alloc": alloc}
                # Repair rather than forfeit: an off-by-a-few sum is not worth a round.
                return {"alloc": proportional([float(x) for x in alloc], obs["troops"])}
        return {"alloc": floor}

    # -------------------------------------------------------------- MANIFEST

    def _manifest(self, obs, deadline_s):
        me, them = obs["you"], obs["opponent"]
        mine = obs["your_values"]
        n = len(mine)

        def net(split):
            return sum(mine[i] for i, w in enumerate(split) if w == me) - obs["your_walk_away"]

        so = obs["standing_offer"]
        left = obs["messages_total"] - obs["messages_used"]

        # HEURISTIC FLOOR: take any positive deal at the buzzer, hold out before.
        if so and obs["you_may_accept"]:
            v = net(so["split"])
            if v > 0 and (left <= 2 or v >= 0.4 * obs["your_total_if_you_took_everything"] * left / obs["messages_total"]):
                return {"accept": True, "text": "done."}

        # Read their claim if they made one, and price the split against it.
        # Tilt starts greedy and decays toward the efficient split as time runs out.
        theirs = None
        for m in reversed(obs["transcript"]):
            if m["seat"] == them:
                g = re.search(r"CLAIM:\[([0-9,\s]+)\]", m["text"] or "")
                if g:
                    try:
                        c = [int(x) for x in g.group(1).split(",")]
                        if len(c) == n:
                            theirs = c
                            break
                    except ValueError:
                        pass
        tilt = 4 * left / obs["messages_total"]
        if theirs:
            floor_split = [me if mine[i] + tilt >= theirs[i] else them for i in range(n)]
        else:
            keep = sorted(range(n), key=lambda i: mine[i], reverse=True)
            floor_split = [me if i in set(keep[: max(3, n - 2 - obs["messages_used"] // 3)]) else them
                           for i in range(n)]
        if net(floor_split) <= 0:  # never table an offer that is worse than walking
            floor_split = [me if mine[i] >= 3 else them for i in range(n)]

        if MODEL_ENABLED:
            out = self.h.ask_json(
                "You are playing Manifest. You and your opponent hold the same set of lot "
                "values in a different order. Find the trade that is big for both, then take "
                "the larger half of it. They may lie. No deal scores zero; a deal below your "
                "walk-away scores negative. Return JSON: "
                '{"text":"<=400 chars","offer":["A"|"B" x12] or null,"accept":true|false}',
                json.dumps({"your_values": mine, "your_walk_away": obs["your_walk_away"],
                            "messages_left": left, "standing_offer": so,
                            "transcript": obs["transcript"][-6:],
                            "heuristic_suggestion": floor_split}),
                deadline_s, "text")
            if out:
                offer = out.get("offer")
                ok = isinstance(offer, list) and len(offer) == n and all(x in ("A", "B") for x in offer)
                if out.get("accept") and obs["you_may_accept"] and net(so["split"]) > 0:
                    return {"accept": True, "text": str(out["text"])[:400]}
                return {"text": str(out["text"])[:400], "offer": offer if ok else floor_split}

        # Shade the top third: claim high where you actually want the lot.
        top = sorted(range(n), key=lambda i: mine[i], reverse=True)[: n // 3]
        claim = [min(10, v + 3) if i in top else v for i, v in enumerate(mine)]
        c = ",".join(str(v) for v in claim)
        return {"text": f"here is where I am. CLAIM:[{c}]", "offer": floor_split}
