import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { RULES, createGame, legalMoves, applyMove, nimHeaps, botMove, validateRules, gamePosition } from "../src/games";
import { publicAgent, decide, type Agent } from "../src/models";
import { replay, sealRecord, encodeReplay, decodeReplay, type RecordData } from "../src/records";
import { recordDigest } from "../src/provenance";

const agent: Agent = { name: "Builder A", kind: "harness", model: "declared/model",
  effort: "default", strategy: "Public strategy", key: "SECRET", endpoint: "https://private.example/move",
  provenance: { builderId: "studio/alice", harnessId: "alice/nim", harnessRevision: "a".repeat(40), attestation: "self-declared" } };
function fixture(): RecordData {
  const f = JSON.parse(readFileSync(new URL("./fixtures/nim-exhibition.json", import.meta.url), "utf8"));
  const r: RecordData = { schema: "builderwars.exhibition.v2", id: "nim-fixture", createdAt: "2026-09-05T00:00:00Z",
    rules: { ...RULES.nim, initialHeaps: f.initialHeaps }, agents: [publicAgent(agent), publicAgent({ ...agent,
      name: "Builder B", provenance: { ...agent.provenance!, builderId: "studio/bob", harnessId: "bob/nim" } })],
    events: f.moves.map((move: string, i: number) => ({ move, ply: i+1, seat: i%2 as 0|1,
      label: "", comment: "fixture", elapsed: 0, tokens: null, cost: null, model: "synthetic/harness" })), status: f.reason };
  return sealRecord(r);
}
test("Nim matches the Python referee across small state spaces, both seats and registered seed setups", () => {
  const oracle = JSON.parse(execFileSync(process.env.PYTHON || "python", ["tests/nim_oracle.py"],
    { encoding: "utf8", maxBuffer: 16*1024*1024 }));
  let transitions = 0;
  for (const c of oracle.cases) {
    const s = createGame(RULES.nim);
    s.rules = { ...s.rules, rows: c.heaps.length };
    s.cells = c.heaps.flatMap((h: number) => Array.from({ length: 7 }, (_, i) => i < h ? "o" : ""));
    s.turn = c.seat;
    assert.deepEqual(legalMoves(s).map((m) => JSON.parse(m)), c.moves);
    c.moves.forEach((move: unknown, i: number) => {
      const next = applyMove(s, JSON.stringify(move)), expected = c.after[i];
      assert.deepEqual(nimHeaps(next), expected.state.heaps);
      assert.equal(next.turn, expected.state.to_move);
      assert.equal(next.over, expected.terminal !== null);
      assert.equal(next.winner, expected.terminal?.winner ?? null);
      if (next.over) assert.equal(next.reason, expected.terminal.reason);
      transitions++;
    });
  }
  for (const s of oracle.setups)
    assert.deepEqual(nimHeaps(createGame({ ...RULES.nim, initialHeaps: s.heaps })), s.heaps);
  assert(transitions > 4000);
  console.log(`Nim parity: ${oracle.cases.length} states / ${transitions} transitions / ${oracle.setups.length} seed setups`);
});
test("Nim rejects illegal or malformed moves without mutation and takes last object to win", () => {
  const s = createGame(RULES.nim), before = JSON.stringify(s);
  for (const move of ['{"heap":true,"take":1}', '{"heap":0,"take":0}', '{"heap":0,"take":4}',
    '{"heap":3,"take":1}', '{"heap":0,"take":1.5}', '{"heap":0,"take":1,"extra":1}', "nonsense"])
    assert.throws(() => applyMove(s, move));
  assert.equal(JSON.stringify(s), before);
  const r = replay(fixture());
  assert(r.state.over);
  assert.equal(r.state.winner, 0);
  assert.equal(r.state.reason, "took_last_object");
  assert.deepEqual(legalMoves(r.state), []);
  assert.deepEqual(gamePosition(s), { heaps: [3,5,7], to_move: 0 });
});
test("Nim setup is bounded, copied, and built-in strategy leaves zero XOR", () => {
  for (const initialHeaps of [[], [1,2], [1,2,3], [0,1,2], [1,2,8], [true,2,4], [1,2,3,4,5]])
    assert.throws(() => validateRules({ ...RULES.nim, initialHeaps }));
  const s = createGame(RULES.nim);
  assert.equal(nimHeaps(applyMove(s, botMove(s))).reduce((x,h) => x^h, 0), 0);
  s.rules.initialHeaps![0] = 7;
  assert.deepEqual(RULES.nim.initialHeaps, [3,5,7]);
});
test("v2 binds builder claims, source revision, settings, seat order and moves; never credentials", async () => {
  const record = fixture();
  assert(!JSON.stringify(record).includes("SECRET"));
  assert(!JSON.stringify(record).includes("private.example"));
  const { digest, ...body } = record;
  assert.equal(digest, createHash("sha256").update(JSON.stringify(body)).digest("hex"));
  assert.equal(recordDigest(body), digest);
  for (const change of [
    (r: RecordData) => { r.agents[0].provenance!.builderId = "imposter"; },
    (r: RecordData) => { r.agents[0].provenance!.harnessRevision = "b".repeat(40); },
    (r: RecordData) => { r.agents[0].strategy = "changed"; },
    (r: RecordData) => { r.agents.reverse(); },
    (r: RecordData) => { r.events.pop(); },
    (r: RecordData) => { delete r.digest; },
  ]) { const changed = structuredClone(record); change(changed); assert.throws(() => replay(changed)); }
  const swapped = sealRecord({ ...record, agents: [...record.agents].reverse() });
  assert.notEqual(swapped.digest, record.digest);
  assert.equal(replay(swapped).record.agents[0].provenance?.builderId, "studio/bob");
  assert.deepEqual((await decodeReplay(await encodeReplay(record))).record, record);
});
test("legacy replays remain explicitly unbound; invalid provenance cannot claim authentication", () => {
  const old = { ...fixture(), schema: "builderwars.exhibition.v1" };
  const parsed = replay(old).record;
  assert.equal(parsed.digest, undefined);
  assert.equal(parsed.agents[0].provenance, undefined);
  for (const provenance of [{ ...agent.provenance, attestation: "verified" },
    { ...agent.provenance, harnessRevision: "main" }, { builderId: "partial" }, null])
    assert.throws(() => publicAgent({ ...agent, provenance } as Agent));
});
test("Nim harness failures make no replacement move and successful requests use heap observations", async () => {
  const saved = globalThis.fetch, s = createGame(RULES.nim), before = JSON.stringify(s);
  let requests = 0;
  globalThis.fetch = async (_url, options) => {
    requests++;
    const req = JSON.parse(String(options?.body));
    assert.deepEqual(req.position, { heaps: [3,5,7], to_move: 0 });
    assert(!JSON.stringify(req).includes("SECRET"));
    return new Response(JSON.stringify({ move: requests === 1 ? "illegal" : req.legalMoves[0] }));
  };
  try {
    await assert.rejects(decide(s, agent, 256, new AbortController().signal, []), /no replacement/);
    assert.equal(requests, 1);
    assert.equal(JSON.stringify(s), before);
    assert.equal((await decide(s, agent, 256, new AbortController().signal, [])).move, legalMoves(s)[0]);
  } finally { globalThis.fetch = saved; }
});
