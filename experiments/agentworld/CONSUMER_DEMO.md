# AgentWorld consumer quests — first implementation

This experiment extends Renay's [three-quest packet](https://github.com/nymrel/builderwars/issues/11#issuecomment-6023984901) and the [maintainer assessment in BuilderWars #11](https://github.com/nymrel/builderwars/issues/11). Renay's quest and guild direction supplies the consumer brief; Renay is the proposed consumer-experience reviewer, with technical review separate. Jalen authorized implementation in the October 6 conversation. This does not alter repository access or account roles.

## The working slice

The existing Relay Commons page now shows three connected cooperative quests and a keyboard-accessible Stop control. The four scripted actors, two crews, turn order, legal actions, original replay schema and engine remain unchanged.

| Quest | Derived completion |
| --- | --- |
| Find the supplies | First accepted collection anywhere in the visit. |
| Bring help home | First reconstructed prefix with at least one delivery by each crew. |
| Finish together | Reconstructed complete status and all 16 supplies delivered. |

`consumer-quests.js` accepts bounded replay text through the existing strict parser and verifier, reconstructs accepted prefixes, and returns a pure versioned projection. No saved milestone flags, imported scores, names or achievement claims override reconstruction. Crew-comparison runs have no applicable cooperative quests. A capped attempt retains earlier milestones and leaves the final quest incomplete. A paused partial recording can resume; reopening any recording reproduces the same progress.

Quest progress is derived from the existing verified checkpoint on reload. It adds no storage record, credits, rankings, automated inference or executable skill. Stop halts watching while preserving the visit. The self-contained preview embeds the quest module under the existing hash-only script policy.

## Fixture and checks

The frozen rules are `builderwars.agentworld.relay.v0.1`. The cooperative scripted seed `20260920` reaches milestones at accepted turns **13, 34, 196**, with Amber 8 and Tide 8 deliveries. The one-time manual north alternative before turn 3 reaches the same milestone counts and final outcome; it is a separate legal recording, not evidence of improvement. Scripted seed `34` reaches the cap and cannot earn Finish together.

Run the engine/ledger and quest suites:

```sh
node --test experiments/agentworld/test.mjs experiments/agentworld/consumer-quests.test.mjs
node experiments/agentworld/consumer-fixtures.mjs PATH_TO_NEW_FIXTURE_DIRECTORY
```

Browser acceptance uses the existing harness on a real loopback origin, with a new output directory:

```sh
python experiments/agentworld/review_acceptance.py --output PATH_TO_NEW_EVIDENCE
python experiments/agentworld/review_acceptance.py --portable-preview --output PATH_TO_OTHER_NEW_EVIDENCE
```

These checks cover exact milestone boundaries, incomplete outcomes, duplicate opening, reconstruction after reload, Stop, refused imports, phone-width layout, existing import races/storage conflict safeguards, and the restrictive preview policy. They are automated checks of this local experiment; consumer enjoyment, physical devices and screen-reader use require their own review.

The October 6 candidate passed **33 Node checks**, **22 real-origin browser checks**, and **23 generated-preview browser checks**. The committed `evidence/consumer-demo-v0.1/` directory contains the four fixture recordings, their content manifest, and source-bound passing browser receipts. Browser coverage used Playwright 1.58.0 with Chromium 145.0.7632.6, at widths from 320 to 1280 pixels. Neither browser run reported a page error, external request, or script-policy violation.

## Next consumer pieces

This first slice establishes visible quests over recorded work. Companion-following, guild naming, the inspect/save/remove route preference, and the original-versus-alternative replay controls remain available next pieces of Renay's packet. They are not an exclusive roadmap: Jalen's subsequent direction lets agents choose new goals, mechanics and combinations of studio capabilities, as described in [agent-directed evolution](AGENT_DIRECTED_EVOLUTION.md). The existing saved visit stays browser-local. Hosted rooms, connected agents, transferable identity and the passive World event export require their existing owner contracts and adapters.

Renay's consumer walkthrough should assess whether the objectives are understandable, Stop is easy to find, returning makes sense, and the characters give a reason to continue. The five-person formative pilot remains proposed; no enjoyment, retention or agent-learning result is asserted.
