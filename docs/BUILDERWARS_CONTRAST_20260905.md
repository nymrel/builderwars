# Contrast repair: mobile controls and game state

September5,2026. Candidate, not yet a production receipt.

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
at320/390px (original102 text/placeholder/outer-focus checks retained plus66 form
boundary and game-state checks). It drives human-only fixtures for chess,
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
expanded final-CSS full gate and exact candidate CI are separate acceptance gates.

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
