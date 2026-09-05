import test from "node:test";
import assert from "node:assert/strict";
import { RULES, createGame, applyMove } from "../src/runtime";
import { isExhibitionLimit, isRuleComplete } from "../src/outcome";
import { freeAcademyRecipe } from "../src/academy";
import { summarizeSeries, type SeriesAttempt } from "../src/evaluation";

function attempt(moves = ["0", "1", "0", "1", "0", "1", "0"]): SeriesAttempt {
  return { exit: "finished", record: {
    schema: "builderwars.exhibition.v1", id: "practice", createdAt: "2026-09-05T00:00:00Z",
    rules: RULES.connect4, status: "Untrusted win label",
    agents: freeAcademyRecipe().agents,
    events: moves.map((move, i) => ({ ply: i + 1, seat: (i % 2) as 0 | 1, move, label: "", comment: "", model: "builtin/test", elapsed: 100, tokens: null, cost: 0 })),
  } };
}
test("Academy recipes are isolated, bounded and contain only free contenders", () => {
  const first = freeAcademyRecipe();
  first.agents[0].key = "sentinel";
  first.rules.name = "modified";
  const next = freeAcademyRecipe();
  assert.equal(next.rules.name, "Connect Four");
  assert(next.agents.every(a => a.kind === "bot" && !a.key && !a.strategy && !a.endpoint));
  assert.equal(next.games, 2);
  assert.equal(next.moveLimit, 80);
  assert.deepEqual(freeAcademyRecipe(true).rules, { kind: "custom", name: "Academy Three", rows: 3, cols: 4, connect: 3, gravity: true });
});
test("paired wins follow entrant identity across alternating seats", () => {
  const first = attempt(), second = attempt();
  second.record.agents.reverse();
  const s = summarizeSeries([first, second], 2);
  assert.equal(s.completed, 2);
  assert.equal(s.completePairs, 1);
  assert.deepEqual(s.wins, [1, 1]);
  assert.equal(s.acceptedMeanLatency, 100);
  assert.equal(s.acceptedReportedCost, 0);
  assert.equal(s.acceptedReportedTokens, null);
});
test("capped and failed attempts are not draws or completed pairs", () => {
  const cap = attempt(["0", "1"]), failed = attempt([]);
  failed.exit = "failed";
  const s = summarizeSeries([cap, failed], 4);
  assert.equal(s.recorded, 2);
  assert.equal(s.completed, 0);
  assert.equal(s.completePairs, 0);
  assert.equal(s.capped, 1);
  assert.equal(s.failed, 1);
  assert.equal(s.draws, 0);
  assert.deepEqual(s.wins, [0, 0]);
});
test("stopped series preserves partial evidence and leaves remaining games unrecorded", () => {
  const stopped = attempt(["0"]);
  stopped.exit = "stopped";
  const s = summarizeSeries([attempt(), stopped], 10);
  assert.equal(s.completed, 1);
  assert.equal(s.stopped, 1);
  assert.equal(s.recorded, 2);
  assert.equal(s.completePairs, 0);
});
test("missing or overflowing accepted-move usage is unknown, never zero", () => {
  assert.equal(summarizeSeries([], 2).acceptedReportedCost, null);
  const a = attempt();
  a.record.events[0].cost = null;
  assert.equal(summarizeSeries([a], 2).acceptedReportedCost, null);
  a.record.events.forEach(e => { e.cost = Number.MAX_VALUE; e.tokens = Number.MAX_VALUE; });
  const s = summarizeSeries([a], 2);
  assert.equal(s.acceptedReportedCost, null);
  assert.equal(s.acceptedReportedTokens, null);
});
test("a real draw is computed from rules, while illegal evidence fails closed", () => {
  const draw = attempt(["0", "1", "2", "4", "3", "5", "7", "6", "8"]);
  draw.record.rules = RULES.tictactoe;
  assert.equal(summarizeSeries([draw], 2).draws, 1);
  draw.record.events[1].move = "0";
  assert.throws(() => summarizeSeries([draw], 2));
});
test("referee hard safety stop is not a rule-complete draw", () => {
  // Synthetic internal near-cap state isolates the referee's safety-stop contract;
  // it is not a claimed 400-ply game transcript or performance result.
  const state = createGame(RULES.connect4);
  state.moves = Array(399).fill("synthetic prior ply");
  const capped = applyMove(state, "0");
  assert.equal(capped.over, true);
  assert.equal(capped.reason, "400-ply exhibition limit");
  assert.equal(isExhibitionLimit(capped), true);
  assert.equal(isRuleComplete(capped), false);
  assert.equal(isRuleComplete({ over: true, reason: "Stalemate" }), true);
  assert.equal(isRuleComplete({ over: true, reason: "Checkmate" }), true);
  assert.equal(isRuleComplete({ over: false, reason: "" }), false);
});
