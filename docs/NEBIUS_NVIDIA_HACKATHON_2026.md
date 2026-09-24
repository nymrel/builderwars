# Nebius × NVIDIA Global AI Hackathon 2026 — execution brief

Tracking: nymrel/nymrel-swarm-studio#14

## Objective

Add one real, reproducible BuilderWars agent/evaluation path that runs on Nebius infrastructure and uses at least one NVIDIA open-source model, while keeping provider credentials and task bodies out of public proof receipts.

This branch is **not** evidence of Devpost registration, Nebius credits, provider access, a completed run, benchmark superiority, or submission.

## Why BuilderWars

BuilderWars already provides the right product frame:

- agents/harnesses compete under versioned rules;
- evaluations and games are replayable;
- evidence and result claims are kept separate;
- public receipts are scoped rather than universal model rankings.

The competition-specific delta should therefore be a real provider-backed execution lane, not a separate demo app.

## Proposed entry

**BuilderWars: Open Agent Proof Arena**

A bounded coding/agent challenge in which:

1. an entrant receives an exact versioned task;
2. at least one entrant is an NVIDIA open model served through Nebius;
3. the harness executes under fixed limits;
4. deterministic or independently checkable scoring is produced;
5. a proof packet captures rules, model/provider metadata, limits, outputs/digests, and replay status;
6. the UI exposes the receipt without inflating it into a universal leaderboard claim.

## Minimum build slice

### 1. Provider adapter

Add a Nebius adapter/config that:

- targets Nebius Token Factory or Nebius AI Cloud;
- references an exact supported NVIDIA open model;
- loads credentials only from environment/secret configuration;
- applies request timeout, output/token, cost/budget, retry, and concurrency bounds;
- sanitizes provider errors;
- never commits credentials.

### 2. One bounded task

Choose one task that is:

- meaningful for agentic coding/engineering;
- small enough to re-run;
- scored from deterministic artifacts or tests;
- license-safe;
- free of private customer data.

Avoid broad subjective “best agent” claims.

### 3. Receipt / replay integration

Record only the evidence needed for reproducibility:

- rules/task version;
- entrant/harness identifier;
- exact model identifier;
- provider = Nebius;
- resource limits;
- test/scoring digest;
- completion/failure reason;
- replay status.

Keep raw secrets and sensitive task contents out of public receipts.

### 4. Demo

Produce a short flow showing:

- task selection;
- real provider-backed run;
- result/scoring;
- replay/evidence inspection;
- a failed or bounded case.

## Optional Tavily prize

Do not add Tavily unless web search is genuinely required by the selected task. Prize stacking must not make the evaluation less reproducible.

## Evidence checklist

- [ ] exact NVIDIA model and license recorded;
- [ ] Nebius runtime call verified;
- [ ] provider adapter tests pass;
- [ ] timeout/retry/budget behavior tested;
- [ ] deterministic scoring/replay passes;
- [ ] no secrets in repository or receipts;
- [ ] at least one independent rerun matches the claimed scoring conditions;
- [ ] all public conclusions stay scoped to the exact task and run conditions;
- [ ] demo + architecture diagram + setup instructions exist.

## External gates

Devpost registration requires explicit user acceptance of the official rules/terms/eligibility statement and completion of the registration form. This branch does not satisfy or imply those agreements.
