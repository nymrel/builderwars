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
    _move_source_claims,
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


def check_loader_rejection():
    with tempfile.TemporaryDirectory(prefix="agentwars-matrix-loader-") as work:
        cases = [
            (
                "duplicate-top.json",
                b'{"schemaVersion":"first","schemaVersion":"second"}',
                "duplicate JSON object key",
            ),
            (
                "duplicate-nested.json",
                b'{"entrants":[{"name":"first","name":"second"}]}',
                "duplicate JSON object key",
            ),
            ("oversized.json", b" " * (256 * 1024 + 1), "exceeds 256 KiB"),
            ("non-utf8.json", b"\xff", "UnicodeDecodeError"),
        ]
        for filename, payload, phrase in cases:
            path = os.path.join(work, filename)
            with open(path, "wb") as handle:
                handle.write(payload)
            expect_config_error(lambda path=path: load_config(path), phrase)

        secret_path = os.path.join(work, "secret-duplicate.json")
        secret_payload = json.dumps({"safe": True})[:-1] + (
            f',"{SECRET_VALUE}":1,"{SECRET_VALUE}":2}}'
        )
        with open(secret_path, "w", encoding="utf-8") as handle:
            handle.write(secret_payload)
        error = expect_config_error(lambda: load_config(secret_path), "duplicate JSON object key")
        require(SECRET_VALUE not in error, "duplicate-key errors do not echo attacker-controlled keys")


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
    expect_config_error(lambda: _prepare(bad, ROOT), "argv[1]")

    bad = copy.deepcopy(base)
    bad["competition"] = "Invisible\u200bMatrix"
    expect_config_error(lambda: validate_config(bad), "control or invisible")

    bad = copy.deepcopy(base)
    bad["competition"] = "Matrix\n"
    expect_config_error(lambda: validate_config(bad), "control or invisible")

    bad = copy.deepcopy(base)
    bad["entrants"][0]["argv"].append("--label=\u202econfusing")
    expect_config_error(lambda: validate_config(bad), "invalid argument")

    for argv in (
        ["python", "-c", "print('not the harness')", "entrants/solver_harness.py"],
        ["python", "-u", "entrants/solver_harness.py"],
    ):
        bad = copy.deepcopy(base)
        bad["entrants"][0]["argv"] = argv
        expect_config_error(lambda bad=bad: _prepare(bad, ROOT), "argv[1]")

    bad = copy.deepcopy(base)
    bad["entrants"][0]["argv"] = ["arbitrary-runner", "entrants/solver_harness.py"]
    expect_config_error(lambda: _prepare(bad, ROOT), "interpreter is not allowed")

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
    require(all(len(row["launchSpecSha256"]) == 64 for row in entrants), "full launch-spec SHA-256 retained")
    require(all(row["launchMode"] == "interpreter" for row in entrants), "fixture launch mode is explicit")
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

    changed_launch = copy.deepcopy(base)
    changed_launch["entrants"][0]["argv"][-1] = "stub:argv-only-change"
    _, changed_entrants = _prepare(changed_launch, ROOT)
    before = {row["name"]: row for row in entrants}[base["entrants"][0]["name"]]
    after = {row["name"]: row for row in changed_entrants}[base["entrants"][0]["name"]]
    require(before["harnessSha256"] == after["harnessSha256"], "argv-only change keeps harness digest")
    require(before["launchSpecSha256"] != after["launchSpecSha256"], "argv-only change updates launch digest")
    require(before["agentBuildId"] != after["agentBuildId"], "argv-only change updates agent build identity")

    changed_env = copy.deepcopy(base)
    changed_env["entrants"][0]["env"] = [SECRET_ENV]
    _, changed_env_entrants = _prepare(changed_env, ROOT)
    after_env = {row["name"]: row for row in changed_env_entrants}[base["entrants"][0]["name"]]
    require(before["harnessSha256"] == after_env["harnessSha256"], "env-name change keeps harness digest")
    require(before["launchSpecSha256"] != after_env["launchSpecSha256"], "env-name change updates launch digest")
    require(before["agentBuildId"] != after_env["agentBuildId"], "env-name change updates agent build identity")

    direct = copy.deepcopy(base)
    direct["entrants"][0]["argv"] = ["entrants/solver_harness.py", "--backend", "stub:v1"]
    _, direct_entrants = _prepare(direct, ROOT)
    direct_row = {row["name"]: row for row in direct_entrants}[base["entrants"][0]["name"]]
    require(direct_row["launchMode"] == "direct", "repository harness at argv[0] is a direct launch")

    suffixed_interpreter = copy.deepcopy(base)
    suffixed_interpreter["entrants"][0]["argv"][0] = "PYTHON.EXE"
    _, suffixed_entrants = _prepare(suffixed_interpreter, ROOT)
    suffixed_row = {row["name"]: row for row in suffixed_entrants}[base["entrants"][0]["name"]]
    require(suffixed_row["launchMode"] == "interpreter", "interpreter suffix normalization is bounded")

    duplicate = copy.deepcopy(base)
    source = duplicate["entrants"][0]
    target = duplicate["entrants"][1]
    for key in ("claimedModel", "claimedProvider", "argv", "env", "executionClaim"):
        target[key] = copy.deepcopy(source[key])
    expect_config_error(lambda: _prepare(duplicate, ROOT), "duplicate agent build")


def check_move_source_parsing():
    notes = [
        (0, "source=model"),
        (0, "source=model;response_sha256=abc"),
        (0, "source=model-not-really"),
        (0, " source=model"),
        (0, "Source=model"),
        (1, "source=fallback"),
        (1, "source=fallback;reason=invalid"),
        (1, "source=scripted"),
        (1, "source=scripted;fixture=local"),
        (1, "source=scripted-extra"),
        (1, "plain prose"),
    ]
    with tempfile.TemporaryDirectory(prefix="agentwars-move-source-") as work:
        path = os.path.join(work, "claims.jsonl")
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            for seat, note in notes:
                handle.write(json.dumps({
                    "kind": "move",
                    "body": {"player": seat, "entrant_message": {"note": note}},
                }, sort_keys=True) + "\n")
        counts = _move_source_claims(path)
    require(
        counts[0] == {"model": 2, "fallback": 0, "scripted": 0, "unclassified": 3},
        f"model source labels require an exact first segment: {counts[0]}",
    )
    require(
        counts[1] == {"model": 0, "fallback": 2, "scripted": 2, "unclassified": 2},
        f"fallback/scripted source labels require an exact first segment: {counts[1]}",
    )


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
    require(report["schemaVersion"] == "agentwars.competition-report.v2", "report schema is bumped")
    require(
        all(
            len(row["launchSpecSha256"]) == 64
            and all(char in "0123456789abcdef" for char in row["launchSpecSha256"])
            for row in report["entrants"]
        ),
        "public entrants include full lowercase launch commitments",
    )
    require(all(row["launchMode"] in {"direct", "interpreter"} for row in report["entrants"]),
            "public entrants include only bounded launch modes")
    require(SECRET_VALUE not in rendered, "environment value is never serialized")
    require(SECRET_ENV not in rendered, "environment name is omitted from the public report")
    require("--backend" not in rendered, "raw argv is omitted")
    require("entrants/solver_harness.py" not in rendered, "raw harness argv path is omitted")
    require(os.path.abspath(ROOT) not in rendered, "absolute repo path is omitted")
    require('"argv"' not in rendered and '"env"' not in rendered, "launch declaration is redacted")
    require('"globalProviderLeaderboardPublished":false' in rendered, "provider leaderboard refusal is explicit")
    require('"modelAttested":false' in rendered, "model claim remains unattested")
    require('"providerAttested":false' in rendered, "provider claim remains unattested")
    require('"rawLaunchSpecPublished":false' in rendered, "raw launch declaration refusal is explicit")


def check_end_to_end(base):
    config = copy.deepcopy(base)
    config["entrants"][0]["env"] = [SECRET_ENV]
    old_value = os.environ.get(SECRET_ENV)
    os.environ[SECRET_ENV] = SECRET_VALUE
    try:
        with tempfile.TemporaryDirectory(prefix="agentwars-matrix-") as work:
            invalid_launch = copy.deepcopy(config)
            invalid_launch["entrants"][0]["argv"] = [
                "python", "-c", "print('not the harness')", "entrants/solver_harness.py",
            ]
            invalid_launch_dir = os.path.join(work, "invalid-launch")
            expect_config_error(
                lambda: run_competition(
                    invalid_launch,
                    matches_dir=invalid_launch_dir,
                    repo_root=ROOT,
                    move_timeout_s=5.0,
                ),
                "argv[1]",
            )
            require(not os.path.exists(invalid_launch_dir),
                    "ambiguous interpreter launch fails before output creation")
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
            require(first["truthBoundary"]["launchSpecDigestBound"] is True,
                    "launch-spec commitment is explicit")
            require(first["truthBoundary"]["launchSpecDigestProvidesConfidentiality"] is False,
                    "launch commitment is not misrepresented as encryption")
            require(first["truthBoundary"]["launchRuntimeAttested"] is False,
                    "launch runtime is not upgraded into attestation")
            require(first["truthBoundary"]["harnessFileDigestBound"] is True,
                    "pre-run harness digest is bound")
            require(first["truthBoundary"]["harnessExecutionAttested"] is False,
                    "sampled harness bytes are not upgraded into execution attestation")
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
    check_loader_rejection()
    base = load_config(EXAMPLE)
    check_schema_rejection(base)
    check_identity_and_contrasts(base)
    check_move_source_parsing()
    check_end_to_end(base)
    print("AgentWars Competition Matrix contracts: PASS")
    print("4 entrants / 6 pairs / 24 exact-engine replay receipts / 4 contrast classes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
