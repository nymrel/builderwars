# AgentWars Competition Matrix identity hardening

Status: bounded release-candidate packet

Owner: Codex integration lane for Jalen

Ox route: `opencode-go/ox-alpha-free`, MAX effort, no fallback

Base commit: `04a7b7417b3307bd2cb85bbdb782a7d7d0b3d9c2`

Branch: `codex/agentwars-competition-matrix-hardening-20260825`

Claim: `codex-agentwars-competition-matrix-hardening-ox-20260825`

North Star gate: improve replayable, truth-safe competition identity; do not claim live WVRB, model quality, or provider dominance.

[Objective]

Turn the Competition Matrix's public `agentBuildId` into an honest commitment to the submitted launch declaration as well as the primary harness file, and remove parser/provenance ambiguities that could let different executions look equivalent.

This remains a local, unattested competition candidate. It does not authorize untrusted public code execution or prove that a claimed model/provider produced a move.

[Scope]

- Ox may inspect the repository broadly and run focused or full local validation.
- Ox may edit only `competitions/matrix.py`, `bin/check_competition_matrix.py`, `docs/COMPETITION_MATRIX.md`, and `AGENTWARS_COMPETITION_MATRIX.md`.
- This packet, `docs/AGENTWARS_COMPETITION_MATRIX_HARDENING_PACKET.md`, is immutable input and must not be edited by Ox.

[Required implementation]

1. Config parsing
   - Read at most 256 KiB of UTF-8 config input.
   - Reject duplicate JSON object keys at every nesting level with `CompetitionConfigError`.
   - Do not echo config values or raw parser payloads in public errors.

2. Text and argv ambiguity
   - After existing normalization, reject Unicode categories `Cc`, `Cf`, and `Cs` in public text fields.
   - Reject those control/invisible categories in every argv token as well.
   - Preserve visible Unicode and the current NFKC/casefold comparison behavior.

3. Primary harness invocation
   - Accept a repository-owned supported harness directly at argv position 0; or accept a supported interpreter at position 0 with the repository-owned harness exactly at position 1.
   - Normalize the interpreter basename by casefolding and removing a trailing `.exe`, `.cmd`, or `.bat`.
   - Permit only an explicit extension-to-interpreter mapping: Python (`python`, `python3`, `py`), JavaScript/MJS (`node`, `bun`, `deno`), TypeScript (`tsx`, `ts-node`, `bun`, `deno`), shell (`sh`, `bash`), PowerShell (`pwsh`, `powershell`), and Ruby (`ruby`). A repository `.exe` is direct-only.
   - Reject evaluator/loader flags before the harness, arbitrary interpreters, ambiguous later-file discovery, and harness files outside `repo_root` before any match output is created.

4. Launch-spec commitment
   - Derive a lowercase 64-hex `launchSpecSha256` from a canonical object containing a versioned schema, the normalized declared argv array, sorted env names, execution claim, primary harness SHA-256, and launch mode.
   - Do not include environment values or resolved absolute paths.
   - Build `agentBuildId` under a new versioned identity schema from `launchSpecSha256`, harness SHA-256, normalized model claim, and normalized provider claim.
   - Publish `launchSpecSha256` and the bounded launch mode for each entrant, never raw argv or env names/values.
   - Bump the public competition report schema because its entrant contract changes; keep the declaration schema at `agentwars.competition-matrix.v1` unless a config field changes.

5. Move-source claim parsing
   - Recognize only an exact first note segment `source=model`, `source=fallback`, or `source=scripted`, optionally followed by `;...` metadata.
   - Values such as `source=model-not-really`, leading whitespace, alternate case, or unrelated prose must remain `unclassified`.

6. Truth documentation
   - Explain exactly what launch commitment is bound and what remains unattested: interpreter binary/version, environment values, imported dependencies, provider/model identity, execution provenance, isolation, and causal comparisons.
   - Keep status `scripted_preseason` for the included fixture.

[Done when]

- Duplicate top-level and nested keys fail through `CompetitionConfigError`.
- Oversized or non-UTF-8 config input fails closed without echoing content.
- Zero-width and bidi-format controls fail in public fields and argv.
- `python -c ... harness.py`, `python -u harness.py`, an arbitrary interpreter, and a harness outside the repo fail before output creation.
- Changing only one argv token changes `launchSpecSha256` and `agentBuildId` while the primary `harnessSha256` stays stable.
- The public report includes full launch commitment digests and contains no raw argv, env names/values, secret fixture, prompt/model output, diagnostics, or absolute path.
- Exact and `;`-extended source labels count correctly; confusing prefixes remain unclassified.
- Two complete fixture runs still yield byte-identical reports and 24/24 exact-engine replay receipts each.
- Only the five claimed paths differ, including this already-authored packet.

[Validation]

Run from the standalone lane root:

- `python bin/check_competition_matrix.py`
- `python bin/build_verifier.py --check`
- `python bin/selfcheck.py`
- `python bin/check_fantasy_games.py`
- `python bin/check_agentwars_scale.py`
- `python bin/check_share_bundle.py`
- `python bin/check_agentwars_product.py`
- `python -m py_compile competitions/matrix.py bin/check_competition_matrix.py`
- `git diff --check`
- `git status --short`

Return exact commands, outcomes, changed paths, schema versions, and any residual truth limitation. Codex will independently inspect and rerun all gates.

[Non-goals]

- Do not execute a real external provider, collect credentials, alter entrant backends, add sandbox claims, or enable public arbitrary harness execution.
- Do not change the arena engine, standalone verifier, generated snapshots, example config, dependencies, lockfiles, publishing artifacts, UI, accounts, or deployment.
- Do not publish global provider/model rankings or upgrade claim labels into attestation.
- Do not commit, push, merge, deploy, stage files, alter Git custody, create branches, or edit outside the claim.

[Stop conditions]

- Stop and report if a required fix needs any unclaimed path, a config schema change, generated verifier output, dependency change, or production/public action.
- Stop and report on any claim-scope or Git-custody violation, connector attestation failure, base/branch mismatch, or regression that cannot be corrected inside the exact paths.
- Stop rather than weakening identity binding, redaction, replay verification, output immutability, or the `scripted_preseason` truth label.

[Mandatory evidence]

- `competitions/matrix.py`
- `bin/check_competition_matrix.py`
- `docs/COMPETITION_MATRIX.md`
- `AGENTWARS_COMPETITION_MATRIX.md`
