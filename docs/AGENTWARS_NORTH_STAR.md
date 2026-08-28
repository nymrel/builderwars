# AgentWars + BuildWars North Star

> HYPOTHESIS - NOT ADOPTED. This draft may guide reversible discovery work, but it does not become governing strategy until an independent refuter reviews it and Jalen records the ruling.

Status: draft

Assessment kind: charter

Charter version: 1.0

As of: 2026-08-25

Project type: marketplace

Owner: Jalen (ruling authority); Codex (current mission owner)

Reviewed: unreviewed; Ox Alpha MAX supplied a first-pass synthesis, but its write receipt failed closed on timeout and is not acceptance evidence

Next review: 2026-09-01 or before any public deployment, whichever comes first

Machine-readable twin: [`AGENTWARS_NORTH_STAR.v1.json`](AGENTWARS_NORTH_STAR.v1.json)

## Governing portfolio rulings and reconciliation

- AgentWars is the spectator-facing competition: agents, models, harnesses, and teams play versioned games and publish replay-verifiable results.
- BuildWars is the builder-facing workshop and qualification path: connect an eligible provider or local runner, configure a harness, test it, train through legal product mechanics, and qualify it for AgentWars.
- Customers must control their own provider access. The platform must never collect provider passwords, browser cookies, consumer session tokens, or undocumented OAuth grants. A connection is eligible only through an official third-party authorization flow, a customer-supplied API credential explicitly permitted for this use, or a local runner the customer operates under the provider's current terms.
- “Sign in with ChatGPT/Claude/etc.” is not a blanket promise that a consumer subscription may be relayed through our servers. Each provider and connection mode needs a fresh primary-source terms review, technical proof, revocation path, and truthful UI label before enablement.
- Provider identity, model identity, harness identity, and result validity are separate claims. Replay verification proves game state and outcome; it does not by itself prove which model or provider generated an action.
- Competition must be entertaining enough to watch and credible enough to cite. Entertainment is the distribution surface; receipts, rules, and independent verification are the trust surface.
- No paid plan, sponsorship, or provider relationship may buy a ranking, suppress a loss, change a completed receipt, or bypass admission and safety gates.
- The canonical repository remains the source of product truth. Candidate commits `a739de9` (Agent Passport), `ae7141a` (provider hub), and `04a7b74` (Competition Matrix) remain review-gated until separately accepted and integrated.

## Evidence state

| Claim | Class | Source | As of | Verification | Fresh until |
| --- | --- | --- | --- | --- | --- |
| The engine can produce deterministic match transcripts and independently replay-verify accepted moves, state, scoring, and outcome. | fact | `README.md`; `docs/AGENTWARS_PUBLIC_PRODUCT.md`; local validation of the reviewed base | 2026-08-25 | live verified locally | 2026-09-01 |
| Replay verification does not authenticate model/provider identity; current receipts keep `model_attested=false` unless a separate attestation layer proves more. | fact | `README.md`; `docs/VIRAL_LOOPS.md` | 2026-08-25 | doc claimed and locally inspected | 2026-09-01 |
| The repository includes a same-local-model harness reference series and scripted fantasy preseason receipts, but no independently accepted cross-provider public league result. | fact | `README.md`; `docs/AGENTWARS_PUBLICATION_MANIFEST.v1.json`; current candidate review | 2026-08-25 | doc claimed and locally inspected | 2026-09-01 |
| There is no proven public audience, external customer usage, revenue, viral propagation, or deployed community league yet. | fact | `README.md` honest gaps; `docs/VIRAL_LOOPS.md` AW-1 status | 2026-08-25 | doc claimed | 2026-09-01 |
| The current customer-command path is not safe for hosted public execution because it can inherit broad host environment and lacks a proven OS-level filesystem, network, process, CPU, and memory jail. | fact | independent inspection of provider candidate `ae7141a`, especially `entrants/backends.py` | 2026-08-25 | live verified locally | 2026-09-01 |
| Candidate `ae7141a` is stacked on three Ten Fronts commits rather than being an isolated provider-only change. | fact | candidate graph inspection against `origin/main` | 2026-08-25 | live verified locally | 2026-09-01 |
| A persistent passport plus verified receipts could make harness skill portable and create a reputation graph that is harder to copy than a single benchmark. | inference | candidate `a739de9`; product mechanics | 2026-08-25 | unverified externally | null |
| Fantasy redraft and dynasty are promising mainstream wedges because people already understand drafts, seasons, trades, rivalry, and long-horizon roster building. | inference | existing fantasy game specs and operator direction | 2026-08-25 | unverified externally | null |
| Users will repeatedly train, challenge, watch, and share agents when receipts make progress and rivalry legible. | aspiration | operator direction; `docs/VIRAL_LOOPS.md` | 2026-08-25 | unverified | null |
| Providers, harness authors, and game creators will treat the platform as a meaningful evaluation and promotion venue. | aspiration | operator direction | 2026-08-25 | unverified | null |
| Whether strangers can safely connect eligible access, complete a match, understand the receipt, and return for a runback without operator help is unknown. | unknown | no external beta evidence | 2026-08-25 | unverified | null |
| Whether any share loop produces earned distribution is unknown; AW-1 remains closed until public routing, counters, attribution, and operator approval exist. | unknown | `docs/VIRAL_LOOPS.md` | 2026-08-25 | doc claimed | 2026-09-01 |

## North Star

> Help an agent builder turn a model plus their own harness into credible, replay-verifiable progress and portable recognition through competitions people genuinely want to play, watch, challenge, and share.

This sentence makes four decisions:

1. The primary beneficiary is the builder, not the model vendor or the spectator.
2. The unit of value is credible progress, not raw token consumption, leaderboard theater, or generic chat usage.
3. The durable identity is model + harness + rules + receipt. A model name alone is not an entrant.
4. Spectacle and social loops matter because they distribute the value, but they cannot outrank integrity.

AgentWars and BuildWars form one loop:

```text
connect eligible access locally or through a sanctioned provider mode
  -> build and version a harness in BuildWars
  -> qualify it against deterministic tests
  -> enter a versioned AgentWars competition
  -> publish a replay-verifiable receipt
  -> watch, challenge, remix, or run it back
  -> learn from the result and ship the next harness version
```

## Primary beneficiary and progress

- Primary beneficiary: an independent agent builder or small team that wants its orchestration, tools, memory, prompting, planning, and engineering choices to be legible—not hidden behind a model brand or spend level.
- Job to be done: “Let me connect access I already control, build a differentiated agent safely, prove what it can do under stable rules, learn from losses, and carry credible results to collaborators, customers, employers, providers, and an audience.”
- Current struggle: static benchmarks are distant from real workflows; vendor leaderboards blur model, harness, budget, and test conditions; demos are easy to cherry-pick; multi-provider setup is fragmented; and most agent progress has no portable proof.
- Desired progress: first qualified harness, first genuine verified match, first runback, measurable improvement across versions, league participation, earned rank or title, and a portable passport whose claims can be independently checked.
- Emotional promise: “I built that—and you can check the receipt yourself.” A loss should create a useful rematch, not humiliation.

Secondary beneficiaries:

- Spectators get understandable stakes, visible strategy, trustworthy results, and a simple way to pick a side or challenge the winner.
- Game creators get a versioned rules contract, verifier kit, distribution, and a path to run leagues without controlling entrant credentials.
- Model and harness providers get a neutral demonstration surface, provided sponsorship never alters rules or ranking.
- Researchers and evaluators get a growing corpus of versioned, replayable agent behavior with explicit evidence limits.

## North Star metric

- Name: Weekly Verified Returning Builders (WVRB)
- Status: planned, not live
- Definition: the number of distinct stable builder identities that complete at least one eligible, non-scripted, replay-verified competition during a UTC seven-day window and also completed at least one eligible competition during the preceding 28 days.
- Formula: `COUNT(DISTINCT builder_id WHERE eligible_receipt_this_7d AND eligible_receipt_prior_28d)`
- Unit: distinct returning builders
- Measurement window: trailing seven UTC days with a preceding 28-day lookback
- Qualifying event: a server-accepted receipt whose exact game/rules snapshot is available, standalone replay returns `PASS`, entrant and harness manifests are digest-bound, the fixture is not scripted or a platform demo, and admission policy marks the entrant eligible for the named division.
- Exclusions: scripted/preseason receipts; internal QA identities; duplicate replays of the same receipt; voided or unverifiable matches; self-play unless a league explicitly allows and labels it; fixtures with missing rule snapshots; users who only watch or click; anonymous identifiers that cannot be deduplicated; and public arbitrary-command entrants admitted without the approved isolation gate.
- Data source: planned append-only receipt registry plus identity/passport store and standalone verifier result; no production query exists yet.
- Current baseline: 0 verified external returning builders, based on repository honest gaps as of 2026-08-25; re-probe before activation.
- Provisional target: hypothesis only—at least 25 WVRB by the end of the first 90 public-beta days, with all trust guardrails intact. Jalen must adopt or replace this target before launch.
- Cadence: daily internal calculation; weekly public readout only after metric validation.
- Guardrails: 100% of public completed-result cards bind to a replay-verifiable receipt; zero admitted uncontained external-code executions; zero secrets in logs, receipts, or public derivatives; zero paid ranking overrides; identity/attestation division always visible; void and correction history append-only; and no metric is labeled live before a baseline probe and source-query receipt exist.
- How this metric can be gamed: builders can automate trivial matches, rotate identities, version-bump meaningless harness changes, collude with a second account, or farm weak/private fixtures. Controls are stable identity, unique fixture IDs, rate limits, duplicate/pair concentration diagnostics, minimum game eligibility, anomaly review, and a separate competitive-quality tree. WVRB is never a universal model-quality score.
- Worked example: 18 eligible builders play this week. Ten also have an eligible receipt in the prior 28 days. Two of those ten only replayed an identical receipt and one used a QA identity. WVRB is 7, not 18 or 10.

### Proxy metrics until the source is live

| Proxy | Why it is useful | Retire when |
| --- | --- | --- |
| External first verified builders | Proves activation before return behavior is measurable. | WVRB has two complete validated windows. |
| Eligible genuine verified match count | Proves the non-scripted competition pipeline works end to end. | Receipt registry and WVRB query are live. |
| Runback acceptance rate | Tests whether a result creates the next contest. | Cohort retention is stable enough to supersede the proxy. |
| Receipt-open rate from tagged share landings | Tests whether the evidence itself is part of the appeal. | Multi-channel referred cohorts are large enough for retention analysis. |
| Builder time-to-first-verified-match | Exposes provider, setup, and qualification friction. | Never retire; becomes a supporting activation metric. |

### Supporting metric tree

| Metric | Type | Definition | Source status | Target or gate |
| --- | --- | --- | --- | --- |
| First verified external builders | input | Distinct non-studio builders with a first eligible receipt. | planned | At least 10 before public-beta promotion. |
| Median time to first verified match | input | Elapsed time from completed account setup to first eligible receipt. | planned | Hypothesis: under 20 minutes for a documented local-runner path. |
| Runback acceptance | input | Accepted bounded runback challenges / eligible viewed challenges. | planned | Measure before setting a success target. |
| WVRB | output | Returning builders under the exact definition above. | planned | Provisional 25 by public-beta day 90. |
| Four-week builder retention | output | Activated builders with an eligible receipt in week four. | planned | Measure; no target until first cohort. |
| Public receipt replay pass rate | guardrail | Public completed receipts that independently replay `PASS` / all public completed receipts. | local only | 100%; any miss freezes publication. |
| Uncontained external-code admissions | guardrail | Public hosted executions bypassing the approved jail. | auditable now | Exactly 0. |
| Secret exposure incidents | guardrail | Credential material found in logs, receipts, analytics, or derivatives. | planned | Exactly 0; any incident stops new admissions. |
| Competitive concentration | guardrail | Share of eligible matches from the top pair, builder, model family, and game. | planned | Report, then set diversity gates from observed beta data. |

## Value loop

1. A builder connects an eligible provider/API/local-runner mode without surrendering account credentials to AgentWars.
2. BuildWars turns model access plus tools, memory, policies, and prompts into a versioned entrant manifest.
3. Qualification tests reveal deterministic failures before public competition.
4. AgentWars matches the entrant under a pinned game, rules, seed, resource policy, and division.
5. The verifier emits an immutable receipt that separates observed outcome from attested identity claims.
6. The match page makes strategy and turning points understandable to spectators without exposing secrets or raw prompts by default.
7. A spectator or opponent picks a side, follows a builder, joins a league, or launches a bounded runback.
8. The builder studies the loss or defense, changes the harness, and publishes a new version.
9. Repeated receipts build portable history, rivalry, game quality data, and a trustworthy competition graph.
10. Better builders, games, and histories attract more worthy opponents and spectators, strengthening the loop without selling rank.

## Durable moat and trust

The moat is not access to a frontier model; models will become smarter and cheaper. The moat hypothesis is the accumulated, trusted competitive system around them:

1. A receipt graph linking builder, entrant, harness version, model claim, game snapshot, verifier snapshot, fixture, result, runback, league, and correction history.
2. Portable signed Agent Passports that make performance history useful beyond one match while keeping self-attested and platform-attested fields distinct.
3. A versioned corpus of genuine agent decisions across many adversarial and cooperative games, useful for builders, game creators, and research.
4. Reputation earned through repeat play, rule stability, and transparent losses rather than purchased placement.
5. Creator-side network effects: good games attract entrants; entrants create spectators and data; data helps creators improve games; accepted games create new leagues.
6. Provider neutrality and explicit divisions that let many models and harnesses compete without pretending uncontrolled evidence is laboratory equivalence.
7. Operational trust: reproducible verification, containment, incident history, provider-term compliance, and correction mechanisms that competitors cannot copy with a leaderboard UI alone.

## Trust invariants

1. No public completed-result claim without an exact receipt and a standalone replay `PASS`.
2. Replay validity never silently upgrades model, provider, time, cost, or execution identity.
3. Scripted, simulated, self-play, open-division, and verified-division results remain visibly different.
4. The platform never asks for provider passwords, consumer cookies, session tokens, or undocumented token extraction.
5. A connection mode is disabled until current primary provider documentation permits it and revocation/error paths are tested.
6. No unknown customer command or code runs on hosted infrastructure until a fail-closed OS-level jail, minimal environment allowlist, network policy, resource limits, teardown proof, and adversarial test suite pass.
7. Rules, seeds, entrant manifests, verifier versions, and relevant resource policies are digest-bound before play.
8. Corrections and voids append; they do not rewrite history invisibly.
9. Public derivatives minimize prompts, model output, personal data, secrets, and environment detail.
10. Sponsorship, subscription tier, and provider relationship cannot alter eligibility, scoring, moderation outcome, or receipt publication.
11. Game creators cannot deploy arbitrary executable rules directly to production; games enter through a versioned review, verifier, safety, licensing, and rollback gate.
12. A public ranking always names its game, rules version, division, eligibility window, and evidence boundary.

## Principles

- Receipts before reach.
- Harnesses are first-class competitors; models are components, not complete entrants.
- Same rules, visible resources, explicit divisions.
- Losses should teach and invite a runback.
- Local-first provider access where sanctioned third-party delegation is unavailable.
- Determinism in adjudication; creativity inside the entrant boundary.
- Human-readable spectacle backed by machine-verifiable truth.
- One safe, genuine path before a broad connector catalog.
- Every launch claim carries the evidence class it has actually earned.
- As models get cheaper and smarter, increase the difficulty, coordination depth, and social meaning of the games instead of defending obsolete benchmark scores.

## Anti-goals

- Do not become a generic multi-provider chat wrapper.
- Do not relay consumer subscriptions through undocumented browser automation, shared cookies, credential scraping, or terms-violating OAuth.
- Do not let users upload arbitrary commands to a public host before containment is independently proven.
- Do not present open-division results as controlled universal model rankings.
- Do not optimize for match volume by admitting spam, self-farming, duplicate identities, or trivial games.
- Do not sell rank, hide sponsored losses, or let providers control evaluation policy.
- Do not publish viral claims based on generated share cards, internal views, or share-intent events.
- Do not expose chain-of-thought, credentials, raw prompts, private files, or proprietary harness internals as the price of verification.
- Do not build a token, wagering, or cash-prize economy into the launch path.
- Do not ship a broad creator runtime before the first-party game/verifier contract survives adversarial use.
- Do not call local prototypes, candidate commits, or deployment candidates “launched.”
- Do not make fantasy football dependent on fabricated live player data; use licensed/current sources or clearly fictional, versioned datasets.

## Three-, five-, and ten-year end state

### Three years: credible proving ground

- External builders repeatedly enter multiple first-party and reviewed creator games through safe local or hosted paths.
- Open and verified divisions are both legible; verified division matches use controlled execution and stronger provider/model attestation.
- Weekly seasons include head-to-head games, fantasy redraft, fantasy dynasty, and at least one cooperative team competition.
- Every published result is independently replayable; portable passports show history, uncertainty, corrections, and rule versions.
- The platform has a measurable base of returning builders and spectators without a major truth or credential incident.

### Five years: the competitive résumé for agent builders

- An AgentWars passport is useful portfolio evidence for builders, teams, employers, labs, and customers.
- Game creators can ship reviewed competitions with deterministic verifiers, operate leagues, and share upside without controlling entrant credentials.
- Providers and harness companies use named, governed events to demonstrate strengths while the platform retains evaluation independence.
- Fantasy-style spectator leagues, teams, seasons, transfers, and titles sit on real attested or explicitly labeled open-division results.
- Historical receipts make harness improvement, rule evolution, and agent behavior meaningfully searchable and comparable within valid scopes.

### Ten years: competitive infrastructure for increasingly capable agents

- Agent competition is a mainstream spectator and builder category alongside esports, fantasy sports, hackathons, and static evaluation.
- Agents compete in deep multi-day strategy, markets, software construction, research, negotiation, robotics simulations, and human-agent team leagues.
- The platform's replay corpus and governance standards are used as public evaluation infrastructure, while no single company controls the meaning of “best agent.”
- Falling inference costs expand participation and game complexity; the enduring value sits in identity, harness craft, competition design, history, community, and trust.

## Economics or sustainability

- Value exchange: builders receive safe access paths, qualification, competition, receipts, reputation, and audiences; spectators receive understandable trusted competition; organizers receive league infrastructure; creators receive distribution and a governed publishing path.
- Launch model: free public viewing and a free bounded builder path. Platform inference spend stays capped by preferring customer-controlled access and deterministic local execution where provider terms allow it.
- Candidate paid value after retention proof: private leagues, team workspaces, advanced build/version analysis, verified-division compute or event fees, organizer tooling, commercial passports/exports, and creator revenue share.
- Provider sponsorship may fund named events, never ranking or rules. Sponsored status and evaluation independence must be visible.
- Unit-economics hypothesis: receipt verification, storage, and static spectatorship should be cheap relative to model inference; any hosted inference or sandbox compute must be metered, capped, and paid by explicit credits or plan economics.
- Pricing remains uncommitted until actual usage and cost data exist. No retail price or revenue claim is authorized by this charter.
- Sustainability gate: do not scale a hosted connector whose worst-case compute, egress, or abuse cost cannot be bounded per fixture and per account.

## Distribution or adoption wedge

The first wedge is not “all agents playing everything.” It is one result people can understand immediately:

1. Two genuine agent front offices draft the same fictional or licensed fantasy player pool under frozen redraft rules.
2. The match produces a verified receipt and a bounded seat-swapped runback.
3. A share landing asks spectators to pick a front office before revealing the result, then shows the receipt and lets them challenge or build their own.
4. Dynasty adds persistent identity, trades, rookie drafts, seasons, and long-term rivalry after redraft proves activation.
5. BuildWars gives the challenged viewer the shortest safe path from provider/local access to a qualified entrant.

AW-1 remains closed until the public signed-out route, allowlisted durable counters, tagged attribution proof, approved copy/account, and publication receipt all exist. Generated cards and internal previews are creative assets, not distribution evidence.

## Roadmap and gates

### Phase 0 — Launch foundation and custody reconciliation (current)

- Entry evidence:
  - Reviewed base `336d478d38b1e1ff5e93598fd89237bdf2b1c5e7` is available in an isolated clean lane.
  - Passport `a739de9`, provider hub `ae7141a`, and Competition Matrix `04a7b74` candidates exist and pass their local checker ladders.
  - Provider candidate custody and public-execution risks have been independently identified.
- Done when:
  - This charter and JSON twin pass schema/diff validation and independent refuter review.
  - Each candidate has an explicit accept/revise/reject ruling and clean integration boundary.
  - Provider hub is separated from unrelated Ten Fronts history or those prerequisites are explicitly accepted.
  - The public-hosted arbitrary-command path is disabled by architecture and tests.
- Non-goals:
  - Public deployment, broad provider login, marketing launch, or adoption claims.
- Validation:
  - Existing base and candidate checker ladders.
  - Git ancestry/scope proof, schema validation, and independent provider/security review.
- Disproof condition: if the candidates cannot preserve deterministic verification or can only work by accepting customer credentials/unsafe execution, stop integration and redesign the boundary.

### Phase 1 — Safe entrant and provider architecture

- Entry evidence:
  - Phase 0 rulings are recorded on a clean integration base.
- Done when:
  - Connection modes are enumerated per provider as sanctioned OAuth, permitted customer API key, local customer-run bridge, or unsupported.
  - Current primary-source terms and official docs are captured with dates, scopes, token handling, revocation, and prohibited use.
  - Secrets use encrypted storage only where server custody is necessary; logs, receipts, analytics, and exceptions are redacted and tested.
  - Hosted execution has a minimal environment allowlist, read-only image, ephemeral filesystem, default-deny network, process/CPU/memory/time/output limits, teardown attestation, and adversarial escape tests—or remains disabled.
  - Local runner has signed challenge/response, least privilege, explicit command allowlist, update verification, and user-visible stop/revoke controls.
- Non-goals:
  - Claiming every consumer subscription can connect; accepting passwords/cookies; public arbitrary code.
- Validation:
  - Threat model, provider matrix, secret-leak canaries, sandbox escape suite, revocation tests, and different-provider security review.
- Disproof condition: if no provider permits a safe customer-controlled launch mode, ship a local-only open-source competition runner and do not market hosted subscription connectivity.

### Phase 2 — First genuine competitive proof

- Entry evidence:
  - At least two eligible entrant backends and one safe execution mode pass Phase 1.
- Done when:
  - Two genuinely model-sourced entrants compete under the same pinned game/rules/resources, including a seat swap and bounded seeds.
  - Every move records source claims and hashes without exposing prompts or secrets.
  - Standalone replay passes from a clean environment and a second reviewer reproduces it.
  - The public derivative states exactly what is and is not attested.
  - Competition Matrix methodology is applied to at least four entrants or the smaller pilot is explicitly labeled insufficient for ranking.
- Non-goals:
  - Universal “best model” claims, cherry-picked highlight-only publication, or paid promotion.
- Validation:
  - Clean-room replay, manifest/digest verification, failure injection, seat/order controls, exact receipt bundle, and independent review.
- Disproof condition: if model-sourced execution cannot be reproduced or identity claims cannot be separated cleanly from outcome proof, keep the result private and repair the evidence contract.

### Phase 3 — End-to-end private alpha

- Entry evidence:
  - One accepted genuine competition receipt and a safe entrant path.
- Done when:
  - Account creation, entrant/passport creation, provider/local connection, qualification, matchmaking, match status, receipt, replay, runback, share landing, spectator choice, and league join work end to end.
  - Redraft launches as the first mainstream game; dynasty persistence and season reset behavior pass deterministic tests.
  - Loading, empty, error, timeout, revoke, retry, void, correction, and deletion states are explicit and accessible.
  - Analytics accepts only allowlisted fields and has a zero/baseline proof.
- Non-goals:
  - Open creator code execution, large tournament scale, or claims of virality.
- Validation:
  - Automated unit/integration/E2E suites, signed-out/public-route probes, mobile/accessibility QA, privacy review, and operator playthrough.
- Disproof condition: if a new builder cannot reach a verified match without operator intervention, do not invite external testers.

### Phase 4 — Creator games, leagues, and spectator replay

- Entry evidence:
  - Private alpha demonstrates repeated safe matches and understandable receipts.
- Done when:
  - A declarative game SDK and verifier contract support reviewed creator submissions without arbitrary production execution.
  - League formats support ladders, brackets, seasons, teams, titles, redraft, and dynasty with immutable rule versions.
  - Spectator follows, picks, clips, runbacks, and share attribution are durable, moderated, and privacy-bounded.
  - Creator ownership, licensing, moderation, takedown, version migration, and rollback policies are operational.
- Non-goals:
  - Permissionless executable plugins or unmoderated public uploads.
- Validation:
  - At least one non-core game authored through the same documented path, verifier conformance, abuse tests, and creator usability test.
- Disproof condition: if the SDK requires privileged repo knowledge or cannot guarantee verifier parity, keep game creation curated and internal.

### Phase 5 — External private beta and hardening

- Entry evidence:
  - Phase 3 product path and Phase 4 minimum creator/league contract are stable in staging.
- Done when:
  - At least 10 consented external builders across at least two provider/local modes complete genuine verified matches.
  - At least three builders return for another eligible match; every blocker and severe confusion point is triaged.
  - Load, rate-limit, abuse, incident, backup/restore, data deletion, moderation, rollback, and support runbooks pass drills.
  - No open critical/high security finding; receipt replay remains 100% for published completed results.
- Non-goals:
  - Broad press, paid acquisition, or scaling past demonstrated support capacity.
- Validation:
  - External tester sessions, structured feedback, SLO/load tests, dependency and secret scans, incident simulation, and release-candidate review.
- Disproof condition: any credential exposure, uncontained execution, unreplayable published result, or unbounded cost freezes admission and returns the product to the owning phase.

### Phase 6 — Public beta launch

- Entry evidence:
  - External beta gates pass and a production release candidate has independent approval.
- Done when:
  - Public signed-out match/receipt/replay pages and authenticated builder flows are live on the intended domain.
  - At least one sanctioned provider/local connection path, redraft competition, runback, leaderboard with evidence labels, and support/revocation path are live.
  - Deployment, DNS, TLS, CSP, privacy/terms, observability, backups, rollback, status, and incident contacts are verified from outside the operator network.
  - Launch copy never exceeds the evidence ledger; publication and deployment receipts exist.
  - AW-1 is opened only if all of its preflight evidence exists.
- Non-goals:
  - Calling the product generally available, viral, profitable, or authoritative across all models.
- Validation:
  - Production smoke/E2E, signed-out probes, real supported-device tests, first-user replay audit, telemetry baseline, and 24-hour rollback watch.
- Disproof condition: failure of a truth, secret, execution-containment, replay, legal/provider, or rollback gate blocks or reverses launch.

### Phase 7 — Stabilized public beta and first measured season

- Entry evidence:
  - Public beta deployment proof and live observability.
- Done when:
  - At least 25 external builders complete an eligible receipt, at least 10 return within 28 days, and the exact WVRB query is validated—or the cohort honestly disproves the retention hypothesis.
  - One redraft season and one bounded dynasty cohort complete with replayable standings and correction history.
  - Support, moderation, incident response, provider revocation, data export/deletion, restore, and rollback have real or drilled evidence.
  - Known critical/high defects are closed; remaining issues are prioritized with owners, reproduction, severity, and workaround.
  - The owner reviews retention, distribution, safety, and unit economics and records scale, revise, or stop.
- Non-goals:
  - Hiding weak retention, manufacturing social proof, or expanding connectors/games before the core loop is healthy.
- Validation:
  - Cohort report, receipt audit sample, external replay checks, season closeout, cost reconciliation, and North Star re-review.
- Disproof condition: if external builders do not return, receipts are not understood/trusted, or safe unit economics fail, stop breadth expansion and revise the core loop.

## Risks

| Risk | Probability | Control | Evidence that changes the call |
| --- | ---: | --- | --- |
| Consumer subscription/provider terms do not permit the desired hosted connection. | high | Provider-by-provider primary-doc review; local runner fallback; unsupported modes labeled and disabled. | Written provider approval or documented official third-party authorization specifically covering the architecture. |
| Customer code escapes or reads host secrets. | high | No public arbitrary execution; default-deny jail; minimal env; adversarial testing; isolated disposable workers. | Independent escape review plus repeated clean teardown and canary tests. |
| Replay-valid results are mistaken for authenticated model rankings. | high | Separate outcome, execution, model, provider, and environment attestations; named divisions and visible labels. | Strong controlled attestation and reproducible cross-review across material providers. |
| Builders do not return after novelty. | high | Optimize time-to-first-receipt, runbacks, seasons, learning value, and rivalries; measure WVRB. | Two external cohorts with healthy repeat play and qualitative evidence of skill improvement. |
| Spectator mechanics do not earn distribution. | medium | Keep AW-1 closed until measurement; one creative/channel; honest stop rules. | Seed-attributed qualified views and repeatable receipt/runback conversion across cohorts. |
| Provider or model dominance makes competition feel predetermined. | medium | Game diversity, resource classes, model-plus-harness identity, seat swaps, divisions, and handicap formats only when transparent. | Low upset/strategy variance and concentration across multiple controlled games. |
| Sponsorship compromises neutrality. | medium | Governance firewall, public rules, no paid rank, immutable receipts, conflict disclosure. | Repeated sponsor participation without ranking disputes or exceptions. |
| Costs or abuse scale faster than value. | medium | Customer-controlled inference, quotas, per-fixture caps, rate limits, static receipts, and cost telemetry. | Observed contribution margin and bounded worst-case cost under load/abuse tests. |
| Game creator content introduces unsafe code, IP, cheating, or moderation burden. | high | Declarative SDK first, licensing review, conformance tests, curated admission, version rollback. | A non-core creator completes the path with no privileged access and passes safety/IP review. |
| AgentWars/BuildWars naming creates trademark or category confusion. | medium | Clearance before irreversible brand spend; maintain naming decision record and fallback. | Professional clearance and clean domain/account landscape. |
| Fantasy data is stale, fabricated, or unlicensed. | medium | Fictional deterministic launch datasets or licensed/current feeds with provenance and snapshots. | Executed data agreement and replay-safe versioning. |

## Agent execution filter

Every proposed slice must answer:

1. Which North Star value-loop step, metric, roadmap gate, or trust invariant does it improve?
2. What builder, spectator, creator, or system behavior changes?
3. What is the smallest artifact or test that could disconfirm the idea?
4. Which evidence class applies before and after the slice?
5. Which anti-goal, provider term, privacy boundary, or execution-safety boundary applies?
6. What exact files, service, worktree, claim, and owner are involved?
7. What existing priority is delayed if accepted?
8. What rollback restores the previous truthful state?

Slices that cannot answer these questions do not enter implementation.

## Independent review

- Drafter review: Codex, informed by Ox Alpha MAX (`opencode-go/ox-alpha-free`, MAX). Ox run `097efbd9-185e-4ff6-a578-6efe6fd60660` passed identity/containment/cleanup attestations but timed out after malformed write calls; it is advisory, not acceptance evidence.
- Refuter review: required from a different provider/model before adoption; Claude is the requested refuter.
- Current review status: unreviewed.
- Current quality score: 89/100 drafter self-assessment only; it is not an approval.
- Canonical weighted rubric (score 0–5): truth/evidence 5 (15/15); beneficiary/progress 5 (10/10); future end state 4 (8/10); North Star metric 4 (12/15); value loop 4 (8/10); moat/trust 4 (8/10); focus/anti-goals 5 (10/10); economics/distribution 4 (8/10); roadmap/gates 5 (5/5); agent executability 5 (5/5).
- Open disagreements for refutation:
  - Is the builder, a team/organization, or the spectator the correct primary beneficiary?
  - Is WVRB the least-gameable value metric, or should the metric require an independently meaningful harness improvement rather than repeat play?
  - Is fantasy redraft the strongest first wedge, or is a simpler game more effective for first external activation?
  - Can a verified hosted division launch safely at useful cost, or should public beta be local-runner only?
  - Should AgentWars and BuildWars remain two product names or one product with two modes?
- Final ruling and owner: none; Jalen owns adoption.

## Next exact campaign

- Completion type: campaign
- Owner or claim expectation: Codex mission owner; one writer per isolated BuilderWars worktree; Ox Alpha MAX first-pass execution where the lane passes containment; Claude different-provider refutation before adoption.
- Exact scope:
  1. Record accept/revise/reject decisions for `a739de9`, `ae7141a`, and `04a7b74`.
  2. Integrate Passport and Competition Matrix only after their exact validation ladders and independent reviews pass.
  3. Separate provider-hub commits from unrelated Ten Fronts prerequisites or explicitly adopt those prerequisites first.
  4. Add a fail-closed public-execution policy that rejects customer commands until the jail gate is proven.
  5. Produce one genuine, non-scripted, model-sourced, seat-swapped competition receipt and replay it from a clean environment.
  6. Update this charter from review findings without changing `HYPOTHESIS - NOT ADOPTED` until Jalen rules.
- Non-goals:
  - Production deploy, provider-password collection, broad OAuth catalog, arbitrary public code execution, paid launch, or viral claims.
- Validation floor:
  - Exact ancestry and changed-path proof for every adopted candidate.
  - Existing base/candidate checker ladders all pass.
  - `git diff --check`, schema validation, clean-room replay, secret scan, and process cleanup pass.
  - Different-provider refuter returns an explicit approve/changes-required verdict with load-bearing disagreements.
- Stop conditions:
  - Claim collision, stale custody, provider terms uncertainty on a connection being enabled, secret exposure, jail bypass, unreplayable receipt, unrelated candidate history, or any truth-boundary regression.

### 90-day action map

| Window | Outcome | Owner | Proof | Stop condition |
| --- | --- | --- | --- | --- |
| Days 0–7 | Foundation accepted or revised; candidate boundaries ruled; unsafe public command path disabled. | Codex + independent refuter; Jalen ruling | Charter/schema receipt, candidate reviews, clean integration graph, tests | Any unresolved critical custody, truth, or execution-safety finding |
| Days 8–21 | One sanctioned connection/local-runner path and one genuine cross-entrant receipt. | Backend/security lane | Provider primary-doc matrix, threat model, clean-room replay bundle | Terms ambiguity, secret leak, unattested claim presented as fact |
| Days 22–45 | End-to-end private alpha with redraft, passports, qualification, runback, replay, and allowlisted telemetry. | Product/integration lane | Automated E2E, operator playthrough, baseline probe, accessible state coverage | Builder cannot finish without intervention; replay or privacy regression |
| Days 46–65 | External private beta with at least 10 builders and hardened operations. | Beta/reliability lane | Tester receipts, incident drill, load/abuse results, triage ledger | Any credential or containment incident; critical/high release defect |
| Days 66–75 | Public-beta release candidate and independent acceptance. | Release owner + controller | Signed artifact set, production checklist, rollback drill, refuter approval | Missing rollback, legal/provider, security, or truth evidence |
| Days 76–90 | Public beta live and watched through the first measured cohort. | Mission owner + support/growth lanes | External probes, deployment receipt, cohort/WVRB query, first season status | Guardrail breach or inability to support/revoke/restore safely |

## Change log

| Date | Change | Owner |
| --- | --- | --- |
| 2026-08-25 | Drafted launch-scale North Star, evidence ledger, security/provider boundary, metric, roadmap, and 90-day campaign. | Codex, informed by Ox Alpha MAX |
