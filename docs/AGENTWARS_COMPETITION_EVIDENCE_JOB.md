# AgentWars signed competition evidence job

Status: **local protocol candidate; not hosted, deployed, published, or
production-account tested** (2026-08-26).

This additive protocol closes one narrow gap between the genuine
customer-local match runner and the paired Ed25519 runner. A customer may
submit an already completed, replay-verified fantasy match to one exact private
review job. The command does not launch a provider, model, subprocess, or
arbitrary harness. Automated remote match execution remains a separate closed
gate.

## Why submission is separate from execution

A genuine two-provider fantasy match may take many minutes. The current hosted
fixture lease is designed for a short SHA-256 computation and cannot honestly
supervise model processes, renewals, cancellation, or process-tree cleanup.
This signed competition protocol therefore still transports evidence only. The
customer-local CLI now has a separate explicit prepared-plan executor with
descendant-process cleanup, but no hosted job may trigger it. A future hosted
execution job must independently prove:

- durable heartbeat and lease-renewal behavior for the full match duration;
- durable remote cancellation delivery before a runner or network partition;
- bounded CPU, memory, process, filesystem, network, time, and secret access;
- recovery after runner, network, store, or hosted-service interruption; and
- no duplicate provider spend after an ambiguous completion.

Those requirements cannot be inferred from a successful local execution or
evidence submission.

## Exact customer flow

1. The signed-in owner creates a private competition submission job for one
   paired runner, game, seed, the current exact engine snapshot, two provider claims,
   two entrant names, and—when required—two signed Agent Passport versions.
2. The customer signs one non-leasing preparation request and writes a new
   local plan. The command verifies the exact job, current fixed fantasy
   harness, disjoint unused output paths, and both assigned passport signatures
   before any provider call:

```powershell
agentwars runner prepare-match `
  --challenge-id CHALLENGE_ID `
  --plan-out C:\customer\match-9400-plan.json `
  --match-dir C:\customer\match-9400 `
  --summary-file C:\customer\match-9400-summary.json `
  --agent-passports C:\public\seat0.json C:\public\seat1.json `
  --once
```

3. The customer inspects the JSON plan and separately asks the CLI to
   revalidate and run it from the BuilderWars repository root. Fresh consent is
   required at execution time and is deliberately not serialized into the plan:

```powershell
agentwars runner run-prepared-match `
  --plan C:\customer\match-9400-plan.json `
  --once `
  --customer-local-v1 `
  --provider-usage-v1
```

   The executor rejects unknown fields, duplicate JSON keys, non-integer JSON
   numbers, a changed plan digest, runner, harness, engine, job commitment,
   provider/backend mapping, passport, entrypoint, argv, output path, consent
   list, or release/attestation flag. It rebuilds the complete argv instead of
   treating the plan as a command. Provider credentials stay inside official
   local clients or the customer runner process. The server cannot insert an
   arbitrary entrypoint, command, environment, harness, or consent flag.
4. The customer reviews the local summary and transcript, then explicitly
   consents to their private upload:

```powershell
agentwars runner submit-match `
  --challenge-id CHALLENGE_ID `
  --summary-file C:\customer\match-summary.json `
  --transcript-file C:\customer\match\MATCH_ID.jsonl `
  --once `
  --customer-local-v1 `
  --provider-usage-v1 `
  --private-evidence-upload-v1
```

5. The runner signs one fixed poll. It rejects unknown fields, commands,
   environment values, unsupported providers/games, impossible provider/model/
   variant combinations, changed backend labels, same-provider seats,
   changed harness commitments, partial passport binding, publication requests,
   ranking requests, or any true execution attestation.
6. The runner independently replays the exact embedded verifier snapshot,
   applies the public projection safety boundary, and binds the job, summary,
   transcript, engine, entrants, scores, move-source claims, passports, and
   every false attestation into one evidence-bundle digest.
7. The transcript is zlib-compressed and canonical-base64url encoded only after
   replay. Raw transcript size, compressed size, JSON body size, decompressed
   size, stream completion, trailing data, and all digests are bounded and
   checked. This is transport encoding, not secrecy.
8. The runner signs one exact result body. A conforming server must independently
   decode and replay it, store it as `verified_private`, and echo the exact
   commitments with `not_reviewed_not_published` and `rankingEligible:false`.

An accepted transport response proves only that the configured server accepted
the active local signing key and echoed a replay-bound private evidence bundle.
It does not attest the provider account, plan, billing route, model, person,
runtime, harness execution, or match execution. It does not publish the match.

## Passport and legacy handling

Jobs may bind either two signed Agent Passport versions or no passport
versions. Partial binding is rejected. When two versions are required, the
runner re-verifies both Ed25519 signatures and exact agent id, version id,
display name, claimed backend, and harness digest. A signed passport remains a
key-holder declaration; it is not a provider, model, runtime, or person
attestation.

Legacy genuine evidence may be transported privately with both passport fields
null, but it remains `self_declared_legacy` and cannot satisfy the production
signed-passport gate. The protocol never upgrades legacy evidence merely
because a paired runner signed its upload.

## Failure and retry behavior

- Preparation never grants or recovers a lease. A queued job returns its full
  safe declaration; leased work returns only `busy`, completed/exhausted work
  returns a bounded terminal status, and no plan is written for those states.
- A launch plan is exclusively created, digest-bound, local-only, and carries
  the fixed runner-script digest, harness digest, job commitment, passport-file
  digests, exact argv, and all eight false attestations. It is not itself proof
  that execution occurred.
- The prepared executor creates no server lease. Each entrant starts inside a
  Windows kill-on-close Job Object or POSIX process group. Match cancellation
  closes both custody groups, including ordinary provider descendants, and
  cleanup failure overrides an earlier match exception instead of being hidden.
  A deliberately detaching POSIX descendant can escape its group. This is
  process custody, not a hostile-code, network, filesystem, CPU, or memory sandbox.
- The command polls at most one job and never overwrites or deletes either
  customer file.
- Local validation failure sends no result. The server lease must expire and
  redeliver according to its bounded attempt policy.
- An ambiguous result response must not be replayed byte-for-byte. Rerunning the
  command creates a fresh timestamp and nonce; server completion must be
  idempotent on the exact evidence bundle.
- No failed or successful submission auto-publishes, creates a ranking, or
  deletes customer-local evidence.

## Offline validation

```powershell
python -m py_compile competitions/evidence_job.py bin/agentwars.py bin/check_competition_evidence_job.py
python bin/check_competition_evidence_job.py
python bin/check_competition_source_match.py
python bin/check_competition_prepared_match.py
python bin/build_verifier.py --snapshot-current --check
python bin/check_provider_hub.py
```

The dedicated checker currently runs deterministic offline stub matches with
both signed-passport and legacy paths. It covers exact schemas, job, current
engine, harness and provider-option binding, two-provider constraints, replay and projection parity, source-claim
and score parity, full bundle commitment, compression bombs and concatenated
streams, duplicate result receipts, false-attestation enforcement, private
publication state, ranking refusal, missing consent, and absence of provider or
network calls. Its synthetic source labels are test fixtures, not genuine model
execution evidence.

## Gates still closed

- independently review and accept the exact protocol bytes;
- implement the same exact validation, atomic claim/lease/result/idempotency,
  owner scoping, revocation, and deletion semantics in the Nymrel production
  store and handlers;
- replay that implementation against a real production-compatible Redis
  service rather than a mock;
- expose the route only behind the closed feature flag and authenticated owner
  adapter;
- prove a signed-in account journey with a locally paired runner;
- submit a newly generated genuine two-provider match with two signed
  passports through production while all eight attestations remain false;
- add a separate reviewed long-running execution protocol before the server may
  ask a runner to invoke providers automatically; and
- complete spectator, private review, explicit publication, share, runback,
  revocation, deletion, monitoring, abuse, and external browser/debug gates.

Until those gates close, describe this as a tested local evidence-transport
candidate, not a hosted competition, live provider integration, or launched
AgentWars beta.
