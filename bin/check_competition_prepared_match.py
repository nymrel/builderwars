#!/usr/bin/env python3
"""Offline adversarial checks for fixed prepared-match execution.

No provider or network is contacted. The only live subprocess proof creates a
temporary Python parent and grandchild, then proves arena cleanup terminates
both through the host's process-tree custody primitive.
"""

from __future__ import annotations

import contextlib
import copy
import ctypes
import io
import json
import os
import socket
import sys
import tempfile
import time
from pathlib import Path
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "bin")
sys.path.insert(0, ROOT)
sys.path.insert(0, BIN)

from arena.canonical import digest  # noqa: E402
from arena import match as arena_match  # noqa: E402
from arena.sandbox import POLICY, Entrant  # noqa: E402
from competitions import prepared_match, source_match  # noqa: E402
from provider_hub.local_runner import RunnerClientError, digest_harness_file  # noqa: E402
import agentwars as runner_cli  # noqa: E402
import check_competition_source_match as source_checks  # noqa: E402


CHECKS = 0
SECRET_SENTINEL = "provider-secret-must-never-render"


def check(condition, label):
    global CHECKS
    if not condition:
        raise AssertionError(label)
    CHECKS += 1


def expect_error(action, fragment):
    try:
        action()
    except RunnerClientError as error:
        check(fragment in str(error), f"refusal contains {fragment!r}")
        check(SECRET_SENTINEL not in str(error), "refusal does not reflect a secret")
        return
    raise AssertionError(f"expected RunnerClientError containing {fragment!r}")


def write_plan(path: Path, plan: dict) -> None:
    path.write_text(
        json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def mutated_plan(plan: dict, mutation) -> dict:
    changed = copy.deepcopy(plan)
    mutation(changed)
    core = {key: value for key, value in changed.items() if key != "launchPlanDigest"}
    changed["launchPlanDigest"] = digest(core)
    return changed


def build_valid_plan(root: Path):
    harness_digest = digest_harness_file(str(source_match.FANTASY_HARNESS_PATH))
    profile = source_checks.profile(harness_digest)
    passports, passport_paths = source_checks.make_passports(root, harness_digest)
    preparation = source_checks.validate_ready(
        profile, source_checks.job_payload(harness_digest, passports)
    )
    plan_path = root / "prepared-plan.json"
    plan = source_match.build_source_match_plan(
        preparation,
        profile=profile,
        plan_path=str(plan_path),
        match_directory=str(root / "prepared-match"),
        summary_path=str(root / "prepared-summary.json"),
        passport_paths=passport_paths,
        backend_timeout=10.125,
    )
    source_match.write_source_match_plan(str(plan_path), plan)
    return plan_path, plan, passport_paths


def check_valid_execution(root: Path, plan_path: Path, plan: dict):
    captured = []

    def fixed_main(argv):
        captured.append(list(argv))
        return 0

    with (
        mock.patch.object(prepared_match, "_fixed_match_main", side_effect=fixed_main),
        mock.patch.object(
            socket, "create_connection", side_effect=AssertionError("network forbidden")
        ),
        mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": SECRET_SENTINEL}),
    ):
        prepared, status = prepared_match.execute_prepared_match(
            str(plan_path), customer_local_v1=True, provider_usage_v1=True
        )
    check(status == 0, "fixed runner status is returned")
    check(prepared.job_id == plan["jobId"], "prepared job id is exact")
    check(
        prepared.launch_plan_digest == plan["launchPlanDigest"],
        "prepared launch digest is exact",
    )
    check(len(captured) == 1, "one fixed match invocation occurs")
    check(
        captured[0] == [*plan["launch"]["argv"], *prepared_match.FRESH_EXECUTION_FLAGS],
        "only exact plan argv plus fresh consent reaches the fixed runner",
    )
    check(
        SECRET_SENTINEL not in json.dumps(captured), "ambient provider secret is absent"
    )

    with mock.patch.object(prepared_match, "_fixed_match_main") as blocked:
        expect_error(
            lambda: prepared_match.execute_prepared_match(
                str(plan_path), customer_local_v1=False, provider_usage_v1=True
            ),
            "fresh customer-local",
        )
        check(
            not blocked.called, "missing consent blocks before fixed runner invocation"
        )
    return prepared


def check_unsigned_provider_options(root: Path) -> None:
    variant_root = root / "unsigned-provider-options"
    variant_root.mkdir()
    harness_digest = digest_harness_file(str(source_match.FANTASY_HARNESS_PATH))
    profile = source_checks.profile(harness_digest)
    payload = source_checks.job_payload(harness_digest)
    payload["seats"][0].update(
        {
            "providerClaim": "openrouter",
            "selectedModelClaim": "openai/gpt-5",
            "backendClaim": "openrouter:openai/gpt-5",
        }
    )
    payload["seats"][1].update(
        {
            "providerClaim": "hermes",
            "selectedModelClaim": "nousresearch/hermes-3",
            "variantClaim": None,
            "backendClaim": "hermes:nousresearch/hermes-3",
        }
    )
    preparation = source_checks.validate_ready(profile, payload)
    plan_path = variant_root / "plan.json"
    plan = source_match.build_source_match_plan(
        preparation,
        profile=profile,
        plan_path=str(plan_path),
        match_directory=str(variant_root / "match"),
        summary_path=str(variant_root / "summary.json"),
        passport_paths=None,
        backend_timeout=12.5,
    )
    source_match.write_source_match_plan(str(plan_path), plan)
    prepared = prepared_match.load_prepared_match(str(plan_path))
    check("--agent-passports" not in prepared.argv, "unsigned plan invents no passport")
    check(
        "--seat0-model=openai/gpt-5" in prepared.argv,
        "OpenRouter model option remains exact",
    )
    check(
        "--seat1-model=nousresearch/hermes-3" in prepared.argv,
        "Hermes model option remains exact",
    )
    with mock.patch.object(
        prepared_match, "_fixed_match_main", return_value=2
    ) as fixed:
        retained, status = prepared_match.execute_prepared_match(
            str(plan_path), customer_local_v1=True, provider_usage_v1=True
        )
    check(status == 2 and retained == prepared, "valid fallback status is preserved")
    check(
        fixed.call_count == 1,
        "unsigned provider-options plan invokes fixed runner once",
    )


def check_hostile_plans(root: Path, plan_path: Path, plan: dict, passport_paths):
    cases = []

    def add(label, fragment, mutation):
        cases.append((label, fragment, mutated_plan(plan, mutation)))

    add(
        "unknown launch environment",
        "exact schema",
        lambda value: value["launch"].update({"environment": {"SECRET": "value"}}),
    )
    add(
        "arbitrary entrypoint",
        "fixed runner",
        lambda value: value["launch"].update({"entrypoint": "bin/hostile.py"}),
    )
    add(
        "extra arbitrary argv",
        "fixed plan data",
        lambda value: value["launch"]["argv"].__setitem__(0, "--command=hostile"),
    )
    add(
        "serialized provider consent",
        "fixed plan data",
        lambda value: value["launch"]["argv"].__setitem__(0, "--provider-usage-v1"),
    )
    add(
        "changed fixed runner digest",
        "runner bytes changed",
        lambda value: value.update({"matchRunnerSha256": "0" * 64}),
    )
    add(
        "changed harness digest",
        "harness bytes changed",
        lambda value: value.update({"requiredHarnessDigest": "0" * 64}),
    )
    add(
        "changed engine",
        "engine snapshot",
        lambda value: value.update({"engineSha256": "0" * 64}),
    )
    add(
        "same provider seats",
        "provider claims must differ",
        lambda value: value["seats"][1].update(
            {
                "providerClaim": value["seats"][0]["providerClaim"],
                "backendClaim": value["seats"][0]["backendClaim"],
                "selectedModelClaim": value["seats"][0]["selectedModelClaim"],
                "variantClaim": value["seats"][0]["variantClaim"],
            }
        ),
    )
    add(
        "disabled provider route",
        "provider is unsupported",
        lambda value: value["seats"][1].update(
            {
                "providerClaim": "claude_code",
                "selectedModelClaim": None,
                "variantClaim": None,
                "backendClaim": "claude_code:claude -p",
            }
        ),
    )
    add(
        "execution overclaim",
        "overstates execution",
        lambda value: value.update({"providerExecutionRequested": True}),
    )
    add(
        "attestation overclaim",
        "overstates execution",
        lambda value: value.update({"modelAttested": True}),
    )
    add(
        "changed job commitment",
        "job commitment",
        lambda value: value.update({"jobCommitmentSha256": "f" * 64}),
    )
    for index, (label, fragment, value) in enumerate(cases):
        candidate = root / f"hostile-{index}.json"
        write_plan(candidate, value)
        expect_error(
            lambda candidate=candidate: prepared_match.load_prepared_match(
                str(candidate)
            ),
            fragment,
        )
        check(candidate.exists(), f"{label} candidate remains for local debugging")

    bad_digest = copy.deepcopy(plan)
    bad_digest["seed"] += 1
    bad_digest_path = root / "bad-digest.json"
    write_plan(bad_digest_path, bad_digest)
    expect_error(
        lambda: prepared_match.load_prepared_match(str(bad_digest_path)), "digest"
    )

    duplicate_path = root / "duplicate.json"
    raw = json.dumps(plan, sort_keys=True)
    duplicate_path.write_text(
        '{"schemaVersion":"duplicate",' + raw[1:], encoding="utf-8"
    )
    expect_error(
        lambda: prepared_match.load_prepared_match(str(duplicate_path)), "strict JSON"
    )

    float_path = root / "float.json"
    float_path.write_text(
        raw.replace('"seed": 9400', '"seed": 9400.0'), encoding="utf-8"
    )
    expect_error(
        lambda: prepared_match.load_prepared_match(str(float_path)), "strict JSON"
    )

    oversized_path = root / "oversized.json"
    oversized_path.write_bytes(b"{" + b" " * prepared_match.MAX_SOURCE_MATCH_PLAN_BYTES)
    expect_error(
        lambda: prepared_match.load_prepared_match(str(oversized_path)), "oversized"
    )

    passport = Path(passport_paths[0])
    original = passport.read_bytes()
    passport.write_bytes(original + b" ")
    try:
        expect_error(
            lambda: prepared_match.load_prepared_match(str(plan_path)),
            "passport bytes changed",
        )
    finally:
        passport.write_bytes(original)

    match_directory = Path(plan["launch"]["matchDirectory"])
    match_directory.mkdir()
    expect_error(
        lambda: prepared_match.load_prepared_match(str(plan_path)), "already exists"
    )


def check_cli_contract(plan_path: Path, prepared):
    argv = [
        "runner",
        "run-prepared-match",
        "--plan",
        str(plan_path),
        "--once",
        "--customer-local-v1",
        "--provider-usage-v1",
    ]
    parsed = runner_cli.build_parser().parse_args(argv)
    check(parsed.plan == str(plan_path), "CLI accepts one exact prepared plan")
    check(parsed.once is True, "CLI requires one-shot intent")
    with mock.patch.object(
        runner_cli, "execute_prepared_match", return_value=(prepared, 0)
    ) as execute:
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            status = runner_cli.main(argv)
    check(status == 0, "CLI returns fixed runner success")
    check(execute.call_count == 1, "CLI invokes one prepared execution")
    check(
        "attestations remain false" in stdout.getvalue(), "CLI preserves truth boundary"
    )

    with contextlib.redirect_stderr(io.StringIO()):
        try:
            runner_cli.build_parser().parse_args(
                ["runner", "run-prepared-match", "--plan", str(plan_path), "--once"]
            )
        except SystemExit as error:
            check(error.code == 2, "CLI refuses missing fresh consent flags")
        else:
            raise AssertionError("CLI accepted missing fresh consent")


def check_process_tree_cleanup(root: Path):
    helper = root / "tree-helper.py"
    pid_file = root / "tree-pids.json"
    helper.write_text(
        "import json, os, subprocess, sys, time\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
        "with open(os.environ['TREE_PID_FILE'], 'w', encoding='utf-8') as handle:\n"
        "    json.dump({'parent': os.getpid(), 'child': child.pid}, handle)\n"
        "    handle.flush()\n"
        "    os.fsync(handle.fileno())\n"
        "while True:\n"
        "    time.sleep(1)\n",
        encoding="utf-8",
    )
    entrant = Entrant(
        {
            "name": "process-tree-proof",
            "cmd": [sys.executable, str(helper)],
            "env": ["TREE_PID_FILE"],
        },
        root / "tree-scratch",
        provisioned_env={"TREE_PID_FILE": str(pid_file)},
    )
    pids = None
    try:
        entrant.start()
        pids = _wait_pid_file(pid_file)
        check(pids is not None, "contained parent published child custody proof")
        check(_process_alive(pids["parent"]), "contained parent is live before cleanup")
        check(
            _process_alive(pids["child"]), "contained grandchild is live before cleanup"
        )
    finally:
        entrant.close(grace_s=0.2)
    _wait_processes_dead(pids)
    check(pids is not None and not _process_alive(pids["parent"]), "parent is reaped")
    check(
        pids is not None and not _process_alive(pids["child"]),
        "provider-like grandchild is terminated",
    )
    check(
        any("descendant_process_tree_termination" in row for row in POLICY["enforced"]),
        "transcript policy declares descendant cleanup",
    )
    check(
        not any("process_tree_containment" in row for row in POLICY["unenforced_v1"]),
        "old direct-PID limitation is removed",
    )
    _check_match_interrupt_cleanup(root, helper)
    _check_cleanup_error_precedence(root, helper)


def _check_match_interrupt_cleanup(root: Path, helper: Path) -> None:
    pid_files = (root / "match-tree-0.json", root / "match-tree-1.json")
    manifests = [_tree_manifest(f"interrupt-seat-{seat}", helper) for seat in range(2)]
    provisioned = [{"TREE_PID_FILE": str(path)} for path in pid_files]
    calls = 0

    def interrupt_second_ask(self, *_args, **_kwargs):
        nonlocal calls
        published = _wait_pid_file(Path(self._provisioned_env["TREE_PID_FILE"]))
        check(published is not None, "match entrant published descendant pids")
        calls += 1
        if calls == 1:
            return {
                "type": "ready",
                "entrant": self.name,
                "version": "1",
                "backend": "process-tree-proof",
            }
        raise KeyboardInterrupt

    with mock.patch.object(
        Entrant, "ask", autospec=True, side_effect=interrupt_second_ask
    ):
        try:
            arena_match.run_match(
                game_name="fantasy_redraft",
                seed=9400,
                entrants=manifests,
                provisioned_envs=provisioned,
                out_dir=root / "interrupt-match",
                move_timeout_s=10,
            )
        except KeyboardInterrupt:
            check(True, "match cancellation propagates after custody cleanup")
        else:
            raise AssertionError("match cancellation was swallowed")
    published_rows = [_wait_pid_file(path) for path in pid_files]
    check(
        all(row is not None for row in published_rows),
        "both interrupted entrants started",
    )
    for row in published_rows:
        _wait_processes_dead(row)
        check(not _process_alive(row["parent"]), "interrupted entrant parent is reaped")
        check(
            not _process_alive(row["child"]),
            "interrupted entrant descendant is reaped",
        )


def _check_cleanup_error_precedence(root: Path, helper: Path) -> None:
    class FailingCleanupEntrant:
        def __init__(self, manifest, *_args, **_kwargs):
            self.name = manifest["name"]

        def start(self):
            return None

        def ask(self, *_args, **_kwargs):
            raise KeyboardInterrupt

        def close(self):
            raise RuntimeError("synthetic cleanup failure")

        def stderr_text(self):
            return ""

    manifests = [
        _tree_manifest(f"cleanup-failure-seat-{seat}", helper) for seat in range(2)
    ]
    with mock.patch.object(arena_match, "Entrant", FailingCleanupEntrant):
        try:
            arena_match.run_match(
                game_name="fantasy_redraft",
                seed=9401,
                entrants=manifests,
                provisioned_envs=[{"TREE_PID_FILE": "unused"}] * 2,
                out_dir=root / "cleanup-failure-match",
                move_timeout_s=10,
            )
        except RuntimeError as error:
            check(
                str(error) == "synthetic cleanup failure",
                "cleanup failure fails closed",
            )
            check(
                isinstance(error.__cause__, KeyboardInterrupt),
                "cleanup failure preserves cancellation as its cause",
            )
            check(
                any("another match exception" in note for note in error.__notes__),
                "cleanup failure records dual-failure custody context",
            )
        else:
            raise AssertionError("cleanup failure was hidden behind cancellation")


def _tree_manifest(name: str, helper: Path) -> dict:
    return {
        "name": name,
        "cmd": [sys.executable, str(helper)],
        "env": ["TREE_PID_FILE"],
        "claimed_model": "fixture:process-tree-proof",
        "execution_claim": "hybrid",
    }


def _wait_pid_file(path: Path) -> dict | None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and not path.exists():
        time.sleep(0.05)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _wait_processes_dead(pids: dict | None) -> None:
    deadline = time.monotonic() + 3
    while pids is not None and time.monotonic() < deadline:
        if not _process_alive(pids["parent"]) and not _process_alive(pids["child"]):
            return
        time.sleep(0.05)


def _process_alive(pid: int) -> bool:
    if os.name != "nt":
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = (ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32)
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.WaitForSingleObject.argtypes = (ctypes.c_void_p, ctypes.c_uint32)
    kernel32.WaitForSingleObject.restype = ctypes.c_uint32
    kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
    kernel32.CloseHandle.restype = ctypes.c_int
    handle = kernel32.OpenProcess(0x00100000, False, pid)
    if not handle:
        return False
    try:
        return kernel32.WaitForSingleObject(handle, 0) == 0x00000102
    finally:
        kernel32.CloseHandle(handle)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="agentwars-prepared-match-") as temp:
        root = Path(temp)
        plan_path, plan, passport_paths = build_valid_plan(root)
        prepared = check_valid_execution(root, plan_path, plan)
        check_unsigned_provider_options(root)
        check_cli_contract(plan_path, prepared)
        check_process_tree_cleanup(root)
        check_hostile_plans(root, plan_path, plan, passport_paths)
    print(f"competition prepared-match checks: {CHECKS} passed")
    print("provider/network calls: 0")
    print("hosted automatic execution: disabled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
