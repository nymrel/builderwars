#!/usr/bin/env python3
"""Adversarial proof for the browser-memory deterministic local exhibition."""

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
    require(node is not None, "Node.js is required to exercise the local exhibition")

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
  const bytes = new TextEncoder().encode(canonical(value));
  const result = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(result)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}
async function rehash(candidate) {
  const unsigned = copy(candidate);
  delete unsigned.candidateDigest;
  candidate.candidateDigest = await digest(unsigned);
  return candidate;
}
async function rejects(task, expected) {
  let message = "";
  try { await task(); } catch (error) { message = error.message; }
  check(message.includes(expected), `rejects ${expected}`);
}

(async () => {
  const view = await adapter.adaptArenaReadModel(model, demo);
  const exhibitions = view.quickMatches.filter((fixture) => fixture.exhibitionAllowed);
  const proposed = view.quickMatches.filter((fixture) => !fixture.exhibitionAllowed);
  check(exhibitions.length === 1, "projects exactly one local exhibition");
  check(proposed.length === 3 && proposed.every((fixture) => fixture.activationStatus === "proposed_not_activated"), "keeps all proposed fixtures inactive");
  const fixture = exhibitions[0];
  check(fixture.id === adapter.LOCAL_EXHIBITION_FIXTURE_ID, "binds the canonical fixture id");
  check(fixture.rulesDigest === adapter.LOCAL_EXHIBITION_RULES_DIGEST, "binds the canonical rules digest");
  check(fixture.resourceClass === adapter.LOCAL_EXHIBITION_RESOURCE_CLASS, "binds the no-model resource class");
  check(fixture.ranked === false && fixture.enabled === false, "does not enable ranking or queue entry");

  const blueprint = {
    agentName: "Local Proof",
    baseModel: "Arena Reason",
    harnessStyle: "Validate every move",
    strictValidation: true,
    fallbackDisclosure: true,
    humanCheckpoints: false,
    localOnly: true,
  };
  const qualification = adapter.buildLocalExhibitionQualification(blueprint, fixture, "verified_corpus");
  const repeated = adapter.buildLocalExhibitionQualification(blueprint, fixture, "verified_corpus");
  check(qualification.schemaVersion === adapter.LOCAL_EXHIBITION_QUALIFICATION_SCHEMA, "uses the versioned local qualification schema");
  check(qualification.qualificationStatus === "qualified_local_exhibition", "qualifies only the bounded local exhibition");
  check(qualification.executionStatus === "available_browser_memory_only", "limits execution to browser memory");
  check(qualification.qualificationKey === repeated.qualificationKey, "qualification is deterministic");
  check(qualification.blueprint.declaredBaseUse === "metadata_only_not_used", "declared base remains unused metadata");
  check(qualification.blueprint.strategyId === "nim_xor_zero_else_first_legal_v1", "maps the supported harness to an explicit deterministic strategy");
  check(qualification.executionBlockers.length === 0, "ready qualification has no hidden blockers");
  check(Object.values(qualification.attestations).every((value) => value === false), "qualification retains zero attestations");
  check(qualification.resourceClass.networkAllowed === false && qualification.resourceClass.providerAllowed === false && qualification.resourceClass.modelAllowed === false && qualification.resourceClass.persistenceAllowed === false, "qualification grants no network, provider, model, or persistence authority");

  for (const [field, expected] of [["strictValidation", "strict_validation_required"], ["fallbackDisclosure", "fallback_disclosure_required"]]) {
    const changed = copy(blueprint);
    changed[field] = false;
    const blocked = adapter.buildLocalExhibitionQualification(changed, fixture, "verified_corpus");
    check(blocked.executionStatus === "disabled" && blocked.executionBlockers.includes(expected), `blocks missing ${field}`);
  }
  const unsupported = copy(blueprint);
  unsupported.harnessStyle = "Budget-aware planner";
  const unsupportedQualification = adapter.buildLocalExhibitionQualification(unsupported, fixture, "verified_corpus");
  check(unsupportedQualification.executionStatus === "disabled" && unsupportedQualification.executionBlockers.includes("harness_style_not_supported_by_local_exhibition"), "refuses unsupported strategy labels");
  await rejects(() => adapter.createLocalExhibitionReceipt(unsupportedQualification), "qualification is not executable");
  const unknownQualificationField = copy(qualification);
  unknownQualificationField.unreviewed = true;
  await rejects(() => adapter.createLocalExhibitionReceipt(unknownQualificationField), "fields drift");
  const qualificationKeyDrift = copy(qualification);
  qualificationKeyDrift.qualificationKey += ":changed";
  await rejects(() => adapter.createLocalExhibitionReceipt(qualificationKeyDrift), "qualification key drift");
  await rejects(() => Promise.resolve(adapter.buildLocalExhibitionQualification(blueprint, fixture, "demo_fixture_fallback")), "verified corpus required");
  for (const [field, value, expected] of [
    ["id", "f".repeat(64), "fixture id drift"],
    ["rulesDigest", "e".repeat(64), "rules binding drift"],
    ["resourceClass", "paid-remote", "resource class drift"],
    ["ranked", true, "ranked claim drift"],
  ]) {
    const changed = copy(fixture);
    changed[field] = value;
    await rejects(() => Promise.resolve(adapter.buildLocalExhibitionQualification(blueprint, changed, "verified_corpus")), expected);
  }

  const receipt = await adapter.createLocalExhibitionReceipt(qualification);
  const repeatedReceipt = await adapter.createLocalExhibitionReceipt(qualification);
  check(receipt.schemaVersion === adapter.LOCAL_EXHIBITION_RECEIPT_SCHEMA, "uses the versioned receipt-candidate schema");
  check(receipt.receiptStatus === "local_receipt_candidate_unreviewed", "keeps the result an unreviewed local candidate");
  check(receipt.candidateDigest === repeatedReceipt.candidateDigest, "receipt candidate is deterministic");
  check(/^[0-9a-f]{64}$/.test(receipt.candidateDigest), "receipt carries a content-shaped digest");
  check(receipt.result.winnerSeat === 0 && receipt.result.reason === "took_last_object", "solved harness wins the fixed conformance position");
  check(receipt.result.moveCount === 7 && receipt.transcript.length === 7, "records the exact bounded transcript");
  check(receipt.transcript.every((move, index) => move.turn === index && move.moveSource === "deterministic_scripted"), "labels every ordered move deterministic scripted");
  check(receipt.evidence.moveSourceCounts.deterministicScripted === 7 && receipt.evidence.moveSourceCounts.model === 0 && receipt.evidence.moveSourceCounts.provider === 0, "reports exact scripted, model, and provider counts");
  check(receipt.evidence.declaredBaseUsed === false && receipt.evidence.hiddenReasoningInferred === false, "does not claim base use or hidden reasoning");
  check(receipt.storageStatus === "browser_memory_only_not_persisted", "keeps the receipt in browser memory only");
  check(receipt.registryStatus === "not_requested" && receipt.publicationStatus === "not_requested" && receipt.ranked === false, "keeps registry, publication, and ranking absent");
  check(Object.values(receipt.attestations).every((value) => value === false), "receipt retains zero attestations");

  const verification = await adapter.verifyLocalExhibitionReceipt(receipt);
  check(verification.schemaVersion === adapter.LOCAL_EXHIBITION_VERIFICATION_SCHEMA, "uses the versioned replay schema");
  check(verification.verificationStatus === "verified_local_receipt_candidate" && verification.replayVerdict === "PASS", "independently reconstructs and verifies the candidate");
  check(verification.replayedMoveCount === 7 && verification.modelMoveCount === 0 && verification.providerMoveCount === 0, "verification reports exact move-source totals");
  check(Object.values(verification.attestations).every((value) => value === false), "verification creates no authority");

  const learning = await adapter.createLocalExhibitionLearning(receipt, verification);
  check(learning.schemaVersion === adapter.LOCAL_EXHIBITION_LEARNING_SCHEMA && learning.learningStatus === "verified_local_observation_only", "derives a versioned observation-only learning object");
  check(learning.parentCandidateDigest === receipt.candidateDigest && learning.replayVerdict === "PASS", "learning binds the verified parent");
  check(learning.hiddenReasoningInferred === false && learning.lessonId === "inspect_xor_zero_strategy", "learning stays on visible game state");
  check(/^[0-9a-f]{64}$/.test(learning.learningDigest), "learning carries a content-shaped digest");
  check(Object.values(learning.authority).every((value) => value === false), "learning creates no authority");

  const runback = await adapter.createLocalExhibitionRunback(receipt, verification, learning);
  const repeatedRunback = await adapter.createLocalExhibitionRunback(receipt, verification, learning);
  check(runback.schemaVersion === adapter.LOCAL_EXHIBITION_RUNBACK_SCHEMA && runback.runbackVersion === 1, "uses the versioned runback schema");
  check(runback.runbackStatus === "versioned_local_runback_unplayed" && runback.executionStatus === "not_run", "keeps the runback unplayed");
  check(runback.parentCandidateDigest === receipt.candidateDigest && runback.parentLearningDigest === learning.learningDigest, "runback binds receipt and learning lineage");
  check(runback.fixtureBinding.rulesDigest === adapter.LOCAL_EXHIBITION_RULES_DIGEST && runback.fixtureBinding.resourceClass === adapter.LOCAL_EXHIBITION_RESOURCE_CLASS, "runback preserves exact rules and resource class");
  check(runback.seatPlan.seatSwap === true && runback.seatPlan.blueprintSeat === 1 && runback.seatPlan.referenceSeat === 0, "runback swaps seats explicitly");
  check(runback.runbackDigest === repeatedRunback.runbackDigest && /^[0-9a-f]{64}$/.test(runback.runbackDigest), "runback is deterministic and digest bound");
  check(runback.registryStatus === "not_requested" && runback.publicationStatus === "not_requested" && runback.ranked === false, "runback creates no public state");
  check(Object.values(runback.attestations).every((value) => value === false), "runback retains zero attestations");

  const digestTamper = copy(receipt);
  digestTamper.result.moveCount = 99;
  await rejects(() => adapter.verifyLocalExhibitionReceipt(digestTamper), "candidate digest mismatch");
  const replayTamper = await rehash(copy(receipt));
  replayTamper.transcript[0].move.take = 1;
  await rehash(replayTamper);
  await rejects(() => adapter.verifyLocalExhibitionReceipt(replayTamper), "deterministic replay mismatch");
  const authorityTamper = copy(receipt);
  authorityTamper.attestations.model = true;
  await rehash(authorityTamper);
  await rejects(() => adapter.verifyLocalExhibitionReceipt(authorityTamper), "deterministic replay mismatch");
  const rulesTamper = copy(receipt);
  rulesTamper.qualification.fixture.rulesDigest = "0".repeat(64);
  await rehash(rulesTamper);
  await rejects(() => adapter.verifyLocalExhibitionReceipt(rulesTamper), "fixture binding drift");
  const verificationTamper = copy(verification);
  verificationTamper.replayVerdict = "FAIL";
  await rejects(() => adapter.createLocalExhibitionLearning(receipt, verificationTamper), "verification drift");
  const learningTamper = copy(learning);
  learningTamper.guidance = "trust me";
  await rejects(() => adapter.createLocalExhibitionRunback(receipt, verification, learningTamper), "learning drift");

  process.stdout.write(JSON.stringify({ status: "PASS", checks: checks.length }));
})().catch((error) => {
  process.stderr.write(error.stack || error.message);
  process.exit(1);
});
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
    require(result.returncode == 0, f"local exhibition check failed: {result.stderr.strip()}")
    payload = json.loads(result.stdout)
    require(payload.get("status") == "PASS", "local exhibition did not report PASS")
    require(payload.get("checks", 0) >= 61, "local exhibition coverage unexpectedly shrank")
    print(f"BuilderWars mobile local exhibition: PASS ({payload['checks']} checks)")
    print("qualification / deterministic play / replay / receipt / learning / versioned unplayed runback")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
