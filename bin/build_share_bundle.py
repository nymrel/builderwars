#!/usr/bin/env python3
"""Build a deterministic, truth-safe share bundle from one verified match.

The output is deliberately static. It contains no raw model response, prompt,
stderr, environment value, or executable script. A bundle is a candidate
content artifact, not evidence that a public route exists or that anyone saw it.
"""

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from urllib.parse import quote, urlencode, urlsplit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from arena.canonical import digest  # noqa: E402
from arena.transcript import load  # noqa: E402
from publishing.projection import PublicationError, project_receipt  # noqa: E402

BUNDLE_VERSION = "1"
SOURCE_LABEL = "agentwars_share_bundle"
CAMPAIGN_ID = "agentwars_verified_moments_v1"
OUTPUT_NAMES = ("manifest.json", "card.svg", "match.html", "copy.md")
MATCH_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")

EVENT_SCHEMA = {
    "share_intent_recorded": {
        "required": ["match_id", "clip_id", "share_method"],
        "optional": ["surface", "campaign_id", "creative_id"],
    },
    "share_landing_viewed": {
        "required": ["match_id", "clip_id", "source_label", "campaign_id", "creative_id"],
        "optional": ["surface"],
    },
    "replay_started": {
        "required": ["match_id", "clip_id"],
        "optional": ["surface"],
    },
    "replay_verified": {
        "required": ["match_id", "clip_id", "verdict"],
        "optional": ["surface"],
    },
    "spectator_vote_cast": {
        "required": ["match_id", "clip_id", "vote"],
        "optional": ["surface"],
    },
    "league_join_clicked": {
        "required": ["match_id", "clip_id"],
        "optional": ["surface"],
    },
}

EVENT_VALUE_ALLOWLISTS = {
    "share_method": ["native", "copy", "download"],
    "surface": ["receipt_card", "share_landing", "match_page"],
    "verdict": ["PASS", "FAIL"],
    "vote": ["seat0", "seat1", "runback"],
}


class BundleError(ValueError):
    pass


def source_kind(note):
    """Classify an entrant-authored provenance note without exposing its tail."""
    if not isinstance(note, str):
        return "other"
    claim = re.split(r"[;:]", note, maxsplit=1)[0]
    return {
        "source=model": "model",
        "source=fallback": "fallback",
        "source=scripted": "scripted",
        "source=scripted_board": "scripted",
    }.get(claim, "other")


def display_text(value, limit=120):
    """Strip unsafe controls, collapse whitespace, and bound public display text."""
    if not isinstance(value, str):
        value = str(value)
    value = "".join(
        char for char in value
        if unicodedata.category(char) not in ("Cc", "Cf", "Cs")
    )
    return " ".join(value.split())[:limit] or "unnamed"


def markdown_text(value, limit=120):
    value = display_text(value, limit)
    for char in ("\\", "`", "*", "_", "[", "]", "<", ">", "#"):
        value = value.replace(char, "\\" + char)
    return value


def normalize_base_url(value):
    if value is None:
        return None
    parsed = urlsplit(value)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.netloc
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or any(char.isspace() or char == "\\" for char in value)
    ):
        raise BundleError("public base URL must be plain HTTP(S) without credentials, query, or fragment")
    return value.rstrip("/")


def find_required(records, kind):
    row = next((record for record in records if record.get("kind") == kind), None)
    if row is None or not isinstance(row.get("body"), dict):
        raise BundleError(f"verified transcript is missing {kind!r}")
    return row


def verify_with_snapshot(transcript_path):
    """Run the standalone verifier so historical receipts use their exact engine snapshot."""
    path = os.path.abspath(transcript_path)
    if not os.path.isfile(path):
        raise BundleError("transcript path must name a local file")
    try:
        completed = subprocess.run(
            [sys.executable, os.path.join(ROOT, "verify.py"), path, "--json"],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise BundleError(f"standalone verifier failed safely: {error.__class__.__name__}") from error
    try:
        report = json.loads(completed.stdout)
    except (TypeError, json.JSONDecodeError) as error:
        raise BundleError("standalone verifier returned an invalid report") from error
    if not isinstance(report, dict):
        raise BundleError("standalone verifier returned an invalid report")
    effective_pass = (
        report.get("verdict") == "PASS"
        and report.get("engine_digest_match") is True
        and report.get("verifier_snapshot_match") is True
    )
    expected_exit = 0 if effective_pass else 1
    if completed.returncode != expected_exit:
        raise BundleError("standalone verifier exit status disagrees with its effective report")
    return report


def require_exact_verification(report):
    if report.get("verifier_snapshot_match") is not True or report.get("engine_digest_match") is False:
        raise BundleError("refusing receipt without an exact embedded verifier-engine match")
    if report.get("verdict") != "PASS":
        errors = report.get("errors") or []
        raise BundleError(f"refusing unverified transcript: {errors[:1]}")
    return report


def entrant_rows(header):
    raw = header.get("entrants")
    if not isinstance(raw, list) or len(raw) != 2:
        raise BundleError("share bundles currently require exactly two transcript entrants")
    rows = []
    for entrant in sorted(raw, key=lambda item: item.get("seat", -1)):
        seat = entrant.get("seat")
        if seat not in (0, 1):
            raise BundleError("entrant seat must be 0 or 1")
        execution_claim = entrant.get("execution_claim", "unspecified")
        if execution_claim not in ("scripted", "model", "hybrid", "unspecified"):
            raise BundleError("entrant execution claim is not a supported public value")
        manifest_digest = entrant.get("manifest_digest")
        if manifest_digest is not None and (
            not isinstance(manifest_digest, str)
            or re.fullmatch(r"[0-9a-f]{64}", manifest_digest) is None
        ):
            raise BundleError("entrant manifest digest is malformed")
        rows.append(
            {
                "seat": seat,
                "name": display_text(entrant.get("name", "unnamed")),
                "executionClaim": execution_claim,
                "manifestDigest": manifest_digest,
            }
        )
    if [row["seat"] for row in rows] != [0, 1]:
        raise BundleError("transcript must contain one entrant in each seat")
    if len({row["name"].casefold() for row in rows}) != 2:
        raise BundleError("entrant display names collide after normalization")
    return rows


def move_source_counts(records, entrants):
    counts = {
        entrant["name"]: {"model": 0, "fallback": 0, "scripted": 0, "other": 0}
        for entrant in entrants
    }
    by_seat = {entrant["seat"]: entrant["name"] for entrant in entrants}
    for record in records:
        if record.get("kind") != "move":
            continue
        body = record.get("body", {})
        seat = body.get("player")
        if seat not in by_seat:
            continue
        message = body.get("entrant_message")
        note = message.get("note") if isinstance(message, dict) else None
        counts[by_seat[seat]][source_kind(note)] += 1
    return counts


def truth_status(entrants, sources):
    model_moves = sum(row["model"] for row in sources.values())
    fallback_moves = sum(row["fallback"] for row in sources.values())
    claims = {entrant["executionClaim"] for entrant in entrants}
    if model_moves:
        return "model_influenced_unattested"
    if claims == {"scripted"}:
        return "scripted_preseason"
    if fallback_moves:
        return "fallback_only_unattested"
    return "execution_claimed_unattested"


def final_state(records):
    states = [record.get("body", {}).get("state") for record in records if record.get("kind") == "state"]
    return states[-1] if states and isinstance(states[-1], dict) else None


def fantasy_scores(state):
    if not isinstance(state, dict) or state.get("format") not in ("redraft", "dynasty", "qb_surge"):
        return None
    players = state.get("players")
    rosters = state.get("rosters")
    if not isinstance(players, list) or not isinstance(rosters, list) or len(rosters) != 2:
        return None
    metric = "redraft_points" if state["format"] == "redraft" else "dynasty_points"
    by_id = {row.get("id"): row for row in players if isinstance(row, dict)}
    try:
        scores = [sum(by_id[player_id][metric] for player_id in roster) for roster in rosters]
        if state["format"] == "qb_surge":
            for seat, roster in enumerate(rosters):
                scores[seat] += sum(
                    by_id[player_id]["redraft_points"]
                    for player_id in roster
                    if by_id[player_id]["position"] == "QB"
                )
    except (KeyError, TypeError):
        return None
    return metric, scores, by_id, rosters


def ten_fronts_scores(state):
    """Extract Ten Fronts scores from referee state only, failing closed.

    The result record's prose is never a score source. A Ten Fronts final
    state must carry exactly two non-negative canonical integers; anything
    else refuses the bundle instead of dropping the score.
    """
    if not isinstance(state, dict):
        raise BundleError("ten fronts receipt has no final referee state")
    scores = state.get("scores")
    if (
        not isinstance(scores, list)
        or len(scores) != 2
        or any(
            not isinstance(value, int) or isinstance(value, bool) or value < 0
            for value in scores
        )
    ):
        raise BundleError(
            "ten fronts final state must carry exactly two non-negative integer scores"
        )
    return scores


def select_highlight(records, state, winner):
    terminal = next(
        (record for record in records if record.get("kind") in ("forfeit", "engine_error")),
        None,
    )
    if terminal is not None:
        kind = terminal["kind"]
        body = terminal.get("body", {})
        if kind == "forfeit":
            label = "Replay-verified forfeit adjudication; not a gameplay-performance claim."
            detail = display_text(body.get("reason", "entrant forfeited"), 80)
            highlight_kind = "forfeit_adjudication"
        else:
            label = "Replay-verified engine-error record; the match was voided, not decided."
            detail = "engine_error"
            highlight_kind = "voided_match"
        return {
            "kind": highlight_kind,
            "label": label,
            "seqStart": terminal["seq"],
            "seqEnd": terminal["seq"],
            "turn": body.get("turn"),
            "seat": body.get("player"),
            "recordHash": terminal["hash"],
            "sourceClaim": "other",
            "detail": detail,
        }

    fantasy = fantasy_scores(state)
    if fantasy is not None and winner in (0, 1) and fantasy[3][winner]:
        metric, _scores, by_id, rosters = fantasy
        player_id = max(rosters[winner], key=lambda item: (by_id[item][metric], -item))
        move_record = next(
            (
                record
                for record in records
                if record.get("kind") == "move"
                and record.get("body", {}).get("player") == winner
                and record.get("body", {}).get("move", {}).get("player_id") == player_id
            ),
            None,
        )
        if move_record is None:
            raise BundleError("winning fantasy pick is missing its move record")
        message = move_record["body"].get("entrant_message", {})
        return {
            "kind": "top_scoring_pick",
            "label": "Top-scoring pick on the winning roster; not a causal winning-move claim.",
            "seqStart": move_record["seq"],
            "seqEnd": move_record["seq"],
            "turn": move_record["body"].get("turn"),
            "seat": winner,
            "recordHash": move_record["hash"],
            "sourceClaim": source_kind(message.get("note") if isinstance(message, dict) else None),
            "player": {
                "id": player_id,
                "name": display_text(by_id[player_id].get("name", player_id), 80),
                "position": display_text(by_id[player_id].get("position", "?"), 12),
                "points": by_id[player_id][metric],
                "metric": metric,
            },
        }

    moves = [record for record in records if record.get("kind") == "move" and record.get("body", {}).get("legal")]
    if not moves:
        raise BundleError("verified transcript has no accepted move to highlight")
    move_record = moves[-1]
    message = move_record["body"].get("entrant_message", {})
    return {
        "kind": "final_accepted_move",
        "label": "Final accepted move in the verified transcript.",
        "seqStart": move_record["seq"],
        "seqEnd": move_record["seq"],
        "turn": move_record["body"].get("turn"),
        "seat": move_record["body"].get("player"),
        "recordHash": move_record["hash"],
        "sourceClaim": source_kind(message.get("note") if isinstance(message, dict) else None),
    }


def story_details(game, entrants, result, state, highlight):
    winner = result.get("winner")
    winner_name = entrants[winner]["name"] if winner in (0, 1) else None
    loser_name = entrants[1 - winner]["name"] if winner in (0, 1) else None
    if highlight["kind"] == "forfeit_adjudication":
        return {
            "headline": f"{winner_name} wins {game.replace('fantasy_', '')} by forfeit",
            "resultLine": display_text(result.get("reason", "verified forfeit"), 160),
            "winner": winner_name,
            "loser": loser_name,
            "scores": None,
            "margin": None,
            "question": "Would you run this matchup back?",
        }
    if highlight["kind"] == "voided_match":
        return {
            "headline": f"{game.replace('fantasy_', '')} match voided",
            "resultLine": display_text(result.get("reason", "engine_error"), 160),
            "winner": None,
            "loser": None,
            "scores": None,
            "margin": None,
            "question": "Should this matchup be replayed?",
        }
    if game == "ten_fronts":
        scores = ten_fronts_scores(state)
        if winner in (0, 1):
            return {
                "headline": f"{winner_name} wins {game.replace('fantasy_', '').replace('_', ' ')}",
                "resultLine": f"{scores[winner]}–{scores[1 - winner]} over {loser_name}",
                "winner": winner_name,
                "loser": loser_name,
                "scores": {entrants[0]["name"]: scores[0], entrants[1]["name"]: scores[1]},
                "margin": abs(scores[0] - scores[1]),
                "question": "Would you run this match back?",
            }
        return {
            "headline": f"{entrants[0]['name']} and {entrants[1]['name']} draw",
            "resultLine": f"{scores[0]}–{scores[1]}",
            "winner": None,
            "loser": None,
            "scores": {entrants[0]["name"]: scores[0], entrants[1]["name"]: scores[1]},
            "margin": abs(scores[0] - scores[1]),
            "question": "Which side would you take in the runback?",
        }

    fantasy = fantasy_scores(state)
    if fantasy is not None:
        _metric, scores, _by_id, _rosters = fantasy
        if winner in (0, 1):
            headline = f"{winner_name} wins {game.replace('fantasy_', '')}"
            result_line = f"{scores[winner]}–{scores[1 - winner]} over {loser_name}"
            question = f"Would you have taken {highlight['player']['name']} there?"
        else:
            headline = f"{entrants[0]['name']} and {entrants[1]['name']} draw"
            result_line = f"{scores[0]}–{scores[1]}"
            question = "Which roster would you run back?"
        return {
            "headline": headline,
            "resultLine": result_line,
            "winner": winner_name,
            "loser": loser_name,
            "scores": {entrants[0]["name"]: scores[0], entrants[1]["name"]: scores[1]},
            "margin": abs(scores[0] - scores[1]),
            "question": question,
        }

    if winner in (0, 1):
        return {
            "headline": f"{winner_name} beats {loser_name}",
            "resultLine": display_text(result.get("reason", "verified result"), 160),
            "winner": winner_name,
            "loser": loser_name,
            "scores": None,
            "margin": None,
            "question": "Would you run this match back?",
        }
    return {
        "headline": f"{entrants[0]['name']} and {entrants[1]['name']} draw",
        "resultLine": display_text(result.get("reason", "verified result"), 160),
        "winner": None,
        "loser": None,
        "scores": None,
        "margin": None,
        "question": "Would you run this match back?",
    }


def candidate_url(base_url, match_id, creative_id):
    if base_url is None:
        return None
    query = urlencode(
        {
            "source_label": SOURCE_LABEL,
            "campaign_id": CAMPAIGN_ID,
            "creative_id": creative_id,
        }
    )
    return f"{base_url}/m/{quote(match_id, safe='')}?{query}"


def build_manifest(transcript_path, public_base_url=None):
    try:
        public_receipt, _public_records = project_receipt(transcript_path)
    except PublicationError as error:
        raise BundleError(str(error)) from error
    report = require_exact_verification(verify_with_snapshot(transcript_path))
    try:
        records = load(transcript_path)
    except Exception as error:
        raise BundleError(f"could not load verified transcript: {error.__class__.__name__}") from error
    header = find_required(records, "header")["body"]
    result = find_required(records, "result")["body"]
    entrants = entrant_rows(header)
    public_by_seat = {row["seat"]: row for row in public_receipt["entrants"]}
    for entrant in entrants:
        public = public_by_seat[entrant["seat"]]
        entrant["entrantId"] = public["entrantId"]
        entrant["harnessVersionId"] = public["harnessVersionId"]
    sources = move_source_counts(records, entrants)
    state = final_state(records)
    winner = result.get("winner")
    highlight = select_highlight(records, state, winner)
    game = display_text(header.get("game", {}).get("name", "unknown"), 80)
    story = story_details(game, entrants, result, state, highlight)
    match_id = header.get("match_id")
    if not isinstance(match_id, str) or MATCH_ID_RE.fullmatch(match_id) is None:
        raise BundleError("match id is not safe for a share route")
    receipt_id = public_receipt["receiptId"]
    fixture_id = public_receipt["fixtureId"]
    clip_seed = f"{BUNDLE_VERSION}\x1f{receipt_id}\x1f{highlight['seqStart']}\x1f{highlight['recordHash']}"
    clip_id = "clip_" + hashlib.sha256(clip_seed.encode("utf-8")).hexdigest()[:16]
    highlight["clipId"] = clip_id
    creative_id = "moment_" + digest({"campaign": CAMPAIGN_ID, "clipId": clip_id})[:16]
    entrant_ids = sorted(entrant["entrantId"] for entrant in entrants)
    rivalry_id = "rivalry_" + digest({"game": game, "entrants": entrant_ids})[:16]
    parent_seed = header.get("seed")
    if (
        not isinstance(parent_seed, int)
        or isinstance(parent_seed, bool)
        or parent_seed < 0
        or parent_seed >= 2_147_483_647
    ):
        raise BundleError("cannot derive a bounded next-seed runback from this receipt")
    runback_seed = parent_seed + 1
    challenge_core = {
        "parentMatchId": match_id,
        "parentReceiptId": receipt_id,
        "parentFixtureId": fixture_id,
        "parentChainHead": report.get("chain_head") or records[-1].get("hash"),
        "game": game,
        "seed": runback_seed,
        "seats": [entrants[1]["name"], entrants[0]["name"]],
    }
    base_url = normalize_base_url(public_base_url)
    status = truth_status(entrants, sources)
    core = {
        "schemaVersion": BUNDLE_VERSION,
        "product": "AgentWars",
        "artifact": "verified_moment_bundle",
        "activationStatus": "candidate_url_unverified" if base_url else "local_preview_only",
        "match": {
            "id": match_id,
            "receiptId": receipt_id,
            "fixtureId": fixture_id,
            "game": game,
            "seed": header.get("seed"),
            "chainHead": report.get("chain_head") or records[-1].get("hash"),
            "verified": True,
            "resultReason": display_text(result.get("reason", "verified result"), 200),
        },
        "story": story,
        "highlight": highlight,
        "rivalry": {
            "id": rivalry_id,
            "historyStatus": "not_loaded",
            "meetingNumber": None,
            "runback": {
                "status": "unplayed_challenge",
                "challengeId": "challenge_" + digest(challenge_core)[:16],
                **challenge_core,
            },
        },
        "entrants": entrants,
        "moveSourceClaims": sources,
        "truth": {
            "status": status,
            "modelAttested": False,
            "executionClaimsAttested": False,
            "entrantIdentityAttested": False,
            "boundary": (
                "Replay reproduces accepted moves, state, scoring, and the published result; "
                "runtime-only forfeits are excluded. Entrant execution "
                "classes, display names, and move-source notes are hash-bound self-declarations, "
                "not proof that the run occurred or independent entrant, provider, or model attestation."
            ),
        },
        "verification": {
            "localCommandTemplate": "python verify.py PATH_TO_TRANSCRIPT.jsonl",
            "candidatePublicCommand": f"python verify.py {receipt_id}",
            "verdict": "PASS",
            "engineDigestMatch": report.get("engine_digest_match"),
            "publicTranscriptStatus": "candidate_until_published" if base_url else "not_configured",
        },
        "campaign": {
            "sourceLabel": SOURCE_LABEL,
            "campaignId": CAMPAIGN_ID,
            "creativeId": creative_id,
            "candidateUrl": candidate_url(base_url, receipt_id, creative_id),
            "urlProof": "unverified_candidate" if base_url else "not_configured",
            "performanceMeasured": False,
        },
        "measurementContract": {
            "status": "schema_only_not_instrumented",
            "privacy": "Allowlisted identifiers only; never record raw hrefs, prompts, output, or credentials.",
            "events": EVENT_SCHEMA,
            "valueAllowlists": EVENT_VALUE_ALLOWLISTS,
        },
    }
    core["bundleDigest"] = digest(core)
    return core


def render_card(manifest):
    story = manifest["story"]
    highlight = manifest["highlight"]
    truth = manifest["truth"]["status"].replace("_", " ").upper()
    game = manifest["match"]["game"].replace("fantasy_", "").replace("_", " ").upper()
    headline = html.escape(display_text(story["headline"], 54))
    result_line = html.escape(display_text(story["resultLine"], 72))
    question = html.escape(display_text(story["question"], 76))
    if highlight["kind"] == "top_scoring_pick":
        player = highlight["player"]
        moment = f"TOP PICK  {player['name']} · {player['points']} {player['metric'].replace('_', ' ')}"
    elif highlight["kind"] == "forfeit_adjudication":
        moment = f"FORFEIT ADJUDICATION · {highlight['detail']}"
    elif highlight["kind"] == "voided_match":
        moment = "MATCH VOIDED · ENGINE ERROR"
    else:
        moment = f"FINAL ACCEPTED MOVE · TURN {highlight.get('turn')}"
    moment = html.escape(display_text(moment, 88))
    match_id = html.escape(manifest["match"]["id"])
    chain = html.escape(str(manifest["match"]["chainHead"])[:16])
    creative = html.escape(manifest["campaign"]["creativeId"])
    runback = manifest["rivalry"]["runback"]
    runback_line = html.escape(
        f"RUN IT BACK · SEED {runback['seed']} · SEATS SWAPPED · UNPLAYED CHALLENGE"
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630" role="img" aria-labelledby="title desc">
<title id="title">{headline}</title>
<desc id="desc">Replay-verified AgentWars {html.escape(game.lower())} result. {result_line}</desc>
<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#090b14"/><stop offset="1" stop-color="#171b2d"/></linearGradient></defs>
<rect width="1200" height="630" rx="36" fill="url(#bg)"/>
<rect x="34" y="34" width="1132" height="562" rx="28" fill="none" stroke="#2d365a" stroke-width="2"/>
<text x="76" y="98" fill="#7ee7c8" font-family="Arial, sans-serif" font-size="24" font-weight="700" letter-spacing="3">AGENTWARS · {html.escape(game)}</text>
<text x="76" y="205" fill="#ffffff" font-family="Arial, sans-serif" font-size="58" font-weight="800">{headline}</text>
<text x="76" y="275" fill="#cdd4f6" font-family="Arial, sans-serif" font-size="36" font-weight="600">{result_line}</text>
<rect x="76" y="322" width="1048" height="84" rx="18" fill="#202742"/>
<text x="106" y="374" fill="#f4c86b" font-family="Arial, sans-serif" font-size="27" font-weight="700">{moment}</text>
<text x="76" y="458" fill="#ffffff" font-family="Arial, sans-serif" font-size="29" font-weight="600">{question}</text>
<text x="76" y="497" fill="#9ba6cf" font-family="Arial, sans-serif" font-size="17" font-weight="700">{runback_line}</text>
<text x="76" y="534" fill="#7ee7c8" font-family="Arial, sans-serif" font-size="20" font-weight="700">REPLAY VERIFIED</text>
<text x="277" y="534" fill="#9ba6cf" font-family="Arial, sans-serif" font-size="20">{html.escape(truth)}</text>
<text x="76" y="570" fill="#6f789f" font-family="monospace" font-size="16">MATCH {match_id} · CHAIN {chain}… · {creative}</text>
</svg>
'''


def render_html(manifest):
    story = manifest["story"]
    entrants = manifest["entrants"]
    sources = manifest["moveSourceClaims"]
    rows = []
    for entrant in entrants:
        name = entrant["name"]
        count = sources[name]
        rows.append(
            "<tr>"
            f"<td>{html.escape(name)}</td>"
            f"<td>{html.escape(display_text(entrant['executionClaim'], 30))}</td>"
            f"<td>{count['model']}</td><td>{count['fallback']}</td><td>{count['scripted']}</td>"
            "</tr>"
        )
    candidate = manifest["campaign"]["candidateUrl"]
    route = (
        f'<p class="hold">Candidate tagged route (not deployment proof): '
        f'<a href="{html.escape(candidate, quote=True)}">{html.escape(candidate)}</a></p>'
        if candidate
        else '<p class="hold">Local preview only. No public match URL has been configured or verified.</p>'
    )
    moment = manifest["highlight"]
    runback = manifest["rivalry"]["runback"]
    if moment["kind"] == "top_scoring_pick":
        player = moment["player"]
        moment_text = (
            f"{player['name']} ({player['position']}), {player['points']} "
            f"{player['metric'].replace('_', ' ')}"
        )
    elif moment["kind"] == "forfeit_adjudication":
        moment_text = f"Forfeit adjudication: {moment['detail']}"
    elif moment["kind"] == "voided_match":
        moment_text = "Match voided after an engine-error record"
    else:
        moment_text = f"Final accepted move, turn {moment.get('turn')}"
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'">
<title>{html.escape(story['headline'])} · AgentWars</title>
<style>body{{margin:0;background:#090b14;color:#edf0ff;font:17px/1.55 system-ui,sans-serif}}main{{max-width:860px;margin:auto;padding:56px 24px}}.eyebrow,.verified{{color:#7ee7c8;font-weight:800;letter-spacing:.08em;text-transform:uppercase}}h1{{font-size:clamp(2.4rem,7vw,4.8rem);line-height:1;margin:.3em 0}}h2{{margin-top:2em}}.result{{font-size:1.5rem;color:#cdd4f6}}.card{{background:#171b2d;border:1px solid #2d365a;border-radius:18px;padding:22px;margin:28px 0}}.table-wrap{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;min-width:650px}}th,td{{text-align:left;padding:10px;border-bottom:1px solid #2d365a}}code{{color:#f4c86b}}.hold{{color:#f4c86b;overflow-wrap:anywhere}}a{{color:#7ee7c8}}</style></head>
<body><main><p class="eyebrow">AgentWars · {html.escape(manifest['match']['game'])}</p>
<h1>{html.escape(story['headline'])}</h1><p class="result">{html.escape(story['resultLine'])}</p>
<div class="card"><p class="verified">Replay verified</p><p>{html.escape(moment_text)}</p><p>{html.escape(moment['label'])}</p><p><strong>{html.escape(story['question'])}</strong></p></div>
<div class="card"><p class="eyebrow">Run it back</p><p>Unplayed challenge: seed {runback['seed']}, seats swapped.</p><p>This is a proposed rematch, not a result. Challenge <code>{html.escape(runback['challengeId'])}</code>.</p></div>
<h2>Execution receipt</h2><div class="table-wrap"><table><thead><tr><th>Entrant</th><th>Declared class</th><th>Model-source claims</th><th>Fallbacks</th><th>Scripted</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p>{html.escape(manifest['truth']['boundary'])}</p>
<h2>Verify it</h2><p>Local command template (replace the placeholder with the receipt path): <code>{html.escape(manifest['verification']['localCommandTemplate'])}</code></p>
<p>Match <code>{html.escape(manifest['match']['id'])}</code> · chain <code>{html.escape(str(manifest['match']['chainHead']))}</code></p>{route}
</main></body></html>
'''


def render_copy(manifest):
    story = manifest["story"]
    sources = manifest["moveSourceClaims"]
    total_model = sum(row["model"] for row in sources.values())
    total_fallback = sum(row["fallback"] for row in sources.values())
    total_scripted = sum(row["scripted"] for row in sources.values())
    url = manifest["campaign"]["candidateUrl"]
    runback = manifest["rivalry"]["runback"]
    link_line = f"\n\nCandidate route, not yet verified live: {url}" if url else ""
    provenance = (
        f"Entrant notes label {total_model} recorded move(s) model-sourced, "
        f"{total_fallback} fallback, and {total_scripted} scripted. "
        "Model identity was not independently attested."
    )
    headline = markdown_text(story["headline"])
    result_line = markdown_text(story["resultLine"])
    question = markdown_text(story["question"])
    return f'''# AgentWars verified moment — draft only

**STATUS: DRAFT. NOT POSTED. NO AUDIENCE OR PERFORMANCE CLAIM.**

## Short post

{headline}. {result_line}.

{provenance}

The match replay verifies. {question}{link_line}

Runback proposed: seed {runback['seed']}, seats swapped. It is an unplayed challenge, not another result.

## Community title

{headline}: {result_line} — replay receipt included

## Community body

This is an AgentWars match receipt, not a model leaderboard claim.

{provenance}

Highlight: {markdown_text(manifest['highlight']['label'], 180)}

Verify locally after replacing the receipt-path placeholder:

`{manifest['verification']['localCommandTemplate']}`

Match `{manifest['match']['id']}` · chain `{manifest['match']['chainHead']}`{link_line}

## Activation gate

- Verify the public match URL while signed out.
- Prove the tagged tuple reaches an allowlisted event counter.
- Name one channel, owner, numeric threshold, and stop-loss date before opening a growth experiment.
- Keep `model_attested=false` visible anywhere the move-source split appears.
- Keep the runback labeled `unplayed_challenge` until a child replay receipt exists.
'''


def build_outputs(transcript_path, public_base_url=None):
    manifest = build_manifest(transcript_path, public_base_url)
    return {
        "manifest.json": json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        "card.svg": render_card(manifest),
        "match.html": render_html(manifest),
        "copy.md": render_copy(manifest),
    }


def write_bundle(transcript_path, out_dir, public_base_url=None):
    outputs = build_outputs(transcript_path, public_base_url)
    destination = os.path.abspath(out_dir)
    if os.path.exists(destination):
        raise BundleError("output directory already exists; choose a new path")
    parent = os.path.dirname(destination)
    os.makedirs(parent, exist_ok=True)
    staging = tempfile.mkdtemp(prefix=".agentwars-share-", dir=parent)
    try:
        for name in OUTPUT_NAMES:
            with open(os.path.join(staging, name), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(outputs[name])
        os.replace(staging, destination)
    except Exception:
        if os.path.isdir(staging):
            shutil.rmtree(staging)
        raise
    return json.loads(outputs["manifest.json"])


def main():
    parser = argparse.ArgumentParser(description="Build a verified AgentWars share bundle.")
    parser.add_argument("transcript")
    parser.add_argument("--out", required=True)
    parser.add_argument("--public-base-url", default=None)
    args = parser.parse_args()
    try:
        manifest = write_bundle(args.transcript, args.out, args.public_base_url)
    except BundleError as error:
        parser.error(str(error))
    print(json.dumps({
        "status": "PASS",
        "out": os.path.abspath(args.out),
        "matchId": manifest["match"]["id"],
        "receiptId": manifest["match"]["receiptId"],
        "fixtureId": manifest["match"]["fixtureId"],
        "creativeId": manifest["campaign"]["creativeId"],
        "truthStatus": manifest["truth"]["status"],
        "activationStatus": manifest["activationStatus"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
