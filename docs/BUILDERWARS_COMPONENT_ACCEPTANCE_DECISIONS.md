# BuilderWars component acceptance decisions

Status: **REVIEW CANDIDATE — no integration or production authority**
Prepared: 2026-08-27
Machine twin: `docs/BUILDERWARS_COMPONENT_ACCEPTANCE_LEDGER.v1.json`
Foundation source: draft PR `#12` at
`a83ce49f4a9cfbeb39ca6d22b64a86fd9b865bff`

## Outcome

The first truthful BuilderWars beta has two required code candidates:

1. BuilderWars owns competition truth, deterministic games, passports,
   schedules, replay, and bounded public result projections.
2. Nymrel owns authenticated customer experience, the protected control room,
   pairing UX, private submission and review, support, publication controls, and
   release evidence.

Everything else in the proposed reuse matrix is optional, conditional, held, or
a design reference. The beta must not become a cross-repository integration
program merely because related Nymrel repositories exist.

The exact candidates are:

| Role | Candidate | Current state |
| --- | --- | --- |
| Competition kernel | BuilderWars `7ed78e1993b60359eb257299705e089acc701d1c` | Clean local implementation candidate; five commits ahead of its remote feature; sequential Max reviews 1-9 plus affected-source closure `51119615-11ef-4962-b223-c368e1884485` pass with zero P0/P1; final frozen-foundation review remains pending; not on main |
| Customer control room | Nymrel `4f3b6270cee69f0465f0bfb458958e9bae0ba91c` | Clean local feature candidate with fail-closed Claude creation gate; one commit ahead of its remote; exact Max micro-review preflight ready; protected integration and production configuration remain held |

The external launch dependencies—Clerk, production-compatible Redis, reviewer
keys, rate limits, feature flags, Cloudflare/DNS, and source-bound hosting—are
protected configuration, not reusable code repositories.

Public naming is also an integration gate. The BuilderWars shell, navigation,
metadata, social cards, and structured data must name BuilderWars as the
umbrella while presenting AgentWars as the agent-sports/evaluation system and
BuildWars as the build-off format. Existing digest-bound `agentwars.*` schema
names, receipts, and verifier snapshots remain compatibility contracts and are
not rewritten merely for presentation.

At exact Nymrel candidate `4f3b6270cee69f0465f0bfb458958e9bae0ba91c`, the
`/builderwars` page metadata and structured data, public breadcrumbs, share
copy, Open Graph poster, arena, review console, league, rivalry, rules, and match
surfaces still present AgentWars as the top-level product. That source is a
functional candidate, not an accepted BuilderWars.com naming cutover. Public
presentation must pass the normalized hierarchy above while compatibility
schema and evidence bytes remain intact.

The exact BuilderWars runner candidate is also pinned to
`https://nymrel.com` in `provider_hub/local_runner.py`; the Nymrel deployment
verifiers currently prove the `/builderwars` preview on that origin. A dedicated
domain cutover therefore requires a reviewed origin-policy change, regenerated
immutable runner bundle and release digests, dedicated-origin deployment
verification, and host-confusion tests. DNS or redirects cannot stand in for
that work: the client validates the exact transport origin separately, while
the signature binds the method, path, body digest, timestamp, nonce, and runner
id. Both boundaries must match the dedicated release.

## Canonical ownership decisions

### 1. Match proof versus generic artifact proof

BuilderWars is the sole source of competitive truth. Its transcript chain,
exact-engine replay, rules version, seat/seed bindings, result, and publication
decision determine whether a match counts.

Nymrel Proof Ledger may later wrap generic build, artifact, roster, review, or
release evidence. It must not replace a game-specific transcript or produce a
second match verdict. Any adapter must reference the existing BuilderWars
receipt digest instead of re-encoding competitive facts.

Decision: **Proof Ledger is conditional and non-blocking for the first beta.**

### 2. Account authentication versus administrative permission

Clerk and the Nymrel application own authenticated customer sessions and tenant
account lifecycle. BuilderWars owns competition roles such as submitter,
reviewer, publisher, league operator, and appeal authority inside its versioned
contracts.

PermitMesh and Agent Action Surety may inform later permission vocabulary, but
neither becomes a second account or authorization database for the beta.

Decision: **no new permission runtime dependency.** Unknown roles and actions
must fail closed in the existing protected application boundary.

### 3. Match chains versus agent-action chains

BuilderWars transcript and receipt chains remain canonical for play. Agent
Proofchain is a research reference for non-match provenance only. Do not copy or
compose hash chains until one documented envelope can reference—not duplicate—
the canonical match receipt.

Decision: **Agent Proofchain is reference-only.**

### 4. Public MCP and plugin ownership

The web beta does not depend on an MCP directory or plugin publication. If a
later host integration is adopted, Nymrel Plugin is the preferred single public
tool surface and begins with read-only discovery and verification. Nymrel MCP
Hub remains a pattern source unless a later decision replaces that owner.

Neither surface may adjudicate, publish, spend, handle provider credentials, or
execute private entrants.

Decision: **no plugin/MCP launch dependency and no duplicate public endpoint.**

### 5. Provider routing versus provider/model attestation

The BuilderWars provider catalog, customer-local runner, exact pairing protocol,
and signed request boundary own the beta's allowed execution routes. Nymrel Agent
may later advise budget or route selection, but an explanation derived from
caller-supplied facts cannot attest a provider account, subscription, model,
runtime, person, or execution.

Decision: **the fixed BuilderWars provider hub remains authoritative for beta;
Nymrel Agent is an optional later adapter.**

### 6. Team coordination versus game communication rules

BuilderWars `Team`, `RosterVersion`, match manifest, and rules version must bind
the actual builders, agents, harnesses, tools, budgets, communication channels,
substitutions, and human-intervention windows.

Nymrel Swarm Protocol and Swarm Studio may inform future protocol and UI design,
but cannot prove which roster competed or which communications were allowed.

Decision: **team protocol and UI remain reference-only until canonical entity
validators and match bindings exist.**

### 7. Customer-local execution versus hosted untrusted execution

The first beta executes only the fixed, reviewed customer-local runner and exact
admitted harness contracts. Public uploaded code, arbitrary entrant commands,
and hosted creator code remain disabled.

Agent Sandstorm, local-agent-forge, or another runtime may be evaluated later,
but repository claims, timeouts, process spawning, allowlist configuration, or
application-level validation do not prove OS confinement.

Decision: **no hosted arbitrary external code in the beta.** This removes Agent
Sandstorm and local-agent-forge from the critical path without weakening the
requested customer-owned runner experience.

The executable kernel enforces that decision with
`builderwars/entrant-admission/1`. The raw `run_match` API requires an exact
execution scope. Reviewed repository fixtures and customer-controlled local
harnesses have separate wrappers and separate receipt values. The named
`external_untrusted_hosted_v1` scope always fails before match-owned filesystem
or process side effects. No caller-supplied isolation receipt can override the
decision, and admitted local receipts keep capability-isolation attestation
false.

### 8. Donor product repositories

DraftADynasty may inform fantasy league, roster, and trade UX while BuilderWars
retains frozen deterministic rules and rights-safe data. SwingersClub may inform
generic tournament operations only after protected-source review; its current
dirty worktree and customer-specific data make it ineligible as a code donor.

Decision: **reference patterns only; no copying and no shared customer data.**

## First-beta dependency graph

```text
BuilderWars reviewed integrated commit
  -> immutable runner/verifier bundle
  -> Nymrel reviewed integrated commit
  -> protected Clerk + Redis + reviewer/rate-limit/feature-flag configuration
  -> source-bound deployment and builderwars.com cutover
  -> fresh consented customer journey
  -> signed 13-stage evidence pack
  -> separate operator launch authorization
```

No optional Nymrel repository may enter this graph without an exact integration
need and a passing acceptance record. This protects delivery speed and prevents
architecture theater from replacing the real customer loop.

## Current component findings

- Only the Nymrel Plugin, Nymrel MCP Hub, Nymrel Machine Trust,
  local-agent-forge, Nymrel Trust Scorecard, Open UCP, Nymrel Proof Ledger, and
  DraftADynasty local heads were observed at the same object as the current
  remote default; several of those checkouts are still dirty.
- Agent Sandstorm, Agent Action Surety, PermitMesh, Agent Proofchain, Nymrel
  Agent, Nymrel Swarm Studio, Nymrel Swarm Protocol, Presence, Nymrel Ecosystem
  Portal, and SwingersClub had a local/remote branch or object mismatch, a dirty
  checkout, or both. Their local bytes are not adoption evidence.
- No checkout named `token-spend-dashboard` was found in the bounded Desktop
  inventory. The platform therefore has no accepted token-cost component from
  that name.
- A clean remote default object is still only a source pin. It does not prove
  the interface, tests, security, maturity, or BuilderWars composition.

## Acceptance record required for any later component

Every adopted component must add one immutable ledger entry containing:

1. canonical repository and exact accepted commit or released package;
2. integration owner and one source-of-truth role;
3. typed interface, schema, and version-negotiation behavior;
4. supported host and runtime matrix;
5. exact local tests, CI, hostile tests, and independent review receipts;
6. credential, identity, data, tenant, and signer custody;
7. time, memory, network, filesystem, process, output, and spend bounds where
   execution is involved;
8. errors, cleanup, revocation, deletion, migration, and rollback;
9. allowed lifecycle classes: local, private, exhibition, ranked, public, or
   production;
10. explicit claims the component still does not prove.

Missing evidence is a held gate, not a field to infer from README prose.

## Closed Max P2 hardening backlog

All five accepted hosted-control-plane P2 findings are now closed in the local
feature candidate. The affected slice passes 25/25 hosted tests, Ruff,
`py_compile`, `git diff --check`, and the complete 10-section provider-hub
regression ladder. Ox Alpha MAX run
`51119615-11ef-4962-b223-c368e1884485` reviewed the exact four-file source diff
against base `6330c5b673589eac69ffcb3fb00c16c6973baa61` and returned P0 `0`,
P1 `0`, P2 `0`, P3 `5`, `VERDICT: APPROVE`.

| Area | Closure proof |
| --- | --- |
| Lease error taxonomy | Poll, renew, abandon, and result use one `invalid_runner` store taxonomy; the direct-store matrix proves identical codes and no row-count mutation |
| Pairing tenant negatives | Wrong-owner approve and reject both fail `not_found`; row counts and the exact challenge row remain unchanged before rightful confirmation succeeds |
| Renewal/refusal fidelity | A renewed attempt accepts its result after the original deadline; refused over-cap renew and transcript-mismatch result preserve the inspected attempt/job rows |
| Strict JSON boundary | Boolean and out-of-range epochs, unknown fields, deep JSON, uppercase digests, body substitution, exact time edges, and nonce preservation are pinned by signed hostile cases |
| Request parsing and envelope types | Immutable `bytes` plus exact string envelope fields are enforced before parsing; recursive/type faults normalize into coded non-reflecting errors and handler fields are validated before nonce consumption |

The accepted source hashes, receipt hashes, full P3 dispositions, and rejected
non-verdict review trace are recorded in
`provider_hub_hosted/OX_REVIEW_HOSTED_CONTROL_PLANE_20260826.md`. This closure is
local evidence only; it does not advance any protected integration or launch
gate.

## Public-beta completion ledger

This ledger maps the operator's nine completion requirements to the exact
current evidence boundary. `candidate` means local or feature-branch evidence
exists but the requirement is not achieved. `held` means a protected action or
external dependency has not been authorized. `closed` means the customer-facing
surface must remain unavailable.

| Requirement | Current state | Evidence that exists | Evidence still required |
| --- | --- | --- | --- |
| 1. Fresh independent BuilderWars and Nymrel review with zero P0/P1 | `candidate` | BuilderWars has nine prior zero-P0/P1 Max slices plus affected-source closure run `51119615-11ef-4962-b223-c368e1884485` at P0/P1/P2 `0`; exact four-file hashes are recorded locally. Nymrel feature `4f3b6270cee69f0465f0bfb458958e9bae0ba91c` is clean and locally committed; its Claude-gate Max micro-review preflight is ready | Completed Max receipt for the final frozen BuilderWars foundation, plus Nymrel Claude-gate and regenerated exact-candidate custody/journey/deployment/support packets; every P0/P1 repaired and re-reviewed |
| 2. True-merge ancestry and immutable runner assets on canonical main | `held` | Candidate branches and exact remote-main heads are recorded | Operator-authorized true merges, ancestry proof, immutable runner/verifier asset digests on BuilderWars main, release descriptor bound to the integrated commits, and rollback target |
| 3. Production-compatible Redis conformance | `held` | Nymrel contains a fail-closed real-Redis verifier and tests; no production-compatible run is claimed | Authorized isolated Redis REST pair; atomicity, expiry, poisoning, idempotency, revocation, cleanup, and account-deletion run against the integrated source; proof that test keys were removed |
| 4. Clerk and protected runtime configuration | `held` | Candidate code contains account-owner mapping, signed `user.deleted` handling, peppers, reviewer bindings, rate-limit policy, no-store behavior, and feature flags | Protected environment checks for the exact Clerk instance, webhook, Redis pair, peppers, reviewer keys, trusted proxy metadata, rate limits, security headers, and closed/open flag states without secret disclosure |
| 5. Source-bound production deployment | `held` | `BuilderWars.com` delegates to Cloudflare nameservers | Authorized clean deployment; exact source and asset binding; apex and `www` DNS; HTTPS, redirect, headers, routes, mobile, accessibility, performance, offline/error-state, support, observability, and rollback proof. The apex currently has no A/AAAA and `www` is NXDOMAIN |
| 6. Fresh consented real-customer journey | `held` | Local deterministic journey fixtures and protected-route candidates exist | One new consenting customer completes signup/signin, runner pairing and recovery, two distinct encrypted passports, genuine provider-backed competition, private review, bounded publication, spectator share, runback, revocation, local/provider cleanup, account deletion, and rollback |
| 7. Signed 13-stage production evidence pack | `candidate` | Nymrel feature source contains initialization, observation, assembly, protected-evidence, deployment, runner-release, support, and journey verifiers | One canonical pack assembled only from the integrated production source, protected-source comparison, detached Ed25519 review, exact deployment/release bindings, final verification, and separate operator launch decision |
| 8. Complete local and production validation | `candidate` | BuilderWars hosted tests are 25/25; provider-hub checker passes 10/10 sections in 122.6 seconds; passports pass 45/45; matrix produces 24 replay-verified receipts; verifier passes 45/45 plus 22 custody attacks. Nymrel's Claude-gate focused suites pass 55/55; lint, typecheck, 1,354 unit tests, operations (178 pass plus one explicit Windows direct-file-symlink host skip), discovery, boundaries, distribution, production build, and bundle budget pass. Its umbrella check stops only at stale portfolio proof entries because protected integration with the current main proof refresh is held | Post-integration proof verification, security, dependency, browser, production smoke, observability, support, rollback, cleanup, and process-leak gates for both exact integrated commits |
| 9. Truthful public-beta claim | `closed` | The domain contract, component ledger, and publication boundaries explicitly forbid a launch claim | Exact live bytes plus the full journey and evidence pack must pass. Until then the allowed labels are closed, local candidate, held, or preview-only |

No row may advance from `candidate` or `held` based only on a source file,
passing unit test, deployment dashboard state, provider availability, domain
purchase, or an earlier receipt for different bytes. Each transition must bind
the exact source, environment, actor, time, inputs, outputs, cleanup, and
independent review.

## Next exact move

1. Freeze implementation candidate `7ed78e1993b60359eb257299705e089acc701d1c`,
   draft PR `#12`, this ledger, and the domain/submission decisions as one
   coherent committed foundation; run its deterministic checker and final
   external immutable Max packet without merging.
2. Complete the exact Nymrel Claude-gate Max review, push only its feature
   branch if accepted, and regenerate every candidate-identity-dependent
   Nymrel packet without merging.
3. Keep optional repositories out of the integration graph.
4. After protected authorization, run Redis and account configuration
   conformance against the same integrated source.

No merge, tag, release, provider use, account mutation, Redis provisioning,
deployment, Cloudflare/DNS change, billing, invitation, or public launch is
authorized by this decision.
