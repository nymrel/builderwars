#!/usr/bin/env python3
"""Exercise proof-linked learning and still-unplayed local runback proposals."""

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
    require(node is not None, "Node.js is required to exercise Arena learning and runback proposals")

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
function learningRejects(mutator, expected) {
  const proof = copy(validProof);
  let source = "verified_corpus";
  mutator({ proof, setSource(value) { source = value; } });
  let message = "";
  try { adapter.buildReceiptLearningAction(proof, source); } catch (error) { message = error.message; }
  check(message.includes(expected), `learning rejects ${expected}`);
}
function proposalRejects(mutator, expected) {
  const learning = copy(validLearning);
  const blueprint = copy(validBlueprint);
  let deltaId = "require_human_checkpoints";
  let source = "verified_corpus";
  mutator({ learning, blueprint, setDelta(value) { deltaId = value; }, setSource(value) { source = value; } });
  let message = "";
  try { adapter.buildRunbackProposal(learning, blueprint, deltaId, source); } catch (error) { message = error.message; }
  check(message.includes(expected), `proposal rejects ${expected}`);
}

const view = adapter.adaptArenaReadModel(model, demo);
check(view.proofReceipts.length === 8, "projects eight reviewed proofs");
check(view.proofReceipts.every((proof) => proof.runback && proof.runback.parentReceiptId === proof.receiptId), "every proof carries parent runback lineage");
check(view.proofReceipts.every((proof) => proof.runback.status === "unplayed_challenge"), "every proof runback remains unplayed");
check(view.proofReceipts.every((proof) => proof.game && proof.game.version === "1"), "every proof carries exact game version");

const validProof = view.proofReceipts.find((proof) => proof.moveSourceCounts.model > 0);
const validLearning = adapter.buildReceiptLearningAction(validProof, "verified_corpus");
check(validLearning.schemaVersion === adapter.LEARNING_SCHEMA, "uses versioned learning schema");
check(validLearning.status === "review_only", "learning stays review only");
check(validLearning.receipt.receiptId === validProof.receiptId, "learning binds exact receipt");
check(validLearning.receipt.fixtureId === validProof.fixtureId, "learning binds exact parent fixture");
check(validLearning.receipt.game.name === validProof.game.name && validLearning.receipt.game.version === "1", "learning binds exact game");
check(validLearning.receipt.replayVerdict === "PASS", "learning retains replay verdict");
check(validLearning.receipt.moveSourceCounts.model === validProof.moveSourceCounts.model, "learning retains visible evidence counts");
check(validLearning.allowedDeltas.length === 3, "learning offers exactly three bounded deltas");
check(new Set(validLearning.allowedDeltas.map((delta) => delta.id)).size === 3, "learning delta ids are unique");
check(validLearning.recommendedDeltaId === "require_strict_validation", "unattested model labels recommend validation review");
check(validLearning.observation.includes("model-source label") && validLearning.observation.includes("unattested"), "learning observation preserves attestation boundary");
check(validLearning.runback.parentReceiptId === validProof.receiptId, "learning carries exact runback parent");
check(validLearning.boundary.includes("does not infer hidden reasoning"), "learning refuses hidden-reasoning claims");

const fallbackProof = view.proofReceipts.find((proof) => proof.moveSourceCounts.fallback > 0);
const fallbackLearning = adapter.buildReceiptLearningAction(fallbackProof, "verified_corpus");
check(fallbackLearning.recommendedDeltaId === "require_fallback_disclosure", "fallback evidence recommends disclosure review");
check(fallbackLearning.observation.includes("fallback move"), "fallback observation is visible-evidence based");
const scriptedProof = view.proofReceipts.find((proof) => proof.moveSourceCounts.scripted > 0);
const scriptedLearning = adapter.buildReceiptLearningAction(scriptedProof, "verified_corpus");
check(scriptedLearning.recommendedDeltaId === "require_human_checkpoints", "scripted reference recommends checkpoint review");
check(scriptedLearning.observation.includes("not model evidence"), "scripted observation refuses model claim");

const validBlueprint = {
  agentName: "Runback Student",
  baseModel: "Arena Small",
  harnessStyle: "Human review checkpoints",
  strictValidation: true,
  fallbackDisclosure: true,
  humanCheckpoints: false,
  localOnly: true,
};
const proposal = adapter.buildRunbackProposal(validLearning, validBlueprint, "require_human_checkpoints", "verified_corpus");
const repeated = adapter.buildRunbackProposal(validLearning, validBlueprint, "require_human_checkpoints", "verified_corpus");
check(proposal.schemaVersion === adapter.RUNBACK_PROPOSAL_SCHEMA, "uses versioned runback proposal schema");
check(proposal.proposalVersion === 1, "sets proposal version one");
check(proposal.proposalKey === repeated.proposalKey, "proposal key is deterministic");
check(proposal.proposalKey.includes(validLearning.receipt.receiptId), "proposal key binds parent receipt");
check(proposal.runbackStatus === "unplayed_proposal", "runback remains an unplayed proposal");
check(proposal.qualificationStatus === "not_run", "runback qualification remains not run");
check(proposal.executionStatus === "disabled", "runback execution remains disabled");
check(proposal.publicationStatus === "not_requested", "runback publication remains unrequested");
check(proposal.parentReceipt.receiptId === validLearning.receipt.receiptId, "proposal preserves parent receipt");
check(proposal.runbackLineage.challengeId === validLearning.runback.challengeId, "proposal preserves challenge id");
check(proposal.runbackLineage.fixtureId === validLearning.runback.fixtureId, "proposal preserves runback fixture id");
check(proposal.gameBinding.name === validLearning.receipt.game.name && proposal.gameBinding.version === "1", "proposal preserves game binding");
check(proposal.rulesBinding.status === "blocked_missing_explicit_rules_digest", "proposal blocks missing rules digest");
check(proposal.rulesBinding.rulesDigest === null, "proposal does not invent rules digest");
check(proposal.blueprint.localOnly === true && proposal.blueprint.agentName === validBlueprint.agentName, "proposal binds local blueprint label");
check(proposal.blueprintDelta.guardKey === "humanCheckpoints", "proposal binds selected guard");
check(proposal.blueprintDelta.from === false && proposal.blueprintDelta.to === true, "proposal describes exact false-to-true delta");
check(proposal.blueprintDelta.changeStatus === "proposed_change", "proposal labels an actual change");
check(JSON.stringify(proposal.executionBlockers) === JSON.stringify(["explicit_rules_digest_not_bound", "qualification_not_run", "sanctioned_runner_not_bound", "local_blueprint_version_not_committed"]), "proposal preserves four execution blockers");
check(Object.values(proposal.attestations).every((value) => value === false), "proposal keeps every attestation false");
check(proposal.boundary.includes("does not qualify, execute, attest, rank, publish, or spend"), "proposal states no-execution boundary");

const alreadyDeclared = adapter.buildRunbackProposal(validLearning, validBlueprint, "require_strict_validation", "verified_corpus");
check(alreadyDeclared.blueprintDelta.changeStatus === "already_declared", "already-true guard is not misrepresented as a change");
check(alreadyDeclared.proposalKey !== proposal.proposalKey, "different deltas produce different proposal keys");

learningRejects(({ setSource }) => { setSource("demo_fixture_fallback"); }, "verified corpus required");
learningRejects(({ proof }) => { proof.receiptId = "bad"; }, "reviewed receipt missing");
learningRejects(({ proof }) => { proof.replayVerdict = "FAIL"; }, "reviewed proof required");
learningRejects(({ proof }) => { proof.publicationApproved = false; }, "reviewed proof required");
learningRejects(({ proof }) => { proof.game.version = "2"; }, "game binding missing");
learningRejects(({ proof }) => { proof.moveSourceCounts.model = -1; }, "invalid model count");
learningRejects(({ proof }) => { delete proof.runback; }, "runback lineage missing");
learningRejects(({ proof }) => { proof.runback.parentReceiptId = "0".repeat(64); }, "runback parent drift");
learningRejects(({ proof }) => { proof.runback.status = "played"; }, "runback already activated");
learningRejects(({ proof }) => { proof.runback.challengeId = "bad"; }, "runback identifiers missing");

proposalRejects(({ setSource }) => { setSource("demo_fixture_fallback"); }, "verified corpus required");
proposalRejects(({ learning }) => { learning.schemaVersion = "drift"; }, "learning action missing");
proposalRejects(({ learning }) => { learning.status = "completed"; }, "learning action missing");
proposalRejects(({ learning }) => { learning.receipt.receiptId = "bad"; }, "parent receipt missing");
proposalRejects(({ learning }) => { learning.runback.parentReceiptId = "0".repeat(64); }, "parent lineage drift");
proposalRejects(({ learning }) => { learning.runback.status = "played"; }, "runback already activated");
proposalRejects(({ learning }) => { learning.runback.fixtureId = "bad"; }, "runback identifiers missing");
proposalRejects(({ blueprint }) => { blueprint.localOnly = false; }, "blueprint must stay local only");
proposalRejects(({ setDelta }) => { setDelta("arbitrary_code"); }, "unknown blueprint delta");

const fallbackView = adapter.demoFallback(demo);
check(fallbackView.proofReceipts.every((proof) => !proof.runback), "demo fallback does not invent runback lineage");
let fallbackMessage = "";
try { adapter.buildReceiptLearningAction(fallbackView.proofReceipts[0], fallbackView.sourceMode); } catch (error) { fallbackMessage = error.message; }
check(fallbackMessage.includes("verified corpus required"), "demo fallback cannot enter receipt learning");

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
    require(result.returncode == 0, f"Arena learning/runback check failed: {result.stderr.strip()}")
    payload = json.loads(result.stdout)
    require(payload.get("status") == "PASS", "Arena learning/runback did not report PASS")
    require(payload.get("checks", 0) >= 65, "Arena learning/runback coverage unexpectedly shrank")
    print(f"BuilderWars mobile receipt learning + runback proposal: PASS ({payload['checks']} checks)")
    print("proof-linked evidence / bounded blueprint delta / blocked rules binding / no execution")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
