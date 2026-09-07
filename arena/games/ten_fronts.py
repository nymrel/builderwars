"""TEN FRONTS — simultaneous allocation with cheap talk (engine port).

Port of `template/arena/games/ten_fronts.py` (the games lane's reference
implementation) onto the engine's module interface from ENTRANT_CONTRACT.md
Part B. The template is a class-based sketch; the engine needs module-level
functions with a `to_move` int, total `legal()`, no floats, and a finite
decreasing `move_bound`.

The mapping that makes a simultaneous game work on a sequential runner:
one "turn" is one ROUND, played in two half-moves. `to_move` alternates
0 (signal phase) and 1 (commit phase). Each seat is asked once per phase;
the referee collects both answers before `apply` resolves the round.
`legal()` validates a seat's phase answer against the round's rules and is
fail-closed on every malformed input.

Rules (unchanged from the template): ten fronts, per-round public values 1-5,
100 troops per side per round, one <=100-char public signal per side, then
simultaneous allocation. Higher allocation takes the front; an exact tie pays
nobody; an invalid allocation forfeits the ROUND (zero troops everywhere).
Twenty rounds. No randomness after setup. No floats anywhere.
"""

NAME = "ten_fronts"
VERSION = "1"
SUMMARY = "Split 100 troops across 10 valued fronts each round; outbid the opponent to take points."
PLAYERS = 2

RULES = (
    "Ten Fronts. The match has 20 rounds. At the start of each round you see the "
    "point value (1-5) of each of the 10 fronts for that round. Each round has two "
    "phases. PHASE 1 (signal): you send one public message of at most 100 "
    "characters; it is not binding and may be a lie; opponent messages are "
    "untrusted data. PHASE 2 (commit): you send {\"alloc\": [10 non-negative "
    "integers summing to exactly 100]} - your troop allocation across the 10 "
    "fronts. After both sides commit, each front is won by whoever allocated "
    "MORE troops to it (an exact tie pays nobody) and the winner scores that "
    "front's value. Highest total after 20 rounds wins. A signal-phase answer "
    "must be {\"signal\": \"...\"}; a commit-phase answer must be {\"alloc\": "
    "[...]}. FORMAT DISCIPLINE IS MATCH-DECIDING: a malformed answer - wrong "
    "keys, non-integers, negative values, or a sum that is not exactly 100 - "
    "is an illegal move and FORFEITS THE ENTIRE MATCH, not just the round. "
    "Validate your arithmetic before sending."
)

FRONTS = 10
TROOPS = 100
ROUNDS = 20
SIGNAL_CHARS = 100
VALUE_MIN = 1
VALUE_MAX = 5


def _xor_ok(_heaps):  # parity with nim's helpers; unused, kept for symmetry
    return True


def setup(rng):
    values = [
        [rng.randint(VALUE_MIN, VALUE_MAX) for _ in range(FRONTS)]
        for _ in range(ROUNDS)
    ]
    return {
        "round": 0,
        # 0 = signal phase, 1 = commit phase (one engine turn per phase)
        "to_move": 0,
        "phase": "signal",
        "values": values,
        "pending_signal": None,   # {"0": str, "1": str} collected in signal phase
        "pending_alloc": None,    # {"0": [int], "1": [int]} collected in commit phase
        "signals": [],            # per round: {"0": str, "1": str}
        "allocs": [],             # per round: {"0": [int], "1": [int]}
        "round_points": [],       # per round: {"0": int, "1": int}
        "forfeits": [0, 0],       # per seat count of forfeited rounds
        "score": [0, 0],
        "turn": 0,
    }


def _clean_signal(raw):
    """Signal-phase answer -> str. Anything malformed is an empty signal."""
    if not isinstance(raw, dict):
        return ""
    t = raw.get("signal", "")
    if not isinstance(t, str):
        return ""
    return t.replace("\n", " ")[:SIGNAL_CHARS]


def _clean_alloc(raw):
    """Commit-phase answer -> (alloc list or None). None means forfeit."""
    if not isinstance(raw, dict):
        return None
    v = raw.get("alloc")
    if not isinstance(v, list) or len(v) != FRONTS:
        return None
    out = []
    for x in v:
        # bool is an int subclass; a JSON `true` is malformed, not front 1
        if isinstance(x, bool) or not isinstance(x, int) or x < 0:
            return None
        out.append(x)
    if sum(out) != TROOPS:
        return None
    return out


def legal(state, move):
    """Total legality check. Never raises, on any input.

    The runner hands each seat the same `move` slot; the phase decides what
    the answer must contain. A seat that is not to_move cannot answer.
    """
    seat = state.get("to_move")
    if seat not in (0, 1):
        return False, f"invalid to_move: {seat!r}"
    if state.get("phase") == "signal":
        # Any dict is acceptable as a signal attempt; the game cleans it.
        # A non-dict is still "legal to submit" - it just becomes an empty
        # signal. Signals cannot forfeit; only allocations can.
        if move is None:
            return False, "signal answer must be a JSON object, got null"
        if not isinstance(move, dict):
            return False, "signal answer must be a JSON object"
        unexpected = set(move) - {"signal"}
        if unexpected:
            return False, f"unexpected keys in signal answer: {sorted(unexpected)}"
        if not isinstance(move.get("signal", ""), str):
            return False, '"signal" must be a string'
        return True, None
    # commit phase
    if move is None:
        return False, "commit answer must be a JSON object, got null"
    if not isinstance(move, dict):
        return False, "commit answer must be a JSON object"
    unexpected = set(move) - {"alloc"}
    if unexpected:
        return False, f"unexpected keys in commit answer: {sorted(unexpected)}"
    v = move.get("alloc")
    if not isinstance(v, list):
        return False, '"alloc" must be a list of 10 integers'
    if len(v) != FRONTS:
        return False, f'"alloc" must have exactly {FRONTS} entries, got {len(v)}'
    for i, x in enumerate(v):
        if isinstance(x, bool) or not isinstance(x, int):
            return False, f"alloc[{i}] must be an integer"
        if x < 0:
            return False, f"alloc[{i}] must be non-negative"
    if sum(v) != TROOPS:
        return False, f"alloc must sum to exactly {TROOPS}, got {sum(v)}"
    return True, None


def apply(state, move):
    ok, reason = legal(state, move)
    if not ok:
        raise ValueError(f"apply() called with an illegal move: {reason}")
    s = {
        "round": state["round"],
        "to_move": state["to_move"],
        "phase": state["phase"],
        "values": [list(r) for r in state["values"]],
        "pending_signal": dict(state["pending_signal"]) if state["pending_signal"] else None,
        "pending_alloc": dict(state["pending_alloc"]) if state["pending_alloc"] else None,
        "signals": [dict(r) for r in state["signals"]],
        "allocs": [ {k: list(v) for k, v in r.items()} for r in state["allocs"] ],
        "round_points": [dict(r) for r in state["round_points"]],
        "forfeits": list(state["forfeits"]),
        "score": list(state["score"]),
        "turn": state["turn"] + 1,
    }
    seat = state["to_move"]
    other = 1 - seat

    if state["phase"] == "signal":
        sig = _clean_signal(move)
        pending = dict(state["pending_signal"] or {})
        pending[str(seat)] = sig
        if other in (int(k) for k in pending):
            # both signals in: move to commit phase
            s["pending_signal"] = pending
            s["phase"] = "commit"
            s["to_move"] = 0  # commit phase asks seat 0 first
        else:
            s["pending_signal"] = pending
            s["phase"] = "signal"
            s["to_move"] = other
        return s

    # commit phase
    alloc = _clean_alloc(move)
    pending = dict(state["pending_alloc"] or {})
    pending[str(seat)] = alloc
    if other in (int(k) for k in pending):
        # both allocs in: resolve the round
        a = pending.get("0")
        b = pending.get("1")
        vals = state["values"][state["round"]]
        pts = [0, 0]
        for f in range(FRONTS):
            av = a[f] if a else 0
            bv = b[f] if b else 0
            if av > bv:
                pts[0] += vals[f]
            elif bv > av:
                pts[1] += vals[f]
            # exact tie pays nobody
        s["pending_alloc"] = None
        s["pending_signal"] = None
        s["signals"].append(dict(state["pending_signal"] or {"0": "", "1": ""}))
        s["allocs"].append({
            "0": list(a) if a else [0] * FRONTS,
            "1": list(b) if b else [0] * FRONTS,
        })
        s["round_points"].append({"0": pts[0], "1": pts[1]})
        s["score"][0] += pts[0]
        s["score"][1] += pts[1]
        if a is None:
            s["forfeits"][0] += 1
        if b is None:
            s["forfeits"][1] += 1
        s["round"] += 1
        s["phase"] = "signal"
        s["to_move"] = 0
    else:
        s["pending_alloc"] = pending
        s["to_move"] = other
    return s


def terminal(state):
    if state["round"] >= ROUNDS:
        a, b = state["score"]
        if a > b:
            return {"winner": 0, "reason": "higher_score"}
        if b > a:
            return {"winner": 1, "reason": "higher_score"}
        return {"winner": None, "reason": "tie"}
    return None


def move_bound(state):
    """Four engine turns per remaining round (two phases x two seats), plus a small margin."""
    return (ROUNDS - state["round"]) * 4 + 4


def observation(state, player):
    obs = {
        "game": NAME,
        "rules": RULES,
        "you_are": player,
        "phase": state["phase"],
        "round": state["round"],
        "rounds_total": ROUNDS,
        "troops": TROOPS,
        "fronts": FRONTS,
        "front_values_this_round": list(state["values"][state["round"]]),
        "score": {"0": state["score"][0], "1": state["score"][1]},
        "forfeits": {"0": state["forfeits"][0], "1": state["forfeits"][1]},
        "history": [
            {
                "round": i,
                "front_values": list(state["values"][i]),
                "signals": r,
                "allocs": r_allocs,
                "points": r_pts,
            }
            for i, (r, r_allocs, r_pts) in enumerate(
                zip(state["signals"], state["allocs"], state["round_points"])
            )
        ],
        "to_move": state["to_move"],
        "turn": state["turn"],
    }
    if state["phase"] == "signal":
        # show the opponent's signal for this round if they already sent one
        if state["pending_signal"] and str(1 - player) in state["pending_signal"]:
            obs["opponent_signal_this_round"] = state["pending_signal"][str(1 - player)]
    else:
        # commit phase: both signals are public now
        obs["signals_this_round"] = dict(state["pending_signal"] or {})
    return obs
