# Cross-model series — STOPPED AT QUALITY GATE (no model result produced)

- **Date:** 2026-08-29 (claims window 18:10–21:10 local, PT)
- **Repo / engine:** BuilderWars @ `04bb2e5` (current deterministic engine), branch `ox/cross-model-series-20260829`
- **Planned experiment:** `--game nim --a entrants/solver_harness.py --b entrants/naive_harness.py --backend-a "cli:ollama run llama3.2:3b" --backend-b "cli:ollama run qwen2.5:14b" --timeout 120 --backend-timeout 300`
- **Status: the full series was NOT run.** The quality gate ("solver moves must come from the model, never fallback") tripped in the smoke test and the gate is unsatisfiable with the assigned model. Per the binding constraint, the series was stopped, the failure mode diagnosed, and nothing was committed as a model result.

## What ran (smoke, seed 4000, both seat orders)

- 2/2 matches replay-verified (VERDICT PASS, engine digest matches current engine).
- Score: solver-harness 2 / 2 (naive 0) — but see the gate.
- **Solver move-source: 4 model / 5 fallback (all `fallback:rejected_model_answer`).**
- No timeouts and no backend errors anywhere (solver latencies 7.4–12.7 s and 7.9–18.4 s per move; B naive latencies similar). Every fallback was a parsed-but-rejected model answer.

## Failure mode (diagnosed with direct probes; artifacts in `probes/`)

The solver harness narrows the model's job to a candidate list and rejects any
answer not on that list. `llama3.2:3b` answers those prompts, at temperature 0,
with an invented "option 2" (or a wrong take value) roughly **1 move in 5**,
concentrated on two-heap positions where the list has exactly one entry. Those
answers parse fine but are not in the candidate list, so the harness records
`fallback:rejected_model_answer`.

Probe evidence (exact solver prompt, shared `parsing.py`, Ollama HTTP API — pure
transport, no content munging; scripts and outputs in `probes/`):

| probe | model / setup | on-list | parse-fail | off-list |
|---|---|---|---|---|
| `bw_probe3.py` batch 1 | llama3.2:3b, temp 0 | 20/24 | 0 | 4 |
| `bw_probe3.py` batch 1 | llama3.2:3b, default temp | 17/24 | 3 | 4 |
| `bw_probe4.py` batch 2 | llama3.2:3b, temp 0 | 18/24 | 0 | 6 |
| `bw_probe4.py` batch 2 | qwen2.5:7b, temp 0 | **24/24** | 0 | **0** |

Failed answers look like `"I'll choose option 2: take 1 from heap 0"` when the
list contains only one option. Temperature 0 removes parsing noise (ANSI
junk / rambling) entirely but leaves the invented-option behavior. Two further
transport variants tested and rejected: `--format json` returns `{  }` (the 3B
cannot fill a JSON schema through the CLI), and plain `ollama run` stdout is
polluted with ANSI erase sequences.

**Conclusion of diagnosis:** the fallbacks are intrinsic model behavior of
llama3.2:3b under this prompt contract, not fixable by timeouts (latency was
never the problem), backend spec, or transport changes. Expected fallback rate
for a full series: ~15–20% of solver moves. A fallback-free series with this
model is not achievable.

## Per-match table (smoke only)

| seed | seat 0 | winner | moves | replay-verified |
|---|---|---|---|---|
| 4000 (order 0) | solver-harness | solver-harness | 7 | yes (PASS) |
| 4000 (order 1) | naive-harness | solver-harness | 10 | yes (PASS) |

The smoke results are recorded as DIAGNOSTIC ONLY. They are **not** a series
result and must not be cited as one: the solver's win was materially assisted
by its own fallback on 5 of 9 moves.

## The one-paragraph honest conclusion

The cross-model series cannot be run as specified. The assigned small model
(llama3.2:3b) answers the narrowed prompts correctly only ~79–83% of the time
even at temperature 0; the rest of the time it names moves outside the
candidate list, and the solver harness — exactly as designed — falls back to
its own computed move. Any 16-match series would therefore contain
fallback-driven wins, which the quality gate (correctly) treats as a void
"model result". Notably, the failure mode is the experiment's thesis in
miniature: a 9 GB model (qwen2.5:7b) answered 24/24 of the same prompts
on-list, so a gate-clean cross-model series may be feasible with a different
A-side model. This run produces no claim about whether the harness or the model
decides; the "cross-model result not yet published" gap remains open. The
August 14 `matches/cheap-vs-expensive/` series remains the only "small beats
large" artifact, and it is known-dead (old-engine digests + fallback-driven).

## Proposed README section (operator-gated; README deliberately not edited)

> ### Cross-model series — blocked at the model-source quality gate (2026-08-29)
>
> The first attempt at the cross-model series (solver harness on
> `llama3.2:3b` vs naive harness on `qwen2.5:14b`, 8 seeds × 2 seat swaps)
> was stopped before full-series start: the smoke match showed 5 of 9
> solver moves carrying `fallback:rejected_model_answer`, violating the
> no-fallback gate. Direct probes under the exact narrowed prompt showed
> `llama3.2:3b` produces candidate-list-valid answers only ~79–83% of the
> time even at temperature 0 — it invents an "option 2" on short lists —
> while `qwen2.5:7b` scored 24/24 on identical prompts. No series result
> was committed and no model-based claim is made. The gap stands. A
> gate-clean series needs an A-side model that holds ~100% on-list
> compliance (qwen2.5:7b is the measured candidate), or an engine-side
> change to how fallbacks are counted. Publication of any future result is
> operator-gated.

## Commands actually run

```
python bin/run_series.py --game nim --a entrants/solver_harness.py --b entrants/naive_harness.py \
  --backend-a "cli:ollama run llama3.2:3b" --backend-b "cli:ollama run qwen2.5:14b" \
  --seeds 1 --start-seed 4000 --out matches/cross-model-20260829/smoke --timeout 120 --backend-timeout 300
python bin/verify_replay.py matches/cross-model-20260829/smoke/4000-0/dc9dbdb6f884c162.jsonl
python bin/verify_replay.py matches/cross-model-20260829/smoke/4000-1/06720d00c3da6c13.jsonl
python matches/cross-model-20260829/probes/bw_probe3.py   # 3b temp0 vs default, 24 positions
python matches/cross-model-20260829/probes/bw_probe4.py   # 3b batch2 + qwen2.5:7b comparison
```

## Artifacts committed under matches/cross-model-20260829/

- `smoke/4000-0/`, `smoke/4000-1/` — the two smoke transcripts (replay-verified PASS), kept as evidence
- `probes/` — probe scripts + raw outputs (3b temp0/default, 3b batch 2, 7b comparison, verify outputs)
- this report

Nothing else. No series transcript, no model result, no README change, no
changes to entrants/ or arena/.
