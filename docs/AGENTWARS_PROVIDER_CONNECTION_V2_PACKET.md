# AgentWars provider connection v2 candidate

Status: local candidate on `codex/agentwars-launch-integration-20260825`;
not independently accepted, integrated into canonical main, deployed, or
tested against a live customer account.

Implementation base: `a99393c461c02794f2ed3b2ffe5523aac418590e`;
the exact candidate commit is recorded only after validation and commit.

Evidence date: 2026-08-27.

## Purpose

Make the customer connection contract tell the truth before account and runner
pairing UI is built. A public surface must not present every provider as a
universal web sign-in or imply that a consumer subscription is third-party API
credit.

The catalog now distinguishes customer-facing `connection_mode` from the
lower-level `connection_transport`:

| provider id | connection mode | current boundary |
|---|---|---|
| `chatgpt_codex` | `local_subscription_session` | customer-local official Codex client |
| `claude_code` | `local_native_client_session` | customer-local unmodified official Claude Code binary; all built-in auth methods remain available and the customer verifies the selected route locally |
| `opencode` | `local_provider_session` | customer-local route-dependent harness |
| `openrouter` | `web_oauth_pkce` | browser approval and exchange inside the customer runner |
| `hermes` | `local_provider_session` | customer-local route-dependent harness |
| `custom_agent` | `local_runtime` | customer-local command, public/shared execution disabled |

`local_api_key` and `unsupported` remain reserved closed vocabulary values. No
current provider id selects either value; a future policy hold can use
`unsupported` only together with disabled execution.

## Versioned contract

`buildwars.provider_link.v1` is still accepted with its original exact key set.
The historical `AGENTWARS_PROVIDER_POLICY.v1.json` is unchanged.

The additive `buildwars.provider_link.v2` requires:

- the exact catalog connection mode and transport for the provider;
- `execution_boundary: customer_local_runner`;
- `credential_custody: customer_only`;
- provider-account, plan-entitlement, billing-route, and model attestation to
  be exactly `false`;
- the existing provider-specific model declaration rules;
- strict rejection of unknown keys, wrong modes, hosted boundaries, string
  booleans, credential escrow, and v1/v2 downgrade confusion.

Hosted provider-account proof or independent model/runtime attestation needs a
future schema and review. It cannot be introduced by loosening v2.

## Current official evidence

- OpenAI documents subscription and API-key sign-in as distinct Codex paths,
  separately documents that general API service is billed independently from
  ChatGPT, and documents `codex exec`, the SDK, and app-server as supported
  product-building surfaces.
- Anthropic's current legal documentation permits products to run an
  unmodified Claude Code binary under its Commercial Terms when each user
  authenticates with their own supported credential and is billed directly.
  It separately forbids third-party login, credential/session intermediation,
  hosted request routing, and resale. This candidate implements only the
  customer-local unmodified binary route and keeps public enablement gated on
  the applicable terms and branding requirements.
- OpenRouter documents a third-party OAuth flow using PKCE S256 that returns a
  user-controlled key.
- OpenCode and Hermes remain route-dependent local harnesses; their labels do
  not attest provider, model, subscription, entitlement, or billing route.
  Hermes' documented Nous Portal route is distinct from permission to route an
  upstream provider's consumer subscription.

Sources are pinned in `provider_hub/catalog.py` and mirrored exactly by
`AGENTWARS_PROVIDER_POLICY.v2.json`.

## Ox Alpha MAX use and acceptance

Read-only Ox run `8f49d7e9-a1a9-410c-b952-6b61c546da11` used OpenCode Go,
`ox-alpha-free`, variant `max`, with 131,072-token capacity and no fallback.
Connector/runtime identity, VCS custody, process cleanup, and seat release all
passed, but the model returned no substantive architecture review, so no Ox
finding was adopted.

One later bounded recovery attempt,
`2a4a4d8e-192d-4d7c-bf27-c5c7b39689cb`, failed closed in broker preflight
before seat acquisition or private-code transmission because the external Ox
provider contract no longer matched the required model, documentation,
endpoint, training, retention, and temporary-offer assertions. It still records
MAX/131072/no fallback. No fallback model or bypass was used, and another Ox run
must wait for a meaningful external contract-state change.

Receipts:
`C:/Users/johns/AppData/Local/JalenBuilds/receipts/ox-alpha-agent-runs/8f49d7e9-a1a9-410c-b952-6b61c546da11.json` and
`C:/Users/johns/AppData/Local/JalenBuilds/receipts/ox-alpha-agent-runs/2a4a4d8e-192d-4d7c-bf27-c5c7b39689cb.json`.

## Validation

`python bin/check_provider_hub.py` passes all ten sections, including the full
existing regression ladder. `python bin/check_cross_provider_match.py` passes
303 checks, `python bin/check_agentwars_runner.py` passes 158 checks, and the
competition evidence/source/prepared suites pass 85, 54, and 118 checks. New
hostile checks cover every provider's v2 mode, cross-provider mode swaps,
reserved modes, hosted execution, escrow custody, truthy attestation flags,
string booleans, unknown keys, v1/v2 downgrade confusion, the exact constrained
Claude argv/environment, and rejection of public arbitrary command routes. The
offline promotion-candidate checker passes 36 checks
with one Windows-host symlink capability skip, and the master ladder compiles
42 claimed files. All checks are offline; they perform no provider login or
call.

`python bin/buildwars_provider.py catalog --json` exposes the connection mode
without logging in, opening a browser, reading credentials, or contacting a
provider.

## Changed paths

- `provider_hub/catalog.py`
- `provider_hub/schemas.py`
- `provider_hub/__init__.py`
- `bin/buildwars_provider.py`
- `bin/check_provider_hub.py`
- `entrants/backends.py`
- `docs/AGENTWARS_PROVIDER_POLICY.md`
- `docs/AGENTWARS_PROVIDER_POLICY.v2.json`
- `docs/PROVIDER_CONNECTIONS.md`
- `docs/AGENTWARS_PROVIDER_CONNECTION_V2_PACKET.md`

## Non-goals and stops

- No hosted account backend, provider credential vault, OAuth callback service,
  browser login, live provider call, billing action, or plan check.
- No provider credential, CLI auth file, browser cookie, refresh token, or raw
  provider error enters an envelope, receipt, transcript, prompt, or log.
- No public or shared arbitrary command execution.
- No claim that a connection, runner signature, harness label, or replay proves
  provider/model identity or subscription entitlement.
- Stop integration and deployment until the exact committed candidate receives
  an explicit independent approval.
