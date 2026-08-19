# Entrant isolation

BuilderWars currently implements one entrant executor:

```text
process
```

It is **process-isolated and capability-unconfined**. It is suitable only for entrant code the operator already trusts to run on the host.

## What process mode enforces

Every current transcript records the exact versioned profile:

```json
{
  "schema": "nymrel.builderwars.isolation.v1",
  "mode": "process",
  "executor": "python-subprocess",
  "capability_isolation": false,
  "trusted_entrants_only": true
}
```

The full profile also records these controls as enforced:

- separate operating-system process;
- per-match scratch working directory;
- environment-variable allowlist;
- inherited file descriptors closed;
- transcript path withheld;
- per-move wall-clock timeout;
- stdout line and total-output limits;
- bounded stderr capture;
- process termination on timeout and match completion.

These controls make the referee/entrant protocol narrow and replayable. They do not make the entrant safe to run when its code is hostile.

## What process mode does not enforce

The same profile records these controls as explicitly absent:

- network-egress blocking;
- filesystem confinement outside the scratch working directory;
- CPU limit;
- memory limit;
- process-count limit;
- host-credential boundary.

Setting a scratch current directory is not a chroot. Passing only selected environment variables does not stop a process from reading host files it can access. A subprocess timeout does not supply a cgroup or Windows job object. Those distinctions are part of the result, not footnotes.

## Strict admission

A caller may require a capability boundary:

```bash
python bin/run_match.py \
  --seed 7 \
  --entrant entrants/solver_harness.py \
  --entrant entrants/naive_harness.py \
  --require-capability-isolation
```

No capability-isolated executor exists yet, so that command fails before:

- loading a game;
- creating an output directory;
- opening a transcript or diagnostics file;
- creating scratch directories;
- constructing or starting entrant processes.

The CLI writes one bounded JSON refusal to stderr and exits `2`:

```json
{
  "available": {
    "mode": "process",
    "capability_isolation": false
  },
  "available_mode": "process",
  "error": "isolation_requirement_unsatisfied",
  "match_started": false,
  "reason": "capability isolation was required, but process mode does not enforce it",
  "requested_mode": "process",
  "required": {
    "mode": "process",
    "capability_isolation": true
  }
}
```

The receipt describes the caller’s actual requirement. An unsupported mode requested without a capability requirement reports that mode and `capability_isolation: false`; it does not manufacture a stronger requirement after the fact.

Strict admission does not create isolation. It prevents an operator’s stronger requirement from silently degrading into process mode.

The same preflight exists on `run_series.py` and runs once before any match in the series begins.

## Transcript and replay behavior

New transcripts store the exact profile under `header.body.isolation`. Replay:

- accepts only the exact implemented field and control sets for the current schema;
- rejects an invented capability claim;
- rejects a profile that deletes an unenforced control;
- rejects unknown controls or fields;
- rejects a header carrying both current and legacy declarations;
- includes process-isolation limitations in `does_not_prove`.

An attacker who edits the profile and repairs the transcript hash chain still receives `FAIL`, because replay validates the isolation declaration independently.

Published legacy transcripts used `sandbox_policy`. Replay continues to accept that shape only when its original enforced controls and its network/filesystem/CPU/memory caveats are all present. The report labels it `nymrel.builderwars.isolation.legacy-v1`; it never upgrades the old result to a current or capability-isolated claim.

Replay validates a declaration and the referee source that produced it. It does not independently observe the host kernel, firewall, mounts, credentials, cgroups, or job objects.

## Standalone verifier parity

`verify.py` embeds the referee package byte-for-byte. Any change to `arena/` changes the engine digest and requires regeneration.

The draft CI sequence is intentionally fail-closed:

1. regenerate `verify.py` from the checked-out branch;
2. run its conformance checks against the package verifier;
3. upload the generated file as a short-lived review artifact;
4. fail unless the committed `verify.py` is byte-identical.

Until that artifact is reviewed and committed, the branch is not merge-ready and must not represent the old verifier as current.

## Gate for a future capability-isolated executor

A new executor is not accepted merely because its code contains Docker, Firecracker, gVisor, WSL, a job object, or a firewall command. It must produce match-bound evidence for the exact execution instance and configuration.

At minimum, the executor must demonstrate:

- deny-all or exact-authorized network policy;
- read-only root/filesystem boundary with bounded writable scratch;
- no inherited host credentials or sensitive environment;
- process-count, CPU, memory, output, and wall-clock ceilings;
- cleanup and teardown outcome;
- executor name, version, image or runtime digest, and configuration digest;
- explicit unsupported behavior on hosts where each control cannot be applied.

BoundaryLab may test an executor and emit a conformance receipt. A separate BoundaryLab run is not evidence that a particular match used that executor. Future integration must bind the match transcript to the exact BoundaryLab receipt, runtime identity, configuration digest, and execution instance without importing raw credentials or private host data.

## Current operating rule

- Maintainer-authored reference entrants: process mode may be used with the limitations visible.
- External or otherwise untrusted entrants: do not run them on the host.
- Operator requires capability isolation: use strict admission and accept the refusal.
- Published result: do not call it sandboxed without immediately stating `process-isolated and capability-unconfined`.

No external-entrant program, hosted executor, container image, provider integration, or isolation certification is authorized by this document.
