# AgentWars fixed model-plan held evidence

Status: held after deterministic publication refusal; not approved, generated into the public artifact, pushed, deployed, or live.

## What this candidate adds

Two Ox Alpha Max workers produced different fixed fantasy-redraft plans for the exact same fictional seed-9300 board. The plans were committed before play, executed by a closed deterministic harness in both seat orders, and replayed against the exact embedded engine snapshot.

The candidate imports only:

- the accepted proof summary;
- the two exact replay-PASS JSONL transcripts; and
- a narrow source classifier that treats the exact `source=model_plan` token as model influence in both the public receipt and share-bundle pipelines.

No raw prompt, private credential, auth file, environment value, provider response, strategy prose, or local path is added to the public derivative.

## Frozen evidence

| Seat order | Match | Chain head | Transcript SHA-256 | Result |
| --- | --- | --- | --- | --- |
| plan `aa668...` then plan `882960...` | `eaefda878377351e` | `59afb275a68b835d401483a954b1cdab1994d4d098c256018a25cb2408d0f6d5` | `56bb1e143ecb0f3b0e34fd39f373917b3b3dcbe2dcc9ed9e7ddd251d1cd233a3` | plan `882960...`, 1721-1676 |
| plan `882960...` then plan `aa668...` | `a424ad0640fecb70` | `2a45e41db806bb9e4f4c50c105474ad2ada4c0675ef51776cca325f647058a31` | `5d5069240ce069c9c0cf18e7e8bce50756dfecae29b0eebba0248e560786154d` | plan `aa668...`, 1702-1695 |

Each transcript contains six accepted `source=model_plan` moves per entrant, zero fallback/scripted/other moves, a complete ready record binding the plan/artifact/Ox receipt hashes, and false model/execution attestations.

## Truth boundary

`source=model_plan` means a fixed plan that an Ox Alpha Max receipt claims came from the named route influenced the accepted move. It does not mean live per-move inference. Replay proves the committed moves, deterministic states, scoring, and result. It does not independently prove provider identity, model identity, account, billing route, runtime, person, or causal execution provenance.

The public status remains:

```text
model_influenced_unattested
```

Every public `modelAttested`, `entrantIdentityAttested`, and `executionClaimsAttested` value remains `false`. Both receipts are non-title exhibitions.

The generic `source=model` token remains separate. Prefix lookalikes such as `source=model_planish` remain `other` because classification requires an exact token before `;` or `:`.

## Snapshot blocker and review gate

The publication manifest records both receipts as `held`. Their embedded verifier snapshot is `da275db125281da2a09decdddf9ddabacc741332e073e44f7371bba565d8be3a`, while the current fantasy rules registry is based on `3afca5e09507ec748c3d91dfbc1157e3f872fc495541063c3575a4c81c03b328`. A temporary approval build fails closed because a single game version cannot currently claim two active verifier snapshots. The normal public build therefore continues to contain only the eight previously approved receipts.

Do not change either decision from `held` until one versioned solution is implemented and independently accepted: regenerate genuine evidence under the active canonical snapshot, or evolve the public schema so historical receipt snapshots and the active future-fixture snapshot are explicit and non-conflicting. Never rewrite the hash-chained evidence bytes.

After that architecture gate, all of these must pass on the exact committed candidate:

1. Ox Alpha Max returns an explicit approval with no P0/P1/P2 correctness, truth, custody, replay, privacy, or publication finding.
2. `python bin/check_fantasy_plan_harness.py` passes the original artifact and proof-runner contract.
3. `python bin/check_share_bundle.py` and `python bin/check_agentwars_product.py` pass, including cross-pipeline source-count parity.
4. Both imported files pass the standalone verifier and reproduce their recorded transcript SHA-256 and chain heads.
5. A temporary manifest with only these two decisions flipped builds deterministically twice, produces two `model_influenced_unattested` receipts with twelve model moves each, preserves each historical verifier snapshot, pins one explicit active snapshot for future fixtures, and awards no title.
6. Secret/path scans find no credential, auth material, environment value, raw provider output, or absolute local path.

The current acceptance suite deliberately performs the temporary flip twice and requires the exact snapshot-conflict refusal. After the schema or regenerated-corpus gate is accepted, replace that refusal assertion with the deterministic ten-receipt build assertion, flip only the two manifest decisions, regenerate the canonical artifact, rerun the complete checker ladder, and obtain a second immutable publication review before integration or deployment.

## Rollback

Before deployment, rollback is deletion of the candidate-only manifest rows and imported proof copies plus reversion of the exact source-token mapping. After a reviewed artifact is generated, rollback is a new explicit manifest decision that removes these receipt ids from the approved set, followed by deterministic artifact regeneration. Never edit or replace the historical transcripts.
