"""Versioned AgentWars product dataset and atomic publication artifact."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from collections import defaultdict
from datetime import datetime
from typing import Any

from arena.canonical import digest

from .projection import (
    HEX64_RE,
    PublicationError,
    file_sha256,
    json_text,
    project_receipt,
    public_clip,
    source_counts_digest,
)

PUBLICATION_MANIFEST_SCHEMA = "agentwars.publication-manifest.v1"
DATASET_SCHEMA = "agentwars.public-product.v1"
SOURCE_MANIFEST_SCHEMA = "agentwars.public-source-manifest.v1"
INSTALL_MANIFEST_SCHEMA = "agentwars.public-install-manifest.v1"
SAFE_COMPONENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
CLIP_ID_RE = re.compile(r"^clip_[0-9a-f]{16}$")
UTC_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
DECISIONS = frozenset({"approved_for_publication", "eligible_for_review", "held"})
ENTRY_KEYS = frozenset(
    {
        "sequence",
        "sourcePath",
        "sourceFileSha256",
        "sourceChainHead",
        "sourceCounts",
        "decision",
        "titleEligible",
        "label",
    }
)

RULES_WEEKS = (
    {
        "rulesWeekId": "agentwars-redraft-core-v1",
        "registryVersion": "1",
        "week": 1,
        "game": "fantasy_redraft",
        "gameVersion": "1",
        "label": "Redraft Opening Week",
        "status": "playable",
        "integerOnlyScoring": True,
        "rule": "One-season roster points decide the match.",
    },
    {
        "rulesWeekId": "agentwars-dynasty-core-v1",
        "registryVersion": "1",
        "week": 2,
        "game": "fantasy_dynasty",
        "gameVersion": "1",
        "label": "Dynasty Window",
        "status": "playable",
        "integerOnlyScoring": True,
        "rule": "Three-year roster value decides the match.",
    },
    {
        "rulesWeekId": "fantasy_qb_surge_v1",
        "registryVersion": "1",
        "week": 3,
        "game": "fantasy_qb_surge",
        "gameVersion": "1",
        "label": "New Rules Week: QB Surge",
        "status": "playable",
        "integerOnlyScoring": True,
        "rule": "The roster quarterback's one-season points count exactly twice.",
    },
)


def _load_json(path: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise PublicationError(f"could not load publication manifest: {error.__class__.__name__}") from error


def _build_integrity(repo_root: str, publication_manifest_path: str) -> dict[str, str]:
    try:
        completed = subprocess.run(
            ["git", "-C", repo_root, "rev-parse", "HEAD"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise PublicationError("could not resolve source repository commit") from error
    source_commit = completed.stdout.strip().lower()
    if completed.returncode != 0 or re.fullmatch(r"[0-9a-f]{40}", source_commit) is None:
        raise PublicationError("source repository commit is unavailable or malformed")
    paths = {
        "publicationManifestFileSha256": publication_manifest_path,
        "datasetBuilderSha256": os.path.join(repo_root, "bin", "build_public_dataset.py"),
        "productExporterSha256": os.path.join(repo_root, "publishing", "product.py"),
        "siteExporterSha256": os.path.join(repo_root, "bin", "export_site.py"),
        "projectionSha256": os.path.join(repo_root, "publishing", "projection.py"),
        "verifierSha256": os.path.join(repo_root, "verify.py"),
    }
    if any(not os.path.isfile(path) for path in paths.values()):
        raise PublicationError("an integrity-envelope source file is missing")
    return {
        "sourceCommit": source_commit,
        **{label: file_sha256(path) for label, path in paths.items()},
    }


def _validate_build_integrity(value: Any) -> dict[str, str]:
    keys = {
        "sourceCommit",
        "publicationManifestFileSha256",
        "datasetBuilderSha256",
        "productExporterSha256",
        "siteExporterSha256",
        "projectionSha256",
        "verifierSha256",
    }
    if not isinstance(value, dict) or set(value) != keys:
        raise PublicationError("build integrity envelope shape is invalid")
    if re.fullmatch(r"[0-9a-f]{40}", value["sourceCommit"]) is None:
        raise PublicationError("sourceCommit must be full lowercase git sha1")
    if any(HEX64_RE.fullmatch(value[key]) is None for key in keys - {"sourceCommit"}):
        raise PublicationError("build integrity file hashes must be lowercase sha256")
    return dict(value)


def _safe_relative_source(repo_root: str, value: Any) -> str:
    """Validate before path construction, then prove the result stays in repo."""
    if not isinstance(value, str) or not value or len(value) > 500:
        raise PublicationError("sourcePath must be a bounded repository-relative string")
    if "\\" in value or value.startswith("/") or ":" in value:
        raise PublicationError("sourcePath must use safe relative POSIX components")
    parts = value.split("/")
    if (
        parts[0] != "matches"
        or any(part in ("", ".", "..") or SAFE_COMPONENT_RE.fullmatch(part) is None for part in parts)
        or not value.endswith(".jsonl")
        or value.endswith(".diagnostics.jsonl")
    ):
        raise PublicationError("sourcePath is not an allowlisted transcript path shape")
    absolute = os.path.abspath(os.path.join(repo_root, *parts))
    root = os.path.abspath(repo_root)
    if os.path.commonpath([root, absolute]) != root:
        raise PublicationError("sourcePath escapes the repository")
    return absolute


def _validate_source_totals(value: Any) -> dict[str, int]:
    keys = ("model", "fallback", "scripted", "other")
    if not isinstance(value, dict) or set(value) != set(keys):
        raise PublicationError("sourceCounts must contain exactly model/fallback/scripted/other")
    if any(not isinstance(value[key], int) or isinstance(value[key], bool) or value[key] < 0 for key in keys):
        raise PublicationError("sourceCounts values must be non-negative integers")
    return {key: value[key] for key in keys}


def load_publication_manifest(repo_root: str, path: str) -> dict[str, Any]:
    payload = _load_json(path)
    if not isinstance(payload, dict) or payload.get("schemaVersion") != PUBLICATION_MANIFEST_SCHEMA:
        raise PublicationError("unsupported publication manifest schema")
    if set(payload) != {
        "schemaVersion", "datasetVersion", "policy", "entries", "futureFixtures"
    }:
        raise PublicationError("publication manifest contains unexpected top-level fields")
    if payload.get("datasetVersion") != "1":
        raise PublicationError("unsupported dataset version")
    if payload.get("policy") != "explicit_reviewed_allowlist_only":
        raise PublicationError("publication selector must be the explicit reviewed allowlist")
    future_fixtures = payload.get("futureFixtures")
    if not isinstance(future_fixtures, list) or not 1 <= len(future_fixtures) <= 16:
        raise PublicationError("futureFixtures must contain 1 through 16 explicit descriptors")
    future_keys = {
        "leagueId", "week", "game", "gameVersion", "rulesVersion", "seed",
        "entrantIdsBySeat", "closeAt", "status", "activationStatus",
    }
    seen_future = set()
    for fixture in future_fixtures:
        if not isinstance(fixture, dict) or set(fixture) != future_keys:
            raise PublicationError("future fixture descriptor shape is invalid")
        if fixture.get("status") != "unplayed":
            raise PublicationError("future fixture status must be unplayed")
        if fixture.get("activationStatus") not in ("proposed_not_activated", "open"):
            raise PublicationError("future fixture activation status is invalid")
        for key in ("leagueId", "game", "gameVersion", "rulesVersion"):
            if not isinstance(fixture.get(key), str) or SAFE_COMPONENT_RE.fullmatch(fixture[key]) is None:
                raise PublicationError(f"future fixture {key} is unsafe")
        week, seed = fixture.get("week"), fixture.get("seed")
        if not isinstance(week, int) or isinstance(week, bool) or not 1 <= week <= 99:
            raise PublicationError("future fixture week must be a bounded integer")
        if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed <= 2_147_483_647:
            raise PublicationError("future fixture seed must be a bounded integer")
        seats = fixture.get("entrantIdsBySeat")
        if (
            not isinstance(seats, list)
            or len(seats) != 2
            or len(set(seats)) != 2
            or any(not isinstance(value, str) or HEX64_RE.fullmatch(value) is None for value in seats)
        ):
            raise PublicationError("future fixture entrantIdsBySeat must contain two distinct ids")
        close_at = fixture.get("closeAt")
        if not isinstance(close_at, str) or UTC_TIME_RE.fullmatch(close_at) is None:
            raise PublicationError("future fixture closeAt must be a fixed UTC timestamp")
        try:
            datetime.strptime(close_at, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError as error:
            raise PublicationError("future fixture closeAt is not a valid calendar timestamp") from error
        identity = (fixture["leagueId"], week)
        if identity in seen_future:
            raise PublicationError("future fixture league/week repeats")
        seen_future.add(identity)
    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        raise PublicationError("publication manifest requires explicit entries")
    normalized = []
    sequences, source_paths = set(), set()
    for raw in entries:
        if not isinstance(raw, dict) or set(raw) != ENTRY_KEYS:
            raise PublicationError("publication entry shape is invalid")
        sequence = raw.get("sequence")
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0 or sequence in sequences:
            raise PublicationError("publication entry sequence must be a unique non-negative integer")
        sequences.add(sequence)
        source_path = raw.get("sourcePath")
        absolute = _safe_relative_source(repo_root, source_path)
        if source_path in source_paths:
            raise PublicationError("publication manifest repeats a sourcePath")
        source_paths.add(source_path)
        for key in ("sourceFileSha256", "sourceChainHead"):
            if not isinstance(raw.get(key), str) or HEX64_RE.fullmatch(raw[key]) is None:
                raise PublicationError(f"{key} must be lowercase sha256")
        decision = raw.get("decision")
        if decision not in DECISIONS:
            raise PublicationError("publication decision is unsupported")
        title_eligible = raw.get("titleEligible")
        if not isinstance(title_eligible, bool):
            raise PublicationError("titleEligible must be boolean")
        label = raw.get("label")
        if not isinstance(label, str) or not label or len(label) > 120:
            raise PublicationError("publication label must be a bounded string")
        normalized.append(
            {
                **raw,
                "absoluteSourcePath": absolute,
                "sourceCounts": _validate_source_totals(raw.get("sourceCounts")),
            }
        )
    normalized.sort(key=lambda item: item["sequence"])
    if [item["sequence"] for item in normalized] != list(range(len(normalized))):
        raise PublicationError("publication sequences must be contiguous from zero")
    return {**payload, "entries": normalized, "manifestDigest": digest(payload)}


def _source_totals(receipt: dict[str, Any]) -> dict[str, int]:
    return {
        key: sum(row[key] for row in receipt["moveSourceClaims"])
        for key in ("model", "fallback", "scripted", "other")
    }


def _fixture_core(receipt: dict[str, Any], seed: int, seats: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schemaVersion": "agentwars.fixture-identity.v1",
        "game": {"name": receipt["game"]["name"], "version": receipt["game"]["version"]},
        "seed": seed,
        "seats": [
            {"entrantId": row["entrantId"], "harnessVersionId": row["harnessVersionId"]}
            for row in seats
        ],
    }


def _runback(receipt: dict[str, Any]) -> dict[str, Any]:
    seed = receipt["seed"] + 1
    if seed > 2_147_483_647:
        raise PublicationError("cannot derive bounded runback seed")
    seats = list(reversed(receipt["entrants"]))
    fixture_id = digest(_fixture_core(receipt, seed, seats))
    core = {
        "parentReceiptId": receipt["receiptId"],
        "fixtureId": fixture_id,
        "game": receipt["game"],
        "seed": seed,
        "entrantIdsBySeat": [row["entrantId"] for row in seats],
    }
    return {
        "status": "unplayed_challenge",
        "challengeId": "challenge_" + digest(core)[:16],
        **core,
    }


def _rivalry_key(receipt: dict[str, Any]) -> tuple[str, tuple[str, str]]:
    competition = "agentwars-fantasy" if receipt["game"]["name"].startswith("fantasy_") else receipt["game"]["name"]
    entrant_ids = tuple(sorted(row["entrantId"] for row in receipt["entrants"]))
    return competition, entrant_ids


def build_rivalries(receipts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, tuple[str, str]], list[dict[str, Any]]] = defaultdict(list)
    for receipt in receipts:
        grouped[_rivalry_key(receipt)].append(receipt)
    rivalries = []
    for (competition, entrant_ids), meetings in sorted(grouped.items()):
        rivalry_id = digest(
            {"schemaVersion": "agentwars.rivalry.v1", "competition": competition, "entrantIds": entrant_ids}
        )
        history = []
        for index, receipt in enumerate(meetings, 1):
            history.append(
                {
                    "meetingNumber": index,
                    "receiptId": receipt["receiptId"],
                    "fixtureId": receipt["fixtureId"],
                    "game": receipt["game"]["name"],
                    "winnerEntrantId": receipt["outcome"]["winnerEntrantId"],
                    "runback": _runback(receipt),
                }
            )
        rivalries.append(
            {
                "schemaVersion": "agentwars.rivalry-history.v1",
                "rivalryId": rivalry_id,
                "competition": competition,
                "entrantIds": list(entrant_ids),
                "meetingCount": len(history),
                "history": history,
            }
        )
    return rivalries


def _title_state(
    receipts: list[dict[str, Any]], title_eligible: set[str], game: str, name: str
) -> dict[str, Any]:
    holder = None
    history = []
    table: dict[str, dict[str, int]] = defaultdict(
        lambda: {"wins": 0, "losses": 0, "ties": 0, "pointsFor": 0}
    )
    for receipt in receipts:
        if receipt["game"]["name"] != game:
            continue
        if receipt["outcome"].get("status") != "final":
            continue
        entrant_ids = [row["entrantId"] for row in receipt["entrants"]]
        scores = receipt["outcome"]["scores"]
        winner = receipt["outcome"]["winnerEntrantId"]
        for seat, entrant_id in enumerate(entrant_ids):
            if scores is not None:
                table[entrant_id]["pointsFor"] += scores[seat]
            if winner is None:
                table[entrant_id]["ties"] += 1
            elif winner == entrant_id:
                table[entrant_id]["wins"] += 1
            else:
                table[entrant_id]["losses"] += 1
        if receipt["receiptId"] not in title_eligible or winner is None:
            continue
        if holder is None or holder in entrant_ids:
            prior = holder
            holder = winner
            history.append(
                {
                    "receiptId": receipt["receiptId"],
                    "previousHolderEntrantId": prior,
                    "holderEntrantId": holder,
                    "action": "inaugural_custody" if prior is None else (
                        "retained" if prior == holder else "changed_hands"
                    ),
                }
            )
    leaderboard = [
        {"entrantId": entrant_id, **row}
        for entrant_id, row in table.items()
    ]
    leaderboard.sort(
        key=lambda row: (-row["wins"], -row["ties"], -row["pointsFor"], row["entrantId"])
    )
    basis_receipt_ids = [
        receipt["receiptId"]
        for receipt in receipts
        if receipt["game"]["name"] == game and receipt["receiptId"] in title_eligible
    ]
    title = {
        "schemaVersion": "agentwars.title-custody.v1",
        "title": name,
        "game": game,
        "holderEntrantId": holder,
        "leaderEntrantId": leaderboard[0]["entrantId"] if leaderboard else None,
        "custodyRule": (
            "The first title-eligible decisive receipt creates custody. Custody changes only "
            "when the holder participates in a later title-eligible decisive receipt."
        ),
        "leaderRule": "Wins, then ties, then integer points-for, then entrantId ascending.",
        "basisReceiptIds": basis_receipt_ids,
        "basisPolicy": "explicit publication allowlist plus titleEligible=true",
        "history": history,
        "leaderboard": leaderboard,
    }
    title["basisDigest"] = digest(
        {
            "basisReceiptIds": basis_receipt_ids,
            "history": history,
            "leaderboard": leaderboard,
        }
    )
    return title


def _teaser(receipt: dict[str, Any]) -> dict[str, Any]:
    entrants = [
        {"seat": row["seat"], "entrantId": row["entrantId"], "name": row["name"]}
        for row in receipt["entrants"]
    ]
    reveal_core = {
        "receiptId": receipt["receiptId"],
        "projectionDigest": receipt["projectionDigest"],
    }
    return {
        "schemaVersion": "agentwars.teaser.v1",
        "receiptId": receipt["receiptId"],
        "fixtureId": receipt["fixtureId"],
        "game": receipt["game"],
        "seed": receipt["seed"],
        "entrants": entrants,
        "status": "reveal_available",
        "revealCommitment": digest(reveal_core),
        "question": f"{entrants[0]['name']} vs {entrants[1]['name']}: pick a side before the receipt reveal.",
        "modelAttested": False,
    }


def _rules_registry(receipts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for registered in RULES_WEEKS:
        candidates = [row for row in receipts if row["game"]["name"] == registered["game"]]
        if not candidates:
            raise PublicationError(f"rules registry lacks an approved proof receipt: {registered['game']}")
        engine_digests = {row["verification"]["engineDigest"] for row in candidates}
        game_versions = {row["game"]["version"] for row in candidates}
        if len(engine_digests) != 1 or game_versions != {registered["gameVersion"]}:
            raise PublicationError("rules registry proof receipts disagree on engine or game version")
        core = {
            **registered,
            "verifierSnapshotDigest": next(iter(engine_digests)),
            "verifierSnapshotAvailable": True,
            "basisReceiptIds": [row["receiptId"] for row in candidates],
        }
        rows.append({**core, "rulesDigest": digest(core)})
    return rows


def _future_fixtures(
    receipts: list[dict[str, Any]],
    manifest_fixtures: list[dict[str, Any]],
    rules_registry: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    entrant_names = {
        entrant["entrantId"]: entrant["name"]
        for receipt in receipts
        for entrant in receipt["entrants"]
    }
    rules_by_game = {row["game"]: row for row in rules_registry}
    fixtures = []
    for raw in manifest_fixtures:
        if raw["game"] not in rules_by_game:
            raise PublicationError(f"future fixture game is absent from rules registry: {raw['game']}")
        if raw["rulesVersion"] != rules_by_game[raw["game"]]["registryVersion"]:
            raise PublicationError("future fixture rulesVersion disagrees with registry")
        if any(entrant_id not in entrant_names for entrant_id in raw["entrantIdsBySeat"]):
            raise PublicationError("future fixture references an unknown public entrantId")
        core = {
            "schemaVersion": "agentwars.future-fixture.v1",
            "status": "unplayed",
            "activationStatus": raw["activationStatus"],
            "leagueId": raw["leagueId"],
            "week": raw["week"],
            "game": {"name": raw["game"], "version": raw["gameVersion"]},
            "format": raw["game"].removeprefix("fantasy_"),
            "rulesVersion": raw["rulesVersion"],
            "rulesWeekId": rules_by_game[raw["game"]]["rulesWeekId"],
            "rulesDigest": rules_by_game[raw["game"]]["rulesDigest"],
            "verifierSnapshotDigest": rules_by_game[raw["game"]]["verifierSnapshotDigest"],
            "seed": raw["seed"],
            "entrantIdsBySeat": raw["entrantIdsBySeat"],
            "closeAt": raw["closeAt"],
        }
        fixture_id = digest(core)
        activation_open = raw["activationStatus"] == "open"
        fixtures.append(
            {
                **core,
                "fixtureId": fixture_id,
                "matchup": [
                    {"seat": seat, "entrantId": entrant_id, "name": entrant_names[entrant_id]}
                    for seat, entrant_id in enumerate(raw["entrantIdsBySeat"])
                ],
                "prediction": {
                    "status": "open" if activation_open else "closed_proposed_not_activated",
                    "schemaVersion": "agentwars.prediction-commitment.v1",
                    "requiredFields": [
                        "fixtureId", "selectionEntrantId", "committedAt", "nonceHash", "commitmentDigest"
                    ],
                    "timestampAuthority": "publishing_site_server",
                    "committedAtSemantics": (
                        "The server writes committedAt on acceptance; client timestamps are ignored."
                    ),
                    "commitmentRule": (
                        "commitmentDigest = sha256(canonical fixtureId, selectionEntrantId, "
                        "server committedAt, and nonceHash); committedAt must be before closeAt."
                    ),
                },
            }
        )
    return fixtures


def _interaction_manifest(
    approved: list[dict[str, Any]],
    clips: list[dict[str, Any]],
    future_fixtures: list[dict[str, Any]],
    rules_registry: list[dict[str, Any]],
    publication_manifest_digest: str,
) -> dict[str, Any]:
    campaign_id = "agentwars_launch_v1"
    source_label = "agentwars_share"
    clip_by_receipt = {row["receiptId"]: row for row in clips}
    rules_by_game = {row["game"]: row for row in rules_registry}
    played = []
    for row in approved:
        receipt, source = row["receipt"], row["source"]
        clip = clip_by_receipt[receipt["receiptId"]]
        creative_id = "moment_" + digest(
            {"campaignId": campaign_id, "receiptId": receipt["receiptId"], "clipId": clip["clipId"]}
        )[:16]
        played.append(
            {
                "kind": "played",
                "receiptId": receipt["receiptId"],
                "fixtureId": receipt["fixtureId"],
                "clipId": clip["clipId"],
                "campaignId": campaign_id,
                "sourceLabel": source_label,
                "creativeId": creative_id,
                "rulesVersion": rules_by_game.get(receipt["game"]["name"], {}).get(
                    "registryVersion", receipt["game"]["version"]
                ),
                "fixtureStatus": "played",
                "publicationEvidence": {
                    "decision": "approved_for_publication",
                    "publicationManifestDigest": publication_manifest_digest,
                    "sourceFileSha256": source["sourceFileSha256"],
                    "sourceChainHead": source["sourceChainHead"],
                    "sourceCountsDigest": source["sourceCountsDigest"],
                    "publicTranscriptPath": source["publicTranscriptPath"],
                    "publicTranscriptSha256": source["publicTranscriptSha256"],
                    "publicTranscriptBytes": source["publicTranscriptBytes"],
                    "shareManifestHash": source["shareManifestHash"],
                    "engineDigest": source["engineDigest"],
                    "verifierSnapshotDigest": source["verifierSnapshotDigest"],
                    "verification": source["verification"],
                },
            }
        )
    future = []
    for row in future_fixtures:
        attribution = {
            "campaignId": campaign_id,
            "fixtureId": row["fixtureId"],
            "rulesVersion": row["rulesVersion"],
            "rulesWeekId": row["rulesWeekId"],
            "rulesDigest": row["rulesDigest"],
            "verifierSnapshotDigest": row["verifierSnapshotDigest"],
        }
        future.append({
            "kind": "future",
            "fixtureId": row["fixtureId"],
            "campaignId": campaign_id,
            "creativeId": "prediction_" + digest(attribution)[:16],
            "rulesVersion": row["rulesVersion"],
            "rulesWeekId": row["rulesWeekId"],
            "rulesDigest": row["rulesDigest"],
            "verifierSnapshotDigest": row["verifierSnapshotDigest"],
            "status": row["status"],
            "activationStatus": row["activationStatus"],
            "closeAt": row["closeAt"],
            "leagueId": row["leagueId"],
            "week": row["week"],
            "game": row["game"],
            "format": row["format"],
            "matchup": row["matchup"],
        })
    core = {
        "schemaVersion": "agentwars.interaction-manifest.v1",
        "campaignId": campaign_id,
        "sourceLabel": source_label,
        "playedArtifacts": played,
        "futureFixtures": future,
    }
    return {**core, "fingerprint": digest(core)}


def assemble_dataset(
    approved: list[dict[str, Any]],
    *,
    publication_manifest_digest: str,
    eligible_for_review: list[dict[str, Any]],
    title_eligible: set[str],
    future_fixtures: list[dict[str, Any]],
    build_integrity: dict[str, str],
) -> dict[str, Any]:
    build_integrity = _validate_build_integrity(build_integrity)
    receipt_ids = [row["receipt"]["receiptId"] for row in approved]
    if len(receipt_ids) != len(set(receipt_ids)):
        raise PublicationError("approved corpus contains a duplicate receiptId")
    if any(HEX64_RE.fullmatch(value) is None for value in receipt_ids):
        raise PublicationError("receiptId must be a full lowercase chain head")
    if any(HEX64_RE.fullmatch(row["receipt"]["fixtureId"]) is None for row in approved):
        raise PublicationError("fixtureId must be a full lowercase deterministic digest")
    clips = [public_clip(row["receipt"], row["records"]) for row in approved]
    if len({row["clipId"] for row in clips}) != len(clips):
        raise PublicationError("clip ids collide")
    receipts = [row["receipt"] for row in approved]
    source_rows = [row["source"] for row in approved]
    rules_rows = _rules_registry(receipts)
    future_rows = _future_fixtures(receipts, future_fixtures, rules_rows)
    interaction_manifest = _interaction_manifest(
        approved, clips, future_rows, rules_rows, publication_manifest_digest
    )
    sorted_receipt_ids = sorted(receipt_ids)
    core = {
        "schemaVersion": DATASET_SCHEMA,
        "datasetVersion": "1",
        "product": "AgentWars",
        "buildIntegrity": build_integrity,
        "digestContract": {
            "algorithm": "sha256",
            "canonicalization": "UTF-8 JSON; object keys sorted; no insignificant whitespace; floats forbidden",
            "recompute": "Remove datasetDigest, canonicalize the remaining top-level object, then sha256 the bytes.",
        },
        "verificationContract": {
            "transcriptRouteTemplate": "public/m/{receiptId}.jsonl",
            "requiredPredicates": [
                "replay_verdict=PASS",
                "engine_digest_match=true",
                "verifier_snapshot_match=true",
            ],
            "successExitCode": 0,
        },
        "publication": {
            "policy": "explicit_reviewed_allowlist_only",
            "manifestDigest": publication_manifest_digest,
            "approvedReceiptIds": sorted_receipt_ids,
            "approvedReceiptCount": len(sorted_receipt_ids),
            "approvedReceiptSetDigest": digest(sorted_receipt_ids),
            "eligibleForReview": eligible_for_review,
            "verifiedDoesNotImplyPublished": True,
        },
        "truthBoundary": {
            "modelAttested": False,
            "statement": (
                "Every published receipt exactly matches an embedded referee snapshot. "
                "Publication approval is a separate explicit allowlist decision."
            ),
        },
        "receipts": receipts,
        "teasers": [_teaser(receipt) for receipt in receipts],
        "clips": clips,
        "interactionManifest": interaction_manifest,
        "interactionManifestFingerprint": interaction_manifest["fingerprint"],
        "rivalries": build_rivalries(receipts),
        "titles": {
            "redraftCrown": _title_state(receipts, title_eligible, "fantasy_redraft", "Redraft Crown"),
            "dynastyThrone": _title_state(receipts, title_eligible, "fantasy_dynasty", "Dynasty Throne"),
        },
        "futureFixtures": future_rows,
        "rulesWeeks": rules_rows,
        "sourceDigest": digest(source_rows),
    }
    core["datasetDigest"] = digest(core)
    return core


def build_product(repo_root: str, publication_manifest_path: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, bytes]]:
    repo_root = os.path.abspath(repo_root)
    publication = load_publication_manifest(repo_root, publication_manifest_path)
    build_integrity = _build_integrity(repo_root, publication_manifest_path)
    approved, eligible = [], []
    title_eligible: set[str] = set()
    for entry in publication["entries"]:
        if entry["decision"] != "approved_for_publication":
            eligible.append(
                {
                    "sequence": entry["sequence"],
                    "sourcePath": entry["sourcePath"],
                    "decision": entry["decision"],
                    "label": entry["label"],
                }
            )
            continue
        path = entry["absoluteSourcePath"]
        actual_file_hash = file_sha256(path)
        if actual_file_hash != entry["sourceFileSha256"]:
            raise PublicationError(f"source file hash parity failed: {entry['sourcePath']}")
        receipt, records = project_receipt(path)
        if receipt["receiptId"] != entry["sourceChainHead"]:
            raise PublicationError(f"source chain-head parity failed: {entry['sourcePath']}")
        totals = _source_totals(receipt)
        if totals != entry["sourceCounts"]:
            raise PublicationError(f"move-source count parity failed: {entry['sourcePath']}")
        source = {
            "sequence": entry["sequence"],
            "sourcePath": entry["sourcePath"],
            "sourceFileSha256": actual_file_hash,
            "sourceChainHead": receipt["receiptId"],
            "sourceCounts": totals,
            "sourceCountsDigest": source_counts_digest(receipt["moveSourceClaims"]),
            "receiptId": receipt["receiptId"],
            "fixtureId": receipt["fixtureId"],
            "publicTranscriptPath": receipt["transcript"]["relativePath"],
            "publicTranscriptSha256": receipt["transcript"]["sha256"],
            "publicTranscriptBytes": receipt["transcript"]["bytes"],
            "shareManifestHash": receipt["shareManifestHash"],
            "engineDigest": receipt["verification"]["engineDigest"],
            "verifierSnapshotDigest": receipt["verification"]["verifierSnapshotDigest"],
            "verification": {
                "replayVerdict": receipt["verification"]["replayVerdict"],
                "engineDigestMatch": receipt["verification"]["engineDigestMatch"],
                "verifierSnapshotMatch": receipt["verification"]["verifierSnapshotMatch"],
                "effectiveVerdict": receipt["verification"]["effectiveVerdict"],
            },
            "label": entry["label"],
        }
        approved.append({"receipt": receipt, "records": records, "source": source, "path": path})
        if entry["titleEligible"]:
            title_eligible.add(receipt["receiptId"])
    if not approved:
        raise PublicationError("publication allowlist approves no receipts")
    dataset = assemble_dataset(
        approved,
        publication_manifest_digest=publication["manifestDigest"],
        eligible_for_review=eligible,
        title_eligible=title_eligible,
        future_fixtures=publication["futureFixtures"],
        build_integrity=build_integrity,
    )
    sources = [row["source"] for row in approved]
    source_manifest_core = {
        "schemaVersion": SOURCE_MANIFEST_SCHEMA,
        "datasetDigest": dataset["datasetDigest"],
        "publicationManifestDigest": publication["manifestDigest"],
        "sourceDigest": dataset["sourceDigest"],
        "interactionManifestFingerprint": dataset["interactionManifestFingerprint"],
        "buildIntegrity": dataset["buildIntegrity"],
        "approvedReceiptIds": dataset["publication"]["approvedReceiptIds"],
        "approvedReceiptCount": dataset["publication"]["approvedReceiptCount"],
        "entries": sources,
    }
    source_manifest = {**source_manifest_core, "manifestDigest": digest(source_manifest_core)}
    outputs: dict[str, bytes] = {
        "dataset.json": json_text(dataset).encode("utf-8"),
        "source-manifest.json": json_text(source_manifest).encode("utf-8"),
        "public/dataset.json": json_text(dataset).encode("utf-8"),
        "public/verify.py": open(os.path.join(repo_root, "verify.py"), "rb").read(),
    }
    receipt_by_id = {row["receiptId"]: row for row in dataset["receipts"]}
    teaser_by_id = {row["receiptId"]: row for row in dataset["teasers"]}
    clips_by_receipt: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for clip in dataset["clips"]:
        clips_by_receipt[clip["receiptId"]].append(clip)
        outputs[f"public/clips/{clip['clipId']}.json"] = json_text(clip).encode("utf-8")
    for row in approved:
        receipt_id = row["receipt"]["receiptId"]
        if HEX64_RE.fullmatch(receipt_id) is None:
            raise PublicationError("unsafe receiptId rejected before output path construction")
        outputs[f"public/m/{receipt_id}.jsonl"] = open(row["path"], "rb").read()
        outputs[f"public/receipts/{receipt_id}.json"] = json_text(receipt_by_id[receipt_id]).encode("utf-8")
        outputs[f"public/teasers/{receipt_id}.json"] = json_text(teaser_by_id[receipt_id]).encode("utf-8")
    return dataset, source_manifest, outputs


def _safe_output_relpath(value: str) -> list[str]:
    if not isinstance(value, str) or "\\" in value or value.startswith("/") or ":" in value:
        raise PublicationError("artifact output path is unsafe")
    parts = value.split("/")
    if any(part in ("", ".", "..") or SAFE_COMPONENT_RE.fullmatch(part) is None for part in parts):
        raise PublicationError("artifact output path is unsafe")
    return parts


def _assert_child(parent: str, child: str) -> None:
    if os.path.commonpath([os.path.abspath(parent), os.path.abspath(child)]) != os.path.abspath(parent):
        raise PublicationError("artifact operation escaped its parent")


def verify_artifact(path: str) -> dict[str, Any]:
    root = os.path.abspath(path)
    install_path = os.path.join(root, "install-manifest.json")
    payload = _load_json(install_path)
    if not isinstance(payload, dict) or payload.get("schemaVersion") != INSTALL_MANIFEST_SCHEMA:
        raise PublicationError("artifact install manifest is invalid")
    files = payload.get("files")
    if not isinstance(files, list):
        raise PublicationError("artifact install file list is invalid")
    expected = {"install-manifest.json"}
    for row in files:
        if not isinstance(row, dict) or set(row) != {"path", "sha256", "bytes"}:
            raise PublicationError("artifact install row is invalid")
        parts = _safe_output_relpath(row["path"])
        target = os.path.abspath(os.path.join(root, *parts))
        _assert_child(root, target)
        if not os.path.isfile(target) or file_sha256(target) != row["sha256"]:
            raise PublicationError(f"artifact file parity failed: {row['path']}")
        if os.path.getsize(target) != row["bytes"]:
            raise PublicationError(f"artifact byte length parity failed: {row['path']}")
        expected.add(row["path"])
    actual = set()
    for directory, _dirs, names in os.walk(root):
        for name in names:
            rel = os.path.relpath(os.path.join(directory, name), root).replace(os.sep, "/")
            actual.add(rel)
    if actual != expected:
        raise PublicationError(
            f"artifact contains stale or missing files: extra={sorted(actual - expected)} missing={sorted(expected - actual)}"
        )
    return payload


def write_public_artifact(repo_root: str, publication_manifest_path: str, destination: str) -> dict[str, Any]:
    dataset, source_manifest, outputs = build_product(repo_root, publication_manifest_path)
    target = os.path.abspath(destination)
    parent = os.path.dirname(target)
    if target == parent or not os.path.basename(target):
        raise PublicationError("artifact destination must be a named child directory")
    os.makedirs(parent, exist_ok=True)
    staging = tempfile.mkdtemp(prefix=".agentwars-public-stage-", dir=parent)
    _assert_child(parent, staging)
    backup = None
    try:
        for rel, content in sorted(outputs.items()):
            parts = _safe_output_relpath(rel)
            path = os.path.join(staging, *parts)
            _assert_child(staging, path)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as handle:
                handle.write(content)
        install_rows = [
            {"path": rel, "sha256": file_sha256(os.path.join(staging, *rel.split("/"))), "bytes": len(content)}
            for rel, content in sorted(outputs.items())
        ]
        install_core = {
            "schemaVersion": INSTALL_MANIFEST_SCHEMA,
            "datasetDigest": dataset["datasetDigest"],
            "sourceManifestDigest": source_manifest["manifestDigest"],
            "interactionManifestFingerprint": dataset["interactionManifestFingerprint"],
            "buildIntegrity": dataset["buildIntegrity"],
            "sitePublicPath": "public/builderwars",
            "siteDatasetPath": "src/data/builderwars.generated.json",
            "files": install_rows,
        }
        with open(os.path.join(staging, "install-manifest.json"), "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json_text({**install_core, "installDigest": digest(install_core)}))
        verify_artifact(staging)
        if os.path.exists(target):
            backup = tempfile.mkdtemp(prefix=".agentwars-public-backup-", dir=parent)
            os.rmdir(backup)
            _assert_child(parent, backup)
            os.replace(target, backup)
        os.replace(staging, target)
        staging = ""
        try:
            verified = verify_artifact(target)
        except Exception:
            if backup and os.path.exists(backup):
                rejected = tempfile.mkdtemp(prefix=".agentwars-public-rejected-", dir=parent)
                os.rmdir(rejected)
                _assert_child(parent, rejected)
                os.replace(target, rejected)
                os.replace(backup, target)
                backup = None
                shutil.rmtree(rejected)
            raise
        if backup and os.path.isdir(backup):
            _assert_child(parent, backup)
            shutil.rmtree(backup)
        return {
            "status": "PASS",
            "destination": target,
            "datasetDigest": dataset["datasetDigest"],
            "sourceManifestDigest": source_manifest["manifestDigest"],
            "receiptCount": len(dataset["receipts"]),
            "fileCount": len(verified["files"]) + 1,
        }
    finally:
        if staging and os.path.isdir(staging):
            _assert_child(parent, staging)
            shutil.rmtree(staging)
        if backup and os.path.isdir(backup):
            _assert_child(parent, backup)
            if not os.path.exists(target):
                os.replace(backup, target)
            else:
                shutil.rmtree(backup)
