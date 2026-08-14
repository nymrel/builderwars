"""Game modules.

A game is a pure state machine. It never performs I/O, never sees an entrant,
and never consumes randomness outside `setup`. Those three restrictions are what
make a match replayable from a seed and a move list.

Required module interface (see ENTRANT_CONTRACT.md for the wire side):

    NAME: str
    VERSION: str
    SUMMARY: str
    PLAYERS: int

    setup(rng)                  -> state
    observation(state, player)  -> dict   # what that player is allowed to see
    legal(state, move)          -> (bool, reason)
    apply(state, move)          -> state  # must not mutate the input
    terminal(state)             -> None | {"winner": int | None, "reason": str}
    move_bound(state)           -> int    # hard cap on remaining moves

`state` must be canonically encodable (see arena.canonical) and must carry a
"to_move" key. Integers only — no floats anywhere in state or scoring.
"""

import importlib

REGISTRY = {"nim": "arena.games.nim"}


def load(name):
    if name not in REGISTRY:
        raise KeyError(f"unknown game {name!r}; known: {sorted(REGISTRY)}")
    return importlib.import_module(REGISTRY[name])
