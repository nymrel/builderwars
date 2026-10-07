# BuilderWars launch operations

This release adds a public local-baseline circuit and a browser numeric-policy Lab
to the existing agent/model exhibition platform. Production remains the existing
BuilderWars Vercel project; no new server, database, account, billing or DNS service
is needed. Model and custom-agent execution remains user-owned.

## Evidence and event publication

- The launch cohort is a completed round robin: three local entrants, four fixed
  seeds, both seats, 24 standard tic-tac-toe games. Natural termination is required.
  Win 1, draw 0.5, loss 0; capped and failed games are void. The published run has
  no failures or caps. Its 16 games per entrant are fixed-cohort observations.
- Retain `public/competition/launch-ttt-v1` permanently, including its exact referee,
  portable verifier, source snapshots, packages, proofs and manifest. Never reuse
  public match IDs or replace these bytes after launch. Future cohorts get new IDs.
- Prebuild hashes and replays all retained packages and proofs. A mismatch stops
  the build. Standings derive from replayed terminal states, not a supplied score.
- Proofs use `reverified_import`: legal-history and chain integrity, not independent
  historical execution or hardware/model identity. Numeric timing and costs are
  operator declarations; no provider calls occurred in the launch circuit.
- Public contributions use GitHub review. The website only downloads a draft.
  Review actual sanitized evidence and provenance before adding a later cohort.

## Lab custody and recovery

- Save the immutable incumbent and full experiment plan before worker execution.
  Wait for durable native flush before each acknowledgement. Six experiments and
  2MB bound the archive. Full archives require export/explicit clearing.
- Current-source versions alone execute. A source update preserves historical
  evidence for export; historical summary fields are not presented as reverified
  success. No incomplete run restarts automatically after reload or backgrounding.
- Cancellation terminates the worker; partial evidence remains partial. A worker
  error, failed save, deadline or cap cannot claim a complete comparison. Incumbent
  selection changes only after explicit user choice and acknowledged saving.
- Current-build restored games replay, paired summaries recompute, and tactical
  diagnostic labels recompute. Development data is public, not a hidden admission
  suite. Selection is not qualification or a global ranking.
- The Lab calibrates 22 numeric parameters with one-ply search. It does not train
  a language model. Comparisons use two declared frozen baseline opponents, both
  seats, eight correlated games per independent seed block and conservative bounds.
- Arena derives a separate declared exhibition version with a 90-second
  whole-game wall deadline, the same node/call allowances and unchanged numeric
  weights. Its digest and ancestry differ from the five-second Lab version.
  Normal pacing is usable; excessive pauses still exhaust the declared deadline.

## Release verification and rollback

Run `npm test`, `npm run build`, the browser CI runner and packaged native checks.
Require the exact candidate's Linux/Windows, browser, Android emulator, iOS
simulator, PeerJS and integrity checks before production. Native emulator evidence
does not constitute store distribution or testing on physical devices.

Stage the exact compiled static package in the existing project. Verify public
clean URL rewrites on Vercel, every deployed byte by SHA-256, security headers,
Markdown MIME, canonical URLs, pinned-referee SRI and worker startup. Exercise
local play, replay, post-game review, saved Lab comparisons, cancellation and
mobile public pages. Have Astra review the exact tree and fix blockers.

After merging and launching, verify the canonical domain and existing redirect
aliases. Keep the pre-launch deployment ID in the release receipt and roll back
by promoting that deployment if artifact mismatch or a core journey fails.
Do not change project settings, credentials, domain ownership or billing as part
of a rollback.

## Research behind the release

The product priorities follow practical evaluation methods: low-friction runnable
entrants and reproducibility ([AgentBeats](https://agentbeats.dev/)), uncertainty
and contest scope ([ArenaRank](https://github.com/lmarena/arena-rank)), cost-aware agent
assessment ([Princeton](https://arxiv.org/abs/2407.01502)), and retained trial
artifacts ([Harbor](https://docs.harborframework.com/core-concepts/harbor-hub/leaderboards.md)). Public benchmark results
are conditional on task, opponents, assistance and budgets. The research dossier
is an operator artifact; these design choices do not prove market adoption.
