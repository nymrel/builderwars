#!/usr/bin/env python3
"""Adversarial contract checks for the AgentWars local launch evidence builder."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin"
if str(BIN) not in sys.path:
    sys.path.insert(0, str(BIN))

import build_agentwars_local_launch_evidence as evidence_builder


checks = 0


def check(condition: bool, label: str) -> None:
    global checks
    if not condition:
        raise AssertionError(label)
    checks += 1


def clean_source() -> dict[str, Any]:
    return {
        "commit": "1" * 40,
        "tree": "2" * 40,
        "branch": "release/test",
        "clean": True,
        "dirtyEntryCount": 0,
        "canonicalMainIntegrated": False,
        "remoteCustodyProven": False,
    }


def passing_runner(argv: Sequence[str], timeout_seconds: int) -> dict[str, Any]:
    del timeout_seconds
    return {
        "argv": ["python" if token == evidence_builder.PYTHON else token for token in argv],
        "status": "PASS",
        "exitCode": 0,
        "timedOut": False,
        "durationMs": 1,
        "stdoutSha256": "3" * 64,
        "stderrSha256": "4" * 64,
        "summary": "synthetic local PASS",
    }


def check_emitted_pack(path: Path) -> None:
    raw = path.read_text(encoding="utf-8")
    pack = json.loads(raw)
    check(isinstance(pack, dict), "emitted pack is a JSON object")
    check(evidence_builder.verify_pack_digest(pack), "emitted pack digest verifies")
    check(pack.get("schema") == evidence_builder.SCHEMA, "emitted pack schema is pinned")
    stages = pack.get("stages")
    check(isinstance(stages, list) and len(stages) == 13, "emitted pack carries exactly 13 stages")
    check([stage.get("order") for stage in stages] == list(range(1, 14)), "emitted stage order is exact")
    check([stage.get("id") for stage in stages] == [stage.stage_id for stage in evidence_builder.STAGES], "emitted stage ids match the contract")
    check(all(stage.get("status") == evidence_builder.PROTECTED_STATUS for stage in stages[-3:]), "emitted protected stages remain held")
    check(pack.get("launchable") is False, "emitted pack remains non-launchable")
    claims = pack.get("productionClaims")
    check(isinstance(claims, dict) and claims and all(value is False for value in claims.values()), "emitted production claims remain false")
    source = pack.get("source")
    check(isinstance(source, dict) and evidence_builder.HEX40.fullmatch(source.get("commit", "")) is not None, "emitted source commit is exact")
    check(evidence_builder.HEX40.fullmatch(source.get("tree", "")) is not None, "emitted source tree is exact")
    check(isinstance(source.get("branch"), str) and bool(source["branch"].strip()), "emitted source branch is named")
    cleanup = pack.get("cleanup")
    check(isinstance(cleanup, dict) and isinstance(cleanup.get("pass"), bool), "emitted cleanup result is explicit")
    local_pass = all(stage.get("status") == "PASS" for stage in stages[:10]) and cleanup["pass"]
    expected_status = evidence_builder.LOCAL_PASS_STATUS if local_pass else evidence_builder.LOCAL_FAIL_STATUS
    check(pack.get("overallStatus") == expected_status, "emitted overall status matches local stages and cleanup")
    check(pack.get("localStagesPass") is local_pass, "emitted local pass flag matches evidence")
    check(str(ROOT) not in raw and str(Path.home()) not in raw, "emitted pack omits absolute repo and home paths")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, help="Also verify one emitted pack without executing its commands.")
    args = parser.parse_args()

    stages = evidence_builder.STAGES
    check(len(stages) == 13, "contract has exactly 13 stages")
    check([stage.order for stage in stages] == list(range(1, 14)), "stage order is exact and contiguous")
    check(len({stage.stage_id for stage in stages}) == 13, "stage ids are unique")
    check([stage.stage_class for stage in stages[-3:]] == ["protected_held"] * 3, "last three stages are protected holds")
    check(all(not stage.commands for stage in stages[-3:]), "protected stages execute no command")
    check(all(stage.held_reason and stage.smallest_operator_action for stage in stages[-3:]), "protected stages name reason and smallest operator action")
    check(
        stages[2].commands == (
            (evidence_builder.PYTHON, "bin/check_agentwars_product.py"),
            (evidence_builder.PYTHON, "bin/check_fantasy_games.py"),
            (evidence_builder.PYTHON, "-B", "bin/check_agentwars_league_operations.py"),
            (evidence_builder.PYTHON, "-B", "bin/check_agentwars_commissioner.py"),
            (evidence_builder.PYTHON, "-B", "bin/check_agentwars_starter_kit.py"),
            (evidence_builder.PYTHON, "bin/check_agentwars_scale.py"),
        ),
        "stage 3 runs product, fantasy, finite-league operations, commissioner, starter, and scale gates",
    )
    check(
        stages[2].evidence_files == (
            "docs/AGENTWARS_FINITE_FANTASY_LEAGUE_OPERATIONS.md",
            "docs/AGENTWARS_COMMISSIONER_STARTER.md",
            "docs/AGENTWARS_STARTER_KIT.md",
        ),
        "stage 3 binds the finite fantasy league operations, commissioner, and starter contracts",
    )
    check(stages[7].stage_id == "real_browser_acceptance", "browser evidence is stage 8")
    check(
        stages[6].evidence_files == (
            "publishing/corrections.py",
            "publishing/agentwars-public-correction-ledger.v1.json",
            "docs/AGENTWARS_PUBLIC_CORRECTIONS.md",
            "docs/BUILDERWARS_MOBILE_AGENT_PASSPORTS.md",
        ),
        "stage 7 binds corrections plus the mobile Agent Passport disclosure contract",
    )
    check(
        stages[8].commands == (
            (evidence_builder.PYTHON, "-m", "unittest", "discover", "-s", "provider_hub_hosted/tests", "-p", "test_*.py"),
            (evidence_builder.PYTHON, "-B", "bin/check_entrant_admission.py"),
            (evidence_builder.PYTHON, "-B", "bin/check_builderwars_capacity.py"),
            (evidence_builder.PYTHON, "-B", "bin/check_builderwars_data_map.py"),
            (evidence_builder.PYTHON, "bin/check_builderwars_threat_model.py"),
        ),
        "stage 9 runs hosted abuse, entrant refusal, capacity-correctness, reference data-map, browser-authorization, and repository-grounded threat-model tests",
    )
    check(stages[8].evidence_files == (
        "arena/admission.py",
        "arena/reference_sources.py",
        "publishing/capacity_readiness.py",
        "docs/BUILDERWARS_BETA_CAPACITY_READINESS.md",
        "docs/BUILDERWARS_REFERENCE_DATA_MAP.md",
        "docs/BUILDERWARS_THREAT_MODEL.md",
        "docs/AGENTWARS_BROWSER_AUTHORIZATION_BOUNDARY.md",
    ), "stage 9 binds executable admission, reviewed source authority, capacity readiness, the reference data map, the threat model, and browser-authorization boundary")
    check(stages[8].not_proven == (
        "production Clerk session verification",
        "production owner pepper custody",
        "production store",
        "durable edge and account rate limits",
        "operator-approved beta capacity target and production load-test receipt",
        "production backpressure, saturation, and capacity acceptance",
        "production idempotency store parity, response-key custody, and rotation execution",
        "production deletion",
        "production regions, subprocessors, privacy obligations, and exact retention periods",
        "OS-level untrusted-code isolation",
        "external penetration review",
        "production security approval",
    ), "stage 9 keeps production auth, idempotency, store, isolation, and review gaps exact")
    check(stages[9].stage_id == "launch_contracts_and_rollback_plan" and stages[9].stage_class == "local_executable", "launch contracts are executable stage 10")
    check(
        stages[9].commands == (
            (evidence_builder.PYTHON, "bin/check_agentwars_measurement.py"),
            (evidence_builder.PYTHON, "bin/check_mobile_arena_performance_budget.py"),
            (evidence_builder.PYTHON, "bin/check_agentwars_observability.py"),
            (evidence_builder.PYTHON, "-B", "bin/check_agentwars_support.py"),
            (evidence_builder.PYTHON, "bin/check_agentwars_retention_recovery.py"),
            (evidence_builder.PYTHON, "bin/check_agentwars_tester_readiness.py"),
            (evidence_builder.PYTHON, "-B", "bin/check_agentwars_discoverability.py"),
        ),
        "stage 10 runs the exact measurement, performance, observability, support, retention/recovery, tester-readiness, and discoverability gates",
    )
    check(stages[10].stage_id == "protected_runtime_configuration", "protected runtime is the first held gate")

    commands = [command for stage in stages for command in stage.commands]
    check(len(commands) == 25, "local evidence contract has exactly 25 bounded commands")
    check(all(command and command[0] == evidence_builder.PYTHON for command in commands), "every executable stage uses the current Python runtime directly")
    flattened = " ".join(token for command in commands for token in command).lower()
    for forbidden in ("curl ", "invoke-webrequest", "vercel", "cloudflare", "git push", "deploy", "publish", "oauth", "clerk"):
        check(forbidden not in flattened, f"local command contract excludes mutation token {forbidden!r}")
    check(all(not any(character in token for character in "|;&><") for command in commands for token in command), "commands contain no shell metacharacters")

    contract = evidence_builder.stage_contract()
    check([row["id"] for row in contract] == [stage.stage_id for stage in stages], "listed contract preserves exact stage ids")
    check(contract[-1]["commands"] == [], "listed launch-authority stage stays commandless")

    with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "synthetic-secret"}, clear=False):
        safe_environment = evidence_builder.safe_child_env()
    check("OPENROUTER_API_KEY" not in safe_environment, "child environment strips ambient provider credentials")
    check(
        set(safe_environment).issubset(set(evidence_builder.SAFE_CHILD_ENV_KEYS) | {"PYTHONDONTWRITEBYTECODE", "PYTHONIOENCODING", "NO_COLOR"}),
        "child environment is a closed allowlist",
    )

    pack = evidence_builder.build_pack(
        observed_at="2026-09-01T00:00:00+00:00",
        source_observer=clean_source,
        command_runner=passing_runner,
    )
    check(pack["schema"] == evidence_builder.SCHEMA, "pack schema is pinned")
    check(pack["packClass"] == "local_launch_candidate", "pack cannot claim production class")
    check(pack["stageCount"] == 13 and len(pack["stages"]) == 13, "pack carries all 13 stages")
    check(pack["overallStatus"] == evidence_builder.LOCAL_PASS_STATUS, "passing local stages remain protected-held overall")
    check(pack["localStagesPass"] is True, "local pass is explicit")
    check(pack["protectedStagesHeld"] is True, "protected holds are explicit")
    check(pack["launchable"] is False, "local pack is never launchable")
    check(all(value is False for value in pack["productionClaims"].values()), "every production claim remains false")
    check(pack["nextGate"]["stage"] == 11, "next gate is the first protected stage")
    check(evidence_builder.verify_pack_digest(pack), "pack digest verifies over canonical bytes")

    canonical = evidence_builder.canonical_bytes(pack).decode("utf-8")
    check(str(ROOT) not in canonical and str(Path.home()) not in canonical, "pack omits absolute repo and home paths")
    check("synthetic local PASS" in canonical, "bounded command summaries remain available")

    def failing_runner(argv: Sequence[str], timeout_seconds: int) -> dict[str, Any]:
        record = passing_runner(argv, timeout_seconds)
        if any(token.endswith("selfcheck.py") for token in argv):
            record.update(status="FAIL", exitCode=1, summary="synthetic refusal")
        return record

    failed_pack = evidence_builder.build_pack(
        observed_at="2026-09-01T00:00:00+00:00",
        source_observer=clean_source,
        command_runner=failing_runner,
    )
    check(failed_pack["overallStatus"] == evidence_builder.LOCAL_FAIL_STATUS, "one failed executable stage fails the pack")
    check(failed_pack["stages"][1]["status"] == "FAIL", "failed command is attributed to its exact stage")
    check(failed_pack["launchable"] is False, "failed pack remains non-launchable")
    check(evidence_builder.verify_pack_digest(failed_pack), "failed pack remains digest-verifiable evidence")

    dirty = clean_source()
    dirty.update(clean=False, dirtyEntryCount=1)
    dirty_pack = evidence_builder.build_pack(
        observed_at="2026-09-01T00:00:00+00:00",
        source_observer=lambda: dict(dirty),
        command_runner=passing_runner,
    )
    check(dirty_pack["stages"][0]["status"] == "FAIL", "dirty source fails custody stage")
    check(all(stage["status"] == "NOT_RUN_SOURCE_CUSTODY" for stage in dirty_pack["stages"][1:10]), "dirty source prevents all later local execution")
    check(dirty_pack["cleanup"]["pass"] is False, "dirty source fails cleanup proof")
    check(dirty_pack["overallStatus"] == evidence_builder.LOCAL_FAIL_STATUS, "dirty source fails overall local status")

    malformed = clean_source()
    malformed["tree"] = "not-a-tree"
    malformed_pack = evidence_builder.build_pack(
        observed_at="2026-09-01T00:00:00+00:00",
        source_observer=lambda: dict(malformed),
        command_runner=passing_runner,
    )
    check(malformed_pack["stages"][0]["status"] == "FAIL", "malformed source tree fails custody")
    check(all(stage["status"] == "NOT_RUN_SOURCE_CUSTODY" for stage in malformed_pack["stages"][1:10]), "malformed source prevents local execution")

    source_reads = 0

    def branch_drift_source() -> dict[str, Any]:
        nonlocal source_reads
        source_reads += 1
        value = clean_source()
        if source_reads > 1:
            value["branch"] = "release/drifted"
        return value

    branch_drift_pack = evidence_builder.build_pack(
        observed_at="2026-09-01T00:00:00+00:00",
        source_observer=branch_drift_source,
        command_runner=passing_runner,
    )
    check(branch_drift_pack["cleanup"]["sourceBranchUnchanged"] is False, "branch drift is attributed during cleanup")
    check(branch_drift_pack["overallStatus"] == evidence_builder.LOCAL_FAIL_STATUS, "branch drift fails the pack")

    sample = b'{"evidence":"immutable"}\n'
    with tempfile.TemporaryDirectory(prefix="agentwars-evidence-contract-") as temporary:
        destination = Path(temporary) / "pack.json"
        evidence_builder.write_exclusive(destination, sample)
        check(destination.read_bytes() == sample, "exclusive writer preserves exact bytes")
        try:
            evidence_builder.write_exclusive(destination, b"rewrite")
        except FileExistsError:
            check(True, "exclusive writer refuses overwrite")
        else:
            raise AssertionError("exclusive writer overwrote evidence")

    allowed = evidence_builder.resolve_output_path(Path("output/launch-evidence/test/pack.json"))
    check(allowed == (ROOT / "output/launch-evidence/test/pack.json").resolve(), "output resolver accepts bounded evidence path")
    try:
        evidence_builder.resolve_output_path(Path("outside-pack.json"))
    except ValueError:
        check(True, "output resolver refuses path outside evidence root")
    else:
        raise AssertionError("output resolver allowed path outside evidence root")

    compact = json.dumps(pack, separators=(",", ":"))
    for forbidden_claim in ('"launchable":true', '"publicLaunch":true', '"productionDeployed":true'):
        check(forbidden_claim not in compact, f"pack cannot emit {forbidden_claim}")

    if args.pack:
        check_emitted_pack(args.pack.resolve())

    print(f"AgentWars local launch evidence contract: PASS ({checks} checks)")
    print("13 ordered stages / 10 local / 3 protected held / immutable output / zero launch overclaim")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
