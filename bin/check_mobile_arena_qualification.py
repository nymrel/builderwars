#!/usr/bin/env python3
"""Exercise receipt routes and the no-execution Arena qualification preview."""

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
    require(node is not None, "Node.js is required to exercise Arena qualification")

    script = r"""
const fs = require("fs");
const path = require("path");
const adapter = require(path.join(process.cwd(), "data-adapter.js"));
const routes = require(path.join(process.cwd(), "app.js"));
const demo = JSON.parse(fs.readFileSync(path.join(process.cwd(), "data", "demo-state.json"), "utf8"));
const model = JSON.parse(fs.readFileSync(path.join(process.cwd(), "data", "arena-read-model.v1.json"), "utf8"));
const checks = [];
function check(predicate, message) {
  if (!predicate) throw new Error(message);
  checks.push(message);
}
function copy(value) { return JSON.parse(JSON.stringify(value)); }
function previewRejects(mutator, expected) {
  const blueprint = copy(validBlueprint);
  const fixture = copy(validFixture);
  let source = "verified_corpus";
  mutator({ blueprint, fixture, setSource(value) { source = value; } });
  let message = "";
  try { adapter.buildQualificationPreview(blueprint, fixture, source); } catch (error) { message = error.message; }
  check(message.includes(expected), `rejects ${expected}`);
}

const receiptId = model.receipts[0].receiptId;
check(routes.formatArenaRoute("arena") === "#arena", "formats base Arena route");
check(routes.formatArenaRoute("watch", receiptId) === `#watch/receipt/${receiptId}`, "formats receipt route");
check(routes.formatArenaRoute("unknown", receiptId) === `#arena/receipt/${receiptId}`, "normalizes unknown view");
check(routes.formatArenaRoute("watch", "unsafe/value") === "#watch", "refuses unsafe receipt route");
check(JSON.stringify(routes.parseArenaRoute("#compete")) === JSON.stringify({ view: "compete", receiptId: null }), "parses base route");
check(routes.parseArenaRoute(`#watch/receipt/${receiptId}`).receiptId === receiptId, "parses receipt route");
check(routes.parseArenaRoute("#unknown") === null, "rejects unknown view");
check(routes.parseArenaRoute("#watch/receipt") === null, "rejects incomplete receipt route");
check(routes.parseArenaRoute("#watch/receipt/unsafe%2Fvalue") === null, "rejects encoded unsafe receipt id");

const view = adapter.adaptArenaReadModel(model, demo);
check(view.rivalries.length === 3, "projects three verified rivalries");
check(view.rivalries.every((rivalry) => view.proofReceipts.some((proof) => proof.receiptId === rivalry.latestReceiptId)), "rivalry links resolve to reviewed receipts");
check(view.rivalries.every((rivalry) => rivalry.runbackStatus === "unplayed_challenge"), "rivalry runbacks remain unplayed");
check(view.rivalries.every((rivalry) => !String(rivalry.record).toLowerCase().includes("rank")), "rivalries make no rank claim");
check(view.quickMatches.length === 3 && view.quickMatches.every((fixture) => fixture.previewAllowed), "projects three preview-only fixtures");

const validBlueprint = {
  agentName: "Receipt Runner",
  baseModel: "Arena Reason",
  harnessStyle: "Validate every move",
  strictValidation: true,
  fallbackDisclosure: true,
  humanCheckpoints: false,
  localOnly: true,
};
const validFixture = view.quickMatches[0];
const preview = adapter.buildQualificationPreview(validBlueprint, validFixture, "verified_corpus");
const repeated = adapter.buildQualificationPreview(validBlueprint, validFixture, "verified_corpus");
check(preview.schemaVersion === adapter.QUALIFICATION_SCHEMA, "uses versioned qualification schema");
check(preview.previewOnly === true, "labels preview only");
check(preview.qualificationStatus === "not_run", "qualification remains not run");
check(preview.executionStatus === "disabled", "execution remains disabled");
check(preview.publicationStatus === "not_requested", "publication remains unrequested");
check(preview.previewKey === repeated.previewKey, "preview key is deterministic");
check(preview.previewKey.includes(encodeURIComponent(validBlueprint.agentName)), "preview key binds blueprint identity label");
check(preview.fixture.fixtureId === validFixture.id, "binds exact fixture");
check(preview.fixture.game.name === validFixture.game.name && preview.fixture.game.version === "1", "binds exact game version");
check(preview.fixture.rulesWeekId === validFixture.rulesWeekId && preview.fixture.rulesDigest === validFixture.rulesDigest, "binds exact rules");
check(preview.resourceClass.id === adapter.PREVIEW_RESOURCE_CLASS, "binds exact preview resource class");
check(preview.resourceClass.computeAllowed === false && preview.resourceClass.networkAllowed === false, "forbids compute and network");
check(preview.readiness === "blueprint_ready_for_future_attempt", "reports ready local guards without qualifying");
check(preview.readinessChecks.length === 4 && preview.readinessChecks.every((item) => item.ready), "reports four ready checks");
check(JSON.stringify(preview.executionBlockers) === JSON.stringify(["qualification_not_run", "fixture_not_activated", "sanctioned_runner_not_bound"]), "preserves three execution blockers");
check(Object.values(preview.attestations).every((value) => value === false), "keeps every attestation false");
check(preview.boundary.includes("does not qualify, execute, authenticate, attest, rank, publish, or spend"), "states no-execution boundary");

const guardOff = copy(validBlueprint);
guardOff.strictValidation = false;
const guardPreview = adapter.buildQualificationPreview(guardOff, validFixture, "verified_corpus");
check(guardPreview.readiness === "blueprint_needs_guard_changes", "guard-off blueprint cannot appear ready");
check(guardPreview.qualificationStatus === "not_run" && guardPreview.executionStatus === "disabled", "guard-off preview stays inactive");

previewRejects(({ blueprint }) => { blueprint.localOnly = false; }, "blueprint must stay local only");
previewRejects(({ blueprint }) => { blueprint.agentName = ""; }, "invalid agent name");
previewRejects(({ blueprint }) => { blueprint.agentName = "x".repeat(37); }, "invalid agent name");
previewRejects(({ blueprint }) => { blueprint.baseModel = "Remote subscription"; }, "unknown demo base");
previewRejects(({ blueprint }) => { blueprint.harnessStyle = "Arbitrary code"; }, "unknown harness style");
previewRejects(({ blueprint }) => { blueprint.strictValidation = "yes"; }, "strictValidation must be boolean");
previewRejects(({ fixture }) => { fixture.previewAllowed = false; }, "fixture is not preview-only");
previewRejects(({ fixture }) => { fixture.enabled = true; }, "fixture is not preview-only");
previewRejects(({ fixture }) => { fixture.id = "bad"; }, "invalid fixture id");
previewRejects(({ fixture }) => { fixture.game.version = "2"; }, "game binding missing");
previewRejects(({ fixture }) => { fixture.rulesDigest = "bad"; }, "rules binding missing");
previewRejects(({ fixture }) => { fixture.activationStatus = "activated"; }, "fixture activation drift");
previewRejects(({ fixture }) => { fixture.fixtureStatus = "played"; }, "fixture activation drift");
previewRejects(({ fixture }) => { fixture.resourceClass = "paid-compute"; }, "resource class drift");
previewRejects(({ setSource }) => { setSource("demo_fixture_fallback"); }, "verified corpus required");

process.stdout.write(JSON.stringify({ status: "PASS", checks: checks.length }));
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
    require(result.returncode == 0, f"Arena qualification check failed: {result.stderr.strip()}")
    payload = json.loads(result.stdout)
    require(payload.get("status") == "PASS", "Arena qualification did not report PASS")
    require(payload.get("checks", 0) >= 45, "Arena qualification coverage unexpectedly shrank")
    print(f"BuilderWars mobile Arena qualification preview: PASS ({payload['checks']} checks)")
    print("receipt routes / verified rivalries / deterministic no-execution qualification boundary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
