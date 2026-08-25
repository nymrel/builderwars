# BuildWars / AgentWars customer provider hub release candidate

Date: 2026-08-25

Status: local candidate; not deployed or live-account tested

This local source candidate adds a customer-operated connection layer for
exactly six provider ids: ChatGPT/Codex, Claude Code, OpenCode, OpenRouter,
Hermes, and a custom prompt/stdout command. Provider credentials remain in the
customer runner; `arena/` remains provider-blind and unchanged.

## Included contracts

- An immutable, fail-closed provider catalog and read-only connection plans.
- A human provider/harness policy plus exact JSON twin that separate provider,
  billing/account route, harness, local execution, hosted status, prohibited
  routes, evidence date, and official sources.
- Six strict versioned schemas for identity, provider link, runner pairing,
  runner capabilities, match job, and result attestation (including replay
  receipt/verdict data), with canonical JSON, secret-shape rejection,
  non-enumerable public ids, and explicit unattested execution claims.
- BuildWars-only HMAC pairing for the three signable runner/result envelopes,
  including payload validation, freshness and identity binding, constant-time
  comparison, and an injectable replay guard.
- OpenRouter PKCE S256 primitives matching the documented authorization,
  callback, exchange-request, and `key` plus optional `user_id` response shapes.
- Executable entrant-side adapters with finite timeouts, bounded output,
  sanitized errors, customer-owned auth, and deterministic legal fallback in
  both existing model harnesses.
- Call-scoped runtime-intent capabilities: every provider adapter and every
  non-stub legacy factory path requires `customer_local_v1`; `custom_agent`
  additionally requires `unsafe_custom_command`. These capabilities are
  explicit intent, not an OS isolation boundary.
- A closed child environment for provider CLIs. Provider children inherit only
  bounded OS/auth-path/locale/TLS values plus six exact OpenCode containment
  keys, never the parent environment wholesale.
- An offline adversarial checker plus the existing repository regression
  ladder. Provider subprocess and HTTP behavior is mocked in this candidate.

## Deliberate boundaries

This candidate proves local code and test contracts only. It does not prove a
live provider login, subscription or plan entitlement, provider permission for
a particular workload, billing route, model identity, production runner
enrollment, durable server replay storage, hosted deployment, customer account
storage, public release, audience, revenue, or virality. OpenRouter calls may
incur charges on the customer's own account.

HMAC uses a shared BuildWars pairing secret. That secret is distinct from every
provider credential and must be provisioned to both verifier and runner over an
authenticated pairing channel. The included in-memory replay guard is a local
reference only; production requires durable atomic single-use storage.

No provider login, browser flow, OAuth exchange, credential inspection, live
model call, deployment, or public release was performed while producing this
candidate. Internal agent provenance and exact promotion receipts remain in the
studio control plane rather than this public source note.

OpenCode's current documentation explicitly warns against its third-party
Claude subscription plugin route, so this candidate disables that route.
Consumer-subscription routing through Hermes is also disabled pending explicit
provider authorization; this is fail-closed product policy, not a claimed
Hermes-specific Anthropic prohibition. OpenRouter's official PKCE flow could
support a future hosted connection, but hosted key custody and its production
controls are not implemented.

## Validation entrypoints

```text
python bin/check_provider_hub.py --skip-regressions
python bin/check_provider_hub.py
python -m py_compile <changed Python paths>
git diff --check
```

The exact commit SHA and remote verification belong in the durable studio
promotion receipt, because embedding a commit's own SHA inside this file would
change that SHA.
