import test from "node:test";
import assert from "node:assert/strict";
import { RULES, createGame, replayStepper, legalMoves, applyMove } from "../src/runtime";
import { WorkBudget, seeded } from "../src/self-improvement";
import { localBaseline } from "../scripts/frontier-store";
import { createVersion, parseVersion, numericVersionMove, assertComparableSuccessor, identityKey } from "../src/frontier-version";
import { positionGroup } from "../src/frontier-cases";
import { strategicFeatures, strategicMove, twoPlyChoices, leafValue, STRATEGIC_FEATURE_COUNT, STRATEGIC_FEATURE_VERSION, STRATEGIC_MODEL } from "../src/strategic-value";
import { sampleStrategicCases, practiceStrategic, parseStrategicBundle, strategicExposedGroups } from "../src/strategic-practice";
import { tacticalChoices, gradeTactic } from "../src/strength";

const budget = () => new WorkBudget(2000000, 300000);
test("pinned referee takes complete capture chains in one turn; cap horizon remains a heuristic", () => {
  const chain = createGame(RULES.checkers); chain.cells.fill("");
  chain.cells[40] = "w"; chain.cells[33] = "b"; chain.cells[19] = "b"; chain.cells[5] = "b";
  assert.deepEqual(legalMoves(chain), ["a6-c4-e2"]);
  assert.throws(() => applyMove(chain, "a6-c4"));
  const next = applyMove(chain, "a6-c4-e2");
  assert.equal(next.turn, 1); assert.equal(next.over, false);
  assert.equal(twoPlyChoices(chain, budget()).length, 1);
  // Synthetic clock-boundary fixture only, NOT a claimed played transcript.
  for (const count of [398, 399]) {
    const boundary = createGame(RULES.checkers); boundary.moves = Array(count).fill("synthetic-clock-fixture");
    const choices = twoPlyChoices(boundary, budget());
    assert.ok(choices.every(c => c.leaves.every(l => l.terminal === null && l.features?.length === 26)));
    assert.ok(legalMoves(boundary).includes(strategicMove(boundary, Array(26).fill(0), seeded(713), budget())));
  }
});
function position(moves: string[]) { const step = replayStepper(RULES.tictactoe); return moves.reduce((_s, m) => step(m), createGame(RULES.tictactoe)); }
test("strategic versions declare distinct identity, features and search; old executor remains one-ply", async () => {
  const baseline = await localBaseline(RULES.tictactoe, "strategic-value"), old = await localBaseline(RULES.tictactoe);
  assert.equal(baseline.config.runtime.resolvedModel, STRATEGIC_MODEL);
  assert.equal(baseline.config.value!.features, STRATEGIC_FEATURE_VERSION);
  assert.equal(baseline.config.value!.weights.length, STRATEGIC_FEATURE_COUNT);
  assert.equal(old.config.harness.kind, "linear-value"); assert.equal(old.config.value!.weights.length, 22);
  assert.deepEqual(await parseVersion(baseline), baseline);
  const config = structuredClone(baseline.config); config.value!.weights[0] = 1;
  const child = await createVersion(config, baseline, { method: "search-pairwise-v1", source: "0".repeat(64), identities: [await identityKey(config.runtime)] });
  assertComparableSuccessor(baseline, child);
  assert.throws(() => assertComparableSuccessor(old, child), /differ/);
  const wrong = structuredClone(config); wrong.tools[0].id = "one-ply-value";
  await assert.rejects(createVersion(wrong), /configuration/);
  await assert.rejects(localBaseline(RULES.chess, "strategic-value"), /strategic rules/);
});
test("two-ply terminal ordering beats saturated heuristics and never ignores an avoidable immediate loss", async () => {
  assert.equal(leafValue({ features: Array(26).fill(1), terminal: null }, Array(26).fill(8)), 0.98);
  const win = position(["0", "3", "1", "4"]), defense = position(["0", "4", "1"]);
  for (const weights of [Array(26).fill(0), Array(26).fill(8), Array(26).fill(-8)]) {
    assert.equal(strategicMove(win, weights, seeded(713), budget()), "2");
    assert.equal(strategicMove(defense, weights, seeded(713), budget()), "2");
  }
  const version = await localBaseline(RULES.tictactoe, "strategic-value");
  assert.equal(numericVersionMove(version, win, budget()), "2");
  assert.throws(() => strategicMove(win, Array(26).fill(0), () => 1, budget()), /random/);
  assert.throws(() => strategicMove(win, Array(26).fill(0), seeded(1), new WorkBudget(1)), /budget/);
});
test("checkers features and group symmetries respect promotion directions and history conservatism", async () => {
  const random = seeded(17); let state = createGame(RULES.checkers);
  for (let ply = 0; ply < 60 && !state.over; ply++) {
    if (ply % 10 === 0) {
      const features = strategicFeatures(state, state.turn);
      assert.equal(features.length, 26); assert.ok(features.every(x => Number.isFinite(x) && x >= 0 && x <= 1));
      const move = strategicMove(state, Array(26).fill(0), random, budget());
      const grade = gradeTactic(tacticalChoices(state, budget()), move);
      assert.equal(grade.legal, true); assert.equal(grade.missedWin, false); assert.equal(grade.avoidableLoss, false);
    }
    const moves = legalMoves(state); state = applyMove(state, moves[Math.floor(random() * moves.length)]);
  }
  const swapped = structuredClone(state), colors: Record<string, string> = { w: "b", b: "w", W: "B", B: "W", "": "" };
  swapped.cells.reverse(); swapped.cells = swapped.cells.map(p => colors[p]); swapped.turn = state.turn === 0 ? 1 : 0;
  assert.equal(await positionGroup(state), await positionGroup(swapped));
  const differentClock = structuredClone(state); differentClock.quiet = 70; differentClock.positions = [];
  assert.equal(await positionGroup(state), await positionGroup(differentClock));
  const reflected = structuredClone(state); reflected.cells = state.cells.map((_p, i) => state.cells[Math.floor(i / 8) * 8 + 7 - i % 8]);
  assert.notEqual(await positionGroup(state), await positionGroup(reflected));
});
test("strategic practice changes coefficients from replayed teacher preferences and rejects contaminated input", async () => {
  const parent = await localBaseline(RULES.tictactoe, "strategic-value"), snapshot = JSON.stringify(parent);
  const training = await sampleStrategicCases(parent, 713, 16, "training", budget());
  const excluded = await strategicExposedGroups(training, budget());
  const development = await sampleStrategicCases(parent, 833, 8, "development", budget(), excluded);
  assert.ok(development.cases.every(c => !excluded.has(c.group)));
  const learned = await practiceStrategic(parent, training, training.digest, { passes: 8, rate: 0.2, margin: 0.05 }, budget());
  assert.equal(learned.candidate.provenance.method, "search-pairwise-v1"); assert.equal(learned.receipt.providerCalls, 0);
  assert.ok(learned.receipt.errors.length); assert.ok(learned.receipt.updates.length);
  assert.notDeepEqual(learned.candidate.config.value!.weights, parent.config.value!.weights);
  assert.notDeepEqual(learned.candidate.config.value!.weights, training.teacher.weights, "The learner must not copy hand-authored teacher coefficients.");
  assert.equal(JSON.stringify(parent), snapshot); assertComparableSuccessor(parent, learned.candidate);
  const altered = structuredClone(training); altered.cases[0].scores[0].value += 0.1;
  await assert.rejects(parseStrategicBundle(altered, parent, budget()), /custody/);
  await assert.rejects(practiceStrategic(parent, development, development.digest, { passes: 8, rate: 0.2, margin: 0.05 }, budget()), /training/);
  await assert.rejects(practiceStrategic(parent, training, "0".repeat(64), { passes: 8, rate: 0.2, margin: 0.05 }, budget()), /training/);
});
