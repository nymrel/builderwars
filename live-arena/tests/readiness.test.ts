import test from "node:test";
import assert from "node:assert/strict";
import {
  buildPosition,
  classifyReadinessFailure,
  READINESS_SUITES,
  runReadinessCheck,
  type ReadinessDecider,
} from "../src/readiness";
import { legalMoves } from "../src/runtime";
import { parseDecision, type Agent } from "../src/models";

const harnessAgent = (overrides: Partial<Agent> = {}): Agent => ({
  name: "Test Harness",
  kind: "harness",
  model: "test-model",
  effort: "default",
  strategy: "",
  endpoint: "https://harness.example/move",
  key: "SECRET-KEY",
  ...overrides,
});

const validDecider: ReadinessDecider = async (state) => ({
  move: legalMoves(state)[0],
  model: "stub/valid",
  elapsed: 12,
});

const invalidReplyDecider: ReadinessDecider = async (state) => {
  const { move } = parseDecision("definitely not a move object", legalMoves(state));
  return { move, model: "stub/invalid", elapsed: 8 };
};

const timeoutDecider: ReadinessDecider = (state, agent, signal) =>
  new Promise((_, reject) => {
    signal.addEventListener("abort", () => reject(signal.reason), { once: true });
  });

const connectionErrorDecider: ReadinessDecider = async () => {
  throw Error("Harness returned 503. Check its connection, origin permission and local token.");
};

test("every readiness suite is ten unique, open, engine-legal positions", () => {
  for (const suite of Object.values(READINESS_SUITES)) {
    assert.equal(suite.sequences.length, 10, suite.id);
    const ids = new Set<string>();
    suite.sequences.forEach((sequence, index) => {
      const { id, state } = buildPosition(suite.id, index);
      ids.add(id);
      assert.match(id, new RegExp(`^${suite.id}-[0-9]{2}$`));
      assert.equal(state.over, false, `${id} must not be finished`);
      const legal = legalMoves(state);
      assert.ok(legal.length >= 1, `${id} must have a move available`);
      assert.deepEqual(state.moves, sequence, `${id} must replay exactly`);
      if (suite.id === "nim")
        for (const move of legal) assert.doesNotThrow(() => JSON.parse(move));
    });
    assert.equal(ids.size, 10, suite.id);
  }
});

test("position building is deterministic across calls", () => {
  for (const suiteId of ["tictactoe", "nim"] as const) {
    for (const index of [0, 4, 9]) {
      const first = buildPosition(suiteId, index);
      const second = buildPosition(suiteId, index);
      assert.equal(first.id, second.id);
      assert.deepEqual(first.state.cells, second.state.cells);
      assert.deepEqual(legalMoves(first.state), legalMoves(second.state));
    }
  }
});

test("buildPosition rejects unknown suites and out-of-range positions", () => {
  assert.throws(() => buildPosition("chess", 0), /tic-tac-toe or Nim/);
  assert.throws(() => buildPosition("tictactoe", 10));
  assert.throws(() => buildPosition("tictactoe", -1));
});

test("a healthy contender passes every position with a credential-free receipt", async () => {
  const receipt = await runReadinessCheck({
    agent: harnessAgent(),
    suiteId: "nim",
    decider: validDecider,
  });
  const text = JSON.stringify(receipt);
  assert.doesNotMatch(text, /SECRET-KEY|harness\.example/);
  assert.equal(receipt.schema, "builderwars.readiness.receipt.v1");
  assert.equal(receipt.suite.id, "nim");
  assert.equal(receipt.suite.oneReplyPerPosition, true);
  assert.equal(receipt.summary.positions, 10);
  assert.equal(receipt.summary.valid, 10);
  assert.equal(receipt.summary.invalidReply, 0);
  assert.equal(receipt.summary.timeout, 0);
  assert.equal(receipt.summary.connectionError, 0);
  assert.equal(receipt.summary.skipped, 0);
  assert.ok(!("key" in receipt.contender));
  assert.ok(!("endpoint" in receipt.contender));
  assert.equal(receipt.contender.name, "Test Harness");
  for (const position of receipt.positions) {
    assert.equal(position.outcome, "valid");
    assert.ok(position.replyMove && position.legalMoves.includes(position.replyMove));
    assert.equal(position.reportedModel, "stub/valid");
    assert.ok(receipt.notes.some((note) => note.includes("no ranking")));
  }
});

test("the receipt summary always accounts for every position", async () => {
  for (const suiteId of ["tictactoe", "nim"] as const) {
    const receipt = await runReadinessCheck({
      agent: harnessAgent(),
      suiteId,
      decider: validDecider,
    });
    const { valid, invalidReply, timeout, connectionError, skipped, positions } = receipt.summary;
    assert.equal(valid + invalidReply + timeout + connectionError + skipped, positions);
  }
});

test("an illegal or unreadable reply is classified, never retried or replaced", async () => {
  const receipt = await runReadinessCheck({
    agent: harnessAgent(),
    suiteId: "tictactoe",
    decider: invalidReplyDecider,
  });
  assert.equal(receipt.summary.invalidReply, 10);
  assert.equal(receipt.summary.valid, 0);
  for (const position of receipt.positions) {
    assert.equal(position.outcome, "invalid-reply");
    assert.equal(position.replyMove, null);
    assert.match(position.detail, /no retry was sent/);
  }
});

test("no reply within the time cap is classified as a timeout, not a loss", async () => {
  const receipt = await runReadinessCheck({
    agent: harnessAgent(),
    suiteId: "tictactoe",
    timeCapMs: 60,
    decider: timeoutDecider,
  });
  assert.equal(receipt.summary.timeout, 10);
  for (const position of receipt.positions) {
    assert.equal(position.outcome, "timeout");
    assert.match(position.detail, /latency evidence, not strategy evidence/);
    assert.ok(position.latencyMs !== null && position.latencyMs < 5000);
  }
});

test("infrastructure failures are classified separately from invalid replies", async () => {
  const receipt = await runReadinessCheck({
    agent: harnessAgent(),
    suiteId: "tictactoe",
    decider: connectionErrorDecider,
  });
  assert.equal(receipt.summary.connectionError, 10);
  assert.equal(receipt.summary.invalidReply, 0);
  for (const position of receipt.positions)
    assert.match(position.detail, /Harness returned 503/);
});

test("human seats are rejected before any request is built", async () => {
  await assert.rejects(
    () =>
      runReadinessCheck({
        agent: harnessAgent({ kind: "human" }),
        suiteId: "tictactoe",
        decider: validDecider,
      }),
    /Human seats/,
  );
});

test("unknown suites are rejected before any position runs", async () => {
  await assert.rejects(
    () => runReadinessCheck({ agent: harnessAgent(), suiteId: "chess", decider: validDecider }),
    /tic-tac-toe or Nim/,
  );
});

test("stopping the check marks the run honestly as skipped, never valid", async () => {
  const external = new AbortController();
  let calls = 0;
  const decider: ReadinessDecider = async (state, agent, signal) => {
    calls++;
    if (calls === 1) {
      external.abort();
      throw new DOMException("Aborted", "AbortError");
    }
    return { move: legalMoves(state)[0], model: null, elapsed: 1 };
  };
  const receipt = await runReadinessCheck({
    agent: harnessAgent(),
    suiteId: "tictactoe",
    signal: external.signal,
    decider,
  });
  assert.equal(receipt.summary.valid, 0);
  assert.equal(receipt.summary.skipped, 10);
  for (const position of receipt.positions) assert.equal(position.outcome, "skipped");
});

test("onPosition reports progress incrementally with bounds", async () => {
  const seen: { id: string; index: number; total: number }[] = [];
  await runReadinessCheck({
    agent: harnessAgent(),
    suiteId: "nim",
    decider: validDecider,
    onPosition: (result, index, total) => seen.push({ id: result.id, index, total }),
  });
  assert.equal(seen.length, 10);
  assert.deepEqual(seen.map((entry) => entry.index), [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]);
  assert.ok(seen.every((entry) => entry.total === 10));
});

test("failure classification maps each playtest failure family to one class", () => {
  const timeout = new DOMException("timed out", "TimeoutError");
  assert.equal(classifyReadinessFailure(timeout).outcome, "timeout");
  assert.equal(classifyReadinessFailure(new DOMException("Aborted", "AbortError")).outcome, "timeout");
  assert.equal(
    classifyReadinessFailure(
      Error("Illegal or unreadable move. Match paused; no replacement move was played."),
    ).outcome,
    "invalid-reply",
  );
  assert.equal(classifyReadinessFailure(Error("Harness returned 503.")).outcome, "connection-error");
  assert.equal(classifyReadinessFailure("network down").outcome, "connection-error");
  assert.ok(classifyReadinessFailure(Error("x".repeat(900))).detail.length <= 300);
});

test("the classifier's contract is pinned to the referee validator message", () => {
  assert.throws(() => parseDecision("garbage with no legal move", ["0", "1", "2"]), /Illegal or unreadable move/);
  assert.equal(parseDecision('{"move":"1"}', ["0", "1", "2"]).move, "1");
});
