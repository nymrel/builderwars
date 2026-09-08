# Nim exhibition slice

This integrates the Nim behavior from historical PR27 into the current live-arena runtime, learning, broadcast and match-package architecture. It does not replace the newer interface with the historical branch. The controlled model study is a separate Python experiment; browser play supplies no scientific result.

## Contract

- Normal play: remove at least one object from one heap; taking the last wins.
- Browser openings are recorded in rules, with default heaps `[3,5,7]`. Imported openings allow three or four heaps of 1–7 objects and nonzero XOR. Python seeds generate parity-test setups, not hidden browser state.
- Moves use canonical `{heap,take}` JSON. Malformed, extra-field and unavailable takes are rejected without mutating state. The built-in tactician uses XOR.
- Nim uses the existing per-seat public declarations and match-package proof controls. Builder, agent, harness, provider and revision identifiers remain self-declared; content hashes do not attest identity or model execution.
- Existing games and provider, import, replay, learning and resource controls remain in force. Human/bot Nim needs no credentials or provider call.

## Validation

The TypeScript suite includes the original Python-referee oracle: 758 states, 4,572 legal transitions, both seats and 18 registered seed setups. Focused tests cover rule bounds, malformed moves, last-object victory, XOR play and replay. The ordinary browser CI runner includes a 390px human Nim move journey, alongside the existing platform journeys. Runtime code, tests and build results are recorded by the integration review; a workflow definition alone is not passing evidence.

This source change does not establish authenticated competition, rankings, hosted persistence, store publication, model quality, or revenue.