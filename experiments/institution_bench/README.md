# InstitutionBench v0

InstitutionBench is a **fixture-only organizational evaluation contract** for BuilderWars.
It makes organizational topology measurable without defining a second Agent/Team identity
system or another execution runtime.

The unit under test is a task-scoped organization:

- exact task and fixture digests;
- organization topology;
- opaque worker references;
- role responsibilities and tool permissions;
- memory policy;
- recovery policy;
- fixed budget;
- fixed evidence and acceptance policy.

v0 supports four structures:

1. `single` — the incumbent baseline;
2. `lead_worker` — one delegating lead plus workers/specialists;
3. `independent_adjudicator` — two or more workers plus an independent adjudicator;
4. `specialist_team` — two or more specialists, optionally with one delegating lead.

A receipt records accepted outcome, operator interventions, operator-active time, resource units, elapsed time,
retries, interruption/recovery facts, duplicate side effects, policy violations and evidence
typed evidence references. Evidence classes must satisfy the declared evidence policy; accepted outcomes that require independent review fail closed without independent evidence. A policy violation, incomplete required recovery, or duplicate side effect fails closed.

Receipt validation is structural by default; it is **not authentication**. For integrity-sensitive use,
callers must retain the receipt digest in Nymrel Evidence (or another independent trusted record)
and pass that expected digest back into `verify_receipt`. InstitutionBench does not invent a second signer.

Two receipts are comparable only when task, fixture, acceptance test, budget, tool surface
and evidence policy match exactly. The comparison returns deltas and explicitly leaves
`ranking: null`; a task-scoped experiment is not a universal model/team/organization score.

## Boundaries

- This does **not** replace the canonical Builder/Agent/Harness/Team/Roster work in issue #16.
- `worker_ref` is an opaque binding, not identity attestation.
- No model/provider call, deployment, payment, marketplace, reputation, or production action exists here.
- No result grants credentials or operational authority.
- An interrupted-and-resumed fixture demonstrates only that exact contract path, not general autonomy.

## Intended first use

Freeze one rights-cleared BuilderWars task and run the same task/budget against a
`single` baseline and one multi-role topology. Preserve every failed run and human correction.
The next research step is to plug real authorized executions into the contract without changing
its evidence or authority boundaries.
