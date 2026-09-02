#!/usr/bin/env python3
"""Adversarial checks for deterministic private inspection-to-blueprint guard proposals."""

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
    require(node is not None, "Node.js is required to exercise private blueprint-delta verification")

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
  try { await adapter.verifyPortablePrivateBlueprintDelta(serialized); } catch (error) { message = error.message; }
  check(message.includes(expected), `guard proposal rejects ${expected}`);
}
async function rejectsPacket(mutator, expected, { reseal = false, source = receipt.packet } = {}) {
  const value = copy(source);
  await mutator(value);
  if (reseal) await resealOuter(value);
  await rejectsSerialized(canonical(value), expected);
}
async function rejectsCreate(learningSerialized, reviewDigest, expected) {
  let message = "";
  try { await adapter.createPortablePrivateBlueprintDelta(learningSerialized, reviewDigest); } catch (error) { message = error.message; }
  check(message.includes(expected), `guard proposal creation rejects ${expected}`);
}

let receipt;

async function makeProposal({ deltaId = "require_human_checkpoints", strictValidation = true, fallbackDisclosure = true, humanCheckpoints = false } = {}) {
  const view = await adapter.adaptArenaReadModel(model, demo);
  const proof = view.proofReceipts.find((candidate) => candidate.moveSourceCounts.model > 0);
  const learning = adapter.buildReceiptLearningAction(proof, "verified_corpus");
  const blueprint = {
    agentName: "Guard Student",
    baseModel: "Arena Reason",
    harnessStyle: "Human review checkpoints",
    strictValidation,
    fallbackDisclosure,
    humanCheckpoints,
    localOnly: true,
  };
  const proposal = adapter.buildRunbackProposal(learning, blueprint, deltaId, "verified_corpus");
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

async function makeLearning(options = {}) {
  const portable = await makeProposal(options);
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
  const learning = await adapter.createPortablePrivateReviewLearning(comparison.serialized);
  return { portable, verified, changed, identical, leftOnly, rightOnly, leftCorrection, rightCorrection, leftExchange, rightExchange, comparison, learning };
}

async function main() {
  check(adapter.PRIVATE_BLUEPRINT_DELTA_SCHEMA === "builderwars.mobile-private-inspection-blueprint-delta.v1", "exports private blueprint-delta schema");
  check(adapter.PRIVATE_BLUEPRINT_DELTA_MAX_LENGTH === 2621440, "exports private blueprint-delta size cap");
  check(typeof adapter.createPortablePrivateBlueprintDelta === "function", "exports private blueprint-delta creator");
  check(typeof adapter.verifyPortablePrivateBlueprintDelta === "function", "exports private blueprint-delta verifier");
  check(Object.keys(adapter.PRIVATE_REVIEW_LESSON_DELTA).sort().join(",") === "inspect_correction_lineage,inspect_evidence,inspect_rules_binding", "exports only three lesson-to-guard mappings");
  check(adapter.PRIVATE_REVIEW_LESSON_DELTA.inspect_evidence === "require_fallback_disclosure", "evidence inspection maps to fallback disclosure");
  check(adapter.PRIVATE_REVIEW_LESSON_DELTA.inspect_rules_binding === "require_human_checkpoints", "rules inspection maps to human checkpoints");
  check(adapter.PRIVATE_REVIEW_LESSON_DELTA.inspect_correction_lineage === "require_strict_validation", "correction inspection maps to strict validation");

  const fixture = await makeLearning();
  receipt = await adapter.createPortablePrivateBlueprintDelta(fixture.learning.serialized, fixture.changed.reviewDigest);
  const again = await adapter.createPortablePrivateBlueprintDelta(fixture.learning.serialized, fixture.changed.reviewDigest);
  const packet = receipt.packet;
  const proposal = packet.payload.proposal;
  const sourceDigests = proposal.sourceDigests;
  check(packet.schemaVersion === adapter.PRIVATE_BLUEPRINT_DELTA_SCHEMA && packet.proposalVersion === 1, "guard proposal is exactly versioned");
  check(Object.keys(packet).sort().join(",") === "boundary,integrity,payload,proposalVersion,schemaVersion", "guard proposal outer fields are exact");
  check(Object.keys(packet.payload).sort().join(",") === "learningReceipt,proposal", "guard proposal payload fields are exact");
  check(Object.keys(packet.integrity).sort().join(",") === "algorithm,comparisonPacketDigest,learningPacketDigest,leftPacketDigest,parentProposalPayloadDigest,payloadDigest,rightPacketDigest,selectedReviewDigest", "guard proposal integrity fields are exact");
  check(Object.keys(proposal).sort().join(",") === "authority,blockers,blueprintIdentity,guardDelta,packetRoles,parentProposalBinding,proposalKey,proposalStatus,selectedLesson,sourceDigests,state", "guard proposal projection fields are exact");
  check(Object.keys(proposal.selectedLesson).sort().join(",") === "classification,deltaId,lessonId,lessonLabel,presence,reviewDigest", "selected lesson fields are exact");
  check(Object.keys(proposal.parentProposalBinding).sort().join(",") === "challengeId,parentReceiptId,proposalKey,proposalPayloadDigest,runbackFixtureId", "parent proposal binding fields are exact");
  check(Object.keys(proposal.packetRoles).sort().join(",") === "left,right", "packet role fields are exact");
  check(Object.keys(proposal.blueprintIdentity).sort().join(",") === "agentName,declaredBase,harnessStyle,localOnly", "blueprint identity fields are exact");
  check(Object.keys(proposal.guardDelta).sort().join(",") === "changeStatus,currentValue,currentValueStatus,guardKey,id,label,rationale,targetValue", "guard delta fields are exact");
  check(Object.keys(proposal.state).sort().join(",") === "committed,executionStatus,played,publicationStatus,qualificationStatus", "guard proposal state fields are exact");
  check(Object.keys(proposal.authority).sort().join(",") === "approval,blueprintAdoption,consensus,correctness,execution,identity,merge,progress,provider,publication,qualification,ranking,registry,resolution,rules,spending", "guard proposal authority fields are exact");
  check(Object.values(proposal.authority).every((value) => value === false), "guard proposal grants no authority");
  check(proposal.proposalStatus === "proposed_uncommitted_guard_delta", "guard proposal status remains uncommitted");
  check(proposal.state.committed === false && proposal.state.played === false, "guard proposal remains uncommitted and unplayed");
  check(proposal.state.qualificationStatus === "not_run" && proposal.state.executionStatus === "disabled" && proposal.state.publicationStatus === "not_requested", "guard proposal keeps downstream states closed");
  check(proposal.packetRoles.left === "packet_a" && proposal.packetRoles.right === "packet_b", "guard proposal preserves neutral packet roles");
  check(proposal.blockers.length === 8 && proposal.blockers[0] === "lesson_does_not_establish_correctness", "guard proposal preserves the exact blocker chain");
  check(proposal.blockers.includes("explicit_rules_digest_not_bound") && proposal.blockers.includes("sanctioned_runner_not_bound"), "guard proposal keeps rules and runner blockers");
  check(proposal.selectedLesson.reviewDigest === fixture.changed.reviewDigest, "guard proposal binds the exact selected review");
  check(proposal.selectedLesson.lessonId === "inspect_correction_lineage", "changed state binds correction-lineage lesson");
  check(proposal.selectedLesson.deltaId === "require_strict_validation", "correction-lineage lesson selects strict validation only");
  check(proposal.guardDelta.id === "require_strict_validation" && proposal.guardDelta.guardKey === "strictValidation", "strict-validation guard is allowlisted");
  check(proposal.guardDelta.currentValue === null && proposal.guardDelta.currentValueStatus === "not_carried_by_parent_proposal", "unknown current guard is disclosed without invention");
  check(proposal.guardDelta.targetValue === true && proposal.guardDelta.changeStatus === "proposed_requirement_only", "unknown current guard creates requirement-only proposal");
  check(proposal.blueprintIdentity.agentName === fixture.verified.proposal.blueprint.agentName, "guard proposal binds parent agent name");
  check(proposal.blueprintIdentity.declaredBase === fixture.verified.proposal.blueprint.declaredBase, "guard proposal binds parent declared base");
  check(proposal.blueprintIdentity.harnessStyle === fixture.verified.proposal.blueprint.harnessStyle && proposal.blueprintIdentity.localOnly === true, "guard proposal binds local parent harness identity");
  check(proposal.parentProposalBinding.proposalPayloadDigest === fixture.verified.payloadDigest, "guard proposal binds parent proposal payload digest");
  check(proposal.parentProposalBinding.proposalKey === fixture.verified.proposal.proposalKey, "guard proposal binds parent proposal key");
  check(proposal.parentProposalBinding.parentReceiptId === fixture.verified.proposal.parentReceipt.receiptId, "guard proposal binds parent receipt");
  check(proposal.parentProposalBinding.challengeId === fixture.verified.proposal.runbackLineage.challengeId, "guard proposal binds parent challenge");
  check(proposal.parentProposalBinding.runbackFixtureId === fixture.verified.proposal.runbackLineage.fixtureId, "guard proposal binds parent runback fixture");
  check(sourceDigests.comparisonPacketDigest === fixture.comparison.packet.integrity.payloadDigest, "guard proposal preserves comparison digest");
  check(sourceDigests.proposalPayloadDigest === fixture.verified.payloadDigest, "guard proposal preserves proposal digest");
  check(sourceDigests.left.correctionExchangePacketDigest === fixture.leftExchange.packet.integrity.payloadDigest, "guard proposal preserves Packet A digest");
  check(sourceDigests.right.correctionExchangePacketDigest === fixture.rightExchange.packet.integrity.payloadDigest, "guard proposal preserves Packet B digest");
  check(packet.integrity.algorithm === "sha256", "guard proposal integrity algorithm is exact");
  check(packet.integrity.learningPacketDigest === fixture.learning.packet.integrity.payloadDigest, "outer integrity binds learning receipt");
  check(packet.integrity.comparisonPacketDigest === fixture.comparison.packet.integrity.payloadDigest, "outer integrity binds comparison receipt");
  check(packet.integrity.parentProposalPayloadDigest === fixture.verified.payloadDigest, "outer integrity binds parent proposal");
  check(packet.integrity.leftPacketDigest === fixture.leftExchange.packet.integrity.payloadDigest, "outer integrity binds Packet A source");
  check(packet.integrity.rightPacketDigest === fixture.rightExchange.packet.integrity.payloadDigest, "outer integrity binds Packet B source");
  check(packet.integrity.selectedReviewDigest === fixture.changed.reviewDigest, "outer integrity binds selected lesson review");
  check(packet.integrity.payloadDigest === await digest(canonical(packet.payload)), "independent guard proposal payload digest agrees");
  check(receipt.serialized === canonical(packet), "guard proposal export is canonical JSON");
  check(receipt.serialized === again.serialized, "same lesson and ancestry create the same guard proposal");
  check(receipt.serialized.length <= adapter.PRIVATE_BLUEPRINT_DELTA_MAX_LENGTH, "guard proposal stays inside explicit size cap");
  check(!receipt.serialized.includes('"correctPacket"'), "guard proposal never names a correct packet");
  check(packet.boundary.includes("uncommitted and unplayed"), "guard proposal boundary refuses commitment and play");
  check(packet.boundary.includes("chooses no correct packet"), "guard proposal boundary refuses correctness");
  check(packet.boundary.includes("provider authority"), "guard proposal boundary refuses provider authority");

  const imported = await adapter.verifyPortablePrivateBlueprintDelta(receipt.serialized);
  check(imported.verificationStatus === "verified_private_local_blueprint_delta_proposal", "fresh import remains private local proposal verification");
  check(imported.packetDigest === packet.integrity.payloadDigest, "fresh import recomputes guard proposal digest");
  check(imported.learningSerialized === fixture.learning.serialized, "fresh import reconstructs exact learning receipt");
  check(imported.learningVerification.comparisonSerialized === fixture.comparison.serialized, "fresh import reconstructs exact comparison receipt");
  check(imported.learningVerification.comparisonVerification.leftSerialized === fixture.leftExchange.serialized, "fresh import reconstructs exact Packet A source");
  check(imported.learningVerification.comparisonVerification.rightSerialized === fixture.rightExchange.serialized, "fresh import reconstructs exact Packet B source");
  check(canonical(imported.proposal) === canonical(proposal), "fresh import reconstructs exact guard projection");
  check(imported.boundary === packet.boundary, "fresh import preserves guard proposal boundary");

  const rulesReceipt = await adapter.createPortablePrivateBlueprintDelta(fixture.learning.serialized, fixture.identical.reviewDigest);
  const rulesProposal = rulesReceipt.packet.payload.proposal;
  check(rulesProposal.selectedLesson.lessonId === "inspect_rules_binding", "identical state binds rules inspection lesson");
  check(rulesProposal.guardDelta.id === "require_human_checkpoints", "rules inspection selects human checkpoint only");
  check(rulesProposal.guardDelta.currentValue === false && rulesProposal.guardDelta.currentValueStatus === "carried_by_parent_proposal", "carried false guard value is preserved");
  check(rulesProposal.guardDelta.changeStatus === "proposed_change", "carried false guard becomes an explicit proposed change");

  const evidenceReceipt = await adapter.createPortablePrivateBlueprintDelta(fixture.learning.serialized, fixture.leftOnly.reviewDigest);
  const evidenceProposal = evidenceReceipt.packet.payload.proposal;
  check(evidenceProposal.selectedLesson.lessonId === "inspect_evidence", "one-sided state binds evidence inspection lesson");
  check(evidenceProposal.guardDelta.id === "require_fallback_disclosure", "evidence inspection selects fallback disclosure only");
  check(evidenceProposal.guardDelta.currentValue === null && evidenceProposal.guardDelta.changeStatus === "proposed_requirement_only", "uncarried fallback guard stays requirement-only");

  const carriedFixture = await makeLearning({ deltaId: "require_strict_validation", strictValidation: true });
  const carriedReceipt = await adapter.createPortablePrivateBlueprintDelta(carriedFixture.learning.serialized, carriedFixture.changed.reviewDigest);
  const carriedProposal = carriedReceipt.packet.payload.proposal;
  check(carriedProposal.guardDelta.currentValue === true && carriedProposal.guardDelta.currentValueStatus === "carried_by_parent_proposal", "carried true guard value is preserved");
  check(carriedProposal.guardDelta.changeStatus === "already_declared_requirement", "carried true guard is not described as a change");

  const swappedComparison = await adapter.createPortablePrivateReviewComparison(fixture.rightExchange.serialized, fixture.leftExchange.serialized);
  const swappedLearning = await adapter.createPortablePrivateReviewLearning(swappedComparison.serialized);
  const swappedReceipt = await adapter.createPortablePrivateBlueprintDelta(swappedLearning.serialized, fixture.changed.reviewDigest);
  check(swappedReceipt.serialized !== receipt.serialized, "swapped packet roles remain explicit in guard proposal receipt");
  check(swappedReceipt.packet.payload.proposal.sourceDigests.left.correctionExchangePacketDigest === fixture.rightExchange.packet.integrity.payloadDigest, "swapped Packet A digest follows input role");
  check(swappedReceipt.packet.payload.proposal.sourceDigests.right.correctionExchangePacketDigest === fixture.leftExchange.packet.integrity.payloadDigest, "swapped Packet B digest follows input role");
  check(swappedReceipt.packet.payload.proposal.guardDelta.id === proposal.guardDelta.id, "swapping neutral roles does not alter fixed lesson-to-guard mapping");

  await rejectsCreate(fixture.learning.serialized, "", "selected review digest rejected");
  await rejectsCreate(fixture.learning.serialized, "0".repeat(64), "selected lesson missing");
  await rejectsCreate("{}", fixture.changed.reviewDigest, "private review learning fields drift");
  await rejectsSerialized("", "input length rejected");
  await rejectsSerialized(" ".repeat(adapter.PRIVATE_BLUEPRINT_DELTA_MAX_LENGTH + 1), "input length rejected");
  await rejectsSerialized("{", "invalid JSON");
  await rejectsSerialized(JSON.stringify(packet, null, 2), "must use canonical JSON");
  await rejectsSerialized(`${receipt.serialized}\n`, "must use canonical JSON");
  await rejectsSerialized(receipt.serialized.replace('"proposalVersion":1', '"proposalVersion":1,"proposalVersion":1'), "must use canonical JSON");

  await rejectsPacket(async (value) => { value.extra = true; }, "private blueprint delta fields drift");
  await rejectsPacket(async (value) => { delete value.boundary; }, "private blueprint delta fields drift");
  await rejectsPacket(async (value) => { value.schemaVersion = "v2"; }, "schema drift");
  await rejectsPacket(async (value) => { value.proposalVersion = 2; }, "schema drift");
  await rejectsPacket(async (value) => { value.boundary = "trusted"; }, "boundary drift");
  await rejectsPacket(async (value) => { value.payload.extra = true; }, "private blueprint delta payload fields drift");
  await rejectsPacket(async (value) => { delete value.payload.proposal; }, "private blueprint delta payload fields drift");
  await rejectsPacket(async (value) => { value.integrity.extra = true; }, "private blueprint delta integrity fields drift");
  await rejectsPacket(async (value) => { delete value.integrity.selectedReviewDigest; }, "private blueprint delta integrity fields drift");
  await rejectsPacket(async (value) => { value.integrity.algorithm = "sha512"; }, "integrity algorithm drift");
  for (const key of ["payloadDigest", "learningPacketDigest", "comparisonPacketDigest", "parentProposalPayloadDigest", "leftPacketDigest", "rightPacketDigest", "selectedReviewDigest"]) {
    await rejectsPacket(async (value) => { value.integrity[key] = "bad"; }, `${key} drift`);
  }
  await rejectsPacket(async (value) => { value.integrity.learningPacketDigest = "0".repeat(64); }, "learning packet digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.comparisonPacketDigest = "0".repeat(64); }, "comparison packet digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.parentProposalPayloadDigest = "0".repeat(64); }, "parent proposal digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.leftPacketDigest = "0".repeat(64); }, "left packet digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.rightPacketDigest = "0".repeat(64); }, "right packet digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.payloadDigest = "0".repeat(64); }, "payload digest mismatch");
  await rejectsPacket(async (value) => { value.integrity.selectedReviewDigest = fixture.identical.reviewDigest; }, "proposal projection mismatch");
  await rejectsPacket(async (value) => { value.payload.proposal.selectedLesson.lessonId = "inspect_evidence"; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.proposal.selectedLesson.deltaId = "require_fallback_disclosure"; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.proposal.guardDelta.guardKey = "networkEnabled"; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.proposal.guardDelta.currentValue = false; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.proposal.guardDelta.targetValue = false; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.proposal.state.committed = true; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.proposal.state.played = true; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.proposal.state.qualificationStatus = "passed"; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.proposal.authority.correctness = true; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.proposal.authority.progress = true; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.proposal.authority.blueprintAdoption = true; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.proposal.authority.provider = true; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.proposal.packetRoles.left = "winner"; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.proposal.sourceDigests.left.packetRole = "winner"; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.proposal.parentProposalBinding.proposalKey = "forged"; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.proposal.blueprintIdentity.agentName = "Replacement"; }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.proposal.blockers.pop(); }, "proposal projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.learningReceipt.payload.learning.authority.progress = true; }, "learning projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.learningReceipt.payload.comparisonReceipt.payload.comparison.authority.merge = true; }, "comparison projection mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.learningReceipt.payload.comparisonReceipt.payload.leftCorrectionExchangePacket.payload.corrections[0].correctedDecision = "reject"; }, "correction digest mismatch", { reseal: true });

  const dangerous = copy(packet);
  dangerous.payload.proposal["__proto__"] = { polluted: true };
  await rejectsSerialized(canonical(dangerous).replace('"authority"', '"__proto__":{"polluted":true},"authority"'), "prohibited key");
  const deep = copy(packet);
  let cursor = deep.payload.proposal;
  for (let index = 0; index < 40; index += 1) { cursor.deep = {}; cursor = cursor.deep; }
  await rejectsSerialized(canonical(deep), "nesting limit exceeded");
  const nodeBomb = copy(packet);
  nodeBomb.payload.proposal.blockers = Array.from({ length: 80000 }, () => null);
  const nodeBombSerialized = canonical(nodeBomb);
  check(nodeBombSerialized.length < adapter.PRIVATE_BLUEPRINT_DELTA_MAX_LENGTH, "guard proposal node bomb stays below byte cap");
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
        timeout=180,
        check=False,
    )
    require(result.returncode == 0, f"private blueprint-delta check failed: {result.stderr.strip()}")
    payload = json.loads(result.stdout.strip())
    require(payload["checks"] >= 100, "private blueprint-delta coverage unexpectedly small")
    require(payload["receiptBytes"] > 0, "private blueprint-delta receipt was empty")
    require(len(payload["digest"]) == 64, "private blueprint-delta digest drift")
    print(
        "BuilderWars private blueprint delta: PASS "
        f"({payload['checks']} checks; receipt {payload['receiptBytes']} bytes; digest {payload['digest'][:12]}...)"
    )
    print("verified lesson / fixed allowlisted guard / exact parent and source digests / uncommitted / unplayed / zero authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
