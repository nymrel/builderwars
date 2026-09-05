# Academy and honest paired comparisons

## Current release status — September 5, 2026

Academy and the free paired comparison/creator exercise are included in web source
`d0873da18dfeeda1062cdce5e503c82aa804d904`, deployed at https://builderwars.com/.
The [release receipt](BUILDERWARS_RELEASE_20260905_NATIVE_CHECKPOINTS.md) supersedes
the historical candidate/review/preflight status below. Exact-source CI includes
`academy_browser.py`; the connection preflight is implemented and covered by
`connections_browser.py`. Prior cross-family review accepted the integrated
learning/connection path. Synthetic preflight and free lessons are not actual
customer-provider execution or evidence of learning improvement.

Limited connect-game practice context is now implemented; see
[the learning contract](BUILDERWARS_GAME_LEARNING.md). The historical statement
below that this Academy slice did not persist memory describes that earlier slice,
not the current product. Model weights, built-in policies, chess and checkers do
not learn automatically, and promotion based on unseen tests remains future work.

## Historical implementation checkpoint

Candidate implementation on `codex/builderwars-portable-proof-20260904`, draft PR #29.
This document describes candidate behavior, not a production release or external-user result.

## Runnable path

1. Open Academy and choose **Run free comparison**. This replaces the current board and contenders with Connect Four, Tactician and Wildcard. Keys, endpoints and strategies are not carried into the new matchup. Previously saved matches remain in the optional local library.
2. Watch two games at an 80-ply cap, with each contender starting once. No model requests, API key or account are required. A running/pending match or spectator session must be paused/left first; repeated lesson clicks do not restart it.
3. Open Evals. Distinguish attempts recorded, rule-complete games, complete pairs, wins, draws, caps, failures and stopped attempts. A pause ends the series; manually resuming the board does not resume that evaluation.
4. Export evaluation JSON, or inspect/replay the last board in Arena. Connect Four retains the portable referee/proof export. Rules reproduce results; model identities and original execution are not attested.
5. Return to Academy and choose **Prepare free creator exercise**. Forge receives a 3-row, 4-column, gravity-enabled, connect-three recipe and free contenders. Review it; **Create & play** prepares the board, then **Start match** runs it. Export/import the rules through Forge. This declarative exercise does not execute arbitrary submitted code.

## Accounting contract

- Outcomes are recomputed through the authoritative referee from each record's moves. A status string is not a win, draw or completion claim.
- Seat A in odd games and seat B in even games are the same original entrant. Results aggregate by original entrant slot, not display name, so identical names do not merge competitors.
- A complete pair requires both games to reach a rules-defined terminal state. Capped, failed or stopped incomplete games are not draws, wins or completed pairs.
- A model error stops the series and retains the attempted game's accepted moves with `exit: failed`. No replacement move or automatic forfeit is manufactured.
- Export preserves `builderwars.evaluation.v1` and `games` with additive fields: requested count, limits, attempt exits, current summary and in-progress status. Empty or in-progress exports are not described as completed evaluations. No evaluation-import compatibility is promised.
- Token/cost/latency totals cover accepted moves in recorded attempts, not the current in-flight game or failed/rejected calls. Unknown and overflowing usage stays unknown. This is not a billing total.
- Series results live in this tab. Export them before reloading or starting another series; the optional match library is separate from an evaluation archive.

## Improvement is a future capability, not an automatic claim

The Academy explains the proposed loop: retain a baseline version; change one thing; compare on equal rules, opponents and budgets; swap seats; test on held-out games; account for failure, uncertainty and cost; promote only after a predeclared threshold is met.

This slice does not train model weights, persist learned memories, rewrite harness code, run a promotion service, assign Elo, prove statistical improvement, or certify world-level chess. Fixed API models do not train themselves just by playing more matches. Model-only, engine-assisted and explicitly trained chess systems need separate comparisons. A rule variant is a new game, not a performance improvement at the original game.

Version registries, opt-in postgame coaching, controlled candidate generation, immutable experiment budgets, held-out suites and rollbackable promotion should be designed as a later bounded feature. Do not expose private prompts or enable recurring model spend as an incidental part of a free lesson. Keep the separate PR #27 metadata/Nim work out of this candidate until its contracts are reconciled.

## Validation and remaining work

- 48 Node tests pass, including seven new tests for recipes, seat mapping, terminal outcomes, caps/failures/stops, real draws, the engine safety-stop contract and unknown/overflow usage.
- TypeScript and production build pass. Referee executable digest remains `d5135878ce69345f5e8ee214c03d53cd1593052b9bcb97d1a96363f9b6dfa823`.
- `python tests/academy_browser.py` passes: actual free pair, repeated-click guard, recipe export, caps, pause, synthetic illegal provider move, secret stripping and 320/390/768/1440px layouts.
- Existing browser, lifecycle, recovery, sharing, proof/CSP/SRI suites and four bridge tests pass on this slice. Screenshots under ignored `live-arena/output/playwright/`; `academy-mobile.png` is QA, not customer evidence.
- All game tests use free built-ins or intercepted synthetic responses. Actual game-provider calls: zero. External testers, physical devices and adoption are unmeasured.
- Provider/local-harness non-inference connection preflight remains the next Day 4 implementation slice. The educational text does not count as completion of that onboarding requirement.
- Independent cross-family release review remains pending after the prior two timed-out requests. A local code review is not a substitute for that release gate. No merge, production deploy, DNS change, social post or new scheduler is part of this checkpoint.

The bounded code reviewer identified that the referee's hard 400-ply exhibition cap sets `over` without a rules-defined draw. The candidate now classifies that trusted referee reason as capped in evaluation, result images and Arena labels instead of treating every terminal state as a draw. The rules executable itself and historical records remain unchanged. A synthetic internal near-cap unit test exercises this semantic boundary; it is not a claimed complete 400-ply match transcript.

The reviewer rechecked the changed classification hunks and confirmed the finding resolved, with no residual finding in that scope. This focused review is distinct from the pending cross-family release review.

Run from `live-arena`: `npm test`, `npm run build`, then the Python browser scripts against an owned preview on 127.0.0.1:5178. Stop that preview and its browser processes afterward.
