# AgentWars retention, deletion, rollback, and recovery contract

Status: **local contract and deterministic drills only**. Nothing in this file
or its checker reads production data, verifies a customer request, deletes an
external record, creates a backup, restores an artifact, changes a feature
flag, deploys a release, or executes rollback.

Run the adversarial contract:

```powershell
python bin\check_agentwars_retention_recovery.py
```

## Why this is a separate contract

BuilderWars already has two narrower truths:

- `buildwars/lifecycle.py` records append-only revocation, retirement, and
  privacy tombstones. A tombstone proves logical suppression while explicitly
  preserving the hash-chained history; it does not claim storage erasure.
- `provider_hub_hosted` exercises tenant-scoped deletion and transaction
  rollback against an ephemeral local SQLite control plane. Those tests do not
  prove production storage topology, backup coverage, restore ability, or a
  deployed rollback target.

This contract fills the launch-evidence gap without weakening either boundary.
It handles digest-only resource inventories and release manifests in memory,
then fails closed when a request, tenant, class policy, source binding, or
recovery step drifts.

## Resource classification

| Resource class | Local disposition | Retention class | Important boundary |
| --- | --- | --- | --- |
| `public_receipt_projection` | Simulate logical suppression | Append-only correction history | Preserve lineage; never rewrite a historical receipt |
| `public_replay_projection` | Simulate logical suppression | Append-only correction history | Preserve replay/correction lineage |
| `private_submission` | Simulate physical deletion | Delete on verified request or policy expiry | The drill has no payload and proves no external deletion |
| `temporary_transcript` | Simulate physical deletion | Delete on verified request or policy expiry | A production TTL still needs an approved policy |
| `runner_profile` | Simulate physical deletion | Delete on verified request | Provider credentials are not admitted into the manifest |
| `nonce_replay_record` | Simulate physical deletion | Expire after the replay window | Production enforcement is not configured here |
| `operational_event` | Hold for policy review | Production policy required | No retention period is invented |
| `synthetic_probe` | Simulate physical deletion | Delete after the drill | Cleanup is local and digest-only |

The contract intentionally does not invent day counts. Production retention
periods depend on the final data map, product behavior, incident needs,
applicable obligations, and an operator-approved policy. An unapproved class is
held atomically instead of partly deleted.

The source-bound candidate in
[`BUILDERWARS_REFERENCE_DATA_MAP.md`](BUILDERWARS_REFERENCE_DATA_MAP.md) maps
the currently implemented browser, hosted-reference, customer-local, public,
and evidence surfaces to these eight resource classes. It is not the final
production data map: regions, subprocessors, purposes, exact periods, deletion
propagation, and backup/restore remain protected facts.

## Deletion drill

The local flow is:

```text
sorted digest-only inventory
  -> synthetic request (not identity or consent)
  -> tenant and class-policy validation
  -> exact all-or-none plan
  -> in-memory deletion/suppression simulation
  -> digest-bound drill receipt
```

The request cannot attest a person, account owner, or consent. The plan refuses
unknown resources, cross-tenant scope, unknown classes, malformed identifiers,
future resources, partial action sets, and action-policy drift. Public evidence
uses logical suppression with preserved lineage. A policy-held resource blocks
the whole plan.

An injected deletion failure produces
`DRILL_REFUSED_INJECTED_FAILURE`, applies zero simulated actions, and records a
post-state digest. A passing receipt still keeps both
`productionDeletionProven` and `actionsExecutedInProduction` false.

## Rollback and recovery drill

The recovery flow binds five last-known-good dimensions:

1. source commit;
2. source tree;
3. artifact digest;
4. verifier digest; and
5. configuration digest.

A snapshot is only a digest manifest with
`digest_manifest_only_no_backup_created`. It cannot claim that an artifact or
database backup exists. A rollback plan binds the current release, a distinct
last-known-good snapshot, the trigger, the exact action order, and the exact
post-restore validation order.

The drill simulates:

```text
hold release
  -> select last-known-good digest manifest
  -> simulate artifact restore
  -> reverify source/tree/artifact/verifier/configuration
  -> record cleanup
```

Four injected failure classes prove fail-closed behavior:

- snapshot unavailable;
- artifact restore failure;
- verification failure; and
- cleanup failure.

The passing drill is an in-memory manifest transition. It keeps
`productionRestoreProven`, `rollbackExecutedInProduction`, and
`actionsExecutedInProduction` false.

## Production activation evidence still required

Before any deletion or recovery claim can become production evidence, the
source-bound launch pack must separately prove all of the following for the
exact target environment:

1. approved data inventory, owners, storage systems, processors, residency,
   retention periods, and deletion/suppression behavior;
2. authenticated requester and tenant authorization without putting identity
   or secrets in the public receipt;
3. deletion propagation across primary stores, queues, caches, search,
   derivatives, logs, analytics, support systems, and documented backup expiry;
4. an idempotent deletion job, retry/dead-letter path, redacted audit receipt,
   and tenant-isolation proof;
5. an externally stored and access-tested backup for the exact last-known-good
   source, artifact, verifier, configuration, and data schema;
6. recovery objectives, compatibility rules, migration/reversal plan, protected
   flag procedure, and an independently verified rollback target;
7. a supervised restore/rollback drill with timestamps, operator identity,
   source-bound receipts, external probes, cleanup, and post-drill review; and
8. an approved incident, support, privacy, and communication path for deletion
   or recovery failure.

Stage 12 remains protected until those facts are proved against a real target.
BuilderWars.com apex and `www` are outside this local contract.

## Production authority

Every generated contract, inventory, request, plan, snapshot, and receipt keeps
all of these false:

- production data read;
- production deletion executed;
- production backup configured or read;
- production restore or rollback executed;
- protected flags or deployment mutated;
- external storage configured;
- operator authority; and
- launchability.

Local success means only that the classification, binding, atomic refusal, and
failure-drill logic passed for synthetic digest manifests.
