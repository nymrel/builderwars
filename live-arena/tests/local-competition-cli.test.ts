import test, { before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, cp, readFile, writeFile, readdir, unlink, symlink, mkdir, lstat } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { defaultCompetitionPlan, runLocalCompetition, verifyLocalCompetition } from '../scripts/run-local-competition';

let root: string, baseline: string;
const digest = (bytes: string) => createHash('sha256').update(bytes).digest('hex');
before(async () => {
  root = await mkdtemp(join(tmpdir(), 'builderwars-local-cup-')); baseline = join(root, 'baseline');
  const plan = { ...defaultCompetitionPlan(), createdAt: '2026-10-21T00:00:00.000Z' };
  await runLocalCompetition(baseline, plan);
});
after(async () => { if (root) await rm(root, { recursive: true, force: true }); });
async function archive(name: string) { const path = join(root, name); await cp(baseline, path, { recursive: true }); return path; }
async function mutate(path: string, name: string, change: (raw: any) => void) {
  const file = join(path, name), raw = JSON.parse(await readFile(file, 'utf8')); change(raw);
  const bytes = JSON.stringify(raw, null, 2) + '\n'; await writeFile(file, bytes); return bytes;
}

test('complete local cup exports and reverifies 36 mirrored matches and offline proofs', async () => {
  const firstDefault = defaultCompetitionPlan(), secondDefault = defaultCompetitionPlan();
  assert.match(firstDefault.id, /^local-cup-[a-f0-9]{16}$/); assert.ok(firstDefault.id.length <= 32);
  assert.notEqual(firstDefault.id, secondDefault.id);
  const result = await verifyLocalCompetition(baseline);
  assert.equal(result.scheduled, 36); assert.equal(result.completed, 36); assert.equal(result.capped, 0); assert.equal(result.providerCalls, 0);
  assert.deepEqual(result.standings.map(group => group.game), ['tictactoe', 'connect4', 'nim']);
  for (const group of result.standings) for (const row of group.rows) {
    assert.equal(row.played, 8); assert.equal(row.firstSeat, 4); assert.equal(row.secondSeat, 4);
  }
  const manifest = JSON.parse(await readFile(join(baseline, 'manifest.json'), 'utf8'));
  const proof = join(baseline, 'matches', `${manifest.matches[0].id}.jsonl`);
  const verified = spawnSync(process.execPath, [join(baseline, 'referee', manifest.referee.verifier), proof], { encoding: 'utf8' });
  assert.equal(verified.status, 0, verified.stderr); assert.equal(JSON.parse(verified.stdout).verified, true);
  assert.equal(JSON.parse(verified.stdout).execution_attested, false);
  assert.ok(manifest.source.files.some((file: any) => file.path === 'src/self-improvement.ts'));
  assert.equal((await readdir(baseline)).includes('INCOMPLETE'), false);
});

test('verification derives scores from replays even if a changed report is rehashed', async () => {
  const path = await archive('forged-report');
  const bytes = await mutate(path, 'report.json', raw => { raw.standings[0].rows[0].points += 1; });
  await mutate(path, 'manifest.json', raw => { raw.report = digest(bytes); });
  await assert.rejects(verifyLocalCompetition(path), /standings differ/);
});

test('verification rejects a valid sibling proof substituted and rehashed', async () => {
  const path = await archive('substituted-proof'), manifest = JSON.parse(await readFile(join(path, 'manifest.json'), 'utf8'));
  const first = manifest.matches[0], sibling = manifest.matches[1];
  const proof = await readFile(join(path, 'matches', `${sibling.id}.jsonl`), 'utf8');
  await writeFile(join(path, 'matches', `${first.id}.jsonl`), proof);
  await mutate(path, 'manifest.json', raw => { raw.matches[0].proofDigest = digest(proof); });
  await assert.rejects(verifyLocalCompetition(path), /Proof does not bind/);
});

test('verification rejects identity tampering, missing matches and source path substitution', async () => {
  const identity = await archive('identity'), manifest = JSON.parse(await readFile(join(identity, 'manifest.json'), 'utf8'));
  await mutate(identity, `matches/${manifest.matches[0].id}.json`, raw => { raw.record.agents[0].name = 'Other agent'; });
  await assert.rejects(verifyLocalCompetition(identity), /declared deterministic fixture/);
  const missing = await archive('missing'); await unlink(join(missing, 'matches', `${manifest.matches[0].id}.json`));
  await assert.rejects(verifyLocalCompetition(missing), /Missing or unexpected/);
  const traversal = await archive('source-path');
  await mutate(traversal, 'manifest.json', raw => { raw.source.files[0].path = '../../private'; });
  await assert.rejects(verifyLocalCompetition(traversal), /Unexpected source paths/);
});

test('existing or incomplete outputs are never overwritten; links and oversized receipts are refused', async () => {
  const before = await readFile(join(baseline, 'manifest.json'), 'utf8');
  await assert.rejects(runLocalCompetition(baseline), /EEXIST/);
  assert.equal(await readFile(join(baseline, 'manifest.json'), 'utf8'), before);
  const incomplete = await archive('incomplete'); await writeFile(join(incomplete, 'INCOMPLETE'), 'interrupted');
  await assert.rejects(verifyLocalCompetition(incomplete), /Missing or unexpected/);
  await assert.rejects(runLocalCompetition(incomplete), /EEXIST/);
  const linked = await archive('linked'), plan = join(linked, 'plan.json'); await unlink(plan);
  await symlink(join(baseline, 'plan.json'), plan);
  await assert.rejects(verifyLocalCompetition(linked), /regular receipt/);
  const oversized = await archive('oversized'); await writeFile(join(oversized, 'plan.json'), ' '.repeat(1_500_001));
  await assert.rejects(verifyLocalCompetition(oversized), /bounded regular/);
  const target = join(root, 'target'), link = join(root, 'parent-link'); await mkdir(target); await symlink(target, link, 'dir');
  await assert.rejects(runLocalCompetition(join(link, 'new', 'cup')), /regular directories/);
  await assert.rejects(lstat(join(target, 'new')), /ENOENT/);
});

test('capped cup exports truthful void results and CLI rejects unsupported arguments', async () => {
  const plan = { ...defaultCompetitionPlan(), id: 'capped-cup', games: ['tictactoe'], seeds: [1], maxPlies: 2 };
  const result = await runLocalCompetition(join(root, 'capped-cup'), plan);
  assert.equal(result.scheduled, 6); assert.equal(result.completed, 0); assert.equal(result.capped, 6);
  assert.ok(result.standings[0].rows.every(row => row.points === 0 && row.draws === 0));
  const cli = resolve('node_modules/tsx/dist/cli.mjs'), script = resolve('scripts/run-local-competition.ts');
  const invalid = spawnSync(process.execPath, [cli, script, '--unknown'], { encoding: 'utf8' });
  assert.equal(invalid.status, 1); assert.match(invalid.stderr, /Usage:/);
  const verified = spawnSync(process.execPath, [cli, script, '--verify', baseline], { encoding: 'utf8' });
  assert.equal(verified.status, 0, verified.stderr); assert.equal(JSON.parse(verified.stdout).verified, true);
});
