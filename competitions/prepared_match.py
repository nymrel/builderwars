"""Strict customer-local execution of one prepared AgentWars source match.

The plan is data, never a command. This module rejects unknown fields, rebuilds
the complete fixed argv, re-hashes the current runner, harness, and public Agent
Passports, requires new output paths, and only then calls the repository's
fixed cross-provider runner with fresh customer/provider consent.
"""

from __future__ import annotations

import base64
import dataclasses
import hashlib
import hmac
import json
import os
import re
import sys
from pathlib import Path

from arena.canonical import digest
from arena.passport import PassportError, loads as load_passport
from competitions.evidence_job import (
    COMPETITION_JOB_MAX_ATTEMPTS,
    COMPETITION_JOB_PROTOCOL,
    COMPETITION_PUBLICATION_MODE,
    COMPETITION_REQUIRED_TRUTH_STATUS,
    FALSE_ATTESTATIONS,
    FANTASY_GAMES,
    STRATEGIES,
    SUPPORTED_PROVIDERS,
    CompetitionJob,
    CompetitionSeat,
    competition_job_commitment_sha256,
)
from competitions.source_match import (
    FANTASY_HARNESS_PATH,
    MATCH_RUNNER_PATH,
    MAX_SOURCE_MATCH_PLAN_BYTES,
    SOURCE_MATCH_ENTRYPOINT,
    SOURCE_MATCH_PLAN_SCHEMA,
)
from provider_hub.catalog import get_provider
from provider_hub.local_runner import (
    RunnerClientError,
    validate_fingerprint,
    validate_runner_id,
)
from provider_hub.secrets import SecretValue


BIN = str(MATCH_RUNNER_PATH.parent)
if BIN not in sys.path:
    sys.path.insert(0, BIN)

from run_agentwars_cross_provider_match import main as _fixed_match_main  # noqa: E402


FIXED_SOURCE_MATCH_HARNESS_ID = "agentwars-cli"
FRESH_EXECUTION_FLAGS = ("--customer-local-v1", "--provider-usage-v1")

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_PROVIDER_OPTION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+@-]{0,239}$")

_PLAN_KEYS = frozenset(
    {
        "schemaVersion",
        "protocolVersion",
        "sourceStatus",
        "runnerId",
        "fingerprint",
        "jobId",
        "competitionId",
        "jobCommitmentSha256",
        "engineSha256",
        "requiredHarnessId",
        "requiredHarnessDigest",
        "matchRunnerSha256",
        "game",
        "seed",
        "seats",
        "requireSignedPassports",
        "signedPassportsBound",
        "launch",
        "publicationDecision",
        "rankingEligible",
        "providerExecutionRequested",
        "subprocessExecutionRequested",
        "launchPlanDigest",
        *FALSE_ATTESTATIONS,
    }
)
_LAUNCH_KEYS = frozenset(
    {
        "entrypoint",
        "argv",
        "matchDirectory",
        "summaryFile",
        "backendTimeoutMilliseconds",
        "requiredFreshConsentFlags",
    }
)
_SEAT_KEYS = frozenset(
    {
        "seat",
        "entrant",
        "providerClaim",
        "selectedModelClaim",
        "variantClaim",
        "backendClaim",
        "strategy",
        "agentId",
        "versionId",
        "passportSha256",
    }
)


@dataclasses.dataclass(frozen=True)
class PreparedMatch:
    plan_path: Path
    job_id: str
    competition_id: str
    launch_plan_digest: str
    provider_ids: tuple[str, str]
    argv: tuple[str, ...]
    match_directory: Path
    summary_file: Path


def load_prepared_match(path: str) -> PreparedMatch:
    """Read and revalidate one immutable local source-match plan."""

    plan_path, raw = _read_regular_file(
        path, MAX_SOURCE_MATCH_PLAN_BYTES, "prepared match plan"
    )
    try:
        plan = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_float=_reject_number,
            parse_constant=_reject_number,
        )
    except (UnicodeError, ValueError, RecursionError) as error:
        raise RunnerClientError("prepared match plan is not strict JSON") from error
    _exact_dict(plan, _PLAN_KEYS, "prepared match plan")
    launch_digest = _hex_digest(plan["launchPlanDigest"], "launch plan digest")
    core = {key: value for key, value in plan.items() if key != "launchPlanDigest"}
    if not hmac.compare_digest(launch_digest, digest(core)):
        raise RunnerClientError("prepared match launch plan digest is invalid")

    if (
        plan["schemaVersion"] != SOURCE_MATCH_PLAN_SCHEMA
        or plan["protocolVersion"] != COMPETITION_JOB_PROTOCOL
        or plan["sourceStatus"] != "ready"
    ):
        raise RunnerClientError("prepared match protocol is unsupported")
    validate_runner_id(plan["runnerId"])
    validate_fingerprint(plan["fingerprint"])
    job_id = _canonical_token(plan["jobId"], "awj1_", "prepared match job id")
    competition_id = _canonical_token(
        plan["competitionId"], "awc1_", "prepared match competition id"
    )
    engine_sha256 = _hex_digest(plan["engineSha256"], "prepared match engine")
    from competitions.evidence_job import COMPETITION_ENGINE_SHA256

    if not hmac.compare_digest(engine_sha256, COMPETITION_ENGINE_SHA256):
        raise RunnerClientError("prepared match engine snapshot is not current")
    if plan["requiredHarnessId"] != FIXED_SOURCE_MATCH_HARNESS_ID:
        raise RunnerClientError(
            "prepared match harness id is not the fixed beta harness"
        )
    harness_digest = _hex_digest(
        plan["requiredHarnessDigest"], "prepared match harness digest"
    )
    current_harness_digest = _regular_file_sha256(
        FANTASY_HARNESS_PATH, "prepared match harness"
    )
    if not hmac.compare_digest(harness_digest, current_harness_digest):
        raise RunnerClientError("prepared match harness bytes changed")
    runner_digest = _hex_digest(
        plan["matchRunnerSha256"], "prepared match runner digest"
    )
    current_runner_digest = _regular_file_sha256(
        MATCH_RUNNER_PATH, "prepared match runner"
    )
    if not hmac.compare_digest(runner_digest, current_runner_digest):
        raise RunnerClientError("prepared match fixed runner bytes changed")

    game = plan["game"]
    if game not in FANTASY_GAMES:
        raise RunnerClientError("prepared match game is unsupported")
    seed = _integer(plan["seed"], "prepared match seed", 0, 2_147_483_647)
    if not isinstance(plan["seats"], list) or len(plan["seats"]) != 2:
        raise RunnerClientError("prepared match requires exactly two seats")
    seats = tuple(
        _validate_seat(value, expected_seat=index)
        for index, value in enumerate(plan["seats"])
    )
    if seats[0].provider_claim == seats[1].provider_claim:
        raise RunnerClientError("prepared match provider claims must differ")
    if seats[0].entrant.casefold() == seats[1].entrant.casefold():
        raise RunnerClientError("prepared match entrant names must differ")

    require_signed = _exact_bool(
        plan["requireSignedPassports"], "prepared match passport requirement"
    )
    signed_bound = _exact_bool(
        plan["signedPassportsBound"], "prepared match passport binding"
    )
    seat_signed = all(
        seat.agent_id is not None
        and seat.version_id is not None
        and seat.passport_sha256 is not None
        for seat in seats
    )
    seat_unsigned = all(
        seat.agent_id is None
        and seat.version_id is None
        and seat.passport_sha256 is None
        for seat in seats
    )
    if not (seat_signed or seat_unsigned):
        raise RunnerClientError("prepared match passport bindings are partial")
    if require_signed is not seat_signed or signed_bound is not seat_signed:
        raise RunnerClientError("prepared match passport policy is contradictory")

    job = CompetitionJob(
        job_id=job_id,
        competition_id=competition_id,
        required_harness_id=plan["requiredHarnessId"],
        required_harness_digest=harness_digest,
        game=game,
        seed=seed,
        engine_sha256=engine_sha256,
        seats=tuple(seat.job_seat for seat in seats),
        require_signed_passports=require_signed,
        required_truth_status=COMPETITION_REQUIRED_TRUTH_STATUS,
        publication_mode=COMPETITION_PUBLICATION_MODE,
        max_attempts=COMPETITION_JOB_MAX_ATTEMPTS,
    )
    job_commitment = _hex_digest(
        plan["jobCommitmentSha256"], "prepared match job commitment"
    )
    if not hmac.compare_digest(job_commitment, competition_job_commitment_sha256(job)):
        raise RunnerClientError("prepared match job commitment is invalid")

    launch = _exact_dict(plan["launch"], _LAUNCH_KEYS, "prepared match launch")
    if launch["entrypoint"] != SOURCE_MATCH_ENTRYPOINT:
        raise RunnerClientError("prepared match entrypoint is not the fixed runner")
    timeout_ms = _integer(
        launch["backendTimeoutMilliseconds"],
        "prepared match provider timeout",
        10_000,
        900_000,
    )
    if launch["requiredFreshConsentFlags"] != list(FRESH_EXECUTION_FLAGS):
        raise RunnerClientError("prepared match fresh consent flags changed")
    match_directory = _new_output_path(
        launch["matchDirectory"], "prepared match directory"
    )
    summary_file = _new_output_path(launch["summaryFile"], "prepared match summary")
    _require_disjoint_paths(plan_path, match_directory, summary_file)

    argv = launch["argv"]
    if (
        not isinstance(argv, list)
        or not argv
        or any(
            not isinstance(value, str) or not value or "\x00" in value for value in argv
        )
    ):
        raise RunnerClientError("prepared match argv is invalid")
    base_argv = _expected_base_argv(
        seats=seats,
        game=game,
        seed=seed,
        timeout_ms=timeout_ms,
        match_directory=match_directory,
        summary_file=summary_file,
    )
    passport_paths: tuple[str, str] | None = None
    if seat_signed:
        if len(argv) != len(base_argv) + 3 or argv[-3] != "--agent-passports":
            raise RunnerClientError("prepared match signed passport argv is invalid")
        passport_paths = (argv[-2], argv[-1])
        if os.path.normcase(passport_paths[0]) == os.path.normcase(passport_paths[1]):
            raise RunnerClientError("prepared match passport files must differ")
        expected_argv = [*base_argv, "--agent-passports", *passport_paths]
    else:
        expected_argv = base_argv
    if argv != expected_argv or any(flag in argv for flag in FRESH_EXECUTION_FLAGS):
        raise RunnerClientError("prepared match argv does not match fixed plan data")
    if passport_paths is not None:
        for seat, passport_path in zip(seats, passport_paths, strict=True):
            _verify_passport_file(
                passport_path, seat=seat, harness_digest=harness_digest
            )

    if (
        plan["publicationDecision"] != "not_reviewed_not_published"
        or plan["rankingEligible"] is not False
        or plan["providerExecutionRequested"] is not False
        or plan["subprocessExecutionRequested"] is not False
        or any(plan[field] is not False for field in FALSE_ATTESTATIONS)
    ):
        raise RunnerClientError(
            "prepared match plan overstates execution or release status"
        )

    return PreparedMatch(
        plan_path=plan_path,
        job_id=job_id,
        competition_id=competition_id,
        launch_plan_digest=launch_digest,
        provider_ids=tuple(seat.provider_claim for seat in seats),
        argv=tuple(argv),
        match_directory=match_directory,
        summary_file=summary_file,
    )


def execute_prepared_match(
    path: str,
    *,
    customer_local_v1: bool,
    provider_usage_v1: bool,
    expected_launch_plan_digest: str | None = None,
    openrouter_api_key: SecretValue | None = None,
) -> tuple[PreparedMatch, int]:
    """Validate then run only the fixed local match implementation."""

    if customer_local_v1 is not True or provider_usage_v1 is not True:
        raise RunnerClientError(
            "prepared match requires fresh customer-local and provider-usage consent"
        )
    prepared = load_prepared_match(path)
    if expected_launch_plan_digest is not None:
        expected_digest = _hex_digest(
            expected_launch_plan_digest, "expected launch plan digest"
        )
        if not hmac.compare_digest(
            expected_digest, prepared.launch_plan_digest
        ):
            raise RunnerClientError(
                "prepared match changed after provider authorization"
            )

    if openrouter_api_key is not None:
        if not isinstance(openrouter_api_key, SecretValue):
            raise RunnerClientError("one-match OpenRouter key must remain wrapped")
        if "openrouter" not in prepared.provider_ids:
            raise RunnerClientError(
                "one-match OpenRouter key does not match the prepared providers"
            )
        if "OPENROUTER_API_KEY" in os.environ:
            raise RunnerClientError(
                "refusing to replace an existing OpenRouter environment key"
            )
        os.environ["OPENROUTER_API_KEY"] = openrouter_api_key.reveal()
        try:
            status = _fixed_match_main([*prepared.argv, *FRESH_EXECUTION_FLAGS])
        finally:
            os.environ.pop("OPENROUTER_API_KEY", None)
    else:
        status = _fixed_match_main([*prepared.argv, *FRESH_EXECUTION_FLAGS])
    if type(status) is not int or status not in (0, 1, 2):
        raise RunnerClientError(
            "prepared match fixed runner returned an invalid status"
        )
    return prepared, status


@dataclasses.dataclass(frozen=True)
class _PreparedSeat:
    job_seat: CompetitionSeat
    passport_sha256: str | None

    @property
    def entrant(self) -> str:
        return self.job_seat.entrant

    @property
    def provider_claim(self) -> str:
        return self.job_seat.provider_claim

    @property
    def agent_id(self) -> str | None:
        return self.job_seat.agent_id

    @property
    def version_id(self) -> str | None:
        return self.job_seat.version_id


def _validate_seat(value, *, expected_seat: int) -> _PreparedSeat:
    seat = _exact_dict(value, _SEAT_KEYS, "prepared match seat")
    if type(seat["seat"]) is not int or seat["seat"] != expected_seat:
        raise RunnerClientError("prepared match seat order is invalid")
    entrant = _bounded_text(seat["entrant"], "prepared match entrant", 80)
    provider = seat["providerClaim"]
    if provider not in SUPPORTED_PROVIDERS:
        raise RunnerClientError("prepared match provider is unsupported")
    model = _provider_option(seat["selectedModelClaim"], "prepared match model")
    variant = _provider_option(seat["variantClaim"], "prepared match variant")
    backend = _bounded_text(seat["backendClaim"], "prepared match backend", 240)
    if backend != _expected_backend_claim(provider, model=model, variant=variant):
        raise RunnerClientError("prepared match backend differs from provider options")
    if seat["strategy"] not in STRATEGIES:
        raise RunnerClientError("prepared match strategy is unsupported")
    agent_id = _optional_digest(seat["agentId"], "prepared match agent id")
    version_id = _optional_digest(seat["versionId"], "prepared match version id")
    passport_sha256 = _optional_digest(
        seat["passportSha256"], "prepared match passport digest"
    )
    if (agent_id is None) != (version_id is None):
        raise RunnerClientError("prepared match agent/version binding is partial")
    return _PreparedSeat(
        job_seat=CompetitionSeat(
            seat=expected_seat,
            entrant=entrant,
            provider_claim=provider,
            selected_model_claim=model,
            variant_claim=variant,
            backend_claim=backend,
            strategy=seat["strategy"],
            agent_id=agent_id,
            version_id=version_id,
        ),
        passport_sha256=passport_sha256,
    )


def _expected_backend_claim(
    provider: str, *, model: str | None, variant: str | None
) -> str:
    entry = get_provider(provider)
    if entry["model_required"] and model is None:
        raise RunnerClientError("prepared match provider model is required")
    if not entry["model_required"] and model is not None:
        raise RunnerClientError("prepared match provider rejects a model option")
    if provider != "opencode" and variant is not None:
        raise RunnerClientError("prepared match provider rejects a variant option")
    if provider == "chatgpt_codex":
        return "chatgpt_codex:codex exec"
    if provider == "claude_code":
        return "claude_code:claude -p"
    if provider == "opencode":
        provider_name, separator, model_name = model.partition("/")
        if (
            not separator
            or not provider_name
            or not model_name
            or "@" in model
            or len(provider_name) > 80
            or len(model_name) > 160
        ):
            raise RunnerClientError("prepared match OpenCode model is invalid")
        return _bounded_text(
            f"opencode-provider:{model}@{variant or 'max'}",
            "prepared match derived backend",
            240,
        )
    if provider == "openrouter":
        return _bounded_text(
            f"openrouter:{model}", "prepared match derived backend", 240
        )
    if provider == "hermes":
        provider_name, separator, model_name = model.partition("/")
        if (
            not separator
            or not provider_name
            or not model_name
            or len(provider_name) > 80
            or len(model_name) > 120
        ):
            raise RunnerClientError("prepared match Hermes model is invalid")
        return _bounded_text(f"hermes:{model}", "prepared match derived backend", 240)
    raise RunnerClientError("prepared match provider is unsupported")


def _expected_base_argv(
    *,
    seats: tuple[_PreparedSeat, _PreparedSeat],
    game: str,
    seed: int,
    timeout_ms: int,
    match_directory: Path,
    summary_file: Path,
) -> list[str]:
    argv: list[str] = []
    for seat_number, seat in enumerate(seats):
        row = seat.job_seat
        prefix = f"--seat{seat_number}"
        argv.extend(
            (
                f"{prefix}-provider={row.provider_claim}",
                f"{prefix}-name={row.entrant}",
                f"{prefix}-strategy={row.strategy}",
            )
        )
        if row.selected_model_claim is not None:
            argv.append(f"{prefix}-model={row.selected_model_claim}")
        if row.variant_claim is not None:
            argv.append(f"{prefix}-variant={row.variant_claim}")
    argv.extend(
        (
            f"--game={game}",
            f"--seed={seed}",
            f"--backend-timeout={_timeout_text(timeout_ms)}",
            f"--out={match_directory}",
            f"--json-out={summary_file}",
        )
    )
    return argv


def _verify_passport_file(
    value: str, *, seat: _PreparedSeat, harness_digest: str
) -> None:
    path, raw = _read_regular_file(value, 64 * 1024, "prepared match passport")
    if value != str(path):
        raise RunnerClientError("prepared match passport path is not normalized")
    if not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), seat.passport_sha256):
        raise RunnerClientError("prepared match passport bytes changed")
    try:
        passport = load_passport(raw.decode("utf-8", errors="strict"))
    except (UnicodeError, PassportError) as error:
        raise RunnerClientError("prepared match passport fails verification") from error
    assigned = seat.job_seat
    if (
        passport["agentId"] != assigned.agent_id
        or passport["versionId"] != assigned.version_id
        or passport["displayName"] != assigned.entrant
        or passport["claimedModel"] != assigned.backend_claim
        or passport["harnessSha256"] != harness_digest
    ):
        raise RunnerClientError("prepared match passport differs from assigned seat")


def _read_regular_file(value: str, maximum: int, label: str) -> tuple[Path, bytes]:
    candidate = Path(value) if isinstance(value, str) else Path()
    if (
        not isinstance(value, str)
        or not value
        or candidate.is_symlink()
        or not candidate.is_file()
    ):
        raise RunnerClientError(f"{label} must be one regular non-symlink file")
    path = Path(os.path.realpath(os.path.abspath(candidate)))
    try:
        with path.open("rb") as handle:
            raw = handle.read(maximum + 1)
    except OSError as error:
        raise RunnerClientError(f"{label} could not be read") from error
    if not raw or len(raw) > maximum:
        raise RunnerClientError(f"{label} is empty or oversized")
    return path, raw


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
    if not isinstance(value, str) or not value or "\x00" in value:
        raise RunnerClientError(f"{label} path is invalid")
    path = Path(os.path.realpath(os.path.abspath(value)))
    if value != str(path):
        raise RunnerClientError(f"{label} path is not normalized")
    if os.path.lexists(path):
        raise RunnerClientError(f"{label} already exists")
    return path


def _require_disjoint_paths(plan: Path, match_root: Path, summary: Path) -> None:
    normalized = [os.path.normcase(str(path)) for path in (plan, match_root, summary)]
    if len(set(normalized)) != 3:
        raise RunnerClientError("prepared match paths must differ")
    for left, right in ((plan, match_root), (plan, summary), (match_root, summary)):
        try:
            common = Path(os.path.commonpath((left, right)))
        except ValueError:
            continue
        if os.path.normcase(str(common)) in {
            os.path.normcase(str(left)),
            os.path.normcase(str(right)),
        }:
            raise RunnerClientError("prepared match paths must not be nested")


def _exact_dict(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise RunnerClientError(f"{label} has an invalid exact schema")
    return value


def _exact_bool(value, label) -> bool:
    if type(value) is not bool:
        raise RunnerClientError(f"{label} is invalid")
    return value


def _integer(value, label, minimum, maximum) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise RunnerClientError(f"{label} is invalid")
    return value


def _hex_digest(value, label) -> str:
    if not isinstance(value, str) or _HEX64_RE.fullmatch(value) is None:
        raise RunnerClientError(f"{label} is invalid")
    return value


def _optional_digest(value, label) -> str | None:
    return None if value is None else _hex_digest(value, label)


def _bounded_text(value, label, maximum) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > maximum
        or any(
            ord(character) < 0x20
            or ord(character) == 0x7F
            or 0xD800 <= ord(character) <= 0xDFFF
            for character in value
        )
    ):
        raise RunnerClientError(f"{label} is invalid")
    return value


def _provider_option(value, label) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or _PROVIDER_OPTION_RE.fullmatch(value) is None:
        raise RunnerClientError(f"{label} is invalid")
    return value


def _canonical_token(value, prefix: str, label: str) -> str:
    if not isinstance(value, str) or not value.startswith(prefix):
        raise RunnerClientError(f"{label} is invalid")
    encoded = value[len(prefix) :]
    if len(encoded) != 22:
        raise RunnerClientError(f"{label} is invalid")
    try:
        padded = encoded + "=" * ((4 - len(encoded) % 4) % 4)
        decoded = base64.b64decode(padded, altchars=b"-_", validate=True)
    except (TypeError, ValueError) as error:
        raise RunnerClientError(f"{label} is invalid") from error
    canonical = base64.urlsafe_b64encode(decoded).decode("ascii").rstrip("=")
    if len(decoded) != 16 or not hmac.compare_digest(canonical, encoded):
        raise RunnerClientError(f"{label} is invalid")
    return value


def _timeout_text(milliseconds: int) -> str:
    seconds = milliseconds / 1_000
    return format(seconds, ".3f").rstrip("0").rstrip(".")


def _reject_duplicate_keys(pairs):
    output = {}
    for key, value in pairs:
        if key in output:
            raise ValueError("duplicate JSON object key")
        output[key] = value
    return output


def _reject_number(_value):
    raise ValueError("non-integer JSON number")
