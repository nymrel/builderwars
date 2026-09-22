import { applyMove, createGame, legalMoves, validateRules, type GameState } from "./runtime";
import { decide, parseDecision, publicAgent, type Agent, type Model, type PublicAgent } from "./models";

// Agent Readiness Check — the four-advisor council's first recommendation from the
// 2026-09-20 studio playtest (experiments/studio-playtest-20260920). Before a real
// match, confirm a contender can answer real request shapes: fixed positions from the
// existing referee engines, one reply per position, no retries, no ranking.
// It measures protocol validity and completion — never strategic strength.

export type ReadinessOutcome =
  | "valid"
  | "invalid-reply"
  | "timeout"
  | "connection-error"
  | "skipped";

export type ReadinessPositionResult = {
  id: string;
  game: string;
  turn: 0 | 1;
  movesSoFar: string[];
  legalMoves: string[];
  outcome: ReadinessOutcome;
  latencyMs: number | null;
  replyMove: string | null;
  reportedModel: string | null;
  detail: string;
};

export type ReadinessReceipt = {
  schema: "builderwars.readiness.receipt.v1";
  generatedAt: string;
  contender: PublicAgent;
  suite: {
    id: string;
    game: string;
    positionCount: number;
    timeCapMs: number;
    oneReplyPerPosition: true;
  };
  positions: ReadinessPositionResult[];
  summary: {
    positions: number;
    valid: number;
    invalidReply: number;
    timeout: number;
    connectionError: number;
    skipped: number;
  };
  notes: string[];
};

export type ReadinessSuite = {
  id: "tictactoe" | "nim";
  label: string;
  sequences: string[][];
};

const nimMove = (heap: number, take: number) => JSON.stringify({ heap, take });

// Every sequence replays through the real engine; buildPosition asserts each resulting
// position is still open with moves available, so suites stay legal by construction.
export const READINESS_SUITES: Record<"tictactoe" | "nim", ReadinessSuite> = {
  tictactoe: {
    id: "tictactoe",
    label: "Tic-tac-toe · 10 fixed positions",
    sequences: [
      [],
      ["4"],
      ["0", "4"],
      ["4", "0", "8"],
      ["0", "8", "1"],
      ["2", "4", "6", "0"],
      ["3", "4", "5"],
      ["0", "1", "2", "3", "4"],
      ["8", "0", "6", "2", "5"],
      ["1", "3", "5", "7"],
    ],
  },
  nim: {
    id: "nim",
    label: "Nim · 10 fixed positions",
    sequences: [
      [],
      [nimMove(0, 1)],
      [nimMove(2, 3)],
      [nimMove(0, 2), nimMove(1, 2)],
      [nimMove(2, 6), nimMove(0, 1), nimMove(1, 4)],
      [nimMove(1, 4), nimMove(2, 3), nimMove(0, 2)],
      [nimMove(0, 1), nimMove(1, 1), nimMove(2, 1), nimMove(0, 1)],
      [nimMove(2, 4), nimMove(1, 3), nimMove(0, 1), nimMove(2, 1)],
      [nimMove(1, 2), nimMove(2, 2), nimMove(0, 1), nimMove(1, 1)],
      [nimMove(0, 2), nimMove(1, 3), nimMove(2, 5), nimMove(0, 1)],
    ],
  },
};

export function buildPosition(suiteId: string, index: number): { id: string; state: GameState } {
  const suite = READINESS_SUITES[suiteId as "tictactoe" | "nim"];
  if (!suite) throw Error("Choose the tic-tac-toe or Nim readiness suite.");
  if (!Number.isInteger(index) || index < 0 || index >= suite.sequences.length)
    throw Error("Readiness position is out of range.");
  let state = createGame(validateRules({ kind: suite.id, name: suite.id === "nim" ? "Nim" : "Tic-tac-toe" }));
  for (const move of suite.sequences[index]) state = applyMove(state, move);
  if (state.over || !legalMoves(state).length)
    throw Error(`Readiness suite ${suite.id} position ${index + 1} is not an open position.`);
  return { id: `${suite.id}-${String(index + 1).padStart(2, "0")}`, state };
}

export type ReadinessDecision = {
  move: string;
  model: string | null;
  elapsed: number;
};

export type ReadinessDecider = (
  state: GameState,
  agent: Agent,
  signal: AbortSignal,
) => Promise<ReadinessDecision>;

// The default decider is the same decide() path a real match uses, so readiness
// exercises the real request/response contract including connection preflight.
const defaultDecider =
  (models: Model[], maxTokens: number): ReadinessDecider =>
  async (state, agent, signal) => {
    const decision = await decide(state, agent, maxTokens, signal, models, undefined);
    return { move: decision.move, model: decision.model || null, elapsed: decision.elapsed };
  };

export function classifyReadinessFailure(error: unknown): {
  outcome: Exclude<ReadinessOutcome, "valid" | "skipped">;
  detail: string;
} {
  const err = error instanceof Error ? error : new Error(String(error));
  if (err.name === "TimeoutError" || err.name === "AbortError")
    return {
      outcome: "timeout",
      detail:
        "No usable reply arrived within the per-position time cap. Timeouts are latency evidence, not strategy evidence.",
    };
  if (err.message.startsWith("Illegal or unreadable move"))
    return {
      outcome: "invalid-reply",
      detail:
        "The reply was not a schema-valid, legal move object. It was paused, not replaced; no retry was sent.",
    };
  return {
    outcome: "connection-error",
    detail: err.message.slice(0, 300) || "The request failed before a reply could be validated.",
  };
}

export const READINESS_NOTES = [
  "One reply per position; invalid replies are never retried or replaced.",
  "Readiness measures protocol validity and completion, not strategic strength; it supports no ranking or leaderboard.",
  "Raw provider replies are not retained; the receipt records the validator verdict and failure class only.",
  "Latency is local wall time around the request and validation, measured by the arena.",
  "Results are local evidence for this browser session; download the receipt to keep it.",
];

export async function runReadinessCheck(options: {
  agent: Agent;
  suiteId: string;
  models?: Model[];
  maxTokens?: number;
  timeCapMs?: number;
  signal?: AbortSignal;
  decider?: ReadinessDecider;
  onPosition?: (result: ReadinessPositionResult, index: number, total: number) => void;
}): Promise<ReadinessReceipt> {
  const { agent, suiteId } = options;
  if (agent.kind === "human")
    throw Error(
      "Readiness checks a connected contender or built-in. Human seats answer on the board, not through the protocol.",
    );
  const suite = READINESS_SUITES[suiteId as "tictactoe" | "nim"];
  if (!suite) throw Error("Choose the tic-tac-toe or Nim readiness suite.");
  const timeCapMs = options.timeCapMs ?? 45000;
  const decider = options.decider ?? defaultDecider(options.models ?? [], options.maxTokens ?? 2048);

  const positions: ReadinessPositionResult[] = [];
  for (let index = 0; index < suite.sequences.length; index++) {
    const { id, state } = buildPosition(suite.id, index);
    const legal = legalMoves(state);
    const base = {
      id,
      game: suite.id,
      turn: state.turn,
      movesSoFar: [...suite.sequences[index]],
      legalMoves: legal,
    };
    if (options.signal?.aborted) {
      const result: ReadinessPositionResult = {
        ...base,
        outcome: "skipped",
        latencyMs: null,
        replyMove: null,
        reportedModel: null,
        detail: "Check stopped before this position was attempted.",
      };
      positions.push(result);
      options.onPosition?.(result, index, suite.sequences.length);
      continue;
    }
    const started = Date.now();
    // A cleared per-position timer with an explicit abort relay: the cap always
    // governs (no AbortSignal.any required), nothing outlives the check, and
    // external stops propagate into this position's signal.
    const controller = new AbortController();
    const timer = setTimeout(
      () =>
        controller.abort(
          new DOMException("No usable reply within the readiness time cap.", "TimeoutError"),
        ),
      timeCapMs,
    );
    const relayStop = () => controller.abort(options.signal?.reason);
    options.signal?.addEventListener("abort", relayStop, { once: true });
    try {
      const decision = await decider(state, agent, controller.signal);
      const result: ReadinessPositionResult = {
        ...base,
        outcome: "valid",
        latencyMs: Math.round(
          Number.isFinite(decision.elapsed) ? decision.elapsed : Date.now() - started,
        ),
        replyMove: decision.move,
        reportedModel: decision.model,
        detail: "A schema-valid, legal move was accepted on the first reply.",
      };
      positions.push(result);
      options.onPosition?.(result, index, suite.sequences.length);
    } catch (error) {
      const failure = classifyReadinessFailure(error);
      const externallyStopped =
        !!options.signal?.aborted && !(error instanceof Error && error.name === "TimeoutError");
      const result: ReadinessPositionResult = {
        ...base,
        outcome: externallyStopped ? "skipped" : failure.outcome,
        latencyMs: Date.now() - started,
        replyMove: null,
        reportedModel: null,
        detail: externallyStopped
          ? "Check stopped while awaiting this reply; no retry was sent."
          : failure.detail,
      };
      positions.push(result);
      options.onPosition?.(result, index, suite.sequences.length);
    } finally {
      clearTimeout(timer);
      options.signal?.removeEventListener("abort", relayStop);
    }
  }

  const count = (outcome: ReadinessOutcome) =>
    positions.filter((position) => position.outcome === outcome).length;
  return {
    schema: "builderwars.readiness.receipt.v1",
    generatedAt: new Date().toISOString(),
    contender: publicAgent(agent),
    suite: {
      id: suite.id,
      game: suite.id,
      positionCount: suite.sequences.length,
      timeCapMs,
      oneReplyPerPosition: true,
    },
    positions,
    summary: {
      positions: positions.length,
      valid: count("valid"),
      invalidReply: count("invalid-reply"),
      timeout: count("timeout"),
      connectionError: count("connection-error"),
      skipped: count("skipped"),
    },
    notes: READINESS_NOTES,
  };
}

// Re-exported for the UI and tests: readiness borrows the existing validator, so a
// "valid" verdict means exactly "the referee would have accepted this reply".
export { parseDecision };
