# Ox Alpha MAX: provider-runner control-plane audit

Produce the audit now from the immutable evidence attached to this request. Do not emit a preamble, ask to read more, call a tool, or defer the answer.

Audit Git HEAD `dc7775ddd4d3ce6b2f964161f49f9a927c3919c7` using only these exact source contracts:

- `AGENTWARS_PROVIDER_HUB_RELEASE.md`
- `docs/AGENTWARS_PROVIDER_CONNECTION_V2_PACKET.md`
- `docs/AGENTWARS_PROVIDER_POLICY.v2.json`
- `provider_hub/schemas.py`
- `provider_hub/signing.py`
- `provider_hub/runner_state.py`
- `provider_hub/local_runner.py`
- `provider_hub/match_worker.py`

Read only. Do not mutate files or Git, run commands, request tools, use credentials, contact providers, deploy, or publish. Consumer passwords, browser cookies, refresh tokens, CLI auth stores, and provider secrets must never enter the hosted service. Unsafe arbitrary customer code remains disabled for public beta. Provider/model/harness declarations remain unattested unless exact evidence proves otherwise.

Goal: define the smallest production-grade bridge from the existing Python contracts to a testable hosted beta where a signed-in customer can pair and revoke a customer-owned local runner, submit one bounded match job, receive a result, and publish only a privacy-safe replay projection. No provider account action is available in this slice.

Return:

1. current exact capabilities and truth limits;
2. P0/P1 issues in pairing, challenge replay, key rotation/revocation, runner liveness, job claim/lease/ack/redelivery, idempotency, durable storage, deletion, privacy, and publication;
3. an explicit browser -> hosted control plane -> durable queue/store -> local runner -> provider -> result -> public replay message sequence, naming which fields are signed and which identities remain self-declared;
4. exactly one reversible next implementation slice that needs no credentials, operator account action, external service, or deployment; name exact contracts/files and tests;
5. a compact acceptance matrix for pair, revoke, submit, claim, renew, complete, retry, expire, replay, delete, and malicious/replayed messages;
6. any secret-leak, replay, confused-deputy, untrusted-code, false-attestation, job-loss, or privacy finding with severity and minimum correction.

Do not recommend a rewrite. Do not assume the separate Nymrel web app implements anything.

End with exactly one standalone line and no text after it:

`VERDICT: READY_FOR_NEXT_SLICE` if the bounded implementation slice can safely proceed, otherwise `VERDICT: STOP`.
