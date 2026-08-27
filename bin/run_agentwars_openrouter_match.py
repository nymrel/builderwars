#!/usr/bin/env python3
"""Run one provider-pinned OpenRouter fantasy match.

This runner is an operator command, not hosted inference. It neither creates a
key nor adds credits. The only credential name passed into entrants is the one
explicitly selected by the operator.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))

from arena.match import run_match  # noqa: E402
from arena.replay import verify  # noqa: E402
from arena.transcript import load  # noqa: E402
from run_agentwars_league import final_scores, move_source_counts  # noqa: E402

_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
DEFAULT_MODEL = "z-ai/glm-5.3-flash"


def manifest(name, strategy, args):
    harness = os.path.join(ROOT, "entrants", "openrouter_fantasy_harness.py")
    command = [
        sys.executable,
        harness,
        "--name",
        name,
        "--strategy",
        strategy,
        "--model",
        args.model,
        "--api-key-env",
        args.api_key_env,
        "--backend-timeout",
        str(args.backend_timeout),
        "--max-tokens",
        str(args.max_tokens),
    ]
    for provider in args.provider:
        command.extend(("--provider", provider))
    return {
        "name": name,
        "cmd": command,
        "env": [args.api_key_env],
        "claimed_model": f"openrouter:{args.model};provider_only={','.join(args.provider)}",
        "execution_claim": "hybrid",
    }


def provider_receipts(transcript_path):
    rows = []
    for record in load(transcript_path):
        if record.get("kind") != "move":
            continue
        body = record.get("body", {})
        note = body.get("entrant_message", {}).get("note", "")
        if not isinstance(note, str):
            continue
        receipt = {}
        for part in note.split(";"):
            if not part.startswith("or_") or "=" not in part:
                continue
            key, value = part.split("=", 1)
            receipt[key[3:]] = value
        if receipt:
            rows.append({"player": body.get("player"), **receipt})
    return rows


def main():
    parser = argparse.ArgumentParser(description="Run a provider-pinned OpenRouter AgentWars match.")
    parser.add_argument("--game", choices=("fantasy_redraft", "fantasy_dynasty"),
                        default="fantasy_redraft")
    parser.add_argument("--seed", type=int, default=9300)
    parser.add_argument("--out", required=True)
    parser.add_argument("--json-out", default=None)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--provider",
        action="append",
        required=True,
        help="Exact OpenRouter provider slug; repeat to provide an ordered allowlist.",
    )
    parser.add_argument("--api-key-env", default="OPENROUTER_API_KEY")
    parser.add_argument("--backend-timeout", type=float, default=300.0)
    parser.add_argument("--max-tokens", type=int, default=256)
    args = parser.parse_args()

    if not isinstance(args.seed, int) or args.seed < 0:
        parser.error("--seed must be a non-negative integer")
    if not isinstance(args.model, str) or "/" not in args.model or any(c.isspace() for c in args.model):
        parser.error("--model must be one OpenRouter provider/model slug")
    if len(args.provider) != len(set(args.provider)) or any(
        not value or any(char.isspace() for char in value) for value in args.provider
    ):
        parser.error("--provider values must be unique non-empty tokens")
    if _ENV_NAME.fullmatch(args.api_key_env) is None:
        parser.error("--api-key-env must be a valid environment-variable name")
    if not 10 <= args.backend_timeout <= 900:
        parser.error("--backend-timeout must be between 10 and 900 seconds")
    if not 16 <= args.max_tokens <= 4096:
        parser.error("--max-tokens must be between 16 and 4096")
    if not os.environ.get(args.api_key_env):
        parser.error(f"{args.api_key_env} is not set; no request was made")

    entrants = [
        manifest("OpenRouter Sunday Machine", "win-now", args),
        manifest("OpenRouter Future Proof", "long-game", args),
    ]
    result = run_match(
        game_name=args.game,
        seed=args.seed,
        entrants=entrants,
        out_dir=args.out,
        move_timeout_s=args.backend_timeout + 30,
    )
    report = verify(result["transcript"])
    if report["verdict"] != "PASS":
        raise RuntimeError(f"OpenRouter match did not replay: {report.get('errors', [])[:2]}")
    sources = move_source_counts(result["transcript"], entrants)
    scores = final_scores(result["transcript"])
    model_move_claims = {name: counts["model"] for name, counts in sources.items()}
    both_used_model = all(count > 0 for count in model_move_claims.values())
    summary = {
        "product": "AgentWars fantasy football",
        "status": "model_influenced_unattested" if both_used_model else "fallback_only_not_model_played",
        "truthBoundary": (
            "The operator requested the declared OpenRouter model through an exact provider allowlist, "
            "with provider fallbacks disabled, data collection denied, and ZDR required. The hash-chained "
            "transcript proves accepted moves and result. Provider/model/usage fields remain API-reported "
            "claims; model_attested=false."
        ),
        "game": args.game,
        "seed": args.seed,
        "requestedModel": args.model,
        "providerOnly": args.provider,
        "allowFallbacks": False,
        "dataCollection": "deny",
        "zdr": True,
        "matchId": result["match_id"],
        "chainHead": result["chain_head"],
        "winner": entrants[result["winner"]]["name"] if result["winner"] is not None else None,
        "scores": {entrants[0]["name"]: scores[0], entrants[1]["name"]: scores[1]},
        "moveSourceClaims": sources,
        "modelMoveClaims": model_move_claims,
        "providerReceipts": provider_receipts(result["transcript"]),
        "modelAttested": False,
        "executionClaimsAttested": False,
        "verified": True,
    }
    rendered = json.dumps(summary, indent=2)
    if args.json_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.json_out)), exist_ok=True)
        with open(args.json_out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(rendered + "\n")
    print(rendered)
    return 0 if both_used_model else 2


if __name__ == "__main__":
    raise SystemExit(main())
