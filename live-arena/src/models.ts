import { botMove, gamePrompt, legalMoves, type GameState } from "./runtime";
import type { MemoryContext } from "./learning";
export type Agent = {
  name: string;
  kind: "bot" | "human" | "openrouter" | "harness";
  model: string;
  effort: string;
  strategy: string;
  endpoint: string;
  key: string;
};
export type PublicAgent = Pick<
  Agent,
  "name" | "kind" | "model" | "effort" | "strategy"
>;
export type Model = {
  id: string;
  name: string;
  pricing?: { prompt: string; completion: string };
  supported_parameters?: string[];
  reasoning?: { supported_efforts?: string[] | null; mandatory?: boolean };
};
export type Decision = {
  move: string;
  comment: string;
  elapsed: number;
  model: string;
  tokens: number | null;
  cost: number | null;
};
export const EFFORTS = [
  "none",
  "minimal",
  "low",
  "medium",
  "high",
  "xhigh",
  "max",
];
export function publicAgent(a: Agent): PublicAgent {
  return {
    name: a.name.slice(0, 64),
    kind: a.kind,
    model: a.model.slice(0, 160),
    effort: a.effort.slice(0, 20),
    strategy: a.strategy.slice(0, 1000),
  };
}
export function supportedEfforts(model?: Model): string[] {
  if (!model?.reasoning) return ["default"];
  const efforts =
    model.reasoning.supported_efforts === null
      ? EFFORTS
      : (model.reasoning.supported_efforts ?? []);
  return [
    "default",
    ...efforts.filter(
      (e) =>
        EFFORTS.includes(e) && (!model.reasoning?.mandatory || e !== "none"),
    ),
  ];
}
export async function catalog(signal?: AbortSignal): Promise<Model[]> {
  const res = await fetch("https://openrouter.ai/api/v1/models", {
    signal,
    credentials: "omit",
    redirect: "error",
  });
  if (!res.ok)
    throw Error(
      "Model catalog is unavailable. Retry or use a built-in opponent.",
    );
  const body = await res.json();
  if (!Array.isArray(body.data)) throw Error("Invalid model catalog.");
  return body.data
    .filter(
      (m: Model) => typeof m.id === "string" && typeof m.name === "string",
    )
    .sort((a: Model, b: Model) => a.name.localeCompare(b.name));
}
export function parseDecision(
  raw: unknown,
  legal: string[],
): { move: string; comment: string } {
  if (typeof raw === "string") {
    const text = raw
      .trim()
      .replace(/^```(?:json)?\s*/, "")
      .replace(/\s*```$/, "");
    try {
      raw = JSON.parse(text);
    } catch {
      raw = { move: text };
    }
  }
  if (
    !raw ||
    typeof raw !== "object" ||
    typeof (raw as any).move !== "string" ||
    !legal.includes((raw as any).move)
  )
    throw Error(
      "Illegal or unreadable move. Match paused; no replacement move was played.",
    );
  return {
    move: (raw as any).move,
    comment:
      typeof (raw as any).comment === "string"
        ? (raw as any).comment.slice(0, 240)
        : "",
  };
}
export function validateEndpoint(raw: string): URL {
  const url = new URL(raw);
  if (url.username || url.password || url.hash || url.search)
    throw Error(
      "Use a plain HTTPS harness URL without embedded credentials or query parameters.",
    );
  if (url.protocol !== "https:" && !(url.origin === "http://127.0.0.1:8765"))
    throw Error(
      "Harnesses need HTTPS, or the local bridge at http://127.0.0.1:8765.",
    );
  return url;
}
export function validateConnection(a: Agent, models: Model[]) {
  if (a.kind === "openrouter") {
    if (!a.key) throw Error("Add your OpenRouter key in Connections.");
    const model = models.find(m => m.id === a.model);
    if (!model) throw Error("Choose a model from the current catalog.");
    if (!supportedEfforts(model).includes(a.effort))
      throw Error("The selected reasoning effort is not advertised for this model.");
  } else if (a.kind === "harness") {
    const url = validateEndpoint(a.endpoint);
    if (url.origin === "http://127.0.0.1:8765") {
      if (url.pathname !== "/move") throw Error("Use the local bridge endpoint http://127.0.0.1:8765/move.");
      if (!a.key) throw Error("Add the temporary local bridge token.");
    }
  }
}
type ConnectionCheck = { checked: boolean; message: string };
const checkedConnections = new WeakMap<Agent, { identity: string; until: number; result: ConnectionCheck }>();
const connectionGenerations = new WeakMap<Agent, number>();
const connectionIdentity = (a: Agent) => JSON.stringify([a.kind, a.key, a.endpoint, a.model, a.effort]);
export function forgetConnectionCheck(a: Agent) {
  checkedConnections.delete(a);
  connectionGenerations.set(a, (connectionGenerations.get(a) ?? 0) + 1);
}
/** A bounded non-inference probe. Never probe arbitrary HTTPS harness URLs. */
export async function checkConnection(a: Agent, models: Model[], signal: AbortSignal, force = true): Promise<ConnectionCheck> {
  validateConnection(a, models);
  signal.throwIfAborted();
  if (force) forgetConnectionCheck(a);
  const identity = connectionIdentity(a), generation = connectionGenerations.get(a) ?? 0;
  const cached = checkedConnections.get(a);
  if (cached && cached.identity === identity && cached.until > Date.now()) return cached.result;
  const local = a.kind === "harness" && validateEndpoint(a.endpoint).origin === "http://127.0.0.1:8765";
  if (a.kind !== "openrouter" && !local) return {
    checked: a.kind !== "harness",
    message: a.kind === "harness" ? "HTTPS configuration is valid. Authentication, CORS, connectivity and limits are unchecked: this harness has no standard non-inference probe. Start a capped match only when your endpoint is ready." : "Local play needs no provider connection or model request.",
  };
  const timeout = AbortSignal.any([signal, AbortSignal.timeout(15000)]);
  let result: ConnectionCheck;
  try {
    const response = await fetch(local ? "http://127.0.0.1:8765/health" : "https://openrouter.ai/api/v1/key", {
      method: "GET", headers: { Authorization: `Bearer ${a.key}` }, signal: timeout,
      credentials: "omit", redirect: "error", cache: "no-store",
    });
    if (!response.ok) throw Error(`Connection check returned ${response.status}. ${response.status === 401 ? "Check the key or local token." : response.status === 429 ? "Rate or session limit reached; wait or inspect your provider limits." : local && response.status === 404 ? "Update your local bridge to support /health." : "Check connectivity and provider/bridge availability."}`);
    const body = await boundedJson(response, 64000);
    timeout.throwIfAborted();
    if (local) {
      if (body?.schema !== "builderwars.bridge.health.v1" || !Number.isInteger(body.remainingCalls) || body.remainingCalls < 0 || body.remainingCalls > 1000 || typeof body.busy !== "boolean") throw Error("Invalid local bridge health response.");
      if (!body.remainingCalls) throw Error("Local bridge session request limit reached. No model request was sent.");
      if (body.busy) throw Error("The local bridge is busy. Wait for its current request; no additional model request was sent.");
      result = { checked: true, message: `Local token and origin accepted; ${body.remainingCalls} session calls reported remaining. No model invoked. Model/effort are configured in your local client, not by website labels; provider entitlement and execution remain untested.` };
    } else {
      const data = body?.data;
      if (!data || typeof data !== "object" || Array.isArray(data) || typeof data.is_free_tier !== "boolean") throw Error("Invalid key-info response.");
      if (data.is_management_key === true || data.is_provisioning_key === true) throw Error("Use an inference API key, not a management or provisioning key.");
      const exhausted = typeof data.limit_remaining === "number" && Number.isFinite(data.limit_remaining) && data.limit_remaining <= 0;
      result = { checked: true, message: `API key recognized. ${exhausted ? "The key reports no remaining configured allowance; inspect its limits. " : ""}No model invoked. Model access, current rate limits and execution are not proven; check provider billing and limits before play.` };
    }
  } catch (error) {
    // Do not display raw network/provider payloads: they may contain account data.
    if (signal.aborted) signal.throwIfAborted();
    if (timeout.aborted) {
      const error = new Error("Connection check timed out after 15 seconds. No model invoked.");
      error.name = "ConnectionCheckTimeout";
      throw error;
    }
    if (error instanceof TypeError || error instanceof SyntaxError) throw Error("Connection check failed. Check network/CORS, bridge version and browser local-network permission.");
    throw error;
  }
  signal.throwIfAborted();
  if (identity !== connectionIdentity(a) || generation !== (connectionGenerations.get(a) ?? 0))
    throw Error("Connection changed during the check. Check the current configuration again.");
  checkedConnections.set(a, { identity, until: Date.now() + 60000, result });
  return result;
}
export async function decide(
  s: GameState,
  a: Agent,
  maxTokens: number,
  signal: AbortSignal,
  models: Model[],
  memory?: MemoryContext,
): Promise<Decision> {
  const started = performance.now(),
    legal = legalMoves(s);
  if (a.kind === "bot")
    return {
      move: botMove(s, a.model),
      comment:
        a.model === "random"
          ? "Random legal move."
          : "Two-ply tactical search.",
      elapsed: performance.now() - started,
      model: `builtin/${a.model}`,
      tokens: null,
      cost: 0,
    };
  if (a.kind === "human") throw Error("Choose a move on the board.");
  await checkConnection(a, models, signal, false);
  signal.throwIfAborted();
  let res: Response,
    actual = "",
    tokens: number | null = null,
    cost: number | null = null,
    content: unknown;
  const timeout = AbortSignal.any([signal, AbortSignal.timeout(120000)]);
  if (a.kind === "openrouter") {
    if (!a.key) throw Error("Add your OpenRouter key in Connections.");
    const model = models.find((m) => m.id === a.model);
    if (!model) throw Error("Choose a model from the current catalog.");
    if (!supportedEfforts(model).includes(a.effort))
      throw Error(
        "The selected reasoning effort is not advertised for this model.",
      );
    const body: Record<string, unknown> = {
      model: a.model,
      messages: [{ role: "user", content: gamePrompt(s, a.strategy) + (memory ? `\n\n${memory.prompt}` : "") }],
      max_tokens: maxTokens,
      provider: { allow_fallbacks: false },
      stream: false,
    };
    if (a.effort !== "default")
      body.reasoning = { effort: a.effort, exclude: true };
    res = await fetch("https://openrouter.ai/api/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${a.key}`,
        "X-Title": "BuilderWars",
      },
      body: JSON.stringify(body),
      signal: timeout,
      credentials: "omit",
      redirect: "error",
    });
    if (!res.ok)
      throw Error(
        `OpenRouter returned ${res.status}. Check your key, balance, model access or rate limit.`,
      );
    const data = await boundedJson(res);
    content = data.choices?.[0]?.message?.content;
    actual = typeof data.model === "string" && data.model.trim() ? data.model : "provider/unreported";
    tokens = Number.isFinite(data.usage?.total_tokens)
      ? data.usage.total_tokens
      : null;
    cost = Number.isFinite(data.usage?.cost) ? data.usage.cost : null;
  } else {
    const url = validateEndpoint(a.endpoint);
    res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(a.key ? { Authorization: `Bearer ${a.key}` } : {}),
      },
      body: JSON.stringify({
        schema: "builderwars.move.v1",
        game: s.rules,
        position: s.fen || s.cells,
        turn: s.turn,
        moves: s.moves,
        legalMoves: legal,
        model: a.model,
        effort: a.effort,
        strategy: a.strategy,
        ...(memory ? { practiceMemory: memory.prompt } : {}),
        maxTokens,
      }),
      signal: timeout,
      credentials: "omit",
      redirect: "error",
    });
    if (!res.ok)
      throw Error(
        `Harness returned ${res.status}. Check its connection, origin permission and local token.`,
      );
    const data = await boundedJson(res);
    content = data;
    actual =
      typeof data.model === "string" && data.model.trim() ? data.model : "harness/unreported";
    tokens = Number.isFinite(data.tokens) ? data.tokens : null;
  }
  return {
    ...parseDecision(content, legal),
    elapsed: performance.now() - started,
    model: actual.slice(0, 160),
    tokens: tokens !== null && tokens >= 0 ? tokens : null,
    cost: cost !== null && cost >= 0 ? cost : null,
  };
}
async function boundedJson(response: Response, limit = 1000000) {
  const reader = response.body?.getReader();
  if (!reader) throw Error("Empty model response.");
  let size = 0;
  const chunks: Uint8Array[] = [];
  while (true) {
    const part = await reader.read();
    if (part.done) break;
    size += part.value.length;
    if (size > limit) {
      await reader.cancel();
      throw Error("Response exceeds the allowed size.");
    }
    chunks.push(part.value);
  }
  return JSON.parse(await new Blob(chunks as BlobPart[]).text());
}
