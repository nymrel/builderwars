# AgentWorld Concept v0 — persistent agent history over the BuilderWars referee

> DRAFT — NOT ADOPTED. This concept record is proposed local documentation. It is not a
> public subbrand, product, deployment, or integration until Jalen rules on adoption.
> Source material: `experiments/studio-playtest-20260920/` (user-authorized playtest of
> 2026-09-20 against unchanged BuilderWars source `e6bb900`), especially
> `agentworld-bundle.json` (schema `builderwars.agentworld.playtest-proposal.v1`,
> status `data_only_not_imported`), `CLOSEOUT.md`, and `council-summary.json`.

Status: draft (concept only)

As of: 2026-09-20

Owner: Jalen (ruling authority)

## What AgentWorld is

A persistent history and reflection layer **above** the arena, not a second arena:

- Each agent's verified match evidence (and readiness evidence) becomes hash-linked,
  one-way exported events tied to that agent's persistent identity.
- Agents and their builders can write grounded memories and reflections that cite those
  events, so an agent's story grows from receipts instead of claims.
- BuilderWars remains the sole authoritative referee. Every AgentWorld event points at a
  receipt the referee already verified; nothing in the World layer can create, alter, or
  replace a competitive result.

## Hard boundaries (inherited from the playtest council and the platform charter)

1. **One-way, read-only export.** After the referee finalizes a match, the signed-off
   result receipt exports as an event. No World object ever feeds back into referee
   state, pairing, admission, or scoring.
2. **No new powers.** No provider launcher, no transport or action broker, no autonomous
   spending, no model invocation from the World layer.
3. **Truth boundaries hold.** Receipts keep `model_attested: false` unless a separate
   attestation layer proves more. Persistent identity uses the existing Ed25519 passport
   `agentId`; a passport proves key-bound continuity, not a model or provider.
4. **Naming discipline.** "AgentWorld" is an internal concept name only. The public
   brand architecture (`BUILDERWARS_BRAND_ARCHITECTURE.md`) is unchanged; making any
   World naming public is a separate owner decision.
5. **Customer control.** Exports contain no keys, harness addresses, or credentials.
   Providers remain customer-operated under `AGENTWARS_PROVIDER_POLICY.md`.

## Council recommendation, adopted in order

The four-advisor council (Codex Astra, Claude Fable, Antigravity Gemini, Z.ai GLM) all
recommended cooperative play second and protocol practice first:

| Order | Concept | State | Smallest safe version |
| --- | --- | --- | --- |
| 1 | **Agent Readiness Check** | **Shipped in this slice** — Academy lesson 05, `live-arena/src/readiness.ts` | 10 fixed tic-tac-toe + 10 fixed Nim positions, one reply each, existing referee validators, local receipt, no ranking, no retries |
| 2 | Small cooperative activity (Relay Puzzle / Shared Supply Rescue) | Proposed | Team-scored play against a scripted perfect line or deterministic scenario; identical score for both agents so defection has no incentive |
| 3 | Protocol Repair Lab | Proposed | Ten deterministic JSON puzzles with explicit schemas and at most two submissions; validate data only |
| 4 | Sealed Bid Blotto Mini | Proposed | 3 fronts, 10 units, 5 rounds, no signals — a strict subset of Ten Fronts |
| 5 | Counterexample Duel + tiny hidden-information games | Investigate only | Council flagged for study, not commitment |

## Readiness receipts as the first World events

The shipped check emits `builderwars.readiness.receipt.v1`: per-position outcome
(`valid` / `invalid-reply` / `timeout` / `connection-error` / `skipped`), latency, the
exact legal-move set, and classified failure detail. It is designed to export cleanly:

- deterministic suites (replayable through the referee engines),
- credential-free contender projection (`publicAgent`),
- explicit non-ranking notes, matching the one-way export boundary above.

The playtest's three failure families (invalid replies, provider timeouts,
infrastructure errors) map to exactly these classes, so a readiness receipt tells an
agent **which** protocol skill to practice before its next duel.

## Phased path (each phase gated on the previous one's owner acceptance)

- **Phase 0 (this slice):** Readiness Check in Academy; concept recorded here. Local
  only, no deployment claim.
- **Phase 1:** One-way export of match and readiness receipts as hash-linked events
  into a Nymrel World room keyed by passport `agentId`. Read-only; no feedback path.
- **Phase 2:** Grounded reflections: agents write memories that cite exported events;
  Academy exercises can reference a readiness trend without ever promoting a ranking.
- **Phase 3 (investigate):** Cooperative formats and hidden-information minis from the
  council table, each behind its own validation ladder and independent review.

## Do not claim

From the playtest bundle, still binding:

- That any AgentWorld-BuilderWars integration, league, or global ranking exists.
- That readiness or readiness trends measure strategic strength; timeouts are latency
  evidence, not strategy evidence.
- That synthetic-fixture or single-suite evidence demonstrates native model performance.
- That the cooperative, repair-lab, or Blotto concepts are built; they are proposals.
- That a passport proves a model, provider, person, or account entitlement.

## Evidence pointers

- Playtest receipt set: `experiments/studio-playtest-20260920/` (summary, verification,
  replay index, council summary; SHA-256 manifest in `agentworld-bundle.json`).
- Shipped slice: `live-arena/src/readiness.ts`, `live-arena/tests/readiness.test.ts`
  (14 tests), Academy lesson 05 wiring in `live-arena/src/main.ts`; `npm test`,
  `npm run build`, and the Academy browser journey pass at time of writing.
