# BuilderWars release: acknowledged device storage

Date: September 5, 2026. Public product: BuilderWars, by Nymrel.

## Release identity

- Public URL: https://builderwars.com/
- Merged PR: https://github.com/nymrel/builderwars/pull/32
- Released source: `d0873da18dfeeda1062cdce5e503c82aa804d904`.
- Its application tree is identical to reviewed candidate
  `ea20112e8638984b3291fc910b8b232d75d36f19`.
- Vercel project: `prj_c2HDxCRh3sEFEZkOxemiwoUmp1Gp`, root `live-arena`.
- Production deployment: `dpl_HEE3Yq1q6sKf6Kd3Ys9eyKjqYDf1`, READY;
  https://builderwars-6deb7p95q-jalens-projects-0ade4450.vercel.app
- Provider Git metadata matches the released source. Direct canonical GETs match
  the local production build's five entry/preload/style assets byte for byte.
  Main asset `/assets/index-CWHU__oJ.js`: 194068 bytes, SHA256
  `da84f6b9ca7126add5ac73ddb06c72538af879323e651afda32a5c50a3c7af3e`.
- `builderswars.com`, `www.builderswars.com`, and `www.builderwars.com` each
  return 308 to `https://builderwars.com/`. No DNS change was made.

## Changed behavior and evidence

Native builds use versioned app-private checkpoint files. Moves and eligible
completed-game practice reviews are acknowledged before showing the next saved
position. Explicit erasure waits for acknowledgement; failures preserve free
play with an unconfirmed-save warning. Old saves cannot silently replace an
authoritative empty checkpoint. Web builds retain browser-local storage.

Candidate [CI33956750534](https://github.com/nymrel/builderwars/actions/runs/33956750534)
passed all five jobs: Linux, Windows, browser, Android debug and iOS simulator.
124 Node tests pass. Independent reviews accepted the checkpoint/integration
changes and the final retry-state correction. Exact merged-source
[CI33957227753](https://github.com/nymrel/builderwars/actions/runs/33957227753)
also passed all five jobs. Its Android receipt independently confirms all three
restart trials; its APK SHA256 is
`84e70291942ee602dc8a6bc3800446fd56269733abe879426026ac1fbf68d9ea`.
Both runs' downloaded artifacts remain under `live-arena/output/playwright/`.

Actual Android 15 emulator/WebView evidence: a complete free five-ply game,
background pause, process recovery, and three rapid-restart trials each restored
exactly two moves and remained paused. Packaged assets matched the build. APK
SHA256 `6dfa8b49ba28f0951d8358ebbeac125c5e24c558c9dab69c0a192a81eee86fee`,
CI merge checkout `98914e57ffcb45e9bff582dcbb5f3493dfe7970a`.
iPhone 17 Pro/iOS 26.2 simulator launched; initial-screen OCR passed and its
settled screenshot was manually inspected. iOS gameplay/recovery, physical
devices, OS share-sheet receiving apps, signing and store publication remain
unverified. Debug/simulator evidence is not an app-store launch.

All twelve credential-free Chromium journeys in the existing browser gate passed
against the canonical production URL, plus the real WebRTC recovery journey.
Canonical production checks include:

- Four games, human win, replay export/import, creator rules, paired series,
  synthetic model picker/move, illegal-move rejection and secret non-persistence;
  responsive destinations at 320, 390, 768 and 1440px.
- Practice review to retained memory to the next synthetic request; reload,
  frozen evaluation, no-memory baseline and clear.
- Portable proof to standalone verifier and clean import in Chromium, Firefox
  and WebKit; SRI/CSP, tamper rejection and small-screen controls.
- Downloaded result PNG, public replay/caption, clean recipient replay/rematch,
  human challenge, no auto-execution from shared model setup, clipboard failure.
- Interrupted/import races preserve newer match and creator state.
- Connection preflight, profile import/export, match packages, resource caps,
  keyboard/touch/reduced-motion accessibility, and the runnable Academy paired
  comparison and creator exercise. Provider responses remain synthetic.
- Real WebRTC spectator reload/rejoin, offline saved view, device reload/resume,
  deletion/opt-out, denied storage and mobile overflow check.
- Cancellation/overlapping-request lifecycle passes under the actual production
  CSP after changing two test-only polling expressions to functions. The initial
  test error was Playwright string evaluation blocked by CSP; production policy
  was not weakened and no application fix was needed.

All model move responses in these release checks were synthetic; no paid model
calls were made. Real PeerJS transport is separately identified above.

An additional single free built-in game was captured from this production
release with observed matching asset bytes: Tactician beat Wildcard in seven
Connect Four plies. A downloaded standalone verifier reproduced it, and a fresh
mobile browser opened its canonical replay safely. The new dated video, card,
proof and caption replace the localhost draft for launch preparation; see
[the share package](BUILDERWARS_SHARE_RUNBACK.md). No actual human or frontier
model result, social publication or repeated-outcome selection is implied.

## Limits, adoption and recovery

Practice context is not weight training. Supported connected contenders can
receive tactical lessons from completed connect games. Chess, checkers and
built-ins do not adapt. Evaluations freeze or omit practice memory and never
train from evaluation results. No named-model mistake-rate improvement is proven.

No consented external tester observations were supplied or collected in this
release. The exact missing adoption input is completed, consented reports from
five non-studio testers following [the tester guide](BUILDERWARS_BETA_TESTER_GUIDE.md),
including attributable start/finish/replay/rematch outcomes and observed time to
first interaction. No approved outbound recruitment action is specified for this
release. This dated readout records missing observations, not zero actual users.
Automated sessions are not counted as people. Activation, repeat play, virality,
revenue and WVRB remain unmeasured; this is an engineering release, not proof of
demand. Outbound recruitment/social publishing was not performed.

Rollback reference: previous READY deployment `dpl_6LwxVfYbZc5SKy5tLyPwyCtFwvax`,
source `65d357c8a256aa13fdd820f43e5c73139f1872a7`. Recheck current production and
ownership before promotion; do not overwrite an intervening owner's release.
Its immutable deployment URL and original main asset returned HTTP200; the asset
still matched SHA256
`c623b78f8190c13c9d7f823d4c0e80bc017fc9edc6b01e988e8c69744026c72d`.
This verifies a retained recovery artifact, not an exercised production rollback.
There are no hosted database migrations or new production secrets in this slice.
A web rollback does not downgrade an installed native binary or erase its data;
do not claim that a web alias move reverses native checkpoint migration.

Next: complete the original beta acceptance audit; use held-out, fixed-budget
memory-on versus memory-off tests before making stronger learning claims. Native
store release and a trained chess agent remain separate work.
