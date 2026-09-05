# Nim builder-fielded exhibition slice

Scope: browser Nim, explicit public builder/harness claims, content-bound
exhibition exports/broadcasts and dedicated hosted CI. The controlled study remains
separate in [PR #5](https://github.com/nymrel/builderwars/pull/5). No deployment,
account system, ratings, model execution or scientific publication is included.

## Contract

- Python `arena/games/nim.py` is unchanged. Browser normal-play legality,
  transitions and terminal results are checked against it in CI.
- Browser initial heaps are recorded, not silently generated from an unrecorded
  seed. Default `[3,5,7]`; 3/4-heap imported positions follow the referee's bounds
  and first-player-win starting-position constraint.
- Builder ID, harness ID and source revision are optional, bounded public claims.
  Both configured builders remain explicitly self-declared. A hash does not
  prove authorship, ownership, the running source or model identity.
- v2 snapshots bind rules, public seat configuration, move sequence and status.
  Legacy v1 stays readable but unbound. Imports reject inconsistent v2 bindings.
- No automatic bot replacement after a model/harness error; no study result is
  inferred from browser matches. The 2×2 study still requires Llama 3.2 3B vs
  Qwen 2.5 14B and Qwen 2.5 3B vs 14B, both seats and zero fallback.

## Validation

Local TypeScript/build and engine/security tests include an oracle comparison of
758 states, 4,572 legal transitions and 18 registered smoke/publication seed
setups against Python. Tests also cover malformed moves, replay/claim tampering,
credential stripping, seat swaps, legacy import, and no replacement on error.
Four Python bridge tests use a synthetic backend; no provider calls are made.

The dedicated workflow triggers on `live-arena/**` and the Python referee,
builds the app, runs unit/parity/replay tests and the bridge tests, then executes
existing browser acceptance plus the new human-Nim, declared-builder pair,
seat-swap, export/import, tamper and responsive journeys. All remote model/harness
responses in those browser tests are synthetic; no credentials are configured.

Local Chromium installation timed out at the upstream download, so browser
journeys are committed for hosted validation but are not claimed locally passed.
Do not treat a newly added workflow as passing evidence before its run completes.

## Remaining holds

Independent review and hosted acceptance remain required. This slice is not
authenticated builder-versus-builder competition. That needs a separately reviewed
identity/ownership and source-execution attestation design. Hosted persistence,
rankings and the actual controlled model study are outside this change.
