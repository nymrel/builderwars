#!/usr/bin/env python3
"""Model-facing AgentWars fantasy GM with a deterministic legal fallback.

This process, not the referee, owns inference. It never imports ``arena`` and
never receives a transcript path. Raw model output stays inside this process;
the receipt records only its digest and whether the accepted pick came from the
model or the fallback.
"""

import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backends import get_backend  # noqa: E402

VERSION = "1"
STRATEGIES = ("win-now", "long-game")
MAX_MODEL_OUTPUT_CHARS = 32768


def send(message):
    sys.stdout.write(json.dumps(message, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def legal_players(observation):
    if not isinstance(observation, dict):
        return []
    needs = observation.get("needs")
    available = observation.get("available_players")
    if not isinstance(needs, dict) or not isinstance(available, list):
        return []
    out = []
    for player in available:
        if not isinstance(player, dict):
            continue
        player_id = player.get("id")
        position = player.get("position")
        if (
            isinstance(player_id, int)
            and not isinstance(player_id, bool)
            and isinstance(position, str)
            and isinstance(needs.get(position), int)
            and not isinstance(needs.get(position), bool)
            and needs[position] > 0
        ):
            out.append(player)
    return out


def fallback_move(observation, strategy):
    players = legal_players(observation)
    if not players:
        return None
    key = "redraft_points" if strategy == "win-now" else "dynasty_points"

    def rank(player):
        value = player.get(key)
        if not isinstance(value, int) or isinstance(value, bool):
            value = -10**9
        peers = sorted(
            (
                row.get(key)
                for row in players
                if row.get("position") == player.get("position")
                and isinstance(row.get(key), int)
                and not isinstance(row.get(key), bool)
            ),
            reverse=True,
        )
        replacement = peers[1] if len(peers) > 1 else 0
        return value * 100 + (value - replacement) * 12, -player["id"]

    return {"player_id": max(players, key=rank)["id"]}


def build_prompt(observation, strategy):
    players = legal_players(observation)
    board = [
        {
            "player_id": row["id"],
            "name": str(row.get("name", ""))[:80],
            "position": row.get("position"),
            "redraft_points": row.get("redraft_points"),
            "dynasty_points": row.get("dynasty_points"),
            "age": row.get("age"),
        }
        for row in players
    ]
    context = {
        "format": observation.get("format"),
        "strategy": strategy,
        "round": observation.get("round"),
        "needs": observation.get("needs"),
        "your_roster": observation.get("your_roster"),
        "opponent_roster": observation.get("opponent_roster"),
        "legal_players": board,
    }
    return (
        "You are an AgentWars fantasy football GM. Pick exactly one legal player "
        f"using the {strategy} strategy. Return ONLY a JSON object with exactly one "
        "key, for example {\"player_id\": 12}. No prose or markdown.\n"
        + json.dumps(context, sort_keys=True, separators=(",", ":"))
    )


def extract_strict_move(raw):
    if not isinstance(raw, str) or not raw or len(raw) > MAX_MODEL_OUTPUT_CHARS:
        return None
    try:
        value = json.loads(raw.strip())
    except json.JSONDecodeError:
        return None
    if not isinstance(value, dict) or set(value) != {"player_id"}:
        return None
    player_id = value["player_id"]
    if not isinstance(player_id, int) or isinstance(player_id, bool):
        return None
    return {"player_id": player_id}


def move_is_legal_for_observation(observation, move):
    if not isinstance(move, dict):
        return False
    legal_ids = {row["id"] for row in legal_players(observation)}
    return move.get("player_id") in legal_ids


def decide(observation, strategy, backend):
    prompt = build_prompt(observation, strategy)
    raw = None
    reason = "invalid_model_output"
    try:
        raw = backend.complete(prompt)
        move = extract_strict_move(raw)
        if move_is_legal_for_observation(observation, move):
            response_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
            return move, f"source=model;response_sha256={response_hash}"
    except Exception as error:
        reason = f"backend_error:{error.__class__.__name__}"

    move = fallback_move(observation, strategy)
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
