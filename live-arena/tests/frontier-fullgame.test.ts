import test from "node:test";
import assert from "node:assert/strict";
import { RULES, createGame, replayStepper } from "../src/runtime";
import { WorkBudget } from "../src/self-improvement";
import { localBaseline } from "../scripts/frontier-store";
import { createVersion, identityKey } from "../src/frontier-version";
import { FULLGAME_GATE, FULLGAME_PROTOCOL, FULLGAME_OPPONENTS, fullgameBlock, fullgameOpening, fullgameOpponentMove, summarizeFullgames, lowerBound, gameFamily, type FullgameBlock, type FullgameRow } from "../src/frontier-fullgame";

const parentId = "0".repeat(64), candidateId = "1".repeat(64);
// Synthetic statistics fixtures only, never playing-strength evidence.
function statisticalBlock(seed: number): FullgameBlock {
  const games: FullgameRow[] = FULLGAME_OPPONENTS.flatMap(opponent => [0, 1].flatMap(seat => [parentId, candidateId].map(version => ({
    version, opponent, seat, opening: [], moves: [], exit: "complete" as const, reason: "synthetic-statistics-fixture", winner: (version === candidateId ? seat : 1 - seat), score: version === candidateId ? 1 : 0,
    decisions: 3, assessed: 3, illegal: 0, winOpportunities: 0, missedWins: 0, defenseOpportunities: 0, avoidableLosses: 0,
    inferenceNodes: 20, opponentNodes: 30, graderNodes: 30, milliseconds: 1, maxDecisionMilliseconds: 0.2, providerCalls: 0 as const,
  }))));
  return { schema: FULLGAME_PROTOCOL, seed, parent: parentId, candidate: candidateId, games };
}
test("confidence uses seed blocks and range two for paired gains, not eight times the sample size", () => {
  const alpha = 0.0125 / 10, n = 64;
  assert.equal(lowerBound(0.5, n, alpha, 2), 0.5 - Math.sqrt(2 * Math.log(1 / alpha) / n));
  const blocks = Array.from({ length: n }, (_, i) => statisticalBlock(i));
  const result = summarizeFullgames(blocks, { ...FULLGAME_GATE, trials: n }, "development");
  assert.equal(result.lowerGain, lowerBound(1, n, alpha, 2));
  assert.equal(result.qualification, "pass"); assert.equal(result.promotion, "not-authorized");
  assert.equal(result.groups.length, 4); assert.equal(result.completedGames, 8 * n);
  assert.equal(result.work[0].inferenceNodes, 4 * n * 20);
  assert.throws(() => lowerBound(0, 0, alpha, 2), /count/);
  assert.throws(() => lowerBound(0, n, NaN, 2), /confidence/);
});
test("caps, tactical errors and seat regressions veto a favorable aggregate; incomplete pairs never pass", () => {
  const gate = { ...FULLGAME_GATE, trials: 64 }, blocks = Array.from({ length: 64 }, (_, i) => statisticalBlock(i));
  const capped = structuredClone(blocks); capped[0].games[0].exit = "capped"; capped[0].games[0].score = null;
  const failed = summarizeFullgames(capped, gate, "admission");
  assert.equal(failed.meanGain, null); assert.equal(failed.qualification, "fail"); assert.equal(failed.capped, 1);
  const tactic = structuredClone(blocks); const bad = tactic[0].games.find(g => g.version === candidateId)!;
  bad.defenseOpportunities = 1; bad.avoidableLosses = 1;
  assert.ok(summarizeFullgames(tactic, gate, "admission").failures.some(f => f.includes("tactical-error")));
  const regression = structuredClone(blocks);
  for (const block of regression) for (const row of block.games) if (row.seat === 1 && row.opponent === FULLGAME_OPPONENTS[0]) {
    row.winner = row.version === candidateId ? 0 : 1; row.score = row.version === candidateId ? 0 : 1;
  }
  assert.ok(summarizeFullgames(regression, gate, "admission").failures.includes("immediate-tactics-v1/seat1/regression-not-excluded"));
  assert.throws(() => summarizeFullgames(blocks.slice(1), gate, "admission"), /Incomplete/);
  const missing = structuredClone(blocks); missing[0].games.pop();
  assert.throws(() => summarizeFullgames(missing, gate, "admission"), /incomplete/);
  assert.throws(() => summarizeFullgames(blocks, { ...gate, maximumSeatRegression: 0.02 }, "admission"), /thresholds/);
});
test("real paired games preserve opening, versions, both seats, replay outcomes and cancellation", async () => {
  const parent = await localBaseline(RULES.tictactoe, "strategic-value"), config = structuredClone(parent.config);
  config.value!.weights[13] = 1;
  const candidate = await createVersion(config, parent, { method: "search-pairwise-v1", source: "2".repeat(64), identities: [await identityKey(config.runtime)] });
  const block = await fullgameBlock(parent, candidate, 713);
  assert.equal(block.games.length, 8);
  assert.deepEqual(block.games[0].opening, fullgameOpening(RULES.tictactoe, 713));
  for (const game of block.games) {
    let state = createGame(RULES.tictactoe); const step = replayStepper(RULES.tictactoe);
    for (const move of game.moves) state = step(move);
    assert.equal(state.over, true); assert.equal(state.winner, game.winner); assert.equal(state.reason, game.reason);
    assert.deepEqual(game.moves.slice(0, game.opening.length), game.opening);
    assert.equal(game.missedWins, 0); assert.equal(game.avoidableLosses, 0);
    assert.ok(game.inferenceNodes > 0 && game.opponentNodes > 0 && game.graderNodes > 0);
  }
  const aborted = new AbortController(); aborted.abort();
  await assert.rejects(fullgameBlock(parent, candidate, 713, 398, aborted.signal));
  assert.equal(gameFamily(RULES.tictactoe), gameFamily(RULES.connect4));
  assert.notEqual(gameFamily(RULES.tictactoe), gameFamily(RULES.checkers));
  assert.throws(() => gameFamily(RULES.chess), /supports/);
  assert.throws(() => fullgameOpponentMove(createGame(RULES.tictactoe), "random" as any, new WorkBudget(1000)), /opponent/);
});
