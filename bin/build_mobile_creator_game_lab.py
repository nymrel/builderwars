#!/usr/bin/env python3
"""Compile one reviewed creator-game candidate into a held mobile lab snapshot.

The compiler reuses the trusted declarative verifier and never grants runtime,
publication, ranking, or creator-code authority. The mobile artifact is a
read-only projection; valid source data remains a held candidate.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arena.canonical import digest  # noqa: E402
from creator_sdk.runtime import (  # noqa: E402
    CANDIDATE_STATUS,
    REGISTRY_STATUS,
    load_manifest,
    load_registry,
    load_replay,
    manifest_sha256,
    replay_sha256,
    verify_replay,
)


SCHEMA_VERSION = "builderwars.mobile-creator-game-lab.v1"
SOURCE_STATUS = "tracked_reviewed_candidate_not_admitted"
EXPECTED_GAME_ID = "creator.signal-siege"
EXPECTED_VERSION = "1.0.0"
DEFAULT_REGISTRY = ROOT / "creator_games" / "registry.v1.json"
DEFAULT_OUTPUT = ROOT / "mobile-arena" / "data" / "creator-game-lab.v1.json"
BOUNDARY = (
    "This lab renders one source-reviewed declarative game candidate and one deterministic replay. "
    "It imports and executes no creator code, calls no model or provider, and grants no identity, "
    "runtime, registry, publication, ranking, spending, legal, or production authority."
)
ADMISSION_GATES = (
    "creator_identity_authorship_license_and_asset_provenance_review",
    "exact_manifest_and_replay_digest_review",
    "independent_visibility_scoring_and_seed_review",
    "unranked_exhibition_decision",
    "mirrored_seat_soak",
    "rollback_and_version_migration_proof",
    "source_controlled_promotion_decision",
    "deployment_and_public_byte_verification",
)
AUTHORITY = {
    "authorEntrantRankingAuthorized": False,
    "codeExecutionAuthorized": False,
    "creatorCodeExecuted": False,
    "executionAuthorized": False,
    "harnessExecutionAttested": False,
    "modelAttested": False,
    "providerAttested": False,
    "publicationAuthorized": False,
    "rankingAuthorized": False,
    "runtimeAttested": False,
}


class CreatorGameLabError(ValueError):
    """Raised when reviewed creator-game source cannot produce the mobile lab."""


def _require(predicate: bool, message: str) -> None:
    if not predicate:
        raise CreatorGameLabError(message)


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CreatorGameLabError(f"{label} is unavailable or invalid") from exc
    _require(type(value) is dict, f"{label} must be an object")
    return value


def build_lab(registry_path: Path = DEFAULT_REGISTRY) -> dict[str, Any]:
    registry = _load_object(registry_path, "creator-game registry")
    registry_report = load_registry(registry_path, ROOT)
    _require(registry_report["candidateStatus"] == REGISTRY_STATUS, "registry admission boundary drift")
    _require(registry_report["entryCount"] == 1 and len(registry["entries"]) == 1, "mobile v1 requires exactly one reviewed candidate")
    entry = registry["entries"][0]
    _require(entry["gameId"] == EXPECTED_GAME_ID and entry["version"] == EXPECTED_VERSION, "reviewed creator-game identity drift")
    _require(entry["decision"] == "held_exhibition_candidate", "creator-game decision overstates admission")
    _require(all(entry[key] is False for key in ("authorEntrantRankingAuthorized", "executionAuthorized", "publicationAuthorized")), "creator-game registry grants forbidden authority")

    manifest = load_manifest(ROOT / entry["manifestPath"])
    replay = load_replay(ROOT / entry["replayPath"])
    report = verify_replay(manifest, replay)
    manifest_digest = manifest_sha256(manifest)
    replay_digest = replay_sha256(replay)
    _require(manifest_digest == entry["manifestSha256"], "manifest digest drift")
    _require(replay_digest == entry["replaySha256"], "replay digest drift")
    _require(report["candidateStatus"] == CANDIDATE_STATUS and report["effectiveVerdict"] == "PASS", "reviewed replay is not a held PASS")
    _require(all(report[key] is False for key in ("modelAttested", "providerAttested", "runtimeAttested", "harnessExecutionAttested", "rankingAuthorized", "publicationAuthorized", "codeExecutionAuthorized")), "replay report grants forbidden authority")

    core: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "sourceStatus": SOURCE_STATUS,
        "candidateStatus": CANDIDATE_STATUS,
        "registryStatus": REGISTRY_STATUS,
        "decision": entry["decision"],
        "manifestSha256": manifest_digest,
        "replaySha256": replay_digest,
        "manifest": manifest,
        "replay": {
            "effectiveVerdict": report["effectiveVerdict"],
            "moveCount": report["moveCount"],
            "seed": replay["seed"],
            "scores": replay["result"]["scores"],
            "winner": replay["result"]["winner"],
            "reason": replay["result"]["reason"],
            "finalStateSha256": replay["finalStateSha256"],
        },
        "authority": dict(AUTHORITY),
        "admissionGates": list(ADMISSION_GATES),
        "boundary": BOUNDARY,
    }
    return {**core, "labDigest": digest(core)}


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        lab = build_lab(args.registry)
        expected = _json_bytes(lab)
        if args.write:
            _atomic_write(args.out, expected)
            print(f"wrote {args.out} ({lab['manifest']['title']}, {lab['labDigest']})")
            return 0
        try:
            actual = args.out.read_bytes()
        except OSError as exc:
            raise CreatorGameLabError(f"compiled mobile creator-game lab is unavailable: {args.out}") from exc
        _require(actual == expected, f"compiled mobile creator-game lab is stale: run {Path(__file__).name} --write")
        print(f"PASS: {args.out} is current ({lab['manifest']['title']}, {lab['labDigest']})")
        return 0
    except CreatorGameLabError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
