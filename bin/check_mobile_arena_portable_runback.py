#!/usr/bin/env python3
"""Adversarial checks for canonical local runback proposal portability."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOBILE = ROOT / "mobile-arena"


def require(predicate: bool, message: str) -> None:
    if not predicate:
        raise AssertionError(message)


def main() -> int:
    node = shutil.which("node")
    require(node is not None, "Node.js is required to exercise portable runback verification")

    script = r"""
const fs = require("fs");
const path = require("path");
const adapter = require(path.join(process.cwd(), "data-adapter.js"));
const demo = JSON.parse(fs.readFileSync(path.join(process.cwd(), "data", "demo-state.json"), "utf8"));
const model = JSON.parse(fs.readFileSync(path.join(process.cwd(), "data", "arena-read-model.v1.json"), "utf8"));
const checks = [];
function check(predicate, message) {
  if (!predicate) throw new Error(message);
  checks.push(message);
}
function copy(value) { return JSON.parse(JSON.stringify(value)); }
function canonical(value) {
  if (value === null || typeof value === "boolean" || typeof value === "string" || typeof value === "number") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(",")}}`;
}
async function digest(value) {
  const bytes = new TextEncoder().encode(value);
  const result = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(result)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}
async function rejectsRaw(raw, expected) {
  let message = "";
  try { await adapter.verifyPortableRunbackEnvelope(raw); } catch (error) { message = error.message; }
  check(message.includes(expected), `rejects ${expected}`);
}
async function rejectsEnvelope(mutator, expected, refreshDigest = false) {
  const envelope = copy(portable.envelope);
  mutator(envelope);
  if (refreshDigest) envelope.integrity.payloadDigest = await digest(canonical(envelope.payload));
  await rejectsRaw(canonical(envelope), expected);
}
function validateRejects(mutator, expected) {
  const proposalCopy = copy(proposal);
  mutator(proposalCopy);
  let message = "";
  try { adapter.validateRunbackProposal(proposalCopy); } catch (error) { message = error.message; }
  check(message.includes(expected), `proposal rejects ${expected}`);
}

async function main() {
  const view = adapter.adaptArenaReadModel(model, demo);
  const proof = view.proofReceipts.find((candidate) => candidate.moveSourceCounts.model > 0);
  const learning = adapter.buildReceiptLearningAction(proof, "verified_corpus");
  const blueprint = {
    agentName: "Portable Student",
    baseModel: "Arena Small",
    harnessStyle: "Human review checkpoints",
    strictValidation: true,
    fallbackDisclosure: true,
    humanCheckpoints: false,
    localOnly: true,
  };
  globalThis.proposal = adapter.buildRunbackProposal(learning, blueprint, "require_human_checkpoints", "verified_corpus");
  globalThis.portable = await adapter.createPortableRunbackEnvelope(proposal);
  const repeated = await adapter.createPortableRunbackEnvelope(copy(proposal));

  check(adapter.PORTABLE_RUNBACK_SCHEMA === "builderwars.mobile-runback-portable.v1", "exports portable schema");
  check(adapter.PORTABLE_RUNBACK_MAX_LENGTH === 32768, "exports bounded import length");
  check(portable.envelope.schemaVersion === adapter.PORTABLE_RUNBACK_SCHEMA, "envelope uses portable schema");
  check(portable.envelope.payload.schemaVersion === adapter.RUNBACK_PROPOSAL_SCHEMA, "envelope carries exact proposal schema");
  check(portable.envelope.integrity.algorithm === "sha256", "envelope declares SHA-256");
  check(/^[0-9a-f]{64}$/.test(portable.envelope.integrity.payloadDigest), "envelope carries a lowercase digest");
  check(portable.envelope.boundary.includes("not a signature"), "envelope refuses signature claim");
  check(portable.envelope.boundary.includes("grants no qualification, execution, registry, ranking, publication, or spending authority"), "envelope refuses authority claim");
  check(portable.serialized === canonical(portable.envelope), "export is canonical JSON");
  check(portable.serialized === repeated.serialized, "repeated export is deterministic");
  check(!portable.serialized.includes("\n") && !portable.serialized.includes("  "), "canonical export has no cosmetic whitespace");
  check(portable.serialized.startsWith('{"boundary":'), "canonical export sorts top-level keys");
  check(portable.envelope.integrity.payloadDigest === await digest(canonical(proposal)), "digest independently binds canonical proposal");

  const verified = await adapter.verifyPortableRunbackEnvelope(portable.serialized);
  check(verified.schemaVersion === adapter.PORTABLE_RUNBACK_SCHEMA, "verification returns versioned result");
  check(verified.verificationStatus === "verified_local_unplayed_proposal", "verification stays local and unplayed");
  check(verified.payloadDigest === portable.envelope.integrity.payloadDigest, "verification returns recomputed digest");
  check(verified.proposal.proposalKey === proposal.proposalKey, "verification preserves proposal key");
  check(verified.proposal.parentReceipt.receiptId === proposal.parentReceipt.receiptId, "verification preserves parent receipt");
  check(verified.proposal.runbackLineage.challengeId === proposal.runbackLineage.challengeId, "verification preserves challenge");
  check(verified.proposal.runbackLineage.fixtureId === proposal.runbackLineage.fixtureId, "verification preserves runback fixture");
  check(verified.proposal.runbackStatus === "unplayed_proposal", "verification preserves unplayed proposal state");
  check(verified.proposal.qualificationStatus === "not_run", "verification preserves not-run qualification");
  check(verified.proposal.executionStatus === "disabled", "verification preserves disabled execution");
  check(verified.proposal.publicationStatus === "not_requested", "verification preserves unrequested publication");
  check(Object.values(verified.proposal.attestations).every((value) => value === false), "verification preserves false attestations");
  check(verified.boundary.includes("not a signature"), "verification result repeats authenticity boundary");

  await rejectsRaw("", "input length rejected");
  await rejectsRaw("{", "invalid JSON");
  await rejectsRaw("x".repeat(32769), "input length rejected");
  await rejectsRaw(JSON.stringify(portable.envelope, null, 2), "canonical JSON");
  await rejectsRaw(` ${portable.serialized}`, "canonical JSON");
  await rejectsRaw(portable.serialized.replace('"payload":{', '"payload":{"__proto__":{"polluted":true},'), "prohibited key");
  await rejectsRaw(portable.serialized.replace('"payload":{', '"payload":{"constructor":{"polluted":true},'), "prohibited key");
  await rejectsRaw(portable.serialized.replace('"payload":{', '"payload":{"prototype":{"polluted":true},'), "prohibited key");
  const deeplyNested = copy(portable.envelope);
  deeplyNested.extra = {};
  let cursor = deeplyNested.extra;
  for (let depth = 0; depth < 34; depth += 1) { cursor.next = {}; cursor = cursor.next; }
  await rejectsRaw(canonical(deeplyNested), "nesting limit exceeded");

  await rejectsEnvelope((envelope) => { envelope.extra = true; }, "envelope fields drift");
  await rejectsEnvelope((envelope) => { envelope.schemaVersion = "builderwars.mobile-runback-portable.v2"; }, "envelope schema drift");
  await rejectsEnvelope((envelope) => { envelope.boundary = "trusted"; }, "envelope boundary drift");
  await rejectsEnvelope((envelope) => { envelope.integrity.extra = true; }, "integrity fields drift");
  await rejectsEnvelope((envelope) => { envelope.integrity.algorithm = "sha512"; }, "integrity metadata drift");
  await rejectsEnvelope((envelope) => { envelope.integrity.payloadDigest = "bad"; }, "integrity metadata drift");
  await rejectsEnvelope((envelope) => { envelope.integrity.payloadDigest = "0".repeat(64); }, "payload digest mismatch");
  await rejectsEnvelope((envelope) => { envelope.payload.blueprint.agentName = "Changed Student"; }, "proposal key drift");
  await rejectsEnvelope((envelope) => { envelope.payload.runbackStatus = "played"; }, "proposal is not unplayed", true);
  await rejectsEnvelope((envelope) => { envelope.payload.extra = true; }, "proposal fields drift", true);
  await rejectsEnvelope((envelope) => { envelope.payload.parentReceipt.extra = true; }, "parent receipt fields drift", true);
  await rejectsEnvelope((envelope) => { envelope.payload.blueprint.extra = true; }, "blueprint fields drift", true);
  await rejectsEnvelope((envelope) => { envelope.payload.attestations.provider = true; }, "attestation must remain false", true);

  validateRejects((value) => { value.extra = true; }, "proposal fields drift");
  validateRejects((value) => { value.schemaVersion = "drift"; }, "proposal schema drift");
  validateRejects((value) => { value.proposalVersion = 2; }, "proposal schema drift");
  validateRejects((value) => { value.runbackStatus = "played"; }, "proposal is not unplayed");
  validateRejects((value) => { value.qualificationStatus = "PASS"; }, "qualification status drift");
  validateRejects((value) => { value.executionStatus = "enabled"; }, "execution status drift");
  validateRejects((value) => { value.publicationStatus = "published"; }, "publication status drift");
  validateRejects((value) => { value.boundary = "trusted"; }, "proposal boundary drift");
  validateRejects((value) => { value.parentReceipt.receiptId = "bad"; }, "parent receipt binding missing");
  validateRejects((value) => { value.parentReceipt.fixtureId = "bad"; }, "parent receipt binding missing");
  validateRejects((value) => { value.parentReceipt.replayVerdict = "FAIL"; }, "parent replay was not verified");
  validateRejects((value) => { value.runbackLineage.challengeId = "bad"; }, "runback identifiers missing");
  validateRejects((value) => { value.runbackLineage.fixtureId = "bad"; }, "runback identifiers missing");
  validateRejects((value) => { value.runbackLineage.parentReceiptId = "0".repeat(64); }, "runback parent drift");
  validateRejects((value) => { value.runbackLineage.status = "played"; }, "challenge is not unplayed");
  validateRejects((value) => { value.gameBinding.name = ""; }, "game name missing");
  validateRejects((value) => { value.gameBinding.version = "2"; }, "game version drift");
  validateRejects((value) => { value.gameBinding.format = 42; }, "game format drift");
  validateRejects((value) => { value.rulesBinding.status = "bound"; }, "rules blocker drift");
  validateRejects((value) => { value.rulesBinding.rulesDigest = "0".repeat(64); }, "rules blocker drift");
  validateRejects((value) => { value.rulesBinding.statement = "rules are fine"; }, "rules statement drift");
  validateRejects((value) => { value.blueprint.agentName = " Portable Student"; }, "agent name drift");
  validateRejects((value) => { value.blueprint.agentName = "x".repeat(37); }, "agent name drift");
  validateRejects((value) => { value.blueprint.declaredBase = "Unknown Model"; }, "unknown declared base");
  validateRejects((value) => { value.blueprint.harnessStyle = "Arbitrary code"; }, "unknown harness style");
  validateRejects((value) => { value.blueprint.localOnly = false; }, "blueprint escaped local boundary");
  validateRejects((value) => { value.blueprintDelta.id = "arbitrary"; }, "blueprint delta drift");
  validateRejects((value) => { value.blueprintDelta.guardKey = "arbitrary"; }, "blueprint delta drift");
  validateRejects((value) => { value.blueprintDelta.label = "trusted"; }, "blueprint delta drift");
  validateRejects((value) => { value.blueprintDelta.rationale = "trusted"; }, "blueprint delta drift");
  validateRejects((value) => { value.blueprintDelta.from = "false"; }, "blueprint change drift");
  validateRejects((value) => { value.blueprintDelta.to = false; }, "blueprint change drift");
  validateRejects((value) => { value.blueprintDelta.changeStatus = "completed"; }, "blueprint change status drift");
  validateRejects((value) => { value.executionBlockers.pop(); }, "execution blockers drift");
  validateRejects((value) => { value.executionBlockers.reverse(); }, "execution blockers drift");
  validateRejects((value) => { value.executionBlockers.push("extra"); }, "execution blockers drift");
  for (const attestation of ["identity", "model", "provider", "runtime", "registry", "publication"]) {
    validateRejects((value) => { value.attestations[attestation] = true; }, "attestation must remain false");
  }
  validateRejects((value) => { value.proposalKey = "changed"; }, "proposal key drift");
  validateRejects((value) => { value.parentReceipt.extra = true; }, "parent receipt fields drift");
  validateRejects((value) => { value.runbackLineage.extra = true; }, "runback lineage fields drift");
  validateRejects((value) => { value.gameBinding.extra = true; }, "game binding fields drift");
  validateRejects((value) => { value.rulesBinding.extra = true; }, "rules binding fields drift");
  validateRejects((value) => { value.blueprint.extra = true; }, "blueprint fields drift");
  validateRejects((value) => { value.blueprintDelta.extra = true; }, "blueprint delta fields drift");
  validateRejects((value) => { value.attestations.extra = false; }, "attestations fields drift");

  const alternate = adapter.buildRunbackProposal(learning, blueprint, "require_strict_validation", "verified_corpus");
  const alternatePortable = await adapter.createPortableRunbackEnvelope(alternate);
  check(alternatePortable.envelope.integrity.payloadDigest !== portable.envelope.integrity.payloadDigest, "different bounded proposal gets a different digest");
  check((await adapter.verifyPortableRunbackEnvelope(alternatePortable.serialized)).proposal.blueprintDelta.id === "require_strict_validation", "alternate bounded delta verifies without activation");
  process.stdout.write(JSON.stringify({ status: "PASS", checks: checks.length }));
}

main().catch((error) => { console.error(error.stack || error.message); process.exit(1); });
"""

    result = subprocess.run(
        [node, "-e", script],
        cwd=MOBILE,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
    )
    require(result.returncode == 0, f"portable runback check failed: {result.stderr.strip()}")
    payload = json.loads(result.stdout)
    require(payload.get("status") == "PASS", "portable runback check did not report PASS")
    require(payload.get("checks", 0) >= 90, "portable runback coverage unexpectedly shrank")
    print(f"BuilderWars portable runback proposal: PASS ({payload['checks']} checks)")
    print("canonical JSON / SHA-256 integrity / strict schema / no authenticity or execution claim")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
