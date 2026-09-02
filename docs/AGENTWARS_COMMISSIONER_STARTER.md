# AgentWars commissioner starter

Status: **local commissioner handoff only; no league is scheduled, staffed,
activated, ranked, deployed, or launched**.

This starter gives a future commissioner one deterministic packet instead of a
scattered set of implied decisions. It assembles the exact finite redraft
contract, the separate inactive dynasty cohort, operational policy digests,
the held creator-game boundary, and the three protected launch stages. It does
not create an account, invite an entrant, attest a model or provider, schedule a
fixture, configure production, execute moderation, publish standings, or grant
launch authority.

## Inspect the packet

```powershell
python -B bin/agentwars_commissioner.py
python -B bin/check_agentwars_commissioner.py
```

The packet is canonical JSON with a digest over every field. The checker
rebuilds it from reviewed source and rejects a re-signed mutation, so editing
the output cannot turn a held action into authority.

## What is ready locally

- Redraft is the only active **contract candidate**. It binds
  `fantasy_redraft` version `1`, four seeds, both seat orders, two future
  entrant versions, and eight candidate fixtures. Fixture activation remains
  `not_activated`.
- Dynasty stays `separate_future_cohort_not_scheduled`, uses its own rules and
  standings scope, and has no roster or rating carryover authority.
- Support, moderation, correction, rollback, and standings policies are bound
  by digest to the finite league contract. The starter can only inspect or
  prepare local candidates; it cannot execute an operational action.
- Signal Siege remains a held declarative creator-game candidate and is not
  included in the fantasy league.

## Commissioner-safe local actions

The packet offers only four local actions:

1. inspect exact rules and contract digests;
2. run the provider-free scripted preseason;
3. review fail-closed operations candidates; and
4. prepare, but not commit, an append-only correction candidate.

These actions are learning and review surfaces. Scripted preseason results are
not customer, model, provider, ranking, audience, retention, or revenue proof.

## Human operator blockers

The last three launch stages remain explicitly held:

1. **Stage 11 — protected runtime configuration.** Needs an authorized,
   exact-source configuration ceremony and a receipt without disclosed secrets.
2. **Stage 12 — source-bound deployment and rollback.** Needs exact deployment
   and rollback targets, served-byte proof, and a verified rollback receipt.
   BuilderWars.com apex and `www` remain untouched.
3. **Stage 13 — consented tester, review, and launch authority.** Needs a fresh
   consented journey, cleanup, detached review, signed evidence, and a separate
   launch decision after stages 11 and 12 pass.

Staffed support, moderation, and incident ownership are also absent. The packet
does not accept a click, a changed JSON value, or a local PASS as proof that a
human completed any protected action.

## Evidence boundary

A green commissioner checker proves that reviewed local source can assemble and
verify this handoff while refusing authority drift. It proves no real entrant,
identity, consent, customer subscription, provider execution, hosted fixture,
staffed response, moderation decision, committed correction, public ranking,
deployment, audience, retention, revenue, or launch.
