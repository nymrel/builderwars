#!/usr/bin/env python3
"""Build one offline, replay-verified AgentWars starter qualification.

This command exercises the bundled redraft rules and referee with two fixed
scripted entrants.  It does not configure a provider, request credentials,
qualify a customer's harness, or authorize ranking, publication, or deploy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arena.games import fantasy_redraft  # noqa: E402
from bin.run_agentwars_league import run_league  # noqa: E402
from entrants.fantasy_model_harness import fallback_move  # noqa: E402


SCHEMA_VERSION = "agentwars.starter_qualification.v1"
STATUS = "pass_local_scripted_environment"
SEED = 9100
GAME = "fantasy_redraft"
SCRIPTED_BACKEND = "scripted:starter-v1"
PROVIDER_CREDENTIAL_ENV_NAMES = frozenset(
    {
        "ANTHROPIC_API_KEY",
        "CODEX_API_KEY",
        "GOOGLE_API_KEY",
        "HERMES_API_KEY",
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
    }
)
TRUTH = {
    "customerHarnessQualified": False,
    "customerModelQualified": False,
    "deploymentAuthorized": False,
    "filesystemConfinementEnforced": False,
    "fixedBundledEntrants": True,
    "hostedRuntimeQualified": False,
    "modelAttested": False,
    "networkEgressBlocked": False,
    "personAttested": False,
    "providerAccountAttested": False,
    "providerCredentialEnvironmentObservedByEntrants": False,
    "providerCredentialsProvisioned": False,
    "providerCredentialsRequested": False,
    "providerRouteConfigured": False,
    "publicationAuthorized": False,
    "rankingAuthorized": False,
}


class StarterQualificationError(ValueError):
    """Bounded local qualification refusal."""


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("ascii")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _is_reparse(path: Path) -> bool:
    try:
        attrs = path.lstat().st_file_attributes
    except AttributeError:
        return False
    return bool(attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _assert_output_target(destination: Path) -> Path:
    if os.name == "nt" and str(destination).startswith("\\\\"):
        raise StarterQualificationError("starter output must be on a direct local path")
    if destination.exists() or destination.is_symlink():
        raise StarterQualificationError("starter output already exists")
    try:
        parent = destination.parent.resolve(strict=True)
    except OSError as error:
        raise StarterQualificationError("starter output parent must already exist") from error
    current = destination.parent.absolute()
    while True:
        if current.exists() and (current.is_symlink() or _is_reparse(current)):
            raise StarterQualificationError("starter output has an indirect ancestor")
        ancestor = current.parent
        if ancestor == current:
            break
        current = ancestor
    return parent / destination.name


def _send(message: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(message, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def _run_scripted_entrant(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--name", required=True)
    parser.add_argument("--strategy", choices=("win-now", "long-game"), required=True)
    args = parser.parse_args(argv)
    if PROVIDER_CREDENTIAL_ENV_NAMES.intersection(os.environ):
        return 78
    for line in sys.stdin:
        if not line.strip():
            continue
        message = json.loads(line)
        if message.get("type") == "hello":
            _send(
                {
                    "type": "ready",
                    "entrant": args.name,
                    "version": "1",
                    "backend": SCRIPTED_BACKEND,
                }
            )
        elif message.get("type") == "move_request":
            move = fallback_move(message.get("observation"), args.strategy)
            _send({"type": "move", "move": move, "note": "source=scripted;starter=v1"})
        elif message.get("type") == "goodbye":
            return 0
    return 0


def _entrant(name: str, strategy: str) -> dict[str, Any]:
    return {
        "name": name,
        "cmd": [
            sys.executable,
            str(Path(__file__).resolve()),
            "__entrant",
            "--name",
            name,
            "--strategy",
            strategy,
        ],
        "env": [],
        "claimed_model": "none:scripted-starter-v1",
        "execution_claim": "scripted",
    }


def _all_moves_scripted(summary: dict[str, Any]) -> bool:
    formats = summary.get("formats")
    if not isinstance(formats, list) or len(formats) != 1:
        return False
    matches = formats[0].get("matches")
    if not isinstance(matches, list) or len(matches) != 2:
        return False
    saw_scripted = False
    for match in matches:
        sources = match.get("moveSourceClaims")
        if not isinstance(sources, dict):
            return False
        for counts in sources.values():
            if not isinstance(counts, dict):
                return False
            if any(counts.get(name) != 0 for name in ("model", "fallback", "other")):
                return False
            if not isinstance(counts.get("scripted"), int) or counts["scripted"] <= 0:
                return False
            saw_scripted = True
    return saw_scripted


def build_qualification(destination: Path) -> dict[str, Any]:
    destination = _assert_output_target(destination.absolute())
    try:
        destination.mkdir()
    except FileExistsError as error:
        raise StarterQualificationError("starter output already exists") from error
    try:
        config = {
            "league": "AgentWars offline starter",
            "description": "Fixed scripted redraft environment qualification; not a model evaluation.",
            "entrants": [
                _entrant("Starter Win Now", "win-now"),
                _entrant("Starter Long Game", "long-game"),
            ],
        }
        summary = run_league(
            config,
            formats=[GAME],
            seeds=1,
            start_seed=SEED,
            out_dir=destination / "matches",
            move_timeout_s=10.0,
        )
        matches = summary["formats"][0]["matches"]
        if (
            summary.get("status") != "scripted_preseason"
            or summary.get("modelAttested") is not False
            or summary.get("executionClaimsAttested") is not False
            or len(matches) != 2
            or not all(match.get("verified") is True for match in matches)
            or not _all_moves_scripted(summary)
        ):
            raise StarterQualificationError("starter league truth checks failed")

        summary_path = destination / "league-summary.json"
        summary_raw = _canonical_bytes(summary)
        summary_path.write_bytes(summary_raw)
        transcript_rows = []
        for path in sorted((destination / "matches").rglob("*.jsonl")):
            if path.name.endswith(".diagnostics.jsonl"):
                continue
            raw = path.read_bytes()
            transcript_rows.append(
                {
                    "file": path.relative_to(destination).as_posix(),
                    "sha256": _sha256(raw),
                }
            )
        if len(transcript_rows) != 2:
            raise StarterQualificationError("starter transcript count is not exact")

        receipt: dict[str, Any] = {
            "schemaVersion": SCHEMA_VERSION,
            "status": STATUS,
            "qualificationScope": "local_rules_and_referee_environment_only",
            "game": GAME,
            "gameVersion": fantasy_redraft.VERSION,
            "seed": SEED,
            "fixtureCount": 2,
            "seatOrders": 2,
            "allReplaysVerified": True,
            "allMovesScripted": True,
            "summaryFile": "league-summary.json",
            "summarySha256": _sha256(summary_raw),
            "transcripts": transcript_rows,
            "truth": dict(TRUTH),
        }
        receipt["receiptDigest"] = _sha256(_canonical_bytes(receipt))
        # Written last: its presence means every bound file above was complete.
        (destination / "qualification.json").write_bytes(_canonical_bytes(receipt))
        return receipt
    except BaseException:
        shutil.rmtree(destination, ignore_errors=True)
        raise


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "__entrant":
        return _run_scripted_entrant(arguments[1:])
    parser = argparse.ArgumentParser(
        description="Run the offline scripted AgentWars starter qualification."
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(arguments)
    try:
        receipt = build_qualification(args.out)
    except (OSError, StarterQualificationError, ValueError) as error:
        print(f"REFUSED: {error}")
        return 2
    print(json.dumps(receipt, indent=2, sort_keys=True))
    print(
        "PASS: local scripted rules/referee environment only; no customer harness, "
        "model, provider account, ranking, publication, or deployment qualification."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
