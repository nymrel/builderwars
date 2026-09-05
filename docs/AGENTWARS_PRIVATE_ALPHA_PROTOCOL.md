# BuilderWars / AgentWars private alpha protocol

Status: **NOT_OPEN**. This is an identity-free operating contract bound to
source `e004aaea86c097dc8427499d0c35413fc1e704a1`. It authorizes no provider
execution, participant contact, account access, spend, deployment,
publication, ranking, or production change.

## Purpose and narrow hypothesis

The private alpha asks one question: can an external builder use a
customer-local harness to create a replay-valid fantasy-redraft receipt,
understand exactly what the receipt does and does not prove, change the
harness strategy, complete a versioned child runback, and voluntarily return
within seven days?

The test is not a model benchmark, provider comparison, fairness study, public
league, marketing launch, or proof of demand. It is a supervised product
falsification exercise for the narrow build -> compete -> inspect -> improve
-> run back loop described in
[`AGENTWARS_NORTH_STAR.md`](AGENTWARS_NORTH_STAR.md) and reviewed in
[`BUILDERWARS_FABLE_5_1_TOP_DOWN_REVIEW_2026-09-01.md`](BUILDERWARS_FABLE_5_1_TOP_DOWN_REVIEW_2026-09-01.md).

## Gate 0: source and authority

Before scheduling a participant, the observer records all of the following in
the evidence manifest:

- exact source SHA
  `e004aaea86c097dc8427499d0c35413fc1e704a1` and a clean-tree result;
- the digest of this protocol, the consent/privacy packet, and the decision
  worksheet;
- `OPERATOR_ASSIGN` values for session owner, support/incident owner, privacy
  contact, private support channel, evidence custodian, and cleanup reviewer;
- a passing local launch pack with stages 11 through 13 still held, consistent
  with
  [`AGENTWARS_LOCAL_LAUNCH_EVIDENCE_PACK.md`](AGENTWARS_LOCAL_LAUNCH_EVIDENCE_PACK.md);
- and a separate operator authorization for the Gate 1 technical pair that
  names the two routes, game, seed, quota/cost disclosure, and hard stops.

Missing authority or an unassigned owner yields `HOLD_NOT_AUTHORIZED`. It is
not permission to infer a role, contact a candidate, or use a provider.

## Gate 1: protected technical proof

The first technical gate is exactly one operator-authorized, customer-local,
explicitly unranked, same-game/same-seed exact-seat-reversal pair for
`fantasy_redraft`. It uses two distinct executable provider routes from the
current catalog: `chatgpt_codex`, `opencode`, `openrouter`, or `hermes`.
`claude_code` is historical-only and is not executable in this source.

The operator and customer control authentication. BuilderWars operators,
services, and the session observer must never receive a credential. For
`openrouter`, customer-local execution necessarily reads
`OPENROUTER_API_KEY` transiently and passes it only to the local adapter/child;
the value must never be printed, persisted, uploaded, included in evidence, or
disclosed to staff. The other executable routes use customer-controlled,
already-configured local CLI sessions. Fresh consent must disclose that the two
calls use participant-controlled provider access and can consume quota or
incur customer-side cost. Provider execution remains a protected action.

The pair passes only when all of these are true:

1. both matches use the identical game, seed, rules, versions, passports, and
   entrant strategies, with only seat assignment reversed;
2. each process exits `0`, all accepted moves are claimed `source=model`, and
   no fallback, partial-model, forfeit, abort, or blocked outcome occurs;
3. two signed Agent Passports verify and bind the declared harness digests;
4. independent replay returns `replay_verdict=PASS`,
   `effective_verdict=PASS`, `engine_digest_match=true`, and
   `verifier_snapshot_match=true` for both matches;
5. a human records the provider-displayed or locally observable cost/quota
   before and after, including `not_available` rather than an estimate when no
   trustworthy observation exists;
6. the redacted evidence passes a secret scan and contains no credential,
   prompt, raw model output, personal identifier, or unrestricted stderr;
7. every spawned process and temporary local artifact is accounted for in a
   cleanup receipt; and
8. the result carries no fairness, provider identity, model identity, billing
   route, causal execution, harness superiority, or ranking claim.

The route and receipt truth boundary is governed by
[`AGENTWARS_PROVIDER_POLICY.md`](AGENTWARS_PROVIDER_POLICY.md), the signed
passport boundary by
[`AGENTWARS_CROSS_PROVIDER_MATCH.md`](AGENTWARS_CROSS_PROVIDER_MATCH.md), and
the browser/account non-authority boundary by
[`AGENTWARS_BROWSER_AUTHORIZATION_BOUNDARY.md`](AGENTWARS_BROWSER_AUTHORIZATION_BOUNDARY.md).
Where prose conflicts with executable catalog state, the current catalog and
its passing checker control; stale prose is a held documentation defect, not a
route authorization.

Gate 1 proves only that the two customer-local routes can produce two
replay-valid, source-claimed artifacts under a seat reversal. It does not prove
competitive parity or the later product iteration loop.

## Gate 2: bounded certification admission

Only after Gate 1 passes may the integrator admit the separately claimed
certification slice: an offline seat-swap pair validator, adversarial self-tests,
and provider-policy/documentation corrections. That slice may make no provider
call, add no schema, enable no ranking, deploy nothing, and touch no protected
stage. Failure or ambiguity returns the project to `HOLD_TECHNICAL_REPAIR`.

## Gate 3: demand recruitment

Only after Gate 2 passes may a separate operator authorization open
`BW-D14-01`. Its fixed 14-calendar-day, identity-separated recruitment test is
defined in
[`BUILDERWARS_DEMAND_EXPERIMENT_BW_D14_01.md`](BUILDERWARS_DEMAND_EXPERIMENT_BW_D14_01.md).
A demand GO permits only a separate operator decision about authorizing the
cohort. It does not open, schedule, contact, or run the cohort by itself.

## Gate 4: cohort and participant criteria

The supervised cohort targets six external builders and requires at least five
valid sessions. A participant must:

- be at least 18 and not have contributed to this source or prior internal
  rehearsals;
- have recent agent, harness, or model-assisted workflow experience;
- be able to use a local CLI and browser without the observer operating either
  for them;
- use only fictional fixtures and their own already-configured provider route;
- accept the identity-free consent and privacy packet; and
- reserve no more than 75 minutes for the live session.

The target mix is four harness/agent builders and two developer or strategy
builders. At least two sessions must exercise an accommodation such as keyboard
only, zoom/text scaling, screen-reader review, or reduced motion. The
participant is represented only by a random cohort code. Recruitment and
contact details, if separately authorized later, never enter the session
ledger.

The cohort opens only on a separate written authorization after the demand
gate. Its fixed window begins at the recorded cohort `OPEN` timestamp and ends
exactly 14 days later. All six primary sessions must occur during days 1 through
7. Each participant may return only during the 168 hours following their own
primary session and never after the cohort's day-14 close. Evaluate the cohort
exactly at the day-14 close; do not extend a session or return window to improve
the result.

## The 75-minute session

| Minute | Participant action | Observer boundary | Required evidence |
| ---: | --- | --- | --- |
| 0–5 | Read the short truth and provider-use disclosures; ask questions; consent or stop | Do not interpret consent for the participant | Consent packet digest, cohort code, consent state |
| 5–10 | Explain what they believe a receipt proves | Ask the four neutral questions verbatim | Pre-task comprehension answers |
| 10–25 | Run or inspect the approved local `fantasy_redraft` baseline | Never authenticate, paste a secret, choose a model, or take control | Parent receipt digest, exit, replay result, observed cost state |
| 25–35 | Inspect proof, replay, passport, and eight false attestation boundaries | Give no competitive conclusion | Proof-inspection completion and confusion class |
| 35–50 | Change one allowlisted strategy or harness version themselves | Do not write the change for them | Before/after harness digest and version note |
| 50–62 | Run the played child runback and verify its parent/child lineage | Stop if the path is unplayed, unverifiable, or requires staff action | Child receipt, lineage, replay result, cleanup inventory |
| 62–68 | Review a neutral peer receipt and answer the truth questions | No provider or model names in comparative questions | Post-task comprehension answers |
| 68–75 | Give structured feedback and choose whether to receive a one-time seven-day return code | No free-text personal data and no pressure to return | Identity-free rubric, return invitation choice |

A session is valid only when the participant, without staff performing product
steps, reaches either a verified child runback or a recorded fail-closed stop.
A stopped session remains valid learning when its stop evidence is complete; it
never counts as a completion.

## Truth-boundary comprehension

Ask these questions without provider or model names:

1. Does replay PASS prove who or which model produced a move?
2. Does a signed passport prove the provider account, billing route, runtime,
   person, or causal model execution?
3. Can two receipts from different local routes be used as a fair public
   ranking under this protocol?
4. What is the one thing the receipt does prove?

Passing answers are: no; no; no; and that the recorded moves, state
transitions, rules, hash chain, scoring, result, engine digest, and verifier
snapshot replayed under the declared local manifest. The observer records only
allowlisted answer codes, not a transcript.

## Evidence manifest

Each session manifest is stored outside tracked source and includes only:

- protocol, consent, worksheet, source, game, seed, rules, engine, verifier,
  strategy, harness, passport, parent receipt, child receipt, and cleanup
  digests;
- a random cohort code, session sequence, timestamps rounded to the minute,
  duration, accommodation class, and allowlisted stop/feedback codes;
- exit and replay verdicts, manual cost observation states, truth-answer codes,
  runback completion, and seven-day return state; and
- explicit false values for identity collection, credential receipt by a
  BuilderWars operator/service/observer, credential printing/persistence/upload
  or evidence inclusion, publication, parity, attestation, ranking, spend by
  BuilderWars, production authority, and public-launch authority.

No name, email, handle, IP address, user agent, account, provider credential,
prompt, raw output, unrestricted note, or contact destination is admitted.
Use the privacy boundary in
[`AGENTWARS_MEASUREMENT_CONTRACT.md`](AGENTWARS_MEASUREMENT_CONTRACT.md) and
the feedback vocabulary in
[`AGENTWARS_TESTER_CEREMONY.md`](AGENTWARS_TESTER_CEREMONY.md); local or
synthetic rehearsals never count as human evidence.

## Product cohort decision

Apply these gates exactly at the fixed cohort day-14 close:

### `GO_NEXT_PRIVATE_GATE`

All must be true:

- at least five sessions are valid;
- every completed parent and child receipt passes independent replay and every
  evidence digest and cleanup inventory reconciles;
- at least four valid participants complete the baseline, harness change, and
  played child runback without staff performing a product step;
- at least four of the minimum five valid participants pass all critical
  neutral-peer truth boundaries uncoached;
- at least two valid participants voluntarily execute the identity-free
  seven-day return, producing a second replay-valid child runback;
- both accommodation sessions complete or fail closed without a severe
  accessibility issue;
- there are zero severe credential, privacy, provider-policy, safety,
  evidence-tamper, ranking/fairness-misrepresentation, accessibility, or
  cleanup issues; and
- cohort work stays within 16 staff hours plus at most four repair hours, with
  $0 BuilderWars spend.

### `HOLD_REPAIR_OR_MORE_EVIDENCE`

Use HOLD when no KILL condition occurred but any GO threshold is missing,
including only four valid sessions, one repairable comprehension or
accessibility failure, fewer than two observed seven-day returns at the fixed
close, or incomplete non-sensitive evidence. One bounded repair pass may use
the four-hour repair reserve; it cannot extend the 14-day window, change the
threshold, or replace a participant result with a rehearsal.

### `KILL_CURRENT_WEDGE`

Kill the tested wedge immediately for any secret or credential exposure,
unauthorized provider/account action, terms ambiguity that cannot be resolved
without accepting on someone else's behalf, evidence tamper or replay
inconsistency, public/ranking/fairness misrepresentation, uncontained process,
unreconciled cleanup after the repair cap, severe unmitigated accessibility or
safety issue, or staff fabrication/substitution. Also kill after five valid
sessions if at most one participant completes a played child runback, no
participant voluntarily returns, or total work exceeds 20 staff hours.

## Hard stops and cleanup

Stop immediately if a credential is requested or displayed, a provider asks
for new terms or an unexpected charge, a fallback occurs, route identity is
uncertain, the game/seed/seat reversal drifts, replay or digest verification
fails, a participant is coached past truth confusion, an unknown entrant or
process appears, contact data reaches the evidence ledger, or any required
cleanup cannot be proven.

The participant owns provider-side and local provider artifacts. The observer
can describe cleanup but cannot claim provider deletion. Local evidence
retention follows
[`BUILDERWARS_ALPHA_CONSENT_AND_PRIVACY.md`](BUILDERWARS_ALPHA_CONSENT_AND_PRIVACY.md)
and is reconciled using the categories in
[`AGENTWARS_RETENTION_DELETION_ROLLBACK_RECOVERY.md`](AGENTWARS_RETENTION_DELETION_ROLLBACK_RECOVERY.md).

## Known design conflict: pair proof versus child runback

Gate 1 is a pure seat-swap integration proof. The cohort's value hypothesis
requires a versioned parent -> harness change -> played child runback. These are
different claims and must not be collapsed. The current source's local starter
material includes an unplayed runback proposal; that does not satisfy the
cohort. Until a later, separately reviewed path proves played child lineage,
the cohort remains `NOT_OPEN` even if Gate 1 passes.
