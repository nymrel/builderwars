# Model-plan proof artifacts (fantasy_redraft, seed 9300)

Two fixed `agentwars.fantasy_plan_artifact.v1` artifacts built as Ox Alpha MAX
bounded-build outputs. Every artifact carries the exact 20-row seed-9300 board
(`EXPECTED_BOARD_SHA256` `aa63466ad9ef2ccd9f9d9d8115e9313406450049fc5fe5fcbe36f0e2397a9bad`)
and validates through `entrants/fantasy_plan_harness.load_artifact`.

Shared claim fields: `modelClaim` `ox-alpha-free`, `reasoningEffort` `max`,
`maxTokens` `131072`, `fallbacksAllowed` `false`, `route` `opencode-go`,
`planLineNumber` `1`.

| Artifact | runId | planLineSha256 | terminalTextExactPlan |
| --- | --- | --- | --- |
| `plans/win-now.json` | `9c2e11de-c782-4747-ad12-3df8467aa8fe` | `bfd80fd360e17fcb1c5cc878aa428733db63d1f1346c847abdd340dc9ac6429a` | `false` |
| `plans/contrarian.json` | `8a28d971-992a-4e79-a820-151b26be94fc` | `7605ee02b48f976942d5b29c7af8146ae08f3d8567100b1b26f1baf22e267b1c` | `true` |

## Truth statements (binding)

- These are fixed model-generated plans, not live inference.
- Source fields are receipt-backed claims but do not attest
  provider/model/person/runtime.
- No credentials are used.
- Replay proves rules, accepted plan-derived moves, state, and scoring only.
- This is not a provider leaderboard result.
