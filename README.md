# BuilderWars

**Same model. Your harness. Re-run every match yourself.**

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

python bin/selfcheck.py               # adversarial referee checks
python bin/isolation_selfcheck.py     # strict admission + repaired-chain attacks
python bin/run_series.py --seeds 12
python bin/build_verifier.py --check  # regenerate verify.py, prove it agrees
```

Stock Python 3. No dependencies, no network, no accounts.

A caller that requires an OS capability boundary can make that requirement fail
closed:

```bash
python bin/run_match.py --seed 7 \
    --entrant entrants/solver_harness.py \
    --entrant entrants/naive_harness.py \
    --require-capability-isolation
```

No capability-isolated executor exists today, so this exits `2` with
`match_started:false` before it creates a transcript, scratch directory, or
entrant process. It does not silently run a weaker match.

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
Isolation and admission contract: [`docs/ISOLATION.md`](docs/ISOLATION.md).
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
follows from referee state rather than anyone's claim · the isolation declaration
has a known, non-overstated process profile · the verifying engine matches the
refereeing one.

**Does not prove:** which model produced a move · any wall-clock event · that the
host actually enforced the recorded process controls · network, filesystem, CPU,
memory, process-count, or host-credential confinement.

The engine never contacts a model, so it cannot witness one — every result carries
`model_attested: false`. Replay validates the isolation declaration and referee
source; it is not kernel, firewall, mount, credential, cgroup, or job-object
telemetry.

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

**3. Process-isolated entrants — capability-unconfined, in the same breath.**
Separate process, scratch cwd, environment allowlist, closed inherited file
descriptors, transcript path withheld, per-move timeout, output caps, bounded
stderr, and process teardown are enforced. **Not** enforced: network egress,
filesystem confinement, CPU, memory, process-count, or host-credential
boundaries. Those require an OS-level executor that does not exist yet.

The exact versioned profile ships inside every new transcript and replay rejects
a profile that invents a control or deletes a limitation. A repaired hash chain
does not rescue a false capability claim. Published legacy transcripts stay
verifiable only when their original caveats remain present.

Strict admission lets an operator refuse before any match side effect when a
capability boundary is required. It prevents silent degradation; it does not
create the missing boundary.

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

- **Two entrants.** Both written by us. There is no community yet.
- **One game played.** Nim. Ten Fronts and Manifest are specified and unplayed.
- **Isolation is by process, not by capability.** No network jail, filesystem
  boundary, CPU/memory/process-count cap, or host-credential boundary. Strict
  admission now refuses when a capability boundary is required; no executor can
  satisfy that requirement yet. That is fine while the entries are ours. It is
  not fine the moment someone we do not know enters.
- **Standalone verifier regeneration is a release gate.** `verify.py` embeds the
  referee byte-for-byte. Engine changes are not merge-ready until the generated
  artifact is reviewed, conformance-checked, and committed with zero diff.
- **Cross-model result not yet published.** The reference series holds the model
  constant, which isolates the harness cleanly but does not by itself show a
  smaller model beating a larger one. That series is in progress.
- **Ten Fronts has a mixed-strategy equilibrium**, so two near-optimal entrants
  trend toward 50/50. Unmeasured: how many rounds it takes to separate two
  *closely matched* harnesses — every pair measured so far had a ≥30% edge.

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

The isolation self-check adds another class of attack: it asks for a capability
boundary that does not exist, deletes a recorded limitation, forges
`capability_isolation:true`, repairs the transcript hash chain, and requires all
four paths to refuse or fail replay.

Each defect is a match-fixing failure in miniature — a result that looks clean
because the thing that should have caught it never ran.

## Layout

```
arena/            the engine. no network, no credentials, no model.
entrants/         reference harnesses. THIS is where a model lives.
bin/              run_match · run_series · verify_replay · selfcheck · isolation_selfcheck · build_verifier
games/            game specs, harness contract, community submission gate
template/         runnable entrant starting point
matches/          published transcripts
verify.py         the whole verifier as one file (generated; do not hand-edit)
```

## Licence

MIT. See [LICENSE](LICENSE).