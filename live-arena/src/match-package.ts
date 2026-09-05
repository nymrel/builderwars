import { replay, refereeManifest, type RecordData } from "./runtime";
import { safeReplay } from "./sharing";
import { matchLimits, type MatchLimits } from "./resources";

export const DECLARATION_FIELDS = ["builderId", "agentId", "agentRevision", "harnessId", "harnessRevision", "providerId", "modelRevision"] as const;
export type SeatDeclaration = Readonly<Record<typeof DECLARATION_FIELDS[number], string | null>>;
export type MatchDeclarations = readonly [SeatDeclaration, SeatDeclaration];
const SCHEMA = "builderwars.match-package.v1";

function exact(raw: unknown, keys: readonly string[]): asserts raw is Record<string, unknown> {
  if (!raw || typeof raw !== "object" || Array.isArray(raw) || Object.keys(raw).sort().join(",") !== [...keys].sort().join(","))
    throw Error("Unexpected match package fields.");
}
export function readDeclaration(raw: unknown): SeatDeclaration {
  exact(raw, DECLARATION_FIELDS);
  const result = {} as Record<typeof DECLARATION_FIELDS[number], string | null>;
  for (const field of DECLARATION_FIELDS) {
    const value = raw[field];
    if (value !== null && (typeof value !== "string" || !/^[a-zA-Z0-9][a-zA-Z0-9._/-]{0,95}$/.test(value)))
      throw Error(`${field}: use a public identifier of up to 96 letters, digits, dots, slashes, underscores or hyphens; leave unknown values blank.`);
    result[field] = value as string | null;
  }
  return Object.freeze(result);
}
export function unknownDeclarations(): MatchDeclarations {
  const empty = Object.fromEntries(DECLARATION_FIELDS.map(field => [field, null]));
  return readDeclarations([empty, empty]);
}
export function readDeclarations(raw: unknown): MatchDeclarations {
  if (!Array.isArray(raw) || raw.length !== 2) throw Error("Two seat-indexed declarations are required.");
  return Object.freeze([readDeclaration(raw[0]), readDeclaration(raw[1])]);
}
function readResources(raw: unknown): MatchLimits | null {
  if (raw === null) return null;
  exact(raw, ["moveLimit", "maxTokens", "moveLimitKnown"]);
  if (typeof raw.moveLimitKnown !== "boolean") throw Error("Resource knowledge must be explicit.");
  return matchLimits(raw.moveLimit as number, raw.maxTokens as number | null, raw.moveLimitKnown);
}
/** Public package, not an execution certificate. The immutable v1 referee stays unchanged. */
export function makeMatchPackage(record: RecordData, declarations: MatchDeclarations, resources: MatchLimits | null) {
  const clean = safeReplay(record);
  const limits = readResources(resources === null ? null : { ...resources, moveLimitKnown: resources.moveLimitKnown === true });
  if (limits && clean.events.length > limits.moveLimit) throw Error("Record exceeds declared move limit.");
  return {
    schema: SCHEMA,
    record: clean,
    declarations: readDeclarations(declarations),
    resources: limits,
    fixture: "standard-initial-position",
    seed: null,
    verification: {
      scope: "legal-moves-only",
      verifierVersion: "builderwars-board-js/1",
      verifierDigest: refereeManifest.digest,
      identityAttested: false,
      modelAttested: false,
      resourcesAttested: false,
    },
  } as const;
}
/** Legacy replays have unknown attribution/resources; editor defaults are never evidence. */
export function readMatchFile(raw: unknown) {
  if ((raw as { schema?: unknown } | null)?.schema === "builderwars.exhibition.v1")
    return { parsed: replay(raw), declarations: unknownDeclarations(), limits: null };
  exact(raw, ["schema", "record", "declarations", "resources", "fixture", "seed", "verification"]);
  if (raw.schema !== SCHEMA || raw.fixture !== "standard-initial-position" || raw.seed !== null)
    throw Error("Unsupported match package version or fixture.");
  exact(raw.verification, ["scope", "verifierVersion", "verifierDigest", "identityAttested", "modelAttested", "resourcesAttested"]);
  const v = raw.verification;
  if (v.scope !== "legal-moves-only" || v.verifierVersion !== "builderwars-board-js/1" || v.verifierDigest !== refereeManifest.digest ||
      v.identityAttested !== false || v.modelAttested !== false || v.resourcesAttested !== false)
    throw Error("Unsupported verifier or attestation claim. Import a compatible legacy replay instead.");
  const declarations = readDeclarations(raw.declarations), limits = readResources(raw.resources);
  // Recompute legality rather than trusting the exported verification label.
  const parsed = replay(safeReplay(replay(raw.record).record));
  if (limits && parsed.record.events.length > limits.moveLimit) throw Error("Record exceeds declared move limit.");
  return { parsed, declarations, limits };
}
