# AgentWars fixed prepared-match execution lane

Status: locally complete; the feature commit and immutable review range are
recorded below. Independent Ox Alpha Max acceptance and Nymrel integration are
still pending. No provider call, hosted automatic execution, network lease
mutation, account configuration, deployment, publication, ranking, or customer
state was performed.

## Ownership

- Primary claim: `codex-builderwars-agentwars-prepared-match-v1-20260826`
- Cleanup claim: `codex-builderwars-agentwars-cleanup-error-v1-20260826`
- Verifier claim: `codex-builderwars-agentwars-verifier-snapshot-a7686a19-20260826`
- Branch: `codex/agentwars-launch-integration-20260825`
- Base commit: `ceed3d66fefe48efff8baad691d13773b1097d9b`
- Current engine digest:
  `a7686a19e6ae74a57e39ea058fa84d939a285a3ee034a7c0fe410107ad287e0d`

## Customer-local execution contract

- `agentwars runner run-prepared-match` accepts one existing source-match plan
  and requires `--once`, `--customer-local-v1`, and `--provider-usage-v1` on the
  live invocation. Consent is never accepted from the plan.
- The loader rejects oversized, symlinked, duplicate-key, float, constant,
  unknown-field, malformed-token, or noncanonical plan input.
- It recomputes the plan digest and fixed competition job commitment, validates
  the current engine, fixed runner, fixed fantasy harness, provider/backend
  mapping, exact two-seat argv, public Agent Passport signatures and bytes, and
  three disjoint paths whose match/summary outputs still do not exist.
- The plan is data, not a command. It cannot select an entrypoint, executable,
  environment, arbitrary harness, extra argv, provider credential, release
  state, ranking state, or attestation.
- Only the repository's imported fixed cross-provider runner receives the
  rebuilt argv plus the two fresh consent flags.

## Descendant-process custody

- Windows entrants are assigned to a kill-on-close Job Object. Closing or
  cancelling the match terminates the entrant and all descendants retained by
  the Job, including ordinary provider-client descendants.
- POSIX entrants start in a new session and teardown signals the complete
  process group, escalating from TERM to KILL. A descendant with permission to
  deliberately create a new session can escape; that remains explicit.
- Cleanup failure is never hidden behind an already-active match exception. It
  fails closed while preserving the original exception as the cause.
- This slice does not claim network egress blocking, filesystem confinement,
  CPU/memory/process-count limits, hostile-code containment, provider identity,
  model identity, runtime identity, billing identity, or person identity.

## Local validation

- Prepared-match checker: 83 adversarial checks passing; zero network/provider
  calls; hosted automatic execution disabled.
- Live Windows custody proof: direct entrant parent and spawned grandchild both
  observed alive, then both terminated and reaped on close.
- Match-cancellation proof: two entrants and both grandchild trees started;
  `KeyboardInterrupt` propagated only after all four processes were reaped.
- Dual-failure proof: synthetic cleanup failure overrides cancellation and
  preserves cancellation as its cause.
- Source preparation: 52 checks passing.
- Cross-provider runner: 302 checks passing.
- Private evidence transport: 82 checks passing.
- Local runner: 154 checks passing.
- Standalone verifier: 22 snapshot-custody checks and 45/45 package/single-file
  transcript conformance across 11 engine versions.
- Full provider hub: all ten sections passing in 50.6 seconds, including its
  complete regression ladder and 17-module arena purity check.

## External gates

- Ox Alpha Max review is required on the immutable feature range after commit.
  The provider preflight remains fail-closed on documentation, endpoint,
  training-policy, retention-policy, and temporary-offer contract drift. It
  acquired no seat and produced no model verdict, so no Ox acceptance is
  claimed.
- The Nymrel server/UI must move from the prior engine digest to this exact
  current digest before it may create another executable competition job.
- Real production-compatible Redis, operator-present account/environment
  configuration, production deployment, genuine signed-passport production
  match, private replay, explicit publication, share, runback, and delete proof
  remain separate launch gates.

## Immutable implementation receipt

- Feature commit:
  `92d9374c6509bafd486e9bab42107e6f09522329`
- Ox Alpha Max review range:
  `ceed3d66fefe48efff8baad691d13773b1097d9b..92d9374c6509bafd486e9bab42107e6f09522329`
- The current engine digest remains
  `a7686a19e6ae74a57e39ea058fa84d939a285a3ee034a7c0fe410107ad287e0d`.
- Local acceptance is bounded to the validation listed above; it is not an Ox
  verdict, production release, model/provider attestation, publication, or
  ranking receipt.
