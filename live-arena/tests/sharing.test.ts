import test from "node:test";
import assert from "node:assert/strict";
import { RULES } from "../src/runtime";
import { makeSetup, encodeSetup, decodeSetup, safeReplay, summarizeMatch } from "../src/sharing";
import type { RecordData } from "../src/records";

function match(): RecordData {
  return {
    schema: "builderwars.exhibition.v1", id: "share-test", createdAt: "2026-09-05T00:00:00Z",
    rules: RULES.connect4, status: "Forged victory for second seat",
    agents: [0, 1].map(i => ({ name: `Contender ${i}`, kind: "openrouter", model: "provider/model", effort: "high", strategy: "PRIVATE PROMPT" })),
    events: ["0", "1", "0", "1", "0", "1", "0"].map((move, i) => ({ ply: i + 1, seat: (i % 2) as 0 | 1, move, label: "", comment: "PRIVATE COMMENT", model: "provider/model", elapsed: 100, tokens: null, cost: null })),
  };
}
test("setup links whitelist public settings and never carry connection material", () => {
  const record = match();
  Object.assign(record.agents[0], { key: "PRIVATE KEY", endpoint: "https://private.example", accountId: "PRIVATE ACCOUNT" });
  const setup = makeSetup(record, 80, 2048);
  const encoded = encodeSetup(setup);
  assert.deepEqual(decodeSetup(encoded), setup);
  assert(!JSON.stringify(setup).includes("PRIVATE"));
  assert(!JSON.stringify(setup).includes("endpoint"));
  assert(!JSON.stringify(setup).includes("accountId"));
  assert.equal(setup.entrants[0].model, "provider/model");
  assert.equal(setup.entrants[0].effort, "high");
});
test("untrusted or oversized setups are rejected before applying settings", () => {
  const setup = makeSetup(match(), 80, 2048);
  assert.throws(() => encodeSetup({ ...setup, start: true }));
  assert.throws(() => encodeSetup({ ...setup, moveLimit: 9999 }));
  assert.throws(() => encodeSetup({ ...setup, rules: { ...setup.rules, rows: 10 } }));
  assert.throws(() => decodeSetup("a".repeat(9000)));
  assert.throws(() => encodeSetup({ ...setup, entrants: [{ ...setup.entrants[0], key: "secret" }, setup.entrants[1]] }));
});
test("harness setup links carry no local model labels, URLs or private prompt", () => {
  const record = match();
  record.agents[0] = { name: "Private display", kind: "harness", model: "private-resource", effort: "private-mode", strategy: "private-prompt" };
  const setup = makeSetup(record, 80, 2048);
  assert.deepEqual(setup.entrants[0], { kind: "harness", model: "", effort: "default" });
  assert(!JSON.stringify(setup).includes("private"));
});
test("public replay and result ignore private text and forged outcome labels", () => {
  const record = match();
  const shared = safeReplay(record);
  assert(!JSON.stringify(shared).includes("PRIVATE"));
  const result = summarizeMatch(record);
  assert.equal(result.title, "Contender 0 wins");
  assert.equal(result.complete, true);
  assert.equal(result.plies, 7);
  assert.equal(result.elapsedMs, 700);
  assert.equal(result.cost, null);
  assert.equal(result.tokens, null);
  assert.match(result.evidence, /not attested/i);
  record.events.pop();
  assert.equal(summarizeMatch(record).complete, false);
  assert.equal(summarizeMatch(record).title, "Unfinished match");
});

test("result totals remain unknown on overflow and entrant declarations stay explicit", () => {
  const record = match();
  record.events.forEach(e => { e.cost = Number.MAX_VALUE; e.tokens = Number.MAX_VALUE; });
  const result = summarizeMatch(record);
  assert.equal(result.cost, null);
  assert.equal(result.tokens, null);
  assert.match(result.entrants[0], /OpenRouter.*high effort \(declared\)/);
  record.agents[0] = { ...record.agents[0], kind: "bot", model: "tactician" };
  assert.equal(summarizeMatch(record).entrants[0], "Built-in · tactician");
});
