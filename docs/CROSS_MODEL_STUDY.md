# AgentWars cross-model study

## Decision encoded

This is the registered study path for the sharper BuilderWars claim. It implements the selected design rather than revisiting it:

- a complete **2×2** matrix for each comparison: small/large model × structured/naive harness;
- matched game seeds and both seat orders for every one of the six treatment pairings;
- the original cross-family demonstration, **Llama 3.2 3B vs Qwen 2.5 14B**;
- a same-family control, **Qwen 2.5 3B vs Qwen 2.5 14B**;
- a **zero-fallback publication gate**: one fallback, backend error, missing source marker, missing receipt, replay failure, or infrastructure outcome holds the entire series.

The study does not authenticate model identity. The arena never contacts a model, so the backend name and execution class remain entrant-declared, hash-bound claims. A passing report may support a claim about the preregistered receipts; it may not claim independent provider attestation.

## Why the complete matrix matters

The four treatment cells are:

| | Naive harness | Structured harness |
|---|---|---|
| Small model | small + naive | small + structured |
| Large model | large + naive | large + structured |

The runner plays all six pairings among those four cells. That produces the direct held-factor contrasts needed to distinguish effects:

1. structured vs naive while the small model is held constant;
2. structured vs naive while the large model is held constant;
3. large vs small while the structured harness is held constant;
4. large vs small while the naive harness is held constant;
5. the headline corner: small + structured vs large + naive;
6. the opposite corner: large + structured vs small + naive.

Seat order is swapped for every seed. The report gives directional win rates and Wilson 95% intervals for each contrast. Its pooled “main effects” are descriptive summaries of the two held-factor contrasts, not a claim of population-level causal identification.

## Commands

Validate the preregistration without loading a model:

```bash
python bin/run_factorial_study.py --validate-plan
python bin/check_factorial_study.py
```

Run the non-publishable smoke profile first:

```bash
python bin/run_factorial_study.py \
  --profile smoke \
  --out matches/studies/agentwars-cross-model-v1-smoke
```

Run the fixed publication profile only after the smoke receipts have no infrastructure failures:

```bash
python bin/run_factorial_study.py \
  --profile publication \
  --out matches/studies/agentwars-cross-model-v1
```

The two comparisons may be executed separately into the same locked output directory:

```bash
python bin/run_factorial_study.py --profile publication \
  --comparison cross-family \
  --out matches/studies/agentwars-cross-model-v1

python bin/run_factorial_study.py --profile publication \
  --comparison same-family-qwen \
  --out matches/studies/agentwars-cross-model-v1
```

Re-verify and re-analyze existing receipts without calling a backend:

```bash
python bin/run_factorial_study.py --profile publication --analyze-only \
  --out matches/studies/agentwars-cross-model-v1
```

The output directory is locked to the exact plan digest and profile. An interrupted run is resumable: existing transcripts are replayed and inspected before missing fixtures are executed.

## Fail-closed outputs

Every invocation writes or refreshes:

- `study.lock.json`: exact plan digest and profile;
- `summary.json`: fixture-level receipt hashes, chain heads, source counts, contrasts, and every hold reason;
- `summary.md`: human-readable evidence report.

`publication-candidate.json` exists **only** when the publication profile is complete and every gate passes. A later hold removes any stale candidate automatically. The candidate pins every receipt by relative path, transcript SHA-256, and chain head.

The smoke profile can finish successfully, but its gate status is `NOT_PUBLISHABLE` and it never produces a publication candidate.

## Zero-fallback semantics

Every move must carry one structured source marker:

- `source=model` — the backend returned a response and the move was model-sourced;
- `source=fallback:...` — the structured harness substituted its own move; holds publication;
- `source=backend_error:...` — the naive harness received no backend response; holds publication;
- missing or unknown source — holds publication.

An illegal move can still be valid experimental evidence when it came from the model. `forfeit:illegal_move` is therefore allowlisted. Timeouts, protocol failures, referee errors, unfinished games, and other infrastructure outcomes are not.

## Claim boundary

A passing v1 result may be described as:

> In the preregistered AgentWars v1 Nim series, with matched seeds and swapped seats, the declared small-model/structured-harness treatment won X of Y replay-verified matches against the declared large-model/naive-harness treatment. Every recorded move was model-sourced under the zero-fallback gate. Model identity remained entrant-declared rather than independently attested.

Do not shorten that to “a 3B model is better than a 14B model.” The experiment is designed to measure the combined treatment and separate the observed harness and model contrasts inside this arena, not establish a universal model ranking.
