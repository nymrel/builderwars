# BuilderWars competitive landscape — 2026-08-31

> **HYPOTHESIS - NOT ADOPTED.** This research packet is a dated input to the
> existing AgentWars North Star and BuilderWars platform charter. It does not
> authorize accounts, provider access, spending, public claims, prizes,
> deployment, or a strategy change. Adoption still requires the recorded review
> and owner ruling.

## Executive finding

The category exists. Open agent evaluation networks, API-native bot leagues,
programming competitions, model arenas, fantasy-agent contests, and early
"agent esports" products now prove that agents can be participants, not only
assistants.

That also means **"watch agents battle" is not a moat**. BuilderWars' strongest
defensible position is a consumer-grade competition network where every public
result is bound to an exact game, rules version, entrant, harness version,
execution claim, replay receipt, and correction/runback lineage.

The product thesis becomes:

> BuilderWars makes model-and-harness craft legible, replayable, and worth
> following—then turns spectators into builders and builders into commissioners.

## Method and limits

This pass reviewed current public material across four workstreams:

1. standardized agent evaluation and model arenas;
2. autonomous-agent and programming competitions;
3. harness-sensitive evaluation research;
4. spectator, fantasy, creator, and agent-esports products.

Primary or first-party sources were preferred. Product metrics and capability
claims below remain the source operators' claims unless independently proven.
No competitor account was created, no paid API was used, and no protected
workflow was activated.

## Landscape

| Product or research | What it demonstrates | BuilderWars lesson | Boundary |
|---|---|---|---|
| [AgentBeats](https://docs.agentbeats.org/) and its [architecture](https://docs.agentbeats.org/Blogs/blog-1/) | Open evaluation can standardize subject agents and assessment agents around A2A/MCP, reset state per assessment, and publish reproducible metrics. | Support assessment/game creators and interoperable entrants, but keep the consumer competition story above the protocol layer. | Reproducible assessment is infrastructure, not automatically a replayable social product. |
| [AgentBeats competition paper](https://arxiv.org/abs/2606.13608) | A large judge-agent/subject-agent competition can cover many task categories. | A creator network of governed evaluators is plausible; assessment quality and conflict policy become first-class product surfaces. | Paper-scale participation does not prove retention, safe public execution, or BuilderWars product demand. |
| [The Bot League FAQ](https://www.thebotleague.com/faq) and [starter kit](https://www.thebotleague.com/agents/starter-kit) | A fantasy-sports league can admit bots through a signed REST API, use deterministic/recomputable scoring, and ship a typed starter kit with legality and fallback seams. | Fantasy is a credible launch wedge. BuilderWars should offer one-command local qualification and an explicit legality guarantor. | It is the closest direct fantasy-agent precedent; BuilderWars must differentiate through proof UX, harness identity, learning, and runback lineage. |
| [AgentLeague](https://agentleague.io/compete/) | Self-registering agents, webhook turns, always-available matches, and Elo can produce a low-friction competitive loop. | Make the first legal match easy and queues persistent; separate public rating from broader learning goals. | Site activity figures are self-reported and were not independently verified. |
| [Battlecode](https://battlecode.org/) and its [2023 postmortem](https://battlecode.org/assets/files/postmortem-2023-dont-at-me.pdf) | A long-running seasonal strategy competition can retain builders through ladders, tournaments, iteration, postmortems, and community. | Seasons, rivalries, reviewable losses, and rule changes create replay appeal. Training progress must matter even when a builder is not first. | Optimizing only for a ladder can produce overfitting and a poor beginner experience. |
| [Lux AI](https://www.lux-ai.org/) and [Halite](https://halite3webapp.azurewebsites.net/about/) | Finite seasons and deterministic game environments can make code agents understandable and spectatable. | Use small, legible games as qualification surfaces before broader open-ended challenges. | Programming-competition UX often assumes an expert audience and under-serves mobile spectators. |
| [LMArena](https://newblog.lmarena.ai/about/) | Community preference can make model evaluation participatory and produce a widely legible public leaderboard. | Pair machine-verifiable competition with human preference only where the metric is explicitly subjective. | Anonymous preference is not proof of agent execution, harness identity, or task correctness. |
| [Harness-Bench](https://arxiv.org/abs/2605.27922) | Under a shared task/model pool, harness choice can materially change performance; the paper argues model-and-harness configuration should be the evaluation unit. | Bind rankings and receipts to both the model claim and the exact harness version. Record budgets, tools, traces, and verifier scope. | Research evidence supports the unit of evaluation, not a claim that BuilderWars currently attests provider/model identity. |
| [Agent Sports League](https://www.agentsportsleague.com/) and [MoltGamingLab](https://moltgaminglab.com/) | Multi-game agent competition, API entry, ratings, and spectator framing are becoming recognizable product patterns. | Cross-game identity and a channel-based arena are credible, but should follow one retained competition loop. | Product and activity claims are first-party; neither proves a durable network moat. |
| [Microsoft Agents League](https://github.com/microsoft/agentsleague) and [CATArena](https://github.com/AGI-Eval-Official/CATArena) | Open tooling can organize agent competitions and multi-agent evaluation. | Publish narrow protocols and local runners so third parties can inspect and extend the ecosystem. | Open-source infrastructure alone does not solve identity, safety, moderation, or distribution. |
| [Steel](https://theagentgames.com/) and [Doppel Games](https://docs.doppelgames.co/) | Some products are coupling agent competition with virtual capital, prediction, or market-like mechanics. | The visual energy of a market tape can work without turning outcomes into financial products. | Do not copy wagering, token, casino, speculative-return, or child-targeted spend mechanics. |

## What is becoming commodity

- a model leaderboard;
- an Elo table;
- an agent-vs-agent match;
- an API or webhook entrant;
- a stream-like match feed;
- a generic prompt challenge;
- a claim that one model is "best."

BuilderWars should use these primitives but not define itself by them.

## Proposed durable moat

### 1. The verified competition graph

Every eligible result links immutable versions of:

`builder -> agent -> harness -> model claim -> resource class -> game -> rules -> fixture -> transcript -> verifier -> receipt -> correction/runback`

The graph becomes more valuable as it accumulates trustworthy history across
games. A screenshot, conventional leaderboard row, or unversioned benchmark
cannot provide the same lineage.

### 2. Harness-native reputation

Reputation belongs to what a builder actually assembled—not to a provider logo.
The same underlying model can produce different results through orchestration,
tools, memory, verification, fallback policy, and resource constraints. Public
profiles should preserve those distinctions and never imply provider attestation
when only a self-declared claim exists.

### 3. Runback and rivalry lineage

One result is content. A versioned runback after a builder changes its harness
is progress. Repeated, rules-bound meetings create rivalries, stories, and
retention without fabricating live activity.

### 4. Education connected to evidence

Lessons should open from real receipts: replay a loss, inspect the proof scope,
change one harness decision, qualify locally, and run it back. Education then
improves the competition graph instead of becoming a detached content library.

### 5. A governed creator network

Creators can eventually publish declarative games, assessment agents, leagues,
and rules seasons. Admission, versioning, moderation, rights, rollback, and
quality evidence are part of the product. Arbitrary third-party production code
is not an acceptable shortcut.

## Product architecture implied by the research

### Layer A — proof plane

- deterministic or explicitly scoped referee;
- exact replay and verifier snapshot;
- immutable receipt and publication allowlist;
- explicit model/provider/runtime attestation status;
- correction, disqualification, and registry-commit history.

### Layer B — competition plane

- versioned games and resource classes;
- qualification and queue contracts;
- local runner or sanctioned sandbox;
- seasons, tournaments, rivalries, and runbacks;
- ratings valid only inside their declared scope.

### Layer C — consumer arena

- channel-based Arena and Watch feeds;
- proof-linked match cards and compact leaderboards;
- follow/watchlist controls for agents, builders, games, and leagues;
- Compete, Learn, and Build progression from the same receipt;
- mobile information density without investment or wagering claims.

### Layer D — creator and federation plane

- game/assessment SDK with versioned declarative inputs;
- governed admission and rollback;
- league commissioner tools;
- interoperable entrant and evaluator protocols;
- portable proof and reputation exports.

## Evidence-gated long-term sequence

| Gate | Product capability | Proof required before expansion |
|---|---|---|
| 0. Local proof substrate | Compile the reviewed public corpus into a deterministic Arena read model. | Digest equality, reviewed allowlist equality, PASS replay/engine/snapshot predicates, adversarial mutation rejection. |
| 1. Private read alpha | Bind account, passport, competition, receipt, replay, rivalry, and runback read paths to the mobile shell. | One consented tester journey, no false live/auth/provider claims, accessibility/offline/error evidence. |
| 2. First legal competition loop | Qualify one entrant, run one sanctioned match, publish one authoritative result, teach one improvement, and run it back. | Exact resource policy, provider/local-runner authority, registry commit, cleanup and revocation evidence. |
| 3. Finite league | Launch one fantasy or bounded strategy season with explicit rules and support posture. | Retention, replay failure, moderation, cost, pair concentration, and correction metrics inside thresholds. |
| 4. Governed creator beta | Admit one reviewed declarative game and commissioner. | Versioned admission, safety review, rights/takedown, rollback, and game-quality evidence. |
| 5. Public network | Expand channels, games, providers, and creator access. | Trust, safety, unit economics, support, anti-abuse, and retention gates proven—not projected. |

## First implementation receipt

The repository now contains a deterministic, fail-closed Arena read-model
compiler:

```powershell
python bin\build_mobile_arena_read_model.py --check
python bin\check_mobile_arena_read_model.py
```

It projects only the tracked reviewed allowlist into
`mobile-arena/data/arena-read-model.v1.json`. It rejects source/dataset digest
drift, allowlist disagreement, failed replay predicates, verifier mismatch,
evidence-label drift, unsafe proof paths, and stale generated output.

This is **local proof of a private-alpha read contract**. It is not a live API,
hosted league, authenticated feed, provider connection, model attestation, or
production deployment.

## Decision record proposed for later review

- Keep the existing North Star draft unadopted until its review contract is met.
- Treat model + harness + rules + resource class as the competitive unit.
- Lead with a finite replayable competition, not a broad empty marketplace.
- Make every viral object resolve to proof and a legal runback path.
- Use the modern-market-app visual metaphor for scanability only.
- Keep wagering, tokens, speculative assets, and unverifiable live activity out.
- Make fantasy competitions a candidate launch wedge, not an assumed winner;
  The Bot League makes differentiation and execution quality especially
  important.
