# Ten Fronts

**One sentence a spectator needs:** whoever puts more troops on a column takes it.

**Capability tested:** strategic reasoning, opponent modelling, deception and
deception-detection, and format discipline under a hard constraint.

Reference implementation: `template/arena/games/ten_fronts.py`. Everything below
is measured against that file, not asserted.

---

## Rules

Ten fronts. Each round every front is publicly worth 1–5 points. Each side has
100 troops and spends all of them, every round.

A round has two phases:

1. **Signal.** Both sides simultaneously send one public message, ≤100
   characters. It is not binding. It can be a lie.
2. **Commit.** Both sides simultaneously submit ten non-negative integers summing
   to exactly 100.

Higher allocation takes the front's points. **An exact tie pays nobody** — copying
your opponent wins you nothing. Twenty rounds. Full history of every signal and
every allocation is visible to both sides and to the audience. Highest total wins.

There is no randomness in resolution. The only uncertainty in the game is the
other model.

### Forfeit rule

An allocation that is late, malformed, negative, or does not sum to exactly 100 is
**not repaired for you**. You are recorded as having sent zero troops everywhere
and your opponent takes every front they placed a single troop on.

This is deliberate. Reliability is a property of the harness, and the arena is
measuring the harness.

### The signal channel

Opponent messages arrive tagged as untrusted data. Lying is legal. Trying to
manipulate the opposing model through the channel is legal — resisting
manipulation is one of the things being tested. **Addressing the engine, the
scorer, or anything outside the match through the signal channel is an immediate
forfeit of the match**, not the round.

---

## Why it is watchable

Ten columns, two rows of bars, colour flips on the reveal, running score in the
corner. A spectator understands the win condition before they finish reading the
header.

The signal line above each side turns it into television. You see the claim, then
you see the truth, one second apart. `probed`: over 40 mirrored seeds the shipped
`liar` bot (announces an all-in on the round's most valuable front, then takes it
with one troop) beats the shipped `gullible` bot **7984 to 5886, a +15.1% edge**.
The bluff is not decoration — it is worth points, and the audience watches it pay.

---

## Anti-degeneracy

| failure mode | why it does not happen | evidence |
|---|---|---|
| Spread evenly and coast | 10-per-front loses to anything that concedes four fronts and overwhelms six | `probed`: `uniform` finished **0W–5L**, last of six on aggregate score |
| Copy the opponent | Simultaneous submission makes it impossible, and exact ties pay zero | `probed`: two identical deterministic bots score **0–0**, every front tied |
| One dumb strategy dominates | Panel is intransitive — no baseline beats all others | `probed`: best baseline took 4 of 5 pairings, `no_dominant_baseline` passes |
| A seat is secretly favoured | Game is seat-symmetric by construction | `probed`: stochastic reference bot mirrored against itself, seat bias **0.0000** |
| Same seed replays differently | Values derive from a seeded PRNG; nothing else is random | `probed`: `deterministic` check passes on byte-identical replay |

**The one real risk, stated plainly.** Colonel Blotto has a mixed-strategy
equilibrium. Two entrants that both play near-optimally will land near 50/50, and
the match becomes noise. This is why the arena's ranking must not be pure
head-to-head — it needs the same low-variance sparring panel used above as a
scored component, because exploiting a *known-exploitable* bot is a measurement
with far less variance than beating a peer.

The asymmetric, per-round front values are what keep pure mixing from being a
cheap escape: the optimal mixture changes every round, so "just randomise" is not
a strategy you can precompute once.

---

## How many rounds, how many seeds

`probed`, over the strategy pairs in `template/measure_variance.py`: a **single
seed reproduced the 120-seed verdict 100% of the time, even at 5 rounds**. Ten
Fronts has almost no seed luck.

`unmeasured`, and the caveat that matters: every pair tested had a large true edge
(≥30%). This does **not** establish how many rounds two closely-matched model
harnesses need. That measurement requires real entrants.

**Recommendation: 20 rounds, 3 seeds.** Twenty rounds because the entertainment
needs the adaptation arc — a pattern established, read, and broken — not because
the statistics need it; five would do statistically and would be a worse show.
Three seeds as cheap insurance against the near-equal case that has not been
measured yet.

**Cost:** 20 rounds × 2 phases = **40 model calls per seat per match**, 160 per
mirrored 2-seed pairing. Prompts are small.
