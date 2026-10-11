// Freeze replay fixtures using the existing engine; refuse to replace earlier evidence.
import './engine.js';
import './consumer-quests.js';
import { mkdirSync, writeFileSync, readFileSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';

const A = globalThis.Agentworld, Q = globalThis.AgentworldQuests;
const output = resolve(process.argv[2] || 'experiments/agentworld/evidence/consumer-demo-v0.1');
const digest = (bytes) => createHash('sha256').update(bytes).digest('hex');
const config = { seed: 20260920, mode: 'cooperative' };
function finish(config, prefix = []) {
  const actions = [...prefix];
  let state = A.run(config, actions);
  while (state.status === 'running') {
    const action = A.scripted(state);
    actions.push(action); state = A.step(state, action);
  }
  return A.pack(config, actions);
}
const original = finish(config);
const checkpoint = A.pack(config, original.actions.slice(0, 34));
const prefix = original.actions.slice(0, 3);
const north = A.legal(A.run(config, prefix), 'manual').find((action) => action.direction === 'north');
assert.ok(north);
const branch = finish(config, [...prefix, north]);
const capped = finish({ seed: 34, mode: 'cooperative' });
assert.deepEqual(Q.project(JSON.stringify(original)).quests.map((quest) => quest.completedAtTurn), [13,34,196]);
assert.deepEqual(Q.project(JSON.stringify(branch)).quests, Q.project(JSON.stringify(original)).quests);
assert.deepEqual(branch.actions.slice(0, 3), original.actions.slice(0, 3));
assert.equal(capped.finalState.status, 'capped');
mkdirSync(output); // No overwrite, reset, or recursive deletion of existing receipts.
const records = {};
for (const [name,packet] of Object.entries({ original, 'checkpoint-turn-34': checkpoint, 'alternative-north-turn-3': branch, 'capped-seed-34': capped })) {
  const text = JSON.stringify(packet)+'\n';
  A.verify(A.parse(text));
  writeFileSync(join(output,name+'.json'),text,{flag:'wx'});
  const projection = Q.project(text);
  records[name] = { sha256:digest(text), config:projection.config, status:projection.status,
    acceptedTurns:projection.turn, crewDeliveries:projection.crewDeliveries, remaining:projection.remaining,
    milestoneTurns:projection.quests.map((quest) => quest.completedAtTurn) };
}
const sources = {};
for (const name of ['engine.js','consumer-quests.js','consumer-fixtures.mjs'])
  sources[name] = digest(readFileSync(new URL(name,import.meta.url)));
const manifest = { schema:'builderwars.agentworld.consumer-fixtures.v1', rules:A.RULES,
  sourceSha256:sources, records, alternative:{ original:'original', prefixTurns:3, action:north,
    changedPath:true, improvedOutcome:false },
  boundaries:['Deterministic scripted/manual fixtures; no model or identity attestation.',
    'File digests establish content references, not execution authenticity.',
    'Quest progress describes this verified recording, not transferable capability.'] };
writeFileSync(join(output,'manifest.json'),JSON.stringify(manifest,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({output,records},null,2));
