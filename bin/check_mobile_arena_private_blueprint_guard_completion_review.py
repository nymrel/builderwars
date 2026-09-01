#!/usr/bin/env python3
"""Adversarial checks for immutable private guard-completion reviews."""

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
    require(node is not None, "Node.js is required to exercise private guard-completion reviews")

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
  try { await adapter.verifyPortablePrivateBlueprintGuardCompletionReview(serialized); } catch (error) { message = error.message; }
  check(message.includes(expected), `guard-completion review rejects ${expected}; got ${message}`);
}
async function rejectsPacket(mutator, expected, { reseal = false, source = receipt.packet } = {}) {
  const value = copy(source);
  await mutator(value);
  if (reseal) await resealOuter(value);
  await rejectsSerialized(canonical(value), expected);
}
async function rejectsCreate(completionSerialized, input, expected) {
  let message = "";
  try { await adapter.createPortablePrivateBlueprintGuardCompletionReview(completionSerialized, input); } catch (error) { message = error.message; }
  check(message.includes(expected), `guard-completion review creation rejects ${expected}; got ${message}`);
}

async function makeGuardCompletion() {
  const view = adapter.adaptArenaReadModel(model, demo);
  const proof = view.proofReceipts.find((candidate) => candidate.moveSourceCounts.model > 0);
  const learningAction = adapter.buildReceiptLearningAction(proof, "verified_corpus");
  const proposal = adapter.buildRunbackProposal(learningAction, {
    agentName: "Completion Review Student",
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
  const draftReview = await adapter.createPortablePrivateBlueprintDraftReview(draft.serialized, {
    reviewerLabel: "Local Draft Reviewer",
    decision: "accept_for_commit_candidate",
    reasonCode: "draft_lineage_verified",
  });
  const completion = await adapter.createPortablePrivateBlueprintGuardCompletion(draftReview.serialized, {
    reviewerLabel: "Guard Completion Reviewer",
    reasonCode: "complete_explicit_unknown_guards",
    guardCompletions: [{ guardKey: "fallbackDisclosure", value: false, provenanceCode: "local_reviewer_declared" }],
  });
  return { portable, verified, changed, left, right, comparison, learning, delta, guardReview, draft, draftReview, completion };
}

let receipt;

async function main() {
  check(adapter.PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_SCHEMA === "builderwars.mobile-private-blueprint-guard-completion-review.v1", "exports guard-completion review schema");
  check(adapter.PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_MAX_LENGTH === 7340032, "exports guard-completion review size cap");
  check(Object.keys(adapter.PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_REASONS).join(",") === "accept_for_commit_review,defer,reject", "exports exact review decisions");
  check(typeof adapter.createPortablePrivateBlueprintGuardCompletionReview === "function", "exports guard-completion review creator");
  check(typeof adapter.verifyPortablePrivateBlueprintGuardCompletionReview === "function", "exports guard-completion review verifier");

  const fixture = await makeGuardCompletion();
  const input = {
    reviewerLabel: "Completion Review Referee",
    decision: "accept_for_commit_review",
    reasonCode: "completion_lineage_verified",
  };
  receipt = await adapter.createPortablePrivateBlueprintGuardCompletionReview(fixture.completion.serialized, input);
  const again = await adapter.createPortablePrivateBlueprintGuardCompletionReview(fixture.completion.serialized, input);
  const packet = receipt.packet;
  const review = packet.payload.review;
  const candidate = review.localCommitReviewCandidate;
  const completion = fixture.completion.packet.payload.completionProposal;

  check(packet.schemaVersion === adapter.PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_SCHEMA && packet.reviewVersion === 1, "guard-completion review is exactly versioned");
  check(Object.keys(packet).sort().join(",") === "boundary,integrity,payload,reviewVersion,schemaVersion", "review outer fields are exact");
  check(Object.keys(packet.payload).sort().join(",") === "guardCompletionProposal,review", "review payload fields are exact");
  check(Object.keys(packet.integrity).sort().join(",") === "acceptedReviewPacketDigest,algorithm,candidateDigest,commitCandidateDigest,completionDigest,completionPacketDigest,draftPacketDigest,draftReviewPacketDigest,guardProposalPacketDigest,parentProposalPayloadDigest,payloadDigest,reviewDigest,selectedReviewDigest", "review integrity fields are exact");
  check(Object.keys(review).sort().join(",") === "authority,blockers,boundary,completionBinding,decision,localCommitReviewCandidate,reasonCode,reviewDigest,reviewStatus,reviewer,state", "review record fields are exact");
  check(Object.keys(review.reviewer).sort().join(",") === "identityAttested,label,localOnly", "reviewer fields are exact");
  check(Object.keys(review.completionBinding).sort().join(",") === "acceptedReviewPacketDigest,commitCandidateDigest,completionDigest,completionKey,completionPacketDigest,draftPacketDigest,draftReviewDigest,draftReviewPacketDigest,guardProposalPacketDigest,parentProposalPayloadDigest,selectedReviewDigest", "completion binding fields are exact");
  check(Object.keys(review.state).sort().join(",") === "adopted,commitReadinessStatus,commitReviewCandidateCreated,committed,completionReviewStatus,executionStatus,localOnly,operatorReviewStatus,played,publicationStatus,qualificationStatus,registryStatus", "review state fields are exact");
  check(Object.keys(review.authority).length === 16 && Object.values(review.authority).every((value) => value === false), "review grants no authority");
  check(review.reviewStatus === "private_local_blueprint_guard_completion_review", "review remains a private local object");
  check(review.decision === input.decision && review.reasonCode === input.reasonCode, "review decision and reason stay exact");
  check(review.reviewer.label === input.reviewerLabel && review.reviewer.identityAttested === false && review.reviewer.localOnly === true, "reviewer stays local and unattested");
  check(review.state.localOnly === true && review.state.committed === false && review.state.adopted === false, "review stays local, uncommitted, and unadopted");
  check(review.state.commitReviewCandidateCreated === true && review.state.completionReviewStatus === "accepted_for_operator_commit_review", "accept creates only an operator-review candidate");
  check(review.state.commitReadinessStatus === "requires_operator_commit_review" && review.state.operatorReviewStatus === "not_run", "operator review remains required and not run");
  check(review.state.qualificationStatus === "not_run" && review.state.played === false && review.state.executionStatus === "disabled", "review stays unqualified, unplayed, and unexecuted");
  check(review.state.registryStatus === "not_requested" && review.state.publicationStatus === "not_requested", "review stays unregistered and unpublished");
  check(review.blockers.length === 11 && review.blockers[0] === "reviewer_identity_unattested", "review carries exact blocker chain");
  check(review.blockers.includes("guard_value_provenance_unattested") && review.blockers.includes("operator_commit_review_not_attested"), "review preserves provenance and operator blockers");

  check(candidate.status === "proposed_local_blueprint_candidate_for_operator_commit_review", "accept creates the exact bounded candidate status");
  check(candidate.parentCompletionKey === completion.proposalKey && candidate.parentCompletionDigest === completion.completionDigest, "candidate binds exact completion");
  check(canonical(candidate.blueprint) === canonical(completion.completedBlueprint), "candidate copies exact completed blueprint");
  check(canonical(candidate.guardCompletions) === canonical(completion.guardCompletions), "candidate preserves exact completion provenance");
  check(candidate.blueprint.guardValues.strictValidation === true && candidate.blueprint.guardValues.fallbackDisclosure === false && candidate.blueprint.guardValues.humanCheckpoints === false, "candidate preserves all completed boolean guards");
  check(candidate.guardCompletionStatus === "verified_complete_guard_values", "candidate carries verified complete guard status");
  check(candidate.completionReviewStatus === "accepted_for_operator_commit_review", "candidate records review acceptance only");
  check(candidate.commitReadinessStatus === "requires_operator_commit_review" && candidate.operatorReviewStatus === "not_run", "candidate remains pending operator review");
  check(candidate.localOnly === true && candidate.committed === false && candidate.adopted === false && candidate.commitReady === false, "candidate is never committed, adopted, or commit-ready");
  check(candidate.qualificationStatus === "not_run" && candidate.played === false && candidate.executionStatus === "disabled", "candidate is unqualified, unplayed, and unexecuted");
  check(candidate.registryStatus === "not_requested" && candidate.publicationStatus === "not_requested", "candidate is unregistered and unpublished");
  check(candidate.blockers.length === 11 && Object.values(candidate.authority).every((value) => value === false), "candidate preserves blockers and zero authority");

  check(review.completionBinding.completionPacketDigest === fixture.completion.packet.integrity.payloadDigest, "review binds completion packet");
  check(review.completionBinding.completionDigest === completion.completionDigest, "review binds completion record");
  check(review.completionBinding.draftReviewPacketDigest === fixture.draftReview.packet.integrity.payloadDigest, "review binds draft-review packet");
  check(review.completionBinding.commitCandidateDigest === fixture.draftReview.packet.payload.review.localCommitCandidate.candidateDigest, "review binds source commit candidate");
  check(review.completionBinding.draftPacketDigest === fixture.draft.packet.integrity.payloadDigest, "review binds draft packet");
  check(review.completionBinding.acceptedReviewPacketDigest === fixture.guardReview.packet.integrity.payloadDigest, "review binds accepted guard review");
  check(review.completionBinding.guardProposalPacketDigest === fixture.delta.packet.integrity.payloadDigest, "review binds guard proposal");
  check(review.completionBinding.parentProposalPayloadDigest === fixture.verified.payloadDigest, "review binds parent proposal");
  check(review.completionBinding.selectedReviewDigest === fixture.changed.reviewDigest, "review binds selected review");
  for (const key of ["completionPacketDigest", "completionDigest", "draftReviewPacketDigest", "commitCandidateDigest", "draftPacketDigest", "acceptedReviewPacketDigest", "guardProposalPacketDigest", "parentProposalPayloadDigest", "selectedReviewDigest"]) {
    check(packet.integrity[key] === review.completionBinding[key], `outer integrity binds ${key}`);
  }
  check(packet.integrity.reviewDigest === review.reviewDigest, "outer integrity binds review digest");
  check(packet.integrity.candidateDigest === candidate.candidateDigest, "outer integrity binds candidate digest");
  const reviewPayload = copy(review); delete reviewPayload.reviewDigest;
  check(review.reviewDigest === await digest(canonical(reviewPayload)), "independent review digest agrees");
  const candidatePayload = copy(candidate); delete candidatePayload.candidateDigest;
  check(candidate.candidateDigest === await digest(canonical(candidatePayload)), "independent candidate digest agrees");
  check(packet.integrity.payloadDigest === await digest(canonical(packet.payload)), "independent packet digest agrees");
  check(receipt.serialized === canonical(packet), "review export is canonical JSON");
  check(receipt.serialized === again.serialized, "same review input creates same receipt");
  check(receipt.serialized.length <= adapter.PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_MAX_LENGTH, "review stays inside size cap");
  check(packet.boundary.includes("later operator commit decision"), "boundary preserves later operator decision");
  check(packet.boundary.includes("does not attest reviewer identity or guard-value provenance"), "boundary refuses identity and provenance attestation");
  check(packet.boundary.includes("call a provider"), "boundary refuses provider calls");

  const imported = await adapter.verifyPortablePrivateBlueprintGuardCompletionReview(receipt.serialized);
  check(imported.verificationStatus === "verified_private_local_blueprint_guard_completion_review", "fresh import remains a private local review");
  check(imported.packetDigest === packet.integrity.payloadDigest, "fresh import recomputes packet digest");
  check(imported.guardCompletionSerialized === fixture.completion.serialized, "fresh import reconstructs exact completion");
  check(imported.guardCompletionVerification.draftReviewSerialized === fixture.draftReview.serialized, "fresh import reconstructs exact draft review");
  check(imported.guardCompletionVerification.draftReviewVerification.draftSerialized === fixture.draft.serialized, "fresh import reconstructs exact blueprint draft");
  check(imported.guardCompletionVerification.draftReviewVerification.draftVerification.acceptedReviewSerialized === fixture.guardReview.serialized, "fresh import reconstructs accepted guard review");
  check(imported.guardCompletionVerification.draftReviewVerification.draftVerification.acceptedReviewVerification.blueprintDeltaSerialized === fixture.delta.serialized, "fresh import reconstructs guard proposal");
  check(imported.guardCompletionVerification.draftReviewVerification.draftVerification.acceptedReviewVerification.blueprintDeltaVerification.learningSerialized === fixture.learning.serialized, "fresh import reconstructs learning receipt");
  check(imported.guardCompletionVerification.draftReviewVerification.draftVerification.acceptedReviewVerification.blueprintDeltaVerification.learningVerification.comparisonSerialized === fixture.comparison.serialized, "fresh import reconstructs comparison");
  check(canonical(imported.review) === canonical(review), "fresh import reconstructs exact review");
  check(imported.boundary === packet.boundary, "fresh import preserves review boundary");

  for (const [decision, reasons] of Object.entries(adapter.PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_REASONS)) {
    for (const reasonCode of reasons) {
      const variant = await adapter.createPortablePrivateBlueprintGuardCompletionReview(fixture.completion.serialized, {
        reviewerLabel: "Variant Referee",
        decision,
        reasonCode,
      });
      const variantReview = variant.packet.payload.review;
      check(variantReview.decision === decision && variantReview.reasonCode === reasonCode, `${decision}/${reasonCode} remains allowlisted`);
      check((variantReview.localCommitReviewCandidate !== null) === (decision === "accept_for_commit_review"), `${decision}/${reasonCode} candidate creation stays fail closed`);
      check(variantReview.state.committed === false && variantReview.state.adopted === false && variantReview.state.played === false, `${decision}/${reasonCode} never commits, adopts, or plays`);
      check(Object.values(variantReview.authority).every((value) => value === false), `${decision}/${reasonCode} grants zero authority`);
      if (variantReview.localCommitReviewCandidate) check(variantReview.localCommitReviewCandidate.commitReady === false, `${decision}/${reasonCode} remains not commit-ready`);
      else check(variant.packet.integrity.candidateDigest === null && variantReview.state.commitReadinessStatus === "not_requested", `${decision}/${reasonCode} carries no candidate digest or readiness`);
    }
  }

  await rejectsCreate(fixture.completion.serialized, { reviewerLabel: "x", decision: "unknown", reasonCode: "completion_lineage_verified" }, "unknown decision");
  await rejectsCreate(fixture.completion.serialized, { reviewerLabel: "x", decision: "defer", reasonCode: "completion_lineage_verified" }, "decision reason drift");
  await rejectsCreate(fixture.completion.serialized, { reviewerLabel: "", decision: input.decision, reasonCode: input.reasonCode }, "reviewer label drift");
  await rejectsCreate(fixture.completion.serialized, { reviewerLabel: " padded ", decision: input.decision, reasonCode: input.reasonCode }, "reviewer label drift");
  await rejectsCreate(fixture.completion.serialized, { reviewerLabel: "x", decision: input.decision, reasonCode: input.reasonCode, extra: true }, "review input fields drift");
  await rejectsCreate("{}", input, "private blueprint guard completion fields drift");
  await rejectsSerialized("", "input length rejected");
  await rejectsSerialized(" ".repeat(adapter.PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_MAX_LENGTH + 1), "input length rejected");
  await rejectsSerialized("{", "invalid JSON");
  await rejectsSerialized(JSON.stringify(packet, null, 2), "must use canonical JSON");
  await rejectsSerialized(`${receipt.serialized}\n`, "must use canonical JSON");
  await rejectsSerialized(receipt.serialized.replace('"reviewVersion":1', '"reviewVersion":1,"reviewVersion":1'), "must use canonical JSON");

  await rejectsPacket(async (value) => { value.extra = true; }, "private blueprint guard completion review fields drift");
  await rejectsPacket(async (value) => { delete value.boundary; }, "private blueprint guard completion review fields drift");
  await rejectsPacket(async (value) => { value.schemaVersion = "v2"; }, "schema drift");
  await rejectsPacket(async (value) => { value.reviewVersion = 2; }, "schema drift");
  await rejectsPacket(async (value) => { value.boundary = "trusted"; }, "boundary drift");
  await rejectsPacket(async (value) => { value.payload.extra = true; }, "private blueprint guard completion review payload fields drift");
  await rejectsPacket(async (value) => { delete value.payload.review; }, "private blueprint guard completion review payload fields drift");
  await rejectsPacket(async (value) => { value.integrity.extra = true; }, "private blueprint guard completion review integrity fields drift");
  await rejectsPacket(async (value) => { delete value.integrity.reviewDigest; }, "private blueprint guard completion review integrity fields drift");
  await rejectsPacket(async (value) => { value.integrity.algorithm = "sha512"; }, "integrity algorithm drift");
  for (const key of ["payloadDigest", "completionPacketDigest", "completionDigest", "draftReviewPacketDigest", "commitCandidateDigest", "draftPacketDigest", "acceptedReviewPacketDigest", "guardProposalPacketDigest", "parentProposalPayloadDigest", "selectedReviewDigest", "reviewDigest"]) {
    await rejectsPacket(async (value) => { value.integrity[key] = "bad"; }, `${key} drift`);
  }
  await rejectsPacket(async (value) => { value.integrity.candidateDigest = "bad"; }, "candidateDigest drift");
  for (const [key, expected] of [
    ["completionPacketDigest", "completion packet digest binding mismatch"],
    ["completionDigest", "completion digest binding mismatch"],
    ["draftReviewPacketDigest", "draft review packet digest binding mismatch"],
    ["commitCandidateDigest", "commit candidate digest binding mismatch"],
    ["draftPacketDigest", "draft packet digest binding mismatch"],
    ["acceptedReviewPacketDigest", "accepted review packet digest binding mismatch"],
    ["guardProposalPacketDigest", "guard proposal packet digest binding mismatch"],
    ["parentProposalPayloadDigest", "parent proposal digest binding mismatch"],
    ["selectedReviewDigest", "selected review digest binding mismatch"],
    ["reviewDigest", "review digest binding mismatch"],
    ["candidateDigest", "candidate digest binding mismatch"],
  ]) await rejectsPacket(async (value) => { value.integrity[key] = "0".repeat(64); }, expected);
  await rejectsPacket(async (value) => { value.integrity.payloadDigest = "0".repeat(64); }, "payload digest mismatch");

  await rejectsPacket(async (value) => { value.payload.review.reviewer.identityAttested = true; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.decision = "defer"; }, "decision reason drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.state.committed = true; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.state.adopted = true; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.state.operatorReviewStatus = "approved"; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.state.qualificationStatus = "passed"; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.state.played = true; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.state.executionStatus = "enabled"; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.blockers.pop(); }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.localCommitReviewCandidate.commitReady = true; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.localCommitReviewCandidate.committed = true; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.localCommitReviewCandidate.adopted = true; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.localCommitReviewCandidate.operatorReviewStatus = "approved"; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.localCommitReviewCandidate.blueprint.guardValues.fallbackDisclosure = true; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.review.localCommitReviewCandidate.guardCompletions[0].provenance.identityAttested = true; }, "review projection mismatch", { reseal: true });
  for (const key of Object.keys(review.authority)) {
    await rejectsPacket(async (value) => { value.payload.review.authority[key] = true; }, "review projection mismatch", { reseal: true });
    await rejectsPacket(async (value) => { value.payload.review.localCommitReviewCandidate.authority[key] = true; }, "review projection mismatch", { reseal: true });
  }
  await rejectsPacket(async (value) => { value.payload.guardCompletionProposal.payload.completionProposal.state.commitReady = true; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.guardCompletionProposal.payload.completionProposal.completedBlueprint.guardValues.strictValidation = false; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.guardCompletionProposal.payload.acceptedDraftReviewReceipt.payload.review.localCommitCandidate.committed = true; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.guardCompletionProposal.payload.acceptedDraftReviewReceipt.payload.blueprintRevisionDraft.payload.draft.state.adopted = true; }, "draft projection mismatch", { reseal: true });

  const dangerous = copy(packet);
  const dangerousSerialized = canonical(dangerous).replace('"guardCompletionProposal"', '"__proto__":{"polluted":true},"guardCompletionProposal"');
  await rejectsSerialized(dangerousSerialized, "prohibited key");
  const deep = copy(packet);
  let cursor = deep.payload.review;
  for (let index = 0; index < 40; index += 1) { cursor.deep = {}; cursor = cursor.deep; }
  await rejectsSerialized(canonical(deep), "nesting limit exceeded");
  const nodeBomb = copy(packet);
  nodeBomb.payload.review.blockers = Array.from({ length: 200000 }, () => null);
  const nodeBombSerialized = canonical(nodeBomb);
  check(nodeBombSerialized.length < adapter.PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_MAX_LENGTH, "review node bomb stays below byte cap");
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
        timeout=240,
        check=False,
    )
    require(result.returncode == 0, f"private guard-completion review check failed: {result.stderr.strip()}")
    payload = json.loads(result.stdout.strip())
    require(payload["checks"] >= 185, "private guard-completion review coverage unexpectedly small")
    require(payload["receiptBytes"] > 0, "private guard-completion review receipt was empty")
    require(len(payload["digest"]) == 64, "private guard-completion review digest drift")
    print(
        "BuilderWars private guard-completion review: PASS "
        f"({payload['checks']} checks; receipt {payload['receiptBytes']} bytes; digest {payload['digest'][:12]}...)"
    )
    print("immutable review / accept-defer-reject / exact completed blueprint / operator review required / not commit-ready / zero authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
