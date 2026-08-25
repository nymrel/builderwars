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

The repository implements the v1 catalog, strict envelopes, pairing
primitives, provider adapters, and local harness integration. It does not yet
implement a hosted BuildWars account service, production runner enrollment,
durable job storage, or a live provider-account linking UI.

The controlling human policy is `AGENTWARS_PROVIDER_POLICY.md`; its exact
machine twin is `AGENTWARS_PROVIDER_POLICY.v1.json`.

## Supported provider ids

| id | customer-side connection | local setup | required options | entrant backend |
|---|---|---|---|---|
| `chatgpt_codex` | locally authenticated Codex CLI | `codex login`, then `codex login status` | none | `codex exec` |
| `claude_code` | locally authenticated Claude Code CLI | start `claude` and complete its browser sign-in on an eligible plan | none | `claude -p` |
| `opencode` | OpenCode's local provider auth | `opencode auth login`, then `opencode auth list` | `provider/model`; optional variant | `opencode run` |
| `openrouter` | OpenRouter OAuth PKCE inside the customer runner | approve at OpenRouter; the exchanged key stays local | model id | OpenAI-compatible chat request |
| `hermes` | Hermes' local provider configuration/auth | `hermes model` and `hermes auth` | `provider/model` | `hermes --oneshot`, safe mode, `clarify` toolset only |
| `custom_agent` | explicit customer-owned JSON argv command | customer-defined | JSON argv | prompt on stdin, answer on stdout |

Unknown provider ids and provider-specific options fail closed. `custom_agent`
is a prompt/stdout adapter for the model harnesses; it is not an `arena/1`
JSONL entrant. A direct `arena/1` entrant is registered as a manifest command
outside these harnesses.

Read-only planning commands perform no login, browser launch, credential-file
inspection, or network request:

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
3. **Choose one of the six exact provider ids.**
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

1. Generate an RFC 7636 verifier and its S256 challenge in the local runner.
   `new_callback_path()` can generate a fresh 128-bit correlation segment when
   the caller controls the callback path; documented fixed HTTPS callback paths
   remain valid.
2. Open `https://openrouter.ai/auth` with exactly `callback_url`,
   `code_challenge`, and `code_challenge_method=S256`.
3. Bind the returned callback to the exact expected scheme, host, effective
   port, and path. An unguessable path is recommended when the caller controls
   it. The expected callback URL has no query; the
   actual callback must have exactly one `code` query parameter.
4. Exchange exactly `code`, `code_verifier`, and
   `code_challenge_method=S256` at the pinned key endpoint. Accept the
   documented response's `key` plus optional string-or-null `user_id`; reject
   every other response field.
5. Keep the exchanged `OPENROUTER_API_KEY` only in the customer runner.

The official flow does not require this implementation to invent `client_id`,
`redirect_uri`, `response_type`, `scope`, or provider-echoed `state` fields.
HTTPS callbacks are accepted; HTTP callbacks are restricted to explicit-port
loopback hosts. Redirects are refused, response sizes are capped, errors are
sanitized, and the test transport is injected so the suite performs no live
exchange. OpenRouter use may incur charges on the customer's OpenRouter
account.

Current references: [OpenAI Codex authentication](https://learn.chatgpt.com/docs/auth),
[Claude Code setup](https://docs.anthropic.com/en/docs/claude-code/getting-started),
[OpenCode providers](https://opencode.ai/docs/providers/),
[OpenCode CLI](https://opencode.ai/docs/cli/), and
[OpenRouter OAuth PKCE](https://openrouter.ai/docs/guides/overview/auth/oauth).

## Trust and replay boundaries

- Provider credentials never enter the six BuildWars envelope schemas.
- The pairing secret is shared by the verifier and runner; HMAC proves
  possession of that BuildWars secret and payload integrity. It does not prove
  provider identity, plan entitlement, billing path, or model identity.
- `InMemoryReplayGuard` is a bounded, thread-safe local reference. Production
  requires durable, atomic single-use/replay storage that survives restarts and
  concurrent workers.
- Provider CLI children receive a closed path/config/locale/TLS environment,
  never the parent environment wholesale. API keys, auth tokens, cloud
  credentials, proxy credentials, loader hooks, and arbitrary host variables
  are excluded. This reduces accidental leakage and API-billing fallback;
  BuildWars still cannot attest a CLI's cached auth method or billing route.
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

It proves that the six-id catalog is immutable and fail-closed; the six
versioned envelope shapes reject unknown keys, floats, secret-like fields, and
binding drift; pairing signatures reject tampering, staleness, future dates,
wrong kinds/users/runners, and replay when a guard is supplied; the OpenRouter
PKCE request/callback/exchange shapes match the current documented fields; and
both AgentWars harnesses can select the provider adapters without changing the
legacy backend path.

It does not prove a live account login, subscription entitlement, provider
permission for every workload, live model response, production enrollment,
durable server replay defense, hosted deployment, customer account storage,
public launch, users, revenue, or virality. All provider adapters remain
unmeasured against authenticated live accounts in this candidate; their
argv/env/network contracts are checked with local help output and mocks.

## Known provider caveats

- Current OpenCode documentation explicitly says its third-party Claude
  subscription plugin path is prohibited. Use the dedicated `claude_code`
  adapter for eligible Claude Code plan access.
- OpenCode and Hermes can route many upstream providers. BuildWars cannot
  infer whether a selected route uses a subscription, an API key, free quota,
  or usage billing.
- BuildWars disables third-party consumer-subscription routing through Hermes
  pending explicit provider authorization. This is a fail-closed product
  policy, not a Hermes-specific prohibition attributed to Anthropic.
- OpenRouter's official PKCE flow can support a third-party app, but hosted key
  custody, rotation/deletion controls, and durable replay defense are not
  implemented. The v1 adapter therefore keeps the key in the customer runner.
- A provider may change CLI flags, auth behavior, quotas, models, or plan
  rules. Revalidate the current provider documentation and CLI before a
  production release.
