# Connection preflight — candidate, not live certification

Scope: `live-arena`, draft PR29 on `codex/builderwars-portable-proof-20260904`.
No new provider credentials, configuration, subscriptions or model spend were used.

## Tester path

1. Open Connections and select an OpenRouter contender. Choose a model and advertised effort, then enter your own inference API key. A consumer subscription is not generic API credit.
2. Choose **Check connection · no model call**. BuilderWars sends an authenticated GET to OpenRouter's `/api/v1/key`, never a chat completion. The result reports key recognition and any reported exhausted allowance warning, but does not promise model entitlement, rate-limit availability, final pricing or successful inference. Management/provisioning keys are rejected. Account labels and account identifiers are discarded, not rendered or persisted.
3. **Use contender** saves the current configuration in this tab after local validation; it does not start play. Before that contender's first move, BuilderWars performs the same non-inference preflight. Successful checks may be reused for the same Agent/configuration for up to 60 seconds. A failed preflight prevents the model POST. The provider still enforces actual access and usage on every inference request.
4. Set a small move/token cap in Arena and inspect provider-side budgets before explicitly starting a game. Browser cancellation is not a guarantee that an already submitted inference stops billing. Automatic preflight timeouts say 15 seconds/no model invoked; model-request timeouts remain separate.
5. A requested model/effort remains a declaration. If a move response omits its model ID, the record says `provider/unreported` or `harness/unreported`, not the requested model name. A returned label is still not independent identity attestation.

## Customer-local route

Use the documented supported local client/bridge startup from `live-arena/README.md`, with the exact site origin and an explicit bounded `--max-calls`. Do not start or authorize paid clients merely to run this check.

- Move URL: `http://127.0.0.1:8765/move`; temporary local token required.
- This bridge version exposes `GET /health`, restricted by the same exact Origin, Host and bearer token as `/move`. Its response is `builderwars.bridge.health.v1`, remaining session call count and busy state only. It does not invoke the backend, consume a call or disclose model configuration, prompts, credentials or provider output.
- An exhausted or busy health response stops a new preflight. Health is an advisory snapshot; `/move` remains responsible for serial execution and enforcing the actual cap.
- Model and reasoning configuration are selected in the local client at startup. Website labels do not change that configuration. Client entitlement and actual execution are not proven by a reachable bridge.
- Older bridges without `/health` need updating. Chromium local-network permission may be needed; other browsers and subscription clients remain separately unverified. Claude Code subscription execution is not offered by this route.
- A custom HTTPS harness receives URL/configuration validation only. There is no assumed universal health protocol: BuilderWars does not probe arbitrary URLs or send a fabricated paid move for testing. The UI explicitly calls its authentication, connectivity, CORS and limits unchecked.

## Safety and failure behavior

Checks omit browser credentials/cookies, reject redirects, use a 15-second deadline and a 64 KB response limit. Keys go only to the selected fixed provider or validated local bridge, not a BuilderWars server. Editing/closing the dialog aborts the displayed probe; snapshot and generation checks prevent stale success. The helper independently rejects changed/forgotten/overlapped credentials before populating its short-lived cache. Forgetting clears the active Agent's cache as well as its key. No check result is a durable authorization receipt.

UI tests cover 401/429/500 before inference, explicit check without POST, account-data stripping, late success after editing, an accelerated synthetic timeout, no implicit generic-HTTPS probe and 320/390/768px connection-dialog layout. Node regressions cover parameter validation, bounded/malformed responses, management keys, unknown returned identity, deadline/cancel races, cache expiry, credential mutation, forgetting and overlapping forced checks. Python bridge tests use isolated ephemeral ports to verify exact Origin/Host/token restrictions, no backend call and no cap consumption during health checks.

## Evidence and limits

- Candidate: 57 Node tests, TypeScript/production build and six bridge tests pass. Existing browser/lifecycle/recovery/proof/sharing/Academy journeys pass; focused connection and lifecycle browser journeys reran after review fixes.
- Focused read-only review found two P2s: stale credential-cache population and incorrect model-timeout copy for preflight. Both fixed, regression-tested and independently confirmed resolved. This does not satisfy the pending cross-family production-release review.
- A credential-free OPTIONS request on 2026-09-05T03:11Z returned 204 with GET and Authorization allowed and `Access-Control-Allow-Origin: *` at the real OpenRouter key endpoint. That proves the observed preflight policy, not key validity, model access or future uptime.
- All authenticated game/provider responses in this pass were synthetic interceptions; actual game-provider calls and new spend: zero. The existing unrelated listener on local port8765 was left untouched. A real browser-to-current-customer-client smoke test was not performed; isolated HTTP bridge tests are not that receipt.
- Referee executable digest remains `d5135878ce69345f5e8ee214c03d53cd1593052b9bcb97d1a96363f9b6dfa823`. Historical proofs and separate PR27 remain untouched. No merge, deployment, DNS, protected flag, customer outreach or scheduler change.

Source: [OpenRouter current-key API](https://openrouter.ai/docs/api/api-reference/api-keys/get-current-api-key), refreshed for this implementation. Model parameter support continues to come from the existing current catalog.
