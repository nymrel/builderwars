/** Immutable configuration and bounded execution. Credentials are transient, never fields here. */
import { sha256, refereeManifest, validateRules, legalMoves, createGame, replayStepper, type Rules, type GameState } from "./runtime";
import { FEATURE_COUNT, FEATURE_VERSION, policyMove, seeded, WorkBudget } from "./self-improvement";
import { STRATEGIC_FEATURE_COUNT, STRATEGIC_FEATURE_VERSION, STRATEGIC_MODEL, strategicMove } from "./strategic-value";

export const VERSION_SCHEMA = "builderwars.frontier-version.v1";
export type RuntimeIdentity = {
  provider: "local" | "openrouter" | "harness";
  requestedModel: string; resolvedModel: string | null;
  evidence: "bundled-code" | "provider-response" | "self-reported" | "unreported";
  reasoning: string;
};
export type VersionConfig = {
  rules: Rules; referee: string; runtime: RuntimeIdentity;
  harness: { kind: "linear-value" | "strategic-value" | "model"; source: string; protocol: string };
  prompt: string; memory: { mode: "none" | "frozen"; content: string };
  tools: { id: string; source: string; parameters: string }[];
  sampling: { temperature: number | null; seed: number | null };
  value: { features: typeof FEATURE_VERSION | typeof STRATEGIC_FEATURE_VERSION; weights: number[] } | null;
  limits: { nodes: number; milliseconds: number; maxTokens: number; maxCalls: number };
};
export type Version = { schema: typeof VERSION_SCHEMA; revision: number; parent: string | null;
  config: VersionConfig; provenance: { method: "baseline" | "manual" | "tactical-pairwise-v1" | "search-pairwise-v1"; source: string | null; identities: string[] }; digest: string };
const learnedMethod = (method: unknown) => method === "tactical-pairwise-v1" || method === "search-pairwise-v1";

export const isDigest = (value: unknown): value is string => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
export function integer(value: unknown, min: number, max: number, label: string): asserts value is number {
  if (!Number.isInteger(value) || (value as number) < min || (value as number) > max) throw Error(`Invalid ${label}.`);
}
export function exact(raw: unknown, keys: string[], label: string): asserts raw is Record<string, any> {
  if (!raw || typeof raw !== "object" || Array.isArray(raw) || Object.keys(raw).sort().join() !== [...keys].sort().join()) throw Error(`Invalid ${label} fields.`);
}
export function freeze<T>(value: T): T {
  if (value && typeof value === "object") { Object.values(value).forEach(freeze); Object.freeze(value); }
  return value;
}
function text(raw: unknown, max: number, label: string, empty = false): asserts raw is string {
  if (typeof raw !== "string" || raw.length > max || (!empty && !raw.trim()) || /[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(raw)) throw Error(`Invalid ${label}.`);
}
export const rulesKey = (r: Rules) => JSON.stringify([r.kind, r.rows, r.cols, r.connect, r.gravity]);

function parseConfig(raw: unknown): VersionConfig {
  exact(raw, ["rules", "referee", "runtime", "harness", "prompt", "memory", "tools", "sampling", "value", "limits"], "version config");
  if (JSON.stringify(raw).length > 24000 || raw.referee !== refereeManifest.digest) throw Error("Unsupported version/referee.");
  exact(raw.rules, ["kind", "name", "rows", "cols", "connect", "gravity"], "version rules");
  const rules = validateRules(raw.rules);
  exact(raw.runtime, ["provider", "requestedModel", "resolvedModel", "evidence", "reasoning"], "runtime identity");
  const r = raw.runtime;
  if (!["local", "openrouter", "harness"].includes(r.provider) || !["bundled-code", "provider-response", "self-reported", "unreported"].includes(r.evidence)) throw Error("Unsupported identity evidence.");
  text(r.requestedModel, 160, "requested model");
  if (r.resolvedModel !== null) text(r.resolvedModel, 160, "resolved model");
  if ((r.evidence === "unreported") !== (r.resolvedModel === null)) throw Error("Identity evidence mismatch.");
  if ((r.provider === "local") !== (r.evidence === "bundled-code")) throw Error("Local code is not provider attestation.");
  if (!["default", "none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"].includes(r.reasoning)) throw Error("Unsupported reasoning declaration.");
  exact(raw.harness, ["kind", "source", "protocol"], "harness");
  if (!["linear-value", "strategic-value", "model"].includes(raw.harness.kind) || !isDigest(raw.harness.source)) throw Error("Invalid harness implementation.");
  text(raw.harness.protocol, 80, "harness protocol");
  text(raw.prompt, 1000, "prompt", true);
  exact(raw.memory, ["mode", "content"], "memory");
  if (!["none", "frozen"].includes(raw.memory.mode) || (raw.memory.mode === "none" && raw.memory.content !== "")) throw Error("Memory must be explicitly frozen or absent.");
  text(raw.memory.content, 4000, "memory content", true);
  if (!Array.isArray(raw.tools) || raw.tools.length > 8) throw Error("Invalid tool declarations.");
  const ids = new Set<string>();
  for (const tool of raw.tools) {
    exact(tool, ["id", "source", "parameters"], "tool"); text(tool.id, 80, "tool id");
    if (!isDigest(tool.source) || !isDigest(tool.parameters) || ids.has(tool.id)) throw Error("Invalid tool custody.");
    ids.add(tool.id);
  }
  exact(raw.sampling, ["temperature", "seed"], "sampling");
  if (raw.sampling.temperature !== null && (!Number.isFinite(raw.sampling.temperature) || raw.sampling.temperature < 0 || raw.sampling.temperature > 2)) throw Error("Invalid temperature.");
  if (raw.sampling.seed !== null) integer(raw.sampling.seed, 0, 0xffffffff, "sampling seed");
  exact(raw.limits, ["nodes", "milliseconds", "maxTokens", "maxCalls"], "resource limits");
  integer(raw.limits.nodes, 1, 2000000, "node limit"); integer(raw.limits.milliseconds, 1, 300000, "time limit");
  integer(raw.limits.maxTokens, 1, 8192, "token limit"); integer(raw.limits.maxCalls, 1, 1000, "call limit");
  if (raw.harness.kind !== "model") {
    const strategic = raw.harness.kind === "strategic-value";
    exact(raw.value, ["features", "weights"], "numeric value model");
    if (raw.value.features !== (strategic ? STRATEGIC_FEATURE_VERSION : FEATURE_VERSION) || !Array.isArray(raw.value.weights) || raw.value.weights.length !== (strategic ? STRATEGIC_FEATURE_COUNT : FEATURE_COUNT)
      || !raw.value.weights.every((w: unknown) => Number.isFinite(w) && Math.abs(w as number) <= 8)) throw Error("Invalid value parameters.");
    if (r.provider !== "local" || r.resolvedModel !== (strategic ? STRATEGIC_MODEL : "builderwars/linear-value-v1") || r.requestedModel !== r.resolvedModel
      || r.reasoning !== "none" || raw.prompt !== "" || raw.memory.mode !== "none" || raw.tools.length !== 1
      || raw.tools[0].id !== (strategic ? "two-ply-minimax-value" : "one-ply-value") || raw.sampling.temperature !== null) throw Error("Unsupported local execution configuration.");
    if (strategic && (rules.kind === "chess" || (rules.kind !== "checkers" && rules.rows * rules.cols > 42))) throw Error("Unsupported strategic rules.");
  } else if (raw.value !== null || r.provider === "local") throw Error("Model harness cannot claim local numeric execution.");
  // Canonical property order, independent of an imported JSON object's key order.
  return { rules, referee: raw.referee, runtime: { provider: r.provider, requestedModel: r.requestedModel, resolvedModel: r.resolvedModel, evidence: r.evidence, reasoning: r.reasoning },
    harness: { kind: raw.harness.kind, source: raw.harness.source, protocol: raw.harness.protocol }, prompt: raw.prompt,
    memory: { mode: raw.memory.mode, content: raw.memory.content }, tools: raw.tools.map((t: any) => ({ id: t.id, source: t.source, parameters: t.parameters })),
    sampling: { temperature: raw.sampling.temperature, seed: raw.sampling.seed }, value: raw.value ? { features: raw.value.features, weights: [...raw.value.weights] } : null,
    limits: { nodes: raw.limits.nodes, milliseconds: raw.limits.milliseconds, maxTokens: raw.limits.maxTokens, maxCalls: raw.limits.maxCalls } };
}
export function identityKey(identity: RuntimeIdentity) { return sha256(JSON.stringify(identity)); }

export async function createVersion(config: VersionConfig, parent: Version | null = null,
  provenance: Version["provenance"] = { method: parent ? "manual" : "baseline", source: null, identities: [] }): Promise<Version> {
  const clean = parseConfig(config), previous = parent ? await parseVersion(parent) : null;
  if (previous && previous.revision >= 1000000) throw Error("Version revision limit reached.");
  exact(provenance, ["method", "source", "identities"], "provenance");
  if (!["baseline", "manual", "tactical-pairwise-v1", "search-pairwise-v1"].includes(provenance.method) || !(provenance.source === null || isDigest(provenance.source))
    || !Array.isArray(provenance.identities) || provenance.identities.length > 8 || !provenance.identities.every(isDigest)
    || new Set(provenance.identities).size !== provenance.identities.length) throw Error("Invalid practice provenance.");
  if (learnedMethod(provenance.method) && (!previous || !provenance.source || provenance.identities.length !== 1
    || provenance.identities[0] !== await identityKey(clean.runtime))) throw Error("Practice identity/source missing.");
  if (clean.harness.kind === "linear-value" && (clean.harness.protocol !== "builderwars.linear-value.v1"
    || clean.tools[0].source !== clean.harness.source || clean.tools[0].parameters !== await sha256(JSON.stringify({ depth: 1 })))) throw Error("Local tool declaration does not match its executor.");
  if (clean.harness.kind === "strategic-value" && (clean.harness.protocol !== "builderwars.strategic-value.v1"
    || clean.tools[0].source !== clean.harness.source || clean.tools[0].parameters !== await sha256(JSON.stringify({ depth: 2, features: STRATEGIC_FEATURE_VERSION })))) throw Error("Strategic tool declaration does not match its executor.");
  const body = { schema: VERSION_SCHEMA as typeof VERSION_SCHEMA, revision: previous ? previous.revision + 1 : 0, parent: previous?.digest ?? null,
    config: clean, provenance: { method: provenance.method, source: provenance.source, identities: [...provenance.identities] } };
  return freeze({ ...body, digest: await sha256(JSON.stringify(body)) });
}
export async function parseVersion(raw: unknown): Promise<Version> {
  exact(raw, ["schema", "revision", "parent", "config", "provenance", "digest"], "version");
  if (raw.schema !== VERSION_SCHEMA || !isDigest(raw.digest) || !(raw.parent === null || isDigest(raw.parent))) throw Error("Unsupported version.");
  integer(raw.revision, 0, 1000000, "version revision");
  if ((raw.revision === 0) !== (raw.parent === null)) throw Error("Version ancestry mismatch.");
  const base = await createVersion(raw.config, null, learnedMethod(raw.provenance.method) ? { method: "manual", source: null, identities: [] } : raw.provenance);
  exact(raw.provenance, ["method", "source", "identities"], "provenance");
  if (learnedMethod(raw.provenance.method) && (!raw.parent || !isDigest(raw.provenance.source)
    || !Array.isArray(raw.provenance.identities) || raw.provenance.identities.length !== 1 || raw.provenance.identities[0] !== await identityKey(base.config.runtime))) throw Error("Practice identity mismatch.");
  const body = { schema: VERSION_SCHEMA, revision: raw.revision, parent: raw.parent, config: base.config,
    provenance: { method: raw.provenance.method, source: raw.provenance.source, identities: [...raw.provenance.identities] } };
  if (await sha256(JSON.stringify(body)) !== raw.digest) throw Error("Version digest mismatch.");
  return freeze({ ...body, digest: raw.digest }) as Version;
}

export type VersionDecision = { move: string; model: string; tokens: number | null; outputTokens: number | null; cost: number | null };
/** Shared inference rule for the session and paired evaluator; caller parses/freezes first. */
export function numericVersionMove(version: Version, state: GameState, budget: WorkBudget) {
  const c = version.config;
  if (!c.value || rulesKey(state.rules) !== rulesKey(c.rules)) throw Error("Numeric version/position mismatch.");
  const random = seeded(((c.sampling.seed ?? 0) + state.moves.length) >>> 0);
  if (c.harness.kind === "linear-value") return policyMove(state, { rules: c.rules, weights: c.value.weights }, random, budget);
  if (c.harness.kind === "strategic-value") return strategicMove(state, c.value.weights, random, budget);
  throw Error("No bundled numeric executor for a provider model.");
}
export function assertComparableSuccessor(parent: Version, candidate: Version) {
  const comparison = structuredClone(candidate.config); comparison.value = parent.config.value;
  if (!learnedMethod(candidate.provenance.method) || candidate.parent !== parent.digest || candidate.revision !== parent.revision + 1
    || !candidate.provenance.source || JSON.stringify(comparison) !== JSON.stringify(parent.config)) throw Error("Compared versions differ beyond learned numeric parameters.");
}
export type VersionTransport = (state: GameState, version: Version, signal: AbortSignal) => Promise<VersionDecision>;
/** A trusted adapter may access transient credentials; it cannot change the frozen config. */
export async function openVersionSession(raw: Version, transport?: VersionTransport) {
  const version = await parseVersion(raw), c = version.config;
  if (!c.runtime.resolvedModel) throw Error("Freeze a reported model identity before opening any versioned session.");
  if (c.harness.kind === "model" && !transport) throw Error("No version-aware transport; no inference started.");
  const abort = new AbortController(), budget = new WorkBudget(c.limits.nodes, c.limits.milliseconds, abort.signal);
  const receipts: (VersionDecision & { version: string; identity: string; ply: number })[] = [];
  let calls = 0, busy = false, stopped = false;
  const identity = await identityKey(c.runtime);
  return {
    version,
    cancel() { stopped = true; abort.abort(); },
    receipts() { return freeze(structuredClone(receipts)); },
    async move(state: GameState, signal = new AbortController().signal) {
      if (stopped || busy) throw Error("Versioned session stopped or busy.");
      if (state.over || rulesKey(state.rules) !== rulesKey(c.rules)) throw Error("Versioned game mismatch.");
      if (calls >= c.limits.maxCalls) { stopped = true; throw Error("Version call budget exhausted."); }
      if (!Array.isArray(state.moves) || state.moves.length > 397 || !state.moves.every(m => typeof m === "string" && m.length <= 100)) throw Error("Invalid versioned history.");
      const replay = replayStepper(c.rules);
      let snapshot = createGame(c.rules);
      for (const move of state.moves) { budget.tick(); snapshot = replay(move); }
      for (const field of ["cells", "turn", "fen", "winner", "over", "reason", "quiet", "positions"] as const) {
        if (JSON.stringify(snapshot[field]) !== JSON.stringify(state[field])) throw Error("Versioned position contradicts replay.");
      }
      freeze(snapshot);
      const combined = AbortSignal.any([abort.signal, signal, AbortSignal.timeout(Math.max(1, Math.ceil(budget.deadline - performance.now())))]);
      combined.throwIfAborted(); budget.tick(); busy = true; calls++;
      try {
        let result: VersionDecision;
        if (c.harness.kind !== "model") {
          result = { move: numericVersionMove(version, snapshot, budget),
            model: c.runtime.resolvedModel!, tokens: 0, outputTokens: 0, cost: 0 };
        } else {
          result = await new Promise<VersionDecision>((resolve, reject) => {
            const onAbort = () => reject(Error("Versioned move aborted; no retry."));
            combined.addEventListener("abort", onAbort, { once: true });
            if (combined.aborted) { onAbort(); return; }
            Promise.resolve().then(() => { combined.throwIfAborted(); return transport!(snapshot, version, combined); }).then(resolve, reject)
              .finally(() => combined.removeEventListener("abort", onAbort));
          });
        }
        combined.throwIfAborted(); budget.tick();
        exact(result, ["move", "model", "tokens", "outputTokens", "cost"], "versioned response");
        if (result.model !== c.runtime.resolvedModel || !legalMoves(snapshot).includes(result.move)) throw Error("Versioned response identity/legality mismatch.");
        for (const field of ["tokens", "outputTokens", "cost"] as const) if (result[field] !== null && (!Number.isFinite(result[field]) || result[field]! < 0)) throw Error("Invalid versioned usage.");
        if ((result.tokens !== null && !Number.isInteger(result.tokens)) || (result.outputTokens !== null && (!Number.isInteger(result.outputTokens) || result.outputTokens > c.limits.maxTokens))
          || (result.tokens !== null && result.outputTokens !== null && result.outputTokens > result.tokens)) throw Error("Version token budget exceeded or inconsistent.");
        const receipt = freeze({ ...result, version: version.digest, identity, ply: snapshot.moves.length });
        receipts.push(receipt); return receipt;
      } catch (error) { stopped = true; abort.abort(); throw error; }
      finally { busy = false; }
    },
  };
}
