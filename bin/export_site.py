#!/usr/bin/env python3
"""Export verified matches into the site: transcripts, the verifier, and a summary.

Two rules this file exists to enforce:

1. **Only replay-verified matches are published.** An unverified transcript is
   not a result. It is excluded and reported, never quietly shipped.
2. **Move provenance travels with the match.** A harness that fell back to its
   own computed move on every turn still wins matches, and a scoreboard alone
   cannot tell you the model never spoke. Every published match carries the
   model/fallback split per seat so the page can say so out loud.

    python bin/export_site.py --out <path-to-nymrel-worktree>
"""

import argparse
import glob
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from arena.replay import verify  # noqa: E402


def model_label(claimed):
    """'cli:ollama run llama3.2:3b' -> 'llama3.2:3b'; 'stub:v1' -> 'stub'."""
    if not claimed:
        return "unknown"
    kind, _, rest = claimed.partition(":")
    if kind == "stub":
        return "stub"
    if kind == "cli":
        return rest.split()[-1] if rest else "cli"
    return rest or kind


def series_of(path):
    rel = os.path.relpath(path, os.path.join(ROOT, "matches")).replace(os.sep, "/")
    parts = rel.split("/")
    return parts[0] if len(parts) > 2 else "single"


def summarise(path):
    report = verify(path)
    if report["verdict"] != "PASS":
        return None, report

    records = [json.loads(line) for line in open(path, "r", encoding="utf-8")]
    header = records[0]["body"]
    result = next((r["body"] for r in records if r["kind"] == "result"), None)
    if result is None:
        return None, report

    seats = []
    for e in header["entrants"]:
        seats.append({
            "seat": e["seat"],
            "name": e["name"],
            "model": model_label(e.get("claimed_model")),
            "backend": e.get("claimed_model"),
        })
    by_seat = {s["seat"]: s for s in seats}

    # provenance: did the model actually answer?
    for s in seats:
        s["modelMoves"] = 0
        s["fallbackMoves"] = 0
    for r in records:
        if r["kind"] != "move":
            continue
        note = r["body"].get("entrant_message", {}).get("note", "") or ""
        seat = r["body"].get("player")
        if seat in by_seat and note.startswith("source="):
            key = "modelMoves" if note == "source=model" else "fallbackMoves"
            by_seat[seat][key] += 1

    winner = result.get("winner")
    return {
        "id": header["match_id"],
        "game": header["game"]["name"],
        "seed": header["seed"],
        "series": series_of(path),
        "moves": result.get("moves"),
        "reason": result.get("reason"),
        "decisive": result.get("decisive"),
        "winnerSeat": winner,
        "winner": by_seat[winner]["name"] if winner is not None else None,
        "winnerModel": by_seat[winner]["model"] if winner is not None else None,
        "loser": by_seat[1 - winner]["name"] if winner is not None else None,
        "loserModel": by_seat[1 - winner]["model"] if winner is not None else None,
        "seats": seats,
        "chainHead": report.get("chain_head"),
        "engineDigestMatch": report.get("engine_digest_match"),
        "modelAttested": header.get("attestation", {}).get("model_attested", False),
        "verified": True,
    }, report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="path to the Nymrel worktree")
    args = ap.parse_args()

    site = os.path.abspath(args.out)
    pub = os.path.join(site, "public", "builderwars", "m")
    os.makedirs(pub, exist_ok=True)

    paths = sorted(
        p for p in glob.glob(os.path.join(ROOT, "matches", "**", "*.jsonl"), recursive=True)
        if not p.endswith(".diagnostics.jsonl")
    )

    matches, excluded = [], []
    for p in paths:
        row, report = summarise(p)
        if row is None:
            excluded.append((os.path.basename(p), report["verdict"], report["errors"][:1]))
            continue
        matches.append(row)
        shutil.copyfile(p, os.path.join(pub, f"{row['id']}.jsonl"))

    shutil.copyfile(os.path.join(ROOT, "verify.py"),
                    os.path.join(site, "public", "builderwars", "verify.py"))

    data = {
        "generatedBy": "arena-engine/bin/export_site.py",
        "matchCount": len(matches),
        "excludedCount": len(excluded),
        "matches": sorted(matches, key=lambda m: (m["series"], m["seed"], m["winnerSeat"] or 0)),
    }
    dest = os.path.join(site, "src", "data", "builderwars.generated.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")

    print(f"exported {len(matches)} verified matches -> {os.path.relpath(dest, site)}")
    print(f"transcripts -> public/builderwars/m/  ({len(matches)} files)")
    print(f"verifier    -> public/builderwars/verify.py")
    if excluded:
        print(f"\nEXCLUDED {len(excluded)} unverified transcript(s) — not published:")
        for name, verdict, errs in excluded:
            print(f"  {name}: {verdict} {errs}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
