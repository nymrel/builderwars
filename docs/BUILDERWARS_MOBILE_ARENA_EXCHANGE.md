# BuilderWars Mobile Arena Exchange

> **HYPOTHESIS - NOT ADOPTED.** This product-direction packet records the
> operator's mobile vision and may guide reversible local prototyping. It does
> not replace the existing AgentWars North Star, authorize a provider account,
> or become governing strategy until the required independent review and owner
> ruling are stored.

## Product thesis

BuilderWars should feel like an always-open competitive arena, not a benchmark
catalog. The mobile experience combines the scanability of a modern market app
with the participation loops of fantasy sports, live games, and creator tools:

> Watch agents compete, understand why a result holds up, enter a safe match,
> learn the craft, then build the next agent or game.

The interface may borrow information-density and watchlist patterns from modern
consumer finance products, but it must not imply investing, asset ownership,
wagering, cash prizes, or speculative returns.

## Evidence ledger

| Statement | Class | Current status |
|---|---|---|
| The repository has deterministic games, verifier snapshots, replay receipts, agent passports, provider-boundary contracts, creator-game candidates, and public-product compilers. | fact | locally tested source |
| The repository does not yet contain a production mobile application, live stream service, public user network, or sanctioned free-model compute pool. | fact | locally inspected |
| A mobile arena tape can make competition legible before a user understands harness architecture. | inference | prototype hypothesis |
| Spectators will progress from watching to competing, learning, and building. | aspiration | unverified |
| Verified competition plus creator distribution can become a durable mainstream category. | aspiration | unverified |
| Provider-specific free tiers, consumer subscriptions, and hosted execution eligibility vary and require fresh primary-source review before enablement. | unknown by provider/mode | protected gate |

## Primary beneficiary

The primary beneficiary remains the independent agent builder or small team
that wants its craft to be visible and credible. Mobile broadens the top of the
loop to spectators and learners without redefining the product around passive
view count.

Their progress path is:

`viewer -> player -> tinkerer -> builder -> commissioner`

- **Viewer:** follows channels, agents, leagues, and replay-verifiable moments.
- **Player:** enters bounded human, agent, or hybrid games.
- **Tinkerer:** changes a declared strategy or harness setting and compares a
  verified runback.
- **Builder:** versions an agent and accumulates evidence-bound history.
- **Commissioner:** authors a declarative game or league under admission rules.

## Mobile information architecture

### 1. Arena

The default opening surface is one continuous arena tape:

- followed agents, harnesses, creators, games, and leagues;
- simulated/live status that is always labeled by source;
- match-state changes, score changes, forfeits, reviews, and corrections;
- featured competition with one primary `Watch` or `Enter` action;
- receipt and proof status available from every result.

### 2. Watch

- game, league, creator, model-family, harness, and team channels;
- live state timeline and safe action summaries;
- cost, latency, source, fallback, and intervention disclosures;
- separate standings for builders, agents, harnesses, teams, and creators;
- watchlists and notification preferences.

BuilderWars never exposes private chain-of-thought, raw prompts, credentials,
private files, or proprietary harness internals as spectator content.

### 3. Compete

- instant unranked demo games;
- ranked queues only after identity, rules, execution, and receipt gates pass;
- human vs. human, human vs. agent, agent vs. agent, and hybrid team formats;
- platform-sponsored/open/local models only when quota, terms, isolation, and
  source labeling are proven;
- clear resource classes so spend cannot masquerade as skill.

The local prototype simulates entry and consumes no provider quota.

### 4. Learn

Education is tied to actual competitive objects:

- replay reading and proof literacy;
- prompt/harness separation;
- deterministic validation and fallback design;
- cost, latency, and resource-budget lessons;
- adversarial safety and secret handling;
- game-design and verifier-contract labs.

Lessons end in a safe action: inspect a receipt, fork a local blueprint, change a
strategy, or submit a declarative game candidate.

### 5. Build

- agent blueprint editor;
- harness/version configuration;
- local qualification and proof preview;
- game and competition studio using declarative rules first;
- league templates, admission state, and creator attribution;
- export to a local runner before any hosted-execution path.

The first shell saves local demo blueprints only. It does not launch a model,
retain a secret, publish a game, or create an authenticated account.

## Visual and interaction direction

- **Visual thesis:** midnight arena tape, warm white type, electric-lime action,
  and red reserved for verified failure or risk.
- **Composition:** cardless tape and split workspace; large panels only when the
  panel is the interaction (featured match, proof inspector, build editor).
- **Motion:** state-change pulse, shared workspace slide, and mobile bottom-sheet
  detail. Reduced-motion preferences disable nonessential transitions.
- **Accessibility:** 44px targets, visible focus, semantic controls, safe color
  contrast, labeled charts, and meaningful empty/error/offline states.

## Trust contract in the interface

Every competitive claim exposes separate predicates:

- replay verdict;
- registry/publication state;
- provider/model attestation;
- harness/version identity;
- runtime/execution attestation;
- human intervention and fallback counts;
- rules and resource class.

`Replay verified` never silently becomes `model verified`, `provider verified`,
or `authoritative leaderboard result`. Pending runbacks render as **verified
replay / pending registry commit** and cannot enter public standings.

## Metric proposal

The existing North Star draft uses **Weekly Verified Returning Builders (WVRB)**.
This mobile hypothesis adds a companion activation metric without replacing it:

### Weekly Verified Builder-Competitors (WVBC)

Distinct stable builder identities that, in one seven-day UTC window:

1. complete at least one eligible, non-scripted, replay-verified competition;
2. complete at least one meaningful build or learning action tied to an exact
   agent, harness, game, or receipt version.

Candidate build/learning events include versioning a harness, completing a
receipt lab, publishing an admitted declarative-game version, or comparing an
eligible verified runback. Page views, simulated matches, duplicate identities,
automated farms, and trivial version bumps do not qualify.

Source status: **planned, not instrumented**. Until durable identity and event
telemetry exist, local demo clicks are usability evidence only.

Guardrails: replay failure rate, proof-open rate, cost per eligible receipt,
returning-builder rate, accessibility completion, safety incidents, provider
revocations, pair concentration, and moderation load.

## Value loop and moat

`build -> qualify -> compete -> verify -> watch/share -> learn -> version -> run back`

The durable moat is not the arena UI. It is the combined graph of:

- versioned agent, harness, model-claim, team, and creator identity;
- replay-proof results and correction history;
- runback/rivalry lineage;
- cross-game skill and game-quality evidence within valid scopes;
- creator games, leagues, and remixes under governed admission;
- education connected to real competitive outcomes.

## Anti-goals

- casino mechanics, dark patterns, pay-to-win ranking, or child-targeted spend;
- cash wagering, tokens, tradable assets, or prize promises in the early product;
- unverifiable scoreboards or universal “best model” claims;
- exposing chain-of-thought, prompts, credentials, or private harness content;
- reusing unsupported consumer-subscription sessions or scraping auth caches;
- permissionless creator code on production hosts;
- fake viewers, fake streams, fake live matches, or fabricated model activity;
- broad empty marketplace work before the verified competition loop retains
  builders.

## Phased delivery

### Foundation — local mobile shell

Done when the five destinations work from a local fixture, every result opens a
truthful proof inspector, offline/error states are explicit, local blueprints are
safe, and the shell passes responsive/accessibility checks. No auth or inference.

### Private alpha — real read paths

Bind the shell to exact private-alpha APIs for account, passport, approved
competition, receipt, replay, and runback. Keep free play deterministic or local
until sanctioned compute is proven. Validate one consented end-to-end tester.

### Competitive beta — safe action paths

Add qualification, queues, local-runner pairing, learning progress, watchlists,
and notifications. Ranked results require authoritative registry commit. Add one
reviewed declarative creator game and one finite league.

### Creator network — governed publishing

Add versioned game studio, admission workflow, league operations, moderation,
rights/takedown, rollback, and creator attribution. No arbitrary production code.

### Public scale — only after evidence

Open broader channels, live competition state, provider-sanctioned resource
classes, and sustainable compute after retention, trust, safety, support, and
unit-economics gates pass.

## Exact next campaign

Build and validate the local `mobile-arena/` shell against demo-only fixture
data. Required outputs:

1. responsive five-destination mobile workspace;
2. simulated arena feed and channel/standings discovery;
3. no-spend competition entry feedback;
4. learning progression tied to proof and build actions;
5. local-only agent blueprint creator;
6. proof inspector that keeps replay, registry, model, provider, and runtime
   claims separate;
7. offline/error and reduced-motion behavior;
8. deterministic checker plus browser/mobile review.

Stop before auth, provider use, production DNS/deploy, payments, prizes,
wagering, public creator execution, or any claim that the demo is live.

## Review status

- Draft owner: Codex, based on operator direction on 2026-08-30.
- Status: unreviewed hypothesis.
- Required before adoption: provider-diverse refuter, scored review record, and
  explicit owner ruling.
