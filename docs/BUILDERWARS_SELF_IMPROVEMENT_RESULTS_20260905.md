# First self-improvement implementation: evidence and limits

September5,2026. Local development increment following the completed beta.
No production contender replacement, automatic inference or store action.

## Actual first-cycle observations

All runs used the existing referee digest
`d5135878ce69345f5e8ee214c03d53cd1593052b9bcb97d1a96363f9b6dfa823`.
Training seed20260905, learning rate0.08, exploration0.25, one-ply value policy.
Initial weights were zero, with the same terminal-win handling as the candidate.
Evaluation used reserved random streams and paired seats against seeded random
opponents. Scores include draws as0.5; they are not win percentages or rankings.

| Game | Completed / attempted practice | Evaluation seed-pairs | Initial score | Candidate score | Admission |
| --- | ---: | ---: | ---: | ---: | --- |
| Tic-tac-toe | 600 / 600 | 128 | 0.7051 | 0.7734 | Retained incumbent; lower gain bound -0.1480 |
| Connect Four | 600 / 600 | 128 | 0.8320 | 0.9531 | Retained incumbent; lower gain bound -0.0953 |
| Custom3x4connect3 | 600 / 600 | 128 | 0.7266 | 0.8672 | Retained incumbent; lower gain bound -0.0757 |
| Chess | 0 / 6 | 16 | Invalid: capped | Invalid: capped | Retained; all64 evaluation games hit24-ply cap |
| Checkers | 10 / 12 | 16 | Invalid: capped | Invalid: capped | Retained;12 evaluation games hit100-ply cap |

Each evaluation seed-pair comprises four games: both policies in both seats.
These are exploratory local results, not independent unseen-state evidence.
No candidate met the fixed per-attempt lower-bound threshold of0.05. Do not
reinterpret sample improvements as established learning uplift or selectively
rerun until a promotion occurs. The numeric weights really changed on completed
training; zero completed chess episodes correctly left its weights unchanged.

Original ignored run directories under `live-arena/output/self-improvement/`:

- `tictactoe-1788609437619-a6fc3f2d-b894-4627-8f55-f9829fa71066`
- `connect4-1788609551775-9c13a7d2-1866-46e6-af70-5109113ac923`
- `custom-1788609552513-59a67ade-6985-45c9-9cb0-717bf72509f0`
- `chess-1788609600061-daed8560-3164-41b5-88e6-62b2e35abf94`
- `checkers-1788609632801-e8decb0a-b6d8-4a15-9af4-f180f5f1e3c1`

These first runs preceded final artifact/report hardening. Their originals are
retained. In particular, the earlier capped receipts contain numeric partial
score fields that are invalid for comparison; final code returns null scores and
bounds when any evaluation game is capped. Those old values are not used above.
New runs also retain source-file digests. Algorithm/features/referee unchanged
by the later guard/report fixes; no re-run was selected to improve these results.

## Real local contender execution

The actual trained tic-tac-toe development candidate
`22b585d7e7984d255d1369731e071159f4ef0d3fade55f68ce93762cf6994b74`
completed a nine-call stdin harness game. Every request replayed the existing
history and checked position/turn/legal moves; output digest matched the loaded
artifact. Moves:4,6,2,1,7,8,0,5,3. Result: Board full, draw. No provider calls.
It was intentionally labeled a development candidate, not a promoted agent.
This proves local process I/O and legal completion, not browser HTTP delivery or
an externally attested agent identity.

## Validation and independent review

Final local test suite:158/158; TypeScript and production build pass. Browser
entry assets and referee remain unchanged because training is a separate local
tool. Fourteen new tests cover training updates, deterministic reproduction,
all-game legality/seat-feature ownership, tampering, caps/cancellation,
evaluation non-mutation, source normalization, stdin validation, failure records,
fresh run directories, and both champion retention/promotion/rollback paths.
The successful-promotion test uses deliberately inverted fixed policy weights
as a **synthetic plumbing fixture**, not evidence of actual training gains.

Tool-less cross-family review resolved to `claude-fable-5-1`:

- Initial session `b9121f13-0a4d-4b03-931c-e93fee0873ea`: changes requested.
  Fixed encoding checks, positive/failure-path coverage, bridge-input tests and
  canonical-parent handling. Original review result retained in task output.
- Follow-up session `72daf016-67c6-4395-ae5b-b88553af96d4`: approved all four
  resolutions, no remaining blocker. Scope was local development tooling.
- Subsequent owner hardening: null invalid capped-comparison fields, source-file
  digests, tests, CLI alias and documentation. No optimizer/search changes.

Provider CLI reported list-cost estimates1.280278 and0.749102USD for the two
reviews, including its Haiku auxiliary usage; this is not measured cash billing.
Game-training provider calls were zero. Local hardware cost remains unknown.

## Remaining admission work

Per-attempt alpha does not control cumulative error over repeated/forked runs.
Before automatic ranked promotion, require an authoritative attempt ledger and
sequential-testing rule, stronger diverse opponent pools, per-seat/regression
checks, immutable execution/version custody and independent final admission.
Long-game search/curricula, frontier-model harness optimization, browser training
UX and additional task adapters remain subsequent implementation stages.
