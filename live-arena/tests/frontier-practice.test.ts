import test from "node:test";
import assert from "node:assert/strict";
import { RULES, createGame, replayStepper } from "../src/runtime";
import { WorkBudget } from "../src/self-improvement";
import { localBaseline } from "../scripts/frontier-store";
import { positionGroup, samplePartitions, validateIsolation, exposedGroups, parseBundle, type CaseBundle } from "../src/frontier-cases";
import { practice, scoreCases, assertPracticeCandidate } from "../src/frontier-practice";

const budget = () => new WorkBudget(2000000, 300000);
function state(moves: string[], game = RULES.tictactoe) {
  const step = replayStepper(game); return moves.reduce((_s, move) => step(move), createGame(game));
}
test("grouping merges board symmetries and equivalent histories but preserves gravity orientation", async () => {
  const a = state(["0", "4", "1"]), reflected = state(["2", "4", "1"]), reordered = state(["1", "4", "0"]), rotated = state(["2", "4", "5"]);
  assert.equal(await positionGroup(a), await positionGroup(reflected));
  assert.equal(await positionGroup(a), await positionGroup(reordered));
  assert.equal(await positionGroup(a), await positionGroup(rotated));
  const c4 = state(["0", "6", "1"], RULES.connect4), mirror = state(["6", "0", "5"], RULES.connect4);
  assert.equal(await positionGroup(c4), await positionGroup(mirror));
  const upsideDown = structuredClone(c4); upsideDown.cells.reverse();
  assert.notEqual(await positionGroup(c4), await positionGroup(upsideDown));
});

test("deterministic partitions exclude public prefixes and never share final target groups", async () => {
  const source = await localBaseline(RULES.tictactoe), counts = { training: 24, development: 12, admission: 12, attempts: 2 };
  const first = await samplePartitions(source, 713, counts, budget());
  assert.deepEqual(first, await samplePartitions(source, 713, counts, budget()));
  await validateIsolation(first.training, first.development, first.admission, budget());
  // Every legal history shares the empty opening. Isolation is of evaluated
  // target groups, not of every position in a trajectory (which is impossible).
  const opening = await positionGroup(createGame(RULES.tictactoe));
  for (const bundle of [first.training, first.development, ...first.admission]) {
    assert.ok((await exposedGroups(bundle, budget())).has(opening));
    assert.ok(bundle.cases.every(c => c.group !== opening));
  }
  const exposed = new Set([...(await exposedGroups(first.training, budget())), ...(await exposedGroups(first.development, budget()))]);
  assert.ok(first.admission.every(b => b.cases.every(c => !exposed.has(c.group))));
  await assert.rejects(validateIsolation(first.training, first.development, [first.admission[0], first.admission[0]], budget()), /reused/);
  await assert.rejects(validateIsolation(first.training, first.training, first.admission, budget()), /partition/);
  const changed = structuredClone(first.training); changed.cases[0].sourceError = !changed.cases[0].sourceError;
  await assert.rejects(parseBundle(changed, source, budget()), /custody/);
  await assert.rejects(samplePartitions(source, 713, counts, new WorkBudget(1)), /budget/);
});

test("play/error/practice changes numeric preferences without network, other config or old policy provenance", async () => {
  const source = await localBaseline(RULES.connect4), original = JSON.stringify(source);
  const data = await samplePartitions(source, 713, { training: 24, development: 12, admission: 12, attempts: 1 }, budget());
  const previousFetch = globalThis.fetch; let calls = 0;
  globalThis.fetch = async () => { calls++; throw Error("Provider must never be called by this learner."); };
  try {
    const options = { passes: 8, rate: 0.2, margin: 0.1 };
    const learned = await practice(source, data.training, data.training.digest, options, budget());
    assert.notDeepEqual(learned.candidate.config.value!.weights, source.config.value!.weights);
    assert.equal(learned.candidate.provenance.method, "tactical-pairwise-v1");
    assert.equal(learned.receipt.providerCalls, 0); assert.equal(learned.receipt.promotion, "not-authorized");
    assert.ok(learned.receipt.errors.length && learned.receipt.updates.length);
    const errors = (report: typeof learned.receipt.before) => report.seats.reduce((n, s) => n + s.missedWins + s.avoidableLosses, 0);
    assert.ok(errors(learned.receipt.after) < errors(learned.receipt.before), "This known public fixture must actually reduce training errors, not merely change numbers.");
    assertPracticeCandidate(source, learned.candidate, data.training.digest);
    assert.equal(JSON.stringify(source), original); assert.equal(calls, 0);
    const second = await practice(source, data.training, data.training.digest, options, budget());
    assert.deepEqual(learned, second);
    const development = await scoreCases(learned.candidate, data.development, budget());
    assert.equal(development.partition, "development");
    await assert.rejects(practice(source, data.development, data.development.digest, options, budget()), /training partition/);
    await assert.rejects(practice(source, data.admission[0], data.admission[0].digest, options, budget()), /training partition/);
    await assert.rejects(practice(source, data.training, "0".repeat(64), options, budget()), /training partition/);
    await assert.rejects(practice(source, data.training, data.training.digest, { ...options, rate: NaN }, budget()), /settings/);
    await assert.rejects(practice(source, data.training, data.training.digest, options, new WorkBudget(1)), /budget/);
  } finally { globalThis.fetch = previousFetch; }
});
