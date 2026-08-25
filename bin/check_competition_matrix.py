#!/usr/bin/env python3
"""Dependency-free acceptance checks for Competition Matrix v1."""

import copy
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from competitions.matrix import (  # noqa: E402
    CompetitionConfigError,
    _prepare,
    classify_pair,
    load_config,
    render_report,
    run_competition,
    validate_config,
    write_report,
)

EXAMPLE = os.path.join(ROOT, "competitions", "examples", "nim_matrix.json")
SECRET_ENV = "AGENTWARS_MATRIX_TEST_SECRET"
SECRET_VALUE = "matrix-secret-value-must-never-appear"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def expect_config_error(fn, phrase):
    try:
        fn()
    except CompetitionConfigError as exc:
        require(phrase in str(exc), f"expected {phrase!r} in {str(exc)!r}")
        return str(exc)
    else:
        raise AssertionError(f"expected CompetitionConfigError containing {phrase!r}")


def check_schema_rejection(base):
    bad = copy.deepcopy(base)
    bad["extra"] = True
    expect_config_error(lambda: validate_config(bad), "unexpected keys")

    bad = copy.deepcopy(base)
    bad["schemaVersion"] = "agentwars.competition-matrix.v0"
    expect_config_error(lambda: validate_config(bad), "schemaVersion")

    bad = copy.deepcopy(base)
    bad["seeds"] = [401, 401]
    expect_config_error(lambda: validate_config(bad), "unique")

    bad = copy.deepcopy(base)
    bad["seeds"] = [True]
    expect_config_error(lambda: validate_config(bad), "integers")

    bad = copy.deepcopy(base)
    bad["game"] = "unregistered-game"
    expect_config_error(lambda: validate_config(bad), "registered games")

    bad = copy.deepcopy(base)
    bad["entrants"][0][SECRET_VALUE] = True
    error = expect_config_error(lambda: validate_config(bad), "unexpected keys")
    require(SECRET_VALUE not in error, "unknown secret-like keys are not echoed")

    bad = copy.deepcopy(base)
    bad["entrants"][0]["env"] = {SECRET_ENV: SECRET_VALUE}
    expect_config_error(lambda: validate_config(bad), "array of names")

    bad = copy.deepcopy(base)
    bad["entrants"][0]["argv"].extend(["--api-key", SECRET_VALUE])
    error = expect_config_error(lambda: validate_config(bad), "credential or environment value")
    require(SECRET_VALUE not in error, "secret-looking argv is not echoed")

    bad = copy.deepcopy(base)
    bad["entrants"][0]["argv"].append(f"{SECRET_ENV}={SECRET_VALUE}")
    expect_config_error(lambda: validate_config(bad), "credential or environment value")

    bad = copy.deepcopy(base)
    bad["entrants"][0]["argv"] = ["python", "missing-harness.py"]
    expect_config_error(lambda: _prepare(bad, ROOT), "no resolvable repository harness")

    with tempfile.TemporaryDirectory(prefix="agentwars-external-harness-") as external:
        external_script = os.path.join(external, "outside.py")
        with open(external_script, "w", encoding="utf-8") as handle:
            handle.write("print('outside')\n")
        bad = copy.deepcopy(base)
        bad["entrants"][0]["argv"] = ["python", external_script]
        expect_config_error(lambda: _prepare(bad, ROOT), "inside repo_root")


def check_identity_and_contrasts(base):
    normalized, entrants = _prepare(base, ROOT)
    require(normalized["seeds"] == sorted(normalized["seeds"]), "seeds normalize deterministically")
    require(len({row["agentBuildId"] for row in entrants}) == len(entrants), "agent build ids unique")
    require(all(len(row["harnessSha256"]) == 64 for row in entrants), "full harness SHA-256 retained")
    contrasts = {
        classify_pair(entrants[first], entrants[second])
        for first in range(len(entrants))
        for second in range(first + 1, len(entrants))
    }
    require(
        contrasts
        == {
            "harness_controlled_claim",
            "model_controlled_claim",
            "provider_controlled_claim",
            "open_agent",
        },
        f"all four comparison classes covered: {contrasts}",
    )

    duplicate = copy.deepcopy(base)
    source = duplicate["entrants"][0]
    target = duplicate["entrants"][1]
    for key in ("claimedModel", "claimedProvider", "argv", "executionClaim"):
        target[key] = copy.deepcopy(source[key])
    expect_config_error(lambda: _prepare(duplicate, ROOT), "duplicate agent build")


def check_schedule(report):
    schedule = report["schedule"]
    require(schedule["entrantCount"] == 4, "four fixture entrants")
    require(schedule["expectedPairs"] == 6 == schedule["completedPairs"], "all unordered pairs")
    require(schedule["expectedMatches"] == 24, "6 pairs x 2 seeds x 2 seats")
    require(schedule["completedMatches"] == 24 == schedule["verifiedMatches"], "all matches verified")
    require(schedule["seatBalanced"] is True, "overall seats are balanced")

    cells = {}
    for match in report["matches"]:
        require(match["verified"] is True, "match replay verified")
        require(match["engineDigestMatch"] is True, "exact engine digest required")
        require(match["modelAttested"] is False, "model truth boundary retained")
        require(match["providerAttested"] is False, "provider truth boundary retained")
        source_total = sum(match["moveSourceClaims"]["seat0"].values()) + sum(
            match["moveSourceClaims"]["seat1"].values()
        )
        require(source_total == match["moves"], "move-source claims account for every move record")
        key = (match["pairId"], match["seed"])
        cells.setdefault(key, []).append(
            (match["seat0"]["agentBuildId"], match["seat1"]["agentBuildId"])
        )
    require(len(cells) == 12, "every pair-seed cell exists")
    for orders in cells.values():
        require(len(orders) == 2, "each pair-seed cell has two matches")
        require(orders[0] == tuple(reversed(orders[1])), "seat order reverses exactly")

    expected_games_per_seat = 3 * 2
    for row in report["agentStandings"]:
        require(row["games"] == 12, "each build plays every opponent, seed, and seat")
        require(row["seat0Games"] == expected_games_per_seat, "seat 0 balance")
        require(row["seat1Games"] == expected_games_per_seat, "seat 1 balance")


def check_report_safety(report):
    rendered = render_report(report)
    require(SECRET_VALUE not in rendered, "environment value is never serialized")
    require(SECRET_ENV not in rendered, "environment name is omitted from the public report")
    require("--backend" not in rendered, "raw argv is omitted")
    require("entrants/solver_harness.py" not in rendered, "raw harness argv path is omitted")
    require(os.path.abspath(ROOT) not in rendered, "absolute repo path is omitted")
    require('"argv"' not in rendered and '"env"' not in rendered, "launch declaration is redacted")
    require('"globalProviderLeaderboardPublished":false' in rendered, "provider leaderboard refusal is explicit")
    require('"modelAttested":false' in rendered, "model claim remains unattested")
    require('"providerAttested":false' in rendered, "provider claim remains unattested")


def check_end_to_end(base):
    config = copy.deepcopy(base)
    config["entrants"][0]["env"] = [SECRET_ENV]
    old_value = os.environ.get(SECRET_ENV)
    os.environ[SECRET_ENV] = SECRET_VALUE
    try:
        with tempfile.TemporaryDirectory(prefix="agentwars-matrix-") as work:
            blocked_dir = os.path.join(work, "blocked")
            expect_config_error(
                lambda: run_competition(
                    config,
                    matches_dir=blocked_dir,
                    repo_root=ROOT,
                    move_timeout_s=5.0,
                    max_matches=23,
                ),
                "authorized max_matches ceiling",
            )
            require(not os.path.exists(blocked_dir), "schedule ceiling fails before output creation")
            first = run_competition(
                config,
                matches_dir=os.path.join(work, "first", "matches"),
                repo_root=ROOT,
                move_timeout_s=5.0,
            )
            second = run_competition(
                config,
                matches_dir=os.path.join(work, "second", "matches"),
                repo_root=ROOT,
                move_timeout_s=5.0,
            )
            expect_config_error(
                lambda: run_competition(
                    config,
                    matches_dir=os.path.join(work, "first", "matches"),
                    repo_root=ROOT,
                    move_timeout_s=5.0,
                ),
                "must be empty",
            )
            first_bytes = render_report(first).encode("utf-8")
            second_bytes = render_report(second).encode("utf-8")
            require(first_bytes == second_bytes, "offline fixture report bytes are deterministic")
            require(first["status"] == "scripted_preseason", "fixture truth status")
            require(first["executionPolicy"]["moveTimeoutMs"] == 5_000, "timeout is receipt-bound")
            require(first["executionPolicy"]["authorizedMatchCeiling"] == 512,
                    "schedule authorization is published")
            require(first["truthBoundary"]["replayVerified"] is True, "truth boundary reports replay")
            require(first["truthBoundary"]["controlledClaimsAreCausalProof"] is False,
                    "controlled claims are not causal proof")
            require(len(first["comparisons"]["harnessControlledClaims"]) == 1, "harness control pair")
            require(len(first["comparisons"]["modelControlledClaims"]) == 1, "model control pair")
            require(len(first["comparisons"]["providerControlledClaims"]) == 1, "provider control pair")
            require(len(first["comparisons"]["openAgent"]) == 3, "open-agent pairs")
            check_schedule(first)
            check_report_safety(first)

            first_path = os.path.join(work, "first-report.json")
            second_path = os.path.join(work, "second-report.json")
            write_report(first, first_path)
            write_report(second, second_path)
            with open(first_path, "rb") as handle:
                persisted_first = handle.read()
            with open(second_path, "rb") as handle:
                persisted_second = handle.read()
            require(persisted_first == first_bytes == persisted_second, "persisted report bytes match")
            expect_config_error(lambda: write_report(first, first_path), "already exists")
    finally:
        if old_value is None:
            os.environ.pop(SECRET_ENV, None)
        else:
            os.environ[SECRET_ENV] = old_value


def main():
    base = load_config(EXAMPLE)
    check_schema_rejection(base)
    check_identity_and_contrasts(base)
    check_end_to_end(base)
    print("AgentWars Competition Matrix contracts: PASS")
    print("4 entrants / 6 pairs / 24 exact-engine replay receipts / 4 contrast classes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
