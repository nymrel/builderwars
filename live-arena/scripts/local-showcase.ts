/** Manual, opt-in local exhibition. Importing this module makes no requests. */
import { randomUUID } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { RULES, createGame, applyMove, legalMoves, moveLabel, gamePrompt, replay,
  encodeReplay, refereeManifest, type GameState, type RecordData } from "../src/runtime";
import { publicAgent, parseDecision } from "../src/models";
import { safeReplay } from "../src/sharing";

export const ENDPOINT = "http://127.0.0.1:8088/v1/chat/completions";
export const MODEL = "qwen2.5-coder-1.5b-instruct-q4-k-m";
export const LIMITS = Object.freeze({ maxCalls: 18, maxTokens: 64, perCallMs: 15000, totalMs: 180000 });
export type Harness = "plain" | "tactical";
export type ExperimentMode = "strict-json" | "gameplay";
type Body = { model: string; messages: { role: string; content: string }[]; max_tokens: number;
  temperature: number; seed: number; stream: boolean; cache_prompt: boolean;
  response_format?: { type: "json_object"; schema: { type: "object";
    properties: { move: { type: "string"; enum: string[] } }; required: ["move"]; additionalProperties: false } } };
type Usage = { inputTokens: number | null; outputTokens: number | null; totalTokens: number | null };
type Call = { number: number; game: number; seat: 0 | 1; harness: Harness; request: Body;
  dispatched: boolean;
  responseText: string | null; responseStatus: number | null; responseModel: string | null;
  responseProvider: string | null; usage: Usage; elapsedMs: number; failure: string | null };
type Game = { game: number; harnesses: Harness[]; exit: "complete" | "failed" | "capped";
  failure: string | null; record: RecordData; replayUrl: string; winnerHarness: Harness | null };
type Options = { fetchImpl: typeof fetch; now?: () => number; mode?: ExperimentMode;
  limits?: Partial<Record<keyof typeof LIMITS, number>>; onRequest?: (call: Call) => Promise<void>;
  onCall?: (call: Call) => Promise<void>;
  onGame?: (game: Game) => Promise<void> };

/** These are observations, never a replacement move selection policy. */
export function tacticalObservations(state: GameState) {
  const immediateWins: string[] = [], noImmediateOpponentWin: string[] = [];
  for (const move of legalMoves(state)) {
    const next = applyMove(state, move);
    if (next.over && next.winner === state.turn) immediateWins.push(move);
    if (next.over || !legalMoves(next).some(reply => {
      const afterReply = applyMove(next, reply);
      return afterReply.over && afterReply.winner === next.turn;
    })) noImmediateOpponentWin.push(move);
  }
  return { immediateWins, noImmediateOpponentWin };
}

export function requestFor(state: GameState, harness: Harness, mode: ExperimentMode = "strict-json"): Body {
  const observation = harness === "tactical"
    ? `\nReferee-computed tactical observations: ${JSON.stringify(tacticalObservations(state))}. The safety list only checks the opponent's immediate reply; it is not a solved-game guarantee.` : "";
  const body: Body = { model: MODEL, messages: [{ role: "user", content:
    gamePrompt(state, "") + observation + '\nReturn only JSON {"move":"one legal move"}. No markdown or explanation.' }],
  max_tokens: LIMITS.maxTokens, temperature: 0, seed: 42, stream: false, cache_prompt: false };
  if (mode === "gameplay") body.response_format = { type: "json_object", schema: {
    type: "object", properties: { move: { type: "string", enum: legalMoves(state) } },
    required: ["move"], additionalProperties: false,
  } };
  return body;
}

function experimentFor(mode: ExperimentMode) {
  if (mode !== "strict-json" && mode !== "gameplay") throw Error("Unsupported experiment mode");
  return { mode, constraintAssistance: mode === "gameplay"
    ? "Both harnesses request legal-move constrained JSON generation through the same referee-derived move enum. This is constrained gameplay, not an unassisted formatting benchmark."
    : "No constrained generation; strict JSON.parse output grader retained",
    decisionParser: mode === "gameplay" ? "Existing src/models.ts parseDecision; legal validation with no replacement move"
      : "Strict JSON.parse and authoritative legal-move validation",
  };
}

function count(raw: unknown): number | null {
  return typeof raw === "number" && Number.isSafeInteger(raw) && raw >= 0 ? raw : null;
}
function reportLabel(raw: unknown): string | null {
  return typeof raw === "string" && raw.trim() && raw.length <= 160 ? raw : null;
}
function sumKnown(calls: Call[], key: keyof Usage) {
  if (!calls.length || calls.some(call => call.usage[key] === null)) return null;
  const total = calls.reduce((sum, call) => sum + call.usage[key]!, 0);
  return Number.isSafeInteger(total) ? total : null;
}
function limitsFor(override: Options["limits"]) {
  const limits = { ...LIMITS, ...override };
  for (const key of Object.keys(LIMITS) as (keyof typeof LIMITS)[]) {
    if (!Number.isInteger(limits[key]) || limits[key] < 1 || limits[key] > LIMITS[key])
      throw Error(`Invalid ${key}; limits may only be reduced from the fixed ceiling.`);
  }
  return limits;
}

export async function runComparison(options: Options) {
  const mode = options.mode ?? "strict-json", experiment = experimentFor(mode);
  const limits = limitsFor(options.limits), now = options.now ?? (() => performance.now());
  const started = now(), deadline = started + limits.totalMs;
  const calls: Call[] = [], games: Game[] = [];
  for (let gameIndex = 0; gameIndex < 2; gameIndex++) {
    const harnesses: Harness[] = gameIndex === 0 ? ["plain", "tactical"] : ["tactical", "plain"];
    let state = createGame(RULES.tictactoe);
    const record: RecordData = {
      schema: "builderwars.exhibition.v1", id: `local-showcase-${randomUUID()}`,
      createdAt: new Date().toISOString(), rules: { ...RULES.tictactoe }, events: [], status: "Unfinished match",
      agents: harnesses.map(harness => publicAgent({ name: `Local Qwen · ${harness} harness${mode === "gameplay" ? " · constrained" : ""}`, kind: "harness",
        model: MODEL, effort: "default", strategy: harness === "plain" ? "Plain referee board and legal moves"
          : "Referee board, legal moves and immediate tactical observations",
        endpoint: ENDPOINT, key: "" })),
    };
    let exit: Game["exit"] = "complete", failure: string | null = null;
    while (!state.over) {
      if (calls.length >= limits.maxCalls || now() >= deadline) {
        exit = "capped"; failure = calls.length >= limits.maxCalls ? "Total inference call cap reached" : "Total time cap reached";
        break;
      }
      const harness = harnesses[state.turn], request = requestFor(state, harness, mode);
      request.max_tokens = limits.maxTokens;
      const call: Call = { number: calls.length + 1, game: gameIndex + 1, seat: state.turn, harness, request,
        dispatched: false,
        responseText: null, responseStatus: null, responseModel: null, responseProvider: null,
        usage: { inputTokens: null, outputTokens: null, totalTokens: null }, elapsedMs: 0, failure: null };
      calls.push(call); // Count attempted requests, including failed or timed-out calls.
      await options.onRequest?.(structuredClone(call));
      // Persist intent before inference. A slow disk must not open a new request after the deadline.
      if (now() >= deadline) {
        call.failure = "Total time cap reached before request dispatch";
        await options.onCall?.(structuredClone(call));
        exit = "capped"; failure = call.failure;
        break;
      }
      const callStarted = now(), controller = new AbortController();
      let timer: ReturnType<typeof setTimeout> | undefined;
      let accepting = true;
      try {
        const timeout = new Promise<never>((_, reject) => {
          timer = setTimeout(() => { accepting = false; controller.abort(); reject(Error("Inference deadline exceeded")); },
            Math.max(1, Math.min(limits.perCallMs, deadline - now())));
        });
        const data = await Promise.race([timeout, (async () => {
          call.dispatched = true;
          const response = await options.fetchImpl(ENDPOINT, { method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify(request), redirect: "error", credentials: "omit", signal: controller.signal });
          if (!accepting) throw Error("Late response rejected");
          call.responseStatus = response.status;
          const text = await response.text();
          if (!accepting) throw Error("Late response rejected");
          call.responseText = text;
          if (response.redirected || (response.url && response.url !== ENDPOINT) || (response.status >= 300 && response.status < 400))
            throw Error("Redirect or unexpected response URL rejected");
          if (!response.ok) throw Error(`Local runtime returned HTTP ${response.status}`);
          return JSON.parse(text);
        })()]);
        if (now() >= deadline || now() - callStarted >= limits.perCallMs) throw Error("Inference deadline exceeded");
        call.responseModel = reportLabel(data?.model);
        call.responseProvider = reportLabel(data?.provider);
        call.usage = { inputTokens: count(data?.usage?.prompt_tokens), outputTokens: count(data?.usage?.completion_tokens),
          totalTokens: count(data?.usage?.total_tokens) };
        if (call.usage.outputTokens !== null && call.usage.outputTokens > limits.maxTokens)
          throw Error("Runtime reported output above the requested token cap");
        const content = data?.choices?.[0]?.message?.content;
        if (typeof content !== "string") throw Error("Missing model message content");
        const decision = mode === "gameplay" ? parseDecision(content, legalMoves(state)) : JSON.parse(content);
        if (!decision || typeof decision.move !== "string" || !legalMoves(state).includes(decision.move))
          throw Error("Malformed or illegal model move; no repair or substitute applied");
        const next = applyMove(state, decision.move);
        record.events.push({ ply: record.events.length + 1, seat: state.turn, move: decision.move,
          label: moveLabel(decision.move, state), comment: "", elapsed: Math.max(0, now() - callStarted),
          // Runtime metadata can contain a private GGUF path. Preserve it only in call receipts.
          model: `declared/${MODEL}`, tokens: call.usage.totalTokens, cost: null });
        state = next;
      } catch (error) {
        call.failure = error instanceof Error ? error.message : String(error);
        exit = "failed"; failure = call.failure;
      } finally {
        accepting = false;
        controller.abort();
        clearTimeout(timer);
        call.elapsedMs = Math.max(0, now() - callStarted);
        await options.onCall?.(structuredClone(call));
      }
      if (failure) break;
    }
    record.status = state.over ? state.reason : "Unfinished match";
    const validated = replay(record);
    if (validated.state.over !== state.over || validated.state.winner !== state.winner)
      throw Error("Independent record replay disagreed with the played state");
    const publicRecord = safeReplay(validated.record);
    const game: Game = { game: gameIndex + 1, harnesses, exit, failure, record: validated.record,
      replayUrl: `https://builderwars.com/#replay=${await encodeReplay(publicRecord)}`,
      winnerHarness: state.over && state.winner !== null ? harnesses[state.winner] : null };
    games.push(game);
    await options.onGame?.(structuredClone(game));
  }
  return {
    schema: "builderwars.local-showcase.v1", createdAt: new Date().toISOString(),
    experiment,
    classification: "Actual local-model exhibition only when executed against the independently identified runtime; mocked tests are synthetic",
    endpoint: ENDPOINT, requestedModel: MODEL, referee: refereeManifest, limits, temperature: 0, seed: 42,
    replayEventModelMeaning: "Replay event.model is the requested local model declaration, prefixed declared/; it is not runtime attestation. Original response model metadata remains in private call receipts only.",
    harnesses: { plain: "Board and legal moves", tactical: "Same model plus referee-computed immediate wins and opponent-reply safety observations" },
    inputTokens: sumKnown(calls, "inputTokens"), outputTokens: sumKnown(calls, "outputTokens"), totalTokens: sumKnown(calls, "totalTokens"),
    dollarCost: null, electricityCost: null, elapsedMs: Math.max(0, now() - started),
    inferenceCalls: calls.filter(call => call.dispatched).length,
    completedGames: games.filter(game => game.exit === "complete").length,
    failedGames: games.filter(game => game.exit === "failed").length,
    cappedGames: games.filter(game => game.exit === "capped").length,
    limitsOfEvidence: ["Two games are not a general performance or compute-parity benchmark", "No weight learning or promotion",
      "Requested identity and response metadata are declarations, not weight/runtime attestation",
      "Harness observations add computation and prompt tokens", "Cancellation stops new requests but cannot attest that local computation immediately stopped",
      "Unknown input/output usage and dollar/electricity costs remain unknown"], calls, games,
  };
}

async function main() {
  const option = process.argv.slice(2).join(" ");
  if (option !== "--run" && option !== "--run-gameplay") {
    console.log("No inference started. Opt in explicitly: npx --no-install tsx scripts/local-showcase.ts --run (strict JSON) or --run-gameplay (constrained gameplay)");
    return;
  }
  const mode: ExperimentMode = option === "--run-gameplay" ? "gameplay" : "strict-json";
  const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
  const parent = resolve(root, "output", "playwright");
  await mkdir(parent, { recursive: true });
  const output = resolve(parent, `local-model-showcase-${new Date().toISOString().replace(/[:.]/g, "-")}-${randomUUID()}`);
  await mkdir(output); // Unique directory; never overwrite earlier receipts.
  const save = (name: string, value: unknown) => writeFile(resolve(output, name), JSON.stringify(value, null, 2), { flag: "wx" });
  await save("intent.json", { endpoint: ENDPOINT, requestedModel: MODEL, limits: LIMITS, experiment: experimentFor(mode),
    classification: "Manual local inference; no cloud or keys", startedAt: new Date().toISOString() });
  console.log(`Recording to ${output}`);
  const receipt = await runComparison({ fetchImpl: fetch, mode,
    onRequest: call => save(`call-${String(call.number).padStart(2, "0")}-request.json`, call),
    onCall: call => save(`call-${String(call.number).padStart(2, "0")}.json`, call),
    onGame: async game => {
      await save(`game-${game.game}.json`, game.record);
      await save(`game-${game.game}-public.json`, safeReplay(game.record));
      await save(`game-${game.game}-result.json`, { ...game, record: undefined });
    },
  });
  await save("receipt.json", receipt);
  console.log(JSON.stringify({ output, inferenceCalls: receipt.inferenceCalls, completedGames: receipt.completedGames,
    failedGames: receipt.failedGames, cappedGames: receipt.cappedGames,
    games: receipt.games.map(({ game, exit, failure, winnerHarness }) => ({ game, exit, failure, winnerHarness })) }));
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main().catch(error => { console.error(error); process.exitCode = 1; });
}
