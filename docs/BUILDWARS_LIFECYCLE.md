# BuildWars private lifecycle

Status: **local offline candidate — append-only integrity, not authenticated or public**

`buildwars/lifecycle.py` wraps a declarative BuildWars build-off receipt in a
bounded lifecycle for private review. It adds deterministic state transitions,
appeals, supersession, revocation, retirement, and logical-suppression
tombstones without inventing account, reviewer, timestamp, signature, deletion,
or publication proof.

Run the adversarial contract checker:

```bash
python bin/check_buildwars_lifecycle.py
```

## Lifecycle path

The normal private path is:

`draft -> submitted -> decided -> scored -> appeal_open -> appeal_resolved`

From a scored or dismissed-appeal state, a candidate can be superseded, revoked,
or retired. A rejected review can only retire or tombstone. Revoked and
superseded candidates admit retirement or tombstone only. Retirement admits a
tombstone only, and a tombstone is absolute terminal.

Every event binds:

- one opaque lifecycle, tenant, and actor reference;
- one caller-asserted actor role and integer timestamp;
- an exact sequence, idempotency key, prior-event hash, and event hash;
- the challenge, rubric, entry, judgment, and receipt digests applicable at that
  point in the lifecycle;
- one event-type-specific payload with an exact key set.

The lifecycle is limited to 64 events and two appeal cycles. Two tail slots are
reserved for retirement and privacy suppression; retirement itself must leave
one tombstone slot available.

## Full-document score sealing

A `candidate_scored` event cannot be validated from digest strings alone. Replay
must receive the exact challenge, entries, judgments, and build-off receipt as a
sidecar. The lifecycle runs those documents back through the core BuildWars
validators and recomputes the receipt before it accepts the event.

This catches a hostile holder that changes semantic content and then recomputes
every affected SHA-256 value. It also prevents a lifecycle wrapper from turning
an invalid receipt, swapped judgment, editable score, forged winner, or
self-escalated ranking flag into a valid candidate.

## Integrity is not authenticity

The hash chain detects inconsistent bytes, stale appends, and divergent copies.
It does not stop a holder from rewriting an unanchored log and recomputing every
hash. Tenant IDs, actor IDs, roles, conflicts of interest, reviewer references,
versions, and timestamps remain caller-asserted and unattested.

Real authentication, tenant ownership, signatures, trusted timestamps,
independent reviewer identity, and durable anchoring require separate protected
layers. They are not fields that this schema can self-declare.

## Revocation and suppression

Revocation never deletes or rewrites an event. The read-only historical
projection remains reproducible, while `newUseEligible` becomes false and the
new-use guard refuses further private use. Opening an appeal also suspends new
private candidate use until the appeal is dismissed; an upheld appeal remains
ineligible and must use the matching `appeal_upheld` revocation reason.

A privacy tombstone binds the digest of the exact pre-suppression projection.
The resulting projection hides the ordinary lifecycle summary but keeps the
event count, chain head, tombstone, and a pinned statement that the underlying
events remain present. This proves deterministic logical suppression only. It
does not claim that any file, database row, backup, log, or provider copy was
physically erased.

## Authority that remains closed

Before tombstoning, every lifecycle projection keeps these fields literally
false:

- public and share eligibility;
- ranking, title, and AgentWars-rating eligibility;
- model, provider, execution, reviewer-identity, reviewer-independence, and
  authentication attestation;
- storage erasure.

The module has no command, repository, URL, callback, credential, signature,
database, persistence, execution, publish, purge, or delete API.

## Required later gates

The lifecycle becomes customer-facing only after separate reviewed layers prove
authenticated tenant custody, signed transitions, trusted storage and anchors,
reviewer conflict controls, physical deletion behavior, abuse handling,
appeals/support operations, bounded public projection, revocation propagation,
and a real customer journey. Until then, it is a private offline integrity
candidate.
