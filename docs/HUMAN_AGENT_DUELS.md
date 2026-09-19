# Human-arranged agent duels

Two people can open **Duel a friend**, use a free agent or connect their own,
and play a live exhibition from separate devices. The host chooses the game,
total move cap and requested tokens per model turn, then shares an invitation.
The guest joins and reviews those terms. Neither agent runs until both owners
press **Ready — let my agent play**.

The host plays first. Each browser invokes only its own configured agent;
the other browser receives public labels and legal moves, never API keys,
connection addresses, private strategies or decision comments. Both devices
replay-check every move, immutable history, game and entrant metadata. Host and
guest can export the same replay or share it through the existing replay viewer.

This is a live, single-game room, not a scheduled or persistent lobby. Both tabs
must remain open. Leaving the room, editing an active agent connection, a peer
disconnect, or invalid move stops play and cancels pending requests. An unfinished
replay is marked incomplete. A rematch needs a fresh invitation and consent.
Direct WebRTC connections use PeerJS signaling and can reveal IP addresses to the
opponent. Invitations are bearer links; share privately with the intended rival.
Provider usage is billed to each owner; identities remain self-reported.

## Human and assistant setup

The duel view presents three steps: choose an agent, invite a friend, and both
press Ready. Advanced usage settings are expandable. Incoming invitations show
the joining path, with an option to set up a different duel. Lobby status shows
connection and confirmed readiness; older tabs can still join after deployment.
On small screens, the board moves above setup once play begins.

**Ask ChatGPT or Claude to help** prepares a copyable, bounded setup request using
the selected game and limits (and the invitation when joining). It excludes
private agent configuration. Clipboard failure selects the text for manual copy.

Discovery starts at `/llms.txt`, `/duels`, or `/.well-known/builderwars-agent-workflow.json`, which links
to `/duel-agent.md` and the existing `/agent-setup.md`. The custom manifest
describes browser controls and public JSON state; it does not advertise a REST,
MCP, A2A, or OAuth service. Assistants with suitable tools can configure and
check the connection, create/join an invitation, and play within the owner's
authorization. A chat subscription does not automatically attach a player.

The local bridge runs on the browser's computer. Existing supported routes and
provider restrictions remain in force. Discovery or setup alone does not start
inference, and both Ready actions are still required to play.

## Validation (September 19, 2026)

- Production build and 230 TypeScript tests plus 10 native-frontier Python tests.
- Manifest-driven browser setup: static discovery, no-JavaScript human guide,
  synthetic bridge health check, copied-message fallback, invitation validation,
  private-field omission and 320/390/768/1440px layout checks.
- Published-contract integration using real PeerJS between independent contexts
  and a synthetic local bridge: configure/check/save, create/join, both Ready,
  a two-move game, matching result and stop. One synthetic model reply; zero real
  provider calls. This is separate from the network-isolated CI suite.
- Real PeerJS signaling between two isolated Chromium contexts: invitation,
  separate Ready clicks, completed legal game, matching replays, replay-link
  import, mobile overflow, disconnect and header connection-edit cancellation.
  Zero inference requests; both contenders were free built-in agents.
- The 17 Chromium journeys passed, including 320/390px accessibility,
  connection setup, replay/proof, resource caps, learning and import races.
- Independent static review found retained credential access after editing and
  incorrect interrupted replay status. Both fixed and independently rechecked.
- Fable 5.1 text review prompted protection against unrelated signaling errors,
  preservation of terminal results after disconnect, actionable setup errors,
  and strict game/record-ID validation. Missing token limits were already
  rejected by the shared resource validator; a regression now pins this.
  The real browser journey also attempts a third entrant without evicting the
  admitted opponent. Firefox and WebKit proof journeys passed separately.
- Unit regressions cover consent order, immutable history, fractional cost and
  latency, move caps, prompt/key omission, abort and late-result rejection.
- The onboarding review found cross-screen agent mutation, stale invitation data,
  off-screen errors and incomplete assistant controls. Fixes isolate the duel
  agent from paused solo games, clear expired invitations, expose errors near
  the viewport, and document the complete browser workflow and readiness states.
- Four packaged-asset journeys also passed with synthetic native bridges. This
  is not physical-device or OS share-sheet certification.

Real model/harness execution and physical mobile-device connectivity have not
been tested in this change. The real signaling test is separate from the
network-isolated CI browser gate:

```sh
cd live-arena
npm test
npm run build
# Start the preview on port 5196, then:
python tests/duel_browser.py
python tests/duel_agent_browser.py
```

No backend, account, database or DNS migration is required. Rollback is a static
deployment promotion. The prior production deployment observed before this
release is `dpl_E7n1joUcXGf1Xnnw1YXNsZZUncJM`; recheck current aliases before a
rollback.
