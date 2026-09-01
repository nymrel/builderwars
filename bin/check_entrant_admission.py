#!/usr/bin/env python3
"""Adversarial checks for executable entrant admission.

The checker is offline.  It proves that hosted-untrusted execution, missing or
unknown scopes, and forged isolation metadata are refused before match-owned
filesystem or process side effects.  It also proves that both admitted local
scopes are truthfully bound into a replay-valid transcript.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from arena.admission import (  # noqa: E402
    CUSTOMER_CONTROLLED_LOCAL_V1,
    EXTERNAL_UNTRUSTED_HOSTED_V1,
    PROTOCOL,
    REFERENCE_REVIEWED_LOCAL_V1,
    UnsupportedEntrantExecution,
)
from arena.match import (  # noqa: E402
    run_customer_local_match,
    run_match,
    run_reference_match,
)
from arena.replay import verify  # noqa: E402


CHECKS = 0


def check(condition, label):
    global CHECKS
    if not condition:
        raise AssertionError(label)
    CHECKS += 1


def expect_error(action, error_type, fragment):
    try:
        action()
    except error_type as error:
        check(fragment in str(error), f"expected {fragment!r} in {error!r}")
        return error
    raise AssertionError(f"expected {error_type.__name__}: {fragment}")


def manifest(name, script, *, extra=None):
    row = {
        "name": name,
        "cmd": [sys.executable, script, "--backend", "stub:v1"],
        "env": [],
        "claimed_model": "stub:v1",
        "execution_claim": "scripted",
    }
    if extra:
        row.update(extra)
    return row


def header(path):
    with open(path, "r", encoding="utf-8") as handle:
        record = json.loads(handle.readline())
    check(record["kind"] == "header", "first record is the committed header")
    return record["body"]


def main():
    harness = os.path.join(ROOT, "entrants", "naive_harness.py")
    pair = [manifest("Local Alpha", harness), manifest("Local Beta", harness)]

    with tempfile.TemporaryDirectory(prefix="builderwars-admission-") as temp:
        root = Path(temp)

        missing_out = root / "missing-scope"
        expect_error(
            lambda: run_match(
                game_name="nim", seed=1, entrants=pair, out_dir=str(missing_out)
            ),
            TypeError,
            "execution_scope",
        )
        check(not missing_out.exists(), "missing scope creates no output directory")

        for index, bad_scope in enumerate((None, {}, "reference_local", True)):
            bad_out = root / f"bad-scope-{index}"
            expect_error(
                lambda bad_scope=bad_scope, bad_out=bad_out: run_match(
                    game_name="nim",
                    seed=2,
                    entrants=pair,
                    execution_scope=bad_scope,
                    out_dir=str(bad_out),
                ),
                ValueError,
                "execution_scope must be exactly one of",
            )
            check(not bad_out.exists(), f"invalid scope {index} creates no output directory")

        marker = root / "entrant-started.txt"
        marker_code = f"from pathlib import Path; Path({str(marker)!r}).write_text('started')"
        hostile_pair = [
            {
                **pair[0],
                "cmd": [sys.executable, "-c", marker_code],
            },
            pair[1],
        ]
        hosted_out = root / "hosted-untrusted"
        error = expect_error(
            lambda: run_match(
                game_name="nim",
                seed=3,
                entrants=hostile_pair,
                execution_scope=EXTERNAL_UNTRUSTED_HOSTED_V1,
                out_dir=str(hosted_out),
            ),
            UnsupportedEntrantExecution,
            "UNSUPPORTED_UNTRUSTED_EXECUTION",
        )
        check(error.scope == EXTERNAL_UNTRUSTED_HOSTED_V1, "refusal carries exact scope")
        check(not hosted_out.exists(), "hosted-untrusted refusal creates no output directory")
        check(not marker.exists(), "hosted-untrusted refusal starts no entrant process")

        forged_out = root / "forged-isolation"
        forged = [
            manifest(
                "Forged Alpha",
                harness,
                extra={"isolation_receipt": {"capability_isolation_attested": True}},
            ),
            pair[1],
        ]
        expect_error(
            lambda: run_reference_match(
                game_name="nim", seed=4, entrants=forged, out_dir=str(forged_out)
            ),
            ValueError,
            "unexpected keys",
        )
        check(not forged_out.exists(), "forged isolation metadata creates no output directory")

        reference = run_reference_match(
            game_name="nim",
            seed=5,
            entrants=pair,
            out_dir=str(root / "reference"),
            move_timeout_s=2,
        )
        reference_header = header(reference["transcript"])
        reference_admission = reference_header["entrant_admission"]
        check(reference_admission["protocol"] == PROTOCOL, "reference admission protocol is bound")
        check(
            reference_admission["scope"] == REFERENCE_REVIEWED_LOCAL_V1,
            "reference scope is bound",
        )
        check(reference_admission["decision"] == "ADMITTED_LOCAL_ONLY", "local-only decision is bound")
        check(reference_admission["platform_hosted"] is False, "reference is not platform-hosted")
        check(
            reference_admission["capability_isolation_attested"] is False,
            "reference run does not forge capability isolation",
        )
        check(verify(reference["transcript"])["verdict"] == "PASS", "reference replay remains valid")

        customer = run_customer_local_match(
            game_name="nim",
            seed=6,
            entrants=pair,
            out_dir=str(root / "customer"),
            move_timeout_s=2,
        )
        customer_admission = header(customer["transcript"])["entrant_admission"]
        check(
            customer_admission["scope"] == CUSTOMER_CONTROLLED_LOCAL_V1,
            "customer-controlled local scope is bound",
        )
        check(
            customer_admission["source_authority"] == "customer_controlled_unreviewed",
            "customer source remains explicitly unreviewed",
        )
        check(customer_admission["platform_hosted"] is False, "customer run is not platform-hosted")
        check(verify(customer["transcript"])["verdict"] == "PASS", "customer replay remains valid")

        expect_error(
            lambda: run_reference_match(
                game_name="nim",
                seed=7,
                entrants=pair,
                execution_scope=CUSTOMER_CONTROLLED_LOCAL_V1,
                out_dir=str(root / "wrapper-override"),
            ),
            TypeError,
            "fixes execution_scope",
        )
        check(not (root / "wrapper-override").exists(), "scope wrapper cannot be overridden")

    print(f"Executable entrant admission: PASS ({CHECKS} checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
