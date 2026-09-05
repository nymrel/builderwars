# BuilderWars private alpha consent and privacy packet

Status: **NOT_OPEN / OPERATOR_ASSIGN**. Bound to source
`e004aaea86c097dc8427499d0c35413fc1e704a1`. This packet is an operating
disclosure for a future supervised local alpha. It is not legal advice, a
provider authorization, an acceptance of provider terms, or permission to
contact a participant.

## Owners required before use

| Role | Required value |
| --- | --- |
| Session owner | `OPERATOR_ASSIGN` |
| Support and incident owner | `OPERATOR_ASSIGN` |
| Private support channel | `OPERATOR_ASSIGN` |
| Privacy and deletion contact | `OPERATOR_ASSIGN` |
| Evidence custodian | `OPERATOR_ASSIGN` |
| Independent cleanup reviewer | `OPERATOR_ASSIGN` |

The cohort remains `HOLD_NOT_AUTHORIZED` while any value is
`OPERATOR_ASSIGN`. The local schema/drill in
[`AGENTWARS_SUPPORT_RUNBOOK.md`](AGENTWARS_SUPPORT_RUNBOOK.md) is not staffed
support and cannot fill these roles.

## Participant-facing disclosure

You are being invited to a private, supervised BuilderWars / AgentWars product
test. You will use a fictional `fantasy_redraft` game to inspect a local match
receipt, change an allowlisted agent/harness strategy, and attempt a verified
runback. The session lasts at most 75 minutes. Participation is optional,
unpaid, carries no prize or public attribution, and you may stop or withdraw at
any time without giving a reason.

### Your provider access stays under your control

- You install, authenticate, select, inspect, and revoke your own supported
  local provider route.
- Provider use can consume your subscription/free quota or incur charges on
  your provider account. BuilderWars cannot determine or guarantee the route,
  entitlement, remaining quota, billing treatment, or cost.
- BuilderWars operators, services, and the observer never receive your
  credential. For OpenRouter, your customer-local process necessarily reads
  `OPENROUTER_API_KEY` transiently and passes it only to the local
  adapter/child. It must not print, persist, upload, include in evidence, or
  disclose that value to staff. Other local CLI routes use your configured,
  customer-controlled sessions.
- You decide whether to proceed after reviewing your provider's current terms,
  quota, and cost. The observer cannot accept terms, choose an account/model,
  authenticate, paste a credential, or approve a charge for you.
- Stop before execution if a new sign-in, terms prompt, credential request, or
  unexpected charge appears.

Current executable route ids are `chatgpt_codex`, `opencode`, `openrouter`, and
`hermes`. `claude_code` is historical-only in this source and may not be used.
The current source of truth is the executable catalog and
[`AGENTWARS_PROVIDER_POLICY.md`](AGENTWARS_PROVIDER_POLICY.md).

### What BuilderWars does not do in this alpha

BuilderWars operators, services, and the observer do not:

- receive, copy, store, upload, escrow, print, include in evidence, or ask you
  to disclose a password, API key, OAuth code, token, cookie, credential-store
  content, or provider account detail; the only admitted credential handling is
  the transient OpenRouter customer-local process boundary described above;
- upload or publish your match evidence, prompt, raw model output, passport,
  receipt, feedback, or identity;
- create an account, connect a hosted runner, modify provider settings, change
  DNS/auth/production, send public content, or execute a protected deletion;
- attest which person, provider account, billing route, model, runtime, or
  harness caused a move; or
- claim competitive parity, fairness, model/provider superiority, a benchmark,
  leaderboard eligibility, ranking, launch, virality, retention, or revenue.

A replay PASS means the recorded evidence replayed under its declared rules,
engine, verifier, and manifest. A signed passport binds a versioned declaration
to a key and harness digest. Neither establishes provider/model identity or
causal execution. Review the full boundary in
[`AGENTWARS_CROSS_PROVIDER_MATCH.md`](AGENTWARS_CROSS_PROVIDER_MATCH.md).

## Identity-free observation

The research ledger uses a random cohort code. It does not admit your name,
email, handle, phone number, IP address, user agent, account, provider/model,
prompt, raw output, unrestricted stderr, URL, free-text biography, or contact
destination. The observer records only allowlisted task states, digest-bound
receipt references, rounded timestamps, structured comprehension answers,
accommodation class, stop/feedback codes, manual cost observation state, and
cleanup result.

If recruitment is separately authorized, identity and contact destination live
only in the access-controlled `contacts.private` map described in
[`BUILDERWARS_DEMAND_EXPERIMENT_BW_D14_01.md`](BUILDERWARS_DEMAND_EXPERIMENT_BW_D14_01.md).
They never enter the pseudonymous event or session ledger.

## Retention, withdrawal, and deletion

- You may stop the session immediately or request withdrawal through the
  assigned privacy/deletion contact.
- Within seven calendar days of a verified request, the team deletes your row
  from its private contact map, controlled delivery correspondence, every
  pseudonymous event/session row associated with you, and unneeded raw local
  session artifacts. Only a non-linkable aggregate decrement and a deletion
  receipt digest with no contact key or identity link may remain. BuilderWars
  does not claim to delete participant-controlled or provider-side artifacts.
- All remaining contact identities and destinations are deleted within 30
  calendar days after experiment close.
- All row-level pseudonymous experiment and session evidence is deleted within
  90 calendar days after the final decision. Only a non-identifying aggregate
  decision may remain.

These 7/30/90-day limits govern only this private alpha. They do not claim a
production retention policy or production deletion capability. The system
boundary is documented in
[`AGENTWARS_RETENTION_DELETION_ROLLBACK_RECOVERY.md`](AGENTWARS_RETENTION_DELETION_ROLLBACK_RECOVERY.md).

## Accessibility and support

You may request keyboard-only use, screen-reader review, zoom/text scaling,
reduced motion, extra orientation time within the 75-minute cap, or another
reasonable local accommodation. Choosing an accommodation is recorded only as
an allowlisted class. If the core loop cannot be completed or stopped safely
with the accommodation, the observer records the accessibility blocker rather
than coaching around it.

The assigned support/incident owner must be reachable in the assigned private
channel for the entire session and cleanup window. No public support channel,
SLA, or production incident response is implied.

## Consent choices

The observer reads each statement verbatim. The participant answers `YES` or
`NO`; no name or signature is collected in the research ledger.

1. I am at least 18, participation is voluntary, and I may stop or withdraw.
2. I understand that I control my provider access and that use may consume my
   quota or incur my provider-side cost.
3. I will not disclose a credential, personal/private dataset, confidential
   prompt, or sensitive model output during the session.
4. I understand that BuilderWars operators, services, and the observer will not
   receive my credentials or upload or publish my evidence; an OpenRouter
   customer-local process may transiently handle its environment key only
   within the disclosed local adapter/child boundary.
5. I understand that replay/passport evidence does not establish provider,
   model, person, billing route, runtime, fairness, parity, or ranking.
6. I consent to identity-free structured observation under the stated
   7/30/90-day deletion limits.
7. I know the assigned private support and privacy contacts and have had an
   opportunity to ask questions.

Every answer must be `YES` before any provider call. A `NO`, uncertainty, or
request for a different condition stops the session without persuasion. The
observer records the packet digest, cohort code, minute-rounded time, and
seven answer bits; this is an operating consent receipt, not identity or legal
attestation.

## Hard-stop and incident procedure

Stop immediately and preserve only the minimum redacted diagnostic evidence
when any of these occurs:

- a credential, private identity, confidential prompt/output, or unrestricted
  provider error appears;
- new provider terms, sign-in, charge, or ambiguous billing route requires an
  action the participant did not independently choose;
- an unsupported route, fallback, unknown process/entrant, or uncontained
  command appears;
- game, seed, source, passport, harness digest, seat reversal, or runback
  lineage differs from the manifest;
- replay, verifier snapshot, engine digest, evidence digest, secret scan, or
  cleanup fails;
- the participant misunderstands the truth boundary after the neutral check;
- the observer would need to perform a product action, accept terms, or attest
  a human action for the participant;
- contact identity enters a session/event ledger, an unauthorized message is
  sent, or a withdrawal/deletion request cannot be honored; or
- distress, harassment, accessibility failure, or another safety issue occurs.

The observer assigns only an allowlisted incident class, not free text; informs
the assigned support/incident and privacy owners; prevents further calls and
publication; reconciles processes and artifacts; and records a redacted stop
and cleanup receipt. A stopped session is learning evidence, not a launch pass.
