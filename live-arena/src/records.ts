import {
  createGame,
  applyMove,
  validateRules,
  moveLabel,
  type GameState,
  type Rules,
} from "./games";
import { type PublicAgent, type Decision } from "./models";
import { recordDigest, validateProvenance } from "./provenance";
export type Event = Decision & { ply: number; seat: 0 | 1; label: string };
export type RecordData = {
  schema: "builderwars.exhibition.v1" | "builderwars.exhibition.v2";
  digest?: string;
  id: string;
  createdAt: string;
  rules: Rules;
  agents: PublicAgent[];
  events: Event[];
  status: string;
};
export function replay(raw: unknown): { record: RecordData; state: GameState } {
  return normalizeReplay(raw, true);
}
function normalizeReplay(raw: unknown, verifyDigest: boolean): { record: RecordData; state: GameState } {
  if (!raw || typeof raw !== "object" || JSON.stringify(raw).length > 350000)
    throw Error("Invalid or oversized replay.");
  const r = raw as RecordData;
  if (
    !["builderwars.exhibition.v1", "builderwars.exhibition.v2"].includes(r.schema) ||
    typeof r.id !== "string" ||
    r.id.length > 80 ||
    typeof r.createdAt !== "string" ||
    !Array.isArray(r.agents) ||
    r.agents.length !== 2 ||
    !Array.isArray(r.events) ||
    r.events.length > 400 ||
    typeof r.status !== "string" ||
    r.status.length > 160
  )
    throw Error("Unsupported replay format.");
  const agents = r.agents.map((a) => {
    if (
      !a ||
      typeof a.name !== "string" ||
      a.name.length > 64 ||
      !["bot", "human", "openrouter", "harness"].includes(a.kind) ||
      typeof a.model !== "string" ||
      a.model.length > 160 ||
      typeof a.effort !== "string" ||
      a.effort.length > 20 ||
      typeof a.strategy !== "string" ||
      a.strategy.length > 1000
    )
      throw Error("Invalid agent metadata.");
    return {
      name: a.name,
      kind: a.kind,
      model: a.model,
      effort: a.effort,
      strategy: a.strategy,
      ...(r.schema === "builderwars.exhibition.v2" && a.provenance !== undefined
        ? { provenance: validateProvenance(a.provenance) } : {}),
    };
  });
  const rules = validateRules(r.rules);
  let state = createGame(rules);
  const events = r.events.map((e, i) => {
    if (
      !e ||
      e.ply !== i + 1 ||
      e.seat !== state.turn ||
      typeof e.move !== "string" ||
      typeof e.comment !== "string" ||
      e.comment.length > 240 ||
      typeof e.model !== "string" ||
      e.model.length > 160 ||
      typeof e.label !== "string" ||
      e.label.length > 80 ||
      !Number.isFinite(e.elapsed) ||
      e.elapsed < 0 ||
      e.elapsed > 3600000 ||
      !(e.tokens === null || (Number.isFinite(e.tokens) && e.tokens >= 0)) ||
      !(e.cost === null || (Number.isFinite(e.cost) && e.cost >= 0))
    )
      throw Error("Invalid move evidence.");
    const label = moveLabel(e.move, state);
    state = applyMove(state, e.move);
    return {
      ply: e.ply,
      seat: e.seat,
      move: e.move,
      comment: e.comment,
      model: e.model,
      label,
      elapsed: e.elapsed,
      tokens: e.tokens,
      cost: e.cost,
    };
  });
  const normalized: RecordData = {
      schema: r.schema,
      id: r.id,
      createdAt: r.createdAt,
      rules,
      agents,
      events,
      status: r.status,
  };
  if (r.schema === "builderwars.exhibition.v2") {
    const digest = recordDigest(normalized);
    if (verifyDigest && r.digest !== digest)
      throw Error("Replay content binding mismatch. Builder claims, seats or moves changed.");
    normalized.digest = digest;
  }
  return { record: normalized, state };
}
/** Snapshot the complete public configuration, seat order and move sequence. Not a signature. */
export function sealRecord(record: RecordData): RecordData {
  return normalizeReplay({ ...record, schema: "builderwars.exhibition.v2" }, false).record;
}
export async function encodeReplay(record: RecordData) {
  const bytes = new TextEncoder().encode(JSON.stringify(sealRecord(record)));
  const compressed = await new Response(
    new Blob([bytes]).stream().pipeThrough(new CompressionStream("gzip")),
  ).arrayBuffer();
  return btoa(String.fromCharCode(...new Uint8Array(compressed)))
    .replaceAll("+", "-")
    .replaceAll("/", "_")
    .replaceAll("=", "");
}
export async function decodeReplay(value: string) {
  if (value.length > 65000)
    throw Error("Replay link too large; import the JSON file.");
  const bytes = Uint8Array.from(
    atob(value.replaceAll("-", "+").replaceAll("_", "/")),
    (c) => c.charCodeAt(0),
  );
  const reader = new Blob([bytes])
    .stream()
    .pipeThrough(new DecompressionStream("gzip"))
    .getReader();
  let size = 0;
  const chunks: Uint8Array[] = [];
  while (true) {
    const part = await reader.read();
    if (part.done) break;
    size += part.value.length;
    if (size > 350000) {
      await reader.cancel();
      throw Error("Replay exceeds the size limit.");
    }
    chunks.push(part.value);
  }
  return replay(JSON.parse(await new Blob(chunks as BlobPart[]).text()));
}
export function download(name: string, value: unknown) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
