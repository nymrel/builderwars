#!/usr/bin/env python3
"""Offline CLI for held declarative AgentWars creator-game candidates."""

from __future__ import annotations

import argparse
import json
import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from creator_sdk.runtime import (  # noqa: E402
    CANDIDATE_STATUS,
    CreatorGameError,
    SealedAllocationGame,
    load_manifest,
    load_registry,
    load_replay,
    verify_replay,
)


def _emit(value: object, *, stream=sys.stdout) -> None:
    stream.write(
        json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    )


def _validate(path: str) -> dict:
    game = SealedAllocationGame(load_manifest(path))
    return {
        "schemaVersion": 1,
        "status": "pass",
        "candidateStatus": CANDIDATE_STATUS,
        "gameId": game.game_id,
        "gameVersion": game.version,
        "manifestSha256": game.manifest_sha256,
        "family": game.manifest["rules"]["family"],
        "rounds": game.rounds,
        "frontCount": len(game.fronts),
        "budgetPerRound": game.budget,
        "moveBound": game.move_bound(),
        "creatorCodeExecuted": False,
        "modelAttested": False,
        "providerAttested": False,
        "runtimeAttested": False,
        "harnessExecutionAttested": False,
        "executionAuthorized": False,
        "publicationAuthorized": False,
        "rankingAuthorized": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate or replay one declarative creator-game candidate offline. "
            "A PASS never admits, executes, publishes, or ranks the game."
        )
    )
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="validate one held game manifest")
    validate.add_argument("manifest")

    replay = commands.add_parser("verify-replay", help="replay one fixed candidate receipt")
    replay.add_argument("manifest")
    replay.add_argument("replay")

    registry = commands.add_parser(
        "check-registry",
        help="verify a source-controlled held registry and all referenced bytes",
    )
    registry.add_argument("registry")
    registry.add_argument("--root", default=ROOT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            report = _validate(args.manifest)
        elif args.command == "verify-replay":
            report = verify_replay(load_manifest(args.manifest), load_replay(args.replay))
        else:
            report = load_registry(args.registry, args.root)
        _emit(report)
        return 0
    except CreatorGameError as error:
        _emit(
            {
                "schemaVersion": 1,
                "status": "fail",
                "code": error.code,
                "candidateStatus": CANDIDATE_STATUS,
                "creatorCodeExecuted": False,
                "executionAuthorized": False,
                "publicationAuthorized": False,
                "rankingAuthorized": False,
            },
            stream=sys.stderr,
        )
        return 2
    except BrokenPipeError:
        return 0
    except Exception:
        _emit(
            {
                "schemaVersion": 1,
                "status": "error",
                "code": "internal_error",
                "candidateStatus": CANDIDATE_STATUS,
                "creatorCodeExecuted": False,
                "executionAuthorized": False,
                "publicationAuthorized": False,
                "rankingAuthorized": False,
            },
            stream=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
