"""Deterministic career projection over replay-verified, passport-signed matches.

A career record is evidence accounting, not a rating:

- every input transcript must independently pass full replay verification
  (rules, chain, adjudication) — a FAIL is refused outright;
- results group by the stable key-derived `agentId`, and per signed
  `versionId`, so two versions of one agent never blur into one line;
- lineage edges are only accepted when parent and child bind the same public
  key; a cross-key edge refuses the whole record;
- claimed model labels are carried as explicitly self-declared;
- nothing here attests a model, runtime, or person, and no opaque rating is
  produced.

Inputs may be transcript paths or already-loaded record lists. Output is fully
deterministic: identical inputs produce byte-identical documents.
"""

from __future__ import annotations

import os
import re
import tempfile
from typing import Any

from arena.transcript import first, load

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CAREER_SCHEMA = "agentbattles.career.v1"
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


class CareerError(ValueError):
    """A career record cannot be built from this corpus without lying."""


def _replay_pass(item):
    """Verify one corpus item (path or loaded records). Returns (report, records)."""
    from arena.replay import verify

    if isinstance(item, (str, bytes, os.PathLike)):
        path = os.fspath(item)
        records = load(path)
        report = verify(path)
    elif isinstance(item, list):
        records = item
        handle = tempfile.NamedTemporaryFile(
            prefix="builderwars-career-", suffix=".jsonl", delete=False
        )
        temporary_path = handle.name
        handle.close()
        try:
            with open(temporary_path, "w", encoding="utf-8", newline="\n") as fh:
                for record in records:
                    fh.write(_compact(record) + "\n")
            report = verify(temporary_path)
        finally:
            try:
                os.unlink(temporary_path)
            except OSError:
                pass
    else:
        raise CareerError("career corpus items must be transcript paths or record lists")
    return report, records


def _compact(record) -> str:
    import json

    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _outcome(result_body, seat):
    winner = result_body.get("winner")
    reason = result_body.get("reason", "")
    if reason == "engine_error":
        return "void"
    if winner is None:
        return "draw"
    if winner == seat:
        return "win"
    forfeit = isinstance(reason, str) and reason.startswith("forfeit:")
    return ("loss_forfeit" if forfeit else "loss")


def _opponent_ref(entrant_row):
    status = (
        "verified_signed"
        if entrant_row.get("agent_passport") is not None
        else "self_declared_legacy"
    )
    if entrant_row.get("agent_passport") is not None:
        stable_id = entrant_row["agent_passport"]["agentId"]
    else:
        from publishing.projection import _entrant_id

        stable_id = _entrant_id(str(entrant_row.get("name", "")))
    return {"entrantId": stable_id, "identityStatus": status}


def build_career(transcripts) -> dict[str, Any]:
    from arena.canonical import digest

    if not isinstance(transcripts, (list, tuple)):
        raise CareerError("transcripts must be a list of paths or record lists")

    versions: dict[str, dict[str, Any]] = {}
    agents: dict[str, dict[str, Any]] = {}
    receipt_ids: list[str] = []
    seen_receipt_ids: set[str] = set()
    signed_transcript_count = 0
    legacy_only_transcript_count = 0

    for item in transcripts:
        report, records = _replay_pass(item)
        if report.get("verdict") != "PASS":
            raise CareerError(
                "refusing transcript that fails replay verification: "
                f"{(report.get('errors') or ['unknown'])[:1]}"
            )
        identity_status = report.get("identity_status")
        if identity_status == "invalid":
            raise CareerError("refusing transcript with invalid passport identity evidence")
        header = first(records, "header")
        result_row = first(records, "result")
        if header is None or result_row is None:
            raise CareerError("verified transcript missing header or result")
        h, rb = header["body"], result_row["body"]
        chain_head = records[-1].get("hash")
        if not isinstance(chain_head, str) or _HEX64_RE.fullmatch(chain_head) is None:
            raise CareerError("verified transcript has no exact lowercase chain-head digest")
        if chain_head in seen_receipt_ids:
            raise CareerError("career corpus repeats the same verified receipt")
        seen_receipt_ids.add(chain_head)
        receipt_ids.append(chain_head)

        rows = h.get("entrants") or []
        seats_with_passports = [
            row for row in rows if isinstance(row, dict) and row.get("agent_passport") is not None
        ]
        # A legacy-only transcript contributes no signed-agent statistics.
        if not seats_with_passports:
            legacy_only_transcript_count += 1
            continue
        signed_transcript_count += 1

        from agent_identity import verify_passport

        verified_rows = []
        for row in rows:
            if not isinstance(row, dict) or row.get("seat") not in (0, 1):
                raise CareerError("malformed entrant seat in verified transcript")
            if row.get("agent_passport") is not None:
                try:
                    normalized = verify_passport(row["agent_passport"])
                except Exception as error:
                    raise CareerError(f"passport failed verification: {error}") from error
                verified_rows.append((row, normalized))
            else:
                verified_rows.append((row, None))

        for row, normalized in verified_rows:
            if normalized is None:
                continue  # legacy opponents are referenced, never aggregated
            seat = row["seat"]
            outcome = _outcome(rb, seat)
            opponent = next(
                other
                for other, _ in verified_rows
                if other.get("seat") == 1 - seat
            )
            opponent_ref = _opponent_ref(opponent)
            agent_id, version_id = normalized["agentId"], normalized["versionId"]

            version = versions.setdefault(
                version_id,
                {
                    "versionId": version_id,
                    "agentId": agent_id,
                    "versionLabel": normalized["versionLabel"],
                    "parentVersionId": normalized["parentVersionId"],
                    "harnessSha256": normalized["harnessSha256"],
                    "claimedModelSelfDeclared": normalized["claimedModel"],
                    "games": 0,
                    "wins": 0,
                    "losses": 0,
                    "lossesByForfeit": 0,
                    "draws": 0,
                    "voids": 0,
                    "opponents": [],
                },
            )
            version["games"] += 1
            if outcome == "win":
                version["wins"] += 1
            elif outcome == "draw":
                version["draws"] += 1
            elif outcome == "void":
                version["voids"] += 1
            elif outcome == "loss":
                version["losses"] += 1
            elif outcome == "loss_forfeit":
                version["losses"] += 1
                version["lossesByForfeit"] += 1
            if opponent_ref not in version["opponents"]:
                version["opponents"].append(opponent_ref)

            agent = agents.setdefault(
                agent_id,
                {
                    "agentId": agent_id,
                    "displayNames": [],
                    "versions": [],
                    "games": 0,
                    "wins": 0,
                    "losses": 0,
                    "draws": 0,
                    "voids": 0,
                },
            )
            if normalized["displayName"] not in agent["displayNames"]:
                agent["displayNames"].append(normalized["displayName"])
            if version_id not in agent["versions"]:
                agent["versions"].append(version_id)
            agent["games"] += 1
            if outcome == "win":
                agent["wins"] += 1
            elif outcome == "draw":
                agent["draws"] += 1
            elif outcome == "void":
                agent["voids"] += 1
            elif outcome.startswith("loss"):
                agent["losses"] += 1

    versions_by_id = {}
    for version_id, version in versions.items():
        versions_by_id[version_id] = {
            "agentId": version["agentId"],
            "versionId": version_id,
            "parentVersionId": version["parentVersionId"],
        }
    from agent_identity import require_same_key_lineage

    try:
        lineage_edges = require_same_key_lineage(versions_by_id)
    except Exception as error:
        from agent_identity import LineageError

        if isinstance(error, LineageError):
            raise CareerError(str(error)) from error
        raise
    declared_but_missing = sorted(set(
        v["parentVersionId"]
        for v in versions.values()
        if v["parentVersionId"] and v["parentVersionId"] not in versions
    ))

    document = {
        "schemaVersion": CAREER_SCHEMA,
        "basis": {
            "transcriptCount": len(transcripts),
            "signedTranscriptCount": signed_transcript_count,
            "legacyOnlyTranscriptCount": legacy_only_transcript_count,
            "receiptIds": sorted(receipt_ids),
            "agents": [agents[k] | {"displayNames": sorted(agents[k]["displayNames"]),
                                     "versions": sorted(agents[k]["versions"])}
                       for k in sorted(agents)],
            "versions": [_sorted_version(v) for _, v in sorted(versions.items())],
            "lineageEdges": sorted(
                lineage_edges, key=lambda e: (e["parentVersionId"], e["childVersionId"])
            ),
            "declaredParentsMissingFromCorpus": declared_but_missing,
            "identityStatus": "signed_agent_records_only",
            "modelAttested": False,
            "runtimeAttested": False,
            "personAttested": False,
            "ratingEmitted": False,
            "boundary": (
                "Counts cover only replay-PASS transcripts whose passports verify "
                "offline. Versions are separate append-only publication lines; a "
                "child version existing says nothing about whether the agent "
                "improved. Claimed model names are self-declared. No rating is emitted."
            ),
        },
    }
    document["basisDigest"] = digest(document["basis"])
    return document


def _sorted_version(version):
    out = dict(version)
    out["opponents"] = sorted(
        version["opponents"],
        key=lambda ref: (ref["entrantId"], ref["identityStatus"]),
    )
    return out


__all__ = ["CAREER_SCHEMA", "CareerError", "build_career"]
