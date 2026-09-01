#!/usr/bin/env python3
"""Adversarial checks for deterministic local operator-review packets."""

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
    require(node is not None, "Node.js is required to exercise operator-review packets")

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
async function resealOperatorRecord(packet) {
  const record = packet.payload.operatorReviewPacket;
  record.verifierEvidence.exactDiffDigest = await digest(canonical(record.exactDiff));
  const recordPayload = copy(record);
  delete recordPayload.operatorPacketDigest;
  record.operatorPacketDigest = await digest(canonical(recordPayload));
  packet.integrity.exactDiffDigest = record.verifierEvidence.exactDiffDigest;
  packet.integrity.operatorPacketDigest = record.operatorPacketDigest;
  return resealOuter(packet);
}
async function rejectsSerialized(serialized, expected) {
  let message = "";
  try { await adapter.verifyPortablePrivateBlueprintOperatorReviewPacket(serialized); } catch (error) { message = error.message; }
  check(message.includes(expected), `operator packet rejects ${expected}; got ${message}`);
}
async function rejectsPacket(mutator, expected, { reseal = false, resealRecord = false } = {}) {
  const value = copy(receipt.packet);
  await mutator(value);
  if (resealRecord) await resealOperatorRecord(value);
  else if (reseal) await resealOuter(value);
  await rejectsSerialized(canonical(value), expected);
}
async function rejectsCreate(reviewSerialized, expected) {
  let message = "";
  try { await adapter.createPortablePrivateBlueprintOperatorReviewPacket(reviewSerialized); } catch (error) { message = error.message; }
  check(message.includes(expected), `operator packet creation rejects ${expected}; got ${message}`);
}

async function makeGuardCompletion() {
  const view = adapter.adaptArenaReadModel(model, demo);
  const proof = view.proofReceipts.find((candidate) => candidate.moveSourceCounts.model > 0);
  const learningAction = adapter.buildReceiptLearningAction(proof, "verified_corpus");
  const proposal = adapter.buildRunbackProposal(learningAction, {
    agentName: "Operator Packet Student",
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
  check(adapter.PRIVATE_BLUEPRINT_OPERATOR_REVIEW_PACKET_SCHEMA === "builderwars.mobile-private-blueprint-operator-review-packet.v1", "exports operator-review packet schema");
  check(adapter.PRIVATE_BLUEPRINT_OPERATOR_REVIEW_PACKET_MAX_LENGTH === 8388608, "exports operator-review packet size cap");
  check(typeof adapter.createPortablePrivateBlueprintOperatorReviewPacket === "function", "exports operator-review packet creator");
  check(typeof adapter.verifyPortablePrivateBlueprintOperatorReviewPacket === "function", "exports operator-review packet verifier");

  const fixture = await makeGuardCompletion();
  const accepted = await adapter.createPortablePrivateBlueprintGuardCompletionReview(fixture.completion.serialized, {
    reviewerLabel: "Completion Review Referee",
    decision: "accept_for_commit_review",
    reasonCode: "completion_lineage_verified",
  });
  receipt = await adapter.createPortablePrivateBlueprintOperatorReviewPacket(accepted.serialized);
  const again = await adapter.createPortablePrivateBlueprintOperatorReviewPacket(accepted.serialized);
  const packet = receipt.packet;
  const record = packet.payload.operatorReviewPacket;
  const binding = record.candidateBinding;
  const evidence = record.verifierEvidence;
  const candidate = accepted.packet.payload.review.localCommitReviewCandidate;

  check(packet.schemaVersion === adapter.PRIVATE_BLUEPRINT_OPERATOR_REVIEW_PACKET_SCHEMA && packet.packetVersion === 1, "operator packet is exactly versioned");
  check(Object.keys(packet).sort().join(",") === "boundary,integrity,packetVersion,payload,schemaVersion", "operator packet outer fields are exact");
  check(Object.keys(packet.payload).sort().join(",") === "acceptedGuardCompletionReviewReceipt,operatorReviewPacket", "operator packet payload fields are exact");
  check(Object.keys(packet.integrity).sort().join(",") === "algorithm,candidateBlueprintDigest,candidateDigest,completionReviewDigest,completionReviewPacketDigest,exactDiffDigest,operatorPacketDigest,payloadDigest,sourceBlueprintDigest", "operator packet integrity fields are exact");
  check(Object.keys(record).sort().join(",") === "authority,blockers,boundary,candidateBinding,candidateBlueprint,exactDiff,operatorAction,operatorPacketDigest,packetKey,packetStatus,rollbackPlan,sourceBlueprint,state,validationPlan,verifierEvidence", "operator packet record fields are exact");
  check(Object.keys(binding).sort().join(",") === "acceptedReviewPacketDigest,candidateDigest,candidateKey,commitCandidateDigest,completionDigest,completionPacketDigest,completionReviewDigest,completionReviewPacketDigest,draftPacketDigest,draftReviewPacketDigest,guardProposalPacketDigest,parentProposalPayloadDigest,selectedReviewDigest", "candidate binding fields are exact");
  check(Object.keys(record.state).sort().join(",") === "adopted,candidateValidationStatus,commitReady,committed,executionStatus,localOnly,operatorPacketPrepared,operatorReviewStatus,played,publicationStatus,qualificationStatus,registryStatus", "operator packet state fields are exact");
  check(Object.keys(record.operatorAction).sort().join(",") === "allowedOutcomes,approvalAttested,identityAttested,requestedDecision,status", "operator action fields are exact");
  check(Object.keys(record.rollbackPlan).sort().join(",") === "action,repositoryMutationStatus,runtimeMutationStatus,status", "rollback fields are exact");
  check(Object.keys(record.validationPlan).sort().join(",") === "status,steps", "validation plan fields are exact");
  check(Object.keys(record.exactDiff).sort().join(",") === "candidateBlueprintDigest,changeCount,changedFieldPaths,fields,sourceBlueprintDigest,unchangedFieldPaths", "exact diff fields are exact");
  check(record.exactDiff.fields.length === 3, "exact diff covers every allowlisted guard");
  for (const field of record.exactDiff.fields) {
    check(Object.keys(field).sort().join(",") === "afterValue,beforeValue,changeStatus,fieldPath,guardKey,label,sourceStage", `diff field ${field.guardKey} has exact shape`);
  }

  check(record.packetStatus === "prepared_local_operator_review_packet", "packet status is preparation only");
  check(record.sourceBlueprint.agentName === candidate.blueprint.agentName, "source identity matches candidate identity");
  check(record.sourceBlueprint.declaredBase === candidate.blueprint.declaredBase, "source declared base stays exact");
  check(record.sourceBlueprint.harnessStyle === candidate.blueprint.harnessStyle, "source harness stays exact");
  check(record.sourceBlueprint.localOnly === true && record.candidateBlueprint.localOnly === true, "both blueprints remain local");
  check(canonical(record.candidateBlueprint) === canonical(candidate.blueprint), "candidate blueprint projection is exact");
  check(record.sourceBlueprint.guardValues.strictValidation === null, "source strict guard remains explicitly unknown");
  check(record.sourceBlueprint.guardValues.fallbackDisclosure === null, "source fallback guard remains explicitly unknown");
  check(record.sourceBlueprint.guardValues.humanCheckpoints === false, "source human checkpoint guard is preserved");
  check(record.candidateBlueprint.guardValues.strictValidation === true, "candidate includes reviewed strict guard");
  check(record.candidateBlueprint.guardValues.fallbackDisclosure === false, "candidate includes reviewed fallback completion");
  check(record.candidateBlueprint.guardValues.humanCheckpoints === false, "candidate preserves human checkpoint value");
  check(record.exactDiff.changeCount === 2, "exact diff reports two real changes");
  check(record.exactDiff.changedFieldPaths.join(",") === "guardValues.strictValidation,guardValues.fallbackDisclosure", "changed field paths are deterministic");
  check(record.exactDiff.unchangedFieldPaths.join(",") === "agentName,declaredBase,harnessStyle,localOnly,guardValues.humanCheckpoints", "unchanged field paths are deterministic");
  check(record.exactDiff.fields[0].sourceStage === "accepted_guard_revision", "strict guard binds accepted revision stage");
  check(record.exactDiff.fields[1].sourceStage === "reviewed_guard_completion", "fallback guard binds completion stage");
  check(record.exactDiff.fields[2].sourceStage === "preserved_source_value", "human checkpoint guard binds preservation stage");

  check(evidence.verificationStatus === "verified_local_portable_lineage", "verifier evidence stays local");
  for (const key of ["nestedLineageReverified", "acceptedDecisionVerified", "candidateProjectionRecomputed", "exactDiffRecomputed", "canonicalPacketRequired"]) {
    check(evidence[key] === true, `${key} is explicit verifier evidence`);
  }
  check(evidence.sourceBlueprintDigest === await digest(canonical(record.sourceBlueprint)), "source blueprint digest independently agrees");
  check(evidence.candidateBlueprintDigest === await digest(canonical(record.candidateBlueprint)), "candidate blueprint digest independently agrees");
  check(evidence.exactDiffDigest === await digest(canonical(record.exactDiff)), "exact diff digest independently agrees");
  const recordPayload = copy(record); delete recordPayload.operatorPacketDigest;
  check(record.operatorPacketDigest === await digest(canonical(recordPayload)), "operator record digest independently agrees");
  check(packet.integrity.payloadDigest === await digest(canonical(packet.payload)), "outer payload digest independently agrees");
  check(receipt.serialized === canonical(packet), "operator packet export is canonical JSON");
  check(receipt.serialized === again.serialized, "same accepted review creates same operator packet");
  check(receipt.serialized.length <= adapter.PRIVATE_BLUEPRINT_OPERATOR_REVIEW_PACKET_MAX_LENGTH, "operator packet stays inside size cap");

  check(binding.completionReviewPacketDigest === accepted.packet.integrity.payloadDigest, "packet binds accepted completion-review packet");
  check(binding.completionReviewDigest === accepted.packet.payload.review.reviewDigest, "packet binds accepted completion-review record");
  check(binding.candidateDigest === candidate.candidateDigest && binding.candidateKey === candidate.candidateKey, "packet binds exact local candidate");
  check(binding.completionPacketDigest === fixture.completion.packet.integrity.payloadDigest, "packet binds completion proposal packet");
  check(binding.completionDigest === fixture.completion.packet.payload.completionProposal.completionDigest, "packet binds completion record");
  check(binding.draftReviewPacketDigest === fixture.draftReview.packet.integrity.payloadDigest, "packet binds draft review packet");
  check(binding.commitCandidateDigest === fixture.draftReview.packet.payload.review.localCommitCandidate.candidateDigest, "packet binds prior commit candidate");
  check(binding.draftPacketDigest === fixture.draft.packet.integrity.payloadDigest, "packet binds draft packet");
  check(binding.acceptedReviewPacketDigest === fixture.guardReview.packet.integrity.payloadDigest, "packet binds accepted guard review");
  check(binding.guardProposalPacketDigest === fixture.delta.packet.integrity.payloadDigest, "packet binds guard proposal");
  check(binding.parentProposalPayloadDigest === fixture.verified.payloadDigest, "packet binds parent proposal");
  check(binding.selectedReviewDigest === fixture.changed.reviewDigest, "packet binds selected private review");
  for (const key of ["completionReviewPacketDigest", "completionReviewDigest", "candidateDigest"]) {
    check(packet.integrity[key] === binding[key], `outer integrity binds ${key}`);
  }
  for (const key of ["sourceBlueprintDigest", "candidateBlueprintDigest", "exactDiffDigest"]) {
    check(packet.integrity[key] === evidence[key], `outer integrity binds ${key}`);
  }
  check(packet.integrity.operatorPacketDigest === record.operatorPacketDigest, "outer integrity binds operator record digest");

  check(record.validationPlan.status === "not_run" && record.validationPlan.steps.length === 4, "validation plan remains not run");
  check(record.validationPlan.steps.map((step) => `${step.id}:${step.command}`).join("|") === [
    "focused_operator_packet:python bin/check_mobile_arena_private_blueprint_operator_review_packet.py",
    "integrated_mobile_exchange:python bin/check_mobile_arena_exchange.py",
    "replay_verifier_parity:python bin/build_verifier.py --check",
    "provider_boundary:python bin/check_provider_hub.py",
  ].join("|"), "validation plan names the exact shipped local commands");
  for (const step of record.validationPlan.steps) {
    check(Object.keys(step).sort().join(",") === "command,evidenceStatus,id", `${step.id} validation step fields are exact`);
    check(step.evidenceStatus === "not_run", `${step.id} carries no fabricated evidence`);
    check(step.command.startsWith("python bin/"), `${step.id} carries a bounded local command`);
  }
  check(record.rollbackPlan.status === "discard_only_uncommitted_state", "rollback is discard-only");
  check(record.rollbackPlan.repositoryMutationStatus === "none" && record.rollbackPlan.runtimeMutationStatus === "none", "rollback reports no prior mutation");
  check(record.operatorAction.status === "not_run", "operator decision is not run");
  check(record.operatorAction.allowedOutcomes.join(",") === "approve_for_separate_commit_preparation,defer,reject", "operator outcomes are bounded");
  check(record.operatorAction.identityAttested === false && record.operatorAction.approvalAttested === false, "operator identity and approval remain unattested");
  check(record.state.localOnly === true && record.state.operatorPacketPrepared === true, "packet state remains prepared and local");
  check(record.state.candidateValidationStatus === "not_run" && record.state.operatorReviewStatus === "not_run", "validation and operator review remain not run");
  check(record.state.committed === false && record.state.adopted === false && record.state.commitReady === false, "packet never commits, adopts, or marks ready");
  check(record.state.qualificationStatus === "not_run" && record.state.played === false && record.state.executionStatus === "disabled", "packet stays unqualified, unplayed, and unexecuted");
  check(record.state.registryStatus === "not_requested" && record.state.publicationStatus === "not_requested", "packet stays unregistered and unpublished");
  check(record.blockers.length === 13 && record.blockers[0] === "operator_identity_unattested", "packet carries the exact blocker chain");
  check(record.blockers.includes("candidate_validation_not_run") && record.blockers.includes("operator_decision_not_recorded"), "packet preserves validation and decision blockers");
  check(Object.keys(record.authority).length === 16 && Object.values(record.authority).every((value) => value === false), "packet grants zero authority");
  check(packet.boundary.includes("Preparation is not an operator review"), "boundary refuses implied operator review");
  check(packet.boundary.includes("provider call"), "boundary refuses provider calls");

  const imported = await adapter.verifyPortablePrivateBlueprintOperatorReviewPacket(receipt.serialized);
  check(imported.verificationStatus === "verified_private_local_blueprint_operator_review_packet", "fresh import stays a private local operator packet");
  check(imported.packetDigest === packet.integrity.payloadDigest, "fresh import recomputes payload digest");
  check(imported.acceptedReviewSerialized === accepted.serialized, "fresh import reconstructs exact accepted completion review");
  check(imported.acceptedReviewVerification.guardCompletionSerialized === fixture.completion.serialized, "fresh import reconstructs exact completion proposal");
  check(imported.acceptedReviewVerification.guardCompletionVerification.draftReviewSerialized === fixture.draftReview.serialized, "fresh import reconstructs exact draft review");
  check(imported.acceptedReviewVerification.guardCompletionVerification.draftReviewVerification.draftSerialized === fixture.draft.serialized, "fresh import reconstructs exact revision draft");
  check(canonical(imported.operatorReviewPacket) === canonical(record), "fresh import reconstructs exact operator packet record");

  const deferred = await adapter.createPortablePrivateBlueprintGuardCompletionReview(fixture.completion.serialized, {
    reviewerLabel: "Deferred Referee", decision: "defer", reasonCode: "needs_operator_commit_review",
  });
  const rejected = await adapter.createPortablePrivateBlueprintGuardCompletionReview(fixture.completion.serialized, {
    reviewerLabel: "Rejected Referee", decision: "reject", reasonCode: "guard_completion_not_approved",
  });
  await rejectsCreate(deferred.serialized, "accepted completion review required");
  await rejectsCreate(rejected.serialized, "accepted completion review required");
  await rejectsCreate("{}", "private blueprint guard completion review fields drift");
  await rejectsSerialized("", "input length rejected");
  await rejectsSerialized(" ".repeat(adapter.PRIVATE_BLUEPRINT_OPERATOR_REVIEW_PACKET_MAX_LENGTH + 1), "input length rejected");
  await rejectsSerialized("{", "invalid JSON");
  await rejectsSerialized(JSON.stringify(packet, null, 2), "must use canonical JSON");
  await rejectsSerialized(`${receipt.serialized}\n`, "must use canonical JSON");

  await rejectsPacket(async (value) => { value.extra = true; }, "private blueprint operator review packet fields drift");
  await rejectsPacket(async (value) => { delete value.boundary; }, "private blueprint operator review packet fields drift");
  await rejectsPacket(async (value) => { value.schemaVersion = "v2"; }, "schema drift");
  await rejectsPacket(async (value) => { value.packetVersion = 2; }, "schema drift");
  await rejectsPacket(async (value) => { value.boundary = "trusted"; }, "boundary drift");
  await rejectsPacket(async (value) => { value.payload.extra = true; }, "private blueprint operator review packet payload fields drift");
  await rejectsPacket(async (value) => { delete value.payload.operatorReviewPacket; }, "private blueprint operator review packet payload fields drift");
  await rejectsPacket(async (value) => { value.integrity.extra = true; }, "private blueprint operator review packet integrity fields drift");
  await rejectsPacket(async (value) => { delete value.integrity.operatorPacketDigest; }, "private blueprint operator review packet integrity fields drift");
  await rejectsPacket(async (value) => { value.integrity.algorithm = "sha512"; }, "integrity algorithm drift");
  for (const key of ["payloadDigest", "completionReviewPacketDigest", "completionReviewDigest", "candidateDigest", "sourceBlueprintDigest", "candidateBlueprintDigest", "exactDiffDigest", "operatorPacketDigest"]) {
    await rejectsPacket(async (value) => { value.integrity[key] = "bad"; }, `${key} drift`);
  }
  for (const [key, expected] of [
    ["completionReviewPacketDigest", "completion review packet digest binding mismatch"],
    ["completionReviewDigest", "completion review digest binding mismatch"],
    ["candidateDigest", "candidate digest binding mismatch"],
    ["sourceBlueprintDigest", "source blueprint digest binding mismatch"],
    ["candidateBlueprintDigest", "candidate blueprint digest binding mismatch"],
    ["exactDiffDigest", "exact diff digest binding mismatch"],
    ["operatorPacketDigest", "operator packet digest binding mismatch"],
  ]) await rejectsPacket(async (value) => { value.integrity[key] = "0".repeat(64); }, expected);
  await rejectsPacket(async (value) => { value.integrity.payloadDigest = "0".repeat(64); }, "payload digest mismatch");

  await rejectsPacket(async (value) => { value.payload.operatorReviewPacket.operatorAction.status = "approved"; }, "packet projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.operatorReviewPacket.operatorAction.identityAttested = true; }, "packet projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.operatorReviewPacket.operatorAction.approvalAttested = true; }, "packet projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.operatorReviewPacket.state.committed = true; }, "packet projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.operatorReviewPacket.state.adopted = true; }, "packet projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.operatorReviewPacket.state.commitReady = true; }, "packet projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.operatorReviewPacket.state.candidateValidationStatus = "passed"; }, "packet projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.operatorReviewPacket.validationPlan.status = "passed"; }, "packet projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.operatorReviewPacket.validationPlan.steps[0].evidenceStatus = "passed"; }, "packet projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.operatorReviewPacket.rollbackPlan.status = "applied"; }, "packet projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.operatorReviewPacket.candidateBlueprint.guardValues.fallbackDisclosure = true; }, "packet projection mismatch", { resealRecord: true });
  await rejectsPacket(async (value) => { value.payload.operatorReviewPacket.exactDiff.fields[0].afterValue = false; }, "packet projection mismatch", { resealRecord: true });
  await rejectsPacket(async (value) => { value.payload.operatorReviewPacket.blockers.pop(); }, "packet projection mismatch", { reseal: true });
  for (const key of Object.keys(record.authority)) {
    await rejectsPacket(async (value) => { value.payload.operatorReviewPacket.authority[key] = true; }, "packet projection mismatch", { reseal: true });
  }
  await rejectsPacket(async (value) => { value.payload.acceptedGuardCompletionReviewReceipt.payload.review.state.operatorReviewStatus = "approved"; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.acceptedGuardCompletionReviewReceipt.payload.review.localCommitReviewCandidate.committed = true; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.acceptedGuardCompletionReviewReceipt.payload.guardCompletionProposal.payload.completionProposal.completedBlueprint.guardValues.strictValidation = false; }, "proposal projection mismatch", { reseal: true });

  const dangerous = copy(packet);
  const dangerousSerialized = canonical(dangerous).replace('"acceptedGuardCompletionReviewReceipt"', '"__proto__":{"polluted":true},"acceptedGuardCompletionReviewReceipt"');
  await rejectsSerialized(dangerousSerialized, "prohibited key");
  const deep = copy(packet);
  let cursor = deep.payload.operatorReviewPacket;
  for (let index = 0; index < 40; index += 1) { cursor.deep = {}; cursor = cursor.deep; }
  await rejectsSerialized(canonical(deep), "nesting limit exceeded");
  const nodeBomb = copy(packet);
  nodeBomb.payload.operatorReviewPacket.blockers = Array.from({ length: 230000 }, () => null);
  const nodeBombSerialized = canonical(nodeBomb);
  check(nodeBombSerialized.length < adapter.PRIVATE_BLUEPRINT_OPERATOR_REVIEW_PACKET_MAX_LENGTH, "operator packet node bomb stays below byte cap");
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
    require(result.returncode == 0, f"private operator-review packet check failed: {result.stderr.strip()}")
    payload = json.loads(result.stdout.strip())
    require(payload["checks"] >= 145, "private operator-review packet coverage unexpectedly small")
    require(payload["receiptBytes"] > 0, "private operator-review packet was empty")
    require(len(payload["digest"]) == 64, "private operator-review packet digest drift")
    print(
        "BuilderWars private operator-review packet: PASS "
        f"({payload['checks']} checks; packet {payload['receiptBytes']} bytes; digest {payload['digest'][:12]}...)"
    )
    print("accepted-review-only / exact original-to-candidate diff / validation not run / discard rollback / operator decision not run / zero authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
