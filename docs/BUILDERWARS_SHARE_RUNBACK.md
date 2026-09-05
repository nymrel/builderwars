# BuilderWars: share a result, challenge a matchup

September 4, 2026. Candidate work in draft PR [#29](https://github.com/nymrel/builderwars/pull/29), not a production release receipt. BuilderWars is a Nymrel product.

## What a player can do in this candidate

1. Choose Connect Four, then **Play free**. Two built-in opponents play without an account, key or provider request. Chess, checkers and tic-tac-toe remain available.
2. After a finish or pause, see the outcome computed from legal moves. A partial game says **Unfinished match**, not a fabricated win. Timing and cost describe accepted moves; they are not a provider billing reconciliation.
3. Download a 1200×675 result image or copy a caption with a self-contained replay. Public names/model labels and moves are included. New public links omit strategy and commentary; private connection fields are never copied. Existing local JSON exports keep their documented legacy format.
4. Open that replay in a clean browser, inspect its move history, then choose **Run it back · free** or **Play it yourself**. A runback preserves the rules but intentionally replaces original entrants with free built-ins or a human plus a built-in. It does not reproduce an original model's behavior or promise the same outcome.
5. **Share current setup** works before a match has moves. The recipient sees a preview; merely opening the link does not overwrite a recoverable match or start requests. **Prepare original matchup** clears keys, private prompts and harness addresses and stays paused. The recipient connects their own contenders and explicitly starts later.

`builderwars.setup.v1` accepts only canonical bounded game rules, two public entrant declarations, move limit and requested token limit. It rejects unsupported/extra fields, noncanonical or oversized encodings, invalid built-ins and altered standard rules. Harness setup links deliberately omit private model/effort labels. Public display names and model labels should never contain secrets.

The image and caption are created on the device. There is no result upload, automatic social post, dynamic per-match Open Graph preview or permanent hosted match page. Attach the image alongside the replay link. Some sharing tools impose shorter URL limits than the app's safety ceiling; use a downloaded replay if a platform rejects the link. The full replay and a fresh setup are different artifacts, not interchangeable proof.

## Evidence boundaries

- The result renderer replays rules before describing the winner. A supplied `status` string cannot change the outcome.
- Connect Four can additionally export `builderwars.board.v1` proof and its exact standalone verifier. Other games retain ordinary replay verification at this stage.
- A legal replay is not provider identity, authenticated builder identity, execution, billing or general-intelligence attestation. Entrant labels are declarations. A signed-in account or named model must not be implied from these exports.
- Unknown or unrepresentable aggregate usage remains unknown. Canceled requests and other provider charges may not appear in accepted-move totals.
- A same-rules rematch is not a controlled comparison by itself. Seat swaps, fixtures, samples and failures belong in Evals.

## Repeatable demonstration

With the built local preview running on 5178:

```powershell
python tests/sharing_browser.py
python tests/record_demo.py
```

The first is scripted QA: human moves produce a known seven-ply win, export a PNG and sanitized replay, and test a clean recipient, human/free rematches, missing-key protection, clipboard denial and 320px layout. It is not a real external-human match.

The second records one actual free built-in game without selecting its outcome. It records a WebM, downloads the result PNG and proof/verifier, independently verifies that match, and writes a receipt with source hashes. Its output lives under ignored `live-arena/output/playwright/free-demo/`. The capture script is deliberately manual, not a CI/browser-video dependency.

Observed local capture: Tactician versus Wildcard, Connect Four, seven plies, winner seat0, four in a row. The verifier reproduced it with model/execution/billing attestation false and no OpenRouter requests. This is an automated studio demonstration of real built-in play, not frontier inference, recruitment or adoption evidence. An initial capture exposed a test timing issue: terminal board state appeared before the result panel finished rendering. The recorder now waits for that panel; the repeat was not selected for a preferred winner.

## Creative package: held until exact-source release

Use the real free-match recording as the lead. Do not substitute frontier model names for its built-ins.

Short clip cut:

- Opening: “Can you beat this?” over the actual Connect Four board. Keep **Built-in · free** visible.
- Middle: show the recorded moves at a readable pace. If shortened, label it a replay/speed-up rather than suggesting real-time provider latency.
- Finish: the actual winning board and result card; “Replay it. Try a free rematch.” Include the matching replay link with the post.
- End card: BuilderWars / a Nymrel product. No artificial live-viewer count, external-user testimonial or intelligence ranking.

Narrative queue:

| Story | Evidence available | Next requirement |
| --- | --- | --- |
| Human challenge | Working human-vs-built-in path; scripted human QA is labeled | Consenting participant and an actual recorded challenge before presenting a person's result |
| Same model, different harness | Setup sharing and local/HTTPS harness paths exist | Eligible real model route, confirmed run cap, matched settings and paired results; no claimed outcome yet |
| Cost/effort tradeoff | Unknown-cost handling and declared effort labels work | Real comparable samples with response metadata and reported costs; no superiority or savings claim yet |

Public copy is a release-gated draft, not a live claim:

**X:** “Can you beat the built-in opponent? Play a free game on BuilderWars, replay the result, then run it back. Connect your own agent when you're ready. A Nymrel product. https://builderwars.com”

**LinkedIn:** “We're building BuilderWars around a simple loop: play, inspect the result, and try again.

The free game uses built-in opponents. Builders can connect their own contenders; shared replays show the moves, while the evidence labels distinguish rule validation from verified model identity.

Our next question is practical: do people want a rematch? https://builderwars.com”

**Short-video caption:** “A free built-in duel on BuilderWars. Watch the moves, then try the matchup yourself. Recorded demo; not a frontier-model benchmark.”

Before any post: independently accept and deploy the exact candidate; open its replay on canonical production; verify account/composer and obtain the exact publication grant; attach the correct image/video; review copy against actual shipped behavior. No posting action is authorized by this document.

## Current checks and next milestone

41 Node tests and the production build pass locally. Existing four-game, lifecycle, recovery, proof/CSP/SRI browser suites and four bridge tests pass, as does the new sharing journey. Tests use synthetic/free entrants, not paid providers. Cross-family review and CI for the final new commit remain separate gates; do not reuse an older head's green badge.

Next: resolve the candidate's independent review, then continue the runnable Academy/provider-harness/paired-experiment milestone. Keep Nim/exhibition-v2 draft PR27 separate until record compatibility and duplicate CI are reconciled. Do not grow public hosting or a creator marketplace before the core replay/challenge experience is accepted.
