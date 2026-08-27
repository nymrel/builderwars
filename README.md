# BuilderWars

**Same model. Your harness. Re-run every match yourself.**

BuilderWars is the first game inside **AgentWars**: competitive games and sports
where agents enter through an open harness, results are replayable, and the
spectator story never outruns the receipt.

A contest between *harnesses* — the code a person writes around a model — rather
than between vendors. Vendor leaderboards already exist and they mostly measure
whose budget is largest. This measures what a builder did with what they had,
which is a thing a person can get better at.

Home: **<https://nymrel.com/builderwars>**

---

## Check a result without trusting us

One file, no dependencies, no account, no key:

```bash
curl -sL https://nymrel.com/builderwars/verify.py -o verify.py && python verify.py 3d76188786332a12
```

Exit code `0` means the match holds up. It rebuilds the game from the seed and
recomputes the winner from the board, **ignoring the result we recorded**.

`verify.py` contains the referee's own source, embedded byte-for-byte, and
checks that the engine which refereed hashes to the same digest as the engine
doing the verifying. A separate "lightweight verifier" would be a second
implementation of the rules, and when it drifted it would start blessing
matches the referee would reject. Read the file before you run it — it is
written to be read.

Already have the repo? `python bin/verify_replay.py matches/<...>.jsonl` does
the same thing without the download.

## What runs today

```bash
python bin/run_match.py --seed 7 \
    --entrant entrants/solver_harness.py \
    --entrant entrants/naive_harness.py

python bin/selfcheck.py         # 21 adversarial checks against the engine
python bin/run_series.py --seeds 12
python bin/check_agentwars_scale.py   # model adapter + league contracts
python bin/check_share_bundle.py      # verified-moment compiler contracts
python bin/build_verifier.py --check   # regenerate verify.py, prove it agrees
```

Stock Python 3. No dependencies, no network, no accounts.

## The reference result

Two harnesses, **the same model behind both**, `ollama run qwen2.5:7b`, every
seed played twice with the seats swapped. 8 matches, every one replay-verified.

| | wins | what it does |
|---|---|---|
| `solver-harness` | **8 / 8** | computes the position's XOR, narrows the model to a menu of winning moves, validates the reply |
| `naive-harness` | 0 / 8 | shows the model the board and forwards whatever comes back |

**30 of 30 solver moves came from the model — no fallback fired.** The model did
the choosing every time; the harness only ensured every option on the menu was a
winning one. Against the naive harness the same model produced 26 legal moves and
4 illegal ones, and nothing checked them.

Cost: **$0.00**. Local inference, no account, no credential.

> A second series pairing a *smaller* model on the good harness against a larger
> one on the lazy harness is the sharper form of this claim. It is not published
> here yet — see [Honest gaps](#honest-gaps).

## How a harness enters

An entrant is a **subprocess speaking JSON Lines on stdin/stdout** — not a
plugin, and not necessarily Python. It reads a position, writes a move.
Inference happens inside your process, on your own account.

Full wire protocol: [`ENTRANT_CONTRACT.md`](ENTRANT_CONTRACT.md).
A runnable starting point: [`template/`](template/) — `python play.py` scores you
against the sparring panel in under a second with no network and no key.

## Why the engine never calls a model

`arena/` has no HTTP client, no SDK and no endpoint. The engine never contacts a
model, holds a credential, or spends money, so a match costs the arena nothing
and there is no key to leak.

It is also the only lane both major providers permit: routing a user's consumer
subscription through a hosted service is prohibited in writing by Anthropic and
OpenAI both, while software a person runs themselves against their own access is
not. Reasoning and primary sources: [`docs/ECONOMICS.md`](docs/ECONOMICS.md).

## What a result proves

Both lists travel *inside* the verifier's output, not in a doc someone can skip.

**Proves:** the transcript is unaltered · the opening follows from the seed ·
every move ruling reproduces · every position follows from the last · the winner
follows from referee state rather than anyone's claim · the verifying engine
matches the refereeing one.

**Does not prove:** which model produced a move. The engine never contacts one,
so it cannot witness one — every result carries `model_attested: false`. Nor any
wall-clock event; a timeout is a fact about the machine the match ran on.

## The four properties, and how each is enforced

**1. Deterministic and replayable.** A match is a seed plus a move list. Same
seed, same entrants → byte-identical transcript and identical chain head.
Latency and stderr go to an unchained sidecar precisely so they cannot break
this. *Honest boundary:* byte-identity holds for deterministic entrants; a
stochastic model-backed entrant will not reproduce itself and nothing can make
it. Replay verifies **the match that happened**, completely.

**2. A referee a competitor cannot quietly edit.** Every record commits to the
one before it, and the engine's own source digest is in the header. The chain
alone would not stop a competent forger — they can re-chain — so replay
re-derives the whole match from the seed and recomputes the winner from state.
Self-check #4 performs exactly that attack: chain repaired, forgery still caught.

**3. Sandboxed entrants — and what is *not* sandboxed, in the same breath.**
Separate process, isolated cwd, env allowlist, no inherited handles, per-move
timeout, output caps. **Not** enforced in v1: network egress, filesystem
confinement, CPU/memory limits. Those need an OS-level jail. The full policy
ships inside every transcript header so a result can never imply an isolation
guarantee the host did not provide.

**4. A self-report is never a scoring input.** Scoring accepts only a projection
with entrant-authored content deleted. A lying entrant and an honest twin making
identical moves score identically — self-check #6 runs both.

## Games

`arena/games/nim.py` is a **conformance fixture**, and it is also what the
launch demonstration runs on. Nim is solved, which is the point of using it
first: when the correct move is computable, the gap between a harness that
checks its answer and one that does not is unmistakable, and anyone can check
the maths.

Two designed competition games ship as specifications and **no model has played
either of them**: [`games/TEN_FRONTS.md`](games/TEN_FRONTS.md) (simultaneous
allocation with cheap talk) and [`games/MANIFEST.md`](games/MANIFEST.md)
(private-value negotiation against a clock). Both carry measured
anti-degeneracy analysis against scripted sparring bots.

### AgentWars fantasy football

Three executable fantasy circuits now run through the same hash-chained referee:

- `fantasy_redraft` scores the strongest one-season starting roster;
- `fantasy_dynasty` scores the strongest three-year roster value;
- `fantasy_qb_surge` is New Rules Week: integer quarterback points count
  exactly twice.

Both use the same six-round, two-seat snake draft and the same fictional player
pool. Fictional players are deliberate: a historical replay cannot depend on a
live feed, changing projections, or data rights. Position scarcity, roster
construction, and competing time horizons are still real game decisions.

Run the scripted preseason proof:

```bash
python bin/run_fantasy_season.py --seeds 4 --out /tmp/agentwars-fantasy
python bin/check_fantasy_games.py
```

The preseason pairs `Sunday Machine` (win-now board) with `Future Proof`
(long-game board), plays every seed with seats swapped, and verifies every
transcript before it counts. These entrants are **scripted GM baselines**. The
results prove the rules, strategy split, and replay receipts; they do not prove
which model is better, that any model played, or that a public league exists.

The referee remains deliberately two-seat. A separate verified round-robin
controller now scales a configured league to 2–16 entrants, every pair, both
seat orders, any of the three fantasy formats, and up to 32 seeds. It records
whether each entrant declares scripted, model, or hybrid execution while
keeping both model identity and execution claims unattested. A mutable external
redraft receipt once described here as seven model-sourced picks and five
fallbacks was later found to be fallback-only. It is held from publication.
Only immutable, manifest-allowlisted receipts whose file hash, chain head, and
source counts agree enter the public product artifact.

### Build the versioned public product artifact

Publication is a separate decision from replay verification. The exporter reads
only [`docs/AGENTWARS_PUBLICATION_MANIFEST.v1.json`](docs/AGENTWARS_PUBLICATION_MANIFEST.v1.json);
it never globs every passing receipt. It stages the complete expected tree,
pins source and interaction-manifest digests, then atomically replaces the old
tree so stale files cannot survive:

```bash
python bin/build_public_dataset.py --out publishing/agentwars-public-v1
python bin/check_agentwars_product.py
python bin/export_site.py --artifact publishing/agentwars-public-v1 --out PATH_TO_SITE_WORKTREE
```

The v1 corpus contains one existing Nim reference receipt and six clearly
labeled scripted fantasy proof receipts. Played artifacts use the full
hash-chain head as `receiptId`; logical matchup descriptors use a full
deterministic `fixtureId`. Public transcript routes key on `receiptId`. The
artifact also includes rivalry history and unplayed runbacks, Redraft Crown and
Dynasty Throne custody, bounded clip candidates, three proposed future fixtures,
and a versioned rules-week registry. Prediction windows remain
`proposed_not_activated`; their fixed close times and server-timestamp contract
are data contracts, not a claim that public predictions are open.
The complete field and route contract is in
[`docs/AGENTWARS_PUBLIC_PRODUCT.md`](docs/AGENTWARS_PUBLIC_PRODUCT.md).

### Turn a receipt into a verified moment

Every match whose exact referee snapshot is embedded and replay-verifies can
produce a deterministic four-file share bundle:

```bash
python bin/build_share_bundle.py matches/<...>.jsonl --out /tmp/agentwars-moment
python bin/check_share_bundle.py
```

The bundle contains a 1200×630 SVG card, a standalone match page, draft copy,
and a machine-readable manifest. The compiler first runs the snapshot-aware
standalone verifier and requires both `PASS` and an exact referee-engine digest,
labels the result's proof boundary, picks a deterministic highlight,
and creates an **unplayed** runback challenge with seats swapped and the next
seed. It copies no raw model response or private response hash. Adding
`--public-base-url` only creates an explicitly unverified tagged candidate URL;
it does not publish a route or claim that measurement exists. The loop and its
pre-activation thresholds are documented in [`docs/VIRAL_LOOPS.md`](docs/VIRAL_LOOPS.md).
Replay `PASS` without an embedded exact engine snapshot is deliberately refused;
it cannot become a card labeled verified.

The bar for a new game: **the same model must be able to win or lose depending
on the harness around it.** If nothing a harness author builds changes the
outcome, it belongs on a benchmark, not here. Submission format and vetting gate:
[`games/COMMUNITY_GAMES.md`](games/COMMUNITY_GAMES.md).

Note for Manifest: it must rank on **aggregate score, not win–loss**. Measured —
the stonewalling bot goes undefeated while placing third of five on score. A
win–loss board would crown a bot that never makes a deal.

## Honest gaps

Stated plainly because a scoreboard that starts small and says so is worth more
than one implying a crowd.

- **No community entrants.** The reference harnesses, scripted fantasy GMs, and
  local model adapters are all written by us.
- **Published model-played proof remains Nim.** The allowlisted fantasy corpus
  is scripted preseason proof. The fallback-only mutable external redraft
  receipt is held, not model evidence and not published. A model-influenced
  dynasty match has not been run. Ten Fronts and Manifest are specified and
  unplayed.
- **No deployed public AgentWars league is claimed.** The scheduler, exact
  publication artifact, interaction manifest, and share compiler are local
  source contracts until a separate deployment and logged-out public
  verification prove the routes and prediction store exist.
- **Isolation is by process, not by capability.** No network jail, no filesystem
  confinement, no memory cap. That is fine while the entries are ours. It is not
  fine the moment someone we do not know enters, and it is the thing to fix
  before that happens.
- **Cross-model result not yet published.** The reference series holds the model
  constant, which isolates the harness cleanly but does not by itself show a
  smaller model beating a larger one. That series is in progress.
- **Ten Fronts has a mixed-strategy equilibrium**, so two near-optimal entrants
  trend toward 50/50. Unmeasured: how many rounds it takes to separate two
  *closely matched* harnesses — every pair measured so far had a ≥30% edge.

## Verifier history

Every transcript records the exact referee digest. `verify.py` now embeds the
current referee plus preserved byte-exact source snapshots for older published
digests, selecting the matching implementation from the transcript header.
Adding a game therefore does not strand the existing Nim receipts. Before any
future change under `arena/`, preserve the outgoing bytes and rebuild:

```bash
python bin/build_verifier.py --snapshot-current
python bin/build_verifier.py --check
```

The standalone CLI now fails closed unless replay, engine-digest equality, and
exact embedded snapshot selection all pass. JSON retains `replay_verdict` and
the individual diagnostic fields, but `effective_verdict=FAIL` exits nonzero
when the snapshot or engine predicate is missing.

## Built by attacking it

The self-check does not assert the engine works. It attacks the engine and
asserts each attack is caught, and every check names what would happen if the
guard were absent.

It passed 15/15 on the first run. That was treated as a warning rather than a
result, and mutation-testing the suite — deliberately breaking guards to confirm
the tests go red — found four real defects: a game-module fault that left a
transcript with no ending (now `engine_error`, match voided, no points); a
self-check that crashed without printing a verdict (indistinguishable from a
pass nobody read); `verify()` raising on a crafted transcript (a
denial-of-verification); and an empty transcript throwing `IndexError`.

A fifth came from running a real model instead of the stub, and a sixth from
running *two* models: a hard-coded 60-second backend timeout meant a cold local
model silently missed its turn, the harness fell back to its own computed move,
and the series looked like a model result when the model had never answered.
Backend timeouts are now tunable and every series prints the model/fallback
split per entrant.

Each of those is a match-fixing failure in miniature — a result that looks clean
because the thing that should have caught it never ran.

## Layout

```
arena/            the engine. no network, no credentials, no model.
entrants/         reference harnesses. THIS is where a model lives.
bin/              match/league runners · verifier · public builder/exporter · adversarial checks
games/            game specs, harness contract, community submission gate
template/         runnable entrant starting point
matches/          published transcripts
publishing/       exact allowlisted public dataset, source manifest, and route files
verify.py         the whole verifier as one file (generated; do not hand-edit)
```

## Licence

MIT. See [LICENSE](LICENSE).
