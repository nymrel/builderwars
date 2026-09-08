"""Offline oracle from the repository's Python referee; never executes entrants."""
import itertools
import json
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from arena.games import nim

cases = []
for count, limit in [(3, 5), (4, 4)]:
    for heaps in itertools.product(range(limit), repeat=count):
        if not sum(heaps):
            continue
        for seat in (0, 1):
            state = {"heaps": list(heaps), "to_move": seat, "last_mover": 1-seat, "turn": 0}
            moves = nim.legal_moves(heaps)
            cases.append({"heaps": heaps, "seat": seat, "moves": moves,
                          "after": [{"state": nim.apply(state, move),
                                     "terminal": nim.terminal(nim.apply(state, move))}
                                    for move in moves]})
print(json.dumps({"cases": cases, "setups": [nim.setup(random.Random(seed))
                 for seed in (41000, 41001, *range(42000, 42016))]}, separators=(",", ":")))
