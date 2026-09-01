# AgentWars browser authorization boundary

Status: local, framework-neutral security reference. This contract is designed to make a future production HTTP adapter small, reviewable, and deny-by-default. It is not live Clerk integration, a production session, a durable perimeter, or production security approval.

## Status and authority boundary

`provider_hub_hosted/browser_gateway.py` is the only reviewed browser-to-owner-command reference in this repository. It accepts sanitized request facts plus an injected `VerifiedBrowserPrincipal`; it never verifies or stores a Clerk cookie itself. The production adapter, Clerk configuration, owner pepper, idempotency-response key custody, durable rate limiter, production-store parity, and public route exposure remain protected work.

All production authority flags remain false. This slice does not accept terms, attest a human action, provision secrets, mutate a customer or production database, change DNS, enable public creator execution, incur paid compute, or promote a deployment. BuilderWars.com apex and www remain untouched.

## Exact browser request contract

`BrowserRequest` has exactly eight fields:

- `method`
- `path`
- raw byte `body`
- exact `origin`
- `content_type`
- `csrf_cookie`
- `csrf_header`
- `idempotency_key`

The request carries no session cookie, bearer token, or owner id. It cannot contain a provider credential, Clerk token, client-selected tenant, arbitrary header map, query string, or redirect target. The idempotency key is public request metadata, not authentication: it is one canonical `awi1_` token carrying exactly 128 bits, and it is hidden from object representations. The gateway accepts only `POST` and `DELETE`, rejects bodies larger than 16 KiB, rejects unknown routes before resolving a principal, and parses JSON with duplicate-key, float, non-finite-number, UTF-8, unknown-key, and non-object rejection.

## Verified principal contract

A production-owned adapter must cryptographically verify the Clerk session before constructing `VerifiedBrowserPrincipal`. The injected value contains only:

- the exact expected HTTPS issuer;
- a canonical Clerk subject;
- a canonical session identifier;
- the verifier's timezone-aware `verified_at` time; and
- the fixed authentication class `clerk_session`.

The gateway accepts principals verified no more than 300 seconds ago and no more than 30 seconds in the future. Wrong issuer, malformed identity, stale/future evidence, wrong authentication class, a naive timestamp, and verifier failure all fail closed. The gateway returns one safe authentication error and never reflects a token, claim, subject, session identifier, or exception detail.

The adapter must not construct this object from unsigned request JSON, query data, arbitrary headers, client-side Clerk state, or decoded-but-unverified token claims.

## Owner derivation and tenant isolation

The owner ID is derived server-side as a domain-separated HMAC-SHA256 over the schema version, normalized issuer, and Clerk subject, using a production-owned pepper. Only the first 128 bits are encoded as an `awu1_` identifier. The session identifier is validated for freshness context but does not change the durable owner ID.

The raw subject is not sent to the hosted control plane, returned to the browser, or accepted from the request. The pepper must be at least 32 random bytes and remain in protected server-side secret custody. Direct public access to `HostedControlPlane` owner methods must be impossible; every browser owner command must pass through the gateway. Foreign runner and pairing probes retain uniform not-found responses.

## Route and body allowlist

| Method | Exact route | Exact body | Operation |
|---|---|---|---|
| `POST` | `/v1/browser/pairings` | `{}` | Create one pairing challenge |
| `POST` | `/v1/browser/pairings/{challenge}/confirm` | `{"approved": true|false}` | Confirm or reject the owner's pairing |
| `POST` | `/v1/browser/runners/{runner}/revoke` | `{}` | Revoke the owner's runner |
| `DELETE` | `/v1/browser/runners/{runner}` | empty | Delete the owner's runner state |
| `POST` | `/v1/browser/runners/{runner}/fixture-jobs` | `{}` or one canonical 128-bit base64url `seed` | Create one deterministic fixture job |
| `DELETE` | `/v1/browser/account` | empty | Delete all state for the derived owner |

Route IDs use the repository's canonical validators. Method confusion, encoded or malformed IDs, extra slashes, fragments, query strings, unknown keys, duplicate keys, and unexpected bodies are refused. No route launches an arbitrary entrant, accepts provider credentials, publishes a result, edits a rating, changes production flags, or executes customer code.

## Origin and CSRF rules

The gateway is initialized with one ASCII, lowercase, no-port, no-path canonical HTTPS origin. Every mutation request must match that exact string. User information, mixed case, a trailing slash, a port, Unicode hostname spelling, HTTP, a subdomain, a query, or a fragment is rejected.

Every request must also provide an exact double-submit CSRF pair: a 32-byte random value encoded in canonical unpadded base64url form in both the cookie and header. Malformed or unequal values are refused with constant-time comparison. Production cookie attributes, Clerk cookie verification, same-site policy, trusted proxy behavior, and edge header normalization remain deployment-specific review items.

## Rate-limit boundary

Rate limiting is an injected `AccountRateLimiter`, scoped to the derived owner and operation. Gateway code fails closed with `503 rate_limit_unavailable` when the limiter raises, returns a malformed decision, or is unavailable. The local `InMemoryAccountRateLimiter` is thread-safe and proves operation separation, owner separation, window reset, and atomic concurrency behavior.

The in-memory limiter is not production protection: it is not durable, global, distributed, edge-scoped, or effective before authentication. Production requires edge/IP abuse controls plus a durable atomic account limiter with monitored capacity and a tested failover policy. The current operation ceilings are local reference values, not approved production policy.

## Idempotency and encrypted replay boundary

Every accepted browser mutation requires one canonical 128-bit idempotency key. The local reference binds `(opaque owner id, idempotency key)` to the exact operation and SHA-256 of the schema, method, path, and raw request body for 24 hours:

- the first request inserts a pending record, performs the owner mutation, seals the exact success response, and completes the record in one SQLite transaction;
- nested domain-store calls use savepoints, so a failure after mutation but before response sealing rolls back both the mutation and retry record;
- the same owner, key, operation, and request bytes return the original status and response without invoking the mutation again;
- the same owner and key with a different operation or request digest returns `409 idempotency_conflict` without mutation;
- a different owner has a separate key namespace; and
- pending, malformed, oversized, unauthenticated, wrong-key, or tampered replay state fails closed as `503 idempotency_unavailable`.

Replay responses are canonical JSON encrypted and authenticated with AES-256-GCM inside the binary envelope `agentwars.idempotency_response_envelope/1`. The envelope carries a non-secret canonical key ID plus a random 96-bit nonce and ciphertext. Associated data binds schema, owner, idempotency key, operation, request digest, status, envelope version, and complete header, so changing a key ID fails authentication even when both named keys exist. This matters because pairing creation returns a one-time secret that must survive a legitimate client retry without being stored in plaintext. The SQLite row stores only the opaque owner id, public idempotency metadata, request digest, timing, status, and sealed response; key material never appears in the database, response, or keyring representation.

The constructor requires a bounded keyring with exactly one active key, zero to two retiring keys, unique 32-byte material, and lowercase canonical key IDs of 3-32 bytes. New responses always use the active key. Eligible old responses remain replayable only while their key ID stays in the ring. Unknown, malformed, substituted, or deliberately retired key IDs fail closed; the gateway never guesses across keys. Local tests prove a staged `old -> old+new(active) -> new-only` transition, but they do not provision or rotate a real secret.

Production must provision separate random keys through protected custody, retain a retiring key for the complete replay-eligibility window plus an approved rollout margin, exercise rollback before retirement, and prove all instances use the same ordered keyring configuration. The replay record intentionally survives account-row deletion during its 24-hour replay-eligibility window so a retried delete returns the same receipt. Expired local rows are purged opportunistically by the next mutation, not by a proven wall-clock deletion worker; production therefore needs scheduled physical expiry and evidence of bounded deletion. This minimal encrypted record and its retention policy require approval. Rate limiting is evaluated before replay, so retry traffic still consumes the configured owner/operation budget.

## Error and enumeration boundary

Client errors use bounded codes such as `authentication_required`, `forbidden`, `invalid_request`, `not_found`, `conflict`, `idempotency_conflict`, `idempotency_unavailable`, `rate_limited`, and `internal_error`. They do not include raw exception text, owner IDs, subjects, session IDs, credentials, request bodies, foreign object existence, SQL details, or internal stack information.

Unknown routes are rejected before principal resolution. Foreign and absent tenant objects are indistinguishable. Authentication-provider outage and rate-limiter outage remain explicit safe failures. Production logging must use a separately reviewed redaction schema and must not log the pepper, raw Clerk artifacts, provider credentials, CSRF value, pairing secret, or full request body.

The local idempotency implementation proves transaction, encrypted-envelope, and bounded key-rotation semantics only. It is not proof that a multi-instance production adapter, protected secret manager, production datastore, backup, failover region, or real rotation runbook preserves those properties.

## Production adapter checklist

Before any authenticated tester or public traffic, the operator-owned integration must prove all of the following against the exact deployment digest:

1. Clerk production issuer, keys, cookie/session mode, and allowed redirect/origin are configured through the protected console.
2. The adapter cryptographically verifies the live Clerk session and constructs `VerifiedBrowserPrincipal` only from verified server-side claims.
3. The production owner pepper is provisioned in server-side secret custody and never appears in source, logs, browser bundles, evidence packs, or test fixtures.
4. Only the browser gateway can call owner-scoped hosted handlers from the public service.
5. Edge/IP controls and a durable atomic owner/operation limiter are active, observable, and tested for fail-closed degradation.
6. The one-active/two-retiring production idempotency keyring has protected custody, staged rotation, rollback, retirement, and restore procedures; every instance shares the exact configuration, and the production store passes same-request replay, request-mismatch conflict, concurrency, rollback, restart, tamper, key-ID substitution, expiry, and account-deletion conformance.
7. CSRF cookie attributes, trusted proxy/origin normalization, CSP, transport security, and error redaction are independently reviewed.
8. A consented tester completes the protected journey; test state is then deleted and protected flags return to their intended state.

No local test, HTTP 200, route existence, deployment readiness state, or Clerk dashboard screenshot substitutes for these proofs.

## Validation and rollback

Run the focused adversarial contract:

```powershell
python -m unittest provider_hub_hosted.tests.test_browser_gateway -v
python -m unittest provider_hub_hosted.tests.test_browser_idempotency -v
python bin/check_builderwars_threat_model.py
```

The full local evidence pack also runs the entire hosted test directory in stage 9. A production rollout must have a separately proven rollback that removes public route exposure, revokes the deployment's secret access, restores the prior deployment digest, invalidates affected sessions if necessary, and verifies that no owner command reaches the hosted control plane. Disabling the local reference or deleting evidence is not a rollback.

Until the production checklist is complete, production browser authentication, owner mapping, owner-pepper and idempotency-key custody/rotation execution, durable rate limiting, production-store idempotency parity, public creator execution, and public launch remain held.
