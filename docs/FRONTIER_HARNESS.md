# Versioned frontier harness and experiment custody

Implementation contract, September 5, 2026. Follows PR39's measured tactical and
seat regressions. This slice implements phase 2; broad strength, web UX, external
model competition and final campaign acceptance remain separate gates.

## Invariants

- Content-addressed immutable versions bind requested and reported model identity,
  provider route, reasoning, prompt, frozen memory, tools, harness implementation,
  local numeric parameters, referee/rules and resource limits. No keys or endpoint
  credentials are persisted in a version. Reported identity is not independently
  attested execution. Ranked execution cannot silently substitute a model.
- A session freezes one version. Changes create a descendant; in-flight work keeps
  its original version and bounded budget. A missing or changed identity fails
  admission rather than inheriting a display name's authority.
- Local tactical calibration learns numeric board-feature preferences from
  referee-verified errors and safe alternatives. It is supervised practice, not
  provider base-model training or the older outcome-trained policy method.
- Train, public development and final admission target positions use conservative
  board/symmetry/history grouping. Development targets cannot occur in training
  prefixes; final targets cannot occur in any public training/development prefix.
  The optimizer receives training cases only. Final case payloads stay in the
  evaluator vault and are opened only after a candidate is frozen and the final
  suite is consumed. Full-game trajectories can revisit familiar positions;
  label their outcomes separately from held-out tactical qualification.
  Private final histories may share opening/prefix positions, including another
  private suite's target; those histories never reach the learner or public
  outputs. This does not assert disjoint full trajectories. Requiring every
  prefix to be disjoint would reject every game because all share an empty board.
- A finite campaign fixes attempt count, resource class and repeated-test policy
  before optimization. Exclusive attempt slots count even if the process crashes.
  Create-only artifacts preserve plan, error/practice evidence, candidate, result
  and failures. A spent admission suite never becomes fresh through a retry or a
  different campaign in the same store. Public development never promotes.
- All local isolation assumes the trusted bundled runner. Same-user file access,
  copied/reset stores and arbitrary external commands are not sandboxed. A local
  receipt is not a globally authoritative leaderboard or independent attestation.

## Implementation and acceptance

Browser-safe version/case/practice modules, a Node-only bounded artifact store and
an explicit CLI form one vertical slice. Preserve the current referee, original
policy schema, public browser bundle and provider routes. No arbitrary uploaded
code, auto-inference, background training or new paid infrastructure.

Tests must reject mutation, unsupported/unknown configuration fields, identity
drift, rule/referee mismatch, wrong partition, symmetry and history contamination,
spent-suite reuse, oversubscribed attempts, interrupted writes, budget exhaustion,
and nonfinite numeric values. Demonstrate a real play/error/practice/candidate
record plus public comparison without using final data to tune the candidate.
One independent review is required for the consequential implementation. Keep its
original verdict and the owner's evidence-backed resolution, not invented approval.

Next phase requires preregistered repeatable both-seat gains against frozen
nonrandom opposition in two game families, uncertainty and regression vetoes.
This contract does not replace that proof with lower training error.

## Local commands and artifacts

From live-arena, with Node22 and installed lockfile dependencies:

```powershell
npm.cmd run frontier -- init --id tactical-ttt --game tictactoe
npm.cmd run frontier -- run --id tactical-ttt
npm.cmd run frontier -- status --id tactical-ttt
npm.cmd run frontier -- admit --id tactical-ttt --slot 1
```

Initialization commits32 training cases,16 development cases and two distinct
16-case final suites by default. It uses a private random sampler seed and reserves
final target groups before publishing the campaign manifest. A store-wide group
registry prevents later campaigns from exposing a reserved target through public
case prefixes, or recycling a public/final target into a new final suite. These are
campaign/store-relative exclusions, not claims that the Internet or a provider's
pretraining has never contained the position. The small game state space can be
exhausted; failure to find sufficient isolated cases is an explicit failure, never
permission to relax grouping or relabel seeds as unseen states.

`run` claims a slot before optimization. Default eight passes use rate0.2 and
margin0.1; changes require a fresh slot and are saved before practice. The learner
receives only the committed training bundle. Development follows candidate sealing.
Two-million-node/300-second limits apply to each bounded sampler/practice/evaluation
operation; update records are capped at10000 and files at2MB. Each attempt reserves
0.05 divided by the fixed attempt count for future whole-game tests; the current
tactical qualifier does not claim a population confidence bound.

`admit` is deliberately explicit and one-shot. It consumes an evaluation marker
before loading any final cases, writes a private replayable audit, and returns only
aggregate seat metrics and its audit digest. Even a perfect tactical result returns
promotion=not-authorized. This module does not implement phase3's whole-game gate.
Individual final outcomes stay in the vault; do not export them or use them for
practice while this campaign still permits another attempt.

The store lives under output/frontier by default. Public files are the campaign
manifest, training/development cases, attempt plans, practice records, frozen
candidate references, development results and rollback records. The immutable
rollback record keeps the original incumbent selected. Content-addressed versions
are in versions/. Final suites, private sampler records and final per-case audits
are in vault/. Spent markers and group reservations are never cleared by retries.
Raw JSON is inspectable by the machine owner; no sandbox or independent authority
is implied. Failed partial files are retained; status never treats a truncated
completion file as success. An interrupted slot remains charged.

Execution fingerprints include local runtime/learner/CLI sources, lockfile, actual
referee bytes and Node version. A changed source/runtime requires a new campaign;
do not patch old manifests to force replay under a different executor.
Historical status and retirement remain available after a source upgrade; status
explicitly reports executionCompatible=false. Execution still fails closed.

`move --version DIGEST` reads one bounded move request from stdin and executes that
exact stored local numeric version. Optional request.version must match. It ignores
website model labels as execution authority and reports its actual configured
identity/version. The existing Python bridge discards extra version metadata and
returns a declared model label: it is not yet an attested version transport. The
new version-aware transport API is tested with stubs; real provider adapters and
browser wiring remain phase4/5 work. No model call occurs from these CLI commands.

`close --id ID` permanently retires the campaign for new training/admission.
It does not kill an already-running process; those operations retain their fixed
budgets. Closing never frees final data for another suite. The next UX phase adds
explicit train cancellation and version selection through a bounded worker/bridge.
