#!/usr/bin/env python3
"""Adversarial checks for deterministic private blueprint guard-completion proposals."""

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
    require(node is not None, "Node.js is required to exercise private blueprint guard completion")

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
  try { await adapter.verifyPortablePrivateBlueprintGuardCompletion(serialized); } catch (error) { message = error.message; }
  check(message.includes(expected), `guard completion rejects ${expected}; got ${message}`);
}
async function rejectsPacket(mutator, expected, { reseal = false, source = receipt.packet } = {}) {
  const value = copy(source);
  await mutator(value);
  if (reseal) await resealOuter(value);
  await rejectsSerialized(canonical(value), expected);
}
async function rejectsCreate(reviewSerialized, input, expected) {
  let message = "";
  try { await adapter.createPortablePrivateBlueprintGuardCompletion(reviewSerialized, input); } catch (error) { message = error.message; }
  check(message.includes(expected), `guard completion creation rejects ${expected}; got ${message}`);
}

let receipt;

async function makeAcceptedDraftReview(decision = "accept_for_commit_candidate") {
  const view = await adapter.adaptArenaReadModel(model, demo);
  const proof = view.proofReceipts.find((candidate) => candidate.moveSourceCounts.model > 0);
  const learningAction = adapter.buildReceiptLearningAction(proof, "verified_corpus");
  const proposal = adapter.buildRunbackProposal(learningAction, {
    agentName: "Guard Completion Student",
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
  const reasonCode = adapter.PRIVATE_BLUEPRINT_DRAFT_REVIEW_REASONS[decision][0];
  const draftReview = await adapter.createPortablePrivateBlueprintDraftReview(draft.serialized, {
    reviewerLabel: "Local Draft Reviewer",
    decision,
    reasonCode,
  });
  return { portable, verified, changed, left, right, comparison, learning, delta, guardReview, draft, draftReview };
}

async function main() {
  check(adapter.PRIVATE_BLUEPRINT_GUARD_COMPLETION_SCHEMA === "builderwars.mobile-private-blueprint-guard-completion-proposal.v1", "exports guard-completion schema");
  check(adapter.PRIVATE_BLUEPRINT_GUARD_COMPLETION_MAX_LENGTH === 6291456, "exports guard-completion size cap");
  check(adapter.PRIVATE_BLUEPRINT_GUARD_COMPLETION_REASONS.length === 3, "exports exact completion reasons");
  check(adapter.PRIVATE_BLUEPRINT_GUARD_COMPLETION_PROVENANCE_CODES.length === 3, "exports exact provenance codes");
  check(typeof adapter.createPortablePrivateBlueprintGuardCompletion === "function", "exports guard-completion creator");
  check(typeof adapter.verifyPortablePrivateBlueprintGuardCompletion === "function", "exports guard-completion verifier");

  const fixture = await makeAcceptedDraftReview();
  const input = {
    reviewerLabel: "Guard Completion Reviewer",
    reasonCode: "complete_explicit_unknown_guards",
    guardCompletions: [{ guardKey: "fallbackDisclosure", value: false, provenanceCode: "local_reviewer_declared" }],
  };
  receipt = await adapter.createPortablePrivateBlueprintGuardCompletion(fixture.draftReview.serialized, input);
  const again = await adapter.createPortablePrivateBlueprintGuardCompletion(fixture.draftReview.serialized, input);
  const packet = receipt.packet;
  const proposal = packet.payload.completionProposal;
  const completion = proposal.guardCompletions[0];
  const sourceCandidate = fixture.draftReview.packet.payload.review.localCommitCandidate;

  check(packet.schemaVersion === adapter.PRIVATE_BLUEPRINT_GUARD_COMPLETION_SCHEMA && packet.proposalVersion === 1, "guard completion is exactly versioned");
  check(Object.keys(packet).sort().join(",") === "boundary,integrity,payload,proposalVersion,schemaVersion", "guard-completion outer fields are exact");
  check(Object.keys(packet.payload).sort().join(",") === "acceptedDraftReviewReceipt,completionProposal", "guard-completion payload fields are exact");
  check(Object.keys(packet.integrity).sort().join(",") === "acceptedReviewDigest,acceptedReviewPacketDigest,algorithm,commitCandidateDigest,completionDigest,draftDigest,draftPacketDigest,draftReviewDigest,draftReviewPacketDigest,guardProposalPacketDigest,parentProposalPayloadDigest,payloadDigest,selectedReviewDigest", "guard-completion integrity fields are exact");
  check(Object.keys(proposal).sort().join(",") === "authority,blockers,boundary,completedBlueprint,completionDigest,completionReviewStatus,guardCompletionStatus,guardCompletions,parentBinding,proposalKey,proposalStatus,reasonCode,remainingUnknownGuardKeys,reviewer,sourceBlueprint,state", "guard-completion proposal fields are exact");
  check(Object.keys(proposal.reviewer).sort().join(",") === "identityAttested,label,localOnly", "guard-completion reviewer fields are exact");
  check(Object.keys(proposal.parentBinding).sort().join(",") === "acceptedReviewDigest,acceptedReviewPacketDigest,appliedGuardId,commitCandidateDigest,commitCandidateKey,draftDigest,draftPacketDigest,draftReviewDigest,draftReviewPacketDigest,guardProposalPacketDigest,parentProposalPayloadDigest,selectedReviewDigest", "guard-completion parent binding fields are exact");
  check(Object.keys(completion).sort().join(",") === "guardKey,label,provenance,value", "guard-completion entry fields are exact");
  check(Object.keys(completion.provenance).sort().join(",") === "code,identityAttested,localOnly,reviewerLabel", "guard-completion provenance fields are exact");
  check(Object.keys(proposal.state).sort().join(",") === "adopted,commitReadinessStatus,commitReady,committed,executionStatus,localOnly,played,publicationStatus,qualificationStatus,registryStatus", "guard-completion state fields are exact");
  check(Object.keys(proposal.authority).sort().join(",") === "approval,blueprintAdoption,consensus,correctness,execution,identity,merge,progress,provider,publication,qualification,ranking,registry,resolution,rules,spending", "guard-completion authority fields are exact");
  check(Object.values(proposal.authority).every((value) => value === false), "guard completion grants no authority");
  check(proposal.proposalStatus === "proposed_uncommitted_local_blueprint_guard_completion", "guard completion remains a proposed local object");
  check(proposal.reasonCode === input.reasonCode, "completion reason stays exact");
  check(proposal.reviewer.label === input.reviewerLabel && proposal.reviewer.identityAttested === false && proposal.reviewer.localOnly === true, "completion reviewer stays local and unattested");
  check(proposal.guardCompletions.length === 1 && completion.guardKey === "fallbackDisclosure", "completion carries exact unknown guard set");
  check(completion.value === false && completion.label === "Require fallback disclosure", "completion carries exact boolean and label");
  check(completion.provenance.code === "local_reviewer_declared", "completion carries bounded provenance code");
  check(completion.provenance.reviewerLabel === input.reviewerLabel && completion.provenance.identityAttested === false && completion.provenance.localOnly === true, "per-key provenance stays local and unattested");
  check(canonical(proposal.sourceBlueprint) === canonical(sourceCandidate.blueprint), "completion copies exact source blueprint");
  check(proposal.sourceBlueprint.guardValues.fallbackDisclosure === null, "source unknown guard remains visibly unknown");
  check(proposal.completedBlueprint.guardValues.fallbackDisclosure === false, "completion applies exact declared boolean");
  check(proposal.completedBlueprint.guardValues.strictValidation === true, "completion preserves reviewed applied guard");
  check(proposal.completedBlueprint.guardValues.humanCheckpoints === false, "completion preserves known non-applied guard");
  check(proposal.remainingUnknownGuardKeys.length === 0 && proposal.guardCompletionStatus === "proposed_complete_guard_values", "proposal reports complete guard values without adoption");
  check(proposal.completionReviewStatus === "not_run", "completion review remains not run");
  check(proposal.state.localOnly === true && proposal.state.committed === false && proposal.state.adopted === false && proposal.state.commitReady === false, "proposal stays local, uncommitted, unadopted, and not ready");
  check(proposal.state.commitReadinessStatus === "requires_guard_completion_review", "proposal requires a later immutable completion review");
  check(proposal.state.qualificationStatus === "not_run" && proposal.state.played === false && proposal.state.executionStatus === "disabled", "proposal stays unqualified, unplayed, and unexecuted");
  check(proposal.state.registryStatus === "not_requested" && proposal.state.publicationStatus === "not_requested", "proposal stays unregistered and unpublished");
  check(proposal.blockers.length === 12 && proposal.blockers[0] === "reviewer_identity_unattested", "proposal carries exact blocker chain");
  check(proposal.blockers.includes("guard_value_provenance_unattested") && proposal.blockers.includes("guard_completion_not_reviewed_for_commit"), "proposal preserves provenance and review blockers");
  check(proposal.parentBinding.draftReviewPacketDigest === fixture.draftReview.packet.integrity.payloadDigest, "completion binds accepted draft-review packet");
  check(proposal.parentBinding.draftReviewDigest === fixture.draftReview.packet.payload.review.reviewDigest, "completion binds accepted draft review");
  check(proposal.parentBinding.commitCandidateDigest === sourceCandidate.candidateDigest && proposal.parentBinding.commitCandidateKey === sourceCandidate.candidateKey, "completion binds exact source candidate");
  check(proposal.parentBinding.draftPacketDigest === fixture.draft.packet.integrity.payloadDigest, "completion binds blueprint draft packet");
  check(proposal.parentBinding.draftDigest === fixture.draft.packet.payload.draft.draftDigest, "completion binds blueprint draft record");
  check(proposal.parentBinding.acceptedReviewPacketDigest === fixture.guardReview.packet.integrity.payloadDigest, "completion binds accepted guard review packet");
  check(proposal.parentBinding.acceptedReviewDigest === fixture.guardReview.packet.payload.review.reviewDigest, "completion binds accepted guard review");
  check(proposal.parentBinding.guardProposalPacketDigest === fixture.delta.packet.integrity.payloadDigest, "completion binds guard proposal");
  check(proposal.parentBinding.parentProposalPayloadDigest === fixture.verified.payloadDigest, "completion binds parent proposal");
  check(proposal.parentBinding.selectedReviewDigest === fixture.changed.reviewDigest, "completion binds selected private review");
  check(proposal.parentBinding.appliedGuardId === "require_strict_validation", "completion binds applied guard id");
  check(packet.integrity.algorithm === "sha256", "guard-completion integrity algorithm is exact");
  for (const key of ["draftReviewPacketDigest", "draftReviewDigest", "commitCandidateDigest", "draftPacketDigest", "draftDigest", "acceptedReviewPacketDigest", "acceptedReviewDigest", "guardProposalPacketDigest", "parentProposalPayloadDigest", "selectedReviewDigest"]) {
    check(packet.integrity[key] === proposal.parentBinding[key], `outer integrity binds ${key}`);
  }
  check(packet.integrity.completionDigest === proposal.completionDigest, "outer integrity binds completion digest");
  const completionPayload = copy(proposal); delete completionPayload.completionDigest;
  check(proposal.completionDigest === await digest(canonical(completionPayload)), "independent completion digest agrees");
  check(packet.integrity.payloadDigest === await digest(canonical(packet.payload)), "independent packet digest agrees");
  check(receipt.serialized === canonical(packet), "guard-completion export is canonical JSON");
  check(receipt.serialized === again.serialized, "same completion input creates same receipt");
  check(receipt.serialized.length <= adapter.PRIVATE_BLUEPRINT_GUARD_COMPLETION_MAX_LENGTH, "guard completion stays inside size cap");
  check(packet.boundary.includes("exact explicitly unknown guard keys"), "boundary limits exact unknown guards");
  check(packet.boundary.includes("not commit-ready"), "boundary preserves commit-readiness hold");
  check(packet.boundary.includes("call a provider"), "boundary refuses provider calls");

  const imported = await adapter.verifyPortablePrivateBlueprintGuardCompletion(receipt.serialized);
  check(imported.verificationStatus === "verified_private_local_blueprint_guard_completion_proposal", "fresh import remains a private local completion proposal");
  check(imported.packetDigest === packet.integrity.payloadDigest, "fresh import recomputes packet digest");
  check(imported.draftReviewSerialized === fixture.draftReview.serialized, "fresh import reconstructs exact draft review");
  check(imported.draftReviewVerification.draftSerialized === fixture.draft.serialized, "fresh import reconstructs exact blueprint draft");
  check(imported.draftReviewVerification.draftVerification.acceptedReviewSerialized === fixture.guardReview.serialized, "fresh import reconstructs accepted guard review");
  check(imported.draftReviewVerification.draftVerification.acceptedReviewVerification.blueprintDeltaSerialized === fixture.delta.serialized, "fresh import reconstructs guard proposal");
  check(imported.draftReviewVerification.draftVerification.acceptedReviewVerification.blueprintDeltaVerification.learningSerialized === fixture.learning.serialized, "fresh import reconstructs learning receipt");
  check(imported.draftReviewVerification.draftVerification.acceptedReviewVerification.blueprintDeltaVerification.learningVerification.comparisonSerialized === fixture.comparison.serialized, "fresh import reconstructs comparison receipt");
  check(imported.draftReviewVerification.draftVerification.acceptedReviewVerification.blueprintDeltaVerification.learningVerification.comparisonVerification.leftSerialized === fixture.left.serialized, "fresh import reconstructs Packet A");
  check(imported.draftReviewVerification.draftVerification.acceptedReviewVerification.blueprintDeltaVerification.learningVerification.comparisonVerification.rightSerialized === fixture.right.serialized, "fresh import reconstructs Packet B");
  check(canonical(imported.completionProposal) === canonical(proposal), "fresh import reconstructs exact completion proposal");
  check(imported.boundary === packet.boundary, "fresh import preserves completion boundary");

  for (const reasonCode of adapter.PRIVATE_BLUEPRINT_GUARD_COMPLETION_REASONS) {
    for (const provenanceCode of adapter.PRIVATE_BLUEPRINT_GUARD_COMPLETION_PROVENANCE_CODES) {
      for (const value of [false, true]) {
        const variant = await adapter.createPortablePrivateBlueprintGuardCompletion(fixture.draftReview.serialized, {
          reviewerLabel: "Variant Reviewer",
          reasonCode,
          guardCompletions: [{ guardKey: "fallbackDisclosure", value, provenanceCode }],
        });
        const record = variant.packet.payload.completionProposal;
        check(record.reasonCode === reasonCode && record.guardCompletions[0].provenance.code === provenanceCode, `${reasonCode}/${provenanceCode}/${value} remains allowlisted`);
        check(record.guardCompletions[0].value === value && record.completedBlueprint.guardValues.fallbackDisclosure === value, `${reasonCode}/${provenanceCode}/${value} applies exact boolean only`);
        check(record.state.commitReady === false && record.state.adopted === false, `${reasonCode}/${provenanceCode}/${value} remains not ready and unadopted`);
      }
    }
  }

  for (const decision of ["defer", "reject"]) {
    const refused = await makeAcceptedDraftReview(decision);
    await rejectsCreate(refused.draftReview.serialized, input, "accepted draft review required");
  }
  await rejectsCreate(fixture.draftReview.serialized, { reviewerLabel: "x", reasonCode: "unknown", guardCompletions: input.guardCompletions }, "reason drift");
  await rejectsCreate(fixture.draftReview.serialized, { reviewerLabel: "", reasonCode: input.reasonCode, guardCompletions: input.guardCompletions }, "reviewer label drift");
  await rejectsCreate(fixture.draftReview.serialized, { reviewerLabel: " padded ", reasonCode: input.reasonCode, guardCompletions: input.guardCompletions }, "reviewer label drift");
  await rejectsCreate(fixture.draftReview.serialized, { reviewerLabel: "x", reasonCode: input.reasonCode, guardCompletions: [] }, "exact unknown guard set required");
  await rejectsCreate(fixture.draftReview.serialized, { reviewerLabel: "x", reasonCode: input.reasonCode, guardCompletions: [...input.guardCompletions, ...input.guardCompletions] }, "exact unknown guard set required");
  await rejectsCreate(fixture.draftReview.serialized, { reviewerLabel: "x", reasonCode: input.reasonCode, guardCompletions: [{ guardKey: "humanCheckpoints", value: false, provenanceCode: "local_reviewer_declared" }] }, "exact unknown guard order required");
  await rejectsCreate(fixture.draftReview.serialized, { reviewerLabel: "x", reasonCode: input.reasonCode, guardCompletions: [{ guardKey: "fallbackDisclosure", value: "false", provenanceCode: "local_reviewer_declared" }] }, "boolean guard value required");
  await rejectsCreate(fixture.draftReview.serialized, { reviewerLabel: "x", reasonCode: input.reasonCode, guardCompletions: [{ guardKey: "fallbackDisclosure", value: false, provenanceCode: "untrusted" }] }, "provenance code drift");
  await rejectsCreate("{}", input, "private blueprint draft review fields drift");
  await rejectsSerialized("", "input length rejected");
  await rejectsSerialized(" ".repeat(adapter.PRIVATE_BLUEPRINT_GUARD_COMPLETION_MAX_LENGTH + 1), "input length rejected");
  await rejectsSerialized("{", "invalid JSON");
  await rejectsSerialized(JSON.stringify(packet, null, 2), "must use canonical JSON");
  await rejectsSerialized(`${receipt.serialized}\n`, "must use canonical JSON");
  await rejectsSerialized(receipt.serialized.replace('"proposalVersion":1', '"proposalVersion":1,"proposalVersion":1'), "must use canonical JSON");

  await rejectsPacket(async (value) => { value.extra = true; }, "private blueprint guard completion fields drift");
  await rejectsPacket(async (value) => { delete value.boundary; }, "private blueprint guard completion fields drift");
  await rejectsPacket(async (value) => { value.schemaVersion = "v2"; }, "schema drift");
  await rejectsPacket(async (value) => { value.proposalVersion = 2; }, "schema drift");
  await rejectsPacket(async (value) => { value.boundary = "trusted"; }, "boundary drift");
  await rejectsPacket(async (value) => { value.payload.extra = true; }, "private blueprint guard completion payload fields drift");
  await rejectsPacket(async (value) => { delete value.payload.completionProposal; }, "private blueprint guard completion payload fields drift");
  await rejectsPacket(async (value) => { value.integrity.extra = true; }, "private blueprint guard completion integrity fields drift");
  await rejectsPacket(async (value) => { delete value.integrity.completionDigest; }, "private blueprint guard completion integrity fields drift");
  await rejectsPacket(async (value) => { value.integrity.algorithm = "sha512"; }, "integrity algorithm drift");
  for (const key of ["payloadDigest", "draftReviewPacketDigest", "draftReviewDigest", "commitCandidateDigest", "draftPacketDigest", "draftDigest", "acceptedReviewPacketDigest", "acceptedReviewDigest", "guardProposalPacketDigest", "parentProposalPayloadDigest", "selectedReviewDigest", "completionDigest"]) {
    await rejectsPacket(async (value) => { value.integrity[key] = "bad"; }, `${key} drift`);
  }
  for (const [key, expected] of [
    ["draftReviewPacketDigest", "draft review packet digest binding mismatch"],
    ["draftReviewDigest", "draft review digest binding mismatch"],
    ["commitCandidateDigest", "commit candidate digest binding mismatch"],
    ["draftPacketDigest", "draft packet digest binding mismatch"],
    ["draftDigest", "draft digest binding mismatch"],
    ["acceptedReviewPacketDigest", "accepted review packet digest binding mismatch"],
    ["acceptedReviewDigest", "accepted review digest binding mismatch"],
    ["guardProposalPacketDigest", "guard proposal packet digest binding mismatch"],
    ["parentProposalPayloadDigest", "parent proposal digest binding mismatch"],
    ["selectedReviewDigest", "selected review digest binding mismatch"],
    ["completionDigest", "completion digest binding mismatch"],
  ]) await rejectsPacket(async (value) => { value.integrity[key] = "0".repeat(64); }, expected);
  await rejectsPacket(async (value) => { value.integrity.payloadDigest = "0".repeat(64); }, "payload digest mismatch");

  await rejectsPacket(async (value) => { value.payload.completionProposal.state.committed = true; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.completionProposal.state.adopted = true; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.completionProposal.state.commitReady = true; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.completionProposal.state.commitReadinessStatus = "ready"; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.completionProposal.state.qualificationStatus = "passed"; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.completionProposal.state.played = true; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.completionProposal.state.executionStatus = "enabled"; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.completionProposal.state.registryStatus = "registered"; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.completionProposal.state.publicationStatus = "published"; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.completionProposal.completedBlueprint.guardValues.strictValidation = false; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.completionProposal.completedBlueprint.guardValues.humanCheckpoints = true; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.completionProposal.completedBlueprint.guardValues.fallbackDisclosure = true; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.completionProposal.sourceBlueprint.guardValues.fallbackDisclosure = false; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.completionProposal.remainingUnknownGuardKeys = ["fallbackDisclosure"]; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.completionProposal.guardCompletions[0].provenance.identityAttested = true; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.completionProposal.guardCompletions[0].provenance.reviewerLabel = "forged"; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.completionProposal.blockers.pop(); }, "proposal projection mismatch", { reseal: true });
  for (const key of Object.keys(proposal.authority)) {
    await rejectsPacket(async (value) => { value.payload.completionProposal.authority[key] = true; }, "proposal projection mismatch", { reseal: true });
  }
  await rejectsPacket(async (value) => { value.payload.acceptedDraftReviewReceipt.payload.review.localCommitCandidate.commitReady = true; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.acceptedDraftReviewReceipt.payload.blueprintRevisionDraft.payload.draft.state.committed = true; }, "draft projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.acceptedDraftReviewReceipt.payload.blueprintRevisionDraft.payload.acceptedReviewReceipt.payload.review.localRevisionCandidate.adopted = true; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.acceptedDraftReviewReceipt.payload.blueprintRevisionDraft.payload.acceptedReviewReceipt.payload.blueprintDeltaProposal.payload.proposal.state.played = true; }, "proposal projection mismatch", { reseal: true });

  const dangerous = copy(packet);
  const dangerousSerialized = canonical(dangerous).replace('"acceptedDraftReviewReceipt"', '"__proto__":{"polluted":true},"acceptedDraftReviewReceipt"');
  await rejectsSerialized(dangerousSerialized, "prohibited key");
  const deep = copy(packet);
  let cursor = deep.payload.completionProposal;
  for (let index = 0; index < 40; index += 1) { cursor.deep = {}; cursor = cursor.deep; }
  await rejectsSerialized(canonical(deep), "nesting limit exceeded");
  const nodeBomb = copy(packet);
  nodeBomb.payload.completionProposal.blockers = Array.from({ length: 165000 }, () => null);
  const nodeBombSerialized = canonical(nodeBomb);
  check(nodeBombSerialized.length < adapter.PRIVATE_BLUEPRINT_GUARD_COMPLETION_MAX_LENGTH, "guard-completion node bomb stays below byte cap");
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
    require(result.returncode == 0, f"private blueprint guard-completion check failed: {result.stderr.strip()}")
    payload = json.loads(result.stdout.strip())
    require(payload["checks"] >= 185, "private blueprint guard-completion coverage unexpectedly small")
    require(payload["receiptBytes"] > 0, "private blueprint guard-completion receipt was empty")
    require(len(payload["digest"]) == 64, "private blueprint guard-completion digest drift")
    print(
        "BuilderWars private blueprint guard completion: PASS "
        f"({payload['checks']} checks; receipt {payload['receiptBytes']} bytes; digest {payload['digest'][:12]}...)"
    )
    print("exact unknown keys / boolean-only / per-key provenance / known guards preserved / not commit-ready / zero authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
