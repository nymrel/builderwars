"""Declarative AgentWars creator-game candidate runtime.

This module interprets one deliberately narrow, finite rule family. Creator
input is data, never Python: there is no import hook, expression language,
callback, template execution, network access, subprocess, or ambient secret
lookup. A valid manifest is still only a held candidate. Source-controlled
admission, review, publication, and ranking are separate decisions.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path, PurePosixPath

from arena.canonical import NonCanonical, canonical_bytes, digest


MANIFEST_PROTOCOL = "agentwars.creator_game.v1"
STATE_PROTOCOL = "agentwars.creator_game_state.v1"
REPLAY_PROTOCOL = "agentwars.creator_replay.v1"
REGISTRY_PROTOCOL = "agentwars.creator_registry.v1"
FAMILY = "sealed_allocation_v1"
CANDIDATE_STATUS = "candidate_not_admitted"
REGISTRY_STATUS = "candidate_registry_not_runtime_admission"
REGISTRY_DECISION = "held_exhibition_candidate"

MAX_MANIFEST_BYTES = 16 * 1024
MAX_REPLAY_BYTES = 128 * 1024
MAX_REGISTRY_BYTES = 32 * 1024
MAX_ROUNDS = 20
MAX_FRONTS = 12
MAX_BUDGET = 1000
MAX_WEIGHT = 1000
MAX_SEED = (1 << 63) - 1

_GAME_ID = re.compile(r"^creator\.[a-z0-9]+(?:-[a-z0-9]+)*$")
_FRONT_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
_SEMVER = re.compile(r"^(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_LICENSES = frozenset({"Apache-2.0", "CC-BY-4.0", "MIT"})

_MANIFEST_KEYS = frozenset(
    {
        "schemaVersion",
        "protocolVersion",
        "gameId",
        "version",
        "title",
        "summary",
        "creator",
        "rules",
        "presentation",
    }
)
_CREATOR_KEYS = frozenset({"displayName", "licenseId"})
_RULE_KEYS = frozenset(
    {
        "family",
        "rounds",
        "budgetPerRound",
        "fronts",
        "frontOrder",
        "allocationVisibility",
        "scoreRule",
        "seatPolicy",
    }
)
_FRONT_KEYS = frozenset({"id", "label", "weight"})
_PRESENTATION_KEYS = frozenset({"spectatorOneLiner", "strategyPrompt"})
_STATE_KEYS = frozenset(
    {
        "protocolVersion",
        "manifestSha256",
        "seed",
        "round",
        "turn",
        "toMove",
        "pending",
        "scores",
        "history",
    }
)
_HISTORY_KEYS = frozenset(
    {"round", "frontOrder", "allocations", "roundScores", "scoresAfter"}
)
_ACTION_KEYS = frozenset({"allocation"})
_REPLAY_ACTION_KEYS = frozenset({"seat", "allocation"})
_REPLAY_KEYS = frozenset(
    {
        "protocolVersion",
        "manifestSha256",
        "gameId",
        "gameVersion",
        "seed",
        "actions",
        "finalStateSha256",
        "result",
        "truth",
    }
)
_RESULT_KEYS = frozenset({"scores", "winner", "reason"})
_TRUTH_KEYS = frozenset(
    {
        "replayVerified",
        "modelAttested",
        "providerAttested",
        "runtimeAttested",
        "harnessExecutionAttested",
        "rankingAuthorized",
        "publicationAuthorized",
    }
)
_REGISTRY_KEYS = frozenset({"schemaVersion", "protocolVersion", "status", "entries"})
_REGISTRY_ENTRY_KEYS = frozenset(
    {
        "gameId",
        "version",
        "manifestPath",
        "manifestSha256",
        "replayPath",
        "replaySha256",
        "decision",
        "authorEntrantRankingAuthorized",
        "executionAuthorized",
        "publicationAuthorized",
    }
)


class CreatorGameError(ValueError):
    """Stable, non-reflective failure for creator-controlled input."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _require(condition: object, code: str, message: str) -> None:
    if not condition:
        raise CreatorGameError(code, message)


def _exact_keys(value: object, keys: frozenset[str], code: str, label: str) -> dict:
    _require(isinstance(value, dict), code, f"{label} must be an object")
    _require(set(value) == keys, code, f"{label} has missing or unexpected fields")
    return value


def _int(value: object, minimum: int, maximum: int, code: str, label: str) -> int:
    _require(
        isinstance(value, int) and not isinstance(value, bool),
        code,
        f"{label} must be an integer",
    )
    _require(minimum <= value <= maximum, code, f"{label} is out of bounds")
    return value


def _text(value: object, minimum: int, maximum: int, code: str, label: str) -> str:
    _require(isinstance(value, str), code, f"{label} must be a string")
    _require(value == unicodedata.normalize("NFC", value), code, f"{label} must use NFC")
    _require(value == value.strip(), code, f"{label} must not have edge whitespace")
    _require(minimum <= len(value) <= maximum, code, f"{label} has invalid length")
    _require(
        not any(unicodedata.category(character).startswith("C") for character in value),
        code,
        f"{label} contains a control or format character",
    )
    return value


def _duplicate_rejector(pairs: list[tuple[str, object]]) -> dict:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise CreatorGameError("duplicate_json_key", "JSON contains a duplicate object key")
        value[key] = item
    return value


def _read_json(path: os.PathLike[str] | str, maximum: int, kind: str) -> dict:
    try:
        with open(path, "rb") as handle:
            raw = handle.read(maximum + 1)
    except (OSError, ValueError) as error:
        raise CreatorGameError(f"{kind}_read_failed", f"{kind} could not be read") from error
    _require(len(raw) <= maximum, f"{kind}_too_large", f"{kind} exceeds its byte limit")
    _require(not raw.startswith(b"\xef\xbb\xbf"), f"{kind}_encoding", f"{kind} must not use a BOM")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_duplicate_rejector)
    except CreatorGameError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CreatorGameError(f"{kind}_json_invalid", f"{kind} is not strict UTF-8 JSON") from error
    _require(isinstance(value, dict), f"{kind}_shape", f"{kind} must be an object")
    try:
        canonical_bytes(value)
    except NonCanonical as error:
        raise CreatorGameError(f"{kind}_noncanonical_value", f"{kind} contains a noncanonical value") from error
    return value


def _clone(value: object):
    return json.loads(canonical_bytes(value).decode("utf-8"))


def validate_manifest(value: object) -> dict:
    manifest = _exact_keys(value, _MANIFEST_KEYS, "manifest_shape", "manifest")
    _int(manifest["schemaVersion"], 1, 1, "manifest_version", "schemaVersion")
    _require(
        manifest["protocolVersion"] == MANIFEST_PROTOCOL,
        "manifest_protocol",
        "manifest protocol is unsupported",
    )
    _require(
        isinstance(manifest["gameId"], str) and _GAME_ID.fullmatch(manifest["gameId"]) is not None,
        "game_id",
        "gameId must be a creator namespace id",
    )
    _require(
        isinstance(manifest["version"], str) and _SEMVER.fullmatch(manifest["version"]) is not None,
        "game_version",
        "version must be stable semantic version text",
    )
    _text(manifest["title"], 3, 80, "game_title", "title")
    _text(manifest["summary"], 20, 280, "game_summary", "summary")

    creator = _exact_keys(manifest["creator"], _CREATOR_KEYS, "creator_shape", "creator")
    _text(creator["displayName"], 2, 80, "creator_name", "creator displayName")
    _require(
        isinstance(creator["licenseId"], str) and creator["licenseId"] in _LICENSES,
        "creator_license",
        "licenseId is unsupported",
    )

    rules = _exact_keys(manifest["rules"], _RULE_KEYS, "rules_shape", "rules")
    _require(rules["family"] == FAMILY, "rule_family", "rule family is unsupported")
    rounds = _int(rules["rounds"], 2, MAX_ROUNDS, "rounds", "rounds")
    budget = _int(rules["budgetPerRound"], 3, MAX_BUDGET, "budget", "budgetPerRound")
    _require(rules["frontOrder"] == "sha256_rotation_v1", "front_order", "frontOrder is unsupported")
    _require(
        rules["allocationVisibility"] == "sealed_until_both_submit",
        "allocation_visibility",
        "allocationVisibility is unsupported",
    )
    _require(
        rules["scoreRule"] == "winner_two_weight_tie_one_each",
        "score_rule",
        "scoreRule is unsupported",
    )
    _require(
        rules["seatPolicy"] == "mirrored_series_required",
        "seat_policy",
        "seatPolicy is unsupported",
    )
    fronts = rules["fronts"]
    _require(isinstance(fronts, list), "fronts_shape", "fronts must be an array")
    _require(3 <= len(fronts) <= MAX_FRONTS, "fronts_count", "front count is out of bounds")
    _require(budget >= len(fronts), "budget_fronts", "budget must cover at least one unit per front")
    front_ids: list[str] = []
    labels: list[str] = []
    weights: list[int] = []
    for index, candidate in enumerate(fronts):
        front = _exact_keys(candidate, _FRONT_KEYS, "front_shape", f"front {index}")
        _require(
            isinstance(front["id"], str) and _FRONT_ID.fullmatch(front["id"]) is not None,
            "front_id",
            "front id is invalid",
        )
        front_ids.append(front["id"])
        labels.append(_text(front["label"], 1, 40, "front_label", "front label"))
        weights.append(_int(front["weight"], 1, MAX_WEIGHT, "front_weight", "front weight"))
    _require(len(front_ids) == len(set(front_ids)), "front_id_duplicate", "front ids must be unique")
    _require(
        len(labels) == len({label.casefold() for label in labels}),
        "front_label_duplicate",
        "front labels must be case-insensitively unique",
    )
    _require(len(set(weights)) >= 3, "front_weight_degenerate", "at least three front weights must differ")
    _require(rounds * sum(weights) * 2 <= 1_000_000, "score_bound", "maximum score is too large")

    presentation = _exact_keys(
        manifest["presentation"],
        _PRESENTATION_KEYS,
        "presentation_shape",
        "presentation",
    )
    _text(
        presentation["spectatorOneLiner"],
        20,
        180,
        "spectator_one_liner",
        "spectatorOneLiner",
    )
    _text(presentation["strategyPrompt"], 20, 500, "strategy_prompt", "strategyPrompt")
    return _clone(manifest)


def load_manifest(path: os.PathLike[str] | str) -> dict:
    return validate_manifest(_read_json(path, MAX_MANIFEST_BYTES, "manifest"))


def manifest_sha256(manifest: object) -> str:
    return digest(validate_manifest(manifest))


def _allocation(value: object, front_count: int, budget: int, code: str) -> list[int]:
    _require(isinstance(value, list), code, "allocation must be an array")
    _require(len(value) == front_count, code, "allocation has the wrong length")
    result = [
        _int(item, 0, budget, code, "allocation entry")
        for item in value
    ]
    _require(sum(result) == budget, code, "allocation has the wrong sum")
    return result


class SealedAllocationGame:
    """Finite interpreter for ``sealed_allocation_v1`` manifests."""

    def __init__(self, manifest: object):
        self.manifest = validate_manifest(manifest)
        self.manifest_sha256 = digest(self.manifest)
        self.game_id = self.manifest["gameId"]
        self.version = self.manifest["version"]
        self.rounds = self.manifest["rules"]["rounds"]
        self.budget = self.manifest["rules"]["budgetPerRound"]
        self.fronts = _clone(self.manifest["rules"]["fronts"])

    def _fronts_for_round(self, seed: int, round_index: int) -> list[dict]:
        preimage = f"{self.manifest_sha256}:{seed}:{round_index}".encode("ascii")
        offset = int.from_bytes(hashlib.sha256(preimage).digest()[:8], "big") % len(self.fronts)
        return _clone(self.fronts[offset:] + self.fronts[:offset])

    def setup(self, seed: int) -> dict:
        _int(seed, -MAX_SEED, MAX_SEED, "seed", "seed")
        return {
            "protocolVersion": STATE_PROTOCOL,
            "manifestSha256": self.manifest_sha256,
            "seed": seed,
            "round": 0,
            "turn": 0,
            "toMove": 0,
            "pending": [None, None],
            "scores": [0, 0],
            "history": [],
        }

    def _score_round(self, fronts: list[dict], pair: list[list[int]]) -> list[int]:
        points = [0, 0]
        for index, front in enumerate(fronts):
            weight = front["weight"]
            if pair[0][index] > pair[1][index]:
                points[0] += weight * 2
            elif pair[1][index] > pair[0][index]:
                points[1] += weight * 2
            else:
                points[0] += weight
                points[1] += weight
        return points

    def _validate_state(self, value: object) -> dict:
        state = _exact_keys(value, _STATE_KEYS, "state_shape", "state")
        _require(state["protocolVersion"] == STATE_PROTOCOL, "state_protocol", "state protocol drifted")
        _require(state["manifestSha256"] == self.manifest_sha256, "state_manifest", "state manifest drifted")
        seed = _int(state["seed"], -MAX_SEED, MAX_SEED, "state_seed", "state seed")
        round_index = _int(state["round"], 0, self.rounds, "state_round", "state round")
        turn = _int(state["turn"], 0, self.rounds * 2, "state_turn", "state turn")
        _int(state["toMove"], 0, 1, "state_to_move", "state toMove")
        _require(isinstance(state["pending"], list) and len(state["pending"]) == 2, "state_pending", "state pending is invalid")
        _require(isinstance(state["scores"], list) and len(state["scores"]) == 2, "state_scores", "state scores are invalid")
        scores = [
            _int(score, 0, 1_000_000, "state_scores", "state score")
            for score in state["scores"]
        ]
        _require(isinstance(state["history"], list), "state_history", "state history is invalid")
        _require(len(state["history"]) == round_index, "state_history", "state history length drifted")

        cumulative = [0, 0]
        for expected_round, candidate in enumerate(state["history"]):
            row = _exact_keys(candidate, _HISTORY_KEYS, "state_history", "history row")
            _require(row["round"] == expected_round, "state_history", "history round drifted")
            fronts = self._fronts_for_round(seed, expected_round)
            expected_order = [front["id"] for front in fronts]
            _require(row["frontOrder"] == expected_order, "state_history", "history front order drifted")
            _require(isinstance(row["allocations"], list) and len(row["allocations"]) == 2, "state_history", "history allocations drifted")
            pair = [
                _allocation(allocation, len(self.fronts), self.budget, "state_history")
                for allocation in row["allocations"]
            ]
            round_scores = self._score_round(fronts, pair)
            _require(row["roundScores"] == round_scores, "state_history", "history round score drifted")
            cumulative = [cumulative[0] + round_scores[0], cumulative[1] + round_scores[1]]
            _require(row["scoresAfter"] == cumulative, "state_history", "history cumulative score drifted")
        _require(scores == cumulative, "state_scores", "state score does not match history")

        pending = state["pending"]
        if round_index == self.rounds:
            _require(pending == [None, None], "state_terminal", "terminal state retains a pending action")
            _require(turn == self.rounds * 2 and state["toMove"] == 0, "state_terminal", "terminal turn drifted")
        elif pending == [None, None]:
            _require(state["toMove"] == 0, "state_pending", "empty round must begin with seat zero")
            _require(turn == round_index * 2, "state_turn", "empty-round turn drifted")
        else:
            _require(pending[1] is None, "state_pending", "seat-one pending action cannot exist alone")
            _allocation(pending[0], len(self.fronts), self.budget, "state_pending")
            _require(state["toMove"] == 1, "state_pending", "sealed response must move to seat one")
            _require(turn == round_index * 2 + 1, "state_turn", "sealed-round turn drifted")
        return state

    def legal(self, state: object, action: object) -> tuple[bool, str]:
        try:
            self._validate_state(state)
        except CreatorGameError:
            return False, "invalid_state"
        if state["round"] >= self.rounds:
            return False, "match_complete"
        if not isinstance(action, dict) or set(action) != _ACTION_KEYS:
            return False, "action_shape"
        try:
            _allocation(action["allocation"], len(self.fronts), self.budget, "allocation_invalid")
        except CreatorGameError as error:
            return False, error.code
        return True, "legal"

    def apply(self, state: object, action: object) -> dict:
        self._validate_state(state)
        legal, code = self.legal(state, action)
        _require(legal, code, "action is illegal")
        nxt = _clone(state)
        allocation = list(action["allocation"])
        seat = nxt["toMove"]
        nxt["pending"][seat] = allocation
        nxt["turn"] += 1
        if seat == 0:
            nxt["toMove"] = 1
            self._validate_state(nxt)
            return nxt

        fronts = self._fronts_for_round(nxt["seed"], nxt["round"])
        pair = [list(nxt["pending"][0]), list(nxt["pending"][1])]
        round_scores = self._score_round(fronts, pair)
        scores_after = [
            nxt["scores"][0] + round_scores[0],
            nxt["scores"][1] + round_scores[1],
        ]
        nxt["history"].append(
            {
                "round": nxt["round"],
                "frontOrder": [front["id"] for front in fronts],
                "allocations": pair,
                "roundScores": round_scores,
                "scoresAfter": scores_after,
            }
        )
        nxt["round"] += 1
        nxt["toMove"] = 0
        nxt["pending"] = [None, None]
        nxt["scores"] = scores_after
        self._validate_state(nxt)
        return nxt

    def observation(self, state: object, seat: int) -> dict:
        self._validate_state(state)
        _int(seat, 0, 1, "seat", "seat")
        current_fronts = (
            self._fronts_for_round(state["seed"], state["round"])
            if state["round"] < self.rounds
            else None
        )
        return {
            "protocolVersion": MANIFEST_PROTOCOL,
            "game": {
                "gameId": self.game_id,
                "version": self.version,
                "manifestSha256": self.manifest_sha256,
                "title": self.manifest["title"],
                "summary": self.manifest["summary"],
            },
            "youAre": seat,
            "round": state["round"],
            "roundsTotal": self.rounds,
            "turn": state["turn"],
            "toMove": state["toMove"],
            "budgetPerRound": self.budget,
            "fronts": current_fronts,
            "scores": list(state["scores"]),
            "history": _clone(state["history"]),
            "submittedSeats": [item is not None for item in state["pending"]],
            "yourPendingAllocation": (
                list(state["pending"][seat]) if state["pending"][seat] is not None else None
            ),
            "opponentPendingAllocationVisible": False,
            "moveSchema": {"allocation": [f"integer x{len(self.fronts)}", f"sum={self.budget}"]},
        }

    def render(self, state: object) -> dict:
        self._validate_state(state)
        current_fronts = (
            self._fronts_for_round(state["seed"], state["round"])
            if state["round"] < self.rounds
            else None
        )
        return {
            "gameId": self.game_id,
            "title": self.manifest["title"],
            "spectatorOneLiner": self.manifest["presentation"]["spectatorOneLiner"],
            "round": state["round"],
            "roundsTotal": self.rounds,
            "fronts": current_fronts,
            "scores": list(state["scores"]),
            "submittedSeats": [item is not None for item in state["pending"]],
            "pendingAllocationsVisible": False,
            "history": _clone(state["history"]),
        }

    def terminal(self, state: object) -> dict | None:
        self._validate_state(state)
        if state["round"] != self.rounds:
            return None
        score_zero, score_one = state["scores"]
        winner = None if score_zero == score_one else (0 if score_zero > score_one else 1)
        return {
            "winner": winner,
            "scores": list(state["scores"]),
            "reason": f"sealed_allocation_score:{score_zero}-{score_one}",
        }

    def reveal(self, state: object) -> dict:
        terminal = self.terminal(state)
        _require(terminal is not None, "reveal_before_terminal", "reveal requires a terminal state")
        return {
            "manifest": _clone(self.manifest),
            "manifestSha256": self.manifest_sha256,
            "state": _clone(state),
            "result": terminal,
        }

    def move_bound(self) -> int:
        return self.rounds * 2

    def make_replay(self, seed: int, actions: object) -> dict:
        _require(isinstance(actions, list), "replay_actions", "actions must be an array")
        state = self.setup(seed)
        normalized_actions: list[dict] = []
        for candidate in actions:
            row = _exact_keys(candidate, _REPLAY_ACTION_KEYS, "replay_action", "replay action")
            seat = _int(row["seat"], 0, 1, "replay_seat", "replay seat")
            _require(seat == state["toMove"], "replay_seat", "replay seat order drifted")
            allocation = _allocation(
                row["allocation"], len(self.fronts), self.budget, "replay_allocation"
            )
            normalized_actions.append({"seat": seat, "allocation": allocation})
            state = self.apply(state, {"allocation": allocation})
        terminal = self.terminal(state)
        _require(terminal is not None, "replay_incomplete", "replay did not reach a terminal state")
        return {
            "protocolVersion": REPLAY_PROTOCOL,
            "manifestSha256": self.manifest_sha256,
            "gameId": self.game_id,
            "gameVersion": self.version,
            "seed": seed,
            "actions": normalized_actions,
            "finalStateSha256": digest(state),
            "result": terminal,
            "truth": {
                "replayVerified": True,
                "modelAttested": False,
                "providerAttested": False,
                "runtimeAttested": False,
                "harnessExecutionAttested": False,
                "rankingAuthorized": False,
                "publicationAuthorized": False,
            },
        }


def load_replay(path: os.PathLike[str] | str) -> dict:
    return _read_json(path, MAX_REPLAY_BYTES, "replay")


def replay_sha256(replay: object) -> str:
    return digest(_validate_replay_shape(replay))


def _validate_replay_shape(value: object) -> dict:
    replay = _exact_keys(value, _REPLAY_KEYS, "replay_shape", "replay")
    _require(replay["protocolVersion"] == REPLAY_PROTOCOL, "replay_protocol", "replay protocol is unsupported")
    _require(isinstance(replay["manifestSha256"], str) and _SHA256.fullmatch(replay["manifestSha256"]), "replay_manifest", "replay manifest digest is invalid")
    _require(isinstance(replay["gameId"], str) and _GAME_ID.fullmatch(replay["gameId"]), "replay_game", "replay game id is invalid")
    _require(isinstance(replay["gameVersion"], str) and _SEMVER.fullmatch(replay["gameVersion"]), "replay_version", "replay game version is invalid")
    _int(replay["seed"], -MAX_SEED, MAX_SEED, "replay_seed", "replay seed")
    _require(isinstance(replay["actions"], list), "replay_actions", "replay actions must be an array")
    _require(len(replay["actions"]) <= MAX_ROUNDS * 2, "replay_actions", "replay has too many actions")
    for candidate in replay["actions"]:
        row = _exact_keys(candidate, _REPLAY_ACTION_KEYS, "replay_action", "replay action")
        _int(row["seat"], 0, 1, "replay_seat", "replay seat")
        _require(
            isinstance(row["allocation"], list) and len(row["allocation"]) <= MAX_FRONTS,
            "replay_allocation",
            "replay allocation is invalid",
        )
        for item in row["allocation"]:
            _int(item, 0, MAX_BUDGET, "replay_allocation", "replay allocation entry")
    _require(isinstance(replay["finalStateSha256"], str) and _SHA256.fullmatch(replay["finalStateSha256"]), "replay_final_state", "final state digest is invalid")
    result = _exact_keys(replay["result"], _RESULT_KEYS, "replay_result", "replay result")
    _require(isinstance(result["scores"], list) and len(result["scores"]) == 2, "replay_result", "replay scores are invalid")
    for score in result["scores"]:
        _int(score, 0, 1_000_000, "replay_result", "replay score")
    _require(
        result["winner"] is None
        or (
            isinstance(result["winner"], int)
            and not isinstance(result["winner"], bool)
            and result["winner"] in (0, 1)
        ),
        "replay_result",
        "replay winner is invalid",
    )
    _text(result["reason"], 1, 100, "replay_result", "replay reason")
    truth = _exact_keys(replay["truth"], _TRUTH_KEYS, "replay_truth", "replay truth")
    _require(truth["replayVerified"] is True, "replay_truth", "replay truth must declare replay verification")
    for key in _TRUTH_KEYS - {"replayVerified"}:
        _require(truth[key] is False, "replay_truth", "replay truth overstates authority or attestation")
    return replay


def verify_replay(manifest: object, replay: object) -> dict:
    game = SealedAllocationGame(manifest)
    candidate = _validate_replay_shape(replay)
    _require(candidate["manifestSha256"] == game.manifest_sha256, "replay_manifest", "replay manifest does not match")
    _require(candidate["gameId"] == game.game_id, "replay_game", "replay game does not match")
    _require(candidate["gameVersion"] == game.version, "replay_version", "replay version does not match")
    rebuilt = game.make_replay(candidate["seed"], candidate["actions"])
    _require(candidate == rebuilt, "replay_mismatch", "replay does not reproduce exactly")
    return {
        "schemaVersion": 1,
        "status": "pass",
        "effectiveVerdict": "PASS",
        "candidateStatus": CANDIDATE_STATUS,
        "gameId": game.game_id,
        "gameVersion": game.version,
        "manifestSha256": game.manifest_sha256,
        "replaySha256": digest(candidate),
        "moveCount": len(candidate["actions"]),
        "modelAttested": False,
        "providerAttested": False,
        "runtimeAttested": False,
        "harnessExecutionAttested": False,
        "rankingAuthorized": False,
        "publicationAuthorized": False,
        "codeExecutionAuthorized": False,
    }


def _safe_registry_path(root: Path, value: object, code: str) -> Path:
    _require(
        isinstance(value, str)
        and 1 <= len(value) <= 240
        and "\\" not in value
        and ":" not in value,
        code,
        "registry path is invalid",
    )
    posix = PurePosixPath(value)
    _require(not posix.is_absolute() and ".." not in posix.parts and "." not in posix.parts, code, "registry path must stay relative")
    _require(all(part and not part.startswith(".") for part in posix.parts), code, "registry path contains a hidden segment")
    unresolved = root.joinpath(*posix.parts)
    try:
        resolved = unresolved.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as error:
        raise CreatorGameError(code, "registry path leaves its source root or is absent") from error
    cursor = unresolved
    while cursor != root:
        _require(not cursor.is_symlink(), code, "registry path must not traverse a symlink")
        cursor = cursor.parent
    _require(resolved.is_file(), code, "registry path must name a file")
    return resolved


def validate_registry(value: object, source_root: os.PathLike[str] | str) -> dict:
    registry = _exact_keys(value, _REGISTRY_KEYS, "registry_shape", "registry")
    _int(registry["schemaVersion"], 1, 1, "registry_version", "registry schemaVersion")
    _require(registry["protocolVersion"] == REGISTRY_PROTOCOL, "registry_protocol", "registry protocol is unsupported")
    _require(registry["status"] == REGISTRY_STATUS, "registry_status", "registry status overstates admission")
    _require(isinstance(registry["entries"], list) and 1 <= len(registry["entries"]) <= 32, "registry_entries", "registry entries are invalid")
    try:
        root = Path(source_root).resolve(strict=True)
    except OSError as error:
        raise CreatorGameError("registry_root", "registry source root is unavailable") from error
    _require(root.is_dir(), "registry_root", "registry source root must be a directory")
    seen: set[tuple[str, str]] = set()
    reports: list[dict] = []
    for candidate in registry["entries"]:
        entry = _exact_keys(candidate, _REGISTRY_ENTRY_KEYS, "registry_entry", "registry entry")
        _require(entry["decision"] == REGISTRY_DECISION, "registry_decision", "registry decision overstates admission")
        for key in (
            "authorEntrantRankingAuthorized",
            "executionAuthorized",
            "publicationAuthorized",
        ):
            _require(entry[key] is False, "registry_authority", "registry entry grants forbidden authority")
        manifest_path = _safe_registry_path(root, entry["manifestPath"], "registry_manifest_path")
        replay_path = _safe_registry_path(root, entry["replayPath"], "registry_replay_path")
        manifest = load_manifest(manifest_path)
        replay = load_replay(replay_path)
        manifest_digest = manifest_sha256(manifest)
        replay_digest = replay_sha256(replay)
        _require(entry["gameId"] == manifest["gameId"], "registry_game", "registry game id drifted")
        _require(entry["version"] == manifest["version"], "registry_version", "registry game version drifted")
        _require(entry["manifestSha256"] == manifest_digest, "registry_manifest_digest", "registry manifest digest drifted")
        _require(entry["replaySha256"] == replay_digest, "registry_replay_digest", "registry replay digest drifted")
        identity = (entry["gameId"], entry["version"])
        _require(identity not in seen, "registry_duplicate", "registry game version is duplicated")
        seen.add(identity)
        report = verify_replay(manifest, replay)
        reports.append(
            {
                "gameId": entry["gameId"],
                "version": entry["version"],
                "manifestSha256": manifest_digest,
                "replaySha256": replay_digest,
                "effectiveVerdict": report["effectiveVerdict"],
                "decision": entry["decision"],
            }
        )
    return {
        "schemaVersion": 1,
        "status": "pass",
        "candidateStatus": REGISTRY_STATUS,
        "entryCount": len(reports),
        "entries": reports,
        "executionAuthorized": False,
        "publicationAuthorized": False,
        "rankingAuthorized": False,
    }


def load_registry(path: os.PathLike[str] | str, source_root: os.PathLike[str] | str) -> dict:
    return validate_registry(_read_json(path, MAX_REGISTRY_BYTES, "registry"), source_root)
