#!/usr/bin/env python3
"""Offline verifier for one deterministic AgentWars customer-runner bundle.

The verifier is stdlib-only and performs no network, provider, credential,
account, install, extraction, or execution action.  It validates the complete
artifact file set, canonical manifests, deterministic ZIP metadata, and every
bundled byte before reporting a candidate-only receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


SCHEMA_VERSION = "agentwars.runner_bundle.v1"
INSTALL_SCHEMA_VERSION = "agentwars.runner_bundle_install.v1"
BUNDLE_STATUS = "candidate_not_published"
BUNDLE_FILENAME = "agentwars-runner-v1.zip"
BUNDLE_ROOT = "agentwars-runner-v1"
FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_ARCHIVE_BYTES = 16 * 1024 * 1024
MAX_MEMBER_BYTES = 2 * 1024 * 1024
MAX_TOTAL_MEMBER_BYTES = 12 * 1024 * 1024
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")

KNOWN_PROVIDER_IDS = (
    "chatgpt_codex",
    "claude_code",
    "opencode",
    "openrouter",
    "hermes",
    "custom_agent",
)
EXECUTABLE_PROVIDER_IDS = (
    "chatgpt_codex",
    "opencode",
    "openrouter",
    "hermes",
    "custom_agent",
)
DISABLED_PROVIDER_IDS = ("claude_code",)
PROVIDER_POLICY_EVIDENCE_DATE = "2026-08-27"
DEPENDENCY_POLICY_EVIDENCE_DATE = "2026-08-26"
EXPECTED_DEPENDENCY_LOCK_SHA256 = (
    "47eadaacd1c4e869c0481aac6588d627cb9451b046236a0e4cdc059ab53162d2"
)
EXPECTED_REQUIREMENTS_LOCK_SHA256 = (
    "635fbdb4b20cb3d6a00456cc4882bdb8e23ba0a2da2ca6ed6db170dd212697ce"
)
EXPECTED_REQUIREMENTS_WRAPPER_SHA256 = (
    "b824c364f028ffdb511122a12520d2e8dbaf2e095fec66b68f952978376aa019"
)
EXPECTED_DEPENDENCY_POLICY = {
    "crossPlatformRuntimeAttested": False,
    "defaultInstallRequiresNetwork": True,
    "evidenceDate": DEPENDENCY_POLICY_EVIDENCE_DATE,
    "hashLocked": True,
    "lockFile": "dependency-lock.json",
    "lockSha256": EXPECTED_DEPENDENCY_LOCK_SHA256,
    "nymrelSignaturePresent": False,
    "onlyBinary": True,
    "pythonMarkersEnforced": True,
    "pythonImplementation": "CPython",
    "pythonRequires": ">=3.10,<3.15",
    "requirementsFile": "requirements.lock",
    "requirementsSha256": EXPECTED_REQUIREMENTS_LOCK_SHA256,
    "sourceBuildsAllowed": False,
    "wheelsBundled": False,
}

EXPECTED_BUNDLE_PATHS = (
    "LICENSE",
    "README.md",
    "START_HERE.md",
    "agent_identity/__init__.py",
    "agent_identity/keys.py",
    "agent_identity/lineage.py",
    "agent_identity/passport.py",
    "arena/__init__.py",
    "arena/admission.py",
    "arena/canonical.py",
    "arena/games/__init__.py",
    "arena/games/fantasy_core.py",
    "arena/games/fantasy_dynasty.py",
    "arena/games/fantasy_qb_surge.py",
    "arena/games/fantasy_redraft.py",
    "arena/games/nim.py",
    "arena/games/ten_fronts.py",
    "arena/integrity.py",
    "arena/match.py",
    "arena/passport.py",
    "arena/process_tree.py",
    "arena/reference_sources.py",
    "arena/replay.py",
    "arena/sandbox.py",
    "arena/scoring.py",
    "arena/transcript.py",
    "bin/agentwars",
    "bin/agentwars.cmd",
    "bin/agentwars.py",
    "bin/check_agentwars_dependency_lock.py",
    "bin/create_agent_passport.py",
    "bin/qualify_agentwars_starter.py",
    "bin/run_agentwars_cross_provider_match.py",
    "bin/run_agentwars_league.py",
    "competitions/__init__.py",
    "competitions/evidence_job.py",
    "competitions/matrix.py",
    "competitions/prepared_match.py",
    "competitions/source_match.py",
    "dependency-lock.json",
    "entrants/backends.py",
    "entrants/fantasy_model_harness.py",
    "entrants/parsing.py",
    "provider_hub/__init__.py",
    "provider_hub/catalog.py",
    "provider_hub/ids.py",
    "provider_hub/local_runner.py",
    "provider_hub/match_worker.py",
    "provider_hub/pkce.py",
    "provider_hub/runner_state.py",
    "provider_hub/schemas.py",
    "provider_hub/secrets.py",
    "provider_hub/signing.py",
    "publishing/__init__.py",
    "publishing/projection.py",
    "requirements.lock",
    "requirements.txt",
    "verify.py",
    "verify_bundle.py",
)

EXECUTABLE_BUNDLE_PATHS = frozenset(
    {
        "bin/agentwars",
        "bin/agentwars.py",
        "bin/check_agentwars_dependency_lock.py",
        "bin/create_agent_passport.py",
        "bin/qualify_agentwars_starter.py",
        "bin/run_agentwars_cross_provider_match.py",
        "bin/run_agentwars_league.py",
        "verify.py",
        "verify_bundle.py",
    }
)

EXPECTED_TRUTH = {
    "billingRouteAttested": False,
    "customerLocalExecutionRequiresExplicitConsent": True,
    "deploymentAuthorized": False,
    "harnessExecutionAttested": False,
    "hostedExecutionEnabled": False,
    "matchExecutionAttested": False,
    "modelAttested": False,
    "personAttested": False,
    "planEntitlementAttested": False,
    "providerAccountAttested": False,
    "providerCredentialsBundled": False,
    "providerCredentialsReadByBuilderOrVerifier": False,
    "publicArbitraryExecutionEnabled": False,
    "publicationAuthorized": False,
    "runtimeAttested": False,
}

_BUNDLE_KEYS = frozenset(
    {
        "schemaVersion",
        "bundleStatus",
        "sourceCommit",
        "builtFromExactHead",
        "pythonRequires",
        "credentialCustody",
        "dependencyPolicy",
        "networkExecution",
        "providerPolicyEvidenceDate",
        "knownProviderIds",
        "executableProviderIds",
        "disabledProviderIds",
        "truth",
        "files",
        "bundleDigest",
    }
)
_INSTALL_KEYS = frozenset(
    {
        "schemaVersion",
        "artifactStatus",
        "sourceCommit",
        "bundleFile",
        "bundleSha256",
        "bundleBytes",
        "bundleManifestFile",
        "bundleManifestSha256",
        "dependencyHashLocked",
        "dependencyInstallRequiresNetwork",
        "dependencyLockSha256",
        "dependencyWheelsBundled",
        "nymrelDependencySignaturePresent",
        "requirementsLockSha256",
        "verifierFile",
        "verifierSha256",
        "publicationAuthorized",
        "deploymentAuthorized",
        "artifactDigest",
    }
)
_FILE_KEYS = frozenset({"bytes", "mode", "sha256"})


class RunnerBundleVerificationError(ValueError):
    """Bounded bundle refusal that contains no source or credential bytes."""


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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


def _without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RunnerBundleVerificationError("manifest contains a duplicate key")
        result[key] = value
    return result


def _reject_number(_value: str) -> Any:
    raise RunnerBundleVerificationError("manifest contains a non-integer number")


def _strict_json(raw: bytes, label: str) -> dict[str, Any]:
    if not raw or len(raw) > MAX_JSON_BYTES or raw.startswith(b"\xef\xbb\xbf"):
        raise RunnerBundleVerificationError(f"{label} has invalid bytes")
    try:
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_without_duplicates,
            parse_float=_reject_number,
            parse_constant=_reject_number,
        )
    except RunnerBundleVerificationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RunnerBundleVerificationError(f"{label} is not strict JSON") from error
    if not isinstance(value, dict) or _canonical_bytes(value) != raw:
        raise RunnerBundleVerificationError(f"{label} is not canonical JSON")
    return value


def _expect_exact_keys(value: dict[str, Any], expected: frozenset[str], label: str) -> None:
    if frozenset(value) != expected:
        raise RunnerBundleVerificationError(f"{label} has an unexpected schema")


def _is_reparse(path: Path) -> bool:
    try:
        attrs = path.lstat().st_file_attributes
    except AttributeError:
        return False
    return bool(attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _assert_direct_ancestors(path: Path) -> None:
    current = path.absolute()
    while True:
        if current.exists() and (current.is_symlink() or _is_reparse(current)):
            raise RunnerBundleVerificationError("artifact path contains an indirect ancestor")
        parent = current.parent
        if parent == current:
            break
        current = parent


def _read_regular(path: Path, maximum: int, label: str) -> bytes:
    try:
        before = path.lstat()
    except OSError as error:
        raise RunnerBundleVerificationError(f"{label} is unavailable") from error
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or path.is_symlink()
        or _is_reparse(path)
    ):
        raise RunnerBundleVerificationError(f"{label} is not a direct regular file")
    if before.st_size < 0 or before.st_size > maximum:
        raise RunnerBundleVerificationError(f"{label} is oversized")
    try:
        raw = path.read_bytes()
        after = path.lstat()
    except OSError as error:
        raise RunnerBundleVerificationError(f"{label} could not be read") from error
    if (
        before.st_dev != after.st_dev
        or before.st_ino != after.st_ino
        or before.st_size != after.st_size
        or len(raw) != after.st_size
    ):
        raise RunnerBundleVerificationError(f"{label} changed during verification")
    return raw


def _valid_bundle_path(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        return False
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and path.as_posix() == value
        and all(part not in {"", ".", ".."} for part in path.parts)
    )


def _validate_file_manifest(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict) or tuple(sorted(value)) != EXPECTED_BUNDLE_PATHS:
        raise RunnerBundleVerificationError("bundle file allowlist is invalid")
    result: dict[str, dict[str, Any]] = {}
    for path, record in value.items():
        if not _valid_bundle_path(path) or not isinstance(record, dict):
            raise RunnerBundleVerificationError("bundle file record is invalid")
        _expect_exact_keys(record, _FILE_KEYS, "bundle file record")
        expected_mode = "0755" if path in EXECUTABLE_BUNDLE_PATHS else "0644"
        if (
            not isinstance(record["bytes"], int)
            or isinstance(record["bytes"], bool)
            or record["bytes"] < 0
            or record["bytes"] > MAX_MEMBER_BYTES
            or record["mode"] != expected_mode
            or not isinstance(record["sha256"], str)
            or HEX64_RE.fullmatch(record["sha256"]) is None
        ):
            raise RunnerBundleVerificationError("bundle file record is invalid")
        result[path] = record
    if sum(record["bytes"] for record in result.values()) > MAX_TOTAL_MEMBER_BYTES:
        raise RunnerBundleVerificationError("bundle expands beyond its total byte limit")
    return result


def _validate_bundle_manifest(raw: bytes) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    manifest = _strict_json(raw, "bundle manifest")
    _expect_exact_keys(manifest, _BUNDLE_KEYS, "bundle manifest")
    if (
        manifest["schemaVersion"] != SCHEMA_VERSION
        or manifest["bundleStatus"] != BUNDLE_STATUS
        or not isinstance(manifest["sourceCommit"], str)
        or HEX40_RE.fullmatch(manifest["sourceCommit"]) is None
        or not isinstance(manifest["builtFromExactHead"], bool)
        or manifest["pythonRequires"] != ">=3.10,<3.15"
        or manifest["credentialCustody"] != "customer_only"
        or manifest["dependencyPolicy"] != EXPECTED_DEPENDENCY_POLICY
        or manifest["networkExecution"] != "customer_invoked_only"
        or manifest["providerPolicyEvidenceDate"] != PROVIDER_POLICY_EVIDENCE_DATE
        or not isinstance(manifest["knownProviderIds"], list)
        or tuple(manifest["knownProviderIds"]) != KNOWN_PROVIDER_IDS
        or not isinstance(manifest["executableProviderIds"], list)
        or tuple(manifest["executableProviderIds"]) != EXECUTABLE_PROVIDER_IDS
        or not isinstance(manifest["disabledProviderIds"], list)
        or tuple(manifest["disabledProviderIds"]) != DISABLED_PROVIDER_IDS
        or manifest["truth"] != EXPECTED_TRUTH
        or not isinstance(manifest["bundleDigest"], str)
        or HEX64_RE.fullmatch(manifest["bundleDigest"]) is None
    ):
        raise RunnerBundleVerificationError("bundle manifest policy is invalid")
    core = dict(manifest)
    claimed_digest = core.pop("bundleDigest")
    if _sha256(_canonical_bytes(core)) != claimed_digest:
        raise RunnerBundleVerificationError("bundle manifest digest is invalid")
    files = _validate_file_manifest(manifest["files"])
    pinned_files = {
        "dependency-lock.json": EXPECTED_DEPENDENCY_LOCK_SHA256,
        "requirements.lock": EXPECTED_REQUIREMENTS_LOCK_SHA256,
        "requirements.txt": EXPECTED_REQUIREMENTS_WRAPPER_SHA256,
    }
    if any(files[path]["sha256"] != digest for path, digest in pinned_files.items()):
        raise RunnerBundleVerificationError("bundle dependency lock digest is invalid")
    return manifest, files


def _zip_mode(info: zipfile.ZipInfo) -> int:
    raw_mode = (info.external_attr >> 16) & 0xFFFF
    if stat.S_IFMT(raw_mode) != stat.S_IFREG:
        raise RunnerBundleVerificationError("bundle contains a non-regular ZIP member")
    return stat.S_IMODE(raw_mode)


def _validate_archive(
    archive_raw: bytes,
    manifest_raw: bytes,
    files: dict[str, dict[str, Any]],
) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(archive_raw), "r") as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            expected_names = [
                f"{BUNDLE_ROOT}/{path}" for path in EXPECTED_BUNDLE_PATHS
            ] + [f"{BUNDLE_ROOT}/bundle-manifest.json"]
            expected_names.sort()
            if len(names) != len(set(names)) or names != expected_names:
                raise RunnerBundleVerificationError("bundle ZIP member allowlist is invalid")
            total = 0
            for info in infos:
                if (
                    info.date_time != FIXED_ZIP_TIME
                    or info.compress_type != zipfile.ZIP_STORED
                    or info.flag_bits != 0
                    or info.create_system != 3
                    or info.file_size < 0
                    or info.file_size > MAX_MEMBER_BYTES
                    or info.compress_size != info.file_size
                ):
                    raise RunnerBundleVerificationError("bundle ZIP metadata is not deterministic")
                total += info.file_size
                relative = info.filename.removeprefix(f"{BUNDLE_ROOT}/")
                expected_mode = 0o644
                if relative in EXECUTABLE_BUNDLE_PATHS:
                    expected_mode = 0o755
                if _zip_mode(info) != expected_mode:
                    raise RunnerBundleVerificationError("bundle ZIP mode is invalid")
                raw = archive.read(info)
                if len(raw) != info.file_size:
                    raise RunnerBundleVerificationError("bundle ZIP member changed during read")
                if relative == "bundle-manifest.json":
                    if raw != manifest_raw:
                        raise RunnerBundleVerificationError("internal bundle manifest differs")
                    continue
                record = files.get(relative)
                if (
                    record is None
                    or len(raw) != record["bytes"]
                    or _sha256(raw) != record["sha256"]
                ):
                    raise RunnerBundleVerificationError("bundle ZIP member digest is invalid")
            if total > MAX_TOTAL_MEMBER_BYTES + len(manifest_raw):
                raise RunnerBundleVerificationError("bundle ZIP expands beyond its limit")
            if archive.testzip() is not None:
                raise RunnerBundleVerificationError("bundle ZIP integrity check failed")
    except RunnerBundleVerificationError:
        raise
    except (OSError, zipfile.BadZipFile, RuntimeError) as error:
        raise RunnerBundleVerificationError("bundle ZIP is invalid") from error


def verify_artifact(artifact_path: str | os.PathLike[str]) -> dict[str, Any]:
    candidate = Path(artifact_path).absolute()
    if os.name == "nt" and str(candidate).startswith("\\\\"):
        raise RunnerBundleVerificationError("artifact must be on a direct local path")
    _assert_direct_ancestors(candidate)
    artifact = candidate.resolve(strict=True)
    if not artifact.is_dir() or artifact.is_symlink() or _is_reparse(artifact):
        raise RunnerBundleVerificationError("artifact must be a direct local directory")
    expected_names = {
        BUNDLE_FILENAME,
        "bundle-manifest.json",
        "install-manifest.json",
        "verify.py",
    }
    try:
        actual_names = {entry.name for entry in artifact.iterdir()}
    except OSError as error:
        raise RunnerBundleVerificationError("artifact directory is unreadable") from error
    if actual_names != expected_names:
        raise RunnerBundleVerificationError("artifact file allowlist is invalid")

    install_raw = _read_regular(
        artifact / "install-manifest.json", MAX_JSON_BYTES, "install manifest"
    )
    install = _strict_json(install_raw, "install manifest")
    _expect_exact_keys(install, _INSTALL_KEYS, "install manifest")
    if (
        install["schemaVersion"] != INSTALL_SCHEMA_VERSION
        or install["artifactStatus"] != BUNDLE_STATUS
        or install["bundleFile"] != BUNDLE_FILENAME
        or install["bundleManifestFile"] != "bundle-manifest.json"
        or install["verifierFile"] != "verify.py"
        or install["dependencyHashLocked"] is not True
        or install["dependencyInstallRequiresNetwork"] is not True
        or install["dependencyWheelsBundled"] is not False
        or install["nymrelDependencySignaturePresent"] is not False
        or install["dependencyLockSha256"] != EXPECTED_DEPENDENCY_LOCK_SHA256
        or install["requirementsLockSha256"] != EXPECTED_REQUIREMENTS_LOCK_SHA256
        or install["publicationAuthorized"] is not False
        or install["deploymentAuthorized"] is not False
        or not isinstance(install["sourceCommit"], str)
        or HEX40_RE.fullmatch(install["sourceCommit"]) is None
        or not isinstance(install["bundleBytes"], int)
        or isinstance(install["bundleBytes"], bool)
        or install["bundleBytes"] < 1
        or install["bundleBytes"] > MAX_ARCHIVE_BYTES
        or any(
            not isinstance(install[key], str) or HEX64_RE.fullmatch(install[key]) is None
            for key in (
                "bundleSha256",
                "bundleManifestSha256",
                "verifierSha256",
                "artifactDigest",
            )
        )
    ):
        raise RunnerBundleVerificationError("install manifest policy is invalid")
    install_core = dict(install)
    artifact_digest = install_core.pop("artifactDigest")
    if _sha256(_canonical_bytes(install_core)) != artifact_digest:
        raise RunnerBundleVerificationError("install manifest digest is invalid")

    bundle_raw = _read_regular(
        artifact / "bundle-manifest.json", MAX_JSON_BYTES, "bundle manifest"
    )
    verifier_raw = _read_regular(
        artifact / "verify.py", MAX_MEMBER_BYTES, "bundle verifier"
    )
    archive_raw = _read_regular(
        artifact / BUNDLE_FILENAME, MAX_ARCHIVE_BYTES, "runner bundle"
    )
    if (
        len(archive_raw) != install["bundleBytes"]
        or _sha256(archive_raw) != install["bundleSha256"]
        or _sha256(bundle_raw) != install["bundleManifestSha256"]
        or _sha256(verifier_raw) != install["verifierSha256"]
    ):
        raise RunnerBundleVerificationError("artifact file digest is invalid")

    manifest, files = _validate_bundle_manifest(bundle_raw)
    if manifest["sourceCommit"] != install["sourceCommit"]:
        raise RunnerBundleVerificationError("artifact source commit is inconsistent")
    _validate_archive(archive_raw, bundle_raw, files)

    current = Path(__file__).resolve()
    self_bound = current == (artifact / "verify.py").resolve()
    if self_bound and _sha256(_read_regular(current, MAX_MEMBER_BYTES, "running verifier")) != install["verifierSha256"]:
        raise RunnerBundleVerificationError("running verifier is not self-bound")

    return {
        "schemaVersion": 1,
        "status": "pass",
        "artifactStatus": BUNDLE_STATUS,
        "sourceCommit": manifest["sourceCommit"],
        "builtFromExactHead": manifest["builtFromExactHead"],
        "bundleDigest": manifest["bundleDigest"],
        "bundleSha256": install["bundleSha256"],
        "fileCount": len(files),
        "providerPolicyEvidenceDate": PROVIDER_POLICY_EVIDENCE_DATE,
        "dependencyPolicyEvidenceDate": DEPENDENCY_POLICY_EVIDENCE_DATE,
        "dependencyLockSha256": EXPECTED_DEPENDENCY_LOCK_SHA256,
        "requirementsLockSha256": EXPECTED_REQUIREMENTS_LOCK_SHA256,
        "dependencyHashLocked": True,
        "dependencyInstallRequiresNetwork": True,
        "dependencyWheelsBundled": False,
        "nymrelDependencySignaturePresent": False,
        "disabledProviderIds": list(DISABLED_PROVIDER_IDS),
        "networkCalls": 0,
        "providerCalls": 0,
        "credentialsRead": False,
        "filesExtracted": 0,
        "processesStarted": 0,
        "publicationAuthorized": False,
        "deploymentAuthorized": False,
        "verifierSelfBound": self_bound,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True)
    args = parser.parse_args(argv)
    try:
        receipt = verify_artifact(args.artifact)
    except (OSError, RunnerBundleVerificationError) as error:
        print(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "status": "refused",
                    "error": str(error),
                    "networkCalls": 0,
                    "providerCalls": 0,
                    "credentialsRead": False,
                    "filesExtracted": 0,
                    "processesStarted": 0,
                    "publicationAuthorized": False,
                    "deploymentAuthorized": False,
                },
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
