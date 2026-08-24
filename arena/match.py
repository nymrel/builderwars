"""The match runner.

Owns the referee, the two entrant processes, and the transcript. Nothing else in
the system is allowed to write a record.

Three properties this file is built to hold:

  1. The referee is the only thing that touches state. An entrant's message is
     read for exactly one key, `move`, which is checked against the rules before
     it can change anything.
  2. Everything that decided the outcome is committed to a hash chain as it
     happens, including the engine's own source digest.
  3. Nothing in here opens a network connection, reads a credential, or knows
     what a model is. Inference, if any, happens on the far side of a pipe, at
     the entrant's own expense.
"""

import json
import os
import random
import re
import shutil
import time

from .canonical import digest
from .games import load as load_game
from .integrity import engine_digest, engine_files, script_digest
from .sandbox import POLICY, Entrant, EntrantFailure
from .scoring import referee_projection, score
from .transcript import TranscriptWriter

PROTOCOL = "arena/1"
EXECUTION_CLAIMS = frozenset({"scripted", "model", "hybrid"})
_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_MATCH_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")
_WINDOWS_DEVICE_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{number}" for number in range(1, 10)}
    | {f"LPT{number}" for number in range(1, 10)}
)
_MANIFEST_KEYS = frozenset(
    {"name", "cmd", "env", "claimed_model", "execution_claim", "agent_passport"}
)
_PASSPORT_PATH_MAX = 4096


def _seat_passport(manifest, seat):
    """Load and fully verify an optional seat passport BEFORE any process starts.

    The passport file is untrusted input: schema, bounds, encodings, ID
    derivation, and the Ed25519 signature are all checked here, fail-closed.
    The engine then performs a preflight binding: the passport's harnessSha256
    must equal this engine's digest of the script path it is preparing to run
    for that seat. On a self-hosted runner this does not attest that the host
    could not swap bytes during execution. A signature never attests the model,
    runtime, person, or host behind the key — only that the key holder signed
    this version declaration (see arena.passport.PROOF_SCOPE).
    """
    path = manifest.get("agent_passport")
    if path is None:
        return None
    if not isinstance(path, str) or not path or len(path) > _PASSPORT_PATH_MAX:
        raise ValueError("entrant agent_passport must be a non-empty path of at most 4096 characters")
    try:
        from . import passport as passport_contract

        record = passport_contract.verify_passport_file(path)
    except ValueError as e:
        raise ValueError(f"seat {seat}: invalid entrant passport ({e})") from e
    actual = script_digest(manifest["cmd"])
    if not isinstance(actual, dict) or actual.get("sha256") != record["harnessSha256"]:
        raise ValueError(
            f"seat {seat}: passport harnessSha256 does not match the engine's digest of "
            "the entrant script for that seat; refusing to start play"
        )
    if record["displayName"] != manifest["name"]:
        raise ValueError(
            f"seat {seat}: passport displayName must exactly match the entrant manifest name"
        )
    if record["claimedModel"] != manifest.get("claimed_model"):
        raise ValueError(
            f"seat {seat}: passport claimedModel must exactly match the manifest's "
            "self-declared claimed_model"
        )
    return record


class _Sidecar:
    """Timing and stderr, deliberately OUTSIDE the hash chain.

    Latency and captured stderr vary between two runs of the same match on the
    same inputs. Committing them would mean a re-run never reproduces the
    original chain head, which would cost the engine its strongest property for
    the sake of two diagnostic fields. They are written here instead: useful,
    inspectable, and explicitly not part of what a result rests on.
    """

    def __init__(self, path):
        self.path = path
        self._fh = open(path, "w", encoding="utf-8", newline="\n")
        self._fh.write(
            json.dumps({"kind": "notice", "authoritative": False,
                        "note": "diagnostics only; not hashed, not scored"}) + "\n"
        )

    def write(self, kind, **fields):
        self._fh.write(json.dumps({"kind": kind, **fields}, ensure_ascii=False) + "\n")
        self._fh.flush()

    def close(self):
        if not self._fh.closed:
            self._fh.close()


def match_id_for(game_name, seed, entrant_names, passport_version_ids=None):
    """Content-addressed id: same matchup and seed, same id.

    The two-argument legacy form returns exactly the historical id. Supplying
    passport_version_ids folds stable signed version IDs into the preimage, so
    the same names/seed under different agent versions get different ids.
    """
    payload = {"game": game_name, "seed": seed, "entrants": list(entrant_names)}
    if passport_version_ids is not None:
        payload["passportVersionIds"] = list(passport_version_ids)
    return digest(payload)[:16]


def validate_match_id(value):
    """Validate an identifier before it can participate in an output path."""
    if not isinstance(value, str) or _MATCH_ID.fullmatch(value) is None:
        raise ValueError(
            "match_id must be 1-80 ASCII letters, digits, underscores, or hyphens "
            "and must start with a letter or digit"
        )
    if value.upper() in _WINDOWS_DEVICE_NAMES:
        raise ValueError("match_id must not be a reserved Windows device name")
    return value


def _manifest_digest(manifest, verified_passport=None):
    # Hash names only. Values of declared env vars are never read here.
    body = {
        "name": manifest["name"],
        "cmd": list(manifest["cmd"]),
        "env": sorted(manifest.get("env", [])),
        "claimed_model": manifest.get("claimed_model"),
        "execution_claim": manifest["execution_claim"],
    }
    if verified_passport is not None:
        # Bind identity by content (key-derived IDs and the signed declaration),
        # never by filesystem path, so equal passports hash equally.
        body["agent_passport"] = verified_passport
    return digest(body)


def validate_manifest(manifest):
    """Reject ambiguous entrant declarations before starting either process."""
    if not isinstance(manifest, dict):
        raise ValueError("entrant manifest must be an object")
    unexpected = set(manifest) - _MANIFEST_KEYS
    if unexpected:
        raise ValueError(f"entrant manifest has unexpected keys: {sorted(unexpected)}")
    name = manifest.get("name")
    if not isinstance(name, str) or not name.strip() or len(name) > 120:
        raise ValueError("entrant name must be a non-empty string of at most 120 characters")
    cmd = manifest.get("cmd")
    if not isinstance(cmd, list) or not cmd or any(not isinstance(part, str) or not part for part in cmd):
        raise ValueError("entrant cmd must be a non-empty array of non-empty strings")
    env = manifest.get("env", [])
    if not isinstance(env, list) or any(not isinstance(key, str) or not _ENV_NAME.fullmatch(key) for key in env):
        raise ValueError("entrant env must contain environment-variable names only")
    if len(env) != len(set(env)):
        raise ValueError("entrant env names must be unique")
    claimed_model = manifest.get("claimed_model")
    if claimed_model is not None and (not isinstance(claimed_model, str) or not claimed_model.strip()):
        raise ValueError("claimed_model must be null or a non-empty string")
    if manifest.get("execution_claim") not in EXECUTION_CLAIMS:
        raise ValueError(
            "execution_claim must be exactly one of: " + ", ".join(sorted(EXECUTION_CLAIMS))
        )
    return manifest


def run_match(
    *,
    game_name,
    seed,
    entrants,
    out_dir,
    move_timeout_s=15.0,
    match_id=None,
    keep_scratch=False,
):
    if len(entrants) != 2:
        raise ValueError("this runner plays two-seat games; got %d entrants" % len(entrants))
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an int so it can be canonically encoded")
    for manifest in entrants:
        validate_manifest(manifest)
    if entrants[0]["name"].casefold() == entrants[1]["name"].casefold():
        raise ValueError("entrant names must be unique within a match")

    # Identity before play: every supplied passport is verified and bound to the
    # actual script digest for its seat before either process can start.
    passports = [_seat_passport(manifest, seat) for seat, manifest in enumerate(entrants)]
    signed_agent_ids = [passport["agentId"] for passport in passports if passport is not None]
    if len(signed_agent_ids) != len(set(signed_agent_ids)):
        raise ValueError("the same signed agentId cannot occupy both seats in one match")

    game = load_game(game_name)
    if match_id is not None:
        selected_match_id = match_id
    elif any(passports):
        # Version-aware id: same names/seed with different signed versions must
        # not collide. Legacy seats contribute null so mixed pairs stay stable.
        selected_match_id = match_id_for(
            game_name,
            seed,
            [e["name"] for e in entrants],
            passport_version_ids=[p["versionId"] if p else None for p in passports],
        )
    else:
        selected_match_id = match_id_for(game_name, seed, [e["name"] for e in entrants])
    mid = validate_match_id(selected_match_id)
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    transcript_path = os.path.join(out_dir, f"{mid}.jsonl")
    sidecar_path = os.path.join(out_dir, f"{mid}.diagnostics.jsonl")
    scratch_root = os.path.join(out_dir, f".scratch-{mid}")

    procs = []
    tw = TranscriptWriter(transcript_path)
    side = _Sidecar(sidecar_path)
    try:
        # -- header: commit to the rules before a move is played -----------
        tw.append(
            "header",
            {
                "protocol": PROTOCOL,
                "match_id": mid,
                "game": {"name": game.NAME, "version": game.VERSION, "summary": game.SUMMARY},
                "seed": seed,
                "engine": {"digest": engine_digest(), "files": engine_files()},
                "entrants": [
                    {
                        "seat": i,
                        "name": e["name"],
                        "manifest_digest": _manifest_digest(e, passports[i]),
                        "script": script_digest(e["cmd"]),
                        "declared_env": sorted(e.get("env", [])),
                        # An entrant's statement about which model it uses. Recorded
                        # as a claim. The engine cannot and does not verify it.
                        "claimed_model": e.get("claimed_model"),
                        # Also self-declared. Bound into the receipt so a scripted
                        # entrant cannot be relabelled after the match.
                        "execution_claim": e["execution_claim"],
                        **(
                            # Engine-verified signed identity. Present only when a
                            # passport was supplied; its absence is the legacy shape.
                            {"agent_passport": passports[i]}
                            if passports[i] is not None
                            else {}
                        ),
                    }
                    for i, e in enumerate(entrants)
                ],
                "sandbox_policy": POLICY,
                "attestation": {
                    "model_attested": False,
                    "execution_claims_attested": False,
                    "reason": (
                        "The engine never contacts a model, so it cannot witness which model "
                        "produced a move. Entrant execution classes are self-declared and bound "
                        "into the receipt. Replay proves rule compliance and adjudication "
                        "integrity, not model identity or execution provenance."
                    ),
                },
                "limits": {"move_timeout_ms": int(move_timeout_s * 1000)},
            },
        )

        # -- start entrants -------------------------------------------------
        for i, manifest in enumerate(entrants):
            workdir = os.path.join(scratch_root, f"seat{i}")
            p = Entrant(manifest, workdir, move_timeout_s=move_timeout_s)
            procs.append(p)

        state = game.setup(random.Random(seed))
        bound = game.move_bound(state)

        outcome = None  # set by forfeit or by the game ending

        for i, p in enumerate(procs):
            try:
                p.start()
                reply = p.ask(
                    {
                        "type": "hello",
                        "protocol": PROTOCOL,
                        "match_id": mid,
                        "you_are": i,
                        "game": game.NAME,
                        "game_version": game.VERSION,
                        "rules": game.RULES if hasattr(game, "RULES") else game.SUMMARY,
                        "move_timeout_ms": int(move_timeout_s * 1000),
                    }
                )
                if reply.get("type") != "ready":
                    raise EntrantFailure("not_ready", f"expected type=ready, got {reply.get('type')!r}")
                tw.append("ready", {"player": i, "entrant_message": _safe(reply)})
            except EntrantFailure as f:
                tw.append(
                    "forfeit",
                    {"player": i, "reason": f.reason, "detail": f.detail, "phase": "handshake"},
                )
                side.write("stderr", player=i, phase="handshake", tail=p.stderr_text()[-2000:])
                outcome = {"winner": 1 - i, "reason": f"forfeit:{f.reason}"}
                break

        tw.append("state", {"state": state, "state_digest": digest(state), "turn": 0})

        # -- play ------------------------------------------------------------
        # Every call into the game module happens inside this boundary. A bug in
        # a game module must not kill the runner and leave a transcript with no
        # ending — a match that stops without a record is the fail-silent shape
        # this engine exists to avoid. An unhandled fault is recorded and VOIDS
        # the match. It is never charged to a player: a referee's own crash must
        # not be allowed to decide who won.
        turn = 0
        try:
            while outcome is None:
                if game.terminal(state) is not None:
                    break
                if turn >= bound:
                    tw.append("abort", {"reason": "move_bound_exceeded", "bound": bound})
                    outcome = {"winner": None, "reason": "move_bound_exceeded"}
                    break

                seat = state["to_move"]
                p = procs[seat]
                request = {
                    "type": "move_request",
                    "turn": turn,
                    "you_are": seat,
                    "observation": game.observation(state, seat),
                    "move_timeout_ms": int(move_timeout_s * 1000),
                }

                started = time.monotonic()
                try:
                    reply = p.ask(request)
                except EntrantFailure as f:
                    tw.append(
                        "forfeit",
                        {
                            "player": seat,
                            "reason": f.reason,
                            "detail": f.detail,
                            "phase": "move",
                            "turn": turn,
                        },
                    )
                    side.write("stderr", player=seat, phase="move", turn=turn, tail=p.stderr_text()[-2000:])
                    outcome = {"winner": 1 - seat, "reason": f"forfeit:{f.reason}"}
                    break
                side.write(
                    "latency", player=seat, turn=turn, ms=int((time.monotonic() - started) * 1000)
                )

                # The only entrant-authored value the referee reads.
                move = reply.get("move")
                ok, why = game.legal(state, move)
                if not ok:
                    tw.append(
                        "move",
                        {
                            "player": seat,
                            "turn": turn,
                            "move": move if _encodable(move) else None,
                            "legal": False,
                            "rejected_because": why,
                            "entrant_message": _safe(reply),
                        },
                    )
                    tw.append(
                        "forfeit",
                        {"player": seat, "reason": "illegal_move", "detail": why, "phase": "move", "turn": turn},
                    )
                    outcome = {"winner": 1 - seat, "reason": "forfeit:illegal_move"}
                    break

                tw.append(
                    "move",
                    {
                        "player": seat,
                        "turn": turn,
                        "move": move,
                        "legal": True,
                        "entrant_message": _safe(reply),
                    },
                )
                state = game.apply(state, move)
                turn += 1
                tw.append("state", {"state": state, "state_digest": digest(state), "turn": turn})

            if outcome is None:
                end = game.terminal(state)
                outcome = (
                    {"winner": end["winner"], "reason": end["reason"]}
                    if end
                    else {"winner": None, "reason": "unfinished"}
                )
        except Exception as e:  # a fault in the referee, not in either entrant
            tw.append(
                "engine_error",
                {
                    "detail": f"{e.__class__.__name__}: {e}"[:1000],
                    "phase": "referee",
                    "turn": turn,
                },
            )
            outcome = {"winner": None, "reason": "engine_error"}

        # -- score from referee state only ------------------------------------
        records_so_far = _reload(transcript_path)
        scored = score(referee_projection(records_so_far), game)

        result_body = {
            "winner": scored["winner"],
            "reason": scored["reason"],
            "moves": scored["moves"],
            "points": scored["points"],
            "decisive": scored["decisive"],
            "seats": {str(i): e["name"] for i, e in enumerate(entrants)},
            "scored_from": "referee_state_only",
            "self_report_excluded": True,
        }
        result = tw.append("result", result_body)

        # Say goodbye; a failure here cannot change the recorded result.
        for p in procs:
            try:
                p.send({"type": "goodbye", "result": {"winner": scored["winner"], "reason": scored["reason"]}})
            except Exception:
                pass

        return {
            "match_id": mid,
            "transcript": transcript_path,
            "diagnostics": sidecar_path,
            "chain_head": result["hash"],
            "engine_digest": engine_digest(),
            **result_body,
        }
    finally:
        tw.close()
        for p in procs:
            p.close()
            side.write("stderr_final", entrant=p.name, tail=p.stderr_text()[-2000:])
        side.close()
        if not keep_scratch:
            shutil.rmtree(scratch_root, ignore_errors=True)


def _reload(path):
    from .transcript import load

    return load(path)


def _encodable(value):
    from .canonical import NonCanonical, canonical_bytes

    try:
        canonical_bytes(value)
        return True
    except NonCanonical:
        return False


def _safe(value, limit=4096):
    """Record an entrant's raw message, bounded and canonically encodable.

    Kept for auditability. Removed by referee_projection before scoring.
    """
    if not _encodable(value):
        return {"unencodable": True, "repr": repr(value)[:limit]}
    text = repr(value)
    if len(text) > limit:
        return {"truncated": True, "repr": text[:limit]}
    return value
