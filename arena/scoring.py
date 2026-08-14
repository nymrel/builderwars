"""Scoring, with entrant self-report structurally excluded.

The rule this module enforces: a competitor's own account of how it did is never
an input to the score. Stating that as a policy is worthless — someone will read
the field "because it was there". So it is enforced by construction instead.

`referee_projection` deletes every entrant-authored byte from the record stream,
and `score` accepts only a projection. A self-reported "I won" cannot reach the
scorer because it no longer exists in the value the scorer is handed.

The one entrant-authored value that survives is `move`, and it survives because
it is not a report — it is a game action, validated against the rules by the
referee before it is permitted to change any state.
"""

from .canonical import digest

# Entrant-authored keys, recorded in the transcript for auditability and removed
# before scoring. Add to this set, never read from it.
ENTRANT_AUTHORED = frozenset({"entrant_message", "entrant_note", "claimed_model"})


class NotAProjection(Exception):
    pass


def referee_projection(records):
    """Strip entrant-authored content. The result is referee-authored only."""
    out = []
    for rec in records:
        body = {k: v for k, v in rec["body"].items() if k not in ENTRANT_AUTHORED}
        if rec["kind"] == "header":
            body = dict(body)
            body["entrants"] = [
                {k: v for k, v in e.items() if k not in ENTRANT_AUTHORED}
                for e in body.get("entrants", [])
            ]
        out.append({"kind": rec["kind"], "seq": rec["seq"], "body": body, "_projected": True})
    return out


def _require_projection(records):
    if not all(r.get("_projected") for r in records):
        raise NotAProjection(
            "score() accepts only a referee_projection(); passing raw records would "
            "expose entrant-authored fields to the scoring path"
        )


def score(projection, game):
    """Derive the outcome from referee state alone.

    Deliberately ignores any `result` record. Replay compares what this returns
    against what the match recorded, so a recorded result that does not follow
    from the state history is caught rather than trusted.
    """
    _require_projection(projection)

    states = [r["body"]["state"] for r in projection if r["kind"] == "state"]
    forfeits = [r["body"] for r in projection if r["kind"] == "forfeit"]
    moves = [r for r in projection if r["kind"] == "move"]
    faults = [r["body"] for r in projection if r["kind"] == "engine_error"]

    if faults:
        # The referee itself failed. Void the match — do not hand the win to the
        # other seat. A bug in the rules code must never decide a contest, and
        # an arena that quietly awards those points is fixing matches by accident.
        return {
            "winner": None,
            "reason": "engine_error",
            "moves": len(moves),
            "points": {"0": 0, "1": 0},
            "decisive": False,
        }

    if not states:
        return {"winner": None, "reason": "no_state_recorded", "moves": 0, "points": {}, "decisive": False}

    if forfeits:
        f = forfeits[0]
        loser = f["player"]
        winner = 1 - loser
        return {
            "winner": winner,
            "reason": f"forfeit:{f['reason']}",
            "moves": len(moves),
            "points": {"0": 1 if winner == 0 else 0, "1": 1 if winner == 1 else 0},
            "decisive": True,
        }

    end = game.terminal(states[-1])
    if end is None:
        return {
            "winner": None,
            "reason": "unfinished",
            "moves": len(moves),
            "points": {"0": 0, "1": 0},
            "decisive": False,
        }

    winner = end["winner"]
    return {
        "winner": winner,
        "reason": end["reason"],
        "moves": len(moves),
        "points": {"0": 1 if winner == 0 else 0, "1": 1 if winner == 1 else 0},
        "decisive": winner is not None,
    }


def score_digest(scored):
    return digest(scored)
