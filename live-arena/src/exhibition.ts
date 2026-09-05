import { replay, sha256, refereeManifest, type RecordData } from "./runtime";
import { safeReplay } from "./sharing";
import { isRuleComplete } from "./outcome";

export const EXHIBITION_SCHEMA = "builderwars.frontier-replay.v1";
export const EXHIBITION_MAX_BYTES = 350_000;
type Evidence = "provider-response" | "client-reported" | "unreported";
type Player = { route: "astra" | "fable" | "grok" | "gemini"; requestedModel: string; resolvedModel: string | null; identityEvidence: Evidence };
export type Exhibition = {
  schema: typeof EXHIBITION_SCHEMA;
  record: RecordData;
  source: { runner: string; plan: string; result: string; originalProof: string; referee: string };
  engine: { name: string; binarySha256: string; nodes: number; threads: number; hashMiB: number; multiPv: number };
  limits: { maxCalls: number; maxPliesPerGame: number; perCallMs: number; totalMs: number };
  game: number;
  gameAttempts: number;
  exit: "complete" | "capped" | "failed";
  players: [Player, Player];
  decisions: { ply: number; requestDigest: string; inputTokens: number | null; outputTokens: number | null }[];
  verification: "replay-integrity-not-execution-attestation";
  digest: string;
};
function exact(value: unknown, keys: string[]): asserts value is Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value) || Object.keys(value).sort().join(",") !== keys.sort().join(",")) throw Error("Unexpected exhibition fields.");
}
function integer(value: unknown, min: number, max: number) {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < min || value > max) throw Error("Invalid exhibition resource or count.");
}
function digest(value: unknown) {
  if (typeof value !== "string" || !/^[a-f0-9]{64}$/.test(value)) throw Error("Invalid exhibition source digest.");
}
function identifier(value: unknown) {
  if (typeof value !== "string" || !/^[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,159}$/.test(value)) throw Error("Invalid public model identifier.");
}
/** Deterministic JSON for the new envelope only; never changes the v1 referee. */
function stable(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map(k => `${JSON.stringify(k)}:${stable((value as Record<string, unknown>)[k])}`).join(",")}}`;
  return JSON.stringify(value);
}
function immutable<T>(value: T): T {
  if (value && typeof value === "object") { Object.values(value).forEach(immutable); Object.freeze(value); }
  return value;
}
/** Structural validation is synchronous for optional device storage. The async
 * reader also verifies the envelope digest before opening a saved/imported file. */
export function validateExhibition(raw: unknown): Exhibition {
  if (new TextEncoder().encode(JSON.stringify(raw)).length > EXHIBITION_MAX_BYTES) throw Error("Exhibition exceeds size limit.");
  exact(raw, ["schema", "record", "source", "engine", "limits", "game", "gameAttempts", "exit", "players", "decisions", "verification", "digest"]);
  if (raw.schema !== EXHIBITION_SCHEMA || raw.verification !== "replay-integrity-not-execution-attestation") throw Error("Unsupported exhibition or attestation claim.");
  digest(raw.digest);
  exact(raw.source, ["runner", "plan", "result", "originalProof", "referee"]);
  Object.values(raw.source).forEach(digest);
  if (raw.source.referee !== refereeManifest.digest) throw Error("Exhibition requires a different referee.");
  exact(raw.engine, ["name", "binarySha256", "nodes", "threads", "hashMiB", "multiPv"]);
  if (raw.engine.name !== "Stockfish 19") throw Error("Unsupported exhibition advisor.");
  digest(raw.engine.binarySha256);
  if (raw.engine.nodes !== 20000 || raw.engine.threads !== 1 || raw.engine.hashMiB !== 16 || raw.engine.multiPv !== 3) throw Error("Unsupported engine-assistance class.");
  exact(raw.limits, ["maxCalls", "maxPliesPerGame", "perCallMs", "totalMs"]);
  integer(raw.limits.maxCalls, 1, 24); integer(raw.limits.maxPliesPerGame, 2, 80);
  integer(raw.limits.perCallMs, 1, 120000); integer(raw.limits.totalMs, 1, 900000);
  integer(raw.game, 1, 2);
  integer(raw.gameAttempts, 0, Number(raw.limits.maxCalls));
  if (!["complete", "capped", "failed"].includes(String(raw.exit))) throw Error("Invalid exhibition exit.");
  const parsed = replay(raw.record), record = safeReplay(parsed.record);
  if (record.rules.kind !== "chess" || stable(record) !== stable(raw.record)) throw Error("Exhibition must contain a sanitized chess replay; no prompts or comments.");
  if (record.events.length > Number(raw.limits.maxPliesPerGame) || record.events.length > Number(raw.limits.maxCalls)) throw Error("Exhibition exceeds declared limits.");
  if (Number(raw.gameAttempts) < record.events.length || Number(raw.gameAttempts) > record.events.length + (raw.exit === "failed" ? 1 : 0)) throw Error("Exhibition attempt count contradicts the replay.");
  if ((raw.exit === "complete") !== isRuleComplete(parsed.state)) throw Error("Exhibition result contradicts the referee.");
  if (!Array.isArray(raw.players) || raw.players.length !== 2) throw Error("Two exhibition players are required.");
  const routes = raw.game === 1 ? ["astra", "fable"] : ["grok", "gemini"];
  for (const [seat, p] of raw.players.entries()) {
    exact(p, ["route", "requestedModel", "resolvedModel", "identityEvidence"]);
    if (p.route !== routes[seat]) throw Error("Unexpected exhibition pairing.");
    identifier(p.requestedModel);
    const requested = { astra: "gpt-6-astra", fable: "fable", grok: "cursor-grok-4.6-high", gemini: "gemini-3.1-pro-high" };
    if (p.requestedModel !== requested[p.route as keyof typeof requested]) throw Error("Unexpected requested frontier route.");
    if (p.resolvedModel !== null) identifier(p.resolvedModel);
    if (!["provider-response", "client-reported", "unreported"].includes(String(p.identityEvidence)) || (p.resolvedModel === null) !== (p.identityEvidence === "unreported")) throw Error("Inconsistent identity evidence.");
    const family = { astra: /^gpt-6-astra(?:$|[-/])/, fable: /^claude-fable-5-1(?:$|-)/, grok: /^(?:cursor-)?grok-4\.6(?:$|-)/, gemini: /^gemini-3\.1-pro(?:$|-)/ };
    if (p.resolvedModel !== null && !family[p.route as keyof typeof family].test(String(p.resolvedModel))) throw Error("Reported identity is outside the selected frontier family.");
    if (record.agents[seat].kind !== "harness" || record.agents[seat].model !== p.requestedModel) throw Error("Replay and requested model differ.");
    const events = record.events.filter(e => e.seat === seat);
    if (!events.length && p.resolvedModel !== null) throw Error("No accepted decision supports this identity.");
    if (events.some(e => e.model !== (p.resolvedModel ?? `unreported:${p.requestedModel}`))) throw Error("Replay and response identity differ.");
  }
  if (!Array.isArray(raw.decisions) || raw.decisions.length !== record.events.length) throw Error("Missing decision evidence.");
  raw.decisions.forEach((d, i) => {
    exact(d, ["ply", "requestDigest", "inputTokens", "outputTokens"]);
    if (d.ply !== i + 1) throw Error("Decision order differs from replay.");
    digest(d.requestDigest);
    for (const n of [d.inputTokens, d.outputTokens]) if (n !== null) integer(n, 0, 1_000_000);
    const tokens = d.inputTokens === null || d.outputTokens === null ? null : Number(d.inputTokens) + Number(d.outputTokens);
    if (record.events[i].tokens !== tokens) throw Error("Reported usage differs from replay.");
  });
  return JSON.parse(JSON.stringify(raw)) as Exhibition;
}
export async function readExhibition(raw: unknown) {
  const value = validateExhibition(raw);
  const { digest: expected, ...payload } = value;
  if (expected !== await sha256(stable(payload))) throw Error("Exhibition content digest mismatch.");
  return immutable(value);
}
export async function sealExhibition(payload: Omit<Exhibition, "digest">) {
  return readExhibition({ ...payload, digest: await sha256(stable(payload)) });
}
export function exhibitionDescription(value: Exhibition): string {
  const exit = value.exit === "complete" ? "Completed game" : value.exit === "capped" ? "Resource-capped · no winner" : "Failed run · no winner";
  return `${exit}. Stockfish 19 assisted both seats: 20,000 nodes, 3 candidate lines per turn. Models selected the recorded moves. ${value.record.events.length} accepted moves / ${value.gameAttempts} attempted calls. Failed-call usage is unknown. Reported costs are list-price estimates, not subscription charges; token counts may exclude caches. Source hashes bind the supplied receipts, not independently attested execution.`;
}
