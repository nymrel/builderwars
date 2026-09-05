import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, readdir, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { RULES, createGame, legalMoves } from "../src/runtime";
import { baselinePolicy, sealPolicy, evaluationPlan, evaluateCandidate, WorkBudget } from "../src/self-improvement";
import { learnedMove, runTraining, parseMoveInput, saveChampion } from "../scripts/self-improve";

test("local trained adapter verifies complete history, rules, turn and legal list", async () => {
  const parent = await baselinePolicy(RULES.tictactoe), state = createGame(parent.rules);
  const request = { game: state.rules, moves: [], turn: state.turn, position: state.cells, legalMoves: legalMoves(state) };
  const result = await learnedMove(request, parent);
  assert(request.legalMoves.includes(result.move));
  assert.equal(result.policyDigest, parent.digest);
  assert.equal(result.model, `local-learned-value/${parent.digest}`);
  assert.deepEqual(await learnedMove(request, parent), result);
  for (const changed of [
    { ...request, turn: 1 }, { ...request, moves: ["0", "0"] },
    { ...request, position: Array(9).fill("w") }, { ...request, legalMoves: ["0"] },
    { ...request, game: RULES.chess },
  ]) await assert.rejects(learnedMove(changed, parent));
});

test("CLI run retains immutable parent on rejection and never reuses a run directory", async () => {
  const root = await mkdtemp(join(tmpdir(), "builderwars-improvement-test-"));
  try {
    const args = ["--game", "tictactoe", "--episodes", "2", "--pairs", "16", "--max-plies", "3", "--seed", "42", "--output", root];
    const first = await runTraining(args), second = await runTraining(args);
    assert.notEqual(first.output, second.output);
    assert.notEqual(first.plan, second.plan);
    assert.equal(first.decision, "retain");
    assert.equal(first.champion, first.parent);
    assert.equal(first.training.completed, 0);
    const files = await readdir(first.output);
    for (const f of ["plan.json", "source.json", "incumbent.json", "candidate.json", "evaluation-spent.json", "evaluation.json", "champion.json", "rollback.json", "training-games.jsonl", "receipt.json"])
      assert(files.includes(f), f);
    const config = JSON.parse(await readFile(join(first.output, "training-config.json"), "utf8"));
    const episodes = (await readFile(join(first.output, "training-games.jsonl"), "utf8")).trim().split("\n").map(line => JSON.parse(line));
    assert(episodes.every(e => !config.excludedSeeds.includes(e.seed)));
  } finally { await rm(root, { recursive: true, force: true }); }
});

test("budget failure leaves evidence but no champion or successful receipt", async () => {
  const root = await mkdtemp(join(tmpdir(), "builderwars-improvement-failure-"));
  try {
    await assert.rejects(runTraining(["--game", "tictactoe", "--episodes", "20", "--pairs", "16", "--nodes", "1", "--output", root]), /without promotion/);
    const [run] = await readdir(root), files = await readdir(join(root, run));
    assert(files.includes("failure.json"));
    assert(!files.includes("champion.json"));
    assert(!files.includes("receipt.json"));
    const failure = JSON.parse(await readFile(join(root, run, "failure.json"), "utf8"));
    assert.equal(failure.decision, "retain");
  } finally { await rm(root, { recursive: true, force: true }); }
});

test("bridge wrapper and plain JSON parse identically; oversized input is rejected", () => {
  const request = { game: RULES.tictactoe, moves: [] };
  const json = JSON.stringify(request);
  assert.deepEqual(parseMoveInput(json), request);
  assert.deepEqual(parseMoveInput("Fixed bridge instructions, not executable.\n" + json), request);
  assert.throws(() => parseMoveInput("a".repeat(64001)), /large/);
  assert.throws(() => parseMoveInput("not json"));
});

test("positive gate and write-once champion/rollback path use an explicit synthetic policy fixture", async () => {
  // Deliberately bad and good fixed coefficients test gate plumbing, NOT training uplift.
  const baseline = await baselinePolicy(RULES.tictactoe), { digest: _, ...body } = baseline;
  const weights = Array(22).fill(0); weights[16] = 8; weights[13] = -8;
  const parent = await sealPolicy({ ...body, weights });
  const candidate = await sealPolicy({ ...body, weights: weights.map(w => -w), parent: parent.digest, revision: 1,
    training: { seed: 1, episodes: 1, completed: 1, capped: 0 } });
  const plan = await evaluationPlan(parent, 9090, 512, 9);
  const result = await evaluateCandidate(parent, candidate, plan, new WorkBudget());
  assert.equal(result.decision, "promote");
  assert(result.lowerGainBound !== null && result.lowerGainBound > plan.minimumGain);
  const root = await mkdtemp(join(tmpdir(), "builderwars-promotion-test-"));
  try {
    const champion = await saveChampion(root, parent, candidate, result);
    assert.equal(champion.digest, candidate.digest);
    const rollback = JSON.parse(await readFile(join(root, "rollback.json"), "utf8"));
    assert.equal(rollback.previous, parent.digest); assert.equal(rollback.promoted, true);
    await assert.rejects(saveChampion(root, parent, candidate, result), /EEXIST/);
  } finally { await rm(root, { recursive: true, force: true }); }
});
