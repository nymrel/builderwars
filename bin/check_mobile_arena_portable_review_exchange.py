#!/usr/bin/env python3
"""Adversarial checks for canonical private-review journal exchange packets."""

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
    require(node is not None, "Node.js is required to exercise portable review exchange verification")

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
  try { await adapter.verifyPortableRunbackReviewExchange(serialized); } catch (error) { message = error.message; }
  check(message.includes(expected), `exchange rejects ${expected}`);
}
async function rejectsPacket(mutator, expected, { reseal = false, source = packet } = {}) {
  const value = copy(source);
  await mutator(value);
  if (reseal) await resealPacket(value);
  await rejectsSerialized(canonical(value), expected);
}

let packet;

async function main() {
  const view = await adapter.adaptArenaReadModel(model, demo);
  const proof = view.proofReceipts.find((candidate) => candidate.moveSourceCounts.model > 0);
  const learning = adapter.buildReceiptLearningAction(proof, "verified_corpus");
  const blueprint = {
    agentName: "Exchange Student",
    baseModel: "Arena Reason",
    harnessStyle: "Human review checkpoints",
    strictValidation: true,
    fallbackDisclosure: true,
    humanCheckpoints: false,
    localOnly: true,
  };
  const proposal = adapter.buildRunbackProposal(learning, blueprint, "require_human_checkpoints", "verified_corpus");
  const portable = await adapter.createPortableRunbackEnvelope(proposal);
  const verified = await adapter.verifyPortableRunbackEnvelope(portable.serialized);
  const accepted = await adapter.appendPortableRunbackReview(verified, {
    reviewerLabel: "Sender A",
    decision: "accept_for_blueprint_revision",
    reasonCode: "receipt_guided_guard_change",
  }, []);
  const deferred = await adapter.appendPortableRunbackReview(verified, {
    reviewerLabel: "Sender B",
    decision: "defer",
    reasonCode: "needs_explicit_rules_binding",
  }, [accepted]);
  const rejected = await adapter.appendPortableRunbackReview(verified, {
    reviewerLabel: "Sender C",
    decision: "reject",
    reasonCode: "unsafe_or_out_of_scope",
  }, [accepted, deferred]);
  const journal = [accepted, deferred, rejected];

  check(adapter.PORTABLE_REVIEW_EXCHANGE_SCHEMA === "builderwars.mobile-runback-review-exchange.v1", "exports review exchange schema");
  check(adapter.PORTABLE_REVIEW_EXCHANGE_MAX_LENGTH === 262144, "exports review exchange size cap");
  check(typeof adapter.createPortableRunbackReviewExchange === "function", "exports review exchange creator");
  check(typeof adapter.verifyPortableRunbackReviewExchange === "function", "exports review exchange verifier");

  const exchange = await adapter.createPortableRunbackReviewExchange(portable.serialized, journal);
  const exchangeAgain = await adapter.createPortableRunbackReviewExchange(portable.serialized, copy(journal));
  packet = exchange.packet;
  check(packet.schemaVersion === adapter.PORTABLE_REVIEW_EXCHANGE_SCHEMA && packet.exchangeVersion === 1, "exchange is exactly versioned");
  check(Object.keys(packet).sort().join(",") === "boundary,exchangeVersion,integrity,payload,schemaVersion", "exchange outer fields are exact");
  check(Object.keys(packet.payload).sort().join(",") === "proposalEnvelope,reviews", "exchange payload fields are exact");
  check(Object.keys(packet.integrity).sort().join(",") === "algorithm,payloadDigest,proposalPayloadDigest,reviewHeadDigest", "exchange integrity fields are exact");
  check(packet.integrity.algorithm === "sha256", "exchange algorithm is exact");
  check(packet.integrity.proposalPayloadDigest === verified.payloadDigest, "exchange binds proposal payload digest");
  check(packet.integrity.reviewHeadDigest === rejected.reviewDigest, "exchange binds review head digest");
  check(packet.payload.reviews.length === 3, "exchange carries exact review count");
  check(packet.payload.reviews[0].reviewDigest === accepted.reviewDigest && packet.payload.reviews[2].reviewDigest === rejected.reviewDigest, "exchange preserves exact journal records");
  check(canonical(packet.payload.proposalEnvelope) === portable.serialized, "exchange preserves exact proposal envelope");
  check(exchange.serialized === canonical(packet), "exchange export is canonical JSON");
  check(exchange.serialized === exchangeAgain.serialized, "same proposal and journal export deterministically");
  check(exchange.serialized.length <= adapter.PORTABLE_REVIEW_EXCHANGE_MAX_LENGTH, "exchange stays inside explicit size cap");
  check(/^[0-9a-f]{64}$/.test(packet.integrity.payloadDigest), "exchange carries lowercase SHA-256 packet digest");
  check(packet.integrity.payloadDigest === await digest(canonical(packet.payload)), "independent packet digest agrees");
  check(packet.boundary.includes("independent local inspection"), "exchange states independent inspection boundary");
  check(packet.boundary.includes("not signatures or identity claims"), "exchange refuses signature and identity claims");
  check(packet.boundary.includes("cannot apply a blueprint"), "exchange refuses blueprint application");
  check(packet.boundary.includes("call a provider"), "exchange refuses provider calls");

  const imported = await adapter.verifyPortableRunbackReviewExchange(exchange.serialized);
  check(imported.schemaVersion === adapter.PORTABLE_REVIEW_EXCHANGE_SCHEMA, "independent import reports exchange schema");
  check(imported.verificationStatus === "verified_private_local_review_exchange", "independent import remains private local verification");
  check(imported.packetDigest === packet.integrity.payloadDigest, "independent import recomputes packet digest");
  check(imported.proposalSerialized === portable.serialized, "independent import reconstructs canonical proposal envelope");
  check(imported.proposalVerification.payloadDigest === verified.payloadDigest, "independent import reverifies proposal digest");
  check(imported.proposalVerification.verificationStatus === "verified_local_unplayed_proposal", "independent import preserves still-unplayed status");
  check(imported.journal.reviewCount === 3 && imported.journal.latestReviewDigest === rejected.reviewDigest, "independent import reverifies full review head");
  check(imported.journal.reviews[1].previousReviewDigest === accepted.reviewDigest, "independent import reverifies append link");
  check(imported.journal.reviews[0].blueprintRevision.committed === false, "imported acceptance remains uncommitted");
  check(imported.journal.reviews[1].blueprintRevision === null && imported.journal.reviews[2].blueprintRevision === null, "imported non-accept reviews create no revision");
  check(Object.values(imported.journal.reviews[0].attestations).every((value) => value === false), "imported authority attestations remain false");
  check(imported.boundary === packet.boundary, "independent import preserves exchange boundary");

  const emptyExchange = await adapter.createPortableRunbackReviewExchange(portable.serialized, []);
  const emptyImport = await adapter.verifyPortableRunbackReviewExchange(emptyExchange.serialized);
  check(emptyExchange.packet.payload.reviews.length === 0, "empty review journal exports without invented records");
  check(emptyExchange.packet.integrity.reviewHeadDigest === null, "empty review journal binds null head");
  check(emptyImport.journal.reviewCount === 0 && emptyImport.journal.latestReviewDigest === null, "empty review journal imports exactly");
  check(emptyImport.proposalVerification.payloadDigest === verified.payloadDigest, "empty journal still reverifies proposal");

  await rejectsSerialized("", "input length rejected");
  await rejectsSerialized(" ".repeat(adapter.PORTABLE_REVIEW_EXCHANGE_MAX_LENGTH + 1), "input length rejected");
  await rejectsSerialized("{", "invalid JSON");
  await rejectsSerialized(JSON.stringify(packet, null, 2), "must use canonical JSON");
  await rejectsSerialized(`${exchange.serialized}\n`, "must use canonical JSON");
  await rejectsSerialized(exchange.serialized.replace('"exchangeVersion":1', '"exchangeVersion":1,"exchangeVersion":1'), "must use canonical JSON");

  await rejectsPacket(async (value) => { value.extra = true; }, "portable review exchange fields drift");
  await rejectsPacket(async (value) => { delete value.boundary; }, "portable review exchange fields drift");
  await rejectsPacket(async (value) => { value.schemaVersion = "v2"; }, "schema drift");
  await rejectsPacket(async (value) => { value.exchangeVersion = 2; }, "schema drift");
  await rejectsPacket(async (value) => { value.boundary = "trusted"; }, "boundary drift");
  await rejectsPacket(async (value) => { value.payload.extra = true; }, "portable review exchange payload fields drift");
  await rejectsPacket(async (value) => { delete value.payload.reviews; }, "portable review exchange payload fields drift");
  await rejectsPacket(async (value) => { value.integrity.extra = true; }, "portable review exchange integrity fields drift");
  await rejectsPacket(async (value) => { delete value.integrity.reviewHeadDigest; }, "portable review exchange integrity fields drift");
  await rejectsPacket(async (value) => { value.integrity.algorithm = "sha512"; }, "integrity algorithm drift");
  await rejectsPacket(async (value) => { value.integrity.payloadDigest = "bad"; }, "integrity digest drift");
  await rejectsPacket(async (value) => { value.integrity.proposalPayloadDigest = "bad"; }, "integrity digest drift");
  await rejectsPacket(async (value) => { value.integrity.reviewHeadDigest = "bad"; }, "review head digest drift");
  await rejectsPacket(async (value) => { value.integrity.payloadDigest = value.integrity.payloadDigest.toUpperCase(); }, "integrity digest drift");
  await rejectsPacket(async (value) => { value.integrity.proposalPayloadDigest = "0".repeat(64); }, "proposal digest binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.reviewHeadDigest = "0".repeat(64); }, "review head binding mismatch");
  await rejectsPacket(async (value) => { value.integrity.payloadDigest = "0".repeat(64); }, "payload digest mismatch");

  await rejectsPacket(async (value) => { value.payload.proposalEnvelope.extra = true; }, "envelope fields drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.proposalEnvelope.schemaVersion = "v2"; }, "envelope schema drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.proposalEnvelope.boundary = "trusted"; }, "envelope boundary drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.proposalEnvelope.integrity.payloadDigest = "0".repeat(64); }, "payload digest mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.proposalEnvelope.payload.runbackStatus = "played"; }, "proposal is not unplayed", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.proposalEnvelope.payload.qualificationStatus = "passed"; }, "qualification status drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.proposalEnvelope.payload.executionStatus = "enabled"; }, "execution status drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.proposalEnvelope.payload.publicationStatus = "published"; }, "publication status drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.proposalEnvelope.payload.attestations.provider = true; }, "attestation must remain false", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.proposalEnvelope.payload.rulesBinding.rulesDigest = "0".repeat(64); }, "rules blocker drift", { reseal: true });

  await rejectsPacket(async (value) => { value.payload.reviews = null; }, "journal length rejected", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.reviews[0].extra = true; }, "portable review fields drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.reviews[0].reviewStatus = "public"; }, "private status drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.reviews[0].reviewer.identityAttested = true; }, "reviewer boundary drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.reviews[0].attestations.execution = true; }, "attestation must remain false", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.reviews[0].blueprintRevision.committed = true; }, "proposed blueprint revision drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.reviews[1].blueprintRevision = copy(value.payload.reviews[0].blueprintRevision); }, "non-accept decision created a blueprint revision", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.reviews[1].previousReviewDigest = "0".repeat(64); }, "append-only chain drift", { reseal: true });
  await rejectsPacket(async (value) => { [value.payload.reviews[0], value.payload.reviews[1]] = [value.payload.reviews[1], value.payload.reviews[0]]; }, "sequence drift", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.reviews[0].reviewDigest = "0".repeat(64); }, "review digest mismatch", { reseal: true });
  await rejectsPacket(async (value) => { value.payload.reviews.pop(); }, "review head binding mismatch", { reseal: true });

  const foreignProposal = adapter.buildRunbackProposal(learning, { ...blueprint, agentName: "Foreign Student" }, "require_human_checkpoints", "verified_corpus");
  const foreignPortable = await adapter.createPortableRunbackEnvelope(foreignProposal);
  const foreignVerified = await adapter.verifyPortableRunbackEnvelope(foreignPortable.serialized);
  await rejectsPacket(async (value) => {
    value.payload.proposalEnvelope = foreignPortable.envelope;
    value.integrity.proposalPayloadDigest = foreignVerified.payloadDigest;
  }, "envelopeDigest drift", { reseal: true });

  await rejectsPacket(async (value) => { value.payload.proposalEnvelope.payload.__proto_probe__ = { constructor: { polluted: true } }; }, "prohibited key", { reseal: false });
  const dangerous = JSON.parse(exchange.serialized.replace('"payload":{', '"payload":{"constructor":{"polluted":true},'));
  await rejectsSerialized(canonical(dangerous), "prohibited key");
  const deep = copy(packet);
  deep.extra = {};
  let cursor = deep.extra;
  for (let index = 0; index < 34; index += 1) { cursor.next = {}; cursor = cursor.next; }
  await rejectsSerialized(canonical(deep), "nesting limit exceeded");
  const tooMany = copy(packet);
  tooMany.payload.reviews = Array.from({ length: 65 }, () => copy(accepted));
  await resealPacket(tooMany);
  await rejectsSerialized(canonical(tooMany), "journal length rejected");

  const fullJournal = [];
  for (let index = 0; index < adapter.PORTABLE_REVIEW_MAX_RECORDS; index += 1) {
    const review = await adapter.appendPortableRunbackReview(verified, {
      reviewerLabel: `Reviewer ${String(index + 1).padStart(2, "0")}`,
      decision: "reject",
      reasonCode: "duplicate_or_stale_proposal",
    }, fullJournal);
    fullJournal.push(review);
  }
  const fullExchange = await adapter.createPortableRunbackReviewExchange(portable.serialized, fullJournal);
  const fullImport = await adapter.verifyPortableRunbackReviewExchange(fullExchange.serialized);
  check(fullJournal.length === 64, "full journal reaches existing 64-record contract");
  check(fullExchange.serialized.length <= adapter.PORTABLE_REVIEW_EXCHANGE_MAX_LENGTH, "full 64-record journal fits exchange cap");
  check(fullImport.journal.reviewCount === 64, "full 64-record journal independently verifies");
  check(fullImport.journal.latestReviewDigest === fullJournal[63].reviewDigest, "full journal head independently verifies");

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
        timeout=90,
        check=False,
    )
    require(result.returncode == 0, f"portable review exchange check failed: {result.stderr.strip()}")
    payload = json.loads(result.stdout)
    require(payload.get("status") == "PASS", "portable review exchange check did not report PASS")
    require(payload.get("checks", 0) >= 80, "portable review exchange coverage unexpectedly shrank")
    require(payload.get("fullPacketLength", 0) < 262144, "full review exchange exceeds declared size cap")
    print(f"BuilderWars portable private review exchange: PASS ({payload['checks']} checks; 64-record packet {payload['fullPacketLength']} bytes)")
    print("fresh-recipient proposal reverify / append-only review-chain reverify / canonical packet digest / inspection only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
