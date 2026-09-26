import test, { type TestContext } from 'node:test';
import assert from 'node:assert/strict';
import { ModelDevelopment, developmentTotals } from '../src/model-development';
import { connectedVersionConfig } from '../src/model-version-transport';
import { createVersion, type VersionConfig } from '../src/frontier-version';
import { PracticeMemory, analyzePractice } from '../src/learning';
import { RULES, replay, sha256, type Rules } from '../src/runtime';
import type { Agent } from '../src/models';

const agent = (): Agent => ({ kind: 'harness', name: 'Test contender', model: 'test/requested', effort: 'high',
  strategy: 'Frozen strategy.', key: 'secret-credential-never-export', endpoint: 'https://private-endpoint.example/move' });
const limits = () => ({ nodes: 100000, milliseconds: 30000, maxTokens: 256, maxCalls: 24 });
const json = (value: unknown) => new Response(JSON.stringify(value), { status: 200 });
type Body = { game: Rules; legalMoves: string[]; turn: number; moves: string[]; strategy: string; practiceMemory?: string; model: string; effort: string; maxTokens: number };
function harness(t: TestContext, answer: (body: Body, init: RequestInit) => unknown | Promise<unknown> = body => ({ move: body.legalMoves[0], model: 'test/resolved', outputTokens: 3 })) {
  const requests: { url: string; body: Body; init: RequestInit }[] = [];
  t.mock.method(globalThis, 'fetch', async (url: RequestInfo | URL, init: RequestInit = {}) => {
    const body = JSON.parse(String(init.body)) as Body;
    requests.push({ url: String(url), body, init });
    return json(await answer(body, init));
  });
  return requests;
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(r => { resolve = r; });
  return { promise, resolve };
}
async function baseline(d: ModelDevelopment, rules = RULES.connect4, a = agent()) {
  const v = await createVersion(connectedVersionConfig(a, rules, 'test/resolved', limits()));
  await d.importVersion(v); d.select(v.digest); return v;
}
async function assertDigest(value: { digest: string }) {
  const { digest, ...body } = value; assert.equal(digest, await sha256(JSON.stringify(body)));
}

test('probe freezes one returned identity, immutable receipt and unknown usage without connection secrets', async t => {
  const requests = harness(t), a = agent(), d = new ModelDevelopment();
  const result = await d.probe(a, RULES.connect4, [], limits());
  assert.equal(requests.length, 1); assert.equal(result.exit, 'complete'); assert.equal(d.busy, false);
  assert.equal(d.active?.config.runtime.requestedModel, 'test/requested');
  assert.equal(d.active?.config.runtime.resolvedModel, 'test/resolved');
  assert.equal(d.active?.config.runtime.evidence, 'self-reported');
  assert.equal(result.calls[0].exit, 'accepted'); assert.equal(result.candidate, d.active?.digest);
  assert.deepEqual(developmentTotals(result), { calls: 1, accepted: 1, complete: 0, capped: 0, tokens: null, outputTokens: 3, cost: null });
  assert.ok(Object.isFrozen(result)); assert.ok(Object.isFrozen(result.calls[0])); assert.ok(Object.isFrozen(d.active?.config));
  assert.throws(() => { result.calls[0].model = 'tampered'; }, TypeError);
  await assertDigest(result); await assertDigest(d.active!);
  const exported = JSON.stringify({ versions: d.versions, attempts: d.attempts });
  for (const secret of [a.key, a.endpoint]) assert.ok(!exported.includes(secret));
  const snapshot = d.attempts as unknown[]; snapshot.length = 0; assert.equal(d.attempts.length, 1);
});

test('builtin probes refuse before dispatch and unreported identities retain one failed attempt without a baseline', async t => {
  const requests = harness(t, body => ({ move: body.legalMoves[0] })), d = new ModelDevelopment();
  await assert.rejects(d.probe({ ...agent(), kind: 'bot', model: 'tactician' }, RULES.connect4, [], limits()), /Connect a model/);
  assert.equal(requests.length, 0); assert.equal(d.attempts.length, 0);
  const result = await d.probe(agent(), RULES.connect4, [], limits());
  assert.equal(requests.length, 1); assert.equal(result.exit, 'failed'); assert.equal(result.calls[0].exit, 'failed');
  assert.equal(d.active, null); assert.equal(d.versions.length, 0); assert.equal(d.attempts.length, 1);
  assert.equal(developmentTotals(result).cost, null); await assertDigest(result);
});

test('manual fork, select, rollback and import are inference-free and never silently replace the incumbent', async t => {
  const requests = harness(t), d = new ModelDevelopment(), parent = await baseline(d);
  const candidate = await d.fork('Changed strategy.', 'Explicit frozen lesson.');
  assert.equal(candidate.parent, parent.digest); assert.equal(candidate.revision, parent.revision + 1);
  assert.equal(candidate.provenance.method, 'manual'); assert.equal(d.active?.digest, parent.digest);
  assert.equal(parent.config.prompt, 'Frozen strategy.'); assert.equal(parent.config.memory.mode, 'none');
  d.select(candidate.digest); assert.equal(d.active?.digest, candidate.digest); assert.equal(d.canRollback, true);
  d.rollback(); assert.equal(d.active?.digest, parent.digest); assert.equal(d.canRollback, false);
  const other = new ModelDevelopment(); await other.importVersion(candidate);
  assert.equal(other.active, null); assert.equal(other.attempts.length, 0);
  const tampered = structuredClone(candidate); tampered.config.prompt = 'Digest forgery';
  await assert.rejects(other.importVersion(tampered), /digest mismatch/); assert.equal(other.versions.length, 1);
  assert.equal(requests.length, 0); assert.equal(d.attempts.length, 0);
});

test('incompatible implementation, connection, comparison settings and ply allowance refuse without inference', async t => {
  const requests = harness(t), d = new ModelDevelopment(), parent = await baseline(d);
  const unsupported = structuredClone(parent.config); unsupported.harness.source = '0'.repeat(64);
  const old = await createVersion(unsupported); await d.importVersion(old);
  assert.throws(() => d.select(old.digest), /source|implementation/i); assert.equal(d.active?.digest, parent.digest);
  for (const mismatch of [{ model: 'other/requested' }, { effort: 'low' }, { kind: 'openrouter' }])
    await assert.rejects(d.run('practice', { ...agent(), ...mismatch } as Agent, [], 4), /provider, model and effort/);
  const config = structuredClone(parent.config); config.limits.maxTokens++;
  const mismatched = await createVersion(config, parent); await d.importVersion(mismatched); d.select(mismatched.digest);
  await assert.rejects(d.run('compare', agent(), [], 4), /identical execution settings/);
  const tinyConfig: VersionConfig = structuredClone(parent.config); tinyConfig.limits.maxCalls = 1;
  const tiny = await createVersion(tinyConfig); await d.importVersion(tiny); d.select(tiny.digest);
  await assert.rejects(d.run('practice', agent(), [], 4), /per-game version call allowance/);
  assert.equal(requests.length, 0); assert.equal(d.attempts.length, 0);
});

test('comparison plays parent and candidate in both seats, preserves caps and never learns or promotes', async t => {
  const requests = harness(t), d = new ModelDevelopment(), parent = await baseline(d);
  const candidate = await d.fork('Candidate strategy.', 'Only frozen candidate memory.'); d.select(candidate.digest);
  const remember = t.mock.method(PracticeMemory.prototype, 'remember', () => { throw Error('Comparison must not learn'); });
  const result = await d.run('compare', agent(), [], 4);
  assert.equal(result.exit, 'complete'); assert.equal(result.candidate, null); assert.equal(result.games.length, 4);
  assert.deepEqual(result.games.map(g => [g.version, g.seat]), [[parent.digest, 0], [candidate.digest, 0], [parent.digest, 1], [candidate.digest, 1]]);
  assert.equal(requests.length, 8); assert.equal(remember.mock.callCount(), 0);
  for (const game of result.games) {
    assert.equal(game.exit, 'capped'); assert.equal(game.record.events.length, 4);
    const final = replay(game.record).state; assert.equal(final.over, false); assert.equal(final.winner, null);
    assert.match(game.record.status, /no result/);
    for (const event of game.record.events) assert.equal(event.model, event.seat === game.seat ? 'test/resolved' : 'builtin/tactician');
  }
  assert.deepEqual(requests.map(r => r.body.strategy), ['Frozen strategy.', 'Frozen strategy.', 'Candidate strategy.', 'Candidate strategy.', 'Frozen strategy.', 'Frozen strategy.', 'Candidate strategy.', 'Candidate strategy.']);
  for (const r of requests) assert.equal(r.body.practiceMemory, r.body.strategy === 'Candidate strategy.' ? 'Only frozen candidate memory.' : undefined);
  assert.equal(d.active?.digest, candidate.digest); assert.equal(d.versions.length, 2); assert.equal(developmentTotals(result).capped, 4);
  assert.equal(developmentTotals(result).complete, 0); assert.equal(developmentTotals(result).tokens, null); await assertDigest(result);
});

test('practice excludes capped games, rejects unsupported games and leaves the incumbent unchanged', async t => {
  const requests = harness(t), d = new ModelDevelopment(), parent = await baseline(d);
  const remember = t.mock.method(PracticeMemory.prototype, 'remember', () => { throw Error('Capped games cannot supply lessons'); });
  const result = await d.run('practice', agent(), [], 4);
  assert.equal(result.exit, 'complete'); assert.equal(result.candidate, null); assert.equal(result.games.length, 2);
  assert.equal(result.games.every(g => g.exit === 'capped'), true); assert.equal(remember.mock.callCount(), 0);
  assert.equal(d.active?.digest, parent.digest); assert.equal(d.versions.length, 1);
  const chess = new ModelDevelopment(); await baseline(chess, RULES.chess);
  await assert.rejects(chess.run('practice', agent(), [], 4), /connect games only/);
  assert.equal(requests.length, 4); assert.equal(chess.attempts.length, 0);
});

test('completed own supported practice games create only an unselected frozen-memory candidate', async t => {
  const requests = harness(t), d = new ModelDevelopment(), parent = await baseline(d, RULES.tictactoe);
  const actualRemember = PracticeMemory.prototype.remember;
  const remember = t.mock.method(PracticeMemory.prototype, 'remember', function (this: PracticeMemory, ...args: Parameters<PracticeMemory['remember']>) {
    return actualRemember.apply(this, args);
  });
  const result = await d.run('practice', agent(), [], 10);
  assert.equal(result.exit, 'complete'); assert.equal(result.games.length, 2); assert.equal(result.games.every(g => g.exit === 'complete'), true);
  assert.equal(remember.mock.callCount(), 2);
  for (const [index, call] of remember.mock.calls.entries()) {
    const [record, players] = call.arguments; assert.deepEqual(record, result.games[index].record);
    assert.equal(players.filter(a => a.kind === 'harness').length, 1);
    assert.equal(players[result.games[index].seat].kind, 'harness'); assert.equal(players[1 - result.games[index].seat].kind, 'bot');
    assert.doesNotThrow(() => analyzePractice(record));
  }
  assert.ok(result.games.some(g => analyzePractice(g.record).mistakes.some(m => m.seat === g.seat)));
  assert.ok(result.candidate); const candidate = d.versions.find(v => v.digest === result.candidate)!;
  assert.equal(candidate.parent, parent.digest); assert.equal(candidate.config.memory.mode, 'frozen');
  assert.match(candidate.config.memory.content, /previous completed practice games/);
  assert.equal(candidate.provenance.source, await sha256(result.id)); assert.equal(candidate.config.runtime.resolvedModel, 'test/resolved');
  assert.equal(d.active?.digest, parent.digest); assert.equal(d.versions.length, 2);
  assert.equal(requests.every(r => r.body.practiceMemory === undefined), true); await assertDigest(result);
});

test('pending operation locks selection/import/fork/second run and cancellation retains a failed-call receipt without retry', async t => {
  const entered = deferred<void>(), late = deferred<unknown>();
  const requests = harness(t, async () => { entered.resolve(); return late.promise; });
  const d = new ModelDevelopment(), parent = await baseline(d), running = d.run('practice', agent(), [], 4);
  await entered.promise; assert.equal(d.busy, true);
  assert.throws(() => d.select(parent.digest), /active operation/); assert.throws(() => d.rollback(), /active operation/);
  await assert.rejects(d.importVersion(parent), /active operation/); await assert.rejects(d.fork('changed', ''), /active operation/);
  await assert.rejects(d.probe(agent(), RULES.connect4, [], limits()), /active operation/);
  await assert.rejects(d.run('practice', agent(), [], 4), /active operation/);
  d.cancel(); const result = await running;
  assert.equal(result.exit, 'cancelled'); assert.equal(result.calls.length, 1); assert.equal(result.calls[0].exit, 'cancelled');
  assert.equal(result.games[0].exit, 'cancelled'); assert.equal(result.games[0].record.events.length, 0);
  assert.equal(developmentTotals(result).tokens, null); assert.equal(developmentTotals(result).cost, null);
  assert.equal(d.active?.digest, parent.digest); assert.equal(d.versions.length, 1); assert.equal(d.busy, false);
  const retained = JSON.stringify(result); late.resolve({ move: '0', model: 'test/resolved', outputTokens: 3 });
  await new Promise(resolve => setTimeout(resolve, 0)); assert.equal(JSON.stringify(result), retained); assert.equal(requests.length, 1);
  assert.match(result.message, /may still be billed; no retry/); await assertDigest(result);
});

test('provider failure is sanitized and immutable, leaves unknown totals and never retries or alters selection', async t => {
  const requests = harness(t, () => { throw Error(`provider exposed ${agent().key} at ${agent().endpoint}`); });
  const d = new ModelDevelopment(), parent = await baseline(d), result = await d.run('practice', agent(), [], 4);
  assert.equal(result.exit, 'failed'); assert.equal(result.calls[0].exit, 'failed'); assert.equal(result.games[0].exit, 'failed');
  assert.equal(result.games[0].record.events.length, 0); assert.equal(requests.length, 1); assert.equal(d.active?.digest, parent.digest);
  assert.equal(result.candidate, null); assert.equal(result.calls[0].model, null); assert.equal(developmentTotals(result).tokens, null);
  assert.equal(developmentTotals(result).cost, null); assert.match(result.message, /No retry/);
  const exported = JSON.stringify(result); for (const secret of [agent().key, agent().endpoint, 'provider exposed']) assert.ok(!exported.includes(secret));
  assert.ok(Object.isFrozen(result.games[0].record.events)); await assertDigest(result);
});

test('probe snapshots agent, rules and limits before asynchronous validation and freezes the exact dispatched configuration', async t => {
  const entered = deferred<void>(), late = deferred<unknown>();
  const requests = harness(t, async () => { entered.resolve(); return late.promise; });
  const d = new ModelDevelopment(), a = agent(), rules = structuredClone(RULES.connect4), cap = limits();
  const running = d.probe(a, rules, [], cap);
  // These changes occur while createVersion is hashing, before dispatch.
  a.model = 'changed/requested'; a.strategy = 'Changed mutable strategy'; a.key = 'changed-secret'; rules.name = 'Changed rules';
  cap.maxTokens = 512;
  await entered.promise;
  cap.maxTokens = 768; cap.maxCalls = 99;
  late.resolve({ move: '0', model: 'test/resolved', outputTokens: 3 });
  const result = await running;
  assert.equal(result.exit, 'complete'); assert.equal(requests.length, 1); assert.equal(requests[0].body.model, 'test/requested');
  assert.equal(requests[0].body.strategy, 'Frozen strategy.'); assert.equal(requests[0].body.game.name, RULES.connect4.name);
  assert.equal((requests[0].init.headers as Record<string, string>).Authorization, `Bearer ${agent().key}`);
  assert.equal(requests[0].body.maxTokens, 256); assert.equal(result.limits.maxTokens, 256);
  assert.equal(d.active?.config.limits.maxTokens, 256); assert.equal(d.active?.config.limits.maxCalls, 24);
});

test('operation admission rechecks the host after probe preflight and does not record a request that never began', async t => {
  const requests = harness(t); let blocked = false, admissions = 0;
  const d = new ModelDevelopment(() => {}, () => { admissions++; if (blocked) throw Error('Arena operation active'); });
  const pending = d.probe(agent(), RULES.connect4, [], limits()); blocked = true;
  await assert.rejects(pending, /Arena operation active/);
  assert.equal(admissions, 1); assert.equal(requests.length, 0); assert.equal(d.busy, false); assert.equal(d.attempts.length, 0);
  await baseline(d); await assert.rejects(d.run('practice', agent(), [], 4), /Arena operation active/);
  assert.equal(admissions, 2); assert.equal(requests.length, 0); assert.equal(d.attempts.length, 0);
});

test('racing probes admit only one request even when both pass the initial idle check', async t => {
  const entered = deferred<void>(), late = deferred<unknown>();
  const requests = harness(t, async () => { entered.resolve(); return late.promise; }), d = new ModelDevelopment();
  const first = d.probe(agent(), RULES.connect4, [], limits());
  const second = d.probe(agent(), RULES.connect4, [], limits());
  const rejected = assert.rejects(second, /active operation/);
  await entered.promise; await rejected; assert.equal(requests.length, 1);
  late.resolve({ move: '0', model: 'test/resolved', outputTokens: 3 });
  assert.equal((await first).exit, 'complete'); assert.equal(d.attempts.length, 1); assert.equal(d.versions.length, 1);
});

test('comparison retains the initial private connection snapshot across all four games', async t => {
  const a = agent(), requests = harness(t, body => {
    a.model = 'changed/model'; a.effort = 'low'; a.strategy = 'Mutable strategy'; a.key = 'changed-key'; a.endpoint = 'https://changed.example/move';
    return { move: body.legalMoves[0], model: 'test/resolved', outputTokens: 3 };
  });
  const d = new ModelDevelopment(), parent = await baseline(d), candidate = await d.fork('Candidate frozen strategy', 'Candidate frozen memory');
  d.select(candidate.digest); const result = await d.run('compare', a, [], 4);
  assert.equal(result.exit, 'complete'); assert.equal(result.games.length, 4); assert.equal(requests.length, 8);
  for (const request of requests) {
    assert.equal(request.url, agent().endpoint); assert.equal(request.body.model, 'test/requested'); assert.equal(request.body.effort, 'high');
    assert.equal((request.init.headers as Record<string, string>).Authorization, `Bearer ${agent().key}`);
    assert.equal([parent.config.prompt, candidate.config.prompt].includes(request.body.strategy), true);
  }
  const exported = JSON.stringify(result);
  for (const privateValue of [agent().key, agent().endpoint, 'changed-key', 'https://changed.example/move', 'Mutable strategy']) assert.ok(!exported.includes(privateValue));
});

test('identity drift during practice stops at the first mismatched request and cannot create learning or promote', async t => {
  const requests = harness(t, body => ({ move: body.legalMoves[0], model: 'different/resolved', outputTokens: 3 }));
  const d = new ModelDevelopment(), parent = await baseline(d), result = await d.run('practice', agent(), [], 4);
  assert.equal(requests.length, 1); assert.equal(result.exit, 'failed'); assert.equal(result.calls[0].exit, 'failed');
  assert.equal(result.games[0].record.events.length, 0); assert.equal(result.candidate, null); assert.equal(d.versions.length, 1);
  assert.equal(d.active?.digest, parent.digest); assert.equal(developmentTotals(result).accepted, 0);
  assert.equal(developmentTotals(result).tokens, null); assert.equal(developmentTotals(result).cost, null);
});
