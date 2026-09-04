# BuilderWars games alpha: release and next increments

Date: 2026-09-04. Owner: Codex. Public brand: BuilderWars.
Source lane: `codex/builderwars-live-games-20260904`.
Hosting: separate Vercel project `builderwars`, id `prj_c2HDxCRh3sEFEZkOxemiwoUmp1Gp`.
Public alpha URL: <https://builderwars.vercel.app>.
Nymrel and the existing receipt-first mobile prototype remain unchanged.

## Delivered contract

- Chess including castling, en passant, repetition, checkmate and selectable human promotion.
- English checkers including mandatory capture chains and promotion-ending turns.
- Connect Four, tic-tac-toe, and bounded custom connect-in-a-row rules.
- Human, free built-in, browser-direct OpenRouter and custom HTTPS harness seats.
- Current OpenRouter catalog; only advertised reasoning efforts; provider fallback disabled.
- Customer-local bridge with exact origin/token checks, bounded requests and session call cap.
- Unlisted peer-to-peer live board sharing, clean OBS view, up to 16 viewers per host.
- Legal-move-validated replay JSON and fragment links with a position slider.
- Paired 2/4/10-game evaluations with seat swaps and export.

No centralized user registry, persistent server, public game uploads, matchmaking,
ratings, leagues, prize pools, scheduled competitions or Twitch/YouTube publishing
is claimed. Creator SDK and existing passport/replay work remain separate durable
foundations. Legal replay is not provider identity or independent result attestation.
Public comments and builder strategies are shared; credentials are not.

## Validation evidence

Local strict TypeScript/Vite build passed. Fourteen engine/input/credential tests
passed; four bridge HTTP/auth tests passed. Dependency audit: zero known findings
at the release-time audit. Browser core suite passed at 320, 390, 768 and 1440px,
including all four games, human win, replay import/export/scrubbing, creator rules,
normal and capped paired series, catalog/effort selection, illegal move rejection,
credential switching and non-persistence. Synthetic provider tests are not API proof.

Lifecycle suite proves one in-flight move, discarded cancelled results and a new
request after reset. Real PeerJS network suite passed both locally and at the
hosted HTTPS origin: two isolated browser contexts, received move, disabled
spectator controls and explicit host disconnect.

Real browser-direct OpenRouter call at hosted origin used
`liquid/lfm-2.5-2.6b:free`: one legal tic-tac-toe move, 541 reported tokens,
2.79-second request, reported cost $0. This is one tested route, not blanket
frontier coverage. A preceding local call reported 486 tokens/$0.

HTTPS website to loopback bridge passed in Chromium 145.0.7632.6, with an explicit
test local-network permission and synthetic backend. This proves transport/auth,
not actual CLI inference. Safari, Firefox and individual subscription clients are
unverified; the UI and guide label the local bridge experimental. The existing
Claude Code execution sentinel remains disabled; no terms were accepted.

## Independent review and disposition

Claude consult requested `claude-fable-5-1` / high. Source-only report
`consult-20260904T232333Z-plan-review-27de6741` returned FINDS. The consult uses
text output; requested model is recorded, but this receipt does not independently
prove a provider-resolved model identifier. A prior 240-second attempt timed out.

- P1 dropped final spectator updates: fixed with trailing-edge coalescing;
  real two-context live test passes. Publish-on-play status added.
- P1 OpenRouter cost omission: not reproduced. Live usage.cost returned without
  an opt-in flag. Current [official usage documentation](https://openrouter.ai/docs/cookbook/administration/usage-accounting)
  explicitly says usage.include is deprecated and no longer required. No deprecated
  parameter added merely to satisfy stale review knowledge.
- P1 deployed-origin bridge gap: Chromium HTTPS-to-loopback test added and passed.
  Cross-browser and per-client claims deliberately remain experimental.
- P2 human terminal UI, mutable move-limit loop, abort notice, secret/strategy
  disclosure, dead host link and duplicate spectator validation addressed.
- Local agent tool exposure: existing Codex backend uses ephemeral scratch and
  read-only mode; OpenCode uses its restricted configuration. Custom commands are
  expressly customer-approved and not represented as sandboxed. No account or
  tool-permission bypass is introduced by the bridge.

## Release boundary and rollback

The first Vercel deployment was automatically assigned production by Vercel despite
omitting --prod. It received production browser/network/model verification. Later
production release is bound to the merged source commit with explicit deployment
metadata. No provider secrets are built into the site. CLI-created local OIDC
file was removed, and .vercel/.env files remain ignored.

Rollback: promote the previous verified BuilderWars deployment through Vercel;
do not roll back or modify Nymrel. This alpha has no server-side customer data or
migrations. Closing a host/bridge stops future local requests but cannot undo
provider requests already accepted. No Cloudflare DNS/domain configuration changed.
BuilderWars.com and BuildersWars.com activation requires its exact domain grant;
the Vercel URL is usable independently.

## Next increments, in order

1. **Own the watch substrate.** Durable match IDs, reconnectable event streams,
   server-side rule validation, authenticated organizers and strict execution budgets.
   Accept only when refresh/rejoin reproduces the same completed match and keys stay
   outside logs, public events and replay blobs.
2. **Creator publishing.** Versioned game/eval manifests, SDK conformance runner,
   resource-constrained sandbox, moderation and abuse handling. Accept only when an
   untrusted submission cannot reach credentials or another match, and a second
   machine reproduces the result under the exact rules version.
3. **Leagues and tournaments.** Bracket/schedule/state machines, paired seeds/seats,
   forfeits/timeouts, quota enforcement, trust-qualified standings and appeals.
   No rankings based only on self-reported browser results.
4. **Repeatable audience loop.** Completed-match pages, opt-in clips, rematch links,
   builder profiles and attributable share-to-play measurements. Measure completed
   matches, spectator-to-player activation and returning builders before claiming
   virality. No fake viewers, model ratings, growth or engagement counters.

Subscription integration expands only through supported customer-local or official
provider flows. Consumer subscription access is never promised as generic API credit.
