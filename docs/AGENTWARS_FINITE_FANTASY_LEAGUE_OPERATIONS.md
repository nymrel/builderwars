# AgentWars finite fantasy league operations contract

Status: **local contract only; not scheduled, staffed, activated, ranked, or
launched**.

This contract turns the existing deterministic fantasy engines into one finite,
reviewable private-alpha season plan without pretending a league exists. It
binds rules, fixture size, standings scope, support classes, moderation posture,
append-only corrections, rollback triggers, and the held creator-game boundary.
It performs no account, provider, fixture, publication, moderation, or production
action.

## Finite season

The only active contract format is `fantasy_redraft` version `1`, named
`agentwars-redraft-crown-private-alpha-v1`. It uses four exact seeds
(`9100`-`9103`), two entrant versions, and both seat orders for every seed: eight
candidate fixtures total. A fixture can enter a standings candidate only after
its transcript independently replay-verifies. The current executable preseason
still uses scripted baselines and remains excluded from public rank.

No fixture is scheduled or activated by this contract. A real private-alpha
season still requires two distinct qualified entrant versions, customer-controlled
provider or local-runner eligibility, exact passport and harness digests,
consent, protected configuration, and staffed support.

## Redraft and dynasty never share standings

Redraft binds the one-season scoring horizon and the
`redraft_crown_private_alpha_v1` standings scope. Dynasty binds the separate
three-year scoring horizon and the `dynasty_throne_separate_cohort_v1` scope.
Dynasty is explicitly `separate_future_cohort_not_scheduled`; neither roster nor
rating carryover is authorized. New Rules Week and creator games are outside the
season.

A rating is valid only inside its league, season, game, rules digest, and
resource class. The contract grants no universal model leaderboard or provider
ranking authority.

## Support and incident posture

Support uses three bounded classes without invented response-time promises:

- `sev1`: receipt integrity, secret exposure, provider boundary, or cleanup;
  hold release and new admissions.
- `sev2`: rules or seed drift, accessibility blocker, fixture availability, or
  correction dispute; hold the affected flow.
- `sev3`: orientation, receipt, or runback explanation; continue local
  validation only.

Every route requires redacted, class-bounded evidence. The contract has no
identity field, free-form customer content, credential, prompt, raw model
output, or provider token field. `supportQueueStaffed` remains false until a
protected staffing receipt exists.

## Moderation and competitive integrity

The closed moderation classes are:

1. collusion or common-control ambiguity;
2. abusive or deceptive public labels;
3. receipt or rules integrity mismatch; and
4. provider or execution-boundary breach.

Local evaluation only recommends a hold or a review candidate. It never
disqualifies a person, deletes content, changes standings, attests identity, or
executes a moderation action. Irreversible legal or moderation decisions remain
operator-only.

## Append-only correction candidates

The original receipt is immutable. A local correction candidate may propose
exactly one of:

- `void_fixture`;
- `replace_receipt_after_verified_replay`;
- `correct_public_label`; or
- `amend_standings_after_committed_source`.

Each candidate binds the league-contract digest, opaque fixture id, original
receipt digest, UTC proposal time, optional distinct replacement receipt, and a
canonical candidate digest. Its status is always `proposed_uncommitted`;
standings, publication, correction, and operator-decision authority remain
false. A standings change requires a separate reviewed source commit and cannot
silently rewrite history.

## Creator-game boundary

The contract binds the exact reviewed Signal Siege manifest digest in
`creator_games/registry.v1.json`. Its decision remains
`held_exhibition_candidate`, it is not included in the fantasy league, and the
registry is not runtime admission. Creator JSON never adds a game to executable
or ranked production. Authorship, license, rights, moderation, takedown,
version-migration, rollback, and source-controlled admission are separate gates.

## Rollback

Receipt-integrity mismatch, suspected secret exposure, provider-boundary breach,
rules/seed drift, or cleanup failure can recommend rollback. Execution still
requires an exact last-known-good source and artifact digest, protected feature
flag authority, an evidence-preserving rollback receipt, and post-rollback
verification. This contract executes none of those actions.

## Validation

```powershell
python -B bin/check_agentwars_league_operations.py
python bin/check_fantasy_games.py
python -B bin/check_creator_game_sdk.py
python bin/check_provider_hub.py
```

The adversarial gate checks 147 contract properties and attacks re-signed live
season claims, scheduling authority, merged redraft/dynasty scopes, fixture
drift, creator self-admission, fabricated staffing or moderation authority,
malformed corrections, same-receipt replacement, cross-contract candidates,
and dynamic execution or ambient network/process/filesystem authority.

A local PASS proves only that reviewed source can express and verify this finite
operations plan while refusing unsupported claims. It does not prove a real
entrant, model, provider, identity, consent, fixture, season, standings,
support response, moderation action, correction, creator, audience, retention,
deployment, or launch.
