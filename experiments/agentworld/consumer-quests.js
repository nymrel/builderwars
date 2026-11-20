/* Pure consumer quest projection over verified Agentworld replays. */
(function (root) {
  'use strict';
  const A = root.Agentworld;
  if (!A) throw new Error('Agentworld engine must be loaded before consumer quests.');

  const SCHEMA = 'builderwars.agentworld.consumer-quests.projection.v1';
  const DEFINITIONS = Object.freeze([
    Object.freeze({ id: 'find-supplies', title: 'Find the supplies' }),
    Object.freeze({ id: 'bring-help-home', title: 'Bring help home' }),
    Object.freeze({ id: 'finish-together', title: 'Finish together' }),
  ]);

  function project(text) {
    const replay = A.parse(text);
    const verified = A.verify(replay);
    const applicable = verified.config.mode === 'cooperative';
    const milestones = [null, null, null];

    if (applicable) {
      let state = A.create(verified.config);
      for (let index = 0; index < verified.actions.length; index++) {
        state = A.step(state, verified.actions[index]);
        const acceptedTurn = index + 1;
        if (milestones[0] === null && verified.actions[index].type === 'collect')
          milestones[0] = acceptedTurn;
        if (milestones[1] === null && state.scores.amber >= 1 && state.scores.tide >= 1)
          milestones[1] = acceptedTurn;
        if (milestones[2] === null && state.status === 'complete' &&
            state.scores.amber + state.scores.tide === 16)
          milestones[2] = acceptedTurn;
      }
    }

    const quests = DEFINITIONS.map((definition, index) => ({
      ...definition,
      applicable,
      complete: applicable && milestones[index] !== null,
      completedAtTurn: applicable ? milestones[index] : null,
    }));
    const nextQuest = quests.find((quest) => quest.applicable && !quest.complete);

    return {
      schema: SCHEMA,
      config: { seed: verified.config.seed, mode: verified.config.mode },
      mode: verified.config.mode,
      turn: verified.state.turn,
      status: verified.state.status,
      crewDeliveries: {
        amber: verified.state.scores.amber,
        tide: verified.state.scores.tide,
      },
      remaining: A.remaining(verified.state),
      quests,
      nextQuest: nextQuest ? { id: nextQuest.id, title: nextQuest.title } : null,
    };
  }

  root.AgentworldQuests = Object.freeze({ SCHEMA, project });
})(globalThis);
