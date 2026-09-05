#!/usr/bin/env python3
"""Adversarial proof for the receipt-bound browser-memory spectator rehearsal."""

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
    require(node is not None, "Node.js is required to exercise the spectator rehearsal")
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
  const bytes = new TextEncoder().encode(canonical(value));
  const result = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(result)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}
async function rehash(candidate) {
  const unsigned = copy(candidate);
  delete unsigned.choiceDigest;
  candidate.choiceDigest = await digest(unsigned);
  return candidate;
}
async function rejects(task, expected) {
  let message = "";
  try { await task(); } catch (error) { message = error.message; }
  check(message.includes(expected), `rejects ${expected}`);
}

(async () => {
  const view = await adapter.adaptArenaReadModel(model, demo);
  check(view.sourceMode === "verified_corpus", "requires the verified reviewed corpus");
  check(view.proofReceipts.length === 8, "projects the exact reviewed receipt set");
  const proof = view.proofReceipts[0];
  check(proof.entrants.length === 2 && proof.entrants.map((entry) => entry.seat).join(",") === "0,1", "projects two ordered spectator choices");
  check(proof.outcome.winnerEntrantId === proof.entrants[proof.outcome.winnerSeat].entrantId, "projects an exact reviewed winner binding");
  check(proof.replayVerdict === "PASS" && proof.publicationApproved === true, "uses only replay-passing allowlisted proof");

  const seat0 = await adapter.createSpectatorRehearsalChoice(proof, view.sourceMode, "seat0");
  const seat0Repeat = await adapter.createSpectatorRehearsalChoice(proof, view.sourceMode, "seat0");
  const seat1 = await adapter.createSpectatorRehearsalChoice(proof, view.sourceMode, "seat1");
  const runback = await adapter.createSpectatorRehearsalChoice(proof, view.sourceMode, "runback");
  check(seat0.schemaVersion === adapter.SPECTATOR_REHEARSAL_SCHEMA, "uses the versioned spectator rehearsal schema");
  check(seat0.choiceDigest === seat0Repeat.choiceDigest && seat0.choiceDigest !== seat1.choiceDigest, "choice digest is deterministic and choice-sensitive");
  check(/^[0-9a-f]{64}$/.test(seat0.choiceDigest), "choice carries a content-shaped digest");
  check(seat0.proofBinding.receiptId === proof.receiptId && seat0.proofBinding.fixtureId === proof.fixtureId, "binds exact receipt and fixture ids");
  check(seat0.proofBinding.replayVerdict === "PASS" && seat0.proofBinding.publicationApproved === true, "binds exact replay and allowlist facts");
  check(seat0.proofBinding.evidenceClass === proof.evidenceClass, "binds exact evidence class");
  check(seat0.selectedChoice.choiceId === "seat0" && seat0.selectedChoice.seat === 0, "seat-zero choice binds the exact entrant seat");
  check(runback.selectedChoice.choiceId === "runback" && runback.selectedChoice.seat === null, "runback choice invents no entrant");
  check(seat0.limitations.join(",") === "result_preexisted,no_trusted_timestamp,not_a_prediction,not_collected,audience_unattested,identity_unattested,not_persisted,ranking_unchanged,publication_not_requested", "binds the exact no-claim limitations");

  const verified0 = await adapter.verifySpectatorRehearsalChoice(proof, view.sourceMode, seat0);
  const verified1 = await adapter.verifySpectatorRehearsalChoice(proof, view.sourceMode, seat1);
  const verifiedRunback = await adapter.verifySpectatorRehearsalChoice(proof, view.sourceMode, runback);
  check(verified0.verified === true && verified0.authority === false, "independently verifies the rehearsal with zero authority");
  check(verified0.choiceRelation === (proof.outcome.winnerSeat === 0 ? "selected_reviewed_winner" : "selected_reviewed_nonwinner"), "seat-zero relation is derived from reviewed proof");
  check(verified1.choiceRelation === (proof.outcome.winnerSeat === 1 ? "selected_reviewed_winner" : "selected_reviewed_nonwinner"), "seat-one relation is derived from reviewed proof");
  check(verifiedRunback.choiceRelation === "local_runback_interest_only", "runback remains local interest only");
  check(proof.runback.status === "unplayed_challenge", "verification preserves the still-unplayed runback");

  await rejects(() => adapter.createSpectatorRehearsalChoice(proof, "demo_fixture_fallback", "seat0"), "verified corpus required");
  await rejects(() => adapter.createSpectatorRehearsalChoice(proof, view.sourceMode, "winner"), "unsupported choice");
  for (const [label, mutate, expected] of [
    ["replay", (row) => { row.replayVerdict = "FAIL"; }, "reviewed proof required"],
    ["allowlist", (row) => { row.publicationApproved = false; }, "reviewed proof required"],
    ["entrant count", (row) => { row.entrants.pop(); }, "exactly two entrants required"],
    ["entrant order", (row) => { row.entrants.reverse(); }, "entrant binding drift"],
    ["winner binding", (row) => { row.outcome.winnerEntrantId = "f".repeat(64); }, "winner binding drift"],
    ["evidence", (row) => { row.evidenceClass = "vendor_claim"; }, "evidence class drift"],
  ]) {
    const changed = copy(proof); mutate(changed);
    await rejects(() => adapter.createSpectatorRehearsalChoice(changed, view.sourceMode, "seat0"), expected);
  }

  const mutations = [
    ["unknown field", (row) => { row.extra = true; }, "fields drift", false],
    ["choice digest", (row) => { row.choiceDigest = "f".repeat(64); }, "choice digest mismatch", false],
    ["receipt", (row) => { row.proofBinding.receiptId = "e".repeat(64); }, "proof or choice projection mismatch", true],
    ["choice id", (row) => { row.selectedChoice.choiceId = "seat1"; }, "proof or choice projection mismatch", true],
    ["choice seat", (row) => { row.selectedChoice.seat = 1; }, "proof or choice projection mismatch", true],
    ["result status", (row) => { row.limitations[0] = "result_pending"; }, "proof or choice projection mismatch", true],
    ["trusted timestamp", (row) => { row.limitations[1] = "trusted_timestamp"; }, "proof or choice projection mismatch", true],
    ["prediction", (row) => { row.limitations[2] = "prediction"; }, "proof or choice projection mismatch", true],
    ["collection", (row) => { row.limitations[3] = "collected"; }, "proof or choice projection mismatch", true],
    ["audience", (row) => { row.limitations[4] = "audience_attested"; }, "proof or choice projection mismatch", true],
    ["identity", (row) => { row.limitations[5] = "identity_attested"; }, "proof or choice projection mismatch", true],
    ["storage", (row) => { row.limitations[6] = "persisted"; }, "proof or choice projection mismatch", true],
    ["ranking", (row) => { row.limitations[7] = "ranking_changed"; }, "proof or choice projection mismatch", true],
    ["publication", (row) => { row.limitations[8] = "publication_requested"; }, "proof or choice projection mismatch", true],
  ];
  for (const [label, mutate, expected, reseal] of mutations) {
    const changed = copy(seat0); mutate(changed); if (reseal) await rehash(changed);
    await rejects(() => adapter.verifySpectatorRehearsalChoice(proof, view.sourceMode, changed), expected);
  }

  const differentProof = view.proofReceipts[1];
  await rejects(() => adapter.verifySpectatorRehearsalChoice(differentProof, view.sourceMode, seat0), "proof or choice projection mismatch");
  console.log(JSON.stringify({ status: "PASS", checks }));
})().catch((error) => { console.error(error.stack || error.message); process.exit(1); });
'''
    result = subprocess.run(
        [node, "-e", script],
        cwd=MOBILE,
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    require(result.returncode == 0, result.stderr or result.stdout)
    payload = json.loads(result.stdout)
    require(payload["status"] == "PASS", "spectator rehearsal checker did not report PASS")
    require(len(payload["checks"]) >= 42, "spectator rehearsal adversarial floor regressed")
    print(f"BuilderWars mobile spectator rehearsal: PASS ({len(payload['checks'])} checks)")
    print("reviewed receipt / local choice / reveal / verification / still-unplayed runback")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
