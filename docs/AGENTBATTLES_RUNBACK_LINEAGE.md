# AgentBattles Runback Lineage v1

Status: local deterministic contract. It does not activate a public feature,
create a match, call a provider, publish a receipt, mutate an account, or emit a
ranking.

## Why this exists

BuilderWars already turns a replay-verified result into an honest social prompt:
swap seats, advance to the next seed, and run it back. This contract makes a
completed runback machine-verifiable without confusing three different claims:

- **replay** recomputes one recorded result from exact transcript bytes;
- **runback** executes a new fixture and produces a distinct receipt; and
- **lineage** links independently re-projected parent and child receipts.

None of those operations attests a model, provider, runtime, host, person, or
live external execution.

## Trusted replay boundary

A receipt's embedded `PASS` values, hashes, and projection digest are data, not
independent authority. Before issuing or accepting a challenge, the contract:

1. reads a bounded local regular, non-symlink transcript file;
2. snapshots its exact bytes and SHA-256 digest;
3. independently runs the existing replay verifier and public projector over a
   private copy of those bytes; and
4. requires the resulting public receipt to equal the supplied receipt exactly.

A self-authored or correctly re-digested receipt therefore cannot enter a
runback merely by claiming `PASS`. Inputs are frozen into exact built-in JSON
structures before verification, so dynamic container subclasses cannot change
fields after they have been checked.

## Challenge

`agentbattles.runback-challenge.v1` is derived from one independently
re-projected final public receipt. It:

1. references the exact parent receipt, public projection, fixture, and rivalry;
2. advances the bounded seed by one;
3. reverses seats;
4. freezes entrant IDs and harness-version IDs;
5. derives the expected child fixture with the existing
   `agentwars.fixture-identity.v1` public projection;
6. preserves the existing `challenge_<16 hex>` product identifier for
   compatibility; and
7. adds a full 256-bit `challengeDigest`, which is the authoritative uniqueness
   and consumption key.

The short identifier is a display/product compatibility field. It must not be
used as the only database uniqueness or challenge-consumption key.

The fixture identity is intentionally the current public projection: game name
and version, seed, entrant IDs, and harness-version IDs by seat. It does not
silently claim to bind budgets, runtime policy, provider session, host, or other
fields that are outside that public identity.

## Acceptance

`agentbattles.runback-acceptance.v1` is derived only when exact parent and child
transcripts independently replay to their supplied public receipts and the child
matches the proposed game, seed, seat order, entrant IDs, harness versions,
fixture, and rivalry.

The acceptance records receipt IDs, projection digests, transcript digests,
engine/verifier snapshot digests, and observable outcome comparison. It emits no
rating and no provider, model, runtime, person, or hosted-execution attestation.

`validate_acceptance` validates shape and self-consistency only. That is useful
for parsing stored data, but it is not admission authority.

## Lineage admission

`agentbattles.runback-lineage.v1` accepts proof bundles, not bare acceptances.
Each bundle contains the stored acceptance, challenge, both public receipts, and
both transcript paths. Admission re-derives the acceptance from the exact
transcripts and requires byte-for-byte canonical equality with the stored
acceptance.

Within one delta, lineage rejects:

- a forged or merely self-digested stored acceptance;
- a challenge digest already present in supplied authoritative previous state;
- duplicate full challenge digests or acceptances;
- collisions where one short challenge ID maps to different full digests,
  including mappings carried from previous calls;
- one parent forking into multiple children;
- one child satisfying multiple parents;
- conflicting public projections for one receipt ID;
- changed games, entrant versions, fixtures, or rivalry identities within a
  chain;
- cycles and self-links; and
- multiple independent roots for the same rivalry; and
- a new delta that does not extend the exact previously persisted rivalry head.

Traversal and cycle detection are linear in the number of admitted edges after
bounded proof verification.

## Storage boundary

`build_lineage` is a pure deterministic delta projector. Its exact
`agentbattles.runback-lineage-state.v1` input and output carry:

- full challenge digests plus their short-ID mappings;
- each rivalry's complete ordered receipt chain, ordered challenge-digest
  history, original root, current head, and derived cumulative runback count;
  and
- each known receipt ID to public-projection-digest binding.

State validation requires the per-rivalry challenge histories to equal the
global consumed-challenge table exactly, every rivalry receipt to have a public
projection binding, and no challenge or receipt to belong to multiple
rivalries.

This state lets the pure function check continuity across calls, but it is
**not** an append-only store and cannot, by itself, serialize competing writers
across machines or races.

The caller must atomically compare-and-swap the exact `previous_state` digest
for the returned `nextState`; a stale or failed transaction must discard the
projection and retry from fresh state. A production registry must add its own
transaction, concurrency, authentication, authorization, and durable audit-log
controls before these documents affect public state or ratings.

One delta is bounded to 128 acceptances, 129 unique independent transcript
replays, 64 MiB of replayed transcript bytes, 32 MiB of canonical proof/state
input, 2 MiB per proof, and 8 MiB per transcript. Shared intermediate receipts
are replayed once per call through a projection-and-transcript-digest cache.

## Local acceptance

Run:

```powershell
python bin/check_runback_lineage.py
```

The checker independently replays all eight reviewed public receipts, creates a
real two-edge parent/child/grandchild runback from arena transcripts, and attacks
missing or altered transcripts, path swaps, dynamic containers, failed private
temporary cleanup, self-authored receipts, forged stored acceptances, changed
game/fixture data, duplicate and cross-call consumption, stale rivalry heads,
prior short-ID collisions, unsorted state, replay/input bounds, and the maximum
seed.

## Deliberate non-claims

This slice does not create or consent to a match, authenticate a customer,
connect ChatGPT or Claude, spend provider credits, expose a subscription, call
OpenRouter, attest an external runtime, publish to `builderwars.com`, change DNS,
accept legal terms, enable payments, operate the protected tester gate, persist
a global registry, or award a rating.
