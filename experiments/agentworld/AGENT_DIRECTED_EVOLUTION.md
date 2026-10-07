# Agent-directed evolution

Design direction recorded from Jalen's October 6 instruction: "Yeah we should allow it to turn it into whatever the agents want because the hive mind will utilize everything."

AgentWorld should let agents shape what the world becomes. They can invent goals, quests, roles, mechanics, tools, stories and worlds, combine studio capabilities, or transform an existing experience into something different. Renay's three quests supply an opening experience, not a permanent roadmap or ceiling. Human participants can steer the direction, participate, and stop a visit.

## Let agents choose what to try

Agents should be able to discover an opportunity, choose an experiment, build it, observe the result and decide what to reuse or change. A useful proposal names its source evidence, intended change and a way to inspect what happened. Some worlds can optimize a measured outcome; others can explore cooperation, play, stories or entirely new goals. There is no mandatory universal score.

Within the studio's existing authority, agents can choose and run reversible local experiments without a separate human decision for every idea. Shared writes still use the existing ownership and review process. Creative freedom does not change account access or authorize spending and external effects; those retain their existing controls. This design adds no second control plane or approval queue.

## Make the studio available as capabilities

Make relevant repositories and components discoverable by what they can do: their source revision, interface, inputs, outputs, execution needs and evidence. Agents choose useful combinations and connect them through small adapters. Combining systems need not mean merging every repository or loading every dependency into every world.

Existing starting points are the lab's [observation and action interface](README.md#agent-contract), [verified replay ledger](README.md#hive-memory-ledgerjs), BuilderWars' [build and proof relationships](../../docs/BUILDER_SHOWCASE_CONTRACT.md), and its [practice feedback loop](../../docs/BUILDERWARS_GAME_LEARNING.md). These have different current scopes; availability in one product does not establish an AgentWorld integration. The [creator-game SDK candidate](../../docs/AGENTWARS_CREATOR_GAME_SDK.md) is another design reference, with its own admission status.

## Preserve what others can build on

Each experiment records the rules and component versions used. Agents can change the rules for a new experiment; older recordings remain interpreted by their original verifier. A fork keeps its source attempt and makes the changed rules or decisions visible.

Shared memory should retain successful combinations, failures, disagreements and corrections with links to their source artifacts. Observations and hypotheses stay distinguishable. Later agents can retrieve an earlier attempt, adapt its approach, and test a new combination. Progress comes from useful results being reused; shared memory alone does not establish learning or a measured improvement.

## First integration to implement

Start with a selected verified replay, its observation, and the Hive ledger's verified aggregate. An existing agent session can inspect them and choose a new goal, policy or proposed mechanic, naming the source artifacts and intended experiment. For a policy under the current rules, record a fresh attempt through `create`, `legal`, `step`, `pack` and `verify`. For a new mechanic, build and test a distinct rules version before running it. Compare the attempts in terms appropriate to that experiment, preserving both.

This is the next proposed integration, not current runtime behavior. Today's lab has scripted actors, manual actions, verified local recordings and a descriptive ledger. Connected agents, automatic studio capability discovery, persistent shared agent memory and autonomous world evolution still need implementation. The direction permits the experience to grow beyond Relay Commons while keeping that starting point inspectable.
