import { createGame, replayStepper, type GameState } from "./games";
import { replay, type RecordData } from "./records";

export const PROOF_PROTOCOL = "builderwars.board.v1";
export const PROOF_LIMIT = 1_500_000;
type Origin = "browser_session" | "reverified_import";
type Envelope = { kind: string; seq: number; body: unknown; prev: string; hash: string };
const digestPattern = /^[a-f0-9]{64}$/;

function validString(value: string) {
  for (const c of value) {
    const n = c.codePointAt(0)!;
    if (n >= 0xd800 && n <= 0xdfff) throw Error("Malformed Unicode.");
  }
  return value;
}
function compareKeys(a: string, b: string) {
  const left = Array.from(a, c => c.codePointAt(0)!);
  const right = Array.from(b, c => c.codePointAt(0)!);
  for (let i = 0; i < Math.min(left.length, right.length); i++) {
    if (left[i] !== right[i]) return left[i] - right[i];
  }
  return left.length - right.length;
}
/** Integer-only, Unicode-code-point sorted canonical JSON. No implicit coercions. */
export function canonical(value: unknown): string {
  if (value === null || typeof value === "boolean") return JSON.stringify(value);
  if (typeof value === "string") return JSON.stringify(validString(value));
  if (typeof value === "number") {
    if (!Number.isSafeInteger(value) || Object.is(value, -0)) throw Error("Canonical numbers must be safe integers.");
    return String(value);
  }
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value && typeof value === "object" && Object.getPrototypeOf(value) === Object.prototype) {
    return `{${Object.keys(value).sort(compareKeys).map(key => `${canonical(key)}:${canonical((value as Record<string, unknown>)[key])}`).join(",")}}`;
  }
  throw Error("Unsupported canonical value.");
}
export async function sha256(bytes: Uint8Array | string) {
  const input = typeof bytes === "string" ? new TextEncoder().encode(bytes) : bytes;
  const digest = await crypto.subtle.digest("SHA-256", input as BufferSource);
  return Array.from(new Uint8Array(digest), n => n.toString(16).padStart(2, "0")).join("");
}
export function parseProof(text: string): Envelope[] {
  if (typeof text !== "string" || new TextEncoder().encode(text).length > PROOF_LIMIT) throw Error("Proof exceeds size limit.");
  const lines = (text.endsWith("\n") ? text.slice(0, -1) : text).split("\n");
  if (lines.length < 3 || lines.length > 803) throw Error("Incomplete or oversized proof.");
  return lines.map(line => {
    const parsed = JSON.parse(line);
    // Requiring canonical wire bytes also rejects duplicate keys, whitespace,
    // unsafe numbers, alternate escapes and other lossy JSON parse forms.
    if (canonical(parsed) !== line) throw Error("Non-canonical proof line.");
    return parsed as Envelope;
  });
}
function settings(engine: string, maxPlies: number, origin: string) {
  if (!digestPattern.test(engine)) throw Error("Invalid engine digest.");
  if (!Number.isSafeInteger(maxPlies) || maxPlies < 2 || maxPlies > 400) throw Error("Invalid move limit.");
  if (origin !== "browser_session" && origin !== "reverified_import") throw Error("Invalid origin declaration.");
}
function outcome(state: GameState, maxPlies: number) {
  return {
    complete: state.over, winner: state.over ? state.winner : null, plies: state.moves.length,
    reason: state.over ? state.reason : state.moves.length >= maxPlies ? "Move limit reached" : "Incomplete snapshot",
    model_attested: false, execution_attested: false,
  };
}
export async function createProof(raw: RecordData, engine: string, maxPlies: number, origin: Origin): Promise<string> {
  settings(engine, maxPlies, origin);
  const { record, state: finalState } = replay(raw);
  if (record.events.length > maxPlies) throw Error("Record exceeds declared move limit.");
  const rows: Envelope[] = [];
  let prev = "0".repeat(64);
  async function append(kind: string, body: unknown) {
    const core = { kind, seq: rows.length, body };
    const hash = await sha256(`${prev}\x1f${canonical(core)}`);
    rows.push({ ...core, prev, hash });
    prev = hash;
  }
  await append("header", {
    protocol: PROOF_PROTOCOL, referee: "builderwars-board-js/1", engine, origin,
    id: record.id, createdAt: record.createdAt, rules: record.rules, maxPlies,
    // Public declarations only. Never serialize prompts, keys or harness URLs.
    agents: record.agents.map(({ name, kind, model, effort }) => ({ name, kind, model, effort })),
    model_attested: false, execution_attested: false,
  });
  await append("state", { ply: 0, digest: await sha256(canonical(createGame(record.rules))) });
  const advance = replayStepper(record.rules);
  for (const e of record.events) {
    await append("move", {
      ply: e.ply, seat: e.seat, move: e.move, model: e.model,
      // Reported metrics are decimal strings, never canonical floating point or independent billing proof.
      elapsedMs: String(e.elapsed), tokens: e.tokens === null ? null : String(e.tokens),
      cost: e.cost === null ? null : String(e.cost),
    });
    await append("state", { ply: e.ply, digest: await sha256(canonical(advance(e.move))) });
  }
  await append("result", outcome(finalState, maxPlies));
  const text = rows.map(canonical).join("\n") + "\n";
  if (new TextEncoder().encode(text).length > PROOF_LIMIT) throw Error("Proof exceeds size limit.");
  return text;
}

export async function verifyProof(text: string, trustedEngine: string) {
  const rows = parseProof(text);
  let prev = "0".repeat(64);
  for (const [i, row] of rows.entries()) {
    if (!row || row.seq !== i || row.prev !== prev || typeof row.kind !== "string" || !digestPattern.test(row.hash)) throw Error("Invalid proof chain.");
    if (row.hash !== await sha256(`${prev}\x1f${canonical({ kind: row.kind, seq: i, body: row.body })}`)) throw Error("Proof hash mismatch.");
    prev = row.hash;
  }
  const header = rows[0].body as Record<string, any>;
  if (rows[0].kind !== "header" || !header || header.protocol !== PROOF_PROTOCOL || header.referee !== "builderwars-board-js/1") throw Error("Unsupported proof version.");
  if (!digestPattern.test(trustedEngine) || header.engine !== trustedEngine) throw Error("Engine mismatch: use the matching trusted verifier.");
  settings(header.engine, header.maxPlies, header.origin);
  if (!Array.isArray(header.agents) || header.agents.length !== 2) throw Error("Invalid entrants.");
  if (rows.at(-1)?.kind !== "result" || rows[1]?.kind !== "state" || rows.length % 2 !== 1) throw Error("Incomplete proof.");
  function metric(value: unknown, nullable: boolean): number | null {
    if (value === null && nullable) return null;
    if (typeof value !== "string" || value.length > 32 || !Number.isFinite(Number(value)) || String(Number(value)) !== value) throw Error("Invalid reported metric.");
    return Number(value);
  }
  const raw: RecordData = {
    schema: "builderwars.exhibition.v1", id: header.id, createdAt: header.createdAt, rules: header.rules,
    agents: header.agents.map(a => ({ ...a, strategy: "" })), status: "",
    events: [],
  };
  for (let i = 2; i < rows.length - 1; i += 2) {
    if (rows[i].kind !== "move" || rows[i + 1].kind !== "state") throw Error("Invalid proof event order.");
    const e = rows[i].body as Record<string, any>;
    raw.events.push({ ply: e.ply, seat: e.seat, move: e.move, model: e.model, comment: "", label: "",
      elapsed: metric(e.elapsedMs, false)!, tokens: metric(e.tokens, true), cost: metric(e.cost, true) });
  }
  const result = replay(raw);
  // Rebuilding from the sole rules authority rejects forged results, extra fields,
  // normalized rules, omitted successor states and tampering even after rechaining.
  const expected = await createProof(result.record, trustedEngine, header.maxPlies, header.origin);
  if (canonical(parseProof(expected)) !== canonical(rows)) throw Error("Proof does not reproduce against this referee.");
  result.record.status = outcome(result.state, header.maxPlies).reason;
  return { ...result, engine: trustedEngine, origin: header.origin as Origin, attested: false as const };
}
