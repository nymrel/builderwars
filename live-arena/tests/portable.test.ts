import assert from "node:assert/strict";
import test from "node:test";
import { createHash } from "node:crypto";
import { copyFile, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { execFileSync } from "node:child_process";
import { tmpdir } from "node:os";
import path from "node:path";
import { RULES, createGame, applyMove, moveLabel } from "../src/games";
import * as runtime from "../src/runtime";
import type { RecordData } from "../src/records";

function fixture(kind: string, moves: string[]): RecordData {
  let state = createGame(RULES[kind]);
  const record: RecordData = {
    schema: "builderwars.exhibition.v1", id: "portable-fixture", createdAt: "2026-09-05T00:00:00Z",
    rules: RULES[kind], status: "Fixture", events: [],
    agents: [0, 1].map(i => ({ name: `Synthetic human ${i}`, kind: "human", model: "human", strategy: "", effort: "default" })),
  };
  for (const move of moves) {
    record.events.push({ move, seat: state.turn, ply: record.events.length + 1, label: moveLabel(move, state), model: "human", comment: "", elapsed: 0, tokens: null, cost: null });
    state = applyMove(state, move);
  }
  return record;
}
test("browser referee snapshot matches the advertised digest and SRI", async () => {
  const bytes = await readFile(new URL(`../public/${runtime.refereeManifest.file}`, import.meta.url));
  assert.equal(createHash("sha256").update(bytes).digest("hex"), runtime.refereeManifest.digest);
  assert.equal(`sha256-${createHash("sha256").update(bytes).digest("base64")}`, runtime.refereeManifest.integrity);
  assert.match(bytes.toString(), /Copyright \(c\) 2025, Jeff Hlywa/);
});
test("source, executable snapshot and portable proof agree on terminal and repetition state", async () => {
  const fixtures = [
    fixture("connect4", ["0", "1", "0", "1", "0", "1", "0"]),
    fixture("chess", ["f2f3", "e7e5", "g2g4", "d8h4"]),
    fixture("chess", ["g1f3", "g8f6", "f3g1", "f6g8", "g1f3", "g8f6", "f3g1", "f6g8"]),
    fixture("tictactoe", ["0", "3", "1", "4", "2"]),
  ];
  for (const record of fixtures) {
    let source = createGame(record.rules);
    let snapshot = runtime.createGame(record.rules);
    for (const e of record.events) {
      source = applyMove(source, e.move);
      snapshot = runtime.applyMove(snapshot, e.move);
      assert.deepEqual(source, snapshot);
    }
    const proof = await runtime.createProof(record, runtime.refereeManifest.digest, 80, "reverified_import");
    assert.deepEqual((await runtime.verifyProof(proof, runtime.refereeManifest.digest)).state, source);
  }
});
test("a copied verifier reproduces Connect Four with only Node, rejecting corrupted proof", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "builderwars-portable-"));
  try {
    const proof = await runtime.createProof(fixture("connect4", ["0", "1", "0", "1", "0", "1", "0"]), runtime.refereeManifest.digest, 80, "reverified_import");
    await copyFile(new URL(`../public/${runtime.refereeManifest.verifier}`, import.meta.url), path.join(dir, "verify.mjs"));
    await writeFile(path.join(dir, "match.jsonl"), proof);
    const result = JSON.parse(execFileSync(process.execPath, ["verify.mjs", "match.jsonl"], { cwd: dir, encoding: "utf8", timeout: 10000 }));
    assert.equal(result.verified, true);
    assert.equal(result.complete, true);
    assert.equal(result.winner, 0);
    assert.equal(result.model_attested, false);
    await writeFile(path.join(dir, "match.jsonl"), proof.replace('"winner":0', '"winner":1'));
    assert.throws(() => execFileSync(process.execPath, ["verify.mjs", "match.jsonl"], { cwd: dir, timeout: 10000, stdio: "pipe" }));
    await writeFile(path.join(dir, "match.jsonl"), Buffer.from([0xff, 0xfe]));
    assert.throws(() => execFileSync(process.execPath, ["verify.mjs", "match.jsonl"], { cwd: dir, timeout: 10000, stdio: "pipe" }));
  } finally {
    // Exact task-created temporary directory; never a project or broad user path.
    await rm(dir, { recursive: true, force: true });
  }
});
