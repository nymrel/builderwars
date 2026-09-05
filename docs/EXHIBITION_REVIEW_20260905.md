# Exhibition replay review and owner dispositions

Astra implementation/integration; independent Fable architecture/product review.
September 5, 2026. No provider gameplay, external publication or account changes
were performed by this implementation/review slice.

The first full-context review timed out after 240 seconds without a verdict;
usage was unavailable. It does not count as approval. One bounded retry used the
existing tool-free, safe-mode Fable round-trip route and returned a real critique.

- Review ID: `builderwars-exhibition-replay-repair-20260905`, turn 1.
- Provider session: `02db3b44-4d1c-4501-a8ec-2947cf62af41`.
- Resolved models: `claude-fable-5-1` and helper `claude-haiku-4-5-20251001`.
- Request hash: `4be5c9a7f828909937d6b327fe911ce00ebb9bb3dc17efec4d39fa984d566ab1`.
- Result hash: `41d05416f5d12b902ec430354309b98e4763fec31f6eafaf5cc82d25d450fd73`.
- Reported usage: 2 input, 23670 cache-creation input, 864 cache-read input,
  12776 output tokens. No incremental subscription-cost claim.
- Original verdict: **changes_requested**. The validator and offline exporter
  met the review requirements; three integration concerns were raised.

The raw receipt is retained outside Git under
`StudioData/artifacts/builderwars-exhibition-replay-20260905-review/`.
The receipt's `published` status means local atomic receipt promotion, not an
external social post or public replay publication.

## Reconciled findings

1. **Stale exhibition after `applySetup`.** The supplied partial diff omitted the
   existing trailing `reset()` call, which already clears the envelope. The owner
   additionally clears it explicitly at setup entry to make this invariant local
   and resilient to future changes. The browser regression now imports an
   exhibition, starts its free runback through `applySetup`, confirms normal
   contenders and cleared evidence, pauses and imports again without model calls.
2. **Zero-event render could crash / no fixture.** Rejected as a current defect:
   `summarizeMatch()` supports an empty record and its last-move access is guarded.
   Node and browser fixtures already covered a zero-ply failed pairing, unknown
   cost, no accepted identities, save/reload, and no winner before the review.
   The actual zero-ply run also converted. Keep these regression assertions; do
   not manufacture a code change or claim the reviewer tested the omitted helper.
3. **Replay-only proof might omit assistance.** The existing handler rejects all
   non-Connect-Four records, while the new schema accepts chess only. Thus the
   reported current export route was already closed. An explicit exhibition
   check was nevertheless added to both the button state and handler, making
   this invariant independent of future game support. Browser tests dispatch the
   disabled proof control directly and verify that no download occurs.

The original Fable verdict is preserved, not relabeled as approval. These are
owner dispositions backed by code and tests, not a second simulated review.
Post-review copy also labels replay feeds **Recorded moves** and uses **No
automatic publication** for file-transfer feedback, without guessing what a user
may subsequently do in an OS sharing sheet.

## Validation and release boundary

Before the two explicit defensive guards, 204 Node tests, 10 native-wrapper tests,
TypeScript/Vite, nine bridge tests, all fourteen guarded Chromium journeys and
Firefox/WebKit proof journeys passed. Synthetic exhibitions cover cap, checkmate,
zero-ply failure, matching exports, imported/saved digest tampering, illegal moves,
unexpected fields, guarded thin shares, keyboard scrubbing and 320/390/768px layout.
The original 23-ply chess replay was also imported in a guarded local browser and
visually inspected. Original native-run source custody was recomputed from Git.

The exact final candidate still must pass the post-review focused test, required
CI and public adoption checks before a shipped claim. See `EXHIBITION_REPLAYS.md`
for source/identity/resource limits. The broader campaign remains active.
