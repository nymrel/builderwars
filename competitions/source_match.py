"""Customer-local source-match preparation for one private AgentWars job.

The preparation step is intentionally non-executing. It validates a signed,
non-leasing server response, the current fixed fantasy harness, optional signed
Agent Passports, and customer-selected output paths, then writes one immutable
local launch plan. It does not call a provider, launch a subprocess, acquire a
competition attempt, upload evidence, publish, or rank a result.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path

from arena.canonical import digest
from arena.passport import PassportError, loads as load_passport
from competitions.evidence_job import (
    COMPETITION_JOB_PROTOCOL,
    FALSE_ATTESTATIONS,
    CompetitionPreparation,
    competition_job_commitment_sha256,
)
from provider_hub.local_runner import (
    RunnerClientError,
    digest_harness_file,
    validate_fingerprint,
    validate_runner_id,
)


SOURCE_MATCH_PLAN_SCHEMA = "agentwars.source_match_plan.v1"
SOURCE_MATCH_ENTRYPOINT = "bin/run_agentwars_cross_provider_match.py"
MAX_SOURCE_MATCH_PLAN_BYTES = 64 * 1024

ROOT = Path(__file__).resolve().parent.parent
MATCH_RUNNER_PATH = ROOT / "bin" / "run_agentwars_cross_provider_match.py"
FANTASY_HARNESS_PATH = ROOT / "entrants" / "fantasy_model_harness.py"


def build_source_match_plan(
    preparation: CompetitionPreparation,
    *,
    profile: dict,
    plan_path: str,
    match_directory: str,
    summary_path: str,
    passport_paths: tuple[str, str] | None,
    backend_timeout: float,
) -> dict:
    """Build one exact, local-only plan after all pre-spend checks pass."""

    if not isinstance(preparation, CompetitionPreparation):
        raise RunnerClientError("source-match preparation response is invalid")
    if not isinstance(profile, dict):
        raise RunnerClientError("source-match runner profile is invalid")
    runner_id = validate_runner_id(profile.get("runnerId"))
    fingerprint = validate_fingerprint(profile.get("fingerprint"))
    job = preparation.job
    if profile.get("harnessId") != job.required_harness_id:
        raise RunnerClientError("source-match plan changed the paired harness id")
    paired_digest = profile.get("harnessDigest")
    if not isinstance(paired_digest, str) or not hmac.compare_digest(
        paired_digest, job.required_harness_digest
    ):
        raise RunnerClientError("source-match plan changed the paired harness digest")

    current_harness_digest = digest_harness_file(str(FANTASY_HARNESS_PATH))
    if not hmac.compare_digest(current_harness_digest, job.required_harness_digest):
        raise RunnerClientError(
            "the current fixed fantasy harness differs from the paired job"
        )
    runner_sha256 = _regular_file_sha256(MATCH_RUNNER_PATH, "source-match runner")

    plan_file = _new_output_path(plan_path, "source-match plan")
    match_root = _new_output_path(match_directory, "source-match directory")
    summary_file = _new_output_path(summary_path, "source-match summary")
    _require_disjoint_outputs(plan_file, match_root, summary_file)
    timeout = _backend_timeout(backend_timeout)

    signed_expected = all(seat.agent_id is not None for seat in job.seats)
    if signed_expected != (passport_paths is not None):
        raise RunnerClientError(
            "source-match passport files must exactly match the job's two-seat binding"
        )
    passports = [None, None]
    passport_digests = [None, None]
    normalized_passport_paths = [None, None]
    if passport_paths is not None:
        if (
            not isinstance(passport_paths, tuple)
            or len(passport_paths) != 2
            or passport_paths[0] == passport_paths[1]
        ):
            raise RunnerClientError("source-match requires two distinct passport files")
        for seat_number, raw_path in enumerate(passport_paths):
            normalized_path, raw, passport = _read_passport(raw_path)
            assigned = job.seats[seat_number]
            if (
                passport["agentId"] != assigned.agent_id
                or passport["versionId"] != assigned.version_id
                or passport["displayName"] != assigned.entrant
                or passport["claimedModel"] != assigned.backend_claim
                or passport["harnessSha256"] != job.required_harness_digest
            ):
                raise RunnerClientError(
                    f"source-match passport {seat_number} differs from its assigned agent version"
                )
            passports[seat_number] = passport
            passport_digests[seat_number] = hashlib.sha256(raw).hexdigest()
            normalized_passport_paths[seat_number] = str(normalized_path)

    launch_argv: list[str] = []
    seats = []
    for seat_number, assigned in enumerate(job.seats):
        prefix = f"--seat{seat_number}"
        launch_argv.extend(
            (
                f"{prefix}-provider={assigned.provider_claim}",
                f"{prefix}-name={assigned.entrant}",
                f"{prefix}-strategy={assigned.strategy}",
            )
        )
        if assigned.selected_model_claim is not None:
            launch_argv.append(f"{prefix}-model={assigned.selected_model_claim}")
        if assigned.variant_claim is not None:
            launch_argv.append(f"{prefix}-variant={assigned.variant_claim}")
        seats.append(
            {
                "seat": seat_number,
                "entrant": assigned.entrant,
                "providerClaim": assigned.provider_claim,
                "selectedModelClaim": assigned.selected_model_claim,
                "variantClaim": assigned.variant_claim,
                "backendClaim": assigned.backend_claim,
                "strategy": assigned.strategy,
                "agentId": assigned.agent_id,
                "versionId": assigned.version_id,
                "passportSha256": passport_digests[seat_number],
            }
        )
    launch_argv.extend(
        (
            f"--game={job.game}",
            f"--seed={job.seed}",
            f"--backend-timeout={_timeout_text(timeout)}",
            f"--out={match_root}",
            f"--json-out={summary_file}",
        )
    )
    if signed_expected:
        launch_argv.extend(
            (
                "--agent-passports",
                str(normalized_passport_paths[0]),
                str(normalized_passport_paths[1]),
            )
        )

    core = {
        "schemaVersion": SOURCE_MATCH_PLAN_SCHEMA,
        "protocolVersion": COMPETITION_JOB_PROTOCOL,
        "sourceStatus": "ready",
        "runnerId": runner_id,
        "fingerprint": fingerprint,
        "jobId": job.job_id,
        "competitionId": job.competition_id,
        "jobCommitmentSha256": competition_job_commitment_sha256(job),
        "engineSha256": job.engine_sha256,
        "requiredHarnessId": job.required_harness_id,
        "requiredHarnessDigest": job.required_harness_digest,
        "matchRunnerSha256": runner_sha256,
        "game": job.game,
        "seed": job.seed,
        "seats": seats,
        "requireSignedPassports": job.require_signed_passports,
        "signedPassportsBound": signed_expected,
        "launch": {
            "entrypoint": SOURCE_MATCH_ENTRYPOINT,
            "argv": launch_argv,
            "matchDirectory": str(match_root),
            "summaryFile": str(summary_file),
            "backendTimeoutMilliseconds": int(round(timeout * 1_000)),
            "requiredFreshConsentFlags": [
                "--customer-local-v1",
                "--provider-usage-v1",
            ],
        },
        "publicationDecision": "not_reviewed_not_published",
        "rankingEligible": False,
        "providerExecutionRequested": False,
        "subprocessExecutionRequested": False,
        **{field: False for field in FALSE_ATTESTATIONS},
    }
    return {**core, "launchPlanDigest": digest(core)}


def write_source_match_plan(path: str, plan: dict) -> Path:
    """Exclusively commit one validated human-readable plan to local storage."""

    if not isinstance(plan, dict) or not isinstance(plan.get("launchPlanDigest"), str):
        raise RunnerClientError("source-match plan has an invalid exact body")
    core = {key: value for key, value in plan.items() if key != "launchPlanDigest"}
    if not hmac.compare_digest(plan["launchPlanDigest"], digest(core)):
        raise RunnerClientError("source-match plan digest is invalid")
    target = _new_output_path(path, "source-match plan")
    raw = (
        json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    if len(raw) > MAX_SOURCE_MATCH_PLAN_BYTES:
        raise RunnerClientError("source-match plan is oversized")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise RunnerClientError(
            "source-match plan directory could not be created"
        ) from error
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    descriptor = None
    created = False
    try:
        descriptor = os.open(target, flags, 0o600)
        created = True
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.chmod(target, 0o600)
        except OSError:
            pass
        _fsync_directory(target.parent)
    except BaseException as error:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if created:
            try:
                target.unlink()
            except OSError:
                pass
        if isinstance(error, OSError):
            raise RunnerClientError("source-match plan could not be written") from error
        raise
    return target


def _read_passport(value: str) -> tuple[Path, bytes, dict]:
    path = Path(value) if isinstance(value, str) else Path()
    if (
        not isinstance(value, str)
        or not value
        or path.is_symlink()
        or not path.is_file()
    ):
        raise RunnerClientError(
            "source-match passport must be one regular non-symlink file"
        )
    path = Path(os.path.realpath(os.path.abspath(path)))
    try:
        with path.open("rb") as handle:
            raw = handle.read(64 * 1024 + 1)
    except OSError as error:
        raise RunnerClientError("source-match passport could not be read") from error
    if not raw or len(raw) > 64 * 1024:
        raise RunnerClientError("source-match passport is empty or oversized")
    try:
        passport = load_passport(raw.decode("utf-8", errors="strict"))
    except (UnicodeError, PassportError) as error:
        raise RunnerClientError(
            "source-match passport fails offline verification"
        ) from error
    return path, raw, passport


def _regular_file_sha256(path: Path, label: str) -> str:
    if path.is_symlink() or not path.is_file():
        raise RunnerClientError(f"{label} must be one regular non-symlink file")
    sha = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(64 * 1024), b""):
                sha.update(block)
    except OSError as error:
        raise RunnerClientError(f"{label} could not be read") from error
    return sha.hexdigest()


def _new_output_path(value: str, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise RunnerClientError(f"{label} path is invalid")
    path = Path(os.path.realpath(os.path.abspath(value)))
    if os.path.lexists(path):
        raise RunnerClientError(f"{label} already exists")
    return path


def _require_disjoint_outputs(plan: Path, match_root: Path, summary: Path) -> None:
    normalized = [os.path.normcase(str(path)) for path in (plan, match_root, summary)]
    if len(set(normalized)) != 3:
        raise RunnerClientError("source-match output paths must differ")
    for left, right in ((plan, match_root), (plan, summary), (match_root, summary)):
        try:
            common = Path(os.path.commonpath((left, right)))
        except ValueError:
            continue
        if os.path.normcase(str(common)) in (
            os.path.normcase(str(left)),
            os.path.normcase(str(right)),
        ):
            raise RunnerClientError("source-match output paths must not be nested")


def _backend_timeout(value: float) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not 10 <= value <= 900
    ):
        raise RunnerClientError(
            "source-match provider timeout must be from 10 to 900 seconds"
        )
    return float(format(float(value), ".3f"))


def _timeout_text(value: float) -> str:
    return format(value, ".3f").rstrip("0").rstrip(".")


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = None
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
