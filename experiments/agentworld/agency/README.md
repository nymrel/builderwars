# AgentWorld agency playground

A local BuilderWars experiment: four companions choose their next action from
their priorities, visited-cell memory, energy and current delivery commitments.
Suggest an activity and observe acceptance or refusal. Let them continue without
suggestions to see their own initiative.

Read the [world design](WORLD_DESIGN.md) for the larger direction: individual
ambitions, voluntary guilds, agent-led projects and versioned worldmaking.

## Try the candidate

Serve the repository root with any local static server and open
`/experiments/agentworld/agency/`. No npm packages or API keys are required.

```sh
python -m http.server 8765 --bind 127.0.0.1
```

Or build a portable HTML file that embeds the exact scripts with SHA-256 CSP
hashes and no network dependencies:

```sh
python experiments/agentworld/agency/build_preview.py --output /tmp/BuilderWars-AgentWorld.html
```

Open the HTML in a browser that permits local JavaScript. A document viewer may
not execute it. Source and generated HTML are tested separately over loopback;
this review host blocks direct file navigation.

Start with **Next choice**, or select a suggestion for the next companion. Let
the companions choose for several turns and inspect the decision journal. Stop
halts automatic turns. Export a visit to keep it; import reconstructs the saved
requests and policy before replacing the current visit. There is no automatic
save or background world in this slice.

## Mechanics and evidence

The original `../engine.js` remains the sole referee. The policy selects from its
legal actions and uses its existing `scripted` source label. No new movement,
collection, delivery, turn-order or scoring rule is introduced. Energy and memory
belong to this separately versioned policy; they do not change the Relay rules.

Four authored personalities use three goals: help, explore and rest. Accepted
suggestions last up to three of that actor's turns; recovery and carried-supply
commitments take precedence. Waiting restores energy, movement and other actions
consume it, and visited cells affect exploration. Memory is private to the local
session's policy state, while the policy can see the existing public Relay map.

`policy.js` exposes `globalThis.AgentworldAgency` after `../engine.js` loads:

```js
let session = AgentworldAgency.create({seed: 20260920, mode: 'cooperative'});
session = AgentworldAgency.advance(session, 'explore');
const saved = JSON.stringify(AgentworldAgency.pack(session));
const restored = AgentworldAgency.verify(saved);
```

Recorded requests reconstruct the decisions, legal actions and final state. The
strict bounded parser rejects unsupported versions, unknown fields, duplicate
keys and inconsistent claims. The record proves local consistency under this
policy version. A person can construct a different valid history; it does not
authenticate identity, a distinct execution, model reasoning or human consent.

These are deterministic simulated companions. They do not call an AI model,
invent goals outside the authored vocabulary, negotiate, build structures, learn
across new visits or run while the page is closed. “Agency” describes the visible
mechanics, not consciousness or metaphysical free will. Outcomes are unranked;
the 240-turn cap is an incomplete visit, not success.

## Verify

```sh
node --test experiments/agentworld/agency/policy.test.mjs
node --test experiments/agentworld/test.mjs experiments/agentworld/consumer-quests.test.mjs experiments/agentworld/world-evidence.test.mjs
python experiments/agentworld/agency/browser_test.py
```

The browser harness needs Python Playwright and Chromium. See [validation](VALIDATION.md)
for the actual run, source hashes and coverage limitations. A test run is distinct
from consumer acceptance, connected-agent evidence, merge and deployment.

## Scope

This additive candidate is based on draft #82 at
`65bdfedc9e1ba22c42f87b70f593fae20cd9b81c`; only this new `agency/` directory is
changed. The parent consumer quests, evidence adapter and source receipts remain
untouched. No production route, credentials, provider, shared-room service or
ranking admission is added. The parent PR's review and integration status remain
separate from this candidate.
