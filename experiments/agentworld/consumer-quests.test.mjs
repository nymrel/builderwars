import test from 'node:test';
import assert from 'node:assert/strict';
import './engine.js';
import './consumer-quests.js';

const A = globalThis.Agentworld;
const Q = globalThis.AgentworldQuests;
const cfg = { seed: 20260920, mode: 'cooperative' };
function replay(config = cfg, actions = []) {
  return JSON.stringify(A.pack(config, actions));
}
function scripted(config = cfg) {
  const actions = [];
  let state = A.create(config);
  while (state.status === 'running') {
    const action = A.scripted(state);
    actions.push(action);
    state = A.step(state, action);
  }
  return actions;
}
function frozen(value) {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) {
    for (const child of Object.values(value)) frozen(child);
    Object.freeze(value);
  }
  return value;
}

test('seeded cooperative replay projects the three verified milestones', () => {
  const actions = scripted();
  const result = Q.project(replay(cfg, actions));
  assert.equal(result.schema, Q.SCHEMA);
  assert.deepEqual(result.config, cfg);
  assert.equal(result.mode, 'cooperative');
  assert.equal(result.status, 'complete');
  assert.deepEqual(result.quests.map((quest) => quest.completedAtTurn), [13, 34, 196]);
  assert.ok(result.quests.every((quest) => quest.applicable && quest.complete));
  assert.equal(result.crewDeliveries.amber, 8);
  assert.equal(result.crewDeliveries.tide, 8);
  assert.equal(result.remaining, 0);
  assert.equal(result.nextQuest, null);
});

test('milestones change only at the first accepted prefix that earns them', () => {
  const actions = scripted();
  const at12 = Q.project(replay(cfg, actions.slice(0, 12)));
  const at13 = Q.project(replay(cfg, actions.slice(0, 13)));
  const at33 = Q.project(replay(cfg, actions.slice(0, 33)));
  const at34 = Q.project(replay(cfg, actions.slice(0, 34)));
  const at195 = Q.project(replay(cfg, actions.slice(0, 195)));
  const at196 = Q.project(replay(cfg, actions.slice(0, 196)));
  assert.deepEqual(at12.quests.map((quest) => quest.completedAtTurn), [null, null, null]);
  assert.deepEqual(at13.quests.map((quest) => quest.completedAtTurn), [13, null, null]);
  assert.deepEqual(at33.quests.map((quest) => quest.completedAtTurn), [13, null, null]);
  assert.deepEqual(at34.quests.map((quest) => quest.completedAtTurn), [13, 34, null]);
  assert.deepEqual(at195.quests.map((quest) => quest.completedAtTurn), [13, 34, null]);
  assert.deepEqual(at196.quests.map((quest) => quest.completedAtTurn), [13, 34, 196]);
});

test('capped and partial runs retain earned quests but cannot earn the finish', () => {
  const cappedConfig = { seed: 34, mode: 'cooperative' };
  const cappedActions = scripted(cappedConfig);
  assert.equal(cappedActions.length, A.LIMIT);
  const capped = Q.project(replay(cappedConfig, cappedActions));
  assert.equal(capped.status, 'capped');
  assert.notEqual(capped.remaining, 0);
  assert.equal(capped.quests[2].complete, false);
  assert.equal(capped.quests[2].completedAtTurn, null);

  const partial = Q.project(replay(cfg, scripted().slice(0, 5)));
  assert.equal(partial.status, 'running');
  assert.equal(partial.quests[0].complete, false);
  assert.equal(partial.nextQuest.id, 'find-supplies');
});

test('crew-race never earns cooperative quest milestones', () => {
  const raceConfig = { seed: 20260920, mode: 'crew-race' };
  const result = Q.project(replay(raceConfig, scripted(raceConfig)));
  assert.equal(result.mode, 'crew-race');
  assert.ok(result.quests.every((quest) => !quest.applicable && !quest.complete));
  assert.ok(result.quests.every((quest) => quest.completedAtTurn === null));
  assert.equal(result.nextQuest, null);
});

test('manual north branch at turn three preserves the same quest projection', () => {
  const actions = scripted();
  const prefixState = A.create(cfg);
  let state = prefixState;
  for (let i = 0; i < 3; i++) state = A.step(state, actions[i]);
  const alternative = A.legal(state, 'manual').find((action) =>
    action.actor === 'tide-2' && action.type === 'move' && action.direction === 'north');
  assert.ok(alternative);
  const branchActions = [...actions.slice(0, 3), alternative];
  state = A.step(state, alternative);
  while (state.status === 'running') {
    const action = A.scripted(state);
    branchActions.push(action);
    state = A.step(state, action);
  }
  const original = Q.project(replay(cfg, actions));
  const branch = Q.project(replay(cfg, branchActions));
  assert.deepEqual(branch.quests, original.quests);
  assert.deepEqual(branch.crewDeliveries, original.crewDeliveries);
  assert.equal(branch.turn, 196);
});

test('projection is repeatable and does not mutate a frozen replay input', () => {
  const packet = frozen(A.pack(cfg, scripted().slice(0, 13)));
  const before = JSON.stringify(packet);
  const text = JSON.stringify(packet);
  assert.deepEqual(Q.project(text), Q.project(text));
  assert.equal(JSON.stringify(packet), before);
  assert.equal(text, JSON.stringify(packet));
});

test('strict engine parsing and verification reject malformed or tampered replay claims', () => {
  assert.throws(() => Q.project('{"schema":"wrong","schema":"duplicate"}'), /Duplicate JSON key/);
  assert.throws(() => Q.project(' '.repeat(A.MAX_BYTES + 1)), /128 KiB limit/);
  const extra = JSON.parse(replay());
  extra.untrustedQuestFlags = [true, true, true];
  assert.throws(() => Q.project(JSON.stringify(extra)), /Unexpected or missing fields/);
  const badScore = JSON.parse(replay());
  badScore.finalState.scores.amber = -1;
  assert.throws(() => Q.project(JSON.stringify(badScore)), /Replay does not match/);
});
