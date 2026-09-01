#!/usr/bin/env python3
"""Adversarial, provider-free checks for the AgentWars starter qualification."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "bin"
if str(BIN) not in sys.path:
    sys.path.insert(0, str(BIN))

from qualify_agentwars_starter import (  # noqa: E402
    GAME,
    SCHEMA_VERSION,
    SEED,
    STATUS,
    TRUTH,
    StarterQualificationError,
    build_qualification,
)


PASSED = 0


def check(condition: bool, name: str) -> None:
    global PASSED
    if not condition:
        raise AssertionError(name)
    PASSED += 1
    print(f"[PASS] {name}")


def tree_bytes(path: Path) -> dict[str, bytes]:
    return {
        file.relative_to(path).as_posix(): file.read_bytes()
        for file in sorted(path.rglob("*"))
        if file.is_file()
    }


def canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("ascii")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def safe_child_env() -> dict[str, str]:
    allowed = (
        "COMSPEC",
        "HOMEDRIVE",
        "HOMEPATH",
        "LOCALAPPDATA",
        "PATH",
        "PATHEXT",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "USERPROFILE",
        "WINDIR",
    )
    environment = {name: os.environ[name] for name in allowed if name in os.environ}
    environment.update(
        {
            "ANTHROPIC_API_KEY": "must-not-reach-an-entrant",
            "OPENAI_API_KEY": "must-not-reach-an-entrant",
            "OPENROUTER_API_KEY": "must-not-reach-an-entrant",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    return environment


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="agentwars-starter-check-") as raw_work:
        work = Path(raw_work)
        first = work / "first"
        second = work / "second"
        first_receipt = build_qualification(first)
        second_receipt = build_qualification(second)

        check(tree_bytes(first) == tree_bytes(second), "two starter qualifications are byte identical")
        check(
            first_receipt["schemaVersion"] == SCHEMA_VERSION
            and first_receipt["status"] == STATUS,
            "receipt pins the starter qualification schema and local-only status",
        )
        check(
            first_receipt["game"] == GAME
            and first_receipt["gameVersion"] == "1"
            and first_receipt["seed"] == SEED
            and first_receipt["fixtureCount"] == first_receipt["seatOrders"] == 2,
            "receipt pins one redraft seed and both seat orders",
        )
        check(
            first_receipt["allReplaysVerified"] is True
            and first_receipt["allMovesScripted"] is True
            and len(first_receipt["transcripts"]) == 2,
            "receipt binds two replay-verified scripted transcripts",
        )
        check(first_receipt["truth"] == TRUTH, "receipt preserves the complete non-attestation boundary")
        receipt_without_digest = dict(first_receipt)
        receipt_digest = receipt_without_digest.pop("receiptDigest")
        check(
            receipt_digest == sha256(canonical(receipt_without_digest))
            and first_receipt["summarySha256"]
            == sha256((first / first_receipt["summaryFile"]).read_bytes())
            and all(
                row["sha256"] == sha256((first / row["file"]).read_bytes())
                for row in first_receipt["transcripts"]
            ),
            "receipt digest binds the summary and both transcript bytes",
        )
        check(
            all(
                first_receipt["truth"][key] is False
                for key in (
                    "customerHarnessQualified",
                    "customerModelQualified",
                    "deploymentAuthorized",
                    "hostedRuntimeQualified",
                    "modelAttested",
                    "personAttested",
                    "providerAccountAttested",
                    "publicationAuthorized",
                    "rankingAuthorized",
                )
            ),
            "starter cannot elevate a user, model, provider, rank, publish, or deploy claim",
        )
        check(
            first_receipt["truth"]["networkEgressBlocked"] is False
            and first_receipt["truth"]["filesystemConfinementEnforced"] is False,
            "starter does not overclaim OS containment",
        )
        summary = json.loads((first / "league-summary.json").read_text(encoding="utf-8"))
        check(
            summary["status"] == "scripted_preseason"
            and summary["modelAttested"] is False
            and summary["executionClaimsAttested"] is False,
            "league summary remains scripted preseason and unattested",
        )
        matches = summary["formats"][0]["matches"]
        check(
            len(matches) == 2
            and all(match["verified"] is True for match in matches)
            and {match["seat0"] for match in matches}
            == {"Starter Win Now", "Starter Long Game"},
            "both fixed entrants receive each seat once",
        )
        check(
            all(
                counts["scripted"] > 0
                and counts["model"] == counts["fallback"] == counts["other"] == 0
                for match in matches
                for counts in match["moveSourceClaims"].values()
            ),
            "every recorded starter move is scripted",
        )

        try:
            build_qualification(first)
        except StarterQualificationError as error:
            check("already exists" in str(error), "starter refuses overwrite")
        else:
            raise AssertionError("starter accepted overwrite")
        check(
            set(path.name for path in work.iterdir()) == {"first", "second"},
            "overwrite refusal leaves no partial output",
        )
        failed = work / "failed"
        try:
            with mock.patch(
                "qualify_agentwars_starter.run_league",
                side_effect=RuntimeError("injected starter failure"),
            ):
                build_qualification(failed)
        except RuntimeError:
            check(not failed.exists(), "failed qualification removes its partial output")
        else:
            raise AssertionError("injected starter failure was not raised")

        cli_out = work / "cli"
        result = subprocess.run(
            [sys.executable, "-B", str(ROOT / "bin" / "qualify_agentwars_starter.py"), "--out", str(cli_out)],
            cwd=ROOT,
            env=safe_child_env(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="strict",
            timeout=60,
            check=False,
        )
        check(
            result.returncode == 0
            and cli_out.is_dir()
            and "no customer harness" in result.stdout.lower(),
            "one-command CLI passes with ambient provider keys withheld from entrants",
        )
        help_result = subprocess.run(
            [sys.executable, "-B", str(ROOT / "bin" / "qualify_agentwars_starter.py"), "--help"],
            cwd=ROOT,
            env=safe_child_env(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="strict",
            timeout=15,
            check=False,
        )
        check(
            help_result.returncode == 0
            and "--out" in help_result.stdout
            and "provider" not in help_result.stdout.lower(),
            "public starter CLI exposes no provider or credential option",
        )

    print(f"AgentWars starter kit contracts: PASS ({PASSED} checks)")
    print("offline scripted qualification / replay verified / no provider / no rank / no publication")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
