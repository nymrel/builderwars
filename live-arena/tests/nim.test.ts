import test from "node:test";
import assert from "node:assert/strict";
import {
  RULES,
  applyMove,
  botMove,
  createGame,
  gamePosition,
  legalMoves,
  moveLabel,
  nimHeaps,
  replayStepper,
  validateRules,
} from "../src/games";
import { replay } from "../src/records";

const take = (heap: number, count: number) => JSON.stringify({ heap, take: count });

test("Nim starts from deterministic heaps and exposes every legal one-heap take", () => {
  const state = createGame(RULES.nim);
  assert.deepEqual(nimHeaps(state), [3, 5, 7]);
  assert.equal(legalMoves(state).length, 15);
  assert.equal(moveLabel(take(1, 4), state), "Heap 2: take 4");
  assert.deepEqual(gamePosition(state), { heaps: [3, 5, 7], to_move: 0 });
});

test("Nim rejects malformed or unavailable takes without mutating state", () => {
  const state = createGame(RULES.nim), before = JSON.stringify(state);
  for (const move of [
    '{"heap":true,"take":1}',
    '{"heap":0,"take":0}',
    '{"heap":0,"take":4}',
    '{"heap":3,"take":1}',
    '{"heap":0,"take":1,"extra":1}',
    "not-json",
  ]) assert.throws(() => applyMove(state, move));
  assert.equal(JSON.stringify(state), before);
});

test("Nim takes the last object to win and replays with the same state", () => {
  let state = createGame({ ...RULES.nim, initialHeaps: [1, 1, 1] });
  const step = replayStepper(state.rules);
  for (const move of [take(0, 1), take(1, 1), take(2, 1)]) {
    state = applyMove(state, move);
    assert.deepEqual(step(move), state);
  }
  assert.equal(state.over, true);
  assert.equal(state.winner, 0);
  assert.equal(state.reason, "took_last_object");
  assert.deepEqual(legalMoves(state), []);
});

test("Nim tactician leaves a zero-XOR reply and replay records preserve its rules", () => {
  const state = createGame(RULES.nim);
  const next = applyMove(state, botMove(state));
  assert.equal(nimHeaps(next).reduce((xor, heap) => xor ^ heap, 0), 0);
  const agent = { name: "Builder", kind: "bot", model: "tactician", effort: "default", strategy: "" } as const;
  const record = replay({
    schema: "builderwars.exhibition.v1",
    id: "nim-local",
    createdAt: "2026-09-08T00:00:00Z",
    rules: { ...RULES.nim, initialHeaps: [1, 1, 1] },
    agents: [agent, agent],
    events: [take(0, 1), take(1, 1), take(2, 1)].map((move, index) => ({
      ply: index + 1,
      seat: (index % 2) as 0 | 1,
      move,
      comment: "local test",
      elapsed: 0,
      model: "builtin/tactician",
      tokens: null,
      cost: 0,
      label: "untrusted",
    })),
    status: "Builder wins",
  });
  assert.equal(record.state.reason, "took_last_object");
  assert.deepEqual(nimHeaps(record.state), [0, 0, 0]);
});

test("Nim setup remains bounded and never mutates the built-in definition", () => {
  for (const initialHeaps of [[], [1, 2], [1, 2, 3], [0, 1, 2], [1, 2, 8], [true, 2, 4], [1, 2, 3, 4, 5]])
    assert.throws(() => validateRules({ ...RULES.nim, initialHeaps }));
  const state = createGame(RULES.nim);
  state.rules.initialHeaps![0] = 7;
  assert.deepEqual(RULES.nim.initialHeaps, [3, 5, 7]);
});
