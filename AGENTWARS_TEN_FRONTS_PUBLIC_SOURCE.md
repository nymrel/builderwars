# AgentWars Ten Fronts public source note

Status: candidate source under claim `codex-app-builderwars-tenfronts-public-source-ox-20260823`. This is a note-only completion pass; it creates this document only and edits nothing else. Prior Ox attempts were rejected solely by byte-level Git-index custody checks; they are not accepted receipts, and nothing here should be read as one. These files remain candidate source until the controller earns a clean guarded acceptance receipt and independently validates them.

## Reviewed source receipt

- Exact source path: `matches/agentwars-ten-fronts/ten_fronts/7000-0/e16ac35d43eb3b47.jsonl`
- File SHA-256: `761329826c2e43970bcc501cb3816ea101935ea337715aa80aa12db1301d4de4`
- Chain head / receipt id: `e0f90384b6cebaa22d230a389026581fc1ad11fcd4596a6c2f255b60b4ff13e4` (final record hash, seq 164)
- Engine digest: `baa77c4dcd746081738dabcdbfc7882432d182dd88a3f596828cd969f9c960f6`
- Match id `e16ac35d43eb3b47`, seed `7000`
- Final score 319–226; margin 93; winner seat 0 `Stub Iron Front`, loser seat 1 `Stub Even Reserve`; decisive result `ten_fronts_score:319-226`; 80 accepted moves
- Move-source totals across accepted moves: `model=0`, `fallback=80`, `scripted=0`, `other=0`; per-seat fallbacks 40/40
- Attestation: `modelAttested=false`, `executionClaimsAttested=false`; entrant identity is self-declared and hash-bound. This receipt is labeled a scripted offline reference / deterministic fallback / not model-played.

## Projected product story

- Headline: `Stub Iron Front wins ten fronts` (state-derived; asserted verbatim by `bin/check_agentwars_product.py`)
- Product JSON result line: `319-226 over Stub Even Reserve` (ASCII hyphen, `publishing/projection.py`)
- Share-bundle typography separately: `319–226 over Stub Even Reserve` (en dash, `bin/build_share_bundle.py`)
- Scores come only from the final referee state; result prose is never a score source

## Bounded moment candidates (local deterministic descriptors, not public engagement)

- One bounded final-accepted-move clip candidate: single record, raw move omitted (`publishing/projection.py` `public_clip`, `kind=final_accepted_move`)
- One own Ten Fronts rivalry meeting: one played meeting forms its own rivalry (`meetingCount == 1`)
- One seat-swapped seed-7001 runback descriptor with status `unplayed_challenge`; it never receives a receipt id

## Scoped candidate paths

- `README.md`
- `bin/build_share_bundle.py`
- `bin/check_agentwars_product.py`
- `bin/check_share_bundle.py`
- `docs/AGENTWARS_PUBLICATION_MANIFEST.v1.json`
- `docs/AGENTWARS_PUBLIC_PRODUCT.md`
- `docs/VIRAL_LOOPS.md`
- `publishing/projection.py`
- `AGENTWARS_TEN_FRONTS_PUBLIC_SOURCE.md` (this note)

## Observed candidate validation facts

- Replay: PASS
- Share-bundle contracts: PASS
- Public-product contracts: PASS with 8 approved receipts and 3 closed future fixtures (`proposed_not_activated`, predictions stay closed)
- Ten Fronts contract checker: PASS (11 sections)
- Scale: PASS with 18 deterministic matches
- Selfcheck: PASS 23/23
- Fantasy contracts: PASS
- Verifier build check and controller rerun: still pending in this note-only pass unless directly rerun without Git
- `py_compile`: PASS

## Proof boundary

This proves local deterministic engine/receipt/compiler behavior only. It does not prove that a model played Ten Fronts, nor public deployment, site install, public audience, prediction activation, sharing, performance, revenue, or virality. No post or deploy occurred.

## Next phase

The controller independently reviews and accepts this source tree, commits/pushes it, then a separate clean guarded Ox lane regenerates only `publishing/agentwars-public-v1/**` so `buildIntegrity.sourceCommit` equals the accepted source commit. Artifact validation and commit follow separately.
