#!/usr/bin/env python3
"""Adversarial checks for deterministic local blueprint-revision draft receipts."""

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
    require(node is not None, "Node.js is required to exercise private blueprint revision drafts")

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
async function resealDraft(packet) {
  const record = copy(packet.payload.draft);
  delete record.draftDigest;
  packet.payload.draft.draftDigest = await digest(canonical(record));
  packet.integrity.draftDigest = packet.payload.draft.draftDigest;
  return resealOuter(packet);
}
async function rejectsSerialized(serialized, expected) {
  let message = "";
  try { await adapter.verifyPortablePrivateBlueprintRevisionDraft(serialized); } catch (error) { message = error.message; }
  check(message.includes(expected), `blueprint revision draft rejects ${expected}; got ${message}`);
}
async function rejectsPacket(mutator, expected, { reseal = false, resealInner = false, source = receipt.packet } = {}) {
  const value = copy(source);
  await mutator(value);
  if (resealInner) await resealDraft(value);
  else if (reseal) await resealOuter(value);
  await rejectsSerialized(canonical(value), expected);
}
async function rejectsCreate(reviewSerialized, expected) {
  let message = "";
  try { await adapter.createPortablePrivateBlueprintRevisionDraft(reviewSerialized); } catch (error) { message = error.message; }
  check(message.includes(expected), `blueprint revision draft creation rejects ${expected}; got ${message}`);
}

let receipt;

async function makeLineage() {
  const view = await adapter.adaptArenaReadModel(model, demo);
  const proof = view.proofReceipts.find((candidate) => candidate.moveSourceCounts.model > 0);
  const learningAction = adapter.buildReceiptLearningAction(proof, "verified_corpus");
  const proposal = adapter.buildRunbackProposal(learningAction, {
    agentName: "Revision Draft Student",
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
  return { portable, verified, changed, identical, leftOnly, left, right, comparison, learning };
}

async function makeAcceptedReview(fixture, reviewDigest, reasonCode = "guard_matches_verified_lesson") {
  const delta = await adapter.createPortablePrivateBlueprintDelta(fixture.learning.serialized, reviewDigest);
  const review = await adapter.createPortablePrivateBlueprintDeltaReview(delta.serialized, {
    reviewerLabel: "Local Revision Reviewer",
    decision: "accept_for_revision",
    reasonCode,
  });
  return { delta, review };
}

async function main() {
  check(adapter.PRIVATE_BLUEPRINT_REVISION_DRAFT_SCHEMA === "builderwars.mobile-private-blueprint-revision-draft.v1", "exports blueprint-revision draft schema");
  check(adapter.PRIVATE_BLUEPRINT_REVISION_DRAFT_MAX_LENGTH === 4194304, "exports blueprint-revision draft size cap");
  check(typeof adapter.createPortablePrivateBlueprintRevisionDraft === "function", "exports blueprint-revision draft creator");
  check(typeof adapter.verifyPortablePrivateBlueprintRevisionDraft === "function", "exports blueprint-revision draft verifier");

  const fixture = await makeLineage();
  const accepted = await makeAcceptedReview(fixture, fixture.changed.reviewDigest);
  receipt = await adapter.createPortablePrivateBlueprintRevisionDraft(accepted.review.serialized);
  const again = await adapter.createPortablePrivateBlueprintRevisionDraft(accepted.review.serialized);
  const packet = receipt.packet;
  const draft = packet.payload.draft;
  const lineage = draft.lineage;
  const review = accepted.review.packet.payload.review;
  const deltaProposal = accepted.delta.packet.payload.proposal;
  const parentProposal = fixture.verified.proposal;

  check(packet.schemaVersion === adapter.PRIVATE_BLUEPRINT_REVISION_DRAFT_SCHEMA && packet.draftVersion === 1, "blueprint revision draft is exactly versioned");
  check(Object.keys(packet).sort().join(",") === "boundary,draftVersion,integrity,payload,schemaVersion", "blueprint-revision outer fields are exact");
  check(Object.keys(packet.payload).sort().join(",") === "acceptedReviewReceipt,draft", "blueprint-revision payload fields are exact");
  check(Object.keys(packet.integrity).sort().join(",") === "acceptedReviewDigest,acceptedReviewPacketDigest,algorithm,draftDigest,guardProposalPacketDigest,parentProposalPayloadDigest,payloadDigest,selectedReviewDigest", "blueprint-revision integrity fields are exact");
  check(Object.keys(draft).sort().join(",") === "appliedGuard,authority,blockers,boundary,draftDigest,draftKey,draftStatus,lineage,parentBlueprint,parentGuardValues,revisedBlueprint,state,unknownGuardKeys", "blueprint-revision draft fields are exact");
  check(Object.keys(lineage).sort().join(",") === "acceptedCandidateRevisionKey,acceptedReviewDigest,acceptedReviewPacketDigest,comparisonPacketDigest,guardDeltaId,guardProposalKey,guardProposalPacketDigest,learningPacketDigest,parentProposalKey,parentProposalPayloadDigest,selectedReviewDigest", "blueprint-revision lineage fields are exact");
  check(Object.keys(draft.parentBlueprint).sort().join(",") === "agentName,declaredBase,harnessStyle,localOnly", "parent blueprint fields stay exact");
  check(Object.keys(draft.parentGuardValues).sort().join(",") === "fallbackDisclosure,humanCheckpoints,strictValidation", "parent guard fields are exact");
  check(Object.keys(draft.revisedBlueprint).sort().join(",") === "agentName,declaredBase,guardValues,harnessStyle,localOnly", "revised blueprint fields are exact");
  check(Object.keys(draft.revisedBlueprint.guardValues).sort().join(",") === "fallbackDisclosure,humanCheckpoints,strictValidation", "revised guard fields are exact");
  check(Object.keys(draft.state).sort().join(",") === "adopted,committed,executionStatus,localOnly,played,publicationStatus,qualificationStatus,registryStatus", "blueprint-revision state fields are exact");
  check(Object.keys(draft.authority).sort().join(",") === "approval,blueprintAdoption,consensus,correctness,execution,identity,merge,progress,provider,publication,qualification,ranking,registry,resolution,rules,spending", "blueprint-revision authority fields are exact");
  check(Object.values(draft.authority).every((value) => value === false), "blueprint revision draft grants no authority");
  check(draft.draftStatus === "proposed_uncommitted_local_blueprint_revision_draft", "blueprint revision stays a proposed local draft");
  check(draft.state.localOnly === true && draft.state.committed === false && draft.state.adopted === false, "draft remains local, uncommitted, and unadopted");
  check(draft.state.qualificationStatus === "not_run" && draft.state.played === false && draft.state.executionStatus === "disabled", "draft remains unqualified, unplayed, and unexecuted");
  check(draft.state.registryStatus === "not_requested" && draft.state.publicationStatus === "not_requested", "draft remains unregistered and unpublished");
  check(canonical(draft.parentBlueprint) === canonical(parentProposal.blueprint), "draft copies exact parent blueprint identity");
  check(draft.parentGuardValues.humanCheckpoints === false, "draft carries the one parent-known guard value");
  check(draft.parentGuardValues.strictValidation === null && draft.parentGuardValues.fallbackDisclosure === null, "draft invents no uncarried parent guard values");
  check(draft.revisedBlueprint.guardValues.strictValidation === true, "draft applies exactly the accepted strict-validation guard");
  check(draft.revisedBlueprint.guardValues.humanCheckpoints === false && draft.revisedBlueprint.guardValues.fallbackDisclosure === null, "draft preserves carried and unknown non-selected guards");
  check(draft.unknownGuardKeys.join(",") === "fallbackDisclosure", "draft reports exact unknown guard keys");
  check(canonical(draft.appliedGuard) === canonical(deltaProposal.guardDelta), "draft preserves exact reviewed allowlisted guard");
  check(draft.blockers.length === 11 && draft.blockers[0] === "reviewer_identity_unattested", "draft preserves exact blocker chain");
  check(draft.blockers.includes("unreviewed_guard_values_not_carried") && draft.blockers.includes("local_draft_not_adopted"), "draft keeps unknown and adoption blockers");
  check(lineage.acceptedReviewPacketDigest === accepted.review.packet.integrity.payloadDigest, "draft binds accepted review packet");
  check(lineage.acceptedReviewDigest === review.reviewDigest, "draft binds accepted immutable review");
  check(lineage.acceptedCandidateRevisionKey === review.localRevisionCandidate.revisionKey, "draft binds accepted revision candidate");
  check(lineage.guardProposalPacketDigest === accepted.delta.packet.integrity.payloadDigest, "draft binds guard proposal packet");
  check(lineage.guardProposalKey === deltaProposal.proposalKey, "draft binds guard proposal key");
  check(lineage.learningPacketDigest === fixture.learning.packet.integrity.payloadDigest, "draft binds learning packet");
  check(lineage.comparisonPacketDigest === fixture.comparison.packet.integrity.payloadDigest, "draft binds comparison packet");
  check(lineage.parentProposalPayloadDigest === fixture.verified.payloadDigest, "draft binds parent proposal digest");
  check(lineage.parentProposalKey === parentProposal.proposalKey, "draft binds parent proposal key");
  check(lineage.selectedReviewDigest === fixture.changed.reviewDigest, "draft binds selected lesson review");
  check(lineage.guardDeltaId === "require_strict_validation", "draft binds exact guard delta id");
  check(draft.draftKey.includes(lineage.acceptedReviewPacketDigest) && draft.draftKey.includes(lineage.guardDeltaId), "draft key binds accepted review and guard");
  check(packet.integrity.algorithm === "sha256", "blueprint-revision integrity algorithm is exact");
  check(packet.integrity.acceptedReviewPacketDigest === lineage.acceptedReviewPacketDigest, "outer integrity binds accepted review packet");
  check(packet.integrity.acceptedReviewDigest === lineage.acceptedReviewDigest, "outer integrity binds accepted review digest");
  check(packet.integrity.guardProposalPacketDigest === lineage.guardProposalPacketDigest, "outer integrity binds guard proposal");
  check(packet.integrity.parentProposalPayloadDigest === lineage.parentProposalPayloadDigest, "outer integrity binds parent proposal");
  check(packet.integrity.selectedReviewDigest === lineage.selectedReviewDigest, "outer integrity binds selected review");
  check(packet.integrity.draftDigest === draft.draftDigest, "outer integrity binds local draft");
  const draftDigestPayload = copy(draft);
  delete draftDigestPayload.draftDigest;
  check(draft.draftDigest === await digest(canonical(draftDigestPayload)), "independent draft digest agrees");
  check(packet.integrity.payloadDigest === await digest(canonical(packet.payload)), "independent packet digest agrees");
  check(receipt.serialized === canonical(packet), "blueprint-revision export is canonical JSON");
  check(receipt.serialized === again.serialized, "same accepted review creates the same draft receipt");
  check(receipt.serialized.length <= adapter.PRIVATE_BLUEPRINT_REVISION_DRAFT_MAX_LENGTH, "blueprint revision stays inside explicit size cap");
  check(packet.boundary.includes("applies only the reviewed allowlisted guard"), "boundary limits the exact applied guard");
  check(packet.boundary.includes("uncommitted, unadopted, unqualified, unplayed"), "boundary preserves local draft state");
  check(packet.boundary.includes("provider authority"), "boundary refuses provider calls");

  const imported = await adapter.verifyPortablePrivateBlueprintRevisionDraft(receipt.serialized);
  check(imported.verificationStatus === "verified_private_local_blueprint_revision_draft", "fresh import remains a private local blueprint draft");
  check(imported.packetDigest === packet.integrity.payloadDigest, "fresh import recomputes packet digest");
  check(imported.acceptedReviewSerialized === accepted.review.serialized, "fresh import reconstructs exact accepted review");
  check(imported.acceptedReviewVerification.blueprintDeltaSerialized === accepted.delta.serialized, "fresh import reconstructs exact guard proposal");
  check(imported.acceptedReviewVerification.blueprintDeltaVerification.learningSerialized === fixture.learning.serialized, "fresh import reconstructs exact learning receipt");
  check(imported.acceptedReviewVerification.blueprintDeltaVerification.learningVerification.comparisonSerialized === fixture.comparison.serialized, "fresh import reconstructs exact comparison receipt");
  check(imported.acceptedReviewVerification.blueprintDeltaVerification.learningVerification.comparisonVerification.leftSerialized === fixture.left.serialized, "fresh import reconstructs Packet A");
  check(imported.acceptedReviewVerification.blueprintDeltaVerification.learningVerification.comparisonVerification.rightSerialized === fixture.right.serialized, "fresh import reconstructs Packet B");
  check(canonical(imported.draft) === canonical(draft), "fresh import reconstructs exact local draft");
  check(imported.boundary === packet.boundary, "fresh import preserves draft boundary");

  const guardCases = [
    [fixture.changed.reviewDigest, "strictValidation", "require_strict_validation"],
    [fixture.identical.reviewDigest, "humanCheckpoints", "require_human_checkpoints"],
    [fixture.leftOnly.reviewDigest, "fallbackDisclosure", "require_fallback_disclosure"],
  ];
  for (const [reviewDigest, guardKey, deltaId] of guardCases) {
    const value = await makeAcceptedReview(fixture, reviewDigest, "guard_closes_local_safety_gap");
    const draftValue = await adapter.createPortablePrivateBlueprintRevisionDraft(value.review.serialized);
    check(draftValue.packet.payload.draft.appliedGuard.id === deltaId, `${deltaId} stays allowlisted`);
    check(draftValue.packet.payload.draft.revisedBlueprint.guardValues[guardKey] === true, `${deltaId} applies only its target requirement`);
    check(draftValue.packet.payload.draft.state.committed === false && draftValue.packet.payload.draft.state.adopted === false, `${deltaId} remains uncommitted and unadopted`);
  }

  for (const decision of ["defer", "reject"]) {
    const reasonCode = adapter.PRIVATE_BLUEPRINT_DELTA_REVIEW_REASONS[decision][0];
    const reviewValue = await adapter.createPortablePrivateBlueprintDeltaReview(accepted.delta.serialized, {
      reviewerLabel: decision,
      decision,
      reasonCode,
    });
    await rejectsCreate(reviewValue.serialized, "accepted review required");
    const nested = copy(packet);
    nested.payload.acceptedReviewReceipt = reviewValue.packet;
    await resealOuter(nested);
    await rejectsSerialized(canonical(nested), "accepted review required");
  }

  await rejectsCreate("{}", "private blueprint delta review fields drift");
  await rejectsSerialized("", "input length rejected");
  await rejectsSerialized(" ".repeat(adapter.PRIVATE_BLUEPRINT_REVISION_DRAFT_MAX_LENGTH + 1), "input length rejected");
  await rejectsSerialized("{", "invalid JSON");
  await rejectsSerialized(JSON.stringify(packet, null, 2), "must use canonical JSON");
  await rejectsSerialized(`${receipt.serialized}\n`, "must use canonical JSON");
  await rejectsSerialized(receipt.serialized.replace('"draftVersion":1', '"draftVersion":1,"draftVersion":1'), "must use canonical JSON");

  await rejectsPacket(async (value) => { value.extra = true; }, "private blueprint revision draft fields drift");
  await rejectsPacket(async (value) => { delete value.boundary; }, "private blueprint revision draft fields drift");
  await rejectsPacket(async (value) => { value.schemaVersion = "v2"; }, "schema drift");
  await rejectsPacket(async (value) => { value.draftVersion = 2; }, "schema drift");
  await rejectsPacket(async (value) => { value.boundary = "trusted"; }, "boundary drift");
  await rejectsPacket(async (value) => { value.payload.extra = true; }, "private blueprint revision draft payload fields drift");
  await rejectsPacket(async (value) => { delete value.payload.draft; }, "private blueprint revision draft payload fields drift");
  await rejectsPacket(async (value) => { value.integrity.extra = true; }, "private blueprint revision draft integrity fields drift");
  await rejectsPacket(async (value) => { delete value.integrity.draftDigest; }, "private blueprint revision draft integrity fields drift");
  await rejectsPacket(async (value) => { value.integrity.algorithm = "sha512"; }, "integrity algorithm drift");
  for (const key of ["payloadDigest", "acceptedReviewPacketDigest", "acceptedReviewDigest", "guardProposalPacketDigest", "parentProposalPayloadDigest", "selectedReviewDigest", "draftDigest"]) {
    await rejectsPacket(async (value) => { value.integrity[key] = "bad"; }, `${key} drift`);
  }
  await rejectsPacket(async (value) => { value.integrity.acceptedReviewPacketDigest = "0".repeat(64); }, "accepted review packet digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.acceptedReviewDigest = "0".repeat(64); }, "accepted review digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.guardProposalPacketDigest = "0".repeat(64); }, "guard proposal packet digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.parentProposalPayloadDigest = "0".repeat(64); }, "parent proposal digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.selectedReviewDigest = "0".repeat(64); }, "selected review digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.draftDigest = "0".repeat(64); }, "draft digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.payloadDigest = "0".repeat(64); }, "payload digest mismatch");
  await rejectsPacket(async (value) => { value.payload.draft.state.committed = true; }, "draft projection mismatch", { resealInner: true });
  await rejectsPacket(async (value) => { value.payload.draft.state.adopted = true; }, "draft projection mismatch", { resealInner: true });
  await rejectsPacket(async (value) => { value.payload.draft.state.played = true; }, "draft projection mismatch", { resealInner: true });
  await rejectsPacket(async (value) => { value.payload.draft.state.qualificationStatus = "passed"; }, "draft projection mismatch", { resealInner: true });
  await rejectsPacket(async (value) => { value.payload.draft.state.executionStatus = "enabled"; }, "draft projection mismatch", { resealInner: true });
  await rejectsPacket(async (value) => { value.payload.draft.state.registryStatus = "registered"; }, "draft projection mismatch", { resealInner: true });
  await rejectsPacket(async (value) => { value.payload.draft.state.publicationStatus = "published"; }, "draft projection mismatch", { resealInner: true });
  await rejectsPacket(async (value) => { value.payload.draft.revisedBlueprint.guardValues.fallbackDisclosure = true; }, "draft projection mismatch", { resealInner: true });
  await rejectsPacket(async (value) => { value.payload.draft.revisedBlueprint.guardValues.strictValidation = false; }, "draft projection mismatch", { resealInner: true });
  await rejectsPacket(async (value) => { value.payload.draft.parentGuardValues.strictValidation = false; }, "draft projection mismatch", { resealInner: true });
  await rejectsPacket(async (value) => { value.payload.draft.parentBlueprint.agentName = "Forged"; }, "draft projection mismatch", { resealInner: true });
  await rejectsPacket(async (value) => { value.payload.draft.appliedGuard.targetValue = false; }, "draft projection mismatch", { resealInner: true });
  await rejectsPacket(async (value) => { value.payload.draft.unknownGuardKeys = []; }, "draft projection mismatch", { resealInner: true });
  await rejectsPacket(async (value) => { value.payload.draft.lineage.parentProposalKey = "forged"; }, "draft projection mismatch", { resealInner: true });
  await rejectsPacket(async (value) => { value.payload.draft.blockers.pop(); }, "draft projection mismatch", { resealInner: true });
  for (const key of Object.keys(draft.authority)) {
    await rejectsPacket(async (value) => { value.payload.draft.authority[key] = true; }, "draft projection mismatch", { resealInner: true });
  }
  await rejectsPacket(async (value) => { value.payload.acceptedReviewReceipt.payload.review.localRevisionCandidate.committed = true; }, "review projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.acceptedReviewReceipt.payload.blueprintDeltaProposal.payload.proposal.state.played = true; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.acceptedReviewReceipt.payload.blueprintDeltaProposal.payload.learningReceipt.payload.learning.authority.progress = true; }, "learning projection mismatch", { reseal: true });

  const dangerous = copy(packet);
  dangerous.payload.draft["__proto__"] = { polluted: true };
  await rejectsSerialized(canonical(dangerous).replace('"appliedGuard"', '"__proto__":{"polluted":true},"appliedGuard"'), "prohibited key");
  const deep = copy(packet);
  let cursor = deep.payload.draft;
  for (let index = 0; index < 40; index += 1) { cursor.deep = {}; cursor = cursor.deep; }
  await rejectsSerialized(canonical(deep), "nesting limit exceeded");
  const nodeBomb = copy(packet);
  nodeBomb.payload.draft.blockers = Array.from({ length: 105000 }, () => null);
  const nodeBombSerialized = canonical(nodeBomb);
  check(nodeBombSerialized.length < adapter.PRIVATE_BLUEPRINT_REVISION_DRAFT_MAX_LENGTH, "blueprint-revision node bomb stays below byte cap");
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
    require(result.returncode == 0, f"private blueprint revision draft check failed: {result.stderr.strip()}")
    payload = json.loads(result.stdout.strip())
    require(payload["checks"] >= 120, "private blueprint revision draft coverage unexpectedly small")
    require(payload["receiptBytes"] > 0, "private blueprint revision draft receipt was empty")
    require(len(payload["digest"]) == 64, "private blueprint revision draft digest drift")
    print(
        "BuilderWars private blueprint revision draft: PASS "
        f"({payload['checks']} checks; receipt {payload['receiptBytes']} bytes; digest {payload['digest'][:12]}...)"
    )
    print("accepted review only / exact guard application / unknown guards preserved / uncommitted / unadopted / zero authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
