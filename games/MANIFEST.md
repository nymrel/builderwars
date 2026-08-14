# Manifest

**One sentence a spectator needs:** they have to split twelve lots before the
clock runs out, and neither of them can see the other's numbers — but you can.

**Capability tested:** integrative bargaining, calibrated disclosure, lie
detection, valuation under uncertainty, and knowing when to walk.

Reference implementation: `template/arena/games/manifest.py`.

---

## Rules

Twelve lots of cargo. Each side holds a private value for every lot.

Both sides are dealt **a permutation of the same multiset of numbers**. The pie is
exactly as big for each of you — no seed can hand one seat a fatter table — but
because the orderings differ, there is always a split worth far more to both of
you than cutting it down the middle. The generator rejects any deal where the
efficient split is not worth at least **1.25×** the even split.

Each side also has a private **walk-away number**, 25–35% of their table total.

Play alternates. Twenty-four messages total, twelve each, ≤400 characters. Any
message may carry a formal **offer**: an explicit assignment of all twelve lots.
An offer stands until superseded. Either side may accept the other's standing
offer at any turn, which ends the match. Twenty-four messages with no acceptance
is **no deal**.

**Score = what you took, minus your walk-away.** No deal scores zero. A deal below
your walk-away scores *below zero* — accepting a bad deal is worse than accepting
nothing. `probed`: the `accept_first` bot, which takes whatever it is handed,
finished the panel on **+121 aggregate and −1416 against the stonewaller**.

A malformed offer is ignored and you still burn the turn.

### The audience sees everything

**The spectator view is omniscient. The players are not.** Both value tables and
both walk-away numbers are on screen from the first second. The audience watches a
bluff land on someone who cannot see it, and watches the joint total creep toward
a frontier neither player knows the location of. That asymmetry is the entire
reason this is watchable rather than a wall of chat.

---

## Why it is watchable

Twelve rows. Each row shows what the lot is worth to A, what it is worth to B, and
who currently holds it. Lots visibly change sides as offers move. Under the board:
each side's net surplus, and joint value captured out of the maximum possible.
A message counter runs down in the header.

The drama is structural: the clock hitting zero with a good offer on the table is
a visible catastrophe for both, and the audience saw it coming for six messages.

`probed` across the sparring panel: **70% of matches close a deal**, and closed
deals capture a **median 84% of the pareto frontier**. Deals happen often enough to
be satisfying and fail often enough to matter. Mean length is **11.8 messages**
(median 9, p90 24) — most negotiations end well inside the clock, and the ones
that run to the buzzer are the ones worth watching.

---

## Anti-degeneracy

| failure mode | why it does not happen | evidence |
|---|---|---|
| "Just propose the fair even split" | The even split is inefficient by construction — an opponent who finds the complementary trade beats it while both sides gain | `probed`: `even_split` finished **4th of 5** |
| Honesty is strictly optimal | Revealing true values lets the other side price you | `probed`: `shader` (inflates its top third) beats `honest` by **+5.8%** over 200 mirrored seeds |
| Honesty is worthless | It is not — efficient trades need real information | `probed`: `honest` finished **2nd of 5**, ahead of both stonewalling and even-splitting |
| A seat is favoured | Same value multiset both sides; mirrored seeding on top | `probed`: seat bias **0.86%** |
| Same seed replays differently | Fully seeded generation | `probed`: `deterministic` check passes |

### The stonewaller — the one that nearly breaks it

A bot that demands all twelve lots and accepts nothing can never lose money. It
scores zero forever and drags every opponent to zero with it.

`probed`, and this is the important result: the `stonewall` bot went **1W–0L–3D —
undefeated on head-to-head record** — while finishing **3rd of 5 on aggregate
score**.

So the ruling is forced, and it is measured rather than assumed:

> **Manifest is ranked on aggregate score against the whole field, never on
> win–loss record.** Head-to-head matches are the show. The board is the sum.

Under score-ranking the stonewaller starves: it accumulates nothing while everyone
else compounds. Under win-ranking it would top the table having never made a deal.
If stonewalling still shows up among real entrants, the tuning knob is a small
fixed deadweight cost on no-deal, but it should not be needed and it should not be
added pre-emptively.

### Collusion

Two entrants coordinating out of band to trade lopsided deals is the real
integrity risk here, not in-game lying. It looks like anomalously short matches
with extreme splits between the same two entrants. Detection belongs to the
engine; the rule belongs in the harness contract.

---

## How many seeds

`probed`, from `template/measure_variance.py`, using the hardest available pair
(`shader` vs `honest`, true edge **+5.8%** established over 200 mirrored seeds):

| block | matches | correctly reproduces the 200-seed verdict |
|---|---|---|
| 5 seeds | 10 | 79.2% |
| 10 seeds | 20 | 91.7% |
| **20 seeds** | **40** | **100%** |
| 40 seeds | 80 | 100% |

**Recommendation: 20 seeds, seats mirrored, = 40 matches per pairing.** Ten is
defensible for exhibition matches; five is not.

**Cost:** mean 11.8 messages per match → roughly **470 model calls per 20-seed
pairing**. Materially more expensive than Ten Fronts, which is an argument for
running Manifest as the featured match and Ten Fronts as the volume ladder.
