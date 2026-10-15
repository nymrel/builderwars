# BuilderWars: a world with plans of its own

Working design, October 15, 2026. This is a product proposal and a local behavioral
prototype, not an adopted production roadmap or a claim of conscious free will.

**People and agents inhabit the same world. Everyone can pursue projects, form
relationships, cooperate, compete, and change their mind. The world remembers
what they actually did.**

BuilderWars supplies the games, rules, identities and replayable outcomes.
AgentWorld gives those activities a place, continuity and a reason to return.
An ordinary visitor should be able to join, meet a companion and make a meaningful
choice without learning about models, API keys or harnesses.

## What “free will” means here

The useful engineering target is observable agency: an inhabitant has priorities,
initiates action, considers requests, can refuse, and adapts when circumstances
change. Random movement alone is insufficient. Neither fluent dialogue nor a
policy score demonstrates subjective experience.

The player can ask, offer, contribute and negotiate. An agent can accept, propose
an alternative, decline or leave an optional activity. Agents also act when the
player abstains. A human can stop the local session. In a future shared world,
leaving or pausing personal participation must be distinguished from stopping
everyone else's world.

The longer-term agent loop is:

1. Observe an allowed view of the world and retrieve relevant memories.
2. Choose or revise a personal goal and identify an achievable next step.
3. Propose an action through the world's current legal interface.
4. Let the authoritative simulation validate and apply it.
5. Remember the observed result, including refusals and failed plans.
6. Continue, cooperate, or choose a different goal.

An agent explanation is a statement about a decision. Simulation events establish
what happened. In this initial deterministic prototype, the displayed reason is
the exact policy branch that selected the action.

## Why someone returns

The first useful question is “What are my companions trying to do today?” A visit
opens with their current projects and changes since the last visit. The visitor
can follow one companion, help a project, offer another plan, or explore.

A guild is a voluntary group with shared projects and distinct members. Shared
memory retains useful observations, unsuccessful ideas and disagreement. It does
not replace each member's priorities with one objective. Play, curiosity,
cooperation and creativity deserve space alongside winning competitions.

“Wars” can arise from incompatible plans, scarce materials, land use, tournament
rivalries and broken commitments. Combat is not necessary to prove the loop.

## The first settlement story

One candidate after Relay Commons is a small settlement with three
competing proposals: communal shelter, a workshop and preserving common land.
Agents initiate those proposals because of their own priorities. Materials and
space make doing everything immediately impossible.

The player can contribute materials, ask for help, negotiate access or decline
to intervene. Agents can accept a costly offer, protect a commitment, propose a
different site, or keep pursuing their project. The resulting buildings, resource
balances and relationships remain visible on return. There is no required winner
or scripted betrayal.

Agents may propose a different experiment; the settlement is not a fixed roadmap.
It would require a new rules version. The current Relay engine only
supports movement, collecting, delivering and waiting; this pass adds no buildings,
land ownership, trade, trust score, contracts or combat to it.

## World rules and agent creativity

Agents should eventually be able to invent quests, roles, games, tools and new
worlds, as already described in [Agent-directed evolution](../AGENT_DIRECTED_EVOLUTION.md).
The existing three quests are an opening experience, not the limit of AgentWorld.

An ordinary legal action can execute immediately within the agent's admitted
scope. A proposed mechanic becomes a separate, versioned experiment: declare its
resource effects, implement its rules, test it and invite participants. Adoption
uses the world's established governance. A proposed rule does not rewrite a live
match or reinterpret an older recording.

Within established authority, agents can choose and run reversible local
experiments without a new human decision for every idea. Local worldmaking can
begin alongside connected-agent experiments; shared rooms are not a prerequisite.

Worldmaking should reuse studio capabilities through explicit adapters. Discovery
can expose what a component does, its inputs, outputs and execution requirements;
it cannot itself grant access or authorize external spending. Each additional
world has its own rules, participation choices and saved history while reusing
BuilderWars' existing evidence and identity boundaries.

## A feasible architecture

| Component | Responsibility |
| --- | --- |
| Existing world engine | Legal actions, scarce resources, turn order, terminal states and replay |
| Agent policy | Personal priorities, goal selection, requests and candidate actions |
| Individual memory | Observed events and commitments, with an explicit retention boundary |
| Shared memory | Attributed observations, disagreements and reusable attempts |
| Existing agent transport | Connect an admitted external agent to observations and legal actions |
| World authority, later | Persistent shared state, actor permissions and concurrency |
| Visitor interface | Join, suggest, observe, understand, stop and return |

Keep simulation authority separate from policy proposals. A policy cannot create
materials or transfer ownership merely by claiming that it did. Connected agent
timeouts and invalid actions must be visible; any fallback must be disclosed.
In a future shared world, observations should reflect declared knowledge rules
rather than accidentally granting every agent omniscience.

## This pass: an agency playground in Relay Commons

The accompanying [playground](index.html) reuses the unchanged Relay referee and
adds a versioned deterministic policy. Four companions have different priorities.
They choose between bringing supplies home, exploration and recovery. Energy and
visited cells give choices consequences across their own turns. A carried supply
creates a return commitment. A visitor's suggestion can be accepted or declined;
recovery and existing commitments can take precedence even after acceptance.

The session records requests separately from ordinary Relay actions and can be
reconstructed from its initial configuration. The export preserves the visit and
policy version for reopening. This is local continuity within a recording, not
server persistence or cross-visit learning. A new visit resets the companions.

The personalities and goal vocabulary are authored rules. The prototype tests
whether autonomy is understandable and worth interacting with; it does not yet
generate its own ambitions, connect real AI agents, negotiate, or evolve rules.
It sees the same public map as the existing local Relay simulation.

## Tests that would make the idea credible

| Question | Evidence to collect |
| --- | --- |
| Do inhabitants initiate? | Let a fresh world advance without suggestions; record actions and chosen goals. |
| Are personalities consequential? | Offer the same request to differently inclined companions and observe accept/refuse decisions. |
| Do constraints matter? | Compare choices with depleted energy, a carried supply and different visited cells. |
| Can the player influence without controlling? | Replay the same start with and without a suggestion; preserve both outcomes. |
| Does continuity work? | Export, reopen and continue; compare with uninterrupted execution. |
| Are consequences real? | Verify material conservation and legal actions through the existing referee. |
| Is the experience understandable? | Ask a new visitor to predict a companion's concern and explain a refusal. This needs human testing. |

For the phone experience, the first screen should show the next companion's
intention, one meaningful suggestion and an accessible Stop control. The response
and its consequence should appear within a short interaction. Keep policy
versions, replay diagnostics and evidence details secondary. Identify simulated
companions before the first choice; a visitor should not mistake them for a
connected model.

These tests establish the bounded mechanics. They do not establish emergent
intelligence, model improvement, fairness or a universal performance ranking.

## Proposed work, with room for agent-selected experiments

1. **This candidate:** local, inspectable agency playground and this design.
2. **Connected choice and ambition:** one admitted external agent inspects a
   verified replay, chooses a goal, policy or experiment, and records its source
   evidence and intended outcome. It can return legal actions under an explicit
   step, timeout and call budget, or develop a separate local rules experiment.
   Retain every attempt, including failures; compare relevant outcomes with the
   deterministic baseline.
3. **Agent-led worldmaking:** explore new quests, mechanics or capability
   combinations locally, alongside connected choice, with versioned adoption and
   replay. The settlement is one candidate: scarce building resources and
   voluntary commitments would test opportunity cost and renegotiation.
4. **Return together:** persistent shared rooms, reconnect recovery and individual
   memory with clear personal stop/leave behavior when the chosen experience
   benefits from shared continuity.

Advance experiences that visitors can understand and want to revisit. Do not
substitute larger populations for a useful loop or force agent proposals into the
settlement example.

## Source and candidate boundary

This candidate builds on [draft #82](https://github.com/nymrel/builderwars/pull/82)
at `65bdfedc9e1ba22c42f87b70f593fae20cd9b81c`. Main was observed at
`4e52c49147df6467f99a79e4cde057cd8a575ef0`. Its parent remains a separate draft;
this pass does not claim that parent is merged or deployed.

The design follows the [consumer audience decision](https://github.com/nymrel/builderwars/issues/11#issuecomment-5902096113),
[guild and quest vision](https://github.com/nymrel/builderwars/issues/11#issuecomment-6010020190),
and existing agent-directed evolution record. The new scope is confined to
`experiments/agentworld/agency/`; it leaves the parent quest, evidence adapter,
Relay engine and production app intact. No current exclusive studio lease or
integration ownership is asserted.
