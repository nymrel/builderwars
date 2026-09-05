# BuilderWars: web, iOS and Android execution

Operator scope expansion, September 4, 2026 (America/Los_Angeles).

Deliver one coherent BuilderWars product across the web, iPhone/iPad and Android,
with enjoyable competition, useful builder tools and inspectable evidence.
Industry leadership is the ambition, not a deliverable an engineering run can
certify. App Store and Google Play acceptance, adoption and competitive standing
are separate outcomes.

This addendum supersedes the five-day beta contract's native-app deferral for
new work. It does not change that frozen v1 document/hash, declare the active
goal complete, schedule background work, or waive its safety and proof gates.
Finish its deployable web increment while developing the native lane.

## Starting point and next increment

The named worktree starts this expansion at `94727b168432f7ddfbc711dab27f7fbfab714570`.
Its exact hosted CI passes Linux/Windows checks and Chromium/Firefox/WebKit proof
journeys. This does not certify physical devices. PR29 is a candidate, not a
production release. The older `mobile-arena` is a browser prototype donor; the
repo has no generated iOS or Android project at this checkpoint.

First shared improvement: strict versioned/legacy agent profile import, export
of the edited draft, and a saved-versus-draft settings comparison. Imports never
start calls; keys/endpoints are cleared; applying to an unfinished game requires
consent. Strategy is intentionally included in local profile files with an
explicit privacy warning. A one-setting difference is not proof of controlled
experiments: endpoints, external harness versions, rules and resources still
need matched evaluation. No weights are trained or improved automatically.

## Implementation direction

Use the canonical Vite/TypeScript arena with bundled Capacitor assets for the
first native vertical slice. This is a provisional engineering choice, supported
by a bounded independent architecture review, not a claim of native quality.
It preserves the tested UI and referee instead of creating another prototype.
Expo/React Native is the alternative if device UX/performance reveals a concrete
ceiling; its native view path would require rebuilding this vanilla DOM UI.
Expo DOM reuse itself adds a WebView and asynchronous bridge.

Sources checked September 4: [Capacitor configuration](https://capacitorjs.com/docs/config),
[environment setup](https://capacitorjs.com/docs/getting-started/environment-setup),
[Expo DOM architecture](https://docs.expo.dev/guides/dom-components/).
Registry preflight resolved Capacitor core/CLI 8.5.1. No dependency installed by
that read. Node 22.17.0 is available. `java`, `adb` and `xcodebuild` were not on
PATH; the standard local Android SDK/Studio locations were absent. This only
describes this Windows surface, not every available build host.

## Ordered delivery gates

| Milestone | Work | Exit evidence |
|---|---|---|
| A. Shared beta | Complete profiles, metadata compatibility, review fixes, failure/accessibility coverage; release current web increment | Exact-source green CI, independent review, canonical browser proof, rollback |
| B. Native offline vertical slice | Bundled local arena, free/human play, recent public matches, proof import/export, share sheet, safe-area/back/keyboard handling | Unsigned build where supported, actual Android and iOS emulator/device execution, native-to-web replay round trip |
| C. Native network parity | Explicit connection preflight, HTTPS harness, capped calls, spectator join/disconnect, interruption/recovery | Synthetic boundary suite first; separately authorized real provider test; no extra call after background/resume |
| D. Tester distribution | Signed release builds, real-device matrix, privacy/data inventory, accurate screenshots/descriptions, support and deletion paths where applicable | TestFlight and Play internal-testing installation receipts, crash/ANR and accessibility checks; store/account/signing custody independently verified |
| E. Public launch | Resolve tester failures, store submission/review, staged rollout and rollback/update instructions | Actual accepted listings and installable versions, source/build binding, web canonical proof; no inferred approval |
| F. Retention and differentiation | Improve onboarding from observations, meaningful builder revisions, fair divisions, creator admission, hosted tournaments | Consented first-match/share/rematch observations, returning builders, verified matches and resource-normalized comparisons |

Near-term work blocks: shared beta and native adapters first, then one Android
debug build and one iOS simulator build through a suitable existing host. Do not
promise all stores within days: device access, platform signing and external
review determine calendar time. Review progress after each validated increment,
not after adding another roadmap. Keep one integrator and at most one disjoint
implementation lane; request one cross-family material review at acceptance.

## Native boundaries that must be implemented and tested

- Public replay/setup/watch links use the canonical website, never a packaged
  localhost origin. Local previews retain their explicit testing routes.
- Bounded file exports use app cache and the native share sheet; cancellation
  is not reported as a completed share. Preserve the matching portable verifier.
- Pause invalidates active runs, aborts pending requests, stores only permitted
  public recovery data and disconnects broadcasting. Resume paused, never with
  automatic paid calls. OS background behavior is not hosted execution.
- Keep provider keys in memory. Disable the desktop loopback bridge on phones;
  localhost means the phone. Do not expose LAN ports or create tunnels silently.
- Bundle a tested content policy: Vercel response headers do not travel with
  installed assets. Do not load remote pages into a privileged native bridge.
  Keep native HTTP fetch patching disabled until its security semantics pass.
- Load the exact digest-addressed referee and fail closed on tampering in both
  WebViews. Never relabel a rebuilt engine with the browser artifact's digest.
- Add only justified permissions. No default contacts, camera, microphone,
  tracking, push notifications or background inference. Store declarations must
  describe the actual shipped code and SDKs, not desired future behavior.

## Quality and efficiency acceptance

Every surface must prove free play, clear outcome, replay recovery, export/import,
safe rematch, configuration failure paths, offline behavior and interruption.
Use real screen readers/large text/touch/keyboard and reduced motion in addition
to viewport automation. Require no unresolved critical security, data-loss or
core-play defect. Measure startup and input latency on a named mid-range Android
device and supported iPhone; record baseline before setting device-specific budgets.

Leadership claims require a declared competitor set, repeatable user-task
comparison and actual participation—not screenshots, model names or store presence.
Track completion, return, replay comprehension and verified builder activity;
unknown adoption/cost remains unknown. For now use the existing small tester
experiment, excluding our automated fixtures and studio accounts.

Stop expanding a failing slice after two unsuccessful repairs and checkpoint
the exact dependency; continue disjoint work. Missing credentials on this
surface are routing evidence, not an invented universal operator blocker.
No new purchases, legal acceptance, identity changes, production secrets, DNS,
outbound posts or store attestations are implied by a successful local build.
Never attest that a human completed an action. Resolve exact protected actions
through current authorized custody when the release actually reaches them.

## Completion reporting

Report each surface independently: source implemented, local checks, device
checks, signed artifact, tester distribution, public publication and observed
usage. Retain known limitations. Do not mark the campaign complete because a
time or token budget elapsed, or claim all three are launched from a web deploy.

Next native action: implement and test canonical-link, file-export and lifecycle
adapters before generating store-oriented projects; verify available build hosts
without starting account setup or buying capacity.

### First checkpoint

Canonical-link adapter is implemented: packaged `capacitor://localhost` and
default localhost WebView origins resolve to the website; explicit browser
preview ports retain their origin. Unit tests reject unknown schemes and
credential-bearing bases. Native file export and lifecycle adapters are next.

Local validation: 64 Node tests, production build, six bridge tests, seven
Chromium journeys and Firefox/WebKit proof journeys passed. Profile browser
coverage includes invalid/cancelled imports, key clearing, unsupported model/
effort preservation, edited-draft export, changed-setting counts, and declined/
accepted reset of an unfinished match. Two existing tests needed explicit reset
consent after the new safeguard. Referee digest is unchanged. This checkpoint
does not certify real provider calls, native WebViews, device quality or stores.

### Native foundation checkpoint — September 4, 2026, 21:48 PDT

Android and iOS projects are now generated under `live-arena`, using bundled
`dist-native` assets. This supersedes the earlier no-project/no-install snapshot.
Core/platform packages are pinned to Capacitor 8.5.1 and App to 8.1.1; CLI 8.4.3
avoids the moderate `xcode`/`uuid` dependency advisory observed with CLI 8.5.1.
Both full and production-only npm audit returned zero vulnerabilities at this
checkpoint. That is a dependency audit result, not a security certification.

Implemented and locally checked: native-only bundled CSP, no remote app shell,
disabled native HTTP/cookie patching, no cleartext/mixed content or WebView debug,
Android backup disabled, and cache-only future export FileProvider scope.
Pause invalidates/aborts runs, closes broadcasts, and ignores late responses.
Foreground return never restarts model calls. Native harness configuration rejects
desktop loopback endpoints and requires HTTPS. Registration-time pause races and
loopback aliases have explicit regression tests. Windows-generated Swift package
paths are normalized for macOS builds by the repeatable native-sync helper.

Local web/native builds, Node tests, native project sync, packaged-asset synthetic
lifecycle checks and portable proof round trip pass. The synthetic bridge suite
uses intercepted requests and is not a real provider or device test. The full web
browser gate also passed before the final two native-only review repairs.

CI now includes Android debug APK and unsigned iOS simulator compilation on
standard hosted runners, with bounded artifacts and no store credentials. At
this checkpoint those new jobs are configured, not yet verified remotely. The
Android job uses the installed SDK and disables SDK downloading; it contains no
license-acceptance command. The iOS job disables signing. The local application
identifier `com.nymrel.builderwars` is not a store-registration receipt.

Still unfinished: native cache/share-sheet export, actual native file import,
safe-area/back/keyboard and physical-device checks, offline recovery on devices,
product icons/splash (generated template assets remain), signed tester builds,
privacy/store declarations and accepted listings. No store publication or native
quality claim follows from generation or compilation. Next: inspect exact hosted
native build receipts, repair concrete failures, then implement native file flows.

### Hosted compile receipt — September 4, 2026, 21:53 PDT

All five jobs passed for PR29 head `44a4fec6376aead65c83cf2646ba48ff95cbfb34`:
[run 33945568353](https://github.com/nymrel/builderwars/actions/runs/33945568353).
This includes Windows/Linux unit/build, web plus synthetic native browser gates,
Android debug APK compilation, and unsigned iOS simulator compilation.
Pull-request Actions built merge checkout `2607ce4cbe735caf144a4e878033f699f5bcd23b`;
artifact names bind to that checkout, while the run's head is the candidate above.

- Android artifact ID `9963229855`; archive digest
  `sha256:8c7529167571669e84a4f357a79df244abc4521e8b98c0ee27219a3f51218605`.
- iOS simulator artifact ID `9963222528`; archive digest
  `sha256:516f344d869c6829906166d3105e775dc1e3ff7d5a74c05c76b8b4792569e6af`.

Artifacts expire after seven days. Neither is a signed store release. A bounded
iPhone-simulator launch/screenshot job is the next inspection step; it selects
one preinstalled shutdown device, never downloads a runtime, and closes only its
selected device. Screenshot capture alone is not successful user-flow proof.
