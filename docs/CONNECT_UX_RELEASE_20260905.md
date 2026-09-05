# Guided connections: production receipt

September 5, 2026. Public URL: https://builderwars.com/.

- PR42: https://github.com/nymrel/builderwars/pull/42.
- Reviewed candidate: `72d21035514b0411bd32a8997f1e92afd73aecb2`.
- Merged/released source: `50607becdda1697f9982609d3f9d438d21267bde`.
  Its application tree is identical to the candidate.
- All five candidate checks passed in
  https://github.com/nymrel/builderwars/actions/runs/33995559809:
  Linux, Windows, browser, Android debug/WebView and iOS simulator.
- Vercel project: `prj_c2HDxCRh3sEFEZkOxemiwoUmp1Gp`.
  Production deployment `dpl_AfAtZkwZAf2FcYtdSvum4tdgcesc` is READY and
  serves the canonical domain. Both provider Git SHA fields match the source.
- Deployment URL:
  https://builderwars-lwo0uiwug-jalens-projects-0ade4450.vercel.app.

## Public adoption proof

At 22:27:55 UTC, direct canonical GETs matched the exact release build for
the HTML, public setup guide and all eleven JS/CSS assets, byte for byte.
Main asset `/assets/index-BixhDdMs.js` is 203901 bytes, SHA256
`b9e9605dd6194a934ddec483121be417aa53b1b4da79bb6d0141191d3c86f8d4`.
`/agent-setup.md` is served as text/markdown, 6461 bytes, SHA256
`28ea6fa1e4583b6afd1dcafbde5844c3a81d1f853cfcbb1b31330b631b84cb5e`.

The upload came from a Git archive of the exact merged `live-arena` tree,
with only the verified existing-project link added. No local experiment outputs,
credentials, ignored files or parent presence changes entered the source archive.
The provider's parent-checkout `gitDirty` flag reflects the managed presence file;
it is not being represented as a clean whole-repository checkout. The clean
source archive and canonical byte comparisons establish the shipped artifact.

The new guarded connection-guide journey, existing connection/preflight journey
and strict profile journey each passed against the canonical production URL.
These cover safe clipboard briefs/fallback, explicit model selection, keyboard
and 320/390/768px layout, local-address credential clearing, help-only selections,
saved-seat isolation, cancellation, profile secret clearing and no automatic
inference. All model/provider responses were synthetic; unexpected external
requests were denied. A separate direct browser inspection confirmed the live
guided form and client-specific setup path without entering credentials.

## Review, custody and limits

See [review dispositions](CONNECT_UX_REVIEW_20260905.md) and the
[connection contract](CONNECT_YOUR_MODELS.md). Local validation also passed
195 Node tests, 10 native-frontier Python tests, nine bridge tests, all thirteen
Chromium journeys, Firefox/WebKit proof and 168 contrast pairs. Final display-label
shortening received another built guide run and the full exact-candidate CI.
The release archive's locked install and strict production build passed.

Local screenshots and machine proof remain under
`live-arena/output/playwright/connect-ux-20260905/`; production narrow-screen
captures are `live-arena/output/playwright/connection-guide-{320,390,768}.png`.
The archive is retained at `live-arena/output/playwright/release-connect-50607bec-20260905/`.

Rollback reference: previous READY production
`dpl_FbRtsAn3aN5gpDQ1xuiQaKGjGKfL`, source
`138e57005782fcf2462958fb809f8c1821db790e`. Reconcile intervening releases
before promoting a rollback. No data migration, account, DNS, billing or
eligibility changes were made. Subscription entitlement and real client/model
execution remain account-specific; native CI is not physical-device or store proof.

The broader frontier-training goal remains active. This UX release does not
claim learned-strength promotion, a completed four-family exhibition, or revenue.
