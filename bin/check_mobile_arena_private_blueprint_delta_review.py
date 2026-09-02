#!/usr/bin/env python3
"""Adversarial checks for deterministic private guard-proposal review receipts."""

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
    require(node is not None, "Node.js is required to exercise private guard-proposal reviews")

    script = r'''
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
  try { await adapter.verifyPortablePrivateBlueprintDeltaReview(serialized); } catch (error) { message = error.message; }
  check(message.includes(expected), `guard review rejects ${expected}; got ${message}`);
}
async function rejectsPacket(mutator, expected, { reseal = false, source = receipt.packet } = {}) {
  const value = copy(source);
  await mutator(value);
  if (reseal) await resealOuter(value);
  await rejectsSerialized(canonical(value), expected);
}
async function rejectsCreate(proposalSerialized, input, expected) {
  let message = "";
  try { await adapter.createPortablePrivateBlueprintDeltaReview(proposalSerialized, input); } catch (error) { message = error.message; }
  check(message.includes(expected), `guard review creation rejects ${expected}`);
}

let receipt;

async function makeProposal() {
  const view = await adapter.adaptArenaReadModel(model, demo);
  const proof = view.proofReceipts.find((candidate) => candidate.moveSourceCounts.model > 0);
  const learning = adapter.buildReceiptLearningAction(proof, "verified_corpus");
  const proposal = adapter.buildRunbackProposal(learning, {
    agentName: "Guard Review Student",
    baseModel: "Arena Reason",
    harnessStyle: "Human review checkpoints",
    strictValidation: true,
    fallbackDisclosure: true,
    humanCheckpoints: false,
    localOnly: true,
  }, "require_human_checkpoints", "verified_corpus");
  return adapter.createPortableRunbackEnvelope(proposal);
}

async function makeDelta() {
  const portable = await makeProposal();
  const verified = await adapter.verifyPortableRunbackEnvelope(portable.serialized);
  const changed = await adapter.appendPortableRunbackReview(verified, {
    reviewerLabel: "Changed Original",
    decision: "accept_for_blueprint_revision",
    reasonCode: "receipt_guided_guard_change",
  }, []);
  const identical = await adapter.appendPortableRunbackReview(verified, {
    reviewerLabel: "Identical Original",
    decision: "defer",
    reasonCode: "needs_explicit_rules_binding",
  }, [changed]);
  const leftOnly = await adapter.appendPortableRunbackReview(verified, {
    reviewerLabel: "Left Original",
    decision: "defer",
    reasonCode: "insufficient_public_evidence",
  }, [changed, identical]);
  const rightOnly = await adapter.appendPortableRunbackReview(verified, {
    reviewerLabel: "Right Original",
    decision: "reject",
    reasonCode: "unsafe_or_out_of_scope",
  }, [changed, identical]);
  const leftCorrection = await adapter.appendPortableRunbackReviewCorrection(verified, [changed, identical, leftOnly], {
    reviewerLabel: "Left Correction",
    targetReviewDigest: changed.reviewDigest,
    action: "correct_decision",
    correctedDecision: "defer",
    reasonCode: "new_private_evidence",
  }, []);
  const rightCorrection = await adapter.appendPortableRunbackReviewCorrection(verified, [changed, identical, rightOnly], {
    reviewerLabel: "Right Correction",
    targetReviewDigest: changed.reviewDigest,
    action: "correct_decision",
    correctedDecision: "reject",
    reasonCode: "new_private_evidence",
  }, []);
  const left = await adapter.createPortableRunbackReviewCorrectionExchange(portable.serialized, [changed, identical, leftOnly], [leftCorrection]);
  const right = await adapter.createPortableRunbackReviewCorrectionExchange(portable.serialized, [changed, identical, rightOnly], [rightCorrection]);
  const comparison = await adapter.createPortablePrivateReviewComparison(left.serialized, right.serialized);
  const learning = await adapter.createPortablePrivateReviewLearning(comparison.serialized);
  const delta = await adapter.createPortablePrivateBlueprintDelta(learning.serialized, changed.reviewDigest);
  return { portable, verified, changed, left, right, comparison, learning, delta };
}

async function main() {
  check(adapter.PRIVATE_BLUEPRINT_DELTA_REVIEW_SCHEMA === "builderwars.mobile-private-inspection-blueprint-delta-review.v1", "exports guard-review schema");
  check(adapter.PRIVATE_BLUEPRINT_DELTA_REVIEW_MAX_LENGTH === 3145728, "exports guard-review size cap");
  check(typeof adapter.createPortablePrivateBlueprintDeltaReview === "function", "exports guard-review creator");
  check(typeof adapter.verifyPortablePrivateBlueprintDeltaReview === "function", "exports guard-review verifier");
  const reasons = adapter.PRIVATE_BLUEPRINT_DELTA_REVIEW_REASONS;
  check(Object.keys(reasons).sort().join(",") === "accept_for_revision,defer,reject", "exports exactly three guard-review decisions");
  check(reasons.accept_for_revision.join(",") === "guard_matches_verified_lesson,guard_closes_local_safety_gap", "accept reasons are fixed");
  check(reasons.defer.join(",") === "needs_explicit_rules_binding,needs_additional_private_evidence,needs_operator_revision_review", "defer reasons are fixed");
  check(reasons.reject.join(",") === "lesson_guard_mismatch,duplicate_or_unnecessary_guard,unsafe_or_out_of_scope", "reject reasons are fixed");

  const fixture = await makeDelta();
  const input = { reviewerLabel: "Local Guard Reviewer", decision: "accept_for_revision", reasonCode: "guard_matches_verified_lesson" };
  receipt = await adapter.createPortablePrivateBlueprintDeltaReview(fixture.delta.serialized, input);
  const again = await adapter.createPortablePrivateBlueprintDeltaReview(fixture.delta.serialized, input);
  const packet = receipt.packet;
  const review = packet.payload.review;
  const binding = review.proposalBinding;
  const candidate = review.localRevisionCandidate;
  const deltaPacket = fixture.delta.packet;
  const deltaProposal = deltaPacket.payload.proposal;

  check(packet.schemaVersion === adapter.PRIVATE_BLUEPRINT_DELTA_REVIEW_SCHEMA && packet.reviewVersion === 1, "guard review is exactly versioned");
  check(Object.keys(packet).sort().join(",") === "boundary,integrity,payload,reviewVersion,schemaVersion", "guard-review outer fields are exact");
  check(Object.keys(packet.payload).sort().join(",") === "blueprintDeltaProposal,review", "guard-review payload fields are exact");
  check(Object.keys(packet.integrity).sort().join(",") === "algorithm,comparisonPacketDigest,learningPacketDigest,leftPacketDigest,parentProposalPayloadDigest,payloadDigest,proposalPacketDigest,reviewDigest,rightPacketDigest,selectedReviewDigest", "guard-review integrity fields are exact");
  check(Object.keys(review).sort().join(",") === "authority,blockers,boundary,decision,localRevisionCandidate,proposalBinding,reasonCode,reviewDigest,reviewStatus,reviewer", "guard-review projection fields are exact");
  check(Object.keys(review.reviewer).sort().join(",") === "identityAttested,label,localOnly", "reviewer fields are exact");
  check(Object.keys(binding).sort().join(",") === "comparisonPacketDigest,guardDeltaId,learningPacketDigest,parentProposalPayloadDigest,proposalKey,proposalPacketDigest,selectedReviewDigest", "guard-review proposal binding fields are exact");
  check(Object.keys(candidate).sort().join(",") === "adopted,committed,guardDelta,localOnly,parentProposalKey,parentProposalPayloadDigest,played,revisionKey,selectedReviewDigest,status", "revision-candidate fields are exact");
  check(Object.keys(review.authority).sort().join(",") === "approval,blueprintAdoption,consensus,correctness,execution,identity,merge,progress,provider,publication,qualification,ranking,registry,resolution,rules,spending", "guard-review authority fields are exact");
  check(Object.values(review.authority).every((value) => value === false), "guard review grants no authority");
  check(review.reviewStatus === "private_local_guard_proposal_review", "guard review remains private and local");
  check(review.decision === input.decision && review.reasonCode === input.reasonCode, "guard review preserves the fixed decision and reason");
  check(review.reviewer.label === input.reviewerLabel, "guard review preserves the local reviewer label");
  check(review.reviewer.identityAttested === false && review.reviewer.localOnly === true, "reviewer remains unattested and local only");
  check(review.blockers.length === 9 && review.blockers[0] === "reviewer_identity_unattested", "guard review preserves exact blocker chain");
  check(review.blockers.includes("local_revision_not_committed") && review.blockers.includes("sanctioned_runner_not_bound"), "guard review keeps revision and runner blockers");
  check(candidate.status === "proposed_uncommitted_local_revision_candidate", "accept creates only an uncommitted local candidate");
  check(candidate.localOnly === true && candidate.committed === false && candidate.adopted === false && candidate.played === false, "candidate remains local, uncommitted, unadopted, and unplayed");
  check(candidate.parentProposalKey === deltaProposal.parentProposalBinding.proposalKey, "candidate binds parent proposal key");
  check(candidate.parentProposalPayloadDigest === deltaProposal.parentProposalBinding.proposalPayloadDigest, "candidate binds parent proposal digest");
  check(candidate.selectedReviewDigest === deltaProposal.selectedLesson.reviewDigest, "candidate binds selected lesson digest");
  check(canonical(candidate.guardDelta) === canonical(deltaProposal.guardDelta), "candidate preserves exact allowlisted guard delta");
  check(candidate.revisionKey.includes(binding.proposalPacketDigest) && candidate.revisionKey.includes(binding.guardDeltaId), "candidate key binds proposal and guard");
  check(binding.proposalPacketDigest === deltaPacket.integrity.payloadDigest, "review binds guard proposal packet digest");
  check(binding.proposalKey === deltaProposal.proposalKey, "review binds guard proposal key");
  check(binding.learningPacketDigest === fixture.learning.packet.integrity.payloadDigest, "review binds learning packet digest");
  check(binding.comparisonPacketDigest === fixture.comparison.packet.integrity.payloadDigest, "review binds comparison packet digest");
  check(binding.parentProposalPayloadDigest === fixture.verified.payloadDigest, "review binds parent proposal digest");
  check(binding.selectedReviewDigest === fixture.changed.reviewDigest, "review binds selected review digest");
  check(binding.guardDeltaId === "require_strict_validation", "review binds exact allowlisted guard id");
  check(packet.integrity.algorithm === "sha256", "guard-review integrity algorithm is exact");
  check(packet.integrity.proposalPacketDigest === binding.proposalPacketDigest, "outer integrity binds guard proposal");
  check(packet.integrity.learningPacketDigest === binding.learningPacketDigest, "outer integrity binds learning receipt");
  check(packet.integrity.comparisonPacketDigest === binding.comparisonPacketDigest, "outer integrity binds comparison receipt");
  check(packet.integrity.parentProposalPayloadDigest === binding.parentProposalPayloadDigest, "outer integrity binds parent proposal");
  check(packet.integrity.leftPacketDigest === fixture.left.packet.integrity.payloadDigest, "outer integrity binds Packet A");
  check(packet.integrity.rightPacketDigest === fixture.right.packet.integrity.payloadDigest, "outer integrity binds Packet B");
  check(packet.integrity.selectedReviewDigest === binding.selectedReviewDigest, "outer integrity binds selected lesson");
  check(packet.integrity.reviewDigest === review.reviewDigest, "outer integrity binds immutable review");
  const reviewDigestPayload = copy(review);
  delete reviewDigestPayload.reviewDigest;
  check(review.reviewDigest === await digest(canonical(reviewDigestPayload)), "independent review digest agrees");
  check(packet.integrity.payloadDigest === await digest(canonical(packet.payload)), "independent packet digest agrees");
  check(receipt.serialized === canonical(packet), "guard-review export is canonical JSON");
  check(receipt.serialized === again.serialized, "same proposal and input create the same review receipt");
  check(receipt.serialized.length <= adapter.PRIVATE_BLUEPRINT_DELTA_REVIEW_MAX_LENGTH, "guard review stays inside explicit size cap");
  check(packet.boundary.includes("records one immutable local review"), "boundary records exactly one immutable review");
  check(packet.boundary.includes("does not adopt or edit the guard"), "boundary refuses guard adoption");
  check(packet.boundary.includes("call a provider"), "boundary refuses provider calls");

  const imported = await adapter.verifyPortablePrivateBlueprintDeltaReview(receipt.serialized);
  check(imported.verificationStatus === "verified_private_local_blueprint_delta_review", "fresh import remains a private local review");
  check(imported.packetDigest === packet.integrity.payloadDigest, "fresh import recomputes packet digest");
  check(imported.blueprintDeltaSerialized === fixture.delta.serialized, "fresh import reconstructs exact guard proposal");
  check(imported.blueprintDeltaVerification.learningSerialized === fixture.learning.serialized, "fresh import reconstructs exact learning receipt");
  check(imported.blueprintDeltaVerification.learningVerification.comparisonSerialized === fixture.comparison.serialized, "fresh import reconstructs exact comparison receipt");
  check(imported.blueprintDeltaVerification.learningVerification.comparisonVerification.leftSerialized === fixture.left.serialized, "fresh import reconstructs Packet A");
  check(imported.blueprintDeltaVerification.learningVerification.comparisonVerification.rightSerialized === fixture.right.serialized, "fresh import reconstructs Packet B");
  check(canonical(imported.review) === canonical(review), "fresh import reconstructs exact immutable review");
  check(imported.boundary === packet.boundary, "fresh import preserves review boundary");

  for (const reasonCode of reasons.accept_for_revision) {
    const value = await adapter.createPortablePrivateBlueprintDeltaReview(fixture.delta.serialized, { reviewerLabel: "Accept", decision: "accept_for_revision", reasonCode });
    check(value.packet.payload.review.localRevisionCandidate !== null, `accept reason ${reasonCode} creates only a candidate`);
  }
  for (const decision of ["defer", "reject"]) {
    for (const reasonCode of reasons[decision]) {
      const value = await adapter.createPortablePrivateBlueprintDeltaReview(fixture.delta.serialized, { reviewerLabel: decision, decision, reasonCode });
      check(value.packet.payload.review.localRevisionCandidate === null, `${decision} reason ${reasonCode} creates no candidate`);
      check(value.packet.payload.review.decision === decision, `${decision} reason ${reasonCode} preserves decision`);
    }
  }

  await rejectsCreate("{}", input, "private blueprint delta fields drift");
  await rejectsCreate(fixture.delta.serialized, {}, "private blueprint delta review input fields drift");
  await rejectsCreate(fixture.delta.serialized, { ...input, extra: true }, "private blueprint delta review input fields drift");
  await rejectsCreate(fixture.delta.serialized, { ...input, reviewerLabel: "" }, "reviewer label drift");
  await rejectsCreate(fixture.delta.serialized, { ...input, reviewerLabel: " x " }, "reviewer label drift");
  await rejectsCreate(fixture.delta.serialized, { ...input, reviewerLabel: "x".repeat(37) }, "reviewer label drift");
  await rejectsCreate(fixture.delta.serialized, { ...input, decision: "approve" }, "unknown decision");
  await rejectsCreate(fixture.delta.serialized, { ...input, reasonCode: "unsafe_or_out_of_scope" }, "decision reason drift");
  await rejectsCreate(fixture.delta.serialized, { ...input, decision: "defer", reasonCode: "guard_matches_verified_lesson" }, "decision reason drift");
  await rejectsSerialized("", "input length rejected");
  await rejectsSerialized(" ".repeat(adapter.PRIVATE_BLUEPRINT_DELTA_REVIEW_MAX_LENGTH + 1), "input length rejected");
  await rejectsSerialized("{", "invalid JSON");
  await rejectsSerialized(JSON.stringify(packet, null, 2), "must use canonical JSON");
  await rejectsSerialized(`${receipt.serialized}\n`, "must use canonical JSON");
  await rejectsSerialized(receipt.serialized.replace('"reviewVersion":1', '"reviewVersion":1,"reviewVersion":1'), "must use canonical JSON");

  await rejectsPacket(async (value) => { value.extra = true; }, "private blueprint delta review fields drift");
  await rejectsPacket(async (value) => { delete value.boundary; }, "private blueprint delta review fields drift");
  await rejectsPacket(async (value) => { value.schemaVersion = "v2"; }, "schema drift");
  await rejectsPacket(async (value) => { value.reviewVersion = 2; }, "schema drift");
  await rejectsPacket(async (value) => { value.boundary = "trusted"; }, "boundary drift");
  await rejectsPacket(async (value) => { value.payload.extra = true; }, "private blueprint delta review payload fields drift");
  await rejectsPacket(async (value) => { delete value.payload.review; }, "private blueprint delta review payload fields drift");
  await rejectsPacket(async (value) => { value.integrity.extra = true; }, "private blueprint delta review integrity fields drift");
  await rejectsPacket(async (value) => { delete value.integrity.reviewDigest; }, "private blueprint delta review integrity fields drift");
  await rejectsPacket(async (value) => { value.integrity.algorithm = "sha512"; }, "integrity algorithm drift");
  for (const key of ["payloadDigest", "proposalPacketDigest", "learningPacketDigest", "comparisonPacketDigest", "parentProposalPayloadDigest", "leftPacketDigest", "rightPacketDigest", "selectedReviewDigest", "reviewDigest"]) {
    await rejectsPacket(async (value) => { value.integrity[key] = "bad"; }, `${key} drift`);
  }
  await rejectsPacket(async (value) => { value.integrity.proposalPacketDigest = "0".repeat(64); }, "proposal packet digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.learningPacketDigest = "0".repeat(64); }, "learning packet digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.comparisonPacketDigest = "0".repeat(64); }, "comparison packet digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.parentProposalPayloadDigest = "0".repeat(64); }, "parent proposal digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.leftPacketDigest = "0".repeat(64); }, "left packet digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.rightPacketDigest = "0".repeat(64); }, "right packet digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.selectedReviewDigest = "0".repeat(64); }, "selected review digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.reviewDigest = "0".repeat(64); }, "review digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.payloadDigest = "0".repeat(64); }, "payload digest mismatch");
  await rejectsPacket(async (value) => { value.payload.review.decision = "reject"; }, "decision reason drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.reasonCode = "guard_closes_local_safety_gap"; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.reviewer.identityAttested = true; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.proposalBinding.guardDeltaId = "network_enabled"; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.localRevisionCandidate.committed = true; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.localRevisionCandidate.adopted = true; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.localRevisionCandidate.played = true; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.localRevisionCandidate.guardDelta.targetValue = false; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.blockers.pop(); }, "review projection mismatch", { reseal: true });
  for (const key of Object.keys(review.authority)) {
    await rejectsPacket(async (value) => { value.payload.review.authority[key] = true; }, "review projection mismatch", { reseal: true });
  }
  await rejectsPacket(async (value) => { value.payload.blueprintDeltaProposal.payload.proposal.state.committed = true; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.blueprintDeltaProposal.payload.learningReceipt.payload.learning.authority.progress = true; }, "learning projection mismatch", { reseal: true });

  const dangerous = copy(packet);
  dangerous.payload.review["__proto__"] = { polluted: true };
  await rejectsSerialized(canonical(dangerous).replace('"authority"', '"__proto__":{"polluted":true},"authority"'), "prohibited key");
  const deep = copy(packet);
  let cursor = deep.payload.review;
  for (let index = 0; index < 40; index += 1) { cursor.deep = {}; cursor = cursor.deep; }
  await rejectsSerialized(canonical(deep), "nesting limit exceeded");
  const nodeBomb = copy(packet);
  nodeBomb.payload.review.blockers = Array.from({ length: 85000 }, () => null);
  const nodeBombSerialized = canonical(nodeBomb);
  check(nodeBombSerialized.length < adapter.PRIVATE_BLUEPRINT_DELTA_REVIEW_MAX_LENGTH, "guard-review node bomb stays below byte cap");
  await rejectsSerialized(nodeBombSerialized, "node limit exceeded");

  console.log(JSON.stringify({ checks: checks.length, receiptBytes: receipt.serialized.length, digest: receipt.packet.integrity.payloadDigest }));
}

main().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exit(1);
});
'''

    result = subprocess.run(
        [node, "-e", script],
        cwd=MOBILE,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=180,
        check=False,
    )
    require(result.returncode == 0, f"private guard-proposal review check failed: {result.stderr.strip()}")
    payload = json.loads(result.stdout.strip())
    require(payload["checks"] >= 120, "private guard-proposal review coverage unexpectedly small")
    require(payload["receiptBytes"] > 0, "private guard-proposal review receipt was empty")
    require(len(payload["digest"]) == 64, "private guard-proposal review digest drift")
    print(
        "BuilderWars private guard-proposal review: PASS "
        f"({payload['checks']} checks; receipt {payload['receiptBytes']} bytes; digest {payload['digest'][:12]}...)"
    )
    print("one immutable decision / accept creates only uncommitted local candidate / defer and reject create none / zero authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
