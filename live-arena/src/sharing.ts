import { replay, validateRules, canonical, type RecordData, type Rules } from "./runtime";
import type { Agent } from "./models";
import { isExhibitionLimit, isRuleComplete } from "./outcome";

type PublicSeat = { kind: Agent["kind"]; model: string; effort: string };
export type MatchSetup = {
  schema: "builderwars.setup.v1";
  rules: Rules;
  moveLimit: number;
  maxTokens: number;
  entrants: PublicSeat[];
};
function exactKeys(value: unknown, keys: string[]): asserts value is Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value) || Object.keys(value).sort().join(",") !== keys.sort().join(",")) throw Error("Unexpected setup fields.");
}
function integer(value: unknown, min: number, max: number) {
  if (typeof value !== "number" || !Number.isInteger(value) || value < min || value > max) throw Error("Invalid setup resource limit.");
  return value;
}
function publicSeat(raw: unknown): PublicSeat {
  exactKeys(raw, ["kind", "model", "effort"]);
  if (!["bot", "human", "openrouter", "harness"].includes(String(raw.kind)) || typeof raw.model !== "string" || raw.model.length > 160 || typeof raw.effort !== "string" || raw.effort.length > 20) throw Error("Invalid shared contender.");
  const { kind, model, effort } = raw as PublicSeat;
  if (kind === "bot" && (!["tactician", "random"].includes(model) || effort !== "default")) throw Error("Unknown built-in opponent.");
  if (kind === "human" && (model !== "human" || effort !== "default")) throw Error("Invalid human setup.");
  if (kind === "harness" && (model !== "" || effort !== "default")) throw Error("Harness connections must be configured locally.");
  if (kind === "openrouter" && (!/^[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,159}$/.test(model) || !/^[a-zA-Z0-9_-]{1,20}$/.test(effort))) throw Error("Invalid public model declaration.");
  return { kind, model, effort };
}
export function validateSetup(raw: unknown): MatchSetup {
  exactKeys(raw, ["schema", "rules", "moveLimit", "maxTokens", "entrants"]);
  if (raw.schema !== "builderwars.setup.v1" || !Array.isArray(raw.entrants) || raw.entrants.length !== 2) throw Error("Unsupported setup format.");
  const rules = validateRules(raw.rules);
  if (canonical(rules) !== canonical(raw.rules)) throw Error("Shared rules are not canonical.");
  return { schema: raw.schema, rules, moveLimit: integer(raw.moveLimit, 2, 400), maxTokens: integer(raw.maxTokens, 256, 16384), entrants: raw.entrants.map(publicSeat) };
}
export function makeSetup(record: RecordData, moveLimit: number, maxTokens: number): MatchSetup {
  const { record: valid } = replay(record);
  return validateSetup({
    schema: "builderwars.setup.v1", rules: valid.rules, moveLimit, maxTokens,
    entrants: valid.agents.map(a => a.kind === "harness" ? { kind: a.kind, model: "", effort: "default" }
      : a.kind === "human" ? { kind: a.kind, model: "human", effort: "default" }
      : { kind: a.kind, model: a.model, effort: a.kind === "bot" ? "default" : a.effort }),
  });
}
export function encodeSetup(raw: unknown) {
  const text = canonical(validateSetup(raw));
  const bytes = new TextEncoder().encode(text);
  if (bytes.length > 4096) throw Error("Setup is too large to share.");
  return btoa(String.fromCharCode(...bytes)).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
}
export function decodeSetup(value: string) {
  if (value.length > 6000 || !/^[a-zA-Z0-9_-]+$/.test(value)) throw Error("Invalid or oversized setup link.");
  const bytes = Uint8Array.from(atob(value.replaceAll("-", "+").replaceAll("_", "/")), c => c.charCodeAt(0));
  const text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  if (bytes.length > 4096) throw Error("Setup is too large to share.");
  const parsed = JSON.parse(text);
  if (canonical(parsed) !== text) throw Error("Non-canonical setup link.");
  return validateSetup(parsed);
}
/** New public shares omit prompt/comment text; local legacy records stay intact. */
export function safeReplay(raw: RecordData): RecordData {
  const { record, state } = replay(raw);
  return { ...record, agents: record.agents.map(a => ({ ...a, strategy: "" })),
    events: record.events.map(e => ({ ...e, comment: "" })),
    status: state.over ? state.reason : "Unfinished match" };
}
export function freeAgents(human = false): Agent[] {
  return [
    { name: human ? "You" : "Tactician", kind: human ? "human" : "bot", model: human ? "human" : "tactician", effort: "default", key: "", endpoint: "", strategy: "" },
    { name: human ? "Tactician" : "Wildcard", kind: "bot", model: human ? "tactician" : "random", effort: "default", key: "", endpoint: "", strategy: "" },
  ];
}
export function configuredAgents(setup: MatchSetup): Agent[] {
  return validateSetup(setup).entrants.map((a, i) => ({ ...a,
    name: a.kind === "human" ? `Human ${i + 1}` : a.kind === "bot" ? a.model === "random" ? "Wildcard" : "Tactician" : a.kind === "harness" ? `Connect harness ${i + 1}` : a.model,
    key: "", endpoint: "", strategy: "",
  }));
}
const cleanText = (value: string) => value.replace(/[\u0000-\u001f\u007f-\u009f\u202a-\u202e\u2066-\u2069]/g, " ").trim();
export function summarizeMatch(raw: RecordData) {
  const { record, state } = replay(raw);
  const names = record.agents.map((a, i) => cleanText(a.name) || `Contender ${i + 1}`);
  const sumKnown = (key: "tokens" | "cost") => {
    if (!record.events.length || record.events.some(e => e[key] === null)) return null;
    const total = record.events.reduce((n, e) => n + e[key]!, 0);
    return Number.isFinite(total) ? total : null;
  };
  const entrants = record.agents.map(a => a.kind === "bot" ? `Built-in · ${a.model}` : a.kind === "human" ? "Human player" : `${a.kind === "harness" ? "Harness" : "OpenRouter"} · ${a.model} · ${a.effort} effort (declared)`);
  return { record, state, names, complete: isRuleComplete(state),
    title: isExhibitionLimit(state) ? "Move limit reached" : state.over ? state.winner === null ? "Draw" : `${names[state.winner]} wins` : "Unfinished match",
    reason: state.over ? state.reason : "No terminal result recorded",
    entrants, plies: record.events.length, elapsedMs: record.events.reduce((n, e) => n + e.elapsed, 0),
    tokens: sumKnown("tokens"), cost: sumKnown("cost"),
    lastMove: record.events.at(-1)?.label || "No moves yet",
    evidence: "Rules replayed · model identity and execution not attested",
  };
}
export type MatchSummary = ReturnType<typeof summarizeMatch>;

/** Canvas drawing is a local export: no third-party image service or match upload. */
export async function resultImage(record: RecordData): Promise<Blob> {
  const summary = summarizeMatch(record);
  if (!summary.plies) throw Error("Play a move before creating a result image.");
  const canvas = document.createElement("canvas");
  canvas.width = 1200; canvas.height = 675;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw Error("Image export is unavailable in this browser.");
  const text = (value: string, x: number, y: number, size: number, color = "#f0f3ec", max = 590) => {
    ctx.font = `${size >= 30 ? 700 : 400} ${size}px system-ui, sans-serif`;
    ctx.fillStyle = color;
    const chars = Array.from(cleanText(value));
    let line = chars.join("");
    while (ctx.measureText(line).width > max && chars.length) { chars.pop(); line = chars.join("") + "…"; }
    ctx.fillText(line, x, y);
  };
  ctx.fillStyle = "#111513"; ctx.fillRect(0, 0, 1200, 675);
  text("BuilderWars", 48, 67, 38, "#c8fa75");
  text("A Nymrel product", 915, 64, 20, "#aeb8b0", 240);
  text(summary.complete ? "EXHIBITION RESULT" : "UNFINISHED EXHIBITION", 540, 146, 18, "#c8fa75");
  text(summary.title, 540, 209, 40);
  text(summary.record.rules.name, 540, 251, 25, "#d4ddce");
  text(`${summary.names[0]} vs ${summary.names[1]}`, 540, 299, 22);
  text(`1: ${summary.entrants[0]}`, 540, 329, 17, "#b0bcb4");
  text(`2: ${summary.entrants[1]}`, 540, 355, 17, "#b0bcb4");
  text(`${summary.plies} plies · ${summary.reason}`, 540, 393, 21, "#b0bcb4");
  text(`Reported decision time: ${(summary.elapsedMs / 1000).toFixed(2)}s`, 540, 424, 18, "#b0bcb4");
  text(`Accepted-move cost: ${summary.cost === null ? "unknown" : `$${summary.cost.toFixed(4)}`}`, 540, 453, 18, "#b0bcb4");
  text("Rules replayed. Model / execution not attested.", 540, 500, 18, "#c8fa75");
  text("One match, not a general model ranking.", 540, 529, 18, "#b0bcb4");
  text("Replay it. Challenge it. Build your next contender.", 48, 600, 25);
  text("builderwars.com", 48, 639, 21, "#c8fa75");
  text("Share the replay link alongside this image.", 655, 639, 18, "#b0bcb4", 490);
  const { rows, cols, kind } = summary.state.rules;
  const tile = Math.min(430 / cols, 420 / rows);
  const x0 = 48 + (430 - cols * tile) / 2, y0 = 122 + (420 - rows * tile) / 2;
  const chess: Record<string, string> = { wp: "♙", wn: "♘", wb: "♗", wr: "♖", wq: "♕", wk: "♔", bp: "♟", bn: "♞", bb: "♝", br: "♜", bq: "♛", bk: "♚" };
  for (let i = 0; i < rows * cols; i++) {
    const x = x0 + (i % cols) * tile, y = y0 + Math.floor(i / cols) * tile;
    ctx.fillStyle = (Math.floor(i / cols) + i % cols) % 2 ? "#293c2e" : "#354d3c";
    ctx.fillRect(x, y, tile, tile);
    const piece = summary.state.cells[i];
    if (!piece) continue;
    if (kind === "chess") {
      ctx.font = `${tile * 0.75}px "Segoe UI Symbol", serif`;
      ctx.fillStyle = piece.startsWith("w") ? "#f6f8ee" : "#111513";
      ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillText(chess[piece] || piece, x + tile / 2, y + tile / 2);
      ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
    } else {
      ctx.beginPath(); ctx.arc(x + tile / 2, y + tile / 2, tile * 0.35, 0, Math.PI * 2);
      ctx.fillStyle = ["X", "w", "W"].includes(piece) ? "#c8fa75" : "#f3f4df";
      ctx.fill();
      if (kind === "checkers" && piece === piece.toUpperCase()) text("K", x + tile * 0.33, y + tile * 0.66, tile * 0.45, "#111513", tile);
    }
  }
  return new Promise((resolve, reject) => canvas.toBlob(blob => blob ? resolve(blob) : reject(Error("Image export failed. Try downloading the replay instead.")), "image/png"));
}
