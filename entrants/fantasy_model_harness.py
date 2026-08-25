#!/usr/bin/env python3
"""Model-facing AgentWars fantasy GM with a deterministic legal fallback.

This process, not the referee, owns inference. It never imports ``arena`` and
never receives a transcript path. Raw model output stays inside this process;
the receipt records only its digest and whether the accepted pick came from the
model or the fallback.
"""

import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backends import (  # noqa: E402
    acknowledge_customer_local_v1,
    acknowledge_unsafe_custom_command,
    get_backend,
    get_provider_backend,
)

VERSION = "1"
STRATEGIES = ("win-now", "long-game")
MAX_MODEL_OUTPUT_CHARS = 32768
PROVIDER_CHOICES = (
    "chatgpt_codex",
    "claude_code",
    "opencode",
    "openrouter",
    "hermes",
    "custom_agent",
)


def build_backend(args, parser=None):
    """Resolve the backend exactly once.

    ``--backend`` keeps its historical meaning byte-for-byte when no provider
    is selected, except that non-stub legacy specs now require the explicit
    ``customer_local_v1`` runtime intent capability via ``--customer-local-v1``.
    With ``--provider``, the catalog id selects a provider-backed adapter
    instead; the two flags are mutually exclusive so an invocation can never
    be ambiguous about what answers. ``custom_agent`` requires an explicit
    repeatable JSON argv vector via ``--provider-command`` AND the second
    ``--unsafe-custom-command`` opt-in.
    """
    if args.provider:
        if args.backend:
            _fail(parser, "--backend and --provider are mutually exclusive")
        runtime_intent = (
            acknowledge_customer_local_v1()
            if getattr(args, "customer_local_v1", False)
            else None
        )
        unsafe_custom_command_intent = (
            acknowledge_unsafe_custom_command()
            if getattr(args, "unsafe_custom_command", False)
            else None
        )
        command = None
        if getattr(args, "provider_command", None):
            try:
                command = json.loads(args.provider_command)
            except json.JSONDecodeError:
                _fail(parser, "--provider-command must be a JSON argv array")
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if root not in sys.path:
            sys.path.insert(0, root)
        try:
            return get_provider_backend(
                args.provider,
                model=args.provider_model,
                variant=args.provider_variant,
                command=command,
                timeout_s=args.backend_timeout,
                runtime_intent=runtime_intent,
                unsafe_custom_command_intent=unsafe_custom_command_intent,
            )
        except (ValueError, RuntimeError) as error:
            _fail(parser, str(error))
    if not args.backend:
        _fail(parser, "--backend is required unless --provider is given")
    if any(
        getattr(args, name, None) is not None
        for name in ("provider_model", "provider_variant", "provider_command")
    ):
        _fail(parser, "provider options are valid only with --provider")
    if getattr(args, "unsafe_custom_command", False):
        _fail(parser, "--unsafe-custom-command is valid only with --provider custom_agent")
    runtime_intent = (
        acknowledge_customer_local_v1()
        if getattr(args, "customer_local_v1", False)
        else None
    )
    try:
        return get_backend(
            args.backend,
            timeout_s=args.backend_timeout,
            runtime_intent=runtime_intent,
        )
    except RuntimeError as error:
        _fail(parser, str(error))


def _fail(parser, message):
    if parser is not None:
        parser.error(message)
    raise SystemExit(f"error: {message}")


def send(message):
    sys.stdout.write(json.dumps(message, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def legal_players(observation):
    if not isinstance(observation, dict):
        return []
    needs = observation.get("needs")
    available = observation.get("available_players")
    if not isinstance(needs, dict) or not isinstance(available, list):
        return []
    out = []
    for player in available:
        if not isinstance(player, dict):
            continue
        player_id = player.get("id")
        position = player.get("position")
        if (
            isinstance(player_id, int)
            and not isinstance(player_id, bool)
            and isinstance(position, str)
            and isinstance(needs.get(position), int)
            and not isinstance(needs.get(position), bool)
            and needs[position] > 0
        ):
            out.append(player)
    return out


def fallback_move(observation, strategy):
    players = legal_players(observation)
    if not players:
        return None
    key = "redraft_points" if strategy == "win-now" else "dynasty_points"

    def rank(player):
        value = player.get(key)
        if not isinstance(value, int) or isinstance(value, bool):
            value = -10**9
        peers = sorted(
            (
                row.get(key)
                for row in players
                if row.get("position") == player.get("position")
                and isinstance(row.get(key), int)
                and not isinstance(row.get(key), bool)
            ),
            reverse=True,
        )
        replacement = peers[1] if len(peers) > 1 else 0
        return value * 100 + (value - replacement) * 12, -player["id"]

    return {"player_id": max(players, key=rank)["id"]}


def build_prompt(observation, strategy):
    players = legal_players(observation)
    board = [
        {
            "player_id": row["id"],
            "name": str(row.get("name", ""))[:80],
            "position": row.get("position"),
            "redraft_points": row.get("redraft_points"),
            "dynasty_points": row.get("dynasty_points"),
            "age": row.get("age"),
        }
        for row in players
    ]
    context = {
        "format": observation.get("format"),
        "strategy": strategy,
        "round": observation.get("round"),
        "needs": observation.get("needs"),
        "your_roster": observation.get("your_roster"),
        "opponent_roster": observation.get("opponent_roster"),
        "legal_players": board,
    }
    return (
        "You are an AgentWars fantasy football GM. Pick exactly one legal player "
        f"using the {strategy} strategy. Return ONLY a JSON object with exactly one "
        "key, for example {\"player_id\": 12}. No prose or markdown.\n"
        + json.dumps(context, sort_keys=True, separators=(",", ":"))
    )


def build_repair_prompt(observation, strategy):
    """Build one self-contained, closed-choice repair prompt.

    Each backend invocation is a fresh session, so this prompt never refers to
    a "previous" answer. The rejected response is deliberately absent: it may
    contain secrets or adversarial text, and the fresh call needs only compact
    authoritative context plus the finite set of legal response objects.
    """
    players = legal_players(observation)
    score_key = "redraft_points" if strategy == "win-now" else "dynasty_points"
    candidates = [
        {
            "player_id": row["id"],
            "position": row.get("position"),
            "score": row.get(score_key),
        }
        for row in players
    ]
    context = {
        "format": observation.get("format"),
        "strategy": strategy,
        "round": observation.get("round"),
        "needs": observation.get("needs"),
        "your_roster": observation.get("your_roster"),
        "opponent_roster": observation.get("opponent_roster"),
        "candidates": candidates,
        "allowed_response_objects": [{"player_id": row["id"]} for row in players],
    }
    return (
        "Make one fresh fantasy football draft choice. Do not run commands, use "
        "tools, explain, or add markdown. Select one candidate using strategy and "
        "score. Return exactly one object from allowed_response_objects and nothing "
        "else.\n"
        + json.dumps(context, sort_keys=True, separators=(",", ":"))
    )


def extract_strict_move(raw):
    if not isinstance(raw, str) or not raw or len(raw) > MAX_MODEL_OUTPUT_CHARS:
        return None
    try:
        value = json.loads(raw.strip())
    except json.JSONDecodeError:
        return None
    if not isinstance(value, dict) or set(value) != {"player_id"}:
        return None
    player_id = value["player_id"]
    if not isinstance(player_id, int) or isinstance(player_id, bool):
        return None
    return {"player_id": player_id}


def move_is_legal_for_observation(observation, move):
    if not isinstance(move, dict):
        return False
    legal_ids = {row["id"] for row in legal_players(observation)}
    return move.get("player_id") in legal_ids


def _response_digest(raw):
    if not isinstance(raw, str):
        return None
    return hashlib.sha256(raw.encode("utf-8", errors="surrogatepass")).hexdigest()[:16]


def _rejection_reason(observation, raw):
    move = extract_strict_move(raw)
    if move is None:
        return "invalid_model_output"
    if not move_is_legal_for_observation(observation, move):
        return "illegal_model_move"
    return None


def _note_with_digests(prefix, raw, prior_raw=None):
    parts = [prefix]
    response_hash = _response_digest(raw)
    prior_hash = _response_digest(prior_raw)
    if response_hash is not None:
        parts.append(f"response_sha256={response_hash}")
    if prior_hash is not None:
        parts.append(f"prior_response_sha256={prior_hash}")
    return ";".join(parts)


def decide(observation, strategy, backend):
    prompt = build_prompt(observation, strategy)
    try:
        raw = backend.complete(prompt)
    except Exception as error:
        move = fallback_move(observation, strategy)
        return move, (
            "source=fallback;"
            f"reason=backend_error:{error.__class__.__name__};attempts=1"
        )

    reason = _rejection_reason(observation, raw)
    if reason is None:
        prefix = (
            "source=model"
            if getattr(backend, "kind", None) == "stub"
            else "source=model;attempts=1"
        )
        return extract_strict_move(raw), _note_with_digests(
            prefix, raw
        )

    # Keep deterministic preseason fixture receipts byte-stable. The stub is a
    # reproducible pseudo-model, not a live provider whose formatting can
    # benefit from a second inference call.
    if getattr(backend, "kind", None) == "stub":
        move = fallback_move(observation, strategy)
        return move, _note_with_digests(
            f"source=fallback;reason={reason}", raw
        )

    try:
        repair_raw = backend.complete(build_repair_prompt(observation, strategy))
    except Exception as error:
        move = fallback_move(observation, strategy)
        return move, _note_with_digests(
            "source=fallback;"
            f"reason=repair_backend_error:{error.__class__.__name__};"
            f"initial_reason={reason};attempts=2",
            None,
            prior_raw=raw,
        )

    repair_reason = _rejection_reason(observation, repair_raw)
    if repair_reason is None:
        return extract_strict_move(repair_raw), _note_with_digests(
            "source=model;attempts=2", repair_raw, prior_raw=raw
        )

    move = fallback_move(observation, strategy)
    return move, _note_with_digests(
        f"source=fallback;reason={repair_reason};attempts=2",
        repair_raw,
        prior_raw=raw,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--backend", default=None,
        help="entrant-side backend spec, e.g. stub:v1 or cli:claude -p",
    )
    parser.add_argument(
        "--provider", choices=PROVIDER_CHOICES, default=None,
        help="BuildWars provider catalog id; mutually exclusive with --backend",
    )
    parser.add_argument("--provider-model", default=None)
    parser.add_argument("--provider-variant", default=None)
    parser.add_argument(
        "--provider-command", default=None,
        help="custom_agent only: explicit repeatable JSON argv array",
    )
    parser.add_argument(
        "--customer-local-v1", action="store_true", dest="customer_local_v1",
        help="pass the customer_local_v1 runtime intent capability, required "
             "before any provider adapter or non-stub legacy backend can be "
             "constructed; records intent only and is NOT an OS isolation "
             "boundary",
    )
    parser.add_argument(
        "--unsafe-custom-command", action="store_true",
        dest="unsafe_custom_command",
        help="custom_agent only: second explicit opt-in; without it default "
             "construction fails before subprocess resolution",
    )
    parser.add_argument("--backend-timeout", type=float, default=None)
    parser.add_argument("--strategy", choices=STRATEGIES, required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    backend = build_backend(args, parser)

    for line in sys.stdin:
        if not line.strip():
            continue
        message = json.loads(line)
        if message.get("type") == "hello":
            send(
                {
                    "type": "ready",
                    "entrant": args.name,
                    "version": VERSION,
                    "backend": backend.label,
                }
            )
        elif message.get("type") == "move_request":
            move, note = decide(message.get("observation"), args.strategy, backend)
            send({"type": "move", "move": move, "note": note})
        elif message.get("type") == "goodbye":
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
