import type { ReadinessReceipt } from "./readiness";

// AgentWorld event export — the one-way bridge format from the concept charter
// (docs/AGENTWORLD_CONCEPT_V0.md, Phase 1). Payloads mirror the Nymrel World
// agent-world event format exactly (agent_world_lib._event_hash): canonical JSON with
// sorted keys and no whitespace, SHA-256 hex. The World's post_event recomputes
// event_id, created_at_ms, prev_hash and event_hash from room state at ingest, so an
// export is a format preview plus portable data (content, data, idempotency_key,
// trust_class), never a pre-signed event. Export only: nothing is uploaded, and no
// World object can feed back into referee state.

export const AGENTWORLD_ROOM_PROPOSAL = "builderwars-readiness";
export const AGENTWORLD_ACTOR_PROPOSAL = "builderwars-contender";
const MAX_EVENT_BYTES = 32768; // World rooms default max_event_bytes.

export function canonicalJson(value: unknown): string {
  const escape = (text: string) =>
    JSON.stringify(text).replace(/[\u0080-\uffff]/g, (ch) =>
      `\\u${ch.charCodeAt(0).toString(16).padStart(4, "0")}`,
    );
  const walk = (node: unknown): string => {
    if (node === null || typeof node === "number" || typeof node === "boolean")
      return JSON.stringify(node);
    if (typeof node === "string") return escape(node);
    if (Array.isArray(node)) return `[${node.map(walk).join(",")}]`;
    if (typeof node !== "object") throw Error("AgentWorld export data must be JSON.");
    const entries = Object.entries(node as Record<string, unknown>)
      .filter(([, member]) => member !== undefined)
      .sort(([left], [right]) => (left < right ? -1 : left > right ? 1 : 0));
    return `{${entries.map(([key, member]) => `${escape(key)}:${walk(member)}`).join(",")}}`;
  };
  return walk(value);
}

export async function sha256Hex(text: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

export type WorldEventFields = {
  eventId: string;
  roomId: string;
  threadId: string | null;
  actorAgentId: string;
  eventType: string;
  content: string;
  dataJson: string;
  parentEventId: string | null;
  trustClass: string;
  createdAtMs: number;
  prevHash: string | null;
};

// Byte-for-byte mirror of agent_world_lib._event_hash(payload).
export async function worldEventHash(fields: WorldEventFields): Promise<string> {
  return sha256Hex(
    canonicalJson({
      event_id: fields.eventId,
      room_id: fields.roomId,
      thread_id: fields.threadId,
      actor_agent_id: fields.actorAgentId,
      event_type: fields.eventType,
      content: fields.content,
      data_json: fields.dataJson,
      parent_event_id: fields.parentEventId,
      trust_class: fields.trustClass,
      created_at_ms: fields.createdAtMs,
      prev_hash: fields.prevHash,
    }),
  );
}

export type AgentWorldEventFile = {
  schema: "builderwars.agentworld.world-event.v1";
  status: "export_only_not_ingested";
  target: {
    room_id: string;
    actor_agent_id_proposed: string;
    event_type: "observation";
    trust_class: "agent-origin";
    format: "agent-world post_event payload v1";
    ingest: string;
  };
  preview: {
    event_id: string;
    thread_id: null;
    parent_event_id: null;
    created_at_ms: number;
    prev_hash: null;
    event_hash: string;
    idempotency_key: string;
    content: string;
    data_json: string;
  };
  notes: string[];
};

export async function agentWorldEventFile(
  receipt: ReadinessReceipt,
  options: { roomId?: string; actorAgentId?: string } = {},
): Promise<AgentWorldEventFile> {
  const summary = receipt.summary;
  const content =
    `Agent readiness ${summary.valid}/${summary.positions} valid, ${summary.invalidReply} invalid reply, ` +
    `${summary.timeout} timeout, ${summary.connectionError} connection error` +
    `${summary.skipped ? `, ${summary.skipped} skipped` : ""} over the ${receipt.suite.game} suite; ` +
    `referee-validated protocol practice over ${receipt.contender.name}. No ranking.`;
  const data = {
    schema: receipt.schema,
    receipt,
    exportedBy: "builderwars-live-arena",
    oneWayExport: true,
  };
  const dataJson = canonicalJson(data);
  if (new TextEncoder().encode(dataJson).length > MAX_EVENT_BYTES)
    throw Error("AgentWorld export exceeds the World room default max_event_bytes.");
  if (new TextEncoder().encode(content).length > MAX_EVENT_BYTES)
    throw Error("AgentWorld export content exceeds the World room default max_event_bytes.");
  const idempotencyKey = `builderwars-readiness-${(await sha256Hex(canonicalJson(receipt))).slice(0, 16)}`;
  const fields: WorldEventFields = {
    eventId: crypto.randomUUID(),
    roomId: options.roomId ?? AGENTWORLD_ROOM_PROPOSAL,
    threadId: null,
    actorAgentId: options.actorAgentId ?? AGENTWORLD_ACTOR_PROPOSAL,
    eventType: "observation",
    content,
    dataJson,
    parentEventId: null,
    trustClass: "agent-origin",
    createdAtMs: Date.now(),
    prevHash: null,
  };
  return {
    schema: "builderwars.agentworld.world-event.v1",
    status: "export_only_not_ingested",
    target: {
      room_id: fields.roomId,
      actor_agent_id_proposed: fields.actorAgentId,
      event_type: "observation",
      trust_class: "agent-origin",
      format: "agent-world post_event payload v1",
      ingest:
        "post_event recomputes event_id, created_at_ms, prev_hash and event_hash from room state; content, data and idempotency_key carry over. Import requires a registered room actor and an owner ruling; nothing feeds back into referee state.",
    },
    preview: {
      event_id: fields.eventId,
      thread_id: null,
      parent_event_id: null,
      created_at_ms: fields.createdAtMs,
      prev_hash: null,
      event_hash: await worldEventHash(fields),
      idempotency_key: idempotencyKey,
      content,
      data_json: dataJson,
    },
    notes: [
      "Export only: this file is not uploaded anywhere and creates no World state.",
      "The event hash is a format preview; the World recomputes the chain at ingest.",
      "One-way boundary: readiness receipts describe protocol validity, not strategic strength; no ranking is claimed.",
    ],
  };
}

// Verifies an exported or stored sequence against the World hash algorithm: each
// event's hash must match its fields and link to the previous event's hash.
export type HashedWorldEvent = WorldEventFields & { eventHash: string };

export async function verifyWorldEventChain(
  events: HashedWorldEvent[],
): Promise<{ valid: boolean; checked: number; failedSeq: number | null; anchorPrevHash: string | null }> {
  let previous: string | null = null;
  let checked = 0;
  for (const [index, event] of events.entries()) {
    if (index > 0 && event.prevHash !== previous)
      return { valid: false, checked, failedSeq: index + 1, anchorPrevHash: events[0].prevHash };
    if ((await worldEventHash(event)) !== event.eventHash)
      return { valid: false, checked, failedSeq: index + 1, anchorPrevHash: events[0].prevHash };
    previous = event.eventHash;
    checked += 1;
  }
  return { valid: true, checked, failedSeq: null, anchorPrevHash: events[0]?.prevHash ?? null };
}
