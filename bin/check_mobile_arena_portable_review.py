#!/usr/bin/env python3
"""Adversarial checks for private append-only portable proposal reviews."""

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
    require(node is not None, "Node.js is required to exercise portable review verification")

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
async function reseal(record) {
  const value = copy(record);
  delete value.reviewDigest;
  record.reviewDigest = await digest(canonical(value));
  return record;
}
async function rejectsAppend(input, expected, existing = [], verifiedInput = verified) {
  let message = "";
  try { await adapter.appendPortableRunbackReview(verifiedInput, input, existing); } catch (error) { message = error.message; }
  check(message.includes(expected), `append rejects ${expected}`);
}
async function rejectsJournal(mutator, expected, journal = baseJournal, verifiedInput = verified, resealIndex = null) {
  const value = copy(journal);
  mutator(value);
  if (Number.isInteger(resealIndex) && value[resealIndex]) await reseal(value[resealIndex]);
  let message = "";
  try { await adapter.verifyPortableRunbackReviewJournal(value, verifiedInput); } catch (error) { message = error.message; }
  check(message.includes(expected), `journal rejects ${expected}`);
}

let verified;
let accepted;
let deferred;
let rejected;
let baseJournal;

async function main() {
  const view = await adapter.adaptArenaReadModel(model, demo);
  const proof = view.proofReceipts.find((candidate) => candidate.moveSourceCounts.model > 0);
  const learning = adapter.buildReceiptLearningAction(proof, "verified_corpus");
  const blueprint = {
    agentName: "Review Student",
    baseModel: "Arena Small",
    harnessStyle: "Human review checkpoints",
    strictValidation: true,
    fallbackDisclosure: true,
    humanCheckpoints: false,
    localOnly: true,
  };
  const proposal = adapter.buildRunbackProposal(learning, blueprint, "require_human_checkpoints", "verified_corpus");
  const portable = await adapter.createPortableRunbackEnvelope(proposal);
  verified = await adapter.verifyPortableRunbackEnvelope(portable.serialized);

  check(adapter.PORTABLE_REVIEW_SCHEMA === "builderwars.mobile-runback-review.v1", "exports review schema");
  check(adapter.PORTABLE_REVIEW_MAX_RECORDS === 64, "exports review journal cap");
  check(Object.keys(adapter.PORTABLE_REVIEW_REASONS).join(",") === "accept_for_blueprint_revision,defer,reject", "exports exact decisions");
  check(adapter.PORTABLE_REVIEW_REASONS.accept_for_blueprint_revision.join(",") === "receipt_guided_guard_change", "accept reason is bounded");
  check(adapter.PORTABLE_REVIEW_REASONS.defer.length === 2 && adapter.PORTABLE_REVIEW_REASONS.reject.length === 2, "defer and reject reasons are bounded");

  accepted = await adapter.appendPortableRunbackReview(verified, {
    reviewerLabel: "Local reviewer A",
    decision: "accept_for_blueprint_revision",
    reasonCode: "receipt_guided_guard_change",
  }, []);
  const acceptedAgain = await adapter.appendPortableRunbackReview(copy(verified), {
    reviewerLabel: "Local reviewer A",
    decision: "accept_for_blueprint_revision",
    reasonCode: "receipt_guided_guard_change",
  }, []);
  check(accepted.schemaVersion === adapter.PORTABLE_REVIEW_SCHEMA && accepted.reviewVersion === 1, "accept record is versioned");
  check(accepted.sequence === 1 && accepted.previousReviewDigest === null, "first review starts the chain");
  check(accepted.reviewStatus === "private_local_review", "review remains private local state");
  check(accepted.decision === "accept_for_blueprint_revision", "accept decision is exact");
  check(accepted.reasonCode === "receipt_guided_guard_change", "accept reason is exact");
  check(accepted.reviewer.label === "Local reviewer A", "reviewer label is preserved");
  check(accepted.reviewer.identityAttested === false && accepted.reviewer.localOnly === true, "reviewer remains unattested and local");
  check(accepted.proposalBinding.envelopeDigest === verified.payloadDigest, "review binds verified envelope digest");
  check(accepted.proposalBinding.proposalKey === proposal.proposalKey, "review binds proposal key");
  check(accepted.proposalBinding.parentReceiptId === proposal.parentReceipt.receiptId, "review binds parent receipt");
  check(accepted.proposalBinding.challengeId === proposal.runbackLineage.challengeId, "review binds challenge");
  check(accepted.proposalBinding.runbackFixtureId === proposal.runbackLineage.fixtureId, "review binds runback fixture");
  check(accepted.blueprintRevision.status === "proposed_uncommitted_revision", "accept creates only a proposed revision");
  check(accepted.blueprintRevision.parentProposalKey === proposal.proposalKey, "revision preserves proposal parent");
  check(accepted.blueprintRevision.acceptedDelta.id === proposal.blueprintDelta.id, "revision preserves exact delta");
  check(accepted.blueprintRevision.localOnly === true && accepted.blueprintRevision.committed === false, "revision remains local and uncommitted");
  check(accepted.blueprintRevision.revisionKey.includes(verified.payloadDigest), "revision key binds envelope digest");
  check(accepted.blockers.length === 7 && accepted.blockers[0] === "reviewer_identity_unattested", "review preserves ordered blockers");
  check(accepted.blockers.includes("explicit_rules_digest_not_bound") && accepted.blockers.includes("qualification_not_run"), "rules and qualification remain blocked");
  check(accepted.blockers.includes("registry_not_requested") && accepted.blockers.includes("publication_not_requested"), "registry and publication remain unrequested");
  check(Object.values(accepted.attestations).every((value) => value === false), "all review attestations remain false");
  check(Object.keys(accepted.attestations).length === 11, "review covers all authority attestations");
  check(accepted.boundary.includes("not a signature or identity claim"), "review refuses authenticity claim");
  check(accepted.boundary.includes("cannot bind missing rules, qualify, execute, attest, register, rank, publish, or spend"), "review refuses authority claim");
  check(/^[0-9a-f]{64}$/.test(accepted.reviewDigest), "review carries lowercase SHA-256 digest");
  check(accepted.reviewDigest === acceptedAgain.reviewDigest, "same first review seals deterministically");
  const acceptedPayload = copy(accepted); delete acceptedPayload.reviewDigest;
  check(accepted.reviewDigest === await digest(canonical(acceptedPayload)), "independent digest binds canonical record");

  const acceptedBeforeAppend = canonical(accepted);
  deferred = await adapter.appendPortableRunbackReview(verified, {
    reviewerLabel: "Local reviewer B",
    decision: "defer",
    reasonCode: "needs_explicit_rules_binding",
  }, [accepted]);
  check(canonical(accepted) === acceptedBeforeAppend, "append does not mutate prior review");
  check(deferred.sequence === 2 && deferred.previousReviewDigest === accepted.reviewDigest, "defer appends to exact prior digest");
  check(deferred.blueprintRevision === null, "defer cannot create blueprint revision");
  rejected = await adapter.appendPortableRunbackReview(verified, {
    reviewerLabel: "Local reviewer C",
    decision: "reject",
    reasonCode: "unsafe_or_out_of_scope",
  }, [accepted, deferred]);
  check(rejected.sequence === 3 && rejected.previousReviewDigest === deferred.reviewDigest, "reject appends to exact prior digest");
  check(rejected.blueprintRevision === null, "reject cannot create blueprint revision");
  baseJournal = [accepted, deferred, rejected];

  const journal = await adapter.verifyPortableRunbackReviewJournal(baseJournal, verified);
  check(journal.schemaVersion === adapter.PORTABLE_REVIEW_SCHEMA, "journal result is versioned");
  check(journal.verificationStatus === "verified_private_local_review_journal", "journal remains private local verification");
  check(journal.envelopeDigest === verified.payloadDigest, "journal binds one verified envelope");
  check(journal.reviewCount === 3 && journal.latestReviewDigest === rejected.reviewDigest, "journal reports exact append head");
  check(journal.reviews.length === 3 && journal.reviews[0].reviewDigest === accepted.reviewDigest, "journal preserves records");
  check(journal.boundary === accepted.boundary, "journal repeats authority boundary");
  const empty = await adapter.verifyPortableRunbackReviewJournal([], verified);
  check(empty.reviewCount === 0 && empty.latestReviewDigest === null, "empty journal verifies without inventing review");

  for (const [decision, reasonCode] of [
    ["accept_for_blueprint_revision", "receipt_guided_guard_change"],
    ["defer", "needs_explicit_rules_binding"],
    ["defer", "insufficient_public_evidence"],
    ["reject", "duplicate_or_stale_proposal"],
    ["reject", "unsafe_or_out_of_scope"],
  ]) {
    const value = await adapter.appendPortableRunbackReview(verified, { reviewerLabel: "Reason matrix", decision, reasonCode }, []);
    check(value.decision === decision && value.reasonCode === reasonCode, `accepts exact ${decision}/${reasonCode}`);
    check((decision === "accept_for_blueprint_revision") === Boolean(value.blueprintRevision), `${decision} revision behavior is exact`);
  }

  await rejectsAppend({ reviewerLabel: "", decision: "reject", reasonCode: "unsafe_or_out_of_scope" }, "reviewer label drift");
  await rejectsAppend({ reviewerLabel: " local", decision: "reject", reasonCode: "unsafe_or_out_of_scope" }, "reviewer label drift");
  await rejectsAppend({ reviewerLabel: "local ", decision: "reject", reasonCode: "unsafe_or_out_of_scope" }, "reviewer label drift");
  await rejectsAppend({ reviewerLabel: "x".repeat(37), decision: "reject", reasonCode: "unsafe_or_out_of_scope" }, "reviewer label drift");
  await rejectsAppend({ reviewerLabel: "local", decision: "approve", reasonCode: "receipt_guided_guard_change" }, "unknown decision");
  await rejectsAppend({ reviewerLabel: "local", decision: "defer", reasonCode: "receipt_guided_guard_change" }, "decision reason drift");
  await rejectsAppend({ reviewerLabel: "local", decision: "reject", reasonCode: "insufficient_public_evidence" }, "decision reason drift");
  await rejectsAppend({ reviewerLabel: "local", decision: "accept_for_blueprint_revision", reasonCode: "unsafe_or_out_of_scope" }, "decision reason drift");
  await rejectsAppend({ reviewerLabel: "local", decision: "reject", reasonCode: "unsafe_or_out_of_scope", extra: true }, "review input fields drift");
  await rejectsAppend({ reviewerLabel: "local", decision: "reject" }, "review input fields drift");
  await rejectsAppend(null, "review input must be an object");

  for (const [field, replacement, expected] of [
    ["schemaVersion", "drift", "verified schema drift"],
    ["verificationStatus", "trusted", "proposal was not independently verified"],
    ["payloadDigest", "bad", "envelope digest missing"],
    ["boundary", "trusted", "verification boundary drift"],
  ]) {
    const drift = copy(verified); drift[field] = replacement;
    await rejectsAppend({ reviewerLabel: "local", decision: "reject", reasonCode: "unsafe_or_out_of_scope" }, expected, [], drift);
  }
  const verifiedExtra = copy(verified); verifiedExtra.extra = true;
  await rejectsAppend({ reviewerLabel: "local", decision: "reject", reasonCode: "unsafe_or_out_of_scope" }, "verified portable result fields drift", [], verifiedExtra);
  const verifiedDigestDrift = copy(verified); verifiedDigestDrift.payloadDigest = "0".repeat(64);
  await rejectsAppend({ reviewerLabel: "local", decision: "reject", reasonCode: "unsafe_or_out_of_scope" }, "verified payload digest mismatch", [], verifiedDigestDrift);
  const verifiedProposalDrift = copy(verified); verifiedProposalDrift.proposal.blueprint.agentName = "Different";
  await rejectsAppend({ reviewerLabel: "local", decision: "reject", reasonCode: "unsafe_or_out_of_scope" }, "proposal key drift", [], verifiedProposalDrift);

  await rejectsJournal((value) => { value[0].extra = true; }, "portable review fields drift");
  await rejectsJournal((value) => { value[0].schemaVersion = "v2"; }, "schema drift");
  await rejectsJournal((value) => { value[0].reviewVersion = 2; }, "schema drift");
  await rejectsJournal((value) => { value[0].sequence = 2; }, "sequence drift");
  await rejectsJournal((value) => { value[0].reviewStatus = "public"; }, "private status drift");
  await rejectsJournal((value) => { value[0].decision = "approve"; }, "unknown decision");
  await rejectsJournal((value) => { value[0].reasonCode = "unsafe_or_out_of_scope"; }, "decision reason drift");
  await rejectsJournal((value) => { value[0].reviewer.extra = true; }, "reviewer fields drift");
  await rejectsJournal((value) => { value[0].reviewer.label = ""; }, "reviewer label drift");
  await rejectsJournal((value) => { value[0].reviewer.label = " local"; }, "reviewer label drift");
  await rejectsJournal((value) => { value[0].reviewer.label = "x".repeat(37); }, "reviewer label drift");
  await rejectsJournal((value) => { value[0].reviewer.identityAttested = true; }, "reviewer boundary drift");
  await rejectsJournal((value) => { value[0].reviewer.localOnly = false; }, "reviewer boundary drift");
  await rejectsJournal((value) => { value[0].proposalBinding.extra = true; }, "review proposal binding fields drift");
  for (const field of ["envelopeDigest", "proposalKey", "parentReceiptId", "challengeId", "runbackFixtureId"]) {
    await rejectsJournal((value) => { value[0].proposalBinding[field] = "drift"; }, `${field} drift`);
  }
  await rejectsJournal((value) => { value[0].previousReviewDigest = "0".repeat(64); }, "append-only chain drift");
  await rejectsJournal((value) => { value[1].previousReviewDigest = "0".repeat(64); }, "append-only chain drift");
  await rejectsJournal((value) => { [value[0], value[1]] = [value[1], value[0]]; }, "sequence drift");
  await rejectsJournal((value) => { value.pop(); value.push(copy(value[0])); }, "sequence drift");

  await rejectsJournal((value) => { value[0].blueprintRevision.extra = true; }, "blueprint revision fields drift");
  for (const field of ["status", "revisionKey", "parentProposalKey", "agentName", "declaredBase", "harnessStyle", "acceptedDelta", "localOnly", "committed"]) {
    await rejectsJournal((value) => {
      if (field === "acceptedDelta") value[0].blueprintRevision.acceptedDelta.id = "drift";
      else if (field === "localOnly") value[0].blueprintRevision[field] = false;
      else if (field === "committed") value[0].blueprintRevision[field] = true;
      else value[0].blueprintRevision[field] = "drift";
    }, "proposed blueprint revision drift");
  }
  await rejectsJournal((value) => { value[1].blueprintRevision = copy(value[0].blueprintRevision); }, "non-accept decision created a blueprint revision");
  await rejectsJournal((value) => { value[2].blueprintRevision = copy(value[0].blueprintRevision); }, "non-accept decision created a blueprint revision");
  await rejectsJournal((value) => { value[0].blueprintRevision = null; }, "blueprint revision must be an object");

  await rejectsJournal((value) => { value[0].blockers.pop(); }, "blockers drift");
  await rejectsJournal((value) => { value[0].blockers.reverse(); }, "blockers drift");
  await rejectsJournal((value) => { value[0].blockers.push("execution_enabled"); }, "blockers drift");
  await rejectsJournal((value) => { value[0].attestations.extra = false; }, "review attestations fields drift");
  for (const field of Object.keys(accepted.attestations)) {
    await rejectsJournal((value) => { value[0].attestations[field] = true; }, "attestation must remain false");
  }
  await rejectsJournal((value) => { value[0].boundary = "trusted"; }, "boundary drift");
  await rejectsJournal((value) => { value[0].reviewDigest = "bad"; }, "review digest missing");
  await rejectsJournal((value) => { value[0].reviewDigest = "0".repeat(64); }, "review digest mismatch");
  await rejectsJournal((value) => { value[0].reviewer.label = "Changed"; }, "review digest mismatch", baseJournal, verified, null);
  await rejectsJournal((value) => { value[1].reviewer.label = "Changed"; }, "review digest mismatch", baseJournal, verified, null);

  const foreignProposal = adapter.buildRunbackProposal(learning, { ...blueprint, agentName: "Foreign student" }, "require_human_checkpoints", "verified_corpus");
  const foreignPortable = await adapter.createPortableRunbackEnvelope(foreignProposal);
  const foreignVerified = await adapter.verifyPortableRunbackEnvelope(foreignPortable.serialized);
  let foreignMessage = "";
  try { await adapter.verifyPortableRunbackReviewJournal(baseJournal, foreignVerified); } catch (error) { foreignMessage = error.message; }
  check(foreignMessage.includes("envelopeDigest drift"), "journal refuses a different verified proposal");

  const tooMany = Array.from({ length: 65 }, () => copy(accepted));
  let lengthMessage = "";
  try { await adapter.verifyPortableRunbackReviewJournal(tooMany, verified); } catch (error) { lengthMessage = error.message; }
  check(lengthMessage.includes("journal length rejected"), "journal refuses more than 64 records");
  const deep = copy(baseJournal);
  deep[0].extra = {};
  let cursor = deep[0].extra;
  for (let index = 0; index < 34; index += 1) { cursor.next = {}; cursor = cursor.next; }
  let deepMessage = "";
  try { await adapter.verifyPortableRunbackReviewJournal(deep, verified); } catch (error) { deepMessage = error.message; }
  check(deepMessage.includes("nesting limit exceeded"), "journal rejects excessive nesting");
  const dangerous = JSON.parse(canonical(baseJournal).replace('"reviewer":{', '"reviewer":{"constructor":{"polluted":true},'));
  let dangerousMessage = "";
  try { await adapter.verifyPortableRunbackReviewJournal(dangerous, verified); } catch (error) { dangerousMessage = error.message; }
  check(dangerousMessage.includes("prohibited key"), "journal rejects prototype pollution keys");

  process.stdout.write(JSON.stringify({ status: "PASS", checks: checks.length }));
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
        timeout=45,
        check=False,
    )
    require(result.returncode == 0, f"portable review check failed: {result.stderr.strip()}")
    payload = json.loads(result.stdout)
    require(payload.get("status") == "PASS", "portable review check did not report PASS")
    require(payload.get("checks", 0) >= 110, "portable review coverage unexpectedly shrank")
    print(f"BuilderWars private portable review journal: PASS ({payload['checks']} checks)")
    print("verified envelope binding / append-only SHA-256 chain / proposed-uncommitted revision / no authority claim")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
