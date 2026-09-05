import type { Agent, PublicAgent } from "./models";

export const PROFILE_SCHEMA = "builderwars.agent-profile.v1";
export const PROFILE_MAX_BYTES = 8192;
export type AgentProfile = { schema: typeof PROFILE_SCHEMA; agent: PublicAgent };
const fields = ["name", "kind", "model", "effort", "strategy"] as const;
const limits = [64, 10, 160, 20, 1000];

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw Error("Expected a profile object.");
  return value as Record<string, unknown>;
}
function exact(value: Record<string, unknown>, keys: readonly string[]) {
  if (Object.keys(value).length !== keys.length || keys.some(k => !Object.hasOwn(value, k)))
    throw Error("Profile has missing or unexpected fields. Connection secrets and endpoints are not accepted.");
}
function entrant(value: unknown): PublicAgent {
  const row = object(value);
  exact(row, fields);
  fields.forEach((key, i) => {
    if (typeof row[key] !== "string" || (row[key] as string).length > limits[i])
      throw Error(`Invalid profile ${key}.`);
  });
  if (!(row.name as string).trim() || !["bot", "human", "openrouter", "harness"].includes(row.kind as string))
    throw Error("Invalid profile name or connection type.");
  if (row.kind === "bot" && !["tactician", "random"].includes(row.model as string))
    throw Error("Choose a recognized built-in opponent.");
  if (row.kind === "human" && row.model !== "human") throw Error("Invalid human profile.");
  if (["bot", "human"].includes(row.kind as string) && row.effort !== "default")
    throw Error("Local profiles use default effort.");
  if (row.kind === "openrouter" && (!(row.model as string).trim() || !(row.effort as string).trim()))
    throw Error("A model profile needs a model and requested effort.");
  return Object.fromEntries(fields.map(k => [k, row[k]])) as PublicAgent;
}
/** Explicit projection, never object spreading an Agent containing credentials. */
export function makeProfile(agent: Agent | PublicAgent): AgentProfile {
  return { schema: PROFILE_SCHEMA, agent: entrant(Object.fromEntries(fields.map(k => [k, agent[k]]))) };
}
export function readProfile(text: string): AgentProfile {
  if (new TextEncoder().encode(text).length > PROFILE_MAX_BYTES) throw Error("Profile exceeds 8 KB.");
  let value: Record<string, unknown>;
  try { value = object(JSON.parse(text)); } catch { throw Error("Profile is not valid JSON."); }
  if (Object.hasOwn(value, "schema")) {
    exact(value, ["schema", "agent"]);
    if (value.schema !== PROFILE_SCHEMA) throw Error("Unsupported profile version.");
    return { schema: PROFILE_SCHEMA, agent: entrant(value.agent) };
  }
  // Preserve the exact five-field legacy Export profile format.
  return { schema: PROFILE_SCHEMA, agent: entrant(value) };
}
export function disconnectedProfile(profile: AgentProfile): Agent {
  return { ...entrant(profile.agent), endpoint: "", key: "" };
}
export function compareProfiles(baseline: PublicAgent, candidate: PublicAgent) {
  // Display names do not count as behavior changes; secrets never enter this comparison.
  const settings = ["kind", "model", "effort", "strategy"] as const;
  const changed = settings.filter(k => baseline[k] !== candidate[k]);
  return { changed, renamed: baseline.name !== candidate.name };
}
