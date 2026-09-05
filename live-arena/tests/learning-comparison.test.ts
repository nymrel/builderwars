import test from "node:test";
import assert from "node:assert/strict";
import { prepareExperiment, runExperiment, requestForCell, symmetryKey, heldOutFixtures, LIMITS } from "../scripts/learning-comparison";
import { ENDPOINT, MODEL } from "../scripts/local-showcase";
import { createGame, applyMove, RULES, legalMoves } from "../src/runtime";

function practice() {
  const agents = ["plain", "tactical"].map(harness => ({ name: `Local Qwen · ${harness} harness · constrained`, kind: "harness",
    model: MODEL, effort: "default", strategy: harness === "plain" ? "Plain referee board and legal moves" : "Tactical observations" }));
  return { schema: "builderwars.local-showcase.v1", experiment: { mode: "gameplay" }, endpoint: ENDPOINT, requestedModel: MODEL,
    games: [["2", "1", "4", "5", "0", "3", "6"], ["2", "4", "1", "5", "0"]].map((moves, index) => ({
      exit: "complete", harnesses: index ? ["tactical", "plain"] : ["plain", "tactical"], record: {
        schema: "builderwars.exhibition.v1", id: `synthetic-practice-${index}`, createdAt: "2026-09-05T00:00:00Z",
        rules: RULES.tictactoe, agents: index ? [...agents].reverse() : agents, status: "ignored",
        events: moves.map((move, i) => ({ ply: i + 1, seat: i % 2, move, label: "", comment: "PRIVATE_COMMENT",
          model: "runtime-reported", elapsed: 1, tokens: null, cost: null })),
      },
    })) };
}
const reply = (move: string, extra = {}) => new Response(JSON.stringify({ model: "/private/models/qwen.gguf",
  choices: [{ message: { content: JSON.stringify({ move }) } }], ...extra }));

test("learning comparison: D4 key matches a rotation and reflection but never merges turns", () => {
  const state = { cells: ["w", "b", "", "", "w", "", "b", "", ""], turn: 0 as const };
  const rotated = { cells: ["b", "", "w", "", "w", "b", "", "", ""], turn: 0 as const };
  const reflected = { cells: ["", "b", "w", "", "w", "", "", "", "b"], turn: 0 as const };
  assert.equal(symmetryKey(state), symmetryKey(rotated));
  assert.equal(symmetryKey(state), symmetryKey(reflected));
  assert.notEqual(symmetryKey(state), symmetryKey({ ...state, turn: 1 }));
});

test("learning comparison: deterministic reachable D4-disjoint twelve balanced fixtures and frozen source-only memory", async () => {
  const plan = await prepareExperiment(practice()), second = await prepareExperiment(practice());
  assert.equal(plan.fixtureDigest, second.fixtureDigest);
  assert.equal(plan.memoryDigest, second.memoryDigest);
  assert.equal(plan.memoryContext.sources.length, 2);
  assert.equal(plan.memoryContext.mode, "frozen-evaluation");
  assert.equal(plan.fixtures.length, 12);
  assert.equal(new Set(plan.fixtures.map(f => f.symmetryKey)).size, 12);
  const groups = new Map<string, number>();
  for (const fixture of plan.fixtures) {
    assert(!plan.excludedPracticeKeys.includes(fixture.symmetryKey));
    let state = createGame(RULES.tictactoe);
    for (const move of fixture.state.moves) state = applyMove(state, move);
    assert.deepEqual(state.cells, fixture.state.cells);
    assert.equal(state.turn, fixture.seat);
    const key = `${fixture.category}/${fixture.seat}`;
    groups.set(key, (groups.get(key) ?? 0) + 1);
  }
  assert.deepEqual([...groups.values()], [3, 3, 3, 3]);
  assert.equal(plan.fixtures.filter(f => f.order[0] === "baseline").length, 6);
  assert.throws(() => plan.memory.episodes.push(plan.memory.episodes[0]));
  const allKeys = new Set<string>();
  for (let i = 0; i < 3 ** 9; i++) {
    const cells = [...i.toString(3).padStart(9, "0")].map(n => n === "0" ? "" : n === "1" ? "w" : "b");
    for (const turn of [0, 1] as const) allKeys.add(symmetryKey({ cells, turn }));
  }
  assert.throws(() => heldOutFixtures(allKeys), /Insufficient/);
});

test("learning comparison: baseline and memory requests differ only by production frozen prompt", async () => {
  const plan = await prepareExperiment(practice());
  for (const fixture of plan.fixtures) {
    const plain = requestForCell(fixture, "baseline", plan.memoryContext), learned = requestForCell(fixture, "frozen-memory", plan.memoryContext);
    assert.equal(learned.messages[0].content, plain.messages[0].content + `\n\n${plan.memoryContext.prompt}`);
    assert.deepEqual({ ...plain, messages: [] }, { ...learned, messages: [] });
    assert(!plain.messages[0].content.includes("tactical observations"));
    assert.deepEqual(plain.response_format!.schema.properties.move.enum, legalMoves(fixture.state));
  }
});

test("learning comparison: predetermined cells continue after illegal/HTTP failures, preserve private usage, no share leakage", async () => {
  const plan = await prepareExperiment(practice()), before = JSON.stringify(plan);
  let calls = 0;
  const result = await runExperiment(plan, { fetchImpl: async (url, options) => {
    assert.equal(url, ENDPOINT); assert.equal(options?.redirect, "error");
    assert.deepEqual(options?.headers, { "Content-Type": "application/json" });
    calls++;
    if (calls === 1) return reply("99");
    if (calls === 2) return new Response("PRIVATE_HTTP_BODY", { status: 503 });
    const body = JSON.parse(String(options?.body));
    return reply(body.response_format.schema.properties.move.enum[0], { usage: { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 } });
  } });
  assert.equal(calls, 24);
  assert.equal(result.privateCells.filter(c => c.exit === "failed").length, 2);
  assert.equal(result.privateCells[1].responseText, "PRIVATE_HTTP_BODY");
  assert.equal(result.privateCells[2].responseModel, "/private/models/qwen.gguf");
  assert.equal(JSON.stringify(plan), before);
  const publicText = JSON.stringify(result.summary);
  for (const secret of ["PRIVATE_HTTP_BODY", "/private/models", ".gguf", "PRIVATE_COMMENT", ENDPOINT]) assert(!publicText.includes(secret));
  assert(result.summary.arms.every(arm => arm.inputTokens === null));
  assert.equal(result.summary.dollarCost, null); assert.equal(result.summary.electricityCost, null);
});

test("learning comparison: mocked exact answers grade correctly with observed token totals", async () => {
  const plan = await prepareExperiment(practice()); let calls = 0;
  const independentlyGraded = plan.fixtures.map(fixture => legalMoves(fixture.state).filter(move => {
    const next = applyMove(fixture.state, move);
    if (fixture.category === "immediate-win") return next.over && next.winner === fixture.seat;
    return next.over || !legalMoves(next).some(opponentMove => {
      const reply = applyMove(next, opponentMove);
      return reply.over && reply.winner === 1 - fixture.seat;
    });
  }));
  plan.fixtures.forEach((fixture, i) => assert.deepEqual(fixture.acceptedMoves, independentlyGraded[i]));
  const result = await runExperiment(plan, { fetchImpl: async () => reply(independentlyGraded[Math.floor(calls++ / 2)][0],
    { usage: { prompt_tokens: 20, completion_tokens: 4, total_tokens: 24 } }) });
  assert(result.summary.arms.every(arm => arm.correct === 12 && arm.inputTokens === 240 && arm.outputTokens === 48));
  assert.equal(result.summary.scheduledCells, 24);
  assert.equal(result.summary.pairedTransitions.bothCorrect, 12);
  assert.deepEqual(result.privateCells.map(c => c.arm), plan.fixtures.flatMap(f => f.order));
});

test("learning comparison: paired transitions and category counts separate tactical errors from incomplete pairs", async () => {
  const plan = await prepareExperiment(practice()); let calls = 0;
  const result = await runExperiment(plan, { fetchImpl: async () => {
    const index = Math.floor(calls / 2), fixture = plan.fixtures[index], arm = fixture.order[calls++ % 2];
    const transition = index % 5;
    if (transition === 4 && arm === "baseline") return new Response("failed fixture", { status: 503 });
    const correct = transition === 0 || transition === 4 || (transition === 1 && arm === "baseline") || (transition === 2 && arm === "frozen-memory");
    const incorrect = legalMoves(fixture.state).find(move => !fixture.acceptedMoves.includes(move));
    assert(incorrect !== undefined);
    return reply(correct ? fixture.acceptedMoves[0] : incorrect);
  } });
  assert.deepEqual(result.summary.pairedTransitions, { bothCorrect: 3, baselineOnlyCorrect: 3, memoryOnlyCorrect: 2, neitherCorrect: 2, incompletePair: 2 });
  for (const arm of result.summary.arms) {
    assert.equal(arm.byCategory.length, 2);
    for (const category of arm.byCategory) {
      assert.equal(category.scheduled, 6);
      assert.equal(category.correct + category.incorrect + category.failed + category.capped, 6);
    }
  }
  assert.equal(result.summary.arms[0].failed, 2);
  const capped = await runExperiment(plan, { limits: { maxCalls: 1 }, fetchImpl: async () => reply(plan.fixtures[0].acceptedMoves[0]) });
  assert.deepEqual(capped.summary.pairedTransitions, { bothCorrect: 0, baselineOnlyCorrect: 0, memoryOnlyCorrect: 0, neitherCorrect: 0, incompletePair: 12 });
  assert.equal(capped.summary.scheduledCells, 24);
  assert.equal(capped.summary.arms.reduce((sum, arm) => sum + arm.incorrect, 0), 0);
  const badSchedule = structuredClone(plan); badSchedule.fixtures[0].order.push("baseline");
  await assert.rejects(runExperiment(badSchedule, { fetchImpl: async () => { throw Error("Must not dispatch"); } }), /twenty-four scheduled/);
});

test("learning comparison: caps, deadlines and redirects preserve failures without replacing moves", async () => {
  const plan = await prepareExperiment(practice());
  let calls = 0;
  const fetchImpl: typeof fetch = async () => { calls++; return reply("99"); };
  await assert.rejects(runExperiment(plan, { fetchImpl, limits: { maxCalls: 25 } }), /only be reduced/);
  assert.equal(calls, 0);
  const capped = await runExperiment(plan, { fetchImpl, limits: { maxCalls: 1 } });
  assert.equal(capped.summary.inferenceCalls, 1);
  assert.equal(capped.privateCells.filter(c => c.exit === "capped").length, 23);
  const timeout = await runExperiment(plan, { limits: { maxCalls: 1, perCallMs: 5 }, fetchImpl: async (_url, options) =>
    new Promise<Response>((_resolve, reject) => options!.signal!.addEventListener("abort", () => reject(Error("aborted")), { once: true })) });
  assert.equal(timeout.privateCells[0].exit, "failed");
  assert.equal(timeout.privateCells[0].failure, "Inference deadline exceeded");
  const redirect = await runExperiment(plan, { limits: { maxCalls: 1 }, fetchImpl: async () => new Response("", { status: 302 }) });
  assert.equal(redirect.privateCells[0].failure, "Redirect rejected");
  let time = 0;
  const total = await runExperiment(plan, { now: () => time, limits: { totalMs: 10 }, fetchImpl: async () => { time = 11; return reply("0"); } });
  assert.equal(total.summary.inferenceCalls, 1); assert.equal(total.privateCells[0].exit, "failed");
  const corrupt = structuredClone(plan); corrupt.memory.episodes[0].mistakes = [];
  await assert.rejects(runExperiment(corrupt, { fetchImpl }), /digest mismatch/);
  assert.deepEqual(LIMITS, { maxCalls: 24, maxTokens: 64, perCallMs: 15000, totalMs: 240000 });
});
