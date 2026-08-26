# AgentWars provider-runner control-plane audit acceptance

Date: 2026-08-26 PT

Status: `ACCEPTED_FOR_BOUNDED_IMPLEMENTATION`

## Immutable review

- BuilderWars HEAD: `dc7775ddd4d3ce6b2f964161f49f9a927c3919c7`
- accepted Ox Alpha MAX run: `4d4f3300-7686-4838-9b90-7e17215bc88f`
- task packet SHA-256: `5885147af7f80bbf41764f5d3b3eb92247a931bec50edca8f6811a873a97d49d`
- receipt SHA-256: `45d69d13fdcd815714d4f485486236a8422ff795976c332780691b178ce70f96`
- terminal verdict: `VERDICT: READY_FOR_NEXT_SLICE`
- connector: `opencode-go / ox-alpha-free / max`, no fallback
- authority/profile: read-only explorer
- source snapshot: immutable Git objects at the exact HEAD above
- VCS guard: pass; HEAD, ref, and index digest unchanged
- tool calls: 0
- cleanup: pass; retained worker processes 0
- provider seat: released

The earlier broad run `dafba178-7783-4db7-8bfc-bba1218bae42` is non-accepting because it returned only a preamble rather than the required audit. Process completion was not treated as review evidence.

## Accepted blocker model

The existing client contracts prove bounded local signing/key-possession behavior and a deterministic fixture. They do not prove a hosted control plane, durable queue, provider hop, provider/model identity, public deployment, or customer account flow.

Before any second-party beta exposure, the hosted path requires:

1. durable nonce uniqueness plus a bounded signature-freshness window;
2. a durable atomic claim/lease/redelivery store;
3. a complete pairing-confirmation contract with hash-at-rest, TTL, single use, and rate bounds;
4. runner revocation and rotation semantics;
5. idempotent result completion;
6. owner-scoped runner/job access, deletion, and privacy-safe projection.

## Selected implementation slice

Add a pure, framework-independent `provider_hub_hosted/` reference control plane and tests. The slice may use a disposable SQLite database for deterministic local verification but must define storage semantics that a production adapter can preserve:

- pairing challenges store only a hash, expire, and are consumed exactly once on confirmation;
- every signed request enforces runner ownership/state, bounded clock skew, and durable unique nonce insertion;
- job claim, renewal, expiry, redelivery, completion, duplication, abandonment, and exhaustion are atomic and fail closed;
- public replay projection excludes account, runner, label, pairing, nonce, signature, secret, seed, and private provider fields;
- runner revocation blocks all subsequent signed work;
- owner deletion cascades private state and removes public projections;
- provider/model/harness declarations and all attestation flags remain conservative.

This slice needs no credential, operator account action, provider contact, external service, deployment, or arbitrary-code execution. It is additive and reversible.

## Truth boundary

Acceptance of this audit does not claim that the recommended implementation exists, that SQLite is the production service, that real Redis behavior has been proved, that a provider/model executed, that a user signed up, that a match was genuine, or that AgentWars is deployed or publicly launched. Each remains a separate evidence gate.

## Implementation correction round 1

Status: `CORRECTED_PENDING_FRESH_EXACT_BYTE_REVIEW`

- Original implementation commit: `679357e95647563360de5b6b6f97c25188f4a644`.
- Corrected implementation commit: `884bfa756f16996bdbf8701b8aa99370ecd90a75`.
- Ox pairing/nonce review `33fcb8d1-c35b-422c-a1f4-ce514cb7939a`: `VERDICT: REJECT`; one P1 on the store trusting an observation clock supplied by its caller.
- Ox signed-boundary review `7d5cd1e6-3c8d-4033-a97a-1901b0344379`: `VERDICT: APPROVE`; no P0/P1.
- Ox hostile-test review `e0540733-d251-41ea-8037-661aa7720517`: `VERDICT: REJECT`; seven P1 test-gate gaps.
- Every accepting review used `opencode-go / ox-alpha-free / max`, no fallback, immutable Git-object evidence, zero tools, unchanged VCS, passed cleanup, and a released provider seat.

The correction moves request-age constants into the transactional store contract, derives nonce observation time from an independently injected store clock, validates the nonce again at the store boundary, binds duplicate result receipts to the job runner, requires exact POST methods on runner mutation handlers, normalizes parsing failures, rejects unknown poll terminal states, and preserves the job creation timestamp across joined rows.

The hosted suite now has 15 tests. New hostile coverage proves distinct-key claim races, reject/confirm idempotency, cross-owner key reuse refusal, nonce-retention clock-jump defense, 20 repeated two-poller races, mismatch recording, foreign/late/wrong-attempt/abandoned result refusal, key/runner/path/method/protocol binding, invalid UTF-8 rejection before nonce use, and cross-owner delete isolation. Incorrect self-consistent output remains an accepted result with `conformance: "mismatch"`; this is intentional competitive truth, because rejecting it would let a losing runner hide behind retries.

Local verification after `884bfa756f16996bdbf8701b8aa99370ecd90a75`:

- hosted unit suite: `15/15 PASS`;
- AgentWars runner verifier: `154 PASS`;
- Provider Hub full verifier: all 10 sections and downstream regression ladder PASS;
- AgentWars public product contracts: PASS;
- AgentWars scale contracts: PASS.

This correction is not accepted for hosted integration until a fresh immutable capsule of the corrected bytes receives zero P0/P1 from Ox Alpha MAX. It still proves no provider/model execution, production storage, authenticated account adapter, deployment, signup, or genuine public match.
