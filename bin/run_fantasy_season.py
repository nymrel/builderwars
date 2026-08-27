#!/usr/bin/env python3
"""Run the bounded AgentWars fantasy circuits and export honest receipts."""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from arena.match import run_match  # noqa: E402
from arena.replay import verify  # noqa: E402
from arena.transcript import load  # noqa: E402


def manifest(name, strategy):
    script = os.path.join(ROOT, "entrants", "fantasy_gm_harness.py")
    return {
        "name": name,
        "cmd": [sys.executable, script, "--name", name, "--strategy", strategy],
        "env": [],
        "claimed_model": "scripted-baseline:v1",
        "execution_claim": "scripted",
    }


def final_scores(path):
    records = load(path)
    state = [r["body"]["state"] for r in records if r["kind"] == "state"][-1]
    by_id = {p["id"]: p for p in state["players"]}
    key = "dynasty_points" if state["format"] == "dynasty" else "redraft_points"
    scores = [sum(by_id[player_id][key] for player_id in roster) for roster in state["rosters"]]
    if state["format"] == "qb_surge":
        for seat, roster in enumerate(state["rosters"]):
            scores[seat] += sum(
                by_id[player_id]["redraft_points"]
                for player_id in roster
                if by_id[player_id]["position"] == "QB"
            )
    return scores


def run_circuit(game, seeds, start_seed, out_dir, entrants):
    rows = []
    standings = {entrant["name"]: {"wins": 0, "losses": 0, "ties": 0, "points": 0} for entrant in entrants}
    for offset in range(seeds):
        seed = start_seed + offset
        for order in (0, 1):
            pair = entrants if order == 0 else list(reversed(entrants))
            result = run_match(
                game_name=game,
                seed=seed,
                entrants=pair,
                out_dir=os.path.join(out_dir, game, f"{seed}-{order}"),
            )
            report = verify(result["transcript"])
            if report["verdict"] != "PASS":
                raise RuntimeError(f"unverified fantasy match {result['match_id']}: {report['errors']}")
            scores = final_scores(result["transcript"])
            winner = result["winner"]
            for seat, entrant in enumerate(pair):
                standings[entrant["name"]]["points"] += scores[seat]
                if winner is None:
                    standings[entrant["name"]]["ties"] += 1
                elif winner == seat:
                    standings[entrant["name"]]["wins"] += 1
                else:
                    standings[entrant["name"]]["losses"] += 1
            rows.append(
                {
                    "matchId": result["match_id"],
                    "seed": seed,
                    "seat0": pair[0]["name"],
                    "seat1": pair[1]["name"],
                    "winner": pair[winner]["name"] if winner is not None else None,
                    "scores": {pair[0]["name"]: scores[0], pair[1]["name"]: scores[1]},
                    "reason": result["reason"],
                    "chainHead": result["chain_head"],
                    "verified": True,
                    "modelAttested": False,
                }
            )
    table = sorted(
        ({"agent": name, **record} for name, record in standings.items()),
        key=lambda row: (-row["wins"], -row["ties"], -row["points"], row["agent"]),
    )
    return {"game": game, "standings": table, "matches": rows}


def main():
    parser = argparse.ArgumentParser(description="Run replay-verified AgentWars fantasy proof circuits.")
    parser.add_argument("--seeds", type=int, default=4)
    parser.add_argument("--start-seed", type=int, default=9100)
    parser.add_argument("--out", required=True, help="directory for transcripts")
    parser.add_argument("--json-out", default=None, help="optional season summary path")
    args = parser.parse_args()
    if args.seeds < 1:
        parser.error("--seeds must be at least 1")

    entrants = [
        manifest("Sunday Machine", "win-now"),
        manifest("Future Proof", "long-game"),
    ]
    circuits = [
        run_circuit("fantasy_redraft", args.seeds, args.start_seed, args.out, entrants),
        run_circuit("fantasy_dynasty", args.seeds, args.start_seed, args.out, entrants),
        run_circuit("fantasy_qb_surge", args.seeds, args.start_seed, args.out, entrants),
    ]
    summary = {
        "product": "AgentWars fantasy football",
        "status": "scripted_preseason",
        "truthBoundary": (
            "These matches use deterministic scripted GM baselines. They prove the rules and replay "
            "receipts, not model identity, public participation, or predictive football accuracy."
        ),
        "formats": circuits,
    }
    rendered = json.dumps(summary, indent=2)
    if args.json_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.json_out)), exist_ok=True)
        with open(args.json_out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(rendered + "\n")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
