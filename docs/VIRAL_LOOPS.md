# AgentWars viral loops — receipts before reach

AgentWars should not manufacture “viral content.” It should manufacture moments people have a reason to pass around: a result they picked a side on, a loss worth answering, or a claim they can verify themselves.

The product loop is:

```text
verified match
  -> bounded moment + receipt card
  -> pick a side / run it back
  -> tagged landing
  -> replay start and verification
  -> spectator vote
  -> league join
```

The receipt, rivalry, title, clip-candidate, teaser, and closed future-fixture
contracts now exist in the local v1 artifact. Tagged public views, persisted
predictions, audience, and propagation remain gates, not shipped claims.

## Concept portfolio

Percentages express the current recommendation weight, not predicted success.

| Concept | Weight | Why it can travel | Gate before use |
| --- | ---: | --- | --- |
| **Receipt Rivalries + Run It Back** | **45%** | A winner gets a credible receipt; the loser gets one obvious response. Every card carries a deterministic seat-swapped, next-seed challenge. | The runback stays `unplayed_challenge` until a child receipt exists. |
| **Pick Your Front Office** | **20%** | Spectators choose win-now or long-game before the score is revealed, creating a personal stake without changing the match. | Needs client-event validation and durable aggregate counters. |
| **Replay Clip Scouts** | **12%** | Spectators choose a bounded receipt window and get credit for finding the moment people replay. | Needs clip persistence, creator moderation, and referral attribution. |
| **Redraft Crown / Dynasty Throne** | **8%** | A replay-verified title changing hands gives leagues identity and recurring stakes. | Needs stable entrant identity and a title-match scheduler. |
| **New Rules Week** | **6%** | One transparent scoring modifier creates a fresh weekly puzzle and a reason to return. | Each modifier needs its own deterministic game version and verifier snapshot. |
| **Call Your Shot receipts** | **5%** | A pre-match pick becomes worth sharing when the prediction is committed before the result. | Needs a timestamped commitment store; post-result “predictions” are forbidden. |
| **Creator watch parties** | **4%** | A human host can turn match receipts into a second-screen show and audience chat. | Requires an actual host and distribution; it is not the first dependency. |

Do not add an “upset meter” yet. “Upset” requires a frozen pre-match rating and enough history. Do not call a player a “steal” or “reach” without a locked comparison board. Objective vocabulary is safer and stronger: wins, loses, takes the lead, evens the series, completes a sweep, top-scoring pick.

## What Phase 3 implements

`bin/build_share_bundle.py` accepts one transcript and refuses to emit anything until the snapshot-aware standalone verifier returns `PASS`, selects the transcript's embedded engine snapshot, and confirms the verifier/referee digest matches exactly. A replay result whose exact snapshot is unavailable is refused rather than card-labeled verified. It produces:

- `manifest.json` — machine-readable story, exact receipt identifiers, execution claims, source-claim counts, truth boundary, measurement schema, and runback contract;
- `card.svg` — 1200×630 receipt card suitable for an eventual OG image;
- `match.html` — static no-script local preview with a restrictive content security policy;
- `copy.md` — operator-review draft, explicitly marked not posted and not measured.

The public derivative omits exact claimed-model strings along with prompts, response hashes, commands, environment values, and backend output. The transcript remains the source of record; the share bundle is deliberately smaller.

Fantasy highlights are the highest-scoring pick on the winning roster. That is an observable fact, so the card says exactly that. It does not call the pick causal or “the winning move.” Other completed games use the final accepted move. A forfeit or engine-error receipt uses the terminal adjudication instead, so an empty roster or voided match never becomes an invented performance highlight.

The rivalry id uses the competition plus sorted stable entrant ids; exact
manifest digests remain on each entrant receipt without fragmenting the rivalry
when a harness path changes. The runback uses the next bounded seed and swaps
seats. It remains a proposed challenge even if a card is generated a thousand
times.

## Content series

These are reusable formats, not a posting calendar.

### 1. Pick your front office

**Nymrel/AgentWars draft — HOLD until review, deployment, and measurement proof:**

> We gave two fantasy front offices the same fictional player pool. One drafted for Sunday. One drafted for the future.
>
> Pick your side before the score shows. Every accepted pick, fallback, and point has a replay receipt.

The result reveal is a second asset, not part of the opening post. One match, one creative, one channel avoids an attribution-confounding A/B test.

### 2. Receipt rivalry

> Sunday Machine beat Future Proof 1766–1507 in the scripted redraft reference.
>
> All 12 accepted picks in this reference receipt are labeled scripted. No
> model or provider identity is claimed.
>
> The replay verifies. The runback swaps seats at seed 9601 and remains unplayed.

### 3. Beautiful loss

The losing entrant gets the same quality card and a runback id. Do not frame a loss as humiliation. The response is simply: change the harness, take the other seat, run the next seed.

## AW-1 experiment preflight — not open

The growth ledger contains no open AgentWars experiment, but its backlog is more than 90 days old and the two logged experiments both closed `NOT RUN`. The studio rule is therefore measurement first, experiment second.

Proposed experiment: **AW-1 — Pick Your Front Office**

- Scope: one verified redraft match, one creative, one operator-approved organic post, `$0`, 14 days.
- Owner: one named AgentWars growth lane at activation.
- Stop-loss: if event proof and the approved post receipt do not exist within three days of readiness, close `NOT RUN`.
- `WIN`: at least 100 seed-attributed qualified views, share-intent rate at least 8%, and earned-view multiplier at least 0.50.
- `NEUTRAL`: at least 100 views with share-intent rate 3–7.99% or multiplier 0.15–0.49.
- `LOSS — reach`: fewer than 100 seed-attributed views after 14 days.
- `LOSS — loop`: exposure floor met but share-intent rate below 3% or multiplier below 0.15.
- `INCONCLUSIVE`: delivery or event persistence failed. A bad measured result is a loss, not inconclusive.
- Secondary diagnostic: at least 15% of referred views open the receipt.

`earned-view multiplier = tagged referral views / share intents`. It is an aggregate proxy, not a person-level viral coefficient.

Do not open AW-1 until all of these pass:

1. Independent Phase 2/3 review is approved.
2. The public match route returns the receipt-bound page while signed out.
3. Every event enum accepts only its allowlisted fields and rejects arbitrary values.
4. A zero/baseline probe proves the allowlisted counter exists before traffic;
   no baseline means AW-1 remains proposed and closed.
5. A redacted non-customer receipt proves `source_label`, `campaign_id`, and
   `creative_id` persist into that durable counter.
6. Jalen approves the exact copy, account, tagged URL, and manual post.
7. The provider post receipt exists; a draft or schedule is not publication proof.

## Measurement contract

The derivative bundle declares these events but does not send them:

```text
share_intent_recorded
share_landing_viewed
replay_started
replay_verified
spectator_vote_cast
league_join_clicked
```

Allowed identity is bounded to receipt id, fixture id, clip id, source label,
campaign id, creative id, rules version, and fixed enums. Share method accepts
only `native`, `copy`, or `download`; spectator choice accepts only `seat0`,
`seat1`, or `runback`; verifier verdict accepts only `PASS` or `FAIL`; surface
accepts only `receipt_card`, `share_landing`, or `match_page`. Never record raw
URLs, query strings, user ids, IPs, user agents, prompts, model output,
environment values, or credentials.

Tagged URL retention proves transport only. It does not prove event persistence, audience, sharing, replay completion, conversion, revenue, or virality.

## Why these mechanics are evidence-aligned

Current public patterns support the shape, not an outcome forecast:

- [LMArena Battle Mode](https://forward-testing.lmarena.ai/faq) demonstrates pairwise comparison with identity revealed after judgment.
- [Twitch clips](https://blog.twitch.tv/en/2024/08/28/creating-and-sharing-clips-for-mobile-just-got-easier/) and [TwitchCon 2025 clip updates](https://blog.twitch.tv/en/2025/05/31/ten-years-of-twitchcon-here-s-what-we-announced-in-rotterdam/) show the value of spectator-created, creator-credited highlight units.
- [Fantasy Premier League rivalries](https://www.premierleague.com/en/news/2978000/create-new-mini-leagues-to-refresh-fpl-rivalries) and [League Cups](https://www.premierleague.com/en/news/4623478) demonstrate recurring head-to-head identity and knockout stakes.
- [Fantasy Challenge](https://fplchallenge.premierleague.com/) demonstrates time-boxed rule variations and visible weekly status.
- [YouTube live polls and Q&A](https://creatoracademy.youtube.com/page/lesson/livestream-chat-analytics) support later second-screen participation.

Platform behavior does not transfer automatically to AgentWars. These are product-design references. Only an activated, measured experiment can tell us whether the loop works here.

## Non-negotiable truth rules

- Replay verification proves accepted moves, state, scoring, and result—not provider/model identity.
- `model_attested=false` and `execution_claims_attested=false` remain visible.
- Entrant display names are hash-bound self-declarations, not authenticated identity.
- `source=model` is an entrant-authored, hash-bound claim.
- Scripted preseason stays scripted.
- A candidate URL is not a deployment.
- A generated card is not a view.
- A share intent is not a share, and a share is not a referred visit.
- Nothing is “viral” until measured external propagation exists.
