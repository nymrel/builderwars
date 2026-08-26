#!/usr/bin/env python3
"""Adversarial offline checks for the customer-local cross-provider runner.

The checker never contacts a provider.  Its only child processes are the
deterministic stub entrants and the repository's standalone replay verifier,
all inside a temporary directory.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import io
import json
import os
import pathlib
import sys
import tempfile
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "bin")
sys.path.insert(0, ROOT)
sys.path.insert(0, BIN)

from arena.canonical import GENESIS, chain, digest  # noqa: E402
from arena.match import run_match, validate_manifest  # noqa: E402
from arena.transcript import load  # noqa: E402
from provider_hub.catalog import get_provider  # noqa: E402
from publishing.projection import verify_with_snapshot  # noqa: E402
from run_agentwars_league import final_scores, move_source_counts  # noqa: E402
import run_agentwars_cross_provider_match as candidate  # noqa: E402


CHECKS = 0
SECRET_SENTINEL = "customer-private-value-that-must-never-render"


def check(condition, label):
    global CHECKS
    if not condition:
        raise AssertionError(label)
    CHECKS += 1


def expect_error(action, message):
    try:
        action()
    except candidate.CrossProviderMatchError as error:
        check(str(error) == message, f"exact refusal code {message}")
        check(SECRET_SENTINEL not in str(error), "refusal never echoes customer key")
        return error
    raise AssertionError(f"expected CrossProviderMatchError({message!r})")


def parse(argv):
    return candidate.parser().parse_args(argv)


def base_argv(out_root, summary_path):
    return [
        "--out",
        str(out_root),
        "--json-out",
        str(summary_path),
        "--customer-local-v1",
        "--provider-usage-v1",
    ]


def check_provider_manifests(work):
    cases = (
        ("chatgpt_codex", None, None),
        ("claude_code", None, None),
        ("opencode", "opencode-go/ox-alpha-free", "max"),
        ("openrouter", "openai/gpt-5:free", None),
        ("hermes", "nous/hermes-4", None),
    )
    runtimes = []
    old_key = os.environ.get("OPENROUTER_API_KEY")
    try:
        os.environ["OPENROUTER_API_KEY"] = SECRET_SENTINEL
        for index, (provider, model, variant) in enumerate(cases):
            runtime = candidate.build_seat_runtime(
                candidate.SeatSpec(
                    name=f" Seat {index} ",
                    provider=provider,
                    strategy="win-now" if index % 2 == 0 else "long-game",
                    model=model,
                    variant=variant,
                ),
                backend_timeout=180,
            )
            runtimes.append(runtime)
            entry = get_provider(provider)
            manifest = runtime.manifest
            rendered_manifest = json.dumps(manifest, sort_keys=True)
            check(manifest["name"] == f"Seat {index}", f"{provider} trims edge whitespace")
            check(runtime.spec.name == f"Seat {index}", f"{provider} stores the normalized entrant name")
            check(runtime.spec.model == model, f"{provider} stores the bounded model selector")
            check(runtime.spec.variant == variant, f"{provider} stores the bounded variant selector")
            check(manifest["execution_claim"] == "hybrid", f"{provider} is never declared model-only")
            check(manifest["cmd"][0] == sys.executable, f"{provider} uses current Python")
            check(
                os.path.abspath(manifest["cmd"][1])
                == os.path.join(ROOT, "entrants", "fantasy_model_harness.py"),
                f"{provider} binds exact fantasy harness",
            )
            check(manifest["cmd"].count("--provider") == 1, f"{provider} has one provider selector")
            provider_index = manifest["cmd"].index("--provider")
            check(manifest["cmd"][provider_index + 1] == provider, f"{provider} selector is exact")
            check("--customer-local-v1" in manifest["cmd"], f"{provider} carries explicit local intent")
            check("--unsafe-custom-command" not in manifest["cmd"], f"{provider} cannot enable custom command")
            check("--provider-command" not in manifest["cmd"], f"{provider} has no arbitrary argv")
            check(runtime.connection_mode == entry["connection_mode"], f"{provider} connection claim from catalog")
            check(runtime.provider_class == entry["provider_class"], f"{provider} provider class from catalog")
            check(runtime.harness_class == entry["harness_class"], f"{provider} harness class from catalog")
            check(SECRET_SENTINEL not in rendered_manifest, f"{provider} manifest contains no key bytes")
            if provider == "openrouter":
                check(manifest["env"] == ["OPENROUTER_API_KEY"], "OpenRouter declares only exact key name")
                check(
                    runtime.provisioned_environment == {"OPENROUTER_API_KEY": SECRET_SENTINEL},
                    "OpenRouter key remains in process-local provisioned environment",
                )
            else:
                check(manifest["env"] == [], f"{provider} declares no injected environment")
                check(runtime.provisioned_environment == {}, f"{provider} receives no provisioned environment")
    finally:
        if old_key is None:
            os.environ.pop("OPENROUTER_API_KEY", None)
        else:
            os.environ["OPENROUTER_API_KEY"] = old_key

    expect_error(
        lambda: candidate.build_seat_runtime(
            candidate.SeatSpec("Unsafe", "custom_agent", "win-now"), backend_timeout=180
        ),
        "provider_not_supported_for_public_runner",
    )
    expect_error(
        lambda: candidate.build_seat_runtime(
            candidate.SeatSpec("Unknown", "made_up", "win-now"), backend_timeout=180
        ),
        "provider_not_supported_for_public_runner",
    )
    expect_error(
        lambda: candidate.build_seat_runtime(
            candidate.SeatSpec("Codex", "chatgpt_codex", "win-now", model="forbidden"),
            backend_timeout=180,
        ),
        "provider_options_invalid",
    )
    expect_error(
        lambda: candidate.build_seat_runtime(
            candidate.SeatSpec("OpenCode", "opencode", "win-now"), backend_timeout=180
        ),
        "provider_options_invalid",
    )
    expect_error(
        lambda: candidate.build_seat_runtime(
            candidate.SeatSpec("OpenRouter", "openrouter", "win-now", model="x", variant="max"),
            backend_timeout=180,
        ),
        "provider_options_invalid",
    )
    expect_error(
        lambda: candidate.build_seat_runtime(
            candidate.SeatSpec("Bad\nName", "chatgpt_codex", "win-now"), backend_timeout=180
        ),
        "entrant_name_invalid",
    )
    expect_error(
        lambda: candidate.build_seat_runtime(
            candidate.SeatSpec("Bad Strategy", "chatgpt_codex", "rush"), backend_timeout=180
        ),
        "strategy_invalid",
    )
    expect_error(
        lambda: candidate.build_seat_runtime(
            candidate.SeatSpec("Bad Timeout", "chatgpt_codex", "win-now"), backend_timeout=True
        ),
        "provider_timeout_invalid",
    )
    check(candidate._timeout(180.0004) == 180.0, "timeout normalization rounds sub-millisecond input once")
    check(candidate._timeout(180.0006) == 180.001, "timeout normalization preserves the next millisecond")
    check(candidate._timeout_text(candidate._timeout(180.0006)) == "180.001", "child timeout uses normalized value")
    with mock.patch.object(candidate, "get_provider_backend", return_value=mock.Mock(label="x" * 241)):
        expect_error(
            lambda: candidate.build_seat_runtime(
                candidate.SeatSpec("Bad Label", "chatgpt_codex", "win-now"), backend_timeout=180
            ),
            "backend_label_invalid",
        )
    for invalid_model in ("-provider/model", " provider/model", "provider model", "x" * 241, "provider/model\n"):
        expect_error(
            lambda invalid_model=invalid_model: candidate.build_seat_runtime(
                candidate.SeatSpec("Bad Model", "opencode", "win-now", model=invalid_model, variant="max"),
                backend_timeout=180,
            ),
            "provider_model_invalid",
        )
    for invalid_variant in ("-max", " max", "high effort", "x" * 241, "max\t"):
        expect_error(
            lambda invalid_variant=invalid_variant: candidate.build_seat_runtime(
                candidate.SeatSpec(
                    "Bad Variant",
                    "opencode",
                    "win-now",
                    model="opencode-go/ox-alpha-free",
                    variant=invalid_variant,
                ),
                backend_timeout=180,
            ),
            "provider_variant_invalid",
        )
    check(len(runtimes) == len(candidate.SUPPORTED_PROVIDERS), "every public provider has a construction check")

    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        try:
            parse(base_argv(work / "no-custom", work / "no-custom.json") + ["--seat0-provider", "custom_agent"])
        except SystemExit as error:
            check(error.code == 2, "CLI parser refuses custom_agent")
        else:
            raise AssertionError("CLI parser accepted custom_agent")


def check_preflight_refusals(work):
    args = parse(["--out", str(work / "missing-intent"), "--json-out", str(work / "missing-intent.json")])
    expect_error(lambda: candidate.run(args), "explicit_customer_provider_intent_required")

    nested_out = work / "overlap"
    args = parse(base_argv(nested_out, nested_out / "summary.json"))
    expect_error(lambda: candidate.run(args), "output_paths_overlap")
    check(not nested_out.exists(), "overlapping outputs refuse before directory creation")

    occupied = work / "occupied"
    occupied.mkdir()
    marker = occupied / "sentinel.txt"
    marker.write_text("preserve", encoding="utf-8")
    args = parse(base_argv(occupied, work / "unused-summary.json"))
    expect_error(lambda: candidate.run(args), "match_output_exists")
    check(marker.read_text(encoding="utf-8") == "preserve", "occupied match output is untouched")

    summary = work / "occupied-summary.json"
    summary.write_text("preserve", encoding="utf-8")
    args = parse(base_argv(work / "unused-match", summary))
    expect_error(lambda: candidate.run(args), "summary_output_exists")
    check(summary.read_text(encoding="utf-8") == "preserve", "occupied summary is untouched")

    args = parse(
        base_argv(work / "same-provider", work / "same-provider.json")
        + ["--seat1-provider", "chatgpt_codex"]
    )
    expect_error(lambda: candidate.run(args), "provider_claims_must_differ")
    check(not (work / "same-provider").exists(), "same-provider refusal occurs before a match starts")

    args = parse(base_argv(work / "duplicate-name", work / "duplicate-name.json") + ["--seat1-name", "codex redraft"])
    expect_error(lambda: candidate.run(args), "entrant_names_not_unique")
    check(not (work / "duplicate-name").exists(), "duplicate-name refusal occurs before a match starts")


def check_summary_reservation(work):
    direct_path = work / "direct-reservation.json"
    reservation = candidate.reserve_json_output(str(direct_path))
    check(direct_path.exists(), "summary reservation creates the exact output path")
    check(direct_path.stat().st_size == 0, "summary reservation is empty before commit")
    reservation.commit({"status": "held"})
    check(json.loads(direct_path.read_text(encoding="utf-8")) == {"status": "held"}, "reservation commit is exact")
    reservation.abort()
    check(direct_path.exists(), "abort after commit cannot remove accepted evidence")
    expect_error(lambda: reservation.commit({"status": "overwrite"}), "summary_reservation_not_open")
    check(json.loads(direct_path.read_text(encoding="utf-8")) == {"status": "held"}, "committed evidence is immutable")

    direct_match = work / "direct-match-reservation"
    check(
        candidate.reserve_match_output_directory(str(direct_match)) == str(direct_match.resolve()),
        "match reservation returns its exact absolute path",
    )
    check(direct_match.is_dir(), "match reservation atomically creates the output directory")
    expect_error(lambda: candidate.reserve_match_output_directory(str(direct_match)), "match_output_exists")
    marker = direct_match / "keep.txt"
    marker.write_text("debug-evidence", encoding="utf-8")
    candidate.remove_empty_match_output_directory(str(direct_match))
    check(marker.read_text(encoding="utf-8") == "debug-evidence", "non-empty match evidence survives cleanup")

    failure_summary = work / "reserved-failure.json"
    failure_out = work / "reserved-failure-match"
    failure_args = parse(base_argv(failure_out, failure_summary))

    def fail_after_reservation(**_kwargs):
        check(failure_summary.exists(), "summary is reserved before provider execution")
        check(failure_summary.stat().st_size == 0, "provider execution sees only an empty reservation")
        check(failure_out.is_dir(), "match directory is reserved before provider execution")
        raise RuntimeError("synthetic provider failure")

    with mock.patch.object(candidate, "run_match", side_effect=fail_after_reservation):
        try:
            candidate.run(failure_args)
        except RuntimeError as error:
            check(str(error) == "synthetic provider failure", "synthetic provider failure remains internal")
        else:
            raise AssertionError("synthetic provider failure was swallowed")
    check(not failure_summary.exists(), "failed match removes its unused summary reservation")
    check(not failure_out.exists(), "mocked failed match creates no match evidence")

    interrupt_summary = work / "reserved-interrupt.json"
    interrupt_out = work / "reserved-interrupt-match"
    interrupt_args = parse(base_argv(interrupt_out, interrupt_summary))
    with mock.patch.object(candidate, "run_match", side_effect=KeyboardInterrupt):
        try:
            candidate.run(interrupt_args)
        except KeyboardInterrupt:
            check(True, "provider interrupt is re-raised")
        else:
            raise AssertionError("synthetic provider interrupt was swallowed")
    check(not interrupt_summary.exists(), "provider interrupt removes its unused summary reservation")
    check(not interrupt_out.exists(), "provider interrupt removes its empty match reservation")

    race_summary = work / "reservation-race.json"
    race_out = work / "reservation-race-match"
    race_args = parse(base_argv(race_out, race_summary))
    real_builder = candidate.build_seat_runtime
    calls = 0

    def inject_summary_race(*args, **kwargs):
        nonlocal calls
        runtime = real_builder(*args, **kwargs)
        calls += 1
        if calls == 2:
            race_summary.write_text("preserve-race-winner", encoding="utf-8")
        return runtime

    with (
        mock.patch.object(candidate, "build_seat_runtime", side_effect=inject_summary_race),
        mock.patch.object(candidate, "run_match") as run_match_mock,
    ):
        expect_error(lambda: candidate.run(race_args), "summary_output_exists")
    run_match_mock.assert_not_called()
    check(race_summary.read_text(encoding="utf-8") == "preserve-race-winner", "reservation race preserves prior writer")
    check(not race_out.exists(), "reservation race refuses before provider execution")

    match_race_summary = work / "match-reservation-race.json"
    match_race_out = work / "match-reservation-race"
    match_race_args = parse(base_argv(match_race_out, match_race_summary))
    calls = 0

    def inject_match_race(*args, **kwargs):
        nonlocal calls
        runtime = real_builder(*args, **kwargs)
        calls += 1
        if calls == 2:
            match_race_out.mkdir()
            (match_race_out / "keep.txt").write_text("preserve-match-race-winner", encoding="utf-8")
        return runtime

    with (
        mock.patch.object(candidate, "build_seat_runtime", side_effect=inject_match_race),
        mock.patch.object(candidate, "run_match") as run_match_mock,
    ):
        expect_error(lambda: candidate.run(match_race_args), "match_output_exists")
    run_match_mock.assert_not_called()
    check(not match_race_summary.exists(), "match reservation race releases the unused summary reservation")
    check(
        (match_race_out / "keep.txt").read_text(encoding="utf-8") == "preserve-match-race-winner",
        "match reservation race preserves the prior writer",
    )


def stub_runtime(name, provider, strategy, backend_name):
    harness = os.path.join(ROOT, "entrants", "fantasy_model_harness.py")
    label = f"stub:{backend_name}"
    manifest = {
        "name": name,
        "cmd": [
            sys.executable,
            harness,
            "--name",
            name,
            "--strategy",
            strategy,
            "--backend",
            label,
        ],
        "env": [],
        "claimed_model": label,
        "execution_claim": "hybrid",
    }
    validate_manifest(manifest)
    entry = get_provider(provider)
    return candidate.SeatRuntime(
        spec=candidate.SeatSpec(name, provider, strategy),
        backend_label=label,
        connection_mode=entry["connection_mode"],
        provider_class=entry["provider_class"],
        harness_class=entry["harness_class"],
        manifest=manifest,
        provisioned_environment={},
    )


def rechain(records, path):
    previous = GENESIS
    output = []
    for sequence, raw in enumerate(records):
        record = {
            "kind": raw["kind"],
            "seq": sequence,
            "body": copy.deepcopy(raw["body"]),
        }
        hashed = chain(previous, record)
        output.append({**record, "prev": previous, "hash": hashed})
        previous = hashed
    pathlib.Path(path).write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n" for row in output),
        encoding="utf-8",
        newline="\n",
    )
    return previous


def summary_with_counts(result, report, runtimes, scores, counts):
    return candidate.build_summary(
        result={**result, "game": "fantasy_redraft", "seed": 9400},
        report=report,
        runtimes=runtimes,
        source_counts=counts,
        scores=scores,
    )


def check_offline_match_and_summary(work):
    runtimes = [
        stub_runtime("Offline Codex Claim", "chatgpt_codex", "win-now", "seat0"),
        stub_runtime("Offline Claude Claim", "claude_code", "long-game", "seat1"),
    ]
    result = run_match(
        game_name="fantasy_redraft",
        seed=9400,
        entrants=[runtime.manifest for runtime in runtimes],
        provisioned_envs=[{}, {}],
        out_dir=str(work / "offline-match"),
        move_timeout_s=30,
    )
    report = verify_with_snapshot(result["transcript"])
    check(report["verdict"] == "PASS", "offline fixture core replay passes")
    check(report["effective_verdict"] == "PASS", "offline fixture exact snapshot replay passes")
    check(report["verifier_snapshot_match"] is True, "offline fixture selects exact embedded verifier")
    audit = candidate.audit_transcript(result=result, report=report, runtimes=runtimes)
    check(audit == {"movesBySeat": [6, 6], "decisive": True, "clean": True}, "offline transcript audit")

    sources = move_source_counts(result["transcript"], [runtime.manifest for runtime in runtimes])
    scores = final_scores(result["transcript"])
    check(all(sum(row.values()) == 6 for row in sources.values()), "fixture has six accepted moves per seat")
    baseline = summary_with_counts(result, report, runtimes, scores, sources)
    core = {key: value for key, value in baseline.items() if key != "summaryDigest"}
    check(baseline["summaryDigest"] == digest(core), "summary digest covers every other summary field")
    check(baseline["publicationDecision"] == "not_reviewed_not_published", "summary cannot self-publish")
    check(baseline["providerClaimsDiffer"] is True, "summary records distinct provider claims")
    check(baseline["universalProviderOrModelRankingEligible"] is False, "open match cannot rank providers")
    check(all(baseline[field] is False for field in candidate.FALSE_ATTESTATIONS), "all trust attestations remain false")
    rendered = json.dumps(baseline, sort_keys=True)
    check(str(work) not in rendered, "summary contains no local evidence path")
    check(SECRET_SENTINEL not in rendered, "summary contains no customer key")

    names = [runtime.manifest["name"] for runtime in runtimes]
    all_model = {name: {"model": 6, "fallback": 0, "scripted": 0, "other": 0} for name in names}
    all_model_status = candidate._source_claim_status([all_model[name] for name in names])
    check(all_model_status == ("model_influenced_unattested", True), "all model-claimed moves remain unattested")

    mixed = {
        names[0]: {"model": 5, "fallback": 1, "scripted": 0, "other": 0},
        names[1]: {"model": 4, "fallback": 2, "scripted": 0, "other": 0},
    }
    mixed_status = candidate._source_claim_status([mixed[name] for name in names])
    check(mixed_status == ("mixed_model_and_fallback_unattested", False), "two influenced seats with fallbacks are mixed")

    partial = {
        names[0]: {"model": 6, "fallback": 0, "scripted": 0, "other": 0},
        names[1]: {"model": 0, "fallback": 6, "scripted": 0, "other": 0},
    }
    partial_status = candidate._source_claim_status([partial[name] for name in names])
    check(partial_status == ("partial_model_influence_unattested", False), "one influenced seat is not mislabeled fallback-only")

    fallback = {name: {"model": 0, "fallback": 6, "scripted": 0, "other": 0} for name in names}
    fallback_status = candidate._source_claim_status([fallback[name] for name in names])
    check(fallback_status == ("fallback_only_not_model_played", False), "zero model claims are fallback-only")

    bad_sources = copy.deepcopy(fallback)
    bad_sources[names[0]]["scripted"] = 1
    bad_sources[names[0]]["fallback"] = 5
    expect_error(
        lambda: candidate._source_claim_status([bad_sources[name] for name in names]),
        "source_count_competitive_invalid",
    )
    expect_error(
        lambda: summary_with_counts(result, report, runtimes, scores, all_model),
        "source_count_transcript_mismatch",
    )
    expect_error(
        lambda: summary_with_counts(result, {**report, "chain_head": "0" * 64}, runtimes, scores, sources),
        "summary_replay_binding_invalid",
    )
    expect_error(
        lambda: summary_with_counts(result, report, runtimes, [True, scores[1]], sources),
        "score_value_invalid",
    )
    expect_error(
        lambda: summary_with_counts({**result, "winner": None}, report, runtimes, scores, sources),
        "summary_winner_invalid",
    )
    expect_error(
        lambda: summary_with_counts({**result, "winner": True}, report, runtimes, scores, sources),
        "summary_winner_invalid",
    )

    output = work / "exclusive-summary.json"
    candidate.write_json_exclusive(str(output), baseline)
    check(json.loads(output.read_text(encoding="utf-8")) == baseline, "exclusive writer preserves summary")
    expect_error(lambda: candidate.write_json_exclusive(str(output), baseline), "summary_output_exists")
    check(json.loads(output.read_text(encoding="utf-8")) == baseline, "exclusive writer never overwrites")

    stale_result = {**result, "transcript": str(work / "different.jsonl")}
    expect_error(
        lambda: candidate.audit_transcript(result=stale_result, report=report, runtimes=runtimes),
        "replay_report_transcript_mismatch",
    )

    records = load(result["transcript"])
    script_tamper = copy.deepcopy(records)
    next(row for row in script_tamper if row["kind"] == "header")["body"]["entrants"][0]["script"] = {
        "path": "forged.py",
        "sha256": "0" * 64,
    }
    script_path = work / "script-rechained.jsonl"
    script_head = rechain(script_tamper, script_path)
    script_report = verify_with_snapshot(str(script_path))
    check(script_report["effective_verdict"] == "PASS", "replay alone permits self-declared script-label rewrite")
    script_result = {**result, "transcript": str(script_path), "chain_head": script_head}
    expect_error(
        lambda: candidate.audit_transcript(result=script_result, report=script_report, runtimes=runtimes),
        "header_entrant_binding_mismatch",
    )

    ready_tamper = copy.deepcopy(records)
    next(row for row in ready_tamper if row["kind"] == "ready")["body"]["entrant_message"]["backend"] = "forged-backend"
    ready_path = work / "ready-rechained.jsonl"
    ready_head = rechain(ready_tamper, ready_path)
    ready_report = verify_with_snapshot(str(ready_path))
    check(ready_report["effective_verdict"] == "PASS", "replay alone permits self-declared ready-label rewrite")
    ready_result = {**result, "transcript": str(ready_path), "chain_head": ready_head}
    expect_error(
        lambda: candidate.audit_transcript(result=ready_result, report=ready_report, runtimes=runtimes),
        "ready_backend_binding_mismatch",
    )

    ready_seat_tamper = copy.deepcopy(records)
    next(row for row in ready_seat_tamper if row["kind"] == "ready" and row["body"]["player"] == 1)["body"]["player"] = True
    ready_seat_path = work / "ready-seat-rechained.jsonl"
    ready_seat_head = rechain(ready_seat_tamper, ready_seat_path)
    ready_seat_report = verify_with_snapshot(str(ready_seat_path))
    ready_seat_result = {**result, "transcript": str(ready_seat_path), "chain_head": ready_seat_head}
    expect_error(
        lambda: candidate.audit_transcript(
            result=ready_seat_result,
            report=ready_seat_report,
            runtimes=runtimes,
        ),
        "ready_seat_invalid",
    )

    move_seat_tamper = copy.deepcopy(records)
    next(row for row in move_seat_tamper if row["kind"] == "move" and row["body"]["player"] == 1)["body"]["player"] = True
    move_seat_path = work / "move-seat-rechained.jsonl"
    move_seat_head = rechain(move_seat_tamper, move_seat_path)
    # A move-seat rewrite correctly breaks the engine digest. Keep the already
    # verified baseline report fields while rebinding only the audit identity so
    # this unit check reaches the runner's independent strict-type guard.
    move_seat_report = {
        **report,
        "transcript": str(move_seat_path),
        "chain_head": move_seat_head,
    }
    move_seat_result = {**result, "transcript": str(move_seat_path), "chain_head": move_seat_head}
    expect_error(
        lambda: candidate.audit_transcript(
            result=move_seat_result,
            report=move_seat_report,
            runtimes=runtimes,
        ),
        "move_seat_invalid",
    )

    source_tamper = copy.deepcopy(records)
    next(row for row in source_tamper if row["kind"] == "move")["body"]["entrant_message"]["note"] = "source=scripted"
    source_path = work / "source-rechained.jsonl"
    source_head = rechain(source_tamper, source_path)
    source_report = verify_with_snapshot(str(source_path))
    check(source_report["effective_verdict"] == "PASS", "replay alone permits self-declared source-label rewrite")
    source_result = {**result, "transcript": str(source_path), "chain_head": source_head}
    expect_error(
        lambda: candidate.audit_transcript(result=source_result, report=source_report, runtimes=runtimes),
        "move_source_claim_invalid",
    )
    check(
        candidate._valid_move_source_note("source=model;response_sha256=0123456789abcdef"),
        "bounded model-source note grammar accepts canonical digest",
    )
    check(
        not candidate._valid_move_source_note("source=model;reason=C:\\private\\secret"),
        "source-note grammar rejects path-shaped payloads",
    )
    check(
        not candidate._valid_move_source_note("source=fallback;reason=backend_error:RuntimeError;attempts=1;reason=duplicate"),
        "source-note grammar rejects duplicate fields",
    )


def check_main_failure_envelope(work):
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        status = candidate.main(["--out", str(work / "blocked"), "--json-out", str(work / "blocked.json")])
    payload = json.loads(stderr.getvalue())
    check(status == 1, "main returns bounded blocked status")
    check(
        payload
        == {
            "schemaVersion": candidate.SUMMARY_SCHEMA,
            "status": "blocked",
            "errorClass": "CrossProviderMatchError",
            "errorCode": "explicit_customer_provider_intent_required",
        },
        "main exposes only schema, status, class, and fixed runner code",
    )
    check(str(work) not in stderr.getvalue(), "failure envelope contains no local path")
    check(SECRET_SENTINEL not in stderr.getvalue(), "failure envelope contains no customer key")

    stderr = io.StringIO()
    with (
        mock.patch.object(candidate, "run", side_effect=RuntimeError(SECRET_SENTINEL)),
        contextlib.redirect_stderr(stderr),
    ):
        status = candidate.main(base_argv(work / "generic", work / "generic.json"))
    payload = json.loads(stderr.getvalue())
    check(status == 1, "generic failure returns blocked status")
    check(
        payload
        == {
            "schemaVersion": candidate.SUMMARY_SCHEMA,
            "status": "blocked",
            "errorClass": "RuntimeError",
        },
        "generic failure exposes no message or runner code",
    )
    check(SECRET_SENTINEL not in stderr.getvalue(), "generic failure cannot echo provider response or secret")

    stderr = io.StringIO()
    with (
        mock.patch.object(candidate, "run", side_effect=candidate.CrossProviderMatchError(SECRET_SENTINEL)),
        contextlib.redirect_stderr(stderr),
    ):
        status = candidate.main(base_argv(work / "malicious-code", work / "malicious-code.json"))
    payload = json.loads(stderr.getvalue())
    check(status == 1, "invalid runner code returns blocked status")
    check(payload["errorCode"] == "cross_provider_match_error", "invalid runner code is replaced by a fixed generic code")
    check(SECRET_SENTINEL not in stderr.getvalue(), "invalid runner code cannot echo secret-shaped input")


def main():
    with tempfile.TemporaryDirectory(prefix="check-cross-provider-match-") as temporary:
        work = pathlib.Path(temporary)
        check_provider_manifests(work)
        check_preflight_refusals(work)
        check_summary_reservation(work)
        check_offline_match_and_summary(work)
        check_main_failure_envelope(work)
    print(f"PASS: {CHECKS} cross-provider match checks")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as failure:
        print(f"FAIL - {failure}", file=sys.stderr)
        raise SystemExit(1)
