# Multi-agent games and competitions

[October 22 Astra collaboration and refreshed evidence](ASTRA_MULTI_AGENT_COMPETITIONS_20261022.md)
continues this original goal and retains its execution history.

## Goal

Enable 3–8 declared local agents to compete in a reproducible multi-game round
robin, then execute a complete 36-match cup across tic-tac-toe, Connect Four and
Nim. Every pairing plays both seats for each fixed seed. Standings must come from
the pinned referee's replay, and every match must retain an importable package
and portable proof.

This is a finite competition among multiple agents using existing two-seat game
engines. It does not add simultaneous multiplayer rules or team coordination.

## Acceptance

- A configurable, bounded local runner supports 3–8 entrants, 1–3 standard games,
  1–8 unique seeds and a 2–400-ply limit. All contenders use declared built-in
  policies: first legal move, seeded random, or the existing Tactician.
- Every distinct entrant pair receives both seats for every game and seed.
  Per-agent random streams reproduce independently of seat order.
- Only replayed natural outcomes earn points: win 1, draw 0.5, loss 0. Capped
  games remain visible and void. Standings stay separate for each game.
- A new output directory holds the plan, source snapshots, match packages,
  proofs, matching standalone referee/verifier and a recomputable report.
  Verification rejects altered, missing, duplicate or mismatched evidence.
- The default cup actually runs: three agents × three games × two seeds × two
  seats for each pair = 36 matches. A fresh verification reproduces its report.
- Focused regression tests, the existing test suite, build and an independent
  source review assess the resulting change.

## Existing work and scope

The Python competition matrix already schedules subprocess entrants for a single
registered game. The live arena also retains a fixed, published 24-match
tic-tac-toe circuit. This goal adds a configurable local competition on the live
arena's current referee path. It preserves that public circuit, its strict
verification contract, the browser UI and existing provider integrations.

The implementation uses new local runner files and a new npm command to avoid
the ongoing UI/native and AgentWorld work. Output is local evidence; the goal
requires no inference purchases, public competition publication or website
deployment. Hashes establish content integrity, not independent execution or
model identity. These scripted baselines do not establish LLM performance.

## Execution receipt

Local implementation and execution completed on October 21, 2026. The saved
plan was created at `2026-10-21T23:52:01.182Z` with cup ID
`local-cup-6759e194c02f7186`.

| Game | First Legal | Seeded Wildcard | Tactician |
| --- | ---: | ---: | ---: |
| Tic-tac-toe | 3 | 2 | 7 |
| Connect Four | 2 | 2 | 8 |
| Nim | 2 | 2 | 8 |

Values are points from eight matches per entrant per game, including four in
each seat. All 36 scheduled matches terminated naturally; zero capped matches,
failures or provider calls occurred. No result was a draw. Tactician led these
three finite baseline cohorts; this establishes no general model ranking.

The full cup passed fresh verification. All 36 copied standalone proofs passed
using only Node and the saved verifier. A second run from the saved plan produced
the same files byte for byte, including the manifest and report.

- [Saved plan](evidence/multi-agent-games-20261021/plan.json)
- [Replay-derived report](evidence/multi-agent-games-20261021/report.json)
- [Artifact and source inventory](evidence/multi-agent-games-20261021/manifest.json)
- [Complete portable cup archive](evidence/multi-agent-games-20261021/BuilderWars-multi-agent-cup.zip)
- Archive SHA-256: `638dc8d772adddc6113f0ee7c3efdb0ee783d0c28f6d9ec0c923a75b1f991a56`
- Report SHA-256: `56c16a34bf2ca0a2b5111fadc4b263f583c3cfadeaa895c7c599dd2e6c749aa4`
- Source inventory digest: `4f418bc0ff090f99f138b825baf439797731548ebb86b60f5ceff76273aca93e`
- Pinned referee: `f2e3187ba13ac6faf66d3c45653c00ef72b0c118ca759a334d09c4364a4562a5`

Validation: `npm test` passed all 273 TypeScript tests and both Python suites
(14 tests discovered, one platform-dependent skip); `npm run build` passed.
Independent bounded source review reran all 12 new tests and found no remaining
confirmed blockers. Review fixes covered source-inventory completeness, symlink
parent handling and malformed Unicode admission. The final reviewed core and CLI
hashes match the saved source inventory.

The complete 805,624-byte evidence directory is retained in the execution
workspace at `live-arena/output/competitions/multi-agent-games-20261021` and in the
downloadable cup archive supplied with this result. The saved plan and exact
source snapshots allow reproduction. This receipt records local execution and
a reviewed source candidate; it does not claim source merge or deployment.
