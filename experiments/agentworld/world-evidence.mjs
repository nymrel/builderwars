import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import './engine.js';
import './ledger.js';
import './consumer-quests.js';

const A = globalThis.Agentworld;
const Ledger = globalThis.AgentworldLedger;
const Q = globalThis.AgentworldQuests;
const HERE = path.dirname(fileURLToPath(import.meta.url));
const BOUNDARIES = Object.freeze([
  'Verified local replay contents; no actor identity or model-execution attestation.',
  'Descriptive memory input; no ranking, learning or capability claim.',
]);

function sha256(value) {
  return createHash('sha256').update(value).digest('hex');
}

function sourceHashes() {
  return {
    'engine.js': sha256(readFileSync(path.join(HERE, 'engine.js'))),
    'ledger.js': sha256(readFileSync(path.join(HERE, 'ledger.js'))),
    'consumer-quests.js': sha256(readFileSync(path.join(HERE, 'consumer-quests.js'))),
    'world-evidence.mjs': sha256(readFileSync(fileURLToPath(import.meta.url))),
  };
}

export function projectWorldEvidence(text) {
  // Parse and verify before constructing any projection. The engine parser rejects
  // duplicate keys and enforces the replay's byte, depth, and value bounds.
  const packet = A.parse(text);
  const verified = A.verify(packet);
  const recording = { config: verified.config, actions: verified.actions };
  const canonicalReplay = A.canonical(recording);

  return {
    schema: 'builderwars.agentworld.world-evidence.v1',
    rules: A.RULES,
    recordingSha256: sha256(canonicalReplay),
    sourceSha256: sourceHashes(),
    replay: A.pack(verified.config, verified.actions),
    quests: Q.project(text),
    hive: Ledger.tallyRuns([{ label: 'recording', text }]),
    boundaries: BOUNDARIES,
  };
}

async function readBoundedStdin() {
  const chunks = [];
  let bytes = 0;
  for await (const chunk of process.stdin) {
    bytes += chunk.length;
    if (bytes > A.MAX_BYTES) throw new Error('Replay exceeds the 128 KiB input limit.');
    chunks.push(chunk);
  }
  return new TextDecoder('utf-8', { fatal: true }).decode(Buffer.concat(chunks, bytes));
}

const invokedPath = process.argv[1] && path.resolve(process.argv[1]);
if (invokedPath === fileURLToPath(import.meta.url)) {
  try {
    const text = await readBoundedStdin();
    const result = projectWorldEvidence(text);
    process.stdout.write(`${JSON.stringify(result)}\n`);
  } catch (error) {
    process.stderr.write(`${error.message || 'Replay refused.'}\n`);
    process.exitCode = 1;
  }
}
