# Economics — why the arena separates adjudication from model execution

**Decision: bring-your-own-runtime, entrant-side. The arena engine makes no
model call; platform infrastructure and customer provider usage are not free by
definition.**

This was settled before the architecture, because it determines the
architecture. It is not a cost optimisation applied afterwards — it is the
reason entrants are subprocesses.

---

## What the prior lane already established

A research lane looked at this question on **2026-08-02** in
`portfolio-control/reports/2026-08-02-user-ai-subscription-integration-paths.md`.
Provider evidence was refreshed on **2026-08-26** because authentication and
third-party product rules drift:

- Anthropic's current legal and Agent SDK guidance says third-party products
  must not offer Claude.ai login or route Free, Pro, or Max credentials without
  approval. AgentWars therefore disables its direct Claude subscription route
  as well as Claude subscription routing through intermediary harnesses.
- OpenAI currently documents Sign in with ChatGPT for Codex and documents Codex
  as a product-building platform through `codex exec`, the SDK, and app-server.
  AgentWars may delegate to a customer-local official Codex client, but that is
  not generic account sharing, provider OAuth, API credit, or model attestation.
- OpenRouter documents a PKCE flow that returns a user-controlled API key. Nous
  documents Nous Portal as a Hermes-owned subscription route. Those routes have
  their own custody, cost, and permission boundaries.

There is no universal "bring your subscription" rule. Each executable route
must have current provider evidence, stay customer-controlled where required,
and fail closed when authorization is absent. A customer-local runner remains
the v1 boundary because it minimizes credential custody and gives builders an
explicit, inspectable execution environment.

**An arena inverts that.** Its users are people who write harnesses. They already
hold keys and already run CLIs. What was a fatal adoption barrier for
FirstOneFitness is the entry requirement here, and it happens to be the only
lane both providers permit.

## What that buys, beyond compliance

| | |
|---|---|
| **Arena inference cost** | **$0 per current match.** The adjudication engine issues no model call. Queue, storage, bandwidth, observability, abuse prevention, and support still cost money. |
| **Customer execution cost** | Route-dependent. Local inference may be free after hardware cost; subscriptions have quotas; API and OpenRouter routes may incur usage charges. |
| **Credential custody** | Reduced, not eliminated. Provider secrets stay customer-side, while BuildWars still protects pairing secrets, account data, and signed-job state. |
| **Revocation** | Provider access is revoked at the provider; BuildWars pairing, publication, and account access require separate revocation and deletion controls. |
| **Vendor exposure** | Limited by adapter boundaries, but provider policy, availability, quotas, pricing, and CLI changes can still disable a route. |
| **Model coverage** | Extensible only where a customer has a permitted route and the harness can declare it truthfully. New routes still require policy and contract validation. |

That last row matters more than the inference-cost saving. Subprocess adapters
reduce central integration and credential custody, but a new model is playable
only after the selected provider route, harness contract, and truth labels pass
the current policy and verification gates.

## How the engine enforces it

Not by policy. By having nowhere to put a credential.

- `arena/` contains no HTTP client, no provider SDK, no endpoint, no key
  handling. Nothing in the package imports `entrants/backends.py`.
- The engine passes environment variables through by **name only**, from a list
  the entrant's manifest declares. Values are never read, logged, or hashed.
  Everything undeclared is stripped.
- Inference happens inside the entrant process, behind a JSON-Lines pipe.

**Probed 2026-08-14:**
`grep -rniE "api_key|anthropic|openai|urllib|requests|socket|http" arena/` returns
**zero matches**, and `grep -rn "backends" arena/` returns zero — the engine has no
import path to the model layer at all. The reference series ran 32 matches (24
against a stub, 8 against a live local model) with **$0.00 measured provider
spend**, and 33 transcripts re-verify from disk. This is local reference-series
evidence, not a claim that production hosting or every customer route costs $0.

## The three backends an entrant can use

Entrant-side only, in `entrants/backends.py`:

| Backend | What it is | Status |
|---|---|---|
| `stub:v1` | deterministic offline pseudo-model | **probed** — the 24-match reference series |
| `cli:<cmd>` | a locally installed CLI the entrant already runs | **probed** — 8 live matches against `ollama run qwen2.5:7b`, 8/8 replay-verified, $0.00 |
| `api:<ENV_VAR>` | the entrant's own API key from their own environment | **implemented, unmeasured** — never called, no spend incurred |

Every non-stub backend created through the supported harness factory now
requires the explicit `--customer-local-v1` flag. `run_match.py` and
`run_series.py` require and forward the same flag for non-stub runs. It records
customer-local intent only; it is not account attestation or OS isolation.
The catalog-visible `claude_code` backend is disabled before process creation;
customer-local intent cannot override an unsupported provider route.

`ollama` is worth noting: local inference is free, private, needs no account,
and raises no terms question whatsoever. For anyone who wants to enter without
paying anyone, it is a complete answer.

## The honest limit

The engine cannot witness a model. It sees moves arriving on a pipe, and a
`claimed_model` string the entrant wrote about itself. So **every result carries
`model_attested: false`**, and replay explicitly lists model identity under *what
this does not prove*.

That is a real constraint and pretending otherwise would be the exact
match-fixing failure this engine exists to avoid. It has a product answer rather
than a technical one — two divisions:

- **Open division.** Anyone runs the engine locally, on their own access, and
  submits a hash-chained transcript. Anyone can replay-verify it. Free, open to
  everyone, labelled `unattested-model`.
- **Verified division.** A future match runs inside arena-controlled isolation
  through a separately sanctioned customer-owned provider route, so the arena
  can observe the execution contract. It would incur platform compute/storage
  costs and possibly customer provider charges. Its evidence class must still
  distinguish runtime observation from independent model identity.

The open division is the current local candidate. The verified division is a
future ladder above it. Neither requires BuildWars to buy provider tokens in the
current architecture, but both still have platform costs. The verified division
also needs the OS-level jail listed as unenforced in `arena/sandbox.py:POLICY`,
sanctioned provider routes, secret handling, and independent acceptance before
it would mean anything.
