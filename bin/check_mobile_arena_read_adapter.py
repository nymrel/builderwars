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
const adapter = require(path.join(process.cwd(), "data-adapter.js"));
const demo = JSON.parse(fs.readFileSync(path.join(process.cwd(), "data", "demo-state.json"), "utf8"));
const model = JSON.parse(fs.readFileSync(path.join(process.cwd(), "data", "arena-read-model.v1.json"), "utf8"));
const checks = [];
function check(predicate, message) {
  if (!predicate) throw new Error(message);
  checks.push(message);
}
function copy(value) { return JSON.parse(JSON.stringify(value)); }
function rejects(mutator, expected) {
  const changed = copy(model);
  mutator(changed);
  let message = "";
  try { adapter.adaptArenaReadModel(changed, demo); } catch (error) { message = error.message; }
  check(message.includes(expected), `rejects ${expected}`);
}
function response(body, ok = true) {
  return { ok, async json() { return copy(body); } };
}

(async () => {
  adapter.validateDemoFixture(demo);
  adapter.validateArenaReadModel(model);
  checks.push("validates bounded inputs");

  const view = adapter.adaptArenaReadModel(model, demo);
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

  rejects((changed) => { changed.truthBoundary.live = true; }, "live must stay false");
  rejects((changed) => { changed.receipts[0].proof.replayVerdict = "FAIL"; }, "replay failed");
  rejects((changed) => { changed.receipts[0].proof.publicationApproved = false; }, "unpublished receipt");
  rejects((changed) => { changed.summary.receiptCount += 1; }, "receipt count mismatch");
  rejects((changed) => { changed.futureFixtures[0].activationStatus = "activated"; }, "activated future fixture");
  rejects((changed) => { changed.receipts[0].entrants[0].harnessVersionContentDerived = false; }, "harness version drift");
  rejects((changed) => { changed.rivalries[0].meetings[0].receiptId = "0".repeat(64); }, "unknown rivalry receipt");
  rejects((changed) => { changed.rivalries[0].meetings[0].winnerEntrantId = changed.rivalries[0].entrantIds[1]; }, "rivalry outcome drift");
  rejects((changed) => { changed.rivalries[0].meetings[0].meetingNumber = 2; }, "rivalry meeting order drift");
  rejects((changed) => { changed.rivalries[0].meetings[0].runback.status = "played"; }, "rivalry runback activated");

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
    require(payload.get("checks", 0) >= 34, "Arena read adapter coverage unexpectedly shrank")
    print(f"BuilderWars mobile Arena read adapter: PASS ({payload['checks']} checks)")
    print("verified corpus / disclosed demo fallback / fail-closed local source boundary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
