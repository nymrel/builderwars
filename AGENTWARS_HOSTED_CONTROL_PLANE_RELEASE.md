# AgentWars hosted provider-runner control plane

Status: local reference candidate; not deployed, not wired to account auth, and not a genuine provider/model match.

## What this slice adds

`provider_hub_hosted/` is an additive, framework-independent reference for the missing hosted side of the customer-owned runner protocol:

- high-entropy pairing challenges stored only as domain-separated hashes;
- bounded TTL, failed-claim rate lock, exact duplicate claim handling, account confirmation, and single-use consumption;
- Ed25519 request verification over the existing seven-line canonical contract;
- bounded timestamp freshness, durable nonce uniqueness, runner ownership, revocation, and deletion;
- atomic fixture-job claim, lease renewal, expiry, redelivery, abandonment, exhaustion, idempotent result completion, and conflict refusal;
- a privacy-safe public projection that excludes owner, runner, label, provider, connection mode, harness, seed, secret, nonce, signature, and private job input;
- cascade deletion of runner/account private state and associated public projections.

SQLite is the deterministic local reference used to prove transaction semantics. A production database adapter must preserve the same uniqueness, transaction, foreign-key, and deletion guarantees; this file does not claim that SQLite has been selected as the hosted production platform.

## What remains false

The control plane stores no provider credential or provider session, calls no provider or model, and executes no customer command. It proves local Ed25519 key possession and deterministic fixture conformance only. Provider account, plan entitlement, billing route, model, person, runtime, harness execution, and match execution attestations remain exactly false in runner responses and public projections.

This slice does not implement Nymrel account authentication, web/API routing, CSRF/origin enforcement, production database provisioning, production job workers, rate limiting across accounts/IPs, operational monitoring, moderation, provider authorization, deployment, signup, or a real public match.

## Local validation

```powershell
python -m py_compile provider_hub_hosted\__init__.py provider_hub_hosted\store.py provider_hub_hosted\verify.py provider_hub_hosted\handlers.py
python -m unittest discover -s provider_hub_hosted\tests -v
python bin\check_agentwars_runner.py
python bin\check_provider_hub.py --skip-regressions
```

The new tests cover pairing claim/confirm/duplicate/expiry/rate-lock, hash-only secret storage, valid and replayed probes, stale/future/bad signatures, revocation, owner scoping, concurrent atomic poll recovery, lease renewal caps, abandonment, three-epoch expiry/redelivery/exhaustion, result mismatch/conflict/idempotency, privacy-safe projection, and cascade deletion.

## Next integration gate

Wire these pure handlers behind authenticated Nymrel routes only after an adapter maps the signed-in account to the opaque owner id, preserves exact request bytes and headers, adds account/IP rate limits plus CSRF/origin controls for browser actions, and provides a production datastore with equivalent atomic constraints. That integration must pass signed-out and signed-in browser/API tests without moving any customer provider credential into Nymrel custody.
