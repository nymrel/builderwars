import { sha256 } from "@noble/hashes/sha2.js";

/** Public claims only. Neither a content hash nor a source revision authenticates a builder. */
export type BuilderProvenance = {
  builderId: string;
  harnessId: string;
  harnessRevision: string;
  attestation: "self-declared";
};
export function validateProvenance(raw: unknown): BuilderProvenance | undefined {
  if (raw === undefined) return undefined;
  if (!raw || typeof raw !== "object" || Array.isArray(raw))
    throw Error("Invalid builder provenance.");
  const p = raw as BuilderProvenance;
  const id = /^[A-Za-z0-9][A-Za-z0-9._/@-]{0,95}$/;
  if (typeof p.builderId !== "string" || !id.test(p.builderId) ||
      typeof p.harnessId !== "string" || !id.test(p.harnessId) ||
      typeof p.harnessRevision !== "string" || !/^(?:[a-f0-9]{40}|[a-f0-9]{64})$/.test(p.harnessRevision) ||
      p.attestation !== "self-declared")
    throw Error("Use public builder/harness IDs and a 40- or 64-character lowercase source hash. Identity remains self-declared.");
  return { builderId: p.builderId, harnessId: p.harnessId,
    harnessRevision: p.harnessRevision, attestation: "self-declared" };
}
/** The caller supplies the normalized record with deterministic property order. */
export function recordDigest(record: unknown): string {
  const bytes = new TextEncoder().encode(JSON.stringify(record));
  return Array.from(sha256(bytes), (b) => b.toString(16).padStart(2, "0")).join("");
}
