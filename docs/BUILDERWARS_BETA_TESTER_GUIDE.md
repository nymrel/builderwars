# BuilderWars beta test: play, replay, improve

## Before you start

Use the exact test URL and version supplied with your invitation. The verified
September 5 web release is `d0873da`; see the
[release receipt](BUILDERWARS_RELEASE_20260905_NATIVE_CHECKPOINTS.md).
The public site is [BuilderWars](https://builderwars.com). If a named control is
missing there, record the URL/version and stop that check instead of assuming it
passed. No TestFlight or Google Play installation is offered by this document.

Allow about 10 minutes for the core checks. No account or model key is needed:
use **Built-in opponent · free** throughout. Connecting an external model is an
optional, separately budgeted test; a provider's free-route label is not a promise
of availability. Do not paste keys into feedback, chat, screenshots or exports.

## Core checks

1. **Start without setup.** Open a fresh browser tab and select **Play free**.
   A match should start within two intentional actions, without signing in or
   entering a key. Record anything that prevents the first move.
2. **Play a complete game.** Choose **Connect Four**, keep both contenders free,
   and select **Start match**. Let it finish. The board, move history and result
   should agree. A move-limit stop is not a completed win or draw.
3. **Take a turn yourself.** From the result, select **Play it yourself**. Make a
   legal move on the board and check that the opponent responds. Try an occupied
   or full location: it must not add an illegal move or silently change the turn.
4. **Replay elsewhere.** Finish a free match, select **Share replay**, and open
   the link in a different browser or private window. Check the same game, move
   count and result. It should not start model calls. Links contain their replay
   data; they are not private accounts or permanent hosted match pages.
5. **Challenge safely.** Select **Share this setup** from a result. Open it in the
   second browser: a preview should appear before play. Select **Play free** and
   complete a new match. The new game must not require the original player's key.
6. **Keep and recover a match.** Read **Recent matches**, enable device saving if
   you agree, play several moves, pause, then reload. Open the saved game and
   follow the offered resume/replay action. Check the board before continuing.
   If storage is unavailable, the app should say so; download the replay instead.
7. **Check a small screen.** Repeat a human turn on your phone or a narrow browser
   window. Confirm board controls, dialogs and result actions remain reachable.
   On desktop, use Tab and Enter without a mouse and check that focus is visible.

Optional: in **Forge**, create a small connect-in-a-row game, export and import
its rules, then play it. In **Evals**, run a two-game series with free opponents
and confirm seats swap. These results compare those games, not model training.

## Check a result independently

For a completed Connect Four game, open its proof controls and download both
**proof (.jsonl)** and the **matching verifier**. With Node.js 22 or later, run
`node <downloaded-verifier-name>.mjs <downloaded-proof-name>.jsonl` locally. The
verifier needs no packages or network. Keep the original files; changing a move
in a separate copy should make verification fail. Ask for help rather than
installing unfamiliar software merely to finish this optional technical check.

Passing proves the recorded moves/result follow that referee's rules. Displayed
model names, reasoning effort and token/cost reports are not independent proof
that a particular provider executed the game.

## Learning check: limited practice context, not model training

Confirm the tested release against the receipt above. Do not expect free fixed bots,
chess or checkers to learn from the initial connect-game feedback feature.
The web release adds past tactical mistakes to supported connected agents' later
requests; it does not train model weights or guarantee better play.

For an approved, capped provider/harness test, record the model, effort, strategy,
game rules and version. Complete a supported practice game that contains a
missed immediate win or avoidable immediate loss. Check that it records a lesson
and that the next request includes it. Report whether the agent follows it.
Imported games, spectator games, unfinished games and evaluation outcomes must
not add lessons. Evaluate with memory off, or with a frozen practice snapshot;
do not change memory between games and call that a fair comparison.

A lesson count or one improved rematch is not proof of learning. Performance
testing needs unseen positions, equal budgets, enough samples and failure counts.
The engineering acceptance details live in the learning candidate's
`docs/BUILDERWARS_GAME_LEARNING.md`; no measured improvement is claimed here.

## Privacy and cleanup

Use a throwaway display name and non-sensitive strategy. Profile exports and
ordinary replay files can include strategy text; inspect them before sharing.
Keys are excluded from exports. Public setup links omit keys, prompts and harness
addresses. Treat anything you share as public, including comments in a replay.

For a live spectator test, read the WebRTC notice first: peer connections expose
IP addresses to participants. Replays do not require a live peer connection.
Do not broadcast or post to social platforms just to complete this checklist.

After exporting anything you want to keep, use **Forget saved matches & turn
saving off**. Clear practice memory separately if the test version offers it,
forget connection keys, stop any local bridge you started, and close test tabs.
Remove test downloads you no longer want; the app cannot remove copies you shared.

## Report one issue or observation

Reply through the channel that supplied your test invitation. Include:

- Test URL/version, device, OS and browser.
- Check number, steps, expected result and actual result.
- Whether retrying reproduced it; attach a redacted screenshot or non-sensitive
  replay if useful. No keys, private prompts or personal account details.
- Could you start, finish, replay and rematch without help? What would make you
  voluntarily play another game?

## Internal collection note

Target five consenting people outside the studio for the first usability pass;
this is a recruitment target, not a count of actual testers. Record outcomes and
time-to-first-move only from their observations, with permission. Keep automated
browser checks separate from human feedback. Until those observations exist,
activation, replay appeal and sharing intent remain unmeasured. This guide does
not recruit, send invitations, add analytics or authorize paid model tests.
