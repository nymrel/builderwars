# AgentWars provider-policy hardening packet

Status: implementation candidate; not integrated, deployed, or public proof.

Base commit: `ae7141aa1da454c17e5236a4ef313e61c44d43f0`

Branch: `codex/agentwars-provider-policy-hardening-20260825`

Current claim: `codex-agentwars-provider-policy-hardening-v3-20260825`

Superseded Ox execution claim: `codex-agentwars-provider-policy-hardening-ox-20260825`

## Objective

Turn the existing customer-owned provider hub into a fail-closed beta contract.
Separate model provider, account/billing route, agent harness, and execution
boundary. Keep provider credentials under customer custody. Prevent a hosted
arena from silently invoking local CLIs or arbitrary commands. Replace broad
child-environment inheritance with a minimal non-secret allowlist.

## Current official-source findings (verified 2026-08-25)

1. OpenAI documents `codex login` with ChatGPT for subscription access in the
   official local Codex clients. API-key access is separately billed. OpenAI
   also says not to expose Codex execution in untrusted or public environments.
   Plugin OAuth is the inverse flow (ChatGPT/Codex authenticating to a plugin's
   MCP server), not a general third-party `Sign in with ChatGPT` inference API.
2. Anthropic documents Claude Code browser login for eligible Claude plans, but
   says Claude subscriptions and API usage are separate products. OpenCode's
   current provider documentation says Anthropic prohibits third-party Claude
   subscription plugins. The only subscription-intent Claude adapter in this
   candidate is therefore Anthropic's official local `claude` CLI. Hermes
   consumer-subscription routes are separately disabled pending explicit
   provider authorization; that is product policy, not an Anthropic-specific
   Hermes prohibition claim.
3. OpenRouter documents a public OAuth-style PKCE S256 flow that returns a
   user-controlled API key. It is the only currently researched provider here
   with an explicit third-party web connection flow. Secure hosted key custody,
   rotation, deletion, and durable replay defense are not implemented in this
   repository, so this candidate keeps the key in the customer runner.
4. OpenCode is a harness and provider router. Its provider documentation names
   its own Go/Zen access, API-key routes, ChatGPT access, local models, and many
   other upstreams. A selected route does not itself attest model identity,
   subscription entitlement, billing, or provider permission.
5. Hermes Agent is also a local harness/router. It supports API providers,
   local models, and multiple OAuth paths. Its upstream route must be evaluated
   separately; a Hermes label never proves a provider subscription or model.

Primary references:

- https://learn.chatgpt.com/docs/auth
- https://developers.openai.com/plugins/build/auth
- https://platform.openai.com/docs/quickstart/make-your-first-api-request
- https://docs.anthropic.com/en/docs/claude-code/getting-started
- https://support.anthropic.com/en/articles/9876003-i-subscribe-to-a-paid-claude-ai-plan-why-do-i-have-to-pay-separately-for-api-usage-on-console
- https://openrouter.ai/docs/guides/overview/auth/oauth
- https://opencode.ai/docs/providers/
- https://hermes-agent.nousresearch.com/docs/integrations/providers

## Owned paths

- `entrants/backends.py`
- `entrants/fantasy_model_harness.py`
- `entrants/naive_harness.py`
- `entrants/solver_harness.py`
- `entrants/ten_fronts_model_harness.py`
- `provider_hub/catalog.py`
- `bin/buildwars_provider.py`
- `bin/check_provider_hub.py`
- `bin/run_agentwars_ox_match.py`
- `bin/run_match.py`
- `bin/run_series.py`
- `docs/PROVIDER_CONNECTIONS.md`
- `docs/ECONOMICS.md`
- `docs/AGENTWARS_PROVIDER_POLICY.md`
- `docs/AGENTWARS_PROVIDER_POLICY.v1.json`
- `AGENTWARS_PROVIDER_HUB_RELEASE.md`
- `README.md`
- `template/README.md`
- `template/entrant.toml`
- this packet

## Required changes

1. Add machine-readable provider-policy fields for provider class, harness
   class, local status, hosted status, custody, prohibited routes, evidence
   date, and official sources. Unknown fields/routes fail closed.
2. Model ChatGPT/Codex and Claude Code subscription access as official local
   client delegation only. Model OpenCode and Hermes as route-dependent
   harnesses. Disable the OpenCode Claude subscription plugin route based on
   OpenCode's current explicit warning. Independently disable consumer-
   subscription routing through Hermes pending explicit provider authorization.
3. Keep OpenRouter's current adapter customer-local even though the provider's
   PKCE flow supports third-party apps. Label hosted PKCE as architecturally
   supported but not implemented in this candidate.
4. Require an explicit, call-scoped `customer_local_v1` runtime intent
   capability before any provider adapter or non-stub legacy backend can be
   constructed through the supported factories. State plainly that this
   capability is not an OS isolation boundary; do not store ambient process
   authorization.
5. Require a second explicit opt-in for `custom_agent`; default construction
   must fail before subprocess resolution.
6. Replace `dict(os.environ)` in provider child execution with a bounded
   allowlist of OS/runtime path and locale variables. Do not inherit API keys,
   tokens, cloud credentials, proxy credentials, or arbitrary host variables.
   Validate process-local extra environment keys and values.
7. Keep raw child stderr, provider response bodies, credentials, absolute auth
   paths, and account identifiers out of public errors and catalog output.
8. Publish a human policy and exact JSON twin; the checker must reject drift.

## Done when

- Existing provider-hub checker passes with new hostile cases.
- A hostile host environment containing unrelated secret variables does not
  reach Codex, Claude, OpenCode, or Hermes child environments.
- Provider and legacy non-stub factory paths fail without the exact
  `customer_local_v1` capability.
- `custom_agent` additionally fails without its explicit unsafe-local opt-in.
- Catalog and JSON policy agree exactly on every route decision.
- Existing verifier/selfcheck/fantasy/scale/share/product regressions pass.
- `py_compile`, `git diff --check`, and an independent property probe pass.
- No live provider login, browser flow, API call, secret read, account change,
  push, merge, deploy, or public-launch claim occurs.

## Non-goals and stops

- Do not implement a hosted secret vault or a public arbitrary-code runner.
- Do not read or copy Codex, Claude, OpenCode, Hermes, or browser credentials.
- Do not claim an OAuth callback proves the model/provider that answered.
- Stop if the exact claim is lost, source scope expands, a test exposes a
  production semantic regression, or any provider fact cannot be sourced.
- Ox Alpha may edit only the owned paths and may not mutate Git custody.

## Ox Alpha MAX adversarial review mode

When the guarded runner grants read authority, review the current candidate
commit and its diff from the recorded base only. Do not edit files, stage
content, commit, switch branches, install software, start a server, launch a
browser, access credentials, or make a live provider call.

Return prioritized, evidence-backed findings with exact file and line anchors.
Attempt to refute all of these claims:

1. Missing or forged runtime-intent objects fail before subprocess resolution,
   and consent cannot linger as ambient process state.
2. Every shared `get_backend` caller either stays stub-only or accepts and
   forwards the explicit intent flag.
3. The child environment cannot inherit API keys, tokens, cloud credentials,
   proxy credentials, loader hooks, or arbitrary host variables, while official
   local clients can still locate their executable and local auth state.
4. `custom_agent` requires both intents and is never described as safely hosted.
5. OpenCode and Hermes remain harnesses rather than provider/model/billing
   attestations. The OpenCode Claude warning and the separate Hermes product
   policy are not conflated.
6. Catalog, CLI JSON, human policy, and JSON policy twin cannot silently drift.
7. No user-facing invocation path or existing regression is broken by the new
   flag contract.

If no release-blocking finding survives, say so explicitly and list residual
risks rather than inventing approval, integration, deployment, or live-account
evidence.
