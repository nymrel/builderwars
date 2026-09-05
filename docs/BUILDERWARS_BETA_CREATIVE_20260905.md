# Three genuine-match creative drafts

September5,2026. BuilderWars, a Nymrel product. Drafts only; no account or
publication action authorized. The public game runtime is released source
5f92f990; the local-model manual runner is not a new hosted provider feature.

## Evidence set and presentation rules

Free lead: the09:19UTC canonical Connect Four recording, Tactician versus Wildcard,
seven plies, Tactician wins. Built-in policies, no frontier inference or person
claimed. The card and video are in `live-arena/output/playwright/free-demo-production-20260905/`.

Model pair: one09:48UTC actual installed Qwen2.5-Coder-1.5B-Instruct Q4_K_M run,
tic-tac-toe, legal-move constrained generation for both harnesses, plain versus
referee-assisted tactical context. Plain wins game1 in7plies; tactical wins game2
in5plies. Seats swapped; first seat wins both. One pair,1–1,12requests,2397reported
tokens. No memory training, no unaided-model claim, no replicated ranking.

The earlier strict-format run failed twice before accepting a move and is retained
in [the experiment ledger](BUILDERWARS_LOCAL_SHOWCASE.md). It was a different
predeclared output contract, not omitted successful-game data or a hidden retry.
All results, limits and missing costs accompany these drafts.

Canonical model replay links live in the gameplay receipt's `games[].replayUrl`
and `canonical-replays/capture-receipt.json` under the exact directory listed in
the experiment ledger. Each was opened in a fresh browser on builderwars.com.
Attach those exact links, not a localhost URL or fabricated match page. Public
replay contains declared labels, not private runtime paths. Only the sanitized
replay/media are publication candidates; original private call receipts are not.

The supplied replay WebMs use450ms-per-move presentation pacing. Label them
**Replay**, not live inference. The old long-name cards truncate the winner
suffix. Released5f92f990 places winner/seat before the name; fresh canonical cards
are in `canonical-replays-card-5f92f990` beside the original gameplay receipt.
Use those new captures or the full-title mobile replay; retain old media as history.
No simulated viewers, human testimonials or provider logos
implying endorsement. A self-contained fragment replay does not produce dynamic
match-specific social previews.

## 1. Same model, different harness

X draft:

> Same local Qwen1.5B, two harnesses. Tactical hints vs plain; seats swapped.
> Result:1–1, first player won both. Both use legal-move constraints. Two games—not
> a ranking or learning result. Watch both BuilderWars replays.

LinkedIn expansion: “We used one installed Qwen1.5B model for both contenders.
Both had the same legal-move output constraints; one also received referee-computed
immediate-win and reply-safety observations. The split result is a reason to run
better controlled tests, not declare a champion. BuilderWars makes the moves
inspectable so the next harness change can be specific.”

Clip storyboard: show game1's full result, a visible “Seats swapped” intertitle,
then game2's full result. End on “1–1. What would you change?” with both replay
links in the accompanying post. Do not show only the assisted win.

## 2. Human challenge — recommended lead

X draft:

> Seven moves. Can you spot the missed block? Tactician beat Wildcard in this free
> BuilderWars Connect Four demo. Replay it, then choose “Play it yourself.” Can you
> do better? Built-in opponents—not a frontier-model benchmark.

Short-video caption: “A recorded free duel. Find the mistake, then challenge the
built-in opponent yourself. BuilderWars · a Nymrel product.”

Use the actual seven-ply free-game clip/card and matching replay from its receipt.
This is an invitation for human play based on a genuine match—not a claim that
a recruited person already played. No new participant consent is needed merely
to draft the invitation; publishing/recruitment remains separately authorized.

## 3. Resource tradeoff, not a dollar-savings claim

X draft:

> Same local Qwen1.5B: plain used995 input tokens; tactical hints used1282. Output:60
> each. Result:1–1. Both legally constrained. Two games; dollar cost unknown—not
> proof of efficiency. Both BuilderWars replays:

LinkedIn expansion: “The assisted harness used287more input tokens across its six
requests. This tells us what this pair consumed, not which harness is cheaper in
general: positions and game lengths differ, latency is warmup/order-confounded,
and hardware/electricity costs are unknown. Requested provider reasoning effort
was not varied. Our next useful comparison holds the evaluation conditions fixed.”

Clip storyboard: replay the two actual endings, then display the four token
counts and “1 pair · dollar cost unknown · not learning.” Keep both conditions and
the no-ranking caveat visible. Do not translate token counts into fabricated API
prices or call extra prompt text a higher provider reasoning-effort setting.

## Release/readiness and next action

Current September5 checkpoint: PR34 merged/released5f92f990; exact candidate and
main CI passed all five jobs and a new Fable review approved that source. Outcome
artwork is fixed and both genuine replays recaptured on canonical production;
see BUILDERWARS_RESULT_CARD_20260905.md. The frozen-memory diagnostic is now
complete: baseline3/12 versus memory2/12, no uplift; see the experiment receipt.
PR35 contains the manual diagnostic and documentation, not new application code.
Its source review approved8d66404; subsequent c8b1a23 CI33961460460 passed all
five jobs and PR35 merged10791126. The earlier iOS timeout remains historical,
not an unresolved current check. Contrast PR36 is released138e5700 with its
source-bound receipt in BUILDERWARS_CONTRAST_20260905.md; the dated capability
preflight is in PERSISTENCE_PLAN. No social posts or external adoption
observations are claimed. Historical pre-release status follows.

PR33 documentation/recorder update merged as fabe467 after all five exact640d955
checks passed (iOS on one unchanged rerun; initial timeout retained). This new
runner/capture/draft increment still needs its own integration checks. Public
application code is unchanged by it. No social posts, hosted archive, paid
inference or new public model-routing option were deployed.

Local validation:136 Node tests/build and two actual canonical replay captures
pass. Requested independent Fable review did not return a confirmed result:
conversation `builderwars-beta-showcase-20260905`,turn1,
request `0da68782a20452d12858cca76c4bc6a243714069cca09c79f93fab4ffde04e98`,
status `blocked.ambiguous_delivery`, no resolved model/result/usage. It is NOT an
approval. Preserve its state and do not blindly submit the same inference again.
Two early adapter-routing/encoding failures preceded the dispatched request;
neither was model output. After dispatch, X copy was shortened editorially to
leave room for both replay links (219/224/209 ordinary characters before links;
actual platform composer validation still required before posting).

Historical next action (superseded by the checkpoint above): integrate this tested artifact increment, then fix long-name outcome artwork
and run the separately specified held-out learning comparison. External adoption
observations remain unavailable as recorded in the release receipt. Creative
draft readiness is not audience response, virality or measured learning.
