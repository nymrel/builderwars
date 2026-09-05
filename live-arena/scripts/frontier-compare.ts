/** Explicit public development comparison. Never reads an evaluator vault. */
import { readFile, mkdir, open, lstat } from "node:fs/promises";
import { createHash } from "node:crypto";
import { resolve, dirname } from "node:path";
import { pathToFileURL } from "node:url";
import { sha256, RULES, type Rules } from "../src/runtime";
import { parseVersion, integer, isDigest, freeze, type Version } from "../src/frontier-version";
import { parseBundle, createBundle } from "../src/frontier-cases";
import { practice } from "../src/frontier-practice";
import { seeded, WorkBudget } from "../src/self-improvement";
import { fullgameBlock, fullgamePublicGroups, summarizeFullgames, FULLGAME_GATE, FULLGAME_PROTOCOL, type FullgameBlock, type FullgameGate } from "../src/frontier-fullgame";
import { sampleStrategicCases, strategicExposedGroups, practiceStrategic, scoreStrategicCases } from "../src/strategic-practice";
import { FrontierStore, frontierSource, localBaseline } from "./frontier-store";

export async function readBounded(path: string, bytes = 2000000): Promise<any> {
  const stat = await lstat(path);
  if (!stat.isFile() || stat.isSymbolicLink() || stat.size > bytes) throw Error("Invalid bounded comparison artifact.");
  return JSON.parse(await readFile(path, "utf8"));
}
export async function writeOnce(path: string, value: unknown) {
  const data = JSON.stringify(value, null, 2) + "\n";
  if (Buffer.byteLength(data) > 2000000) throw Error("Comparison artifact exceeds two megabytes.");
  const handle = await open(path, "wx");
  try { await handle.writeFile(data); await handle.sync(); } finally { await handle.close(); }
}
export async function fullgameSource() {
  const files: Record<string, string> = {};
  for (const name of ["../src/frontier-fullgame.ts", "./frontier-compare.ts"]) files[name] = createHash("sha256").update(await readFile(new URL(name, import.meta.url))).digest("hex");
  return sha256(JSON.stringify({ inferenceAndPractice: await frontierSource(), files, node: process.version }));
}
function timeRemaining(deadline: number) {
  const remaining = Math.floor(deadline - performance.now());
  if (remaining < 1) throw Error("Public comparison deadline exhausted; no complete result.");
  return remaining;
}
async function finishPublicComparison(root: string, parent: Version, candidate: Version,
  plan: { source: string; gate: FullgameGate; seeds: number[]; seedProvenance: string }, deadline: number, registry: FrontierStore) {
  const blocks: FullgameBlock[] = [], digests: string[] = [], { seeds, source, gate } = plan;
  for (let index = 0; index < gate.trials; index++) {
    const remaining = timeRemaining(deadline);
    const block = await fullgameBlock(parent, candidate, seeds[index], 398, undefined, Math.min(remaining, 30000));
    await registry.recordPublicGroups(await fullgamePublicGroups(parent.config.rules, block), source);
    timeRemaining(deadline);
    await writeOnce(resolve(root, `block-${String(index + 1).padStart(3, "0")}.json`), block);
    blocks.push(block); digests.push(await sha256(JSON.stringify(block)));
    if ((index + 1) % 8 === 0) console.error(`Public development: ${index + 1}/${gate.trials} seed blocks recorded.`);
  }
  if (source !== await fullgameSource()) throw Error("Executor source changed during comparison.");
  timeRemaining(deadline);
  const summary = summarizeFullgames(blocks, gate, "development");
  const result = { ...summary, source, plan: await sha256(JSON.stringify(plan)), blocks: digests,
    seedProvenance: plan.seedProvenance, completedAt: new Date().toISOString() };
  timeRemaining(deadline);
  await writeOnce(resolve(root, "result.json"), result);
  return result;
}
export async function publicComparison(storeRoot: string, campaign: string, output: string, trials = 32, seed = 713, milliseconds = 300000) {
  if (!/^[a-z][a-z0-9-]{0,63}$/.test(campaign)) throw Error("Invalid public campaign id.");
  integer(trials, 16, 64, "public development trials"); integer(seed, 0, 0xffffffff, "public seed");
  integer(milliseconds, 1, 300000, "campaign milliseconds");
  const root = resolve(output); await mkdir(dirname(root), { recursive: true });
  await mkdir(root); // Existing output, even partial, is never overwritten.
  const deadline = performance.now() + milliseconds;
  try {
    const campaignRoot = resolve(storeRoot, "campaigns", campaign), manifest = await readBounded(resolve(campaignRoot, "manifest.json"), 16000);
    if (!isDigest(manifest.incumbent) || manifest.id !== campaign) throw Error("Invalid source campaign.");
    const prior = await parseVersion(await readBounded(resolve(storeRoot, "versions", `${manifest.incumbent}.json`), 32000));
    const budget = new WorkBudget(2000000, timeRemaining(deadline));
    const original = await parseBundle(await readBounded(resolve(campaignRoot, "training.json")), prior, budget);
    if (original.partition !== "training" || original.digest !== manifest.training) throw Error("Only public training cases may be replayed.");
    const parent = await localBaseline(prior.config.rules), training = await createBundle("training", parent, original.cases, budget);
    const source = await fullgameSource(), rng = seeded(seed), seeds = Array.from({ length: trials }, () => Math.floor(rng() * 4294967296));
    const options = { passes: 8, rate: 0.2, margin: 0.1 }, gate = { ...FULLGAME_GATE, trials };
    const plan = freeze({ schema: "builderwars.fullgame-development-plan.v1", source, protocol: FULLGAME_PROTOCOL, partition: "public-development-only",
      importedPublicTraining: original.digest, originalSourceVersion: prior.digest, training: training.digest, parent: parent.digest, options, gate, seeds,
      seedProvenance: "Public deterministic PRNG stream; confidence numbers are illustrative, not admission guarantees.", maxPlies: 398, milliseconds });
    await writeOnce(resolve(root, "plan.json"), plan); await writeOnce(resolve(root, "training.json"), training);
    await writeOnce(resolve(root, "parent.json"), parent);
    timeRemaining(deadline);
    const learned = await practice(parent, training, training.digest, options, budget);
    await writeOnce(resolve(root, "candidate.json"), learned.candidate); await writeOnce(resolve(root, "practice.json"), learned.receipt);
    return await finishPublicComparison(root, parent, learned.candidate, plan, deadline, new FrontierStore(storeRoot));
  } catch (error) {
    await writeOnce(resolve(root, "failed.json"), { status: "failed", promotion: "not-authorized", error: error instanceof Error ? error.message : "Comparison failed" });
    throw error;
  }
}

export async function publicStrategicComparison(rules: Rules, output: string, trials = 32, seed = 713,
  registryRoot = "output/frontier", importReservations: string[] = [], milliseconds = 300000) {
  integer(trials, 16, 64, "public development trials"); integer(seed, 0, 0xffffffff, "public seed");
  integer(milliseconds, 1, 300000, "campaign milliseconds");
  const root = resolve(output); await mkdir(dirname(root), { recursive: true }); await mkdir(root);
  const deadline = performance.now() + milliseconds;
  try {
    const registry = new FrontierStore(registryRoot), imports = [];
    for (const path of importReservations) { timeRemaining(deadline); imports.push(await registry.importGroupReservations(path)); }
    const protectedTargets = await registry.publicPracticeExclusions(), parent = await localBaseline(rules, "strategic-value");
    const budget = new WorkBudget(2000000, timeRemaining(deadline));
    const training = await sampleStrategicCases(parent, seed, 48, "training", budget, protectedTargets, protectedTargets);
    const exposed = await strategicExposedGroups(training, budget);
    for (const group of protectedTargets) exposed.add(group);
    const development = await sampleStrategicCases(parent, (seed ^ 0x9e3779b9) >>> 0, 16, "development", budget, exposed, protectedTargets);
    timeRemaining(deadline);
    await registry.recordStrategicPublic(parent, training); await registry.recordStrategicPublic(parent, development);
    timeRemaining(deadline);
    const source = await fullgameSource(), rng = seeded((seed ^ 0xa5a5a5a5) >>> 0), seeds = Array.from({ length: trials }, () => Math.floor(rng() * 4294967296));
    const options = { passes: 16, rate: 0.2, margin: 0.05 }, gate = { ...FULLGAME_GATE, trials };
    const plan = freeze({ schema: "builderwars.strategic-development-plan.v1", source, protocol: FULLGAME_PROTOCOL, partition: "public-development-only",
      training: training.digest, development: development.digest, parent: parent.digest, options, gate, seeds, teacher: training.teacher, reservationImports: imports,
      seedProvenance: "Public deterministic PRNG stream; confidence numbers are illustrative, not admission guarantees.", maxPlies: 398, milliseconds });
    await writeOnce(resolve(root, "plan.json"), plan); await writeOnce(resolve(root, "parent.json"), parent);
    await writeOnce(resolve(root, "training.json"), training); await writeOnce(resolve(root, "development.json"), development);
    timeRemaining(deadline);
    const learned = await practiceStrategic(parent, training, training.digest, options, budget);
    await writeOnce(resolve(root, "candidate.json"), learned.candidate); await writeOnce(resolve(root, "practice.json"), learned.receipt);
    await writeOnce(resolve(root, "case-development.json"), { before: await scoreStrategicCases(parent, development, budget),
      after: await scoreStrategicCases(learned.candidate, development, budget) });
    return await finishPublicComparison(root, parent, learned.candidate, plan, deadline, registry);
  } catch (error) {
    await writeOnce(resolve(root, "failed.json"), { status: "failed", promotion: "not-authorized", error: error instanceof Error ? error.message : "Strategic comparison failed" });
    throw error;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  if (process.argv[2] === "strategic-public") {
    const [game, output, count = "32", seed = "713", registry = "output/frontier", ...imports] = process.argv.slice(3);
    if (!Object.hasOwn(RULES, game ?? "") || !output || imports.length > 2) { console.error("Use strategic-public GAME NEW_OUTPUT [TRIALS16..64] [SEED] [REGISTRY] [IMPORT_STORE...]."); process.exitCode = 1; }
    else publicStrategicComparison(RULES[game], output, Number(count), Number(seed), registry, imports).then(result => console.log(JSON.stringify(result, null, 2)))
      .catch(error => { console.error(error instanceof Error ? error.message : "Strategic comparison failed"); process.exitCode = 1; });
  } else {
  const [command, store, campaign, output, count = "32", seed = "713", ...extra] = process.argv.slice(2);
  if (command !== "public" || !store || !campaign || !output || extra.length) {
    console.error("Use public STORE CAMPAIGN NEW_OUTPUT_DIRECTORY [TRIALS16..64] [SEED]. No admission or private-data mode."); process.exitCode = 1;
  } else publicComparison(store, campaign, output, Number(count), Number(seed)).then(result => console.log(JSON.stringify(result, null, 2)))
    .catch(error => { console.error(error instanceof Error ? error.message : "Comparison failed"); process.exitCode = 1; });
  }
}
