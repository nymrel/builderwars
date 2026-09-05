import { applyMove, createGame, legalMoves, replay, sha256, type GameState, type Rules, type RecordData } from "./runtime";
import type { Agent } from "./models";
import { isRuleComplete } from "./outcome";

export const MEMORY_SCHEMA = "builderwars.practice-memory.v1";
export const MEMORY_KEY = MEMORY_SCHEMA;
type MistakeKind = "missed-win" | "allowed-immediate-loss";
export type Mistake = { kind: MistakeKind; ply: number; seat: number; played: string; better: string[]; position: string[] };
type Episode = { profile: string; source: string; rules: string; mistakes: Mistake[] };
export type MemorySnapshot = { schema: typeof MEMORY_SCHEMA; episodes: Episode[] };
export type MemoryContext = { schema: typeof MEMORY_SCHEMA; mode: "practice" | "frozen-evaluation"; digest: string; sources: string[]; prompt: string };
type StoragePort = Pick<Storage, "getItem" | "setItem" | "removeItem">;
const MAX_EPISODES = 64;
const hashPattern = /^[a-f0-9]{64}$/;
const ruleKey = (r: Rules) => JSON.stringify([r.kind, r.rows, r.cols, r.connect, r.gravity]);
export const supportsLearning = (r: Rules) => ["connect4", "tictactoe", "custom"].includes(r.kind) && r.rows * r.cols <= 42;

// Credentials are never part of persisted memory. Hash the contender configuration
// to isolate different strategies and harness endpoints without storing their text.
export function profileKey(a: Agent) {
  return sha256(JSON.stringify([a.name, a.kind, a.model, a.effort, a.strategy, a.kind === "harness" ? a.endpoint : ""]));
}

/** Complete, replay-verified games only. No verdict is inferred from status or comments. */
export function analyzePractice(raw: unknown): { record: RecordData; mistakes: Mistake[] } {
  const { record, state: final } = replay(raw);
  if (!isRuleComplete(final)) throw Error("Practice needs a rule-complete game.");
  if (!supportsLearning(record.rules)) throw Error("Tactical practice memory supports connect games up to 42 cells.");
  const mistakes: Mistake[] = [];
  let state = createGame(record.rules);
  for (const event of record.events) {
    const seat = state.turn;
    const choices = legalMoves(state).map(move => ({ move, next: applyMove(state, move) }));
    const wins = choices.filter(c => c.next.over && c.next.winner === seat).map(c => c.move);
    if (wins.length && !wins.includes(event.move)) {
      mistakes.push({ kind: "missed-win", ply: event.ply, seat, played: event.move, better: wins, position: [...state.cells] });
    } else if (!wins.length) {
      const losesImmediately = (s: GameState) => !s.over && legalMoves(s).some(move => {
        const next = applyMove(s, move);
        return next.over && next.winner === 1 - seat;
      });
      const safe = choices.filter(c => !losesImmediately(c.next)).map(c => c.move);
      const played = choices.find(c => c.move === event.move)!;
      if (safe.length && losesImmediately(played.next))
        mistakes.push({ kind: "allowed-immediate-loss", ply: event.ply, seat, played: event.move, better: safe, position: [...state.cells] });
    }
    state = applyMove(state, event.move);
  }
  return { record, mistakes };
}

/** Evaluation diagnostics are read-only and never passed to remember(). */
export function scoreTactics(records: unknown[]) {
  const contenders = [0, 1].map(() => ({ decisions: 0, missedWins: 0, avoidableLosses: 0 }));
  let reviewedGames = 0, excludedGames = 0;
  records.forEach((raw, index) => {
    try {
      const { record, mistakes } = analyzePractice(raw);
      reviewedGames++;
      for (const event of record.events) contenders[(event.seat + index) % 2].decisions++;
      for (const mistake of mistakes) {
        const contender = contenders[(mistake.seat + index) % 2];
        if (mistake.kind === "missed-win") contender.missedWins++;
        else contender.avoidableLosses++;
      }
    } catch { excludedGames++; }
  });
  return { reviewedGames, excludedGames, contenders };
}

function readSnapshot(raw: string | null): MemorySnapshot {
  const empty: MemorySnapshot = { schema: MEMORY_SCHEMA, episodes: [] };
  if (!raw || raw.length > 256000) return empty;
  try {
    const value = JSON.parse(raw);
    if (value.schema !== MEMORY_SCHEMA || !Array.isArray(value.episodes) || value.episodes.length > MAX_EPISODES) return empty;
    for (const e of value.episodes) {
      if (!hashPattern.test(e.profile) || !hashPattern.test(e.source) || typeof e.rules !== "string" || e.rules.length > 100 || !Array.isArray(e.mistakes) || e.mistakes.length > 8) return empty;
      for (const m of e.mistakes) {
        if (!["missed-win", "allowed-immediate-loss"].includes(m.kind) || !Number.isInteger(m.ply) || m.ply < 1 || m.ply > 42 || ![0, 1].includes(m.seat) || !/^\d{1,2}$/.test(m.played) || !Array.isArray(m.better) || m.better.length > 42 || !m.better.length || !m.better.every((n: unknown) => typeof n === "string" && /^\d{1,2}$/.test(n)) || !Array.isArray(m.position) || m.position.length > 42 || !m.position.every((n: unknown) => ["", "w", "b"].includes(n as string))) return empty;
      }
    }
    // Copy only the schema fields. Stored text is never allowed to become instructions.
    return { schema: MEMORY_SCHEMA, episodes: value.episodes.map((e: Episode) => ({ profile: e.profile, source: e.source, rules: e.rules, mistakes: e.mistakes.map(m => ({ kind: m.kind, ply: m.ply, seat: m.seat, played: m.played, better: [...m.better], position: [...m.position] })) })) };
  } catch { return empty; }
}

export class PracticeMemory {
  private data: MemorySnapshot;
  private generation = 0;
  persistent = true;
  constructor(private storage?: StoragePort) {
    let raw: string | null = null;
    try { raw = storage?.getItem(MEMORY_KEY) ?? null; } catch { this.persistent = false; }
    if (!storage) this.persistent = false;
    this.data = readSnapshot(raw);
  }
  snapshot(): MemorySnapshot { return structuredClone(this.data); }
  get episodeCount() { return this.data.episodes.length; }
  clear() {
    this.generation++;
    this.data = { schema: MEMORY_SCHEMA, episodes: [] };
    try { this.storage?.removeItem(MEMORY_KEY); } catch { this.persistent = false; }
  }
  async remember(raw: unknown, agents: Agent[]): Promise<number> {
    const generation = this.generation;
    const { record, mistakes } = analyzePractice(raw);
    const source = await sha256(JSON.stringify([record.id, record.rules, record.events.map(e => e.move)]));
    const profiles = await Promise.all(agents.map(profileKey));
    if (generation !== this.generation) return 0;
    let added = 0;
    for (let seat = 0; seat < 2; seat++) {
      if (!["openrouter", "harness"].includes(agents[seat]?.kind)) continue;
      const profile = profiles[seat];
      if (this.data.episodes.some(e => e.profile === profile && e.source === source)) continue;
      const errors = mistakes.filter(m => m.seat === seat).slice(-8);
      this.data.episodes.push({ profile, source, rules: ruleKey(record.rules), mistakes: errors });
      added += errors.length;
    }
    this.data.episodes = this.data.episodes.slice(-MAX_EPISODES);
    try { this.storage?.setItem(MEMORY_KEY, JSON.stringify(this.data)); } catch { this.persistent = false; }
    return added;
  }
  async context(a: Agent, rules: Rules, mode: MemoryContext["mode"], snapshot = this.snapshot()): Promise<MemoryContext | undefined> {
    if (!["openrouter", "harness"].includes(a.kind) || !supportsLearning(rules)) return;
    const profile = await profileKey(a);
    const episodes = snapshot.episodes.filter(e => e.profile === profile && e.rules === ruleKey(rules));
    const examples = episodes.flatMap(e => e.mistakes.map(m => ({ source: e.source, ...m }))).slice(-4);
    if (!examples.length) return;
    const sources = [...new Set(examples.map(m => m.source))];
    const prompt = "Lessons from your previous completed practice games (fixed model weights; these are past positions, not the current board). Before choosing, check all legal immediate wins, then all opponent immediate winning replies. A forced loss is not an avoidable mistake. Past board cells use empty string for empty, w first seat, b second seat; moves use the game's legal-move encoding.\n" + examples.map(m => `Past ply ${m.ply}, seat ${m.seat}: ${m.kind}; board ${JSON.stringify(m.position)}; played ${m.played}; ${m.kind === "missed-win" ? "winning" : "safe against immediate loss"} alternatives [${m.better.join(",")}].`).join("\n");
    return { schema: MEMORY_SCHEMA, mode, sources, digest: await sha256(prompt), prompt };
  }
}
