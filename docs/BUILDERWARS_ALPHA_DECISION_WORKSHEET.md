# BuilderWars private alpha deterministic decision worksheet

Status: **NOT_OPEN**. Source:
`e004aaea86c097dc8427499d0c35413fc1e704a1`. Initial decision:
`HOLD_NOT_AUTHORIZED`.

This worksheet makes no provider call and grants no authority. Complete it
from evidence manifests, not memory or narrative. `PASS` requires cited
evidence; missing, indirect, synthetic, locally rehearsed, or stale evidence is
`MISSING`, never PASS.

## Decision precedence

Evaluate in this order:

1. Any `KILL` row = `KILL_CURRENT_WEDGE` and stop.
2. If authorization is absent or any required owner is `OPERATOR_ASSIGN` =
   `HOLD_NOT_AUTHORIZED`.
3. If an earlier stage is not PASS = that stage's HOLD status; later evidence
   cannot bypass it.
4. If no KILL applies but a threshold/evidence row is missing and the cap
   remains = `HOLD_REPAIR_OR_MORE_EVIDENCE`.
5. A stage advances only when every mandatory row for that stage is PASS.

No outcome from this worksheet authorizes public launch, rankings, outreach,
production, DNS/auth changes, billing, prizes, publication, or provider
expansion.

## A. Source and authority

| Gate | Required evidence | State | Evidence reference |
| --- | --- | --- | --- |
| Exact clean source | Clean tree at `e004aaea86c097dc8427499d0c35413fc1e704a1` | `MISSING` | |
| Packet binding | Digests for protocol, consent/privacy, demand packet, and this worksheet | `MISSING` | |
| Pair authorization | Separate operator authorization names two supported customer-local routes, `fantasy_redraft`, exact seed, unranked status, quota/cost disclosure, and stop conditions | `MISSING` | |
| Session owner | Not `OPERATOR_ASSIGN` | `MISSING` | |
| Support/incident owner and private channel | Not `OPERATOR_ASSIGN` | `MISSING` | |
| Privacy/deletion contact | Not `OPERATOR_ASSIGN` | `MISSING` | |
| Evidence custodian and cleanup reviewer | Not `OPERATOR_ASSIGN` | `MISSING` | |

Current stage decision: `HOLD_NOT_AUTHORIZED`.

## B. Protected technical pair

Both rows of the pair use two distinct ids from `chatgpt_codex`, `opencode`,
`openrouter`, or `hermes`; `claude_code` is historical-only. Pure seat-swap
proof is explicitly unranked.

| Gate | PASS rule | State | Evidence reference |
| --- | --- | --- | --- |
| Same game and seed | Both are `fantasy_redraft` with identical integer seed | `MISSING` | |
| Exact seat reversal | Same entrants, versions, strategies, rules, engine, verifier, and passports; only seat assignment reverses | `MISSING` | |
| Exit and source | Both exit `0`; all accepted moves are `source=model`; no fallback/partial/forfeit/abort/block | `MISSING` | |
| Signed passports | Two passports independently verify and bind exact harness digests in both runs | `MISSING` | |
| Independent replay | Both return replay/effective PASS and matching engine/verifier snapshot | `MISSING` | |
| Manual cost observation | Before/after provider or local observations recorded; unknown is `not_available`, never estimated | `MISSING` | |
| Secret/privacy scan | Redacted pack passes; no credential, identity, prompt, raw output, unrestricted stderr, or contact destination | `MISSING` | |
| Cleanup | All spawned processes and temporary artifacts accounted for; provider-side deletion not claimed | `MISSING` | |
| Truth labels | All fairness/provider/model/billing/runtime/causal/ranking/launch flags false | `MISSING` | |

Stage PASS outcome: `GO_CERTIFICATION_PATCH_ADMISSION`. Otherwise
`HOLD_TECHNICAL_PROOF`; any hard stop below is KILL.

## C. Bounded certification patch

| Gate | PASS rule | State | Evidence reference |
| --- | --- | --- | --- |
| Scope | Offline seat-swap pair validator, adversarial self-tests, and provider-policy/documentation correction only | `MISSING` | |
| No expansion | No provider call, schema expansion, ranking, deployment, or protected stage | `MISSING` | |
| Adversarial cases | Rejects seat drift, source/fallback drift, passport/manifest drift, replay/digest mismatch, duplicates, tamper, and identity/ranking claims | `MISSING` | |
| Provider truth | Executable catalog and docs agree that Claude is historical-only | `MISSING` | |
| Independent review | Detached reviewer accepts exact diff and test evidence | `MISSING` | |

Stage PASS outcome: `GO_DEMAND_AUTHORIZATION_DECISION`. Otherwise
`HOLD_CERTIFICATION_REPAIR`.

## D. Demand experiment `BW-D14-01`

| Gate | PASS rule | State | Evidence reference |
| --- | --- | --- | --- |
| Demand authorization | Separate authorization opens Gate 3 `BW-D14-01`, permits the 50-candidate private map, and approves messages/channels/owners | `MISSING` | |
| Authorized freeze | Exactly 50 qualified candidates frozen only after authorization: 36 independent agent builders, 8 technical commissioners, 6 evaluation-team leads | `MISSING` | |
| Fixed timing | First approved outreach attempt creates OPEN; all initial attempts by end day 3; one follow-up only during days 5–7; replies through day 14; decision exactly at day-14 close | `MISSING` | |
| Delivery | At least 40 approved invitations delivered by the day-14 close | `MISSING` | |
| Commitments | At least 8 active qualified commitments at close | `MISSING` | |
| Custody | Private contact map and pseudonymous ledger never join; random keys are not identity hashes; zero identity leakage | `MISSING` | |
| Event vocabulary | Only the eight exact allowlisted demand events appear | `MISSING` | |
| Reply classification | Every non-withdrawn substantive reply received through day-14 close has complete `reply_classified` evidence | `MISSING` | |
| Retention | Withdrawal purges contact, correspondence, and pseudonymous rows within 7 days; general 30/90-day due dates recorded and honored | `MISSING` | |
| Truth/safety | Zero unauthorized contact, credential/provider-policy, consent, deletion, harassment, ranking/parity, or material privacy incident | `MISSING` | |
| Time/spend | `$0`; no more than 16 execution + 4 analysis/repair hours | `MISSING` | |

At the day-14 close, with 50 frozen and at least 40 delivered: 8 or more active
commitments is `GO_DEMAND_GATE`; 6–7 is `HOLD_MINIMUM_MET`; 4–5 is
`HOLD_BELOW_MINIMUM`; and 0–3 is `KILL_CURRENT_RECRUITMENT_WEDGE`. Fewer than
50 frozen or 40 delivered is `HOLD_INCOMPLETE`, never a demand KILL. A universal
safety/privacy/material-truth KILL may stop early; no market or low-trust
decision is made early. At close, with at least 40 delivered and complete
classification for every non-withdrawn substantive reply, at least 50% low
receipt/truth trust is also KILL. Below 40 delivered, `HOLD_INCOMPLETE`
controls and low trust cannot produce KILL. A `GO_DEMAND_GATE` permits only a
separate operator cohort-authorization decision, not contact, scheduling,
provider execution, or cohort opening. Full rules are in
[`BUILDERWARS_DEMAND_EXPERIMENT_BW_D14_01.md`](BUILDERWARS_DEMAND_EXPERIMENT_BW_D14_01.md).

## E. Product cohort

| Gate | PASS rule | State | Evidence reference |
| --- | --- | --- | --- |
| Cohort authorization | Separate operator authorization creates the Gate 4 cohort OPEN timestamp after demand review | `MISSING` | |
| Fixed timing | Window ends exactly 14 days after OPEN; all 6 primary sessions occur days 1–7; each return is within 168 hours of its primary and no later than cohort close; decision exactly at close | `MISSING` | |
| Valid sessions | At least 5 of 6 scheduled sessions satisfy protocol validity | `MISSING` | |
| Played iteration | At least 4 of the minimum 5 valid participants independently complete parent receipt, harness change, and replay-valid child runback | `MISSING` | |
| Integrity and cleanup | 100% of completed parent/child evidence replays and reconciles; 100% cleanup receipts reconcile | `MISSING` | |
| Truth comprehension | At least 4 of the minimum 5 valid participants pass all critical neutral-peer truth boundaries uncoached | `MISSING` | |
| Seven-day return | At least 2 valid participants voluntarily return and produce another replay-valid child runback | `MISSING` | |
| Accessibility | Two accommodation sessions complete or fail closed; zero severe unresolved accessibility issue | `MISSING` | |
| Safety/privacy | Zero severe credential, privacy, provider-policy, safety, tamper, ranking/parity, accessibility, or cleanup issue | `MISSING` | |
| Time/spend | No more than 16 execution + 4 repair hours; `$0` BuilderWars spend | `MISSING` | |

Stage PASS outcome: `GO_NEXT_PRIVATE_GATE`. Apply the exact product
GO/HOLD/KILL thresholds in
[`AGENTWARS_PRIVATE_ALPHA_PROTOCOL.md`](AGENTWARS_PRIVATE_ALPHA_PROTOCOL.md).

## F. Universal KILL checks

Mark `YES` if any occurred. Any YES overrides every PASS above. Rows labeled
closeout-only are evaluated only at the fixed close and never trigger an early
stop.

| KILL condition | YES/NO | Evidence reference |
| --- | --- | --- |
| Credential/secret/private identity reached a BuilderWars operator/service/observer, was printed/persisted/uploaded/included in evidence, or entered a pseudonymous ledger; allowed transient OpenRouter customer-local adapter/child handling is not itself a violation | `NO_EVIDENCE` | |
| Unauthorized provider/account action, contact, spend, terms acceptance, publication, deployment, DNS/auth/production change, or protected-stage action | `NO_EVIDENCE` | |
| Replay, verifier, engine, passport, manifest, source, lineage, or evidence digest tamper/inconsistency | `NO_EVIDENCE` | |
| Fallback, unsupported/historical provider route, unknown entrant/process, uncontained execution, or unresolved cleanup | `NO_EVIDENCE` | |
| Fairness, parity, provider/model identity, billing route, causal execution, ranking, launch, virality, retention, or revenue represented as proven | `NO_EVIDENCE` | |
| Severe safety/accessibility/privacy incident not contained within the repair cap | `NO_EVIDENCE` | |
| Staff performed participant product steps, fabricated evidence, substituted rehearsal for human proof, or changed a threshold after seeing results | `NO_EVIDENCE` | |
| Product cohort: at most one played child runback, zero voluntary returns, or over 20 staff hours after 5 valid sessions | `NO_EVIDENCE` | |
| Demand closeout only: at day-14 close, 50 frozen and at least 40 delivered but only zero through three active commitments; or at least 50% of substantive replies report low trust when every non-withdrawn substantive reply has complete `reply_classified` evidence. Below 40 delivered is HOLD_INCOMPLETE, never this KILL | `NO_EVIDENCE` | |

`NO_EVIDENCE` is the zero baseline, not proof that a condition is false. During
an authorized run, replace it with `NO` plus a cited complete manifest or `YES`
plus an incident receipt.

## G. Cleanup and retention closeout

| Artifact class | Due rule | State | Receipt |
| --- | --- | --- | --- |
| Participant/provider-controlled artifacts | Participant controls; team makes no deletion claim | `NOT_APPLICABLE_TEAM_CUSTODY` | |
| Withdrawal-linked contact row, controlled correspondence, pseudonymous event/session rows, and unneeded raw local artifacts | Delete within 7 calendar days; retain only non-linkable aggregate decrement and deletion receipt digest | `NOT_STARTED` | |
| Private identities/contact map | Delete within 30 calendar days after close | `NOT_STARTED` | |
| Pseudonymous row-level evidence | Delete within 90 calendar days after final decision | `NOT_STARTED` | |
| Spawned processes/temp files | Reconcile at the end of every run/session | `NOT_STARTED` | |
| Aggregate decision | Retain only without row data, keys, free text, or identity link | `NOT_STARTED` | |

## H. Final decision record

| Field | Value |
| --- | --- |
| Evaluated source | `e004aaea86c097dc8427499d0c35413fc1e704a1` |
| Decision | `HOLD_NOT_AUTHORIZED` |
| Highest passed stage | `PACKETS_PREPARED_ONLY` |
| Public launch authorized | `false` |
| Outreach authorized | `false` |
| Provider execution authorized by this worksheet | `false` |
| Ranking/fairness claim eligible | `false` |
| Identity collected | `false` |
| Spend authorized | `false` |
| Evaluator | `OPERATOR_ASSIGN` |
| Independent reviewer | `OPERATOR_ASSIGN` |
| Evidence manifest digest | `MISSING` |
| Next exact gate | Separate operator authorization and evidence for the pure seat-swapped technical pair |

## Unresolved evidence distinction

A passing same-seed exact-seat-reversal pair proves bounded integration and
replay behavior. It does not prove the versioned parent -> harness change ->
played child runback required by the product cohort. Record and decide these as
separate stages. An unplayed runback proposal cannot satisfy the child-runback
row.
