#!/usr/bin/env python3
"""Build one deterministic, candidate-only AgentWars local-runner artifact.

The release CLI reads the exact Git HEAD blobs for a closed source allowlist.
It never reads provider credentials, invokes a provider, installs software,
publishes, deploys, or overwrites an output.  The resulting ZIP is stored
without compression so its bytes are deterministic across zlib versions.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "bin"
if str(BIN) not in sys.path:
    sys.path.insert(0, str(BIN))

from verify_agentwars_runner_bundle import (  # noqa: E402
    BUNDLE_FILENAME,
    BUNDLE_ROOT,
    BUNDLE_STATUS,
    DISABLED_PROVIDER_IDS,
    EXECUTABLE_BUNDLE_PATHS,
    EXECUTABLE_PROVIDER_IDS,
    EXPECTED_BUNDLE_PATHS,
    EXPECTED_TRUTH,
    FIXED_ZIP_TIME,
    INSTALL_SCHEMA_VERSION,
    KNOWN_PROVIDER_IDS,
    PROVIDER_POLICY_EVIDENCE_DATE,
    SCHEMA_VERSION,
    verify_artifact,
)


SOURCE_PATH_BY_BUNDLE_PATH = {
    path: path
    for path in EXPECTED_BUNDLE_PATHS
    if path not in {"README.md", "verify_bundle.py"}
}
SOURCE_PATH_BY_BUNDLE_PATH.update(
    {
        "README.md": "docs/AGENTWARS_RUNNER_BUNDLE.md",
        "verify_bundle.py": "bin/verify_agentwars_runner_bundle.py",
    }
)

_TEST_SOURCE_POLICY = object()


class RunnerBundleBuildError(ValueError):
    """Bounded packaging refusal with no source or credential reflection."""


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


def _git(*args: str) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            ["git", "-C", str(ROOT), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as error:
        raise RunnerBundleBuildError("Git is unavailable") from error


def _exact_head_source() -> tuple[str, dict[str, bytes]]:
    top = _git("rev-parse", "--show-toplevel")
    if top.returncode != 0:
        raise RunnerBundleBuildError("runner bundle source is not a Git checkout")
    try:
        git_root = Path(top.stdout.decode("utf-8", errors="strict").strip()).resolve()
    except UnicodeDecodeError as error:
        raise RunnerBundleBuildError("Git root is not valid UTF-8") from error
    if git_root != ROOT.resolve():
        raise RunnerBundleBuildError("runner bundle source root is ambiguous")

    head_result = _git("rev-parse", "HEAD")
    if head_result.returncode != 0:
        raise RunnerBundleBuildError("runner bundle source commit is unavailable")
    head = head_result.stdout.decode("ascii", errors="strict").strip()
    if len(head) != 40 or any(char not in "0123456789abcdef" for char in head):
        raise RunnerBundleBuildError("runner bundle source commit is invalid")

    source_paths = tuple(sorted(set(SOURCE_PATH_BY_BUNDLE_PATH.values())))
    _working_tree_source()
    for diff_args in (
        ("diff", "--quiet", "HEAD", "--", *source_paths),
        ("diff", "--cached", "--quiet", "HEAD", "--", *source_paths),
    ):
        result = _git(*diff_args)
        if result.returncode == 1:
            raise RunnerBundleBuildError(
                "runner bundle source allowlist differs from exact Git HEAD"
            )
        if result.returncode != 0:
            raise RunnerBundleBuildError("runner bundle Git comparison failed")

    blobs: dict[str, bytes] = {}
    for destination, source in sorted(SOURCE_PATH_BY_BUNDLE_PATH.items()):
        result = _git("show", f"HEAD:{source}")
        if result.returncode != 0:
            raise RunnerBundleBuildError("runner bundle source allowlist is incomplete")
        blobs[destination] = result.stdout
    return head, blobs


def _is_reparse(path: Path) -> bool:
    try:
        attrs = path.lstat().st_file_attributes
    except AttributeError:
        return False
    return bool(attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _working_tree_source() -> dict[str, bytes]:
    blobs: dict[str, bytes] = {}
    for destination, source in sorted(SOURCE_PATH_BY_BUNDLE_PATH.items()):
        path = ROOT / source
        try:
            before = path.lstat()
        except OSError as error:
            raise RunnerBundleBuildError("runner bundle test source is unavailable") from error
        if not stat.S_ISREG(before.st_mode) or path.is_symlink() or _is_reparse(path):
            raise RunnerBundleBuildError("runner bundle test source is not a regular file")
        try:
            raw = path.read_bytes()
            after = path.lstat()
        except OSError as error:
            raise RunnerBundleBuildError("runner bundle test source could not be read") from error
        if (
            before.st_dev != after.st_dev
            or before.st_ino != after.st_ino
            or before.st_size != after.st_size
            or len(raw) != after.st_size
        ):
            raise RunnerBundleBuildError("runner bundle test source changed during read")
        blobs[destination] = raw
    return blobs


def _validate_source_map(blobs: dict[str, bytes]) -> None:
    if tuple(sorted(SOURCE_PATH_BY_BUNDLE_PATH)) != EXPECTED_BUNDLE_PATHS:
        raise RunnerBundleBuildError("runner bundle source map disagrees with verifier")
    if tuple(sorted(blobs)) != EXPECTED_BUNDLE_PATHS:
        raise RunnerBundleBuildError("runner bundle source bytes are incomplete")
    known, executable, disabled, evidence_date = _catalog_policy(
        blobs["provider_hub/catalog.py"]
    )
    if (
        known != KNOWN_PROVIDER_IDS
        or executable != EXECUTABLE_PROVIDER_IDS
        or disabled != DISABLED_PROVIDER_IDS
        or evidence_date != PROVIDER_POLICY_EVIDENCE_DATE
    ):
        raise RunnerBundleBuildError("runner bundle provider policy drifted")


def _catalog_policy(raw: bytes) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], str]:
    """Read the exact catalog policy as data without importing customer code."""
    try:
        tree = ast.parse(raw.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, SyntaxError) as error:
        raise RunnerBundleBuildError("runner bundle provider catalog is invalid") from error
    assignments: dict[str, ast.AST] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            assignments[node.targets[0].id] = node.value
    try:
        known_value = ast.literal_eval(assignments["PROVIDER_IDS"])
        evidence_value = ast.literal_eval(assignments["PROVIDER_POLICY_EVIDENCE_DATE"])
        catalog_node = assignments["_CATALOG"]
    except (KeyError, ValueError, TypeError, SyntaxError) as error:
        raise RunnerBundleBuildError("runner bundle provider catalog policy is missing") from error
    if (
        not isinstance(known_value, tuple)
        or not all(isinstance(value, str) for value in known_value)
        or not isinstance(evidence_value, str)
        or not isinstance(catalog_node, ast.Dict)
    ):
        raise RunnerBundleBuildError("runner bundle provider catalog policy is invalid")
    local_execution: dict[str, bool] = {}
    for provider_key, entry_node in zip(catalog_node.keys, catalog_node.values, strict=True):
        try:
            provider_id = ast.literal_eval(provider_key)
        except (ValueError, TypeError, SyntaxError) as error:
            raise RunnerBundleBuildError("runner bundle provider catalog id is invalid") from error
        if not isinstance(provider_id, str) or not isinstance(entry_node, ast.Dict):
            raise RunnerBundleBuildError("runner bundle provider catalog entry is invalid")
        entry: dict[str, ast.AST] = {}
        for key_node, value_node in zip(entry_node.keys, entry_node.values, strict=True):
            try:
                key = ast.literal_eval(key_node)
            except (ValueError, TypeError, SyntaxError) as error:
                raise RunnerBundleBuildError("runner bundle provider field is invalid") from error
            if isinstance(key, str):
                entry[key] = value_node
        try:
            enabled = ast.literal_eval(entry["local_execution"])
        except (KeyError, ValueError, TypeError, SyntaxError) as error:
            raise RunnerBundleBuildError("runner bundle provider availability is missing") from error
        if not isinstance(enabled, bool):
            raise RunnerBundleBuildError("runner bundle provider availability is invalid")
        local_execution[provider_id] = enabled
    known = tuple(known_value)
    if tuple(local_execution) != known:
        raise RunnerBundleBuildError("runner bundle provider catalog order is inconsistent")
    executable = tuple(provider for provider in known if local_execution[provider])
    disabled = tuple(provider for provider in known if not local_execution[provider])
    return known, executable, disabled, evidence_value


def _assert_output_target(destination: Path) -> Path:
    if os.name == "nt" and str(destination).startswith("\\\\"):
        raise RunnerBundleBuildError("runner bundle output must be on a direct local path")
    if destination.exists() or destination.is_symlink():
        raise RunnerBundleBuildError("runner bundle output already exists")
    parent = destination.parent.resolve(strict=True)
    current = destination.parent.absolute()
    while True:
        if current.exists() and (current.is_symlink() or _is_reparse(current)):
            raise RunnerBundleBuildError("runner bundle output has an indirect ancestor")
        ancestor = current.parent
        if ancestor == current:
            break
        current = ancestor
    if not parent.is_dir() or parent.is_symlink() or _is_reparse(parent):
        raise RunnerBundleBuildError("runner bundle output parent is not a direct directory")
    if destination.parent.resolve(strict=True) != parent:
        raise RunnerBundleBuildError("runner bundle output parent changed")
    return parent


def _write_new(path: Path, raw: bytes, mode: int = 0o644) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, mode)
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise


def _file_manifest(blobs: dict[str, bytes]) -> dict[str, dict[str, Any]]:
    return {
        path: {
            "bytes": len(blobs[path]),
            "mode": "0755" if path in EXECUTABLE_BUNDLE_PATHS else "0644",
            "sha256": _sha256(blobs[path]),
        }
        for path in sorted(blobs)
    }


def _bundle_manifest(
    source_commit: str,
    built_from_exact_head: bool,
    blobs: dict[str, bytes],
) -> bytes:
    core = {
        "schemaVersion": SCHEMA_VERSION,
        "bundleStatus": BUNDLE_STATUS,
        "sourceCommit": source_commit,
        "builtFromExactHead": built_from_exact_head,
        "pythonRequires": ">=3.11",
        "credentialCustody": "customer_only",
        "networkExecution": "customer_invoked_only",
        "providerPolicyEvidenceDate": PROVIDER_POLICY_EVIDENCE_DATE,
        "knownProviderIds": list(KNOWN_PROVIDER_IDS),
        "executableProviderIds": list(EXECUTABLE_PROVIDER_IDS),
        "disabledProviderIds": list(DISABLED_PROVIDER_IDS),
        "truth": EXPECTED_TRUTH,
        "files": _file_manifest(blobs),
    }
    return _canonical_bytes({**core, "bundleDigest": _sha256(_canonical_bytes(core))})


def _zip_info(path: str, mode: int) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(path, date_time=FIXED_ZIP_TIME)
    info.create_system = 3
    info.compress_type = zipfile.ZIP_STORED
    info.flag_bits = 0
    info.external_attr = (stat.S_IFREG | mode) << 16
    return info


def _write_archive(path: Path, blobs: dict[str, bytes], manifest_raw: bytes) -> None:
    members = {
        f"{BUNDLE_ROOT}/{bundle_path}": raw
        for bundle_path, raw in blobs.items()
    }
    members[f"{BUNDLE_ROOT}/bundle-manifest.json"] = manifest_raw
    try:
        with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_STORED) as archive:
            for member_path in sorted(members):
                relative = member_path.removeprefix(f"{BUNDLE_ROOT}/")
                mode = 0o755 if relative in EXECUTABLE_BUNDLE_PATHS else 0o644
                archive.writestr(_zip_info(member_path, mode), members[member_path])
    except (OSError, zipfile.BadZipFile) as error:
        raise RunnerBundleBuildError("runner bundle ZIP could not be written") from error


def _install_manifest(
    source_commit: str,
    archive_raw: bytes,
    bundle_manifest_raw: bytes,
    verifier_raw: bytes,
) -> bytes:
    core = {
        "schemaVersion": INSTALL_SCHEMA_VERSION,
        "artifactStatus": BUNDLE_STATUS,
        "sourceCommit": source_commit,
        "bundleFile": BUNDLE_FILENAME,
        "bundleSha256": _sha256(archive_raw),
        "bundleBytes": len(archive_raw),
        "bundleManifestFile": "bundle-manifest.json",
        "bundleManifestSha256": _sha256(bundle_manifest_raw),
        "verifierFile": "verify.py",
        "verifierSha256": _sha256(verifier_raw),
        "publicationAuthorized": False,
        "deploymentAuthorized": False,
    }
    return _canonical_bytes({**core, "artifactDigest": _sha256(_canonical_bytes(core))})


def build_bundle(
    destination: str | os.PathLike[str],
    *,
    _source_policy: object | None = None,
) -> dict[str, Any]:
    """Build one new artifact directory; the private policy is checker-only."""
    output = Path(destination).absolute()
    parent = _assert_output_target(output)
    if _source_policy is _TEST_SOURCE_POLICY:
        source_commit = "0" * 40
        built_from_exact_head = False
        blobs = _working_tree_source()
    elif _source_policy is None:
        source_commit, blobs = _exact_head_source()
        built_from_exact_head = True
    else:
        raise RunnerBundleBuildError("runner bundle source policy is invalid")
    _validate_source_map(blobs)

    stage = Path(tempfile.mkdtemp(prefix=".agentwars-runner-bundle-", dir=parent))
    try:
        manifest_raw = _bundle_manifest(source_commit, built_from_exact_head, blobs)
        _write_new(stage / "bundle-manifest.json", manifest_raw)
        verifier_raw = blobs["verify_bundle.py"]
        _write_new(stage / "verify.py", verifier_raw, 0o755)
        archive_path = stage / BUNDLE_FILENAME
        _write_archive(archive_path, blobs, manifest_raw)
        archive_raw = archive_path.read_bytes()
        install_raw = _install_manifest(
            source_commit, archive_raw, manifest_raw, verifier_raw
        )
        _write_new(stage / "install-manifest.json", install_raw)
        receipt = verify_artifact(stage)
        if output.exists() or output.is_symlink():
            raise RunnerBundleBuildError("runner bundle output appeared during build")
        os.replace(stage, output)
        try:
            directory_descriptor = os.open(parent, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        except OSError:
            pass
        return {
            **receipt,
            "status": "candidate_built_not_published",
            "outputCreated": True,
            "publicationAuthorized": False,
            "deploymentAuthorized": False,
        }
    except BaseException:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--candidate-only-v1", action="store_true")
    parser.add_argument("--customer-local-v1", action="store_true")
    parser.add_argument("--no-provider-call-v1", action="store_true")
    parser.add_argument("--no-publication-v1", action="store_true")
    args = parser.parse_args(argv)
    if not all(
        (
            args.candidate_only_v1,
            args.customer_local_v1,
            args.no_provider_call_v1,
            args.no_publication_v1,
        )
    ):
        print(
            json.dumps(
                {
                    "status": "refused",
                    "error": "all four candidate-only acknowledgements are required",
                    "providerCalls": 0,
                    "credentialsRead": False,
                    "publicationAuthorized": False,
                    "deploymentAuthorized": False,
                },
                sort_keys=True,
            )
        )
        return 2
    try:
        result = build_bundle(args.out)
    except (OSError, RunnerBundleBuildError, ValueError) as error:
        print(
            json.dumps(
                {
                    "status": "refused",
                    "error": str(error),
                    "providerCalls": 0,
                    "credentialsRead": False,
                    "publicationAuthorized": False,
                    "deploymentAuthorized": False,
                },
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
