#!/usr/bin/env python3
"""Adversarial checks for deterministic private comparison-linked learning receipts."""

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
    require(node is not None, "Node.js is required to exercise private review learning verification")

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
async function resealOuter(packet) {
  packet.integrity.payloadDigest = await digest(canonical(packet.payload));
  return packet;
}
async function rejectsSerialized(serialized, expected) {
  let message = "";
  try { await adapter.verifyPortablePrivateReviewLearning(serialized); } catch (error) { message = error.message; }
  check(message.includes(expected), `inspection receipt rejects ${expected}`);
}
async function rejectsPacket(mutator, expected, { reseal = false, source = receipt.packet } = {}) {
  const value = copy(source);
  await mutator(value);
  if (reseal) await resealOuter(value);
  await rejectsSerialized(canonical(value), expected);
}

let receipt;

async function makeProposal(agentName = "Inspection Student") {
  const view = await adapter.adaptArenaReadModel(model, demo);
  const proof = view.proofReceipts.find((candidate) => candidate.moveSourceCounts.model > 0);
  const learning = adapter.buildReceiptLearningAction(proof, "verified_corpus");
  const blueprint = {
    agentName,
    baseModel: "Arena Reason",
    harnessStyle: "Human review checkpoints",
    strictValidation: true,
    fallbackDisclosure: true,
    humanCheckpoints: false,
    localOnly: true,
  };
  const proposal = adapter.buildRunbackProposal(learning, blueprint, "require_human_checkpoints", "verified_corpus");
  return adapter.createPortableRunbackEnvelope(proposal);
}

async function appendReview(verified, existing, reviewerLabel, decision, reasonCode) {
  return adapter.appendPortableRunbackReview(verified, { reviewerLabel, decision, reasonCode }, existing);
}

async function appendCorrection(verified, reviews, existing, reviewerLabel, targetReviewDigest, correctedDecision) {
  return adapter.appendPortableRunbackReviewCorrection(verified, reviews, {
    reviewerLabel,
    targetReviewDigest,
    action: "correct_decision",
    correctedDecision,
    reasonCode: "new_private_evidence",
  }, existing);
}

async function makeComparison() {
  const portable = await makeProposal();
  const verified = await adapter.verifyPortableRunbackEnvelope(portable.serialized);
  const changed = await appendReview(verified, [], "Changed Original", "accept_for_blueprint_revision", "receipt_guided_guard_change");
  const identical = await appendReview(verified, [changed], "Identical Original", "defer", "needs_explicit_rules_binding");
  const leftOnly = await appendReview(verified, [changed, identical], "Left Original", "defer", "insufficient_public_evidence");
  const rightOnly = await appendReview(verified, [changed, identical], "Right Original", "reject", "unsafe_or_out_of_scope");
  const leftCorrection = await appendCorrection(verified, [changed, identical, leftOnly], [], "Left Correction", changed.reviewDigest, "defer");
  const rightCorrection = await appendCorrection(verified, [changed, identical, rightOnly], [], "Right Correction", changed.reviewDigest, "reject");
  const leftExchange = await adapter.createPortableRunbackReviewCorrectionExchange(portable.serialized, [changed, identical, leftOnly], [leftCorrection]);
  const rightExchange = await adapter.createPortableRunbackReviewCorrectionExchange(portable.serialized, [changed, identical, rightOnly], [rightCorrection]);
  const comparison = await adapter.createPortablePrivateReviewComparison(leftExchange.serialized, rightExchange.serialized);
  return { portable, verified, changed, identical, leftOnly, rightOnly, leftCorrection, rightCorrection, leftExchange, rightExchange, comparison };
}

async function main() {
  check(adapter.PRIVATE_REVIEW_LEARNING_SCHEMA === "builderwars.mobile-private-review-learning.v1", "exports inspection learning schema");
  check(adapter.PRIVATE_REVIEW_LEARNING_MAX_ENTRIES === 128, "exports inspection learning entry cap");
  check(adapter.PRIVATE_REVIEW_LEARNING_MAX_LENGTH === 2097152, "exports inspection learning size cap");
  check(typeof adapter.createPortablePrivateReviewLearning === "function", "exports inspection learning creator");
  check(typeof adapter.verifyPortablePrivateReviewLearning === "function", "exports inspection learning verifier");
  check(Object.keys(adapter.PRIVATE_REVIEW_INSPECTION_LESSONS).sort().join(",") === "inspect_correction_lineage,inspect_evidence,inspect_rules_binding", "exports only three inspection lessons");

  const fixture = await makeComparison();
  receipt = await adapter.createPortablePrivateReviewLearning(fixture.comparison.serialized);
  const again = await adapter.createPortablePrivateReviewLearning(fixture.comparison.serialized);
  const packet = receipt.packet;
  const learning = packet.payload.learning;
  const sourceDigests = learning.sourceDigests;
  check(packet.schemaVersion === adapter.PRIVATE_REVIEW_LEARNING_SCHEMA && packet.learningVersion === 1, "inspection receipt is exactly versioned");
  check(Object.keys(packet).sort().join(",") === "boundary,integrity,learningVersion,payload,schemaVersion", "inspection outer fields are exact");
  check(Object.keys(packet.payload).sort().join(",") === "comparisonReceipt,learning", "inspection payload fields are exact");
  check(Object.keys(packet.integrity).sort().join(",") === "algorithm,comparisonPacketDigest,leftPacketDigest,payloadDigest,proposalPayloadDigest,rightPacketDigest", "inspection integrity fields are exact");
  check(Object.keys(learning).sort().join(",") === "authority,lessons,sourceDigests,summary", "inspection projection fields are exact");
  check(Object.keys(sourceDigests).sort().join(",") === "comparisonPacketDigest,left,proposalPayloadDigest,right", "inspection source digest fields are exact");
  check(Object.keys(sourceDigests.left).sort().join(",") === "correctionCount,correctionExchangePacketDigest,correctionHeadDigest,packetRole,reviewCount,reviewHeadDigest", "Packet A source fields are exact");
  check(Object.keys(sourceDigests.right).sort().join(",") === "correctionCount,correctionExchangePacketDigest,correctionHeadDigest,packetRole,reviewCount,reviewHeadDigest", "Packet B source fields are exact");
  check(sourceDigests.left.packetRole === "packet_a" && sourceDigests.right.packetRole === "packet_b", "packet roles stay explicit and neutral");
  check(Object.values(learning.authority).every((value) => value === false), "inspection receipt grants no authority");
  check(Object.keys(learning.authority).sort().join(",") === "approval,blueprintAdoption,consensus,execution,identity,merge,progress,provider,publication,qualification,ranking,registry,resolution,rules,spending", "inspection authority fields are exact");
  check(packet.integrity.algorithm === "sha256", "inspection integrity algorithm is exact");
  check(packet.integrity.comparisonPacketDigest === fixture.comparison.packet.integrity.payloadDigest, "inspection binds comparison packet digest");
  check(packet.integrity.leftPacketDigest === fixture.leftExchange.packet.integrity.payloadDigest, "inspection binds Packet A correction packet digest");
  check(packet.integrity.rightPacketDigest === fixture.rightExchange.packet.integrity.payloadDigest, "inspection binds Packet B correction packet digest");
  check(packet.integrity.proposalPayloadDigest === fixture.verified.payloadDigest, "inspection binds proposal payload digest");
  check(sourceDigests.left.reviewHeadDigest === fixture.leftExchange.packet.payload.reviewExchangePacket.integrity.reviewHeadDigest, "inspection preserves Packet A review head digest");
  check(sourceDigests.right.reviewHeadDigest === fixture.rightExchange.packet.payload.reviewExchangePacket.integrity.reviewHeadDigest, "inspection preserves Packet B review head digest");
  check(sourceDigests.left.correctionHeadDigest === fixture.leftCorrection.correctionDigest, "inspection preserves Packet A correction head digest");
  check(sourceDigests.right.correctionHeadDigest === fixture.rightCorrection.correctionDigest, "inspection preserves Packet B correction head digest");
  check(packet.integrity.payloadDigest === await digest(canonical(packet.payload)), "independent inspection payload digest agrees");
  check(receipt.serialized === canonical(packet), "inspection export is canonical JSON");
  check(receipt.serialized === again.serialized, "same comparison creates the same inspection receipt");
  check(receipt.serialized.length <= adapter.PRIVATE_REVIEW_LEARNING_MAX_LENGTH, "inspection receipt stays inside explicit size cap");
  check(learning.summary.entryCount === 4, "inspection counts exact comparison entries");
  check(learning.summary.inspectEvidenceCount === 2, "one-sided reviews map to evidence inspection");
  check(learning.summary.inspectRulesBindingCount === 1, "identical state maps to rules-binding inspection");
  check(learning.summary.inspectCorrectionLineageCount === 1, "changed state maps to correction-lineage inspection");
  check(learning.lessons.map((entry) => entry.reviewDigest).join(",") === [...learning.lessons.map((entry) => entry.reviewDigest)].sort().join(","), "inspection lessons preserve digest order");

  const changedLesson = learning.lessons.find((entry) => entry.reviewDigest === fixture.changed.reviewDigest);
  const identicalLesson = learning.lessons.find((entry) => entry.reviewDigest === fixture.identical.reviewDigest);
  const leftOnlyLesson = learning.lessons.find((entry) => entry.reviewDigest === fixture.leftOnly.reviewDigest);
  const rightOnlyLesson = learning.lessons.find((entry) => entry.reviewDigest === fixture.rightOnly.reviewDigest);
  check(changedLesson.classification === "changed_effective_state" && changedLesson.lessonId === "inspect_correction_lineage", "changed state selects correction-lineage inspection only");
  check(identicalLesson.classification === "identical_effective_state" && identicalLesson.lessonId === "inspect_rules_binding", "identical state selects rules-binding inspection only");
  check(leftOnlyLesson.classification === "left_only_review" && leftOnlyLesson.lessonId === "inspect_evidence", "Packet A-only state selects evidence inspection only");
  check(rightOnlyLesson.classification === "right_only_review" && rightOnlyLesson.lessonId === "inspect_evidence", "Packet B-only state selects evidence inspection only");
  check(changedLesson.left.packetRole === "packet_a" && changedLesson.right.packetRole === "packet_b", "changed lesson preserves both packet roles");
  check(changedLesson.left.latestCorrectionDigest === fixture.leftCorrection.correctionDigest, "changed lesson preserves Packet A correction digest");
  check(changedLesson.right.latestCorrectionDigest === fixture.rightCorrection.correctionDigest, "changed lesson preserves Packet B correction digest");
  check(leftOnlyLesson.right === null && rightOnlyLesson.left === null, "one-sided lesson state remains absent on the other role");
  check(!receipt.serialized.includes('"correctPacket"'), "inspection receipt never names a correct packet");
  check(packet.boundary.includes("without choosing a correct state"), "inspection boundary refuses correctness selection");
  check(packet.boundary.includes("granting consensus, approval"), "inspection boundary refuses approval and progress");
  check(packet.boundary.includes("merging histories"), "inspection boundary refuses merge authority");
  check(packet.boundary.includes("provider authority"), "inspection boundary refuses provider authority");

  const imported = await adapter.verifyPortablePrivateReviewLearning(receipt.serialized);
  check(imported.verificationStatus === "verified_private_local_review_learning", "fresh import remains private local inspection verification");
  check(imported.packetDigest === packet.integrity.payloadDigest, "fresh import recomputes inspection packet digest");
  check(imported.comparisonSerialized === fixture.comparison.serialized, "fresh import reconstructs exact comparison receipt");
  check(imported.comparisonVerification.leftSerialized === fixture.leftExchange.serialized, "fresh import reconstructs exact Packet A source");
  check(imported.comparisonVerification.rightSerialized === fixture.rightExchange.serialized, "fresh import reconstructs exact Packet B source");
  check(canonical(imported.learning) === canonical(learning), "fresh import reconstructs exact inspection projection");
  check(imported.boundary === packet.boundary, "fresh import preserves inspection boundary");

  const swappedComparison = await adapter.createPortablePrivateReviewComparison(fixture.rightExchange.serialized, fixture.leftExchange.serialized);
  const swappedReceipt = await adapter.createPortablePrivateReviewLearning(swappedComparison.serialized);
  const swappedLearning = swappedReceipt.packet.payload.learning;
  check(swappedReceipt.serialized !== receipt.serialized, "swapped packet roles remain explicit in inspection receipt");
  check(swappedLearning.sourceDigests.left.correctionExchangePacketDigest === fixture.rightExchange.packet.integrity.payloadDigest, "swapped Packet A digest follows input role");
  check(swappedLearning.sourceDigests.right.correctionExchangePacketDigest === fixture.leftExchange.packet.integrity.payloadDigest, "swapped Packet B digest follows input role");
  check(swappedLearning.lessons.find((entry) => entry.reviewDigest === fixture.changed.reviewDigest).left.latestCorrectionDigest === fixture.rightCorrection.correctionDigest, "swapped lesson preserves role-specific correction lineage");

  const identicalComparison = await adapter.createPortablePrivateReviewComparison(fixture.leftExchange.serialized, fixture.leftExchange.serialized);
  const identicalReceipt = await adapter.createPortablePrivateReviewLearning(identicalComparison.serialized);
  const identicalImport = await adapter.verifyPortablePrivateReviewLearning(identicalReceipt.serialized);
  check(identicalImport.learning.summary.inspectRulesBindingCount === 3, "same-packet comparison maps every identical review to rules-binding inspection");
  check(identicalImport.learning.summary.inspectEvidenceCount === 0 && identicalImport.learning.summary.inspectCorrectionLineageCount === 0, "same-packet inspection invents no differences");

  await rejectsSerialized("", "input length rejected");
  await rejectsSerialized(" ".repeat(adapter.PRIVATE_REVIEW_LEARNING_MAX_LENGTH + 1), "input length rejected");
  await rejectsSerialized("{", "invalid JSON");
  await rejectsSerialized(JSON.stringify(packet, null, 2), "must use canonical JSON");
  await rejectsSerialized(`${receipt.serialized}\n`, "must use canonical JSON");
  await rejectsSerialized(receipt.serialized.replace('"learningVersion":1', '"learningVersion":1,"learningVersion":1'), "must use canonical JSON");

  await rejectsPacket(async (value) => { value.extra = true; }, "private review learning fields drift");
  await rejectsPacket(async (value) => { delete value.boundary; }, "private review learning fields drift");
  await rejectsPacket(async (value) => { value.schemaVersion = "v2"; }, "schema drift");
  await rejectsPacket(async (value) => { value.learningVersion = 2; }, "schema drift");
  await rejectsPacket(async (value) => { value.boundary = "trusted"; }, "boundary drift");
  await rejectsPacket(async (value) => { value.payload.extra = true; }, "private review learning payload fields drift");
  await rejectsPacket(async (value) => { delete value.payload.learning; }, "private review learning payload fields drift");
  await rejectsPacket(async (value) => { value.integrity.extra = true; }, "private review learning integrity fields drift");
  await rejectsPacket(async (value) => { delete value.integrity.comparisonPacketDigest; }, "private review learning integrity fields drift");
  await rejectsPacket(async (value) => { value.integrity.algorithm = "sha512"; }, "integrity algorithm drift");
  await rejectsPacket(async (value) => { value.integrity.payloadDigest = "bad"; }, "integrity digest drift");
  await rejectsPacket(async (value) => { value.integrity.comparisonPacketDigest = "bad"; }, "integrity digest drift");
  await rejectsPacket(async (value) => { value.integrity.leftPacketDigest = "bad"; }, "integrity digest drift");
  await rejectsPacket(async (value) => { value.integrity.rightPacketDigest = "bad"; }, "integrity digest drift");
  await rejectsPacket(async (value) => { value.integrity.proposalPayloadDigest = "bad"; }, "integrity digest drift");
  await rejectsPacket(async (value) => { value.integrity.comparisonPacketDigest = "0".repeat(64); }, "comparison packet digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.leftPacketDigest = "0".repeat(64); }, "left packet digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.rightPacketDigest = "0".repeat(64); }, "right packet digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.proposalPayloadDigest = "0".repeat(64); }, "proposal digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.payloadDigest = "0".repeat(64); }, "payload digest mismatch");
  await rejectsPacket(async (value) => { value.payload.learning.summary.inspectEvidenceCount = 0; }, "learning projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.learning.lessons[0].lessonId = "inspect_evidence"; }, "learning projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.learning.lessons[0].inspectionGuidance = "Choose A"; }, "learning projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.learning.authority.progress = true; }, "learning projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.learning.authority.consensus = true; }, "learning projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.learning.sourceDigests.left.packetRole = "winner"; }, "learning projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.learning.lessons[0].left.packetRole = "winner"; }, "learning projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.comparisonReceipt.payload.comparison.authority.merge = true; }, "comparison projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.comparisonReceipt.payload.leftCorrectionExchangePacket.payload.corrections[0].correctedDecision = "reject"; }, "correction digest mismatch", { reseal: true });

  const dangerous = copy(packet);
  dangerous.payload.learning.lessons[0]["__proto__"] = { polluted: true };
  await rejectsSerialized(canonical(dangerous).replace('"classification"', '"__proto__":{"polluted":true},"classification"'), "prohibited key");
  const deep = copy(packet);
  let cursor = deep.payload.learning;
  for (let index = 0; index < 40; index += 1) { cursor.deep = {}; cursor = cursor.deep; }
  await rejectsSerialized(canonical(deep), "nesting limit exceeded");
  const nodeBomb = copy(packet);
  nodeBomb.payload.learning.lessons = Array.from({ length: 70000 }, () => null);
  const nodeBombSerialized = canonical(nodeBomb);
  check(nodeBombSerialized.length < adapter.PRIVATE_REVIEW_LEARNING_MAX_LENGTH, "inspection node bomb stays below byte cap");
  await rejectsSerialized(nodeBombSerialized, "node limit exceeded");

  console.log(JSON.stringify({ checks: checks.length, receiptBytes: receipt.serialized.length, digest: receipt.packet.integrity.payloadDigest }));
}

main().catch((error) => {
  console.error(error.stack || error.message || String(error));
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
        timeout=120,
        check=False,
    )
    require(result.returncode == 0, f"private review learning check failed: {result.stderr.strip()}")
    payload = json.loads(result.stdout.strip())
    require(payload["checks"] >= 85, "private review learning coverage unexpectedly small")
    require(payload["receiptBytes"] > 0, "private review learning receipt was empty")
    require(len(payload["digest"]) == 64, "private review learning digest drift")
    print(
        "BuilderWars private review learning: PASS "
        f"({payload['checks']} checks; receipt {payload['receiptBytes']} bytes; digest {payload['digest'][:12]}...)"
    )
    print("verified comparison / fixed inspection lessons / both packet roles and source digests / zero authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
