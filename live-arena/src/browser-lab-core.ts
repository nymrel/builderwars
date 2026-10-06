/** Browser development evidence. No provider inference or automatic promotion. */
import { RULES, refereeManifest, sha256, createGame, replay, replayStepper, moveLabel, type RecordData } from "./runtime";
import { numericBaseline } from "./numeric-baseline";
import { createVersion, parseVersion, assertComparableSuccessor, exact, integer, type Version } from "./frontier-version";
import { seeded, WorkBudget } from "./self-improvement";
import { FULLGAME_GATE, summarizeFullgames, fullgameOpening, type FullgameBlock } from "./frontier-fullgame";
import type { CaseBundle } from "./frontier-cases";
import { scoreCases } from "./frontier-practice";
import { parseBundle } from "./frontier-cases";
import { isRuleComplete } from "./outcome";
import type { practice } from "./frontier-practice";
import source from "./lab-source-manifest";

export const LAB_SCHEMA = "builderwars.browser-lab.v1";
export const LAB_LIMITS = Object.freeze({ nodes: 250000, milliseconds: 5000, maxTokens: 512, maxCalls: 100 });
export const LAB_MAX_RUNS = 6, LAB_MAX_BYTES = 2000000;
export type LabStatus = "prepared" | "sampling" | "training" | "evaluating" | "completed" | "failed" | "cancelled" | "interrupted";
export type LabPlan = { source: string; referee: string; seed: number; seeds: number[]; passes: number; caseCount: number; trials: number; maxPlies: number; digest: string };
export type LabRun = {
  schema: typeof LAB_SCHEMA; id: string; createdAt: string; status: LabStatus; parent: Version; plan: LabPlan;
  partitions?: { training: CaseBundle; development: CaseBundle; admission: CaseBundle[] };
  candidate?: Version; practice?: Awaited<ReturnType<typeof practice>>["receipt"];
  development?: { before: Awaited<ReturnType<typeof scoreCases>>; after: Awaited<ReturnType<typeof scoreCases>> };
  blocks: FullgameBlock[]; summary?: ReturnType<typeof summarizeFullgames>; error?: string;
};
export const labSource = source;
export const ARENA_LAB_LIMITS = Object.freeze({ ...LAB_LIMITS, milliseconds: 90000 });
export async function validateLabVersion(raw: unknown): Promise<Version> { return validateLocalConfig(raw,LAB_LIMITS); }
export async function validateArenaLabVersion(raw: unknown): Promise<Version> { return validateLocalConfig(raw,ARENA_LAB_LIMITS); }
export async function arenaLabVersion(raw: unknown) {
  const parent = await validateLabVersion(raw), config = structuredClone(parent.config);
  config.limits = { ...ARENA_LAB_LIMITS };
  return createVersion(config,parent);
}
async function validateLocalConfig(raw: unknown, limits: Version["config"]["limits"]): Promise<Version> {
  const version = await parseVersion(raw), c = version.config;
  if (!["tictactoe", "connect4"].includes(c.rules.kind) || c.harness.kind !== "linear-value"
    || c.harness.source !== source.digest || c.runtime.provider !== "local" || c.prompt !== ""
    || c.memory.mode !== "none" || c.sampling.seed !== 0 || c.sampling.temperature !== null
    || JSON.stringify(c.limits) !== JSON.stringify(limits)) throw Error("Use a local numeric version from this Lab build. Other model, source and resource configurations are not executable here.");
  const baseline = await numericBaseline(c.rules, source.digest, "linear-value", { ...limits });
  const comparable = structuredClone(c); comparable.value = baseline.config.value;
  if (JSON.stringify(comparable) !== JSON.stringify(baseline.config)) throw Error("Lab runtime, tools, memory or resource configuration was changed.");
  return version;
}
export async function labBaseline(game: string) {
  if (!["tictactoe", "connect4"].includes(game)) throw Error("Choose a supported Lab game.");
  return numericBaseline(RULES[game], source.digest, "linear-value", { ...LAB_LIMITS });
}
export async function makeLabRun(parent: Version, seed: number, trials = 16): Promise<LabRun> {
  parent = await validateLabVersion(parent); integer(seed, 0, 0xffffffff, "experiment seed");
  if (![16, 32, 64].includes(trials)) throw Error("Choose 16, 32 or 64 paired blocks.");
  const rng = seeded((seed ^ 0xa5a5a5a5) >>> 0), seeds = new Set<number>();
  while (seeds.size < trials) seeds.add(Math.floor(rng() * 4294967296));
  const body = { source: source.digest, referee: refereeManifest.digest, seed, seeds: [...seeds], passes: 12,
    caseCount: 8, trials, maxPlies: parent.config.rules.kind === "tictactoe" ? 9 : 42 };
  return { schema: LAB_SCHEMA, id: crypto.randomUUID(), createdAt: new Date().toISOString(), status: "prepared", parent,
    plan: { ...body, digest: await sha256(JSON.stringify(body)) }, blocks: [] };
}
export async function validateLabPlan(run: LabRun) {
  if (run.schema !== LAB_SCHEMA || !/^[a-f0-9-]{36}$/.test(run.id) || typeof run.createdAt !== "string") throw Error("Invalid experiment identity.");
  await validateLabVersion(run.parent);
  const { digest, ...body } = run.plan;
  if (digest !== await sha256(JSON.stringify(body)) || body.source !== source.digest || body.referee !== refereeManifest.digest
    || ![16, 32, 64].includes(body.trials) || body.seeds.length !== body.trials || new Set(body.seeds).size !== body.trials
    || body.passes !== 12 || body.caseCount !== 8 || body.maxPlies !== (run.parent.config.rules.kind === "tictactoe" ? 9 : 42)) throw Error("Experiment plan was changed or is unsupported.");
  integer(body.seed, 0, 0xffffffff, "seed");
  for (const seed of body.seeds) integer(seed, 0, 0xffffffff, "trial seed");
}
export function labSummary(run: LabRun) {
  if (!run.candidate || run.blocks.length !== run.plan.trials) throw Error("Comparison is incomplete.");
  return summarizeFullgames(run.blocks, { ...FULLGAME_GATE, trials: run.plan.trials }, "development");
}
export async function validateLabImport(raw: unknown): Promise<Version> {
  // Import accepts one small immutable version, never uploaded executable code or a claimed score.
  return validateLabVersion(raw);
}
export function labReplay(run: LabRun, blockIndex: number, gameIndex: number): RecordData {
  integer(blockIndex, 0, run.blocks.length - 1, "block"); integer(gameIndex, 0, 7, "game");
  const row = run.blocks[blockIndex].games[gameIndex], version = row.version === run.parent.digest ? run.parent : run.candidate;
  if (!version) throw Error("Missing replay version.");
  let state = createGame(version.config.rules); const step = replayStepper(version.config.rules);
  const numeric = { name: `Local policy r${version.revision}`, kind: "harness" as const, model: `${version.config.runtime.resolvedModel}@${version.digest}`, effort: "none", strategy: "" };
  const opponent = { name: row.opponent, kind: "bot" as const, model: row.opponent, effort: "default", strategy: "" };
  const events = row.moves.map((move, i) => {
    const label = moveLabel(move, state), seat = state.turn;
    const model = i < row.opening.length ? "fixed-opening-fixture" : seat === row.seat ? numeric.model : opponent.model;
    state = step(move);
    return { ply: i + 1, seat, move, label, model, comment: i < row.opening.length ? "Declared opening fixture; not a contender decision." : "",
      elapsed: row.elapsedByPly?.[i] ?? 0, tokens: null, cost: 0 };
  });
  return { schema: "builderwars.exhibition.v1", id: `${run.id.slice(0, 8)}-${blockIndex}-${gameIndex}`, createdAt: run.createdAt,
    rules: version.config.rules, agents: row.seat === 0 ? [numeric, opponent] : [opponent, numeric], events, status: state.over ? state.reason : "Lab ply cap" };
}

/** Restored scores are recomputed from replayed outcomes; saved summaries are not authority. */
export async function validateLabRun(run: LabRun) {
  await validateLabPlan(run);
  if (!Array.isArray(run.blocks) || run.blocks.length > run.plan.trials) throw Error('Malformed saved comparison.');
  if (run.candidate) { await validateLabVersion(run.candidate); assertComparableSuccessor(run.parent, run.candidate); }
  for (const [i, block] of run.blocks.entries()) {
    if (!run.candidate || block.seed !== run.plan.seeds[i] || block.parent !== run.parent.digest || block.candidate !== run.candidate.digest || block.games.length !== 8) throw Error('Saved paired block custody mismatch.');
    for (const [g, row] of block.games.entries()) {
      const parsed = replay(labReplay(run,i,g));
      if (row.moves.length > run.plan.maxPlies || JSON.stringify(row.opening) !== JSON.stringify(fullgameOpening(run.parent.config.rules,block.seed))
        || (row.exit === 'complete' ? !isRuleComplete(parsed.state) || parsed.state.winner !== row.winner || row.score !== (row.winner === null ? 0.5 : row.winner === row.seat ? 1 : 0) : row.score !== null || isRuleComplete(parsed.state))) throw Error('Saved game outcome contradicts referee replay.');
    }
  }
  if (run.status === 'completed') run.summary = labSummary(run);
  else delete run.summary;
  // Diagnostic labels are also recomputed from their bounded referee-checked targets.
  if (run.development) {
    if (!run.candidate || !run.partitions) throw Error('Missing saved diagnostic targets.');
    const budget = new WorkBudget(2000000, 5000);
    const bundle = await parseBundle(run.partitions.development,run.parent,budget);
    run.development = {before:await scoreCases(run.parent,bundle,budget),after:await scoreCases(run.candidate,bundle,budget)};
  }
}

/** Opaque historical evidence is readable/exportable, never granted execution by this parser. */
export async function readLabVersion(raw: unknown): Promise<Version> {
  const v = raw as Version;
  if (v?.config?.harness?.source === source.digest) return validateLabVersion(v);
  if (!v || JSON.stringify(v).length > 24000 || v.schema !== 'builderwars.frontier-version.v1'
    || !Number.isInteger(v.revision) || v.revision < 0 || typeof v.config?.rules?.name !== 'string'
    || !['tictactoe','connect4'].includes(v.config.rules.kind) || v.config.harness.kind !== 'linear-value'
    || typeof v.config.runtime?.resolvedModel !== 'string' || v.config.runtime.resolvedModel.length > 160
    || !/^[a-f0-9]{64}$/.test(v.config.harness.source) || !Array.isArray(v.config.value?.weights)
    || v.config.value.weights.length !== 22 || v.config.value.weights.some(w => !Number.isFinite(w))) throw Error('Malformed historical Lab version.');
  const {digest, ...body} = v;
  if (digest !== await sha256(JSON.stringify(body))) throw Error('Historical version digest mismatch.');
  return v;
}
