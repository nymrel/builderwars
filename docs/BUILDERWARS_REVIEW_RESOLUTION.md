# PR29 review resolution and remaining launch work

## Consolidated review — September 5, 2026 UTC

Fable round-trip `builderwars-learning-20260905`, turn 3, returned **approved**
for integrated application source `b553b96b8394759659324d9c03f69254fda1a4d1`.
Receipt: `C:/Users/johns/StudioData/artifacts/fable-roundtrip/builderwars-learning-20260905-turn-3.json`;
resolved runtime `claude-fable-5-1`, result hash
`4d815c2fd44bc1168d21801d5195d1b1e69940b3f872134acd16a670ff32db1a`.
It explicitly covers the previously uncovered `e3a56b6..6eaaba1` profile,
resource, package, keyboard and native-file/lifecycle delta plus learning
integration. This is source reasoning, not independent execution of tests.
Turn 2 separately approved the learning delta. The requested
`a80c64d..b553b96` check shows only `docs/BUILDERWARS_BETA_TESTER_GUIDE.md`.
Exact release-head CI and canonical deployment are still required; the earlier
dated status sections below are historical, not current launch evidence.

Non-blocking findings and disposition:

- OpenRouter authentication preflight depends on a valid key-endpoint response,
  including boolean `is_free_tier`; unexpected bodies or rate limits stop moves.
  Keep this explicit dependency and retry/free-opponent fallback. Do not silently
  bypass a failed preflight and start a billable request.
- Proof-import ordering was flagged as a possible partial update if resource
  validation throws. Inspected `verifyProof` calls `settings` before returning,
  enforcing an integer `maxPlies` in 2..400; `matchLimits(maxPlies, null)` accepts
  precisely that domain. No current reproducer survives verification. Earlier
  validation would be defensive refactoring, not a demonstrated release defect.
- Legacy bridge health 501 guidance and inactive-cell hover/focus polish remain
  small follow-ups; no automatic weaker inference or permission fallback added.
- Native share/cancel/cache and lifecycle interactions remain synthetic except
  the named iOS simulator startup receipt. Android emulator play, physical
  devices, signing and stores are unverified, not approved by this review.

The separate real-WebRTC recovery script still expected editing the cap after
play began to change that match. Reproduced its failure, then updated the test
to choose six before play, edit to nine after two moves and require recovery of
six. The entire real-browser recovery/rejoin/offline-cache journey now passes;
application code and frozen resource rules were not weakened. Other current
resource tests already cover pause, proof round trip and unknown imported caps.

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

### CI-exposed mobile defect

Hosted run33942291399 at053a140 passed both Node jobs but the new Linux browser job found 320px Arena overflow. Diagnostic-only headc61467c (run33942428935) retained the failing assertion and captured the outlying navigation button geometry. The narrowest navigation now uses five equal tracks with icons above labels, rather than relying on OS-specific font widths fitting a single row. Browser tests additionally require all five tabs to remain within the viewport and at least44px tall. No global overflow hiding or reduced assertion was used. Exact follow-up CI must pass before this defect is considered release-verified.

## Current beta acceptance checkpoint — September 5, 2026

Latest release138e5700 supersedes the production baseline in this checkpoint:
see BUILDERWARS_CONTRAST_20260905.md for exact review/CI, canonical168pairs,
twelve journeys, cross-browser proof, redirects and retained5f92f990 rollback.
Required features are delivered; final receipt integration is the remaining
closeout task. The following dated baseline and ranked future work are retained.

This section supersedes the historical open-work table below, without rewriting
its dated findings. Current production5f92f990 has all-five candidate/main CI,
independent source review, canonical artifact/redirect checks and retained rollback
availability in BUILDERWARS_RESULT_CARD_20260905.md. The preceding native-checkpoint
release receipt records the full canonical twelve-journey, cross-browser and real
PeerJS recovery passes; the only subsequent application delta fixes PNG outcome
visibility and has its own canonical sharing/replay coverage.

- Record metadata and fixed-resource/paired-condition work are implemented in
  BUILDERWARS_MATCH_PACKAGE.md and resources/profile/package tests. They no longer
  await PR27 reconciliation. Declarations remain distinct from attestation.
- Three genuine-match creative narratives now exist in the dated beta package;
  the local model duel is1–1, not a performance win. Result artwork is repaired.
- Academy, safe connections, configuration comparisons and creator exercises have
  executable browser coverage. Memory reminders are useful to inspect but showed
  no uplift in the separate3/12 versus2/12 actual diagnostic; no training claim.
- Adoption has an exact unavailable-input readout in the native-checkpoint release
  receipt. External observations, revenue and WVRB remain unmeasured.
- A new dated two-route infrastructure preflight is recorded in the persistence
  plan. Authenticated transactional private preview remains held, not promised.
- Remaining engineering closure at this checkpoint: computed contrast evidence
  and acceptance of the final test/docs candidate. PR35 prior8d66404 CI failed
  iOS simulator launch; c8b1a23 subsequently passed all five jobs in33961460460
  and PR35 merged as10791126. The earlier failure remains historical evidence.

### Ranked next backlog

1. Close the final candidate's actual CI/contrast findings and evidence audit;
   never waive a required check or change its threshold merely to finish.
2. When an exact recruitment action is authorized, collect the five-tester
   observations described in the guide. Diagnose the first-play/replay/rematch
   friction before expanding the product surface.
3. Test one versioned harness-improvement candidate against a fresh held-out set.
   Separate reminders, deterministic tools and model training; promote only on
   credible quality/resource evidence, retaining regressions and prior versions.
4. Resume one private hosted match only when its scoped runtime/auth/storage/cost
   input and safety tests clear. No anonymous uploads or always-on model claims.
5. Use day14/day30 observed participation to prioritize; native store publication,
   leagues and creator marketplace remain later gated phases, not this beta's
   missing engineering requirements. Keep the MIT engine/protocol intact.

## Historical launch audit: incomplete at that candidate

This table keeps the original five-day scope visible; it does not redefine completion around the current candidate.

| Requirement | Current evidence / remaining work |
| --- | --- |
| Free play within two actions | Existing quick-play route and browser free-routing assertions; exact release and external usability observations still separate. |
| One rules authority and portable familiar-game proof | Connect Four browser/Node artifact, invalid turn/result/version/hash tests and legacy replay compatibility. Rules proof is not model identity proof. |
| Minimal record metadata | Version, digest, game rules, move cap, entrant/model declarations and reported move metrics exist. Separate builder/agent/harness/provider declarations, fixture/randomness and token-resource metadata need explicit reconciliation with the separately owned PR27 contract before calling the full record requirement done. |
| Replay, card, safe rematch and clip | Implemented and browser-tested; genuine built-in demo and social drafts exist. Same-model/different-harness and cost/effort narratives remain held pending eligible real evidence, not fabricated demonstrations. |
| Supported connection route | Non-inference OpenRouter/local-bridge checks and bounded synthetic protocol tests. Real customer-client execution remains an explicitly unverified conditional cell; do not block free play on invented customer participation. |
| Useful fair comparisons | Profile import/export and saved-versus-draft comparison are implemented at63a8686. The next increment freezes per-match resources and renders/exports rule, standard fixture and uncontrolled-randomness context. This is not a matched-seed benchmark or automatic agent improvement. |
| Mobile/accessibility/failure cases | Chromium/Firefox/WebKit proof plus existing viewport/failure journeys. Complete keyboard/touch/contrast and failure-matrix audit still required; physical-device evidence unavailable in this pass. |
| Conditional hosting/PWA | Not shipped by this increment. Refresh the short eligible-infrastructure preflight once, record exact held conditions; do not add unsafe hosting or caches to satisfy a checkbox. |
| Release and adoption | Independent review of later material changes, exact-source merge/deploy/canonical/redirect/rollback receipts, tester instructions and adoption readout or exact unavailable input remain required. External testers, WVRB and viral reach are unmeasured. |

Next: finish and verify the browser CI gate, return these exact findings/resolutions to the existing Claude review lane, then implement the configuration-comparison gap and reconcile record metadata with PR27. No new scheduler or automatic model training/promotion is implied.

## Match resources and keyboard review — September 5 UTC

Base63a8686966cac8726e8465936316dca254360c77 has independently checked hosted CI success
(run33943405340). This new increment still needs its own exact-head CI and cross-family release review.

- Capture move/token limits once per match and retain them through pause, device recovery,
  proof cap round trips and seat-swapped series. Later field edits apply to a new match.
  Requested tokens are not a provider compute or billing guarantee.
- Store explicit known-cap state separately from fallback recovery settings. Plain imported
  or watched records must remain unknown after save/reopen. Legacy own matches retain a
  bounded recovery policy labeled as such, not as original resource evidence.
- Evaluation exports include rules, standard initial position, uncontrolled randomness,
  requested resources and exact referee version/digest. Invalid new-series inputs cannot
  overwrite completed-series conditions. Builder/harness provenance reconciliation with
  separate PR27 is still incomplete.
- Board squares have one tab stop, visual-order arrow/Home/End navigation, accessible
  labels and retained focus across human and automated turns. Temporarily unavailable
  squares remain focusable with aria-disabled; the move handler still rejects input.
  The contender dialog has an accessible title. This is not a complete WCAG certification.

One bounded independent code review found three P2 defects: unknown cap promotion after
storage, focus loss during an automated turn, and runback ignoring edited resources.
All three were corrected with browser regressions. The same reviewer rechecked those
resolutions and returned no remaining findings; its13 focused unit tests passed.
This is an independent same-family review, not a substitute for the pending cross-family
review of the full release candidate.

Local evidence:69 Node tests and production build pass; focused keyboard/touch and
resource browser journeys pass. The expanded isolated full browser gate passed all nine
Chromium journeys, six bridge tests, and Firefox/WebKit proof checks (session15142).
Exact committed source belongs in the handoff. No real model calls or charges.
The immutable referee digest remains d5135878ce69345f5e8ee214c03d53cd1593052b9bcb97d1a96363f9b6dfa823.
No production deployment, native binary, device acceptance or store listing is claimed.
