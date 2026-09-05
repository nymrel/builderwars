#!/usr/bin/env python3
"""Adversarial checks for executable entrant admission.

The checker is offline.  It proves that hosted-untrusted execution, missing or
unknown scopes, and forged isolation metadata are refused before match-owned
filesystem or process side effects.  It also proves that both admitted local
scopes are truthfully bound into a replay-valid transcript.
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest import mock

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
from arena.reference_sources import (  # noqa: E402
    PROTOCOL as REFERENCE_SOURCE_PROTOCOL,
    REVIEWED_REFERENCE_SOURCES,
    UnreviewedReferenceSource,
    registry_digest,
)


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
        check(
            reference_admission["reviewed_source_preflight_bound"] is True,
            "reference source preflight is explicitly bound",
        )
        check(
            reference_admission["reviewed_source_registry_protocol"]
            == REFERENCE_SOURCE_PROTOCOL,
            "reference source registry protocol is bound",
        )
        check(
            reference_admission["reviewed_source_registry_digest"] == registry_digest(),
            "reference source registry digest is bound",
        )
        check(
            reference_admission["reviewed_source_registry_entry_count"]
            == len(REVIEWED_REFERENCE_SOURCES),
            "reference source registry size is bound",
        )
        check(
            reference_admission["reviewed_source_registry_scope"]
            == "all_reviewed_entrant_sources",
            "reference registry covers entrant entrypoints and shared source dependencies",
        )
        reviewed_sources = reference_admission["reviewed_sources"]
        check(
            reviewed_sources
            == [
                {
                    "seat": seat,
                    "path": "entrants/naive_harness.py",
                    "sha256": REVIEWED_REFERENCE_SOURCES["entrants/naive_harness.py"],
                }
                for seat in (0, 1)
            ],
            "each reference seat binds its exact reviewed path and digest",
        )
        check(verify(reference["transcript"])["verdict"] == "PASS", "reference replay remains valid")

        copied_harness = root / "copied-naive-harness.py"
        shutil.copyfile(harness, copied_harness)
        copied_pair = [
            manifest("Copied Alpha", str(copied_harness)),
            manifest("Copied Beta", str(copied_harness)),
        ]
        copied_out = root / "copied-reference"
        expect_error(
            lambda: run_match(
                game_name="nim",
                seed=51,
                entrants=copied_pair,
                execution_scope=REFERENCE_REVIEWED_LOCAL_V1,
                out_dir=str(copied_out),
            ),
            UnreviewedReferenceSource,
            "outside the reviewed repository root",
        )
        check(
            not copied_out.exists(),
            "byte-identical external copy cannot bypass reference source authority",
        )

        unregistered = os.path.join(ROOT, "entrants", "backends.py")
        unregistered_pair = [
            manifest("Unregistered Alpha", unregistered),
            manifest("Unregistered Beta", unregistered),
        ]
        unregistered_out = root / "unregistered-reference"
        expect_error(
            lambda: run_reference_match(
                game_name="nim",
                seed=52,
                entrants=unregistered_pair,
                out_dir=str(unregistered_out),
            ),
            UnreviewedReferenceSource,
            "is not an executable reviewed entrypoint",
        )
        check(
            not unregistered_out.exists(),
            "unregistered repository source creates no output directory",
        )

        ambiguous_pair = [dict(pair[0]), dict(pair[1])]
        ambiguous_pair[0]["cmd"] = [sys.executable, "-c", "raise SystemExit(0)", harness]
        ambiguous_out = root / "ambiguous-reference"
        expect_error(
            lambda: run_reference_match(
                game_name="nim",
                seed=53,
                entrants=ambiguous_pair,
                out_dir=str(ambiguous_out),
            ),
            UnreviewedReferenceSource,
            "does not identify one exact supported harness",
        )
        check(
            not ambiguous_out.exists(),
            "ambiguous command creates no output directory or process",
        )

        drift_out = root / "digest-drift-reference"
        with mock.patch("arena.reference_sources.file_digest", return_value="0" * 64):
            expect_error(
                lambda: run_reference_match(
                    game_name="nim",
                    seed=54,
                    entrants=pair,
                    out_dir=str(drift_out),
                ),
                UnreviewedReferenceSource,
                "reviewed registry digest mismatch",
            )
        check(
            not drift_out.exists(),
            "reviewed source digest drift creates no output directory or process",
        )

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
        check(
            customer_admission["reviewed_source_preflight_bound"] is False
            and customer_admission["reviewed_source_registry_scope"] is None
            and customer_admission["reviewed_sources"] == [],
            "customer-local source is never mislabeled as repository reviewed",
        )
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
