/** Pure baseline construction; the caller supplies the measured execution-source digest. */
import { refereeManifest, sha256, type Rules } from "./runtime";
import { createVersion, type VersionConfig } from "./frontier-version";
import { FEATURE_COUNT, FEATURE_VERSION } from "./self-improvement";
import { STRATEGIC_FEATURE_COUNT, STRATEGIC_FEATURE_VERSION, STRATEGIC_MODEL } from "./strategic-value";

export async function numericBaseline(rules: Rules, source: string, kind: "linear-value" | "strategic-value" = "linear-value",
  limits: VersionConfig["limits"] = { nodes: 2000000, milliseconds: 300000, maxTokens: 512, maxCalls: 400 }) {
  const strategic = kind === "strategic-value", model = strategic ? STRATEGIC_MODEL : "builderwars/linear-value-v1";
  return createVersion({ rules, referee: refereeManifest.digest,
    runtime: { provider: "local", requestedModel: model, resolvedModel: model, evidence: "bundled-code", reasoning: "none" },
    harness: { kind, source, protocol: strategic ? "builderwars.strategic-value.v1" : "builderwars.linear-value.v1" },
    prompt: "", memory: { mode: "none", content: "" },
    tools: [{ id: strategic ? "two-ply-minimax-value" : "one-ply-value", source,
      parameters: await sha256(JSON.stringify(strategic ? { depth: 2, features: STRATEGIC_FEATURE_VERSION } : { depth: 1 })) }],
    sampling: { temperature: null, seed: 0 },
    value: { features: strategic ? STRATEGIC_FEATURE_VERSION : FEATURE_VERSION,
      weights: Array(strategic ? STRATEGIC_FEATURE_COUNT : FEATURE_COUNT).fill(0) }, limits });
}
