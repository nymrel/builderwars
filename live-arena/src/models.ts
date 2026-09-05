import { botMove, gamePrompt, gamePosition, legalMoves, type GameState } from "./games";
import { validateProvenance, type BuilderProvenance } from "./provenance";
export type Agent = {
  name: string;
  kind: "bot" | "human" | "openrouter" | "harness";
  model: string;
  effort: string;
  strategy: string;
  endpoint: string;
  key: string;
  provenance?: BuilderProvenance;
};
export type PublicAgent = Pick<
  Agent,
  "name" | "kind" | "model" | "effort" | "strategy" | "provenance"
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
    ...(a.provenance !== undefined ? { provenance: validateProvenance(a.provenance) } : {}),
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
export async function decide(
  s: GameState,
  a: Agent,
  maxTokens: number,
  signal: AbortSignal,
  models: Model[],
): Promise<Decision> {
  const started = performance.now(),
    legal = legalMoves(s);
  if (a.kind === "bot")
    return {
      move: botMove(s, a.model),
      comment:
        a.model === "random"
          ? "Random legal move."
          : s.rules.kind === "nim" ? "Built-in solved Nim strategy (XOR)." : "Two-ply tactical search.",
      elapsed: performance.now() - started,
      model: `builtin/${a.model}`,
      tokens: null,
      cost: 0,
    };
  if (a.kind === "human") throw Error("Choose a move on the board.");
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
      messages: [{ role: "user", content: gamePrompt(s, a.strategy) }],
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
    actual = typeof data.model === "string" ? data.model : a.model;
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
        position: gamePosition(s),
        turn: s.turn,
        moves: s.moves,
        legalMoves: legal,
        model: a.model,
        effort: a.effort,
        strategy: a.strategy,
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
      typeof data.model === "string" ? data.model : "custom/self-reported";
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
async function boundedJson(response: Response) {
  const reader = response.body?.getReader();
  if (!reader) throw Error("Empty model response.");
  let size = 0;
  const chunks: Uint8Array[] = [];
  while (true) {
    const part = await reader.read();
    if (part.done) break;
    size += part.value.length;
    if (size > 1000000) {
      await reader.cancel();
      throw Error("Model response exceeds 1 MB.");
    }
    chunks.push(part.value);
  }
  return JSON.parse(await new Blob(chunks as BlobPart[]).text());
}
