#!/usr/bin/env python3
"""Model-facing AgentWars Ten Fronts GM with a deterministic legal fallback.

This process, not the referee, owns inference. It never imports ``arena`` and
never receives a transcript path. Raw model output stays inside this process;
the receipt records only its digest and whether the accepted move came from the
model or the fallback. The fallback mirrors the game's public rules exactly, so
a model that stays silent can never forfeit on formatting.
"""

import argparse
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backends import get_backend  # noqa: E402

VERSION = "1"
STRATEGIES = ("value-blitz", "even-pressure")
MAX_MODEL_OUTPUT_CHARS = 4096

FRONTS = 10
TROOPS = 100
SIGNAL_MAX_CHARS = 100

# Mirror of arena.games.ten_fronts.OUTSIDE_MATCH_TOKENS. The harness must stay
# independent of the engine package, so this list is duplicated by hand; the
# deterministic check program asserts the two agree.
SURFACE_TOKENS = (
    "engine", "scorer", "referee", "judge", "arena", "verifier", "transcript",
    "standings", "leaderboard", "moderator", "admin", "operator",
    "system prompt", "api key", "credentials", "stdout", "stdin", "stderr",
    "subprocess", "filesystem", "database", "sudo",
)

_SURFACE_RE = re.compile(
    "|".join(r"\b" + re.escape(token) + r"\b" for token in SURFACE_TOKENS),
    re.IGNORECASE,
)


def send(message):
    sys.stdout.write(json.dumps(message, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def signal_is_clean(text):
    return _SURFACE_RE.search(text) is None


def signal_is_legal(text):
    return (
        isinstance(text, str)
        and len(text) <= SIGNAL_MAX_CHARS
        and signal_is_clean(text)
    )


def allocation_is_legal(alloc):
    return (
        isinstance(alloc, list)
        and len(alloc) == FRONTS
        and all(_is_int(t) and t >= 0 for t in alloc)
        and sum(alloc) == TROOPS
    )


def extract_strict_signal(raw):
    if not isinstance(raw, str) or not raw or len(raw) > MAX_MODEL_OUTPUT_CHARS:
        return None
    try:
        value = json.loads(raw.strip())
    except json.JSONDecodeError:
        return None
    if not isinstance(value, dict) or set(value) != {"signal"}:
        return None
    text = value["signal"]
    if not signal_is_legal(text):
        return None
    return {"signal": text}


def extract_strict_allocation(raw):
    if not isinstance(raw, str) or not raw or len(raw) > MAX_MODEL_OUTPUT_CHARS:
        return None
    try:
        value = json.loads(raw.strip())
    except json.JSONDecodeError:
        return None
    if not isinstance(value, dict) or set(value) != {"allocation"}:
        return None
    alloc = value["allocation"]
    if not allocation_is_legal(alloc):
        return None
    return {"allocation": list(alloc)}


def _largest_remainder(weights, total=TROOPS):
    weight_sum = sum(weights)
    base = [total * w // weight_sum for w in weights]
    order = sorted(range(FRONTS), key=lambda i: (-weights[i], i))
    for k in range(total - sum(base)):
        base[order[k]] += 1
    return base


def fallback_allocation(front_values, strategy):
    if strategy == "value-blitz":
        weights = [v * v for v in front_values]
    else:
        weights = [v for v in front_values]
    return _largest_remainder(weights)


def fallback_signal(strategy):
    if strategy == "value-blitz":
        return "Everything goes at the two most valuable fronts."
    return "Covering every front; no all-in bluffs from me."


def _history_tail(observation, keep=4):
    rows = observation.get("history") or []
    trimmed = []
    for row in rows[-keep:]:
        trimmed.append(
            {
                "round": row.get("round"),
                "values": row.get("values"),
                "signals": row.get("signals"),
                "allocations": row.get("allocations"),
                "points": row.get("points"),
            }
        )
    return trimmed


def build_prompt(observation, phase, strategy):
    context = {
        "phase": phase,
        "strategy": strategy,
        "round": observation.get("round"),
        "rounds_total": observation.get("rounds_total"),
        "you_are": observation.get("you_are"),
        "front_values": observation.get("front_values"),
        "troops": observation.get("troops"),
        "fronts": observation.get("fronts"),
        "scores": observation.get("scores"),
        "recent_history": _history_tail(observation),
        "channel_warning": observation.get("signal_channel_note"),
    }
    if phase == "signal":
        ask = (
            "Choose your public signal for this round. Return ONLY a JSON "
            'object with exactly one key, for example {"signal": "I will '
            'stack front 5"}. At most 100 characters. It may be a lie.'
        )
    else:
        ask = (
            f"Commit your troop allocation: {FRONTS} non-negative integers "
            f"summing to exactly {TROOPS}, one per front in order. Return ONLY "
            "a JSON object with exactly one key, for example "
            '{"allocation": [10,10,10,10,10,10,10,10,10,10]}. No prose or '
            "markdown."
        )
    return f"You are an AgentWars Ten Fronts commander.\n{ask}\n" + json.dumps(
        context, sort_keys=True, separators=(",", ":")
    )


def move_is_legal_for_observation(observation, move):
    if not isinstance(move, dict) or len(move) != 1:
        return False
    if "signal" in move:
        return observation.get("phase") == "signal" and signal_is_legal(move["signal"])
    if "allocation" in move:
        return (
            observation.get("phase") == "commit"
            and allocation_is_legal(move["allocation"])
        )
    return False


def decide(observation, strategy, backend):
    phase = observation.get("phase")
    extract = extract_strict_signal if phase == "signal" else extract_strict_allocation
    raw = None
    reason = "invalid_model_output"
    try:
        raw = backend.complete(build_prompt(observation, phase, strategy))
        move = extract(raw)
        if move_is_legal_for_observation(observation, move):
            response_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
            return move, f"source=model;response_sha256={response_hash}"
    except Exception as error:
        reason = f"backend_error:{error.__class__.__name__}"

    if phase == "signal":
        move = {"signal": fallback_signal(strategy)}
    else:
        values = observation.get("front_values")
        if not isinstance(values, list) or len(values) != FRONTS:
            values = [1] * FRONTS
        move = {"allocation": fallback_allocation(values, strategy)}

    if raw is not None and isinstance(raw, str):
        response_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        return move, f"source=fallback;reason={reason};response_sha256={response_hash}"
    return move, f"source=fallback;reason={reason}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", required=True)
    parser.add_argument("--backend-timeout", type=float, default=None)
    parser.add_argument("--strategy", choices=STRATEGIES, required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    backend = get_backend(args.backend, timeout_s=args.backend_timeout)

    for line in sys.stdin:
        if not line.strip():
            continue
        message = json.loads(line)
        if message.get("type") == "hello":
            send(
                {
                    "type": "ready",
                    "entrant": args.name,
                    "version": VERSION,
                    "backend": backend.label,
                }
            )
        elif message.get("type") == "move_request":
            move, note = decide(message.get("observation"), args.strategy, backend)
            send({"type": "move", "move": move, "note": note})
        elif message.get("type") == "goodbye":
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
