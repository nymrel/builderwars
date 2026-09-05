import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, rm, readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { validateChessDecision, runChessContest, CHESS_PLAYERS, type ChessDecision, type ChessPort } from "../scripts/frontier-chess";
import { analyzeChess } from "../scripts/chess-engine";
import { createGame, replayStepper, RULES, legalMoves, replay } from "../src/runtime";
const decision: ChessDecision = { move: "e2e4", comment: "Take central space.", requestedModel: "gpt-6-astra", resolvedModel: null,
  identityEvidence: "unreported", inputTokens: null, outputTokens: null, listCostUsd: null, elapsedMilliseconds: 300, toolsUsed: false };
test("frontier chess retains unavailable identity and rejects illegal/fabricated/tool-assisted decisions", () => {
  assert.equal(validateChessDecision(decision, "astra", ["e2e4"]).resolvedModel, null);
  assert.throws(() => validateChessDecision({ ...decision, move: "e2e5" }, "astra", ["e2e4"]), /Illegal/);
  assert.throws(() => validateChessDecision({ ...decision, toolsUsed: true }, "astra", ["e2e4"]), /tool use/);
  assert.throws(() => validateChessDecision({ ...decision, identityEvidence: "provider-response" }, "astra", ["e2e4"]), /identity/);
  assert.throws(() => validateChessDecision({ ...decision, requestedModel: "other" }, "astra", ["e2e4"]), /identity/);
  assert.throws(() => validateChessDecision({ ...decision, listCostUsd: NaN }, "astra", ["e2e4"]), /cost/);
  assert.throws(() => validateChessDecision({ ...decision, outputTokens: -1 }, "astra", ["e2e4"]), /token/);
  assert.throws(() => validateChessDecision({ ...decision, resolvedModel: "gpt-5.4-mini", identityEvidence: "provider-response" }, "astra", ["e2e4"]), /substitution/);
});
test("two synthetic-client games honor shared caps, identity drift and failures without substituted moves", async () => {
  const root = await mkdtemp(join(tmpdir(), "bw-chess-contest-test-"));
  const digest = "0".repeat(64), pin = { file: join(root, "fake-engine"), sha256: digest, name: "synthetic-test-engine" };
  const services = { source: async () => digest, binaryDigest: async () => digest,
    analyze: (async (_pin, history) => {
      let state = createGame(RULES.chess); const step = replayStepper(RULES.chess);
      for (const move of history) state = step(move);
      return { lines: [{ rank: 1, score: { kind: "cp", value: 0 }, moves: [legalMoves(state)[0]] }] };
    }) as typeof analyzeChess };
  const port: ChessPort = async (player, prompt) => ({ ...decision, requestedModel: CHESS_PLAYERS[player].model,
    move: /Legal UCI moves: (\S+)/.exec(prompt)![1] });
  try {
    const result = await runChessContest(pin, join(root, "capped"), port, { maxCalls: 4 }, services);
    assert.equal(result.providerAttempts, 4); assert.equal(result.acceptedDecisions, 4);
    assert.deepEqual(result.games.map(g => [g.plies, g.exit, g.winner]), [[2, "capped", null], [2, "capped", null]]);
    assert.equal(result.independentModelIdentity, false); assert.equal(result.providerWeightTraining, false);
    const record = JSON.parse(await readFile(join(root, "capped", "game-1.json"), "utf8"));
    assert.equal(replay(record).state.moves.length, 2);
    const seen = new Set<string>();
    const drift: ChessPort = async (player, prompt, ms) => {
      const reply = await port(player, prompt, ms);
      if (seen.has(player)) return { ...reply, resolvedModel: "changed-model", identityEvidence: "client-reported" };
      seen.add(player); return reply;
    };
    const changed = await runChessContest(pin, join(root, "drift"), drift, { maxCalls: 8 }, services);
    assert.equal(changed.acceptedDecisions, 4); assert.equal(changed.providerAttempts, 6);
    assert.ok(changed.games.every(g => g.exit === "failed" && g.plies === 2 && g.winner === null));
    const failed = await runChessContest(pin, join(root, "failed"), async () => { throw Error("Synthetic client failure"); }, { maxCalls: 4 }, services);
    assert.equal(failed.providerAttempts, 2); assert.equal(failed.acceptedDecisions, 0);
    assert.ok(failed.games.every(g => g.plies === 0 && g.winner === null));
    await assert.rejects(runChessContest(pin, join(root, "capped"), port, {}, services), /EEXIST/);
  } finally { await rm(root, { recursive: true, force: true }); }
});
