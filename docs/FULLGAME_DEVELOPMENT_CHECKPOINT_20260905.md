# Full-game development checkpoint — September 5, 2026

Status: bounded local research, **no candidate promoted; phase 3 not achieved**.

## Operator-directed change in priority

The operator directed us to use mature open-source game intelligence and put
actual frontier models into more complex games now. Stop the small numeric
learner approach after its diagnostic revision. Retain this reusable measurement
code and its failures; prioritize an explicitly engine-assisted chess exhibition.
Do not make that exhibition wait for the numeric learner to become strong.

## Implemented measurement infrastructure

- A declared 26-feature, fixed two-ply numeric harness, separate from the legacy
  one-ply executor. A depth-three public heuristic teacher supplies preferences;
  pairwise fitting changes numeric coefficients, not provider-model weights.
- Connect-game and English-checkers position grouping. Train/development targets
  respect prior private reservations and exposed public histories.
- Paired full-game blocks: incumbent and candidate, both seats, two frozen
  non-random opponents. Inference, opponent and tactical-grading work are separate.
- Caps invalidate scores rather than becoming draws. Illegal/unassessed moves,
  tactical errors, uncertain seat regressions and uncertain gains veto admission.
- Development outputs are create-only, source-fingerprinted and non-promoting.
  The proposed 2,048-block admission setting is NOT an implemented private
  campaign ledger or a completed statistical qualification.

## Retained development failures

All three runs used 32 public deterministic seed blocks (256 games), zero
provider calls, and no private evaluator payload reads. They are exploratory
diagnostics, not independent held-out evidence or actual frontier-model games.

| Local run | Harness | Completed/capped | Observed gain | Result |
|---|---|---:|---:|---|
| checkers-01 | one-ply numeric | 236 / 20 | null | retain |
| checkers-strategic-01 | two-ply numeric | 247 / 9 | null | retain |
| ttt-strategic-01 | two-ply numeric | 256 / 0 | 0.14453125 | retain; uncertainty gate fails |

The two-ply runs recorded zero missed immediate wins or avoidable one-reply
losses. That is not proof of strong play. Checkers completion still fails.
Tic-tac-toe candidate observed score was 0.66796875, versus 0.5234375 baseline.

Historical executor fingerprints: one-ply comparison
`3bbc314a203bef1874132ab2d7fdb8c8789887c1ba01e6e2479a9e6372804212`;
two-ply comparisons
`f3ce7811d164542f0f3c813074c36c52f5d951f4b660ec3892ba6e666b38db5a`.
Those exploratory runs preceded final fixes and were not committed source
snapshots. Do not represent the current code as their byte-identical executor.
Full local receipts remain under `live-arena/output/fullgame-development/`.

## Audit and corrections

- Fable resolved as `claude-fable-5-1`, session
  `22759f86-4572-4d96-b562-05b38fe88470`, returned CHANGES_REQUESTED.
  Corrected the near-400-ply search horizon to use a nonterminal heuristic,
  never a cap-as-draw. The alleged multi-capture turn bug did not apply: this
  referee requires full capture chains in one move. Added an invariant/test.
  Reported list cost was $0.68564 including a Haiku helper; not incremental
  subscription billing. A preceding rate-limited call produced no review.
- Gemini methodology advisory informed seed-block analysis and finite-sample
  bounds. Its proposed sample count was not adopted wholesale. Its subsequent
  code review timed out with no verdict after 300 seconds, receipt
  `peer-antigravity-20260905T210324Z-b97b82948a`.
- Independent Codex static review found a shared-deadline gap. Preprocessing now
  shares a budget; deadline checks precede later stages and result publication.
  Filesystem calls are not OS-preemptible: this is cooperative deadline
  enforcement, not a guarantee that a stalled disk operation ends at five minutes.
- Public full-game replays initially lacked a private-target overlap guard.
  Historical marker-only audit found zero collisions for either checkers run,
  but **11 reserved target groups** appeared in the tic-tac-toe replays.
  That run is categorically ineligible for private-position novelty claims.
  Prior phase-2 campaigns were already closed before these runs; their old
  results are historical, and ALL unused private targets remain permanently
  burned. No vault payload was opened or reused. Future public replay writes
  reject such overlap without resampling.
- The historical exposure audit encountered 25,151 group markers beyond the
  old 20,000 reader bound. No evidence was deleted. The limit is now 65,536,
  with public batch preflight to prevent a write from overflowing that bound.
  The completed audit registered non-private public groups and retained private
  markers unchanged. Same-user trusted local storage is not independent custody.

## Statistical interpretation

The independent unit for a proposed random experiment is a seed block, not its
eight correlated games. Paired score differences have range width 2; scores
have width 1. The one-sided bound is
`mean - width * sqrt(log(1 / alphaEndpoint) / (2 * trials))`.
Ten score endpoints share the per-attempt alpha conservatively. The 0.5
balanced score floor is explicitly observed, not a population lower-bound claim.
Public deterministic PRNG diagnostics have no guaranteed random-sampling coverage.
Reference: [Hoeffding's inequality, Theorem 2](https://ai.stanford.edu/~jduchi/projects/probability_bounds.pdf).

## Validation and limits

188 tests plus TypeScript/Vite passed before the last deadline refinement;
focused filesystem/deadline tests and TypeScript passed after it. Exact final
source still requires full CI before integration. The browser entry bundle
remains `index-DAHsmVZF.js`; referee digest remains
`d5135878ce69345f5e8ee214c03d53cd1593052b9bcb97d1a96363f9b6dfa823`.
No public web or native-store deployment is claimed by this checkpoint.

Remaining original goals include qualified two-family gains, opt-in version UX,
actual eligible four-family games, reviewed source integration and required
public adoption proof. The next move is open-source-assisted chess competition,
not another numeric learner retry or another private holdout draw.
