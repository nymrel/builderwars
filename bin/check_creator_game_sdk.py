#!/usr/bin/env python3
"""Adversarial, provider-free checks for the declarative creator-game SDK."""

from __future__ import annotations

import ast
import copy
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from creator_sdk.runtime import (  # noqa: E402
    CANDIDATE_STATUS,
    CreatorGameError,
    MAX_MANIFEST_BYTES,
    REGISTRY_STATUS,
    SealedAllocationGame,
    load_manifest,
    load_registry,
    load_replay,
    manifest_sha256,
    replay_sha256,
    validate_manifest,
    validate_registry,
    verify_replay,
)
from arena.games import REGISTRY as ENGINE_GAME_REGISTRY  # noqa: E402


MANIFEST_PATH = ROOT / "creator_games" / "signal-siege" / "game.v1.json"
REPLAY_PATH = ROOT / "creator_games" / "signal-siege" / "replay.v1.json"
REGISTRY_PATH = ROOT / "creator_games" / "registry.v1.json"
EXPECTED_MANIFEST_SHA256 = "691e7e77ff333f3ac64ae4e801c5b682bbcd755fb46a9aa138137be1e1d17504"
EXPECTED_REPLAY_SHA256 = "939b0380416d97d09104b394fa29e161897fb3498f110f28de4dca02e124e9a1"
CANARY = "CREATOR_SECRET_CANARY_71A9"
PASSED = 0


def check(condition: object, name: str) -> None:
    global PASSED
    if not condition:
        raise AssertionError(name)
    PASSED += 1
    print(f"[PASS] {name}")


def expect_error(action, code: str, name: str) -> None:
    try:
        action()
    except CreatorGameError as error:
        check(error.code == code and CANARY not in str(error), name)
        return
    raise AssertionError(f"{name}: accepted")


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True),
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    manifest = load_manifest(MANIFEST_PATH)
    replay = load_replay(REPLAY_PATH)
    game = SealedAllocationGame(manifest)
    report = verify_replay(manifest, replay)
    registry_report = load_registry(REGISTRY_PATH, ROOT)

    check(game.manifest_sha256 == EXPECTED_MANIFEST_SHA256, "manifest digest is exact")
    check(replay_sha256(replay) == EXPECTED_REPLAY_SHA256, "replay digest is exact")
    check(
        report["effectiveVerdict"] == "PASS"
        and report["candidateStatus"] == CANDIDATE_STATUS
        and report["moveCount"] == game.move_bound() == 12,
        "example replay reaches one exact terminal state",
    )
    check(
        all(
            report[field] is False
            for field in (
                "modelAttested",
                "providerAttested",
                "runtimeAttested",
                "harnessExecutionAttested",
                "rankingAuthorized",
                "publicationAuthorized",
                "codeExecutionAuthorized",
            )
        ),
        "replay grants no model provider runtime harness ranking publication or code authority",
    )
    check(
        registry_report["status"] == "pass"
        and registry_report["candidateStatus"] == REGISTRY_STATUS
        and registry_report["entryCount"] == 1
        and not registry_report["executionAuthorized"]
        and not registry_report["publicationAuthorized"]
        and not registry_report["rankingAuthorized"],
        "source registry remains held and authority-free",
    )
    check("creator.signal-siege" not in ENGINE_GAME_REGISTRY, "candidate is absent from executable engine registry")

    source = (ROOT / "creator_sdk" / "runtime.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            imported.add(node.module.split(".")[0])
    direct_calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    attribute_calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    attribute_access = {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }
    open_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "open"
    ]
    check(
        imported <= {"__future__", "arena", "hashlib", "json", "os", "re", "unicodedata", "pathlib"}
        and direct_calls.isdisjoint({"eval", "exec", "compile", "__import__"})
        and attribute_calls.isdisjoint(
            {
                "system",
                "popen",
                "Popen",
                "run",
                "urlopen",
                "request",
                "connect",
                "unlink",
                "remove",
                "rename",
                "replace",
                "mkdir",
                "makedirs",
                "rmdir",
            }
        )
        and attribute_access.isdisjoint({"environ", "getenv", "putenv"})
        and all(
            len(node.args) >= 2
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value == "rb"
            for node in open_calls
        ),
        "runtime has no creator code import eval subprocess network or dynamic expression surface",
    )

    state_a = game.setup(20260826)
    state_b = game.setup(20260826)
    check(state_a == state_b, "setup is deterministic for an exact seed")
    reordered_manifest = {key: manifest[key] for key in reversed(list(manifest))}
    check(
        manifest_sha256(reordered_manifest) == game.manifest_sha256,
        "manifest identity ignores JSON object insertion order",
    )
    action_zero = replay["actions"][0]
    initial_copy = copy.deepcopy(state_a)
    sealed = game.apply(state_a, {"allocation": action_zero["allocation"]})
    check(state_a == initial_copy and sealed is not state_a, "apply never mutates creator-game input state")
    seat_one = game.observation(sealed, 1)
    spectator = game.render(sealed)
    check(
        seat_one["yourPendingAllocation"] is None
        and seat_one["opponentPendingAllocationVisible"] is False
        and action_zero["allocation"] not in seat_one.values()
        and "[8, 6, 4, 3, 3]" not in json.dumps(spectator),
        "sealed seat-zero allocation is hidden from seat one and spectators",
    )
    check(
        game.observation(sealed, 0)["yourPendingAllocation"] == action_zero["allocation"],
        "a seat can recover only its own pending allocation",
    )

    invalid_actions = [
        None,
        {},
        {"allocation": [24, 0, 0, 0]},
        {"allocation": [24, 0, 0, 0, 1]},
        {"allocation": [True, 5, 5, 5, 8]},
        {"allocation": [-1, 5, 5, 5, 10]},
        {"allocation": [24, 0, 0, 0, 0], "expression": CANARY},
    ]
    check(
        all(not game.legal(state_a, candidate)[0] for candidate in invalid_actions),
        "actions reject null missing wrong-length wrong-sum bool negative and extra fields",
    )

    bad_score = copy.deepcopy(sealed)
    bad_score["scores"][0] = 1
    check(not game.legal(bad_score, {"allocation": replay["actions"][1]["allocation"]})[0], "tampered score invalidates state")
    bad_pending = copy.deepcopy(sealed)
    bad_pending["pending"] = [None, replay["actions"][1]["allocation"]]
    check(not game.legal(bad_pending, {"allocation": replay["actions"][1]["allocation"]})[0], "seat-one-only pending state is impossible")
    bad_boolean_turn = copy.deepcopy(state_a)
    bad_boolean_turn["toMove"] = True
    check(not game.legal(bad_boolean_turn, {"allocation": action_zero["allocation"]})[0], "boolean seat values cannot masquerade as integers")
    expect_error(lambda: game.reveal(state_a), "reveal_before_terminal", "private state cannot reveal before terminal")

    rebuilt = game.make_replay(replay["seed"], replay["actions"])
    check(rebuilt == replay, "replay rebuild is byte-semantics exact")
    final_state = game.setup(replay["seed"])
    for action in replay["actions"]:
        final_state = game.apply(final_state, {"allocation": action["allocation"]})
    check(
        game.terminal(final_state) == replay["result"]
        and game.reveal(final_state)["result"] == replay["result"],
        "terminal scoring and post-match reveal agree",
    )

    tampered_digest = copy.deepcopy(replay)
    tampered_digest["finalStateSha256"] = "0" * 64
    expect_error(lambda: verify_replay(manifest, tampered_digest), "replay_mismatch", "tampered final digest is refused")
    tampered_action = copy.deepcopy(replay)
    tampered_action["actions"][0]["allocation"] = [24, 0, 0, 0, 0]
    expect_error(lambda: verify_replay(manifest, tampered_action), "replay_mismatch", "tampered legal action is refused")
    overstated = copy.deepcopy(replay)
    overstated["truth"]["modelAttested"] = True
    expect_error(lambda: verify_replay(manifest, overstated), "replay_truth", "model attestation overclaim is refused")
    boolean_seat = copy.deepcopy(replay)
    boolean_seat["actions"][0]["seat"] = False
    expect_error(lambda: verify_replay(manifest, boolean_seat), "replay_seat", "boolean replay seat is refused")
    boolean_winner = copy.deepcopy(replay)
    boolean_winner["result"]["winner"] = True
    expect_error(lambda: verify_replay(manifest, boolean_winner), "replay_result", "boolean winner is refused")
    replay_extra = copy.deepcopy(replay)
    replay_extra["expression"] = CANARY
    expect_error(lambda: verify_replay(manifest, replay_extra), "replay_shape", "replay extras are refused")
    wrong_manifest = copy.deepcopy(replay)
    wrong_manifest["manifestSha256"] = "0" * 64
    expect_error(lambda: verify_replay(manifest, wrong_manifest), "replay_manifest", "wrong manifest binding is refused")
    incomplete = copy.deepcopy(replay)
    incomplete["actions"] = incomplete["actions"][:-1]
    expect_error(lambda: game.make_replay(incomplete["seed"], incomplete["actions"]), "replay_incomplete", "incomplete replay is refused")

    manifest_attacks = []
    boolean_schema = copy.deepcopy(manifest)
    boolean_schema["schemaVersion"] = True
    manifest_attacks.append((boolean_schema, "manifest_version"))
    extra = copy.deepcopy(manifest)
    extra["pythonModule"] = CANARY
    manifest_attacks.append((extra, "manifest_shape"))
    expression = copy.deepcopy(manifest)
    expression["rules"]["scoreExpression"] = CANARY
    manifest_attacks.append((expression, "rules_shape"))
    wrong_family = copy.deepcopy(manifest)
    wrong_family["rules"]["family"] = "python_callback"
    manifest_attacks.append((wrong_family, "rule_family"))
    bool_rounds = copy.deepcopy(manifest)
    bool_rounds["rules"]["rounds"] = True
    manifest_attacks.append((bool_rounds, "rounds"))
    float_weight = copy.deepcopy(manifest)
    float_weight["rules"]["fronts"][0]["weight"] = 1.5
    manifest_attacks.append((float_weight, "front_weight"))
    unsafe_license = copy.deepcopy(manifest)
    unsafe_license["creator"]["licenseId"] = CANARY
    manifest_attacks.append((unsafe_license, "creator_license"))
    unhashable_license = copy.deepcopy(manifest)
    unhashable_license["creator"]["licenseId"] = ["MIT"]
    manifest_attacks.append((unhashable_license, "creator_license"))
    duplicate_id = copy.deepcopy(manifest)
    duplicate_id["rules"]["fronts"][1]["id"] = duplicate_id["rules"]["fronts"][0]["id"]
    manifest_attacks.append((duplicate_id, "front_id_duplicate"))
    duplicate_label = copy.deepcopy(manifest)
    duplicate_label["rules"]["fronts"][1]["label"] = "BEACON"
    manifest_attacks.append((duplicate_label, "front_label_duplicate"))
    degenerate = copy.deepcopy(manifest)
    for front in degenerate["rules"]["fronts"]:
        front["weight"] = 1
    manifest_attacks.append((degenerate, "front_weight_degenerate"))
    control = copy.deepcopy(manifest)
    control["summary"] = f"A valid-length summary containing {CANARY}\u202e hidden control text."
    manifest_attacks.append((control, "game_summary"))
    non_nfc = copy.deepcopy(manifest)
    non_nfc["title"] = "Signa\u0301l Siege"
    manifest_attacks.append((non_nfc, "game_title"))
    check(
        all(_raises_code(lambda candidate=candidate: validate_manifest(candidate), code) for candidate, code in manifest_attacks),
        "manifest rejects code hooks expressions type confusion license drift duplicates degeneracy and Unicode controls",
    )
    check(
        all(
            _raises_creator_error(
                lambda field=field: validate_manifest(
                    {**copy.deepcopy(manifest), field: {"payload": CANARY}}
                )
            )
            for field in manifest
        ),
        "every manifest boundary field rejects hostile object substitution without an internal exception",
    )
    check(
        all(
            _raises_creator_error(
                lambda field=field: verify_replay(
                    manifest,
                    {**copy.deepcopy(replay), field: {"payload": CANARY}},
                )
            )
            for field in replay
        ),
        "every replay boundary field rejects hostile object substitution without an internal exception",
    )
    check(
        all(
            game.legal(
                {**copy.deepcopy(state_a), field: {"payload": CANARY}},
                {"allocation": action_zero["allocation"]},
            )
            == (False, "invalid_state")
            for field in state_a
        ),
        "every state boundary field fails closed under hostile object substitution",
    )

    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    registry_authority = copy.deepcopy(registry)
    registry_authority["entries"][0]["executionAuthorized"] = True
    expect_error(lambda: validate_registry(registry_authority, ROOT), "registry_authority", "registry cannot grant execution")
    registry_decision = copy.deepcopy(registry)
    registry_decision["entries"][0]["decision"] = "approved"
    expect_error(lambda: validate_registry(registry_decision, ROOT), "registry_decision", "registry cannot self-promote")
    registry_digest = copy.deepcopy(registry)
    registry_digest["entries"][0]["manifestSha256"] = "0" * 64
    expect_error(lambda: validate_registry(registry_digest, ROOT), "registry_manifest_digest", "registry digest drift is refused")
    registry_escape = copy.deepcopy(registry)
    registry_escape["entries"][0]["manifestPath"] = "../README.md"
    expect_error(lambda: validate_registry(registry_escape, ROOT), "registry_manifest_path", "registry path traversal is refused")
    registry_boolean_schema = copy.deepcopy(registry)
    registry_boolean_schema["schemaVersion"] = True
    expect_error(lambda: validate_registry(registry_boolean_schema, ROOT), "registry_version", "boolean registry version is refused")
    registry_windows_escape = copy.deepcopy(registry)
    registry_windows_escape["entries"][0]["manifestPath"] = "..\\README.md"
    expect_error(lambda: validate_registry(registry_windows_escape, ROOT), "registry_manifest_path", "backslash registry traversal is refused")
    check(
        all(
            _raises_creator_error(
                lambda field=field: validate_registry(
                    {**copy.deepcopy(registry), field: {"payload": CANARY}},
                    ROOT,
                )
            )
            for field in registry
        ),
        "every registry boundary field rejects hostile object substitution without an internal exception",
    )

    with tempfile.TemporaryDirectory(prefix="agentwars-creator-sdk-") as temp:
        root = Path(temp)
        duplicate_path = root / "duplicate.json"
        duplicate_path.write_text('{"schemaVersion":1,"schemaVersion":1}', encoding="utf-8")
        expect_error(lambda: load_manifest(duplicate_path), "duplicate_json_key", "duplicate JSON keys are refused")
        bom_path = root / "bom.json"
        bom_path.write_bytes(b"\xef\xbb\xbf{}")
        expect_error(lambda: load_manifest(bom_path), "manifest_encoding", "UTF-8 BOM is refused")
        oversized_path = root / "oversized.json"
        oversized_path.write_bytes(b"{" + b" " * MAX_MANIFEST_BYTES + b"}")
        expect_error(lambda: load_manifest(oversized_path), "manifest_too_large", "oversized manifest is refused")
        nan_path = root / "nan.json"
        nan_path.write_text('{"weight":NaN}', encoding="utf-8")
        expect_error(lambda: load_manifest(nan_path), "manifest_noncanonical_value", "non-finite JSON number is refused")
        invalid_path = root / "invalid.json"
        bad = copy.deepcopy(manifest)
        bad["summary"] = f"A long enough invalid candidate that includes {CANARY} but no executable authority."
        bad["rules"]["family"] = "python_callback"
        write_json(invalid_path, bad)
        process = subprocess.run(
            [sys.executable, "-B", str(ROOT / "bin" / "creator_game.py"), "validate", str(invalid_path)],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
        )
        failure = json.loads(process.stderr)
        check(
            process.returncode == 2
            and failure["code"] == "rule_family"
            and CANARY not in process.stdout + process.stderr
            and not failure["executionAuthorized"],
            "CLI fails with bounded non-reflective JSON and no authority",
        )

    outputs = []
    for hash_seed in ("1", "937"):
        environment = dict(os.environ)
        environment["PYTHONHASHSEED"] = hash_seed
        process = subprocess.run(
            [
                sys.executable,
                "-B",
                str(ROOT / "bin" / "creator_game.py"),
                "verify-replay",
                str(MANIFEST_PATH),
                str(REPLAY_PATH),
            ],
            cwd=ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
        )
        check(process.returncode == 0 and not process.stderr, f"cross-process replay succeeds with hash seed {hash_seed}")
        outputs.append(process.stdout)
    check(outputs[0] == outputs[1], "cross-process replay report is byte-identical")

    print(
        f"all {PASSED} declarative creator-game checks passed; "
        "candidate remains non-executable and unadmitted."
    )
    return 0


def _raises_code(action, code: str) -> bool:
    try:
        action()
    except CreatorGameError as error:
        return error.code == code and CANARY not in str(error)
    return False


def _raises_creator_error(action) -> bool:
    try:
        action()
    except CreatorGameError as error:
        return CANARY not in str(error)
    return False


if __name__ == "__main__":
    raise SystemExit(main())
