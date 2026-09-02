#!/usr/bin/env python3
"""Adversarial checks for the fail-closed mobile Creator Game Lab."""

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
    require(node is not None, "Node.js is required to check the mobile creator-game adapter")
    build_check = subprocess.run(
        [str(Path(shutil.which("python") or "python")), str(ROOT / "bin" / "build_mobile_creator_game_lab.py"), "--check"],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
    )
    require(build_check.returncode == 0, f"mobile creator-game projection drift: {build_check.stderr.strip()}")

    script = r'''
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const adapter = require(path.join(process.cwd(), "data-adapter.js"));
const lab = JSON.parse(fs.readFileSync(path.join(process.cwd(), "data", "creator-game-lab.v1.json"), "utf8"));
const checks = [];
function check(predicate, message) { if (!predicate) throw new Error(message); checks.push(message); }
function copy(value) { return JSON.parse(JSON.stringify(value)); }
function canonicalJSON(value) {
  if (value === null || typeof value === "boolean" || typeof value === "string" || typeof value === "number") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map((item) => canonicalJSON(item)).join(",")}]`;
  return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJSON(value[key])}`).join(",")}}`;
}
function digestLab(value) {
  const payload = copy(value); delete payload.labDigest;
  return crypto.createHash("sha256").update(canonicalJSON(payload), "utf8").digest("hex");
}
async function rejects(mutator, expected) {
  const changed = copy(lab); mutator(changed);
  let message = "";
  try { await adapter.verifyCreatorGameLabIntegrity(changed); } catch (error) { message = error.message; }
  check(message.includes(expected), `rejects ${expected}`);
}
function response(body, ok = true) { return { ok, async json() { return copy(body); } }; }
(async () => {
  adapter.validateCreatorGameLab(lab);
  const verified = await adapter.verifyCreatorGameLabIntegrity(lab);
  check(verified.labDigest === adapter.CREATOR_GAME_LAB_DIGEST_PIN, "pins the exact reviewed lab digest");
  check(verified.manifest.gameId === "creator.signal-siege" && verified.manifest.version === "1.0.0", "binds the reviewed candidate identity");
  check(verified.manifest.rules.family === "sealed_allocation_v1", "permits only the fixed declarative family");
  check(verified.replay.effectiveVerdict === "PASS" && verified.replay.moveCount === 12, "preserves the deterministic replay verdict");
  check(Object.values(verified.authority).every((value) => value === false), "keeps every authority and attestation false");
  check(verified.admissionGates.length === 8, "preserves every separate admission gate");
  await rejects((value) => { value.authority.executionAuthorized = true; }, "authority inflation");
  await rejects((value) => { value.authority.modelAttested = true; }, "authority inflation");
  await rejects((value) => { value.manifest.rules.family = "javascript_v1"; }, "unknown rule family");
  await rejects((value) => { value.manifest.rules.expression = "process.env"; }, "rules fields drift");
  await rejects((value) => { value.manifest.presentation.strategyPrompt = "https://example.invalid/creator-game-hook"; }, "external URL present");
  await rejects((value) => { value.replay.effectiveVerdict = "SKIP"; }, "replay verdict");
  await rejects((value) => { value.replay.scores.push(999); }, "replay scores drift");
  await rejects((value) => { value.admissionGates.pop(); }, "admission gate drift");
  await rejects((value) => { value.decision = "admitted"; }, "decision overstates admission");
  await rejects((value) => { value.manifest.summary += " changed"; }, "digest mismatch");
  const rehashed = copy(lab);
  rehashed.manifest.summary += " locally rehashed but unreviewed";
  rehashed.labDigest = digestLab(rehashed);
  let rehashMessage = "";
  try { await adapter.verifyCreatorGameLabIntegrity(rehashed); } catch (error) { rehashMessage = error.message; }
  check(rehashMessage.includes("digest pin mismatch"), "rejects internally consistent but unreviewed bytes");
  const loaded = await adapter.loadCreatorGameLab(async () => response(lab));
  check(loaded.labDigest === lab.labDigest, "loads only the bounded local lab source");
  let missingMessage = "";
  try { await adapter.loadCreatorGameLab(async () => response({}, false)); } catch (error) { missingMessage = error.message; }
  check(missingMessage.includes("creator game lab request failed"), "fails closed when the source is missing");
  const descriptor = Object.getOwnPropertyDescriptor(globalThis, "crypto");
  Object.defineProperty(globalThis, "crypto", { value: undefined, configurable: true });
  try {
    let integrityMessage = "";
    try { await adapter.loadCreatorGameLab(async () => response(lab)); } catch (error) { integrityMessage = error.message; }
    check(integrityMessage.includes("SHA-256 unavailable"), "fails closed when SHA-256 is unavailable");
  } finally {
    if (descriptor) Object.defineProperty(globalThis, "crypto", descriptor); else delete globalThis.crypto;
  }
  process.stdout.write(JSON.stringify({ status: "PASS", checks: checks.length }));
})().catch((error) => { process.stderr.write(error.stack || error.message); process.exit(1); });
'''
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
    require(result.returncode == 0, f"mobile creator-game adapter failed: {result.stderr.strip()}")
    payload = json.loads(result.stdout)
    require(payload.get("status") == "PASS" and payload.get("checks", 0) >= 20, "mobile creator-game coverage shrank")
    print(f"BuilderWars mobile Creator Game Lab: PASS ({payload['checks']} checks)")
    print("reviewed declarative candidate / exact digest pin / zero execution or publication authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
