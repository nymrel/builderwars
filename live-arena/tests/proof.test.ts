import assert from "node:assert/strict";
import test from "node:test";
import { RULES, createGame, applyMove, moveLabel } from "../src/games";
import type { RecordData } from "../src/records";
import { canonical, createProof, verifyProof, parseProof, sha256 } from "../src/proof";

const engine = "a".repeat(64);
function match(moves = ["0", "1", "0", "1", "0", "1", "0"]): RecordData {
  let state = createGame(RULES.connect4);
  const record: RecordData = {
    schema: "builderwars.exhibition.v1", id: "test-duel", createdAt: "2026-09-05T00:00:00.000Z",
    rules: { ...RULES.connect4 }, status: "Untrusted display label",
    agents: [0, 1].map((i) => ({ name: `Human ${i}`, kind: "human", model: "human", effort: "default", strategy: "" })),
    events: [],
  };
  for (const move of moves) {
    record.events.push({ ply: record.events.length + 1, seat: state.turn, move, label: moveLabel(move, state), comment: "", model: "human", elapsed: 12.3456, tokens: null, cost: null });
    state = applyMove(state, move);
  }
  return record;
}
test("portable proof reproduces a full Connect Four outcome without trusting its display status", async () => {
  const proof = await createProof(match(), engine, 80, "browser_session");
  const result = await verifyProof(proof, engine);
  assert.equal(result.state.winner, 0);
  assert.equal(result.state.over, true);
  assert.equal(result.record.status, result.state.reason);
  assert.equal(result.attested, false);
  assert.deepEqual(parseProof(proof), proof.trimEnd().split("\n").map(line => JSON.parse(line)));
});
test("unknown engines, truncation, tampered outcomes and metadata fail closed", async () => {
  const proof = await createProof(match(), engine, 80, "browser_session");
  await assert.rejects(verifyProof(proof, "b".repeat(64)), /engine/i);
  await assert.rejects(verifyProof(proof.trimEnd().split("\n").slice(0, -1).join("\n"), engine));
  await assert.rejects(verifyProof(proof.replace('"winner":0', '"winner":1'), engine));
  await assert.rejects(verifyProof(proof.replace('Human 0', 'Pretender'), engine));
});
test("canonical wire rejects duplicate keys, unsafe numbers and malformed Unicode", () => {
  assert.throws(() => parseProof('{"a":1,"a":1}\n'));
  assert.throws(() => canonical({ n: 0.25 }));
  assert.throws(() => canonical({ n: Number.MAX_SAFE_INTEGER + 1 }));
  assert.throws(() => canonical({ name: "\ud800" }));
  assert.equal(canonical({ "😀": 1, "\ue000": 2 }), '{"":2,"😀":1}');
});
test("duplicate keys and alternate wire encodings are rejected inside a complete proof", async () => {
  const proof = await createProof(match(), engine, 80, "browser_session");
  assert.throws(() => parseProof(proof.replace('"seq":0', '"seq":0,"seq":0')), /canonical/i);
  assert.throws(() => parseProof(proof.replace('"seq":0', '"seq":0.0')), /canonical/i);
  assert.throws(() => parseProof(proof.replaceAll("\n", "\r\n")), /canonical/i);
  assert.throws(() => parseProof(proof.replace('"id":"test-duel"', '"id":"\\ud800"')), /Unicode/i);
});
test("unfinished snapshots never become completed or provider-attested results", async () => {
  const proof = await createProof(match(["0"]), engine, 2, "reverified_import");
  const result = await verifyProof(proof, engine);
  assert.equal(result.state.over, false);
  assert.equal(result.origin, "reverified_import");
  assert.equal(result.record.status, "Incomplete snapshot");
  assert.equal(result.attested, false);
});

async function rechain(rows: ReturnType<typeof parseProof>) {
  let prev = "0".repeat(64);
  for (const [seq, row] of rows.entries()) {
    row.seq = seq;
    row.prev = prev;
    row.hash = await sha256(`${prev}\x1f${canonical({ kind: row.kind, seq, body: row.body })}`);
    prev = row.hash;
  }
  return rows.map(canonical).join("\n") + "\n";
}
test("rechaining cannot bless a forged result, rule override, state, turn, version or illegal move", async () => {
  const original = await createProof(match(), engine, 80, "browser_session");
  const mutations: ((rows: any[]) => void)[] = [
    rows => { rows.at(-1).body.winner = 1; },
    rows => { rows[0].body.rules.rows = 10; },
    rows => { rows[1].body.digest = "b".repeat(64); },
    rows => { rows[2].body.seat = 1; },
    rows => { delete rows[0].body.protocol; },
    rows => { rows[0].body.referee = "builderwars-board-js/2"; },
    rows => { rows[2].body.move = "99"; },
    rows => { rows[0].body.model_attested = true; },
    rows => { rows[0].body.extra = "untrusted"; },
    rows => { rows.splice(3, 1); },
  ];
  for (const mutate of mutations) {
    const rows = parseProof(original);
    mutate(rows);
    await assert.rejects(verifyProof(await rechain(rows), engine));
  }
});
test("proof strips strategies, public comments and unrecognized connection fields", async () => {
  const input = match();
  input.agents[0].strategy = "private strategy sentinel";
  Object.assign(input.agents[0], { key: "secret sentinel", endpoint: "https://private.example" });
  input.events[0].comment = "comment sentinel";
  const proof = await createProof(input, engine, 80, "browser_session");
  for (const sentinel of ["private strategy sentinel", "secret sentinel", "private.example", "comment sentinel"]) assert(!proof.includes(sentinel));
  assert.equal((await verifyProof(proof, engine)).record.agents[0].strategy, "");
});
test("a capped unfinished game remains incomplete and cannot exceed its limit", async () => {
  const input = match(["0", "1"]);
  const result = await verifyProof(await createProof(input, engine, 2, "browser_session"), engine);
  assert.equal(result.state.over, false);
  assert.equal(result.state.winner, null);
  assert.equal(result.record.status, "Move limit reached");
  await assert.rejects(createProof(match(), engine, 2, "browser_session"));
});
