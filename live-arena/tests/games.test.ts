import test from "node:test";
import assert from "node:assert/strict";
import {
  RULES,
  createGame,
  applyMove,
  legalMoves,
  validateRules,
  botMove,
  replayStepper,
} from "../src/games";
import {
  parseDecision,
  supportedEfforts,
  publicAgent,
  validateEndpoint,
} from "../src/models";
import { replay } from "../src/records";

test("incremental replay has exact state parity and rejects moves after terminal state", () => {
  const lines = [
    ["e2e4", "a7a6", "e4e5", "d7d5", "e5d6"],
    ["g1f3", "g8f6", "e2e3", "e7e6", "f1e2", "f8e7", "e1g1"],
    ["g1f3", "g8f6", "f3g1", "f6g8", "g1f3", "g8f6", "f3g1", "f6g8"],
    ["f2f3", "e7e5", "g2g4", "d8h4"],
  ];
  for (const moves of lines) {
    let state = createGame(RULES.chess);
    const step = replayStepper(RULES.chess);
    assert.throws(() => step("e2e5"));
    for (const move of moves) {
      state = applyMove(state, move);
      const result = step(move);
      assert.deepEqual(result, state);
      result.moves.length = 0; // Exposed snapshots cannot mutate the cursor.
    }
    if (state.over) assert.throws(() => step("a2a3"));
  }
});

test("chess checks legal movement and checkmate", () => {
  let s = createGame(RULES.chess);
  assert.equal(legalMoves(s).length, 20);
  assert.throws(() => applyMove(s, "e2e5"));
  for (const m of ["f2f3", "e7e5", "g2g4", "d8h4"]) s = applyMove(s, m);
  assert.equal(s.reason, "Checkmate");
  assert.equal(s.winner, 1);
  assert.deepEqual(legalMoves(s), []);
});
test("chess castling, en passant and threefold repetition", () => {
  let s = createGame(RULES.chess);
  for (const m of ["e2e4", "a7a6", "e4e5", "d7d5"]) s = applyMove(s, m);
  assert(legalMoves(s).includes("e5d6"));
  s = applyMove(s, "e5d6");
  assert.equal(s.cells[27], "");
  s = createGame(RULES.chess);
  for (const m of ["g1f3", "g8f6", "e2e3", "e7e6", "f1e2", "f8e7"])
    s = applyMove(s, m);
  assert(legalMoves(s).includes("e1g1"));
  s = applyMove(s, "e1g1");
  assert.equal(s.cells[62], "wk");
  s = createGame(RULES.chess);
  for (const m of [
    "g1f3",
    "g8f6",
    "f3g1",
    "f6g8",
    "g1f3",
    "g8f6",
    "f3g1",
    "f6g8",
  ])
    s = applyMove(s, m);
  assert.equal(s.reason, "Threefold repetition");
});
test("checkers forces full capture chains and removes captured pieces", () => {
  let s = createGame(RULES.checkers);
  s.cells.fill("");
  s.cells[40] = "w";
  s.cells[33] = "b";
  s.cells[19] = "b";
  assert.deepEqual(legalMoves(s), ["a6-c4-e2"]);
  assert.throws(() => applyMove(s, "a6-c4"));
  s = applyMove(s, "a6-c4-e2");
  assert.equal(s.cells[33], "");
  assert.equal(s.cells[19], "");
  assert.equal(s.winner, 0);
});
test("checkers promotion ends capture turn under English rules", () => {
  let s = createGame(RULES.checkers);
  s.cells.fill("");
  s.cells[17] = "w";
  s.cells[10] = "b";
  s.cells[12] = "b";
  assert.deepEqual(legalMoves(s), ["b3-d1"]);
  s = applyMove(s, "b3-d1");
  assert.equal(s.cells[3], "W");
  assert.equal(s.turn, 1);
});
test("connect four gravity, column capacity and victory", () => {
  let s = createGame(RULES.connect4);
  for (const m of ["0", "1", "0", "1", "0", "1", "0"]) s = applyMove(s, m);
  assert.equal(s.winner, 0);
  assert.equal(s.reason, "4 in a row");
  s = createGame(RULES.connect4);
  for (let i = 0; i < 6; i++) s = applyMove(s, "2");
  assert(!legalMoves(s).includes("2"));
});
test("tic tac toe diagonal win and full-board draw", () => {
  let s = createGame(RULES.tictactoe);
  for (const m of ["0", "1", "4", "2", "8"]) s = applyMove(s, m);
  assert.equal(s.winner, 0);
  s = createGame(RULES.tictactoe);
  for (const m of ["0", "4", "8", "1", "7", "6", "2", "5", "3"])
    s = applyMove(s, m);
  assert.equal(s.over, true);
  assert.equal(s.winner, null);
});
test("creator rejects unsafe bounds and built-ins cannot be overridden", () => {
  assert.throws(() =>
    validateRules({
      kind: "custom",
      name: "bad",
      rows: 100000,
      cols: 3,
      connect: 3,
      gravity: false,
    }),
  );
  assert.deepEqual(validateRules({ ...RULES.chess, rows: 100 }), RULES.chess);
  const r = validateRules({
    kind: "custom",
    name: "My game",
    rows: 5,
    cols: 5,
    connect: 4,
    gravity: false,
  });
  assert.equal(legalMoves(createGame(r)).length, 25);
});
test("tactician takes immediate wins and blocks opponent wins", () => {
  let s = createGame(RULES.tictactoe);
  for (const m of ["0", "3", "1", "4"]) s = applyMove(s, m);
  assert.equal(botMove(s), "2");
  s = createGame(RULES.tictactoe);
  for (const m of ["0", "4", "1"]) s = applyMove(s, m);
  assert.equal(botMove(s), "2");
});
test("all built-in bots play legal games through terminal states", () => {
  for (const key of Object.keys(RULES)) {
    let s = createGame(RULES[key]);
    for (let i = 0; i < 400 && !s.over; i++) {
      const before = JSON.stringify(s);
      const move = botMove(s, "random");
      const next = applyMove(s, move);
      assert.equal(JSON.stringify(s), before);
      s = next;
    }
    assert(s.over);
  }
});
test("provider decisions reject malformed and illegal moves", () => {
  assert.deepEqual(
    parseDecision('```json\n{"move":"e2e4","comment":"Center"}\n```', ["e2e4"]),
    { move: "e2e4", comment: "Center" },
  );
  assert.throws(() => parseDecision('{"move":"e2e8"}', ["e2e4"]));
  assert.throws(() => parseDecision("<script>x</script>", ["e2e4"]));
});
test("reasoning selector only enables advertised levels", () => {
  assert.deepEqual(supportedEfforts({ id: "x", name: "x" }), ["default"]);
  assert.deepEqual(
    supportedEfforts({
      id: "x",
      name: "x",
      reasoning: {
        supported_efforts: ["high", "low", "none"],
        mandatory: true,
      },
    }),
    ["default", "high", "low"],
  );
});
test("public contender drops credentials and endpoints", () => {
  const p = publicAgent({
    name: "A",
    kind: "harness",
    model: "m",
    effort: "high",
    strategy: "s",
    endpoint: "https://private.example",
    key: "SECRET",
  });
  assert(!JSON.stringify(p).includes("SECRET"));
  assert(!("endpoint" in p));
});
test("harness endpoints disallow userinfo, query credentials and insecure non-loopback", () => {
  assert.throws(() => validateEndpoint("http://example.com"));
  assert.throws(() => validateEndpoint("https://user:pass@example.com"));
  assert.throws(() => validateEndpoint("https://example.com?key=secret"));
  assert.equal(
    validateEndpoint("http://127.0.0.1:8765/move").pathname,
    "/move",
  );
});
test("replay validates moves and strips untrusted extra fields", () => {
  const a = {
    name: "A",
    kind: "bot",
    model: "random",
    effort: "default",
    strategy: "",
  };
  const r = {
    schema: "builderwars.exhibition.v1",
    id: "test",
    createdAt: "2026-09-04",
    rules: RULES.chess,
    agents: [a, a],
    events: [
      {
        ply: 1,
        seat: 0,
        move: "e2e4",
        comment: "",
        elapsed: 3,
        model: "builtin/random",
        tokens: null,
        cost: 0,
        label: "e4",
        key: "SECRET",
      },
    ],
    status: "Paused",
    key: "SECRET",
  };
  assert.equal(replay(r).state.moves.length, 1);
  assert.equal(
    replay({ ...r, events: [{ ...r.events[0], label: "false label" }] }).record
      .events[0].label,
    "e4",
  );
  assert(!JSON.stringify(replay(r).record).includes("SECRET"));
  assert.throws(() =>
    replay({ ...r, events: [{ ...r.events[0], move: "e2e6" }] }),
  );
  assert.throws(() => replay({ ...r, events: [{ ...r.events[0], seat: 1 }] }));
});
