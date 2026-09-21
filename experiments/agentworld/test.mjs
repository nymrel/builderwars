import test from 'node:test';
import assert from 'node:assert/strict';
import './engine.js';
const E = globalThis.Agentworld;
const cfg = { seed: 20260920, mode: 'cooperative' };
const clone = (x) => JSON.parse(JSON.stringify(x));
function play(c = cfg) { let state = E.create(c); const actions = []; while (state.status === 'running') { const a = E.scripted(state); actions.push(a); state = E.step(state, a); } return { state, actions }; }

test('same seed gives identical initial world and full execution', () => {
  assert.deepEqual(E.create(cfg), E.create(cfg)); assert.deepEqual(play(), play());
});
test('world generator is rotationally symmetric with sixteen supplies', () => {
  const s = E.create(cfg); assert.equal(E.remaining(s), 16);
  for (const p of s.supplies) assert.ok(s.supplies.some((q) => p.x + q.x === 7 && p.y + q.y === 7 && p.amount === q.amount));
});
test('different seeds can produce different worlds', () => assert.notDeepEqual(E.create(cfg).supplies, E.create({ ...cfg, seed: 5 }).supplies));
test('invalid configs fail closed', () => {
  for (const seed of [0, -1, 1.5, NaN, Infinity, '2', 4294967296]) assert.throws(() => E.create({ ...cfg, seed }));
  assert.throws(() => E.create({ ...cfg, provider: 'fictional' }));
  assert.throws(() => E.create({ ...cfg, mode: 'ranked' }));
});
test('stale turn, wrong actor, unknown action, direction and fields rejected', () => {
  const s = E.create(cfg), a = E.scripted(s);
  for (const invalid of [{ ...a, turn: -1 }, { ...a, turn: '0' }, { ...a, actor: 'tide-1' }, { ...a, direction: 'teleport' }, { ...a, token: 'x' }, { ...a, source: 'hosted-model' }]) assert.throws(() => E.step(s, invalid));
  assert.throws(() => E.step(s, { turn: 0, actor: E.active(s), source: 'manual', type: 'execute-code' }));
});
test('invalid action and accepted transition never mutate input', () => {
  const s = E.create(cfg), before = clone(s); E.step(s, E.scripted(s)); assert.deepEqual(s, before);
  assert.throws(() => E.step(s, { turn: 0, actor: E.active(s), source: 'manual', type: 'deliver' })); assert.deepEqual(s, before);
});
test('out-of-bounds move and collect without supply rejected', () => {
  const s = E.create(cfg), base = { turn: 0, actor: E.active(s), source: 'manual' };
  assert.throws(() => E.step(s, { ...base, type: 'move', direction: 'west' }));
  assert.throws(() => E.step(s, { ...base, type: 'collect' }));
});
test('manual actions remain declared manual in replay without identity attestation', () => {
  const s = E.create(cfg), a = { ...E.scripted(s), source: 'manual' };
  const p = E.pack(cfg, [a]); assert.equal(E.verify(p).actions[0].source, 'manual');
  assert.equal('model_attested' in p, false);
});
test('all tested runs conserve supplies and stay in bounds at every turn', () => {
  for (let seed = 1; seed <= 100; seed++) {
    let s = E.create({ ...cfg, seed });
    while (s.status === 'running') {
      s = E.step(s, E.scripted(s));
      assert.equal(E.remaining(s) + s.scores.amber + s.scores.tide, 16);
      for (const a of s.agents) { assert.ok(a.x >= 0 && a.x < 8 && a.y >= 0 && a.y < 8); assert.ok([0, 1].includes(a.carry)); }
      assert.ok(s.turn <= E.LIMIT);
    }
  }
});
test('terminal worlds reject further actions', () => {
  const p = play(); assert.ok(['complete', 'capped'].includes(p.state.status)); assert.equal(E.legal(p.state).length, 0);
  assert.throws(() => E.step(p.state, { turn: p.state.turn, actor: E.active(p.state), source: 'manual', type: 'wait' }));
});
test('wait loop hits exact hard cap', () => {
  let s = E.create(cfg); for (let i = 0; i < E.LIMIT; i++) s = E.step(s, E.legal(s)[0]);
  assert.equal(s.turn, 240); assert.equal(s.status, 'capped');
});
test('export, parse and replay reproduce exact state', () => {
  const p = play(); assert.deepEqual(E.verify(E.parse(JSON.stringify(E.pack(cfg, p.actions)))).state, p.state);
});
test('modified claimed scores and rules fail replay validation', () => {
  const p = E.pack(cfg, play().actions); p.finalState.scores.amber++; assert.throws(() => E.verify(p));
  const q = E.pack(cfg, []); q.finalState.rules = 'different'; assert.throws(() => E.verify(q));
});
test('reordered or removed actions fail replay', () => {
  const p = E.pack(cfg, play().actions); [p.actions[0], p.actions[1]] = [p.actions[1], p.actions[0]]; assert.throws(() => E.verify(p));
  const q = E.pack(cfg, play().actions); q.actions.pop(); assert.throws(() => E.verify(q));
});
test('replay version, unknown fields and oversized action list refused', () => {
  const p = E.pack(cfg, []); assert.throws(() => E.verify({ ...p, schema: 'other' }));
  assert.throws(() => E.verify({ ...p, ranked: true }));
  assert.throws(() => E.pack(cfg, Array(241).fill({})));
});
test('duplicate JSON keys, including escaped equivalents, refused', () => {
  assert.throws(() => E.parse('{"seed":1,"seed":2}'));
  assert.throws(() => E.parse('{"seed":1,"se\\u0065d":2}'));
});
test('oversized, deep, unsafe-number and malformed JSON refused', () => {
  for (const text of [' '.repeat(E.MAX_BYTES + 1), '['.repeat(15) + '0' + ']'.repeat(15), '1.5', '1e2', 'NaN', '9007199254740992', '{"a":1,}', '[1,]', '01', 'null trailing']) assert.throws(() => E.parse(text));
});
test('JSON parser supports escapes and cannot prototype-pollute', () => {
  assert.equal(E.parse('{"x":"a\\n\\\"b"}').x, 'a\n"b');
  const p = E.parse('{"__proto__":{"polluted":true}}'); assert.equal(Object.getPrototypeOf(p), null); assert.equal({}.polluted, undefined);
});
test('both modes retain identical mechanics and separate mode in manifest', () => {
  const a = play(cfg), b = play({ ...cfg, mode: 'crew-race' }); assert.deepEqual(a.actions, b.actions); assert.deepEqual(a.state.scores, b.state.scores);
  assert.notEqual(E.pack(cfg, []).config.mode, E.pack({ ...cfg, mode: 'crew-race' }, []).config.mode);
});
