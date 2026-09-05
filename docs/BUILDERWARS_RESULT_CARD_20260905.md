# Result-image outcome visibility

September5,2026. PR34 merged and released as5f92f99071533ca8355ef5cf69a4f671354ae910.

Release receipt: deployment dpl_4cTgTHmFyQ2rePzQxn9QFe9Et5ZE on the existing
BuilderWars project/team; canonical https://builderwars.com. Exact candidate
1ca032e passed all five required jobs in CI33960005977; merged-source CI33960411858
also passed all five. Cross-family receipt
`builderwars-beta-1ca032e/1` approved the committed diff; resolved model metadata
lists claude-fable-5-1 and claude-haiku-4-5-20251001. That release review excludes
the later learning experiment committed in PR35 and does not recover the previous
timed-out review. PR35 has a separate source-review receipt and CI gate.

Upload used `git archive` of the merged SHA, with an identical tree to the
reviewed candidate, extracted under output/playwright/release-5f92f990-20260905.
Archive SHA256:2c6a4aa95dc86623df0c0c1973d36fe3566a1fa497b0e0d125018ad4a7f167db.
Vercel inherited gitDirty=1 from the ancestor worktree; the uploaded archive
contained only committed source, not that worktree's unfinished experiment.
The artifact receipt and canonical byte match, not the dirty metadata label,
establish source custody. Main asset index-CHp1TxrL.js is194179bytes, SHA256
0244a3b0b93b0b465f4d6521fca77f6081f9eaf9603ac2048c4e4e5cc7126f4d.

Canonical sharing-browser journey PASS, including real canvas export and320px
safe recipient/rematch. Both original genuine model replays recaptured in fresh
390px contexts,0providerrequests/pageerrors, matching canonical/local asset bytes.
New immutable folder: original gameplay receipt's canonical-replays-card-5f92f990.
Game1PNG SHA256:4ae098c88062a4b57be57993e96baf2c4684497202870bd46e173ba2b2aae9a1;
game2PNG:9a8f5de4184525f1612493ff54f8206f0f35912f9e7e50218e7349a970ea3ce8.
Game1PNG visually inspected. Old captures remain unchanged historical evidence.
The PNG says `Winner · Seat N: name`; the on-page result still says `name wins`.
Node mocked width is regression logic; actual pixel evidence comes from browser
canvas measurement and inspected PNG. All three plural/www redirects remain308
to canonical. Previous deployment dpl_HEE3Yq1q6sKf6Kd3Ys9eyKjqYDf1 retained as
rollback: its original194068byte main asset still200 with the previous hash.
Rollback availability is verified; no production rollback was exercised.

Historical implementation notes follow.

The actual local-model replay capture exposed a PNG-only issue: long entrant
names consumed the headline width before the trailing `wins` label. The full
browser result remained correct. Fix: derive `Winner · Seat N` from replayed
referee state and place it before the name in the image. Draw, unfinished and
exhibition-limit headlines retain their existing wording. No rule, model,
learning, provider, storage or result-summary behavior changed.

The frontend-polish skill informed this small hierarchy correction; existing
canvas dimensions, type, palette and privacy notices were retained. This is
product-specific formatting, not a new shared UI primitive or dependency.

Regression evidence: the new canvas test failed on the old source with
`Very long contender model…`, then passed with winner/seat visible. It covers
both winning seats, 64-character names, draw and unfinished play. The real-browser
regression observes the actual canvas measurement without replacing rendering,
downloads a1200×675PNG and checks a390px fresh recipient without execution.

Local validation:137Node tests and production build PASS. Rendered
`live-arena/output/playwright/long-name-result-regression.png` visually inspected:
outcome and seat visible, name clipped safely, board and evidence caveats intact.
The full isolated browser gate passed:12Chromium journeys, Firefox/WebKit proof
journeys, and9local bridge unit checks. Synthetic provider fixtures are not real
inference or proof of learning. Owned preview/browser processes were stopped;
no residual preview56139 or model8088 listener remained.

Independent bounded code review by `erasure_retry_review`: no actionable findings.
This is not the pending cross-family release review. The original Fable turn
`builderwars-beta-showcase-20260905/1` remains `blocked.ambiguous_delivery`; exact
session transcript inspection found no assistant response. No resend or result
recovery was performed.

PR34 old head77e3dc3 CI33959411202: Linux, Windows, browser and Android PASS;
iOS failed on simctl launch60stimeout, followed by terminate30stimeout. Shutdown
still ran. No underlying cause or iOS acceptance is established. Do not carry
these checks to a newer source head or merge around the failed gate.

At initial candidate checkpoint, production and retained media were unchanged.
The dated release section above supersedes that hold; no previous media erased.
