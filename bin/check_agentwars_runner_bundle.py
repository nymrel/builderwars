#!/usr/bin/env python3
"""Adversarial, provider-free checks for the AgentWars runner bundle."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import warnings
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "bin"
if str(BIN) not in sys.path:
    sys.path.insert(0, str(BIN))

from build_agentwars_runner_bundle import (  # noqa: E402
    _TEST_SOURCE_POLICY,
    build_bundle,
)
from verify_agentwars_runner_bundle import (  # noqa: E402
    BUNDLE_FILENAME,
    BUNDLE_ROOT,
    BUNDLE_STATUS,
    EXECUTABLE_PROVIDER_IDS,
    EXPECTED_DEPENDENCY_LOCK_SHA256,
    EXPECTED_DEPENDENCY_POLICY,
    EXPECTED_BUNDLE_PATHS,
    RunnerBundleVerificationError,
    _validate_bundle_manifest,
    verify_artifact,
)


PASSED = 0


def check(condition: bool, name: str) -> None:
    global PASSED
    if not condition:
        raise AssertionError(name)
    PASSED += 1
    print(f"[PASS] {name}")


def expect_refusal(action, name: str, phrase: str | None = None) -> None:
    try:
        action()
    except (OSError, RunnerBundleVerificationError, ValueError) as error:
        if phrase is not None and phrase not in str(error):
            raise AssertionError(f"{name}: wrong refusal") from error
        check(True, name)
        return
    raise AssertionError(f"{name}: accepted")


def canonical(value: object) -> bytes:
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


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def tree_bytes(path: Path) -> dict[str, bytes]:
    return {
        file.relative_to(path).as_posix(): file.read_bytes()
        for file in sorted(path.rglob("*"))
        if file.is_file()
    }


def refresh_install_for_archive(artifact: Path) -> None:
    install_path = artifact / "install-manifest.json"
    install = json.loads(install_path.read_text(encoding="utf-8"))
    archive_raw = (artifact / BUNDLE_FILENAME).read_bytes()
    install["bundleBytes"] = len(archive_raw)
    install["bundleSha256"] = sha256(archive_raw)
    install.pop("artifactDigest", None)
    install["artifactDigest"] = sha256(canonical(install))
    install_path.write_bytes(canonical(install))


def append_member(artifact: Path, name: str, raw: bytes) -> None:
    with zipfile.ZipFile(artifact / BUNDLE_FILENAME, "a", compression=zipfile.ZIP_STORED) as archive:
        info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
        info.create_system = 3
        info.compress_type = zipfile.ZIP_STORED
        info.external_attr = (stat.S_IFREG | 0o644) << 16
        archive.writestr(info, raw)
    refresh_install_for_archive(artifact)


def rewrite_archive_member_mode(artifact: Path, target: str, mode: int) -> None:
    archive_path = artifact / BUNDLE_FILENAME
    replacement = archive_path.with_suffix(".replacement")
    with zipfile.ZipFile(archive_path, "r") as source, zipfile.ZipFile(
        replacement, "x", compression=zipfile.ZIP_STORED
    ) as destination:
        for old in source.infolist():
            info = zipfile.ZipInfo(old.filename, date_time=old.date_time)
            info.create_system = old.create_system
            info.compress_type = old.compress_type
            info.flag_bits = 0
            info.external_attr = old.external_attr
            if old.filename == target:
                info.external_attr = mode << 16
            destination.writestr(info, source.read(old))
    os.replace(replacement, archive_path)
    refresh_install_for_archive(artifact)


def rewrite_archive_compressed(artifact: Path) -> None:
    archive_path = artifact / BUNDLE_FILENAME
    replacement = archive_path.with_suffix(".replacement")
    with zipfile.ZipFile(archive_path, "r") as source, zipfile.ZipFile(
        replacement, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as destination:
        for old in source.infolist():
            info = zipfile.ZipInfo(old.filename, date_time=old.date_time)
            info.create_system = old.create_system
            info.compress_type = zipfile.ZIP_DEFLATED
            info.flag_bits = 0
            info.external_attr = old.external_attr
            destination.writestr(info, source.read(old))
    os.replace(replacement, archive_path)
    refresh_install_for_archive(artifact)


def safe_child_env() -> dict[str, str]:
    allowed = (
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
    environment = {
        name: os.environ[name]
        for name in allowed
        if isinstance(os.environ.get(name), str)
    }
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    environment["NO_COLOR"] = "1"
    return environment


def run_isolated(arguments: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", *arguments],
        cwd=cwd,
        env=safe_child_env(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=60,
        check=False,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="agentwars-runner-bundle-check-") as raw_work:
        work = Path(raw_work)
        first = work / "first"
        second = work / "second"
        first_receipt = build_bundle(first, _source_policy=_TEST_SOURCE_POLICY)
        second_receipt = build_bundle(second, _source_policy=_TEST_SOURCE_POLICY)

        check(first_receipt["status"] == "candidate_built_not_published", "builder reports candidate-only status")
        check(first_receipt["builtFromExactHead"] is False, "checker-only build cannot claim exact-head release custody")
        check(tree_bytes(first) == tree_bytes(second), "two working-tree test builds are byte identical")
        check(set(tree_bytes(first)) == {BUNDLE_FILENAME, "bundle-manifest.json", "install-manifest.json", "verify.py"}, "artifact has the exact four-file allowlist")

        receipt = verify_artifact(first)
        check(receipt["status"] == "pass" and receipt["artifactStatus"] == BUNDLE_STATUS, "offline verifier accepts the deterministic artifact")
        check(receipt["networkCalls"] == receipt["providerCalls"] == 0 and receipt["credentialsRead"] is False, "verification has zero network/provider/credential activity")
        check(receipt["publicationAuthorized"] is False and receipt["deploymentAuthorized"] is False, "bundle cannot authorize publication or deployment")
        check(
            receipt["dependencyHashLocked"] is True
            and receipt["dependencyLockSha256"] == EXPECTED_DEPENDENCY_LOCK_SHA256
            and receipt["dependencyWheelsBundled"] is False
            and receipt["nymrelDependencySignaturePresent"] is False,
            "artifact receipt preserves exact hash lock and unsigned/unbundled truth",
        )

        manifest = json.loads((first / "bundle-manifest.json").read_text(encoding="utf-8"))
        check(tuple(sorted(manifest["files"])) == EXPECTED_BUNDLE_PATHS, "manifest pins the complete source allowlist")
        check(
            tuple(manifest["executableProviderIds"]) == EXECUTABLE_PROVIDER_IDS
            and manifest["disabledProviderIds"] == ["claude_code"],
            "manifest retains Claude only in the disabled provider set",
        )
        check(manifest["truth"]["providerCredentialsBundled"] is False and manifest["truth"]["publicArbitraryExecutionEnabled"] is False, "manifest preserves credential and arbitrary-execution boundaries")
        check(
            manifest["dependencyPolicy"] == EXPECTED_DEPENDENCY_POLICY,
            "manifest pins the complete dependency policy",
        )
        malformed_policy = dict(manifest)
        malformed_policy["knownProviderIds"] = 1
        malformed_policy.pop("bundleDigest", None)
        malformed_policy["bundleDigest"] = sha256(canonical(malformed_policy))
        expect_refusal(
            lambda: _validate_bundle_manifest(canonical(malformed_policy)),
            "hostile provider-list type fails with a bounded refusal",
            "policy",
        )

        extract = work / "extract"
        extract.mkdir()
        with zipfile.ZipFile(first / BUNDLE_FILENAME, "r") as archive:
            archive.extractall(extract)
        bundle_root = extract / BUNDLE_ROOT
        check(bundle_root.is_dir() and not bundle_root.is_symlink(), "verified archive extracts under one fixed root")
        readme = (bundle_root / "README.md").read_text(encoding="utf-8")
        windows_entrypoint = r".\.venv\Scripts\python.exe -B bin\agentwars.py"
        posix_entrypoint = "./.venv/bin/python -B bin/agentwars.py"
        windows_passport_entrypoint = (
            r".\.venv\Scripts\python.exe -B bin\create_agent_passport.py"
        )
        posix_passport_entrypoint = "./.venv/bin/python -B bin/create_agent_passport.py"
        customer_commands = (
            "provider catalog",
            "provider connect-plan openrouter",
            "runner --help",
            "runner pair",
            "runner run-prepared-match",
        )
        check(
            "python -B verify.py --artifact ." in readme
            and all(
                f"{entrypoint} {command}" in readme
                for entrypoint in (windows_entrypoint, posix_entrypoint)
                for command in customer_commands
            ),
            "bundled README exposes exact no-bytecode verifier, Windows, and POSIX entrypoints",
        )
        check(
            all(
                f"{entrypoint} {command}" in readme
                for entrypoint in (windows_passport_entrypoint, posix_passport_entrypoint)
                for command in ("create-key", "create-version", "verify")
            ),
            "bundled README exposes exact no-bytecode Agent Passport creation and verification entrypoints",
        )
        readme_lines = tuple(line.strip() for line in readme.splitlines())
        check(
            not any(
                line.startswith(r".\.venv\Scripts\python.exe bin\agentwars.py")
                or line.startswith("./.venv/bin/python bin/agentwars.py")
                or line.startswith(
                    r".\.venv\Scripts\python.exe bin\create_agent_passport.py"
                )
                or line.startswith("./.venv/bin/python bin/create_agent_passport.py")
                or line == "python verify.py --artifact ."
                for line in readme_lines
            ),
            "bundled README contains no writable-bytecode verifier, runner, or passport invocation",
        )
        compile_result = run_isolated(["-m", "compileall", "-q", "."], bundle_root)
        check(compile_result.returncode == 0, "bundled Python compiles in an isolated interpreter")

        dependency_result = run_isolated(
            ["bin/check_agentwars_dependency_lock.py", "--root", ".", "--json"],
            bundle_root,
        )
        dependency_receipt = json.loads(dependency_result.stdout)
        check(
            dependency_result.returncode == 0
            and dependency_receipt["status"] == "pass"
            and dependency_receipt["artifactCount"] == 43
            and dependency_receipt["dependencyLockSha256"]
            == EXPECTED_DEPENDENCY_LOCK_SHA256
            and dependency_receipt["downloads"]
            == dependency_receipt["installs"]
            == dependency_receipt["networkCalls"]
            == 0,
            "bundled stdlib checker validates the exact dependency lock offline",
        )

        help_result = run_isolated(["bin/agentwars.py", "runner", "--help"], bundle_root)
        check(help_result.returncode == 0 and "prepare-match" in help_result.stdout and "submit-match" in help_result.stdout, "bundled runner exposes the complete beta command surface")
        run_help = run_isolated(["bin/agentwars.py", "runner", "run-prepared-match", "--help"], bundle_root)
        check(
            run_help.returncode == 0
            and "--openrouter-pkce-v1" in run_help.stdout
            and "--openrouter-provider-key-persists-v1" in run_help.stdout
            and "--provider-usage-v1" in run_help.stdout,
            "bundled prepared runner exposes provider-use, PKCE, and key-lifetime intents",
        )
        provider_help = run_isolated(["bin/agentwars.py", "provider", "--help"], bundle_root)
        check(provider_help.returncode == 0 and "catalog" in provider_help.stdout and "connect-plan" in provider_help.stdout, "bundled runner exposes read-only provider discovery")
        provider_catalog = run_isolated(["bin/agentwars.py", "provider", "catalog"], bundle_root)
        check(
            provider_catalog.returncode == 0
            and all(provider in provider_catalog.stdout for provider in ("chatgpt_codex", "claude_code", "opencode", "openrouter", "hermes", "custom_agent"))
            and "No account or credential was read" in provider_catalog.stdout,
            "bundled provider catalog lists every known route without probing",
        )
        openrouter_plan = run_isolated(["bin/agentwars.py", "provider", "connect-plan", "openrouter"], bundle_root)
        check(
            openrouter_plan.returncode == 0
            and "OPENROUTER_API_KEY" in openrouter_plan.stdout
            and "No login, browser, network request" in openrouter_plan.stdout,
            "bundled OpenRouter plan is actionable and read-only",
        )
        pair_help = run_isolated(["bin/agentwars.py", "runner", "pair", "--help"], bundle_root)
        check(
            pair_help.returncode == 0
            and all(provider in pair_help.stdout for provider in EXECUTABLE_PROVIDER_IDS)
            and "claude_code" not in pair_help.stdout,
            "bundled pairing help exposes only executable provider ids",
        )
        passport_help = run_isolated(["bin/create_agent_passport.py", "--help"], bundle_root)
        check(
            passport_help.returncode == 0
            and all(command in passport_help.stdout for command in ("create-key", "create-version", "verify")),
            "bundled Agent Passport CLI exposes the complete offline identity surface",
        )
        passport_work = work / "passport-proof"
        passport_work.mkdir()
        key_result = run_isolated(
            [
                "bin/create_agent_passport.py",
                "create-key",
                "--out-dir",
                str(passport_work),
                "--name",
                "bundle-test",
                "--insecure-unencrypted-key",
            ],
            bundle_root,
        )
        key_path = passport_work / "bundle-test.unsafe-test-only.key.pem"
        check(
            key_result.returncode == 0
            and key_path.is_file()
            and "must never leave this machine or be committed" in key_result.stdout,
            "bundled Agent Passport CLI creates only an explicitly unsafe ephemeral test key in this check",
        )
        passport_path = passport_work / "bundle-test.agent.json"
        version_result = run_isolated(
            [
                "bin/create_agent_passport.py",
                "create-version",
                "--key",
                str(key_path),
                "--key-is-unencrypted",
                "--display-name",
                "Bundle Test",
                "--version-label",
                "v1",
                "--harness-file",
                "entrants/fantasy_model_harness.py",
                "--claimed-model",
                "test/provider-model",
                "--out",
                str(passport_path),
            ],
            bundle_root,
        )
        check(
            version_result.returncode == 0
            and passport_path.is_file()
            and "agentId" in version_result.stdout
            and "versionId" in version_result.stdout,
            "bundled Agent Passport CLI signs one ephemeral harness-bound version outside the extracted bundle",
        )
        passport_verify = run_isolated(
            ["bin/create_agent_passport.py", "verify", str(passport_path)],
            bundle_root,
        )
        check(
            passport_verify.returncode == 0
            and "signature : PASS" in passport_verify.stdout
            and "proofScope: model/runtime/person/execution attestation all false" in passport_verify.stdout,
            "bundled Agent Passport CLI verifies the signed version without elevating identity or execution truth",
        )
        public_fixture = ROOT / "matches" / "agentwars-fantasy" / "fantasy_redraft" / "9600-0" / "8d161a470a12b0c3.jsonl"
        replay_result = run_isolated([str(bundle_root / "verify.py"), str(public_fixture), "--json"], work)
        replay_receipt = json.loads(replay_result.stdout)
        check(replay_result.returncode == 0 and replay_receipt["effective_verdict"] == "PASS" and replay_receipt["verifier_snapshot_match"] is True, "bundled transcript verifier replays a current public fixture")
        empty_state = work / "empty-state"
        list_result = run_isolated(["bin/agentwars.py", "runner", "list", "--state-dir", str(empty_state)], bundle_root)
        check(list_result.returncode == 0 and "No local AgentWars runner profiles" in list_result.stdout, "bundled runner reads an explicit empty local state without network")
        self_verify = run_isolated([str(first / "verify.py"), "--artifact", str(first)], work)
        self_receipt = json.loads(self_verify.stdout)
        check(self_verify.returncode == 0 and self_receipt["verifierSelfBound"] is True, "artifact verifier is self-bound when run from the artifact")

        unexpected = work / "unexpected"
        shutil.copytree(first, unexpected)
        (unexpected / "extra.txt").write_text("unexpected", encoding="utf-8")
        expect_refusal(lambda: verify_artifact(unexpected), "unexpected artifact file is refused", "allowlist")

        changed_manifest = work / "changed-manifest"
        shutil.copytree(first, changed_manifest)
        with (changed_manifest / "bundle-manifest.json").open("ab") as handle:
            handle.write(b" ")
        expect_refusal(lambda: verify_artifact(changed_manifest), "changed external manifest is refused", "digest")

        changed_archive = work / "changed-archive"
        shutil.copytree(first, changed_archive)
        archive_bytes = bytearray((changed_archive / BUNDLE_FILENAME).read_bytes())
        archive_bytes[len(archive_bytes) // 2] ^= 1
        (changed_archive / BUNDLE_FILENAME).write_bytes(archive_bytes)
        expect_refusal(lambda: verify_artifact(changed_archive), "changed ZIP byte is refused", "digest")

        traversal = work / "traversal"
        shutil.copytree(first, traversal)
        append_member(traversal, f"{BUNDLE_ROOT}/../escape.txt", b"escape")
        expect_refusal(lambda: verify_artifact(traversal), "ZIP traversal member is refused", "allowlist")

        duplicate = work / "duplicate"
        shutil.copytree(first, duplicate)
        with zipfile.ZipFile(duplicate / BUNDLE_FILENAME, "r") as archive:
            readme = archive.read(f"{BUNDLE_ROOT}/README.md")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            append_member(duplicate, f"{BUNDLE_ROOT}/README.md", readme)
        expect_refusal(lambda: verify_artifact(duplicate), "duplicate ZIP member is refused", "allowlist")

        symlink = work / "symlink"
        shutil.copytree(first, symlink)
        rewrite_archive_member_mode(
            symlink,
            f"{BUNDLE_ROOT}/README.md",
            stat.S_IFLNK | 0o777,
        )
        expect_refusal(lambda: verify_artifact(symlink), "ZIP symlink member is refused", "non-regular")

        compressed = work / "compressed"
        shutil.copytree(first, compressed)
        rewrite_archive_compressed(compressed)
        expect_refusal(lambda: verify_artifact(compressed), "compressed ZIP member is refused", "deterministic")

        expect_refusal(
            lambda: build_bundle(first, _source_policy=_TEST_SOURCE_POLICY),
            "builder refuses overwrite",
            "already exists",
        )
        check(not any(path.name.startswith(".agentwars-runner-bundle-") for path in work.iterdir()), "failed builds leave no staging directory")

        missing_output = work / "missing-ack"
        missing = subprocess.run(
            [sys.executable, str(ROOT / "bin" / "build_agentwars_runner_bundle.py"), "--out", str(missing_output)],
            cwd=ROOT,
            env=safe_child_env(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="strict",
            timeout=30,
            check=False,
        )
        check(missing.returncode == 2 and not missing_output.exists() and "four candidate-only acknowledgements" in missing.stdout, "release CLI refuses missing acknowledgements before output")

    print(f"AgentWars runner bundle contracts: PASS ({PASSED} checks)")
    print("deterministic candidate / offline verify / no provider / no credentials / no publication")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
