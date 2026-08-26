#!/usr/bin/env python3
"""Offline policy checker for the AgentWars runner dependency lock.

The checked files pin a deliberately narrow CPython/wheel matrix.  This tool
does not contact an index, download or install a package, inspect credentials,
or claim that Nymrel signed upstream wheels.  It can also print the canonical
lock files so maintainers can review a dependency refresh before applying it.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import stat
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_VERSION = "agentwars.runner_dependencies.v1"
ARTIFACT_STATUS = "candidate_not_published"
EVIDENCE_DATE = "2026-08-26"
INDEX_ORIGIN = "https://pypi.org/simple"
PYTHON_VERSIONS = ("3.10", "3.11", "3.12", "3.13", "3.14")
MAX_FILE_BYTES = 2 * 1024 * 1024
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

PLATFORMS = (
    {
        "id": "linux_glibc_arm64",
        "wheelSuffix": "manylinux2014_aarch64.manylinux_2_17_aarch64.whl",
    },
    {
        "id": "linux_glibc_x86_64",
        "wheelSuffix": "manylinux2014_x86_64.manylinux_2_17_x86_64.whl",
    },
    {
        "id": "linux_musl_arm64",
        "wheelSuffix": "musllinux_1_2_aarch64.whl",
    },
    {
        "id": "linux_musl_x86_64",
        "wheelSuffix": "musllinux_1_2_x86_64.whl",
    },
    {"id": "macos_arm64", "wheelSuffix": "macosx_11_0_arm64.whl"},
    {"id": "windows_x86_64", "wheelSuffix": "win_amd64.whl"},
)

# filename, sha256, bytes.  Every row was reconciled against the exact-version
# PyPI JSON endpoints named in _expected_lock on EVIDENCE_DATE.
CRYPTOGRAPHY_ARTIFACTS = (
    (
        "cryptography-50.0.1-cp39-abi3-macosx_11_0_arm64.whl",
        "ca83d00d9e69cd5eb63f2e69c3a5a59e0cecae5ae14c6ae0b35830fe3b37bad0",
        4035307,
    ),
    (
        "cryptography-50.0.1-cp39-abi3-manylinux2014_aarch64.manylinux_2_17_aarch64.whl",
        "05ba322c4da95b262a212c345af888ef2c37c88c0509756ea00a0e6d68850f23",
        4751900,
    ),
    (
        "cryptography-50.0.1-cp39-abi3-manylinux2014_x86_64.manylinux_2_17_x86_64.whl",
        "e22dfed744bd4002e909464cb23d2f0b05c6f3113a79ef2e9864a53db737c733",
        4738357,
    ),
    (
        "cryptography-50.0.1-cp39-abi3-musllinux_1_2_aarch64.whl",
        "fd3718b960d0b5dd213cdf03f3bcb7000e69dda0de8b956061947ff6bcff5558",
        4888413,
    ),
    (
        "cryptography-50.0.1-cp39-abi3-musllinux_1_2_x86_64.whl",
        "2a93d05e34d5f67fba6f891fe85d929999baa7195e853923ea6d7576c9e68c5e",
        5044355,
    ),
    (
        "cryptography-50.0.1-cp39-abi3-win_amd64.whl",
        "55d16b1ef3ee0958d893a977b19777887e546c9954ea81b200c3301a864013f2",
        3875429,
    ),
    (
        "cryptography-50.0.1-cp311-abi3-macosx_11_0_arm64.whl",
        "b8f852c65863251b9e3a1b8c150ce21e59b522dbb6a7d4bc80e680d38388e986",
        4010153,
    ),
    (
        "cryptography-50.0.1-cp311-abi3-manylinux2014_aarch64.manylinux_2_17_aarch64.whl",
        "53e279950892dc102c6b4e52af03ae5ea92fac572a1ddab78ca73a997f62b69f",
        4723133,
    ),
    (
        "cryptography-50.0.1-cp311-abi3-manylinux2014_x86_64.manylinux_2_17_x86_64.whl",
        "ff838d62ec1bfce4f9ba7fa16f4a7b554cd8d0c299e6be37502161a660c84eef",
        4712478,
    ),
    (
        "cryptography-50.0.1-cp311-abi3-musllinux_1_2_aarch64.whl",
        "be224a65493ec5b74a158ff22a5522ce4a5ca1e543c647a3a4730d4a09e5f959",
        4862596,
    ),
    (
        "cryptography-50.0.1-cp311-abi3-musllinux_1_2_x86_64.whl",
        "9ebcdd5519be9b652a46f507817a74591774fc3d6923ac364e4dfa64e36b291b",
        5014082,
    ),
    (
        "cryptography-50.0.1-cp311-abi3-win_amd64.whl",
        "aed8db4f6d71c51efb89530e12d9464e7bf2923d46c3205dc794a2a93f8c0648",
        3842826,
    ),
)

CFFI_ARTIFACTS = (
    (
        "cffi-2.1.1-cp310-cp310-macosx_11_0_arm64.whl",
        "ca82be1a1d406ecfe1d25dc16cb33488e5a16bf4438c9fb590484ea29d92478b",
        184178,
    ),
    (
        "cffi-2.1.1-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.whl",
        "5a59cc1c4442bc3d5c703bf720b51138d0bfc173618807c9ee2490a7541dd3d9",
        218652,
    ),
    (
        "cffi-2.1.1-cp310-cp310-manylinux2014_x86_64.manylinux_2_17_x86_64.whl",
        "194cffa889098ced9976c3fc6340305e43f6303657d298da55366907c05c22d6",
        218742,
    ),
    (
        "cffi-2.1.1-cp310-cp310-musllinux_1_2_aarch64.whl",
        "5bb4e7ea95dcd6a014a6fef62e62467d67d8e582326443f3d68e71d6320a9fcf",
        221054,
    ),
    (
        "cffi-2.1.1-cp310-cp310-musllinux_1_2_x86_64.whl",
        "1dea0e4d7d4f11f619fe8c1d76caf49e24405b4b5743c0e3be16a500ecd930c9",
        220241,
    ),
    (
        "cffi-2.1.1-cp310-cp310-win_amd64.whl",
        "a48d62ab9d6f4f98c983223a547af44be6ca3691074c31cecced6facd3ba2dc1",
        185082,
    ),
    (
        "cffi-2.1.1-cp311-cp311-macosx_11_0_arm64.whl",
        "398aff33cee2767e3e781d2554c54bd0dff386bb437581e0d8011fde1a942ec1",
        184168,
    ),
    (
        "cffi-2.1.1-cp311-cp311-manylinux2014_aarch64.manylinux_2_17_aarch64.whl",
        "3311ed60d36f83378794e1009ac6258bafbf81f7888b4caa7b35a521e3f95813",
        218716,
    ),
    (
        "cffi-2.1.1-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.whl",
        "34e261f78cb6ceaaa36f42f2613f4380d94d9c759a9c73c769ee6e0247364632",
        217807,
    ),
    (
        "cffi-2.1.1-cp311-cp311-musllinux_1_2_aarch64.whl",
        "7225e4514edb64eb6740324353e0da0711954fd8d7da4576755b1c6e09b697cd",
        221252,
    ),
    (
        "cffi-2.1.1-cp311-cp311-musllinux_1_2_x86_64.whl",
        "f5cfbc5fe74540d335175b656c725d74d90e3730c626d92575eea35029d9afaa",
        219408,
    ),
    (
        "cffi-2.1.1-cp311-cp311-win_amd64.whl",
        "42f6930c31dc7f50732c9ae793c2786c7b6b044195967bbdde40bb9be81c4cc0",
        185096,
    ),
    (
        "cffi-2.1.1-cp312-cp312-macosx_11_0_arm64.whl",
        "f81b3b8f3d4e343550fa4baa0e479bba9f2d29ce9c2e9b51d1ce1718d7442fcf",
        184719,
    ),
    (
        "cffi-2.1.1-cp312-cp312-manylinux2014_aarch64.manylinux_2_17_aarch64.whl",
        "68e62fe11f30d5ca8289242866f0a5291402d8529ca2178ab8afc5c9694ae890",
        222389,
    ),
    (
        "cffi-2.1.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl",
        "c1453022f490d2459a11819d83ad1d586e9ff65a12ac3e705ffebd46d3685dcf",
        221822,
    ),
    (
        "cffi-2.1.1-cp312-cp312-musllinux_1_2_aarch64.whl",
        "208f941bb9d18e768138677f0a6d2ce01f590df56043dda1df1535ac57c88517",
        225232,
    ),
    (
        "cffi-2.1.1-cp312-cp312-musllinux_1_2_x86_64.whl",
        "210019b6c7cf07f081b4c54635c8cf744377001350e29cc0f81c4377b4797735",
        223597,
    ),
    (
        "cffi-2.1.1-cp312-cp312-win_amd64.whl",
        "f53e442b08449d42821fa4a4fba000095af9f62742a500f978a9f557ec44339a",
        185919,
    ),
    (
        "cffi-2.1.1-cp313-cp313-macosx_11_0_arm64.whl",
        "19ee6127ee34de7d83ce3d371ebc5ed91addbdcc39f9ab15ce4eb35a4e534971",
        184764,
    ),
    (
        "cffi-2.1.1-cp313-cp313-manylinux2014_aarch64.manylinux_2_17_aarch64.whl",
        "f16c709686a78c727bbbf059f92b0bf41c6fc60deec706d2dc19f529175a6125",
        222369,
    ),
    (
        "cffi-2.1.1-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.whl",
        "a931079504ecc49efed7744c476a5c343a92fabf66dec2db95edb1b2fdc770e2",
        221824,
    ),
    (
        "cffi-2.1.1-cp313-cp313-musllinux_1_2_aarch64.whl",
        "a2d7755bef5a12ed488f4ef1f1b69ee9191d7396083b755a5d2295f6edb4768b",
        225148,
    ),
    (
        "cffi-2.1.1-cp313-cp313-musllinux_1_2_x86_64.whl",
        "e0bcb7e0f677f543555d2adff3bf19c05f66cdb4796e5ff602442ab2fe3c4ef7",
        223564,
    ),
    (
        "cffi-2.1.1-cp313-cp313-win_amd64.whl",
        "1aa5645c30469b09530c4ebca77ebf8f17618293c58f8549cb1a543a50236e7d",
        185688,
    ),
    (
        "cffi-2.1.1-cp314-cp314-macosx_11_0_arm64.whl",
        "661c298b4821edebead0c91edd2b00374d67ad7c5a1f7a91d4442633b79d6a72",
        184962,
    ),
    (
        "cffi-2.1.1-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.whl",
        "58acb8ab8e295e6c5ea12f888cbb13cf21511ef2a3303a23f4325c29d17fe5c1",
        222328,
    ),
    (
        "cffi-2.1.1-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.whl",
        "b0431303acaea1089ad4b3e9ce4e6518193def1118d4073ca848635ee4ea2e96",
        221525,
    ),
    (
        "cffi-2.1.1-cp314-cp314-musllinux_1_2_aarch64.whl",
        "64faea20f4e2613363a1a9b9c7dd73058f3ecd00133a511e72ad7c511658f527",
        225053,
    ),
    (
        "cffi-2.1.1-cp314-cp314-musllinux_1_2_x86_64.whl",
        "5c58fe613dc5e5336357eff555824a314d8e43282600435c8d1cb6a7a2fedd13",
        223213,
    ),
    (
        "cffi-2.1.1-cp314-cp314-win_amd64.whl",
        "3222ba5d678f80a030e6afbcc33dc1ae5cb45facabb61cee2c7016b8432fde48",
        187949,
    ),
)

PYCPARSER_ARTIFACTS = (
    (
        "pycparser-3.0-py3-none-any.whl",
        "b727414169a36b7d524c1c3e31839a521725078d7b2ff038656844266160a992",
        48172,
    ),
)

PACKAGE_ROWS = (
    {
        "artifacts": CRYPTOGRAPHY_ARTIFACTS,
        "dependencies": ("cffi==2.1.1",),
        "licenseExpression": "Apache-2.0 OR BSD-3-Clause",
        "name": "cryptography",
        "requiresPython": "!=3.9.0,!=3.9.1,>=3.9",
        "version": "50.0.1",
    },
    {
        "artifacts": CFFI_ARTIFACTS,
        "dependencies": ("pycparser==3.0",),
        "licenseExpression": "MIT-0",
        "name": "cffi",
        "requiresPython": ">=3.10",
        "version": "2.1.1",
    },
    {
        "artifacts": PYCPARSER_ARTIFACTS,
        "dependencies": (),
        "licenseExpression": "BSD-3-Clause",
        "name": "pycparser",
        "requiresPython": ">=3.10",
        "version": "3.0",
    },
)

REQUIREMENTS_WRAPPER = (
    "# Compatibility entrypoint for the exact AgentWars runner dependency lock.\n"
    "# The included lock forces PyPI, binary wheels, exact versions, and hashes.\n"
    "-r requirements.lock\n"
).encode("ascii")


class DependencyLockError(ValueError):
    """Bounded refusal without reflecting package or credential content."""


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("ascii")


def _without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DependencyLockError("dependency lock contains a duplicate key")
        result[key] = value
    return result


def _reject_number(_value: str) -> Any:
    raise DependencyLockError("dependency lock contains a non-integer number")


def _strict_json(raw: bytes) -> dict[str, Any]:
    if not raw or len(raw) > MAX_FILE_BYTES or raw.startswith(b"\xef\xbb\xbf"):
        raise DependencyLockError("dependency lock has invalid bytes")
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_without_duplicates,
            parse_float=_reject_number,
            parse_constant=_reject_number,
        )
    except DependencyLockError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DependencyLockError("dependency lock is not strict JSON") from error
    if not isinstance(value, dict) or _canonical_bytes(value) != raw:
        raise DependencyLockError("dependency lock is not canonical JSON")
    return value


def _platform_for_filename(filename: str) -> str:
    if filename.endswith("py3-none-any.whl"):
        return "any"
    matches = [
        row["id"] for row in PLATFORMS if filename.endswith(row["wheelSuffix"])
    ]
    if len(matches) != 1:
        raise DependencyLockError("dependency artifact has an unsupported platform")
    return matches[0]


def _python_versions_for_filename(filename: str) -> list[str]:
    if "-cp39-abi3-" in filename:
        return ["3.10"]
    if "-cp311-abi3-" in filename:
        return [version for version in PYTHON_VERSIONS if version != "3.10"]
    if filename.endswith("py3-none-any.whl"):
        return list(PYTHON_VERSIONS)
    match = re.search(r"-cp(310|311|312|313|314)-cp\1-", filename)
    if match is None:
        raise DependencyLockError("dependency artifact has an unsupported Python tag")
    digits = match.group(1)
    return [f"{digits[0]}.{digits[1:]}"]


def _artifact_record(row: tuple[str, str, int]) -> dict[str, Any]:
    filename, digest, size = row
    if (
        not filename.endswith(".whl")
        or HEX64_RE.fullmatch(digest) is None
        or not isinstance(size, int)
        or isinstance(size, bool)
        or size < 1
    ):
        raise DependencyLockError("dependency artifact policy is invalid")
    return {
        "bytes": size,
        "filename": filename,
        "platform": _platform_for_filename(filename),
        "pythonVersions": _python_versions_for_filename(filename),
        "sha256": digest,
    }


def _render_requirements() -> bytes:
    lines = [
        "# Exact binary-only dependency lock for the AgentWars customer-local runner.",
        "# Network access is required unless the tester pre-populates an exact wheel cache.",
        f"--index-url {INDEX_ORIGIN}",
        "--only-binary=:all:",
        "--require-hashes",
        "",
    ]
    def append_requirement(requirement: str, artifacts: tuple[tuple[str, str, int], ...]) -> None:
        lines.append(requirement + " " + "\\")
        for index, (_, digest, _) in enumerate(artifacts):
            suffix = " " + "\\" if index < len(artifacts) - 1 else ""
            lines.append(f"    --hash=sha256:{digest}{suffix}")
        lines.append("")

    for package in PACKAGE_ROWS:
        artifacts = tuple(package["artifacts"])
        requirement = f"{package['name']}=={package['version']}"
        if package["name"] == "cryptography":
            python_310 = tuple(row for row in artifacts if "-cp39-abi3-" in row[0])
            python_311_plus = tuple(
                row for row in artifacts if "-cp311-abi3-" in row[0]
            )
            append_requirement(
                requirement + ' ; python_version == "3.10"', python_310
            )
            append_requirement(
                requirement
                + ' ; python_version >= "3.11" and python_version < "3.15"',
                python_311_plus,
            )
        else:
            append_requirement(requirement, artifacts)
    return ("\n".join(lines).rstrip() + "\n").encode("ascii")


def _expected_lock() -> dict[str, Any]:
    packages = []
    for package in PACKAGE_ROWS:
        packages.append(
            {
                "artifacts": [
                    _artifact_record(row) for row in package["artifacts"]
                ],
                "dependencies": list(package["dependencies"]),
                "licenseExpression": package["licenseExpression"],
                "name": package["name"],
                "requiresPython": package["requiresPython"],
                "version": package["version"],
            }
        )
    return {
        "artifactStatus": ARTIFACT_STATUS,
        "evidenceDate": EVIDENCE_DATE,
        "indexOrigin": INDEX_ORIGIN,
        "metadataSources": [
            "https://pypi.org/pypi/cffi/2.1.1/json",
            "https://pypi.org/pypi/cryptography/50.0.1/json",
            "https://pypi.org/pypi/pycparser/3.0/json",
        ],
        "packages": packages,
        "platforms": [dict(row) for row in PLATFORMS],
        "python": {
            "freeThreaded": False,
            "implementation": "CPython",
            "versions": list(PYTHON_VERSIONS),
        },
        "requirementsLockFile": "requirements.lock",
        "requirementsLockSha256": _sha256(_render_requirements()),
        "schemaVersion": SCHEMA_VERSION,
        "truth": {
            "crossPlatformRuntimeAttested": False,
            "defaultInstallRequiresNetwork": True,
            "hashesReconciledToMetadataOnEvidenceDate": True,
            "nymrelSignaturePresent": False,
            "onlyBinary": True,
            "pythonMarkersEnforced": True,
            "sourceBuildsAllowed": False,
            "upstreamArtifactSignaturesVerified": False,
            "wheelsBundled": False,
        },
    }


def expected_lock_bytes() -> bytes:
    return _canonical_bytes(_expected_lock())


def expected_requirements_bytes() -> bytes:
    return _render_requirements()


def _validate_lock_bytes(raw: bytes) -> dict[str, Any]:
    value = _strict_json(raw)
    if value != _expected_lock():
        raise DependencyLockError("dependency lock policy is invalid")
    artifacts = [
        artifact
        for package in value["packages"]
        for artifact in package["artifacts"]
    ]
    filenames = [artifact["filename"] for artifact in artifacts]
    digests = [artifact["sha256"] for artifact in artifacts]
    if len(filenames) != 43 or len(filenames) != len(set(filenames)):
        raise DependencyLockError("dependency artifact allowlist is invalid")
    if len(digests) != len(set(digests)):
        raise DependencyLockError("dependency artifact hashes are not unique")
    for platform in (row["id"] for row in PLATFORMS):
        for version in PYTHON_VERSIONS:
            for package in value["packages"]:
                if not any(
                    artifact["platform"] in {platform, "any"}
                    and version in artifact["pythonVersions"]
                    for artifact in package["artifacts"]
                ):
                    raise DependencyLockError(
                        "dependency lock has incomplete platform coverage"
                    )
    return value


def verify_dependency_bytes(
    lock_raw: bytes,
    requirements_raw: bytes,
    wrapper_raw: bytes,
) -> dict[str, Any]:
    value = _validate_lock_bytes(lock_raw)
    expected_requirements = _render_requirements()
    if requirements_raw != expected_requirements:
        raise DependencyLockError("requirements lock bytes are invalid")
    if wrapper_raw != REQUIREMENTS_WRAPPER:
        raise DependencyLockError("requirements wrapper bytes are invalid")
    if value["requirementsLockSha256"] != _sha256(requirements_raw):
        raise DependencyLockError("requirements lock digest is invalid")
    return {
        "artifactCount": 43,
        "artifactStatus": ARTIFACT_STATUS,
        "credentialReads": 0,
        "dependencyLockSha256": _sha256(lock_raw),
        "downloads": 0,
        "evidenceDate": EVIDENCE_DATE,
        "hashLocked": True,
        "installs": 0,
        "networkCalls": 0,
        "nymrelSignaturePresent": False,
        "packageVersions": {
            package["name"]: package["version"] for package in value["packages"]
        },
        "platformCount": len(PLATFORMS),
        "requirementsLockSha256": _sha256(requirements_raw),
        "sourceBuildsAllowed": False,
        "status": "pass",
        "wheelsBundled": False,
    }


def _is_reparse(path: Path) -> bool:
    try:
        attributes = path.lstat().st_file_attributes
    except AttributeError:
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _read_regular(path: Path) -> bytes:
    try:
        before = path.lstat()
    except OSError as error:
        raise DependencyLockError("dependency lock file is unavailable") from error
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or path.is_symlink()
        or _is_reparse(path)
        or before.st_size < 1
        or before.st_size > MAX_FILE_BYTES
    ):
        raise DependencyLockError("dependency lock file is not a direct regular file")
    try:
        raw = path.read_bytes()
        after = path.lstat()
    except OSError as error:
        raise DependencyLockError("dependency lock file could not be read") from error
    if (
        before.st_dev != after.st_dev
        or before.st_ino != after.st_ino
        or before.st_size != after.st_size
        or len(raw) != after.st_size
    ):
        raise DependencyLockError("dependency lock file changed during read")
    return raw


def verify_dependency_files(root: str | Path = ROOT) -> dict[str, Any]:
    base = Path(root).absolute()
    return verify_dependency_bytes(
        _read_regular(base / "dependency-lock.json"),
        _read_regular(base / "requirements.lock"),
        _read_regular(base / "requirements.txt"),
    )


def _expect_refusal(action, phrase: str) -> None:
    try:
        action()
    except DependencyLockError as error:
        if phrase not in str(error):
            raise AssertionError("dependency lock refused for the wrong reason") from error
        return
    raise AssertionError("dependency lock mutation was accepted")


def _self_test(lock_raw: bytes, requirements_raw: bytes, wrapper_raw: bytes) -> int:
    receipt = verify_dependency_bytes(lock_raw, requirements_raw, wrapper_raw)
    checks = 8
    if receipt["artifactCount"] != 43 or receipt["platformCount"] != 6:
        raise AssertionError("dependency lock receipt counts drifted")
    duplicate = lock_raw.replace(
        b"{\n", b'{\n  "schemaVersion": "duplicate",\n', 1
    )
    _expect_refusal(lambda: _validate_lock_bytes(duplicate), "duplicate key")
    checks += 1

    unknown = copy.deepcopy(_expected_lock())
    unknown["unexpected"] = True
    _expect_refusal(
        lambda: _validate_lock_bytes(_canonical_bytes(unknown)), "policy"
    )
    checks += 1

    changed_hash = copy.deepcopy(_expected_lock())
    changed_hash["packages"][0]["artifacts"][0]["sha256"] = "0" * 64
    _expect_refusal(
        lambda: _validate_lock_bytes(_canonical_bytes(changed_hash)), "policy"
    )
    checks += 1

    missing_wheel = copy.deepcopy(_expected_lock())
    missing_wheel["packages"][1]["artifacts"].pop()
    _expect_refusal(
        lambda: _validate_lock_bytes(_canonical_bytes(missing_wheel)), "policy"
    )
    checks += 1

    source_build = copy.deepcopy(_expected_lock())
    source_build["truth"]["sourceBuildsAllowed"] = True
    _expect_refusal(
        lambda: _validate_lock_bytes(_canonical_bytes(source_build)), "policy"
    )
    checks += 1

    free_threaded = copy.deepcopy(_expected_lock())
    free_threaded["python"]["freeThreaded"] = True
    _expect_refusal(
        lambda: _validate_lock_bytes(_canonical_bytes(free_threaded)), "policy"
    )
    checks += 1

    _expect_refusal(
        lambda: verify_dependency_bytes(
            lock_raw, requirements_raw.replace(b"--require-hashes\n", b""), wrapper_raw
        ),
        "requirements lock bytes",
    )
    checks += 1

    _expect_refusal(
        lambda: verify_dependency_bytes(
            lock_raw,
            requirements_raw.replace(
                b' ; python_version == "3.10"', b"", 1
            ),
            wrapper_raw,
        ),
        "requirements lock bytes",
    )
    checks += 1

    _expect_refusal(
        lambda: verify_dependency_bytes(
            lock_raw,
            requirements_raw,
            b"cryptography>=50.0.0,<51\n",
        ),
        "requirements wrapper bytes",
    )
    checks += 1
    return checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--json", action="store_true")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--print-lock", action="store_true")
    output.add_argument("--print-requirements", action="store_true")
    args = parser.parse_args(argv)
    if args.print_lock:
        sys.stdout.buffer.write(expected_lock_bytes())
        return 0
    if args.print_requirements:
        sys.stdout.buffer.write(expected_requirements_bytes())
        return 0
    try:
        root = Path(args.root).absolute()
        lock_raw = _read_regular(root / "dependency-lock.json")
        requirements_raw = _read_regular(root / "requirements.lock")
        wrapper_raw = _read_regular(root / "requirements.txt")
        receipt = verify_dependency_bytes(lock_raw, requirements_raw, wrapper_raw)
        receipt["checks"] = _self_test(lock_raw, requirements_raw, wrapper_raw)
    except (OSError, DependencyLockError, AssertionError) as error:
        print(
            json.dumps(
                {
                    "credentialReads": 0,
                    "downloads": 0,
                    "error": str(error),
                    "installs": 0,
                    "networkCalls": 0,
                    "status": "refused",
                },
                sort_keys=True,
            )
        )
        return 2
    if args.json:
        print(json.dumps(receipt, sort_keys=True))
    else:
        print(
            "AgentWars dependency lock: PASS "
            f"({receipt['checks']} checks, {receipt['artifactCount']} wheels)"
        )
        print(
            "exact versions / hashes / binary only / no download / no install / "
            "not Nymrel-signed"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
