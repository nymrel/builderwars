#!/usr/bin/env python3
"""Contract and replay checks for the AgentWars fantasy games."""

import copy
import os
import random
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from arena.canonical import canonical_bytes  # noqa: E402
from arena.games import load  # noqa: E402
from arena.match import run_match  # noqa: E402
from arena.replay import verify  # noqa: E402


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def manifest(name, strategy):
    script = os.path.join(ROOT, "entrants", "fantasy_gm_harness.py")
    return {
        "name": name,
        "cmd": [sys.executable, script, "--name", name, "--strategy", strategy],
        "env": [],
        "claimed_model": "scripted-baseline:v1",
        "execution_claim": "scripted",
    }


def play_state(game, strategy):
    state = game.setup(random.Random(77))
    while game.terminal(state) is None:
        obs = game.observation(state, state["to_move"])
        key = "redraft_points" if strategy == "win-now" else "dynasty_points"
        legal = [p for p in obs["available_players"] if obs["needs"].get(p["position"], 0) > 0]
        move = {"player_id": max(legal, key=lambda p: (p[key], -p["id"]))["id"]}
        before = copy.deepcopy(state)
        ok, why = game.legal(state, move)
        require(ok, f"expected legal move: {why}")
        state = game.apply(state, move)
        require(before != state, "apply must advance state")
        require(game.setup(random.Random(77)) == game.setup(random.Random(77)), "setup must be deterministic")
    return state


def main():
    hostile = [None, True, 4, "4", [], {}, {"player_id": True}, {"player_id": "1"}, {"x": 1}]
    for name in ("fantasy_redraft", "fantasy_dynasty", "fantasy_qb_surge"):
        game = load(name)
        for seed in range(25):
            state = game.setup(random.Random(seed))
            canonical_bytes(state)
            require(len(state["available"]) == 20, "board must have 20 players")
            for move in hostile:
                ok, why = game.legal(state, move)
                require(ok is False and isinstance(why, str), f"legal() must reject total input: {move!r}")
        final = play_state(game, "win-now")
        require(final["turn"] == 12, "fantasy draft must end after 12 picks")
        require(game.terminal(final) is not None, "complete roster must be terminal")
        for roster in final["rosters"]:
            require(len(roster) == 6 and len(set(roster)) == 6, "each roster needs six unique players")

    entrants = [manifest("Sunday Machine", "win-now"), manifest("Future Proof", "long-game")]
    with tempfile.TemporaryDirectory(prefix="agentwars-fantasy-check-") as out:
        outcomes = {}
        for game_name in ("fantasy_redraft", "fantasy_dynasty", "fantasy_qb_surge"):
            winners = []
            first_chain = None
            for order in (0, 1):
                pair = entrants if order == 0 else list(reversed(entrants))
                result = run_match(game_name=game_name, seed=9100, entrants=pair, out_dir=os.path.join(out, game_name, str(order)))
                report = verify(result["transcript"])
                require(report["verdict"] == "PASS", f"{game_name} transcript must replay")
                winners.append(pair[result["winner"]]["name"] if result["winner"] is not None else None)
                if order == 0:
                    first_chain = result["chain_head"]
                    repeated = run_match(
                        game_name=game_name,
                        seed=9100,
                        entrants=pair,
                        out_dir=os.path.join(out, game_name, "repeat"),
                    )
                    require(repeated["chain_head"] == first_chain, f"{game_name} must be byte-deterministic")
            outcomes[game_name] = winners
        require(outcomes["fantasy_redraft"] != outcomes["fantasy_dynasty"], "formats must reward different strategy windows")
        surge = load("fantasy_qb_surge")
        surge_state = play_state(surge, "win-now")
        by_id = {row["id"]: row for row in surge_state["players"]}
        for seat, roster in enumerate(surge_state["rosters"]):
            base = sum(by_id[player_id]["redraft_points"] for player_id in roster)
            qb = sum(by_id[player_id]["redraft_points"] for player_id in roster if by_id[player_id]["position"] == "QB")
            require(surge.roster_score(surge_state, seat) == base + qb,
                    "QB Surge must count the roster quarterback exactly twice")

    print("AgentWars fantasy contracts: PASS")
    print(f"strategy split at seed 9100: {outcomes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
