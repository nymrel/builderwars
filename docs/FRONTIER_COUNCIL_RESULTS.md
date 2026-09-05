# Four-family campaign: decisions and first measurement

September 5, 2026. Owning execution lane: Astra / Codex. Strategy remains
HYPOTHESIS - NOT ADOPTED. Implementation is operator-authorized independently of
North Star adoption. This is a BuilderWars campaign, not a studio priority override.

## Actual contributions and identity limits

| Family | Execution receipt | Contribution and owner ruling |
| --- | --- | --- |
| Astra | Current Codex lane; claim codex-builderwars-four-frontier-20260905 | Implemented diagnostics, tests, fixed opponents, evidence and integration. No independent-review claim for self-assessment. |
| Fable | Claude session 64273ee8-5c40-4d68-8444-3279b0c15d9f; modelUsage resolved claude-fable-5-1 | Original charter 62/100, changes requested. Accepted builder-first comparison-report wedge, removal of unsupported tester target, and retain-inclusive leading indicator. |
| Grok / Cursor | peer-cursor-20260905T185154Z-a1c2d61489; completed 102898 ms | Requested catalog model cursor-grok-4.6-high. Accepted weak-opponent disproof, seat-separated before/after evidence and simpler replay experiment. |
| Gemini / Antigravity | peer-antigravity-20260905T185107Z-a30b0adb30; completed 72505 ms | Requested catalog model gemini-3.1-pro-high. Accepted separate final-position/opponent custody, spent-suite retirement and contamination controls beyond hidden seeds. |

Cursor and Antigravity receipts record catalog-verified model arguments and real
completed consult outputs, but text-mode responses do not attest provider-resolved
model identity. Do not relabel them as independently attested model executions.
The selected Gemini Pro route is an analytical choice, not a claim that it is the
universally strongest Gemini model. No global routing or account changes occurred.
Internal consult artifacts reside under portfolio-control/reports/consults/studio-peers/
in the cursor and antigravity directories, with the exact receipt IDs above.

Failures retained: Cursor xhigh was rejected by wrapper policy before a call;
the full Cursor prompt exceeded the Windows command-length limit before inference
(peer-cursor-20260905T185131Z-db72e91b38). A shorter high-effort consult succeeded.
Fable session 16fb0f26-e0bf-48f3-98ca-6d2d5365e2c0 returned unusable tool-like markup;
it is failed output, not a review. A text-only correction produced the scored return.
No Grok Build inference or credential workaround was used.

Owner disagreements: the short-game PR38 exploration completed; reject Fable's
description of those samples as capped, while retaining its warning that they do
not prove uplift. Six capped chess episodes with unchanged weights do not establish
that chess cannot learn. Hidden seeds or one hidden suite do not prove generalization.
No majority vote overrides source evidence or expands action authority.

## Independent implementation review

Fable reviewed the exact three new TypeScript files, text-only, session
08f0bf1a-4482-42e8-be6d-de85133c37dc, resolved claude-fable-5-1. It returned
CHANGES_REQUESTED with three bounded issues. Owner resolution:

1. Added a hand-labeled board-filling draw fixture: drawing is safe and not an
   avoidable loss. The proposed deletion mutation now fails the safe-list assertion.
2. Limited measurement to 398 plies so two-ply lookahead stays below the referee's
   400-ply exhibition boundary. Tests reject 399 and verify the accepted upper bound.
3. Recorded node/time limits in plan.json and tested invalid/over-limit inputs.
   The existing WorkBudget constructor already validated integer finite limits;
   no duplicate validator or weaker maximum was introduced.

Also bound outcome.ts in the source receipt and documented win-over-defense
precedence. Confirmed src/games.ts advanceMove alternates the player at lines
246-247; checkers capture paths are whole moves, not same-seat continuations.
Failures preserve failure artifacts rather than partially successful reports.
Fable did not execute tests. Owner reran the focused seven tests, all 165 tests,
TypeScript/build, and four exact report reproductions after the corrections.
The original review verdict is retained; owner resolved the findings, not a
fabricated follow-up reviewer approval. No repeat council to seek a nicer score.

Claude reported list-price usage totals of $0.256024 for the failed-format call,
$0.2763645 for charter review and $0.957953 for implementation review, each including
small Haiku helper usage. These are reported list-cost estimates, not verified
incremental subscription charges. Cursor/Gemini cost and token usage are unknown.
The game-strength runs used zero provider calls.

## First reproducible strength baseline

Four frozen policies, 16 public development seeds, both seats, two opponents:
256 games completed, zero capped games and zero illegal responses. This is local
development evidence, not a new admission attempt, production promotion, provider
competition or generalization claim. Candidates are the saved PR38 artifacts;
no retraining or candidate selection occurred in this measurement.

Score is wins plus half draws divided by 16 games for each seat/opponent. The
tactical opponent chooses an immediate win, otherwise a move that prevents an
immediate reply loss when possible, with a canonical tie-break. It is not an engine.

| Game / opponent | Baseline seat 1 | Candidate seat 1 | Baseline seat 2 | Candidate seat 2 |
| --- | ---: | ---: | ---: | ---: |
| Tic-tac-toe / random | .90625 | .875 | .59375 | .6875 |
| Tic-tac-toe / tactical | .25 | 0 | .125 | 0 |
| Connect Four / random | .8125 | 1 | .75 | .875 |
| Connect Four / tactical | .125 | 1 | .25 | 0 |

Against tactical opposition, tic-tac-toe candidate made 32 avoidable losses in
32 defense opportunities. Connect Four candidate made 0/16 in seat 1 but 16/16 in
seat 2. All observed win opportunities were taken; absence of an opportunity is
null, not a perfect rate. Repeated deterministic trajectories are correlated;
16 repeated seeds do not create 16 independent strength observations.

Ruling: neither candidate qualifies as broad improvement. Retain incumbents.
The new diagnostic exposes regressions that random-opponent summaries can hide.
Its reports cannot promote anything and do not alter the original admission gate.

Complete frozen policies, plans, source hashes, report digests, opportunities and
replay histories: [machine evidence](FRONTIER_STRENGTH_EVIDENCE_20260905.json).
All four embedded reports were recomputed from their policies and matched exactly.
Node work: 15481 and 39989 for baselines, 15098 and 38559 for candidates, under
500000 nodes / 120 seconds per run. Before-review diagnostic artifacts remain
local; evidence above is the corrected-source rerun, not cherry-picked outcomes.

## Next exact move

Implement immutable harness/version and attempt-ledger contracts with isolated
training, public development and final admission custody. Use the exposed seat-2
failures as public practice cases, never hidden admission cases. Predeclare a
finite comparison before new training. Do not scale chess episode counts or add
spectator features until the relevant evidence gate is ready.

The browser bundle index-DAHsmVZF.js and referee
d5135878ce69345f5e8ee214c03d53cd1593052b9bcb97d1a96363f9b6dfa823
are not changed by this local tool.
Exact referee digest is carried in the machine evidence; integration/CI and any
public deployment must be reported separately from these local results.
