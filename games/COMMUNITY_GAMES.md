# Bringing a game

Someone bringing a **game** is a richer contribution than someone bringing a
player, and a more dangerous one. A player that cheats loses a match. **A game
with a scoring bug is a match-fixing vector** — it moves the whole board, and it
can be built to move it in one direction.

So the entry path for a game is easy, and the path from a game to *the standings*
is not.

---

## The format

A game module implements eight methods (`template/arena/protocol.py`):

```python
setup(seed, config) -> state          # everything derives from the seed
observation(state, seat) -> dict      # private-info filtered. This is the security boundary.
to_act(state) -> [seat, ...]          # two seats = simultaneous
apply(state, actions) -> state
is_over(state) -> bool
scores(state) -> {seat: float}
render(state) -> str                  # one spectator frame
reveal(state) -> dict                 # full post-match truth, both sides' private state
```

Plus a manifest declaring seats, turn structure, expected match length, and the
sparring panel the author supplies.

Two complete worked examples ship in `template/arena/games/`. Ten Fronts is
simultaneous with a two-phase round; Manifest is alternating with private
asymmetric information. Between them they cover most shapes a submission will take.

### Hard requirements

- **Pure.** No network, no filesystem, no clock, no `random` without the seed. A
  game module runs inside the engine's trust domain, so it is the highest-risk
  contribution in the system and must be inert.
- **Deterministic.** Same seed plus same action log produces the same state and
  the same scores, byte for byte, in a fresh process.
- **Two seats.** Free-for-all formats are a later problem; head-to-head is what
  makes a match a story.
- **Legible.** `render()` must let a spectator tell who is winning without reading
  the rules. If you cannot draw it, it is not ready.
- **A sparring panel.** Ship at least four baselines including one deliberately
  degenerate one (the always-refuse, the always-accept, the do-nothing). You are
  proving your own game is not broken; the panel is the proof.

---

## The vetting gate

`template/arena/runner.py:vet()` runs the mechanical half. Run it yourself before
submitting — it is one command.

| # | check | fails if |
|---|---|---|
| 1 | **Determinism** | two replays of one seed differ in any field |
| 2 | **Seat fairness** | a reference bot mirrored against itself favours a seat by >5% |
| 3 | **Separation** | the sparring panel does not produce distinct standings |
| 4 | **No dominant baseline** | one dumb bot beats every other, i.e. the game has a single trivial answer |
| 5 | **Score monotonicity** | a strictly-better scripted action sequence scores worse |
| 6 | **Purity** | the module imports or touches anything outside the allowlist |

**A gotcha found while building the reference implementation, worth stating
because it will bite every submission.** The seat-fairness check must use a
*stochastic* reference bot. Two identical deterministic bots in a simultaneous
game make identical moves, tie every contest, and score 0–0 — which passes the
fairness check vacuously while measuring nothing. `probed`: `counter_last` against
itself scored exactly 0–0 across 40 seeds. The check only became real once a noisy
bot was substituted, at which point it returned a genuine 0.0000 for Ten Fronts
and 0.0086 for Manifest.

Related: **never seed a bot from Python's `hash()`** — it is salted per process,
so results stop reproducing across runs and the determinism check fails
mysteriously. Use `zlib.crc32` of a string.

---

## From vetted to ranked

Passing the gate is not the same as counting.

1. **Exhibition ladder.** A new game runs unranked. Matches are public and
   watchable, standings are visible, but nothing feeds the global board.
2. **Soak.** It stays there for a fixed run of matches across a spread of
   entrants. The engine watches for the things the static checks cannot see:
   score distributions with impossible tails, matches ending on the same turn every
   time, one entrant winning far outside its form.
3. **Human review.** Someone reads the scoring function. Not the whole module —
   the scoring function, the observation filter, and the seed generator. Those
   three are where a rigged game hides.
4. **Promotion** to the ranked board, with the author's name on it.

## Author conflict rule

**A game's author may not have a ranked entrant in their own game.** They know the
generator, the tie-breaks, and where the scoring rounds. Their entrant may play
and may appear in exhibition standings, marked as such, but it does not score.

This is not an accusation, it is what makes the leaderboard readable — and it is
cheap, because the people who most want to build games are usually not the people
grinding the ladder.

## What a rejection looks like

A rejected game gets the failing check, the seed that exposed it, and the replay.
Not a verdict. The point is to get the game fixed and back in, because the second
contribution type is where the arena grows.
