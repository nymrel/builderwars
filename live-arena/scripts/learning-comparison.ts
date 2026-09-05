/** Manual frozen-practice experiment. Imports and --prepare never dispatch inference. */
import { randomUUID } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { PracticeMemory, analyzePractice, profileKey, type MemorySnapshot, type MemoryContext } from "../src/learning";
import { parseDecision, type Agent } from "../src/models";
import { createGame, applyMove, legalMoves, replay, sha256, RULES, refereeManifest, type GameState } from "../src/runtime";
import { ENDPOINT, MODEL, requestFor, tacticalObservations } from "./local-showcase";

export const LIMITS = Object.freeze({ maxCalls: 24, maxTokens: 64, perCallMs: 15000, totalMs: 240000 });
type Arm = "baseline" | "frozen-memory";
type Category = "immediate-win" | "avoidable-threat";
export type Fixture = { id: string; category: Category; seat: 0 | 1; symmetryKey: string;
  state: GameState; acceptedMoves: string[]; order: Arm[] };
export type Plan = { schema: "builderwars.learning-comparison.v1"; sourceDigest: string; referee: typeof refereeManifest;
  plainProfile: Agent; memory: MemorySnapshot; memoryContext: MemoryContext;
  memoryDigest: string; fixtureDigest: string; excludedPracticeKeys: string[]; fixtures: Fixture[] };
type Cell = { number: number; fixtureId: string; arm: Arm; category: Category; seat: 0 | 1;
  exit: "accepted" | "failed" | "capped"; move: string | null; correct: boolean | null; failure: string | null;
  dispatched: boolean; elapsedMs: number; responseText: string | null; responseStatus: number | null;
  responseModel: unknown; usage: { inputTokens: number | null; outputTokens: number | null; totalTokens: number | null };
  request: ReturnType<typeof requestFor> };
type Options = { fetchImpl: typeof fetch; now?: () => number; limits?: Partial<Record<keyof typeof LIMITS, number>>;
  onRequest?: (cell: Cell) => Promise<void>; onResult?: (cell: Cell) => Promise<void> };

function freeze<T>(value: T): T {
  if (value && typeof value === "object") { Object.values(value).forEach(freeze); Object.freeze(value); }
  return value;
}
/** D4 equivalence preserves player marks and includes the side to move. */
export function symmetryKey(state: Pick<GameState, "cells" | "turn">): string {
  if (state.cells.length !== 9) throw Error("Expected a 3x3 position");
  const variants: string[] = [];
  for (const reflected of [false, true]) for (let rotations = 0; rotations < 4; rotations++) {
    const cells = Array<string>(9).fill("");
    for (let i = 0; i < 9; i++) {
      let row = Math.floor(i / 3), col = i % 3;
      if (reflected) col = 2 - col;
      for (let n = 0; n < rotations; n++) [row, col] = [col, 2 - row];
      cells[row * 3 + col] = state.cells[i];
    }
    variants.push(`${state.turn}:${cells.map(cell => cell || ".").join("")}`);
  }
  return variants.sort()[0];
}

export function heldOutFixtures(excluded: Set<string>): Fixture[] {
  const queue = [createGame(RULES.tictactoe)], seen = new Set<string>(), buckets = new Map<string, Fixture[]>();
  for (let index = 0; index < queue.length; index++) {
    const state = queue[index], key = symmetryKey(state);
    if (seen.has(key)) continue;
    seen.add(key);
    if (state.over) continue;
    if (!excluded.has(key)) {
      const tactics = tacticalObservations(state), legal = legalMoves(state);
      const category: Category | null = tactics.immediateWins.length ? "immediate-win"
        : tactics.noImmediateOpponentWin.length > 0 && tactics.noImmediateOpponentWin.length < legal.length ? "avoidable-threat" : null;
      if (category) {
        const bucketKey = `${category}/${state.turn}`, bucket = buckets.get(bucketKey) ?? [];
        if (bucket.length < 3) bucket.push({ id: "", category, seat: state.turn, symmetryKey: key,
          state: structuredClone(state), acceptedMoves: category === "immediate-win" ? tactics.immediateWins : tactics.noImmediateOpponentWin, order: [] });
        buckets.set(bucketKey, bucket);
      }
    }
    for (const move of legalMoves(state)) queue.push(applyMove(state, move));
  }
  const fixtures: Fixture[] = [];
  for (const category of ["immediate-win", "avoidable-threat"] as const) for (const seat of [0, 1]) {
    const bucket = buckets.get(`${category}/${seat}`) ?? [];
    if (bucket.length !== 3) throw Error(`Insufficient disjoint fixtures for ${category}/seat${seat}: ${bucket.length}/3`);
    fixtures.push(...bucket);
  }
  return fixtures.map((fixture, index) => ({ ...fixture, id: `position-${String(index + 1).padStart(2, "0")}`,
    order: index % 2 ? ["frozen-memory", "baseline"] : ["baseline", "frozen-memory"] }));
}

export async function prepareExperiment(raw: unknown): Promise<Plan> {
  const receipt = raw as any;
  if (receipt?.schema !== "builderwars.local-showcase.v1" || receipt.experiment?.mode !== "gameplay"
    || receipt.requestedModel !== MODEL || receipt.endpoint !== ENDPOINT || receipt.games?.length !== 2)
    throw Error("Use the retained two-game local gameplay receipt");
  const memory = new PracticeMemory(), excluded = new Set<string>();
  let plainProfile: Agent | undefined;
  for (let index = 0; index < 2; index++) {
    const game = receipt.games[index], { record, state: final } = replay(game.record);
    if (game.exit !== "complete" || !final.over || record.rules.kind !== "tictactoe"
      || JSON.stringify(game.harnesses) !== JSON.stringify(index === 0 ? ["plain", "tactical"] : ["tactical", "plain"]))
      throw Error("Practice must contain the original completed seat-swapped tic-tac-toe games");
    const agents: Agent[] = record.agents.map(agent => ({ ...agent, endpoint: ENDPOINT, key: "" }));
    const plain = agents[index];
    if (plain.kind !== "harness" || plain.model !== MODEL) throw Error("Unexpected plain practice profile");
    if (plainProfile && await profileKey(plainProfile) !== await profileKey(plain)) throw Error("Plain profile changed across practice games");
    plainProfile = plain;
    const mistakes = analyzePractice(record).mistakes;
    if (!mistakes.some(m => m.seat === index && m.ply === (index === 0 ? 5 : 4)
      && m.kind === (index === 0 ? "missed-win" : "allowed-immediate-loss")))
      throw Error("Required plain-harness practice lesson is missing");
    let state = createGame(record.rules);
    excluded.add(symmetryKey(state));
    for (const event of record.events) { state = applyMove(state, event.move); excluded.add(symmetryKey(state)); }
    await memory.remember(record, agents); // Only these original completed practice games enter memory.
  }
  const snapshot = memory.snapshot();
  const context = await memory.context(plainProfile!, RULES.tictactoe, "frozen-evaluation", snapshot);
  if (!context || context.sources.length !== 2) throw Error("Two-source frozen plain memory is required");
  const fixtures = heldOutFixtures(excluded);
  return freeze({ schema: "builderwars.learning-comparison.v1", sourceDigest: await sha256(JSON.stringify(raw)),
    referee: refereeManifest, plainProfile: plainProfile!, memory: snapshot, memoryContext: context,
    memoryDigest: await sha256(JSON.stringify(snapshot)), fixtureDigest: await sha256(JSON.stringify(fixtures)),
    excludedPracticeKeys: [...excluded].sort(), fixtures });
}

export function requestForCell(fixture: Fixture, arm: Arm, context: MemoryContext) {
  const request = requestFor(fixture.state, "plain", "gameplay");
  if (arm === "frozen-memory") request.messages[0].content += `\n\n${context.prompt}`;
  return request;
}
const count = (raw: unknown): number | null => typeof raw === "number" && Number.isSafeInteger(raw) && raw >= 0 ? raw : null;
function sumKnown(cells: Cell[], key: keyof Cell["usage"]) {
  const dispatched = cells.filter(cell => cell.dispatched);
  if (!dispatched.length || dispatched.some(cell => cell.usage[key] === null)) return null;
  const total = dispatched.reduce((sum, cell) => sum + cell.usage[key]!, 0);
  return Number.isSafeInteger(total) ? total : null;
}
function cellCounts(cells: Cell[]) {
  return { scheduled: cells.length, correct: cells.filter(cell => cell.exit === "accepted" && cell.correct === true).length,
    incorrect: cells.filter(cell => cell.exit === "accepted" && cell.correct === false).length,
    failed: cells.filter(cell => cell.exit === "failed").length, capped: cells.filter(cell => cell.exit === "capped").length };
}

export async function runExperiment(input: Plan, options: Options) {
  const plan = freeze(structuredClone(input));
  if (plan.fixtures.length !== 12 || new Set(plan.fixtures.map(fixture => fixture.id)).size !== 12
    || plan.fixtures.some(fixture => fixture.order.length !== 2 || [...fixture.order].sort().join(",") !== "baseline,frozen-memory"))
    throw Error("Exactly twelve positions and twenty-four scheduled cells are required");
  if (await sha256(JSON.stringify(plan.memory)) !== plan.memoryDigest || await sha256(JSON.stringify(plan.fixtures)) !== plan.fixtureDigest)
    throw Error("Frozen memory or fixture digest mismatch");
  const memory = new PracticeMemory();
  const context = await memory.context(plan.plainProfile, RULES.tictactoe, "frozen-evaluation", plan.memory);
  if (!context || context.digest !== plan.memoryContext.digest || context.prompt !== plan.memoryContext.prompt)
    throw Error("Frozen production memory context mismatch");
  const limits = { ...LIMITS, ...options.limits };
  for (const key of Object.keys(LIMITS) as (keyof typeof LIMITS)[])
    if (!Number.isInteger(limits[key]) || limits[key] < 1 || limits[key] > LIMITS[key]) throw Error("Experiment limits may only be reduced");
  const now = options.now ?? (() => performance.now()), started = now(), deadline = started + limits.totalMs;
  const cells: Cell[] = [];
  let dispatched = 0;
  for (const fixture of plan.fixtures) for (const arm of fixture.order) {
    const request = requestForCell(fixture, arm, context);
    request.max_tokens = limits.maxTokens;
    const cell: Cell = { number: cells.length + 1, fixtureId: fixture.id, arm, category: fixture.category, seat: fixture.seat,
      exit: "capped", move: null, correct: null, failure: null, dispatched: false, elapsedMs: 0,
      responseText: null, responseStatus: null, responseModel: null,
      usage: { inputTokens: null, outputTokens: null, totalTokens: null }, request };
    cells.push(cell);
    if (dispatched >= limits.maxCalls || now() >= deadline) {
      cell.failure = "Total request or time cap reached";
      await options.onResult?.(structuredClone(cell));
      continue;
    }
    await options.onRequest?.(structuredClone(cell));
    if (now() >= deadline) { cell.failure = "Total time cap reached before dispatch"; await options.onResult?.(structuredClone(cell)); continue; }
    const controller = new AbortController(), callStarted = now();
    let timer: ReturnType<typeof setTimeout> | undefined, accepting = true;
    try {
      const timeout = new Promise<never>((_, reject) => {
        timer = setTimeout(() => { accepting = false; controller.abort(); reject(Error("Inference deadline exceeded")); },
          Math.max(1, Math.min(limits.perCallMs, deadline - now())));
      });
      const data = await Promise.race([timeout, (async () => {
        cell.dispatched = true; dispatched++;
        const response = await options.fetchImpl(ENDPOINT, { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify(request), credentials: "omit", redirect: "error", signal: controller.signal });
        if (!accepting) throw Error("Late response rejected");
        cell.responseStatus = response.status;
        const text = await response.text();
        if (!accepting) throw Error("Late response rejected");
        cell.responseText = text;
        if (response.redirected || (response.url && response.url !== ENDPOINT) || (response.status >= 300 && response.status < 400)) throw Error("Redirect rejected");
        if (!response.ok) throw Error(`Local HTTP ${response.status}`);
        return JSON.parse(text);
      })()]);
      if (now() >= deadline || now() - callStarted >= limits.perCallMs) throw Error("Inference deadline exceeded");
      cell.responseModel = data?.model ?? null; // Private receipt only; never copied into share summaries.
      cell.usage = { inputTokens: count(data?.usage?.prompt_tokens), outputTokens: count(data?.usage?.completion_tokens), totalTokens: count(data?.usage?.total_tokens) };
      if (cell.usage.outputTokens !== null && cell.usage.outputTokens > limits.maxTokens) throw Error("Reported output exceeds token cap");
      const decision = parseDecision(data?.choices?.[0]?.message?.content, legalMoves(fixture.state));
      applyMove(fixture.state, decision.move); // Independent authoritative legality check, with no state update to the fixture.
      cell.move = decision.move; cell.correct = fixture.acceptedMoves.includes(decision.move); cell.exit = "accepted";
    } catch (error) { cell.failure = error instanceof Error ? error.message : String(error); cell.exit = "failed"; }
    finally {
      accepting = false; controller.abort(); clearTimeout(timer);
      cell.elapsedMs = Math.max(0, now() - callStarted);
      await options.onResult?.(structuredClone(cell));
    }
  }
  if (await sha256(JSON.stringify(plan.memory)) !== plan.memoryDigest || memory.episodeCount !== 0) throw Error("Evaluation mutated memory");
  if (cells.length !== 24) throw Error("Expected exactly twenty-four scheduled cells");
  const pairedTransitions = { bothCorrect: 0, baselineOnlyCorrect: 0, memoryOnlyCorrect: 0, neitherCorrect: 0, incompletePair: 0 };
  for (const fixture of plan.fixtures) {
    const baseline = cells.find(cell => cell.fixtureId === fixture.id && cell.arm === "baseline")!;
    const learned = cells.find(cell => cell.fixtureId === fixture.id && cell.arm === "frozen-memory")!;
    if (baseline.exit !== "accepted" || learned.exit !== "accepted") pairedTransitions.incompletePair++;
    else if (baseline.correct && learned.correct) pairedTransitions.bothCorrect++;
    else if (baseline.correct) pairedTransitions.baselineOnlyCorrect++;
    else if (learned.correct) pairedTransitions.memoryOnlyCorrect++;
    else pairedTransitions.neitherCorrect++;
  }
  const summary = {
    schema: plan.schema, sourceDigest: plan.sourceDigest, memoryDigest: plan.memoryDigest, fixtureDigest: plan.fixtureDigest,
    requestedModel: MODEL, responseIdentity: "Declared requested model only; private runtime metadata is not attestation", limits,
    inferenceCalls: dispatched, positions: plan.fixtures.length, scheduledCells: cells.length, pairedTransitions,
    elapsedMs: Math.max(0, now() - started),
    arms: (["baseline", "frozen-memory"] as const).map(arm => {
      const selected = cells.filter(cell => cell.arm === arm);
      return { arm, ...cellCounts(selected), byCategory: (["immediate-win", "avoidable-threat"] as const).map(category =>
        ({ category, ...cellCounts(selected.filter(cell => cell.category === category)) })), inputTokens: sumKnown(selected, "inputTokens"),
        outputTokens: sumKnown(selected, "outputTokens"), totalTokens: sumKnown(selected, "totalTokens"),
        elapsedMs: selected.reduce((sum, cell) => sum + cell.elapsedMs, 0) };
    }), dollarCost: null, electricityCost: null,
    limitsOfEvidence: ["Twelve deterministic tactical positions, not a general performance benchmark", "D4 symmetry exclusion includes all practice positions and turn",
      "Both arms use identical legal-move constrained generation", "Frozen memory adds prompt tokens; compute is not equalized",
      "No weight training, automatic promotion, or evaluation-to-memory feedback", "Aborts do not attest immediate cessation of local computation"],
    cells: cells.map(({ fixtureId, arm, category, seat, exit, move, correct, elapsedMs, usage }) =>
      ({ fixtureId, arm, category, seat, exit, move, correct, elapsedMs, usage })),
  };
  return { summary, privateCells: cells };
}

async function main() {
  const [mode, receiptPath, ...extra] = process.argv.slice(2);
  if (!["--prepare", "--run"].includes(mode) || !receiptPath || extra.length) {
    console.log("No inference started. Usage: tsx scripts/learning-comparison.ts --prepare <practice-receipt.json> | --run <practice-receipt.json>"); return;
  }
  const plan = await prepareExperiment(JSON.parse(await readFile(resolve(receiptPath), "utf8")));
  const parent = resolve(dirname(fileURLToPath(import.meta.url)), "../output/playwright");
  await mkdir(parent, { recursive: true });
  const output = resolve(parent, `learning-comparison-${mode.slice(2)}-${new Date().toISOString().replace(/[:.]/g, "-")}-${randomUUID()}`);
  await mkdir(output); await mkdir(resolve(output, "private"));
  const save = (name: string, value: unknown) => writeFile(resolve(output, name), JSON.stringify(value, null, 2), { flag: "wx" });
  await save("intent.json", { mode, endpoint: ENDPOINT, requestedModel: MODEL, limits: LIMITS,
    sourceDigest: plan.sourceDigest, fixtureDigest: plan.fixtureDigest, memoryDigest: plan.memoryDigest,
    memoryPromptDigest: plan.memoryContext.digest, cells: 24, positions: 12,
    assistance: "Identical legal-move constrained generation; only frozen production memory prompt differs between arms",
    grading: "Immediate win or avoidable immediate opponent threat; no retry, move replacement, weight training or general performance claim" });
  await save("private/plan.json", plan); // Fixture, memory and source digests exist on disk before any dispatch.
  if (mode === "--prepare") { console.log(JSON.stringify({ output, inferenceCalls: 0, fixtureDigest: plan.fixtureDigest, memoryDigest: plan.memoryDigest })); return; }
  const result = await runExperiment(plan, { fetchImpl: fetch,
    onRequest: cell => save(`private/request-${String(cell.number).padStart(2, "0")}.json`, cell),
    onResult: cell => save(`private/result-${String(cell.number).padStart(2, "0")}.json`, cell),
  });
  await save("share-summary.json", result.summary);
  console.log(JSON.stringify({ output, ...result.summary, cells: undefined }));
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href)
  main().catch(error => { console.error(error); process.exitCode = 1; });
