# Local multi-agent competitions

Run a finite cup among 3–8 declared agents using the live arena's pinned rules
engine. The default cup plays First Legal, Seeded Wildcard and Tactician across
tic-tac-toe, Connect Four and Nim: three pairings, two seeds, both seats, 36 games.

From `live-arena` after `npm ci`:

```sh
npm run compete -- --out output/competitions/my-first-cup
npm run compete -- --verify output/competitions/my-first-cup
```

Choose a new output directory for each run. Existing directories are never
overwritten. Verification rereads the evidence, reproduces the bounded local
policy decisions and recomputes standings. It creates no new archive and calls
no provider. On Windows PowerShell use `npm.cmd`
when forwarding arguments.

## Choose games and entrants

Pass `--plan my-cup.json` together with `--out`. A plan has this exact shape:

```json
{
  "schema": "builderwars.local-competition-plan.v1",
  "id": "my-cup",
  "createdAt": "2026-10-21T00:00:00.000Z",
  "agents": [
    {"id": "first", "name": "First Legal", "policy": "first-legal"},
    {"id": "random", "name": "Seeded Wildcard", "policy": "seeded-random"},
    {"id": "tactics", "name": "Tactician", "policy": "tactician"}
  ],
  "games": ["tictactoe", "connect4", "nim"],
  "seeds": [20261021, 817263],
  "maxPlies": 42
}
```

Plan and agent IDs use lowercase ASCII slugs of at most 32 characters. Agent IDs
and names must be unique. Games and seeds cannot repeat. Choose 1–3 listed games,
1–8 unsigned 32-bit seeds and a move limit from 2 through 400. Even the largest
plan has only 1,344 scheduled matches. Additional agents can use the same policy
under distinct declared identities; that does not imply distinct models.

Each unordered pair plays twice per seed in each game, reversing seats. Random
choices use a seeded stream per agent, so changing seats does not share or consume
an opponent's random stream. Agent IDs participate in that stream identity; keep
the plan unchanged to reproduce a run.

## Read the result

Standings stay separate for each game. A natural win earns 1 point, a natural
draw 0.5 and a loss 0. A match that reaches the chosen move cap remains visible
as capped and earns no points. It cannot count as a draw or win. Equal points
share a rank; display order is not a tie-break claim. These small, correlated
seed cohorts establish results for this cup, not statistical general superiority.

The output retains the plan, report, manifest, source snapshots, match packages,
proofs and matching standalone referee/verifier. Packages import through the
arena's existing replay import. The competition manifest binds the seed and
schedule; the legacy match-package seed field remains unknown because that
version does not carry a competition plan. Keep the complete directory together.

Full-cup verification requires a matching source checkout: the command compares
the runner's inventoried source files and dependency lock with their saved
snapshots before reproducing policy decisions. Archived code is data and is
never automatically executed. Each match proof can also be checked separately
with the saved `referee/verify-<digest>.mjs` file and Node.js 22 or later, without
npm dependencies or network access:

```sh
node CUP_DIRECTORY/referee/verify-DIGEST.mjs CUP_DIRECTORY/matches/MATCH_ID.jsonl
```

That standalone check verifies one legal game history. It does not recompute the
complete cup's schedule, agent policies or standings.

Verification checks content digests, schedule coverage, declarations, limits,
replay legality, proof correspondence and the recomputed standings. Missing or
inconsistent evidence fails verification. A failed write is incomplete evidence,
not a completed cup; preserve it for diagnosis and rerun into a new directory.

Elapsed values in replay events are zero placeholders, not measured latency.
Tokens remain unavailable and local policy moves incur no provider charge.
Hashes and replay proofs establish content integrity and legal game history;
they do not authenticate the operator or independently attest execution or agent
identity. Anyone able to replace an entire unsigned evidence directory can create
a different internally consistent cup.

These are scripted local agents. This runner does not connect LLMs, execute
submitted programs, train a model, publish a league, update global rankings or
change the website. Use the existing customer-owned connection workflow for
model exhibitions and the Python competition matrix for subprocess entrants.

Goal and measured execution:
[Multi-agent games goal](BUILDERWARS_MULTI_AGENT_GAMES_GOAL_20261021.md).
