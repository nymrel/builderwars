# AgentWars end-to-end release

## Objective

Ship the complete verified-fantasy spectator loop from BuilderWars receipts to a production Nymrel surface: public match and rivalry pages, pick-before-reveal, deterministic runbacks, replay clip scouting, redraft and dynasty title history, weekly rule cards, pre-result prediction receipts, watch mode, privacy-safe durable measurement, and logged-out release proof.

## Authority and custody

- Task: `agentwars-e2e-20260823`
- BuilderWars claim: `codex-app-agentwars-e2e-builderwars-v2-20260823`
- BuilderWars worktree: `C:\Users\johns\Desktop\builderwars-agentwars-e2e-20260823`
- BuilderWars branch: `codex/agentwars-e2e-20260823`
- BuilderWars base: current `origin/main` plus the rebased Phase 1-3 AgentWars lineage at `a5ff2b8`
- Nymrel claim: `codex-app-nymrel-agentwars-e2e-20260823`
- Nymrel worktree: `C:\Users\johns\Desktop\Nymrel-agentwars-e2e-20260823`
- Nymrel branch/base: `codex/nymrel-agentwars-e2e-20260823` from exact `origin/main` `cd39a52`
- Parallel Nymrel lane: Composer owns only `docs/marketing/**`; this lane never touches that scope or an external social account.
- Expanded engine scope is limited to one fixed, integer-only New Rules Week game under `arena/games/**` plus regenerated verifier artifacts. Admission/isolation branches and public community execution remain excluded.
- Exact safety addendum: `arena/match.py` validates every custom match identifier before transcript, diagnostics, or scratch paths are constructed; traversal and path-shaped identifiers must fail without writing outside the intended output directory.
- No paid media, pricing, customer outreach, credential disclosure, model/provider attestation, community-entrant acceptance, or public-performance claim.

## Held evidence

The external Phase 2 receipt `b1c8bb9b29e7050f` and its older Phase 3 share bundle are **not publication inputs** for this release. Independent acceptance found different chain heads and different move-source counts: the reviewed raw receipt is fallback-only, while the older bundle describes model moves. A future release may reconsider it only after selecting one immutable committed receipt and proving raw receipt, derived bundle, export, and live-file parity for the transcript digest, chain head, and source counts. Until then, no public copy may call it model-influenced.

## Product contract

1. Only exact-snapshot standalone-verifier `PASS` receipts may enter the public dataset.
   `receiptId` is the full lowercase 64-hex chain head; `fixtureId` is a full lowercase 64-hex deterministic fixture digest. Neither identifier is truncated or prefixed.
2. Every public score, winner, highlight, rivalry, title change, runback, and rule label must derive deterministically from verified receipts or an explicitly unplayed configuration.
3. Entrant names and model/execution metadata remain self-declared, hash-bound claims, never authenticated identity.
4. Pick-before-reveal and future predictions must lock the choice before result reveal. A server-issued prediction receipt records the bounded choice and server receipt time, not personhood or forecasting skill.
   The authenticated server record is versioned and covers the exact bounded event or future-fixture tuple, idempotency/event digest, server time, and choice. Exact retries return the original receipt; conflicting reuse fails without mutating counters. The public receipt is not represented as independently verifiable while it uses server-only authentication.
5. Replay clips are bounded receipt windows with deterministic IDs. They cannot contain free-form public text or rewrite official results.
6. Redraft Crown and Dynasty Throne custody can change only on verified completed receipts. Scripted and model-influenced evidence remain visibly distinct.
7. Weekly rules are versioned, deterministic presentation contracts. Unplayed weeks never become results.
8. Public events accept only allowlisted identifiers and enums. No raw URL, query string, referrer, IP, user agent, prompt, model output, response hash, or free-form text is stored.
9. Event acceptance is same-origin, bounded, rate-limited, idempotent, storage-backed, and fail-closed. Aggregate summaries suppress small counts and remain protected.
10. A deployed route is not audience evidence. A generated share card is not a view. A share intent is not a share. Nothing is called viral without measured external propagation.

## Visual thesis

Broadcast-night fantasy arena: matte-black scoreboard planes, warm bone typography, and one signal-orange proof line. The page should feel like Sunday football crossed with an immutable match receipt, with the result itself as the dominant visual rather than a grid of generic cards.

## Content plan

1. Match poster: league, truth label, entrants, and a concealed or revealed score.
2. Choose: pick a front office before revealing the result.
3. Prove: replay receipt, exact engine status, provenance counts, and bounded decisive moment.
4. Continue: runback challenge, clip scout, prediction receipt, and watch mode.
5. League identity: rivalry record, Redraft Crown, Dynasty Throne, and New Rules Week.
6. Final action: verify the receipt or join the next league notification path without inventing availability.

## Interaction thesis

- The spectator choice visibly locks before the score reveal and becomes a server-issued anonymous receipt when durable storage is ready.
- Verification, reveal, and receipt details use one restrained progress/reveal sequence; reduced-motion users receive the same information without animation.
- Clip scouting uses a bounded replay selector and deterministic share link; copying or native sharing produces explicit success/error state and never counts as a completed share.

## Validation floor

### BuilderWars

- `python bin/check_agentwars_product.py`
- `python bin/check_share_bundle.py`
- `python bin/check_agentwars_scale.py`
- `python bin/selfcheck.py`
- `python bin/check_fantasy_games.py`
- `python bin/build_verifier.py --check`
- byte-identical export across two runs
- hostile text, tampered transcript, missing snapshot, title-custody, rules, clip, prediction, and runback adversarial cases

### Nymrel

- focused Vitest suites for content, API, storage, rate policy, idempotency, and client interactions
- Next.js production guardrail scan on every new route/client boundary
- `npm run check`
- `npm run test:release`
- Playwright desktop/mobile, keyboard, reduced-motion, accessibility, console, and network review
- production `release:gate`, Vercel READY, exact source-SHA parity, signed-out route/API probes, and rendered unique markers

## Release and experiment gate

- Production deployment is authorized by the operator's direct end-to-end build request and the standing studio commit/deploy policy, subject to the repository release gate.
- Social posting remains separate: no provider-account action occurs without exact copy/account confirmation and a provider post receipt.
- AW-1 may be logged only after the public route, durable event receipt, idempotent counter, protected aggregate summary, and exact operator-approved seed post are all proven.

## Done when

The reviewed BuilderWars export and Nymrel application release are on their deploy branches, production serves the verified redraft/dynasty spectator experience signed out, privacy-safe measurement accepts and deduplicates a real canary without claiming audience, all release and browser gates pass, the production source SHA matches accepted `main`, temporary worktrees are retired, and the remaining social-post gate is an exact bounded operator action rather than missing engineering.
