#!/usr/bin/env python3
"""Adversarial checks for deterministic private review-state comparison receipts."""

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
    require(node is not None, "Node.js is required to exercise private review comparison verification")

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
  try { await adapter.verifyPortablePrivateReviewComparison(serialized); } catch (error) { message = error.message; }
  check(message.includes(expected), `comparison receipt rejects ${expected}`);
}
async function rejectsPacket(mutator, expected, { reseal = false, source = receipt.packet } = {}) {
  const value = copy(source);
  await mutator(value);
  if (reseal) await resealOuter(value);
  await rejectsSerialized(canonical(value), expected);
}

let receipt;

async function makeProposal(agentName = "Comparison Student") {
  const view = adapter.adaptArenaReadModel(model, demo);
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

async function main() {
  check(adapter.PORTABLE_REVIEW_COMPARISON_SCHEMA === "builderwars.mobile-private-review-comparison.v1", "exports comparison schema");
  check(adapter.PORTABLE_REVIEW_COMPARISON_MAX_ENTRIES === 128, "exports comparison entry cap");
  check(adapter.PORTABLE_REVIEW_COMPARISON_MAX_LENGTH === 1572864, "exports comparison size cap");
  check(typeof adapter.createPortablePrivateReviewComparison === "function", "exports comparison creator");
  check(typeof adapter.verifyPortablePrivateReviewComparison === "function", "exports comparison verifier");

  const portable = await makeProposal();
  const verified = await adapter.verifyPortableRunbackEnvelope(portable.serialized);
  const common = await appendReview(verified, [], "Common Original", "accept_for_blueprint_revision", "receipt_guided_guard_change");
  const leftOnly = await appendReview(verified, [common], "Left Original", "defer", "needs_explicit_rules_binding");
  const rightOnly = await appendReview(verified, [common], "Right Original", "reject", "unsafe_or_out_of_scope");
  const leftCorrection = await appendCorrection(verified, [common, leftOnly], [], "Left Correction", common.reviewDigest, "defer");
  const rightCorrection = await appendCorrection(verified, [common, rightOnly], [], "Right Correction", common.reviewDigest, "reject");
  const leftExchange = await adapter.createPortableRunbackReviewCorrectionExchange(portable.serialized, [common, leftOnly], [leftCorrection]);
  const rightExchange = await adapter.createPortableRunbackReviewCorrectionExchange(portable.serialized, [common, rightOnly], [rightCorrection]);

  receipt = await adapter.createPortablePrivateReviewComparison(leftExchange.serialized, rightExchange.serialized);
  const again = await adapter.createPortablePrivateReviewComparison(leftExchange.serialized, rightExchange.serialized);
  const packet = receipt.packet;
  const comparison = packet.payload.comparison;
  check(packet.schemaVersion === adapter.PORTABLE_REVIEW_COMPARISON_SCHEMA && packet.comparisonVersion === 1, "comparison receipt is exactly versioned");
  check(Object.keys(packet).sort().join(",") === "boundary,comparisonVersion,integrity,payload,schemaVersion", "comparison outer fields are exact");
  check(Object.keys(packet.payload).sort().join(",") === "comparison,leftCorrectionExchangePacket,rightCorrectionExchangePacket", "comparison payload fields are exact");
  check(Object.keys(packet.integrity).sort().join(",") === "algorithm,leftPacketDigest,payloadDigest,proposalPayloadDigest,rightPacketDigest", "comparison integrity fields are exact");
  check(Object.keys(comparison).sort().join(",") === "authority,entries,left,proposalPayloadDigest,right,summary", "comparison projection fields are exact");
  check(Object.values(comparison.authority).every((value) => value === false), "comparison grants no authority");
  check(Object.keys(comparison.authority).sort().join(",") === "execution,identity,merge,publication,qualification,ranking,registry,resolution,rules,spending", "comparison authority fields are exact");
  check(packet.integrity.algorithm === "sha256", "comparison integrity algorithm is exact");
  check(packet.integrity.leftPacketDigest === leftExchange.packet.integrity.payloadDigest, "comparison binds left packet digest");
  check(packet.integrity.rightPacketDigest === rightExchange.packet.integrity.payloadDigest, "comparison binds right packet digest");
  check(packet.integrity.proposalPayloadDigest === verified.payloadDigest, "comparison binds shared proposal digest");
  check(packet.integrity.payloadDigest === await digest(canonical(packet.payload)), "independent comparison payload digest agrees");
  check(receipt.serialized === canonical(packet), "comparison export is canonical JSON");
  check(receipt.serialized === again.serialized, "same two packets compare deterministically");
  check(receipt.serialized.length <= adapter.PORTABLE_REVIEW_COMPARISON_MAX_LENGTH, "comparison stays inside explicit size cap");
  check(comparison.summary.distinctReviewCount === 3, "comparison counts exact distinct reviews");
  check(comparison.summary.sharedReviewCount === 1, "comparison counts exact shared reviews");
  check(comparison.summary.leftOnlyReviewCount === 1 && comparison.summary.rightOnlyReviewCount === 1, "comparison counts one-sided reviews");
  check(comparison.summary.changedEffectiveStateCount === 1 && comparison.summary.identicalEffectiveStateCount === 0, "comparison counts changed shared state");
  check(comparison.entries.map((entry) => entry.reviewDigest).join(",") === [...comparison.entries.map((entry) => entry.reviewDigest)].sort().join(","), "comparison entries are digest sorted");
  const commonEntry = comparison.entries.find((entry) => entry.reviewDigest === common.reviewDigest);
  check(commonEntry.presence === "both" && commonEntry.classification === "changed_effective_state", "shared corrected review is classified as changed");
  check(commonEntry.left.originalDecision === "accept_for_blueprint_revision" && commonEntry.right.originalDecision === "accept_for_blueprint_revision", "comparison preserves immutable original decision");
  check(commonEntry.left.effectiveDecision === "defer" && commonEntry.right.effectiveDecision === "reject", "comparison projects each latest effective decision");
  check(commonEntry.left.latestCorrectionDigest === leftCorrection.correctionDigest && commonEntry.right.latestCorrectionDigest === rightCorrection.correctionDigest, "comparison binds each effective correction head");
  check(comparison.entries.some((entry) => entry.reviewDigest === leftOnly.reviewDigest && entry.classification === "left_only_review" && entry.right === null), "left-only review stays factual and unmerged");
  check(comparison.entries.some((entry) => entry.reviewDigest === rightOnly.reviewDigest && entry.classification === "right_only_review" && entry.left === null), "right-only review stays factual and unmerged");
  check(packet.boundary.includes("without choosing a winner"), "comparison boundary refuses winner selection");
  check(packet.boundary.includes("merging histories"), "comparison boundary refuses history merge");
  check(packet.boundary.includes("resolving a dispute"), "comparison boundary refuses dispute resolution");
  check(packet.boundary.includes("calling a provider"), "comparison boundary refuses provider calls");

  const imported = await adapter.verifyPortablePrivateReviewComparison(receipt.serialized);
  check(imported.verificationStatus === "verified_private_local_review_comparison", "fresh import remains private local comparison verification");
  check(imported.packetDigest === packet.integrity.payloadDigest, "fresh import recomputes comparison packet digest");
  check(imported.leftSerialized === leftExchange.serialized && imported.rightSerialized === rightExchange.serialized, "fresh import reconstructs both exact correction packets");
  check(canonical(imported.comparison) === canonical(comparison), "fresh import reconstructs exact comparison projection");
  check(imported.leftVerification.correctionJournal.effectiveReviews.find((entry) => entry.reviewDigest === common.reviewDigest).effectiveDecision === "defer", "fresh import reverifies left state");
  check(imported.rightVerification.correctionJournal.effectiveReviews.find((entry) => entry.reviewDigest === common.reviewDigest).effectiveDecision === "reject", "fresh import reverifies right state");
  check(imported.boundary === packet.boundary, "fresh import preserves comparison boundary");

  const identical = await adapter.createPortablePrivateReviewComparison(leftExchange.serialized, leftExchange.serialized);
  const identicalImport = await adapter.verifyPortablePrivateReviewComparison(identical.serialized);
  check(identicalImport.comparison.summary.sharedReviewCount === 2, "same-packet comparison shares every review");
  check(identicalImport.comparison.summary.identicalEffectiveStateCount === 2 && identicalImport.comparison.summary.changedEffectiveStateCount === 0, "same-packet comparison reports identical effective states");
  check(identicalImport.comparison.summary.leftOnlyReviewCount === 0 && identicalImport.comparison.summary.rightOnlyReviewCount === 0, "same-packet comparison invents no one-sided reviews");

  const swapped = await adapter.createPortablePrivateReviewComparison(rightExchange.serialized, leftExchange.serialized);
  const swappedCommon = swapped.packet.payload.comparison.entries.find((entry) => entry.reviewDigest === common.reviewDigest);
  check(swapped.serialized !== receipt.serialized, "packet roles remain explicit when inputs are swapped");
  check(swappedCommon.left.effectiveDecision === "reject" && swappedCommon.right.effectiveDecision === "defer", "swapped receipt preserves role-specific states");

  const otherPortable = await makeProposal("Other Proposal");
  const otherVerified = await adapter.verifyPortableRunbackEnvelope(otherPortable.serialized);
  const otherReview = await appendReview(otherVerified, [], "Other Original", "defer", "needs_explicit_rules_binding");
  const otherExchange = await adapter.createPortableRunbackReviewCorrectionExchange(otherPortable.serialized, [otherReview], []);
  let crossProposalMessage = "";
  try { await adapter.createPortablePrivateReviewComparison(leftExchange.serialized, otherExchange.serialized); } catch (error) { crossProposalMessage = error.message; }
  check(crossProposalMessage.includes("proposal mismatch"), "comparison refuses cross-proposal inputs");

  await rejectsSerialized("", "input length rejected");
  await rejectsSerialized(" ".repeat(adapter.PORTABLE_REVIEW_COMPARISON_MAX_LENGTH + 1), "input length rejected");
  await rejectsSerialized("{", "invalid JSON");
  await rejectsSerialized(JSON.stringify(packet, null, 2), "must use canonical JSON");
  await rejectsSerialized(`${receipt.serialized}\n`, "must use canonical JSON");
  await rejectsSerialized(receipt.serialized.replace('"comparisonVersion":1', '"comparisonVersion":1,"comparisonVersion":1'), "must use canonical JSON");

  await rejectsPacket(async (value) => { value.extra = true; }, "portable private review comparison fields drift");
  await rejectsPacket(async (value) => { delete value.boundary; }, "portable private review comparison fields drift");
  await rejectsPacket(async (value) => { value.schemaVersion = "v2"; }, "schema drift");
  await rejectsPacket(async (value) => { value.comparisonVersion = 2; }, "schema drift");
  await rejectsPacket(async (value) => { value.boundary = "trusted"; }, "boundary drift");
  await rejectsPacket(async (value) => { value.payload.extra = true; }, "portable private review comparison payload fields drift");
  await rejectsPacket(async (value) => { delete value.payload.comparison; }, "portable private review comparison payload fields drift");
  await rejectsPacket(async (value) => { value.integrity.extra = true; }, "portable private review comparison integrity fields drift");
  await rejectsPacket(async (value) => { delete value.integrity.leftPacketDigest; }, "portable private review comparison integrity fields drift");
  await rejectsPacket(async (value) => { value.integrity.algorithm = "sha512"; }, "integrity algorithm drift");
  await rejectsPacket(async (value) => { value.integrity.payloadDigest = "bad"; }, "integrity digest drift");
  await rejectsPacket(async (value) => { value.integrity.leftPacketDigest = "bad"; }, "integrity digest drift");
  await rejectsPacket(async (value) => { value.integrity.rightPacketDigest = "bad"; }, "integrity digest drift");
  await rejectsPacket(async (value) => { value.integrity.proposalPayloadDigest = "bad"; }, "integrity digest drift");
  await rejectsPacket(async (value) => { value.integrity.leftPacketDigest = "0".repeat(64); }, "left packet digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.rightPacketDigest = "0".repeat(64); }, "right packet digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.proposalPayloadDigest = "0".repeat(64); }, "proposal digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.payloadDigest = "0".repeat(64); }, "payload digest mismatch");
  await rejectsPacket(async (value) => { value.payload.comparison.summary.changedEffectiveStateCount = 0; }, "comparison projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.comparison.entries[0].classification = "identical_effective_state"; }, "comparison projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.comparison.authority.merge = true; }, "comparison projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.leftCorrectionExchangePacket.payload.corrections[0].correctedDecision = "reject"; }, "correction digest mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.rightCorrectionExchangePacket = copy(value.payload.leftCorrectionExchangePacket); }, "comparison projection mismatch", { reseal: true });

  const dangerous = copy(packet);
  dangerous.payload.comparison.entries[0]["__proto__"] = { polluted: true };
  await rejectsSerialized(canonical(dangerous).replace('"classification"', '"__proto__":{"polluted":true},"classification"'), "prohibited key");
  const deep = copy(packet);
  let cursor = deep.payload.comparison;
  for (let index = 0; index < 40; index += 1) { cursor.deep = {}; cursor = cursor.deep; }
  await rejectsSerialized(canonical(deep), "nesting limit exceeded");
  const nodeBomb = copy(packet);
  nodeBomb.payload.comparison.entries = Array.from({ length: 50000 }, () => null);
  const nodeBombSerialized = canonical(nodeBomb);
  check(nodeBombSerialized.length < adapter.PORTABLE_REVIEW_COMPARISON_MAX_LENGTH, "node bomb stays below byte cap");
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
    require(result.returncode == 0, f"private review comparison check failed: {result.stderr.strip()}")
    payload = json.loads(result.stdout.strip())
    require(payload["checks"] >= 75, "private review comparison coverage unexpectedly small")
    require(payload["receiptBytes"] > 0, "private review comparison receipt was empty")
    require(len(payload["digest"]) == 64, "private review comparison digest drift")
    print(
        "BuilderWars private review comparison: PASS "
        f"({payload['checks']} checks; receipt {payload['receiptBytes']} bytes; digest {payload['digest'][:12]}...)"
    )
    print("same proposal / two reverified correction packets / read-only differences / no merge or resolution authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
