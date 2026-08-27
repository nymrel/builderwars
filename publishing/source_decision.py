"""Fail-closed source-control decision for one AgentWars promotion candidate.

This module is deliberately narrower than a publisher.  It validates the four-file
offline candidate, independently replays its transcript, and stages exactly two
reviewable source changes: one transcript plus one explicit manifest entry.  It
does not rebuild the public product, commit, deploy, rank, or attest a provider,
model, reviewer, or server identity.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .product import load_publication_manifest
from .projection import PublicationError, project_receipt
from .promotion import (
    ENGINE_SHA256,
    PromotionCandidateError,
    _assert_direct_ancestors,
    _is_reparse,
    _parse_strict_json,
    _read_regular_file,
    _tree_digest,
    canonical_digest,
    canonical_json,
    sha256_hex,
)


class SourceDecisionError(ValueError):
    """A bounded, non-sensitive source-decision refusal."""


CANDIDATE_FILES = frozenset(
    {
        "candidate.json",
        "manifest-entry-candidate.json",
        "public-receipt-preview.json",
        "transcript.jsonl",
    }
)
CANDIDATE_KEYS = frozenset(
    {
        "schemaVersion",
        "candidateId",
        "candidateStatus",
        "sourceContract",
        "sourceExport",
        "reviewDecisionClaim",
        "evidenceBindings",
        "verification",
        "suggestedSourcePath",
        "files",
        "authorizations",
        "truthBoundary",
        "candidateDigest",
    }
)
SOURCE_EXPORT_KEYS = frozenset(
    {
        "exactFileSha256",
        "canonicalPayloadSha256",
        "exactBytes",
        "reviewerAccessClaim",
        "reviewerExportOriginAttested",
        "reviewerIdentityAttested",
        "serverSignatureVerified",
        "authenticatedTransportVerifiedOffline",
    }
)
REVIEW_DECISION_KEYS = frozenset(
    {
        "status",
        "reasonCode",
        "publicationDecision",
        "promotionStatus",
        "decisionReceiptCommitment",
        "requestCommitment",
    }
)
EVIDENCE_BINDING_KEYS = frozenset(
    {
        "jobCommitmentSha256",
        "evidenceBundleSha256",
        "resultBodySha256",
        "summarySha256",
        "summaryDigest",
        "compressedTranscriptSha256",
        "transcriptSha256",
        "projectionDigest",
        "chainHead",
        "engineSha256",
    }
)
VERIFICATION_KEYS = frozenset(
    {
        "builderWarsReplayVerdict",
        "builderWarsEffectiveVerdict",
        "engineDigestMatch",
        "verifierSnapshotMatch",
        "crossImplementationProjectionMatch",
        "allAcceptedMovesModelClaimed",
        "modelAttested",
        "publicationManifestUnchanged",
        "generatedArtifactUnchanged",
    }
)
AUTHORIZATION_KEYS = frozenset(
    {
        "manifestMutationAuthorized",
        "generatedArtifactMutationAuthorized",
        "publicationAuthorized",
        "deploymentAuthorized",
        "rankingAuthorized",
        "providerOrModelAttested",
        "sourceControlReviewRequired",
    }
)
MANIFEST_CANDIDATE_KEYS = frozenset(
    {
        "schemaVersion",
        "candidateId",
        "candidateStatus",
        "sequenceAssignmentRequired",
        "requiredDecision",
        "suggestedSourcePath",
        "entryWithoutSequence",
        "authorizations",
    }
)
ENTRY_WITHOUT_SEQUENCE_KEYS = frozenset(
    {
        "sourcePath",
        "sourceFileSha256",
        "sourceChainHead",
        "sourceCounts",
        "decision",
        "titleEligible",
        "label",
    }
)
FILE_ROW_KEYS = frozenset({"sha256", "bytes"})
SOURCE_COUNT_KEYS = frozenset({"model", "fallback", "scripted", "other"})
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
CANDIDATE_ID_RE = re.compile(r"^candidate_[0-9a-f]{24}$")
SOURCE_PATH_RE = re.compile(
    r"^matches/agentwars-review-candidates/"
    r"([A-Za-z0-9][A-Za-z0-9._-]{0,63})/"
    r"(0|[1-9][0-9]{0,9})-([0-9a-f]{16})/([0-9a-f]{64})\.jsonl$"
)
EXPECTED_AUTHORIZATIONS = {
    "manifestMutationAuthorized": False,
    "generatedArtifactMutationAuthorized": False,
    "publicationAuthorized": False,
    "deploymentAuthorized": False,
    "rankingAuthorized": False,
    "providerOrModelAttested": False,
    "sourceControlReviewRequired": True,
}
EXPECTED_CANDIDATE_TRUTH_BOUNDARY = (
    "The export's internal commitments and embedded replay verify, but the offline file "
    "does not cryptographically prove its Nymrel server origin or reviewer identity. "
    "Only a separate reviewed source commit may choose a publication decision."
)


def _expect_row(value: Any, keys: frozenset[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise SourceDecisionError(f"{label} shape is invalid")
    return value


def _expect_hex(value: Any, label: str) -> str:
    if not isinstance(value, str) or HEX64_RE.fullmatch(value) is None:
        raise SourceDecisionError(f"{label} must be lowercase sha256")
    return value


def _expect_nonnegative_integer(
    value: Any, label: str, maximum: int = 10_000_000
) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or not 0 <= value <= maximum
    ):
        raise SourceDecisionError(f"{label} must be a bounded non-negative integer")
    return value


def _canonical_json_file(raw: bytes, label: str) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise SourceDecisionError(f"{label} must be UTF-8 JSON") from error
    try:
        payload = _parse_strict_json(text, label)
    except PromotionCandidateError as error:
        raise SourceDecisionError(str(error)) from error
    if not isinstance(payload, dict):
        raise SourceDecisionError(f"{label} root must be an object")
    expected = (canonical_json(payload) + "\n").encode("utf-8")
    if raw != expected:
        raise SourceDecisionError(
            f"{label} bytes are not the canonical candidate encoding"
        )
    return payload


def _read_candidate_directory(repo_root: str, candidate_dir: str) -> dict[str, bytes]:
    root = os.path.abspath(repo_root)
    candidate = os.path.abspath(candidate_dir)
    try:
        shared_path = os.path.commonpath([root, candidate])
    except ValueError:
        shared_path = None
    if shared_path is not None and os.path.normcase(shared_path) == os.path.normcase(
        root
    ):
        raise SourceDecisionError(
            "candidate directory must remain outside the source repository"
        )
    try:
        _assert_direct_ancestors(candidate, include_leaf=True)
    except PromotionCandidateError as error:
        raise SourceDecisionError(str(error)) from error
    metadata = os.lstat(candidate)
    if not stat.S_ISDIR(metadata.st_mode) or _is_reparse(candidate):
        raise SourceDecisionError("candidate path must be one direct local directory")
    try:
        names = frozenset(os.listdir(candidate))
    except OSError as error:
        raise SourceDecisionError("candidate directory could not be listed") from error
    if names != CANDIDATE_FILES:
        raise SourceDecisionError(
            "candidate directory must contain exactly the four reviewed files"
        )
    files: dict[str, bytes] = {}
    for name in sorted(CANDIDATE_FILES):
        try:
            files[name] = _read_regular_file(os.path.join(candidate, name))
        except PromotionCandidateError as error:
            raise SourceDecisionError(str(error)) from error
    return files


def _validate_authorizations(value: Any, label: str) -> dict[str, bool]:
    row = _expect_row(value, AUTHORIZATION_KEYS, label)
    if row != EXPECTED_AUTHORIZATIONS:
        raise SourceDecisionError(f"{label} overstates candidate authority")
    return row


def _validate_file_rows(candidate: dict[str, Any], files: dict[str, bytes]) -> None:
    rows = candidate.get("files")
    expected_names = CANDIDATE_FILES - {"candidate.json"}
    if not isinstance(rows, dict) or set(rows) != expected_names:
        raise SourceDecisionError("candidate file inventory shape is invalid")
    for name in sorted(expected_names):
        row = _expect_row(rows[name], FILE_ROW_KEYS, f"candidate file inventory {name}")
        if _expect_hex(
            row["sha256"], f"candidate file inventory {name} sha256"
        ) != sha256_hex(files[name]):
            raise SourceDecisionError(
                f"candidate file inventory hash differs for {name}"
            )
        if _expect_nonnegative_integer(
            row["bytes"], f"candidate file inventory {name} bytes", 262_144
        ) != len(files[name]):
            raise SourceDecisionError(
                f"candidate file inventory byte count differs for {name}"
            )


def _validate_source_counts(value: Any) -> dict[str, int]:
    row = _expect_row(value, SOURCE_COUNT_KEYS, "manifest candidate source counts")
    return {
        key: _expect_nonnegative_integer(
            row[key], f"manifest candidate source count {key}"
        )
        for key in ("model", "fallback", "scripted", "other")
    }


def _source_totals(receipt: dict[str, Any]) -> dict[str, int]:
    return {
        key: sum(row[key] for row in receipt["moveSourceClaims"])
        for key in ("model", "fallback", "scripted", "other")
    }


def validate_source_decision_candidate(
    repo_root: str,
    candidate_dir: str,
    expected_candidate_digest: str,
) -> dict[str, Any]:
    """Validate one candidate and independently re-project its transcript."""

    expected_candidate_digest = _expect_hex(
        expected_candidate_digest, "expected candidate digest"
    )
    files = _read_candidate_directory(repo_root, candidate_dir)
    candidate = _expect_row(
        _canonical_json_file(files["candidate.json"], "candidate.json"),
        CANDIDATE_KEYS,
        "candidate",
    )
    manifest_candidate = _expect_row(
        _canonical_json_file(
            files["manifest-entry-candidate.json"],
            "manifest-entry-candidate.json",
        ),
        MANIFEST_CANDIDATE_KEYS,
        "manifest entry candidate",
    )
    preview = _canonical_json_file(
        files["public-receipt-preview.json"],
        "public-receipt-preview.json",
    )
    _validate_file_rows(candidate, files)

    candidate_digest = _expect_hex(candidate["candidateDigest"], "candidate digest")
    core = dict(candidate)
    del core["candidateDigest"]
    if (
        canonical_digest(core) != candidate_digest
        or candidate_digest != expected_candidate_digest
    ):
        raise SourceDecisionError(
            "candidate digest does not match the exact reviewed candidate"
        )
    candidate_id = candidate.get("candidateId")
    if (
        not isinstance(candidate_id, str)
        or CANDIDATE_ID_RE.fullmatch(candidate_id) is None
    ):
        raise SourceDecisionError("candidate id is malformed")
    if (
        candidate.get("schemaVersion") != "agentwars.publication-candidate.v1"
        or candidate.get("candidateStatus") != "offline_export_verified_candidate_only"
        or candidate.get("sourceContract") != "nymrel_reviewer_case_response_shape.v1"
        or candidate.get("truthBoundary") != EXPECTED_CANDIDATE_TRUTH_BOUNDARY
    ):
        raise SourceDecisionError("candidate status or truth boundary is invalid")

    source_export = _expect_row(
        candidate["sourceExport"], SOURCE_EXPORT_KEYS, "candidate source export"
    )
    for key in ("exactFileSha256", "canonicalPayloadSha256"):
        _expect_hex(source_export[key], f"candidate source export {key}")
    _expect_nonnegative_integer(
        source_export["exactBytes"], "candidate source export bytes", 262_144
    )
    if source_export.get("reviewerAccessClaim") != "authorized_reviewer" or any(
        source_export[key] is not False
        for key in (
            "reviewerExportOriginAttested",
            "reviewerIdentityAttested",
            "serverSignatureVerified",
            "authenticatedTransportVerifiedOffline",
        )
    ):
        raise SourceDecisionError(
            "candidate source export overstates offline origin or identity"
        )

    review = _expect_row(
        candidate["reviewDecisionClaim"],
        REVIEW_DECISION_KEYS,
        "candidate review decision",
    )
    if (
        review.get("status") != "approved"
        or review.get("reasonCode") != "evidence_verified_for_separate_manual_promotion"
        or review.get("publicationDecision") != "reviewer_approved_not_published"
        or review.get("promotionStatus") != "eligible_for_separate_manual_promotion"
    ):
        raise SourceDecisionError(
            "candidate is not an approved but still-unpublished review claim"
        )
    for key in ("decisionReceiptCommitment", "requestCommitment"):
        _expect_hex(review[key], f"candidate review decision {key}")

    bindings = _expect_row(
        candidate["evidenceBindings"],
        EVIDENCE_BINDING_KEYS,
        "candidate evidence bindings",
    )
    for key in EVIDENCE_BINDING_KEYS:
        _expect_hex(bindings[key], f"candidate evidence binding {key}")
    if bindings["engineSha256"] != ENGINE_SHA256:
        raise SourceDecisionError(
            "candidate engine differs from the fixed competition snapshot"
        )

    verification = _expect_row(
        candidate["verification"], VERIFICATION_KEYS, "candidate verification"
    )
    if verification != {
        "builderWarsReplayVerdict": "PASS",
        "builderWarsEffectiveVerdict": "PASS",
        "engineDigestMatch": True,
        "verifierSnapshotMatch": True,
        "crossImplementationProjectionMatch": True,
        "allAcceptedMovesModelClaimed": True,
        "modelAttested": False,
        "publicationManifestUnchanged": True,
        "generatedArtifactUnchanged": True,
    }:
        raise SourceDecisionError(
            "candidate verification state is not the fixed fail-closed shape"
        )
    authorizations = _validate_authorizations(
        candidate["authorizations"], "candidate authorizations"
    )

    if (
        manifest_candidate.get("schemaVersion")
        != "agentwars.publication-manifest-entry-candidate.v1"
        or manifest_candidate.get("candidateId") != candidate_id
        or manifest_candidate.get("candidateStatus") != "source_control_review_required"
        or manifest_candidate.get("sequenceAssignmentRequired") is not True
        or manifest_candidate.get("requiredDecision")
        != "independently_choose_approved_for_publication_or_held"
    ):
        raise SourceDecisionError("manifest entry candidate status is invalid")
    if (
        _validate_authorizations(
            manifest_candidate["authorizations"],
            "manifest candidate authorizations",
        )
        != authorizations
    ):
        raise SourceDecisionError("candidate authority envelopes differ")

    entry = _expect_row(
        manifest_candidate["entryWithoutSequence"],
        ENTRY_WITHOUT_SEQUENCE_KEYS,
        "manifest entry without sequence",
    )
    source_counts = _validate_source_counts(entry["sourceCounts"])
    if (
        entry.get("decision") != "eligible_for_review"
        or entry.get("titleEligible") is not False
    ):
        raise SourceDecisionError(
            "manifest candidate must remain review-eligible and title-ineligible"
        )
    if not isinstance(entry.get("label"), str) or not 1 <= len(entry["label"]) <= 120:
        raise SourceDecisionError("manifest candidate label is invalid")
    source_path = entry.get("sourcePath")
    if (
        not isinstance(source_path, str)
        or source_path != candidate.get("suggestedSourcePath")
        or source_path != manifest_candidate.get("suggestedSourcePath")
    ):
        raise SourceDecisionError("candidate source paths differ")
    source_match = SOURCE_PATH_RE.fullmatch(source_path)
    if source_match is None:
        raise SourceDecisionError(
            "candidate source path is outside the reviewed path contract"
        )

    transcript_sha = sha256_hex(files["transcript.jsonl"])
    if (
        _expect_hex(entry["sourceFileSha256"], "manifest candidate source hash")
        != transcript_sha
        or bindings["transcriptSha256"] != transcript_sha
    ):
        raise SourceDecisionError(
            "candidate transcript hash differs across files and bindings"
        )

    transcript_path = os.path.join(os.path.abspath(candidate_dir), "transcript.jsonl")
    try:
        receipt, _records = project_receipt(transcript_path)
    except (OSError, PublicationError, ValueError) as error:
        raise SourceDecisionError(
            "candidate transcript failed independent BuilderWars replay"
        ) from error
    if canonical_json(preview) != canonical_json(receipt):
        raise SourceDecisionError(
            "candidate public preview differs from independent projection"
        )
    if (
        receipt.get("receiptId") != entry.get("sourceChainHead")
        or receipt.get("receiptId") != bindings["chainHead"]
        or receipt.get("projectionDigest") != bindings["projectionDigest"]
        or receipt.get("transcript", {}).get("sha256") != transcript_sha
        or receipt.get("sourceParity", {}).get("fileSha256") != transcript_sha
        or receipt.get("verification", {}).get("engineDigest")
        != bindings["engineSha256"]
        or receipt.get("verification", {}).get("effectiveVerdict") != "PASS"
        or receipt.get("verification", {}).get("engineDigestMatch") is not True
        or receipt.get("verification", {}).get("verifierSnapshotMatch") is not True
        or receipt.get("truth", {}).get("modelAttested") is not False
        or receipt.get("truth", {}).get("status") != "model_influenced_unattested"
    ):
        raise SourceDecisionError(
            "candidate transcript truth or replay bindings differ"
        )
    totals = _source_totals(receipt)
    if (
        totals != source_counts
        or totals["model"] <= 0
        or any(totals[key] != 0 for key in ("fallback", "scripted", "other"))
    ):
        raise SourceDecisionError(
            "candidate transcript is not entirely self-declared model moves"
        )
    if (
        source_match.group(1) != receipt["game"]["name"]
        or int(source_match.group(2)) != receipt["seed"]
        or source_match.group(4) != receipt["receiptId"]
    ):
        raise SourceDecisionError(
            "candidate source path does not preserve game, seed, and chain head"
        )

    return {
        "candidate": candidate,
        "manifestCandidate": manifest_candidate,
        "receipt": receipt,
        "sourcePath": source_path,
        "sourceCounts": source_counts,
        "transcript": files["transcript.jsonl"],
        "transcriptSha256": transcript_sha,
    }


def _git(repo_root: str, *args: str) -> bytes:
    git_executable = shutil.which("git")
    if git_executable is None:
        raise SourceDecisionError("source repository Git executable is unavailable")
    git_executable = os.path.realpath(git_executable)
    if not os.path.isfile(git_executable) or _is_reparse(git_executable):
        raise SourceDecisionError(
            "source repository Git executable is unavailable or indirect"
        )
    try:
        completed = subprocess.run(
            [git_executable, "-C", repo_root, *args],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise SourceDecisionError(
            "source repository Git state could not be inspected"
        ) from error
    if completed.returncode != 0:
        raise SourceDecisionError("source repository Git state could not be inspected")
    return completed.stdout


def _decode_git_output(value: bytes, label: str) -> str:
    try:
        return value.decode("utf-8", errors="strict")
    except UnicodeError as error:
        raise SourceDecisionError(f"{label} has an invalid encoding") from error


def _git_state(repo_root: str, expected_head: str) -> tuple[str, set[tuple[str, str]]]:
    expected_head = expected_head.lower()
    if re.fullmatch(r"[0-9a-f]{40}", expected_head) is None:
        raise SourceDecisionError(
            "expected source head must be one full lowercase Git SHA"
        )
    resolved_root = os.path.normcase(
        os.path.abspath(
            _decode_git_output(
                _git(repo_root, "rev-parse", "--show-toplevel"),
                "source repository root",
            ).strip()
        )
    )
    if resolved_root != os.path.normcase(os.path.abspath(repo_root)):
        raise SourceDecisionError(
            "source repository root differs from the requested worktree"
        )
    actual_head = (
        _decode_git_output(
            _git(repo_root, "rev-parse", "HEAD"),
            "source repository head",
        )
        .strip()
        .lower()
    )
    if actual_head != expected_head:
        raise SourceDecisionError(
            "source repository HEAD differs from the reviewed commit"
        )
    raw = _git(repo_root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    rows: set[tuple[str, str]] = set()
    for item in raw.split(b"\0"):
        if not item:
            continue
        if len(item) < 4:
            raise SourceDecisionError("source repository status is malformed")
        status = _decode_git_output(item[:2], "source repository status")
        path = _decode_git_output(item[3:], "source repository path").replace("\\", "/")
        rows.add((status, path))
    return actual_head, rows


def _git_common_dir(repo_root: str) -> str:
    root = os.path.abspath(repo_root)
    raw = _decode_git_output(
        _git(root, "rev-parse", "--git-common-dir"),
        "Git common directory",
    ).strip()
    unresolved = (
        os.path.abspath(raw)
        if os.path.isabs(raw)
        else os.path.abspath(os.path.join(root, raw))
    )
    common_dir = os.path.realpath(unresolved)
    if not os.path.isdir(common_dir) or _is_reparse(common_dir):
        raise SourceDecisionError("Git common directory is unavailable or indirect")
    return common_dir


def _git_path_is_ignored(repo_root: str, source_path: str) -> bool:
    git_executable = shutil.which("git")
    if git_executable is None:
        raise SourceDecisionError(
            "candidate source ignore state could not be inspected"
        )
    git_executable = os.path.realpath(git_executable)
    if not os.path.isfile(git_executable) or _is_reparse(git_executable):
        raise SourceDecisionError(
            "candidate source ignore state could not be inspected"
        )
    try:
        completed = subprocess.run(
            [
                git_executable,
                "-C",
                repo_root,
                "check-ignore",
                "--no-index",
                "--quiet",
                "--",
                source_path,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise SourceDecisionError(
            "candidate source ignore state could not be inspected"
        ) from error
    if completed.returncode == 0:
        return True
    if completed.returncode == 1:
        return False
    raise SourceDecisionError("candidate source ignore state could not be inspected")


def _safe_source_target(repo_root: str, source_path: str) -> tuple[str, list[str]]:
    match = SOURCE_PATH_RE.fullmatch(source_path)
    if match is None:
        raise SourceDecisionError(
            "candidate source path is outside the reviewed path contract"
        )
    root = os.path.abspath(repo_root)
    if _is_reparse(root):
        raise SourceDecisionError("source repository root cannot be a reparse point")
    parts = source_path.split("/")
    current = root
    created: list[str] = []
    try:
        for part in parts[:-1]:
            current = os.path.join(current, part)
            if os.path.lexists(current):
                metadata = os.lstat(current)
                if not stat.S_ISDIR(metadata.st_mode) or _is_reparse(current):
                    raise SourceDecisionError(
                        "candidate source path traverses a non-directory or reparse point"
                    )
            else:
                os.mkdir(current)
                created.append(current)
                if _is_reparse(current) or not stat.S_ISDIR(os.lstat(current).st_mode):
                    raise SourceDecisionError(
                        "candidate source directory could not be created safely"
                    )
    except (OSError, SourceDecisionError):
        _remove_empty_created_directories(created)
        raise
    target = os.path.join(root, *parts)
    if os.path.commonpath([root, os.path.abspath(target)]) != root:
        raise SourceDecisionError("candidate source path escapes the repository")
    return target, created


def _remove_empty_created_directories(created: list[str]) -> None:
    for path in reversed(created):
        try:
            if not _is_reparse(path) and not os.listdir(path):
                os.rmdir(path)
        except OSError:
            break


def _write_new_file(path: str, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags, 0o644)
    identity: tuple[int, int] | None = None
    write_error: OSError | None = None
    try:
        metadata = os.fstat(descriptor)
        identity = (metadata.st_dev, metadata.st_ino)
        total = 0
        while total < len(data):
            written = os.write(descriptor, data[total:])
            if written <= 0:
                raise OSError("exclusive write made no progress")
            total += written
        os.fsync(descriptor)
    except OSError as error:
        write_error = error
    finally:
        try:
            os.close(descriptor)
        except OSError as error:
            write_error = write_error or error
    if write_error is not None:
        try:
            current = os.lstat(path)
            if (
                identity is not None
                and not _is_reparse(path)
                and (current.st_dev, current.st_ino) == identity
                and stat.S_ISREG(current.st_mode)
            ):
                os.unlink(path)
        except OSError:
            pass
        raise write_error


def _atomic_replace(path: str, data: bytes) -> None:
    directory = os.path.dirname(path)
    original_mode = stat.S_IMODE(os.stat(path, follow_symlinks=False).st_mode)
    descriptor, temporary = tempfile.mkstemp(
        prefix=".agentwars-manifest-", dir=directory
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, original_mode)
        os.replace(temporary, path)
    finally:
        if os.path.lexists(temporary) and not _is_reparse(temporary):
            try:
                os.unlink(temporary)
            except OSError:
                pass


def _validate_label(label: str) -> str:
    if (
        not isinstance(label, str)
        or not 1 <= len(label) <= 120
        or label != label.strip()
        or any(ord(character) < 32 or ord(character) == 127 for character in label)
    ):
        raise SourceDecisionError(
            "source decision label must be 1-120 printable trimmed characters"
        )
    return label


def _manifest_entry(
    *,
    sequence: int,
    source_path: str,
    source_sha256: str,
    chain_head: str,
    source_counts: dict[str, int],
    decision: str,
    label: str,
) -> dict[str, Any]:
    return {
        "decision": decision,
        "label": label,
        "sequence": sequence,
        "sourceChainHead": chain_head,
        "sourceCounts": source_counts,
        "sourceFileSha256": source_sha256,
        "sourcePath": source_path,
        "titleEligible": False,
    }


def inspect_source_decision_state(repo_root: str) -> dict[str, Any]:
    """Return the non-secret immutable inputs required by the apply command."""

    root = os.path.abspath(repo_root)
    manifest_path = os.path.join(root, "docs", "AGENTWARS_PUBLICATION_MANIFEST.v1.json")
    artifact_path = os.path.join(root, "publishing", "agentwars-public-v1")
    if not os.path.isfile(manifest_path) or _is_reparse(manifest_path):
        raise SourceDecisionError("publication manifest is unavailable or indirect")
    head = (
        _decode_git_output(
            _git(root, "rev-parse", "HEAD"),
            "source repository head",
        )
        .strip()
        .lower()
    )
    _actual_head, status_rows = _git_state(root, head)
    lock_path = os.path.join(_git_common_dir(root), "agentwars-source-decision.lock")
    try:
        publication = load_publication_manifest(root, manifest_path)
    except PublicationError as error:
        raise SourceDecisionError("publication manifest failed validation") from error
    return {
        "status": "protected_source_state",
        "sourceHead": head,
        "worktreeClean": not status_rows,
        "dirtyEntryCount": len(status_rows),
        "publicationManifestSha256": sha256_hex(Path(manifest_path).read_bytes()),
        "generatedArtifactTreeDigest": _tree_digest(artifact_path),
        "publicationEntryCount": len(publication["entries"]),
        "sourceDecisionLockPresent": os.path.lexists(lock_path),
        "publicArtifactMutationAuthorized": False,
        "deploymentAuthorized": False,
    }


@contextmanager
def _source_decision_lock(repo_root: str) -> Iterator[None]:
    """Serialize source decisions across every worktree of one Git repository."""

    root = os.path.abspath(repo_root)
    common_dir = _git_common_dir(root)
    lock_path = os.path.join(common_dir, "agentwars-source-decision.lock")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(lock_path, flags, 0o600)
    except FileExistsError as error:
        raise SourceDecisionError(
            "another AgentWars source decision holds the repository lock"
        ) from error
    except OSError as error:
        raise SourceDecisionError(
            "AgentWars source-decision lock could not be acquired"
        ) from error
    identity: tuple[int, int] | None = None
    initialization_error: OSError | None = None
    try:
        metadata = os.fstat(descriptor)
        identity = (metadata.st_dev, metadata.st_ino)
        marker = (
            canonical_json(
                {
                    "pid": os.getpid(),
                    "schemaVersion": "agentwars.source-decision-lock.v1",
                }
            )
            + "\n"
        ).encode("utf-8")
        total = 0
        while total < len(marker):
            written = os.write(descriptor, marker[total:])
            if written <= 0:
                raise OSError("lock write made no progress")
            total += written
        os.fsync(descriptor)
    except OSError as error:
        initialization_error = error
    finally:
        try:
            os.close(descriptor)
        except OSError as error:
            initialization_error = initialization_error or error
    if initialization_error is not None:
        try:
            current = os.lstat(lock_path)
            if (
                identity is not None
                and not _is_reparse(lock_path)
                and (current.st_dev, current.st_ino) == identity
                and stat.S_ISREG(current.st_mode)
            ):
                os.unlink(lock_path)
        except OSError:
            pass
        raise SourceDecisionError(
            "AgentWars source-decision lock could not be initialized"
        ) from initialization_error
    try:
        yield
    finally:
        try:
            current = os.lstat(lock_path)
            if (
                identity is None
                or _is_reparse(lock_path)
                or (current.st_dev, current.st_ino) != identity
                or not stat.S_ISREG(current.st_mode)
            ):
                raise SourceDecisionError(
                    "AgentWars source-decision lock identity changed"
                )
            os.unlink(lock_path)
        except SourceDecisionError:
            raise
        except OSError as error:
            raise SourceDecisionError(
                "AgentWars source-decision lock could not be released"
            ) from error


def _apply_source_decision_locked(
    repo_root: str,
    candidate_dir: str,
    *,
    expected_candidate_digest: str,
    expected_head: str,
    expected_manifest_sha256: str,
    expected_generated_tree_digest: str,
    decision: str,
    label: str,
) -> dict[str, Any]:
    """Stage one transcript and one explicit source manifest decision.

    The caller must separately review and commit these bytes.  Generated public
    artifacts are protected and must remain byte-identical.
    """

    root = os.path.abspath(repo_root)
    if decision not in ("approved_for_publication", "held"):
        raise SourceDecisionError(
            "source decision must be approved_for_publication or held"
        )
    label = _validate_label(label)
    expected_manifest_sha256 = _expect_hex(
        expected_manifest_sha256, "expected manifest sha256"
    )
    expected_generated_tree_digest = _expect_hex(
        expected_generated_tree_digest,
        "expected generated artifact tree digest",
    )
    validated = validate_source_decision_candidate(
        root, candidate_dir, expected_candidate_digest
    )
    manifest_path = os.path.join(root, "docs", "AGENTWARS_PUBLICATION_MANIFEST.v1.json")
    artifact_path = os.path.join(root, "publishing", "agentwars-public-v1")
    if not os.path.isfile(manifest_path) or _is_reparse(manifest_path):
        raise SourceDecisionError("publication manifest is unavailable or indirect")
    manifest_before_bytes = Path(manifest_path).read_bytes()
    manifest_before_sha = sha256_hex(manifest_before_bytes)
    if manifest_before_sha != expected_manifest_sha256:
        raise SourceDecisionError(
            "publication manifest differs from the reviewed bytes"
        )
    artifact_before = _tree_digest(artifact_path)
    if artifact_before != expected_generated_tree_digest:
        raise SourceDecisionError(
            "generated public artifact tree differs from the reviewed bytes"
        )
    try:
        manifest_payload = _parse_strict_json(
            manifest_before_bytes.decode("utf-8"),
            "publication manifest",
        )
        publication = load_publication_manifest(root, manifest_path)
    except (UnicodeDecodeError, PromotionCandidateError, PublicationError) as error:
        raise SourceDecisionError(
            "publication manifest failed strict validation"
        ) from error
    if not isinstance(manifest_payload, dict):
        raise SourceDecisionError("publication manifest root is invalid")

    source_path = validated["sourcePath"]
    source_sha = validated["transcriptSha256"]
    chain_head = validated["receipt"]["receiptId"]
    matching = [
        row
        for row in publication["entries"]
        if row["sourcePath"] == source_path
        or row["sourceFileSha256"] == source_sha
        or row["sourceChainHead"] == chain_head
    ]
    next_sequence = len(publication["entries"])
    intended = _manifest_entry(
        sequence=next_sequence,
        source_path=source_path,
        source_sha256=source_sha,
        chain_head=chain_head,
        source_counts=validated["sourceCounts"],
        decision=decision,
        label=label,
    )
    already_decided = False
    if matching:
        if len(matching) != 1:
            raise SourceDecisionError(
                "publication manifest contains conflicting candidate identities"
            )
        existing = {
            key: value
            for key, value in matching[0].items()
            if key != "absoluteSourcePath"
        }
        intended["sequence"] = existing.get("sequence")
        if existing != intended:
            raise SourceDecisionError(
                "publication manifest already binds this candidate differently"
            )
        already_decided = True

    target = os.path.join(root, *source_path.split("/"))
    source_exists = os.path.lexists(target)
    if source_exists:
        if _is_reparse(target) or not stat.S_ISREG(os.lstat(target).st_mode):
            raise SourceDecisionError(
                "candidate source target exists but is not one direct regular file"
            )
        if Path(target).read_bytes() != validated["transcript"]:
            raise SourceDecisionError(
                "candidate source target exists with different bytes"
            )

    actual_head, status_rows = _git_state(root, expected_head)
    if _git_path_is_ignored(root, source_path):
        raise SourceDecisionError(
            "candidate source path is ignored by repository policy"
        )
    allowed_status: set[tuple[str, str]] = set()
    if source_exists:
        allowed_status.add(("??", source_path))
    if already_decided:
        allowed_status.add((" M", "docs/AGENTWARS_PUBLICATION_MANIFEST.v1.json"))
        allowed_status.add(("M ", "docs/AGENTWARS_PUBLICATION_MANIFEST.v1.json"))
    if status_rows - allowed_status:
        raise SourceDecisionError(
            "source repository contains unrelated or contradictory changes"
        )
    if not source_exists and any(path == source_path for _status, path in status_rows):
        raise SourceDecisionError("candidate source Git state is contradictory")
    if already_decided:
        if not source_exists:
            raise SourceDecisionError(
                "publication decision exists without its exact source transcript"
            )
        if _tree_digest(artifact_path) != artifact_before:
            raise SourceDecisionError(
                "generated public artifact changed during idempotent verification"
            )
        return {
            "status": "source_decision_already_staged_not_built",
            "candidateId": validated["candidate"]["candidateId"],
            "candidateDigest": validated["candidate"]["candidateDigest"],
            "decision": decision,
            "label": label,
            "sequence": intended["sequence"],
            "sourcePath": source_path,
            "sourceFileSha256": source_sha,
            "receiptId": chain_head,
            "expectedSourceCommit": actual_head,
            "manifestSha256": manifest_before_sha,
            "generatedArtifactTreeDigest": artifact_before,
            "titleEligible": False,
            "publicArtifactBuilt": False,
            "deployed": False,
            "rankingAuthorized": False,
            "providerOrModelAttested": False,
        }

    created_directories: list[str] = []
    source_created = False
    try:
        if not source_exists:
            target, created_directories = _safe_source_target(root, source_path)
            _write_new_file(target, validated["transcript"])
            source_created = True
        if Path(target).read_bytes() != validated["transcript"]:
            raise SourceDecisionError(
                "candidate source bytes changed before manifest staging"
            )
        if Path(manifest_path).read_bytes() != manifest_before_bytes:
            raise SourceDecisionError(
                "publication manifest changed during source staging"
            )
        if _tree_digest(artifact_path) != artifact_before:
            raise SourceDecisionError(
                "generated public artifact changed during source staging"
            )
        manifest_payload["entries"].append(intended)
        new_manifest_bytes = (
            json.dumps(manifest_payload, indent=2, ensure_ascii=True) + "\n"
        ).encode("utf-8")

        descriptor, temporary_manifest = tempfile.mkstemp(
            prefix=".agentwars-source-decision-validate-",
            suffix=".json",
            dir=os.path.dirname(manifest_path),
        )
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(new_manifest_bytes)
                handle.flush()
                os.fsync(handle.fileno())
            load_publication_manifest(root, temporary_manifest)
        except (PublicationError, OSError) as error:
            raise SourceDecisionError(
                "staged publication manifest failed validation"
            ) from error
        finally:
            if os.path.lexists(temporary_manifest) and not _is_reparse(
                temporary_manifest
            ):
                os.unlink(temporary_manifest)

        if Path(manifest_path).read_bytes() != manifest_before_bytes:
            raise SourceDecisionError(
                "publication manifest changed before atomic install"
            )
        _atomic_replace(manifest_path, new_manifest_bytes)
        if _tree_digest(artifact_path) != artifact_before:
            raise SourceDecisionError(
                "generated public artifact changed after source decision"
            )
        _post_head, post_status_rows = _git_state(root, expected_head)
        expected_status_rows = {(" M", "docs/AGENTWARS_PUBLICATION_MANIFEST.v1.json")}
        if source_created or ("??", source_path) in status_rows:
            expected_status_rows.add(("??", source_path))
        if post_status_rows != expected_status_rows:
            raise SourceDecisionError(
                "staged source decision produced an unexpected Git status"
            )
    except Exception:
        if source_created and Path(manifest_path).read_bytes() == manifest_before_bytes:
            try:
                if (
                    not _is_reparse(target)
                    and Path(target).read_bytes() == validated["transcript"]
                ):
                    os.unlink(target)
                    _remove_empty_created_directories(created_directories)
            except OSError:
                pass
        raise

    manifest_after_sha = sha256_hex(Path(manifest_path).read_bytes())
    return {
        "status": "source_decision_staged_not_built",
        "candidateId": validated["candidate"]["candidateId"],
        "candidateDigest": validated["candidate"]["candidateDigest"],
        "decision": decision,
        "label": label,
        "sequence": intended["sequence"],
        "sourcePath": source_path,
        "sourceFileSha256": source_sha,
        "receiptId": chain_head,
        "expectedSourceCommit": actual_head,
        "manifestSha256Before": manifest_before_sha,
        "manifestSha256After": manifest_after_sha,
        "generatedArtifactTreeDigest": artifact_before,
        "titleEligible": False,
        "publicArtifactBuilt": False,
        "deployed": False,
        "rankingAuthorized": False,
        "providerOrModelAttested": False,
    }


def apply_source_decision(
    repo_root: str,
    candidate_dir: str,
    *,
    expected_candidate_digest: str,
    expected_head: str,
    expected_manifest_sha256: str,
    expected_generated_tree_digest: str,
    decision: str,
    label: str,
) -> dict[str, Any]:
    """Serialize and safely stage one source-only promotion decision."""

    root = os.path.abspath(repo_root)
    with _source_decision_lock(root):
        try:
            return _apply_source_decision_locked(
                root,
                candidate_dir,
                expected_candidate_digest=expected_candidate_digest,
                expected_head=expected_head,
                expected_manifest_sha256=expected_manifest_sha256,
                expected_generated_tree_digest=expected_generated_tree_digest,
                decision=decision,
                label=label,
            )
        except SourceDecisionError:
            raise
        except (
            OSError,
            UnicodeError,
            PublicationError,
            PromotionCandidateError,
            subprocess.SubprocessError,
        ) as error:
            raise SourceDecisionError(
                "source decision failed safely at the local verification boundary"
            ) from error
