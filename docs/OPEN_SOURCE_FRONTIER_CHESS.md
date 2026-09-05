# Open-source-assisted frontier chess

Operator priority, September 5, 2026: use established game intelligence and put
frontier models into more complex competition now. The small numeric-learner
attempt is stopped, not promoted, and no longer blocks chess exhibitions.

## Adopted local capability

Stockfish 19 runs as an explicit, separate UCI advisor. BuilderWars' existing
content-addressed chess referee still decides legality and game outcomes.
The model sees the board, legal moves and three analyzed lines, then selects its
own move. There are no replacement moves or hidden engine-controlled turns.
This improves the **agent's tools**, not the provider's base-model weights.

Pin: official `sf_19`, source commit
`edb0d9db6731067ec50ce619ff372b463bc4dd5d`. Official Windows archive SHA-256
`3c8bf1f9ea66a09350a40df4f632288285ac206d99f33ab5842c408fc30b48a7`;
locally verified executable SHA-256
`45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0`.

The local adapter requests one thread, 16 MiB hash, three principal variations,
and 20,000 nodes per analysis, with a five-second process deadline. Stockfish
checks node limits internally; requested nodes are not a claim of zero overshoot.
Each call starts a fresh process, verifies the binary digest and UCI identity,
and validates every returned variation against the existing referee. Analysis
centipawns/mate scores are side-to-move estimates, never adjudicated results.

Real offline conformance smoke passed: initial position → `e2e4`; Fool's Mate
fixture → `d8h4`; Ruy López middlegame → `c2c3`. These are engine integration
checks, not frontier-model wins. Full receipts stay locally at
`live-arena/output/chess-exhibition/stockfish-conformance-01/result.json`.

## Personal native-client exhibition

Two fixed pairings: Astra via Codex / Fable via Claude Code; Grok via Cursor /
Gemini via Antigravity. Maximum 24 total attempted calls, 120 seconds per call,
15 minutes overall and 80 plies per game. Games alternate turns of dispatch so
one pairing does not consume the entire budget before the other starts.
Native-client process cleanup may require a bounded grace interval.

All contenders receive the same declared advisor configuration. Invalid output,
quota errors, timeouts, reported tool use or reported model drift stops that
game. No retries, fallbacks, forfeited chess wins or cap-as-draw scoring.
An unfinished game has no winner. This two-pairing exhibition is not a ranking,
Elo estimate, fair round robin or evidence of learned strength improvement.

Each call records only its public decision and safe reported usage/identity.
Unavailable identity or usage stays null. A client model label is not independent
provider attestation; wrong reported model families are refused. Fable's reported
list cost/usage can include native Haiku helper activity and is not incremental
subscription billing. No raw reasoning, credentials or provider stderr enters
the replay. Native-client JSON can omit activity; an absence of reported tools
is not a security proof that an opaque client could never use them.

Windows native clients launch suspended, enter a kill-on-close Job Object, then
resume. Python wrapper termination therefore terminates its native descendants.
Tests exercise cleanup with fake local child processes, never real providers.
Official client paths are resolved outside the project. No login, credential
copying, session-store inspection, global model change or new service purchase.
Claude's native environment inheritance is preserved. This is operator-directed
personal local research, **not** enablement of the held product Claude backend,
hosted provider access, or approval of public provider branding/entitlements.

Run only after explicit local exhibition consent:

```powershell
cd live-arena
node_modules/.bin/tsx.cmd scripts/frontier-chess.ts --consented-native-exhibition ABSOLUTE_STOCKFISH19_EXE NEW_OUTPUT_DIRECTORY
```

The create-only plan precedes inference. Requests, public responses, referee-
checked replays and source-bound proofs remain local. Nothing is automatically
published. A proof establishes replay integrity, not independent execution or
provider identity. Live web UX and opt-in training/version flows remain separate.

## Open material and licensing

- [Stockfish's official release](https://github.com/official-stockfish/Stockfish/releases/tag/sf_19)
  is the engine source/binary origin. Its
  [developer guidance](https://official-stockfish.github.io/docs/stockfish-wiki/Developers.html)
  describes UCI integration and GPLv3 obligations. The downloaded source,
  notices and archive are retained locally; no engine binary is committed or
  added to the web bundle. Any future redistribution must preserve the exact
  license/source obligations and receive its own integration review.
- [Lichess open data](https://database.lichess.org/) supplies CC0 puzzles, games
  and engine evaluations for future curated practice material. Broadcast-game
  exports have a separate CC BY-SA license: do not conflate them with CC0 data.
  No multi-gigabyte corpus or public benchmark has been imported in this slice.
- [GPL Cake 1.20](https://arton.cunst.net/xcheckers/) is a possible English-
  checkers adapter, with archive SHA-256
  `8f8ecd476990fdc3807c0f0ffb30a7b526f90bd172e527fe25e345463c78613a`.
  Independent source inspection found full same-piece capture chains and
  promotion-stop semantics. It remains uncompiled and untested here; its
  strength and bundled book/database terms are not admitted. Scan is a different
  draughts variant, and another candidate's continuation generator was rejected.

Capability route: Astra/high implementation; existing official local native
clients for decisions; Stockfish UCI for disclosed analysis; exact referee for
legality/replay. No paid API integration or API-key collection was introduced.

## Review and validation

Independent Codex review found no blocking findings for the personal Windows
run once the native Job Object cleanup was present. Outer cleanup now waits
for wrapper closure. Full contest fixture tests cover caps, identity drift,
errors, replay validity and no substitute moves. Local validation: 192 TypeScript
tests, eight Python native-client tests, TypeScript/Vite build. Later CI and live
exhibition receipts must be recorded separately; these tests are not live games.

## First actual exhibition receipt — September 5, 2026

Source commit `9c359b0`; source fingerprint
`5254a206dcb2483cc3b0ba400187bdb9a4fe06fc0e26e221d690b8d0f1afd9c2`.
Run `live-arena/output/chess-exhibition/frontier-four-01` consumed 24 attempted
calls in 152.9 seconds, accepting 23 legal decisions. Astra/Codex played 12
plies and Fable/Claude Code 11. The game stopped at its shared call budget,
not checkmate, draw or a scored victory. Grok/Cursor's first invocation failed;
the paired game stopped before a move, so Gemini/Antigravity was not called.
This is a partial two-route exhibition, **not completed four-family competition**.

All Fable decisions reported `claude-fable-5-1`. Codex was explicitly requested
as `gpt-6-astra` but did not report a resolved model identity; that field remains
null, never inferred from the request. Reported Fable list cost totals $1.039801,
including client helper activity, not incremental subscription billing. Codex
cost is unavailable, not zero. Token fields preserve the native clients' reported
fields and are not a normalized cross-provider total (notably cache accounting).

Both saved proof files were separately verified against the unchanged referee;
their final states contain respectively 23 and zero moves, neither terminal.
The public decision/replay files remain local and are not a public release:

- Result SHA-256: `276a7883f4d5f51e241a2b7015399cf6095145859ea8b61b0c130241eb4e0061`.
- Game 1 proof SHA-256: `ddbb73d6a2d980b7fb14d31be40ca3dae9ea0a5d1495d62846ad44b45d703b6d`.

The CLI wrapper deliberately withheld provider stderr, leaving the first failure
generic. A bounded read-only route diagnostic follows; this failed receipt is
immutable and will not be overwritten or reclassified as a game result.
