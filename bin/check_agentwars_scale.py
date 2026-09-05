#!/usr/bin/env python3
"""Focused contracts for AgentWars model adapters and scaled leagues."""

import copy
import json
import os
import random
import subprocess
import sys
import tempfile
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))

from arena.games import load as load_game  # noqa: E402
from arena.match import validate_manifest  # noqa: E402
from arena.transcript import load  # noqa: E402
from entrants.fantasy_model_harness import (  # noqa: E402
    MAX_MODEL_OUTPUT_CHARS,
    decide,
    extract_strict_move,
    fallback_move,
    move_is_legal_for_observation,
)
from entrants.backends import OpenCodeBackend, execution_claim_for_backend  # noqa: E402
from run_agentwars_league import FORMATS, run_league, truth_status, validate_config  # noqa: E402


def require(condition, message):
    if not condition:
        raise AssertionError(message)


class FixedBackend:
    label = "fixture:fixed"

    def __init__(self, response):
        self.response = response

    def complete(self, _prompt):
        return self.response


class FailingBackend:
    label = "fixture:failing"

    def complete(self, _prompt):
        raise RuntimeError("fixture failure that must not cross the entrant pipe")


def scripted_manifest(name, strategy):
    script = os.path.join(ROOT, "entrants", "fantasy_gm_harness.py")
    return {
        "name": name,
        "cmd": [sys.executable, script, "--name", name, "--strategy", strategy],
        "env": [],
        "claimed_model": "scripted-baseline:v1",
        "execution_claim": "scripted",
    }


def expect_value_error(fn, fragment):
    try:
        fn()
    except ValueError as error:
        require(fragment in str(error), f"expected {fragment!r} in {error!r}")
        return
    raise AssertionError(f"expected ValueError containing {fragment!r}")


def check_adapter():
    game = load_game("fantasy_redraft")
    state = game.setup(random.Random(9200))
    observation = game.observation(state, 0)
    legal = fallback_move(observation, "win-now")
    require(move_is_legal_for_observation(observation, legal), "fallback must be legal")
    raw = json.dumps(legal, separators=(",", ":"))
    move, note = decide(observation, "win-now", FixedBackend(raw))
    require(move == legal and note.startswith("source=model"), "strict legal JSON must count as model")

    hostile = [
        None,
        "",
        "I pick 10",
        "```json\n{\"player_id\":10}\n```",
        "{\"player_id\":true}",
        "{\"player_id\":999}",
        "{\"player_id\":10,\"confidence\":1}",
        "x" * (MAX_MODEL_OUTPUT_CHARS + 1),
    ]
    for response in hostile:
        move, note = decide(observation, "win-now", FixedBackend(response))
        require(note.startswith("source=fallback"), f"hostile output must fall back: {response!r}")
        require(move_is_legal_for_observation(observation, move), "hostile output fallback must stay legal")
    move, note = decide(observation, "long-game", FailingBackend())
    require(note.startswith("source=fallback;reason=backend_error:RuntimeError"),
            "backend error class must be visible without its private message")
    require(move_is_legal_for_observation(observation, move), "backend failure fallback must stay legal")
    require(extract_strict_move('{"player_id":12}') == {"player_id": 12}, "strict parser fixture")
    event = json.dumps({"type": "text", "part": {"text": '{"player_id":12}'}}).encode("utf-8")
    completed = subprocess.CompletedProcess([], 0, stdout=event + b"\n", stderr=b"")
    with mock.patch("entrants.backends.shutil.which", return_value="opencode-fixture"), \
            mock.patch("entrants.backends.subprocess.run", return_value=completed):
        require(OpenCodeBackend("opencode-go/ox-alpha-free").complete("pick") == '{"player_id":12}',
                "OpenCode JSON transport must expose assistant text only")
    require(execution_claim_for_backend("opencode:opencode-go/ox-alpha-free@max") == "model",
            "OpenCode backend must map to a model execution claim")

    overflow = copy.deepcopy(observation)
    overflow["needs"]["QB"] = 0
    qb_id = next(row["id"] for row in overflow["available_players"] if row["position"] == "QB")
    move, note = decide(overflow, "win-now", FixedBackend(json.dumps({"player_id": qb_id})))
    require(note.startswith("source=fallback"), "position-overflow model pick must fall back")
    require(move_is_legal_for_observation(overflow, move), "overflow fallback must select an open position")


def check_manifests():
    valid = scripted_manifest("Valid", "win-now")
    validate_manifest(valid)
    invalid = dict(valid, execution_claim="probably-a-model")
    expect_value_error(lambda: validate_manifest(invalid), "execution_claim")
    invalid = dict(valid, cmd="python entrant.py")
    expect_value_error(lambda: validate_manifest(invalid), "cmd")
    invalid = dict(valid, env=["TOKEN=value"])
    expect_value_error(lambda: validate_manifest(invalid), "environment-variable names")
    require(truth_status([dict(valid, execution_claim="model")]) == "model_claimed_unattested",
            "all-model league truth label")
    require(truth_status([valid, dict(valid, name="Other", execution_claim="model")]) == "mixed_unattested",
            "mixed league truth label")
    require(truth_status([dict(valid, execution_claim="hybrid")]) == "model_influenced_unattested",
            "hybrid league truth label")


def check_league():
    entrants = [
        scripted_manifest("Sunday Machine", "win-now"),
        scripted_manifest("Future Proof", "long-game"),
        scripted_manifest("Clock Manager", "win-now"),
    ]
    config = {"league": "AgentWars contract league", "description": "fixture", "entrants": entrants}
    duplicate = copy.deepcopy(config)
    duplicate["entrants"][2]["name"] = "future proof"
    expect_value_error(lambda: validate_config(duplicate), "unique")
    unexpected = copy.deepcopy(config)
    unexpected["entrants"][0]["credential"] = "never allowed"
    expect_value_error(lambda: validate_config(unexpected), "unexpected keys")

    with tempfile.TemporaryDirectory(prefix="agentwars-scale-check-") as work:
        first = run_league(
            config,
            formats=list(FORMATS),
            seeds=1,
            start_seed=9200,
            out_dir=os.path.join(work, "first"),
        )
        second = run_league(
            config,
            formats=list(reversed(FORMATS)),
            seeds=1,
            start_seed=9200,
            out_dir=os.path.join(work, "second"),
        )
        first_bytes = json.dumps(first, sort_keys=True, separators=(",", ":")).encode("utf-8")
        second_bytes = json.dumps(second, sort_keys=True, separators=(",", ":")).encode("utf-8")
        require(first_bytes == second_bytes, "deterministic entrants must reproduce league summary bytes")
        require(first["status"] == "scripted_preseason", "scripted fixture truth label")
        matches = [match for circuit in first["formats"] for match in circuit["matches"]]
        require(len(matches) == 18, "3 entrants x 3 pairs x 2 seats x 3 formats")
        require([match["sequence"] for match in matches] == list(range(18)), "schedule order must be stable")
        require(all(match["verified"] and not match["modelAttested"] for match in matches),
                "every result must replay and remain unattested")

        sample_id = matches[0]["matchId"]
        sample = next(
            path for path, _, files in os.walk(os.path.join(work, "first"))
            for filename in files if filename == f"{sample_id}.jsonl"
        )
        sample_path = os.path.join(sample, f"{sample_id}.jsonl")
        header = load(sample_path)[0]["body"]
        require(all(row["execution_claim"] == "scripted" for row in header["entrants"]),
                "execution claims must be hash-bound in the header")
        require(header["attestation"]["model_attested"] is False, "model identity remains unattested")
        standalone = subprocess.run(
            [sys.executable, os.path.join(ROOT, "verify.py"), sample_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        require(standalone.returncode == 0 and "VERDICT: PASS" in standalone.stdout,
                f"standalone verifier must accept Phase 2 receipt: {standalone.stdout[-500:]}")

    expect_value_error(
        lambda: run_league(config, formats=["fantasy_redraft"], seeds=0, start_seed=1, out_dir="unused"),
        "seeds",
    )
    expect_value_error(
        lambda: run_league(config, formats=["fantasy_redraft", "fantasy_redraft"],
                           seeds=1, start_seed=1, out_dir="unused"),
        "formats",
    )


def main():
    check_adapter()
    check_manifests()
    check_league()
    print("AgentWars scale contracts: PASS")
    print("3 entrants / 18 replay-verified deterministic matches / strict model fallback")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
