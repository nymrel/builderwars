# AgentWars hosted provider-runner control plane

Status: local reference candidate; not deployed, not wired to account auth, and not a genuine provider/model match.

## What this slice adds

`provider_hub_hosted/` is an additive, framework-independent reference for the missing hosted side of the customer-owned runner protocol:

- high-entropy pairing challenges stored only as domain-separated hashes;
- bounded TTL, failed-claim rate lock, exact duplicate claim handling, account confirmation, and single-use consumption;
- Ed25519 request verification over the existing seven-line canonical contract;
- bounded timestamp freshness checked against an independently injected store clock, durable nonce uniqueness, runner ownership, revocation, and deletion;
- atomic fixture-job claim, lease renewal, expiry, redelivery, abandonment, exhaustion, runner-bound idempotent result completion, and conflict refusal;
- a public projection restricted to a documented allow-list that excludes owner, runner, label, provider, connection mode, harness, seed, secret, nonce, signature, and private job input;
- transactional revocation that abandons active attempts and terminalizes every unfinished runner-bound job without deleting completed evidence;
- strict signed-envelope types, exact immutable request bytes, bounded JSON depth, canonical lowercase SHA-256 commitments, and pre-nonce request-schema refusal;
- cascade deletion of runner/account private state and associated public projections.

SQLite is the deterministic local reference used to prove transaction semantics. A production database adapter must preserve the same uniqueness, transaction, foreign-key, and deletion guarantees; this file does not claim that SQLite has been selected as the hosted production platform.

## What remains false

The control plane stores no provider credential or provider session, calls no provider or model, and executes no customer command. It demonstrates local Ed25519 key possession and deterministic fixture conformance only. A self-consistent but incorrect fixture output is intentionally recorded as `conformance: "mismatch"` rather than rejected, so a losing or incorrect fixture run cannot disappear behind a retry. Provider account, plan entitlement, billing route, model, person, runtime, harness execution, and match execution attestations remain exactly false in runner responses and public projections.

This slice does not implement Nymrel account authentication, web/API routing, CSRF/origin enforcement, production database provisioning, production job workers, rate limiting across accounts/IPs, operational monitoring, moderation, provider authorization, deployment, signup, or a real public match.

## Local validation

```powershell
python -m py_compile provider_hub_hosted\__init__.py provider_hub_hosted\store.py provider_hub_hosted\verify.py provider_hub_hosted\handlers.py
python -m unittest discover -s provider_hub_hosted\tests -v
python -m ruff check provider_hub_hosted\store.py provider_hub_hosted\handlers.py provider_hub_hosted\verify.py provider_hub_hosted\tests\test_control_plane.py
python bin\check_agentwars_runner.py
python bin\check_provider_hub.py
```

The 25 hosted tests cover pairing claim/confirm/reject/duplicate/expiry/rate-lock, hash-only secret storage, distinct-key claim races, key reuse, wrong-owner approve/reject non-mutation, valid and replayed probes, immutable body/signature binding, strict envelope types, bounded JSON nesting, boolean/out-of-range epoch refusal, exact schemas, lowercase digests, pre-nonce rejection, independent store-clock retention defense, exact stale/future boundaries, runner/path/method/protocol binding, transactional revocation of queued and leased work, owner scoping, 20-round concurrent atomic poll recovery, lease renewal caps, result acceptance after the original deadline, refused renew/result row immutability, abandonment, three-epoch expiry/redelivery/exhaustion, immutable recorded result mismatch, foreign/late/abandoned result refusal, conflict/idempotency, allow-list public projection, cascade deletion, and preservation of another tenant's runner and public replay.

The full provider-hub checker passed all 10 sections in 122.6 seconds, including
42-file compilation and every runner, publication, scale, share, product, Ten
Fronts, fantasy, self-check, and verifier regression rung.

## Independent Max acceptance

Ox Alpha MAX run `51119615-11ef-4962-b223-c368e1884485` reviewed the exact
four-file source diff against base
`6330c5b673589eac69ffcb3fb00c16c6973baa61`. It returned P0 `0`, P1 `0`, P2
`0`, P3 `5`, and `VERDICT: APPROVE`. The accepted output SHA-256 is
`ac587924a22c1193d976a6086595d028995bdd0f6b3eace0536ade061d8c98d0`; the
receipt SHA-256 is
`891107e08a1dfc300a6b4460fc8bba88b4f080e9318b3dfafba3afd17bbbe491`.
The exact source hashes and P3 dispositions are recorded in
`provider_hub_hosted/OX_REVIEW_HOSTED_CONTROL_PLANE_20260826.md`.

## Next integration gate

Wire these pure handlers behind authenticated Nymrel routes only after an adapter maps the signed-in account to the opaque owner id, preserves exact request bytes and headers, adds account/IP rate limits plus CSRF/origin controls for browser actions, and provides a production datastore with equivalent atomic constraints. That integration must pass signed-out and signed-in browser/API tests without moving any customer provider credential into Nymrel custody.
