# AgentWars Viral Phase 3 — Verified Moment Bundles

## Objective

Turn every replay-verified AgentWars match into a deterministic, truth-safe share unit: a bounded replay moment, receipt card, local match page, draft social copy, and measurement contract. The artifact should make a result worth sharing without converting entrant claims into model attestation or calling unmeasured reach “viral.”

## Authority and custody

- Repo: `C:\Users\johns\Desktop\builderwars-agentwars-viral-phase3-20260823`
- Base: `ac281427d1d02f222e3c012cf1e109faa0b03a21`
- Branch: `codex/agentwars-viral-phase3-20260823`
- Claim: `codex-app-agentwars-viral-phase3-20260823`
- Allowed writes: this packet, `README.md`, `bin/build_share_bundle.py`, `bin/check_share_bundle.py`, `bin/export_site.py`, and `docs/VIRAL_LOOPS.md`.
- No merge, deployment, public post, account action, ad spend, credential access, DraftADynasty write, or `portfolio-control` source write.

## Selected loop

`verified match -> moment bundle -> tagged landing -> replay start -> replay verification -> spectator vote -> league join`

The first slice implements the verified-match-to-bundle substrate only. Later funnel stages remain an explicit event schema and activation gate until a public route and working counters exist.

## Required implementation

1. Refuse any transcript that does not pass the snapshot-aware standalone replay verifier with an exact embedded referee-engine digest before creating output. A replay `PASS` with no matching snapshot is not enough for a public verified label.
2. Select one deterministic, bounded highlight window. Completed fantasy matches use the winning roster's highest-scoring pick and label it as a top-scoring pick, not a causal “winning move.” Other completed games use the final accepted move; forfeits and engine errors use their terminal adjudication so empty or voided state cannot become an invented performance highlight.
3. Derive a deterministic rivalry id and a seat-swapped next-seed runback descriptor. It must remain `unplayed_challenge` until a separate child receipt exists; never present the proposed runback as a played result.
4. Emit deterministic `manifest.json`, `card.svg`, `match.html`, and `copy.md` files. Include match id, score/result, entrants, execution claims, move-source counts, chain head, verification command, highlight sequence/hash, and explicit `model_attested=false` / source-claim boundary.
5. Escape all entrant-authored text in HTML and SVG. Never emit raw prompts, environment values, stderr, backend output, response hashes, or credential material.
6. Emit tagged candidate URLs only when an explicit HTTP(S) base URL is supplied. Mark them unverified candidates; tagged transport is not attribution persistence or audience evidence.
7. Define an allowlisted measurement schema for landing, replay, vote, and join events without recording raw URLs or private content.
8. Repair the existing site exporter so Phase 2 `source=model;response_sha256=...` notes count as model-source claims and execution truth travels with exported rows.
9. Update README truth: Phase 2 supports 2–16 entrant round robins and has one model-influenced, unattested fantasy redraft receipt; no public league or deployed spectator page is claimed.

## Validation floor

- `python bin/check_share_bundle.py`
- `python bin/check_agentwars_scale.py`
- `python bin/selfcheck.py`
- `python bin/check_fantasy_games.py`
- `python bin/build_verifier.py --check`
- deterministic byte comparison across two builds
- hostile-name escaping check
- altered-transcript refusal with no partial output
- one live Phase 2 transcript independently replayed and bundled locally
- `git diff --check`

## Growth gate

Do not open a formal growth experiment yet. The current growth ledger has no open AgentWars experiment, but the required public URL and working landing/replay counters do not exist. A numeric experiment can open only after those prerequisites are verified and one owner plus stop-loss date are named.

## Done when

The claimed branch produces deterministic verified-moment bundles from exact-snapshot-verifiable receipts, rejects tampered chains/outcomes and engine-mismatched receipts, leaves standalone historical verifier conformance unchanged, labels entrant names as self-declared rather than authenticated identity, carries honest execution provenance, and leaves a review-ready product/content substrate without deployment or performance claims.

## Return / outcome

- Implemented a deterministic four-file verified-moment compiler, strict standalone snapshot-verifier gate, fantasy and terminal-adjudication highlights, rivalry/runback receipts, bounded measurement schema, truth-safe draft copy, and responsive static match preview.
- Repaired the site export seam so exact model/fallback/scripted provenance variants agree across bundles and exported rows, execution claims travel, and receipts without an exact embedded engine snapshot are excluded rather than labeled verified.
- Live redraft proof `b1c8bb9b29e7050f` compiled to `C:\Users\johns\Desktop\agentwars-runs\phase3-20260823\verified-moment-b1c8bb9b29e7050f-release`: exact engine match, `model_influenced_unattested`, seven model-source claims, five fallbacks, entrant/model identity unattested, and seat-swapped seed-9301 runback still `unplayed_challenge`.
- Acceptance: share-bundle adversarial contracts PASS; scale contracts PASS with 12 replay-verified deterministic matches; engine self-check 21/21; fantasy contracts PASS; standalone verifier conformance 36/36; `git diff --check` clean. Browser review rendered the 1200×630 card and responsive match page successfully; the only console entry was the temporary preview server's missing favicon.
- Independent read-only acceptance review: PASS with no blocking findings. Its end-to-end exporter check emitted 34 exact-engine matches and excluded two invalid or missing-proof receipts.
- No merge, deployment, public post, account mutation, paid spend, audience claim, or formal growth experiment was opened.
