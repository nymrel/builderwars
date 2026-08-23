#!/usr/bin/env python3
"""Scripted fantasy GM used to prove the game before any model plays it.

This entrant deliberately makes no model call. The season runner labels its
backend `scripted-baseline:v1`; those matches prove the rules, replay, and
strategy split, not model quality.
"""

import argparse
import json
import sys

VERSION = "1"


def send(message):
    sys.stdout.write(json.dumps(message, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def rank(player, strategy, available):
    key = "redraft_points" if strategy == "win-now" else "dynasty_points"
    value = player[key]
    same_position = sorted(
        (row[key] for row in available if row["position"] == player["position"]),
        reverse=True,
    )
    replacement = same_position[1] if len(same_position) > 1 else 0
    scarcity = value - replacement
    # Value dominates; scarcity breaks close calls and rewards a real draft
    # board over a raw sort.
    return value * 100 + scarcity * 12, -player["id"]


def choose(observation, strategy):
    needs = observation["needs"]
    available = observation["available_players"]
    legal = [row for row in available if needs.get(row["position"], 0) > 0]
    if not legal:
        return None
    player = max(legal, key=lambda row: rank(row, strategy, available))
    return {"player_id": player["id"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", choices=("win-now", "long-game"), required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()

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
                    "backend": "scripted-baseline:v1",
                }
            )
        elif message.get("type") == "move_request":
            move = choose(message["observation"], args.strategy)
            send(
                {
                    "type": "move",
                    "move": move,
                    "note": f"source=scripted_board;strategy={args.strategy}",
                }
            )
        elif message.get("type") == "goodbye":
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
