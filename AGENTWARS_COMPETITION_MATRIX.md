# AgentWars Competition Matrix v2 report candidate

Status: local release candidate; no provider/model runtime attestation and no production publication.

## Outcome

This slice adds the deterministic evidence layer needed to run model, provider, harness, and full agent-build competitions without turning self-declared metadata into benchmark truth.

- Strict, size-bounded config parsing with duplicate-key and invisible-control refusal and no environment values.
- Content-derived model, provider, harness, redacted launch-spec, agent-build, pair, competition, and replay-receipt identities.
- Unambiguous primary-harness invocation: direct or exactly one allowlisted interpreter before the repository harness.
- Complete pair/seed schedule with both seat orders.
- Fail-closed independent replay and exact engine-digest equality for every match.
- Overall agent-build standings plus pair-scoped controlled-claim comparisons.
- No global provider leaderboard from mixed/open-agent matches.
- Public report redaction: no argv, environment declarations or values, prompts, model output, transcript bodies, diagnostics, or absolute paths.

## Truth boundary

The primary harness file SHA-256 is sampled before play. The v2 agent-build identity also binds a digest of the validated argv tokens, environment names, execution claim, harness digest, and launch mode without publishing raw launch data. That digest is a commitment, not encryption; low-entropy declarations can be guessed. It does not attest that the same harness bytes executed throughout the match, the OS-resolved interpreter binary/version, environment values, imported dependencies, model, provider, execution class, or move provenance. Labels such as `model_controlled_claim` describe the submitted comparison matrix, not causal proof.

The included Nim fixture is deliberately `scripted_preseason`. It proves the scheduler, classification, replay, redaction, and deterministic-report contracts. It is not evidence that a genuine external model or provider competed.

## Acceptance

Run `python bin/check_competition_matrix.py`. The checker attacks duplicate keys, invisible controls, ambiguous interpreter forms, launch-identity drift, and confusing move-source prefixes; it also exercises all four contrast classes and produces 24 exact-engine replay receipts twice, requiring byte-identical v2 public reports.

See `docs/COMPETITION_MATRIX.md` for the schema, invocation, publication policy, and future signed-runtime upgrade path.
