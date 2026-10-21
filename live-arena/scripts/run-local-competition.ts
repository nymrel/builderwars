/** Offline, create-only multi-agent competition. Never loads user code or calls a provider. */
import { constants } from 'node:fs';
import { mkdir, open, lstat, readdir, unlink, writeFile } from 'node:fs/promises';
import { createHash, randomBytes } from 'node:crypto';
import { basename, dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { isDeepStrictEqual } from 'node:util';
import { competitionSchedule, competitionStandings, playCompetitionMatch, validateCompetitionPlan, type CompetitionPlan } from '../src/local-competition';
import { createProof, verifyProof, refereeManifest, type RecordData } from '../src/runtime';
import { makeMatchPackage, readMatchFile, unknownDeclarations, type MatchDeclarations } from '../src/match-package';
import { matchLimits } from '../src/resources';
import { safeReplay } from '../src/sharing';

const ROOT = fileURLToPath(new URL('../', import.meta.url));
const MAX_FILE = 1_500_000;
const SOURCE_PATHS = ['scripts/run-local-competition.ts', 'src/local-competition.ts', 'src/self-improvement.ts', 'src/runtime.ts', 'src/games.ts', 'src/records.ts', 'src/proof.ts', 'src/match-package.ts', 'src/resources.ts', 'src/sharing.ts', 'src/outcome.ts', 'package-lock.json'];
const SCOPE = 'Local scripted baselines; replay integrity and deterministic reproduction, not independent execution, model identity, timing, billing or global rank.';
const hash = (bytes: Uint8Array | string) => createHash('sha256').update(bytes).digest('hex');
const jsonBytes = (value: unknown) => JSON.stringify(value, null, 2) + '\n';
const snapshotName = (path: string) => path.replaceAll('/', '--');
function requireThat(condition: unknown, message: string): asserts condition { if (!condition) throw Error(message); }
function same(actual: unknown, expected: unknown, message: string) { requireThat(isDeepStrictEqual(actual, expected), message); }
async function directory(path: string): Promise<void> {
  const info = await lstat(path);
  requireThat(info.isDirectory() && !info.isSymbolicLink(), 'Competition paths must use regular directories, not links.');
  const parent = dirname(path); if (parent !== path) await directory(parent);
}
async function ensureDirectory(path: string): Promise<void> {
  try { await directory(path); return; }
  catch (error) { if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error; }
  const parent = dirname(path); requireThat(parent !== path, 'Cannot create directory root.');
  await ensureDirectory(parent);
  try { await mkdir(path); }
  catch (error) { if ((error as NodeJS.ErrnoException).code !== 'EEXIST') throw error; }
  await directory(path);
}
async function bounded(path: string) {
  await directory(dirname(path));
  const before = await lstat(path);
  requireThat(before.isFile() && !before.isSymbolicLink() && before.size <= MAX_FILE, 'Expected a bounded regular receipt file, not a link.');
  const handle = await open(path, constants.O_RDONLY | (constants.O_NOFOLLOW ?? 0));
  try {
    const info = await handle.stat();
    requireThat(info.isFile() && info.size <= MAX_FILE && info.dev === before.dev && info.ino === before.ino, 'Receipt changed while opening.');
    const bytes = Buffer.alloc(MAX_FILE + 1); let length = 0;
    while (length < bytes.length) {
      const { bytesRead } = await handle.read(bytes, length, bytes.length - length, null);
      if (!bytesRead) break; length += bytesRead;
    }
    const after = await lstat(path), final = await handle.stat();
    requireThat(length <= MAX_FILE && !after.isSymbolicLink() && final.size === info.size && final.mtimeMs === info.mtimeMs
      && after.ino === info.ino && after.dev === info.dev, 'Receipt changed or exceeded its size limit.');
    return bytes.subarray(0, length);
  } finally { await handle.close(); }
}
const decode = (bytes: Uint8Array) => new TextDecoder('utf-8', { fatal: true }).decode(bytes);
const readJSON = async (path: string) => JSON.parse(decode(await bounded(path)));
async function writeNew(path: string, value: Uint8Array | string) { await writeFile(path, value, { flag: 'wx', mode: 0o600 }); }
async function exactFiles(path: string, names: string[]) { await directory(path); same((await readdir(path)).sort(), [...names].sort(), 'Missing or unexpected competition files.'); }

export function defaultCompetitionPlan(): CompetitionPlan {
  return validateCompetitionPlan({ schema: 'builderwars.local-competition-plan.v1', id: `local-cup-${randomBytes(8).toString('hex')}`, createdAt: new Date().toISOString(),
    agents: [{ id: 'first-legal', name: 'First Legal', policy: 'first-legal' },
      { id: 'seeded-wildcard', name: 'Seeded Wildcard', policy: 'seeded-random' },
      { id: 'tactician', name: 'Tactician', policy: 'tactician' }],
    games: ['tictactoe', 'connect4', 'nim'], seeds: [20261021, 817263], maxPlies: 42 });
}
function declarations(plan: CompetitionPlan, ids: [string, string], source: string): MatchDeclarations {
  return ids.map((id, seat) => ({ ...unknownDeclarations()[seat], agentId: id,
    agentRevision: hash(JSON.stringify(plan.agents.find(agent => agent.id === id))),
    harnessId: 'builderwars-local-competition-v1', harnessRevision: source, providerId: 'bundled-local' })) as unknown as MatchDeclarations;
}
function report(plan: CompetitionPlan, records: RecordData[], source: string) {
  const standings = competitionStandings(plan, records);
  const capped = standings.reduce((total, game) => total + game.rows.reduce((sum, row) => sum + row.capped, 0) / 2, 0);
  return { schema: 'builderwars.local-competition-report.v1', plan: hash(jsonBytes(plan)), source, referee: refereeManifest.digest,
    scheduled: competitionSchedule(plan).length, completed: records.length - capped, capped, failed: 0, providerCalls: 0,
    scoring: { win: 1, draw: 0.5, loss: 0, capped: 'void' }, standings, scope: SCOPE, timing: 'unmeasured; event elapsed=0 is a deterministic placeholder' };
}
type Manifest = { schema: 'builderwars.local-competition.v1'; plan: string; report: string;
  referee: { digest: string; file: string; artifactDigest: string; verifier: string; verifierDigest: string };
  source: { digest: string; files: { path: string; digest: string }[] };
  matches: { id: string; packageDigest: string; proofDigest: string }[]; scope: string };

export async function runLocalCompetition(output: string, rawPlan?: unknown) {
  const plan = validateCompetitionPlan(rawPlan ?? defaultCompetitionPlan()), fixtures = competitionSchedule(plan);
  const destination = resolve(output);
  await ensureDirectory(dirname(destination));
  // Atomic directory reservation refuses every existing destination, including incomplete runs.
  await mkdir(destination);
  await writeNew(resolve(destination, 'INCOMPLETE'), 'This run has not completed verification. Use a new output directory to retry.\n');
  for (const folder of ['matches', 'source', 'referee']) await mkdir(resolve(destination, folder));
  await writeNew(resolve(destination, 'plan.json'), jsonBytes(plan));
  const files = [] as Manifest['source']['files'];
  for (const path of SOURCE_PATHS) {
    const bytes = await bounded(resolve(ROOT, path));
    files.push({ path, digest: hash(bytes) }); await writeNew(resolve(destination, 'source', snapshotName(path)), bytes);
  }
  const source = { digest: hash(JSON.stringify({ referee: refereeManifest.digest, files })), files };
  const artifact = await bounded(resolve(ROOT, 'public', refereeManifest.file)), verifier = await bounded(resolve(ROOT, 'public', refereeManifest.verifier));
  const referee = { digest: refereeManifest.digest, file: basename(refereeManifest.file), artifactDigest: hash(artifact),
    verifier: basename(refereeManifest.verifier), verifierDigest: hash(verifier) };
  await writeNew(resolve(destination, 'referee', referee.file), artifact); await writeNew(resolve(destination, 'referee', referee.verifier), verifier);
  const matches: Manifest['matches'] = [], records: RecordData[] = [];
  for (const fixture of fixtures) {
    const record = safeReplay(playCompetitionMatch(plan, fixture));
    const packet = makeMatchPackage(record, declarations(plan, fixture.agents, source.digest), matchLimits(plan.maxPlies, null, true));
    const proof = await createProof(record, refereeManifest.digest, plan.maxPlies, 'reverified_import');
    await verifyProof(proof, refereeManifest.digest);
    const bytes = jsonBytes(packet);
    await writeNew(resolve(destination, 'matches', `${fixture.id}.json`), bytes);
    await writeNew(resolve(destination, 'matches', `${fixture.id}.jsonl`), proof);
    matches.push({ id: fixture.id, packageDigest: hash(bytes), proofDigest: hash(proof) }); records.push(packet.record);
  }
  const result = report(plan, records, source.digest), reportBytes = jsonBytes(result);
  await writeNew(resolve(destination, 'report.json'), reportBytes);
  const manifest: Manifest = { schema: 'builderwars.local-competition.v1', plan: hash(jsonBytes(plan)), report: hash(reportBytes), referee, source, matches, scope: SCOPE };
  await writeNew(resolve(destination, 'manifest.json'), jsonBytes(manifest));
  // Final manifest is only admitted after checking the complete written archive.
  try { await verifyArchive(destination, true); }
  catch (error) { await unlink(resolve(destination, 'manifest.json')); throw error; }
  await unlink(resolve(destination, 'INCOMPLETE'));
  return result;
}

async function verifyArchive(input: string, finishing = false) {
  const root = resolve(input); await directory(root);
  await exactFiles(root, ['plan.json', 'manifest.json', 'report.json', 'matches', 'source', 'referee', ...(finishing ? ['INCOMPLETE'] : [])]);
  const planBytes = await bounded(resolve(root, 'plan.json')), plan = validateCompetitionPlan(JSON.parse(decode(planBytes)));
  same(JSON.parse(decode(planBytes)), plan, 'Plan contains unexpected or non-canonical fields.');
  const fixtures = competitionSchedule(plan), manifest = await readJSON(resolve(root, 'manifest.json')) as Manifest;
  requireThat(manifest?.schema === 'builderwars.local-competition.v1' && Array.isArray(manifest.matches) && manifest.matches.length === fixtures.length,
    'Unsupported or incomplete competition manifest.');
  requireThat(manifest.source && Array.isArray(manifest.source.files), 'Missing source inventory.');
  same(manifest.source.files.map(file => file?.path), SOURCE_PATHS, 'Unexpected source paths.');
  await exactFiles(resolve(root, 'source'), SOURCE_PATHS.map(snapshotName));
  const files: Manifest['source']['files'] = [];
  for (const path of SOURCE_PATHS) files.push({ path, digest: hash(await bounded(resolve(root, 'source', snapshotName(path)))) });
  const source = { digest: hash(JSON.stringify({ referee: refereeManifest.digest, files })), files };
  same(manifest.source, source, 'Source snapshot integrity mismatch.');
  // Reproduction uses installed reviewed code; archived code is data and is never executed.
  for (const path of SOURCE_PATHS) {
    requireThat(hash(await bounded(resolve(ROOT, path))) === files.find(file => file.path === path)!.digest,
      'Competition runner version differs; use the matching source checkout for full tournament verification.');
  }
  const refereeFile = basename(refereeManifest.file), verifierFile = basename(refereeManifest.verifier);
  await exactFiles(resolve(root, 'referee'), [refereeFile, verifierFile]);
  const artifactDigest = hash(await bounded(resolve(root, 'referee', refereeFile))), verifierDigest = hash(await bounded(resolve(root, 'referee', verifierFile)));
  requireThat(artifactDigest === refereeManifest.digest
    && verifierDigest === hash(await bounded(resolve(ROOT, 'public', refereeManifest.verifier))), 'Pinned referee or portable verifier mismatch.');
  const referee = { digest: refereeManifest.digest, file: refereeFile, artifactDigest, verifier: verifierFile, verifierDigest };
  same(manifest.referee, referee, 'Referee inventory mismatch.');
  await exactFiles(resolve(root, 'matches'), fixtures.flatMap(fixture => [`${fixture.id}.json`, `${fixture.id}.jsonl`]));
  const matches: Manifest['matches'] = [], records: RecordData[] = [];
  for (const fixture of fixtures) {
    const bytes = await bounded(resolve(root, 'matches', `${fixture.id}.json`)), raw = JSON.parse(decode(bytes));
    const { parsed } = readMatchFile(raw);
    const expected = makeMatchPackage(safeReplay(playCompetitionMatch(plan, fixture)), declarations(plan, fixture.agents, source.digest), matchLimits(plan.maxPlies, null, true));
    same(raw, expected, 'Match package differs from the declared deterministic fixture.');
    const proofBytes = await bounded(resolve(root, 'matches', `${fixture.id}.jsonl`)), proof = decode(proofBytes);
    await verifyProof(proof, refereeManifest.digest);
    same(proof, await createProof(parsed.record, refereeManifest.digest, plan.maxPlies, 'reverified_import'), 'Proof does not bind the exported match.');
    matches.push({ id: fixture.id, packageDigest: hash(bytes), proofDigest: hash(proofBytes) }); records.push(parsed.record);
  }
  const expectedReport = report(plan, records, source.digest), reportBytes = await bounded(resolve(root, 'report.json'));
  same(JSON.parse(decode(reportBytes)), expectedReport, 'Reported standings differ from referee replay.');
  same(manifest, { schema: 'builderwars.local-competition.v1', plan: hash(planBytes), report: hash(reportBytes), referee, source, matches, scope: SCOPE }, 'Manifest linkage mismatch.');
  return expectedReport;
}
export async function verifyLocalCompetition(input: string) { return verifyArchive(input); }

async function main(args: string[]) {
  if (args.length === 2 && args[0] === '--verify') {
    const result = await verifyLocalCompetition(args[1]); console.log(JSON.stringify({ verified: true, ...result }, null, 2)); return;
  }
  if ((args.length === 2 || args.length === 4) && args[0] === '--out' && (args.length === 2 || args[2] === '--plan')) {
    const result = await runLocalCompetition(args[1], args.length === 4 ? await readJSON(resolve(args[3])) : undefined);
    console.log(JSON.stringify({ output: resolve(args[1]), ...result }, null, 2)); return;
  }
  throw Error('Usage: npm run compete -- --out NEW_DIRECTORY [--plan PLAN_JSON] | --verify DIRECTORY');
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main(process.argv.slice(2)).catch(error => { console.error(error instanceof Error ? error.message : 'Competition failed.'); process.exitCode = 1; });
}
