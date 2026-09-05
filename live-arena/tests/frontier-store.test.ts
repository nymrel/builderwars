import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, rm, readFile, writeFile, mkdir, readdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { RULES, sha256 } from "../src/runtime";
import { FrontierStore } from "../scripts/frontier-store";
import { frontier } from "../scripts/frontier";

async function fixture(fn: (store: FrontierStore, dir: string) => Promise<void>) {
  const dir = await mkdtemp(join(tmpdir(), "bw-frontier-store-"));
  try { await fn(new FrontierStore(dir, () => 713), dir); }
  finally { await rm(dir, { recursive: true, force: true }); }
}
const counts = (attempts = 2) => ({ training: 24, development: 12, admission: 12, attempts });
const load = async (path: string) => JSON.parse(await readFile(path, "utf8"));

test("a real campaign freezes candidate before private evaluation, with source-bound errors and rollback", async () => fixture(async (store, dir) => {
  const initialized = await store.initialize("flow", RULES.tictactoe, counts());
  assert.equal(initialized.manifest.alphaPerAttempt, 0.025);
  assert.equal(JSON.stringify(initialized).includes('"history"'), false); // No final case payloads returned.
  await assert.rejects(store.admit("flow", 1));
  const options = { passes: 8, rate: 0.2, margin: 0.1 }, pending = store.run("flow", options);
  options.rate = 1; // The caller cannot change the already selected experiment.
  const result = await pending;
  const attempt = join(dir, "campaigns", "flow", "attempts", "01");
  assert.equal(result.promotion, "not-authorized"); assert.equal(result.status, "ready-for-admission");
  const practice = await load(join(attempt, "practice.json"));
  assert.equal(practice.options.rate, 0.2);
  assert.ok(practice.errors.length); assert.ok(practice.updates.length);
  assert.equal(practice.identity, initialized.manifest.identity);
  const rollback = await load(join(attempt, "rollback.json"));
  assert.equal(rollback.selected, initialized.manifest.incumbent);
  const before = await readFile(join(attempt, "candidate.json"), "utf8");
  const admission = await store.admit("flow", 1);
  assert.equal(admission.promotion, "not-authorized"); assert.equal(admission.providerCalls, 0);
  assert.equal(JSON.stringify(admission).includes('"history"'), false);
  assert.equal(JSON.stringify(admission).includes('"rows"'), false);
  assert.equal((await store.status("flow")).attempts[0].state, "completed");
  await assert.rejects(store.admit("flow", 1), /exist|EEXIST/);
  assert.equal(await readFile(join(attempt, "candidate.json"), "utf8"), before);
  await assert.rejects(writeFile(join(attempt, "plan.json"), "{}", { flag: "wx" }), /exist|EEXIST/);
  const other = new FrontierStore(dir, () => 29117);
  const second = await other.initialize("another", RULES.tictactoe, { training: 12, development: 8, admission: 8, attempts: 1 });
  assert.notEqual(second.manifest.suites[0], initialized.manifest.suites[0]);
  const firstGroups = new Set((await load(join(dir, "vault", `${initialized.manifest.suites[0]}.json`))).cases.map((r: any) => r.group));
  const secondGroups = (await load(join(dir, "vault", `${second.manifest.suites[0]}.json`))).cases.map((r: any) => r.group);
  assert.ok(secondGroups.every((g: string) => !firstGroups.has(g)));
}));

test("concurrent runs cannot overclaim a single attempt and repeated candidates consume separate budgets", async () => fixture(async (store, dir) => {
  await store.initialize("single", RULES.connect4, counts(1));
  const results = await Promise.allSettled([store.run("single"), store.run("single")]);
  assert.equal(results.filter(r => r.status === "fulfilled").length, 1);
  assert.equal(results.filter(r => r.status === "rejected").length, 1);
  assert.equal((await readdir(join(dir, "campaigns", "single", "attempts"))).length, 1);
  await assert.rejects(store.run("single"), /budget exhausted/);
  const another = new FrontierStore(dir, () => 888);
  const initialized = await another.initialize("double", RULES.connect4, counts(2));
  const first = await another.run("double"), second = await another.run("double");
  assert.equal(first.candidate, second.candidate); // Duplicate candidate is still charged two attempts.
  assert.equal(initialized.manifest.alphaPerAttempt, 0.025);
  assert.equal((await readdir(join(dir, "spent"))).length, 3);
}));

test("interrupted reservations and evaluations remain spent; malformed completion is not success", async () => fixture(async (store, dir) => {
  await store.initialize("crash", RULES.tictactoe, counts());
  const root = join(dir, "campaigns", "crash", "attempts");
  await mkdir(join(root, "01")); // Simulated crash immediately after exclusive slot allocation.
  assert.equal((await store.status("crash")).attempts[0].state, "reserved-or-interrupted");
  await assert.rejects(store.admit("crash", 1));
  const run = await store.run("crash"); assert.equal(run.slot, 2);
  await writeFile(join(root, "02", "evaluation-started.json"), "{}", { flag: "wx" });
  await assert.rejects(store.admit("crash", 2), /exist|EEXIST/);
  assert.equal((await store.status("crash")).attempts[1].state, "admission-spent-without-result");
  await writeFile(join(root, "02", "admission-result.json"), '{"status":"completed"', { flag: "wx" });
  assert.equal((await store.status("crash")).attempts[1].state, "invalid-completion");
  await assert.rejects(store.run("crash"), /budget exhausted/);
}));

test("wrong partitions, changed source contracts and corrupt candidates fail closed before admission", async () => fixture(async (store, dir) => {
  const initialized = await store.initialize("corrupt", RULES.connect4, counts());
  const root = join(dir, "campaigns", "corrupt");
  await assert.rejects(store.run("corrupt", { passes: 0, rate: 0.2, margin: 0.1 }), /passes/);
  assert.equal((await store.status("corrupt")).attempts[0].state, "unclaimed");
  const trainPath = join(root, "training.json"), original = await readFile(trainPath, "utf8");
  await writeFile(trainPath, await readFile(join(root, "development.json"), "utf8"));
  await assert.rejects(store.run("corrupt"), /commitment/);
  assert.equal((await store.status("corrupt")).attempts[0].state, "failed-spent");
  await writeFile(trainPath, original);
  const run = await store.run("corrupt"); assert.equal(run.slot, 2);
  const versionPath = join(dir, "versions", `${run.candidate}.json`), candidate = await load(versionPath);
  candidate.config.runtime.resolvedModel = "other-provider";
  await writeFile(versionPath, JSON.stringify(candidate));
  await assert.rejects(store.admit("corrupt", 2), /configuration|identity|digest/);
  await assert.rejects(readFile(join(root, "attempts", "02", "evaluation-started.json")));
  const changed = structuredClone(initialized.manifest); changed.source = "0".repeat(64);
  const { digest: _digest, ...body } = changed; changed.digest = await sha256(JSON.stringify(body));
  await writeFile(join(root, "manifest.json"), JSON.stringify(changed));
  assert.equal((await store.status("corrupt")).executionCompatible, false);
  await assert.rejects(store.run("corrupt"), /source changed/);
  await assert.rejects(store.admit("corrupt", 2), /source changed/);
  assert.equal((await store.close("corrupt")).retired, true);
}));

test("explicit retirement blocks future training/admission; CLI rejects invalid options and paths", async () => fixture(async (store, dir) => {
  await store.initialize("retire", RULES.tictactoe, counts(1));
  await store.run("retire"); await store.close("retire");
  assert.equal((await store.status("retire")).closed, true);
  await assert.rejects(store.run("retire"), /closed/); await assert.rejects(store.admit("retire", 1), /cannot enter/);
  await assert.rejects(store.initialize("retire", RULES.tictactoe, counts(1)), /exist|EEXIST/);
  await assert.rejects(store.status("../escape"), /slug/);
  await assert.rejects(frontier(["run", "--id", "x", "--id", "y"]), /duplicate/);
  await assert.rejects(frontier(["run", "--secret", "x"]), /Unknown/);
  const unrelated = join(dir, "unrelated"); await mkdir(unrelated); await writeFile(join(unrelated, "keep.txt"), "keep");
  await assert.rejects(new FrontierStore(unrelated).status("x"), /not an initialized/);
  assert.equal(await readFile(join(unrelated, "keep.txt"), "utf8"), "keep");
}));
