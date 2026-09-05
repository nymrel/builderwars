# BuilderWars beta capacity readiness

Status: **operator-fill planning contract and local concurrency correctness
only**. No beta population, request mix, performance SLO, cost budget,
production throughput, provider spend, infrastructure activation, or launch
authority is selected or claimed.

The executable contract is `publishing/capacity_readiness.py`. The bounded CLI
is `bin/builderwars_capacity.py`, and the adversarial/local concurrency checker
is `bin/check_builderwars_capacity.py`.

## Why this contract exists

The repository already bounds individual work:

- browser bodies are capped at 16,384 bytes;
- runner bodies and responses are capped at 65,536 bytes;
- browser mutations have exact per-owner, per-operation fixed-window policies;
- pairing has a 600-second TTL and eight claim attempts;
- signed runner requests have bounded clock skew and nonce retention;
- leases, renewals, match attempts, idempotency lifetime, and sealed retry
  responses are bounded.

Those controls do not answer how many authenticated users, runners,
spectators, jobs, or requests define the first beta. The contract therefore
requires those values as explicit operator inputs instead of deriving a target
from a laptop or inventing one in documentation.

## Current local reference policies

| Browser operation | Per-owner limit | Window |
| --- | ---: | ---: |
| Create pairing | 6 | 60 seconds |
| Confirm pairing | 12 | 60 seconds |
| Create fixture job | 12 | 60 seconds |
| Revoke runner | 6 | 60 seconds |
| Delete runner | 6 | 60 seconds |
| Delete owner | 2 | 300 seconds |

These are local reference policies. The in-memory limiter is thread-safe and
fails closed through the browser gateway, but it is not durable, shared across
instances, or an edge perimeter.

## Exact operator-fill packet

Print the template:

```powershell
python -B bin\builderwars_capacity.py --template
```

The operator fills one JSON object containing exactly:

- scenario ID and candidate label;
- an observation window divisible by 300 seconds;
- authenticated active users, connected customer-local runners, and public
  spectators;
- the per-active-user count for all six browser mutation operations;
- runner polls and results per runner;
- public replay reads per spectator;
- peak queued jobs and concurrent attempts;
- `publicCreatorExecutionEnabled: false`;
- `paidComputeAuthorized: false`.

No default numeric target is emitted. After the values are reviewed, save only
the filled `operatorInputs` object and evaluate it locally:

```powershell
python -B bin\builderwars_capacity.py --evaluate .\operator-capacity-input.json
```

Exit `0` means the candidate fits the current **local per-owner browser
policies** and may advance to a separately authorized production capacity test.
Exit `3` means the candidate exceeds at least one local browser policy. Exit
`2` means the input was malformed or unsafe. None of those exits authorizes a
deployment or proves production capacity.

The candidate derives exact integer request totals and a rational
`numerator/denominatorSeconds` request rate. It uses no floating-point estimate.
It preserves the requested queue and concurrency peaks, names every missing
production receipt, and leaves all authority flags false.

## Local concurrency correctness probe

Run:

```powershell
python -B bin\check_builderwars_capacity.py
```

The fixed local probe deliberately has no latency or throughput threshold. It:

1. sends seven simultaneous fixed-window decisions for each of 32 synthetic
   owners through 16 workers;
2. proves exactly six create-pairing decisions per owner are allowed and one is
   refused (192 allowed, 32 refused total);
3. performs 1,024 concurrent missing public-replay lookups against a fresh
   ephemeral SQLite reference;
4. proves all lookups return no projection and every reference table remains
   unchanged and empty;
5. records `networkUsed`, `providerCalled`, `throughputClaimed`,
   `performanceThresholdApplied`, and `productionTargetObserved` as false.

This proves local atomic quota enforcement, owner independence, bounded
spectator-miss behavior, and non-mutation under the fixed fixture. It does not
measure an HTTP edge, multi-instance limiter, production database, cache,
queue, network, latency percentile, saturation point, cost, or user experience.

## Protected production evidence still required

After the operator selects a candidate, the protected capacity ceremony still
requires all of the following against the exact release source:

1. Approved beta population and request mix.
2. Durable edge, service, tenant, and global limit configuration.
3. Exact production store, queue, cache, and connection-pool topology.
4. A source-bound load generator and sanitized test tenants.
5. Approved latency, saturation, error, and queue thresholds.
6. An approved cost budget; this contract never grants paid-provider authority.
7. Production telemetry, alert delivery, and staffed response.
8. Backpressure, degraded-mode, recovery, and rollback rehearsal.
9. Test-state cleanup and an accountable capacity-acceptance receipt.

Public arbitrary creator execution remains disabled. BuilderWars.com apex and
`www`, protected accounts, secrets, customer OAuth/subscription consent,
billing, and production data remain outside this local contract.
