import test from 'node:test';
import assert from 'node:assert/strict';
import './engine.js';
import './ledger.js';
const E = globalThis.Agentworld;
const L = globalThis.AgentworldLedger;
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

test('hive ledger aggregates verified runs and matches engine scores', () => {
  const entries = [5, 20260920].map((seed) => {
    let s = E.create({ seed, mode: 'cooperative' }); const actions = [];
    while (s.status === 'running') { const a = E.scripted(s); actions.push(a); s = E.step(s, a); }
    return { label: `seed-${seed}`, text: JSON.stringify(E.pack({ seed, mode: 'cooperative' }, actions)) };
  });
  const ledger = L.tallyRuns(entries);
  assert.equal(ledger.totals.runs, 2); assert.equal(ledger.totals.refused, 0);
  const perActor = {};
  for (const run of ledger.runs) for (const id of E.ORDER) perActor[id] = (perActor[id] || 0) + run.perActor[id].deliveries;
  for (const id of E.ORDER) assert.equal(ledger.actors[id].deliveries, perActor[id]);
  assert.equal(ledger.actors['amber-1'].deliveries + ledger.actors['amber-2'].deliveries, ledger.runs.reduce((n, r) => n + r.amber, 0));
  assert.ok(ledger.runs.every((r) => /^[0-9a-f]{8}$/.test(r.fingerprint)));
});
test('hive ledger is order-independent and refuses tampered or malformed packets with reasons', () => {
  const run = (seed) => { let s = E.create({ seed, mode: 'crew-race' }); const actions = []; while (s.status === 'running') { const a = E.scripted(s); actions.push(a); s = E.step(s, a); } return { label: `s${seed}`, text: JSON.stringify(E.pack({ seed, mode: 'crew-race' }, actions)) }; };
  const good = [run(7), run(9)];
  const tampered = { label: 'tampered', text: JSON.stringify((() => { const p = E.pack({ seed: 5, mode: 'cooperative' }, []); p.finalState.scores.amber = 3; return p; })()) };
  const malformed = { label: 'malformed', text: '{"seed":1,"seed":2}' };
  const a = L.tallyRuns([...good, tampered, malformed]);
  const b = L.tallyRuns([malformed, tampered, ...good]);
  assert.equal(a.totals.runs, 2); assert.equal(a.totals.refused, 2);
  assert.equal(JSON.stringify(a), JSON.stringify(b));
  assert.equal(a.refused.filter((r) => r.label === 'tampered').length, 1);
  assert.ok(a.refused.every((r) => r.reason && r.reason.length > 0));
  assert.deepEqual(a.modes['crew-race'], { runs: 2, complete: a.modes['crew-race'].complete, capped: 0, delivered: a.modes['crew-race'].delivered });
});
test('hive ledger keeps manual source labels visible and bounds input fail-closed', () => {
  const s = E.create({ seed: 5, mode: 'cooperative' });
  const mixed = E.pack({ seed: 5, mode: 'cooperative' }, [{ ...E.scripted(s), source: 'manual' }]);
  const ledger = L.tallyRuns([{ label: 'mixed', text: JSON.stringify(mixed) }]);
  assert.equal(ledger.totals.sources.manual, 1); assert.equal(ledger.totals.sources.scripted, 0);
  assert.throws(() => L.tallyRuns(Array.from({ length: 65 }, (_, i) => ({ label: `r${i}`, text: JSON.stringify(E.pack({ seed: i + 1, mode: 'cooperative' }, [])) }))));
  assert.equal(L.tallyRuns([]).totals.runs, 0);
});

test('hive ledger counts full canonical replay content once under renamed and reformatted files', () => {
  const packet = E.pack(cfg, play().actions);
  const reordered = { finalState: packet.finalState, actions: packet.actions.map((a) => Object.fromEntries(Object.entries(a).reverse())), config: { mode: cfg.mode, seed: cfg.seed }, schema: packet.schema };
  const entries = [
    { label: 'z-copy.json', text: JSON.stringify(packet) },
    { label: 'a-first.json', text: JSON.stringify(reordered, null, 2) },
    { label: 'm-copy.json', text: JSON.stringify(packet) }
  ];
  const result = L.tallyRuns(entries);
  assert.equal(result.totals.runs, 1);
  assert.equal(result.totals.refused, 2);
  assert.equal(result.totals.actions, packet.actions.length);
  assert.equal(result.totals.delivered, packet.finalState.scores.amber + packet.finalState.scores.tide);
  assert.equal(result.runs[0].label, 'a-first.json');
  assert.deepEqual(result.refused.map((r) => r.label), ['m-copy.json', 'z-copy.json']);
  assert.ok(result.refused.every((r) => r.reason.includes('Duplicate verified replay') && r.reason.includes('a-first.json')));
  for (const order of [entries.toReversed(), [entries[1], entries[0], entries[2]]]) {
    assert.equal(JSON.stringify(result), JSON.stringify(L.tallyRuns(order)));
  }
});

test('hive ledger preserves real fingerprint collisions and serializes ties independently of input order', () => {
  const config = { seed: 1, mode: 'cooperative' };
  const packets = [0xDACC00, 0x202500].map((mask) => E.pack(config, Array.from({ length: 24 }, (_, turn) => ({
    turn, actor: E.ORDER[turn % E.ORDER.length], source: ((mask >>> turn) & 1) ? 'manual' : 'scripted', type: 'wait'
  }))));
  const content = packets.map(({ config, actions }) => ({ config, actions }));
  assert.notEqual(E.canonical(content[0]), E.canonical(content[1]));
  assert.deepEqual(content.map((p) => L.fingerprint(p)), ['f94daf04', 'f94daf04']);
  const entries = packets.map((p) => ({ label: 'collision.json', text: JSON.stringify(p) }));
  const result = L.tallyRuns(entries);
  assert.equal(result.totals.runs, 2);
  assert.equal(result.totals.refused, 0);
  assert.equal(result.totals.actions, 48);
  assert.deepEqual(result.totals.sources, { scripted: 35, manual: 13 });
  assert.equal(JSON.stringify(result), JSON.stringify(L.tallyRuns(entries.toReversed())));
  const withDuplicate = [...entries, { label: 'renamed.json', text: JSON.stringify(packets[0], null, 2) }];
  const deduped = L.tallyRuns(withDuplicate);
  assert.equal(deduped.totals.runs, 2);
  assert.equal(deduped.totals.refused, 1);
  assert.equal(JSON.stringify(deduped), JSON.stringify(L.tallyRuns(withDuplicate.toReversed())));
});

test('hive ledger serializes refusals, equal labels, and mode summaries in a stable full result', () => {
  const entries = [
    { label: 'same', text: '{broken' }, { label: 'same', text: '{"seed":1,"seed":2}' },
    { label: 'same', error: 'Replay file could not be read.' },
    { label: 'same', text: JSON.stringify(E.pack({ seed: 5, mode: 'crew-race' }, [])) },
    { label: 'same', text: JSON.stringify(E.pack({ seed: 5, mode: 'cooperative' }, [])) },
    { label: 'same', text: JSON.stringify(E.pack({ seed: 5, mode: 'cooperative' }, [])) }
  ];
  const serialized = JSON.stringify(L.tallyRuns(entries));
  for (const order of [entries.toReversed(), [entries[3], entries[1], entries[5], entries[0], entries[4], entries[2]]]) {
    assert.equal(serialized, JSON.stringify(L.tallyRuns(order)));
  }
});

test('hive ledger bounds entries and refusal text without dropping valid imports or any refusal', () => {
  assert.throws(() => L.tallyRuns(null));
  const good = { label: 'good', text: JSON.stringify(E.pack(cfg, [])) };
  const entries = [null, undefined, [], 'bad', { label: 7, text: good.text }, { label: 'bad-text', text: 7 },
    { label: 'ambiguous', text: good.text, error: 'unreadable' }, { label: 'missing' }, { label: 'bad-error', error: 7 },
    { label: 'x'.repeat(120), error: 'y'.repeat(200) },
    { label: 'large', text: ' '.repeat(E.MAX_BYTES + 1) }, good];
  const result = L.tallyRuns(entries);
  assert.equal(result.totals.runs, 1);
  assert.equal(result.totals.refused, entries.length - 1);
  assert.ok(result.refused.every((r) => r.label.length <= L.MAX_LABEL && r.reason.length > 0 && r.reason.length <= 160));
  const bound = L.tallyRuns(Array.from({ length: L.MAX_RUNS }, () => good));
  assert.equal(bound.totals.runs, 1);
  assert.equal(bound.totals.refused, L.MAX_RUNS - 1);
  assert.throws(() => L.tallyRuns(Array.from({ length: L.MAX_RUNS + 1 }, () => good)));
});
