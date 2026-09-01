#!/usr/bin/env python3
"""Exercise the mobile Arena read adapter and its fail-closed fallback policy."""

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
    require(node is not None, "Node.js is required to exercise the Arena read adapter")

    script = r"""
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const adapter = require(path.join(process.cwd(), "data-adapter.js"));
const demo = JSON.parse(fs.readFileSync(path.join(process.cwd(), "data", "demo-state.json"), "utf8"));
const model = JSON.parse(fs.readFileSync(path.join(process.cwd(), "data", "arena-read-model.v1.json"), "utf8"));
const checks = [];
function check(predicate, message) {
  if (!predicate) throw new Error(message);
  checks.push(message);
}
function copy(value) { return JSON.parse(JSON.stringify(value)); }
function canonicalJSON(value) {
  if (value === null || typeof value === "boolean" || typeof value === "string" || typeof value === "number") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map((item) => canonicalJSON(item)).join(",")}]`;
  return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJSON(value[key])}`).join(",")}}`;
}
function digestModel(value) {
  const payload = Object.fromEntries(Object.entries(value).filter(([key]) => key !== "readModelDigest"));
  return crypto.createHash("sha256").update(canonicalJSON(payload), "utf8").digest("hex");
}
async function rejects(mutator, expected) {
  const changed = copy(model);
  mutator(changed);
  let message = "";
  try { await adapter.adaptArenaReadModel(changed, demo); } catch (error) { message = error.message; }
  check(message.includes(expected), `rejects ${expected}`);
}
function response(body, ok = true) {
  return { ok, async json() { return copy(body); } };
}

(async () => {
  adapter.validateDemoFixture(demo);
  adapter.validateArenaReadModel(model);
  checks.push("validates bounded inputs");
  await adapter.verifyArenaReadModelIntegrity(model);
  check(adapter.READ_MODEL_DIGEST_PIN === model.readModelDigest, "pins the reviewed read-model digest in executable source");

  const view = await adapter.adaptArenaReadModel(model, demo);
  check(view.schemaVersion === adapter.VIEW_SCHEMA, "projects versioned view schema");
  check(view.sourceMode === "verified_corpus", "selects verified corpus");
  check(view.demoOnly === false, "does not relabel corpus as demo");
  check(view.proofReceipts.length === 8, "projects eight reviewed receipts");
  check(view.tape.length === view.proofReceipts.length, "tape is receipt-backed");
  check(view.channels.every((channel) => channel.viewers === null), "does not invent viewers");
  check(view.leaderboard.every((row) => row.record.includes("not ranked")), "does not invent ranking");
  check(view.quickMatches.length === 3 && view.quickMatches.every((fixture) => fixture.enabled === false), "keeps proposed fixtures inactive");
  check(view.quickMatches.every((fixture) => fixture.previewAllowed === true && fixture.actionLabel === "Preview"), "projects proposed fixtures as previews");
  check(view.quickMatches.every((fixture) => fixture.resourceClass === adapter.PREVIEW_RESOURCE_CLASS), "binds no-compute preview resource class");
  check(view.rivalries.length === 3, "projects three verified rivalries");
  check(view.rivalries.every((rivalry) => view.proofReceipts.some((proof) => proof.receiptId === rivalry.latestReceiptId)), "rivalry receipt links resolve");
  check(view.rivalries.every((rivalry) => rivalry.runbackStatus === "unplayed_challenge"), "rivalry runbacks remain inactive");
  check(view.account.creditsRemaining === 0, "does not invent live credits");
  check(view.featured.proof.replayVerdict === "PASS", "preserves replay verdict");
  check(view.featured.proof.receiptId.length === 64, "binds featured proof receipt");
  check(view.truthBoundary.live === false && view.truthBoundary.hosted === false, "preserves non-live boundary");
  check(view.featured.proof.modelAttested === false && view.featured.proof.providerAttested === false, "preserves unattested boundary");
  check(view.proofReceipts.every((proof) => proof.runback?.parentReceiptId === proof.receiptId), "projects exact proof-to-runback lineage");
  check(view.proofReceipts.every((proof) => proof.runback?.status === "unplayed_challenge"), "keeps every proof runback unplayed");
  check(view.proofReceipts.every((proof) => proof.game?.version === "1"), "projects proof game bindings");

  await rejects((changed) => { changed.truthBoundary.live = true; }, "live must stay false");
  await rejects((changed) => { changed.receipts[0].proof.replayVerdict = "FAIL"; }, "replay failed");
  await rejects((changed) => { changed.receipts[0].proof.publicationApproved = false; }, "unpublished receipt");
  await rejects((changed) => { changed.summary.receiptCount += 1; }, "receipt count mismatch");
  await rejects((changed) => { changed.futureFixtures[0].activationStatus = "activated"; }, "activated future fixture");
  await rejects((changed) => { changed.receipts[0].entrants[0].harnessVersionContentDerived = false; }, "harness version drift");
  await rejects((changed) => { changed.rivalries[0].meetings[0].receiptId = "0".repeat(64); }, "unknown rivalry receipt");
  await rejects((changed) => { changed.rivalries[0].meetings[0].winnerEntrantId = changed.rivalries[0].entrantIds[1]; }, "rivalry outcome drift");
  await rejects((changed) => { changed.rivalries[0].meetings[0].meetingNumber = 2; }, "rivalry meeting order drift");
  await rejects((changed) => { changed.rivalries[0].meetings[0].runback.status = "played"; }, "rivalry runback activated");
  await rejects((changed) => { changed.rivalries[1].meetings[0].receiptId = changed.rivalries[0].meetings[0].receiptId; }, "duplicate rivalry receipt");
  await rejects((changed) => { changed.rivalries[0].meetings.pop(); changed.rivalries[0].meetingCount -= 1; }, "receipt missing rivalry runback lineage");

  await rejects((changed) => { changed.receipts[0].headline += " altered"; }, "digest mismatch");
  const rehashedMutation = copy(model);
  rehashedMutation.receipts[0].headline += " altered and rehashed";
  rehashedMutation.readModelDigest = digestModel(rehashedMutation);
  let pinMessage = "";
  try { await adapter.adaptArenaReadModel(rehashedMutation, demo); } catch (error) { pinMessage = error.message; }
  check(pinMessage.includes("digest pin mismatch"), "rejects a locally rehashed but unreviewed corpus");

  const validFetch = async (url) => response(url.includes("arena-read-model") ? model : demo);
  const loaded = await adapter.loadArenaData(validFetch);
  check(loaded.sourceMode === "verified_corpus", "loads verified corpus first");

  const missingModelFetch = async (url) => url.includes("arena-read-model") ? response({}, false) : response(demo);
  const missingFallback = await adapter.loadArenaData(missingModelFetch);
  check(missingFallback.sourceMode === "demo_fixture_fallback", "falls back when corpus is missing");
  check(missingFallback.sourceMeta.fallbackReason !== null, "discloses fallback reason");

  const invalidModel = copy(model);
  invalidModel.truthBoundary.authenticated = true;
  const invalidModelFetch = async (url) => response(url.includes("arena-read-model") ? invalidModel : demo);
  const invalidFallback = await adapter.loadArenaData(invalidModelFetch);
  check(invalidFallback.sourceMode === "demo_fixture_fallback", "falls back when corpus is invalid");

  const digestMutation = copy(model);
  digestMutation.receipts[0].headline += " altered";
  const digestMutationFetch = async (url) => response(url.includes("arena-read-model") ? digestMutation : demo);
  const digestFallback = await adapter.loadArenaData(digestMutationFetch);
  check(digestFallback.sourceMode === "demo_fixture_fallback", "falls back when corpus digest does not match its content");
  check(digestFallback.sourceMeta.fallbackReason === "verified_read_model_digest_mismatch", "discloses bounded digest-mismatch fallback reason");

  const rehashedMutationFetch = async (url) => response(url.includes("arena-read-model") ? rehashedMutation : demo);
  const pinFallback = await adapter.loadArenaData(rehashedMutationFetch);
  check(pinFallback.sourceMode === "demo_fixture_fallback", "falls back when an unreviewed digest is internally self-consistent");
  check(pinFallback.sourceMeta.fallbackReason === "verified_read_model_digest_mismatch", "does not relabel a rehashed unreviewed corpus as verified");

  const cryptoDescriptor = Object.getOwnPropertyDescriptor(globalThis, "crypto");
  Object.defineProperty(globalThis, "crypto", { value: undefined, configurable: true });
  try {
    const unavailableIntegrityFallback = await adapter.loadArenaData(validFetch);
    check(unavailableIntegrityFallback.sourceMode === "demo_fixture_fallback", "falls back when browser SHA-256 is unavailable");
    check(unavailableIntegrityFallback.sourceMeta.fallbackReason === "verified_read_model_integrity_unavailable", "discloses bounded integrity-unavailable fallback reason");
  } finally {
    if (cryptoDescriptor) Object.defineProperty(globalThis, "crypto", cryptoDescriptor);
    else delete globalThis.crypto;
  }

  let demoFailure = "";
  try { await adapter.loadArenaData(async () => response({}, false)); } catch (error) { demoFailure = error.message; }
  check(demoFailure.includes("demo fixture request failed"), "fails closed when bounded fallback is unavailable");

  process.stdout.write(JSON.stringify({ status: "PASS", checks: checks.length }));
})().catch((error) => {
  process.stderr.write(error.stack || error.message);
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
        timeout=30,
        check=False,
    )
    require(result.returncode == 0, f"Arena read-adapter check failed: {result.stderr.strip()}")
    payload = json.loads(result.stdout)
    require(payload.get("status") == "PASS", "Arena read adapter did not report PASS")
    require(payload.get("checks", 0) >= 48, "Arena read adapter coverage unexpectedly shrank")
    print(f"BuilderWars mobile Arena read adapter: PASS ({payload['checks']} checks)")
    print("verified corpus / disclosed demo fallback / fail-closed local source boundary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
