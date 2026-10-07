import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import './engine.js';
import './ledger.js';
import './consumer-quests.js';
import { projectWorldEvidence } from './world-evidence.mjs';

const A = globalThis.Agentworld;
const HERE = path.dirname(fileURLToPath(import.meta.url));
const CLI = path.join(HERE, 'world-evidence.mjs');
const config = { seed: 20260920, mode: 'cooperative' };

function scripted(cfg = config) {
  const actions = [];
  let state = A.create(cfg);
  while (state.status === 'running') {
    const action = A.scripted(state);
    actions.push(action);
    state = A.step(state, action);
  }
  return actions;
}

function replay(cfg = config, actions = scripted(cfg)) {
  return JSON.stringify(A.pack(cfg, actions));
}

function hash(value) {
  return createHash('sha256').update(value).digest('hex');
}

test('exports verified completion, canonical replay identity, quest projection, and one-run ledger', () => {
  const text = replay();
  const evidence = projectWorldEvidence(text);
  assert.equal(evidence.schema, 'builderwars.agentworld.world-evidence.v1');
  assert.equal(evidence.rules, A.RULES);
  assert.equal(evidence.recordingSha256,
    hash(A.canonical({ config, actions: scripted() })));
  assert.deepEqual(evidence.quests.quests.map((quest) => quest.completedAtTurn), [13, 34, 196]);
  assert.equal(evidence.hive.totals.runs, 1);
  assert.equal(evidence.hive.runs[0].label, 'recording');
  assert.deepEqual(evidence.boundaries, [
    'Verified local replay contents; no actor identity or model-execution attestation.',
    'Descriptive memory input; no ranking, learning or capability claim.',
  ]);
});

test('capped replay leaves the final cooperative quest incomplete', () => {
  const cfg = { seed: 34, mode: 'cooperative' };
  const actions = scripted(cfg);
  assert.equal(actions.length, A.LIMIT);
  const evidence = projectWorldEvidence(replay(cfg, actions));
  assert.equal(evidence.quests.status, 'capped');
  assert.equal(evidence.quests.quests[2].complete, false);
  assert.equal(evidence.quests.quests[2].completedAtTurn, null);
});

test('formatting and property-order copies produce identical evidence', () => {
  const packet = A.pack(config, scripted());
  const compact = JSON.stringify(packet);
  const formatted = JSON.stringify(packet, null, 2);
  assert.deepEqual(projectWorldEvidence(compact), projectWorldEvidence(formatted));
});

test('rejects tampered claims, duplicate keys, and oversized replay text', () => {
  const packet = A.pack(config, []);
  packet.finalState.scores.amber = 7;
  assert.throws(() => projectWorldEvidence(JSON.stringify(packet)), /does not match/);
  assert.throws(() => projectWorldEvidence('{"schema":"wrong","schema":"duplicate"}'), /Duplicate JSON key/);
  assert.throws(() => projectWorldEvidence(' '.repeat(A.MAX_BYTES + 1)), /128 KiB/);
});

test('crew-race output never marks cooperative quests applicable or complete', () => {
  const cfg = { seed: 20260920, mode: 'crew-race' };
  const evidence = projectWorldEvidence(replay(cfg));
  assert.ok(evidence.quests.quests.every((quest) => !quest.applicable && !quest.complete));
  assert.equal(evidence.quests.nextQuest, null);
});

test('source bindings are exact SHA-256 hashes of the four named source files', () => {
  const evidence = projectWorldEvidence(replay(config, []));
  const expected = Object.fromEntries([
    'engine.js', 'ledger.js', 'consumer-quests.js', 'world-evidence.mjs',
  ].map((name) => [name, hash(readFileSync(path.join(HERE, name)))]));
  assert.deepEqual(evidence.sourceSha256, expected);
  assert.deepEqual(Object.keys(evidence.sourceSha256), [
    'engine.js', 'ledger.js', 'consumer-quests.js', 'world-evidence.mjs',
  ]);
});

test('CLI emits verified JSON for bounded input and refuses oversize input without JSON output', () => {
  const good = spawnSync(process.execPath, [CLI], { input: replay(config, []), encoding: 'utf8' });
  assert.equal(good.status, 0, good.stderr);
  assert.equal(JSON.parse(good.stdout).schema, 'builderwars.agentworld.world-evidence.v1');

  const tooLarge = spawnSync(process.execPath, [CLI], {
    input: ' '.repeat(A.MAX_BYTES + 1), encoding: 'utf8', maxBuffer: 1024 * 1024,
  });
  assert.equal(tooLarge.status, 1);
  assert.equal(tooLarge.stdout, '');
  assert.match(tooLarge.stderr, /128 KiB/);
});
