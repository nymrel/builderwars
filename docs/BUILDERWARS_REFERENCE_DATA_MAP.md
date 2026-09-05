# BuilderWars reference data map

Status: **source-bound local candidate; not a production inventory, privacy approval, or launch authorization**.

The executable contract is `publishing/reference_data_map.py`; its adversarial
checker is `bin/check_builderwars_data_map.py`. The contract is deliberately
deterministic and performs no I/O. It records what the repository currently
implements and keeps every deployment-specific fact that is not in source
visibly unresolved.

## What is mapped

| Reference system | Current custody | Production claim |
| --- | --- | --- |
| Mobile Arena browser state | Two `localStorage` keys: starter-guide completion and a private local blueprint | None; state remains on that browser unless a future reviewed flow is added |
| Mobile Arena static cache | Service-worker `CacheStorage` for static assets and the reviewed local fixture | None; cache residency is the user's browser, not a production-region claim |
| Hosted reference store | Nine SQLite tables covering opaque owners, pairing, runners, nonces, jobs, attempts, results, replay projections, and browser idempotency | None; SQLite is a conformance reference, not the selected production store |
| Customer-local runner | Provider credentials or sessions, one-time pairing input, prompts, model output, and bounded runner diagnostics | Provider authority must stay customer-local and must not enter the hosted control plane or a public projection |
| Reviewed public artifacts | Receipt, replay, proof, and share projections admitted by explicit source review | Repository artifacts only; no public hosting or reviewer identity is attested |
| Local launch evidence | Source commit/tree, bounded command outcomes, file digests, and protected holds | Local evidence only; it does not prove a production deployment |

The contract names 19 reference datasets and five data flows. It binds each
applicable dataset to the existing retention/deletion class in
`publishing/retention_recovery.py`, including append-only correction lineage,
verified-request deletion candidates, nonce expiry, policy-held operational
events, and synthetic-probe cleanup. This binding is a policy-shape contract;
it does **not** establish exact retention periods or prove external deletion.

## Public projection boundary

Only bounded, reviewed receipt/replay fields may become publication
candidates: digests, bounded labels or verified moves, score, correction
lineage, and the review decision. Public eligibility is not direct publication;
the existing source-decision, replay-verification, and false-attestation gates
still apply.

The contract explicitly denies public projection of:

- raw prompts or raw model output;
- provider keys, access/refresh tokens, subscription cookies, or pairing secrets;
- Clerk subjects, email addresses, IP addresses, and opaque owner identifiers;
- private input bytes and sealed idempotency responses.

Digests do not prove model identity, provider identity, subscription ownership,
human identity, or human review. A replay projection stored in the hosted
reference table remains private until the publication pipeline independently
admits its bounded public form.

## Production facts still held

The reference map refuses to invent the following:

1. The production system inventory and accountable owners.
2. Regions, residency, and cross-border transfer paths.
3. Subprocessors and their contractual roles.
4. Processing purposes, legal basis, privacy notice, and age-related obligations.
5. Exact retention periods and policy owners.
6. Deletion-propagation targets, timing, and the request/DSAR process.
7. Backup destinations, encryption, access, retention, RTO, RPO, and restore evidence.
8. Production observability storage, sampling, and support access.

Those facts require the exact deployment architecture plus operator and, where
appropriate, qualified policy/legal review. The contract carries false
authority flags for all eight topics, deletion propagation, backup/restore,
legal review, launch approval, and launchability.

## Verification

Run from the repository root:

```powershell
python -B bin/check_builderwars_data_map.py
```

The checker discovers the current SQLite tables, browser storage keys, and
service-worker cache directly from source; verifies every retention resource
class is represented; resolves all source anchors; and attacks the contract
with resealed mutations that attempt to invent a region or subprocessor,
publish private data, remove deny rules, hide unknowns, approve production, or
claim launch authority.

Passing proves that the repository's **reference candidate** is internally
consistent with the current source. It does not prove production storage,
residency, privacy compliance, deletion, backup, restore, consent, or launch.
