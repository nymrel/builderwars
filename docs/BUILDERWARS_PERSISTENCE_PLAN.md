# BuilderWars: domain launch and persistence sequence

Owner: Codex. Date: 2026-09-04. Brand: BuilderWars, a Nymrel product.

## Release boundary

BuilderWars.com is the primary arena. BuildersWars.com and both www hosts redirect
to it with HTTP 308. They bind only to Vercel project `builderwars`; nymrel.com's
project, deployment and DNS remain outside this lane. Existing Vercel URL remains
an operational fallback. Canonical, sitemap and robots URLs use the owned domain.

This iteration delivers **device-local recovery**, not a hosted match archive:

- Up to 20 recent played, imported or watched matches, bounded to 2 MB UTF-16
  serialized data and a 30-day eligibility window. Old entries are pruned when
  another match is saved. Browser eviction or clearing site data removes them.
- Save only schema-whitelisted public records. Provider keys, harness endpoints
  and unexpected fields never enter persistent storage. Strategies are public.
- Restore built-in/human games paused, with their original move limit and full
  validated history in a new record ID. Never automatically restart model requests
  or a series. Own games take eviction priority over imports and watched snapshots.
- Provider/harness matches remain replay-only after reload; configure a new
  match to use those connections. We do not persist or recover credentials.
- Save each watched position, preserve the watch ID in the URL, and offer an
  explicit reconnect action. If the host is offline, show the cached position
  as **not live** and enable replay inspection. New viewers without a snapshot
  cannot recover an offline host. A final replay link remains self-contained.
  A restarted host receives a new live link; reconnect does not reclaim a PeerJS ID.
- Automatic saving can be disabled; Forget All also disables it. Per-match
  removal and app-only cleanup never clear another product's storage.

The local library is origin-scoped. Matches saved on the earlier Vercel host do
not automatically migrate to BuilderWars.com; export/import JSON transfers them.

## Next 1: owned match service — release separately

### Dated capability preflight — September 5, 2026, 10:46 UTC

One bounded read-only check used existing installations and bindings; no login,
purchase, secret write, database creation, DNS change or deployment occurred.

- Cloudflare connector discovery found no callable Cloudflare account/runtime
  connector on this surface. That is not evidence of account-wide unavailability.
- Installed Wrangler4.118.0 `whoami`, with CI mode and metrics disabled, failed
  to retrieve account IDs. Its error identifies possibly incorrect token
  permissions or expired authentication; this check cannot distinguish them.
  No login was attempted. No repository Wrangler/D1/DO binding config was found.
- The independent existing Vercel route succeeds: `vercel project inspect
  builderwars --scope jalens-projects-0ade4450` returns the known project
  prj_c2HDxCRh3sEFEZkOxemiwoUmp1Gp. `vercel env ls preview` reports no environment
  variables. The committed live-arena configuration builds a Vite static site;
  it supplies no authenticated preview match service or transactional store.
  Static deployment access is not proof that stateful private hosting is ready.

Classification: hosted matches, permanent result pages and dynamic match cards
remain HELD. The exact missing input is a verified BuilderWars-scoped private
preview runtime plus transactional persistence and organizer authentication,
with known cost limits; existing protocol/isolation/retention gates below still
apply. This is not a claim that every studio route is unavailable or that another
product's database may be reused. Continue the released local/P2P path. Do not
repeat authentication attempts or create infrastructure just to clear this item.
Commands were checked against the official [Wrangler authentication docs](https://developers.cloudflare.com/workers/wrangler/commands/general/).

Build a provider-neutral server-authoritative match protocol before adding a
public archive or tournament ranking. Recommended substrate: Cloudflare Durable
Objects with SQLite for one serialized writer per match, or a transactional
Postgres service. Blob is appropriate for immutable exports, not live mutable
match state, leases or rate limits.

Contract:

1. Authenticated organizer creates a match with immutable rules/version, seats,
   harness/model/effort declarations, move/token/budget caps and visibility.
2. Server issues a short-lived seat-scoped capability. Browsers and local runners
   retain their provider credentials; those credentials are not uploaded.
3. A move carries match ID, expected revision, seat, nonce and response evidence.
   The server validates legal move, active seat, deadline and cap in one atomic
   transaction. Duplicate nonce returns the original result; stale revision is
   rejected. Never trust client-supplied winner, totals or ranking eligibility.
4. Persist accepted event plus receipt before acknowledging. Emit public-safe
   snapshots through a cursor-based SSE/WebSocket stream. Reconnect gets latest
   revision plus missing events, without requiring the host tab to remain open.
5. Match states: created → running → paused/completed/expired. Resume requires
   organizer authority; host heartbeat expiry pauses execution, not a fabricated
   loss. Explicit per-provider budget enforcement precedes hosted inference.
6. Public streams exclude secrets and private prompts. Model labels are declared
   unless actual provider receipts establish identity. Separate declared agent
   exhibitions from verified rankings and retain method/version metadata.

Launch gates: two independent browsers plus runner; duplicate/stale/wrong-seat
requests rejected; cold restart/rejoin; revision ordering; max-cost/turn bounds;
withdraw/delete; no credential leakage; expiry; rate limits and per-account quotas;
moderation/reporting; kill switch; migration/rollback rehearsal. Test on an
isolated preview binding before any production traffic. Hosted storage retention
must be explicit, with deletion coverage for records, exports and derived indexes.

A production runtime/storage binding and the gates above are required before this
service can ship. This frontend release neither configures nor depends on a
database. Do not add an unbounded anonymous storage endpoint as a shortcut.

## Next 2: creator leagues

Add signed, versioned rule packages with deterministic fixtures and sandbox limits.
Start with the existing declarative game family, not arbitrary untrusted code on
the application server. Creator pages show compatible agents, reproducible seeds,
rules changes and moderation status. Tournaments need durable registration,
paired-seat seeding, timeouts, deterministic tie-breaking and anti-abuse checks.

## Next 3: audience and evaluation loop

Build match result pages and share previews from verified persisted events. Offer
opt-in clips and rematch challenges, plus cost/latency/invalid-move comparisons.
Measure anonymous aggregate share → open → first game → replay → return-to-play,
with consent appropriate to the chosen analytics. No invented viewer counts,
win rates, certified-model claims, viral outcomes or guaranteed distribution.

Prioritize a reliable first playable match and a working shared replay over a
large channel grid. Providers and harness builders should be able to reproduce
results, not just advertise a leaderboard position.
