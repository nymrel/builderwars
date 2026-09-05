# Execution-model bakeoff

This lane supports issue #8 without turning BuilderWars into Nymrel's production
router or overstating what a receipt proves.

## Two separate comparisons

1. **Model-controlled:** run the same BuilderWars harness through OpenRouter with
   the exact model, provider allowlist, prompt, seed, timeout, and privacy policy.
   This isolates model/provider behavior.
2. **Whole-system:** run matched repository tasks through Cline + OpenRouter,
   native Codex + Luna, and optionally ZCode + GLM. This measures the combined
   model and coding-agent harness, which is the studio's real operating cost.

Do not combine these into one leaderboard. A result from one answers a different
question from a result in the other.

## Offline validation

```bash
python bin/check_openrouter_backend.py
python -m py_compile \
  entrants/openrouter_backend.py \
  entrants/openrouter_fantasy_harness.py \
  bin/run_agentwars_openrouter_match.py
```

No API key or network access is used by those checks. The registered PR workflow
runs the entrant checker on CPython 3.13 across Windows x64, Linux x64, Linux
ARM64, and macOS ARM64 when GitHub Actions instantiates the workflow.

## One controlled GLM match

First copy the exact provider slug from the current OpenRouter model endpoint
page. Do not guess it. Then, in an operator-owned shell:

```bash
export OPENROUTER_API_KEY='...'
python bin/run_agentwars_openrouter_match.py \
  --model z-ai/glm-5.3-flash \
  --provider EXACT_PROVIDER_SLUG \
  --seed 9300 \
  --out private-results/glm-5.3-flash/9300 \
  --json-out private-results/glm-5.3-flash/9300.json
```

The request enforces:

- an exact provider allowlist;
- provider fallbacks disabled;
- required request parameters;
- temperature fixed at zero;
- provider data collection denied;
- Zero Data Retention required.

If no endpoint satisfies those controls, the call must fail rather than silently
changing provider or privacy posture.

The sanitized receipt carries API-reported requested/resolved model, provider,
prompt/completion/total tokens, reasoning tokens, cache reads/writes, charged
cost, and upstream inference cost when present. It does not carry prompt or
completion text. These fields support accepted-task cost accounting but remain
provider/API claims rather than independent model attestation.

## Candidate matrix

Run the same seeds and settings for:

- `z-ai/glm-5.3-flash` — provisional default;
- the exact stable DeepSeek V4 Flash slug chosen before the run;
- `qwen/qwen3.8-flash` — canary challenger.

Use native Codex for the GPT-5.6 Luna whole-system control. A separate API-level
Luna run is optional and should not be presented as equivalent to native Codex.

## Spend and publication gates

- Existing authorized credits only; no refill, subscription, or billing change.
- Stop before a call when the balance/cap cannot be verified.
- Raw prompts, completions, account details, and provider receipts stay private.
- Publish only sanitized aggregates after independent review.
- Model and provider fields are API-reported claims. Replay proves the accepted
  moves and adjudication, not model identity or execution provenance.
