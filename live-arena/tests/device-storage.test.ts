import test from "node:test";
import assert from "node:assert/strict";
import { DeviceStorage } from "../src/device-storage";
import { NativeCheckpoint, type CheckpointPort } from "../src/native-checkpoint";
import { MatchLibrary, LIBRARY_PREFIX, LIBRARY_OPT_OUT, MAX_SAVED, MAX_LIBRARY_BYTES } from "../src/library";
import { PracticeMemory, MEMORY_KEY } from "../src/learning";
import { RULES, type RecordData } from "../src/runtime";
import { publicAgent, type Agent } from "../src/models";

class Legacy {
  data = new Map<string, string>();
  failRemove = false;
  get length() { return this.data.size; }
  key(i: number) { return [...this.data.keys()][i] ?? null; }
  getItem(k: string) { return this.data.get(k) ?? null; }
  setItem(k: string, v: string) { this.data.set(k, v); }
  removeItem(k: string) { if (this.failRemove) throw Error("Denied"); this.data.delete(k); }
}
class Disk implements CheckpointPort {
  files = new Map<string, string>();
  fail = false;
  hold: Promise<void> = Promise.resolve();
  async list() { return [...this.files].map(([name, text]) => ({ name, type: "file", size: new TextEncoder().encode(text).byteLength })); }
  async read(name: string) { return this.files.get(name)!; }
  async write(name: string, text: string) { await this.hold; if (this.fail) throw Error("Full"); this.files.set(name, text); }
  async promote(from: string, to: string) { this.files.set(to, this.files.get(from)!); this.files.delete(from); }
  async remove(name: string) { this.files.delete(name); }
}
const players: Agent[] = [0, 1].map(i => ({ name: `Learner ${i}`, kind: "openrouter", model: "test/model", effort: "default", strategy: "", endpoint: "", key: "PRIVATE_KEY" }));
function game(moves = ["0", "3"], id = "test-game"): RecordData {
  return { schema: "builderwars.exhibition.v1", id, createdAt: new Date().toISOString(), rules: RULES.tictactoe,
    agents: players.map(publicAgent), status: "Playing", events: moves.map((move, i) => ({ move, ply: i + 1, seat: (i % 2) as 0 | 1, label: "", comment: "", model: "test/model", elapsed: 1, tokens: null, cost: null })) };
}

test("native migration sanitizes matches and preserves memory, retention and opt-out", async () => {
  const legacy = new Legacy(), disk = new Disk();
  const old = new MatchLibrary(legacy); old.save(game(), "own", 80);
  const entry = old.list()[0], raw = JSON.parse(legacy.getItem(entry.key)!);
  raw.privateExtra = "PRIVATE_EXTRA"; legacy.setItem(entry.key, JSON.stringify(raw));
  legacy.setItem(`${LIBRARY_PREFIX}invalid`, "invalid"); legacy.setItem("unrelated", "keep");
  await new PracticeMemory(legacy).remember(game(["0", "3", "1", "4", "8", "5"]), players);
  old.setEnabled(false);
  const device = await DeviceStorage.open(disk, legacy), migrated = new MatchLibrary(device);
  assert.equal(migrated.list()[0].savedAt, entry.savedAt);
  assert.equal(migrated.enabled(), false);
  assert.equal(new PracticeMemory(device).episodeCount, new PracticeMemory(legacy).episodeCount);
  assert(!JSON.stringify([...disk.files.values()]).includes("PRIVATE_"));
  assert.equal(legacy.getItem(`${LIBRARY_PREFIX}invalid`), "invalid");
  assert.equal(legacy.getItem("unrelated"), "keep");
});

test("game and practice memory survive a fresh process only after native acknowledgement", async () => {
  const disk = new Disk(), legacy = new Legacy(), device = await DeviceStorage.open(disk, legacy);
  const library = new MatchLibrary(device), memory = new PracticeMemory(device);
  library.save(game(), "own", 80);
  await memory.remember(game(["0", "3", "1", "4", "8", "5"]), players);
  let release!: () => void; disk.hold = new Promise<void>(r => { release = r; });
  let acknowledged = false; const saving = device.flush().then(() => { acknowledged = true; });
  await Promise.resolve(); assert.equal(acknowledged, false); assert.equal(device.status, "saving");
  release(); await saving;
  const reopened = await DeviceStorage.open(disk, legacy);
  assert.equal(new MatchLibrary(reopened).list()[0].record.events.length, 2);
  assert(new PracticeMemory(reopened).episodeCount > 0);
  assert.equal(device.status, "saved");
});

test("coalesces pending snapshots and retains a clear-then-readd erasure barrier", async () => {
  const disk = new Disk(), legacy = new Legacy(), device = await DeviceStorage.open(disk, legacy);
  device.setItem(MEMORY_KEY, "old lesson"); await device.flush();
  let release!: () => void; disk.hold = new Promise<void>(r => { release = r; });
  device.setItem(LIBRARY_OPT_OUT, "1"); const first = device.flush();
  device.removeItem(MEMORY_KEY); device.setItem(MEMORY_KEY, "new lesson");
  const pending = [first];
  for (let i = 0; i < 40; i++) { device.setItem(MEMORY_KEY, `new lesson ${i}`); pending.push(device.flush()); }
  release(); await Promise.all(pending);
  assert.equal((await NativeCheckpoint.open(disk)).snapshot()[MEMORY_KEY], "new lesson 39");
  assert(![...disk.files.values()].some(text => text.includes("old lesson")));
  assert.equal(disk.files.size, 1);
});

test("native failures stay dirty for explicit retry and corrupt native history never imports legacy", async () => {
  const disk = new Disk(), legacy = new Legacy(), device = await DeviceStorage.open(disk, legacy);
  device.setItem(MEMORY_KEY, "lesson"); disk.fail = true;
  await assert.rejects(device.flush()); assert.equal(device.status, "unavailable");
  assert.equal((await NativeCheckpoint.open(disk)).snapshot()[MEMORY_KEY], undefined);
  disk.fail = false; await device.flush(); assert.equal(device.status, "saved");
  for (const name of disk.files.keys()) disk.files.set(name, "corrupt");
  new MatchLibrary(legacy).save(game(), "own", 80);
  await assert.rejects(DeviceStorage.open(disk, legacy));
});

test("flush covers a mutation queued after drain exits but before its finally clears", async () => {
  const disk = new Disk(), device = await DeviceStorage.open(disk, new Legacy());
  const internal = device as unknown as { drain(): Promise<void> };
  const original = internal.drain.bind(device);
  let once = true, second!: Promise<void>;
  // Deterministic white-box seam: queue the caller before flush attaches finally.
  internal.drain = () => {
    const done = original();
    if (once) {
      once = false;
      void done.then(() => { device.setItem(MEMORY_KEY, "second"); second = device.flush(); });
    }
    return done;
  };
  device.setItem(MEMORY_KEY, "first"); await device.flush(); await second;
  assert.equal((await NativeCheckpoint.open(disk)).snapshot()[MEMORY_KEY], "second");
});

test("explicit erasure retry switches a failed store to saving before acknowledgement", async () => {
  const disk = new Disk(), device = await DeviceStorage.open(disk, new Legacy());
  device.setItem(MEMORY_KEY, "saved lesson"); await device.flush();
  disk.fail = true; device.setItem(MEMORY_KEY, "new lesson");
  await assert.rejects(device.flush());
  device.removeItem(MEMORY_KEY);
  assert.equal(device.status, "unavailable");
  let release!: () => void; disk.hold = new Promise<void>(r => { release = r; }); disk.fail = false;
  const saving = device.flush();
  assert.equal(device.status, "saving");
  release(); await saving;
  assert.equal(device.status, "saved");
  assert.equal((await NativeCheckpoint.open(disk)).snapshot()[MEMORY_KEY], undefined);
});

test("full library byte/count caps plus near-limit practice memory and opt-out fit one native checkpoint", async () => {
  const disk = new Disk(), device = await DeviceStorage.open(disk, new Legacy()), library = new MatchLibrary(device);
  for (let i = 0; i < MAX_SAVED; i++) assert(library.save(game(undefined, `capacity-${i}`), "own", 80));
  // JSON whitespace is accepted legacy data: exercise the actual library budget,
  // including one record at its 355000-character individual ceiling.
  const keys = library.keys();
  keys.forEach((key, i) => device.setItem(key, device.getItem(key)!.padEnd(i === 0 ? 355000 : Math.floor((MAX_LIBRARY_BYTES / 2 - 355000) / (MAX_SAVED - 1)))));
  assert.equal(library.list().length, MAX_SAVED);
  const mistake = { kind: "allowed-immediate-loss", ply: 42, seat: 1, played: "41", better: Array(42).fill("41"), position: Array(42).fill("w") };
  const snapshot = { schema: MEMORY_KEY, episodes: Array.from({length:64}, () => ({profile:"a".repeat(64),source:"b".repeat(64),rules:"r".repeat(100),mistakes:Array(8).fill(mistake)})) };
  while (JSON.stringify(snapshot).length > 256000) snapshot.episodes.find(e => e.mistakes.length)!.mistakes.pop();
  assert(JSON.stringify(snapshot).length > 255000);
  device.setItem(MEMORY_KEY, JSON.stringify(snapshot)); library.setEnabled(false);
  assert.equal(new PracticeMemory(device).episodeCount, 64);
  assert.equal(device.length, 22);
  await device.flush();
  const reopened = await DeviceStorage.open(disk, new Legacy());
  assert.equal(new MatchLibrary(reopened).list().length, MAX_SAVED);
  assert.equal(new PracticeMemory(reopened).episodeCount, 64);
  assert.equal(new MatchLibrary(reopened).enabled(), false);
});

test("max-length Unicode replay IDs migrate and oversized writes cannot poison healthy storage", async () => {
  const disk = new Disk(), legacy = new Legacy();
  assert(new MatchLibrary(legacy).save(game(undefined, "界".repeat(80)), "own", 80));
  const device = await DeviceStorage.open(disk, legacy);
  assert.equal(new MatchLibrary(device).list().length, 1);
  assert.throws(() => device.setItem(MEMORY_KEY, "x".repeat(256001)));
  await device.flush();
  assert.equal(device.status, "saved");
  assert.equal(new MatchLibrary(await DeviceStorage.open(disk, legacy)).list().length, 1);
});

test("forget removes native and legacy copies without reimport, preserves saving opt-out and unrelated data", async () => {
  const disk = new Disk(), legacy = new Legacy(); new MatchLibrary(legacy).save(game(), "own", 80);
  legacy.setItem(`${LIBRARY_PREFIX}invalid`, "invalid"); legacy.setItem("other", "keep");
  const device = await DeviceStorage.open(disk, legacy);
  new MatchLibrary(device).forget(); device.forgetLegacyMatches();
  legacy.failRemove = true; await device.flush(); assert.equal(device.status, "cleanup-pending");
  legacy.failRemove = false; await device.flush();
  const reopened = await DeviceStorage.open(disk, legacy);
  assert.equal(new MatchLibrary(reopened).list().length, 0);
  assert.equal(new MatchLibrary(reopened).enabled(), false);
  assert.deepEqual([...legacy.data.keys()], ["other"]);
  assert(![...disk.files.values()].some(text => text.includes("test-game")));
  reopened.removeItem(MEMORY_KEY); await reopened.flush();
  assert.equal((await NativeCheckpoint.open(disk)).snapshot()[LIBRARY_OPT_OUT], "1");
});
