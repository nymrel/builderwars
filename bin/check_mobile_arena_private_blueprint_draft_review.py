#!/usr/bin/env python3
"""Adversarial checks for deterministic private blueprint-draft review receipts."""

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
    require(node is not None, "Node.js is required to exercise private blueprint-draft reviews")

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
  try { await adapter.verifyPortablePrivateBlueprintDraftReview(serialized); } catch (error) { message = error.message; }
  check(message.includes(expected), `blueprint draft review rejects ${expected}; got ${message}`);
}
async function rejectsPacket(mutator, expected, { reseal = false, source = receipt.packet } = {}) {
  const value = copy(source);
  await mutator(value);
  if (reseal) await resealOuter(value);
  await rejectsSerialized(canonical(value), expected);
}
async function rejectsCreate(draftSerialized, input, expected) {
  let message = "";
  try { await adapter.createPortablePrivateBlueprintDraftReview(draftSerialized, input); } catch (error) { message = error.message; }
  check(message.includes(expected), `blueprint draft review creation rejects ${expected}; got ${message}`);
}

let receipt;

async function makeDraft() {
  const view = await adapter.adaptArenaReadModel(model, demo);
  const proof = view.proofReceipts.find((candidate) => candidate.moveSourceCounts.model > 0);
  const learningAction = adapter.buildReceiptLearningAction(proof, "verified_corpus");
  const proposal = adapter.buildRunbackProposal(learningAction, {
    agentName: "Draft Review Student",
    baseModel: "Arena Reason",
    harnessStyle: "Human review checkpoints",
    strictValidation: true,
    fallbackDisclosure: true,
    humanCheckpoints: false,
    localOnly: true,
  }, "require_human_checkpoints", "verified_corpus");
  const portable = await adapter.createPortableRunbackEnvelope(proposal);
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
  const guardReview = await adapter.createPortablePrivateBlueprintDeltaReview(delta.serialized, {
    reviewerLabel: "Local Revision Reviewer",
    decision: "accept_for_revision",
    reasonCode: "guard_matches_verified_lesson",
  });
  const draft = await adapter.createPortablePrivateBlueprintRevisionDraft(guardReview.serialized);
  return { portable, verified, changed, left, right, comparison, learning, delta, guardReview, draft };
}

async function main() {
  check(adapter.PRIVATE_BLUEPRINT_DRAFT_REVIEW_SCHEMA === "builderwars.mobile-private-blueprint-revision-draft-review.v1", "exports blueprint-draft review schema");
  check(adapter.PRIVATE_BLUEPRINT_DRAFT_REVIEW_MAX_LENGTH === 5242880, "exports blueprint-draft review size cap");
  check(typeof adapter.createPortablePrivateBlueprintDraftReview === "function", "exports blueprint-draft review creator");
  check(typeof adapter.verifyPortablePrivateBlueprintDraftReview === "function", "exports blueprint-draft review verifier");

  const fixture = await makeDraft();
  const input = { reviewerLabel: "Local Draft Reviewer", decision: "accept_for_commit_candidate", reasonCode: "draft_lineage_verified" };
  receipt = await adapter.createPortablePrivateBlueprintDraftReview(fixture.draft.serialized, input);
  const again = await adapter.createPortablePrivateBlueprintDraftReview(fixture.draft.serialized, input);
  const packet = receipt.packet;
  const review = packet.payload.review;
  const candidate = review.localCommitCandidate;
  const draft = fixture.draft.packet.payload.draft;

  check(packet.schemaVersion === adapter.PRIVATE_BLUEPRINT_DRAFT_REVIEW_SCHEMA && packet.reviewVersion === 1, "blueprint draft review is exactly versioned");
  check(Object.keys(packet).sort().join(",") === "boundary,integrity,payload,reviewVersion,schemaVersion", "blueprint draft-review outer fields are exact");
  check(Object.keys(packet.payload).sort().join(",") === "blueprintRevisionDraft,review", "blueprint draft-review payload fields are exact");
  check(Object.keys(packet.integrity).sort().join(",") === "acceptedReviewPacketDigest,algorithm,commitCandidateDigest,draftDigest,draftPacketDigest,guardProposalPacketDigest,parentProposalPayloadDigest,payloadDigest,reviewDigest,selectedReviewDigest", "blueprint draft-review integrity fields are exact");
  check(Object.keys(review).sort().join(",") === "authority,blockers,boundary,decision,draftBinding,localCommitCandidate,reasonCode,reviewDigest,reviewStatus,reviewer,state", "blueprint draft-review record fields are exact");
  check(Object.keys(review.reviewer).sort().join(",") === "identityAttested,label,localOnly", "blueprint draft-review reviewer fields are exact");
  check(Object.keys(review.draftBinding).sort().join(",") === "acceptedReviewDigest,acceptedReviewPacketDigest,appliedGuardId,draftDigest,draftKey,draftPacketDigest,guardProposalPacketDigest,parentProposalPayloadDigest,selectedReviewDigest", "blueprint draft-review binding fields are exact");
  check(Object.keys(review.state).sort().join(",") === "adopted,commitCandidateCreated,commitReadinessStatus,committed,executionStatus,localOnly,played,publicationStatus,qualificationStatus,registryStatus", "blueprint draft-review state fields are exact");
  check(Object.keys(candidate).sort().join(",") === "adopted,appliedGuard,authority,blockers,blueprint,boundary,candidateDigest,candidateKey,commitReadinessStatus,commitReady,committed,executionStatus,guardCompletionStatus,localOnly,parentDraftDigest,parentDraftKey,publicationStatus,qualificationStatus,registryStatus,status,unknownGuardKeys", "commit candidate fields are exact");
  check(Object.keys(candidate.authority).sort().join(",") === "approval,blueprintAdoption,consensus,correctness,execution,identity,merge,progress,provider,publication,qualification,ranking,registry,resolution,rules,spending", "candidate authority fields are exact");
  check(Object.values(review.authority).every((value) => value === false), "draft review grants no authority");
  check(Object.values(candidate.authority).every((value) => value === false), "commit candidate grants no authority");
  check(review.reviewStatus === "private_local_blueprint_revision_draft_review", "review status stays private and local");
  check(review.decision === "accept_for_commit_candidate" && review.reasonCode === "draft_lineage_verified", "accept decision and reason remain exact");
  check(review.reviewer.label === input.reviewerLabel && review.reviewer.identityAttested === false && review.reviewer.localOnly === true, "reviewer remains labelled, unattested, and local");
  check(review.state.localOnly === true && review.state.committed === false && review.state.adopted === false, "review state stays local, uncommitted, and unadopted");
  check(review.state.commitCandidateCreated === true && review.state.commitReadinessStatus === "blocked_unknown_guard_values", "review reports a blocked local candidate");
  check(review.state.qualificationStatus === "not_run" && review.state.played === false && review.state.executionStatus === "disabled", "review stays unqualified, unplayed, and unexecuted");
  check(review.state.registryStatus === "not_requested" && review.state.publicationStatus === "not_requested", "review stays unregistered and unpublished");
  check(candidate.status === "proposed_uncommitted_local_blueprint_commit_candidate", "candidate status remains proposed and uncommitted");
  check(candidate.localOnly === true && candidate.committed === false && candidate.adopted === false && candidate.commitReady === false, "candidate stays local, uncommitted, unadopted, and not ready");
  check(candidate.guardCompletionStatus === "incomplete_unknown_guard_values", "candidate exposes incomplete guard values");
  check(candidate.commitReadinessStatus === "blocked_unknown_guard_values", "unknown guards block commit readiness");
  check(candidate.qualificationStatus === "not_run" && candidate.executionStatus === "disabled", "candidate stays unqualified and unexecuted");
  check(candidate.registryStatus === "not_requested" && candidate.publicationStatus === "not_requested", "candidate stays unregistered and unpublished");
  check(canonical(candidate.blueprint) === canonical(draft.revisedBlueprint), "candidate copies exact reviewed revised blueprint");
  check(canonical(candidate.appliedGuard) === canonical(draft.appliedGuard), "candidate copies exact reviewed guard");
  check(canonical(candidate.unknownGuardKeys) === canonical(draft.unknownGuardKeys) && candidate.unknownGuardKeys.join(",") === "fallbackDisclosure", "candidate preserves exact unknown guards");
  check(candidate.blockers.includes("unknown_guard_values_block_commit_readiness"), "candidate carries unknown-guard blocker");
  check(candidate.blockers.includes("operator_commit_review_not_attested"), "candidate carries operator-review blocker");
  check(candidate.parentDraftKey === draft.draftKey && candidate.parentDraftDigest === draft.draftDigest, "candidate binds exact parent draft");
  check(candidate.candidateKey.includes(review.draftBinding.draftPacketDigest) && candidate.candidateKey.includes(review.draftBinding.appliedGuardId), "candidate key binds draft and applied guard");
  check(review.draftBinding.draftPacketDigest === fixture.draft.packet.integrity.payloadDigest, "review binds draft packet");
  check(review.draftBinding.draftDigest === draft.draftDigest && review.draftBinding.draftKey === draft.draftKey, "review binds draft record");
  check(review.draftBinding.acceptedReviewPacketDigest === fixture.guardReview.packet.integrity.payloadDigest, "review binds accepted guard review packet");
  check(review.draftBinding.acceptedReviewDigest === fixture.guardReview.packet.payload.review.reviewDigest, "review binds accepted guard review");
  check(review.draftBinding.guardProposalPacketDigest === fixture.delta.packet.integrity.payloadDigest, "review binds guard proposal");
  check(review.draftBinding.parentProposalPayloadDigest === fixture.verified.payloadDigest, "review binds parent proposal");
  check(review.draftBinding.selectedReviewDigest === fixture.changed.reviewDigest, "review binds selected review");
  check(review.draftBinding.appliedGuardId === "require_strict_validation", "review binds exact applied guard id");
  check(packet.integrity.algorithm === "sha256", "draft-review integrity algorithm is exact");
  check(packet.integrity.draftPacketDigest === review.draftBinding.draftPacketDigest, "outer integrity binds draft packet");
  check(packet.integrity.draftDigest === review.draftBinding.draftDigest, "outer integrity binds draft digest");
  check(packet.integrity.acceptedReviewPacketDigest === review.draftBinding.acceptedReviewPacketDigest, "outer integrity binds accepted review");
  check(packet.integrity.guardProposalPacketDigest === review.draftBinding.guardProposalPacketDigest, "outer integrity binds guard proposal");
  check(packet.integrity.parentProposalPayloadDigest === review.draftBinding.parentProposalPayloadDigest, "outer integrity binds parent proposal");
  check(packet.integrity.selectedReviewDigest === review.draftBinding.selectedReviewDigest, "outer integrity binds selected review");
  check(packet.integrity.reviewDigest === review.reviewDigest, "outer integrity binds draft review");
  check(packet.integrity.commitCandidateDigest === candidate.candidateDigest, "outer integrity binds commit candidate");
  const reviewPayload = copy(review); delete reviewPayload.reviewDigest;
  check(review.reviewDigest === await digest(canonical(reviewPayload)), "independent review digest agrees");
  const candidatePayload = copy(candidate); delete candidatePayload.candidateDigest;
  check(candidate.candidateDigest === await digest(canonical(candidatePayload)), "independent candidate digest agrees");
  check(packet.integrity.payloadDigest === await digest(canonical(packet.payload)), "independent packet digest agrees");
  check(receipt.serialized === canonical(packet), "draft review export is canonical JSON");
  check(receipt.serialized === again.serialized, "same draft review creates same receipt");
  check(receipt.serialized.length <= adapter.PRIVATE_BLUEPRINT_DRAFT_REVIEW_MAX_LENGTH, "draft review stays inside size cap");
  check(packet.boundary.includes("uncommitted, unadopted local candidate"), "boundary limits accepted candidate state");
  check(packet.boundary.includes("force commit readiness blocked"), "boundary preserves unknown guard blocker");
  check(packet.boundary.includes("calls a provider"), "boundary refuses provider calls");

  const imported = await adapter.verifyPortablePrivateBlueprintDraftReview(receipt.serialized);
  check(imported.verificationStatus === "verified_private_local_blueprint_revision_draft_review", "fresh import remains a private local draft review");
  check(imported.packetDigest === packet.integrity.payloadDigest, "fresh import recomputes packet digest");
  check(imported.draftSerialized === fixture.draft.serialized, "fresh import reconstructs exact draft");
  check(imported.draftVerification.acceptedReviewSerialized === fixture.guardReview.serialized, "fresh import reconstructs accepted guard review");
  check(imported.draftVerification.acceptedReviewVerification.blueprintDeltaSerialized === fixture.delta.serialized, "fresh import reconstructs guard proposal");
  check(imported.draftVerification.acceptedReviewVerification.blueprintDeltaVerification.learningSerialized === fixture.learning.serialized, "fresh import reconstructs learning receipt");
  check(imported.draftVerification.acceptedReviewVerification.blueprintDeltaVerification.learningVerification.comparisonSerialized === fixture.comparison.serialized, "fresh import reconstructs comparison receipt");
  check(imported.draftVerification.acceptedReviewVerification.blueprintDeltaVerification.learningVerification.comparisonVerification.leftSerialized === fixture.left.serialized, "fresh import reconstructs Packet A");
  check(imported.draftVerification.acceptedReviewVerification.blueprintDeltaVerification.learningVerification.comparisonVerification.rightSerialized === fixture.right.serialized, "fresh import reconstructs Packet B");
  check(canonical(imported.review) === canonical(review), "fresh import reconstructs exact review");
  check(imported.boundary === packet.boundary, "fresh import preserves review boundary");

  for (const [decision, reasons] of Object.entries(adapter.PRIVATE_BLUEPRINT_DRAFT_REVIEW_REASONS)) {
    for (const reasonCode of reasons) {
      const value = await adapter.createPortablePrivateBlueprintDraftReview(fixture.draft.serialized, { reviewerLabel: decision, decision, reasonCode });
      const valueReview = value.packet.payload.review;
      check(valueReview.decision === decision && valueReview.reasonCode === reasonCode, `${decision}/${reasonCode} stays allowlisted`);
      check((decision === "accept_for_commit_candidate") === (valueReview.localCommitCandidate !== null), `${decision}/${reasonCode} candidate presence is exact`);
      check(valueReview.state.committed === false && valueReview.state.adopted === false, `${decision}/${reasonCode} remains uncommitted and unadopted`);
      if (decision !== "accept_for_commit_candidate") check(value.packet.integrity.commitCandidateDigest === null, `${decision}/${reasonCode} carries no candidate digest`);
    }
  }

  await rejectsCreate(fixture.draft.serialized, { reviewerLabel: "x", decision: "unknown", reasonCode: "draft_lineage_verified" }, "unknown decision");
  await rejectsCreate(fixture.draft.serialized, { reviewerLabel: "x", decision: "defer", reasonCode: "draft_lineage_verified" }, "decision reason drift");
  await rejectsCreate(fixture.draft.serialized, { reviewerLabel: "", decision: "defer", reasonCode: "required_guard_values_unknown" }, "reviewer label drift");
  await rejectsCreate(fixture.draft.serialized, { reviewerLabel: " padded ", decision: "defer", reasonCode: "required_guard_values_unknown" }, "reviewer label drift");
  await rejectsCreate("{}", input, "private blueprint revision draft fields drift");
  await rejectsSerialized("", "input length rejected");
  await rejectsSerialized(" ".repeat(adapter.PRIVATE_BLUEPRINT_DRAFT_REVIEW_MAX_LENGTH + 1), "input length rejected");
  await rejectsSerialized("{", "invalid JSON");
  await rejectsSerialized(JSON.stringify(packet, null, 2), "must use canonical JSON");
  await rejectsSerialized(`${receipt.serialized}\n`, "must use canonical JSON");
  await rejectsSerialized(receipt.serialized.replace('"reviewVersion":1', '"reviewVersion":1,"reviewVersion":1'), "must use canonical JSON");

  await rejectsPacket(async (value) => { value.extra = true; }, "private blueprint draft review fields drift");
  await rejectsPacket(async (value) => { delete value.boundary; }, "private blueprint draft review fields drift");
  await rejectsPacket(async (value) => { value.schemaVersion = "v2"; }, "schema drift");
  await rejectsPacket(async (value) => { value.reviewVersion = 2; }, "schema drift");
  await rejectsPacket(async (value) => { value.boundary = "trusted"; }, "boundary drift");
  await rejectsPacket(async (value) => { value.payload.extra = true; }, "private blueprint draft review payload fields drift");
  await rejectsPacket(async (value) => { delete value.payload.review; }, "private blueprint draft review payload fields drift");
  await rejectsPacket(async (value) => { value.integrity.extra = true; }, "private blueprint draft review integrity fields drift");
  await rejectsPacket(async (value) => { delete value.integrity.reviewDigest; }, "private blueprint draft review integrity fields drift");
  await rejectsPacket(async (value) => { value.integrity.algorithm = "sha512"; }, "integrity algorithm drift");
  for (const key of ["payloadDigest", "draftPacketDigest", "draftDigest", "acceptedReviewPacketDigest", "guardProposalPacketDigest", "parentProposalPayloadDigest", "selectedReviewDigest", "reviewDigest"]) {
    await rejectsPacket(async (value) => { value.integrity[key] = "bad"; }, `${key} drift`);
  }
  await rejectsPacket(async (value) => { value.integrity.commitCandidateDigest = "bad"; }, "commitCandidateDigest drift");
  await rejectsPacket(async (value) => { value.integrity.draftPacketDigest = "0".repeat(64); }, "draft packet digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.draftDigest = "0".repeat(64); }, "draft digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.acceptedReviewPacketDigest = "0".repeat(64); }, "accepted review packet digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.guardProposalPacketDigest = "0".repeat(64); }, "guard proposal packet digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.parentProposalPayloadDigest = "0".repeat(64); }, "parent proposal digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.selectedReviewDigest = "0".repeat(64); }, "selected review digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.reviewDigest = "0".repeat(64); }, "review digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.commitCandidateDigest = "0".repeat(64); }, "commit candidate digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.payloadDigest = "0".repeat(64); }, "payload digest mismatch");

  await rejectsPacket(async (value) => { value.payload.review.state.committed = true; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.state.adopted = true; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.state.commitReadinessStatus = "ready"; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.localCommitCandidate.committed = true; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.localCommitCandidate.adopted = true; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.localCommitCandidate.commitReady = true; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.localCommitCandidate.commitReadinessStatus = "ready"; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.localCommitCandidate.blueprint.guardValues.fallbackDisclosure = true; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.localCommitCandidate.unknownGuardKeys = []; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.localCommitCandidate.blockers.pop(); }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.blockers.pop(); }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.reviewer.identityAttested = true; }, "review projection mismatch", { reseal: true });
  for (const key of Object.keys(review.authority)) {
    await rejectsPacket(async (value) => { value.payload.review.authority[key] = true; }, "review projection mismatch", { reseal: true });
    await rejectsPacket(async (value) => { value.payload.review.localCommitCandidate.authority[key] = true; }, "review projection mismatch", { reseal: true });
  }
  await rejectsPacket(async (value) => { value.payload.blueprintRevisionDraft.payload.draft.state.committed = true; }, "draft projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.blueprintRevisionDraft.payload.acceptedReviewReceipt.payload.review.localRevisionCandidate.adopted = true; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.blueprintRevisionDraft.payload.acceptedReviewReceipt.payload.blueprintDeltaProposal.payload.proposal.state.played = true; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.blueprintRevisionDraft.payload.acceptedReviewReceipt.payload.blueprintDeltaProposal.payload.learningReceipt.payload.learning.authority.progress = true; }, "learning projection mismatch", { reseal: true });

  const dangerous = copy(packet);
  const dangerousSerialized = canonical(dangerous).replace('"blueprintRevisionDraft"', '"__proto__":{"polluted":true},"blueprintRevisionDraft"');
  await rejectsSerialized(dangerousSerialized, "prohibited key");
  const deep = copy(packet);
  let cursor = deep.payload.review;
  for (let index = 0; index < 40; index += 1) { cursor.deep = {}; cursor = cursor.deep; }
  await rejectsSerialized(canonical(deep), "nesting limit exceeded");
  const nodeBomb = copy(packet);
  nodeBomb.payload.review.blockers = Array.from({ length: 132000 }, () => null);
  const nodeBombSerialized = canonical(nodeBomb);
  check(nodeBombSerialized.length < adapter.PRIVATE_BLUEPRINT_DRAFT_REVIEW_MAX_LENGTH, "draft-review node bomb stays below byte cap");
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
    require(result.returncode == 0, f"private blueprint draft review check failed: {result.stderr.strip()}")
    payload = json.loads(result.stdout.strip())
    require(payload["checks"] >= 150, "private blueprint draft review coverage unexpectedly small")
    require(payload["receiptBytes"] > 0, "private blueprint draft review receipt was empty")
    require(len(payload["digest"]) == 64, "private blueprint draft review digest drift")
    print(
        "BuilderWars private blueprint draft review: PASS "
        f"({payload['checks']} checks; receipt {payload['receiptBytes']} bytes; digest {payload['digest'][:12]}...)"
    )
    print("accept/defer/reject / unknown guards block readiness / uncommitted / unadopted / zero authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
