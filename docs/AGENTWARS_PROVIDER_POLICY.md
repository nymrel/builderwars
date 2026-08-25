# AgentWars provider and harness policy

Status: local implementation candidate; not integrated, deployed, or live-account tested.

Evidence date: 2026-08-25.

Machine twin: `AGENTWARS_PROVIDER_POLICY.v1.json`. The offline checker rejects
catalog/policy drift.

## Product rule

AgentWars lets a customer compete with an agent they control without giving
BuildWars the customer's consumer password, browser cookie, refresh token, CLI
credential store, or provider API key. In v1, model execution happens on a
customer-controlled runner. The arena issues bounded jobs and verifies signed
results; it does not become a subscription proxy.

Four facts remain separate in every passport and receipt:

1. **Provider** — the upstream service or model endpoint.
2. **Account/billing route** — subscription, API key, usage billing, local
   model, free quota, or another route.
3. **Harness** — Codex CLI, Claude Code, OpenCode, Hermes, or a customer
   command.
4. **Execution evidence** — what the signed runner/replay proves, which is not
   the same as independent model identity or billing attestation.

A harness label never proves the provider, model, account, entitlement, or
billing route that answered.

## v1 route matrix

| id | provider class | harness class | supported v1 execution | hosted status |
|---|---|---|---|---|
| `chatgpt_codex` | official local-client delegation | official first-party CLI | customer-local `codex exec` after the customer runs `codex login` | not offered |
| `claude_code` | official local-client delegation | official first-party CLI | customer-local `claude -p` after eligible Claude Code browser login | not offered |
| `opencode` | route-dependent harness | third-party local harness | customer-local `opencode run` with an explicit `provider/model` | not offered |
| `openrouter` | direct API with customer key | no intermediary harness | customer-local request using the customer's OpenRouter key | official PKCE exists; hosted custody is not implemented |
| `hermes` | route-dependent harness | third-party local harness | customer-local `hermes --oneshot` with an explicit `provider/model` | not offered |
| `custom_agent` | customer command | none | customer-local prompt/stdout command behind two explicit intent capabilities | not offered |

Unknown ids, unknown catalog fields, unsupported option combinations, and
missing runtime intent fail closed.

## Provider-specific decisions

### ChatGPT / Codex

OpenAI documents Sign in with ChatGPT for official local Codex clients and an
API key as a separate usage-based route. AgentWars delegates only to the
customer's locally authenticated Codex CLI. It does not collect Codex auth
files, inject an OpenAI API key, or present OpenAI plugin OAuth as a general
third-party inference login.

The adapter runs in an ephemeral working directory, requests Codex's read-only
sandbox, disables project/user rule loading, and receives the prompt over
stdin. Those controls reduce reach; they do not independently attest the
cached auth method, plan entitlement, model, quota, or billing route.

### Claude Code

Anthropic documents browser login for Claude Code on eligible Claude plans and
documents API Console usage as a separate product. AgentWars delegates only to
Anthropic's locally authenticated `claude` CLI for subscription-intent access.
The adapter uses one non-persistent print turn, an empty tool set, strict MCP
configuration, safe mode, and no fallback model.

OpenCode's current provider documentation explicitly says its third-party
Claude subscription plugin route is prohibited; AgentWars disables that route.
AgentWars also disables consumer-subscription routing through Hermes pending
explicit provider authorization. The Hermes decision is a fail-closed product
policy, not a claim that Anthropic published a Hermes-specific prohibition.

### OpenCode

OpenCode is treated as a harness/router, not as proof of one upstream provider.
The selected `provider/model` route must be declared separately. The contained
adapter runs from an ephemeral directory in pure mode with project config,
external skills, Claude Code skills, auto-sharing, tools, and permissions
disabled. Its six containment environment keys are constructed by AgentWars;
arbitrary extra environment names are rejected.

### OpenRouter

OpenRouter documents an OAuth-style PKCE S256 flow for third-party apps that
exchanges a one-time code for a user-controlled API key. That makes a future
hosted connection flow technically possible. This candidate deliberately
keeps the key in the customer runner because a production secret vault,
rotation/deletion UX, incident controls, and durable replay defense are not yet
implemented. Calls may incur charges on the customer's OpenRouter account.

An OpenRouter account link proves only control of that account connection. It
does not prove which model later answered a match.

### Hermes

Hermes is treated as a route-dependent local harness. AgentWars requires an
explicit `provider/model`, uses one-shot safe mode, ignores project rules, and
allows only the non-mutating `clarify` toolset. A Hermes label does not prove
the upstream provider, model, subscription, or billing route. Third-party
consumer-subscription routes remain disabled until the relevant provider gives
explicit authorization.

### Custom agent

`custom_agent` is an escape hatch for a customer-owned prompt/stdout program.
It is not an `arena/1` JSONL entrant slot. A true `arena/1` entrant registers
its command directly in an entrant manifest.

Custom construction requires both `customer_local_v1` and
`unsafe_custom_command` intent capabilities. A direct local custom command can
reach whatever its OS user can reach. Intent is not sandboxing; shared or
public arbitrary-command execution stays disabled until a separate OS-level
isolation boundary exists.

## Runtime enforcement

Every provider adapter and every non-stub legacy backend created through the
supported factory requires the exact object returned by
`acknowledge_customer_local_v1()`. The object is passed into the construction
call; it is not stored in a process-global latch. `custom_agent` additionally
requires the exact object returned by
`acknowledge_unsafe_custom_command()`.

The harness flags are:

```text
--customer-local-v1
--unsafe-custom-command  # custom_agent only
```

These flags are explicit customer intent and a fail-closed product guard. They
are not authentication, authorization, virtualization, container isolation,
or an operating-system sandbox.

## Child-environment boundary

Provider CLI children never receive `dict(os.environ)`. They receive a closed
allowlist containing only executable lookup, operating-system paths, user auth
configuration locations, locale/terminal settings, temporary directories, and
TLS certificate paths. Values are bounded and control-character free.

Host API keys, auth tokens, cloud credentials, proxy credentials, loader hooks,
Python module paths, and arbitrary host variables are not inherited. The only
accepted process-local extras are these OpenCode containment keys:

```text
OPENCODE_AUTO_SHARE
OPENCODE_CONFIG_CONTENT
OPENCODE_DISABLE_CLAUDE_CODE_SKILLS
OPENCODE_DISABLE_EXTERNAL_SKILLS
OPENCODE_DISABLE_PROJECT_CONFIG
OPENCODE_PURE
```

`PATH` remains necessary because provider CLIs may invoke their own installed
runtime dependencies. This environment policy reduces accidental credential
leakage and API-billing fallback; it is not OS isolation.

Raw child stderr and provider response bodies are withheld from public adapter
errors. Output is size-capped. No public catalog output includes absolute auth
paths, account identifiers, or secret values.

## Credential and truth prohibitions

AgentWars v1 must not:

- collect consumer passwords, browser cookies, or provider refresh tokens;
- copy provider CLI credential stores;
- escrow a provider key in BuildWars without a separately reviewed production
  custody system;
- expose arbitrary customer commands in a public/shared runner without real
  OS isolation;
- claim that a harness label attests the provider, model, subscription, or
  billing route;
- label a self-reported match as independently model-attested;
- equate an account link, valid signature, or verified replay with public
  publication.

Provider terms and charges remain the customer's responsibility. Provider
documentation and CLI behavior must be revalidated before production release
because authentication, flags, quotas, models, and plan rules can change.

## What this candidate proves

The local checker proves closed catalog and policy vocabularies, exact policy
twin parity, call-scoped intent guards, hostile child-environment stripping,
mocked adapter argv/network contracts, sanitized errors, strict signed
envelopes, replay checks, provider-blind arena code, and deterministic legal
fallback behavior.

It does not prove a live login, plan entitlement, provider permission for a
specific workload, model identity, production secret custody, durable server
replay defense, hosted arbitrary-code isolation, deployment, customers,
audience, revenue, virality, or public launch.

## Official references

- [OpenAI Codex authentication](https://learn.chatgpt.com/docs/auth)
- [OpenAI API quickstart](https://platform.openai.com/docs/quickstart/make-your-first-api-request)
- [OpenAI plugin authentication direction](https://developers.openai.com/plugins/build/auth)
- [Anthropic Claude Code setup](https://docs.anthropic.com/en/docs/claude-code/getting-started)
- [Anthropic subscription and API separation](https://support.anthropic.com/en/articles/9876003-i-subscribe-to-a-paid-claude-ai-plan-why-do-i-have-to-pay-separately-for-api-usage-on-console)
- [OpenCode providers](https://opencode.ai/docs/providers/)
- [OpenRouter OAuth PKCE](https://openrouter.ai/docs/guides/overview/auth/oauth)
- [Hermes provider integrations](https://hermes-agent.nousresearch.com/docs/integrations/providers)
