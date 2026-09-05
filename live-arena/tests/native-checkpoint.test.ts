import { test } from "node:test";
import assert from "node:assert/strict";
import { NativeCheckpoint, type CheckpointPort } from "../src/native-checkpoint";

const key = "builderwars.match.v1:own:fixture";
class Disk implements CheckpointPort {
  files = new Map<string, string>();
  failWrite = false;
  partialWrite = false;
  failPromotion = false;
  failCleanup = false;
  async list() { return [...this.files].map(([name, text]) => ({ name, type: "file", size: new TextEncoder().encode(text).byteLength })); }
  async read(name: string) { if (!this.files.has(name)) throw Error("Missing file"); return this.files.get(name)!; }
  async write(name: string, text: string) {
    if (this.failWrite) throw Error("Disk full");
    this.files.set(name, this.partialWrite ? text.slice(0, 40) : text);
  }
  async promote(from: string, to: string) {
    if (this.failPromotion) throw Error("Rename failed");
    assert(!this.files.has(to));
    this.files.set(to, await this.read(from)); this.files.delete(from);
  }
  async remove(name: string) { if (this.failCleanup) throw Error("Delete denied"); this.files.delete(name); }
}
test("acknowledged checkpoint survives a fresh store with the exact latest values", async () => {
  const disk = new Disk(), store = await NativeCheckpoint.open(disk);
  assert.equal(store.hasCheckpoint, false);
  await store.save({ [key]: "one move" });
  await store.save({ [key]: "two moves", "builderwars.practice-memory.v1": "lessons" });
  assert.deepEqual((await NativeCheckpoint.open(disk)).snapshot(), { [key]: "two moves", "builderwars.practice-memory.v1": "lessons" });
});
test("partial writes and failed promotions preserve the previous committed checkpoint", async () => {
  for (const failure of ["failWrite", "partialWrite", "failPromotion"] as const) {
    const disk = new Disk(), store = await NativeCheckpoint.open(disk);
    await store.save({ [key]: "one" }); disk[failure] = true;
    await assert.rejects(store.save({ [key]: "two" }));
    assert.deepEqual((await NativeCheckpoint.open(disk)).snapshot(), { [key]: "one" });
    disk[failure] = false;
    await store.save({ [key]: "retry" });
    assert.deepEqual((await NativeCheckpoint.open(disk)).snapshot(), { [key]: "retry" });
  }
});
test("queued writes retain submission order and cannot capture later caller mutations", async () => {
  const disk = new Disk(), store = await NativeCheckpoint.open(disk);
  const value = { [key]: "first" };
  const first = store.save(value); value[key] = "second";
  const second = store.save(value); value[key] = "unsaved";
  assert.deepEqual((await Promise.all([first, second])).map(r => r.revision), [1, 2]);
  assert.deepEqual((await NativeCheckpoint.open(disk)).snapshot(), { [key]: "second" });
});
test("save cannot acknowledge before promotion completes", async () => {
  const disk = new Disk(); let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  const promote = disk.promote.bind(disk);
  disk.promote = async (from, to) => { await gate; await promote(from, to); };
  const store = await NativeCheckpoint.open(disk); let acknowledged = false;
  const save = store.save({ [key]: "two" }).then(() => { acknowledged = true; });
  await new Promise(resolve => setTimeout(resolve, 10));
  assert.equal(acknowledged, false);
  assert.equal((await NativeCheckpoint.open(disk)).hasCheckpoint, false);
  release(); await save;
  assert.equal(acknowledged, true);
});
test("empty committed checkpoint prevents legacy resurrection; corrupt newest fails closed", async () => {
  const disk = new Disk(), store = await NativeCheckpoint.open(disk);
  await store.save({ [key]: "forgotten" }); await store.save({});
  const empty = await NativeCheckpoint.open(disk);
  assert.equal(empty.hasCheckpoint, true); assert.deepEqual(empty.snapshot(), {});
  assert.equal(disk.files.size, 1, "forgotten data cannot remain in a previous checkpoint");
  const newest = [...disk.files.keys()].find(name => name.startsWith("checkpoint-2-"))!;
  disk.files.set(newest, "corrupt");
  await assert.rejects(NativeCheckpoint.open(disk));
});
test("retention only removes older owned committed files and reports cleanup failure", async () => {
  const disk = new Disk(), store = await NativeCheckpoint.open(disk);
  disk.files.set("unrelated-user-file", "preserve");
  for (let i = 1; i <= 4; i++) await store.save({ [key]: String(i) });
  assert.equal(disk.files.size, 3); assert.equal(disk.files.get("unrelated-user-file"), "preserve");
  disk.failCleanup = true;
  const receipt = await store.save({ [key]: "5" });
  assert.equal(receipt.cleanupFailures, 1);
  assert.deepEqual((await NativeCheckpoint.open(disk)).snapshot(), { [key]: "5" });
});
test("scope, size, and ambiguous writer history are rejected without mutation", async () => {
  const disk = new Disk(), store = await NativeCheckpoint.open(disk);
  await assert.rejects(store.save({ "provider-key": "do not persist" }));
  await assert.rejects(store.save({ [key]: "x".repeat(355001) }));
  assert.equal(disk.files.size, 0);
  await store.save({ [key]: "one" });
  const [name, data] = [...disk.files][0];
  disk.files.set(name.replace(/[a-f0-9-]{36}(?=\.json$)/, "00000000-0000-0000-0000-000000000000"), data);
  await assert.rejects(NativeCheckpoint.open(disk), /Ambiguous/);
});
test("structural readback tolerates surrounding whitespace but rejects payload mutation", async () => {
  const disk = new Disk(); const read = disk.read.bind(disk);
  disk.read = async name => `${await read(name)}\n`;
  const store = await NativeCheckpoint.open(disk);
  await store.save({ [key]: "one" });
  assert.deepEqual((await NativeCheckpoint.open(disk)).snapshot(), { [key]: "one" });
  disk.read = async name => (await read(name)).replace("one", "two");
  await assert.rejects(store.save({ [key]: "one" }), /integrity/);
});
test("stale partial files are reclaimed only through a committed revision", async () => {
  const disk = new Disk(), store = await NativeCheckpoint.open(disk);
  const stale = "checkpoint-1-00000000-0000-0000-0000-000000000000.json.part";
  const future = stale.replace("checkpoint-1-", "checkpoint-9-");
  disk.files.set(stale, "interrupted"); disk.files.set(future, "potentially in flight");
  await store.save({ [key]: "one" });
  assert.equal(disk.files.has(stale), false); assert.equal(disk.files.has(future), true);
});
test("erasure cleanup failure is reported and retried across restart", async () => {
  const disk = new Disk(), store = await NativeCheckpoint.open(disk);
  await store.save({ [key]: "private old game" }); disk.failCleanup = true;
  assert.equal((await store.save({})).cleanupFailures, 1);
  const pending = await NativeCheckpoint.open(disk);
  assert.equal(pending.cleanupFailures, 1); assert.deepEqual(pending.snapshot(), {});
  disk.failCleanup = false;
  const recovered = await NativeCheckpoint.open(disk);
  assert.equal(recovered.cleanupFailures, 0); assert.equal(disk.files.size, 1);
  assert(![...disk.files.values()].some(text => text.includes("private old game")));
});
test("queued checkpoint memory is bounded and recovers after pending writes settle", async () => {
  const disk = new Disk(), store = await NativeCheckpoint.open(disk);
  const pending = Array.from({ length: 16 }, (_, i) => store.save({ [key]: String(i) }));
  await assert.rejects(store.save({ [key]: "overflow" }), /queue is full/);
  await Promise.all(pending);
  await store.save({ [key]: "after queue" });
  assert.equal(store.snapshot()[key], "after queue");
});
