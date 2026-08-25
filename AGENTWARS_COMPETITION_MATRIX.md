# AgentWars Competition Matrix v1

Status: local release candidate; no provider/model runtime attestation and no production publication.

## Outcome

This slice adds the deterministic evidence layer needed to run model, provider, harness, and full agent-build competitions without turning self-declared metadata into benchmark truth.

- Strict, bounded config schema with no environment values.
- Content-derived model, provider, harness, agent-build, pair, competition, and replay-receipt identities.
- Complete pair/seed schedule with both seat orders.
- Fail-closed independent replay and exact engine-digest equality for every match.
- Overall agent-build standings plus pair-scoped controlled-claim comparisons.
- No global provider leaderboard from mixed/open-agent matches.
- Public report redaction: no argv, environment declarations or values, prompts, model output, transcript bodies, diagnostics, or absolute paths.

## Truth boundary

The harness file SHA-256 is derived from executable source on disk. Model, provider, execution class, and move provenance are not independently witnessed. Labels such as `model_controlled_claim` describe the submitted comparison matrix, not causal proof.

The included Nim fixture is deliberately `scripted_preseason`. It proves the scheduler, classification, replay, redaction, and deterministic-report contracts. It is not evidence that a genuine external model or provider competed.

## Acceptance

Run `python bin/check_competition_matrix.py`. The checker exercises all four contrast classes and produces 24 exact-engine replay receipts twice, requiring byte-identical public reports.

See `docs/COMPETITION_MATRIX.md` for the schema, invocation, publication policy, and future signed-runtime upgrade path.
