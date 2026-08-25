#!/usr/bin/env python3
"""Fixed fantasy plan entrant: executes one immutable model-derived ranking.

This is not live inference and is not model attestation. An Ox Alpha MAX worker
produced a fixed draft ranking from an immutable fictional board; that ranking
is shipped as a strict, hash-bound artifact. This process validates the
artifact and the referee's every observation, then plays the ranking
deterministically. It never imports ``arena``, never touches a network,
subprocess, environment value, secret, or dynamic import, and never improvises:
any mismatch returns a controlled forfeit instead of a fallback pick.

Source claims stay claims. ``terminalTextSha256`` claims the digest of the
complete terminal text the worker saw; this harness cannot see that text and
never verifies it. One real terminal response was pure JSON; another carried
the minified plan on line 1 plus controller-mandated receipt prose afterwards,
so ``planLineNumber`` records the exact source line (always 1) and
``terminalTextExactPlan`` states whether the full text equaled the plan.
``planLineSha256`` is the one digest verified here: it must equal the SHA-256
of ``rawPlan``, which must itself strict-parse and minified-round-trip exactly.
"""

import argparse
import hashlib
import json
import os
import re
import stat
import sys

VERSION = "1"
BACKEND_LABEL = "fixed-model-plan:v1"

MAX_PLAN_BYTES = 64 * 1024
MAX_PATH_CHARS = 4096

ARTIFACT_SCHEMA = "agentwars.fantasy_plan_artifact.v1"
PLAN_SCHEMA = "agentwars.fantasy_draft_plan.v1"
PROTOCOL = "arena/1"
EXPECTED_GAME = "fantasy_redraft"
EXPECTED_FORMAT = "redraft"
EXPECTED_SEED = 9300
MODEL_CLAIM = "ox-alpha-free"
REASONING_EFFORT = "max"
MAX_TOKENS = 131072
ROUTE = "opencode-go"

MIN_TIMEOUT_MS = 1
MAX_TIMEOUT_MS = 3600000

ARTIFACT_KEYS = frozenset({"schema", "source", "board", "rawPlan"})
SOURCE_KEYS = frozenset(
    {
        "runId",
        "receiptSha256",
        "terminalTextSha256",
        "planLineSha256",
        "planLineNumber",
        "terminalTextExactPlan",
        "modelClaim",
        "reasoningEffort",
        "maxTokens",
        "fallbacksAllowed",
        "route",
    }
)
PLAN_KEYS = frozenset({"schema", "game", "seed", "strategy", "ranking"})

BOARD_SIZE = 20
BOARD_ROW_KEYS = frozenset(
    {"id", "name", "position", "redraft_points", "dynasty_points", "age"}
)
POSITION_LIMITS = {"QB": 1, "RB": 2, "WR": 2, "TE": 1}
TOTAL_PICKS = sum(POSITION_LIMITS.values()) * 2

OBSERVATION_KEYS = frozenset(
    {
        "game",
        "format",
        "rules",
        "you_are",
        "to_move",
        "turn",
        "round",
        "needs",
        "your_roster",
        "opponent_roster",
        "available_players",
    }
)

HELLO_KEYS = frozenset(
    {
        "type",
        "protocol",
        "match_id",
        "you_are",
        "game",
        "game_version",
        "rules",
        "move_timeout_ms",
    }
)
MOVE_REQUEST_KEYS = frozenset(
    {"type", "turn", "you_are", "observation", "move_timeout_ms"}
)
GOODBYE_KEYS = frozenset({"type", "result"})

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


class PlanArtifactError(Exception):
    """A short, public rejection code; never carries plan contents."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


class _StrictJsonError(Exception):
    """Internal marker for duplicate keys or non-finite JSON constants."""


def _has_control_or_surrogate(text):
    return any(
        ord(ch) < 0x20 or ord(ch) == 0x7F or 0xD800 <= ord(ch) <= 0xDFFF for ch in text
    )


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _pairs_without_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise _StrictJsonError("duplicate_key")
        result[key] = value
    return result


def _reject_constant(_name):
    raise _StrictJsonError("non_finite_constant")


def _parse_strict(text):
    return json.loads(
        text,
        object_pairs_hook=_pairs_without_duplicates,
        parse_constant=_reject_constant,
    )


def _parse_strict_artifact(text, code):
    try:
        return _parse_strict(text)
    except (_StrictJsonError, RecursionError, ValueError):
        raise PlanArtifactError(code) from None


def _ban_floats(value):
    if isinstance(value, float):
        raise PlanArtifactError("plan_float_forbidden")
    if isinstance(value, dict):
        for nested in value.values():
            _ban_floats(nested)
    elif isinstance(value, list):
        for nested in value:
            _ban_floats(nested)


def read_plan_text(path):
    """Read the plan bytes without following a final symlink, fail-closed."""
    if not isinstance(path, str) or not path or len(path) > MAX_PATH_CHARS:
        raise PlanArtifactError("plan_path_invalid")
    try:
        pre = os.lstat(path)
    except FileNotFoundError:
        raise PlanArtifactError("plan_not_found") from None
    except OSError:
        raise PlanArtifactError("plan_not_readable") from None
    if stat.S_ISLNK(pre.st_mode):
        raise PlanArtifactError("plan_is_symlink")
    if not stat.S_ISREG(pre.st_mode):
        raise PlanArtifactError("plan_not_regular")
    if pre.st_nlink > 1:
        raise PlanArtifactError("plan_multi_linked")
    if pre.st_size == 0:
        raise PlanArtifactError("plan_empty")
    if pre.st_size > MAX_PLAN_BYTES:
        raise PlanArtifactError("plan_oversized")
    parent = os.path.dirname(os.path.abspath(path))
    real_parent = os.path.dirname(os.path.realpath(path))
    if os.path.normcase(real_parent) != os.path.normcase(parent):
        raise PlanArtifactError("plan_parent_redirect")

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        raise PlanArtifactError("plan_open_failed") from None
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            raise PlanArtifactError("plan_not_regular")
        if opened.st_nlink > 1:
            raise PlanArtifactError("plan_multi_linked")
        if (opened.st_dev, opened.st_ino) != (pre.st_dev, pre.st_ino):
            raise PlanArtifactError("plan_identity_changed")
        if opened.st_size != pre.st_size:
            raise PlanArtifactError("plan_size_changed")
        chunks = []
        total = 0
        while True:
            block = os.read(fd, 65536)
            if not block:
                break
            chunks.append(block)
            total += len(block)
            if total > MAX_PLAN_BYTES:
                raise PlanArtifactError("plan_oversized")
        flushed = os.fstat(fd)
        identity_stable = (flushed.st_dev, flushed.st_ino) == (pre.st_dev, pre.st_ino)
        if not identity_stable or flushed.st_size != total or total != pre.st_size:
            raise PlanArtifactError("plan_changed_during_read")
    finally:
        os.close(fd)

    # Post-read boundary check: the path must still name the same regular,
    # single-link file of the same size it named before the open/read cycle.
    try:
        post = os.lstat(path)
    except OSError:
        raise PlanArtifactError("plan_post_lstat_failed") from None
    if not stat.S_ISREG(post.st_mode):
        raise PlanArtifactError("plan_not_regular_after_read")
    if post.st_nlink > 1:
        raise PlanArtifactError("plan_multi_linked_after_read")
    if (post.st_dev, post.st_ino) != (pre.st_dev, pre.st_ino):
        raise PlanArtifactError("plan_identity_changed_after_read")
    if post.st_size != total:
        raise PlanArtifactError("plan_size_changed_after_read")

    data = b"".join(chunks)
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise PlanArtifactError("plan_invalid_utf8") from None


_ROW_FIELD_KIND_CODES = {
    "id": "board_player_id",
    "name": "board_name",
    "position": "board_position",
    "points": "board_points",
    "age": "board_age",
}


def _row_field_kind(row):
    """Semantic kind of the first strictly invalid board-row field, else None."""
    if not _is_int(row["id"]) or not 1 <= row["id"] <= 2147483647:
        return "id"
    name = row["name"]
    if (
        not isinstance(name, str)
        or not 1 <= len(name) <= 80
        or _has_control_or_surrogate(name)
    ):
        return "name"
    if not isinstance(row["position"], str) or row["position"] not in POSITION_LIMITS:
        return "position"
    for key in ("redraft_points", "dynasty_points"):
        value = row[key]
        if not _is_int(value) or not -100000 <= value <= 100000:
            return "points"
    if not _is_int(row["age"]) or not 1 <= row["age"] <= 200:
        return "age"
    return None


def _validate_board(board):
    if not isinstance(board, list) or len(board) != BOARD_SIZE:
        raise PlanArtifactError("board_shape")
    rows = []
    seen_ids = set()
    counts = {position: 0 for position in POSITION_LIMITS}
    for row in board:
        if not isinstance(row, dict) or set(row) != set(BOARD_ROW_KEYS):
            raise PlanArtifactError("board_row_keys")
        kind = _row_field_kind(row)
        if kind is not None:
            raise PlanArtifactError(_ROW_FIELD_KIND_CODES[kind])
        player_id = row["id"]
        if player_id in seen_ids:
            raise PlanArtifactError("board_duplicate_id")
        seen_ids.add(player_id)
        counts[row["position"]] += 1
        rows.append(dict(row))
    # Both seats must be able to finish legal rosters from this board alone.
    for position, limit in POSITION_LIMITS.items():
        if counts[position] < 2 * limit:
            raise PlanArtifactError("board_position_counts_infeasible")
    return rows


def load_artifact(path):
    """Validate the full plan artifact and return its trusted projection."""
    text = read_plan_text(path)
    value = _parse_strict_artifact(text, "plan_invalid_json")
    _ban_floats(value)
    if not isinstance(value, dict):
        raise PlanArtifactError("plan_not_object")
    if set(value) != set(ARTIFACT_KEYS):
        raise PlanArtifactError("plan_unexpected_keys")
    if value["schema"] != ARTIFACT_SCHEMA:
        raise PlanArtifactError("plan_bad_schema")

    source = value["source"]
    if not isinstance(source, dict) or set(source) != set(SOURCE_KEYS):
        raise PlanArtifactError("source_bad_keys")
    run_id = source["runId"]
    if not isinstance(run_id, str) or _UUID_RE.fullmatch(run_id) is None:
        raise PlanArtifactError("source_run_id")
    receipt_sha = source["receiptSha256"]
    if not isinstance(receipt_sha, str) or _HEX64_RE.fullmatch(receipt_sha) is None:
        raise PlanArtifactError("source_receipt_sha")
    # Claim only: describes the full terminal text, which is never visible here.
    terminal_text_sha = source["terminalTextSha256"]
    if (
        not isinstance(terminal_text_sha, str)
        or _HEX64_RE.fullmatch(terminal_text_sha) is None
    ):
        raise PlanArtifactError("source_terminal_text_sha")
    # Verified below against rawPlan itself.
    plan_line_sha = source["planLineSha256"]
    if not isinstance(plan_line_sha, str) or _HEX64_RE.fullmatch(plan_line_sha) is None:
        raise PlanArtifactError("source_plan_line_sha")
    plan_line_number = source["planLineNumber"]
    if not _is_int(plan_line_number) or plan_line_number != 1:
        raise PlanArtifactError("source_plan_line_number")
    terminal_exact_plan = source["terminalTextExactPlan"]
    if not isinstance(terminal_exact_plan, bool):
        raise PlanArtifactError("source_terminal_exact_plan")
    if source["modelClaim"] != MODEL_CLAIM:
        raise PlanArtifactError("source_model_claim")
    if source["reasoningEffort"] != REASONING_EFFORT:
        raise PlanArtifactError("source_reasoning_effort")
    if source["maxTokens"] != MAX_TOKENS or not _is_int(source["maxTokens"]):
        raise PlanArtifactError("source_max_tokens")
    if source["fallbacksAllowed"] is not False:
        raise PlanArtifactError("source_fallbacks_allowed")
    if source["route"] != ROUTE:
        raise PlanArtifactError("source_route")

    rows = _validate_board(value["board"])

    raw_plan = value["rawPlan"]
    if not isinstance(raw_plan, str) or not raw_plan:
        raise PlanArtifactError("raw_plan_not_string")
    computed_plan_sha = hashlib.sha256(raw_plan.encode("utf-8")).hexdigest()
    if computed_plan_sha != plan_line_sha:
        raise PlanArtifactError("raw_plan_digest_mismatch")
    parsed = _parse_strict_artifact(raw_plan, "raw_plan_invalid_json")
    _ban_floats(parsed)
    if not isinstance(parsed, dict) or set(parsed) != set(PLAN_KEYS):
        raise PlanArtifactError("raw_plan_bad_keys")
    if parsed["schema"] != PLAN_SCHEMA:
        raise PlanArtifactError("raw_plan_schema")
    if parsed["game"] != EXPECTED_GAME:
        raise PlanArtifactError("raw_plan_game")
    if parsed["seed"] != EXPECTED_SEED or not _is_int(parsed["seed"]):
        raise PlanArtifactError("raw_plan_seed")
    strategy = parsed["strategy"]
    if (
        not isinstance(strategy, str)
        or not 1 <= len(strategy) <= 500
        or _has_control_or_surrogate(strategy)
    ):
        raise PlanArtifactError("raw_plan_strategy")
    ranking = parsed["ranking"]
    if not isinstance(ranking, list) or len(ranking) != len(rows):
        raise PlanArtifactError("raw_plan_ranking_shape")
    board_ids = {row["id"] for row in rows}
    seen_ranked = set()
    for player_id in ranking:
        if not _is_int(player_id) or player_id not in board_ids:
            raise PlanArtifactError("raw_plan_ranking_entry")
        if player_id in seen_ranked:
            raise PlanArtifactError("raw_plan_ranking_duplicate")
        seen_ranked.add(player_id)
    # Minified and canonical: byte-round-trips through its own parse with no
    # insignificant whitespace and no redundant escapes.
    try:
        canonical = json.dumps(
            parsed, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        )
    except (ValueError, UnicodeEncodeError):
        raise PlanArtifactError("raw_plan_not_canonical") from None
    if raw_plan != canonical:
        raise PlanArtifactError("raw_plan_not_canonical")

    return {
        "artifact_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "plan_sha256": computed_plan_sha,
        "run_id": run_id,
        "receipt_sha256": receipt_sha,
        "strategy": strategy,
        "rows_by_id": {row["id"]: row for row in rows},
        "ranking": list(ranking),
    }


def seat_for_turn(turn):
    round_index, pick_in_round = divmod(turn, 2)
    return pick_in_round if round_index % 2 == 0 else 1 - pick_in_round


def picks_assigned_before(turn):
    picks = [0, 0]
    for earlier_turn in range(turn):
        picks[seat_for_turn(earlier_turn)] += 1
    return picks


class PlanSession:
    """One seat's validated view of the match, driven only by its artifact."""

    def __init__(self, artifact, seat):
        self.rows_by_id = artifact["rows_by_id"]
        self.ranking = artifact["ranking"]
        self.seat = seat
        self.last_turn = None

    def handle_move_request(self, message):
        observation = message.get("observation") if isinstance(message, dict) else None
        reason = self._validate(message, observation)
        if reason is not None:
            return None, reason
        move = self._choose(observation)
        if move is None:
            return None, "no_ranked_legal_player"
        return move, None

    def _validate(self, message, observation):
        if set(message) != MOVE_REQUEST_KEYS:
            return "bad_request_shape"
        timeout_ms = message["move_timeout_ms"]
        if not _is_int(timeout_ms) or not MIN_TIMEOUT_MS <= timeout_ms <= MAX_TIMEOUT_MS:
            return "bad_timeout"
        if not isinstance(observation, dict) or set(observation) != set(OBSERVATION_KEYS):
            return "bad_observation_shape"
        if observation["game"] != EXPECTED_GAME:
            return "bad_game"
        if observation["format"] != EXPECTED_FORMAT:
            return "bad_format"
        rules = observation["rules"]
        if (
            not isinstance(rules, str)
            or not rules
            or len(rules) > 2000
            or _has_control_or_surrogate(rules)
        ):
            return "bad_rules"
        for claimed_seat in (message.get("you_are"), observation["you_are"], observation["to_move"]):
            if not _is_int(claimed_seat) or claimed_seat != self.seat:
                return "bad_seat"
        turn = observation["turn"]
        if not _is_int(turn) or not 0 <= turn < TOTAL_PICKS:
            return "bad_turn"
        request_turn = message.get("turn")
        if not _is_int(request_turn) or request_turn != turn:
            return "bad_turn_mismatch"
        if seat_for_turn(turn) != self.seat:
            return "bad_turn_seat"
        if observation["round"] != turn // 2 + 1 or not _is_int(observation["round"]):
            return "bad_round"
        if self.last_turn is not None and turn <= self.last_turn:
            return "bad_turn_order"

        needs = observation["needs"]
        if not isinstance(needs, dict) or set(needs) != set(POSITION_LIMITS):
            return "bad_needs_shape"
        for position, remaining in needs.items():
            if not _is_int(remaining) or not 0 <= remaining <= POSITION_LIMITS[position]:
                return "bad_needs_value"

        available_rows = observation["available_players"]
        if not isinstance(available_rows, list):
            return "bad_available_shape"
        available_ids = []
        for row in available_rows:
            if not isinstance(row, dict) or set(row) != set(BOARD_ROW_KEYS):
                return "bad_row_shape"
            player_id = row["id"]
            if not _is_int(player_id) or player_id not in self.rows_by_id:
                return "unknown_player"
            if _row_field_kind(row) is not None or row != self.rows_by_id[player_id]:
                return "row_mismatch"
            available_ids.append(player_id)
        if len(set(available_ids)) != len(available_ids):
            return "duplicate_available_id"

        rosters = {}
        for label, value in (("your_roster", observation["your_roster"]),
                             ("opponent_roster", observation["opponent_roster"])):
            if not isinstance(value, list):
                return f"bad_{label}"
            for player_id in value:
                if not _is_int(player_id) or player_id not in self.rows_by_id:
                    return "unknown_roster_player"
            if len(set(value)) != len(value):
                return f"duplicate_{label}_id"
            rosters[label] = value

        combined = available_ids + rosters["your_roster"] + rosters["opponent_roster"]
        if len(combined) != len(self.rows_by_id) or set(combined) != set(self.rows_by_id):
            return "bad_partition"

        # Each roster must be exactly as long as the number of picks the snake
        # schedule actually assigned that seat before this turn — a partition
        # alone could still hide a shifted or skipped pick.
        expected_lengths = picks_assigned_before(turn)
        if len(rosters["your_roster"]) != expected_lengths[self.seat]:
            return "bad_your_roster_length"
        if len(rosters["opponent_roster"]) != expected_lengths[1 - self.seat]:
            return "bad_opponent_roster_length"

        counts = {position: 0 for position in POSITION_LIMITS}
        for player_id in rosters["your_roster"]:
            counts[self.rows_by_id[player_id]["position"]] += 1
        expected_needs = {
            position: POSITION_LIMITS[position] - counts[position]
            for position in POSITION_LIMITS
        }
        if any(needs[position] != expected_needs[position] for position in POSITION_LIMITS):
            return "needs_mismatch"

        self.last_turn = turn
        return None

    def _choose(self, observation):
        needs = observation["needs"]
        available = {row["id"] for row in observation["available_players"]}
        for player_id in self.ranking:
            if player_id not in available:
                continue
            position = self.rows_by_id[player_id]["position"]
            if needs[position] > 0:
                return {"player_id": player_id}
        return None


def send(message):
    sys.stdout.write(json.dumps(message, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Execute one fixed model-plan fantasy artifact deterministically."
    )
    parser.add_argument("--plan", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args(argv)
    name = args.name
    if not isinstance(name, str) or not name.strip() or len(name) > 120:
        sys.stderr.write("error: bad_entrant_name\n")
        return 2

    try:
        artifact = load_artifact(args.plan)
    except PlanArtifactError as error:
        sys.stderr.write(f"error: {error.code}\n")
        return 2

    note_prefix = (
        "source=model_plan"
        f";plan_sha256={artifact['plan_sha256']}"
        f";ox_run_id={artifact['run_id']}"
        f";ox_receipt_sha256={artifact['receipt_sha256']}"
    )
    ready_sent = False
    session = None
    try:
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                message = _parse_strict(line)
            except (_StrictJsonError, RecursionError, ValueError):
                sys.stderr.write("error: malformed_protocol_json\n")
                return 2
            if not isinstance(message, dict):
                sys.stderr.write("error: malformed_protocol_message\n")
                return 2
            kind = message.get("type")
            if kind == "hello":
                if ready_sent:
                    sys.stderr.write("error: duplicate_hello\n")
                    return 2
                if set(message) != HELLO_KEYS:
                    sys.stderr.write("error: bad_handshake_shape\n")
                    return 2
                if message["protocol"] != PROTOCOL:
                    sys.stderr.write("error: bad_protocol\n")
                    return 2
                seat = message["you_are"]
                if not _is_int(seat) or seat not in (0, 1):
                    sys.stderr.write("error: bad_handshake\n")
                    return 2
                if message["game"] != EXPECTED_GAME:
                    sys.stderr.write("error: wrong_game\n")
                    return 2
                game_version = message["game_version"]
                if (
                    not isinstance(game_version, str)
                    or not game_version
                    or len(game_version) > 120
                    or _has_control_or_surrogate(game_version)
                ):
                    sys.stderr.write("error: bad_game_version\n")
                    return 2
                rules = message["rules"]
                if (
                    not isinstance(rules, str)
                    or not rules
                    or len(rules) > 2000
                    or _has_control_or_surrogate(rules)
                ):
                    sys.stderr.write("error: bad_rules\n")
                    return 2
                match_id = message["match_id"]
                if (
                    not isinstance(match_id, str)
                    or not match_id
                    or len(match_id) > 80
                    or _has_control_or_surrogate(match_id)
                ):
                    sys.stderr.write("error: bad_match_id\n")
                    return 2
                timeout_ms = message["move_timeout_ms"]
                if not _is_int(timeout_ms) or not MIN_TIMEOUT_MS <= timeout_ms <= MAX_TIMEOUT_MS:
                    sys.stderr.write("error: bad_timeout\n")
                    return 2
                ready_sent = True
                session = PlanSession(artifact, seat)
                send(
                    {
                        "type": "ready",
                        "entrant": name,
                        "version": VERSION,
                        "backend": BACKEND_LABEL,
                        "artifact_sha256": artifact["artifact_sha256"],
                        "plan_sha256": artifact["plan_sha256"],
                        "ox_run_id": artifact["run_id"],
                        "ox_receipt_sha256": artifact["receipt_sha256"],
                    }
                )
            elif kind == "move_request":
                if session is None:
                    sys.stderr.write("error: move_before_hello\n")
                    return 2
                move, reason = session.handle_move_request(message)
                note = note_prefix if reason is None else f"{note_prefix};reason={reason}"
                send({"type": "move", "move": move, "note": note})
            elif kind == "goodbye":
                if not ready_sent or set(message) != GOODBYE_KEYS:
                    sys.stderr.write("error: bad_goodbye_sequence\n")
                    return 2
                return 0
            else:
                sys.stderr.write("error: unknown_message_type\n")
                return 2
        return 0
    except Exception:
        sys.stderr.write("error: internal_failure\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
