import test from "node:test";
import assert from "node:assert/strict";
import { chessPosition, parseEngineLine, analyzeChess, ENGINE_LIMITS } from "../scripts/chess-engine";
import { applyMove } from "../src/runtime";

test("engine inputs are referee-replayed and UCI injection or finished games are rejected", async () => {
  assert.throws(() => chessPosition(["e2e4\nquit"]), /history/);
  assert.throws(() => chessPosition(["e2e5"]), /illegal/);
  assert.throws(() => chessPosition(["f2f3", "e7e5", "g2g4", "d8h4"]), /live position/);
  assert.equal(chessPosition(["e2e4"]).turn, 1);
  await assert.rejects(analyzeChess({ file: "relative.exe", name: "fake", sha256: "0".repeat(64) }, [], ENGINE_LIMITS), /absolute/);
  await assert.rejects(analyzeChess({ file: "relative.exe", name: "fake", sha256: "0".repeat(64) }, [], { ...ENGINE_LIMITS, nodes: 1000001 }), /budget/);
  const cancelled = new AbortController(); cancelled.abort();
  await assert.rejects(analyzeChess({ file: "relative.exe", name: "fake", sha256: "0".repeat(64) }, [], ENGINE_LIMITS, cancelled.signal));
});
test("engine PV lines must be legal and bounded, and scores are not referee adjudications", () => {
  const state = chessPosition([]), row = parseEngineLine("info depth 8 seldepth 10 multipv 1 score cp 23 nodes 20000 nps 100000 pv e2e4 e7e5 g1f3", state)!;
  assert.deepEqual(row.score, { kind: "cp", value: 23 }); assert.equal(row.moves.length, 3);
  assert.equal(parseEngineLine("info depth 8 multipv 1 score cp 23 lowerbound nodes 20000 pv e2e4", state), null);
  assert.equal(parseEngineLine("info string hello", state), null);
  assert.throws(() => parseEngineLine("info depth 8 score cp 23 nodes 20000 pv e2e5", state), /referee/);
  const mate = chessPosition(["f2f3", "e7e5", "g2g4"]);
  assert.deepEqual(parseEngineLine("info depth 1 score mate 1 nodes 100 pv d8h4", mate)!.score, { kind: "mate", value: 1 });
  assert.equal(applyMove(mate, "d8h4").winner, 1);
});
