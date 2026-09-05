# Contrast repair: mobile controls and game state

September5,2026. Released as138e57005782fcf2462958fb809f8c1821db790e.

## Production receipt

PR36 candidate38ff928a20a54f5a63efa6e6048cc22b4c2e2093 passed all five CI jobs
in33962628832. Its application/test tree is identical to Fable-reviewed7089da79;
the follow-up only reconciled documentation. Merge138e5700 has the same tree.
Merged-source CI33962910085 has an unresolved iOS simulator launch failure:
unsigned build/install succeeded, simctl launch exceeded60seconds, diagnostic
spawn exceeded30seconds, and shutdown ran. Exact job101297815271/log retained.
The app/test tree is unchanged from the passing candidate; that does not erase
this failure or establish its underlying cause. No check bypass or rerun yet.

Exact committed git archive SHA256:
57752305f6601623d781b950c85de6424028bd4a539c2ca54ceff7de34c89257.
Production deployment dpl_FbRtsAn3aN5gpDQ1xuiQaKGjGKfL is READY on the existing
project prj_c2HDxCRh3sEFEZkOxemiwoUmp1Gp/team_MkEJAArMiAM6dAEnF96D5GLE.
Canonical https://builderwars.com resolves to
https://builderwars-m669eqlr8-jalens-projects-0ade4450.vercel.app.
All five entry/preload/style asset bytes matched the local release build.
CSS index-s7snZS0D.css:17269bytes, SHA256
940bf62f5c584e244e7c69071589f3803e2c6b8c3762584933f9f5461b71aa24.
Main index-DAHsmVZF.js:194179bytes, SHA256
0244a3b0b93b0b465f4d6521fca77f6081f9eaf9603ac2048c4e4e5cc7126f4d.
The JS bytes remain unchanged; its filename changes with the CSS build graph.

Canonical accessibility journey passed all168pairs at320/390px with zero
contrast failures, unsupported paint cases, external requests or page errors.
Actual390px screenshot visually inspected:
live-arena/output/playwright/nontext-live-138e5700-20260905.png,
SHA256 ffe49f0855557a1ad8f21db8b6d20d044d742dc2f1fbcb94a57a6913aa03e2ca.
Black piece silhouette, legal dots, coordinates and inset focus are discernible.
This is human-driven QA fixture evidence, not an external tester or full WCAG audit.

All three plural/www origins return308 to canonical. Previous production
dpl_4cTgTHmFyQ2rePzQxn9QFe9Et5ZE remains READY/available: its immutable
index-CHp1TxrL.js returned200 with194179bytes and the preceding main hash above.
Rollback availability verified; no disruptive production rollback exercised.
No domain, environment secret, account, model or stored customer state changed.

All12 canonical Chromium journeys passed (including accessibility above), plus
Firefox and WebKit portable-proof journeys. These cover free games, lifecycle,
connections, profiles, match packages, import races, resource caps, Academy,
memory mechanics and sharing. Synthetic provider routes are not actual inference.
Real PeerJS recovery remains separately proven by the prior unchanged-runtime
receipt; this CSS-only release does not recertify customer clients or native OS UI.
Owned preview42404 stopped after PID/creation/command verification;5189/8088
listeners absent. The canonical browser processes completed normally and closed.

Historical implementation and preview evidence follows.

The new computed audit found actual defects on canonical5f92f990, not merely
missing documentation. At320/390px, default placeholders were3.71694:1 against
their field; inputs' borders were2.189:1 against the page and1.890:1 in a dialog.
Dark-board focus, dark-disc silhouette, grid/hole edges and legal-move dots also
failed the applicable3:1 threshold. A selected white checker relied on a pale
fill/border and blurred shadow rather than a reliably contrasting silhouette.

The CSS-only application fix keeps the existing green palette and rules intact:
semantic control-edge token, readable opaque placeholders/coordinates, brighter
dark-game edges/focus, opaque legal targets and a dark white-piece outline.
No new dependency, animation, layout, provider or game-logic change. Decorative
dividers and text-identified button boundaries are not indiscriminately restyled.

The existing accessibility browser journey now checks168 actual computed pairs
at320/390px across text, placeholders, focus, form boundaries and game states.
It drives human-only fixtures for chess,
checkers, Connect Four, tic-tac-toe and one3x3non-gravity custom recipe; it does
not inject replacement styles or model responses. Transparent layers are
composited, unsupported paint/effects fail explicitly, and unrounded ratios are
used for acceptance. Existing keyboard, touch, focus-continuity and reduced-motion
checks remain. Failure paths close browser contexts; external HTTP/WS blocked.

| Fixed pair | Observed ratio |
| --- | ---: |
| Placeholder on field | 6.803 |
| Input edge on page / dialog | 5.134 / 4.434 |
| Dark grid / hole edge on cell | 3.476 |
| Black disc edge on TTT/custom cell / Connect Four hole | 3.476 / 4.757 |
| Dark-board inset focus | 10.322 |
| Dark-board coordinate text | 4.952 |
| Dark legal target / Connect Four hole target | 4.952 / 6.778 |
| Sample chess-light / checker-dark legal target | 11.566 / 3.633 |
| Selected white-checker outline | 10.344 |

First final-CSS preview run passed all168pairs with no unsupported cases, external
requests or page errors. Type/build and144Node tests pass; the placeholder-only
earlier full gate passed12Chromium, Firefox/WebKit proof and9bridge tests. The
expanded final-CSS full gate subsequently passed all12Chromium journeys,
Firefox/WebKit proof journeys and9bridge tests. Exact7089da79 candidate CI
33962292654 passed all five jobs. Documentation-only follow-up checks remain
source-specific; those results do not establish a production deployment.

Fable source review builderwars-beta-1ca032e/3 approved7089da79, resolved model
claude-fable-5-1, result hash
00c23ada3d2b0581e5abf23a67574046dfa781d65a06914568a8860da6d3af39.
Stale CI lines were corrected and the intermediate check-count split removed.
The Connect Four disc ratio assumes its edge meets the hole fill; against the
cell the edge is3.476:1, also passing. Explicit both-shade legal-target and
empty-cell focus samples remain non-blocking coverage improvements; this audit
does not claim exhaustive state coverage. Source review is not live verification.

Canonical before and rebuilt-preview after screenshots were independently
inspected, retained under live-arena/output/playwright/nontext-canonical-20260905.png
and nontext-fixed-preview-20260905.png. The after frame shows discernible black
piece, empty legal spots, coordinates and a clear inset focus rectangle. It is
test imagery, not customer participation or full accessibility certification.

Threshold/reference: [W3C text contrast](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum)
and [meaningful non-text contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html).
Coverage is representative rendered CSS under Chromium, not every board state,
image/video, assistive-technology behavior, native OS UI or full WCAG certification.
Release requires independent review, exact CI and canonical changed-state proof.
