# Portable board-game proof

## Current status — September 5, 2026

Connect Four portable proof is released at https://builderwars.com. Full canonical
Chromium/Firefox/WebKit browser export, downloaded standalone verification,
clean import and tamper checks are recorded in
[the full release receipt](BUILDERWARS_RELEASE_20260905_NATIVE_CHECKPOINTS.md).
Current source138e5700 and canonical custody are recorded in
[the latest release receipt](BUILDERWARS_CONTRAST_20260905.md). Later changes fixed
the result-image heading and mobile contrast. The referee digest is unchanged.
The implementation description below remains applicable. The old PR29 and failed
review notes at the end are historical, not current integration or release holds.
Portable rules proof still does not establish model identity or execution.

## What a player gets

Choose Connect Four, complete a match, open **Verify this match**, and download the `.jsonl` proof and matching `verify-<engine>.mjs`. On another machine with Node.js 22 or newer:

```sh
node verify-<engine>.mjs builderwars-<match>.jsonl
```

The verifier needs no packages, account or network. It returns a JSON summary and exit code 0 for a reproduced snapshot, including `complete`, the computed result, and false model/execution/billing attestations. Check `complete`: a verified partial snapshot is not a completed competition. Invalid, truncated, mismatched or tampered evidence returns exit code 1.

Keep **both** files. A future website release may use a different engine. The browser only accepts its currently trusted engine; it never downloads executable code nominated by a proof. The standalone verifier embeds its original executable, so saved pairs remain usable after a website update. Only run a verifier obtained from a trusted BuilderWars release/source, not an executable supplied by an unknown match participant.

The UI initially admits Connect Four proof only. Chess, checkers and custom games retain their existing exhibition/replay controls. Some additional engine parity tests are present, but that does not broaden public proof admission. Older `builderwars.exhibition.v1` JSON imports and the separate Python `arena/1` verifier are preserved.

## Evidence boundaries

This reproduces accepted moves, intermediate states and the result under an exact executable rules version. It does **not** prove that a named person, agent, model, provider or harness played; that the run was autonomous; that latency, tokens or cost are accurate; that the transcript was captured live; or that the match is a controlled general-intelligence evaluation. Anyone can construct a different legal match and recompute its chain.

`browser_session` is an unverified origin declaration for a new match in the current browser. Imported, recovered and spectator records export as `reverified_import`, including a verified proof that is imported and re-exported. Neither is an execution attestation. The exported move limit is the declared limit at export, not independently proven historical resource enforcement.

Only public entrant names, connection kinds, declared model labels/efforts and reported move metadata are retained. Strategies, comments, keys, endpoints and unknown extra connection fields are excluded from this new format. Legacy JSON replays still contain explicitly disclosed public strategies/comments; they are not silently upgraded to this proof class.

## Single rules authority and executable custody

- `live-arena/src/games.ts` remains the only board-game rules implementation. `records.ts` reconstructs legal records; `proof.ts` adds evidence validation without implementing another game.
- `scripts/build-referee.mjs` bundles `src/referee.ts`, its complete code dependencies and `chess.js` into one ESM artifact. SHA-256 is calculated over the **actual executable bytes**, not a label or selected source files. MIT and chess.js license notices remain embedded.
- The browser's gameplay, move selection and replay paths import `src/runtime.ts`. It loads `/referee/<digest>.mjs` using a module script with SHA-256 Subresource Integrity under the existing `script-src 'self'` policy. No blob/eval permission is added. An integrity/load failure prevents startup and explains how to reload; it never silently selects a different referee.
- The generated portable CLI embeds those same bytes, checks their digest, then executes that trusted embedded module locally. No code, path or URL from the proof is executed.
- Build/test/dev presteps regenerate the artifact and manifest. Source/dependency changes must regenerate before use; Vite hot reload alone does not refresh the referee snapshot. Generated artifacts are ignored, never competing hand-edited source. CI builds from lockfile on Windows and Linux.
- A production release still requires clean source/build custody, exact live asset checks and browser validation. A local digest or SRI check alone does not establish release identity or protect against a compromised trusted distribution.

## Protocol `builderwars.board.v1`

This is deliberately **not** Python `arena/1`. That format's Python source snapshots and game set cannot truthfully certify the browser's JavaScript/chess dependency closure. Existing Python receipts and verifier entrypoints remain untouched.

UTF-8 canonical JSONL, at most 1,500,000 bytes and 803 records. One optional final LF; no CRLF, BOM, duplicate keys or noncanonical alternate encodings. Strings must contain valid Unicode scalar values. Object keys sort by Unicode code point, not UTF-16 code unit. Numbers are safe integers only (`-0` rejected); fractional reported metrics use canonical JavaScript numeric strings, validated on import. The JSONL canonicality check rejects any representation that changes after parse/canonical serialization.

Each envelope has exactly `kind`, `seq`, `body`, `prev`, `hash`. Sequence starts at 0; genesis `prev` is 64 zeros. For each row:

```text
hash = SHA256(prev-as-ASCII + byte-0x1f + canonical({kind, seq, body}))
```

Order: header, initial-state digest, then alternating move/successor-state digest pairs, and finally a referee-computed result. The header binds protocol, referee namespace, engine digest, origin declaration, match metadata, canonical rules, two entrants, declared move limit and false attestations. Every successor state covers the full serialized rules state, including repetition information. The final result distinguishes terminal win/draw from capped or incomplete snapshots; a cap never becomes a competitive forfeit.

Verification checks the chain, known protocol/referee/engine, bounds, event order and legal replay, then rebuilds the full expected proof. Exact comparison rejects extra fields, rule normalization tricks, changed turns, missing states and forged outcomes even if an attacker recomputes every hash. A fully rewritten legal sequence remains a new, unattested legal sequence—not an authenticated original.

## Local validation commands

```sh
cd live-arena
npm ci --ignore-scripts
npm test
npm run build
node node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 5178 --strictPort
# Separate terminal, with the repo's Python Playwright environment:
python tests/proof_browser.py
python tests/browser.py
python tests/lifecycle.py
python tests/recovery.py
```

The new browser test exercises a real browser-produced completed proof through the downloaded standalone verifier, independent browser-context import/replay, altered-result rejection, paid-seat-to-free-play switching with zero inference calls, production CSP plus SRI failure, and 320px layout. All fixtures are synthetic QA, not external users or frontier-provider validation. Unit tests additionally test rechained tampering, version/engine mismatch, truncation, canonical limits, source/bundle parity and copied-verifier portability. Cross-platform CI and independent review must be recorded separately from local passes.

## Historical milestones — September 4 candidate

Implementation checkpoint: [draft PR #29](https://github.com/nymrel/builderwars/pull/29), code commit `f758bfe2dafa446c3eecc062c54670a810c01d5c`. Local validation: 36 Node tests, build, four bridge tests, proof browser journey and existing browser/lifecycle/recovery suites pass. [Hosted Windows/Linux CI](https://github.com/nymrel/builderwars/actions/runs/33937893936) passed on that code commit. These are synthetic QA receipts, not external-user or provider execution evidence.

Independent Fable review timed out after 300 seconds without a usable response, resolved-model identity or usage receipt. Release remains held for a usable review, not for new operator authorization. Production remains on the prior verified release. Existing draft PR #27 adds Nim, exhibition-v2 metadata and a separate CI workflow; preserve it and reconcile those contracts/workflows before combining candidates.

Result cards, safe configuration/rematch links, richer learning/onboarding and the full five-day release/adoption gates remain separate required work. Do not present this first slice as completion of the beta campaign or verified viral demand.
