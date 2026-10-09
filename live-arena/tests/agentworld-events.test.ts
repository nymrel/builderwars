import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import {
  AGENTWORLD_ACTOR_PROPOSAL,
  AGENTWORLD_ROOM_PROPOSAL,
  agentWorldEventFile,
  canonicalJson,
  sha256Hex,
  verifyWorldEventChain,
  worldEventHash,
  type HashedWorldEvent,
  type WorldEventFields,
} from "../src/agentworld-events";
import type { ReadinessReceipt } from "../src/readiness";

// Cross-implementation golden vector: canonical payload string and event hash produced
// by the Nymrel World's own agent_world_lib._event_hash (tools/_golden probe run).
const GOLDEN_CANONICAL =
  '{"actor_agent_id":"a","content":"c","created_at_ms":1,"data_json":"{}","event_id":"e","event_type":"observation","parent_event_id":null,"prev_hash":null,"room_id":"r","thread_id":null,"trust_class":"agent-origin"}';
const GOLDEN_HASH = "6a5e27a953c3ff8c2854c96884a323b24a1f9b06fc4ec7a588874b42c0a96ab0";

const receipt = (): ReadinessReceipt => ({
  schema: "builderwars.readiness.receipt.v1",
  generatedAt: "2026-09-21T00:00:00.000Z",
  contender: { name: "Test Harness", kind: "harness", model: "test-model", effort: "default", strategy: "" },
  suite: { id: "tictactoe", game: "tictactoe", positionCount: 10, timeCapMs: 45000, oneReplyPerPosition: true },
  positions: [
    {
      id: "tictactoe-01",
      game: "tictactoe",
      turn: 0,
      movesSoFar: [],
      legalMoves: ["0", "1", "2", "3", "4", "5", "6", "7", "8"],
      outcome: "valid",
      latencyMs: 12,
      replyMove: "0",
      reportedModel: "stub/valid",
      detail: "A schema-valid, legal move was accepted on the first reply.",
    },
  ],
  summary: { positions: 1, valid: 1, invalidReply: 0, timeout: 0, connectionError: 0, skipped: 0 },
  notes: ["One reply per position; invalid replies are never retried or replaced."],
});

const deterministicFields = (overrides: Partial<WorldEventFields> = {}): WorldEventFields => ({
  eventId: "e",
  roomId: "r",
  threadId: null,
  actorAgentId: "a",
  eventType: "observation",
  content: "c",
  dataJson: "{}",
  parentEventId: null,
  trustClass: "agent-origin",
  createdAtMs: 1,
  prevHash: null,
  ...overrides,
});

test("canonicalJson matches the World's sorted, whitespace-free, ascii-escaped format", () => {
  assert.equal(canonicalJson({ b: 1, a: "x", c: [true, null] }), '{"a":"x","b":1,"c":[true,null]}');
  assert.equal(canonicalJson({ k: "\u00b7\u2014" }), '{"k":"\\u00b7\\u2014"}');
  assert.equal(canonicalJson({ z: undefined, a: 1 }), '{"a":1}');
  assert.equal(canonicalJson(GOLDEN_CANONICAL), JSON.stringify(GOLDEN_CANONICAL));
});

test("event hashing is byte-for-byte compatible with agent_world_lib._event_hash", async () => {
  const fields = deterministicFields();
  const hash = await worldEventHash(fields);
  assert.equal(hash, GOLDEN_HASH);
  assert.equal(hash, createHash("sha256").update(GOLDEN_CANONICAL).digest("hex"));
  assert.equal(await sha256Hex(GOLDEN_CANONICAL), createHash("sha256").update(GOLDEN_CANONICAL).digest("hex"));
});
test("receipt exports carry portable data with a preview hash verifiable from the file", async () => {
  const file = await agentWorldEventFile(receipt());
  assert.equal(file.schema, "builderwars.agentworld.world-event.v1");
  assert.equal(file.status, "export_only_not_ingested");
  assert.equal(file.target.room_id, AGENTWORLD_ROOM_PROPOSAL);
  assert.equal(file.target.actor_agent_id_proposed, AGENTWORLD_ACTOR_PROPOSAL);
  assert.equal(file.target.event_type, "observation");
  assert.equal(file.target.trust_class, "agent-origin");
  const round = JSON.parse(file.preview.data_json) as { receipt: ReadinessReceipt };
  assert.equal(round.receipt.generatedAt, "2026-09-21T00:00:00.000Z");
  assert.equal(round.receipt.contender.name, "Test Harness");
  assert.match(file.preview.content, /1\/1 valid/);
  assert.match(file.preview.content, /No ranking/);
  assert.match(file.preview.idempotency_key, /^builderwars-readiness-[0-9a-f]{16}$/);
  const expectedKey = `builderwars-readiness-${(await sha256Hex(canonicalJson(receipt()))).slice(0, 16)}`;
  assert.equal(file.preview.idempotency_key, expectedKey);
  const recomputed = await worldEventHash({
    eventId: file.preview.event_id,
    roomId: file.target.room_id,
    threadId: file.preview.thread_id,
    actorAgentId: file.target.actor_agent_id_proposed,
    eventType: file.target.event_type,
    content: file.preview.content,
    dataJson: file.preview.data_json,
    parentEventId: file.preview.parent_event_id,
    trustClass: file.target.trust_class,
    createdAtMs: file.preview.created_at_ms,
    prevHash: file.preview.prev_hash,
  });
  assert.equal(file.preview.event_hash, recomputed);
  assert.ok(!JSON.stringify(file).includes("SECRET"));
});

test("chain verification accepts intact links and pins the first broken sequence", async () => {
  const first = deterministicFields({ eventId: "e1" });
  const second = deterministicFields({
    eventId: "e2",
    content: "c2",
    prevHash: await worldEventHash(deterministicFields({ eventId: "e1" })),
  });
  const linked: HashedWorldEvent[] = [
    { ...first, eventHash: await worldEventHash(first) },
    { ...second, eventHash: await worldEventHash(second) },
  ];
  assert.deepEqual(await verifyWorldEventChain(linked), {
    valid: true,
    checked: 2,
    failedSeq: null,
    anchorPrevHash: null,
  });
  const tampered = linked.map((event, index) =>
    index === 1 ? { ...event, content: "tampered" } : event,
  );
  const tamperReport = await verifyWorldEventChain(tampered);
  assert.equal(tamperReport.valid, false);
  assert.equal(tamperReport.failedSeq, 2);
  const brokenLink = linked.map((event, index) =>
    index === 1 ? { ...event, prevHash: "not-the-link" } : event,
  );
  const linkReport = await verifyWorldEventChain(brokenLink);
  assert.equal(linkReport.valid, false);
  assert.equal(linkReport.failedSeq, 2);
});

test("exports exceeding the World room byte budget fail closed", async () => {
  const oversized = receipt();
  oversized.notes.push(`padding ${"x".repeat(40000)}`);
  await assert.rejects(() => agentWorldEventFile(oversized), /max_event_bytes/);
});

test("idempotency keys differ when receipt content differs", async () => {
  const first = await agentWorldEventFile(receipt());
  const changed = receipt();
  changed.summary.valid = 0;
  changed.summary.invalidReply = 1;
  changed.positions[0].outcome = "invalid-reply";
  const second = await agentWorldEventFile(changed);
  assert.notEqual(first.preview.idempotency_key, second.preview.idempotency_key);
});

