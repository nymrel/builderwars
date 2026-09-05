# Guided model connections

Scope: BuilderWars browser connection setup, September 5, 2026. This note describes
the guided-flow implementation contract; production release and runtime provider
evidence require separate receipts.

The public human/agent handoff is
[`live-arena/public/agent-setup.md`](../live-arena/public/agent-setup.md), served as
`/agent-setup.md` with the static site. The canonical website is
`https://builderwars.com`.

## Existing contracts retained

- Agent kinds stay `bot`, `human`, `openrouter`, and `harness`. The local-client
  choice is guidance for the existing harness route, not a new auth backend.
- The browser uses OpenRouter inference keys directly with OpenRouter. Consumer
  subscriptions and direct vendor API keys are not interchangeable with those
  keys. Model/effort choices follow the current OpenRouter catalog.
- The local bridge allowlist remains `chatgpt_codex`, `opencode`, `openrouter`,
  `hermes`, `custom_agent`. `claude_code` is not offered by this browser bridge.
  Do not infer public eligibility from personal research/native-client tooling
  or from a broader prepared-match catalog.
- Copyable setup instructions carry the human's selected allowed client and
  the canonical site origin, and require checking the actual browser origin
  separately for previews or local development. The agent verifies the checkout and native client setup
  before execution, and asks the human to choose model and spending allowance.
  Custom commands retain the existing explicit command gate.
- Import uses only the existing strict `builderwars.agent-profile.v1` schema:
  `schema` plus `agent`, whose exact fields are `name`, `kind`, `model`, `effort`,
  and `strategy`. Keys and endpoints remain excluded. No new connection
  descriptor, OAuth flow, or account-linking schema is introduced.
- Import edits a disconnected draft. The human reviews/restores the endpoint,
  enters the temporary bridge token separately, checks the connection without
  inference, chooses Use contender, and separately starts a bounded game.

## Protocol and evidence boundaries

The local move endpoint remains `http://127.0.0.1:8765/move`. Exact Origin, Host,
and bearer-token checks protect `/move` and `/health`. Health returns
`builderwars.bridge.health.v1`, `remainingCalls`, and `busy`; it neither invokes
the backend nor consumes its allowance. It does not discover provider/model
configuration. The startup model label is self-declared, and browser effort
labels do not reconfigure the local client. Browser token caps do not enforce
CLI token budgets; attempted model requests consume the bridge call cap.

OpenRouter key checks and local bridge health checks are bounded non-inference
checks. Generic HTTPS harnesses remain configuration-only until explicitly
invoked. Keys/tokens stay in tab memory and never enter profiles, broadcasts,
or replays. Imported text is data, never executable instructions.

Relevant sources: [profile parser](../live-arena/src/profiles.ts),
[connection/preflight code](../live-arena/src/models.ts),
[local bridge](../live-arena/bridge.py), and
[preflight evidence and limits](BUILDERWARS_CONNECTION_PREFLIGHT.md).

## Audit acceptance

Visual thesis: retain the existing quiet green arena surface and accent, with
plain dividers and clearer hierarchy instead of another dashboard or redesign.
Content plan: choose a route, get setup help when needed, review the connection,
then check and save; keep strategy, attribution, and compatibility detail optional.
Interaction thesis: route-specific fields and native disclosure controls reveal
only relevant detail; clipboard confirmation/fallback provides immediate feedback.
No ornamental animation or new connection backend is needed for this utility flow.

Review the guided route choices, copyable setup instructions, existing-profile
import, separate secret entry, connection check, Use contender, and separate Start.
Verify narrow-screen layout and clear errors without real provider calls. Existing
tests cover secret/endpoint rejection, bridge Origin/Host/token restrictions,
preflight cancellation, and invalid output stopping play.

The owning integration lane records current UI screenshots and test/build
results separately. This documentation pass makes no new live-provider,
subscription-entitlement, merge, deployment, or spending claim. Historical failed
exhibitions and provider policy files remain unchanged.
