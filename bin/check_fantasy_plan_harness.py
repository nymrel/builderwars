#!/usr/bin/env python3
"""Hostile independent contract test for the fixed fantasy plan harness.

This checker never trusts the harness under test: it rebuilds strict seed-9300
artifacts from ``arena.games.fantasy_core``, attacks every documented boundary
(JSON strictness, file boundaries, wire protocol, observation validation), and
then runs two fixture artifacts through the real league scheduler and both
standalone verifiers. It writes only inside a temporary directory and touches
no network, model, credential, or environment value.
"""

import copy
import faulthandler
import hashlib
import importlib.util
import json
import os
import random
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.dont_write_bytecode = True

from arena.games.fantasy_core import (  # noqa: E402
    apply as core_apply,
    legal as core_legal,
    observation as core_observation,
    setup as core_setup,
    terminal as core_terminal,
)
from run_agentwars_league import run_league  # noqa: E402

faulthandler.dump_traceback_later(30, exit=True)

HARNESS_PATH = os.path.join(ROOT, "entrants", "fantasy_plan_harness.py")
VERIFY_ROOT = os.path.join(ROOT, "verify.py")
VERIFY_REPLAY = os.path.join(ROOT, "bin", "verify_replay.py")

ARTIFACT_SCHEMA = "agentwars.fantasy_plan_artifact.v1"
PLAN_SCHEMA = "agentwars.fantasy_draft_plan.v1"
SEED = 9300
RUN_ID = "0f0e0d0c-0b0a-4099-8076-5f4e3d2c1b0a"
RECEIPT_SHA = "ab" * 32
TERMINAL_TEXT_SHA = "cd" * 32
STRATEGY = "fixture: follow the immutable ranking, strongest open slot first"
MOVE_TIMEOUT_MS = 15000

PASSED = 0
SKIPPED = 0
BOARD = None
RANKINGS = None


def ok(name, condition, detail=""):
    global PASSED
    if not condition:
        raise AssertionError(f"{name}: {detail or 'contract violated'}")
    PASSED += 1
    print(f"  [ok] {name}")


def skip(name, reason):
    global SKIPPED
    SKIPPED += 1
    print(f"  [SKIP] {name}: {reason}")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def load_harness():
    spec = importlib.util.spec_from_file_location("fantasy_plan_harness_under_test", HARNESS_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_hex(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def raw_plan_text(ranking, strategy=STRATEGY):
    return json.dumps(
        {
            "schema": PLAN_SCHEMA,
            "game": "fantasy_redraft",
            "seed": SEED,
            "strategy": strategy,
            "ranking": list(ranking),
        },
        separators=(",", ":"),
        ensure_ascii=False,
    )


def build_source(raw_plan):
    return {
        "runId": RUN_ID,
        "receiptSha256": RECEIPT_SHA,
        "terminalTextSha256": TERMINAL_TEXT_SHA,
        "planLineSha256": sha256_hex(raw_plan),
        "planLineNumber": 1,
        "terminalTextExactPlan": True,
        "modelClaim": "ox-alpha-free",
        "reasoningEffort": "max",
        "maxTokens": 131072,
        "fallbacksAllowed": False,
        "route": "opencode-go",
    }


def build_artifact(ranking, exact_plan=True, strategy=STRATEGY):
    plan = raw_plan_text(ranking, strategy)
    source = build_source(plan)
    source["terminalTextExactPlan"] = exact_plan
    source["terminalTextSha256"] = source["planLineSha256"] if exact_plan else TERMINAL_TEXT_SHA
    return {"schema": ARTIFACT_SCHEMA, "source": source, "board": copy.deepcopy(BOARD), "rawPlan": plan}


def resign(artifact):
    """Re-bind the verified digest after a rawPlan mutation."""
    artifact["source"]["planLineSha256"] = sha256_hex(artifact["rawPlan"])
    if artifact["source"]["terminalTextExactPlan"]:
        artifact["source"]["terminalTextSha256"] = artifact["source"]["planLineSha256"]
    return artifact


def with_plan(ranking, plan):
    """A consistent artifact whose rawPlan is exactly ``plan``."""
    artifact = build_artifact(ranking)
    artifact["rawPlan"] = plan
    return resign(artifact)


def artifact_text(artifact):
    return json.dumps(artifact, separators=(",", ":"), ensure_ascii=False)


def write_plan(directory, name, content):
    path = os.path.join(directory, name)
    with open(path, "wb") as fh:
        fh.write(content.encode("utf-8") if isinstance(content, str) else content)
    return path


def expect_code(harness, tmp, name, content, code):
    path = write_plan(tmp, name.replace(" ", "_") + ".json", content)
    try:
        harness.load_artifact(path)
    except harness.PlanArtifactError as error:
        ok(name, error.code == code, f"expected code {code!r}, got {error.code!r}")
        return
    raise AssertionError(f"{name}: hostile artifact was accepted (wanted {code!r})")


def rankings():
    by_redraft = [row["id"] for row in sorted(BOARD, key=lambda r: (-r["redraft_points"], r["id"]))]
    by_dynasty = [row["id"] for row in sorted(BOARD, key=lambda r: (-r["dynasty_points"], -r["id"]))]
    weakest_first = [row["id"] for row in sorted(BOARD, key=lambda r: (r["redraft_points"], r["id"]))]
    return by_redraft, by_dynasty, weakest_first


def hello_message(match_id, seat=0):
    return {
        "type": "hello",
        "protocol": "arena/1",
        "match_id": match_id,
        "you_are": seat,
        "game": "fantasy_redraft",
        "game_version": "1",
        "rules": "Two general-manager harnesses run a six-round snake draft.",
        "move_timeout_ms": MOVE_TIMEOUT_MS,
    }


def run_protocol(plan_path, lines):
    process = subprocess.Popen(
        [sys.executable, HARNESS_PATH, "--plan", plan_path, "--name", "Fixture One"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    try:
        out, err = process.communicate(
            "".join((line if isinstance(line, str) else json.dumps(line)) + "\n"
                    for line in lines),
            timeout=6,
        )
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        raise AssertionError("harness subprocess hung past its protocol deadline")
    return process.returncode, out, err


def line_json(text):
    return [json.loads(row) for row in text.splitlines() if row.strip()]


def check_valid_load_and_projection(harness, tmp):
    print("valid load, projection, determinism, isolation")
    ranking_a, ranking_b, weakest = RANKINGS
    ok("the two fixture rankings are distinct permutations", ranking_a != ranking_b
       and sorted(ranking_a) == sorted(ranking_b))
    plan_path = write_plan(tmp, "valid.json", artifact_text(build_artifact(ranking_a)))
    project = harness.load_artifact(plan_path)
    ok("direct non-object move request stays controlled",
       harness.PlanSession(project, 0).handle_move_request(None)
       == (None, "bad_request_shape"))

    ok("projection exposes exactly the documented keys", set(project) == {
        "artifact_sha256", "plan_sha256", "run_id", "receipt_sha256",
        "strategy", "rows_by_id", "ranking"})
    with open(plan_path, "r", encoding="utf-8") as fh:
        text = fh.read()
    ok("artifact digest binds the file bytes", project["artifact_sha256"] == sha256_hex(text))
    ok("plan digest binds rawPlan", project["plan_sha256"] == sha256_hex(raw_plan_text(ranking_a)))
    ok("artifact and plan digests are distinct",
       project["artifact_sha256"] != project["plan_sha256"])
    ok("identity projection exact",
       project["run_id"] == RUN_ID and project["receipt_sha256"] == RECEIPT_SHA
       and project["strategy"] == STRATEGY)
    ok("ranking projection exact", project["ranking"] == ranking_a)
    ok("board projection exact",
       project["rows_by_id"] == {row["id"]: row for row in BOARD})

    state = core_setup(random.Random(SEED), "redraft")
    observation = core_observation(state, 0)
    request = {
        "type": "move_request",
        "turn": 0,
        "you_are": 0,
        "observation": observation,
        "move_timeout_ms": MOVE_TIMEOUT_MS,
    }
    first = harness.PlanSession(project, 0).handle_move_request(copy.deepcopy(request))
    second = harness.PlanSession(project, 0).handle_move_request(copy.deepcopy(request))
    ok("first-ranked choice deterministic and accepted",
       first[0] == {"player_id": ranking_a[0]} and first == second and first[1] is None,
       repr(first))
    ok("first-ranked choice legal", core_legal(state, first[0])[0] is True)

    weak_project = harness.load_artifact(
        write_plan(tmp, "weak.json", artifact_text(build_artifact(weakest))))
    weak_move, weak_reason = harness.PlanSession(weak_project, 0).handle_move_request(
        copy.deepcopy(request))
    ok("executes the shipped plan, never its own preference",
       weak_move == {"player_id": weakest[0]} and weak_reason is None
       and weakest[0] != ranking_a[0], repr((weak_move, weak_reason)))

    source = open(HARNESS_PATH, "r", encoding="utf-8").read()
    ok("no arena import anywhere in harness source",
       re.search(r"^\s*(?:import|from)\s+arena\b", source, re.M) is None)
    ok("no dynamic import surface in harness source",
       "__import__" not in source and "importlib" not in source)


def check_hostile_json(harness, tmp):
    print("hostile artifact and raw-plan JSON")
    ranking_a, _, _ = RANKINGS
    good = lambda: build_artifact(ranking_a)  # noqa: E731

    dup_top = '{"schema":"x","schema":"x","source":{},"board":[],"rawPlan":"y"}'
    expect_code(harness, tmp, "duplicate top-level key", dup_top, "plan_invalid_json")

    flat = artifact_text(good())
    poisoned = flat.replace(
        '"source":{"runId":"' + RUN_ID + '",',
        '"source":{"runId":"' + RUN_ID + '","runId":"' + RUN_ID + '",', 1)
    require(poisoned != flat, "fixture bug: source duplication splice missed")
    expect_code(harness, tmp, "duplicate key inside source", poisoned, "plan_invalid_json")

    plan_dup = with_plan(ranking_a, raw_plan_text(ranking_a).replace(
        '"seed":9300,', '"seed":9300,"game":"fantasy_redraft",', 1))
    expect_code(harness, tmp, "duplicate key inside rawPlan", artifact_text(plan_dup),
                "raw_plan_invalid_json")

    expect_code(harness, tmp, "NaN constant",
                artifact_text(good()).replace('"planLineNumber":1', '"planLineNumber":NaN'),
                "plan_invalid_json")
    expect_code(harness, tmp, "Infinity constant",
                artifact_text(good()).replace('"maxTokens":131072', '"maxTokens":-Infinity'),
                "plan_invalid_json")

    floated_board = good()
    floated_board["board"][0]["age"] = 25.5
    expect_code(harness, tmp, "float in board row", artifact_text(floated_board),
                "plan_float_forbidden")
    floated_plan = with_plan(ranking_a, raw_plan_text(ranking_a).replace('"seed":9300', '"seed":9300.0'))
    expect_code(harness, tmp, "float inside rawPlan", artifact_text(floated_plan),
                "plan_float_forbidden")

    bool_age = good()
    bool_age["board"][0]["age"] = True
    expect_code(harness, tmp, "bool-as-int board age", artifact_text(bool_age), "board_age")
    bool_line = good()
    bool_line["source"]["planLineNumber"] = True
    expect_code(harness, tmp, "bool-as-int planLineNumber", artifact_text(bool_line),
                "source_plan_line_number")
    zero_fallback = good()
    zero_fallback["source"]["fallbacksAllowed"] = 0
    expect_code(harness, tmp, "int masquerading as fallbacksAllowed", artifact_text(zero_fallback),
                "source_fallbacks_allowed")

    trusted = good()
    trusted["trusted"] = True
    expect_code(harness, tmp, "unknown top-level trust key", artifact_text(trusted),
                "plan_unexpected_keys")
    missing = good()
    del missing["rawPlan"]
    expect_code(harness, tmp, "missing top-level key", artifact_text(missing),
                "plan_unexpected_keys")
    attested = good()
    attested["source"]["attestedModel"] = "ox-alpha-free"
    expect_code(harness, tmp, "unknown source key", artifact_text(attested), "source_bad_keys")
    dropped = good()
    del dropped["source"]["route"]
    expect_code(harness, tmp, "missing source key", artifact_text(dropped), "source_bad_keys")

    bad_run = good()
    bad_run["source"]["runId"] = 17
    expect_code(harness, tmp, "non-string runId", artifact_text(bad_run), "source_run_id")
    short_receipt = good()
    short_receipt["source"]["receiptSha256"] = "ab" * 31
    expect_code(harness, tmp, "short receipt digest", artifact_text(short_receipt),
                "source_receipt_sha")
    upper_claim = good()
    upper_claim["source"]["terminalTextSha256"] = TERMINAL_TEXT_SHA.upper()
    expect_code(harness, tmp, "uppercase terminal-text claim", artifact_text(upper_claim),
                "source_terminal_text_sha")
    wrong_model = good()
    wrong_model["source"]["modelClaim"] = "some-other-model"
    expect_code(harness, tmp, "wrong model claim", artifact_text(wrong_model), "source_model_claim")

    control_name = good()
    control_name["board"][0]["name"] = "Pocket\x01Ace"
    expect_code(harness, tmp, "control character in board name", artifact_text(control_name),
                "board_name")
    long_name = good()
    long_name["board"][0]["name"] = "A" * 81
    expect_code(harness, tmp, "oversized board name", artifact_text(long_name), "board_name")
    big_points = good()
    big_points["board"][3]["redraft_points"] = 100001
    expect_code(harness, tmp, "out-of-bound points", artifact_text(big_points), "board_points")
    old_age = good()
    old_age["board"][3]["age"] = 201
    expect_code(harness, tmp, "out-of-bound age", artifact_text(old_age), "board_age")
    zero_id = good()
    zero_id["board"][3]["id"] = 0
    expect_code(harness, tmp, "out-of-bound player id", artifact_text(zero_id), "board_player_id")
    kicker = good()
    kicker["board"][3]["position"] = "K"
    expect_code(harness, tmp, "unknown position", artifact_text(kicker), "board_position")
    extra_row_key = good()
    extra_row_key["board"][3]["bye_week"] = 7
    expect_code(harness, tmp, "unexpected board row key", artifact_text(extra_row_key),
                "board_row_keys")

    long_strategy = with_plan(ranking_a, raw_plan_text(ranking_a, "S" * 501))
    expect_code(harness, tmp, "oversized strategy", artifact_text(long_strategy),
                "raw_plan_strategy")
    control_strategy = with_plan(ranking_a, raw_plan_text(ranking_a, "S\x02T"))
    expect_code(harness, tmp, "control character in strategy", artifact_text(control_strategy),
                "raw_plan_strategy")

    wrong_schema = with_plan(ranking_a, raw_plan_text(ranking_a).replace(
        PLAN_SCHEMA, PLAN_SCHEMA + "2"))
    expect_code(harness, tmp, "wrong plan schema", artifact_text(wrong_schema), "raw_plan_schema")
    wrong_game = with_plan(ranking_a, raw_plan_text(ranking_a).replace(
        '"game":"fantasy_redraft"', '"game":"fantasy_dynasty"'))
    expect_code(harness, tmp, "wrong game in plan", artifact_text(wrong_game), "raw_plan_game")
    wrong_seed = with_plan(ranking_a, raw_plan_text(ranking_a).replace('"seed":9300', '"seed":9200'))
    expect_code(harness, tmp, "wrong seed in plan", artifact_text(wrong_seed), "raw_plan_seed")

    surrogate_plan = build_artifact(ranking_a)
    surrogate_plan["rawPlan"] = "\ud800"
    surrogate_text = json.dumps(surrogate_plan, separators=(",", ":"), ensure_ascii=True)
    expect_code(harness, tmp, "lone surrogate rawPlan stays controlled", surrogate_text,
                "raw_plan_not_utf8")

    exact_but_hashes_differ = build_artifact(ranking_a, exact_plan=True)
    exact_but_hashes_differ["source"]["terminalTextSha256"] = TERMINAL_TEXT_SHA
    expect_code(harness, tmp, "exact-terminal claim requires matching hashes",
                artifact_text(exact_but_hashes_differ),
                "source_terminal_claim_contradiction")

    appended_but_hashes_match = build_artifact(ranking_a, exact_plan=False)
    appended_but_hashes_match["source"]["terminalTextSha256"] = (
        appended_but_hashes_match["source"]["planLineSha256"]
    )
    expect_code(harness, tmp, "appended-terminal claim requires distinct hashes",
                artifact_text(appended_but_hashes_match),
                "source_terminal_claim_contradiction")

    mismatched = good()
    mismatched["source"]["planLineSha256"] = "ee" * 32
    expect_code(harness, tmp, "plan digest mismatch", artifact_text(mismatched),
                "raw_plan_digest_mismatch")

    spaced_text = json.dumps(json.loads(raw_plan_text(ranking_a)), indent=1)
    spaced = with_plan(ranking_a, spaced_text)
    expect_code(harness, tmp, "noncanonical whitespace in plan", artifact_text(spaced),
                "raw_plan_not_canonical")

    duplicated_rank = list(ranking_a)
    duplicated_rank[1] = duplicated_rank[0]
    dup_entry = with_plan(ranking_a, raw_plan_text(duplicated_rank))
    expect_code(harness, tmp, "duplicate ranking id", artifact_text(dup_entry),
                "raw_plan_ranking_duplicate")
    missing_rank = with_plan(ranking_a, raw_plan_text(ranking_a[:-1]))
    expect_code(harness, tmp, "missing ranking id", artifact_text(missing_rank),
                "raw_plan_ranking_shape")
    unknown_rank = with_plan(ranking_a, raw_plan_text([999] + ranking_a[:-1]))
    expect_code(harness, tmp, "unknown ranking id", artifact_text(unknown_rank),
                "raw_plan_ranking_entry")

    duplicate_board = good()
    duplicate_board["board"][1]["id"] = duplicate_board["board"][0]["id"]
    expect_code(harness, tmp, "duplicate board id", artifact_text(duplicate_board),
                "board_duplicate_id")
    different_seed_board = good()
    different_seed_board["board"][0]["redraft_points"] += 1
    expect_code(harness, tmp, "board must be the exact seed-9300 snapshot",
                artifact_text(different_seed_board), "board_seed_mismatch")
    short_board = good()
    short_board["board"] = short_board["board"][:-1]
    expect_code(harness, tmp, "wrong board size", artifact_text(short_board), "board_shape")
    thin_te = good()
    te_seen = 0
    for row in thin_te["board"]:
        if row["position"] == "TE":
            te_seen += 1
            if te_seen <= 3:
                row["position"] = "WR"
    require(sum(1 for row in thin_te["board"] if row["position"] == "TE") == 1,
            "fixture bug: TE thinning failed")
    expect_code(harness, tmp, "infeasible position counts", artifact_text(thin_te),
                "board_position_counts_infeasible")

    not_string = good()
    not_string["rawPlan"] = SEED
    expect_code(harness, tmp, "rawPlan not a string", artifact_text(not_string),
                "raw_plan_not_string")

    ranking_b = RANKINGS[1]
    exact_false = harness.load_artifact(write_plan(
        tmp, "exact_false.json", artifact_text(build_artifact(ranking_b, exact_plan=False))))
    exact_true = harness.load_artifact(write_plan(
        tmp, "exact_true.json", artifact_text(build_artifact(ranking_b, exact_plan=True))))
    ok("terminalTextExactPlan stays an accepted claim in both directions",
       exact_false["ranking"] == exact_true["ranking"] == ranking_b)


def check_file_boundary(harness, tmp):
    print("file boundary")
    ranking_a, _, _ = RANKINGS
    valid_bytes = artifact_text(build_artifact(ranking_a)).encode("utf-8")

    try:
        harness.load_artifact(os.path.join(tmp, "does_not_exist.json"))
        raise AssertionError("missing file was accepted")
    except harness.PlanArtifactError as error:
        ok("missing file rejected", error.code == "plan_not_found", error.code)

    directory = tempfile.mkdtemp(prefix="boundary-dir-", dir=tmp)
    try:
        harness.load_artifact(directory)
        raise AssertionError("directory was accepted")
    except harness.PlanArtifactError as error:
        ok("directory rejected", error.code == "plan_not_regular", error.code)

    empty = os.path.join(tmp, "empty.json")
    open(empty, "wb").close()
    try:
        harness.load_artifact(empty)
        raise AssertionError("empty file was accepted")
    except harness.PlanArtifactError as error:
        ok("empty file rejected", error.code == "plan_empty", error.code)

    oversized = os.path.join(tmp, "oversized.json")
    with open(oversized, "wb") as fh:
        fh.write(b"x" * (64 * 1024 + 1))
    try:
        harness.load_artifact(oversized)
        raise AssertionError("oversized file was accepted")
    except harness.PlanArtifactError as error:
        ok("oversized file rejected", error.code == "plan_oversized", error.code)

    invalid_utf8 = os.path.join(tmp, "invalid_utf8.json")
    with open(invalid_utf8, "wb") as fh:
        fh.write(b'{"schema":"\xff\xfe"}')
    try:
        harness.load_artifact(invalid_utf8)
        raise AssertionError("invalid UTF-8 was accepted")
    except harness.PlanArtifactError as error:
        ok("invalid UTF-8 rejected", error.code == "plan_invalid_utf8", error.code)

    hard_target = write_plan(tmp, "hard_original.json", valid_bytes)
    try:
        os.link(hard_target, os.path.join(tmp, "hard_alias.json"))
    except OSError as error:
        skip("multi-linked file rejected", f"host cannot create hard links ({error})")
    else:
        try:
            harness.load_artifact(hard_target)
            raise AssertionError("multi-linked file was accepted")
        except harness.PlanArtifactError as error:
            ok("multi-linked file rejected", error.code == "plan_multi_linked", error.code)

    final_link = os.path.join(tmp, "final_symlink.json")
    try:
        os.symlink(hard_target, final_link)
    except (OSError, NotImplementedError) as error:
        skip("final symlink rejected", f"host cannot create symlinks ({error})")
    else:
        try:
            harness.load_artifact(final_link)
            raise AssertionError("final symlink was accepted")
        except harness.PlanArtifactError as error:
            ok("final symlink rejected", error.code == "plan_is_symlink", error.code)

    real_dir = os.path.join(tmp, "real_parent")
    os.makedirs(real_dir, exist_ok=True)
    write_plan(real_dir, "inside.json", valid_bytes)
    link_dir = os.path.join(tmp, "linked_parent")
    try:
        os.symlink(real_dir, link_dir, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        skip("symlinked parent rejected", f"host cannot create directory symlinks ({error})")
    else:
        try:
            harness.load_artifact(os.path.join(link_dir, "inside.json"))
            raise AssertionError("symlinked parent was accepted")
        except harness.PlanArtifactError as error:
            ok("symlinked parent rejected", error.code == "plan_parent_redirect", error.code)


def check_protocol_subprocesses(harness, tmp):
    print("wire protocol in subprocesses")
    ranking_a, _, _ = RANKINGS
    plan_a = write_plan(tmp, "proto_a.json", artifact_text(build_artifact(ranking_a)))

    state = core_setup(random.Random(SEED), "redraft")
    turn0_obs = core_observation(state, 0)
    rc, out, err = run_protocol(plan_a, [
        hello_message("happy-path"),
        {"type": "move_request", "turn": 0, "you_are": 0, "observation": turn0_obs,
         "move_timeout_ms": MOVE_TIMEOUT_MS},
        {"type": "goodbye", "result": {"winner": 0, "reason": "done"}},
    ])
    ok("happy path exits 0", rc == 0, f"rc={rc} stderr={err.strip()[:120]}")
    messages = line_json(out)
    ok("exactly ready then move emitted", len(messages) == 2, str(len(messages)))
    project = harness.load_artifact(plan_a)
    expected_ready = {
        "type": "ready",
        "entrant": "Fixture One",
        "version": "1",
        "backend": "fixed-model-plan:v1",
        "artifact_sha256": project["artifact_sha256"],
        "plan_sha256": project["plan_sha256"],
        "ox_run_id": project["run_id"],
        "ox_receipt_sha256": project["receipt_sha256"],
    }
    ok("ready message is the exact source projection", messages[0] == expected_ready,
       json.dumps(messages[0])[:200])
    ok("first move follows ranking with model_plan note",
       messages[1] == {"type": "move", "move": {"player_id": ranking_a[0]},
                       "note": ("source=model_plan;plan_sha256=" + project["plan_sha256"]
                                + ";ox_run_id=" + RUN_ID + ";ox_receipt_sha256=" + RECEIPT_SHA)},
       json.dumps(messages[1])[:200])

    marker = "dupkey-marker-zz9"
    dup_hello = json.dumps(hello_message(marker))
    dup_hello = dup_hello[:-1] + ',"type":"hello"}'
    rc, out, err = run_protocol(plan_a, [dup_hello])
    ok("duplicate-key hello fails controlled",
       rc == 2 and "error: malformed_protocol_json" in err and "Traceback" not in err,
       f"rc={rc} err={err.strip()[:160]}")
    ok("duplicate-key input never echoed", marker not in out and marker not in err,
       "marker leaked")

    rc, out, err = run_protocol(plan_a, ['{"type":"hello","protocol":BROKEN_MARKER'])
    ok("malformed JSON fails controlled",
       rc == 2 and "error: malformed_protocol_json" in err and "Traceback" not in err
       and out.strip() == "",
       f"rc={rc} err={err.strip()[:160]}")
    ok("malformed input never echoed", "BROKEN_MARKER" not in out + err, "input echoed")

    rc, out, err = run_protocol(plan_a, [
        {"type": "move_request", "turn": 0, "you_are": 0, "observation": turn0_obs,
         "move_timeout_ms": MOVE_TIMEOUT_MS},
    ])
    ok("move before hello exits 2", rc == 2 and "error: move_before_hello" in err,
       f"rc={rc} err={err.strip()[:120]}")

    incomplete = hello_message("shape-probe")
    del incomplete["match_id"]
    rc, out, err = run_protocol(plan_a, [incomplete])
    ok("bad hello shape exits 2", rc == 2 and "error: bad_handshake_shape" in err,
       f"rc={rc} err={err.strip()[:120]}")

    wrong_protocol = hello_message("protocol-probe")
    wrong_protocol["protocol"] = "arena/2"
    rc, out, err = run_protocol(plan_a, [wrong_protocol])
    ok("bad protocol exits 2", rc == 2 and "error: bad_protocol" in err,
       f"rc={rc} err={err.strip()[:120]}")

    rc, out, err = run_protocol(plan_a, [hello_message("again"), hello_message("again")])
    ok("duplicate hello exits 2", rc == 2 and "error: duplicate_hello" in err,
       f"rc={rc} err={err.strip()[:120]}")

    rc, out, err = run_protocol(plan_a, [
        hello_message("teleport"), {"type": "teleport", "payload": {}}])
    ok("unknown message type exits 2", rc == 2 and "error: unknown_message_type" in err,
       f"rc={rc} err={err.strip()[:120]}")

    rc, out, err = run_protocol(plan_a, [{"type": "goodbye", "result": {}}])
    ok("goodbye before ready exits 2", rc == 2 and "error: bad_goodbye_sequence" in err,
       f"rc={rc} err={err.strip()[:120]}")

    rc, out, err = run_protocol(plan_a, [hello_message("seat-swap", seat=1)])
    ready = line_json(out)[0]
    ok("ready carries no attestation claims",
       rc == 0 and all(key not in ready for key in (
           "modelAttested", "runtimeAttested", "personAttested", "executionClaimsAttested")),
       json.dumps(sorted(ready)))


def baseline_turn4_request(harness, project):
    """Play four authentic turns; return the still-pending seat-0 turn-4 request."""
    sessions = {0: harness.PlanSession(project, 0), 1: harness.PlanSession(project, 1)}
    state = core_setup(random.Random(SEED), "redraft")
    for turn in range(4):
        seat = state["to_move"]
        observation = core_observation(state, seat)
        request = {
            "type": "move_request",
            "turn": turn,
            "you_are": seat,
            "observation": observation,
            "move_timeout_ms": MOVE_TIMEOUT_MS,
        }
        move, reason = sessions[seat].handle_move_request(copy.deepcopy(request))
        require(reason is None, f"baseline draft broke at turn {turn}: {reason}")
        legal_here, why = core_legal(state, move)
        require(legal_here, f"baseline pick illegal at turn {turn}: {why}")
        state = core_apply(state, move)
    require(state["turn"] == 4 and state["to_move"] == 0,
            "fixture bug: baseline did not land on the pending turn-4 seat-0 pick")
    return {
        "type": "move_request",
        "turn": 4,
        "you_are": 0,
        "observation": core_observation(state, 0),
        "move_timeout_ms": MOVE_TIMEOUT_MS,
    }


def check_observation_validation(harness, tmp):
    print("tampered observations stay controlled")
    ranking_a, ranking_b, _ = RANKINGS
    project = harness.load_artifact(
        write_plan(tmp, "obs_base.json", artifact_text(build_artifact(ranking_a))))
    opponent_project = harness.load_artifact(
        write_plan(tmp, "obs_opp.json", artifact_text(build_artifact(ranking_b))))

    request = baseline_turn4_request(harness, project)

    def tampered(mutate):
        broken = copy.deepcopy(request)
        mutate(broken)
        return broken

    def toggle_qb_need(message):
        needs = message["observation"]["needs"]
        needs["QB"] = 1 - needs["QB"]

    cases = [
        ("wrong game field", lambda m: m["observation"].__setitem__("game", "fantasy_dynasty")),
        ("wrong format field", lambda m: m["observation"].__setitem__("format", "dynasty")),
        ("empty rules text", lambda m: m["observation"].__setitem__("rules", "")),
        ("control character in rules", lambda m: m["observation"].__setitem__("rules", "rules\x07")),
        ("message seat mismatch", lambda m: m.__setitem__("you_are", 1)),
        ("observation seat mismatch", lambda m: m["observation"].__setitem__("you_are", 1)),
        ("to_move seat mismatch", lambda m: m["observation"].__setitem__("to_move", 1)),
        ("turn out of range", lambda m: m["observation"].__setitem__("turn", 99)),
        ("turn type confusion", lambda m: m["observation"].__setitem__("turn", "4")),
        ("request turn split from observation", lambda m: m.__setitem__("turn", 3)),
        ("round drifts from turn", lambda m: m["observation"].__setitem__("round", 9)),
        ("needs missing key", lambda m: m["observation"]["needs"].pop("TE")),
        ("needs above limit", lambda m: m["observation"]["needs"].__setitem__("QB", 2)),
        ("negative need", lambda m: m["observation"]["needs"].__setitem__("WR", -1)),
        ("needs contradict roster", toggle_qb_need),
        ("partition loses a player", lambda m: m["observation"]["available_players"].pop(0)),
        ("duplicate available row", lambda m: m["observation"]["available_players"].append(
            copy.deepcopy(m["observation"]["available_players"][0]))),
        ("tampered row data", lambda m: m["observation"]["available_players"][0].__setitem__(
            "redraft_points", 1)),
        ("unknown available id", lambda m: m["observation"]["available_players"][0].__setitem__(
            "id", 4242)),
        ("row schema violation", lambda m: m["observation"]["available_players"][0].pop("age")),
        ("unknown roster player", lambda m: m["observation"]["your_roster"].append(9999)),
        ("duplicate your_roster id", lambda m: m["observation"]["your_roster"].append(
            m["observation"]["your_roster"][0])),
        ("your roster pick count shifted", lambda m: m["observation"]["your_roster"].pop()),
        ("opponent roster pick count shifted", lambda m: m["observation"]["opponent_roster"].pop()),
        ("zero timeout", lambda m: m.__setitem__("move_timeout_ms", 0)),
        ("timeout above ceiling", lambda m: m.__setitem__("move_timeout_ms", 3600001)),
        ("timeout type confusion", lambda m: m.__setitem__("move_timeout_ms", "soon")),
        ("extra request key", lambda m: m.__setitem__("hint", "take the quarterback")),
    ]

    reasons = {}
    for name, mutate in cases:
        move, reason = harness.PlanSession(project, 0).handle_move_request(tampered(mutate))
        ok(f"controlled forfeit: {name}", move is None and isinstance(reason, str),
           f"move={move!r} reason={reason!r}")
        reasons[name] = reason
    bounded = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
    leaks = {name: reason for name, reason in reasons.items() if not bounded.fullmatch(reason)}
    ok("every rejection reason is a bounded public code", not leaks, json.dumps(leaks))

    replay_session = harness.PlanSession(project, 0)
    first_reply = replay_session.handle_move_request(copy.deepcopy(request))
    ok("fresh session accepts turn 4 once", first_reply[1] is None, repr(first_reply[1]))
    repeat_reply = replay_session.handle_move_request(copy.deepcopy(request))
    ok("replayed turn rejected as out of order",
       repeat_reply == (None, "bad_turn_order"), repr(repeat_reply))

    full_sessions = {0: harness.PlanSession(opponent_project, 0),
                     1: harness.PlanSession(project, 1)}
    live = core_setup(random.Random(SEED), "redraft")
    moves_played = 0
    while core_terminal(live) is None:
        seat = live["to_move"]
        ask = {
            "type": "move_request",
            "turn": live["turn"],
            "you_are": seat,
            "observation": core_observation(live, seat),
            "move_timeout_ms": MOVE_TIMEOUT_MS,
        }
        move, reason = full_sessions[seat].handle_move_request(copy.deepcopy(ask))
        require(reason is None, f"full draft broke at turn {live['turn']}: {reason}")
        legal_here, why = core_legal(live, move)
        require(legal_here, f"full draft produced an illegal move at turn {live['turn']}: {why}")
        live = core_apply(live, move)
        moves_played += 1
    end = core_terminal(live)
    ok("two distinct fixture plans complete a legal twelve-pick draft",
       moves_played == 12 and end is not None
       and all(len(roster) == 6 for roster in live["rosters"]),
       f"moves={moves_played} end={end!r}")


def plan_manifest(name, plan_path):
    return {
        "name": name,
        "cmd": [sys.executable, HARNESS_PATH, "--plan", plan_path, "--name", name],
        "env": [],
        "claimed_model": "ox-alpha-free",
        "execution_claim": "hybrid",
    }


def find_transcripts(root):
    found = []
    for current, _, files in os.walk(root):
        for filename in files:
            if filename.endswith(".jsonl") and not filename.endswith(".diagnostics.jsonl"):
                found.append(os.path.join(current, filename))
    return sorted(found)


def run_verifier(verifier, transcript):
    try:
        return subprocess.run(
            [sys.executable, verifier, transcript],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", timeout=8,
        )
    except subprocess.TimeoutExpired as expired:
        raise AssertionError(f"{verifier} timed out on {transcript}: {expired.output!r}") from None


def check_league_and_verdicts(harness, tmp):
    print("league execution of two fixture artifacts")
    ranking_a, ranking_b, _ = RANKINGS
    league_root = os.path.join(tmp, "league")
    plans = {}
    for label, ranking in (("alpha", ranking_a), ("beta", ranking_b)):
        plans[label] = write_plan(
            tmp, f"league_{label}.json",
            artifact_text(build_artifact(ranking, exact_plan=label == "alpha")))
    config = {
        "league": "Fantasy plan contract league",
        "description": "two immutable model-plan artifacts, one seed",
        "entrants": [plan_manifest("Plan Alpha", plans["alpha"]),
                     plan_manifest("Plan Beta", plans["beta"])],
    }
    summary = run_league(config, formats=["fantasy_redraft"], seeds=1, start_seed=SEED,
                         out_dir=league_root)

    matches = [match for circuit in summary["formats"] for match in circuit["matches"]]
    ok("built-in scheduler ran exactly the two seat orders",
       len(matches) == 2
       and len({match["matchId"] for match in matches}) == 2
       and {(match["seat0"], match["seat1"]) for match in matches}
       == {("Plan Alpha", "Plan Beta"), ("Plan Beta", "Plan Alpha")},
       json.dumps([[match["seat0"], match["seat1"]] for match in matches]))
    ok("one seed starting 9300", [match["seed"] for match in matches] == [SEED, SEED],
       str([match["seed"] for match in matches]))
    ok("both matches decisive without forfeits",
       all(match["verified"] and match["winner"] is not None
           and match["reason"].startswith("redraft_roster_score:") for match in matches),
       json.dumps([match["reason"] for match in matches]))

    ok("summary status is exactly model_influenced_unattested",
       summary["status"] == "model_influenced_unattested", repr(summary["status"]))
    ok("summary keeps every attestation false",
       summary["modelAttested"] is False and summary["executionClaimsAttested"] is False)
    ok("summary entrants keep hybrid claims",
       all(row["executionClaim"] == "hybrid" and row["claimedModel"] == "ox-alpha-free"
           for row in summary["entrants"]))
    ok("per-match attestation flags false",
       all(match["modelAttested"] is False and match["executionClaimsAttested"] is False
           for match in matches))
    ok("all counted move sources are model with zero fallback/scripted/other",
       all(source == {"model": 6, "fallback": 0, "scripted": 0, "other": 0}
           for match in matches for source in match["moveSourceClaims"].values()),
       json.dumps([match["moveSourceClaims"] for match in matches]))
    ok("standings accumulate twelve model-claimed moves each",
       all(row["modelMoveClaims"] == 12 and row["fallbackMoves"] == 0
           and row["scriptedMoves"] == 0 and row["otherMoves"] == 0
           for circuit in summary["formats"] for row in circuit["standings"]),
       json.dumps(summary["formats"][0]["standings"]))

    print("transcript headers, notes, and standalone verdicts")
    transcripts = find_transcripts(league_root)
    ok("exactly two transcripts on disk", len(transcripts) == 2, str(len(transcripts)))
    expected_transcript_identities = {
        match["matchId"]: (match["seat0"], match["seat1"]) for match in matches
    }
    observed_transcript_identities = {}
    transcript_digests = set()
    for transcript in transcripts:
        tag = os.path.basename(transcript)[:12]
        with open(transcript, "rb") as transcript_file:
            transcript_bytes = transcript_file.read()
        transcript_digests.add(hashlib.sha256(transcript_bytes).hexdigest())
        records = [
            json.loads(line)
            for line in transcript_bytes.decode("utf-8").splitlines()
            if line.strip()
        ]
        header = next(record["body"] for record in records if record["kind"] == "header")
        header_match_id = header["match_id"]
        header_seat_order = tuple(
            row["name"] for row in sorted(header["entrants"], key=lambda row: row["seat"])
        )
        ok(f"transcript filename binds header match id [{tag}]",
           os.path.basename(transcript) == f"{header_match_id}.jsonl")
        ok(f"transcript header identity binds summary [{tag}]",
           expected_transcript_identities.get(header_match_id) == header_seat_order,
           repr((header_match_id, header_seat_order)))
        require(header_match_id not in observed_transcript_identities,
                f"duplicate transcript match id: {header_match_id}")
        observed_transcript_identities[header_match_id] = header_seat_order
        ok(f"header attestation false [{tag}]",
           header["attestation"]["model_attested"] is False
           and header["attestation"]["execution_claims_attested"] is False)
        ok(f"header keeps hybrid claims [{tag}]",
           [row["execution_claim"] for row in header["entrants"]] == ["hybrid", "hybrid"])
        move_records = [record["body"] for record in records if record["kind"] == "move"]
        ok(f"every note starts source=model_plan [{tag}]",
           len(move_records) == 12
           and all(body["legal"] is True
                   and body["entrant_message"]["note"].startswith("source=model_plan")
                   for body in move_records))
        ok(f"transcript holds no forfeit [{tag}]",
           not any(record["kind"] == "forfeit" for record in records))
        result_body = next(record["body"] for record in records if record["kind"] == "result")
        ok(f"recorded result non-forfeit [{tag}]",
           result_body["winner"] in (0, 1)
           and result_body["reason"].startswith("redraft_roster_score:"),
           result_body["reason"])

        for verifier in (VERIFY_ROOT, VERIFY_REPLAY):
            completed = run_verifier(verifier, transcript)
            label = os.path.basename(verifier)
            ok(f"{label} PASS exit 0 [{tag}]",
               completed.returncode == 0 and "VERDICT: PASS" in completed.stdout,
               completed.stdout[-300:])
    ok("transcripts cover the two distinct summary matches exactly once",
       observed_transcript_identities == expected_transcript_identities
       and len(transcript_digests) == len(transcripts),
       repr((observed_transcript_identities, expected_transcript_identities,
             len(transcript_digests))))


def main():
    global BOARD, RANKINGS
    try:
        BOARD = core_setup(random.Random(SEED), "redraft")["players"]
        RANKINGS = rankings()
        harness = load_harness()
        with tempfile.TemporaryDirectory(prefix="check-fantasy-plan-harness-") as tmp:
            check_valid_load_and_projection(harness, tmp)
            check_hostile_json(harness, tmp)
            check_file_boundary(harness, tmp)
            check_protocol_subprocesses(harness, tmp)
            check_observation_validation(harness, tmp)
            check_league_and_verdicts(harness, tmp)
        print(f"fantasy plan harness contracts: PASS ({PASSED} checks, {SKIPPED} skipped)")
        return 0
    finally:
        faulthandler.cancel_dump_traceback_later()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as failure:
        print(f"fantasy plan harness contracts: FAIL — {failure}", file=sys.stderr)
        raise SystemExit(1)
