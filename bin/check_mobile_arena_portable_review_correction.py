#!/usr/bin/env python3
"""Adversarial checks for immutable private-review corrections and exchange."""

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
    require(node is not None, "Node.js is required to exercise portable review correction verification")

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
async function resealPacket(packet) {
  packet.integrity.payloadDigest = await digest(canonical(packet.payload));
  return packet;
}
async function rejectsSerialized(serialized, expected) {
  let message = "";
  try { await adapter.verifyPortableRunbackReviewCorrectionExchange(serialized); } catch (error) { message = error.message; }
  check(message.includes(expected), `correction exchange rejects ${expected}`);
}
async function rejectsPacket(mutator, expected, { reseal = false, source = packet } = {}) {
  const value = copy(source);
  await mutator(value);
  if (reseal) await resealPacket(value);
  await rejectsSerialized(canonical(value), expected);
}
async function rejectsAppend(input, existing, expected, reviews = journal) {
  let message = "";
  try { await adapter.appendPortableRunbackReviewCorrection(verified, reviews, input, existing); } catch (error) { message = error.message; }
  check(message.includes(expected), `correction append rejects ${expected}`);
}

let packet;
let journal;
let verified;

async function main() {
  const view = await adapter.adaptArenaReadModel(model, demo);
  const proof = view.proofReceipts.find((candidate) => candidate.moveSourceCounts.model > 0);
  const learning = adapter.buildReceiptLearningAction(proof, "verified_corpus");
  const blueprint = {
    agentName: "Correction Student",
    baseModel: "Arena Reason",
    harnessStyle: "Human review checkpoints",
    strictValidation: true,
    fallbackDisclosure: true,
    humanCheckpoints: false,
    localOnly: true,
  };
  const proposal = adapter.buildRunbackProposal(learning, blueprint, "require_human_checkpoints", "verified_corpus");
  const portable = await adapter.createPortableRunbackEnvelope(proposal);
  verified = await adapter.verifyPortableRunbackEnvelope(portable.serialized);
  const accepted = await adapter.appendPortableRunbackReview(verified, {
    reviewerLabel: "Original A",
    decision: "accept_for_blueprint_revision",
    reasonCode: "receipt_guided_guard_change",
  }, []);
  const deferred = await adapter.appendPortableRunbackReview(verified, {
    reviewerLabel: "Original B",
    decision: "defer",
    reasonCode: "needs_explicit_rules_binding",
  }, [accepted]);
  const rejected = await adapter.appendPortableRunbackReview(verified, {
    reviewerLabel: "Original C",
    decision: "reject",
    reasonCode: "unsafe_or_out_of_scope",
  }, [accepted, deferred]);
  journal = [accepted, deferred, rejected];

  check(adapter.PORTABLE_REVIEW_CORRECTION_SCHEMA === "builderwars.mobile-runback-review-correction.v1", "exports correction schema");
  check(adapter.PORTABLE_REVIEW_CORRECTION_EXCHANGE_SCHEMA === "builderwars.mobile-runback-review-correction-exchange.v1", "exports correction exchange schema");
  check(adapter.PORTABLE_REVIEW_CORRECTION_MAX_RECORDS === 64, "exports correction record cap");
  check(adapter.PORTABLE_REVIEW_CORRECTION_EXCHANGE_MAX_LENGTH === 524288, "exports correction exchange size cap");
  check(typeof adapter.appendPortableRunbackReviewCorrection === "function", "exports correction appender");
  check(typeof adapter.verifyPortableRunbackReviewCorrectionJournal === "function", "exports correction journal verifier");
  check(typeof adapter.createPortableRunbackReviewCorrectionExchange === "function", "exports correction exchange creator");
  check(typeof adapter.verifyPortableRunbackReviewCorrectionExchange === "function", "exports correction exchange verifier");
  check(Object.keys(adapter.PORTABLE_REVIEW_CORRECTION_REASONS).sort().join(",") === "correct_decision,withdraw_review", "correction actions are bounded");

  const corrected = await adapter.appendPortableRunbackReviewCorrection(verified, journal, {
    reviewerLabel: "Correction A",
    targetReviewDigest: accepted.reviewDigest,
    action: "correct_decision",
    correctedDecision: "defer",
    reasonCode: "clerical_decision_error",
  }, []);
  const withdrawn = await adapter.appendPortableRunbackReviewCorrection(verified, journal, {
    reviewerLabel: "Correction B",
    targetReviewDigest: accepted.reviewDigest,
    action: "withdraw_review",
    correctedDecision: null,
    reasonCode: "reviewer_requested_withdrawal",
  }, [corrected]);
  const restored = await adapter.appendPortableRunbackReviewCorrection(verified, journal, {
    reviewerLabel: "Correction C",
    targetReviewDigest: accepted.reviewDigest,
    action: "correct_decision",
    correctedDecision: "reject",
    reasonCode: "new_private_evidence",
  }, [corrected, withdrawn]);
  const correctedAccept = await adapter.appendPortableRunbackReviewCorrection(verified, journal, {
    reviewerLabel: "Correction D",
    targetReviewDigest: deferred.reviewDigest,
    action: "correct_decision",
    correctedDecision: "accept_for_blueprint_revision",
    reasonCode: "new_private_evidence",
  }, [corrected, withdrawn, restored]);
  const corrections = [corrected, withdrawn, restored, correctedAccept];
  const originalBytes = canonical(journal);
  const verifiedCorrections = await adapter.verifyPortableRunbackReviewCorrectionJournal(corrections, verified, journal);

  check(canonical(journal) === originalBytes, "correction verification never mutates original reviews");
  check(verifiedCorrections.verificationStatus === "verified_private_local_review_correction_journal", "correction journal stays private local verification");
  check(verifiedCorrections.correctionCount === 4, "correction journal preserves exact count");
  check(verifiedCorrections.latestCorrectionDigest === correctedAccept.correctionDigest, "correction journal binds global head");
  check(corrected.sequence === 1 && corrected.previousCorrectionDigest === null && corrected.supersedesCorrectionDigest === null, "first correction starts both chains exactly");
  check(withdrawn.previousCorrectionDigest === corrected.correctionDigest && withdrawn.supersedesCorrectionDigest === corrected.correctionDigest, "second same-target correction binds global and target predecessor");
  check(restored.previousCorrectionDigest === withdrawn.correctionDigest && restored.supersedesCorrectionDigest === withdrawn.correctionDigest, "third same-target correction supersedes withdrawal without deleting it");
  check(correctedAccept.previousCorrectionDigest === restored.correctionDigest && correctedAccept.supersedesCorrectionDigest === null, "different-target correction keeps global chain and starts target chain");
  check(corrected.targetReview.reviewDigest === accepted.reviewDigest && corrected.targetReview.sequence === accepted.sequence, "correction binds immutable review digest and sequence");
  check(corrected.proposalBinding.envelopeDigest === verified.payloadDigest, "correction binds proposal digest");
  check(corrected.action === "correct_decision" && corrected.correctedDecision === "defer", "correction carries exact corrected decision");
  check(withdrawn.action === "withdraw_review" && withdrawn.correctedDecision === null, "withdrawal carries no invented decision");
  check(corrected.blueprintRevision === null && withdrawn.blueprintRevision === null && restored.blueprintRevision === null, "non-accept corrections create no blueprint revision");
  check(correctedAccept.blueprintRevision.status === "proposed_uncommitted_correction_revision", "corrected acceptance creates only proposed correction revision");
  check(correctedAccept.blueprintRevision.committed === false && correctedAccept.blueprintRevision.targetReviewDigest === deferred.reviewDigest, "correction revision stays uncommitted and target-bound");
  check(Object.values(correctedAccept.attestations).every((value) => value === false), "correction attestations all remain false");
  check(corrected.boundary.includes("preserves its immutable target review"), "correction boundary preserves original review");
  check(corrected.boundary.includes("cannot rewrite history"), "correction boundary refuses history rewrite");
  check(corrected.boundary.includes("call a provider"), "correction boundary refuses provider call");
  check(verifiedCorrections.effectiveReviews[0].originalDecision === "accept_for_blueprint_revision", "effective projection preserves first original decision");
  check(verifiedCorrections.effectiveReviews[0].effectiveDecision === "reject" && verifiedCorrections.effectiveReviews[0].correctionCount === 3, "latest same-target correction drives private interpretation");
  check(verifiedCorrections.effectiveReviews[1].effectiveDecision === "accept_for_blueprint_revision" && verifiedCorrections.effectiveReviews[1].correctionCount === 1, "different-target corrected acceptance projects exactly");
  check(verifiedCorrections.effectiveReviews[2].effectiveStatus === "original_private_review" && verifiedCorrections.effectiveReviews[2].effectiveDecision === "reject", "uncorrected review remains original");

  await rejectsAppend({ reviewerLabel: "X", targetReviewDigest: accepted.reviewDigest, action: "correct_decision", correctedDecision: "accept_for_blueprint_revision", reasonCode: "clerical_decision_error" }, [], "corrected decision is unchanged");
  await rejectsAppend({ reviewerLabel: "X", targetReviewDigest: "0".repeat(64), action: "correct_decision", correctedDecision: "defer", reasonCode: "clerical_decision_error" }, [], "immutable target review missing");
  await rejectsAppend({ reviewerLabel: "X", targetReviewDigest: accepted.reviewDigest, action: "withdraw_review", correctedDecision: "reject", reasonCode: "duplicate_review" }, [], "withdrawal decision drift");
  await rejectsAppend({ reviewerLabel: "X", targetReviewDigest: accepted.reviewDigest, action: "correct_decision", correctedDecision: "defer", reasonCode: "duplicate_review" }, [], "action reason drift");
  await rejectsAppend({ reviewerLabel: "X", targetReviewDigest: accepted.reviewDigest, action: "withdraw_review", correctedDecision: null, reasonCode: "duplicate_review" }, [corrected, withdrawn], "review already withdrawn");

  const exchange = await adapter.createPortableRunbackReviewCorrectionExchange(portable.serialized, journal, corrections);
  const exchangeAgain = await adapter.createPortableRunbackReviewCorrectionExchange(portable.serialized, copy(journal), copy(corrections));
  packet = exchange.packet;
  check(packet.schemaVersion === adapter.PORTABLE_REVIEW_CORRECTION_EXCHANGE_SCHEMA && packet.exchangeVersion === 1, "correction exchange is exactly versioned");
  check(Object.keys(packet).sort().join(",") === "boundary,exchangeVersion,integrity,payload,schemaVersion", "correction exchange outer fields are exact");
  check(Object.keys(packet.payload).sort().join(",") === "corrections,reviewExchangePacket", "correction exchange payload fields are exact");
  check(Object.keys(packet.integrity).sort().join(",") === "algorithm,correctionHeadDigest,payloadDigest,reviewExchangePayloadDigest", "correction exchange integrity fields are exact");
  check(packet.integrity.algorithm === "sha256", "correction exchange algorithm is exact");
  check(packet.integrity.reviewExchangePayloadDigest === packet.payload.reviewExchangePacket.integrity.payloadDigest, "correction exchange binds nested review packet");
  check(packet.integrity.correctionHeadDigest === correctedAccept.correctionDigest, "correction exchange binds correction head");
  check(packet.payload.corrections.length === 4, "correction exchange carries exact corrections");
  check(exchange.serialized === canonical(packet), "correction exchange export is canonical JSON");
  check(exchange.serialized === exchangeAgain.serialized, "same review and correction history exports deterministically");
  check(exchange.serialized.length <= adapter.PORTABLE_REVIEW_CORRECTION_EXCHANGE_MAX_LENGTH, "correction exchange stays inside explicit size cap");
  check(packet.integrity.payloadDigest === await digest(canonical(packet.payload)), "independent correction packet digest agrees");
  check(packet.boundary.includes("immutable private reviews"), "correction exchange states immutable review boundary");
  check(packet.boundary.includes("cannot rewrite a review"), "correction exchange refuses review rewrite");

  const imported = await adapter.verifyPortableRunbackReviewCorrectionExchange(exchange.serialized);
  check(imported.verificationStatus === "verified_private_local_review_correction_exchange", "fresh import remains private local correction verification");
  check(imported.packetDigest === packet.integrity.payloadDigest, "fresh import recomputes correction packet digest");
  check(imported.reviewExchangeSerialized === canonical(packet.payload.reviewExchangePacket), "fresh import reconstructs canonical nested review packet");
  check(imported.proposalSerialized === portable.serialized, "fresh import reconstructs original proposal envelope");
  check(imported.proposalVerification.verificationStatus === "verified_local_unplayed_proposal", "fresh import keeps proposal still unplayed");
  check(imported.journal.reviewCount === 3 && imported.journal.latestReviewDigest === rejected.reviewDigest, "fresh import reverifies immutable review chain");
  check(imported.correctionJournal.correctionCount === 4 && imported.correctionJournal.latestCorrectionDigest === correctedAccept.correctionDigest, "fresh import reverifies correction and supersession chains");
  check(imported.correctionJournal.effectiveReviews[0].effectiveDecision === "reject", "fresh import reconstructs latest private interpretation");
  check(canonical(imported.journal.reviews) === originalBytes, "fresh import preserves exact original review bytes");
  check(imported.boundary === packet.boundary, "fresh import preserves correction exchange boundary");

  const emptyExchange = await adapter.createPortableRunbackReviewCorrectionExchange(portable.serialized, journal, []);
  const emptyImport = await adapter.verifyPortableRunbackReviewCorrectionExchange(emptyExchange.serialized);
  check(emptyExchange.packet.payload.corrections.length === 0, "empty correction history exports without invented records");
  check(emptyExchange.packet.integrity.correctionHeadDigest === null, "empty correction history binds null head");
  check(emptyImport.correctionJournal.correctionCount === 0 && emptyImport.correctionJournal.latestCorrectionDigest === null, "empty correction history imports exactly");
  check(emptyImport.correctionJournal.effectiveReviews.every((review) => review.effectiveStatus === "original_private_review"), "empty correction history preserves original interpretation");

  await rejectsSerialized("", "input length rejected");
  await rejectsSerialized(" ".repeat(adapter.PORTABLE_REVIEW_CORRECTION_EXCHANGE_MAX_LENGTH + 1), "input length rejected");
  await rejectsSerialized("{", "invalid JSON");
  await rejectsSerialized(JSON.stringify(packet, null, 2), "must use canonical JSON");
  await rejectsSerialized(`${exchange.serialized}\n`, "must use canonical JSON");
  await rejectsSerialized(exchange.serialized.replace('"exchangeVersion":1', '"exchangeVersion":1,"exchangeVersion":1'), "must use canonical JSON");

  await rejectsPacket(async (value) => { value.extra = true; }, "portable review correction exchange fields drift");
  await rejectsPacket(async (value) => { delete value.boundary; }, "portable review correction exchange fields drift");
  await rejectsPacket(async (value) => { value.schemaVersion = "v2"; }, "schema drift");
  await rejectsPacket(async (value) => { value.exchangeVersion = 2; }, "schema drift");
  await rejectsPacket(async (value) => { value.boundary = "trusted"; }, "boundary drift");
  await rejectsPacket(async (value) => { value.payload.extra = true; }, "portable review correction exchange payload fields drift");
  await rejectsPacket(async (value) => { delete value.payload.corrections; }, "portable review correction exchange payload fields drift");
  await rejectsPacket(async (value) => { value.integrity.extra = true; }, "portable review correction exchange integrity fields drift");
  await rejectsPacket(async (value) => { delete value.integrity.correctionHeadDigest; }, "portable review correction exchange integrity fields drift");
  await rejectsPacket(async (value) => { value.integrity.algorithm = "sha512"; }, "integrity algorithm drift");
  await rejectsPacket(async (value) => { value.integrity.payloadDigest = "bad"; }, "integrity digest drift");
  await rejectsPacket(async (value) => { value.integrity.reviewExchangePayloadDigest = "bad"; }, "integrity digest drift");
  await rejectsPacket(async (value) => { value.integrity.correctionHeadDigest = "bad"; }, "correction head digest drift");
  await rejectsPacket(async (value) => { value.integrity.reviewExchangePayloadDigest = "0".repeat(64); }, "review exchange digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.correctionHeadDigest = "0".repeat(64); }, "correction head binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.payloadDigest = "0".repeat(64); }, "payload digest mismatch");

  await rejectsPacket(async (value) => { value.payload.reviewExchangePacket.extra = true; }, "portable review exchange fields drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.reviewExchangePacket.payload.reviews[0].reviewStatus = "public"; }, "private status drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.reviewExchangePacket.payload.proposalEnvelope.payload.runbackStatus = "played"; }, "proposal is not unplayed", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.reviewExchangePacket.payload.proposalEnvelope.payload.attestations.provider = true; }, "attestation must remain false", { reseal: true });

  await rejectsPacket(async (value) => { value.payload.corrections = null; }, "journal length rejected", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.corrections[0].extra = true; }, "portable review correction fields drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.corrections[0].schemaVersion = "v2"; }, "schema drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.corrections[0].sequence = 2; }, "sequence drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.corrections[0].correctionStatus = "public"; }, "private status drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.corrections[0].action = "approve"; }, "unknown action", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.corrections[0].reasonCode = "duplicate_review"; }, "action reason drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.corrections[0].correctedDecision = "accept_for_blueprint_revision"; }, "corrected decision is unchanged", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.corrections[0].reviewer.identityAttested = true; }, "reviewer boundary drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.corrections[0].proposalBinding.envelopeDigest = "0".repeat(64); }, "envelopeDigest drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.corrections[0].targetReview.sequence = 3; }, "immutable target review missing", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.corrections[0].targetReview.reviewDigest = "0".repeat(64); }, "immutable target review missing", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.corrections[1].previousCorrectionDigest = null; }, "append-only chain drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.corrections[1].supersedesCorrectionDigest = null; }, "supersession link drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.corrections[1].correctedDecision = "reject"; }, "withdrawal decision drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.corrections[0].blueprintRevision = copy(correctedAccept.blueprintRevision); }, "correction created an unauthorized revision", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.corrections[3].blueprintRevision.committed = true; }, "proposed correction revision drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.corrections[0].blockers.pop(); }, "blockers drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.corrections[0].attestations.execution = true; }, "attestation must remain false", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.corrections[0].boundary = "trusted"; }, "boundary drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.corrections[0].correctionDigest = "0".repeat(64); }, "correction digest mismatch", { reseal: true });
  await rejectsPacket(async (value) => { [value.payload.corrections[0], value.payload.corrections[1]] = [value.payload.corrections[1], value.payload.corrections[0]]; }, "sequence drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.corrections.pop(); }, "correction head binding mismatch", { reseal: true });

  const foreignProposal = adapter.buildRunbackProposal(learning, { ...blueprint, agentName: "Foreign Correction" }, "require_human_checkpoints", "verified_corpus");
  const foreignPortable = await adapter.createPortableRunbackEnvelope(foreignProposal);
  const foreignReview = await adapter.appendPortableRunbackReview(await adapter.verifyPortableRunbackEnvelope(foreignPortable.serialized), {
    reviewerLabel: "Foreign",
    decision: "reject",
    reasonCode: "unsafe_or_out_of_scope",
  }, []);
  const foreignReviewExchange = await adapter.createPortableRunbackReviewExchange(foreignPortable.serialized, [foreignReview]);
  await rejectsPacket(async (value) => {
    value.payload.reviewExchangePacket = foreignReviewExchange.packet;
    value.integrity.reviewExchangePayloadDigest = foreignReviewExchange.packet.integrity.payloadDigest;
  }, "envelopeDigest drift", { reseal: true });

  const dangerous = JSON.parse(exchange.serialized.replace('"payload":{', '"payload":{"constructor":{"polluted":true},'));
  await rejectsSerialized(canonical(dangerous), "prohibited key");
  const deep = copy(packet);
  deep.extra = {};
  let cursor = deep.extra;
  for (let index = 0; index < 34; index += 1) { cursor.next = {}; cursor = cursor.next; }
  await rejectsSerialized(canonical(deep), "nesting limit exceeded");
  const nodeBomb = copy(packet);
  nodeBomb.extra = Array.from({ length: 20000 }, () => null);
  await rejectsSerialized(canonical(nodeBomb), "node limit exceeded");
  const tooMany = copy(packet);
  tooMany.payload.corrections = Array.from({ length: 65 }, () => copy(corrected));
  await resealPacket(tooMany);
  await rejectsSerialized(canonical(tooMany), "journal length rejected");

  const fullReviews = [];
  for (let index = 0; index < adapter.PORTABLE_REVIEW_MAX_RECORDS; index += 1) {
    const review = await adapter.appendPortableRunbackReview(verified, {
      reviewerLabel: `Original ${String(index + 1).padStart(2, "0")}`,
      decision: "reject",
      reasonCode: "duplicate_or_stale_proposal",
    }, fullReviews);
    fullReviews.push(review);
  }
  const fullCorrections = [];
  const cycle = [
    { action: "correct_decision", correctedDecision: "defer", reasonCode: "clerical_decision_error" },
    { action: "withdraw_review", correctedDecision: null, reasonCode: "reviewer_requested_withdrawal" },
    { action: "correct_decision", correctedDecision: "reject", reasonCode: "new_private_evidence" },
    { action: "correct_decision", correctedDecision: "accept_for_blueprint_revision", reasonCode: "new_private_evidence" },
  ];
  for (let index = 0; index < adapter.PORTABLE_REVIEW_CORRECTION_MAX_RECORDS; index += 1) {
    const step = cycle[index % cycle.length];
    const correction = await adapter.appendPortableRunbackReviewCorrection(verified, fullReviews, {
      reviewerLabel: `Correction ${String(index + 1).padStart(2, "0")}`,
      targetReviewDigest: fullReviews[0].reviewDigest,
      ...step,
    }, fullCorrections);
    fullCorrections.push(correction);
  }
  const fullExchange = await adapter.createPortableRunbackReviewCorrectionExchange(portable.serialized, fullReviews, fullCorrections);
  const fullImport = await adapter.verifyPortableRunbackReviewCorrectionExchange(fullExchange.serialized);
  check(fullReviews.length === 64 && fullCorrections.length === 64, "full packet reaches both 64-record contracts");
  check(fullExchange.serialized.length <= adapter.PORTABLE_REVIEW_CORRECTION_EXCHANGE_MAX_LENGTH, "full review and correction history fits correction exchange cap");
  check(fullImport.journal.reviewCount === 64 && fullImport.correctionJournal.correctionCount === 64, "full 64 plus 64 history independently verifies");
  check(fullImport.correctionJournal.latestCorrectionDigest === fullCorrections[63].correctionDigest, "full correction head independently verifies");
  check(fullImport.correctionJournal.effectiveReviews[0].effectiveDecision === "accept_for_blueprint_revision", "full supersession cycle derives latest private decision");

  process.stdout.write(JSON.stringify({ status: "PASS", checks: checks.length, fullPacketLength: fullExchange.serialized.length }));
}

main().catch((error) => { console.error(error.stack || error.message); process.exit(1); });
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
    require(result.returncode == 0, f"portable review correction check failed: {result.stderr.strip()}")
    payload = json.loads(result.stdout)
    require(payload.get("status") == "PASS", "portable review correction check did not report PASS")
    require(payload.get("checks", 0) >= 100, "portable review correction coverage unexpectedly shrank")
    require(payload.get("fullPacketLength", 0) < 524288, "full correction exchange exceeds declared size cap")
    print(
        "BuilderWars immutable private review corrections: "
        f"PASS ({payload['checks']} checks; 64-review/64-correction packet {payload['fullPacketLength']} bytes)"
    )
    print("immutable targets / global and per-target supersession chains / fresh-recipient packet / no authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
