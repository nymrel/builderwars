# AgentWars local launch evidence pack

Status: local candidate contract. It is not a production evidence pack, launch
authorization, deployment receipt, provider attestation, customer journey, or
detached independent review.

## Purpose

BuilderWars already has many strong local checks, but a green command printed in
isolation does not bind the exact source, cleanup state, remaining gates, or
claims it cannot prove. The local evidence builder orders those checks into one
machine-readable candidate while preserving the production dependency graph:

```text
reviewed BuilderWars source
  -> immutable runner and verifier evidence
  -> protected runtime configuration
  -> source-bound deployment and rollback
  -> fresh consented tester journey
  -> detached independent production review
  -> separate operator launch authorization
```

The local builder covers only the first node and its credential-free validation.
It deliberately records the protected downstream nodes as held.

## Ordered 13-stage contract

| Order | Stage | Local behavior | What remains unproven |
| ---: | --- | --- | --- |
| 1 | Source custody | Records exact commit, tree, branch, and clean status | Canonical-main integration, remote custody, deployment binding |
| 2 | Deterministic arena | Runs the adversarial engine self-check | Hosted/provider execution and production containment |
| 3 | Product, leagues, starter, and scale | Checks public product, distinct redraft/dynasty, deterministic scale, the finite season support/moderation/correction/rollback contract, and a two-fixture offline scripted starter loop from versioned blueprint through a pre-execution format-eligibility decision, proof-linked learning, and an unplayed runback | Live leagues, legal or provider-terms approval, customer harness/model qualification, played runback, staffed support, executed moderation/corrections, audience, retention, rankings |
| 4 | Provider boundaries and regressions | Runs the complete provider-hub regression ladder | Customer authorization, provider identity, paid compute, production secrets |
| 5 | Runner bundle and dependencies | Checks immutable offline bundle and dependency lock | Public artifact hosting, Nymrel signature, provider runtime identity |
| 6 | Replay and verifier parity | Checks package versus standalone verifier parity | Production custody, registry commit, external signature |
| 7 | Mobile static contracts | Checks deterministic mobile, truth, offline, and accessibility contracts | Hosted route, real user, deployed device support |
| 8 | Real-browser acceptance | Runs Chromium navigation, failure, storage, responsive, offline, and accessibility journeys | Production browser, authenticated journey, external performance |
| 9 | Hosted security, abuse, cleanup, browser authorization, and threat model | Runs local hosted-control-plane refusal, rollback, cleanup, browser-gateway, atomic-idempotency, and bounded key-rotation adversarial tests plus the repository-grounded 10-threat/8-boundary security model | Live Clerk/session verification, durable production store/rate-limit/deletion/idempotency parity, owner-pepper and idempotency-response-key custody/rotation execution, OS isolation, penetration review, and security approval |
| 10 | Launch contracts, measurement, performance, observability, retention/deletion, incident, recovery, tester-readiness, and discoverability drills | Runs strict measurement and observability zero-baseline gates, deterministic incident/support drills, classified atomic deletion simulation, source-bound rollback/recovery failure drills, deterministic Mobile Arena asset budgets, an exact fail-closed 16-step synthetic tester rehearsal, and a prelaunch search/AI contract with indexing disabled | Consented human tester and feedback, durable/live counters and telemetry, real deletion, backup/restore, alert delivery, staffed support, production rollback/performance, canonical origin, indexing, citations, audience, legal approval |
| 11 | Protected runtime configuration | Executes nothing; records `HELD_PROTECTED` | Clerk, Redis, webhook, peppers, reviewer keys, rate limits, flags |
| 12 | Source-bound deployment and rollback | Executes nothing; records `HELD_PROTECTED` | Target, DNS/TLS, served bytes, performance, observability, rollback |
| 13 | Tester, review, and launch authority | Executes nothing; records `HELD_PROTECTED` | Consented customer, genuine provider match, deletion, detached review, launch decision |

There are exactly ten local stages and three protected held stages. A passing
local pack reports `LOCAL_PASS_PROTECTED_HELD`, `localStagesPass: true`,
`protectedStagesHeld: true`, and `launchable: false`. Any local failure or dirty
source reports `LOCAL_FAIL`. If source custody fails, stages 2 through 10 are
recorded as `NOT_RUN_SOURCE_CUSTODY`; the builder does not run evidence against
an unbound source.

## Commands

Validate the builder contract without running the full evidence ladder:

```powershell
python bin\check_agentwars_local_launch_evidence.py
python bin\build_agentwars_local_launch_evidence.py --list-stages
```

After committing the candidate, use its full 40-character SHA in a new output
path:

```powershell
python bin\build_agentwars_local_launch_evidence.py `
  --output output/launch-evidence/<full-source-sha>/pack.json
```

The evidence path is create-only. A second attempt to the same path is refused;
use a new source SHA or a distinct observation filename rather than rewriting
history. `output/launch-evidence/` is ignored by Git so pack generation does not
dirty the evaluated source.

`--require-launchable` intentionally returns exit code `3` while the protected
stages remain held. The local builder has no option that activates those stages.

## Pack integrity and privacy

The JSON includes:

- schema and pack class;
- UTC observation time;
- exact Git commit, tree, branch, clean state, and dirty-entry count;
- Python/platform metadata without an absolute home or repository path;
- ordered stage records with argv, exit code, timeout state, duration, bounded
  sanitized summary, and SHA-256 digests of stdout and stderr;
- SHA-256 and byte size for required launch-contract files;
- one finite eight-fixture redraft candidate season with a separate inactive
  dynasty cohort, scoped standings, bounded support/moderation decisions,
  append-only correction candidates, creator admission held, and every season,
  staffing, action, ranking, and launch authority flag false;
- two byte-identical offline starter runs covering one fixed redraft seed and
  both seat orders, with a source-digest-bound blueprint, exact rules/resource
  binding, a fail-closed pre-execution competition-format eligibility decision,
  replay-verified scripted moves, proof-linked observation-only learning, and
  one versioned unqualified/unplayed runback; the format decision is not legal
  advice or provider-terms approval, and no provider route, credential
  provisioning, customer harness/model qualification, ranking, publication, or
  deployment authority is granted;
- a strict six-event measurement contract and honest zero baseline with every
  production, audience, performance, identity, retention, and launch flag false;
- deterministic raw and gzip budgets for the exact tracked Mobile Arena asset
  set, with no network, timing, real-user, or production-performance claim;
- a strict ten-event operational schema, zero observability baseline, and
  deterministic incident/support decisions with no telemetry, alert delivery,
  flag mutation, rollback execution, or production-authority claim;
- an eight-class digest-only retention inventory, atomic deletion/suppression
  simulation, five-dimension last-known-good recovery plan, and injected
  deletion/recovery failures with no data access, external deletion, backup,
  restore, deployment, flag, or operator-authority claim;
- a repository-grounded ten-threat security model covering eight trust
  boundaries and seventeen exact source anchors, with a fail-closed local
  browser-authorization gateway and production Clerk, tenant-store,
  rate-limit, provider-secret, OS-isolation, monitoring, deletion, deployment,
  and independent-review production gates held;
- an exact 16-step tester contract, synthetic six-step local rehearsal,
  eight-category uncollected feedback rubric, 11-class cleanup matrix, and
  non-actionable operator packet with every human and production authority
  field false;
- a versioned discoverability and launch-copy contract, crawler-wide prelaunch
  disallow policy, voluntary AI-orientation file, absent sitemap/canonical/
  structured-data claims, and explicit zero indexing, citation, audience,
  publication, and launch authority;
- post-run source/tree/cleanliness proof;
- false production claims and the next protected gate; and
- `packDigest`, the SHA-256 of canonical JSON before that field is added.

The pack stores no credentials, cookies, API keys, customer data, prompts, raw
model output, identity assertion, or provider subscription material. The browser
stage uses only an ephemeral `127.0.0.1` server. All other commands are local and
credential-free. Child checks receive only a closed allowlist of non-secret
system variables, so ambient provider credentials are not inherited.

Validate an emitted pack without rerunning its commands:

```powershell
python bin\check_agentwars_local_launch_evidence.py `
  --pack output/launch-evidence/<full-source-sha>/pack.json
```

## Exact evidence boundary

This pack can prove that one clean committed BuilderWars source passed its
declared local contracts without leaving tracked mutations. It cannot prove:

- an accepted true merge to canonical `main`;
- Nymrel integration or served-byte parity;
- Clerk, Redis, DNS, TLS, provider, billing, reviewer, or feature-flag state;
- production performance, observability, support, abuse response, deletion,
  backup/restore, or rollback;
- a real person, customer, model, provider, runtime, or legal identity;
- a consented tester journey or human feedback, public audience, retention, or revenue; or
- independent production review or operator launch authorization.

Those claims require the protected source-bound evidence described in
`BUILDERWARS_COM_DOMAIN_CUTOVER_CONTRACT.md` and
`BUILDERWARS_COMPONENT_ACCEPTANCE_DECISIONS.md`. The local pack must never be
renamed or promoted to the signed production pack.
