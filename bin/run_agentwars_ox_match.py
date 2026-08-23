#!/usr/bin/env python3
"""Run one same-model Ox Alpha fantasy match with tools denied.

This is an operator-owned entrant path, not a referee model integration. The
engine passes only process-policy variable names, never credentials. Even when
model-source notes appear, the replay remains explicit that provider identity
and execution provenance are not independently attested.
"""

import argparse
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))

from arena.match import run_match  # noqa: E402
from arena.replay import verify  # noqa: E402
from run_agentwars_league import final_scores, move_source_counts  # noqa: E402

MODEL = "opencode-go/ox-alpha-free"
VARIANT = "max"
ENV_NAMES = ("OPENCODE_CONFIG_CONTENT", "OPENCODE_DISABLE_PROJECT_CONFIG", "OPENCODE_PURE")


def deny_tool_policy():
    permissions = {
        "*": "deny",
        "read": "deny",
        "glob": "deny",
        "grep": "deny",
        "list": "deny",
        "edit": "deny",
        "bash": "deny",
        "task": "deny",
        "external_directory": {"*": "deny"},
        "lsp": "deny",
        "skill": "deny",
        "question": "deny",
        "webfetch": "deny",
        "websearch": "deny",
    }
    return {
        "permission": permissions,
        "default_agent": "agentwars-entrant",
        "agent": {
            "agentwars-entrant": {
                "description": "Tool-free AgentWars fantasy decision entrant.",
                "mode": "primary",
                "model": MODEL,
                "variant": VARIANT,
                "steps": 1,
                "permission": permissions,
            }
        },
    }


def manifest(name, strategy, backend_timeout):
    harness = os.path.join(ROOT, "entrants", "fantasy_model_harness.py")
    backend = f"opencode:{MODEL}@{VARIANT}"
    return {
        "name": name,
        "cmd": [
            sys.executable,
            harness,
            "--name",
            name,
            "--strategy",
            strategy,
            "--backend",
            backend,
            "--backend-timeout",
            str(backend_timeout),
        ],
        "env": list(ENV_NAMES),
        "claimed_model": f"{MODEL}/{VARIANT}",
        # The harness can fall back deterministically, so "model" would be an
        # overclaim even if every move in one match happens to come from Ox.
        "execution_claim": "hybrid",
    }


def main():
    parser = argparse.ArgumentParser(description="Run one tool-free Ox Alpha AgentWars match.")
    parser.add_argument("--game", choices=("fantasy_redraft", "fantasy_dynasty"),
                        default="fantasy_redraft")
    parser.add_argument("--seed", type=int, default=9300)
    parser.add_argument("--out", required=True)
    parser.add_argument("--json-out", default=None)
    parser.add_argument("--backend-timeout", type=float, default=300.0)
    args = parser.parse_args()
    if not isinstance(args.seed, int) or args.seed < 0:
        parser.error("--seed must be a non-negative integer")
    if not 10 <= args.backend_timeout <= 900:
        parser.error("--backend-timeout must be between 10 and 900 seconds")
    if shutil.which("opencode") is None:
        parser.error("opencode is not available on PATH")

    os.environ["OPENCODE_CONFIG_CONTENT"] = json.dumps(deny_tool_policy(), separators=(",", ":"))
    os.environ["OPENCODE_DISABLE_PROJECT_CONFIG"] = "1"
    os.environ["OPENCODE_PURE"] = "1"
    entrants = [
        manifest("Ox Sunday Machine", "win-now", args.backend_timeout),
        manifest("Ox Future Proof", "long-game", args.backend_timeout),
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
        raise RuntimeError(f"Ox match did not replay: {report.get('errors', [])[:2]}")
    sources = move_source_counts(result["transcript"], entrants)
    scores = final_scores(result["transcript"])
    model_move_claims = {name: counts["model"] for name, counts in sources.items()}
    both_used_model = all(count > 0 for count in model_move_claims.values())
    summary = {
        "product": "AgentWars fantasy football",
        "status": "model_influenced_unattested" if both_used_model else "fallback_only_not_model_played",
        "truthBoundary": (
            "The operator launched the declared Ox Alpha backend with all OpenCode tools denied. "
            "The hash-chained transcript proves the accepted moves and result. Model identity and "
            "move-source notes remain entrant claims, model_attested=false."
        ),
        "game": args.game,
        "seed": args.seed,
        "matchId": result["match_id"],
        "chainHead": result["chain_head"],
        "winner": entrants[result["winner"]]["name"] if result["winner"] is not None else None,
        "scores": {entrants[0]["name"]: scores[0], entrants[1]["name"]: scores[1]},
        "moveSourceClaims": sources,
        "modelMoveClaims": model_move_claims,
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
