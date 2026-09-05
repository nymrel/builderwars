# Bringing a game

Someone bringing a **game** is a richer contribution than someone bringing a
player, and a more dangerous one. A player that cheats loses a match. **A game
with a scoring bug is a match-fixing vector** — it moves the whole board, and it
can be built to move it in one direction.

So the entry path for a game is easy, and the path from a game to *the standings*
is not.

> **Launch boundary (2026-08-26):** the only current creator SDK candidate is
> declarative `agentwars.creator_game.v1`. It executes no creator code and is
> documented in
> [`docs/AGENTWARS_CREATOR_GAME_SDK.md`](../docs/AGENTWARS_CREATOR_GAME_SDK.md).
> Passing its verifier leaves a game `candidate_not_admitted`. The Python-module
> format retained below is prior design research for trusted first-party source;
> it is not a public submission, upload, exhibition, or ranking path.

---

## Current launch path: declarative data

Creators can describe a bounded `sealed_allocation_v1` game with strict JSON.
The trusted interpreter owns state transitions, hidden-information filtering,
integer scoring, move bounds, terminal results, and replay. The manifest has no
module, callback, expression, command, URL, provider, credential, or runtime
field.

```bash
python -B bin/creator_game.py validate creator_games/signal-siege/game.v1.json
python -B bin/creator_game.py verify-replay creator_games/signal-siege/game.v1.json creator_games/signal-siege/replay.v1.json
python -B bin/check_creator_game_sdk.py
```

The source-controlled registry binds exact manifest and replay digests while
keeping execution, publication, ranking, and author-entrant ranking false. It
does not auto-load games into `arena.games.REGISTRY`. Signal Siege is the first
studio-authored usability fixture and remains a held, non-executable candidate;
it is not evidence of a community creator or a deployed league.

## Legacy module research format (not admissible)

A trusted research game module implements eight methods
(`template/arena/protocol.py`):

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
sparring panel the author supplies. This remains useful for first-party rule
research, but static purity checks are not an OS sandbox and do not make
untrusted code safe to run.

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

## From vetted to ranked — future governed path

Passing either the declarative gate or a trusted first-party research gate is
not the same as counting. The current declarative registry stops before step 1;
each later transition requires a separate source-controlled review.

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
