import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, rm, mkdir, writeFile, readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { FrontierStore } from "../scripts/frontier-store";
import { readBounded, writeOnce, publicStrategicComparison } from "../scripts/frontier-compare";
import { RULES } from "../src/runtime";

test("comparison artifacts are bounded/create-only and public replay reservations fail closed", async () => {
  const root = await mkdtemp(join(tmpdir(), "bw-fullgame-"));
  try {
    const artifact = join(root, "once.json"); await writeOnce(artifact, { retained: true });
    await assert.rejects(writeOnce(artifact, {}), /EEXIST/);
    assert.deepEqual(await readBounded(artifact), { retained: true });
    await assert.rejects(readBounded(artifact, 1), /bounded/);
    await assert.rejects(writeOnce(join(root, "large.json"), "x".repeat(2000001)), /megabytes/);
    const storePath = join(root, "store"), store = new FrontierStore(storePath);
    await store.publicPracticeExclusions();
    // Synthetic reservation marker, not a production evaluator payload.
    const privateGroup = "a".repeat(64), publicGroup = "b".repeat(64);
    await writeFile(join(storePath, "groups", `${privateGroup}.json`), JSON.stringify({ group: privateGroup, kind: "admission", owner: "test" }));
    await assert.rejects(store.recordPublicGroups(new Set([publicGroup, privateGroup]), "test"), /reserved private target/);
    await assert.rejects(readFile(join(storePath, "groups", `${publicGroup}.json`)));
    await store.recordPublicGroups(new Set([publicGroup]), "test");
    await store.recordPublicGroups(new Set([publicGroup]), "repeat-public");
    const imported = new FrontierStore(join(root, "import"));
    assert.deepEqual(await imported.importGroupReservations(storePath), { public: 1, private: 1, payloadsRead: false });
    assert.deepEqual([...(await imported.publicPracticeExclusions())], [privateGroup]);
    const conflict = new FrontierStore(join(root, "conflict"));
    await conflict.recordPublicGroups(new Set([privateGroup]), "test");
    await assert.rejects(conflict.importGroupReservations(storePath), /conflict/);
    const output = join(root, "existing-output"); await mkdir(output);
    await assert.rejects(publicStrategicComparison(RULES.tictactoe, output), /EEXIST/);
    await assert.rejects(publicStrategicComparison(RULES.tictactoe, join(root, "invalid-count"), 1), /trials/);
    const expired = join(root, "expired");
    await assert.rejects(publicStrategicComparison(RULES.tictactoe, expired, 16, 713, join(root, "deadline-store"), [], 1), /deadline|budget/);
    assert.equal((await readBounded(join(expired, "failed.json"))).promotion, "not-authorized");
    await assert.rejects(readFile(join(expired, "result.json")));
  } finally { await rm(root, { recursive: true, force: true }); }
});
