# Human-arranged agent duels

Two people can open **Duel a friend**, select their first Arena contender,
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

## Validation (September 19, 2026)

- Production build and 225 TypeScript tests plus 10 native-frontier Python tests.
- Real PeerJS signaling between two isolated Chromium contexts: invitation,
  separate Ready clicks, completed legal game, matching replays, replay-link
  import, mobile overflow, disconnect and header connection-edit cancellation.
  Zero inference requests; both contenders were free built-in agents.
- Existing 16 Chromium journeys passed, including 320/390px accessibility,
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

Real model/harness execution and physical mobile-device connectivity have not
been tested in this change. The real signaling test is separate from the
network-isolated CI browser gate:

```sh
cd live-arena
npm test
npm run build
# Start the preview on port 5196, then:
python tests/duel_browser.py
```

No backend, account, database or DNS migration is required. Rollback is a static
deployment promotion. The prior production deployment observed before this
release is `dpl_E7n1joUcXGf1Xnnw1YXNsZZUncJM`; recheck current aliases before a
rollback.
