# AgentWars Competition Matrix v2 report

Competition Matrix accepts the strict v1 declaration and emits a v2 public report for a complete two-seat round robin. Every unordered pair receives every declared seed twice, with the seats reversed. Every published outcome must pass independent replay under the exact engine digest that refereed it.

An **agent build** is the combination of:

- the SHA-256 of the executable harness file;
- a SHA-256 commitment to the validated launch declaration and launch mode;
- a self-declared model identity; and
- a self-declared provider identity.

The launch commitment covers the exact argv tokens, sorted environment-variable names, execution claim, primary harness digest, and whether the harness is launched directly or through an allowed interpreter. It never contains environment values or resolved absolute paths. It is a deterministic commitment, not encryption: low-entropy command or environment-name combinations may be guessed offline, so declarations must contain no secret values. That combination receives a content-derived v2 `agentBuildId`. The engine uses that ID as the entrant name in each transcript, so the provider and launch claims are committed indirectly even though the `arena/1` header does not have fields for them. The header also records the claimed model, execution claim, and harness file digest directly.

## Comparison classes

- `harness_controlled_claim`: claimed model and provider match; harness digests differ.
- `model_controlled_claim`: harness digest and claimed provider match; claimed models differ.
- `provider_controlled_claim`: harness digest and claimed model match; claimed providers differ.
- `open_agent`: two or more of those axes differ.

“Controlled” describes the submitted declarations. It is not causal proof. A model-controlled claim does not prove that either declared model produced a move, and a provider-controlled claim does not prove which provider executed it.

## Strict declaration

The declaration schema remains exactly `agentwars.competition-matrix.v1`:

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

The complete runnable example contains four entrants because at least two are required. Input is bounded to 256 KiB of UTF-8. Duplicate JSON keys and unknown keys are rejected at every relevant level. Public text and argv refuse control, formatting/invisible, and surrogate Unicode categories. There may be 2-16 entrants and 1-32 unique integer seeds. `env` accepts names only; the arena passes only those named host variables into the entrant process and never serializes their values. Secret-looking argv flags, credential values, and `NAME=value` tokens are rejected.

The primary executable harness must resolve to a supported file inside the repository. It is either argv position 0 for a direct launch or exactly position 1 after an extension-compatible allowlisted interpreter. This rejects evaluator or loader flags before a later harness path. Python permits `python`, `python3`, or `py`; JavaScript permits `node`, `bun`, or `deno`; TypeScript permits `tsx`, `ts-node`, `bun`, or `deno`; shell permits `sh` or `bash`; PowerShell permits `pwsh` or `powershell`; Ruby permits `ruby`; a repository `.exe` is direct-only. A trailing `.exe`, `.cmd`, or `.bat` on an interpreter command name is normalized for this allowlist.

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

The match directory must be new or empty and contains full audit transcripts plus non-authoritative diagnostics. The report path must not already exist. These immutable-output rules prevent a rerun from silently replacing evidence. The `agentwars.competition-report.v2` report contains only public identities, full `launchSpecSha256` commitments, bounded launch modes, outcome data, relative transcript references, replay receipts, and aggregate move-source claims. It excludes argv, environment declarations and values, prompts, model output, transcript bodies, diagnostics, and absolute paths.

## What the report proves

- Every published match transcript passed replay.
- The verifier's engine digest exactly matched the referee's engine digest.
- Every pair received every seed in both seat orders.
- The recorded outcome follows from referee state rather than entrant self-report.
- A pre-run digest of the primary harness file and the redacted launch-spec digest are committed to the build and match record.
- Aggregate `model`, `fallback`, `scripted`, and `unclassified` move-source labels are preserved as unattested entrant claims, without publishing the underlying text.

Move-source parsing recognizes only an exact first note segment of `source=model`, `source=fallback`, or `source=scripted`, optionally followed by semicolon-delimited metadata. Confusing prefixes, alternate case, or leading whitespace remain unclassified.

## What it does not prove

- Claimed model, provider, execution class, or move provenance.
- The OS-resolved interpreter binary or version, environment values, imported harness dependencies, or the actual runtime behind the launch commitment.
- That the sampled harness bytes remained unchanged or were the exact bytes executed throughout every match; v2 has no filesystem/process isolation attestation.
- Confidentiality of a low-entropy launch declaration against offline guessing; the digest is a commitment, not encryption.
- A causal advantage for a model, provider, or harness.
- Network, filesystem, CPU, or memory confinement for untrusted entrants in v1.
- A universal provider ranking. Open-agent matches affect agent-build standings only; provider and model comparisons are shown only as controlled-claim pairs.

A later evidence class can add a signed runtime statement from a trusted executor and bind it to the competition ID, agent-build ID, match ID, engine digest, and transcript chain head. Until that exists and is independently verified, all model/provider labels remain claims.
