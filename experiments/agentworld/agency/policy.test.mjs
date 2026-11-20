import test from 'node:test';
import assert from 'node:assert/strict';
import '../engine.js';
import './policy.js';

const E = globalThis.Agentworld, A = globalThis.AgentworldAgency;
const config = { seed: 5, mode: 'cooperative' };
const clone = (value) => JSON.parse(JSON.stringify(value));
const latest = (session) => session.history.at(-1);
function until(session, turn, suggestion = () => null) {
  while (session.world.status === 'running' && session.world.turn < turn) session = A.advance(session, suggestion(session.world.turn));
  return session;
}
const baseline = until(A.create(config), E.LIMIT);

test('identical seed and suggestion log reproduce every decision and memory', () => {
  const schedule = (turn) => turn % 13 === 0 ? 'rest' : turn % 9 === 3 ? 'explore' : null;
  assert.deepEqual(until(A.create(config), 80, schedule), until(A.create(config), 80, schedule));
  assert.deepEqual(A.verify(JSON.stringify(A.pack(baseline))), baseline);
  assert.equal(A.MAX_ENERGY, 6);
  assert.deepEqual(A.PROFILES.map((profile) => profile.id), E.ORDER);
});

test('companions initiate help, exploration, and recovery without player requests', () => {
  assert.ok(baseline.requests.every((request) => request === null));
  assert.deepEqual(new Set(baseline.history.map((decision) => decision.goal)), new Set(['help', 'explore', 'rest']));
  assert.ok(baseline.world.scores.amber + baseline.world.scores.tide > 0);
  assert.ok(baseline.actors.every((actor) => actor.visited.length > 1));
  assert.notEqual(baseline.history[0].goal, baseline.history[1].goal);
});

test('same suggestion produces contrasting acceptance; declining preserves autonomous behavior', () => {
  let session = A.advance(A.create(config), 'help');
  assert.equal(latest(session).response, 'accepted');
  const withoutRequest = A.advance(session);
  session = A.advance(session, 'help');
  assert.equal(latest(session).response, 'declined');
  assert.equal(latest(session).goal, 'explore');
  assert.deepEqual(session.world, withoutRequest.world);
  assert.deepEqual(session.actors, withoutRequest.actors);
  assert.equal(session.requests[1], 'help');
  assert.equal(A.verify(JSON.stringify(A.pack(session))).history[1].response, 'declined');
  const declined = A.advance(A.create(config), 'explore');
  assert.equal(latest(declined).response, 'declined');
  assert.equal(latest(declined).goal, 'help');
  assert.equal(latest(declined).action.direction, 'east');
});

test('accepted suggestion changes a physical action and lasts three own turns, not three world ticks', () => {
  const start = A.create(config), acceptedRest = A.advance(start, 'rest');
  assert.equal(latest(acceptedRest).response, 'accepted');
  assert.equal(latest(acceptedRest).action.type, 'wait');
  assert.notDeepEqual(acceptedRest.world, A.advance(start).world);
  let session = until(start, 3);
  session = A.advance(session, 'explore');
  assert.deepEqual(session.actors[3].suggestion, { goal: 'explore', turnsLeft: 2 });
  session = until(session, 7);
  assert.equal(session.actors[3].suggestion.turnsLeft, 2);
  session = A.advance(session);
  assert.equal(latest(session).goal, 'explore');
  assert.equal(latest(session).commitment, 'suggestion');
  assert.equal(session.actors[3].suggestion.turnsLeft, 1);
  session = until(session, 12);
  assert.equal(latest(session).goal, 'explore');
  assert.equal(session.actors[3].suggestion, null);
  session = until(session, 16);
  assert.equal(latest(session).goal, 'help');
  assert.equal(latest(session).commitment, 'initiative');
});

test('delivery commitments refuse diversion, and low energy overrides delivery for recovery', () => {
  const carrying = until(A.create(config), 12);
  assert.equal(carrying.world.agents[0].carry, 1);
  const redirected = A.advance(carrying, 'explore');
  assert.equal(latest(redirected).response, 'declined');
  assert.equal(latest(redirected).commitment, 'delivery');
  assert.deepEqual(latest(redirected).action, E.scripted(carrying.world));
  const tired = until(carrying, 20);
  assert.equal(tired.actors[0].energy, 1);
  assert.equal(tired.world.agents[0].carry, 1);
  const recovered = A.advance(tired, 'help');
  assert.equal(latest(recovered).response, 'declined');
  assert.equal(latest(recovered).commitment, 'recovery');
  assert.equal(latest(recovered).action.type, 'wait');
  assert.equal(recovered.actors[0].energy, 4);
  assert.equal(recovered.world.agents[0].carry, 1);
  assert.equal(latest(until(recovered, 25)).commitment, 'delivery');
  const pending = A.advance(until(A.create(config), 16), 'help');
  const interrupted = until(pending, 21);
  assert.equal(latest(interrupted).commitment, 'recovery');
  assert.match(latest(interrupted).reason, /overrides/);
  assert.deepEqual(interrupted.actors[0].suggestion, { goal: 'help', turnsLeft: 1 });
});

test('exploration follows nearest unvisited cells and records actual visits once', () => {
  const visited = Object.fromEntries(E.create(config).agents.map((actor) => [actor.id, new Set([`${actor.x},${actor.y}`])]));
  let world = E.create(config);
  for (const decision of baseline.history) {
    const actor = world.agents.find((candidate) => candidate.id === decision.actor);
    if (decision.goal === 'explore') {
      const unknown = [];
      for (let x = 0; x < E.SIZE; x++) for (let y = 0; y < E.SIZE; y++) {
        if (!visited[actor.id].has(`${x},${y}`)) unknown.push([x, y]);
      }
      const distance = ([x, y]) => Math.abs(actor.x - x) + Math.abs(actor.y - y);
      unknown.sort((a, b) => distance(a) - distance(b) || a[0] - b[0] || a[1] - b[1]);
      const next = E.step(world, decision.action).agents.find((candidate) => candidate.id === actor.id);
      const [x, y] = unknown[0];
      assert.equal(Math.abs(next.x - x) + Math.abs(next.y - y), distance(unknown[0]) - 1);
    }
    world = E.step(world, decision.action);
    const next = world.agents.find((candidate) => candidate.id === actor.id);
    visited[actor.id].add(`${next.x},${next.y}`);
  }
  for (const actor of baseline.actors) assert.deepEqual(actor.visited, [...visited[actor.id]]);
});

test('across seeds and suggestions, actions remain legal and conserve supplies and energy bounds', () => {
  for (const seed of [1, 2, 3, 7, 19, 42, 1234567, 4294967295]) {
    let session = A.create({ ...config, seed });
    while (session.world.status === 'running') {
      const previous = session, turn = previous.world.turn;
      const request = turn % 11 === 0 ? ['help', 'explore', 'rest'][Math.floor(turn / 11) % 3] : null;
      session = A.advance(previous, request);
      const decision = latest(session);
      assert.ok(E.legal(previous.world).some((action) => E.canonical(action) === E.canonical(decision.action)));
      assert.equal(decision.action.source, 'scripted');
      assert.equal(E.remaining(session.world) + session.world.scores.amber + session.world.scores.tide, 16);
      assert.equal(decision.energyAfter, decision.action.type === 'wait' ? Math.min(6, decision.energyBefore + 3) : decision.energyBefore - 1);
      for (const actor of session.actors) {
        assert.ok(Number.isInteger(actor.energy) && actor.energy >= 0 && actor.energy <= 6);
        assert.equal(actor.visited.length, new Set(actor.visited).size);
      }
      for (const actor of session.world.agents) assert.ok(actor.x >= 0 && actor.x < 8 && actor.y >= 0 && actor.y < 8);
    }
    assert.ok(session.world.turn <= 240);
  }
});

test('the unchanged Relay referee independently replays every chosen action', () => {
  const actions = baseline.history.map((decision) => decision.action);
  const verified = E.verify(E.pack(config, actions));
  assert.deepEqual(verified.state, baseline.world);
  assert.ok(actions.every((action) => action.source === 'scripted'));
  assert.equal(baseline.world.rules, E.RULES);
});

test('checkpoint import restores pending suggestions, fatigue, memory, and identical continuation', () => {
  const pending = A.advance(until(A.create(config), 3), 'explore');
  const recovery = until(A.create(config), 21);
  for (const checkpoint of [pending, recovery]) {
    const imported = A.verify(JSON.stringify(A.pack(checkpoint)));
    assert.deepEqual(imported, checkpoint);
    const schedule = (turn) => turn % 17 === 0 ? 'help' : null;
    assert.deepEqual(until(imported, 70, schedule), until(checkpoint, 70, schedule));
  }
});

test('public operations neither mutate nor alias caller-owned state or profiles', () => {
  const session = until(A.create(config), 12), before = clone(session);
  const next = A.advance(session, 'rest'), packet = A.pack(session);
  assert.deepEqual(session, before);
  next.actors[0].visited.push('invalid');
  next.world.scores.amber = 999;
  next.history[0].action.type = 'invalid';
  packet.finalActors[0].energy = 999;
  packet.finalWorld.scores.amber = 999;
  packet.requests[0] = 'rest';
  assert.deepEqual(session, before);
  assert.throws(() => A.PROFILES[0].accepts.push('teleport'));
  assert.equal(A.create(config).actors[0].energy, 6);
});

test('invalid configs, requests, non-JSON sessions, and modified histories fail closed', () => {
  for (const value of [null, [], {}, { ...config, mode: 'crew-race' }, { ...config, seed: 0 },
    { ...config, seed: 1.5 }, { ...config, seed: '5' }, { ...config, provider: 'fake' }, { ...config, [Symbol('hidden')]: true }]) assert.throws(() => A.create(value));
  const accessor = { mode: 'cooperative', get seed() { throw new Error('Accessor must not run.'); } };
  assert.throws(() => A.create(accessor), /fields/);
  for (const request of ['', false, 0, {}, [], 'deliver', 'HELP']) assert.throws(() => A.advance(A.create(config), request));
  const valid = until(A.create(config), 12);
  const mutations = [
    (s) => { s.history[0].reason = 'invented'; }, (s) => { s.actors[0].energy++; },
    (s) => { s.actors[0].visited.push('7,7'); }, (s) => { s.world.agents[0].x++; },
    (s) => { s.history[0].action.source = 'manual'; }, (s) => { s.actors[0].hidden = true; },
    (s) => { Object.defineProperty(s.actors[0], 'hidden', { value: true }); },
    (s) => { s.actors[0][Symbol('hidden')] = true; }, (s) => { s.actors[0].energy = NaN; },
    (s) => { s.actors[0].suggestion = s; }, (s) => { delete s.requests[0]; }
  ];
  for (const mutate of mutations) {
    const invalid = clone(valid); mutate(invalid);
    assert.throws(() => A.advance(invalid)); assert.throws(() => A.pack(invalid));
  }
});

test('version, unknown fields, state tampering, and invalid replay logs are refused', () => {
  const original = A.pack(A.advance(A.create(config), 'rest'));
  const mutations = [
    (p) => { p.schema = 'other'; }, (p) => { p.policy = 'future'; }, (p) => { p.trusted = true; },
    (p) => { p.config.mode = 'crew-race'; }, (p) => { p.config.extra = true; },
    (p) => { p.finalWorld.scores.amber++; }, (p) => { p.finalWorld.extra = true; },
    (p) => { p.finalActors[0].energy--; }, (p) => { p.finalActors[0].visited.push('1,1'); },
    (p) => { p.finalActors[0].extra = true; }, (p) => { p.requests[0] = null; },
    (p) => { p.requests = ['teleport']; }, (p) => { p.requests = Array(241).fill(null); }
  ];
  for (const mutate of mutations) {
    const invalid = clone(original); mutate(invalid);
    assert.throws(() => A.verify(JSON.stringify(invalid)));
  }
  assert.throws(() => A.verify(original));
});

test('bounded strict JSON rejects duplicates and escaped duplicates without escaping ambiguities', () => {
  const text = JSON.stringify(A.pack(A.advance(A.create(config), 'help')));
  assert.throws(() => A.verify(text.replace('"seed":5', '"seed":5,"seed":5')));
  assert.throws(() => A.verify(text.replace('"seed":5', '"seed":5,"se\\u0065d":5')));
  assert.throws(() => A.verify(text.replace('"requests":', '"requests":[],"requests":')));
  assert.throws(() => A.verify(text.replace('"seed":5', '"seed":5.0')));
  for (const invalid of [' '.repeat(E.MAX_BYTES + 1), '['.repeat(15) + '0' + ']'.repeat(15), text + ' trailing', '{"__proto__":{"polluted":true}}']) assert.throws(() => A.verify(invalid));
  assert.deepEqual(A.verify(text.replace('"seed":5', '"se\\u0065d":5').replace('"help"', '"he\\u006cp"')), A.verify(text));
  const reordered = JSON.stringify(Object.fromEntries(Object.entries(JSON.parse(text)).reverse()), null, 2);
  assert.deepEqual(A.verify(reordered), A.verify(text));
  assert.equal({}.polluted, undefined);
});

test('the 240-turn cap survives export and import; exported packets fit the parser limit', () => {
  assert.equal(baseline.world.turn, 240);
  assert.equal(baseline.world.status, 'capped');
  const text = JSON.stringify(A.pack(baseline), null, 2);
  assert.ok(new TextEncoder().encode(text).length < E.MAX_BYTES);
  const imported = A.verify(text);
  assert.throws(() => A.advance(imported));
  assert.equal(imported.requests.length, 240);
});
