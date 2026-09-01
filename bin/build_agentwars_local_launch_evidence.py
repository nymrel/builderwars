#!/usr/bin/env python3
"""Assemble the source-bound 13-stage AgentWars local launch evidence pack.

The pack executes local, credential-free checks only. Protected runtime,
deployment, real-customer, independent-review, and launch-authority stages are
recorded as HELD and never inferred from local success.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_OUTPUT_ROOT = ROOT / "output" / "launch-evidence"
SCHEMA = "agentwars.local-launch-evidence-pack/1"
PACK_CLASS = "local_launch_candidate"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
PROTECTED_STATUS = "HELD_PROTECTED"
LOCAL_PASS_STATUS = "LOCAL_PASS_PROTECTED_HELD"
LOCAL_FAIL_STATUS = "LOCAL_FAIL"
SAFE_CHILD_ENV_KEYS = (
    "COMSPEC",
    "HOMEDRIVE",
    "HOMEPATH",
    "LOCALAPPDATA",
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "USERPROFILE",
    "WINDIR",
)


@dataclass(frozen=True)
class StageDefinition:
    order: int
    stage_id: str
    label: str
    stage_class: str
    commands: tuple[tuple[str, ...], ...] = ()
    timeout_seconds: int = 180
    evidence_files: tuple[str, ...] = ()
    held_reason: str | None = None
    smallest_operator_action: str | None = None
    not_proven: tuple[str, ...] = ()


PYTHON = "{python}"


STAGES: tuple[StageDefinition, ...] = (
    StageDefinition(
        1,
        "source_custody",
        "Exact source, branch, tree, and cleanliness",
        "local_observation",
        evidence_files=(".git",),
        not_proven=("canonical main integration", "remote custody", "deployment source binding"),
    ),
    StageDefinition(
        2,
        "deterministic_arena",
        "Deterministic arena and adversarial engine self-check",
        "local_executable",
        commands=((PYTHON, "bin/selfcheck.py"),),
        not_proven=("hosted execution", "provider execution", "production containment"),
    ),
    StageDefinition(
        3,
        "product_leagues_and_scale",
        "Public product, redraft/dynasty rules, and deterministic scale",
        "local_executable",
        commands=(
            (PYTHON, "bin/check_agentwars_product.py"),
            (PYTHON, "bin/check_fantasy_games.py"),
            (PYTHON, "bin/check_agentwars_scale.py"),
        ),
        not_proven=("live league", "audience", "retention", "ranked competition"),
    ),
    StageDefinition(
        4,
        "provider_boundaries_and_regressions",
        "Provider boundary contracts and full repository regression ladder",
        "local_executable",
        commands=((PYTHON, "bin/check_provider_hub.py"),),
        timeout_seconds=360,
        not_proven=("customer provider authorization", "provider identity", "paid compute", "production secrets"),
    ),
    StageDefinition(
        5,
        "runner_bundle_and_dependencies",
        "Immutable runner bundle and offline dependency integrity",
        "local_executable",
        commands=(
            (PYTHON, "-B", "bin/check_agentwars_dependency_lock.py"),
            (PYTHON, "-B", "bin/check_agentwars_runner_bundle.py"),
        ),
        timeout_seconds=240,
        not_proven=("public artifact publication", "download hosting", "Nymrel signature", "provider runtime identity"),
    ),
    StageDefinition(
        6,
        "replay_and_verifier_parity",
        "Package and standalone verifier parity",
        "local_executable",
        commands=((PYTHON, "bin/build_verifier.py", "--check"),),
        not_proven=("production receipt custody", "public registry commit", "external reviewer signature"),
    ),
    StageDefinition(
        7,
        "mobile_static_contracts",
        "Mobile Arena deterministic, offline, accessibility, and truth contracts",
        "local_executable",
        commands=((PYTHON, "bin/check_mobile_arena_exchange.py"),),
        not_proven=("hosted mobile route", "real user", "supported-device deployment"),
    ),
    StageDefinition(
        8,
        "real_browser_acceptance",
        "Real Chromium navigation, failures, accessibility, offline, and responsive proof",
        "local_executable",
        commands=((PYTHON, "bin/check_mobile_arena_browser.py"),),
        timeout_seconds=180,
        not_proven=("production browser", "authenticated journey", "external network", "production performance"),
    ),
    StageDefinition(
        9,
        "hosted_security_abuse_and_cleanup",
        "Hosted-control-plane security, refusal, rollback, cleanup, and repository-grounded threat-model tests",
        "local_executable",
        commands=(
            (PYTHON, "-m", "unittest", "discover", "-s", "provider_hub_hosted/tests", "-p", "test_*.py"),
            (PYTHON, "bin/check_builderwars_threat_model.py"),
        ),
        evidence_files=(
            "docs/BUILDERWARS_THREAT_MODEL.md",
            "docs/AGENTWARS_BROWSER_AUTHORIZATION_BOUNDARY.md",
        ),
        timeout_seconds=180,
        not_proven=(
            "production Clerk session verification",
            "production owner pepper custody",
            "production store",
            "durable edge and account rate limits",
            "production idempotency store parity and response-key custody",
            "production deletion",
            "OS-level untrusted-code isolation",
            "external penetration review",
            "production security approval",
        ),
    ),
    StageDefinition(
        10,
        "launch_contracts_and_rollback_plan",
        "Launch, measurement, performance, observability, incident, rollback, retention, tester-readiness, and truth-boundary contracts",
        "local_executable",
        commands=(
            (PYTHON, "bin/check_agentwars_measurement.py"),
            (PYTHON, "bin/check_mobile_arena_performance_budget.py"),
            (PYTHON, "bin/check_agentwars_observability.py"),
            (PYTHON, "bin/check_agentwars_retention_recovery.py"),
            (PYTHON, "bin/check_agentwars_tester_readiness.py"),
        ),
        evidence_files=(
            "docs/BUILDERWARS_COM_DOMAIN_CUTOVER_CONTRACT.md",
            "docs/BUILDERWARS_COMPONENT_ACCEPTANCE_DECISIONS.md",
            "docs/AGENTWARS_NORTH_STAR.v1.json",
            "docs/AGENTWARS_MEASUREMENT_CONTRACT.md",
            "docs/AGENTWARS_PERFORMANCE_BUDGET.md",
            "docs/AGENTWARS_OBSERVABILITY_INCIDENT_CONTRACT.md",
            "docs/AGENTWARS_RETENTION_DELETION_ROLLBACK_RECOVERY.md",
            "docs/AGENTWARS_TESTER_CEREMONY.md",
            "docs/AGENTWARS_LOCAL_LAUNCH_EVIDENCE_PACK.md",
        ),
        not_proven=("consented human tester and feedback", "production deletion and backup/restore", "production rollback rehearsal", "production telemetry and alert delivery", "production performance", "staffed support response", "legal approval"),
    ),
    StageDefinition(
        11,
        "protected_runtime_configuration",
        "Clerk, Redis, reviewer, rate-limit, webhook, pepper, and feature-flag configuration",
        "protected_held",
        held_reason="Protected account/runtime configuration has not been independently verified for the exact release source.",
        smallest_operator_action="Authorize the named protected configuration ceremony against the exact integrated source; do not disclose secrets in the pack.",
        not_proven=("authentication", "tenant ownership", "production state", "deletion webhook", "rate-limit enforcement"),
    ),
    StageDefinition(
        12,
        "source_bound_deployment_and_rollback",
        "Source-bound production deployment, DNS, served bytes, performance, observability, and rollback",
        "protected_held",
        held_reason="No authorized BuilderWars production target, source-bound deployment, DNS cutover, or rollback rehearsal is recorded by this local pack.",
        smallest_operator_action="Authorize one exact deployment target and rollback target after protected configuration passes; BuilderWars.com apex and www remain untouched.",
        not_proven=("production host", "DNS", "TLS", "served-byte parity", "performance", "observability", "rollback"),
    ),
    StageDefinition(
        13,
        "consented_tester_review_and_launch_authority",
        "Fresh consented tester journey, independent review, signed production pack, and launch authorization",
        "protected_held",
        held_reason="No fresh consented production tester journey, detached independent review, signed production pack, or separate launch authorization is recorded.",
        smallest_operator_action="After stages 11 and 12 pass, consent to the exact tester journey and later record a separate launch decision only if every receipt verifies and cleanup completes.",
        not_proven=("real customer", "provider-backed match", "account deletion", "independent signature", "public launch authority"),
    ),
)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_text(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def observe_source() -> dict[str, Any]:
    commit = git_text("rev-parse", "HEAD")
    tree = git_text("rev-parse", "HEAD^{tree}")
    branch = git_text("branch", "--show-current")
    porcelain = git_text("status", "--porcelain=v1", "--untracked-files=all")
    return {
        "commit": commit,
        "tree": tree,
        "branch": branch,
        "clean": porcelain == "",
        "dirtyEntryCount": 0 if porcelain == "" else len(porcelain.splitlines()),
        "canonicalMainIntegrated": False,
        "remoteCustodyProven": False,
    }


def resolve_argv(argv: Sequence[str]) -> list[str]:
    return [sys.executable if token == PYTHON else token for token in argv]


def display_argv(argv: Sequence[str]) -> list[str]:
    return ["python" if token == sys.executable else token for token in argv]


def sanitize_output(value: bytes) -> str:
    text = value.decode("utf-8", errors="replace").replace("\r\n", "\n")
    replacements = ((str(ROOT), "<repo>"), (str(Path.home()), "<home>"))
    for raw, replacement in replacements:
        text = text.replace(raw, replacement).replace(raw.replace("\\", "/"), replacement)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return " | ".join(lines[-3:])[:1200]


def safe_child_env() -> dict[str, str]:
    """Return only non-secret system values required by local check processes."""
    environment = {
        name: os.environ[name]
        for name in SAFE_CHILD_ENV_KEYS
        if isinstance(os.environ.get(name), str)
    }
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    environment["NO_COLOR"] = "1"
    return environment


def run_command(argv: Sequence[str], timeout_seconds: int) -> dict[str, Any]:
    resolved = resolve_argv(argv)
    started = time.monotonic()
    try:
        completed = subprocess.run(
            resolved,
            cwd=ROOT,
            env=safe_child_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
        )
        duration_ms = round((time.monotonic() - started) * 1000)
        return {
            "argv": display_argv(resolved),
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "exitCode": completed.returncode,
            "timedOut": False,
            "durationMs": duration_ms,
            "stdoutSha256": sha256_bytes(completed.stdout),
            "stderrSha256": sha256_bytes(completed.stderr),
            "summary": sanitize_output(completed.stdout or completed.stderr),
        }
    except subprocess.TimeoutExpired as error:
        duration_ms = round((time.monotonic() - started) * 1000)
        stdout = error.stdout or b""
        stderr = error.stderr or b""
        if isinstance(stdout, str):
            stdout = stdout.encode("utf-8", errors="replace")
        if isinstance(stderr, str):
            stderr = stderr.encode("utf-8", errors="replace")
        return {
            "argv": display_argv(resolved),
            "status": "FAIL",
            "exitCode": None,
            "timedOut": True,
            "durationMs": duration_ms,
            "stdoutSha256": sha256_bytes(stdout),
            "stderrSha256": sha256_bytes(stderr),
            "summary": sanitize_output(stdout or stderr) or f"timed out after {timeout_seconds}s",
        }


def inspect_files(relative_paths: Iterable[str]) -> tuple[list[dict[str, Any]], list[str]]:
    evidence: list[dict[str, Any]] = []
    missing: list[str] = []
    for relative in relative_paths:
        if relative == ".git":
            continue
        path = ROOT / relative
        if not path.is_file():
            missing.append(relative)
            continue
        evidence.append({"path": relative.replace("\\", "/"), "sha256": file_sha256(path), "bytes": path.stat().st_size})
    return evidence, missing


def build_pack(
    *,
    observed_at: str | None = None,
    source_observer: Callable[[], dict[str, Any]] = observe_source,
    command_runner: Callable[[Sequence[str], int], dict[str, Any]] = run_command,
) -> dict[str, Any]:
    source_before = source_observer()
    source_eligible = bool(
        source_before["clean"]
        and source_before["dirtyEntryCount"] == 0
        and HEX40.fullmatch(source_before["commit"])
        and HEX40.fullmatch(source_before["tree"])
        and source_before["branch"].strip()
    )
    stages: list[dict[str, Any]] = []
    for definition in STAGES:
        base: dict[str, Any] = {
            "order": definition.order,
            "id": definition.stage_id,
            "label": definition.label,
            "class": definition.stage_class,
            "notProven": list(definition.not_proven),
        }
        if definition.stage_class == "protected_held":
            base.update(
                status=PROTECTED_STATUS,
                commands=[],
                evidence=[],
                heldReason=definition.held_reason,
                smallestOperatorAction=definition.smallest_operator_action,
            )
        elif definition.stage_id == "source_custody":
            base.update(
                status="PASS" if source_eligible else "FAIL",
                commands=[],
                evidence=[
                    {"type": "git_commit", "value": source_before["commit"]},
                    {"type": "git_tree", "value": source_before["tree"]},
                    {"type": "branch", "value": source_before["branch"]},
                    {"type": "clean", "value": source_before["clean"]},
                ],
            )
        elif not source_eligible:
            base.update(
                status="NOT_RUN_SOURCE_CUSTODY",
                commands=[],
                evidence=[],
                heldReason="Stage 1 source custody failed; later local evidence was not executed.",
            )
        elif definition.stage_class == "local_observation":
            evidence, missing = inspect_files(definition.evidence_files)
            base.update(status="PASS" if not missing else "FAIL", commands=[], evidence=evidence, missing=missing)
        else:
            command_records = [command_runner(command, definition.timeout_seconds) for command in definition.commands]
            evidence, missing = inspect_files(definition.evidence_files)
            base.update(
                status="PASS" if all(record["status"] == "PASS" for record in command_records) and not missing else "FAIL",
                commands=command_records,
                evidence=evidence,
                missing=missing,
            )
        stages.append(base)

    source_after = source_observer()
    cleanup_clean = bool(
        source_after["clean"]
        and source_after["dirtyEntryCount"] == 0
        and source_after["commit"] == source_before["commit"]
        and source_after["tree"] == source_before["tree"]
        and source_after["branch"] == source_before["branch"]
    )
    local_stages = [stage for stage in stages if stage["class"] != "protected_held"]
    local_pass = all(stage["status"] == "PASS" for stage in local_stages) and cleanup_clean
    pack: dict[str, Any] = {
        "schema": SCHEMA,
        "packClass": PACK_CLASS,
        "observedAt": observed_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": source_before,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.system(),
            "architecture": platform.machine(),
            "networkScope": "loopback_only_for_browser_stage; all other stages local and credential-free",
        },
        "stageCount": len(stages),
        "stages": stages,
        "cleanup": {
            "sourceCommitUnchanged": source_after["commit"] == source_before["commit"],
            "sourceTreeUnchanged": source_after["tree"] == source_before["tree"],
            "sourceBranchUnchanged": source_after["branch"] == source_before["branch"],
            "worktreeCleanAfter": source_after["clean"],
            "pass": cleanup_clean,
        },
        "overallStatus": LOCAL_PASS_STATUS if local_pass else LOCAL_FAIL_STATUS,
        "localStagesPass": local_pass,
        "protectedStagesHeld": all(stage["status"] == PROTECTED_STATUS for stage in stages[-3:]),
        "launchable": False,
        "productionClaims": {
            "canonicalMainIntegrated": False,
            "protectedRuntimeVerified": False,
            "productionDeployed": False,
            "dnsCutoverVerified": False,
            "providerConnected": False,
            "identityAttested": False,
            "consentedTesterCompleted": False,
            "independentReviewSigned": False,
            "operatorLaunchAuthorized": False,
            "publicLaunch": False,
        },
        "nextGate": {
            "stage": 11,
            "id": "protected_runtime_configuration",
            "action": STAGES[10].smallest_operator_action,
        },
    }
    pack["packDigest"] = sha256_bytes(canonical_bytes(pack))
    return pack


def verify_pack_digest(pack: dict[str, Any]) -> bool:
    candidate = dict(pack)
    digest = candidate.pop("packDigest", None)
    return isinstance(digest, str) and digest == sha256_bytes(canonical_bytes(candidate))


def write_exclusive(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def resolve_output_path(value: Path) -> Path:
    candidate = value if value.is_absolute() else ROOT / value
    candidate = candidate.resolve()
    try:
        candidate.relative_to(EVIDENCE_OUTPUT_ROOT.resolve())
    except ValueError as error:
        raise ValueError("evidence output must stay under output/launch-evidence") from error
    return candidate


def stage_contract() -> list[dict[str, Any]]:
    return [
        {
            "order": stage.order,
            "id": stage.stage_id,
            "label": stage.label,
            "class": stage.stage_class,
            "commands": [["python" if token == PYTHON else token for token in command] for command in stage.commands],
            "heldReason": stage.held_reason,
        }
        for stage in STAGES
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write one new immutable JSON pack; existing paths are refused.")
    parser.add_argument("--list-stages", action="store_true", help="Print the ordered stage contract without executing checks.")
    parser.add_argument("--require-launchable", action="store_true", help="Return 3 while any protected stage remains held.")
    args = parser.parse_args()

    if args.list_stages:
        print(json.dumps(stage_contract(), indent=2))
        return 0

    try:
        pack = build_pack()
        if not verify_pack_digest(pack):
            raise RuntimeError("internal pack digest verification failed")
        encoded = json.dumps(pack, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
        if args.output:
            output_path = resolve_output_path(args.output)
            write_exclusive(output_path, encoded)
            print(
                json.dumps(
                    {
                        "status": pack["overallStatus"],
                        "output": output_path.relative_to(ROOT).as_posix(),
                        "sourceCommit": pack["source"]["commit"],
                        "packDigest": pack["packDigest"],
                        "stageCount": pack["stageCount"],
                        "launchable": pack["launchable"],
                    },
                    indent=2,
                )
            )
        else:
            sys.stdout.buffer.write(encoded)
    except FileExistsError as error:
        print(json.dumps({"status": "REFUSED", "message": f"evidence path already exists: {error.filename}"}, indent=2))
        return 2
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error": type(error).__name__, "message": str(error)}, indent=2))
        return 1

    if pack["overallStatus"] == LOCAL_FAIL_STATUS:
        return 1
    if args.require_launchable and not pack["launchable"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
