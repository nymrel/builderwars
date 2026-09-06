# OpenRouter entrants — the first paid, api-backed matches in this arena

- **Date:** 2026-09-06
- **Repo / branch:** BuilderWars @ `ox/cross-model-series-20260829` (main checkout)
- **Engine digest:** `afa6eeaf5f5a3d0eca669281ba2504a9c84fd45e8bf5aa5538b294f1370dfd27` — unchanged; no file under `arena/` was modified by this lane.
- **Entrant:** `entrants/or_harness.py` v2, registered as `or-harness` and `or-harness-m3`, handle `claude-cli`.
- **Spend:** **$0.2490** measured (or-harness side, from the provider's own usage accounting, recorded per move in each transcript). 16 transcripts, under the 20-match cap.

---

## ALL RESULTS HERE ARE EXHIBITION, NOT RANKED

Under the registry's `author_conflict_rule` — *"an entrant's author may not rank
in a game they authored"* — nothing on this board is a ranked result:

- Both games in this checkout (`nim`, `ten_fronts`) are **studio-authored**.
- Every registered entrant (`tf-harness`, `tf-naive-harness`, `or-harness`,
  `or-harness-m3`, and the nim reference arms) is **studio-authored**.

So there is no pairing available in this repo today that is not
author-conflicted. **Every number below is exhibition.** The board does not
become rankable until a game or an entrant arrives from outside the studio.
Stating that plainly is cheaper than publishing a standing that quietly
violates the rule the registry commits to.

---

## What already existed, before this lane

Worth stating exactly, because the brief I was given had it wrong in one
direction and a mid-lane correction had it wrong in the other.

| Backend | Status before 2026-09-06 |
|---|---|
| `stub:` | Measured — the reference series, the tournament, both nim arms. |
| `cli:` | **Exercised, but never concluded.** 16 transcripts (8 `matches/ollama/`, 3 `matches/cheap-vs-expensive/`, 2 `matches/cross-model-20260829/smoke/`, 3 `matches/model/`). Spot-checked here: they still replay-verify PASS under the current engine and 49 of 51 recorded moves carry `source=model`. |
| `api:` | **Never run.** No transcript in the repo carried an `api:` backend. |

And the distinction that matters: **no valid cross-model result had ever been
produced in this repo.** `cross-model-20260829` stopped at its no-fallback
quality gate (llama3.2:3b answered on-list only ~79–83% of the time), and the
August `cheap-vs-expensive` series is recorded there as fallback-driven and not
citable. "The cli backend has run" and "the arena has published a cross-model
finding" are different claims; only the first was true.

The old `backends.py` docstring said `cli` and `api` were *"implemented and
UNMEASURED — no key was used and no spend was incurred building this."* Split by
clause: the **no-key/no-spend half was true** and is still true of `cli` (local
Ollama weights and a prepaid subscription CLI have no marginal cost), while the
**`cli` is unmeasured half stopped being accurate on 2026-08-14**. The docstring
now says exactly that rather than reversing a true statement.

---

## What this lane added

1. `entrants/backends.py` — `ApiBackend` is now provider-aware. Spec grammar:
   `api:<ENV_VAR>` (Anthropic, unchanged), `api:<ENV_VAR>:<model>`, and
   `openrouter:<ENV_VAR>:<model>`. `max_tokens` defaults **8000** on OpenRouter,
   because reasoning models spend their budget on hidden reasoning tokens and
   truncate the *visible* answer to an empty string below that — the old 256
   default would have made every reasoning model look like a model that never
   answers. Per-call token and cost accounting, in **integer micro-USD** because
   `arena/canonical.py` refuses to encode a float and a float in a transcript
   note would abort the match.
2. `entrants/or_harness.py` — the entrant. Plays `nim` and `ten_fronts`, in the
   shape of the reference computing arms: the harness does the arithmetic, the
   model's job is narrowed to picking from a validated short list, and an
   unusable answer falls back to a computed move rather than forfeiting.
3. `bin/run_match.py`, `bin/run_series.py` — an additive `--entrant-env NAME`
   flag. See the next section; this was the blocker for the whole lane.
4. `entrants/registry.json` — both entrants, declared honestly.

---

## The gap that made `api:` unreachable

`ENTRANT_CONTRACT.md` documents a manifest `env` list as the sanctioned way to
hand an entrant its own credential, and `arena/sandbox.py` already implements
it correctly. But **all three shipped runners hardcoded `"env": []`**, so the
`api:` backend the contract sanctions could not receive a key from any shipped
tool. The flag closes that and nothing else; default stays `[]`, so a run that
does not ask for a credential still cannot be handed one. **No file under
`arena/` was touched.**

### Mutation-proved both directions, same seed (9000)

| Run | `--entrant-env` | Result |
|---|---|---|
| `envproof-negative` | absent | `source=fallback:backend_error:RuntimeError`, **`calls=0 cost_micro_usd=0`** — the engine stripped the key, no HTTP happened, nothing was spent. The harness's fallback still won the match rather than forfeiting. |
| `envproof-positive` | `OPENROUTER_API_KEY` | `source=model` on 6/6 moves, `calls=6 tok_in=990 tok_out=1533 cost_micro_usd=3829`. **VERDICT: PASS** on replay. |

That pair is the evidence for the property the whole project rests on: the
engine holds no credential, and it demonstrably strips one it was not explicitly
told to forward.

---

## Results

### nim — `z-ai/glm-5.2` behind **both** entrants (model held constant)

| seed | seat 0 | winner | moves | verified |
|---|---|---|---|---|
| 9200 | or-harness | or-harness | 5 | PASS |
| 9200 | naive-harness | naive-harness | 5 | PASS |
| 9201 | or-harness | or-harness | 17 | PASS |
| 9201 | naive-harness | naive-harness | 17 | PASS |

**4/4 replay-verified. or-harness: 22/22 moves from the model, 0 fallback.**
2–2, and the split is a pure seat effect: nim's `setup` starts from a
first-player win, seat 0 won all four, so **both arms played optimally**.

This is the **first gate-clean real-model result in this repo** — the exact gate
`cross-model-20260829` failed. `glm-5.2` went 22/22 on-list where `llama3.2:3b`
managed ~79–83%.

It also **fails to reproduce the arena's thesis on nim**, and that is the honest
finding: with a model this strong the naive control arm never emitted a
malformed move, so the validating harness had nothing to save it from. Nim
separates harnesses only when the model is weak enough to blink.

### nim — `minimax/minimax-m3` behind both entrants (frontier headline)

| seed | seat 0 | winner | moves | verified |
|---|---|---|---|---|
| 9300 | or-harness | or-harness | 11 | PASS |
| 9300 | naive-harness | naive-harness | 9 | PASS |

**2/2 replay-verified. or-harness: 10/10 from the model, 0 fallback.** Same seat
effect, same conclusion.

### ten_fronts — `glm-5.2` vs the unvalidated control arm on `stub:v1`

| seed | seat 0 | winner | moves | reason | verified |
|---|---|---|---|---|---|
| 9400 | or-harness | or-harness | 2 | forfeit:illegal_move | PASS |
| 9400 | tf-naive-harness | or-harness | 1 | forfeit:illegal_move | PASS |

**or-harness 2/2 (100%).** The control arm forfeited on its first commit, which
is what it is built to demonstrate: in Ten Fronts, format discipline is
match-deciding. Backends were **split** here, so this measures harness, not
model.

---

## Finding: no Ten Fronts match in this repo has ever finished, and none can

The deep match (`tf-deep`, seed 9500, or-harness on `glm-5.2` vs `tf-harness` on
`stub:v1`) is the first Ten Fronts match here in which **both** entrants were
competent enough to play past round 1. Both seat orders ended:

```
void / unfinished, at exactly 44 moves
```

`arena/games/ten_fronts.py`:

```python
def move_bound(state):
    """Two engine turns per remaining round, plus a small margin."""
    return (ROUNDS - state["round"]) * 2 + 4
```

A round is **four** engine turns, not two — signal seat 0, signal seat 1, commit
seat 0, commit seat 1. The runner asks each seat once per phase. So a full match
needs `20 × 4 = 80` turns and the bound allows `44`. **Short by 36.**

This has been latent since the game landed, because it can only be reached by two
entrants that both survive round 1. Every pre-existing `matches/tournament/`
Ten Fronts transcript ends in a forfeit at move 0–2:

```
forfeit:entrant_exited | moves 1      forfeit:illegal_move | moves 1
forfeit:entrant_exited | moves 0      forfeit:illegal_move | moves 2
forfeit:illegal_move   | moves 1      forfeit:entrant_exited | moves 0
```

**Not fixed here** — a game module runs inside the engine's trust domain and is
outside this lane's scope, and changing it requires a `VERSION` bump that
invalidates existing replays. The one-line patch, for the games/engine lane:

```python
    return (ROUNDS - state["round"]) * 4 + 4
```

Until it lands, **no Ten Fronts standing is meaningful**: a competent pairing
voids, so the only results the game can currently produce are forfeits by
whichever side is worse at formatting.

---

## Finding: the series move-source counter mis-reports rich notes, loudly and backwards

`bin/run_series.py` classifies provenance with an exact string equality:

```python
key = "model" if note == "source=model" else "fallback"
```

The first version of `or_harness.py` appended telemetry to `note`. Every move
was then counted as a fallback and the series printed:

> `or-harness: 0/8 moves came from the model, 8 from fallback`
> `^^ THE MODEL NEVER ANSWERED. This result is about the harness's own solver, not the model.`

over a run in which the transcripts show `source=model` on **8 of 8** moves. The
warning fires in the most damaging possible direction — it manufactures the exact
finding that stopped `cross-model-20260829` — and any entrant with a richer note
inherits it.

Fixed **entrant-side**: `note` is now exactly `source=<value>` and telemetry
moved to its own `usage` key. The referee reads only `move`, so both are
transcribed for audit and structurally removed before scoring.

The reporting-layer patch is left for the owning lane, since a note is documented
as free-form:

```python
key = "model" if note.split()[0] == "source=model" else "fallback"
```

---

## A paid entrant cannot become a money faucet

`or_harness.py` v2 carries `--max-spend-micro-usd`, default **250 000**
(= $0.25) per entrant process, which is per match. Past the ceiling it stops
calling the model and plays its own computed move — so hitting the cap costs
accuracy, never a forfeit.

Mutation-proved at `--max-spend-micro-usd 0`:

```json
{"type":"move","move":{"heap":0,"take":1},"note":"source=fallback:spend_ceiling",
 "usage":"model=api:openrouter:z-ai/glm-5.2 calls=0 tok_in=0 tok_out=0 cost_micro_usd=0"}
```

`calls=0`, `cost_micro_usd=0`, and the move it played is the correct XOR-winning
move for `[3,5,7]`. The most expensive real match measured here was **$0.1097**,
so the ceiling is ~2.3× headroom on honest play.

These entrants are **local, operator-run only**. Nothing here is wired to a
public endpoint, and nothing here should be: the runner must be handed
`--entrant-env` explicitly on the command line, and the negative proof above
shows what happens without it.

---

## Spend

Measured from the provider's own usage accounting, recorded per move in each
transcript. or-harness side only — the opponent side in the nim series ran on the
same model and carries no cost telemetry, so true total is somewhat higher.

| series | micro-USD | USD |
|---|---|---|
| `nim-glm52-v2` (4 matches) | 31 734 | $0.0317 |
| `nim-minimax-m3` (2 matches) | 12 884 | $0.0129 |
| `tf-glm52` (2 matches) | 1 792 | $0.0018 |
| `tf-deep` (2 matches) | 202 603 | $0.2026 |
| `envproof-negative` | 0 | $0.0000 |
| **total** | **249 013** | **$0.2490** |

`nim-glm52` (the superseded v1 run) and `envproof-positive` report 0 above
because they used the old note format; their real cost was ~$0.0106 and
~$0.0038 respectively.

Note that the engine's own line — `cost: $0.00 — the engine makes no model
calls` — remains **literally true**. The arena still spent nothing. The entrant
spent $0.25, in its own process, on its own key.

## Commands

```bash
python bin/register_entrant.py --script entrants/or_harness.py --handle claude-cli \
  --backend "openrouter:OPENROUTER_API_KEY:z-ai/glm-5.2" --games nim ten_fronts \
  --features fallback retries

python bin/run_match.py --game nim --seed 9000 --entrant entrants/or_harness.py \
  --entrant entrants/naive_harness.py --backend "openrouter:OPENROUTER_API_KEY:z-ai/glm-5.2" \
  --entrant-env OPENROUTER_API_KEY --out matches/openrouter-20260906/envproof-positive

python bin/run_series.py --game nim --a entrants/or_harness.py --b entrants/naive_harness.py \
  --backend-a "openrouter:OPENROUTER_API_KEY:z-ai/glm-5.2" \
  --backend-b "openrouter:OPENROUTER_API_KEY:z-ai/glm-5.2" \
  --entrant-env OPENROUTER_API_KEY --seeds 2 --start-seed 9200 \
  --out matches/openrouter-20260906/nim-glm52-v2 --timeout 120 --backend-timeout 90

python bin/verify_replay.py matches/openrouter-20260906/envproof-positive/d58894c2215abc21.jsonl
```

## Model identity

`claimed_model` is the model ID **requested** at the provider. It is never the
model's self-report — models misreport their own identity. The reliable signal
is that the provider refuses an unknown ID, mutation-proved 2026-09-06: a known
ID returns 200 and an invented one (`z-ai/glm-9point9-nonexistent`) exits
non-zero. Every result still carries `model_attested: false`; replay proves rule
compliance and adjudication integrity, never who was behind the pipe.
