"""Nim — the engine's conformance fixture, not a competition game.

This is here because proving a match runner needs a game whose correct outcome
is not a matter of opinion. Nim is solved: from any position, the player to move
wins exactly when the XOR of the heap sizes is non-zero, and the winning move is
any move that makes that XOR zero. So the referee's adjudication can be checked
against mathematics rather than against taste, which is what a fixture is for.

Designing the actual competition games is a different lane's work. Nothing here
should be read as a proposal for one.

It happens to demonstrate the thesis cleanly: a harness that computes the XOR
beats a harness that asks the model to eyeball it, using the same model behind
both. Skill lives in the harness.

Normal play: the player who removes the last object wins.
"""

NAME = "nim"
VERSION = "1"
SUMMARY = "Remove objects from heaps; take the last object to win."
PLAYERS = 2

RULES = (
    "Heaps of objects sit on the table. On your turn choose one heap and remove "
    "at least one object from it. You may remove up to the whole heap. The player "
    "who removes the final object on the table wins. A move is "
    '{"heap": <0-based heap index>, "take": <count >= 1>}. An illegal or '
    "malformed move forfeits the match."
)


def _xor(heaps):
    x = 0
    for h in heaps:
        x ^= h
    return x


def setup(rng):
    heaps = [rng.randint(1, 7) for _ in range(rng.choice([3, 4]))]
    # Start from a first-player win so the outcome turns on play rather than on
    # a dead position. Nudge one heap until the XOR is non-zero.
    guard = 0
    while _xor(heaps) == 0:
        i = rng.randrange(len(heaps))
        heaps[i] = rng.randint(1, 7)
        guard += 1
        if guard > 64:  # unreachable in practice; refuse to loop forever
            heaps[0] = heaps[0] + 1 if heaps[0] < 7 else 1
    return {"heaps": heaps, "to_move": 0, "last_mover": None, "turn": 0}


def observation(state, player):
    # Nim is a perfect-information game, so both players see the same board.
    # The observation is still built per player, because the interface must not
    # assume otherwise.
    return {
        "game": NAME,
        "rules": RULES,
        "heaps": list(state["heaps"]),
        "you_are": player,
        "to_move": state["to_move"],
        "turn": state["turn"],
        "objects_remaining": sum(state["heaps"]),
    }


def legal(state, move):
    if not isinstance(move, dict):
        return False, "move must be an object"
    if set(move) - {"heap", "take"}:
        return False, f"unexpected keys in move: {sorted(set(move) - {'heap', 'take'})}"
    if "heap" not in move or "take" not in move:
        return False, 'move requires "heap" and "take"'
    heap, take = move["heap"], move["take"]
    # bool is an int subclass; a JSON `true` here is a malformed move, not heap 1.
    if isinstance(heap, bool) or not isinstance(heap, int):
        return False, '"heap" must be an integer'
    if isinstance(take, bool) or not isinstance(take, int):
        return False, '"take" must be an integer'
    heaps = state["heaps"]
    if not (0 <= heap < len(heaps)):
        return False, f'"heap" {heap} out of range 0..{len(heaps) - 1}'
    if take < 1:
        return False, '"take" must be at least 1'
    if take > heaps[heap]:
        return False, f'"take" {take} exceeds heap {heap} which holds {heaps[heap]}'
    return True, None


def apply(state, move):
    ok, reason = legal(state, move)
    if not ok:
        raise ValueError(f"apply() called with an illegal move: {reason}")
    heaps = list(state["heaps"])
    heaps[move["heap"]] -= move["take"]
    return {
        "heaps": heaps,
        "to_move": 1 - state["to_move"],
        "last_mover": state["to_move"],
        "turn": state["turn"] + 1,
    }


def terminal(state):
    if sum(state["heaps"]) == 0:
        return {"winner": state["last_mover"], "reason": "took_last_object"}
    return None


def move_bound(state):
    # Every legal move removes at least one object.
    return sum(state["heaps"])


# --- solved-game helpers -------------------------------------------------
# Exposed so harnesses can be strong. The referee does not use them, and an
# entrant importing them gains nothing it could not compute in three lines.


def winning_moves(heaps):
    """Every move that leaves an XOR of zero. Empty when the position is lost."""
    target = _xor(heaps)
    if target == 0:
        return []
    out = []
    for i, h in enumerate(heaps):
        want = h ^ target
        if want < h:
            out.append({"heap": i, "take": h - want})
    return out


def legal_moves(heaps):
    return [{"heap": i, "take": t} for i, h in enumerate(heaps) for t in range(1, h + 1)]
