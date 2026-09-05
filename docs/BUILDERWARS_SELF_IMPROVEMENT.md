# BuilderWars self-improvement: measured competitors, not remembered captions

September 5, 2026. First local implementation; not a production strength claim.

## Product direction

Build agents whose improvements are visible, reproducible and attributable to
specific model, tool, policy and harness versions. Success means fewer illegal
responses and tactical mistakes, stronger play against qualified opponents, and
competitive results within explicit compute classes. Industry leadership is an
aspiration requiring external competitions, not a label earned by our own tests.

Keep three separate divisions: raw-model decisions, tool/search-assisted agents,
and outcome-trained local policies. A strong engine assisting a model must never
be reported as the unaided model learning chess. Existing rule-replay receipts
remain distinct from model/execution attestations.

## Implemented first loop

Practice episodes -> terminal rewards -> updated value-policy coefficients ->
immutable candidate -> reserved paired evaluation -> retain or local promotion.

- `live-arena/src/self-improvement.ts` uses the existing immutable referee runtime.
  Chess, checkers, Connect Four, tic-tac-toe and validated custom connect rules
  share the same legal-state/action boundary. No second rules implementation.
- A bounded Monte Carlo return update changes22 numeric feature weights after
  completed practice episodes. This is actual parameter learning in a small local
  value model, not LLM fine-tuning, prompt reminders or a world-class game engine.
- Fixed board features and one-ply successor inspection are explicit assistance.
  Candidate and initial baseline have the same features, terminal detection and
  search budget; observed differences can be associated with learned weights.
- Training mixes self-play and seeded random opponents. Unfinished/capped games
  produce no training reward. Natural draws are0; wins/losses are+1/-1 with a
  fixed temporal discount. No heuristic material score is substituted for a win.
- Evaluation uses frozen policies, matched seeded openings/opponents and seat
  swaps. Its seed stream is reserved and saved before training, excluded from
  training episode seeds. Evaluation outcomes never update parameters.
- The per-attempt gate uses bounded paired score differences and a conservative
  lower gain bound. Capped evaluation games veto promotion. All failures and
  rejected versions remain visible. There is no production champion mutation.
- Artifacts contain exact rules/referee/version/parent/weights and a digest.
  Node/time limits, cancellation, schema validation and replay legality fail
  closed. A unique output directory prevents overwriting an earlier experiment.

The reserved evaluation is **not an unseen-position guarantee**: board states may
overlap across independent game streams. Seeded-random opposition is a development
qualification only. It is insufficient to certify strength against Tactician,
human experts, Stockfish, stronger frontier harnesses or an external league.
Do not select repeatedly tested candidates by their displayed qualification scores
and then call that same suite a fresh holdout. Fresh external admission is separate.

## Run a bounded local training cycle

From `live-arena`, after the existing dependency setup and `npm run referee`:

```powershell
node node_modules/tsx/dist/cli.mjs scripts/self-improve.ts --game tictactoe --episodes 600 --pairs 128 --seed 20260905 --seconds 120 --nodes 500000
```

The convenience alias is `npm run improve -- ...` (`npm.cmd` in Windows
PowerShell when passing flags). Its pre-hook builds the referee automatically.

Supported `--game`: `chess`, `checkers`, `connect4`, `tictactoe`, `custom`.
The CLI custom recipe is3x4 gravity/connect3; the library accepts other validated
custom boards. `--max-plies` is1–400 for training and at least3 for evaluation.
Use a realistic cap for long games; a short chess cap measures incomplete runs,
not chess improvement. Work limits are cooperative between referee transitions;
a single synchronous transition can overshoot a wall-clock deadline.

Each directory in ignored `live-arena/output/self-improvement/` contains:

- `plan.json` and `training-config.json`, persisted before optimization;
- `incumbent.json`, `candidate.json`, original `training-games.jsonl`;
- `evaluation-spent.json`, `evaluation.json` with all matched games;
- `champion.json`, retaining the incumbent on rejection, plus `rollback.json`;
- `receipt.json`, or `failure.json` on an interrupted/failed cycle.

To continue a lineage, run another finite cycle with `--parent` pointing at the
previous accepted `champion.json`. Do not silently use the newest candidate.
Every new invocation reserves a fresh evaluation stream; fixed training seeds and
saved plans allow source-bound reproduction. No persistent service, scheduler,
download, cloud inference or new spend is started by training.

## Play the learned policy through the existing local harness route

The same script supports `--move PATH_TO_POLICY_JSON`, accepts the existing
bridge's game JSON on stdin, and returns a legal move on stdout. It reconstructs
the complete supplied move history and rejects a contradictory board, turn, rules
or legal list. No arbitrary commands are taken from game requests.

Use the existing customer-command bridge with an explicit fixed argv containing
absolute paths to Node, `node_modules/tsx/dist/cli.mjs`, `scripts/self-improve.ts`,
`--move`, and the selected immutable policy artifact. Configure its public model
label as `local-learned-value/<artifact digest>`, retain exact origin/token/call
limits and the existing custom-command acknowledgements. The bridge is a real
local execution boundary, not a renamed browser bot. Connection instructions and
all bridge restrictions remain in `live-arena/README.md`.

Candidate artifacts can be played as clearly labeled development contenders;
their existence is not admission to a ranked division. The current public website
does not yet have a one-click training/import control or account-wide champion
registry. Website defaults and all existing contenders are unchanged.

## Ordered next stages

1. **Reliability and tactics:** replay actual mistakes as regression cases; add
   stronger frozen opponent pools and independent tactical graders. Report invalid
   outputs, missed wins, preventable losses, completion and resource use separately.
   Use fresh evaluation positions after any tuning, with symmetry/history controls.
2. **Long-game strength:** efficient search adapters and proper long-horizon chess/
   checkers curricula. Establish fixed engine versions and compute controls before
   using expert engines as opponents or teachers. Separate distilled knowledge,
   search assistance and learned behavior. Preserve licenses and engine attribution.
3. **Frontier harness optimization:** task-bounded candidates changing prompts,
   planning/search depth, memory retrieval or tools. Use eligible provider access,
   confirmed inference caps and frozen model/effort snapshots. No unsupported
   subscription reuse, hidden paid retries or automatic production code execution.
4. **Product integration:** explicit opt-in training controls, progress/cancel,
   immutable version selection, source-bound playback, rollback and portable
   artifacts. Match and Evals freeze the selected version. Browser clients must
   not inherit another user's mutable champion or silently start training/inference.
5. **Broader activities and competitions:** typed task adapters with explicit
   observations/actions/rewards/resource limits, contamination-resistant graders
   and separate train/development/admission partitions. No arbitrary uploaded code
   until containment and creator admission exist.
6. **External qualification:** repeated performance against strong diverse
   opponents, seat fairness, uncertainty, compute/cost comparisons and independent
   reproducible events. Only this evidence can justify best-in-class claims.

Each stage earns its next expansion through verified outcomes. Do not multiply
training volume because logs exist; retain an incumbent when gains are absent.

## Research informing the design

[AlphaZero primary paper](https://arxiv.org/abs/1712.01815) combines self-play,
learned value/policy representations and search. This implementation is a small
local baseline, not an AlphaZero replication or comparable training run.
[Reflexion](https://arxiv.org/abs/2303.11366) describes verbal feedback/memory;
that mechanism is distinct from the numeric outcome updates here and from LLM
weight training. Neither paper establishes results for BuilderWars.
