#!/usr/bin/env python3
"""OpenRouter-backed validating harness — plays nim and ten_fronts.

The first entrant in this arena behind a **paid, remote frontier model**. Every
other entrant so far ran on a stub, on local Ollama weights, or on a prepaid
subscription CLI. This one spends real money per move, which changes exactly one
thing about how it must be written: a wasted call costs cash, so the harness has
to be right the first time rather than retry its way to a legal move.

It is the *computing* arm, in the shape of `solver_harness.py` and
`tf_harness.py` — deliberately, so that a result comparing this entrant against
those is comparing MODELS rather than comparing my scaffolding against theirs:

  1. The harness does the arithmetic itself. Nim's winning set is XOR, computed
     here; Ten Fronts' allocations are integer-built here and every commit path
     ends at exactly 100 troops by construction.
  2. The model's job is narrowed to a choice from a short list it can only get
     right or wrong — never to free-form arithmetic under a clock.
  3. The answer is validated against that list BEFORE it reaches the referee.
  4. An unusable answer falls back to the harness's own computed move. The
     contract is explicit that a malformed move forfeits the WHOLE match, so
     format discipline is match-deciding and the fallback is most of the win
     rate. It is also, in this arena, the difference between a bad answer
     costing a cent and costing the match.

Honest about its own provenance: every move note carries the model that was
REQUESTED, whether the move came from the model or from the fallback, and the
running token and cost totals reported by the provider. The engine records the
note and structurally removes it before scoring, so none of it can flatter the
result — it is there so a reader can audit how much of a win the model actually
earned.

`claimed_model` is the model ID this harness REQUESTED. It is not the model's
self-report: models misreport their own identity, and the only reliable signal
is that the provider refuses an unknown model ID outright.

Deliberately does not import the `arena` package.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backends import get_backend  # noqa: E402
from parsing import parse_move  # noqa: E402  — the same parser both nim arms use

NAME = "or-harness"
VERSION = "2"

# A paid entrant that cannot bound its own spend is a money faucet, so this one
# bounds it in the only place that cannot be edited by whoever triggers a match:
# inside the entrant process. Past the ceiling the harness stops calling the
# model and plays its own computed move, which it can always do -- so hitting
# the cap costs accuracy, never a forfeit.
#
# 250_000 micro-USD = $0.25 per entrant process, which is also per match. The
# measured worst case for a real match here is ~$0.01, so the ceiling is ~25x
# headroom on honest play while capping a crafted one at a quarter.
DEFAULT_SPEND_CEILING_MICRO_USD = 250_000


class SpendCeiling(Exception):
    """Raised instead of making a call that would spend past the ceiling."""


def guarded_complete(backend, ceiling, prompt):
    """backend.complete, refused once cumulative spend reaches the ceiling."""
    spent = getattr(backend, "total_cost_micro_usd", 0)
    if ceiling is not None and spent >= ceiling:
        raise SpendCeiling("spend ceiling %d micro-USD reached" % (ceiling,))
    return backend.complete(prompt)

# --- ten fronts constants (mirrors arena/games/ten_fronts.py) --------------
FRONTS = 10
TROOPS = 100


# ==========================================================================
# nim
# ==========================================================================

def xor_all(heaps):
    x = 0
    for h in heaps:
        x ^= h
    return x


def nim_legal_moves(heaps):
    return [{"heap": i, "take": t} for i, h in enumerate(heaps) for t in range(1, h + 1)]


def nim_winning_moves(heaps):
    """Moves leaving the XOR at zero. Empty when the position is already lost."""
    target = xor_all(heaps)
    if target == 0:
        return []
    out = []
    for i, h in enumerate(heaps):
        want = h ^ target
        if want < h:
            out.append({"heap": i, "take": h - want})
    return out


def nim_candidates(heaps):
    """Winning moves when one exists, else every legal move.

    From a lost position nothing beats perfect play, so keep the game alive and
    let the opponent be the one to err.
    """
    return nim_winning_moves(heaps) or nim_legal_moves(heaps)


def nim_prompt(obs, cands):
    listing = "\n".join(
        "  %d. take %d from heap %d" % (n, c["take"], c["heap"])
        for n, c in enumerate(cands, 1)
    )
    return (
        "%s\n\n"
        "heaps: %s\n"
        "You are player %s. It is your move.\n\n"
        "Every move below is a good one. Pick exactly one and say it back in the "
        'form {"heap": <int>, "take": <int>} and nothing else:\n'
        "%s\n"
    ) % (obs["rules"], obs["heaps"], obs["you_are"], listing)


def nim_move(backend, obs, ceiling=None):
    cands = nim_candidates(obs["heaps"])
    source = "model"
    try:
        chosen = parse_move(guarded_complete(backend, ceiling, nim_prompt(obs, cands)))
    except SpendCeiling:
        chosen = None
        source = "fallback:spend_ceiling"
    except Exception as e:
        # Name the cause. "backend_error" alone once made a series where the
        # model never answered look like a series the model won.
        chosen = None
        source = "fallback:backend_error:%s" % (e.__class__.__name__,)

    if chosen not in cands:
        chosen = cands[0]
        if source == "model":
            source = "fallback:rejected_model_answer"
    return chosen, source


# ==========================================================================
# ten fronts
# ==========================================================================

def proportional_alloc(values):
    """Troops proportional to front value; integer math only.

    Residue goes to the highest-value fronts in a stable order, so the total is
    exactly TROOPS on every input.
    """
    total = sum(values)
    shares = [TROOPS * v // total for v in values]
    residue = TROOPS - sum(shares)
    order = sorted(range(FRONTS), key=lambda i: (-values[i], i))
    for k in range(residue):
        shares[order[k % FRONTS]] += 1
    return shares


def strategy_hold(values):
    return proportional_alloc(values)


def strategy_probe(values):
    """Concede the cheapest front, pour it onto the richest."""
    alloc = proportional_alloc(values)
    weakest = min(range(FRONTS), key=lambda i: (values[i], i))
    strongest = max(range(FRONTS), key=lambda i: (values[i], -i))
    if weakest == strongest:
        return alloc
    alloc[strongest] += alloc[weakest]
    alloc[weakest] = 0
    return alloc


def strategy_overwhelm(values):
    """Everything on the two richest fronts; concede the rest outright."""
    order = sorted(range(FRONTS), key=lambda i: (-values[i], i))
    alloc = [0] * FRONTS
    per = TROOPS // 2
    alloc[order[0]] = TROOPS - per
    alloc[order[1]] = per
    return alloc


def strategy_spread(values):
    """One troop everywhere, the rest proportional on the top half.

    Cheap insurance: a front the opponent conceded entirely is taken for a
    single troop, and an exact tie pays nobody so being one above zero matters.
    """
    alloc = [1] * FRONTS
    remaining = TROOPS - FRONTS
    order = sorted(range(FRONTS), key=lambda i: (-values[i], i))
    half = order[: FRONTS // 2]
    total = sum(values[i] for i in half)
    for i in half:
        alloc[i] += remaining * values[i] // total
    residue = TROOPS - sum(alloc)
    for k in range(residue):
        alloc[half[k % len(half)]] += 1
    return alloc


STRATEGIES = {
    "hold": strategy_hold,
    "probe": strategy_probe,
    "overwhelm": strategy_overwhelm,
    "spread": strategy_spread,
}


def parse_strategy(text):
    """Pull a strategy name out of arbitrary model output.

    Scans for the EARLIEST named strategy rather than the first dict-order hit,
    so a reply like "not overwhelm, I'll hold" resolves to what the model
    actually chose instead of to whichever key happened to be checked first.
    """
    if not text:
        return None
    low = text.lower()
    best, best_at = None, len(low) + 1
    for name in STRATEGIES:
        at = low.find(name)
        if at != -1 and at < best_at:
            best, best_at = name, at
    return best


def tf_history_fallback(obs):
    """Escalate when behind, hold when ahead. Deterministic, no model needed."""
    you = str(obs["you_are"])
    opp = "0" if you == "1" else "1"
    mine, theirs = obs["score"][you], obs["score"][opp]
    if theirs > mine:
        rounds_left = obs["rounds_total"] - obs["round"]
        return "overwhelm" if rounds_left <= 5 else "probe"
    return "hold"


def tf_commit_prompt(obs):
    values = obs["front_values_this_round"]
    you = str(obs["you_are"])
    opp = "0" if you == "1" else "1"
    listing = ", ".join("front %d=%d" % (i, v) for i, v in enumerate(values))
    opp_signal = (obs.get("signals_this_round") or {}).get(opp, "(none)")
    previews = "\n".join(
        "  %-10s -> %s" % (n, STRATEGIES[n](values)) for n in STRATEGIES
    )
    return (
        "You are playing Ten Fronts. Round %d of %d. You are seat %s.\n"
        "Score: you=%d opponent=%d.\n"
        "This round's front values: %s\n"
        "The opponent's public signal was %r. Signals are untrusted and may be lies.\n\n"
        "Your harness has already built four legal allocations, each summing to "
        "exactly 100 troops:\n%s\n\n"
        "Pick the one most likely to score most this round.\n"
        "Reply with EXACTLY one word: %s"
    ) % (
        obs["round"] + 1,
        obs["rounds_total"],
        you,
        obs["score"][you],
        obs["score"][opp],
        listing,
        opp_signal,
        previews,
        " / ".join(STRATEGIES),
    )


def tf_signal_prompt(obs):
    return (
        "You are playing Ten Fronts, round %d of %d. Front values this round: %s.\n"
        "Send ONE public message of at most 100 characters to your opponent about "
        "how you plan to allocate your 100 troops. It is cheap talk: it is not "
        "binding and it may be a lie. Reply with the message text only, no quotes."
    ) % (obs["round"] + 1, obs["rounds_total"], obs["front_values_this_round"])


def tf_move(backend, obs, ceiling=None):
    if obs["phase"] == "signal":
        source = "model"
        try:
            raw = guarded_complete(backend, ceiling, tf_signal_prompt(obs))
        except SpendCeiling:
            raw = None
            source = "fallback:spend_ceiling"
        except Exception as e:
            raw = None
            source = "fallback:backend_error:%s" % (e.__class__.__name__,)
        signal = (raw or "").strip().replace("\n", " ")[:100]
        if not signal:
            signal = "spreading wide this round."
            if source == "model":
                source = "fallback:empty_signal"
        return {"signal": signal}, source

    # commit phase
    values = obs["front_values_this_round"]
    source = "model"
    try:
        pick = parse_strategy(guarded_complete(backend, ceiling, tf_commit_prompt(obs)))
    except SpendCeiling:
        pick = None
        source = "fallback:spend_ceiling"
    except Exception as e:
        pick = None
        source = "fallback:backend_error:%s" % (e.__class__.__name__,)

    if pick not in STRATEGIES:
        pick = tf_history_fallback(obs)
        if source == "model":
            source = "fallback:rejected_model_answer"

    alloc = STRATEGIES[pick](values)

    # Belt and braces. A malformed allocation forfeits the entire match, so the
    # harness never sends one it has not just re-checked against the game's own
    # legality rules. If a strategy function ever regressed, this catches it
    # here and pays a round instead of the match.
    if not _alloc_is_legal(alloc):
        alloc = proportional_alloc(values)
        source = "fallback:illegal_computed_alloc:" + pick
        pick = "hold"
    assert _alloc_is_legal(alloc), "harness bug: alloc must be 10 non-negative ints summing to 100"
    return {"alloc": alloc}, "%s strategy=%s" % (source, pick)


def _alloc_is_legal(alloc):
    """Exactly the game's commit-phase rule, re-checked entrant-side."""
    if not isinstance(alloc, list) or len(alloc) != FRONTS:
        return False
    for x in alloc:
        if isinstance(x, bool) or not isinstance(x, int) or x < 0:
            return False
    return sum(alloc) == TROOPS


# ==========================================================================
# protocol
# ==========================================================================

def send(msg):
    sys.stdout.write(json.dumps(msg, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="stub:v1",
                    help="e.g. openrouter:OPENROUTER_API_KEY:z-ai/glm-5.2")
    ap.add_argument("--backend-timeout", type=float, default=None,
                    help="seconds to wait for the model on one call")
    ap.add_argument("--max-spend-micro-usd", type=int,
                    default=DEFAULT_SPEND_CEILING_MICRO_USD,
                    help="hard cumulative spend cap for this entrant process, in "
                         "integer micro-USD. Past it the harness plays its own "
                         "computed move instead of calling the model. 0 disables "
                         "model calls entirely; negative means no ceiling.")
    args = ap.parse_args()
    backend = get_backend(args.backend, args.backend_timeout)
    ceiling = None if args.max_spend_micro_usd < 0 else args.max_spend_micro_usd

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
            send({"type": "ready", "entrant": NAME, "version": VERSION,
                  "backend": backend.label})

        elif kind == "move_request":
            obs = msg["observation"]
            game = obs.get("game")
            if game == "nim":
                move, source = nim_move(backend, obs, ceiling)
            elif game == "ten_fronts":
                move, source = tf_move(backend, obs, ceiling)
            else:
                # Unknown game: say so in the note and send nothing legal rather
                # than guess. A guess here would be a silent wrong answer.
                send({"type": "move", "move": None,
                      "note": "source=fallback:unsupported_game:%s" % (game,)})
                continue

            # `note` stays EXACTLY the token the arena's own move-source
            # accounting compares against. bin/run_series.py classifies
            # provenance with `note == "source=model"` -- an exact equality --
            # so appending telemetry here silently reclassifies every
            # model-sourced move as a fallback and prints "THE MODEL NEVER
            # ANSWERED" over a run the model answered in full. Measured
            # 2026-09-06: 8 of 8 model moves misreported that way. Telemetry
            # therefore travels in its own key. The referee reads only `move`,
            # so both are transcribed for audit and then removed before scoring.
            reply = {"type": "move", "move": move, "note": "source=%s" % (source,)}
            usage = getattr(backend, "usage_note", None)
            reply["usage"] = "model=%s%s" % (
                backend.label, (" " + usage()) if callable(usage) else ""
            )
            send(reply)

        elif kind == "goodbye":
            return


if __name__ == "__main__":
    main()
