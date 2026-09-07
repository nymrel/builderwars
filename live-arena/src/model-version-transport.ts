/** Version-aware browser execution. Connections and credentials stay in closures,
 * never in version artifacts. Provider identity remains reported, not attested. */
import modelVersionManifest from "./model-version-manifest";
import { decide, validateConnection, type Agent, type Model } from "./models";
import { MEMORY_SCHEMA, type MemoryContext } from "./learning";
import { refereeManifest, validateRules, sha256, type Rules } from "./runtime";
import { exact, freeze, integer, isDigest, parseVersion, type Version, type VersionConfig, type VersionTransport } from "./frontier-version";

export const MODEL_BROWSER_PROTOCOL = "builderwars.browser-model.v1";
function reported(value: unknown): value is string {
  return typeof value === "string" && /^[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,159}$/.test(value)
    && !/(?:^|[/:_-])(?:unreported|unknown|unavailable)(?:$|[/:_-])/i.test(value);
}
function boundedText(value: unknown, limit: number) {
  if (typeof value !== "string" || value.length > limit || /[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(value)) throw Error("Invalid frozen browser text.");
}
function assertConfig(c: VersionConfig) {
  exact(c, ["rules", "referee", "runtime", "harness", "prompt", "memory", "tools", "sampling", "value", "limits"], "browser config");
  exact(c.harness, ["kind", "source", "protocol"], "browser harness");
  if (!isDigest(modelVersionManifest.digest) || c.harness.kind !== "model" || c.harness.protocol !== MODEL_BROWSER_PROTOCOL
    || c.harness.source !== modelVersionManifest.digest || c.referee !== refereeManifest.digest) throw Error("Browser version executor source, protocol or referee mismatch.");
  if (JSON.stringify(validateRules(c.rules)) !== JSON.stringify(c.rules)) throw Error("Browser version rules are not canonical.");
  exact(c.runtime, ["provider", "requestedModel", "resolvedModel", "evidence", "reasoning"], "browser runtime");
  const r = c.runtime;
  if (!["openrouter", "harness"].includes(r.provider) || r.evidence !== (r.provider === "openrouter" ? "provider-response" : "self-reported")
    || !reported(r.requestedModel) || !reported(r.resolvedModel)) throw Error("Browser version needs a reported model identity and matching provider evidence.");
  if (!["default", "none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"].includes(r.reasoning)) throw Error("Invalid browser reasoning declaration.");
  if (!Array.isArray(c.tools) || c.tools.length || c.value !== null) throw Error("Browser model transport does not execute declared tools or numeric values.");
  exact(c.sampling, ["temperature", "seed"], "browser sampling");
  if (c.sampling.temperature !== null || c.sampling.seed !== null) throw Error("Browser model transport does not implement sampling overrides.");
  boundedText(c.prompt, 1000); exact(c.memory, ["mode", "content"], "browser memory"); boundedText(c.memory.content, 4000);
  if (!["none", "frozen"].includes(c.memory.mode) || (c.memory.mode === "none" && c.memory.content !== "")) throw Error("Browser memory must be absent or explicitly frozen.");
  exact(c.limits, ["nodes", "milliseconds", "maxTokens", "maxCalls"], "browser limits");
  integer(c.limits.nodes, 1, 2000000, "browser node limit"); integer(c.limits.milliseconds, 1, 300000, "browser time limit");
  integer(c.limits.maxTokens, 1, 8192, "browser output token limit"); integer(c.limits.maxCalls, 1, 1000, "browser call limit");
}
/** Synchronous execution compatibility check; parseVersion verifies content digest. */
export function assertBrowserVersion(version: Version): void { assertConfig(version.config); }

export function connectedVersionConfig(agent: Agent, rules: Rules, resolvedModel: string,
  limits: VersionConfig["limits"], memoryContent = ""): VersionConfig {
  if (agent.kind !== "openrouter" && agent.kind !== "harness") throw Error("Choose a connected model for a browser version.");
  const config: VersionConfig = {
    rules: structuredClone(rules), referee: refereeManifest.digest,
    runtime: { provider: agent.kind, requestedModel: agent.model, resolvedModel,
      evidence: agent.kind === "openrouter" ? "provider-response" : "self-reported", reasoning: agent.effort },
    harness: { kind: "model", source: modelVersionManifest.digest, protocol: MODEL_BROWSER_PROTOCOL },
    prompt: agent.strategy, memory: { mode: memoryContent ? "frozen" : "none", content: memoryContent }, tools: [],
    sampling: { temperature: null, seed: null }, value: null, limits: { ...limits },
  };
  assertConfig(config); return freeze(config);
}

export function browserVersionTransport(agent: Agent, models: Model[]): VersionTransport {
  // Copy only the supported connection fields; later UI edits cannot redirect a run.
  const connection: Agent = freeze({ name: agent.name, kind: agent.kind, model: agent.model, effort: agent.effort,
    strategy: agent.strategy, endpoint: agent.endpoint, key: agent.key });
  const catalog = freeze(structuredClone(models));
  if (connection.kind !== "openrouter" && connection.kind !== "harness") throw Error("No browser model transport for local opponents.");
  validateConnection(connection, catalog);
  return async (state, rawVersion, signal) => {
    signal.throwIfAborted();
    const version = await parseVersion(rawVersion); assertBrowserVersion(version);
    const c = version.config;
    if (c.runtime.provider !== connection.kind || c.runtime.requestedModel !== connection.model || c.runtime.reasoning !== connection.effort)
      throw Error("Version identity or effort differs from the connected contender.");
    const memory: MemoryContext | undefined = c.memory.mode === "frozen" ? {
      schema: MEMORY_SCHEMA, mode: "frozen-evaluation", digest: await sha256(c.memory.content), sources: [], prompt: c.memory.content,
    } : undefined;
    signal.throwIfAborted();
    const result = await decide(state, { ...connection, strategy: c.prompt }, c.limits.maxTokens, signal, catalog, memory);
    signal.throwIfAborted();
    if (result.model !== c.runtime.resolvedModel) throw Error("Browser response identity differs from the frozen version; no fallback.");
    const outputTokens = result.outputTokens ?? null;
    if (outputTokens !== null && (!Number.isSafeInteger(outputTokens) || outputTokens < 0 || outputTokens > c.limits.maxTokens))
      throw Error("Reported browser output exceeds the frozen token limit.");
    return { move: result.move, model: result.model, tokens: result.tokens, outputTokens, cost: result.cost };
  };
}
