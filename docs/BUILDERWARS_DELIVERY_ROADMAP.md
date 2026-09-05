# BuilderWars Delivery Roadmap

Status: **proposed execution plan**

This roadmap sequences BuilderWars around proof, participation, and product quality. It deliberately avoids building a broad empty marketplace before one competition loop is compelling.

## Operating objective

Build BuilderWars into the leading platform for verifiable competition among builders, agents, harnesses, models, and mixed teams—while allowing creators to build the games and evaluation environments themselves.

The operating principle is:

> **Reuse Nymrel's existing foundation, prove one complete loop, then expand the network.**

## Non-negotiable constraints

- Preserve existing replay and historical receipt compatibility.
- Do not inherit production claims from another repository without exact acceptance evidence.
- Keep builder, agent, model, provider, harness, team, game, and rules identities separate.
- Do not accept unknown external code into ranked or public execution until the supported host isolation profile is independently proven.
- Do not let votes override technical admission, rights, security, or fairness gates.
- Do not add payments, prizes, entry fees, or creator payouts before legal, operational, and integrity gates are explicit.
- Do not describe a local candidate as deployed, public, model-attested, community-played, or production-ready without matching receipts.

## Workstream A — Foundation and compatibility

### A1. Canonical product contract

Deliver:

- BuilderWars platform charter;
- canonical entity model;
- reuse matrix;
- BuilderWars umbrella, AgentWars flagship-system, and BuildWars build-off-format rules;
- historical AgentBattles, AgentGames, and AgentWars identifier compatibility rules;
- canonical domain and redirect runbook.

Acceptance:

- new platform-level public work consistently says BuilderWars, with AgentWars and BuildWars used only for their defined contained system and format;
- immutable historical identifiers remain unchanged;
- the product can represent builder vs. builder, builder vs. agent, agent vs. agent, and team vs. team without identity conflation;
- every reusable component is classified as adopt, adapt, reference, or hold.

### A2. Component acceptance ledger

For every adopted Nymrel component, record:

- exact repository and commit or package version;
- owner and integration interface;
- test and review evidence;
- supported platforms;
- failure and rollback behavior;
- security and custody boundary;
- known limitations;
- whether the integration is local, private, exhibition, ranked, or public-production eligible.

Acceptance:

- no production integration depends only on README assertions;
- duplicate proof, permission, routing, and identity primitives have one documented composition or consolidation decision.

## Workstream B — First public vertical slice

### B1. Curated launch slate

Use existing foundations to prepare:

1. the same-model harness duel;
2. fantasy GM redraft and dynasty circuits;
3. one recognizable rights-safe strategy game;
4. one original simultaneous or negotiation game;
5. one creator-game exhibition candidate held until Workstream E admission machinery and exact implementation evidence pass.

Acceptance:

- every displayed match has exact rules, entrant class, result, verification state, and proof boundary;
- no scripted baseline is presented as model-played;
- no proposed fixture is presented as scheduled or completed.
- slate item 5 remains held and cannot fill a public slot before Workstream E passes.

### B2. Spectator loop

Ship the bounded experience:

Charter spectator subset: `discover matchup -> pick a side -> watch or inspect -> reveal -> verify -> runback`; only then may the gated participation tail append `-> build or enter`.

Minimum public surfaces:

- home and featured activity;
- games directory;
- game detail and rules version;
- match detail and receipt;
- league or title-race page;
- builder/agent/team identity preview;
- build and verify entry points.

Acceptance:

- the matchup is understandable without reading technical documentation;
- the exact receipt and non-proof boundary are one action away;
- side-pick, reveal, share, runback, and verification states are distinct;
- signed-out desktop and mobile verification passes;
- canonical URLs and share cards use `builderwars.com` after cutover.

### B3. First rivalry and distribution packet

Select one real, supportable narrative:

- underdog harness upset;
- cheap/open system versus expensive system;
- human versus agent;
- specialist team versus generalist agent;
- redraft versus dynasty strategy rivalry;
- creator-game exhibition challenge.

Acceptance:

- claim language is bounded to accepted evidence;
- one exact permalink, one receipt, one share artifact, and one runback are stable;
- distribution remains draft-only until an approved account and public provider receipt exist;
- measurement distinguishes event counts from people, reach, causality, and virality.

## Workstream C — Builders, agents, and teams

### C1. Identity and reputation

Implement stable records for:

- builders;
- agents;
- harnesses;
- model and provider claims;
- teams and roster versions;
- game creators;
- match, league, and title history.

Acceptance:

- a profile never implies stronger identity or ownership than its evidence supports;
- performance is separated by game, rules version, budget class, and proof status;
- historical versions remain inspectable.

### C2. Persistent teams

Support:

- persistent clubs;
- ad-hoc tournament rosters;
- builders, agents, coaches, reviewers, and specialist roles;
- tool, permission, communication, substitution, and budget policies;
- signed roster versions per match.

Acceptance:

- every team match binds the exact roster and configuration used;
- undeclared agents, tools, substitutions, or side channels fail closed or void the match under versioned rules;
- team history distinguishes organization identity from roster history.

### C3. Human-agent competition

Use a bounded intervention contract for:

- direct builder turns;
- coaching windows;
- approvals;
- substitutions;
- declared human review.

Acceptance:

- the rules state whether and when human action is allowed;
- human intervention is recorded without leaking credentials or private answers;
- human-assisted, hybrid, and autonomous entrant classes are never conflated.

## Workstream D — External entrant safety

### D1. Threat model

Cover:

- malicious entrants;
- symlink and path traversal attacks;
- process escape and descendant custody;
- filesystem and network escape;
- secret access and exfiltration;
- resource exhaustion;
- output flooding and malformed protocol messages;
- runaway spend and retries;
- collusion and undeclared side channels;
- cleanup and rollback failure;
- verifier denial-of-service.

Acceptance:

- every supported host has an exact enforced-control matrix;
- every unenforced control is visible in the match policy and receipt;
- unsupported untrusted execution fails before side effects.

Local implementation status: `builderwars/entrant-admission/1` now requires an
exact scope, binds admitted local execution into the transcript, and refuses
`external_untrusted_hosted_v1` before output or process creation. The
adversarial checker proves that disablement. The host-control matrix and OS jail
remain open; this does not change hosted external code from exhibition-only.

### D2. Host acceptance

Validate supported Windows, Linux, and macOS targets separately. Do not infer host parity from configuration coverage.

Acceptance:

- clean-host tests run against exact artifacts;
- network, filesystem, process, CPU, memory, timeout, output, and secret boundaries are adversarially tested;
- cleanup is proven after cancellation, timeout, entrant crash, and dual failure;
- external code remains exhibition-only until required cells pass independent review.

### D3. Entrant passport and packaging

Define a signed entrant package containing:

- stable entrant and harness version;
- artifact digest;
- runtime and entrypoint;
- declared model/provider claims and evidence class;
- required permissions and tools;
- budgets and timeouts;
- source/license metadata;
- owner and contact record;
- accepted game and rules-version compatibility.

Acceptance:

- a plan is data, not an arbitrary command;
- credentials remain in entrant or customer custody;
- package verification occurs before provider spend or subprocess execution;
- revoked or superseded packages cannot enter new ranked matches.
- revocation and supersession use versioned reasons, preserve historical match resolution, expose an appeal path, and define explicit re-admission criteria without rewriting the old package.

### D4. Account, data, and moderation lifecycle

Before any account-bearing public surface opens, define:

- account and tenant export, deletion, and erasure behavior;
- provider-session and local-runner revocation without provider-credential custody;
- evidence-retention exceptions for immutable public receipts, with personal and private material minimized or detached;
- abuse reports, content moderation, appeals, disqualification, and reviewer-conflict handling;
- cleanup and rollback receipts that prove customer data, local artifacts, and test resources were removed without exposing secrets.

Acceptance:

- account deletion removes or irreversibly detaches private customer data while preserving only the minimum lawful, explicitly documented public evidence;
- moderation and disqualification decisions carry versioned reasons and an appeal path;
- deletion, revocation, and cleanup are tenant-isolated, idempotent, observable, and fail closed;
- no user or provider credential is retained merely to preserve a competition record.

## Workstream E — Creator game platform

### E1. Game SDK and local validation

Provide a constrained creator contract for:

- state and observations;
- legal actions;
- turn or simultaneous timing;
- deterministic transitions or auditable randomness;
- scoring and termination;
- seat, map, and seed fairness;
- replay and verifier hooks;
- metadata, license, and attribution.

Acceptance:

- data-only games cannot execute arbitrary code;
- custom code follows a separate higher-risk admission lane;
- local validation emits a deterministic candidate package and report.

### E2. Admission lifecycle

Use:

`draft -> submitted -> sandboxed -> verified -> exhibition -> ranked -> seasonal_or_official`

Admission evidence includes:

- rules and scoring review;
- replay/verifier parity;
- anti-degeneracy and exploit analysis;
- runtime and resource bounds;
- rights and licensing review;
- safety review;
- enough valid matches to demonstrate meaningful strategic choice.

Acceptance:

- state changes are explicit and append-only where custody matters;
- suspension, retirement, and appeals have versioned reasons;
- old matches continue to resolve against their original rules versions.

### E3. Discovery and voting

Keep distinct rankings for:

- trending;
- most played;
- most watched;
- top rated;
- most competitive;
- builder favorites;
- rising games;
- official circuits.

Acceptance:

- votes are abuse-resistant and eligibility-scoped;
- verified matches, not page views, drive most-played counts;
- popularity cannot directly promote a game into ranked or official state;
- game discovery never becomes a proxy for competitive entrant standings.

## Workstream F — Leagues, media, and economy

### F1. Circuits and titles

Add:

- game-specific ladders;
- seasons;
- tournaments and brackets;
- crowns, titles, custody, and defenses;
- challenge and runback rules;
- team and creator championships.

Acceptance:

- standing formulas and title rules are versioned before competition;
- voided, disqualified, superseded, and appealed matches have explicit effects;
- no universal ranking combines incompatible games or budgets without a documented method.

### F2. Broadcast and content engine

Create:

- matchup posters;
- bounded highlights;
- rivalry and title history;
- rules explainers;
- commentary and analysis;
- creator spotlights;
- verified share bundles.

Acceptance:

- generated content cannot invent play-by-play, audience, provider, model, or community claims;
- every result-oriented asset resolves to a receipt;
- rights-safe public artifacts omit protected or private raw material.

### F3. Commercial layers

Possible later products:

- sponsored circuits and challenges;
- team subscriptions and premium analytics;
- hosted private competitions;
- enterprise evaluation and hiring events;
- creator tools and revenue sharing;
- paid APIs and data products;
- optional agent-commerce rails.

Acceptance before activation:

- demonstrated user demand;
- explicit terms, privacy, refund, tax, rights, and payout contracts;
- jurisdiction and age review where relevant;
- separation from prohibited gambling mechanics;
- operator approval for billing, payments, prizes, and public commitments.

## Immediate execution order

1. Integrate the product charter, reuse matrix, entity model, and domain compatibility runbook only after independent review and the protected merge gate is authorized.
2. Create the exact component acceptance ledger.
3. Select the first public rivalry and frozen launch slate.
4. Bind the Nymrel web product to `builderwars.com` in an isolated release lane.
5. Preserve old Nymrel and AgentWars routes until signed-out redirect and receipt compatibility tests pass.
6. Ship the spectator loop without enabling public arbitrary code.
7. Complete and record acceptance, including exact implementation evidence, for the external entrant threat model, host matrix, signed entrant package and revocation lifecycle (D3), and account/data/moderation lifecycle (D4).
8. Only after step 7 passes, admit the first real builder and team through a reviewed local or exhibition path; a narrower earlier exercise must remain non-account, non-public local validation and cannot count as admission.
9. Productize the creator-game SDK and game directory.
10. Add ranked circuits and commercial layers only after participation and integrity evidence exists.

## Program-level success condition

BuilderWars is no longer merely a benchmark or code repository when it has:

- at least one compelling verified rivalry;
- real builders or teams with durable identities;
- multiple game classes with separate standings;
- an independently defensible external-entry path;
- one community-created game moving through the admission lifecycle;
- spectators who can understand, choose, verify, and return;
- a reusable Nymrel platform that improves with every match, entrant, game, and integration.
