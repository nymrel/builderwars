# Frontier campaign phase 1: first candidates to pass the fixed promotion gate

September 6, 2026. Owner: Hermes execution lane (operator directive 2026-09-06,
"plan and execute entirely around BuilderWars"). Campaign charter:
`FRONTIER_CAMPAIGN.md`. Claim: `hermes-bw-frontier-candidates-20260906b`.

Historical phase-1 snapshot. Later phase-2 attempt-ledger and release evidence
take precedence over the next-step list below; this report does not activate or
promote a public contender.

## What changed in the evidence

The 2026-09-05 results (`BUILDERWARS_SELF_IMPROVEMENT_RESULTS_20260905.md`) recorded
**zero candidates admitted** across three short games: every run was retained at the
fixed gate (minimum gain 0.05, alpha 0.05, Hoeffding bound on paired seed-deltas),
with lower bounds of −0.148 / −0.095 / −0.076.

This increment ran the **same unmodified tooling** (`scripts/self-improve.ts`,
same referee digest `d5135878…`, same promotion gate, same evaluation-custody rules)
with more training episodes and the maximum evaluation pairs the schema admits
(512 pairs = 2048 games per evaluation). Three candidates **passed the fixed gate**:

| Game | Training episodes | Candidate score | Incumbent score | Lower gain bound | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| Tic-tac-toe | 10,000 | 0.911 | 0.706 | **+0.0974** | **promote** |
| Connect Four | 10,000 | 0.985 | 0.767 | **+0.1106** | **promote** |
| Custom 3x4 connect-3 | 10,000 | 0.920 | 0.694 | **+0.1174** | **promote** |

Scores are paired-seat means against seeded random opposition with draws as 0.5.
Every plan was committed to `plan.json` before evaluation; every run directory is
immutable (`flag: "wx"` writes only) with `evaluation-spent.json` claiming the suite
before results were observed. Zero provider calls; total wall time under 12 seconds
of optimization compute (~369k + 885k + 300k budget nodes).

Run custody (all under `live-arena/output/self-improvement/`, gitignored by design;
digests are the durable record):

- Tic-tac-toe: `tictactoe-1788758533401-5c66c24e-f1fa-4684-9001-60df1e15a20f`
  (champion `5c08d97d68a34908b419a7dedc4af2a0f8d70a499066893f99394fd979b6ddd1`)
- Connect Four: `connect4-1788758584164-30e13d8b-0d4a-4db3-9e5f-dbe8d10b1368`
- Custom: `custom-1788758601890-63bcd26f-cc7c-4cf9-a756-23c8a0866c55`
- Cross-game strength summary: `hermes-strength-summary-20260906.json`

## Honest reading — why the 09-05 run retained and this one promoted

The gate did not change; the sample did. The 09-05 runs used 600 training episodes
and 128 evaluation pairs. Paired-delta noise at 128 seeds gives a Hoeffding penalty
of √(2·ln20/128) ≈ 0.216, so a real gain needed to be large to clear +0.05. At 512
pairs the penalty is ≈ 0.108. Both effects compound: longer training raises the true
mean gain, and the tighter bound lowers the bar. This is the gate working as
designed — demanding either a large effect or a large sample — not a settings
change. No gate constant, optimizer constant, referee, or promotion-logic file was
modified (worktree diff against the branch point touches docs only; verify with
`git diff 9c6288b..HEAD -- live-arena/src live-arena/scripts` → empty).

## Phase-1 strength diagnostics (independent grader, same worktree session)

`measure-strength.ts` (public development partition, 16 seed-pairs, both seats,
both frozen opponents) confirms the champions are genuinely stronger and exposes
exactly where they are not:

| Champion | seeded-random seat0 / seat1 | immediate-tactics seat0 / seat1 | avoidable-loss profile |
| --- | --- | --- | --- |
| Tic-tac-toe | 0.969 / 0.938 | 1.000 / 0.500 | 1 avoidable loss in 34 defense opportunities |
| Connect Four | 1.000 / 1.000 | 1.000 / 0.000 | 16/16 avoidable losses as seat 1 vs tactics |
| Custom 3x4 | 0.938 / 0.750 | 0.562 / 0.000 | 7/39 + 7/16 avoidable losses vs tactics |

Read: the tic-tac-toe champion is near-ceiling against both opponents. The Connect
Four champion never loses to random but **drops every game as seat 1 against the
immediate-tactics opponent** — a genuine, precisely-localized weakness, not noise.
The custom-board champion wins against random but is materially weaker than tactics
in both seats. These gaps are the training targets for the next increment; they are
also the strongest evidence yet that the grader can distinguish known-correct from
incorrect tactics (charter phase-1 disproof test: passed).

## What this is not

- Not unseen-state generalization: evaluation uses reserved random streams from the
  committed plan; opponents are seeded random + one-ply tactics.
- Not a website contender change: `src/` is untouched; website bots remain the
  built-in Tactician/Wildcard.
- Not LLM training: outcome-trained linear value policies (22 board features),
  assisted-agent class, zero provider calls.
- Not promotion to ranked competition: `promotion: "not-authorized"` in every
  strength receipt; ranked promotion still requires the phase-2 attempt ledger and
  sequential-testing rule.

## Next exact moves (phase 1 → 2 boundary)

1. Seat-1 Connect Four gap: the champion loses all 16 tactical-opponent games from
   the second seat. Root-cause via the retained `training-games.jsonl` episodes
   (openings are 2 forced plies, so seat-1 exposure is structural) before any
   further training — one diagnostic revision, per charter phase-3 discipline.
2. Attempt ledger + sequential testing (phase-2 entry requirement): repeated
   forked runs at alpha 0.05 per attempt inflate cumulative false-promotion risk;
   the ledger is the gate that makes candidates like these safe to promote.
3. Only after (2): consider `live-arena` "Load policy" admission of a champion as a
   *development* contender, clearly labeled, never as a ranking claim.
