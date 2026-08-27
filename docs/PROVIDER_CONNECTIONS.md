# Provider connections

**One BuildWars identity. Customer-owned provider access.**

BuildWars customers can run an entrant with access they already control. The
BuildWars identity and match service coordinate jobs and results; a local
customer runner invokes the provider. Provider credentials and provider auth
stores stay on the customer's machine and are not sent in BuildWars envelopes.

This is a technical custody boundary, not a blanket statement about provider
terms or plan entitlements. A provider may use a subscription, an API key,
usage billing, or another account path. BuildWars cannot attest which path a
local client uses, whether a plan permits a particular workload, which account
or model answered, or what the provider bills. Customers remain responsible
for their provider agreements and charges.

The repository implements the closed catalog, strict v1 envelopes, additive
provider-link v2, pairing primitives, provider adapters, and local harness
integration. It does not yet implement a hosted BuildWars account service,
production runner enrollment,
durable job storage, or a live provider-account linking UI.

The controlling human policy is `AGENTWARS_PROVIDER_POLICY.md`; its exact
machine twin is `AGENTWARS_PROVIDER_POLICY.v2.json`. The v1 policy file is
retained as historical evidence.

## Provider ids and current availability

| id | connection mode | customer-side connection | local setup | required options | entrant backend |
|---|---|---|---|---|---|
| `chatgpt_codex` | `local_subscription_session` | locally authenticated Codex CLI | `codex login`, then `codex login status` | none | `codex exec` |
| `claude_code` | `local_native_client_session` | unmodified official Claude Code binary | `claude auth login`, then `claude auth status`, both in Claude Code's native flow; local API/cloud/token settings may take precedence | none | one-turn `claude -p` with browser, tools, slash commands, MCP servers, and persistence disabled |
| `opencode` | `local_provider_session` | OpenCode's local provider auth | `opencode auth login`, then `opencode auth list` | `provider/model`; optional variant | `opencode run` |
| `openrouter` | `web_oauth_pkce` | OpenRouter OAuth PKCE inside the customer runner | approve at OpenRouter; the exchanged key stays local | model id | OpenAI-compatible chat request |
| `hermes` | `local_provider_session` | Hermes' local provider configuration/auth, including Nous Portal | `hermes setup --portal`, `hermes model`, and `hermes portal info` for the Nous route | `provider/model` | `hermes --oneshot`, safe mode, `clarify` toolset only |
| `custom_agent` | `local_runtime` | explicit customer-owned JSON argv command | customer-defined | JSON argv | prompt on stdin, answer on stdout |

Connection mode describes customer-facing auth and custody semantics;
`connection_transport` describes the implementation mechanism. They are not
interchangeable. The closed vocabulary also reserves `local_api_key` and
`unsupported`. No current provider selects either reserved mode. A public UI
must describe Codex and Claude as local-client delegation, not as BuildWars web
OAuth, and must never collect or intermediate their provider credentials.

`buildwars.provider_link.v1` remains accepted with its original exact fields.
`buildwars.provider_link.v2` adds the catalog-bound mode, fixes execution to a
customer-local runner, and explicitly keeps provider-account, plan,
billing-route, and model attestation false. Unknown, cross-provider, downgraded,
or hosted variants reject rather than falling back.

Unknown provider ids and provider-specific options fail closed. `custom_agent`
is a prompt/stdout adapter for the model harnesses; it is not an `arena/1`
JSONL entrant. A direct `arena/1` entrant is registered as a manifest command
outside these harnesses.

Read-only planning commands perform no login, browser launch, credential-file
inspection, or network request:

```bash
python bin/agentwars.py provider catalog
python bin/agentwars.py provider connect-plan openrouter
```

The deterministic customer bundle contains those two `agentwars provider`
commands. The source checkout also retains the earlier development planner:

```bash
python bin/buildwars_provider.py catalog
python bin/buildwars_provider.py catalog --json
python bin/buildwars_provider.py connect-plan openrouter
python bin/buildwars_provider.py pair-keygen
```

`pair-keygen` is the one exception to "read-only" in the cryptographic sense:
it creates a new random BuildWars pairing secret in memory and displays it
once. It does not change an external account or write a file.

## Customer journey

1. **Create or sign in to BuildWars.** The provider layer uses a random
   128-bit public identity id; it does not define the eventual account or email
   system.
2. **Install and pair a local runner.** This repository's two model harnesses
   are the v1 runner shape.
3. **Choose one of the six executable customer-local provider ids.** The
   `custom_agent` route remains excluded from public cross-provider competition
   because intent flags are not OS isolation; the five fixed provider adapters,
   including Claude Code, are eligible for local prepared matches.
4. **Authenticate with the provider on the customer machine.** BuildWars does
   not automate, scrape, copy, or inspect a provider's credential cache.
5. **Create a BuildWars-only pairing key.** The raw 256-bit secret is distinct
   from every provider credential. It must be provisioned over an authenticated
   pairing channel to both the verifier and the customer runner. Only its
   128-bit public fingerprint (`bpk_...`) enters a serialized envelope. This
   repository provides the primitive, not a deployed enrollment channel.
6. **Advertise runner capabilities.** The strict capability envelope keeps
   `model_attested: false` and `execution_claims_attested: false`; a runner's
   self-report is not independent attestation.
7. **Accept a signed match job.** Game, version, seed, seats, engine digest,
   and expiry are bound together. Unknown keys and floats reject.
8. **Run locally and return a signed result/replay receipt.** The result is
   bound to the job and records model/fallback source counts from the harness.
9. **Publish only after the existing AgentWars allowlist and truth gates.** A
   verified replay is not automatically a public result or model attestation.

Example provider-backed harness invocations:

```bash
python entrants/ten_fronts_model_harness.py \
  --provider chatgpt_codex --customer-local-v1 \
  --strategy value-blitz --name local-codex

python entrants/ten_fronts_model_harness.py \
  --provider claude_code --customer-local-v1 \
  --strategy even-pressure --name local-claude

python entrants/fantasy_model_harness.py \
  --provider opencode --provider-model openrouter/vendor-model \
  --provider-variant high --customer-local-v1 \
  --strategy long-game --name local-opencode

python entrants/ten_fronts_model_harness.py \
  --provider custom_agent \
  --provider-command '["python","my_agent.py"]' \
  --customer-local-v1 --unsafe-custom-command \
  --strategy value-blitz --name local-custom
```

On PowerShell, quote the JSON argv so it reaches Python as one argument.

## OpenRouter PKCE contract

The current OpenRouter flow is deliberately implemented as documented, rather
than as generic OAuth:

1. Validate the complete prepared match before any browser or network action.
   The bundled CLI starts this path only with explicit `--openrouter-pkce-v1`,
   only when the plan contains OpenRouter, only when no existing
   `OPENROUTER_API_KEY` would be overwritten, and only with the explicit
   `--openrouter-provider-key-persists-v1` acknowledgement.
2. Generate an RFC 7636 verifier and its S256 challenge in the local runner.
   Bind an HTTP listener only to `127.0.0.1` on an OS-assigned port and use
   `new_callback_path()` for a fresh 128-bit correlation segment.
3. Open `https://openrouter.ai/auth` with exactly `callback_url`,
   `code_challenge`, and `code_challenge_method=S256`.
4. Bind the returned callback to the exact expected scheme, host, effective
   port, and path. An unguessable path is recommended when the caller controls
   it. The expected callback URL has no query; the
   actual callback must have exactly one `code` query parameter.
5. Exchange exactly `code`, `code_verifier`, and
   `code_challenge_method=S256` at the pinned key endpoint. Accept the
   documented response's `key` plus optional string-or-null `user_id`; reject
   every other response field.
6. Reload and revalidate the plan against the pre-authorization
   `launchPlanDigest`. Only then place the wrapped key in the current process
   environment for the fixed match invocation, and remove it in `finally` on
   success or failure.

The official flow does not require this implementation to invent `client_id`,
`redirect_uri`, `response_type`, `scope`, or provider-echoed `state` fields.
HTTPS callbacks are accepted; HTTP callbacks are restricted to explicit-port
loopback hosts. OpenRouter's current documentation explicitly supports
localhost callbacks on arbitrary ports and separately documents a headless
copy/paste flow. This CLI implements only the local callback flow. Redirects
are refused, response sizes are capped, errors are sanitized, the callback
page never echoes the code, and the tests use an injected exchange transport
plus a real loopback-only callback so they perform no live provider exchange.
The key is never printed, serialized, persisted locally, or sent to
BuildWars/Nymrel. Ending local custody does not revoke the provider-side key;
the CLI always directs the customer to review or revoke the newly created key
in the OpenRouter dashboard. Automatic deletion is not claimed or attempted
because OpenRouter's documented delete endpoint requires a separate management
key, which this candidate does not request or custody. OpenRouter use may incur
charges on the customer's OpenRouter account.

Current references: [OpenAI Codex authentication](https://learn.chatgpt.com/docs/auth),
[OpenAI Codex as a platform](https://developers.openai.com/blog/codex-as-a-platform),
[Anthropic Claude Code authentication](https://code.claude.com/docs/en/authentication),
[Anthropic Claude Code legal and compliance](https://code.claude.com/docs/en/legal-and-compliance),
[Anthropic Claude Code CLI reference](https://code.claude.com/docs/en/cli-reference),
[OpenCode providers](https://opencode.ai/docs/providers/),
[OpenCode CLI](https://opencode.ai/docs/cli/),
[OpenRouter OAuth PKCE](https://openrouter.ai/docs/guides/overview/auth/oauth),
[Hermes providers](https://hermes-agent.nousresearch.com/docs/integrations/providers),
and [Hermes Nous Portal](https://hermes-agent.nousresearch.com/docs/integrations/nous-portal).

## Trust and replay boundaries

- Provider credentials never enter the seven BuildWars envelope schemas.
- The pairing secret is shared by the verifier and runner; HMAC proves
  possession of that BuildWars secret and payload integrity. It does not prove
  provider identity, plan entitlement, billing path, or model identity.
- `InMemoryReplayGuard` is a bounded, thread-safe local reference. Production
  requires durable, atomic single-use/replay storage that survives restarts and
  concurrent workers.
- Codex, OpenCode, Hermes, and custom-command children receive a closed
  path/config/locale/TLS environment rather than the parent environment
  wholesale. Claude Code is the explicit exception: Anthropic requires every
  built-in auth method to remain available, so that unmodified child inherits
  the customer's environment without AgentWars enumerating its values. A local
  API key, cloud setting, token, profile, or helper can therefore outrank a
  subscription. The customer must confirm `claude auth status`; BuildWars
  cannot attest the selected auth method or billing route.
- Local provider clients can still retain local sessions, logs, or provider-side
  records according to their own behavior. BuildWars does not inspect those
  stores.
- The Hermes adapter exposes only its non-mutating `clarify` toolset. This is a
  process-level containment choice, not proof about future Hermes versions;
  revalidate the installed CLI before production use.
- Provider subprocess output is size-capped and raw stderr is withheld from
  adapter errors. The custom command keeps the caller's working directory but
  receives the same closed child environment. It can still reach anything the
  caller's OS account can reach; runtime intent is not isolation.
- Construction is call-scoped and fail-closed: provider adapters require the
  exact `customer_local_v1` intent capability, and `custom_agent` also requires
  `unsafe_custom_command`. Shared arbitrary command execution remains disabled
  until a separate OS isolation boundary exists.
- `arena/` remains provider-blind: it imports no provider hub module and holds
  no provider credential.

## What the local candidate proves

It proves that the six-id catalog is immutable and fail-closed, with six
customer-local executable ids; the seven
versioned envelope shapes reject unknown keys, floats, secret-like fields, and
binding drift; pairing signatures reject tampering, staleness, future dates,
wrong kinds/users/runners, and replay when a guard is supplied; the OpenRouter
PKCE request/callback/exchange shapes match the current documented fields; and
both AgentWars harnesses can select only executable provider adapters without
changing the legacy backend path.

It does not prove a live account login, subscription entitlement, provider
permission for every workload, live model response, production enrollment,
durable server replay defense, hosted deployment, customer account storage,
public launch, users, revenue, or virality. All provider adapters remain
unmeasured against authenticated live accounts in this candidate; their
argv/env/network contracts are checked with local help output and mocks.

## Known provider caveats

- Anthropic's current legal documentation permits a product to run the
  unmodified Claude Code binary under its Commercial Terms when the end user
  authenticates with their own supported credential and is billed directly.
  This candidate implements only that customer-local binary route. BuildWars
  does not offer Claude login, collect/intermediate credentials, proxy requests,
  pay on a user's behalf, or resell access. Public enablement remains gated on
  the applicable Commercial Terms and branding requirements. Intermediary
  Claude-subscription routes through OpenCode or Hermes remain disabled.
- OpenCode and Hermes can route many upstream providers. BuildWars cannot
  infer whether a selected route uses a subscription, an API key, free quota,
  or usage billing.
- Nous Portal is a documented Hermes-owned subscription route. Other upstream
  consumer-subscription routing through Hermes remains disabled pending the
  relevant provider's authorization; a Hermes label is not permission evidence.
- OpenRouter's official PKCE flow can support a third-party app, but hosted key
  custody, rotation/deletion controls, and durable replay defense are not
  implemented. The v1 adapter therefore keeps the key in the customer runner.
- A provider may change CLI flags, auth behavior, quotas, models, or plan
  rules. Revalidate the current provider documentation and CLI before a
  production release.
