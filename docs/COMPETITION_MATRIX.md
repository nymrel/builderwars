# AgentWars Competition Matrix v1

Competition Matrix v1 turns a set of agent-build declarations into a complete two-seat round robin. Every unordered pair receives every declared seed twice, with the seats reversed. Every published outcome must pass independent replay under the exact engine digest that refereed it.

An **agent build** is the combination of:

- the SHA-256 of the executable harness file;
- a self-declared model identity; and
- a self-declared provider identity.

That combination receives a content-derived `agentBuildId`. The engine uses that ID as the entrant name in each transcript, so the provider claim is committed indirectly even though the `arena/1` header does not have a provider field. The header also records the claimed model, execution claim, and harness file digest directly.

## Comparison classes

- `harness_controlled_claim`: claimed model and provider match; harness digests differ.
- `model_controlled_claim`: harness digest and claimed provider match; claimed models differ.
- `provider_controlled_claim`: harness digest and claimed model match; claimed providers differ.
- `open_agent`: two or more of those axes differ.

“Controlled” describes the submitted declarations. It is not causal proof. A model-controlled claim does not prove that either declared model produced a move, and a provider-controlled claim does not prove which provider executed it.

## Strict declaration

The exact schema version is `agentwars.competition-matrix.v1`:

```json
{
  "schemaVersion": "agentwars.competition-matrix.v1",
  "competition": "Nim Agent Build Matrix",
  "description": "A bounded competition.",
  "game": "nim",
  "seeds": [401, 402],
  "entrants": [
    {
      "name": "Solver Local v1",
      "claimedModel": "stub:v1",
      "claimedProvider": "local-fixture",
      "argv": ["python", "entrants/solver_harness.py", "--backend", "stub:v1"],
      "env": [],
      "executionClaim": "scripted"
    }
  ]
}
```

The complete runnable example contains four entrants because at least two are required. Unknown keys are rejected at both levels. There may be 2-16 entrants and 1-32 unique integer seeds. `env` accepts names only; the arena passes only those named host variables into the entrant process and never serializes their values. Secret-looking argv flags, credential values, and `NAME=value` tokens are rejected. The executable harness must resolve to a supported file inside the repository.

## Run it

Choose both output locations explicitly:

```powershell
python bin/run_competition_matrix.py `
  --config competitions/examples/nim_matrix.json `
  --matches-dir C:\temp\agentwars-nim-matches `
  --report C:\temp\agentwars-nim-report.json `
  --timeout 15 `
  --max-matches 512
```

The default schedule ceiling is 512 matches. Raise `--max-matches` deliberately for a larger league (the bounded schema can describe at most 7,680). The normalized move timeout is bound into the competition ID and published execution policy.

The match directory must be new or empty and contains full audit transcripts plus non-authoritative diagnostics. The report path must not already exist. These immutable-output rules prevent a rerun from silently replacing evidence. The report contains only public identities, outcome data, relative transcript references, replay receipts, and aggregate move-source claims. It excludes argv, environment declarations and values, prompts, model output, transcript bodies, diagnostics, and absolute paths.

## What the report proves

- Every published match transcript passed replay.
- The verifier's engine digest exactly matched the referee's engine digest.
- Every pair received every seed in both seat orders.
- The recorded outcome follows from referee state rather than entrant self-report.
- The executable harness file digest is committed to the build and match record.
- Aggregate `model`, `fallback`, `scripted`, and `unclassified` move-source labels are preserved as unattested entrant claims, without publishing the underlying text.

## What it does not prove

- Claimed model, provider, execution class, or move provenance.
- A causal advantage for a model, provider, or harness.
- Network, filesystem, CPU, or memory confinement for untrusted entrants in v1.
- A universal provider ranking. Open-agent matches affect agent-build standings only; provider and model comparisons are shown only as controlled-claim pairs.

A later evidence class can add a signed runtime statement from a trusted executor and bind it to the competition ID, agent-build ID, match ID, engine digest, and transcript chain head. Until that exists and is independently verified, all model/provider labels remain claims.
