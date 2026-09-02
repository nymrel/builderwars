#!/usr/bin/env python3
"""Adversarial checks for exact-scope, non-ranking AgentWars proof boards."""

from __future__ import annotations

import ast
import copy
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bin.build_mobile_arena_read_model import build_read_model
from publishing import scoped_ratings as ratings


CHECKS = 0


def check(condition: bool, label: str) -> None:
    global CHECKS
    if not condition:
        raise AssertionError(label)
    CHECKS += 1


def refuses(callable_, label: str) -> None:
    try:
        callable_()
    except ratings.ScopedRatingError:
        check(True, label)
    else:
        raise AssertionError(label)


def load_projection() -> dict[str, object]:
    dataset = json.loads((ROOT / "publishing" / "agentwars-public-v1" / "dataset.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "publishing" / "agentwars-public-v1" / "source-manifest.json").read_text(encoding="utf-8"))
    ledger = json.loads((ROOT / "publishing" / "agentwars-public-correction-ledger.v1.json").read_text(encoding="utf-8"))
    return build_read_model(dataset, manifest, ledger)


def rebuild(model: dict[str, object], receipts: list[dict[str, object]]) -> list[dict[str, object]]:
    source = model["source"]
    return ratings.build_scoped_rating_boards(
        receipts,
        dataset_digest=source["datasetDigest"],
        source_manifest_digest=source["sourceManifestDigest"],
    )


def main() -> int:
    model = load_projection()
    receipts = model["receipts"]
    boards = model["scopedRatingBoards"]
    check(model["projectionVersion"] == "3", "read-model projection version is pinned")
    check(model["summary"]["scopedRatingBoardCount"] == 5, "summary records five exact scopes")
    check(len(boards) == 5, "five exact scoped proof boards are emitted")
    check(sum(board["receiptCount"] for board in boards) == 8, "eight reviewed receipts are covered once")
    check(rebuild(model, receipts) == boards, "tracked boards equal the deterministic rebuild")
    check(
        ratings.verify_scoped_rating_boards(
            boards,
            receipts,
            dataset_digest=model["source"]["datasetDigest"],
            source_manifest_digest=model["source"]["sourceManifestDigest"],
        ) == boards,
        "tracked boards verify against reviewed receipts",
    )
    check(rebuild(model, list(reversed(receipts))) == boards, "receipt ordering cannot change board output")

    expected_scopes = {
        ("fantasy_dynasty", "1", "dynasty"): 2,
        ("fantasy_qb_surge", "1", "qb_surge"): 2,
        ("fantasy_redraft", "1", "redraft"): 2,
        ("nim", "1", None): 1,
        ("ten_fronts", "1", None): 1,
    }
    actual_scopes = {
        (board["scope"]["gameName"], board["scope"]["gameVersion"], board["scope"]["format"]): board["receiptCount"]
        for board in boards
    }
    check(actual_scopes == expected_scopes, "redraft, dynasty, QB Surge, Nim, and Ten Fronts stay separate")
    check([board["scope"]["gameName"] for board in boards] == sorted(scope[0] for scope in expected_scopes), "boards use deterministic game ordering")

    covered_receipts: set[str] = set()
    for board in boards:
        check(board["schemaVersion"] == ratings.SCHEMA_VERSION, "board schema is pinned")
        check(board["status"] == ratings.STATUS, "board declares non-ranking status")
        check(board["scope"]["ratingMethod"] == ratings.RATING_METHOD, "scope binds the exact rating method")
        check(board["scope"]["resourceClass"] == ratings.RESOURCE_CLASS, "scope binds the reviewed receipt resource class")
        check(board["scopeId"] == ratings.digest(board["scope"]), "scope ID seals exact game, format, engine, method, and resource")
        core = {key: value for key, value in board.items() if key != "boardDigest"}
        check(board["boardDigest"] == ratings.digest(core), "board digest seals the complete snapshot")
        check(all(value is False for value in board["authority"].values()), "board grants zero comparison or production authority")
        check("not ranked" in board["boundary"]["statement"], "board boundary disclaims ranking")
        check(board["receiptIds"] == sorted(board["receiptIds"]), "board receipt IDs are sorted")
        check(covered_receipts.isdisjoint(board["receiptIds"]), "a receipt cannot enter two scoped boards")
        covered_receipts.update(board["receiptIds"])
        check([row["entrantId"] for row in board["entrants"]] == sorted(row["entrantId"] for row in board["entrants"]), "rows are alphabetic by stable entrant ID, not score")
        check(all(row["status"] == "not_ranked" and row["eligibleForPublicRanking"] is False for row in board["entrants"]), "every entrant stays ranking-ineligible")
        check(all(row["ratingUnit"] == ratings.RATING_UNIT and row["ratingPoints"] == row["wins"] for row in board["entrants"]), "one reviewed win equals exactly one proof point")
        check(all(row["receiptCount"] == row["wins"] + row["losses"] for row in board["entrants"]), "entrant records reconcile")
        check(all(row["harnessVersionIds"] == sorted(set(row["harnessVersionIds"])) for row in board["entrants"]), "harness lineage is unique and sorted")
    check(covered_receipts == {receipt["receiptId"] for receipt in receipts}, "board coverage equals the reviewed receipt set")

    duplicate = copy.deepcopy(receipts)
    duplicate.append(copy.deepcopy(duplicate[0]))
    refuses(lambda: rebuild(model, duplicate), "duplicate receipt IDs are refused")

    replay_failure = copy.deepcopy(receipts)
    replay_failure[0]["proof"]["replayVerdict"] = "FAIL"
    refuses(lambda: rebuild(model, replay_failure), "failed replay proof is refused")

    engine_failure = copy.deepcopy(receipts)
    engine_failure[0]["proof"]["engineDigestMatch"] = False
    refuses(lambda: rebuild(model, engine_failure), "engine mismatch is refused")

    missing_engine = copy.deepcopy(receipts)
    missing_engine[0]["proof"].pop("engineDigest")
    refuses(lambda: rebuild(model, missing_engine), "missing exact engine digest is refused")

    unpublished = copy.deepcopy(receipts)
    unpublished[0]["proof"]["publicationApproved"] = False
    refuses(lambda: rebuild(model, unpublished), "unpublished receipts are refused")

    unfinished = copy.deepcopy(receipts)
    unfinished[0]["outcome"]["status"] = "pending"
    refuses(lambda: rebuild(model, unfinished), "non-final receipts are refused")

    unknown_winner = copy.deepcopy(receipts)
    unknown_winner[0]["outcome"]["winnerEntrantId"] = "0" * 64
    refuses(lambda: rebuild(model, unknown_winner), "unknown winners are refused")

    inconsistent_identity = copy.deepcopy(receipts)
    repeated_id = inconsistent_identity[0]["entrants"][0]["entrantId"]
    for receipt in inconsistent_identity[1:]:
        for entrant in receipt["entrants"]:
            if entrant["entrantId"] == repeated_id:
                entrant["name"] += " drift"
                refuses(lambda: rebuild(model, inconsistent_identity), "cross-receipt entrant name drift is refused")
                break
        else:
            continue
        break

    moved_scope = copy.deepcopy(receipts)
    moved_scope[0]["proof"]["engineDigest"] = "0" * 64
    changed_boards = rebuild(model, moved_scope)
    check(changed_boards != boards, "engine digest drift changes the exact scope instead of silently merging")
    refuses(
        lambda: ratings.verify_scoped_rating_boards(
            boards,
            moved_scope,
            dataset_digest=model["source"]["datasetDigest"],
            source_manifest_digest=model["source"]["sourceManifestDigest"],
        ),
        "old boards cannot verify after engine scope drift",
    )

    authority_tamper = copy.deepcopy(boards)
    authority_tamper[0]["authority"]["ranking"] = True
    refuses(
        lambda: ratings.verify_scoped_rating_boards(
            authority_tamper,
            receipts,
            dataset_digest=model["source"]["datasetDigest"],
            source_manifest_digest=model["source"]["sourceManifestDigest"],
        ),
        "ranking authority tamper is refused",
    )

    score_tamper = copy.deepcopy(boards)
    score_tamper[0]["entrants"][0]["ratingPoints"] += 100
    refuses(
        lambda: ratings.verify_scoped_rating_boards(
            score_tamper,
            receipts,
            dataset_digest=model["source"]["datasetDigest"],
            source_manifest_digest=model["source"]["sourceManifestDigest"],
        ),
        "proof-point inflation is refused",
    )

    source_path = ROOT / "publishing" / "scoped_ratings.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imports = {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    } | {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    check(imports <= {"__future__", "arena", "collections", "re", "typing"}, "ratings import only pure local or standard-library modules")
    check(not any(isinstance(node, (ast.With, ast.AsyncWith)) for node in tree.body), "ratings have no import-time file or context-manager side effects")
    check(not any(isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) for node in tree.body), "ratings have no import-time call expressions")

    print(f"AgentWars scoped proof ratings: PASS ({CHECKS} checks, 5 scopes, 8 reviewed receipts)")
    print("alphabetic non-ranking snapshots / exact game-format-engine-resource binding / zero production authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
