# PR29 review resolution and remaining launch work

Candidate lineage: `a85f6818285a42ad94ce0351117fea98ed63653f` plus this review-fix increment. This is not a production release receipt.

## Review received

Claude's studio note `20260904-2006000700-review-result--builderwars-pr29--e3a56b6--independent-review--no.md` reviews the earlier `ffa9ccc..e3a56b6` diff. It reports a Gemini adversarial pass followed by Claude verification, with a **FIX-FIRST** verdict. That note is useful cross-family review evidence for its named source, not blanket approval for later Academy/preflight changes. Its model identity is reported by the producing surface; this lane did not independently attest the remote runtime.

1. **Suggested public-replay credential leak:** refuted by the review and source inspection. `safeReplay` first calls the authoritative `replay`, which rebuilds public fields. The sharing regression now injects `key`, `endpoint`, and `accountId` and proves none reaches the share object. Private strategy and commentary remain stripped.
2. **Arbitrary bot declaration looks like a trusted built-in:** reproduced by a failing regression, then fixed at the presentation boundary. A legal legacy proof with an arbitrary bot model remains replayable, but now reads “Unrecognized bot declaration”. Known names read “Declared built-in” in summaries/cards/replays. Spectator seats no longer use the “You” or trusted built-in avatar/label. Even an allowlisted name would not prove who executed it, so tightening an allowlist in the referee is not an identity attestation. The referee bytes, digest and historical proof contract remain unchanged.
3. **Browser paths absent from CI:** valid coverage gap. The existing Windows/Linux Node job is retained; this increment adds bounded browser execution against a production preview. See the workflow and runner for the exact covered journeys and external-signaling exclusions; do not equate this with real-customer or provider certification.
4. **Shared replay can replace current work:** same-tab fragment loading now asks before replacing an unfinished own match or a running/pending session. Declining keeps the board/contenders unchanged. Browser regression exercises decline and accept with device persistence opted out. Fresh recipients still open directly; replay mode never starts paid calls. This does not prevent normal browser navigation from closing a tab or promise recovery when storage is unavailable.

## Local evidence

- 58 Node tests, six ephemeral-port Python bridge tests and production TypeScript/Vite build pass.
- Sharing browser regression passes: private-field stripping, image download, clean replay/runback, no inherited paid connections, replay-replacement consent, truthful unknown entrant declarations and clipboard failure.
- The complete proof journey passes separately in Chromium, Firefox and WebKit: browser export, standalone Node verification, clean-context import, replay stepping, re-export origin, tamper rejection, free routing, production CSP/SRI and 320px layout. Browser engines are automated on Windows, not physical iOS/Android devices.
- `python tests/run_browser_ci.py` passes locally with pinned Python Playwright1.58.0. It starts an owned strict-port production preview, runs six bridge tests and six Chromium journeys, then repeats proof in Firefox/WebKit sequentially. Browser HTTP requests outside the preview origin are blocked unless intercepted by the synthetic test; WebSocket requests are closed. Processes have bounded waits and cleanup. The CI Linux job uses an isolated Python virtual environment and leaves the Windows/Linux Node jobs intact. Real PeerJS signaling and `recovery.py` remain a separate local integration gate, not silently mocked CI coverage.
- Referee digest: `d5135878ce69345f5e8ee214c03d53cd1593052b9bcb97d1a96363f9b6dfa823`.
- No game-provider requests, spend, DNS, production settings, social posts or customer data changed. Exact-head CI and deployment must be checked after the commit; prior green heads do not count.

## Launch audit: still incomplete

This table keeps the original five-day scope visible; it does not redefine completion around the current candidate.

| Requirement | Current evidence / remaining work |
| --- | --- |
| Free play within two actions | Existing quick-play route and browser free-routing assertions; exact release and external usability observations still separate. |
| One rules authority and portable familiar-game proof | Connect Four browser/Node artifact, invalid turn/result/version/hash tests and legacy replay compatibility. Rules proof is not model identity proof. |
| Minimal record metadata | Version, digest, game rules, move cap, entrant/model declarations and reported move metrics exist. Separate builder/agent/harness/provider declarations, fixture/randomness and token-resource metadata need explicit reconciliation with the separately owned PR27 contract before calling the full record requirement done. |
| Replay, card, safe rematch and clip | Implemented and browser-tested; genuine built-in demo and social drafts exist. Same-model/different-harness and cost/effort narratives remain held pending eligible real evidence, not fabricated demonstrations. |
| Supported connection route | Non-inference OpenRouter/local-bridge checks and bounded synthetic protocol tests. Real customer-client execution remains an explicitly unverified conditional cell; do not block free play on invented customer participation. |
| Useful fair comparisons | Seat swaps, complete pairs, failures, accepted latency/tokens/cost and bounded Academy exercise exist. Explicit configuration round-trip and one-change comparison workflow still need implementation; current profile export alone is not import support. Comparison rule/fixture/resource context needs a final rendered audit. |
| Mobile/accessibility/failure cases | Chromium/Firefox/WebKit proof plus existing viewport/failure journeys. Complete keyboard/touch/contrast and failure-matrix audit still required; physical-device evidence unavailable in this pass. |
| Conditional hosting/PWA | Not shipped by this increment. Refresh the short eligible-infrastructure preflight once, record exact held conditions; do not add unsafe hosting or caches to satisfy a checkbox. |
| Release and adoption | Independent review of later material changes, exact-source merge/deploy/canonical/redirect/rollback receipts, tester instructions and adoption readout or exact unavailable input remain required. External testers, WVRB and viral reach are unmeasured. |

Next: finish and verify the browser CI gate, return these exact findings/resolutions to the existing Claude review lane, then implement the configuration-comparison gap and reconcile record metadata with PR27. No new scheduler or automatic model training/promotion is implied.
