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

Identity is a separate axis reported alongside the verdict: a legacy unsigned
transcript can still PASS with `identity_status="self_declared_legacy"`; mixed
signed/legacy seats are labeled `mixed_verified_and_legacy`; and any supplied
passport that fails schema, signature, declaration consistency, or harness
binding makes the verdict FAIL (`identity_status="invalid"`) rather than being
downgraded. A valid signature proves only that the key holder signed that
version declaration — never the model claim, runtime, or person.
"""

import random

from .canonical import digest
from .games import load as load_game
from .integrity import engine_digest
from .scoring import referee_projection, score
from .transcript import first, load, verify_chain

_HEX_DIGITS = frozenset("0123456789abcdef")


def _hex64(value):
    return isinstance(value, str) and len(value) == 64 and set(value) <= _HEX_DIGITS


def _verify_header_identity(header):
    """Re-verify embedded passport evidence offline. Separate axis from rules.

    Returns (status, seats, error). Statuses:
      - "self_declared_legacy": no passports supplied anywhere (legacy shape)
      - "verified_signed": both seats have valid passports
      - "mixed_verified_and_legacy": supplied passports verify, some seats legacy
      - "invalid": any supplied passport fails any check — never downgraded

    A repaired hash chain does NOT rescue tampered identity evidence: the
    signature is over the declaration bytes themselves, so an attacker who edits
    a field and rechains still fails here.
    """
    try:
        rows = header.get("entrants")
        if (
            not isinstance(rows, list)
            or len(rows) != 2
            or any(not isinstance(row, dict) for row in rows)
            or any(type(row.get("seat")) is not int for row in rows)
            or [row["seat"] for row in rows] != [0, 1]
        ):
            return "invalid", [], "header must contain exactly ordered entrant seats 0 and 1"
        present = []
        passport_fields = []
        for row in rows:
            field_present = isinstance(row, dict) and "agent_passport" in row
            record = row.get("agent_passport") if field_present else None
            passport_fields.append(field_present)
            present.append(record)
        if not any(passport_fields):
            return "self_declared_legacy", [], None

        try:
            from . import passport as passport_contract
        except ImportError as e:
            return (
                "invalid",
                [],
                "passport evidence present but the in-engine passport verifier is unavailable in "
                f"this verifier build ({e.__class__.__name__})",
            )

        seats = []
        seen_agent_ids = set()
        for index, record in enumerate(present):
            if not passport_fields[index]:
                seats.append({"seat": index, "identityStatus": "self_declared_legacy"})
                continue
            if record is None:
                seats.append(
                    {
                        "seat": index,
                        "identityStatus": "invalid",
                        "errorCode": "passport_invalid",
                        "detail": "agent_passport field must contain a signed object",
                    }
                )
                continue
            try:
                normalized = passport_contract.verify_passport(record)
            except passport_contract.PassportDependencyError as e:
                seats.append(
                    {
                        "seat": index,
                        "identityStatus": "invalid",
                        "errorCode": "dependency_missing",
                        "detail": str(e)[:300],
                    }
                )
                continue
            except Exception as e:
                seats.append(
                    {
                        "seat": index,
                        "identityStatus": "invalid",
                        "errorCode": "passport_invalid",
                        "detail": str(e)[:300],
                    }
                )
                continue
            # Artifact binding: the signed harness digest must equal the script
            # digest recorded by the refereeing engine for this seat.
            script = None
            for row in rows:
                if isinstance(row, dict) and row.get("seat") == index:
                    script = row.get("script")
                    break
            recorded_sha = script.get("sha256") if isinstance(script, dict) else None
            bound = isinstance(recorded_sha, str) and recorded_sha == normalized["harnessSha256"]
            row = rows[index]
            declaration_consistent = (
                row.get("name") == normalized["displayName"]
                and row.get("claimed_model") == normalized["claimedModel"]
            )
            unique_agent = normalized["agentId"] not in seen_agent_ids
            seen_agent_ids.add(normalized["agentId"])
            ok = bound and declaration_consistent and unique_agent
            seats.append(
                {
                    "seat": index,
                    "identityStatus": "verified_signed" if ok else "invalid",
                    "agentId": normalized["agentId"],
                    "versionId": normalized["versionId"],
                    "parentVersionId": normalized["parentVersionId"],
                    "recordedHarnessDigestBound": bound,
                    "declarationConsistent": declaration_consistent,
                    "uniqueAgentInMatch": unique_agent,
                    **(
                        {}
                        if ok
                        else {
                            "detail": (
                                "harness, manifest declaration, or unique-agent binding failed"
                            )
                        }
                    ),
                }
            )
        ok = all(
            seat["identityStatus"] in ("verified_signed", "self_declared_legacy")
            for seat in seats
        )
        if not ok:
            return "invalid", seats, None
        signed_count = sum(seat["identityStatus"] == "verified_signed" for seat in seats)
        status = "verified_signed" if signed_count == len(seats) else "mixed_verified_and_legacy"
        return status, seats, None
    except Exception as e:  # never let hostile input raise out of verification
        return "invalid", [], f"{e.__class__.__name__}: {e}"


def verify(transcript_path):
    report = {
        "transcript": str(transcript_path),
        "chain_ok": False,
        "engine_digest_match": None,
        "attestation_ok": False,
        "abort_free": False,
        "engine_error_integrity": False,
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

    known_kinds = {"header", "ready", "state", "move", "forfeit", "abort", "engine_error", "result"}
    header_positions = [i for i, r in enumerate(records) if r["kind"] == "header"]
    result_positions = [i for i, r in enumerate(records) if r["kind"] == "result"]
    unknown_kinds = sorted({r["kind"] for r in records} - known_kinds)
    structure_ok = (
        header_positions == [0]
        and len(result_positions) == 1
        and result_positions == [len(records) - 1]
    )
    note(
        "transcript_structure",
        structure_ok,
        None if structure_ok else "transcript must open with one header and close with exactly one result",
    )
    kinds_ok = not unknown_kinds
    note("record_kinds", kinds_ok, None if kinds_ok else f"unknown record kinds: {unknown_kinds}")

    report["match_id"] = h.get("match_id")
    report["seed"] = h.get("seed")
    game_block = h.get("game")
    report["game"] = game_block.get("name") if isinstance(game_block, dict) else None

    attestation = h.get("attestation")
    attestation_ok = (
        isinstance(attestation, dict)
        and attestation.get("model_attested") is False
        and attestation.get("execution_claims_attested") is False
    )
    report["attestation_ok"] = attestation_ok
    note(
        "attestation_boundary",
        attestation_ok,
        None
        if attestation_ok
        else "attestation must be an object with model and execution claims exactly false",
    )

    # 2. is the verifying engine the refereeing engine?
    mine = engine_digest()
    engine_block = h.get("engine")
    theirs = engine_block.get("digest") if isinstance(engine_block, dict) else None
    digest_fields_ok = _hex64(mine) and _hex64(theirs)
    digest_match = digest_fields_ok and mine == theirs
    report["engine_digest_match"] = digest_match
    report["engine_digest_recorded"] = theirs
    report["engine_digest_verifier"] = mine
    note(
        "engine_digest",
        digest_match,
        None
        if digest_match
        else "engine digests must be 64-char lowercase hex and match exactly",
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
    aborts = []
    engine_errors = []

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

            elif kind == "abort":
                aborts.append(body)

            elif kind == "engine_error":
                engine_errors.append(body)
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

    # 4. forfeit integrity, then adjudication: at most one forfeit, fully typed,
    # and the forfeiting seat must be the one that lost
    forfeit_ok = len(forfeits) <= 1
    if forfeits:
        fb = forfeits[0]
        forfeit_ok = (
            forfeit_ok
            and isinstance(fb.get("player"), int)
            and not isinstance(fb.get("player"), bool)
            and fb["player"] in (0, 1)
            and isinstance(fb.get("reason"), str)
            and bool(fb["reason"])
            and isinstance(fb.get("phase"), str)
            and bool(fb["phase"])
        )
    note(
        "forfeit_integrity",
        forfeit_ok,
        None if forfeit_ok else "forfeit records must be singular and well-formed",
    )
    adjudication_ok = True
    recorded_result = first(records, "result")
    if recorded_result and forfeits and forfeit_ok:
        loser = forfeits[0]["player"]
        if recorded_result["body"].get("winner") != 1 - loser:
            adjudication_ok = False
    note("forfeit_adjudication", adjudication_ok, None if adjudication_ok else "forfeiting seat was not ruled the loser")

    abort_free = not aborts
    report["abort_free"] = abort_free
    note(
        "abort_free",
        abort_free,
        None if abort_free else "an aborted match is incomplete and cannot replay PASS",
    )

    engine_error_shape_ok = len(engine_errors) <= 1
    if engine_errors:
        eb = engine_errors[0]
        common_ok = (
            isinstance(eb.get("detail"), str)
            and 0 < len(eb["detail"]) <= 160
            and isinstance(eb.get("code"), str)
            and isinstance(eb.get("phase"), str)
        )
        handshake_ok = (
            set(eb) == {"detail", "code", "phase", "seat"}
            and eb.get("code") == "handshake_failed"
            and eb.get("phase") == "handshake"
            and type(eb.get("seat")) is int
            and eb["seat"] in (0, 1)
        )
        referee_ok = (
            set(eb) == {"detail", "code", "phase", "turn"}
            and eb.get("code") == "referee_fault"
            and eb.get("phase") == "referee"
            and type(eb.get("turn")) is int
            and eb["turn"] >= 0
        )
        engine_error_shape_ok = engine_error_shape_ok and common_ok and (
            handshake_ok or referee_ok
        )
    note(
        "engine_error_shape",
        engine_error_shape_ok,
        None
        if engine_error_shape_ok
        else "engine-error records must be singular, bounded, and fully typed",
    )

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
    engine_error_outcome_ok = True
    if engine_errors:
        engine_error_outcome_ok = (
            recomputed.get("winner") is None
            and recomputed.get("reason") == "engine_error"
            and recomputed.get("decisive") is False
            and recomputed.get("points") == {"0": 0, "1": 0}
            and rb.get("winner") is None
            and rb.get("reason") == "engine_error"
            and rb.get("decisive") is False
            and rb.get("points") == {"0": 0, "1": 0}
        )
    engine_error_integrity = engine_error_shape_ok and engine_error_outcome_ok
    report["engine_error_integrity"] = engine_error_integrity
    note(
        "engine_error_void_adjudication",
        engine_error_integrity,
        None
        if engine_error_integrity
        else "an engine error must produce an exact non-decisive zero-point void",
    )

    # 6. identity is a separate axis: rules replay and signed identity are
    # reported independently, and a supplied passport that fails any check can
    # never be silently downgraded to a legacy pass.
    identity_status, identity_seats, identity_error = _verify_header_identity(h)
    report["identity_status"] = identity_status
    report["identity_seats"] = identity_seats
    report["identity"] = {
        "status": identity_status,
        "seats": identity_seats,
        **({"error": identity_error} if identity_error else {}),
        "modelAttested": False,
        "runtimeAttested": False,
        "personAttested": False,
        "entrantIdentityAttested": False,
        "executionClaimsAttested": False,
        "errorCodes": sorted(
            {
                seat["errorCode"]
                for seat in identity_seats
                if isinstance(seat, dict) and seat.get("errorCode")
            }
        ),
        "boundary": (
            "Signed passports bind a tamper-evident, version-addressed declaration "
            "to a public key. They do not attest the model behind a move, the "
            "runtime, or the person holding the key."
        ),
    }
    if identity_error:
        note("passport_identity", False, identity_error)
    elif identity_status == "invalid":
        bad = [s for s in identity_seats if s.get("identityStatus") == "invalid"]
        note(
            "passport_identity",
            False,
            "; ".join(f"seat {s['seat']}: {s.get('detail', 'invalid')}" for s in bad) or "invalid passport evidence",
        )
    else:
        note(
            "passport_identity",
            True,
            (
                None
                if identity_status == "self_declared_legacy"
                else "all supplied passports verify; unsigned seats remain explicitly legacy"
            ),
        )

    passed = (
        report["chain_ok"]
        and report["engine_digest_match"] is True
        and attestation_ok
        and structure_ok
        and kinds_ok
        and setup_ok
        and states_ok
        and moves_ok
        and forfeit_ok
        and adjudication_ok
        and abort_free
        and engine_error_integrity
        and same
        and identity_status != "invalid"
    )
    report["verdict"] = "PASS" if passed else "FAIL"

    report["proves"] = [
        "transcript unaltered since it was written (hash chain recomputed)",
        "opening position follows from the recorded seed",
        "every move ruling reproduces under this engine's rules",
        "every position follows from the previous one",
        "the recorded winner follows from state, not from any entrant's claim",
    ]
    if identity_status in ("verified_signed", "mixed_verified_and_legacy"):
        report["proves"].append(
            "each supplied passport's signature verifies offline against its "
            "declared version content, key-derived IDs, and recorded preflight harness digest"
        )
    model_attested = attestation.get("model_attested") if isinstance(attestation, dict) else None
    report["does_not_prove"] = [
        "which model produced any move (the engine never contacts a model; "
        f"model_attested={model_attested})",
        "wall-clock events such as timeouts, which are recorded facts about the "
        "machine the match ran on",
    ]
    if identity_status in ("verified_signed", "mixed_verified_and_legacy"):
        report["does_not_prove"].append(
            "the person or legal owner behind the signing key, the runtime that "
            "executed the harness, or that the declared model claim is true — "
            "claimed model names are self-declared"
        )
    if not report["engine_digest_match"]:
        report["does_not_prove"].append(
            "that the refereeing engine matched this one — the engine digests differ, "
            "so these results describe different rule code"
        )
    return report
