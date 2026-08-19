#!/usr/bin/env python3
"""Attack BuilderWars isolation claims and prove each guard fires.

This is intentionally separate from the ordinary unit suite. It runs the real
match engine, repairs a forged transcript's hash chain, and exits zero only when
strict admission and replay both refuse the stronger claim.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arena.canonical import GENESIS, chain  # noqa: E402
from arena.isolation import (  # noqa: E402
    IsolationRequirementError,
    resolve_isolation,
    validate_isolation_profile,
)
from arena.match import run_match  # noqa: E402
from arena.replay import verify  # noqa: E402
from arena.transcript import load  # noqa: E402

RESULTS = []


def check(name, ok, absent_guard_result, detail=""):
    RESULTS.append((name, bool(ok), absent_guard_result, detail))
    mark = "PASS" if ok else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{mark}] {name}{suffix}")
    return ok


def entrant(script):
    return {
        "name": Path(script).stem.replace("_", "-"),
        "cmd": [
            sys.executable,
            str(ROOT / "entrants" / script),
            "--backend",
            "stub:v1",
        ],
        "env": [],
        "claimed_model": "stub:v1",
    }


def rechain(path, mutate):
    records = load(path)
    mutate(records)
    previous = GENESIS
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for index, record in enumerate(records):
            body = {
                "kind": record["kind"],
                "seq": index,
                "body": record["body"],
            }
            digest = chain(previous, body)
            handle.write(
                json.dumps(
                    {**body, "prev": previous, "hash": digest},
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
                + "\n"
            )
            previous = digest


def main():
    print("\n=== BuilderWars isolation self-check ===")
    with tempfile.TemporaryDirectory(prefix="builderwars-isolation-") as temporary:
        root = Path(temporary)

        print("\n1. strict admission refuses before any match artifact")
        strict_out = root / "strict-must-not-exist"
        try:
            run_match(
                game_name="nim",
                seed=7,
                entrants=[entrant("solver_harness.py"), entrant("naive_harness.py")],
                out_dir=strict_out,
                require_capability_isolation=True,
            )
            refused = False
            refusal = "no refusal"
        except IsolationRequirementError as exc:
            refused = exc.to_json().get("match_started") is False
            refusal = exc.reason
        check(
            "capability requirement is refused",
            refused,
            "the engine would silently degrade into process mode",
            refusal,
        )
        check(
            "strict refusal created no output directory",
            not strict_out.exists(),
            "a transcript or scratch artifact would imply a match had started",
        )

        print("\n2. deleting limitations cannot make the profile stronger")
        deleted = resolve_isolation()
        del deleted["unenforced"]["network_egress_blocking"]
        try:
            validate_isolation_profile(deleted)
            deletion_rejected = False
        except ValueError:
            deletion_rejected = True
        check(
            "deleted network limitation is rejected",
            deletion_rejected,
            "a caller could omit an absent control and publish a cleaner-looking profile",
        )

        forged = resolve_isolation()
        forged["capability_isolation"] = True
        try:
            validate_isolation_profile(forged)
            claim_rejected = False
        except ValueError:
            claim_rejected = True
        check(
            "direct capability-isolation claim is rejected",
            claim_rejected,
            "process mode could label itself an OS jail",
        )

        print("\n3. a normal process match remains reproducible and honestly bounded")
        good = run_match(
            game_name="nim",
            seed=23,
            entrants=[entrant("solver_harness.py"), entrant("naive_harness.py")],
            out_dir=root / "good",
        )
        report = verify(good["transcript"])
        check(
            "ordinary process match replay-verifies",
            report["verdict"] == "PASS",
            "the new claim gate would have broken the existing referee path",
            f"winner=seat{good['winner']}",
        )
        check(
            "replay carries the capability-unconfined caveat",
            any("capability-unconfined" in item for item in report["does_not_prove"]),
            "a reader could see PASS without the isolation limitation",
        )

        print("\n4. repairing the chain does not rescue a forged isolation claim")
        rechain(
            good["transcript"],
            lambda records: records[0]["body"]["isolation"].__setitem__(
                "capability_isolation", True
            ),
        )
        forged_report = verify(good["transcript"])
        check(
            "forged profile has a valid repaired hash chain",
            forged_report["chain_ok"] is True,
            "the test would not exercise the replay guard beyond ordinary tamper evidence",
        )
        check(
            "re-chained capability forgery still fails",
            forged_report["verdict"] == "FAIL"
            and forged_report["isolation_profile_ok"] is False,
            "a careful forger could publish stronger isolation than the match used",
        )

    passed = sum(1 for _, ok, _, _ in RESULTS if ok)
    print(f"\n{passed}/{len(RESULTS)} isolation attacks caught")
    if passed != len(RESULTS):
        print("\nFailures and what their missing guards would allow:")
        for name, ok, absent, detail in RESULTS:
            if not ok:
                print(f"  - {name}: {absent}" + (f" ({detail})" if detail else ""))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
