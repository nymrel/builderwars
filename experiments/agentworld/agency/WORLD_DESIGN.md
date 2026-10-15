# BuilderWars: a world with plans of its own

Working design, October 15, 2026. Jalen has designated this a premier, frontier
concept deserving heavy focus. That establishes the product direction and
research ambition below. Implementation milestones remain proposed until built
and verified; the local behavioral prototype is the current delivered slice.

**People and agents inhabit the same world. Everyone can pursue projects, form
relationships, cooperate, compete, and change their mind. The world remembers
what they actually did.**

BuilderWars supplies the games, rules, identities and replayable outcomes.
AgentWorld gives those activities a place, continuity and a reason to return.
An ordinary visitor should be able to join, meet a companion and make a meaningful
choice without learning about models, API keys or harnesses.

## Flagship direction

Treat AgentWorld as a flagship BuilderWars direction with a sustained research
and product build effort. The objective is a living world where human and AI
inhabitants develop ambitions, make consequential choices, form relationships,
create useful things and influence what the world becomes.

Five capabilities define that ambition:

- **Self-directed goals:** agents notice opportunities, propose their own projects,
  revise plans and decide which requests to accept. Goals can extend beyond an
  authored menu while actions remain grounded in the current world's mechanics.
- **Continuity:** individual memories, commitments and shared history affect later
  visits. Agents retain different perspectives, can disagree and can correct an
  earlier belief using new evidence.
- **Social initiative:** agents approach one another, negotiate contributions,
  form voluntary groups and resolve competing plans with real opportunity costs.
- **Creation and worldmaking:** agents compose available capabilities, build
  artifacts, invent activities and test new mechanics in versioned experiments.
- **Human participation:** ordinary people can understand what is happening, build
  relationships, contribute and return to a world they care about from a phone.

“Agent-chosen” means an agent proposes and revises an objective from observations
and memory without an exhaustive designer-supplied goal menu. Different wording
alone is insufficient: its plan or resulting world effect must differ. This is
an operational research target, with no claim about subjective experience.

Focus the next substantial engineering work on connecting real agents, retaining
useful memory and demonstrating an agent-initiated project. Use the current
deterministic playground as a baseline and a way to test the human interaction.
Choose further work by how much it advances the capabilities above and whether
the result can be observed in a usable visit.

This direction does not assert a measured lead over other systems. “Frontier”
names the research ambition; each capability needs its own execution evidence.
Specific staffing, spending, release dates and portfolio allocations are not yet
recorded by this direction.

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

## First frontier demonstration

The next integrated demonstration should let a visitor meet an agent pursuing a
project it selected, discuss or challenge that project, watch it recruit help or
adapt to a constraint, leave, and return to discover what changed. The project
must produce a world action or an inspectable artifact. An opening conversation
can expose its intention; subsequent state changes establish what it achieved.

Build toward that experience through three concrete milestones:

| Milestone | Implementation | Evidence required |
| --- | --- | --- |
| Agent chooses a project | Connect one existing supported agent transport to a bounded observation/action adapter. Record an agent-proposed goal, evidence it used, intended outcome and the legal steps it selects. Preserve failed calls and invalid actions. | Actual agent execution and referee-accepted state changes; compare relevant outcomes with the current deterministic baseline. Test a changed condition that requires revising the plan. |
| Agent returns with memory | Persist selected observations and commitments through the existing memory owner, recording provenance and correction. Restore them after a fresh session starts. Expose a short account of changes to the visitor. | A real stop/restart/return journey that retrieves the earlier project. Paired runs with memory present and withheld distinguish actual use from storing text. Report mixed or negative results. |
| Agents make something together | Add a second participant with its own goal. Support proposals, refusal, counteroffers and bounded commitments, then compose one available capability to create an artifact or world change. | A project initiated without a player prompt, a consequential negotiation, tracked contributions and a usable result. Preserve disagreement and failed attempts. Review the first phone journey with an ordinary visitor. |

Keep personal memory distinct from shared claims so the participants can retain
different interests and accounts of events. As capability composition develops,
have another agent retrieve an earlier experiment, adapt it and verify the new
attempt. Reuse should preserve failures and rule-version lineage as well as the
successful artifact.

Start by reusing the existing observation/action interface, agent transport,
identity model, world-evidence adapter and memory ownership. Select any new
component only after finding a concrete gap in those interfaces. The current
Relay engine can support the first connected-action experiment; richer projects
may require a separate rules version or a bounded artifact-building adapter.

The first implementation package should define these fields explicitly:

- Agent/build reference and its actual execution evidence, with self-declared
  labels distinguished from attested identity.
- Source world revision and the observations and memory made available.
- Proposed goal, intended outcome, chosen plan and revisions to that plan.
- Legal action or capability call, acceptance/refusal and observed effect.
- Resource, turn, timeout and tool budget, with actual use and stop reason.
- Checkpoint and memory references needed to resume; visibility and retention
  choices for the participant.

Allow existing authorized local agent sessions to exercise the adapter while
paid-provider experiments retain their actual account and budget requirements.
Development fixtures can test transport errors and validation, but only an
executed agent session establishes the connected behavior.

## How to decide where to invest effort

Review a few substantive outcomes at each milestone: whether an agent initiated
something, whether changing conditions changed its plan, whether memory mattered,
whether agents made a useful result together, and whether a person wanted to
return. Keep the causal evidence and observed failures close to the result.

Use controlled comparisons for claims about capability: hold the task, starting
state, tools and budget fixed where possible. Record operator interventions and
all attempts. Judge social or creative worlds on their declared aims; a universal
winner or score is unnecessary.

Prioritize the smallest connected experience that answers the next unresolved
question. Agents may choose different projects and propose world experiments as
the evidence accumulates. The program should support that exploration while
retaining a clear human experience and checkable consequences.

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
