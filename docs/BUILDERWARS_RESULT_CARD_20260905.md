# Result-image outcome visibility

September5,2026. Candidate follow-through on PR34; not deployed.

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

Production and retained canonical media are unchanged. Capture new canonical
artwork only after exact-source review, successful required checks and release.
