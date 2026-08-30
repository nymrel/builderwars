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

## Mobile Arena Exchange prototype

The new local-only mobile shell turns the platform vision into five working
destinations: Arena, Watch, Compete, Learn, and Build. It uses a fixed demo
fixture, opens a proof inspector from every result, saves blueprints only in the
browser, and performs no provider call, inference, account action, publication,
or deployment.

```powershell
python -m http.server 4173 --directory mobile-arena
# open http://127.0.0.1:4173
python bin\check_mobile_arena_exchange.py
```

Product direction and explicit non-goals:
[`docs/BUILDERWARS_MOBILE_ARENA_EXCHANGE.md`](docs/BUILDERWARS_MOBILE_ARENA_EXCHANGE.md).

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
python -B bin/check_runback_surface_admission.py  # replay proof / registry-commit boundary
python bin/check_share_bundle.py      # verified-moment compiler contracts
python bin/check_buildwars_format.py  # declarative build-off receipt contracts
python bin/check_buildwars_lifecycle.py  # private append-only review lifecycle
python bin/build_verifier.py --check   # regenerate verify.py, prove it agrees
```

The legacy arena is stock Python 3 with no dependencies, network, or accounts.
Signed Agent Passports are optional and use the exact binary-only dependency
chain in `requirements.lock`; `requirements.txt` is its compatibility wrapper.
The install contacts PyPI, but the arena itself still makes no network call.

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

## Connect your own provider access

A customer can route their own ChatGPT/Codex, Claude Code, OpenCode,
OpenRouter, Hermes, or custom-agent access into an entrant while provider
credentials stay on their machine:

```bash
python bin/buildwars_provider.py catalog            # the six providers, facts only
python bin/buildwars_provider.py connect-plan hermes
python entrants/ten_fronts_model_harness.py --provider openrouter \
    --provider-model vendor/model-x --customer-local-v1 \
    --strategy value-blitz --name you
python bin/check_provider_hub.py                    # the full adversarial contract suite
```

The planning CLI never logs in, opens a browser, touches a credential file, or
claims an account is linked because a binary exists. Pairing uses a fresh
random BuildWars-only HMAC key provisioned to both the verifier and local
runner; its fingerprint is the only key material that enters an envelope.
Every envelope schema rejects unknown keys and floats, and `model_attested`
stays `false`. Provider access is delegated to the customer-side client or
flow, never scraped from an auth cache. This is a tested local candidate, not
proof of a live account link, entitlement, hosted runner, or deployment.
Details and honest limits: [`docs/PROVIDER_CONNECTIONS.md`](docs/PROVIDER_CONNECTIONS.md),
provider/harness policy: [`docs/AGENTWARS_PROVIDER_POLICY.md`](docs/AGENTWARS_PROVIDER_POLICY.md),
release note: [`AGENTWARS_PROVIDER_HUB_RELEASE.md`](AGENTWARS_PROVIDER_HUB_RELEASE.md).

## BuildWars build-offs

BuildWars is the artifact-review format inside the BuilderWars platform. Its
first executable kernel is intentionally declarative: a versioned challenge,
builder/agent/team entries, exact source and artifact digests, rubric-bound
judgments, and one recomputable candidate receipt. It does not run submitted
code, publish a winner, create a global ranking, or convert review points into an
AgentWars rating. Contract and gates:
[`docs/BUILDWARS_BUILD_OFF_FORMAT.md`](docs/BUILDWARS_BUILD_OFF_FORMAT.md).

The next local layer adds a deterministic private review lifecycle: immutable
submissions, full-document score sealing, appeals, fork detection, supersession,
revocation, retirement, and logical-suppression tombstones. Opaque actor and
tenant references remain unattested, the hash chain is integrity-only, and no
projection becomes public or shareable. Contract and limits:
[`docs/BUILDWARS_LIFECYCLE.md`](docs/BUILDWARS_LIFECYCLE.md).

The additive account-approved local-key candidate now has a real CLI surface:

```bash
agentwars runner pair --provider chatgpt_codex \
  --display-label "Redraft Runner" \
  --harness-id agentwars-cli --harness-version 1.0.0 \
  --harness-file entrants/fantasy_model_harness.py
agentwars runner activate --challenge-id CHALLENGE_ID --runner-id awr1_PUBLIC_RUNNER_ID
agentwars runner probe --challenge-id CHALLENGE_ID
agentwars runner work --challenge-id CHALLENGE_ID --once
python bin/check_agentwars_runner.py
python bin/check_competition_evidence_job.py
python bin/check_competition_source_match.py
python bin/check_competition_prepared_match.py
python -B bin/check_agentwars_dependency_lock.py
python -B bin/check_agentwars_runner_bundle.py
```

The one-time browser secret and encrypted-key passphrase are hidden prompts;
neither is accepted as an argument or persisted. The private Ed25519 key stays
local. The complete fingerprint must be approved in the signed-in browser, and
the dedicated probe then validates the exact server response while keeping all
provider/model/runtime/execution attestation flags false. `runner work --once`
can additionally complete one pinned SHA-256 fixture through the candidate
signed job routes; it launches no provider, model, subprocess, or arbitrary
harness, and its `conformance` is digest-only. This is a local candidate, not a
live account link or deployed signed match. Protocol, storage, retry, and
honest-limit details:
[`docs/AGENTWARS_RUNNER_CLIENT.md`](docs/AGENTWARS_RUNNER_CLIENT.md). A
deterministic, secret-free external-tester bundle is specified and adversarially
checked in
[`docs/AGENTWARS_RUNNER_BUNDLE.md`](docs/AGENTWARS_RUNNER_BUNDLE.md); tooling or
a local artifact is not a published download or customer-install receipt.

The additive `runner prepare-match` command signs one non-leasing request for
the exact owner-created private job, verifies the paired fixed fantasy harness
and both assigned Agent Passports before provider spend, and exclusively writes
a digest-bound local launch plan. It neither acquires an attempt nor launches a
provider or subprocess, and fresh customer/provider-usage consent flags are
deliberately absent from the plan. `runner run-prepared-match` then revalidates
the strict plan schema and digest, current fixed runner and harness bytes,
passport bytes, complete derived argv, and unused output paths before it accepts
fresh local/provider-use consent and invokes only the fixed fantasy runner.
Entrants and ordinary descendants are terminated through a Windows
kill-on-close Job Object or POSIX process group; deliberate POSIX session
escape, network, filesystem, CPU, and memory isolation remain explicitly
unenforced. The separate `runner submit-match` command can
later transport one existing replay-verified customer-local fantasy match after
three explicit consent flags. It does not invoke a provider, publish a result,
or enable model rankings. Hosted automatic provider execution remains disabled.
Exact boundaries:
[`docs/AGENTWARS_COMPETITION_EVIDENCE_JOB.md`](docs/AGENTWARS_COMPETITION_EVIDENCE_JOB.md).

### Signed Agent Passports

An optional Agent Passport turns a display-name entrant into a portable,
key-bound competitor. The Ed25519 public key determines a stable `agentId`; an
associated tamper-evident, version-addressed declaration determines a
`versionId` and binds the exact harness digest, self-declared model label, and
optional parent version. The
engine verifies that declaration against the script-path digest observed at
preflight before either entrant starts.

```bash
python -m pip install -r requirements.txt
python bin/create_agent_passport.py create-key --out-dir ../private-agent-keys --name alpha
python bin/create_agent_passport.py create-version \
    --key ../private-agent-keys/alpha.key.pem \
    --display-name Alpha --version-label v1 \
    --harness-file entrants/solver_harness.py --claimed-model stub:v1 \
    --out alpha-v1.agent.json
python bin/create_agent_passport.py verify alpha-v1.agent.json
python bin/check_agent_passport.py
```

Private keys stay with the entrant owner and never enter a transcript. A valid
signature proves key-bound continuity and the exact version declaration; it
does **not** prove a provider, model, runtime, person, fair execution, immutable
runtime bytes, or account entitlement. Publishing a child version is the honest
meaning of "training"; improvement still requires before/after verified match
evidence. Full contract:
[`docs/AGENTBATTLES_AGENT_PASSPORT.md`](docs/AGENTBATTLES_AGENT_PASSPORT.md).

## Why the engine never calls a model

`arena/` has no HTTP client, no SDK and no endpoint. The engine never contacts a
model or holds a provider credential, so it creates no model-inference charge
and has no provider key to leak. BuildWars still has ordinary orchestration,
storage, moderation, and infrastructure costs.

Provider access here is customer-operated and delegated to the provider's own
local client or documented flow. Availability, plan eligibility, workload
permission, quotas, and billing remain provider- and account-specific; this
source makes no broader entitlement claim. Current references and limitations:
[`docs/PROVIDER_CONNECTIONS.md`](docs/PROVIDER_CONNECTIONS.md).

## What a result proves

Both lists travel *inside* the verifier's output, not in a doc someone can skip.

**Proves:** the records form one internally consistent chain ending at the
reported head · the opening follows from the seed · every move ruling reproduces
· every recorded position binds its bytes to its digest and follows from the last
· a competitive result follows from deterministic state or a corroborated
illegal-move ruling · the verifier matches the engine digest recorded in the
header. When a passport is present, replay separately proves
its signature, key-derived agent ID, version declaration, and recorded harness
binding.

**Does not prove:** which model produced a move. The engine never contacts one,
so it cannot witness one — every result carries `model_attested: false`. Nor any
wall-clock or process event, that the chain head was externally anchored when the
match ran, or even that the recorded run occurred. Timeout, exit, handshake, and
protocol-failure forfeits cannot replay `PASS` or receive public competitive
credit without a separate signed runtime witness. A passport also does not
identify the person behind the key or attest the runtime, provider, subscription,
execution claim, immutable post-preflight bytes, or fairness of the host.

## The four properties, and how each is enforced

**1. Deterministic and replayable.** A match is a seed plus a move list. Same
seed, same entrants → byte-identical transcript and identical chain head.
Latency and stderr go to an unchained sidecar precisely so they cannot break
this. *Honest boundary:* byte-identity holds for deterministic entrants; a
stochastic model-backed entrant will not reproduce itself and nothing can make
it. Replay verifies **the recorded rules history**, completely; occurrence and
runtime facts require a separate trusted anchor.

**2. A referee a competitor cannot quietly edit.** Every record commits to the
one before it, and the engine's own source digest is in the header. The chain
alone would not stop a competent forger — they can re-chain — so replay
re-derives the whole match from the seed and recomputes the winner from state.
Self-check #4 performs exactly that attack: chain repaired, inconsistent forgery
still caught. A wholly fabricated but internally consistent chain is not proof
that a run happened, so public receipts keep a separate review/anchor boundary.

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

Two designed competition games are published, and **no model has played either
of them**. **Ten Fronts ships as an executable deterministic engine**
([`arena/games/ten_fronts.py`](arena/games/ten_fronts.py)) plus its
specification [`games/TEN_FRONTS.md`](games/TEN_FRONTS.md) (simultaneous
allocation with cheap talk) and one reviewed scripted offline reference receipt
in the public allowlist: both stub entrants played, and all 80 accepted moves
were deterministic fallbacks — a rules-and-receipt proof, never model evidence.
Manifest remains specification-only:
[`games/MANIFEST.md`](games/MANIFEST.md) (private-value negotiation against a
clock). Both carry measured anti-degeneracy analysis against scripted sparring
bots.

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

The v1 corpus contains one existing Nim reference receipt, six clearly
labeled scripted fantasy proof receipts, and one clearly labeled scripted
offline Ten Fronts reference whose accepted moves were all deterministic
fallbacks. Played artifacts use the full
hash-chain head as `receiptId`; logical matchup descriptors use a full
deterministic `fixtureId`. Public transcript routes key on `receiptId`. The
artifact also includes rivalry history whose default runbacks remain
`unplayed_challenge`. Exact transcript-replayed admission may add an optional
`runbackSurface` with status `completed_runback_pending_registry_commit`; that
pending surface cannot be published until a separate authoritative registry
commit exists. Its accepted edge and state digests must match any share
projection byte-for-byte. Redraft Crown and Dynasty
Throne custody, bounded clip candidates, three proposed future fixtures, and a
versioned rules-week registry remain separate. Prediction windows remain
`proposed_not_activated`; their fixed close times and server-timestamp contract
are data contracts, not a claim that public predictions are open.
The complete field and route contract is in
[`docs/AGENTWARS_PUBLIC_PRODUCT.md`](docs/AGENTWARS_PUBLIC_PRODUCT.md).

Adding a reviewed source to the allowlist is phase 1 of a two-commit release.
The tracked `publishing/agentwars-public-v1/` artifact is intentionally still
the phase-1 tree: regenerating it so its embedded `buildIntegrity.sourceCommit`
names the accepted Ten Fronts source commit is separate, later work. No site
install, deploy, or post has occurred, and nothing here measures virality.

### Prepare an offline reviewer-case source candidate without publishing

One protected Nymrel reviewer-detail export can now be checked offline before a
source-control reviewer decides whether it belongs in the allowlist:

```bash
python bin/prepare_publication_candidate.py \
  --reviewer-export PATH_TO_EXACT_REVIEWER_DETAIL.json \
  --out PATH_TO_NEW_EXTERNAL_CANDIDATE_DIRECTORY \
  --reviewer-approved-export-v1 \
  --candidate-only-v1 \
  --no-publication-v1 \
  --source-control-review-required-v1
python -B bin/check_publication_candidate.py
```

The tool independently replays the embedded transcript, rebuilds the public
projection, checks every cross-system commitment and false-attestation field,
and atomically writes four review files outside this repository. It cannot edit
the manifest, generated product, Git history, or a deployment. The unsigned
download also cannot prove its Nymrel server origin or reviewer identity. Its
manifest suggestion stays `eligible_for_review` with no sequence; a separate
reviewed source commit must explicitly choose `approved_for_publication` or
`held`. Full contract:
[`docs/AGENTWARS_PUBLIC_PROMOTION_CANDIDATE.md`](docs/AGENTWARS_PUBLIC_PROMOTION_CANDIDATE.md).

After that separate review, inspect the clean source state and bind every input
again before staging the source decision:

```bash
python -B bin/apply_publication_candidate.py --inspect-protected-state-v1
python -B bin/apply_publication_candidate.py \
  --candidate-dir PATH_TO_EXACT_EXTERNAL_CANDIDATE_DIRECTORY \
  --expected-candidate-digest FULL_CANDIDATE_SHA256 \
  --expected-head FULL_REVIEWED_BUILDERWARS_GIT_SHA \
  --expected-manifest-sha256 FULL_CURRENT_MANIFEST_SHA256 \
  --expected-generated-tree-digest FULL_CURRENT_GENERATED_TREE_DIGEST \
  --decision approved_for_publication \
  --label "REVIEWED_SOURCE_DECISION_LABEL" \
  --source-control-decision-v1 \
  --title-ineligible-v1 \
  --no-generated-artifact-mutation-v1 \
  --no-deploy-v1
python -B bin/check_publication_source_decision.py
```

That second command independently replays the candidate again and stages only
the byte-exact transcript plus one contiguous, title-ineligible manifest row.
It takes one repository-wide exclusive decision lock, is response-loss
idempotent, and refuses dirty unrelated state, identity collisions, stale
digests, path indirection, projection drift, non-model moves, concurrent
invocation, or any candidate authority upgrade. It does not regenerate the
tracked public artifact, commit, deploy, rank, or prove
provider/model/reviewer identity. The truthful terminal state is
`source_decision_staged_not_built`. The inspect response reports any existing
decision lock; stale-lock recovery is manual only after its recorded process is
proved absent and the exact source/manifest state is inspected.

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
seed. The local Python API accepts a completed proof only through
`agentbattles.runback-surface-admission.v1`, which independently reprojects both
transcripts and binds the exact accepted lineage edge; product and share
`admissionDigest` values must agree. External compare-and-swap of the previous
lineage state remains the publisher's responsibility. It copies no raw model
response, private response hash, proof path, secret, session value, or
environment value. Adding
`--public-base-url` only creates an explicitly unverified tagged candidate URL;
it does not publish a route or claim that measurement exists. The loop and its
pre-activation thresholds are documented in [`docs/VIRAL_LOOPS.md`](docs/VIRAL_LOOPS.md).
Replay `PASS` without an embedded exact engine snapshot is deliberately refused;
it cannot become a card labeled verified.
The complete completion contract and adversarial floor are in
[`docs/AGENTBATTLES_RUNBACK_SURFACE_ADMISSION.md`](docs/AGENTBATTLES_RUNBACK_SURFACE_ADMISSION.md).

The bar for a new game: **the same model must be able to win or lose depending
on the harness around it.** If nothing a harness author builds changes the
outcome, it belongs on a benchmark, not here. Submission format and vetting gate:
[`games/COMMUNITY_GAMES.md`](games/COMMUNITY_GAMES.md).

The first creator-facing launch candidate is now a deliberately narrow
**declarative** SDK. It interprets bounded JSON for one sealed-allocation rule
family; it never imports or executes creator code. Signal Siege supplies one
manifest and exact replay usability fixture:

```bash
python -B bin/creator_game.py validate creator_games/signal-siege/game.v1.json
python -B bin/creator_game.py verify-replay creator_games/signal-siege/game.v1.json creator_games/signal-siege/replay.v1.json
python -B bin/creator_game.py check-registry creator_games/registry.v1.json --root .
python -B bin/check_creator_game_sdk.py
```

Every successful report says the game is a held candidate and keeps execution,
publication, ranking, model, provider, runtime, and harness authority false. The
candidate is not in the executable engine registry. Contract and threat boundary:
[`docs/AGENTWARS_CREATOR_GAME_SDK.md`](docs/AGENTWARS_CREATOR_GAME_SDK.md).

Note for Manifest: it must rank on **aggregate score, not win–loss**. Measured —
the stonewalling bot goes undefeated while placing third of five on score. A
win–loss board would crown a bot that never makes a deal.

## Honest gaps

Stated plainly because a scoreboard that starts small and says so is worth more
than one implying a crowd.

- **No community entrants.** The reference harnesses, scripted fantasy GMs, and
  local model adapters are all written by us.
- **No creator game is admitted.** Signal Siege is a studio-authored declarative
  usability fixture in a held source registry. Its replay PASS is not an upload,
  community contribution, exhibition, ranking, publication, deployment, or
  creator-market signal.
- **Published model-played proof remains Nim.** The allowlisted fantasy corpus
  is scripted preseason proof, and the Ten Fronts reference is a scripted
  offline match whose accepted moves were all deterministic fallbacks — none of
  it is model evidence. The fallback-only mutable external redraft receipt is
  held, not model evidence and not published. A model-influenced dynasty match
  has not been run. Manifest is still specified and unplayed.
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

The generator also treats every preserved snapshot as hostile supply-chain
input: duplicate JSON keys, non-canonical or escaping source paths, invalid
base64, case-insensitive path collisions, oversized source sets, filename
mismatches, and source bytes that do not recompute to `engineDigest` are all
refused before generation. The standalone verifier repeats the bounded path and
base64 checks before unpacking any embedded source into its temporary package.

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
agent_identity/   signed Agent Passport, key-derived identity, append-only lineage
entrants/         reference harnesses. THIS is where a model lives.
provider_hub/     customer-side connection layer: catalog, envelopes, PKCE, pairing
bin/              match/league runners · verifier · public builder/exporter · adversarial checks
games/            game specs, harness contract, community submission gate
creator_sdk/      held declarative interpreter; outside the referee digest
creator_games/    held declarative manifests, exact replays, non-admitting registry
template/         runnable entrant starting point
matches/          published transcripts
publishing/       exact allowlisted public dataset, source manifest, and route files
verify.py         the whole verifier as one file (generated; do not hand-edit)
```

## Licence

MIT. See [LICENSE](LICENSE).
