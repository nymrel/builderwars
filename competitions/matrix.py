"""Balanced, replay-verified AgentWars competition matrices.

The matrix compares public *claims* about models and providers plus a digest of
the executable harness that actually entered the arena. It deliberately does
not upgrade any of those claims into provider or model attestation.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path

from arena.canonical import digest
from arena.games import REGISTRY
from arena.integrity import engine_digest, script_digest
from arena.match import EXECUTION_CLAIMS, run_match, validate_manifest
from arena.replay import verify
from arena.transcript import load as load_transcript

SCHEMA_VERSION = "agentwars.competition-matrix.v1"
REPORT_SCHEMA_VERSION = "agentwars.competition-report.v1"

_TOP_LEVEL_KEYS = frozenset(
    {"schemaVersion", "competition", "description", "game", "seeds", "entrants"}
)
_ENTRANT_KEYS = frozenset(
    {"name", "claimedModel", "claimedProvider", "argv", "env", "executionClaim"}
)
_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SUPPORTED_HARNESS_EXTENSIONS = frozenset(
    {".py", ".js", ".mjs", ".ts", ".sh", ".ps1", ".rb", ".exe"}
)
_SECRET_FLAG = re.compile(
    r"^--?(?:api[-_]?key|access[-_]?key|authorization|password|secret|token)(?:=|$)",
    re.IGNORECASE,
)
_SECRET_VALUE = re.compile(
    r"(?:^sk[-_][A-Za-z0-9_-]{12,}|^ghp_[A-Za-z0-9]{12,}|^github_pat_|"
    r"^xox[baprs]-|^AKIA[A-Z0-9]{12,}|^AIza[A-Za-z0-9_-]{12,}|"
    r"^Bearer\s+|^eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|://[^/@:]+:[^/@]+@)",
    re.IGNORECASE,
)
_MAX_SEED = 2_147_483_647


class CompetitionConfigError(ValueError):
    """The competition declaration is ambiguous or unsafe to execute."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CompetitionConfigError(message)


def _text(value, label: str, maximum: int, *, allow_empty: bool = False) -> str:
    _require(isinstance(value, str), f"{label} must be a string")
    normalized = unicodedata.normalize("NFKC", value).strip()
    _require(allow_empty or bool(normalized), f"{label} must not be empty")
    _require(len(normalized) <= maximum, f"{label} must be at most {maximum} characters")
    _require(not any(char in normalized for char in "\x00\r\n"), f"{label} contains a control character")
    return normalized


def _claim_key(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip().casefold()


def _validate_argv(value, entrant_name: str) -> list[str]:
    _require(isinstance(value, list), f"entrant {entrant_name!r} argv must be an array")
    _require(1 <= len(value) <= 32, f"entrant {entrant_name!r} argv must contain 1-32 strings")
    result = []
    total = 0
    for part in value:
        _require(
            isinstance(part, str) and bool(part),
            f"entrant {entrant_name!r} argv must contain non-empty strings",
        )
        _require(
            len(part) <= 1_000 and not any(char in part for char in "\x00\r\n"),
            f"entrant {entrant_name!r} argv contains an invalid argument",
        )
        _require(
            _SECRET_FLAG.search(part) is None
            and _SECRET_VALUE.search(part) is None
            and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", part) is None,
            f"entrant {entrant_name!r} argv appears to contain a credential or environment value; pass a variable name through env instead",
        )
        total += len(part)
        result.append(part)
    _require(total <= 8_192, f"entrant {entrant_name!r} argv is too large")
    return result


def _validate_env(value, entrant_name: str) -> list[str]:
    _require(isinstance(value, list), f"entrant {entrant_name!r} env must be an array of names")
    _require(len(value) <= 32, f"entrant {entrant_name!r} env may contain at most 32 names")
    _require(
        all(isinstance(name, str) and _ENV_NAME.fullmatch(name) for name in value),
        f"entrant {entrant_name!r} env must contain environment-variable names only",
    )
    _require(
        len(value) == len({name.casefold() for name in value}),
        f"entrant {entrant_name!r} env names must be unique, ignoring case",
    )
    return sorted(value)


def validate_config(value: object) -> dict:
    """Validate and normalize the strict public matrix declaration."""

    _require(isinstance(value, dict), "competition config must be an object")
    unexpected = set(value) - _TOP_LEVEL_KEYS
    missing = _TOP_LEVEL_KEYS - set(value) - {"description"}
    _require(not unexpected, "competition config has unexpected keys")
    _require(not missing, f"competition config is missing keys: {sorted(missing)}")
    _require(value.get("schemaVersion") == SCHEMA_VERSION, f"schemaVersion must be exactly {SCHEMA_VERSION}")

    competition = _text(value.get("competition"), "competition", 120)
    description = _text(value.get("description", ""), "description", 500, allow_empty=True)
    game = _text(value.get("game"), "game", 80)
    _require(game in REGISTRY, f"game must be one of the registered games: {sorted(REGISTRY)}")

    raw_seeds = value.get("seeds")
    _require(isinstance(raw_seeds, list), "seeds must be an array")
    _require(1 <= len(raw_seeds) <= 32, "seeds must contain 1-32 integers")
    _require(
        all(isinstance(seed, int) and not isinstance(seed, bool) and 0 <= seed <= _MAX_SEED for seed in raw_seeds),
        f"seeds must be integers from 0 through {_MAX_SEED}",
    )
    _require(len(raw_seeds) == len(set(raw_seeds)), "seeds must be unique")
    seeds = sorted(raw_seeds)

    raw_entrants = value.get("entrants")
    _require(isinstance(raw_entrants, list), "entrants must be an array")
    _require(2 <= len(raw_entrants) <= 16, "entrants must contain 2-16 declarations")
    entrants = []
    seen_names = set()
    for index, raw in enumerate(raw_entrants):
        _require(isinstance(raw, dict), f"entrant {index} must be an object")
        unexpected = set(raw) - _ENTRANT_KEYS
        missing = _ENTRANT_KEYS - set(raw) - {"env"}
        _require(not unexpected, f"entrant {index} has unexpected keys")
        _require(not missing, f"entrant {index} is missing keys: {sorted(missing)}")
        name = _text(raw.get("name"), f"entrant {index} name", 120)
        name_key = _claim_key(name)
        _require(name_key not in seen_names, "entrant names must be unique, ignoring case")
        seen_names.add(name_key)
        claimed_model = _text(raw.get("claimedModel"), f"entrant {name!r} claimedModel", 160)
        claimed_provider = _text(
            raw.get("claimedProvider"), f"entrant {name!r} claimedProvider", 120
        )
        execution_claim = raw.get("executionClaim")
        _require(
            execution_claim in EXECUTION_CLAIMS,
            "executionClaim must be exactly one of: " + ", ".join(sorted(EXECUTION_CLAIMS)),
        )
        argv = _validate_argv(raw.get("argv"), name)
        env = _validate_env(raw.get("env", []), name)
        manifest = {
            "name": name,
            "cmd": argv,
            "env": env,
            "claimed_model": claimed_model,
            "execution_claim": execution_claim,
        }
        try:
            validate_manifest(manifest)
        except ValueError as exc:
            raise CompetitionConfigError(f"entrant {name!r} is invalid: {exc}") from None
        entrants.append(
            {
                "name": name,
                "claimedModel": claimed_model,
                "claimedProvider": claimed_provider,
                "argv": argv,
                "env": env,
                "executionClaim": execution_claim,
            }
        )

    entrants.sort(key=lambda row: (_claim_key(row["name"]), row["name"]))
    return {
        "schemaVersion": SCHEMA_VERSION,
        "competition": competition,
        "description": description,
        "game": game,
        "seeds": seeds,
        "entrants": entrants,
    }


def load_config(path: os.PathLike | str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise CompetitionConfigError(f"could not load competition config: {exc.__class__.__name__}") from None
    return validate_config(value)


def _resolve_runtime_argv(argv: list[str], repo_root: Path) -> list[str]:
    """Resolve only repository-owned executable files for the scratch cwd."""

    root = repo_root.resolve()
    resolved = []
    for token in argv:
        replacement = token
        try:
            path = Path(token)
            candidate = path if path.is_absolute() else root / path
            candidate = candidate.resolve()
            if candidate.is_file() and candidate.suffix.lower() in _SUPPORTED_HARNESS_EXTENSIONS:
                try:
                    candidate.relative_to(root)
                except ValueError:
                    raise CompetitionConfigError(
                        "executable harness files must resolve inside repo_root"
                    ) from None
                replacement = str(candidate)
        except CompetitionConfigError:
            raise
        except (OSError, RuntimeError, ValueError):
            pass
        resolved.append(replacement)
    return resolved


def _identity_for(entrant: dict, repo_root: Path) -> dict:
    runtime_argv = _resolve_runtime_argv(entrant["argv"], repo_root)
    # Prefer a script after an interpreter; fall back to argv[0] for compiled harnesses.
    harness = script_digest(runtime_argv[1:]) or script_digest(runtime_argv)
    _require(
        harness is not None,
        f"entrant {entrant['name']!r} has no resolvable repository harness file",
    )
    model_key = _claim_key(entrant["claimedModel"])
    provider_key = _claim_key(entrant["claimedProvider"])
    harness_id = "hrn_" + harness["sha256"]
    model_id = "mdl_" + digest({"claim": model_key})
    provider_id = "prv_" + digest({"claim": provider_key})
    agent_build_id = "agb_" + digest(
        {
            "schema": "agentwars.agent-build.v1",
            "harnessSha256": harness["sha256"],
            "modelClaim": model_key,
            "providerClaim": provider_key,
        }
    )
    return {
        **entrant,
        "runtimeArgv": runtime_argv,
        "harnessFile": harness["path"],
        "harnessSha256": harness["sha256"],
        "harnessId": harness_id,
        "modelClaimId": model_id,
        "providerClaimId": provider_id,
        "agentBuildId": agent_build_id,
    }


def _prepare(config: object, repo_root: os.PathLike | str) -> tuple[dict, list[dict]]:
    normalized = validate_config(config)
    root = Path(repo_root).resolve()
    _require(root.is_dir(), "repo_root must identify a directory")
    entrants = [_identity_for(row, root) for row in normalized["entrants"]]
    seen = set()
    for entrant in entrants:
        build_id = entrant["agentBuildId"]
        _require(
            build_id not in seen,
            "duplicate agent build: model, provider, and executable harness must not all match",
        )
        seen.add(build_id)
    return normalized, entrants


def classify_pair(left: dict, right: dict) -> str:
    """Classify one pair without pretending its public claims are attested."""

    same_harness = left["harnessId"] == right["harnessId"]
    same_model = left["modelClaimId"] == right["modelClaimId"]
    same_provider = left["providerClaimId"] == right["providerClaimId"]
    if same_model and same_provider and not same_harness:
        return "harness_controlled_claim"
    if same_harness and same_provider and not same_model:
        return "model_controlled_claim"
    if same_harness and same_model and not same_provider:
        return "provider_controlled_claim"
    differences = sum((not same_harness, not same_model, not same_provider))
    if differences >= 2:
        return "open_agent"
    raise CompetitionConfigError("pair does not define a distinct comparison axis")


def _pair_id(left: dict, right: dict) -> str:
    return "pair_" + digest({"agentBuildIds": sorted([left["agentBuildId"], right["agentBuildId"]])})


def _runtime_manifest(entrant: dict) -> dict:
    # The build commitment is the transcript-bound name. This indirectly binds
    # the provider claim even though arena/1 has no provider field of its own.
    return {
        "name": entrant["agentBuildId"],
        "cmd": list(entrant["runtimeArgv"]),
        "env": list(entrant["env"]),
        "claimed_model": entrant["claimedModel"],
        "execution_claim": entrant["executionClaim"],
    }


def _empty_stats(entrant: dict) -> dict:
    return {
        "agent": entrant["name"],
        "agentBuildId": entrant["agentBuildId"],
        "games": 0,
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "matchPoints": 0,
        "seat0Games": 0,
        "seat1Games": 0,
        "seat0Wins": 0,
        "seat1Wins": 0,
        "modelMoveClaims": 0,
        "fallbackMoveClaims": 0,
        "scriptedMoveClaims": 0,
        "unclassifiedMoveClaims": 0,
    }


def _record_result(
    stats: dict, *, seat: int, winner: int | None, points: int, sources: dict
) -> None:
    stats["games"] += 1
    stats["matchPoints"] += points
    stats[f"seat{seat}Games"] += 1
    if winner is None:
        stats["draws"] += 1
    elif winner == seat:
        stats["wins"] += 1
        stats[f"seat{seat}Wins"] += 1
    else:
        stats["losses"] += 1
    stats["modelMoveClaims"] += sources["model"]
    stats["fallbackMoveClaims"] += sources["fallback"]
    stats["scriptedMoveClaims"] += sources["scripted"]
    stats["unclassifiedMoveClaims"] += sources["unclassified"]


def _move_source_claims(transcript_path: os.PathLike | str) -> list[dict]:
    counts = [
        {"model": 0, "fallback": 0, "scripted": 0, "unclassified": 0},
        {"model": 0, "fallback": 0, "scripted": 0, "unclassified": 0},
    ]
    for record in load_transcript(transcript_path):
        if record.get("kind") != "move":
            continue
        body = record.get("body") or {}
        seat = body.get("player")
        if seat not in (0, 1):
            continue
        message = body.get("entrant_message")
        note = message.get("note", "") if isinstance(message, dict) else ""
        if isinstance(note, str) and note.startswith("source=model"):
            source = "model"
        elif isinstance(note, str) and note.startswith("source=fallback"):
            source = "fallback"
        elif isinstance(note, str) and note.startswith("source=scripted"):
            source = "scripted"
        else:
            source = "unclassified"
        counts[seat][source] += 1
    return counts


def _rank(rows) -> list[dict]:
    return sorted(
        rows,
        key=lambda row: (
            -row["wins"],
            -row["draws"],
            -row["matchPoints"],
            _claim_key(row["agent"]),
            row["agentBuildId"],
        ),
    )


def _truth_status(entrants: list[dict]) -> str:
    claims = {row["executionClaim"] for row in entrants}
    if claims == {"scripted"}:
        return "scripted_preseason"
    if claims == {"model"}:
        return "model_claimed_unattested"
    return "mixed_unattested"


def run_competition(
    config: object,
    *,
    matches_dir: os.PathLike | str,
    repo_root: os.PathLike | str,
    move_timeout_s: float = 15.0,
    max_matches: int = 512,
) -> dict:
    """Run every pair, seed, and seat order and return a public-safe report."""

    _require(
        isinstance(move_timeout_s, (int, float))
        and not isinstance(move_timeout_s, bool)
        and 0.1 <= move_timeout_s <= 900,
        "move_timeout_s must be between 0.1 and 900 seconds",
    )
    _require(
        isinstance(max_matches, int) and not isinstance(max_matches, bool) and 1 <= max_matches <= 10_000,
        "max_matches must be an integer from 1 through 10000",
    )
    move_timeout_ms = int(round(move_timeout_s * 1_000))
    normalized_timeout_s = move_timeout_ms / 1_000
    normalized, entrants = _prepare(config, repo_root)
    expected_pairs = len(entrants) * (len(entrants) - 1) // 2
    expected_matches = expected_pairs * len(normalized["seeds"]) * 2
    _require(
        expected_matches <= max_matches,
        f"planned schedule has {expected_matches} matches, above the authorized max_matches ceiling",
    )
    output_root = Path(matches_dir).resolve()
    if output_root.exists():
        _require(output_root.is_dir(), "matches_dir must identify a directory")
        _require(not any(output_root.iterdir()), "matches_dir must be empty to preserve existing receipts")
    else:
        output_root.mkdir(parents=True, exist_ok=False)
    config_digest = digest(normalized)
    current_engine_digest = engine_digest()
    competition_id = "awc_" + digest(
        {
            "configDigest": config_digest,
            "engineDigest": current_engine_digest,
            "moveTimeoutMs": move_timeout_ms,
        }
    )

    overall = {row["agentBuildId"]: _empty_stats(row) for row in entrants}
    pair_stats = {}
    matches = []
    sequence = 0
    for first in range(len(entrants)):
        for second in range(first + 1, len(entrants)):
            original_pair = [entrants[first], entrants[second]]
            pair_id = _pair_id(*original_pair)
            contrast = classify_pair(*original_pair)
            pair_stats[pair_id] = {
                "pairId": pair_id,
                "contrast": contrast,
                "stats": {
                    row["agentBuildId"]: _empty_stats(row) for row in original_pair
                },
            }
            for seed in normalized["seeds"]:
                for order in (0, 1):
                    pair = original_pair if order == 0 else list(reversed(original_pair))
                    runtime_pair = [_runtime_manifest(row) for row in pair]
                    match_dir = output_root / f"{sequence:06d}"
                    result = run_match(
                        game_name=normalized["game"],
                        seed=seed,
                        entrants=runtime_pair,
                        out_dir=str(match_dir),
                        move_timeout_s=normalized_timeout_s,
                    )
                    replay = verify(result["transcript"])
                    if replay.get("verdict") != "PASS" or replay.get("engine_digest_match") is not True:
                        raise RuntimeError(
                            f"match sequence {sequence} failed exact-engine replay verification"
                        )
                    winner = result["winner"]
                    points = result.get("points") or {}
                    sources = _move_source_claims(result["transcript"])
                    for seat, entrant in enumerate(pair):
                        match_points = points.get(str(seat), 0)
                        _record_result(
                            overall[entrant["agentBuildId"]],
                            seat=seat,
                            winner=winner,
                            points=match_points,
                            sources=sources[seat],
                        )
                        _record_result(
                            pair_stats[pair_id]["stats"][entrant["agentBuildId"]],
                            seat=seat,
                            winner=winner,
                            points=match_points,
                            sources=sources[seat],
                        )
                    relative_transcript = (match_dir / Path(result["transcript"]).name).relative_to(
                        output_root
                    )
                    receipt_id = "rct_" + digest(
                        {
                            "matchId": result["match_id"],
                            "chainHead": result["chain_head"],
                            "engineDigest": current_engine_digest,
                        }
                    )
                    matches.append(
                        {
                            "sequence": sequence,
                            "receiptId": receipt_id,
                            "matchId": result["match_id"],
                            "pairId": pair_id,
                            "contrast": contrast,
                            "seed": seed,
                            "seat0": {
                                "agent": pair[0]["name"],
                                "agentBuildId": pair[0]["agentBuildId"],
                                "matchPoints": points.get("0", 0),
                            },
                            "seat1": {
                                "agent": pair[1]["name"],
                                "agentBuildId": pair[1]["agentBuildId"],
                                "matchPoints": points.get("1", 0),
                            },
                            "winner": pair[winner]["name"] if winner is not None else None,
                            "winnerAgentBuildId": (
                                pair[winner]["agentBuildId"] if winner is not None else None
                            ),
                            "reason": result["reason"],
                            "moves": result["moves"],
                            "chainHead": result["chain_head"],
                            "transcriptFile": relative_transcript.as_posix(),
                            "verified": True,
                            "engineDigestMatch": True,
                            "modelAttested": False,
                            "providerAttested": False,
                            "executionClaimsAttested": False,
                            "moveSourceClaimsAttested": False,
                            "moveSourceClaims": {
                                "seat0": sources[0],
                                "seat1": sources[1],
                            },
                        }
                    )
                    sequence += 1

    pair_summaries = []
    for pair_id in sorted(pair_stats):
        row = pair_stats[pair_id]
        pair_summaries.append(
            {
                "pairId": pair_id,
                "contrast": row["contrast"],
                "standings": _rank(row["stats"].values()),
            }
        )
    grouped = {
        "harnessControlledClaims": [],
        "modelControlledClaims": [],
        "providerControlledClaims": [],
        "openAgent": [],
    }
    group_for = {
        "harness_controlled_claim": "harnessControlledClaims",
        "model_controlled_claim": "modelControlledClaims",
        "provider_controlled_claim": "providerControlledClaims",
        "open_agent": "openAgent",
    }
    for summary in pair_summaries:
        grouped[group_for[summary["contrast"]]].append(summary)

    public_entrants = [
        {
            "name": row["name"],
            "agentBuildId": row["agentBuildId"],
            "claimedModel": row["claimedModel"],
            "modelClaimId": row["modelClaimId"],
            "claimedProvider": row["claimedProvider"],
            "providerClaimId": row["providerClaimId"],
            "executionClaim": row["executionClaim"],
            "harnessFile": row["harnessFile"],
            "harnessSha256": row["harnessSha256"],
            "harnessId": row["harnessId"],
        }
        for row in entrants
    ]
    standings = _rank(overall.values())
    seat_balanced = all(row["seat0Games"] == row["seat1Games"] for row in standings)
    return {
        "schemaVersion": REPORT_SCHEMA_VERSION,
        "competitionId": competition_id,
        "configDigest": config_digest,
        "competition": normalized["competition"],
        "description": normalized["description"],
        "game": normalized["game"],
        "engineDigest": current_engine_digest,
        "status": _truth_status(entrants),
        "executionPolicy": {
            "moveTimeoutMs": move_timeout_ms,
            "authorizedMatchCeiling": max_matches,
        },
        "truthBoundary": {
            "replayVerified": True,
            "exactEngineDigestRequired": True,
            "harnessFileDigestVerified": True,
            "modelAttested": False,
            "providerAttested": False,
            "executionClaimsAttested": False,
            "moveSourceClaimsAttested": False,
            "controlledClaimsAreCausalProof": False,
            "untrustedEntrantIsolationAttested": False,
            "proves": [
                "each published match replays under the exact refereeing engine",
                "every entrant pair received every seed in both seat orders",
                "the executable harness file digest is bound to each agent build",
                "the recorded outcome follows from referee state rather than entrant self-report",
            ],
            "doesNotProve": [
                "that a claimed model or provider produced any move",
                "that a controlled-claim contrast establishes a causal model, provider, or harness effect",
                "that execution claims or move provenance were independently witnessed",
                "that v1 confines untrusted entrants at the network, filesystem, CPU, or memory layer",
            ],
        },
        "entrants": public_entrants,
        "schedule": {
            "seeds": normalized["seeds"],
            "entrantCount": len(entrants),
            "expectedPairs": expected_pairs,
            "completedPairs": len(pair_summaries),
            "matchesPerPairSeed": 2,
            "expectedMatches": expected_matches,
            "completedMatches": len(matches),
            "verifiedMatches": len(matches),
            "seatBalanced": seat_balanced,
            "coverageDigest": digest(
                [
                    {
                        "pairId": row["pairId"],
                        "seed": row["seed"],
                        "seat0": row["seat0"]["agentBuildId"],
                        "seat1": row["seat1"]["agentBuildId"],
                    }
                    for row in matches
                ]
            ),
        },
        "agentStandings": standings,
        "comparisons": grouped,
        "matches": matches,
        "publicationPolicy": {
            "globalProviderLeaderboardPublished": False,
            "providerClaimsComparedOnlyWithin": "provider_controlled_claim",
            "modelClaimsComparedOnlyWithin": "model_controlled_claim",
            "openAgentMatchesAffectAgentStandingsOnly": True,
        },
    }


def render_report(report: dict) -> str:
    return json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def write_report(report: dict, path: os.PathLike | str) -> None:
    output = Path(path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    _require(not output.exists(), "report path already exists; receipts are immutable")
    with open(output, "x", encoding="utf-8", newline="\n") as handle:
        handle.write(render_report(report))
