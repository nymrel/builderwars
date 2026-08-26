#!/usr/bin/env python3
"""Run one customer-local, replay-verified cross-provider fantasy match.

Provider credentials stay inside each provider's supported local client or the
customer's explicitly provisioned OpenRouter environment.  The arena records
provider/model/harness labels as claims only.  A replay PASS proves the game
and accepted moves, not provider, account, model, billing, person, or runtime
identity.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from arena.canonical import digest  # noqa: E402
from arena.integrity import script_digest  # noqa: E402
from arena.match import run_match, validate_manifest  # noqa: E402
from arena.transcript import find, first, load  # noqa: E402
from entrants.backends import (  # noqa: E402
    acknowledge_customer_local_v1,
    get_provider_backend,
)
from provider_hub.catalog import get_provider  # noqa: E402
from publishing.projection import verify_with_snapshot  # noqa: E402
from run_agentwars_league import final_scores, move_source_counts  # noqa: E402


SUMMARY_SCHEMA = "agentwars.cross_provider_match_summary.v1"
EVIDENCE_CLASS = "customer_local_provider_claims_with_replay"
FANTASY_GAMES = ("fantasy_redraft", "fantasy_dynasty", "fantasy_qb_surge")
STRATEGIES = ("win-now", "long-game")
SUPPORTED_PROVIDERS = (
    "chatgpt_codex",
    "claude_code",
    "opencode",
    "openrouter",
    "hermes",
)
FALSE_ATTESTATIONS = (
    "providerAccountAttested",
    "planEntitlementAttested",
    "billingRouteAttested",
    "modelAttested",
    "personAttested",
    "runtimeAttested",
    "harnessExecutionAttested",
    "matchExecutionAttested",
)
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_HEX16_RE = re.compile(r"^[0-9a-f]{16}$")
_ERROR_CLASS_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,79}$")
_ERROR_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{0,79}$")
_PROVIDER_OPTION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+@-]{0,239}$")


class CrossProviderMatchError(RuntimeError):
    """Bounded local failure code that contains no credential or response."""

    def __init__(self, code: str):
        if not isinstance(code, str) or _ERROR_CODE_RE.fullmatch(code) is None:
            code = "cross_provider_match_error"
        self.code = code
        super().__init__(code)


@dataclasses.dataclass(frozen=True)
class SeatSpec:
    name: str
    provider: str
    strategy: str
    model: str | None = None
    variant: str | None = None
    passport_path: str | None = None


@dataclasses.dataclass(frozen=True)
class SeatRuntime:
    spec: SeatSpec
    backend_label: str
    connection_mode: str
    provider_class: str
    harness_class: str
    manifest: dict
    provisioned_environment: dict[str, str]


def _bounded_name(value: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > 80
        or any(ord(ch) < 0x20 or ord(ch) == 0x7F or 0xD800 <= ord(ch) <= 0xDFFF for ch in value)
    ):
        raise CrossProviderMatchError("entrant_name_invalid")
    return value.strip()


def _timeout(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 10 <= value <= 900:
        raise CrossProviderMatchError("provider_timeout_invalid")
    # Normalize once so the child-adapter timeout and arena move timeout cannot
    # diverge on a sub-millisecond input.
    return float(format(float(value), ".3f"))


def _timeout_text(value: float) -> str:
    return format(value, ".3f").rstrip("0").rstrip(".")


def _bounded_provider_option(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or value != value.strip()
        or _PROVIDER_OPTION_RE.fullmatch(value) is None
    ):
        raise CrossProviderMatchError(f"{field}_invalid")
    return value


def _bounded_backend_label(value: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > 240
        or any(ord(ch) < 0x20 or ord(ch) == 0x7F or 0xD800 <= ord(ch) <= 0xDFFF for ch in value)
    ):
        raise CrossProviderMatchError("backend_label_invalid")
    return value


def _is_seat(value: object) -> bool:
    return type(value) is int and value in (0, 1)


def _openrouter_environment() -> dict[str, str]:
    key = os.environ.get("OPENROUTER_API_KEY")
    if (
        not isinstance(key, str)
        or not key
        or len(key) > 8192
        or any(ord(ch) < 0x20 or ord(ch) == 0x7F or 0xD800 <= ord(ch) <= 0xDFFF for ch in key)
    ):
        raise CrossProviderMatchError("openrouter_customer_key_unavailable")
    return {"OPENROUTER_API_KEY": key}


def _manifest_receipt_digest(manifest: dict, observed: dict) -> str | None:
    passport_expected = "agent_passport" in manifest
    passport_observed = "agent_passport" in observed
    if passport_expected != passport_observed:
        return None
    body = {
        "name": manifest["name"],
        "cmd": list(manifest["cmd"]),
        "env": sorted(manifest.get("env", [])),
        "claimed_model": manifest.get("claimed_model"),
        "execution_claim": manifest["execution_claim"],
    }
    if passport_expected:
        if not isinstance(observed.get("agent_passport"), dict):
            return None
        body["agent_passport"] = observed["agent_passport"]
    return digest(body)


def _valid_move_source_note(note: object) -> bool:
    if not isinstance(note, str) or not 1 <= len(note) <= 256:
        return False
    parts = note.split(";")
    if parts[0] not in ("source=model", "source=fallback"):
        return False
    source = parts[0].removeprefix("source=")
    allowed = {
        "attempts",
        "reason",
        "initial_reason",
        "response_sha256",
        "prior_response_sha256",
    }
    fields = {}
    for part in parts[1:]:
        key, separator, value = part.partition("=")
        if not separator or key not in allowed or key in fields or not value:
            return False
        fields[key] = value
    if fields.get("attempts") not in (None, "1", "2"):
        return False
    for key in ("response_sha256", "prior_response_sha256"):
        if key in fields and _HEX16_RE.fullmatch(fields[key]) is None:
            return False
    reason = fields.get("reason")
    initial_reason = fields.get("initial_reason")
    simple_reasons = ("invalid_model_output", "illegal_model_move")
    if source == "model":
        return (
            reason is None
            and initial_reason is None
            and "response_sha256" in fields
            and ("prior_response_sha256" not in fields or fields.get("attempts") == "2")
        )
    if reason in simple_reasons:
        if initial_reason is not None:
            return False
        if fields.get("attempts") is None:
            return "response_sha256" in fields and "prior_response_sha256" not in fields
        return fields.get("attempts") == "2" and {
            "response_sha256",
            "prior_response_sha256",
        } <= set(fields)
    reason_kind, separator, error_class = (reason or "").partition(":")
    if not separator or reason_kind not in ("backend_error", "repair_backend_error"):
        return False
    if _ERROR_CLASS_RE.fullmatch(error_class) is None:
        return False
    if reason_kind == "backend_error":
        return (
            fields.get("attempts") == "1"
            and initial_reason is None
            and "response_sha256" not in fields
            and "prior_response_sha256" not in fields
        )
    return (
        fields.get("attempts") == "2"
        and initial_reason in simple_reasons
        and "response_sha256" not in fields
        and "prior_response_sha256" in fields
    )


def build_seat_runtime(spec: SeatSpec, *, backend_timeout: float) -> SeatRuntime:
    if not isinstance(spec, SeatSpec):
        raise CrossProviderMatchError("seat_spec_invalid")
    if spec.provider not in SUPPORTED_PROVIDERS:
        raise CrossProviderMatchError("provider_not_supported_for_public_runner")
    name = _bounded_name(spec.name)
    if spec.strategy not in STRATEGIES:
        raise CrossProviderMatchError("strategy_invalid")
    model = _bounded_provider_option(spec.model, "provider_model")
    variant = _bounded_provider_option(spec.variant, "provider_variant")
    normalized_spec = dataclasses.replace(spec, name=name, model=model, variant=variant)
    backend_timeout = _timeout(backend_timeout)
    entry = get_provider(spec.provider)
    try:
        backend = get_provider_backend(
            spec.provider,
            model=model,
            variant=variant,
            timeout_s=backend_timeout,
            runtime_intent=acknowledge_customer_local_v1(),
        )
    except (TypeError, ValueError, RuntimeError) as error:
        raise CrossProviderMatchError("provider_options_invalid") from error
    backend_label = _bounded_backend_label(backend.label)

    harness = os.path.join(ROOT, "entrants", "fantasy_model_harness.py")
    command = [
        sys.executable,
        harness,
        "--name",
        name,
        "--strategy",
        spec.strategy,
        "--provider",
        spec.provider,
        "--customer-local-v1",
        "--backend-timeout",
        _timeout_text(backend_timeout),
    ]
    if model is not None:
        command.extend(("--provider-model", model))
    if variant is not None:
        command.extend(("--provider-variant", variant))

    declared_environment = ["OPENROUTER_API_KEY"] if spec.provider == "openrouter" else []
    provisioned_environment = _openrouter_environment() if spec.provider == "openrouter" else {}
    manifest = {
        "name": name,
        "cmd": command,
        "env": declared_environment,
        "claimed_model": backend_label,
        # The harness can take a deterministic fallback after a malformed or
        # failed provider response, so the declaration can never be `model`.
        "execution_claim": "hybrid",
    }
    if spec.passport_path is not None:
        if not isinstance(spec.passport_path, str) or not spec.passport_path:
            raise CrossProviderMatchError("passport_path_invalid")
        manifest["agent_passport"] = os.path.abspath(spec.passport_path)
    validate_manifest(manifest)
    return SeatRuntime(
        spec=normalized_spec,
        backend_label=backend_label,
        connection_mode=entry["connection_mode"],
        provider_class=entry["provider_class"],
        harness_class=entry["harness_class"],
        manifest=manifest,
        provisioned_environment=provisioned_environment,
    )


def audit_transcript(*, result: dict, report: dict, runtimes: list[SeatRuntime]) -> dict:
    if len(runtimes) != 2:
        raise CrossProviderMatchError("seat_count_invalid")
    if report.get("verdict") != "PASS" or report.get("effective_verdict") != "PASS":
        raise CrossProviderMatchError("replay_not_pass")
    if report.get("engine_digest_match") is not True or report.get("verifier_snapshot_match") is not True:
        raise CrossProviderMatchError("verifier_snapshot_not_exact")
    path = result.get("transcript")
    if not isinstance(path, str):
        raise CrossProviderMatchError("transcript_path_missing")
    if os.path.abspath(str(report.get("transcript", ""))) != os.path.abspath(path):
        raise CrossProviderMatchError("replay_report_transcript_mismatch")
    records = load(path)
    header = first(records, "header")
    terminal = first(records, "result")
    if header is None or terminal is None:
        raise CrossProviderMatchError("transcript_terminal_shape_invalid")
    if find(records, "forfeit") or find(records, "abort") or find(records, "engine_error"):
        raise CrossProviderMatchError("competitive_match_not_clean")
    if terminal["body"].get("decisive") is not True or not _is_seat(terminal["body"].get("winner")):
        raise CrossProviderMatchError("competitive_match_not_decisive")
    if terminal["body"].get("winner") != result.get("winner"):
        raise CrossProviderMatchError("result_winner_mismatch")
    if header["body"].get("match_id") != result.get("match_id"):
        raise CrossProviderMatchError("match_identity_mismatch")
    if (
        report.get("match_id") != result.get("match_id")
        or report.get("chain_head") != result.get("chain_head")
        or records[-1].get("hash") != result.get("chain_head")
    ):
        raise CrossProviderMatchError("replay_report_identity_mismatch")
    attestation = header["body"].get("attestation")
    if not isinstance(attestation, dict) or attestation.get("model_attested") is not False or attestation.get("execution_claims_attested") is not False:
        raise CrossProviderMatchError("header_attestation_overclaim")

    entrants = header["body"].get("entrants")
    if not isinstance(entrants, list) or len(entrants) != 2:
        raise CrossProviderMatchError("header_entrant_shape_invalid")
    ready = find(records, "ready")
    if len(ready) != 2:
        raise CrossProviderMatchError("ready_record_count_invalid")
    if any(not _is_seat(row["body"].get("player")) for row in ready):
        raise CrossProviderMatchError("ready_seat_invalid")
    ready_by_seat = {row["body"].get("player"): row["body"].get("entrant_message") for row in ready}
    for seat, runtime in enumerate(runtimes):
        expected = runtime.manifest
        observed = entrants[seat]
        if (
            not isinstance(observed, dict)
            or not _is_seat(observed.get("seat"))
            or observed.get("seat") != seat
            or observed.get("name") != expected["name"]
            or observed.get("claimed_model") != expected["claimed_model"]
            or observed.get("execution_claim") != "hybrid"
            or observed.get("declared_env") != sorted(expected["env"])
            or observed.get("script") != script_digest(expected["cmd"])
            or observed.get("manifest_digest") != _manifest_receipt_digest(expected, observed)
        ):
            raise CrossProviderMatchError("header_entrant_binding_mismatch")
        if ready_by_seat.get(seat) != {
            "type": "ready",
            "entrant": expected["name"],
            "version": "1",
            "backend": runtime.backend_label,
        }:
            raise CrossProviderMatchError("ready_backend_binding_mismatch")

    moves_by_seat = [0, 0]
    for row in find(records, "move"):
        seat = row["body"].get("player")
        note = row["body"].get("entrant_message", {}).get("note")
        if not _is_seat(seat):
            raise CrossProviderMatchError("move_seat_invalid")
        if not _valid_move_source_note(note):
            raise CrossProviderMatchError("move_source_claim_invalid")
        moves_by_seat[seat] += 1
    if moves_by_seat != [6, 6]:
        raise CrossProviderMatchError("fantasy_move_count_invalid")
    return {"movesBySeat": moves_by_seat, "decisive": True, "clean": True}


def _transcript_sha256(path: str) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            sha.update(block)
    return sha.hexdigest()


def _source_claim_status(count_rows: list[dict]) -> tuple[str, bool]:
    if not isinstance(count_rows, list) or len(count_rows) != 2:
        raise CrossProviderMatchError("source_count_seat_shape_invalid")
    all_model = True
    both_model_influenced = True
    any_model_influenced = False
    for counts in count_rows:
        if not isinstance(counts, dict) or set(counts) != {"model", "fallback", "scripted", "other"}:
            raise CrossProviderMatchError("source_count_shape_invalid")
        if any(type(counts[key]) is not int or counts[key] < 0 for key in counts):
            raise CrossProviderMatchError("source_count_value_invalid")
        if sum(counts.values()) != 6 or counts["scripted"] != 0 or counts["other"] != 0:
            raise CrossProviderMatchError("source_count_competitive_invalid")
        all_model = all_model and counts == {"model": 6, "fallback": 0, "scripted": 0, "other": 0}
        both_model_influenced = both_model_influenced and counts["model"] > 0
        any_model_influenced = any_model_influenced or counts["model"] > 0
    if all_model:
        return "model_influenced_unattested", True
    if both_model_influenced:
        return "mixed_model_and_fallback_unattested", False
    if any_model_influenced:
        return "partial_model_influence_unattested", False
    return "fallback_only_not_model_played", False


def build_summary(
    *,
    result: dict,
    report: dict,
    runtimes: list[SeatRuntime],
    source_counts: dict,
    scores: list[int],
) -> dict:
    if len(runtimes) != 2 or len(scores) != 2:
        raise CrossProviderMatchError("summary_input_shape_invalid")
    if any(type(score) is not int for score in scores):
        raise CrossProviderMatchError("score_value_invalid")
    if runtimes[0].spec.provider == runtimes[1].spec.provider:
        raise CrossProviderMatchError("provider_claims_must_differ")
    path = result.get("transcript")
    if not isinstance(path, str) or not os.path.isfile(path):
        raise CrossProviderMatchError("summary_transcript_invalid")
    if not _is_seat(result.get("winner")):
        raise CrossProviderMatchError("summary_winner_invalid")
    recorded = report.get("recorded")
    if (
        report.get("verdict") != "PASS"
        or report.get("effective_verdict") != "PASS"
        or report.get("engine_digest_match") is not True
        or report.get("verifier_snapshot_match") is not True
        or report.get("match_id") != result.get("match_id")
        or report.get("chain_head") != result.get("chain_head")
        or report.get("game") != result.get("game")
        or report.get("seed") != result.get("seed")
        or not isinstance(recorded, dict)
        or recorded.get("winner") != result.get("winner")
        or os.path.abspath(str(report.get("transcript", "")))
        != os.path.abspath(path)
    ):
        raise CrossProviderMatchError("summary_replay_binding_invalid")
    expected_names = [runtime.manifest["name"] for runtime in runtimes]
    if len(set(expected_names)) != 2:
        raise CrossProviderMatchError("summary_entrant_names_invalid")
    if not isinstance(source_counts, dict) or set(source_counts) != set(expected_names):
        raise CrossProviderMatchError("source_count_entrant_set_invalid")
    if source_counts != move_source_counts(path, [runtime.manifest for runtime in runtimes]):
        raise CrossProviderMatchError("source_count_transcript_mismatch")
    if scores != final_scores(path):
        raise CrossProviderMatchError("score_transcript_mismatch")
    count_rows = [source_counts[name] for name in expected_names]
    status, all_model = _source_claim_status(count_rows)
    rows = []
    for seat, runtime in enumerate(runtimes):
        name = runtime.manifest["name"]
        counts = source_counts[name]
        rows.append({
            "seat": seat,
            "entrant": name,
            "providerClaim": runtime.spec.provider,
            "selectedModelClaim": runtime.spec.model,
            "variantClaim": runtime.spec.variant,
            "connectionModeClaim": runtime.connection_mode,
            "providerClass": runtime.provider_class,
            "harnessClass": runtime.harness_class,
            "backendClaim": runtime.backend_label,
            "strategy": runtime.spec.strategy,
            "score": scores[seat],
            "moveSourceClaims": dict(counts),
        })
    core = {
        "schemaVersion": SUMMARY_SCHEMA,
        "status": status,
        "evidenceClass": EVIDENCE_CLASS,
        "publicationDecision": "not_reviewed_not_published",
        "truthBoundary": (
            "The customer-local runner observed the declared provider adapters and the replay verifier "
            "proved the accepted moves, deterministic state, scoring, and result. Provider, account, "
            "plan, billing route, model, person, runtime, and causal execution identity remain unattested."
        ),
        "game": result.get("game"),
        "seed": result.get("seed"),
        "matchId": result.get("match_id"),
        "chainHead": result.get("chain_head"),
        "transcriptSha256": _transcript_sha256(path),
        "winnerSeat": result.get("winner"),
        "winnerEntrant": runtimes[result["winner"]].manifest["name"],
        "seats": rows,
        "providerClaimsDiffer": runtimes[0].spec.provider != runtimes[1].spec.provider,
        "allAcceptedMovesModelClaimed": all_model,
        "universalProviderOrModelRankingEligible": False,
        "verification": {
            "replayVerdict": report.get("verdict"),
            "effectiveVerdict": report.get("effective_verdict"),
            "engineDigest": report.get("engine_digest_recorded"),
            "engineDigestMatch": report.get("engine_digest_match"),
            "verifierSnapshotMatch": report.get("verifier_snapshot_match"),
            "identityStatus": report.get("identity_status"),
            "signedHarnessVersionsVerified": report.get("identity_status") == "verified_signed",
        },
        **{field: False for field in FALSE_ATTESTATIONS},
    }
    if (
        core["game"] not in FANTASY_GAMES
        or type(core["seed"]) is not int
        or not isinstance(core["matchId"], str)
        or not isinstance(core["chainHead"], str)
        or _HEX64_RE.fullmatch(core["chainHead"]) is None
        or _HEX64_RE.fullmatch(core["transcriptSha256"]) is None
    ):
        raise CrossProviderMatchError("summary_identity_invalid")
    return {**core, "summaryDigest": digest(core)}


class _ReservedJsonOutput:
    def __init__(self, path: str):
        if not isinstance(path, str) or not path:
            raise CrossProviderMatchError("summary_path_invalid")
        self.path = os.path.abspath(path)
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_BINARY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        try:
            self.fd = os.open(self.path, flags, 0o600)
        except FileExistsError:
            raise CrossProviderMatchError("summary_output_exists") from None
        self.committed = False

    def commit(self, value: dict) -> None:
        if self.fd is None or self.committed:
            raise CrossProviderMatchError("summary_reservation_not_open")
        try:
            encoded = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
            fd = self.fd
            handle = os.fdopen(fd, "wb")
            self.fd = None
            with handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
        except BaseException:
            self.abort()
            raise
        self.committed = True

    def abort(self) -> None:
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None
        if not self.committed:
            try:
                os.unlink(self.path)
            except OSError:
                pass


def reserve_json_output(path: str) -> _ReservedJsonOutput:
    return _ReservedJsonOutput(path)


def reserve_match_output_directory(path: str) -> str:
    if not isinstance(path, str) or not path:
        raise CrossProviderMatchError("match_path_invalid")
    absolute = os.path.abspath(path)
    os.makedirs(os.path.dirname(absolute), exist_ok=True)
    try:
        os.mkdir(absolute)
    except FileExistsError:
        raise CrossProviderMatchError("match_output_exists") from None
    return absolute


def remove_empty_match_output_directory(path: str) -> None:
    try:
        os.rmdir(path)
    except OSError:
        # Non-empty failure evidence is intentionally retained for debugging.
        pass


def write_json_exclusive(path: str, value: dict) -> None:
    reservation = reserve_json_output(path)
    try:
        reservation.commit(value)
    except BaseException:
        reservation.abort()
        raise


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="Run one customer-local AgentWars provider match.")
    command.add_argument("--game", choices=FANTASY_GAMES, default="fantasy_redraft")
    command.add_argument("--seed", type=int, default=9400)
    command.add_argument("--out", required=True)
    command.add_argument("--json-out", required=True)
    command.add_argument("--backend-timeout", type=float, default=180.0)
    for seat, default_provider, default_name, default_strategy in (
        (0, "chatgpt_codex", "Codex Redraft", "win-now"),
        (1, "claude_code", "Claude Dynasty", "long-game"),
    ):
        command.add_argument(f"--seat{seat}-provider", choices=SUPPORTED_PROVIDERS, default=default_provider)
        command.add_argument(f"--seat{seat}-name", default=default_name)
        command.add_argument(f"--seat{seat}-strategy", choices=STRATEGIES, default=default_strategy)
        command.add_argument(f"--seat{seat}-model")
        command.add_argument(f"--seat{seat}-variant")
    command.add_argument("--agent-passports", nargs=2, metavar=("SEAT0_JSON", "SEAT1_JSON"))
    command.add_argument("--customer-local-v1", action="store_true")
    command.add_argument(
        "--provider-usage-v1",
        action="store_true",
        help="acknowledge that local provider calls consume customer-owned quota or may incur customer charges",
    )
    return command


def _seat_from_args(args, seat: int) -> SeatSpec:
    passports = args.agent_passports or (None, None)
    return SeatSpec(
        name=getattr(args, f"seat{seat}_name"),
        provider=getattr(args, f"seat{seat}_provider"),
        strategy=getattr(args, f"seat{seat}_strategy"),
        model=getattr(args, f"seat{seat}_model"),
        variant=getattr(args, f"seat{seat}_variant"),
        passport_path=passports[seat],
    )


def run(args) -> tuple[dict, int]:
    if args.customer_local_v1 is not True or args.provider_usage_v1 is not True:
        raise CrossProviderMatchError("explicit_customer_provider_intent_required")
    if type(args.seed) is not int or not 0 <= args.seed <= 2_147_483_647:
        raise CrossProviderMatchError("seed_invalid")
    timeout = _timeout(args.backend_timeout)
    out_root = os.path.realpath(os.path.abspath(args.out))
    summary_path = os.path.realpath(os.path.abspath(args.json_out))
    try:
        common_output_path = os.path.commonpath((out_root, summary_path))
    except ValueError:
        common_output_path = None
    if common_output_path in (out_root, summary_path):
        raise CrossProviderMatchError("output_paths_overlap")
    if os.path.lexists(out_root):
        raise CrossProviderMatchError("match_output_exists")
    if os.path.lexists(summary_path):
        raise CrossProviderMatchError("summary_output_exists")
    runtimes = [
        build_seat_runtime(_seat_from_args(args, seat), backend_timeout=timeout)
        for seat in (0, 1)
    ]
    if runtimes[0].manifest["name"].casefold() == runtimes[1].manifest["name"].casefold():
        raise CrossProviderMatchError("entrant_names_not_unique")
    if runtimes[0].spec.provider == runtimes[1].spec.provider:
        raise CrossProviderMatchError("provider_claims_must_differ")
    reservation = reserve_json_output(summary_path)
    try:
        reserve_match_output_directory(out_root)
    except BaseException:
        reservation.abort()
        raise
    try:
        result = run_match(
            game_name=args.game,
            seed=args.seed,
            entrants=[row.manifest for row in runtimes],
            provisioned_envs=[row.provisioned_environment for row in runtimes],
            out_dir=out_root,
            move_timeout_s=timeout + 30,
        )
        report = verify_with_snapshot(result["transcript"])
        audit_transcript(result=result, report=report, runtimes=runtimes)
        sources = move_source_counts(result["transcript"], [row.manifest for row in runtimes])
        scores = final_scores(result["transcript"])
        summary = build_summary(
            result={**result, "game": args.game, "seed": args.seed},
            report=report,
            runtimes=runtimes,
            source_counts=sources,
            scores=scores,
        )
        reservation.commit(summary)
    except BaseException:
        reservation.abort()
        remove_empty_match_output_directory(out_root)
        raise
    return summary, 0 if summary["allAcceptedMovesModelClaimed"] else 2


def main(argv=None) -> int:
    try:
        args = parser().parse_args(argv)
        summary, status = run(args)
        print(json.dumps(summary, indent=2, sort_keys=True))
        return status
    except SystemExit:
        raise
    except Exception as error:
        # Provider stderr, responses, credentials, and local paths are never
        # copied into this public failure envelope.
        error_class = error.__class__.__name__
        if _ERROR_CLASS_RE.fullmatch(error_class) is None:
            error_class = "Exception"
        payload = {
            "schemaVersion": SUMMARY_SCHEMA,
            "status": "blocked",
            "errorClass": error_class,
        }
        if isinstance(error, CrossProviderMatchError):
            payload["errorCode"] = error.code
        print(
            json.dumps(payload),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
