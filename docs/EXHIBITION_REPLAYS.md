# Source-bound exhibition replays

This is a replay format and viewer, not a new provider adapter, competition result,
training admission or permission to publish. It preserves the evidence accompanying
the bounded, customer-local chess runner in `OPEN_SOURCE_FRONTIER_CHESS.md`.

## Open a run

In the web app, choose **Watch → Import exhibition file**. The existing replay
import also recognizes `builderwars.frontier-replay.v1`. Moves are reproduced by
the unchanged board referee before the current match is replaced. Scrub the board
with the existing slider or previous/next controls.

The inspector keeps these separate:

- rule-completed games, resource-capped games, and failed runs;
- requested routes, reported resolved identities, and unreported identities;
- Stockfish assistance and raw-model play;
- accepted-move usage, missing usage and unknown failed-call usage;
- internal replay/receipt consistency and independently attested execution.

The new envelope's digest is a content-integrity check, **not a signature**. An
organizer who fabricates a mutually consistent set of receipts can also compute
new hashes. Provider-response and client-reported are classifications of supplied
records, not assertions that the browser contacted or independently verified a
provider. Unknown identities remain unknown. No model is silently substituted.

Imported exhibitions are spectator-only. Every replay/package download and the
main Share control retain the full envelope. Thin replay links, captions, result
images, setup links and broadcasts cannot silently strip the assistance and source
context. Downloading does not post or publish a match. Rematches explicitly create
new free play, without reconnecting the recorded providers or advisor.

Optional recent-match storage retains the complete envelope, including zero-ply
failures. Reopening verifies its content digest again. Invalid metadata is not
converted into an ordinary trusted-looking replay. Opt-out, existing 20-match/
30-day retention, storage quotas and native persistence constraints still apply.
Source-detail hashes wrap on narrow screens; no additional animation is needed.

## Convert native receipts locally

From `live-arena`, after the original run has finished:

```powershell
npm run export:exhibition -- output/chess-exhibition/frontier-four-01 1 output/chess-exhibition/game-1.exhibition.json
```

Choose game `1` (Astra/Fable) or `2` (Grok/Gemini); the final path must not exist and
its parent must already exist. The converter makes **zero model and engine calls**.
It reads regular, bounded, non-symlink receipt files, checks both games against the
original plan/result, reproduces the original proof bytes, checks request hashes,
response links, every move, identity consistency and reported usage, then writes
one create-only file. It does not rewrite the original run, retry failed routes,
copy raw prompts/comments, include private paths, transfer credentials, or publish.

The exported source fingerprint is historical: it is not relabeled as the current
exporter's source. Source, plan, result, original proof, advisor-binary and referee
digests remain visible. The sanitized record intentionally differs from the raw
proof, which includes public comments; the original proof digest is a receipt
reference, not a claim that the sanitized record recreates the original bytes.
Keep the original local receipts to independently inspect that relationship.

The v1 envelope is deliberately the existing fixed chess-runner contract: Stockfish
19, one thread, 16 MiB hash, three candidate lines and `go nodes 20000` requested
per turn. UCI node counts may overshoot the requested stopping threshold. Native
calls remain capped at 24 per run, 120 seconds per call and 15 minutes per run;
each game is at most 80 plies. This is two fixed pairings with one seat assignment
each, not a balanced round robin. Extending routes or resource classes needs a new
reviewed contract, not fabricated compatibility in a replay file.

## September 5 actual conversion

Both original `frontier-four-01` games converted without changing the originals:

| Local file | Actual recorded result | Envelope content digest |
| --- | --- | --- |
| `frontier-four-01-game-1.exhibition.json` | 23 legal plies; resource capped; no winner | `d93a3f429c7878a5d2fc9c69ae15f499d93c8953c4ada3edc480e5cd6fda0c14` |
| `frontier-four-01-game-2.exhibition.json` | failed at first route; zero legal plies; no winner | `21878ca801a89b14b6394bb6480be5e2753e75fffd9a6d24611f50baa25e9c6e` |

These files remain in ignored `live-arena/output/chess-exhibition/`, not bundled
into the website or posted externally. Fable reported `claude-fable-5-1`; Astra's
resolved identity was unreported. The original failed pairing has no accepted
Grok or Gemini decision. The separate later Gemini opening probe is not spliced
into this event. Cost figures remain reported list-price estimates, not measured
incremental subscription charges. The original source, route-limit and cleanup
receipts remain in `OPEN_SOURCE_FRONTIER_CHESS.md`.

The historical runner fingerprint was independently recomputed in this slice from
Git revision `9c359b0`, the six source files named by `chessContestSource()`, Node
`v22.22.0` and the unchanged referee digest. It matches
`5254a206dcb2483cc3b0ba400187bdb9a4fe06fc0e26e221d690b8d0f1afd9c2` in the original
run. This establishes recoverable source custody for the supplied receipts,
not independent provider-execution attestation.

The overall campaign still needs qualified two-family improvement, the remaining
version/training UX, complete eligible-route exhibition evidence, and the creator
task-adapter starter. This replay feature does not waive those gates.
