# BuilderWars playable alpha

A static, browser-hosted arena: real rules, real moves, optional customer-owned
models, peer-to-peer spectators, and portable replay evidence. No platform API
keys, centralized account database, paid credits, fabricated audience or rankings.

## Local self-improvement lab

`npm run improve -- --game tictactoe` runs bounded, outcome-trained local policy
development. It saves immutable candidates, paired evaluation evidence and a
retained/promoted local champion. It makes no provider calls and does not change
website contenders. This is not LLM weight training or industry-strength proof.
See [training, local-harness execution and limitations](../docs/BUILDERWARS_SELF_IMPROVEMENT.md).
On Windows PowerShell, use `npm.cmd` when passing flags to preserve the arguments.

`npm.cmd run strength -- --game tictactoe --pairs 16` measures the zero-weight
baseline against seeded random and a fixed immediate-tactics opponent. Add
`--policy PATH` to measure an existing artifact. Reports separate seats, completed
outcomes, missed wins and avoidable next-reply losses. Public development fixtures
are not hidden admission data. This never promotes or changes a website contender.
See the [frontier campaign](../docs/FRONTIER_CAMPAIGN.md) for the remaining gates.

`npm.cmd run frontier -- init --id my-training --game tictactoe` creates an isolated
local experiment; `run --id my-training` records verified errors, bounded numeric
practice and a frozen candidate. Explicit one-shot tactical qualification never
promotes by itself. See [versioning, custody and commands](../docs/FRONTIER_HARNESS.md).

## Play and build

```sh
cd live-arena
npm ci
npm run dev
```

Open the printed local URL. **Quick match** runs the currently selected contenders;
the initial pair are free built-in Tactician and Wildcard. Games: chess (chess.js),
English checkers, Connect Four and tic-tac-toe. Human seats support board clicks;
choose a chess promotion piece under Match settings before promoting.

Forge creates bounded connect-in-a-row definitions (3–10 rows/columns, optional
gravity). Import/export rules as JSON. For entirely new engines, use the repository's
`creator_sdk/`; uploading arbitrary executable code to the public website is not supported.

Evals runs 2, 4 or 10 exhibitions, swapping seats. Each game respects its move limit.
Invalid output or a connection error pauses the series without substituting a bot.
Requested effort and provider-reported identity are not independent execution attestation.

## Bring models and harnesses

Start with the [human and agent setup guide](public/agent-setup.md) for choosing a
connection, preparing a secret-free profile, and checking it before play.

### OpenRouter

Connect a seat, select OpenRouter, browse its current catalog, choose an advertised
reasoning effort, and enter **your own OpenRouter API key**. It is sent directly
from this browser to OpenRouter, never to BuilderWars hosting. It is kept only
in tab memory, and lost on refresh. It is not in exports, broadcasts or localStorage.
Switching connection type or harness endpoint clears the credential field.

OpenRouter usage is separate from ChatGPT or Claude consumer subscriptions.
Free routes require your own key and provider availability. Token/move limits are
request limits, not a guaranteed dollar cap. Set provider-side budgets as well.
A request already accepted by a provider may still be billed after Pause.

### HTTPS harness

Use your endpoint and optional bearer token. It must allow the exact website
origin through CORS, accept POST JSON and reject requests you have not authorized.
The browser rejects redirects, embedded URL credentials, queries, and non-HTTPS
endpoints except `http://127.0.0.1:8765`.

```json
{
  "schema": "builderwars.move.v1",
  "game": {"kind":"chess","name":"Chess","rows":8,"cols":8,"connect":0,"gravity":false},
  "position": "current FEN or array of board cells",
  "turn": 0,
  "moves": [],
  "legalMoves": ["e2e4"],
  "model": "your-model-label",
  "effort": "high",
  "strategy": "Control the center",
  "maxTokens": 2048
}
```

Return `{"move":"e2e4","comment":"Control the center.","model":"resolved-model"}`.
The legal move list is authoritative. Comments are public and capped at 240
characters; do not return private reasoning or secrets. Optional `tokens` is
self-reported. Replies have a 1 MB limit and a 120-second timeout.

### Customer-local subscription/client bridge

Run from a full source checkout on **your own machine** with an already configured,
supported client. Provider terms and account entitlements still apply. BuilderWars
does not obtain, proxy, or resell a consumer subscription or copy login cookies.

```sh
python live-arena/bridge.py --origin https://YOUR-DEPLOYED-SITE --provider opencode --model YOUR-CONFIGURED-MODEL --allow-model-requests --max-calls 20
```

The bridge prints a temporary local connection token. Paste it in a harness seat
with endpoint `http://127.0.0.1:8765/move`. Browser local-network permission may be
required. Leave the terminal open; Ctrl+C stops it. Do not expose the port publicly.

Backend choices reuse the existing customer-local adapters: `chatgpt_codex`,
`opencode`, `openrouter`, `hermes`, `custom_agent`. The repository's legacy
`claude_code` adapter is held by provider policy and is not offered by this bridge.
Claude models remain selectable through eligible OpenRouter API routes. Availability
depends on the installed client. The bridge's configured model/variant is fixed
at startup; browser model/effort labels do not reconfigure it. CLI clients have
their own token/budget controls; the browser token setting is not enforced by this
bridge. Custom commands additionally require `--allow-custom-command` and a fixed
JSON argv `--command`. Never run an untrusted command or grant filesystem/tool
permissions to match content. Only one request runs at once; all attempts count
toward the session cap. Bridge HTTP/auth tests are not proof of every CLI provider.

## Watch and share

Broadcast creates an unlisted WebRTC board link for up to 16 viewers, using
PeerJS's public signaling service. The host tab must stay open. Peer connection
metadata can reveal IP addresses. Viewers receive model labels, strategies,
moves and public comments, but no connection keys or endpoints. They validate
every move locally. Stop broadcasting in Watch; closing the tab also disconnects.

Clean stream view works as an OBS source. Twitch/YouTube video publishing remains
in your own streaming application. There is no central livestream directory or
always-on match server. Network/NAT restrictions may prevent live connections.

Share replay copies a compressed fragment URL; a recipient can scrub the board
and inspect every move. JSON export/import is the fallback for large records.
The fragment is not uploaded to BuilderWars hosting. Anyone with the link can
read its public match data. Legal replay does **not** prove that a claimed model
actually generated those moves or that reported costs are independently verified.

## Validation and release

### Recent matches

Played and watched games save on this browser by default (up to 20 entries, 2 MB,
30-day eligibility; prune on the next save). Own games take priority over spectator
snapshots and imported replays. Disable saving or Forget All in **Recent matches**;
Forget All disables future auto-saves. Device clearing or browser eviction removes
the library. Keys and harness URLs are not saved. Public strategies/comments are.

Resume restores a built-in/human game **paused**, into a new record ID to avoid
cross-tab continuation conflicts. It preserves the move limit. Provider games are
replay-only after reload; reconnect those contenders in a new match. Replay URLs
do not automatically enter the library; use **Save current replay** to retain one.

Spectator reload attempts the same live host link and shows a saved, explicitly
non-live position if unavailable. A 5-second heartbeat detects silence after
15 seconds (browser timer throttling can extend this). If the host restarts their
broadcast, they must share its new link. There is no server archive or background
model execution. Browser storage is origin-scoped; export/import JSON when moving
from the Vercel fallback host to `https://builderwars.com`.

```sh
npm test
npm run build
python -m unittest discover -s tests -p test_bridge.py
python tests/browser.py
python tests/network.py
python tests/recovery.py
```

Browser tests need Python Playwright and Chromium. Set `BUILDERWARS_TEST_URL`
to test another local or deployed origin. Browser suite uses explicitly synthetic
provider replies; network suite uses real PeerJS signaling and two browser contexts.

Vercel project root is this directory, with no secret environment variables.
`vercel.json` defines security headers and static routes. Do not deploy this root
into the existing Nymrel project. Roll back by promoting a previous verified
BuilderWars deployment; for the first release, revert/unpublish this project
without touching Nymrel. BuilderWars.com and BuildersWars.com were activated under
PA-0904-0642; future DNS changes still require exact domain authority.

References: [OpenRouter reasoning](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens),
[model catalog](https://openrouter.ai/docs/guides/overview/models),
[chess.js](https://jhlywa.github.io/chess.js/),
[PeerJS cloud signaling](https://peerjs.com/server/cloud).

### Non-inference connection checks

Connections includes **Check connection · no model call**. OpenRouter checks use
its authenticated key-info GET; the local bridge uses authenticated `/health`
without invoking a model or consuming its session call cap. Known routes are
checked automatically before their first move; successes cache for at most 60s
for the same configuration. This does not prove model access or billing limits.
Generic HTTPS harnesses have no assumed health protocol and are explicitly
configuration-only/unchecked until a real capped move is requested.

See [connection preflight and its limits](../docs/BUILDERWARS_CONNECTION_PREFLIGHT.md).
Run `python tests/connections_browser.py` against an owned preview for synthetic
authentication/error/cancellation tests; `python -m unittest tests/test_bridge.py`
checks bridge auth and no-call health behavior on isolated ephemeral ports.
