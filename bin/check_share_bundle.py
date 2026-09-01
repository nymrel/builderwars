#!/usr/bin/env python3
"""Focused adversarial contracts for AgentWars verified-moment bundles."""

import copy
import json
import os
import sys
import tempfile
import unicodedata
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))

from arena.canonical import GENESIS, chain, digest  # noqa: E402
from arena.match import (  # noqa: E402
    run_customer_local_match,
    run_reference_match as run_match,
)
from arena.transcript import load  # noqa: E402
from build_share_bundle import (  # noqa: E402
    BundleError,
    EVENT_SCHEMA,
    EVENT_VALUE_ALLOWLISTS,
    OUTPUT_NAMES,
    build_manifest,
    build_outputs,
    entrant_rows,
    final_state,
    normalize_base_url,
    require_exact_verification,
    select_highlight,
    source_kind,
    story_details,
    ten_fronts_scores,
    write_bundle,
)
from export_site import summarise  # noqa: E402
from publishing.projection import project_receipt  # noqa: E402
from publishing.runback import (  # noqa: E402
    accept_runback,
    empty_lineage_state,
    issue_runback,
    validate_surface_shape,
)

TEN_FRONTS = os.path.join(
    ROOT,
    "matches",
    "agentwars-ten-fronts",
    "ten_fronts",
    "7000-0",
    "e16ac35d43eb3b47.jsonl",
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def scripted_manifest(name, strategy):
    script = os.path.join(ROOT, "entrants", "fantasy_gm_harness.py")
    return {
        "name": name,
        "cmd": [sys.executable, script, "--name", name, "--strategy", strategy],
        "env": [],
        "claimed_model": "scripted-baseline:v1",
        "execution_claim": "scripted",
    }


def expect_bundle_error(fn, fragment):
    try:
        fn()
    except BundleError as error:
        require(fragment in str(error), f"expected {fragment!r} in {error!r}")
        return
    raise AssertionError(f"expected BundleError containing {fragment!r}")


def build_fixture(work, names=("Sunday Machine", "Future Proof")):
    result = run_match(
        game_name="fantasy_redraft",
        seed=9400,
        entrants=[scripted_manifest(names[0], "win-now"), scripted_manifest(names[1], "long-game")],
        out_dir=os.path.join(work, "match"),
    )
    return result["transcript"]


def rewrite_and_rechain(transcript, mutate):
    with open(transcript, "r", encoding="utf-8") as fh:
        records = [json.loads(line) for line in fh]
    mutate(records)
    previous = GENESIS
    for record in records:
        body = {"kind": record["kind"], "seq": record["seq"], "body": record["body"]}
        record["prev"] = previous
        record["hash"] = chain(previous, body)
        previous = record["hash"]
    with open(transcript, "w", encoding="utf-8", newline="\n") as fh:
        for record in records:
            fh.write(json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n")


def check_source_claims():
    require(source_kind("source=model") == "model", "bare model source")
    require(source_kind("source=model;response_sha256=abc") == "model", "model metadata tail")
    require(source_kind("source=model_plan;plan_sha256=" + "a" * 64) == "model",
            "fixed model-plan source is model-influenced")
    require(source_kind("source=fallback;reason=bad") == "fallback", "fallback metadata tail")
    require(source_kind("source=fallback:rejected_model_answer") == "fallback",
            "historical colon fallback tail")
    require(source_kind("source=scripted_board;strategy=win-now") == "scripted", "scripted variant")
    require(source_kind("source=modelish;response_sha256=abc") == "other",
            "source claims require an exact token")
    require(source_kind("model probably") == "other", "unstructured source must stay other")


def check_bundle_contract():
    with tempfile.TemporaryDirectory(prefix="agentwars-share-check-") as work:
        transcript = build_fixture(work)
        first = build_outputs(transcript)
        second = build_outputs(transcript)
        require(first == second, "same verified receipt must produce byte-identical bundle outputs")
        expect_bundle_error(
            lambda: require_exact_verification(
                {"verdict": "PASS", "verifier_snapshot_match": True}
            ),
            "exact embedded verifier-engine match",
        )
        require(tuple(first) == OUTPUT_NAMES, "bundle file order and surface must stay bounded")
        manifest = json.loads(first["manifest.json"])
        require(manifest["match"]["verified"] is True, "bundle must record replay verification")
        require(manifest["truth"]["status"] == "scripted_preseason", "scripted truth label")
        require(manifest["truth"]["modelAttested"] is False, "model attestation must stay false")
        require(manifest["truth"]["executionClaimsAttested"] is False,
                "execution attestation must stay false")
        require(manifest["truth"]["entrantIdentityAttested"] is False,
                "entrant display names must stay self-declared")
        require(manifest["highlight"]["kind"] == "top_scoring_pick", "fantasy highlight kind")
        require(manifest["highlight"]["clipId"].startswith("clip_"), "bounded moment id")
        require("not a causal" in manifest["highlight"]["label"], "highlight causality guard")
        runback = manifest["rivalry"]["runback"]
        golden_core = {
            "parentMatchId": manifest["match"]["id"],
            "parentReceiptId": manifest["match"]["receiptId"],
            "parentFixtureId": manifest["match"]["fixtureId"],
            "parentChainHead": manifest["match"]["chainHead"],
            "game": manifest["match"]["game"],
            "seed": 9401,
            "seats": [
                manifest["entrants"][1]["name"],
                manifest["entrants"][0]["name"],
            ],
        }
        require(
            runback
            == {
                "status": "unplayed_challenge",
                "challengeId": "challenge_" + digest(golden_core)[:16],
                **golden_core,
            },
            "default share runback preserves the exact legacy v1 golden shape and types",
        )
        require(
            "runbackSurface" not in manifest["rivalry"],
            "default share payload omits the optional proof surface sibling",
        )
        require("response_sha256" not in "".join(first.values()), "derived pack must omit response hashes")
        require("OPENCODE_" not in "".join(first.values()), "derived pack must omit environment names")
        require(
            ".diagnostics.jsonl" not in "".join(first.values())
            and "agentwars-transcript-snapshot-" not in "".join(first.values())
            and work not in "".join(first.values()),
            "public bundle must exclude private diagnostics and local snapshot paths",
        )
        require(all("claimedModel" not in entrant for entrant in manifest["entrants"]),
                "share bundle must omit untrusted claimed-model strings")
        require(manifest["verification"]["localCommandTemplate"] ==
                "python verify.py PATH_TO_TRANSCRIPT.jsonl", "local verification must not imply publication")
        require(all("href" not in field for spec in EVENT_SCHEMA.values()
                    for field in spec["required"] + spec["optional"]), "events must omit raw href")
        require("share_intent_recorded" in EVENT_SCHEMA, "primary share-intent metric needs an event")
        require(EVENT_VALUE_ALLOWLISTS["share_method"] == ["native", "copy", "download"],
                "share methods must be bounded")
        require(EVENT_VALUE_ALLOWLISTS["vote"] == ["seat0", "seat1", "runback"],
                "spectator votes must be bounded")

        records = load(transcript)
        state = final_state(records)
        result = next(record["body"] for record in records if record["kind"] == "result")
        baseline_highlight = select_highlight(records, state, result.get("winner"))
        original_position = next(
            index
            for index, record in enumerate(records)
            if record.get("hash") == baseline_highlight["recordHash"]
        )
        rejected_copy = copy.deepcopy(records[original_position])
        rejected_copy["body"]["legal"] = False
        rejected_copy["hash"] = "0" * 64
        records.insert(original_position, rejected_copy)
        guarded_highlight = select_highlight(records, state, result.get("winner"))
        require(
            guarded_highlight["recordHash"] == baseline_highlight["recordHash"],
            "top-pick highlight must ignore a rejected move for the same player",
        )
        expect_bundle_error(
            lambda: story_details(
                "fantasy_redraft",
                manifest["entrants"],
                {"winner": None, "reason": "forfeit:illegal_move"},
                state,
                {"kind": "forfeit_adjudication"},
            ),
            "winning seat",
        )

        tagged = build_manifest(transcript, "https://nymrel.com/builderwars")
        require(tagged["activationStatus"] == "candidate_url_unverified", "candidate route truth")
        url = tagged["campaign"]["candidateUrl"]
        require("source_label=agentwars_share_bundle" in url, "source label retained in candidate URL")
        require("campaign_id=agentwars_verified_moments_v1" in url, "campaign id retained")
        require(tagged["campaign"]["performanceMeasured"] is False, "no performance laundering")

        export, report = summarise(transcript)
        require(report["verdict"] == "PASS" and export is not None, "site exporter replay gate")
        require(export["truthStatus"] == "scripted_preseason", "site and share truth labels agree")
        require(all(seat["scriptedMoves"] > 0 for seat in export["seats"]),
                "site exporter must classify scripted source variants")

        out = os.path.join(work, "bundle")
        write_bundle(transcript, out)
        require(sorted(os.listdir(out)) == sorted(OUTPUT_NAMES), "writer emits only bounded files")
        expect_bundle_error(lambda: write_bundle(transcript, out), "already exists")


def check_hostile_names_are_escaped():
    with tempfile.TemporaryDirectory(prefix="agentwars-share-hostile-") as work:
        hostile = "<script>\x00\u202ealert(1)</script> & Winner"
        transcript = build_fixture(work)
        def mutate(records):
            records[0]["body"]["entrants"][0]["name"] = hostile
            records[0]["body"]["entrants"][1]["name"] = "Future <img src=x>\x1f"
        rewrite_and_rechain(transcript, mutate)
        outputs = build_outputs(transcript)
        require("<script>alert" not in outputs["match.html"], "hostile name must not create HTML script")
        require("<script>alert" not in outputs["card.svg"], "hostile name must not create SVG script")
        require("&lt;script&gt;" in outputs["match.html"], "hostile name should remain visibly escaped")
        require("<img src=x>" not in outputs["match.html"], "hostile image tag must be escaped")
        ET.fromstring(outputs["card.svg"])
        for name, content in outputs.items():
            require("\x00" not in content, f"{name} must not contain NUL")
            require(all(
                char in "\n\r\t" or unicodedata.category(char) not in ("Cc", "Cf", "Cs")
                for char in content
            ), f"{name} must not contain unsafe control or format characters")


def check_public_identity_guard():
    digest_value = "a" * 64
    header = {
        "entrants": [
            {"seat": 0, "name": "Same Name", "execution_claim": "scripted",
             "manifest_digest": digest_value},
            {"seat": 1, "name": " same   name ", "execution_claim": "scripted",
             "manifest_digest": "b" * 64},
        ]
    }
    expect_bundle_error(lambda: entrant_rows(header), "collide")


def check_hostile_match_id_is_refused():
    with tempfile.TemporaryDirectory(prefix="agentwars-share-match-id-") as work:
        transcript = build_fixture(work)
        rewrite_and_rechain(
            transcript,
            lambda records: records[0]["body"].__setitem__("match_id", ".."),
        )
        expect_bundle_error(lambda: build_manifest(transcript), "match id")


def check_tamper_refusal_has_no_partial_output():
    with tempfile.TemporaryDirectory(prefix="agentwars-share-tamper-") as work:
        transcript = build_fixture(work)
        with open(transcript, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        first = json.loads(lines[0])
        first["body"]["seed"] += 1
        lines[0] = json.dumps(first, sort_keys=True, separators=(",", ":")) + "\n"
        tampered = os.path.join(work, "tampered.jsonl")
        with open(tampered, "w", encoding="utf-8", newline="\n") as fh:
            fh.writelines(lines)
        out = os.path.join(work, "must-not-exist")
        expect_bundle_error(lambda: write_bundle(tampered, out), "refusing unverified")
        require(not os.path.exists(out), "failed verification must leave no output directory")


def check_runtime_forfeit_refusal():
    with tempfile.TemporaryDirectory(prefix="agentwars-share-forfeit-") as work:
        script = os.path.join(ROOT, "entrants", "fantasy_gm_harness.py")
        entrants = [
            {
                "name": "Exit Early",
                "cmd": [sys.executable, "-c", "raise SystemExit(0)"],
                "env": [],
                "claimed_model": "scripted-exit:v1",
                "execution_claim": "scripted",
            },
            {
                "name": "Sunday Machine",
                "cmd": [sys.executable, script, "--name", "Sunday Machine", "--strategy", "win-now"],
                "env": [],
                "claimed_model": "scripted-baseline:v1",
                "execution_claim": "scripted",
            },
        ]
        result = run_customer_local_match(
            game_name="fantasy_redraft",
            seed=9450,
            entrants=entrants,
            out_dir=os.path.join(work, "match"),
        )
        require(result["reason"] == "forfeit:entrant_exited", "forfeit fixture must be decisive")
        expect_bundle_error(
            lambda: build_outputs(result["transcript"]),
            "runtime-only or malformed forfeits",
        )
        export, report = summarise(result["transcript"])
        require(
            export is None and report["verdict"] == "FAIL",
            "site export excludes an unattested runtime-forfeit win",
        )
        out = os.path.join(work, "must-not-exist")
        expect_bundle_error(
            lambda: write_bundle(result["transcript"], out),
            "runtime-only or malformed forfeits",
        )
        require(not os.path.exists(out), "runtime-forfeit refusal leaves no partial bundle")


def check_generic_historical_match():
    transcript = os.path.join(ROOT, "matches", "series", "1000-0", "935cef8302327b32.jsonl")
    manifest = build_manifest(transcript)
    require(manifest["match"]["game"] == "nim", "historical generic game remains supported")
    require(manifest["highlight"]["kind"] == "forfeit_adjudication",
            "historical forfeit needs a terminal highlight")
    require(manifest["verification"]["engineDigestMatch"] is True,
            "historical bundle must use an exact embedded engine snapshot")
    export, report = summarise(transcript)
    require(report["verdict"] == "PASS" and export is not None, "historical exporter replay gate")
    require(export["engineDigestMatch"] is True, "exported historical row needs exact engine proof")
    require(sum(seat["fallbackMoves"] for seat in export["seats"]) == 3,
            "historical colon fallback notes must remain fallbacks")
    missing_snapshot = os.path.join(ROOT, "matches", "e18c36c2f8903c1f.jsonl")
    expect_bundle_error(lambda: build_manifest(missing_snapshot), "exact embedded verifier-engine match")
    missing_row, missing_report = summarise(missing_snapshot)
    require(missing_row is None and missing_report["verdict"] == "FAIL",
            "site exporter must exclude a receipt whose exact engine snapshot is unavailable")
    completed = os.path.join(ROOT, "matches", "ollama", "5000-0", "3d76188786332a12.jsonl")
    completed_manifest = build_manifest(completed)
    require(completed_manifest["highlight"]["kind"] == "final_accepted_move",
            "completed non-fantasy receipt needs a final accepted-move highlight")


def check_url_guard():
    require(normalize_base_url("https://nymrel.com/builderwars/") ==
            "https://nymrel.com/builderwars", "base URL normalization")
    for value in (
        "javascript:alert(1)",
        "https://user:secret@example.com/path",
        "https://example.com/path?secret=value",
        "https://example.com/path#fragment",
        "https://example.com/bad path",
        "https://example.com\\@evil.test/path",
    ):
        expect_bundle_error(lambda value=value: normalize_base_url(value), "public base URL")


def check_ten_fronts_moment_bundle():
    require(ten_fronts_scores({"scores": [319, 226]}) == [319, 226], "canonical scores accepted")
    for hostile in (None, {}, {"scores": [319]}, {"scores": [319.0, 1]}, {"scores": [-2, 4]}):
        expect_bundle_error(lambda hostile=hostile: ten_fronts_scores(hostile), "ten fronts")

    first = build_outputs(TEN_FRONTS)
    second = build_outputs(TEN_FRONTS)
    require(first == second, "ten fronts bundle must be deterministic")
    manifest = json.loads(first["manifest.json"])
    require(manifest["match"]["game"] == "ten_fronts", "reviewed offline reference game")
    story = manifest["story"]
    require(story["headline"] == "Stub Iron Front wins ten fronts", "state-derived headline")
    require(story["resultLine"] == "319–226 over Stub Even Reserve",
            "share typography result line with en dash")
    require(story["scores"] == {"Stub Iron Front": 319, "Stub Even Reserve": 226},
            "seat-order referee scores in share story")
    require(story["margin"] == 93, "margin derived from referee state only")
    require(story["question"] == "Would you run this match back?", "honest runback question")
    require(manifest["highlight"]["kind"] == "final_accepted_move",
            "bounded final-accepted-move clip contract remains")
    require(manifest["highlight"]["clipId"].startswith("clip_"), "bounded moment id")
    require(manifest["truth"]["status"] == "scripted_preseason", "scripted truth label")
    require(manifest["truth"]["modelAttested"] is False, "no model attestation")
    require(manifest["truth"]["executionClaimsAttested"] is False,
            "execution claims stay unattested")
    sources = manifest["moveSourceClaims"]
    require(all(row["fallback"] == 40 and row["model"] == 0
                for row in sources.values()), "per-seat fallback counts stay 40/40")
    runback = manifest["rivalry"]["runback"]
    require(runback["status"] == "unplayed_challenge", "runback is an unplayed challenge")
    require(runback["seed"] == 7001, "runback seed is deterministic parent+1")
    require(
        runback["seats"]
        == [manifest["entrants"][1]["name"], manifest["entrants"][0]["name"]]
        and all(type(value) is str for value in runback["seats"]),
        "legacy share runback preserves display-name seat strings",
    )
    require("runbackSurface" not in manifest["rivalry"], "default Ten Fronts payload omits proof surface")
    require("response_sha256" not in "".join(first.values()),
            "ten fronts pack must omit response hashes")
    rendered = json.dumps(manifest, sort_keys=True)
    for fragment in ("stub:v1", "invalid_model_output"):
        require(fragment not in rendered, f"share manifest leaked raw value {fragment!r}")

    with tempfile.TemporaryDirectory(prefix="agentwars-share-tenfronts-bytes-") as work:
        out_a = os.path.join(work, "bundle-a")
        out_b = os.path.join(work, "bundle-b")
        write_bundle(TEN_FRONTS, out_a)
        write_bundle(TEN_FRONTS, out_b)
        for name in OUTPUT_NAMES:
            with open(os.path.join(out_a, name), "rb") as handle_a, \
                    open(os.path.join(out_b, name), "rb") as handle_b:
                require(handle_a.read() == handle_b.read(),
                        f"byte-identical {name} across two temp directories")

    with tempfile.TemporaryDirectory(prefix="agentwars-ten-fronts-refusal-") as work:
        bad = os.path.join(work, "malformed-scores.jsonl")

        def break_scores(records):
            states = [row for row in records if row.get("kind") == "state"]
            states[-1]["body"]["state"]["scores"] = [319]

        rewrite_and_rechain_copy(TEN_FRONTS, bad, break_scores)
        expect_bundle_error(lambda: build_manifest(bad), "refusing unverified")


def check_completed_runback_surface():
    with tempfile.TemporaryDirectory(prefix="agentwars-share-runback-") as work:
        parent_result = run_match(
            game_name="fantasy_redraft",
            seed=9420,
            entrants=[
                scripted_manifest("Share Sunday", "win-now"),
                scripted_manifest("Share Future", "long-game"),
            ],
            out_dir=os.path.join(work, "parent"),
            match_id="share-surface-parent",
        )
        child_result = run_match(
            game_name="fantasy_redraft",
            seed=9421,
            entrants=[
                scripted_manifest("Share Future", "long-game"),
                scripted_manifest("Share Sunday", "win-now"),
            ],
            out_dir=os.path.join(work, "child"),
            match_id="share-surface-child",
        )
        parent, _parent_records = project_receipt(parent_result["transcript"])
        child, _child_records = project_receipt(child_result["transcript"])
        challenge = issue_runback(parent, transcript_path=parent_result["transcript"])
        acceptance = accept_runback(
            challenge,
            parent,
            child,
            parent_transcript_path=parent_result["transcript"],
            child_transcript_path=child_result["transcript"],
        )
        runback_proof = {
            "acceptance": acceptance,
            "challenge": challenge,
            "parentReceipt": parent,
            "parentTranscriptPath": parent_result["transcript"],
            "childReceipt": child,
            "childTranscriptPath": child_result["transcript"],
        }
        outputs = build_outputs(
            parent_result["transcript"],
            runback_proof=runback_proof,
            previous_lineage_state=empty_lineage_state(),
        )
        manifest = json.loads(outputs["manifest.json"])
        legacy = manifest["rivalry"]["runback"]
        surface = manifest["rivalry"]["runbackSurface"]
        require(
            legacy["status"] == "unplayed_challenge"
            and all(type(value) is str for value in legacy["seats"]),
            "proof candidate preserves the legacy share runback unchanged",
        )
        require(
            surface["status"] == "completed_runback_pending_registry_commit",
            "exact proof produces only a pending share surface",
        )
        require(
            surface["acceptedEdge"]["childReceiptId"] == child["receiptId"],
            "share surface pins exact accepted child receipt",
        )
        require(validate_surface_shape(surface) == surface, "pending share surface shape validates")
        require(
            "VERIFIED / PENDING REGISTRY COMMIT" in outputs["card.svg"]
            and "COMPLETE" not in outputs["card.svg"],
            "pending card never renders authoritative completion",
        )
        require(
            "Runback verified / pending registry commit" in outputs["match.html"]
            and "Runback complete" not in outputs["match.html"],
            "pending HTML never renders authoritative completion",
        )
        require(
            "Runback replay verified / pending registry commit" in outputs["copy.md"]
            and "Runback completed" not in outputs["copy.md"],
            "pending copy never renders authoritative completion",
        )
        require(
            all(
                fragment not in "".join(outputs.values())
                for fragment in (
                    parent_result["transcript"],
                    child_result["transcript"],
                    "claimed_model",
                    "OPENCODE_",
                )
            ),
            "completed share outputs omit proof custody and untrusted runtime metadata",
        )
        forged = copy.deepcopy(runback_proof)
        forged["acceptance"]["acceptanceDigest"] = "f" * 64
        destination = os.path.join(work, "forged-output")
        expect_bundle_error(
            lambda: write_bundle(
                parent_result["transcript"],
                destination,
                runback_proof=forged,
                previous_lineage_state=empty_lineage_state(),
            ),
            "surface admission failed closed",
        )
        require(not os.path.exists(destination), "failed completion leaves no partial share tree")


def rewrite_and_rechain_copy(source, destination, mutate):
    """Copy a transcript to destination, mutate it there, then repair its hash chain."""
    with open(source, "r", encoding="utf-8") as fh:
        records = [json.loads(line) for line in fh]
    mutate(records)
    previous = GENESIS
    for record in records:
        body = {"kind": record["kind"], "seq": record["seq"], "body": record["body"]}
        record["prev"] = previous
        record["hash"] = chain(previous, body)
        previous = record["hash"]
    with open(destination, "w", encoding="utf-8", newline="\n") as fh:
        for record in records:
            fh.write(json.dumps(record, sort_keys=True, separators=(",", ":"),
                                ensure_ascii=True) + "\n")


def main():
    check_source_claims()
    check_bundle_contract()
    check_hostile_names_are_escaped()
    check_public_identity_guard()
    check_hostile_match_id_is_refused()
    check_tamper_refusal_has_no_partial_output()
    check_runtime_forfeit_refusal()
    check_generic_historical_match()
    check_ten_fronts_moment_bundle()
    check_completed_runback_surface()
    check_url_guard()
    print("AgentWars verified-moment bundle contracts: PASS")
    print("deterministic bundle / provenance parser / hostile escaping / tamper refusal / runback guard")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
