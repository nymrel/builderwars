#!/usr/bin/env python3
"""Run a deterministic round-robin AgentWars fantasy league.

The scheduler scales a two-seat replay engine by pairing 2–16 entrants across
formats, seeds, and both seat orders. It records execution declarations and
move-source notes as claims; neither is upgraded into model attestation.
"""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from arena.canonical import digest  # noqa: E402
from arena.match import run_customer_local_match as run_match, validate_manifest  # noqa: E402
from arena.replay import verify  # noqa: E402
from arena.transcript import load  # noqa: E402

FORMATS = ("fantasy_redraft", "fantasy_dynasty", "fantasy_qb_surge")
TOP_LEVEL_KEYS = frozenset({"league", "description", "entrants"})


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_config(value):
    _require(isinstance(value, dict), "league config must be an object")
    unexpected = set(value) - TOP_LEVEL_KEYS
    _require(not unexpected, f"league config has unexpected keys: {sorted(unexpected)}")
    league = value.get("league")
    _require(isinstance(league, str) and league.strip() and len(league) <= 120,
             "league must be a non-empty string of at most 120 characters")
    description = value.get("description", "")
    _require(isinstance(description, str) and len(description) <= 500,
             "description must be a string of at most 500 characters")
    entrants = value.get("entrants")
    _require(isinstance(entrants, list) and 2 <= len(entrants) <= 16,
             "entrants must contain between 2 and 16 manifests")

    normalized = []
    seen = set()
    for raw in entrants:
        _require(isinstance(raw, dict), "each entrant manifest must be an object")
        manifest = {
            "name": raw.get("name"),
            "cmd": raw.get("cmd"),
            "env": raw.get("env", []),
            "claimed_model": raw.get("claimed_model"),
            "execution_claim": raw.get("execution_claim"),
        }
        if set(raw) - set(manifest):
            raise ValueError(f"entrant manifest has unexpected keys: {sorted(set(raw) - set(manifest))}")
        validate_manifest(manifest)
        folded = manifest["name"].casefold()
        _require(folded not in seen, "entrant names must be unique, ignoring case")
        seen.add(folded)
        normalized.append(manifest)
    return {"league": league, "description": description, "entrants": normalized}


def load_config(path):
    with open(path, "r", encoding="utf-8") as fh:
        return validate_config(json.load(fh))


def final_scores(path):
    records = load(path)
    state = [record["body"]["state"] for record in records if record["kind"] == "state"][-1]
    by_id = {player["id"]: player for player in state["players"]}
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


def move_source_counts(path, pair):
    counts = {entrant["name"]: {"model": 0, "fallback": 0, "scripted": 0, "other": 0}
              for entrant in pair}
    for record in load(path):
        if record["kind"] != "move":
            continue
        body = record["body"]
        seat = body.get("player")
        if seat not in (0, 1):
            continue
        note = body.get("entrant_message", {}).get("note", "")
        if note.startswith("source=model"):
            source = "model"
        elif note.startswith("source=fallback"):
            source = "fallback"
        elif note.startswith("source=scripted"):
            source = "scripted"
        else:
            source = "other"
        counts[pair[seat]["name"]][source] += 1
    return counts


def truth_status(entrants):
    claims = {entrant["execution_claim"] for entrant in entrants}
    if claims == {"scripted"}:
        return "scripted_preseason"
    if claims == {"model"}:
        return "model_claimed_unattested"
    if claims == {"hybrid"}:
        return "model_influenced_unattested"
    return "mixed_unattested"


def _new_record(entrant):
    return {
        "wins": 0,
        "losses": 0,
        "ties": 0,
        "points": 0,
        "modelMoveClaims": 0,
        "fallbackMoves": 0,
        "scriptedMoves": 0,
        "otherMoves": 0,
    }


def run_league(config, *, formats, seeds, start_seed, out_dir, move_timeout_s=15.0):
    config = validate_config(config)
    _require(isinstance(formats, list) and formats, "formats must be a non-empty list")
    _require(len(formats) == len(set(formats)) and all(name in FORMATS for name in formats),
             "formats must be unique registered fantasy formats")
    ordered_formats = [name for name in FORMATS if name in formats]
    _require(isinstance(seeds, int) and not isinstance(seeds, bool) and 1 <= seeds <= 32,
             "seeds must be an integer from 1 through 32")
    _require(isinstance(start_seed, int) and not isinstance(start_seed, bool)
             and 0 <= start_seed <= 2_147_483_647,
             "start_seed must be an integer from 0 through 2147483647")
    _require(start_seed + seeds - 1 <= 2_147_483_647, "seed range exceeds 2147483647")
    _require(isinstance(move_timeout_s, (int, float)) and not isinstance(move_timeout_s, bool)
             and 0.1 <= move_timeout_s <= 900,
             "move timeout must be between 0.1 and 900 seconds")

    entrants = config["entrants"]
    format_rows = []
    sequence = 0
    for game_name in ordered_formats:
        standings = {entrant["name"]: _new_record(entrant) for entrant in entrants}
        matches = []
        for seed in range(start_seed, start_seed + seeds):
            for first in range(len(entrants)):
                for second in range(first + 1, len(entrants)):
                    original_pair = [entrants[first], entrants[second]]
                    for order in (0, 1):
                        pair = original_pair if order == 0 else list(reversed(original_pair))
                        match_dir = os.path.join(
                            os.path.abspath(out_dir), game_name, str(seed), f"{first}-{second}-{order}"
                        )
                        result = run_match(
                            game_name=game_name,
                            seed=seed,
                            entrants=pair,
                            out_dir=match_dir,
                            move_timeout_s=move_timeout_s,
                        )
                        report = verify(result["transcript"])
                        if report["verdict"] != "PASS":
                            raise RuntimeError(
                                f"unverified match {result['match_id']}: {report.get('errors', [])[:2]}"
                            )
                        scores = final_scores(result["transcript"])
                        sources = move_source_counts(result["transcript"], pair)
                        for seat, entrant in enumerate(pair):
                            row = standings[entrant["name"]]
                            row["points"] += scores[seat]
                            row["modelMoveClaims"] += sources[entrant["name"]]["model"]
                            row["fallbackMoves"] += sources[entrant["name"]]["fallback"]
                            row["scriptedMoves"] += sources[entrant["name"]]["scripted"]
                            row["otherMoves"] += sources[entrant["name"]]["other"]
                            if result["winner"] is None:
                                row["ties"] += 1
                            elif result["winner"] == seat:
                                row["wins"] += 1
                            else:
                                row["losses"] += 1
                        matches.append(
                            {
                                "sequence": sequence,
                                "matchId": result["match_id"],
                                "seed": seed,
                                "seat0": pair[0]["name"],
                                "seat1": pair[1]["name"],
                                "winner": pair[result["winner"]]["name"]
                                if result["winner"] is not None else None,
                                "scores": {pair[0]["name"]: scores[0], pair[1]["name"]: scores[1]},
                                "reason": result["reason"],
                                "chainHead": result["chain_head"],
                                "verified": True,
                                "modelAttested": False,
                                "executionClaimsAttested": False,
                                "executionClaims": {
                                    pair[0]["name"]: pair[0]["execution_claim"],
                                    pair[1]["name"]: pair[1]["execution_claim"],
                                },
                                "moveSourceClaims": sources,
                            }
                        )
                        sequence += 1
        table = sorted(
            ({"agent": name, **record} for name, record in standings.items()),
            key=lambda row: (-row["wins"], -row["ties"], -row["points"], row["agent"]),
        )
        format_rows.append({"game": game_name, "standings": table, "matches": matches})

    public_entrants = [
        {
            "name": entrant["name"],
            "claimedModel": entrant["claimed_model"],
            "executionClaim": entrant["execution_claim"],
            "manifestDigest": digest(entrant),
        }
        for entrant in entrants
    ]
    return {
        "product": "AgentWars fantasy football",
        "league": config["league"],
        "description": config["description"],
        "status": truth_status(entrants),
        "truthBoundary": (
            "Replay verifies rules, moves, state, and scoring. Entrant execution classes, "
            "claimed model names, and move-source notes are self-declared and hash-bound but "
            "not independently attested. Credentials remain inside entrant processes."
        ),
        "configDigest": digest({"league": config["league"], "entrants": entrants}),
        "modelAttested": False,
        "executionClaimsAttested": False,
        "entrants": public_entrants,
        "formats": format_rows,
    }


def main():
    parser = argparse.ArgumentParser(description="Run a replay-verified AgentWars fantasy league.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--json-out", default=None)
    parser.add_argument("--format", action="append", choices=FORMATS, dest="formats")
    parser.add_argument("--seeds", type=int, default=1)
    parser.add_argument("--start-seed", type=int, default=9200)
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()

    summary = run_league(
        load_config(args.config),
        formats=args.formats or list(FORMATS),
        seeds=args.seeds,
        start_seed=args.start_seed,
        out_dir=args.out,
        move_timeout_s=args.timeout,
    )
    rendered = json.dumps(summary, indent=2)
    if args.json_out:
        parent = os.path.dirname(os.path.abspath(args.json_out))
        os.makedirs(parent, exist_ok=True)
        with open(args.json_out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(rendered + "\n")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
