import test from 'node:test';
import assert from 'node:assert/strict';
import '../engine.js';
import './policy.js';
import './return-visit.js';

const A = globalThis.AgentworldAgency, R = globalThis.AgentworldReturn;
function fixture() {
  const data = new Map();
  const port = { getItem: k => data.get(k) ?? null, setItem: (k, v) => data.set(k, v), removeItem: k => data.delete(k) };
  return { data, port, store: R.createStore(port) };
}
function visit(turns = 8) {
  let session = A.create({ seed: 481516, mode: 'cooperative' });
  for (let i = 0; i < turns; i++) session = A.advance(session, i === 0 ? 'rest' : null);
  return session;
}

test('reading an empty device neither creates a checkpoint nor opts into saving', () => {
  const { store, data } = fixture();
  assert.deepEqual(store.load(), { raw: null, session: null, error: null });
  assert.equal(data.size, 0);
});
test('a saved visit reconstructs exact world, plans, memory and continuation', () => {
  const { store } = fixture(), session = visit();
  const raw = store.save(session, null), loaded = store.load();
  assert.equal(loaded.raw, raw);
  assert.deepEqual(loaded.session, session);
  assert.deepEqual(A.advance(loaded.session), A.advance(session));
  assert.equal(loaded.error, null);
});
test('quota failure preserves the last acknowledged checkpoint', () => {
  const { port, store } = fixture();
  const raw = store.save(visit(), null);
  port.setItem = () => { throw Error('quota'); };
  assert.throws(() => store.save(visit(9), raw), /quota/);
  assert.equal(store.load().raw, raw);
  assert.equal(store.load().session.world.turn, 8);
});
test('changed checkpoints are neither overwritten nor removed by a stale tab', () => {
  const { port, store } = fixture(), other = R.createStore(port);
  const first = store.save(visit(), null), newer = other.save(visit(9), first);
  assert.throws(() => store.save(visit(10), first), /another tab/);
  assert.throws(() => store.forget(first), /another tab/);
  assert.equal(store.load().raw, newer);
});
test('corrupt, unsupported, duplicate-key and oversized saves are retained without restoration', () => {
  const packet = A.pack(visit());
  for (const text of ['{', JSON.stringify({ ...packet, policy: 'unknown' }),
    JSON.stringify(packet).replace('"schema":', '"schema":"duplicate","schema":'), ' '.repeat(globalThis.Agentworld.MAX_BYTES + 1)]) {
    const { data, store } = fixture();
    data.set(R.KEY, text);
    const loaded = store.load();
    assert.equal(loaded.session, null);
    assert.ok(loaded.error);
    assert.equal(data.get(R.KEY), text);
    store.forget(loaded.raw);
    assert.equal(data.size, 0);
  }
});
test('blocked storage does not become an empty acknowledged checkpoint', () => {
  const store = R.createStore(() => { throw Error('blocked'); });
  assert.equal(store.load().raw, undefined);
  assert.ok(store.load().error);
  assert.throws(() => store.save(visit(), undefined), /another tab/);
});
test('unacknowledged writes cannot be reported as saved', () => {
  const { port, store } = fixture();
  port.setItem = () => {};
  assert.throws(() => store.save(visit(), null), /could not be confirmed/);
});
test('forget removes only this experiment checkpoint and preserves unrelated keys', () => {
  const { data, store } = fixture();
  data.set('another-project', 'keep');
  const raw = store.save(visit(), null);
  store.forget(raw);
  assert.deepEqual([...data], [['another-project', 'keep']]);
});
