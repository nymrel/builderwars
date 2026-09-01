# AgentWars browser authorization boundary

Status: local, framework-neutral security reference. This contract is designed to make a future production HTTP adapter small, reviewable, and deny-by-default. It is not live Clerk integration, a production session, a durable perimeter, or production security approval.

## Status and authority boundary

`provider_hub_hosted/browser_gateway.py` is the only reviewed browser-to-owner-command reference in this repository. It accepts sanitized request facts plus an injected `VerifiedBrowserPrincipal`; it never verifies or stores a Clerk cookie itself. The production adapter, Clerk configuration, owner pepper, durable rate limiter, production store, and public route exposure remain protected work.

All production authority flags remain false. This slice does not accept terms, attest a human action, provision secrets, mutate a customer or production database, change DNS, enable public creator execution, incur paid compute, or promote a deployment. BuilderWars.com apex and www remain untouched.

## Exact browser request contract

`BrowserRequest` has exactly seven fields:

- `method`
- `path`
- raw byte `body`
- exact `origin`
- `content_type`
- `csrf_cookie`
- `csrf_header`

The request carries no session cookie, bearer token, or owner id. It cannot contain a provider credential, Clerk token, client-selected tenant, arbitrary header map, query string, or redirect target. The gateway accepts only `POST` and `DELETE`, rejects bodies larger than 16 KiB, rejects unknown routes before resolving a principal, and parses JSON with duplicate-key, float, non-finite-number, UTF-8, unknown-key, and non-object rejection.

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

## Error and enumeration boundary

Client errors use bounded codes such as `authentication_required`, `forbidden`, `invalid_request`, `not_found`, `conflict`, `rate_limited`, and `internal_error`. They do not include raw exception text, owner IDs, subjects, session IDs, credentials, request bodies, foreign object existence, SQL details, or internal stack information.

Unknown routes are rejected before principal resolution. Foreign and absent tenant objects are indistinguishable. Authentication-provider outage and rate-limiter outage remain explicit safe failures. Production logging must use a separately reviewed redaction schema and must not log the pepper, raw Clerk artifacts, provider credentials, CSRF value, pairing secret, or full request body.

Idempotency is not implemented in this local gateway. The production adapter must supply and persist bounded idempotency semantics for retried destructive or job-creation operations before public exposure.

## Production adapter checklist

Before any authenticated tester or public traffic, the operator-owned integration must prove all of the following against the exact deployment digest:

1. Clerk production issuer, keys, cookie/session mode, and allowed redirect/origin are configured through the protected console.
2. The adapter cryptographically verifies the live Clerk session and constructs `VerifiedBrowserPrincipal` only from verified server-side claims.
3. The production owner pepper is provisioned in server-side secret custody and never appears in source, logs, browser bundles, evidence packs, or test fixtures.
4. Only the browser gateway can call owner-scoped hosted handlers from the public service.
5. Edge/IP controls and a durable atomic owner/operation limiter are active, observable, and tested for fail-closed degradation.
6. Production idempotency, store, backup/restore, deletion, retention, and rollback behavior are tested.
7. CSRF cookie attributes, trusted proxy/origin normalization, CSP, transport security, and error redaction are independently reviewed.
8. A consented tester completes the protected journey; test state is then deleted and protected flags return to their intended state.

No local test, HTTP 200, route existence, deployment readiness state, or Clerk dashboard screenshot substitutes for these proofs.

## Validation and rollback

Run the focused adversarial contract:

```powershell
python -m unittest provider_hub_hosted.tests.test_browser_gateway -v
python bin/check_builderwars_threat_model.py
```

The full local evidence pack also runs the entire hosted test directory in stage 9. A production rollout must have a separately proven rollback that removes public route exposure, revokes the deployment's secret access, restores the prior deployment digest, invalidates affected sessions if necessary, and verifies that no owner command reaches the hosted control plane. Disabling the local reference or deleting evidence is not a rollback.

Until the production checklist is complete, production browser authentication, owner mapping, durable rate limiting, production store access, public creator execution, and public launch remain held.
