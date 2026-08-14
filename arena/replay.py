"""Independent replay verification.

Give this a transcript and it re-derives the match without the entrants: it
recomputes the hash chain, rebuilds the opening position from the seed, replays
every recorded move through this engine's own copy of the rules, and re-derives
the score from state alone. Then it compares all of that to what the transcript
claims.

What a PASS proves:
  - the transcript has not been altered since it was written
  - the opening position really does follow from the recorded seed
  - every move that was accepted was legal, and every move that was rejected was
    genuinely illegal
  - each recorded position follows from the previous one under the stated rules
  - the recorded winner follows from the state history, not from anyone's say-so
  - the engine that verified is byte-identical to the engine that refereed
    (reported separately; a mismatch does not silently pass)

What a PASS does NOT prove:
  - that a move came from the model the entrant claimed. The engine never
    contacts a model, so it cannot witness one. Results carry `model_attested:
    false` for this reason.
  - wall-clock events. A timeout is a recorded fact about the machine the match
    ran on; replay verifies the adjudication that followed it, not the timing.
"""

import random

from .canonical import digest
from .games import load as load_game
from .integrity import engine_digest
from .scoring import referee_projection, score
from .transcript import first, load, verify_chain


def verify(transcript_path):
    report = {
        "transcript": str(transcript_path),
        "chain_ok": False,
        "engine_digest_match": None,
        "setup_ok": False,
        "moves_ok": False,
        "states_ok": False,
        "result_matches_recomputation": False,
        "verdict": "FAIL",
        "checks": [],
        "errors": [],
        "proves": [],
        "does_not_prove": [],
    }

    def note(name, ok, detail=None):
        report["checks"].append({"check": name, "ok": bool(ok), "detail": detail})
        if not ok and detail:
            report["errors"].append(f"{name}: {detail}")
        return ok

    try:
        records = load(transcript_path)
    except Exception as e:
        report["errors"].append(f"could not read transcript: {e}")
        return report

    if not records:
        note("non_empty", False, "transcript contains no records")
        return report

    # 1. chain integrity
    ok, err = verify_chain(records)
    report["chain_ok"] = ok
    note("hash_chain", ok, err)
    if not ok:
        report["errors"].append("chain is broken; nothing below can be trusted")
        return report
    report["chain_head"] = records[-1]["hash"]

    header = first(records, "header")
    if header is None:
        report["errors"].append("no header record")
        return report
    h = header["body"]
    report["match_id"] = h.get("match_id")
    report["seed"] = h.get("seed")
    report["game"] = h.get("game", {}).get("name")

    # 2. is the verifying engine the refereeing engine?
    mine = engine_digest()
    theirs = h.get("engine", {}).get("digest")
    report["engine_digest_match"] = mine == theirs
    report["engine_digest_recorded"] = theirs
    report["engine_digest_verifier"] = mine
    note(
        "engine_digest",
        mine == theirs,
        None if mine == theirs else "verifier engine differs from the engine that refereed",
    )

    try:
        game = load_game(h["game"]["name"])
    except Exception as e:
        report["errors"].append(f"unknown game: {e}")
        return report
    if game.VERSION != h["game"].get("version"):
        note("game_version", False, f"transcript wants {h['game'].get('version')}, have {game.VERSION}")
        return report
    note("game_version", True)

    # 3. replay
    computed = None
    seen_initial = False
    move_count = 0
    states_ok = True
    moves_ok = True
    setup_ok = False
    forfeits = []

    # A transcript handed to this function is untrusted input — it may be
    # crafted, truncated, or produced by a buggy engine. `verify` must always
    # return a verdict and must never raise: a verifier that throws a traceback
    # is a denial-of-verification, and a reader cannot tell a crash from a
    # result nobody looked at. Found by mutation-testing the self-check.
    try:
        for rec in records:
            kind, body = rec["kind"], rec["body"]

            if kind == "state":
                if not seen_initial:
                    computed = game.setup(random.Random(h["seed"]))
                    seen_initial = True
                    setup_ok = digest(computed) == body["state_digest"]
                    note(
                        "opening_position_from_seed",
                        setup_ok,
                        None if setup_ok else "seed does not reproduce the recorded opening position",
                    )
                    if not setup_ok:
                        states_ok = False
                else:
                    match_ = digest(computed) == body["state_digest"]
                    if not match_:
                        states_ok = False
                        note(
                            f"state_after_turn_{body.get('turn')}",
                            False,
                            "position does not follow from the previous move",
                        )

            elif kind == "move":
                move_count += 1
                if computed is None:
                    moves_ok = False
                    note(f"move_turn_{body.get('turn')}", False, "a move precedes any recorded position")
                    continue
                ok_here, why = game.legal(computed, body.get("move"))
                claimed_legal = bool(body.get("legal"))
                if ok_here != claimed_legal:
                    moves_ok = False
                    note(
                        f"move_turn_{body.get('turn')}",
                        False,
                        f"transcript says legal={claimed_legal}, this engine says legal={ok_here} ({why})",
                    )
                elif claimed_legal:
                    computed = game.apply(computed, body["move"])

            elif kind == "forfeit":
                forfeits.append(body)

            elif kind == "engine_error":
                report["engine_error_recorded"] = body.get("detail")
    except Exception as e:
        note(
            "replay_execution",
            False,
            f"replaying this transcript raised {e.__class__.__name__}: {e}",
        )
        report["verdict"] = "FAIL"
        return report

    report["setup_ok"] = setup_ok
    report["states_ok"] = states_ok
    report["moves_ok"] = moves_ok
    report["moves_replayed"] = move_count
    note("all_positions_follow_the_rules", states_ok)
    note("all_move_rulings_reproduce", moves_ok)

    # 4. adjudication of forfeits: the forfeiting seat must be the one that lost
    adjudication_ok = True
    recorded_result = first(records, "result")
    if recorded_result and forfeits:
        loser = forfeits[0]["player"]
        if recorded_result["body"].get("winner") != 1 - loser:
            adjudication_ok = False
    note("forfeit_adjudication", adjudication_ok, None if adjudication_ok else "forfeiting seat was not ruled the loser")

    # 5. recompute the score from referee state, ignoring the recorded result
    try:
        recomputed = score(referee_projection(records), game)
    except Exception as e:
        note("score_recomputation", False, f"{e.__class__.__name__}: {e}")
        report["verdict"] = "FAIL"
        return report
    report["recomputed"] = recomputed
    if recorded_result is None:
        note("result_present", False, "no result record")
        return report
    rb = recorded_result["body"]
    report["recorded"] = {k: rb.get(k) for k in ("winner", "reason", "moves", "points", "decisive")}
    same = all(recomputed[k] == rb.get(k) for k in ("winner", "reason", "moves", "points", "decisive"))
    report["result_matches_recomputation"] = same
    note(
        "recorded_result_follows_from_state",
        same,
        None if same else f"recorded {report['recorded']} vs recomputed {recomputed}",
    )

    passed = (
        report["chain_ok"]
        and setup_ok
        and states_ok
        and moves_ok
        and adjudication_ok
        and same
    )
    report["verdict"] = "PASS" if passed else "FAIL"

    report["proves"] = [
        "transcript unaltered since it was written (hash chain recomputed)",
        "opening position follows from the recorded seed",
        "every move ruling reproduces under this engine's rules",
        "every position follows from the previous one",
        "the recorded winner follows from state, not from any entrant's claim",
    ]
    report["does_not_prove"] = [
        "which model produced any move (the engine never contacts a model; "
        f"model_attested={h.get('attestation', {}).get('model_attested')})",
        "wall-clock events such as timeouts, which are recorded facts about the "
        "machine the match ran on",
    ]
    if not report["engine_digest_match"]:
        report["does_not_prove"].append(
            "that the refereeing engine matched this one — the engine digests differ, "
            "so these results describe different rule code"
        )
    return report
