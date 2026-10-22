import test from "node:test";
import assert from "node:assert/strict";
import { replay, RULES } from "../src/runtime";
import { makeMatchPackage, unknownDeclarations, readMatchFile } from "../src/match-package";
import { matchLimits } from "../src/resources";
import {
  validateCompetitionPlan, competitionSchedule, playCompetitionMatch, competitionStandings,
  type CompetitionPlan,
} from "../src/local-competition";

const plan: CompetitionPlan = {
  schema: "builderwars.local-competition-plan.v1", id: "test-cup", createdAt: "2026-10-21T00:00:00.000Z",
  agents: [
    { id: "first", name: "First Legal", policy: "first-legal" },
    { id: "random", name: "Seeded Wildcard", policy: "seeded-random" },
    { id: "tactics", name: "Tactician", policy: "tactician" },
  ],
  games: ["tictactoe", "connect4", "nim"], seeds: [20261021, 817263], maxPlies: 42,
};
const clone = <T>(value: T): T => structuredClone(value);
const singleGame: CompetitionPlan = { ...plan, games: ["tictactoe"], seeds: [17] };
function run(p = singleGame) { return competitionSchedule(p).map(fixture => playCompetitionMatch(p, fixture)); }

test("multi-game schedule includes every rival, seed and both seats exactly once", () => {
  const fixtures = competitionSchedule(plan);
  assert.equal(fixtures.length, 36);
  assert.equal(new Set(fixtures.map(f => f.id)).size, 36);
  for (const game of plan.games) for (const seed of plan.seeds) for (const a of plan.agents)
    for (const b of plan.agents) if (a.id !== b.id)
      assert.equal(fixtures.filter(f => f.game === game && f.seed === seed && f.agents[0] === a.id && f.agents[1] === b.id).length, 1);
  const large: CompetitionPlan = { ...plan, id: "a".repeat(32), seeds: [0, 1, 2, 3, 4, 5, 6, 0xffffffff],
    agents: Array.from({ length: 8 }, (_, i) => ({ id: `agent-${i}`, name: `Agent ${i}`, policy: "first-legal" })),
  };
  assert.equal(competitionSchedule(large).length, 1344);
  assert(competitionSchedule(large).every(f => f.id.length <= 80));
});

test("all policies play reproducibly regardless of execution order; standings are per game and balanced", () => {
  const fixtures = competitionSchedule(plan), records = fixtures.map(f => playCompetitionMatch(plan, f));
  for (let i = fixtures.length - 1; i >= 0; i--) assert.deepEqual(playCompetitionMatch(plan, fixtures[i]), records[i]);
  assert(records.every(record => replay(record).state.over));
  const results = competitionStandings(plan, records);
  assert.equal(results.length, 3);
  for (const group of results) {
    assert.equal(group.rows.reduce((sum, row) => sum + row.points, 0), 12);
    for (const row of group.rows) {
      assert.equal(row.played, 8); assert.equal(row.completed, 8); assert.equal(row.capped, 0);
      assert.equal(row.firstSeat, 4); assert.equal(row.secondSeat, 4);
      assert.equal(row.wins + row.draws + row.losses, row.completed);
      assert.equal(row.points, row.wins + row.draws * 0.5);
    }
  }
  assert.deepEqual(competitionStandings(plan, [...records].reverse()), results);
});

test("standings reject missing, duplicated, unknown or altered schedule evidence", () => {
  const records = run();
  assert.throws(() => competitionStandings(singleGame, records.slice(1)), /Missing/);
  const duplicate = clone(records); duplicate[1] = duplicate[0];
  assert.throws(() => competitionStandings(singleGame, duplicate), /duplicated/);
  for (const mutate of [
    (r: typeof records) => { r[0].id = "foreign-game"; },
    (r: typeof records) => { r[0].createdAt = "2026-10-20T00:00:00.000Z"; },
    (r: typeof records) => { r[0].agents[0].name = "Other"; },
    (r: typeof records) => { r[0].agents[0].model = "other"; },
    (r: typeof records) => { r[0].agents[0].strategy = "tactician"; },
    (r: typeof records) => { r[0].agents[0].kind = "harness"; },
    (r: typeof records) => { r[0].agents[0].effort = "high"; },
    (r: typeof records) => { r[0].events[0].model = "other"; },
    (r: typeof records) => { r[0].events[0].cost = 1; },
    (r: typeof records) => { r[0].events[0].elapsed = 1; },
    (r: typeof records) => { r[0].events[0].tokens = 5; },
    (r: typeof records) => { r[0].events[0].comment = "Forged"; },
    (r: typeof records) => { r[0].status = "Invented winner"; },
    (r: typeof records) => { r[0].events[0].move = "900"; },
    (r: typeof records) => { r[0].rules = RULES.connect4; },
  ]) {
    const altered = clone(records); mutate(altered);
    assert.throws(() => competitionStandings(singleGame, altered));
  }
  const wrongFixture = clone(competitionSchedule(singleGame)[0]); wrongFixture.seed++;
  assert.throws(() => playCompetitionMatch(singleGame, wrongFixture), /schedule/);
  const wrongSeat = clone(competitionSchedule(singleGame)[0]); wrongSeat.agents.reverse();
  assert.throws(() => playCompetitionMatch(singleGame, wrongSeat), /schedule/);
});

test("capped matches are void, portable, and cannot masquerade as draws or early exits", () => {
  const cappedPlan = { ...singleGame, maxPlies: 2 }, records = run(cappedPlan);
  assert(records.every(r => r.events.length === 2 && r.status === "Unfinished match" && !replay(r).state.over));
  const standings = competitionStandings(cappedPlan, records);
  for (const row of standings[0].rows) {
    assert.equal(row.played, 4); assert.equal(row.completed, 0); assert.equal(row.capped, 4);
    assert.equal(row.draws, 0); assert.equal(row.points, 0); assert.equal(row.rank, 1);
  }
  const portable = records.map(record => readMatchFile(makeMatchPackage(record, unknownDeclarations(), matchLimits(2, null, true))).parsed.record);
  assert.deepEqual(competitionStandings(cappedPlan, portable), standings);
  const early = clone(records); early[0].events.pop();
  assert.throws(() => competitionStandings(cappedPlan, early), /completion evidence/);
  assert.throws(() => competitionStandings({ ...cappedPlan, maxPlies: 3 }, records), /completion evidence/);
  const falseDraw = clone(records); falseDraw[0].status = "Draw";
  assert.throws(() => competitionStandings(cappedPlan, falseDraw));
});

test("plan admission rejects unsupported, duplicate and unbounded inputs before execution", () => {
  assert.deepEqual(validateCompetitionPlan(plan), plan);
  for (const mutate of [
    (p: any) => { p.schema = "arbitrary"; },
    (p: any) => { p.id = "../escape"; },
    (p: any) => { p.id = "a".repeat(33); },
    (p: any) => { p.createdAt = "yesterday"; },
    (p: any) => { p.createdAt = "2026-02-30T00:00:00.000Z"; },
    (p: any) => { p.agents.pop(); },
    (p: any) => { p.agents = Array(9).fill(p.agents[0]); },
    (p: any) => { p.agents[1].id = p.agents[0].id; },
    (p: any) => { p.agents[1].name = p.agents[0].name; },
    (p: any) => { p.agents[0].policy = "external-command"; },
    (p: any) => { p.agents[0].name = "\nSpoofed"; },
    (p: any) => { p.agents[0].name = "\ud800"; },
    (p: any) => { p.agents[0].name = "Agent \udfff"; },
    (p: any) => { p.agents[0].endpoint = "https://example.com"; },
    (p: any) => { p.games = ["chess"]; },
    (p: any) => { p.games = []; },
    (p: any) => { p.games = ["nim", "nim"]; },
    (p: any) => { p.seeds = []; },
    (p: any) => { p.seeds = Array(9).fill(0); },
    (p: any) => { p.seeds = [0, 0]; },
    (p: any) => { p.seeds = [-1]; },
    (p: any) => { p.seeds = [0x100000000]; },
    (p: any) => { p.seeds = [1.5]; },
    (p: any) => { p.maxPlies = 1; },
    (p: any) => { p.maxPlies = 401; },
    (p: any) => { p.maxPlies = NaN; },
    (p: any) => { p.source = "injected"; },
  ]) {
    const altered = clone(plan); mutate(altered);
    assert.throws(() => validateCompetitionPlan(altered));
  }
  const unicode = clone(plan); unicode.agents[0].name = "Agent 🤖";
  assert.equal(validateCompetitionPlan(unicode).agents[0].name, "Agent 🤖");
  const copy = validateCompetitionPlan(plan); copy.agents[0].name = "Changed"; copy.games.reverse(); copy.seeds.push(7);
  assert.equal(plan.agents[0].name, "First Legal"); assert.equal(plan.games[0], "tictactoe"); assert.equal(plan.seeds.length, 2);
});

test("tied results retain equal ranks and a stable ID order", () => {
  const tiedPlan: CompetitionPlan = { ...singleGame,
    agents: singleGame.agents.map(agent => ({ ...agent, policy: "first-legal" })),
  };
  const rows = competitionStandings(tiedPlan, run(tiedPlan))[0].rows;
  assert.deepEqual(rows.map(row => row.id), ["first", "random", "tactics"]);
  assert.deepEqual(rows.map(row => row.rank), [1, 1, 1]);
  assert.deepEqual(rows.map(row => row.points), [2, 2, 2]);
});
