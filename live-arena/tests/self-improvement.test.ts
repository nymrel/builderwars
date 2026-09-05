import test from "node:test";
import assert from "node:assert/strict";
import { RULES, createGame, legalMoves, replayStepper, refereeManifest, type Rules } from "../src/runtime";
import { isRuleComplete } from "../src/outcome";
import {
  FEATURE_COUNT, WorkBudget, baselinePolicy, parsePolicy, sealPolicy, seeded,
  policyMove, playEpisode, trainPolicy, evaluationPlan, evaluateCandidate, type Policy,
  boardFeatures,
} from "../src/self-improvement";

const budget = () => new WorkBudget(100000, 30000);
const optimizer = { seed: 73, episodes: 24, maxPlies: 9, learningRate: 0.1, exploration: 0.3 };
async function unchangedChild(parent: Policy) {
  const { digest, ...body } = parent;
  return sealPolicy({ ...body, parent: digest, revision: parent.revision + 1,
    training: { seed: 1, episodes: 1, completed: 1, capped: 0 } });
}

test("seeded streams and complete self-play episodes reproduce exactly", async () => {
  const first = seeded(91), second = seeded(91), other = seeded(92);
  const values = Array.from({ length: 20 }, () => first());
  assert.deepEqual(values, Array.from({ length: 20 }, () => second()));
  assert.notDeepEqual(values, Array.from({ length: 20 }, () => other()));
  const parent = await baselinePolicy(RULES.tictactoe);
  const run = () => playEpisode(RULES.tictactoe, [parent, parent], 91, budget(), 9);
  assert.deepEqual(run(), run());
  assert.equal(run().episode.exit, "complete");
});

test("policy artifacts round-trip and reject corruption, referee and rules changes", async () => {
  const parent = await baselinePolicy(RULES.tictactoe);
  assert.equal(parent.referee, refereeManifest.digest);
  assert.equal(parent.weights.length, FEATURE_COUNT);
  assert.deepEqual(await parsePolicy(JSON.parse(JSON.stringify(parent))), parent);
  for (const corrupt of [
    { ...parent, weights: parent.weights.map((w, i) => i === 0 ? 0.5 : w) },
    { ...parent, referee: "0".repeat(64) },
    { ...parent, rules: RULES.connect4 },
    { ...parent, training: { ...parent.training, completed: 1 } },
    { ...parent, weights: Array(FEATURE_COUNT).fill(Number.NaN) },
  ]) await assert.rejects(parsePolicy(corrupt));
  assert.throws(() => policyMove(createGame(RULES.connect4), parent, seeded(1), budget()), /rules/i);
});

test("only completed episodes update parameters, and training is reproducible", async () => {
  const parent = await baselinePolicy(RULES.tictactoe), before = JSON.stringify(parent);
  const capped = await trainPolicy(parent, { ...optimizer, episodes: 4, maxPlies: 1 }, budget());
  assert.equal(capped.training.completed, 0);
  assert.equal(capped.training.capped, 4);
  assert.deepEqual(capped.weights, parent.weights);
  const trained = await trainPolicy(parent, optimizer, budget());
  assert.equal(trained.training.completed, optimizer.episodes);
  assert.equal(trained.training.capped, 0);
  assert.notDeepEqual(trained.weights, parent.weights);
  assert.equal(trained.parent, parent.digest);
  assert.equal(trained.revision, parent.revision + 1);
  assert.deepEqual(await trainPolicy(parent, optimizer, budget()), trained);
  assert.equal(JSON.stringify(parent), before);
  assert.equal(isRuleComplete({ over: true, reason: "400-ply exhibition limit" }), false);
  assert.equal(isRuleComplete({ over: true, reason: "Board full" }), true);
});

test("heldout evaluation retains an unchanged candidate and never mutates its inputs", async () => {
  const parent = await baselinePolicy(RULES.tictactoe), candidate = await unchangedChild(parent);
  const plan = await evaluationPlan(parent, 9001, 16, 9);
  const before = JSON.stringify([parent, candidate, plan]);
  const result = await evaluateCandidate(parent, candidate, plan, budget());
  assert.equal(result.decision, "retain");
  assert.equal(result.meanGain, 0);
  assert.equal(result.capped, 0);
  assert.equal(result.games.length, 64);
  assert(result.games.every(game => game.exit === "complete"));
  assert.equal(JSON.stringify([parent, candidate, plan]), before);
});

test("capped heldout games invalidate promotion", async () => {
  const parent = await baselinePolicy(RULES.tictactoe), candidate = await unchangedChild(parent);
  const plan = await evaluationPlan(parent, 123, 16, 3);
  const result = await evaluateCandidate(parent, candidate, plan, budget());
  assert.equal(result.decision, "retain");
  assert.equal(result.capped, result.games.length);
  assert.equal(result.candidateScore, null);
  assert.equal(result.lowerGainBound, null);
  assert(result.games.every(game => game.exit === "capped" && game.winner === null));
});

test("node exhaustion and cancellation abort work, including exploration", async () => {
  const parent = await baselinePolicy(RULES.tictactoe), state = createGame(RULES.tictactoe);
  assert.throws(() => policyMove(state, parent, seeded(1), new WorkBudget(1, 30000)), /budget/i);
  await assert.rejects(trainPolicy(parent, optimizer, new WorkBudget(1, 30000)), /budget/i);
  const controller = new AbortController();
  controller.abort();
  for (const epsilon of [0, 1]) {
    assert.throws(() => policyMove(state, parent, seeded(1), new WorkBudget(100, 30000, controller.signal), epsilon), { name: "AbortError" });
  }
  await assert.rejects(trainPolicy(parent, optimizer, new WorkBudget(100, 30000, controller.signal)), { name: "AbortError" });
});

test("learned policies play legal authoritative trajectories in all five game kinds", async () => {
  const custom: Rules = { kind: "custom", name: "Four by four", rows: 4, cols: 4, connect: 3, gravity: false };
  for (const rules of [...Object.values(RULES), custom]) {
    const parent = await baselinePolicy(rules);
    const { episode } = playEpisode(rules, [parent, parent], 19, budget(), 8);
    const advance = replayStepper(rules);
    let state = createGame(rules);
    for (const move of episode.moves) {
      assert(legalMoves(state).includes(move), `${rules.kind}: ${move}`);
      state = advance(move);
    }
    assert.deepEqual(state.moves, episode.moves);
    assert.equal(episode.exit === "complete", isRuleComplete(state));
    assert.equal(episode.winner, isRuleComplete(state) ? state.winner : null);
  }
});

test("feature ownership mirrors both seats in every supported game", () => {
  const custom: Rules = { kind: "custom", name: "Feature test", rows: 3, cols: 4, connect: 3, gravity: true };
  for (const rules of [...Object.values(RULES), custom]) {
    const step = replayStepper(rules);
    let state = createGame(rules);
    for (let i = 0; i < 3; i++) state = step(legalMoves(state)[0]);
    const a = boardFeatures(state, 0), b = boardFeatures(state, 1);
    assert.deepEqual(a.slice(0, 6), b.slice(6, 12));
    assert.deepEqual(a.slice(6, 12), b.slice(0, 6));
    assert.deepEqual(a.slice(12, 15), b.slice(15, 18));
    assert.equal(a[18], b[19]); assert.equal(a[20], b[21]);
    assert(a.some(n => n > 0));
  }
  const invalid = createGame(RULES.chess);
  invalid.cells[0] = "w?";
  assert.throws(() => boardFeatures(invalid, 0), /encoding/);
});

test("training uses canonical parsed parent instead of raw caller key order", async () => {
  const parent = await baselinePolicy(RULES.tictactoe);
  const reordered = Object.fromEntries(Object.entries(parent).reverse()) as Policy;
  assert.deepEqual(await parsePolicy(reordered), parent);
  const candidate = await trainPolicy(reordered, optimizer, budget());
  assert.deepEqual(await parsePolicy(candidate), candidate);
});
