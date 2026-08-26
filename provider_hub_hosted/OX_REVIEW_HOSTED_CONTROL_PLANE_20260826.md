# Ox Alpha MAX exact-byte review: AgentWars hosted control plane

Audit the actual immutable committed source at BuilderWars HEAD `679357e` (full SHA must be taken from the supplied Git evidence). Produce the review now from attached evidence; do not emit a preamble, defer, request tools, or assume omitted web/account code exists.

## Authority

- Read only. Do not edit, run commands, request tools, contact providers, use credentials, deploy, publish, or mutate Git.
- Audit only the new additive files: `store.py`, `verify.py`, `handlers.py`, `tests/test_control_plane.py`, `__init__.py`, and the release truth boundary.
- The hosted service must never receive consumer passwords, browser cookies, provider refresh tokens, CLI auth stores, provider API secrets, or arbitrary customer code.
- Treat all provider/model/person/runtime/harness/match attestations as false.
- SQLite is a reference contract, not a claimed production database selection.

## Required review

Find P0/P1/P2 issues, with exact code paths and minimum corrections, across:

1. pairing-secret entropy, hash-at-rest, TTL, failed-attempt lock, duplicate claims, confirmation/rejection, key reuse, confirmation idempotency, and owner scoping;
2. Ed25519 public-key/signature canonicalization, exact-body/path/method binding, timestamp windows, verification ordering, durable nonce uniqueness, revocation races, replay and confused-deputy resistance;
3. SQLite schema/foreign keys/strict tables/WAL setup, transaction boundaries, exception rollback, multi-thread/process atomicity, retry/collision behavior, and portability to supported Python/SQLite;
4. job creation, single active lease, recovery polling, expiry/redelivery, renewal cap, abandonment, three-attempt exhaustion, result verification, mismatch semantics, duplicate/idempotent result handling, and conflict refusal;
5. public response compatibility with the existing local validators, conservative evidence labels, projection privacy, output escaping assumptions, runner/owner deletion cascade, and stale-public-data risk;
6. denial-of-service and resource limits, error disclosure, malformed/duplicate/floating JSON behavior, nonce consumption ordering, clock behavior, and concurrency tests;
7. whether the nine new tests actually prove the claimed contract and which hostile cases are missing.

Do not reject merely because account authentication, HTTP adapters, CSRF, production database provisioning, rate limiting across IP/accounts, provider execution, or deployment are explicitly outside this bounded local slice. Do reject any local contract flaw that would make later integration unsafe.

Return:

- `Executive verdict`
- `P0 findings`
- `P1 findings`
- `P2 findings`
- `Test gaps`
- `Minimum correction plan`
- `Evidence inspected`

End with exactly one standalone line and no text after it:

`VERDICT: APPROVE` only when there are no P0/P1 findings; otherwise `VERDICT: REJECT`.
