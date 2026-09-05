"""Output, manifest, and lock helpers for the AgentWars factorial study."""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from factorial_study_core import *  # noqa: F401,F403

def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# {summary['study_id']} — {summary['profile']}",
        "",
        f"**Publication gate: {summary['publication_gate']['status']}**",
        "",
        f"Receipts: {summary['observed_fixtures']} / {summary['expected_fixtures']}",
        f"Plan digest: `{summary['plan_digest']}`",
        f"Summary digest: `{summary['summary_digest']}`",
        "",
        "> Replay proves the recorded match and referee result. Model identity and execution claims remain unattested.",
        "",
    ]
    for comparison in summary["comparisons"]:
        lines.extend([f"## {comparison['comparison_id']} ({comparison['kind']})", ""])
        lines.append("| Contrast | Preferred arm | W-L | Win rate | Wilson 95% |")
        lines.append("|---|---|---:|---:|---:|")
        for contrast in comparison["contrasts"].values():
            if contrast.get("win_rate") is None:
                lines.append(f"| {contrast['label']} | `{contrast['preferred']}` | — | — | — |")
                continue
            interval = contrast["win_rate_wilson95"]
            lines.append(
                "| {label} | `{preferred}` | {wins}-{losses} | {rate:.1%} | {low:.1%}–{high:.1%} |".format(
                    label=contrast["label"], preferred=contrast["preferred"],
                    wins=contrast["wins"], losses=contrast["losses"], rate=contrast["win_rate"],
                    low=interval[0], high=interval[1],
                )
            )
        lines.append("")
    violations = summary["publication_gate"]["violations"]
    if violations:
        lines.extend(["## Hold reasons", ""])
        lines.extend(f"- {violation}" for violation in violations[:100])
        if len(violations) > 100:
            lines.append(f"- … {len(violations) - 100} additional violations in `summary.json`")
        lines.append("")
    return "\n".join(lines)


def make_manifest(treatment: dict[str, Any], backend_timeout_s: float, execution_claim_for_backend: Any) -> dict[str, Any]:
    harness = os.path.join(ROOT, treatment["harness_path"])
    command = [sys.executable, harness, "--backend", treatment["backend"],
               "--backend-timeout", str(backend_timeout_s), "--customer-local-v1"]
    claim = execution_claim_for_backend(treatment["backend"])
    require(claim == "model", f"{treatment['id']} is not a model execution treatment")
    return {
        "name": treatment["id"],
        "cmd": command,
        "env": [],
        "claimed_model": treatment["backend"],
        "execution_claim": claim,
    }


def receipt_directory(output_root: str, fixture: dict[str, Any]) -> str:
    return os.path.join(
        output_root,
        "receipts",
        fixture["comparison_id"],
        fixture["pairing_id"],
        f"r{fixture['replicate']:02d}",
        f"s{fixture['seed']}-o{fixture['order']}",
    )


def expected_transcript_path(output_root: str, fixture: dict[str, Any]) -> str:
    return os.path.join(receipt_directory(output_root, fixture), f"{fixture['match_id']}.jsonl")


def ensure_lock(output_root: str, plan: dict[str, Any], profile_name: str) -> None:
    lock_path = os.path.join(output_root, "study.lock.json")
    expected = {
        "schema": LOCK_SCHEMA,
        "study_id": plan["study_id"],
        "plan_digest": plan_digest(plan),
        "profile": profile_name,
    }
    if os.path.exists(lock_path):
        actual = load_json(lock_path)
        require(actual == expected, "output directory is locked to a different plan or profile")
    else:
        atomic_write_json(lock_path, expected)


def write_outputs(output_root: str, summary: dict[str, Any]) -> None:
    summary_path = os.path.join(output_root, "summary.json")
    atomic_write_json(summary_path, summary)
    atomic_write_text(os.path.join(output_root, "summary.md"), render_markdown(summary))
    candidate_path = os.path.join(output_root, "publication-candidate.json")
    if summary["publication_gate"]["status"] == "PASS":
        candidate = {
            "schema": CANDIDATE_SCHEMA,
            "study_id": summary["study_id"],
            "plan_digest": summary["plan_digest"],
            "summary_digest": summary["summary_digest"],
            "summary_sha256": file_digest(summary_path),
            "profile": summary["profile"],
            "attestation_boundary": summary["attestation_boundary"],
            "comparisons": summary["comparisons"],
            "receipt_manifest": [
                {
                    "fixture_id": row["fixture_id"],
                    "transcript": row["transcript"],
                    "transcript_sha256": row["transcript_sha256"],
                    "chain_head": row["chain_head"],
                }
                for row in summary["fixtures"]
            ],
        }
        atomic_write_json(candidate_path, candidate)
    elif os.path.exists(candidate_path):
        os.unlink(candidate_path)

