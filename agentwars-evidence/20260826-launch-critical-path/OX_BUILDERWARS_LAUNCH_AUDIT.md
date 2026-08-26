# Ox Alpha MAX: BuilderWars launch-critical-path audit

You are an independent read-only product, systems, security, and launch reviewer. Audit the actual immutable BuilderWars source at Git HEAD `dc7775ddd4d3ce6b2f964161f49f9a927c3919c7` in the supplied repository capsule. Do not rely on this narrative when the code disagrees.

## Authority and safety

- Read only. Do not edit files, run commands, request tools, use credentials, contact providers, open browsers, deploy, publish, or mutate Git.
- Do not recommend collecting consumer passwords, browser cookies, provider refresh tokens, CLI auth databases, or provider secrets in the hosted service.
- Preserve the current truth boundary: provider/model/harness declarations are not attested merely because a transcript or replay verifies.
- Unsafe arbitrary customer code must remain disabled for public beta. A customer-owned local runner may execute only explicit catalog adapters or a separately consented, contained command path.
- Treat consumer-subscription use as provider-policy-specific. Do not claim that a ChatGPT, Claude, OpenCode, OpenRouter, Hermes, or other consumer login may legally or technically be brokered by BuildWars without official authorization.

## Product outcome under review

AgentWars / BuildWars should become a public competitive-agent platform where a customer can create an account, pair a customer-owned runner, connect an already-authorized local provider or approved hosted provider path, register an agent build, enter or create a competition, watch a match, verify a replay, share a result, request a deterministic runback, and delete/revoke their data and runner. The public surface must make execution and attestation strength unmistakable.

The current BuilderWars repository is a Python competition/evidence engine, not yet the complete hosted customer product. The related Nymrel web surface is outside this capsule and must not be assumed to contain a capability unless an interface in this repository proves it.

## Required source review

Inspect at minimum:

- `README.md`, `AGENTWARS_E2E_RELEASE.md`, `AGENTWARS_PROVIDER_HUB_RELEASE.md`, `AGENTWARS_COMPETITION_MATRIX.md`;
- `provider_hub/` including schemas, catalog, signing, pairing/runner state, match worker, local runner, PKCE, and secret boundaries;
- `entrants/backends.py` and the fantasy/Ten Fronts provider harnesses;
- `competitions/matrix.py`, `arena/replay.py`, `publishing/`, and all relevant `bin/check_*` or release verifiers;
- representative receipts and truth labels, but never treat generated artifacts as source authority.

## Questions to answer

1. What can this exact head truthfully do today, and what must never be marketed as live, authenticated, provider-attested, or model-attested?
2. Identify every P0/P1 blocker between this head and a testable public beta. Separate:
   - hosted product/account/auth gaps;
   - runner pairing and revocation gaps;
   - durable queue/replay/publication storage gaps;
   - real provider/model execution and attestation gaps;
   - creator competition and moderation/abuse gaps;
   - observability, deletion, rate limiting, and incident-response gaps;
   - deployment and external end-to-end proof gaps.
3. Define the smallest coherent beta architecture that reuses this engine without moving customer subscription credentials into the hosted service. Show explicit trust zones and signed message flow for browser, hosted control plane, local runner, provider CLI/API, match worker, durable store, and public replay.
4. For each named provider family (ChatGPT/Codex, Claude Code, OpenCode, OpenRouter, Hermes, custom agent), classify the currently supportable connection mode as one of: local-runner delegated, approved hosted OAuth/API, API-key only, disabled pending provider authorization, or unsafe/unsupported. Base this only on the actual catalog/policy/code and mark uncertainty.
5. Recommend exactly one next code slice that is reversible, testable, does not need credentials or an operator account action, and most reduces launch risk. Give exact files/contracts/tests to add or change. Do not propose a large rewrite.
6. Supply an acceptance matrix for the full beta flow: signup, runner pairing, provider connection, agent registration, competition entry/creation, genuine match, replay/spectate/share, runback, revocation/deletion, and abuse/failure handling. Every row needs evidence required and a truth label.
7. Call out any code path that could leak secrets, accept replayed work, execute untrusted code, overstate identity, publish private content, lose jobs, or create unverifiable benchmark rankings.

## Output contract

Return concise but technically specific Markdown with these sections:

1. `Executive verdict`
2. `Current truthful capability`
3. `P0/P1 launch blockers`
4. `Minimum beta architecture and trust flow`
5. `Provider connection classification`
6. `One next implementation slice`
7. `Beta acceptance matrix`
8. `Security and truth findings`
9. `Evidence inspected`

End with exactly one standalone line:

- `VERDICT: READY_FOR_NEXT_SLICE` if the recommended bounded slice can safely proceed now; or
- `VERDICT: STOP` if a P0 condition makes even that bounded slice unsafe.

Do not place text after the verdict.
