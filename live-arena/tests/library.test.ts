import test from "node:test";
import assert from "node:assert/strict";
import {
  MatchLibrary,
  canResume,
  LIBRARY_PREFIX,
  MAX_SAVED,
  RETENTION_MS,
} from "../src/library";
import { RULES } from "../src/games";
import { type RecordData } from "../src/records";

class MemoryStorage {
  data = new Map<string, string>();
  get length() {
    return this.data.size;
  }
  key(i: number) {
    return [...this.data.keys()][i] ?? null;
  }
  getItem(key: string) {
    return this.data.get(key) ?? null;
  }
  setItem(key: string, value: string) {
    this.data.set(key, value);
  }
  removeItem(key: string) {
    this.data.delete(key);
  }
}
function record(id = "test"): RecordData {
  return {
    schema: "builderwars.exhibition.v1",
    id,
    createdAt: new Date().toISOString(),
    rules: RULES.tictactoe,
    status: "Playing",
    agents: [0, 1].map((i) => ({
      name: `Bot ${i}`,
      kind: "bot",
      model: "random",
      effort: "default",
      strategy: "",
    })),
    events: [
      {
        ply: 1,
        seat: 0,
        move: "0",
        label: "0",
        elapsed: 2,
        cost: 0,
        tokens: null,
        model: "random",
        comment: "",
      },
    ],
  };
}

test("library saves validated evidence without connection or unknown fields", () => {
  const storage = new MemoryStorage();
  const library = new MatchLibrary(storage);
  const raw = record() as any;
  raw.agents[0].key = "secret";
  raw.agents[0].endpoint = "https://private.example";
  raw.secret = "other-secret";
  raw.events[0].accessToken = "bad";
  library.save(raw, "own", 40);
  const entry = library.list()[0];
  assert.equal(entry.record.events.length, 1);
  assert(!JSON.stringify([...storage.data.values()]).includes("secret"));
  assert(!JSON.stringify([...storage.data.values()]).includes("endpoint"));
  assert(canResume(entry));
});
test("untrusted replay and connected-agent games cannot start provider calls on recovery", () => {
  const library = new MatchLibrary(new MemoryStorage());
  library.save(record(), "replay", 40);
  assert(!canResume(library.list()[0]));
  const remote = record("remote");
  remote.agents[0].kind = "openrouter";
  library.save(remote, "own", 40);
  assert(!canResume(library.list().find((e) => e.record.id === "remote")!));
  library.save(record("capped"), "own", 2);
  const capped = library.list().find((e) => e.record.id === "capped")!;
  capped.moveLimit = 1;
  assert(!canResume(capped));
});
test("invalid and expired entries cannot poison recent matches", () => {
  const storage = new MemoryStorage();
  let clock = Date.now();
  const library = new MatchLibrary(storage, () => clock);
  library.save(record("old"), "own", 40);
  clock += RETENTION_MS + 1;
  library.save(record("new"), "watch", 80, "valid-peer");
  storage.setItem(LIBRARY_PREFIX + "bad", "not JSON");
  storage.setItem(
    LIBRARY_PREFIX + "fake",
    JSON.stringify({
      record: record(),
      savedAt: clock,
      source: "own",
      moveLimit: 80,
      watchId: "",
    }),
  );
  assert.deepEqual(
    library.list().map((e) => e.record.id),
    ["new"],
  );
  assert.throws(() => library.save(record(), "watch", 80, "bad/id"));
  const illegal = record();
  illegal.events[0].move = "90";
  assert.throws(() => library.save(illegal, "own", 80));
});
test("bounded retention and deletion preserve unrelated storage", () => {
  const storage = new MemoryStorage();
  let clock = Date.now();
  storage.setItem("another-app", "keep");
  const library = new MatchLibrary(storage, () => ++clock);
  for (let i = 0; i < 30; i++) library.save(record(String(i)), "own", 80);
  assert.equal(library.list().length, MAX_SAVED);
  assert.equal(library.keys().length, MAX_SAVED);
  library.forget();
  library.save(record("after-delete"), "own", 80);
  assert.equal(library.keys().length, 0);
  assert.equal(storage.getItem("another-app"), "keep");
  assert(!library.enabled());
  library.setEnabled(true);
  library.save(record("again"), "own", 80);
  assert.equal(library.list().length, 1);
});
test("storage failures are surfaced and independent tabs merge by match key", () => {
  const storage = new MemoryStorage();
  const a = new MatchLibrary(storage),
    b = new MatchLibrary(storage);
  a.save(record("a"), "own", 80);
  b.save(record("b"), "own", 80);
  assert.equal(a.list().length, 2);
  storage.setItem = () => {
    throw Error("Quota exceeded");
  };
  assert.throws(() => a.save(record("c"), "own", 80), /Quota/);
});
test("replays cannot evict own games, and clock rollback does not delete history", () => {
  const storage = new MemoryStorage();
  let clock = Date.now();
  const library = new MatchLibrary(storage, () => clock);
  for (let i = 0; i < MAX_SAVED; i++)
    library.save(record(`own-${i}`), "own", 80);
  clock += 100;
  assert.equal(library.save(record("untrusted"), "replay", 80), false);
  assert.equal(
    library.list().filter((e) => e.source === "own").length,
    MAX_SAVED,
  );
  library.remove(library.list()[0].key);
  clock -= 120000;
  library.save(record("clock-reset"), "own", 80);
  assert.equal(library.list().length, MAX_SAVED);
  assert(library.list().some((e) => e.record.id === "own-1"));
});
test("size-bounded legacy data is not deleted just because it cannot replay", () => {
  const storage = new MemoryStorage();
  const library = new MatchLibrary(storage);
  const key = LIBRARY_PREFIX + "legacy";
  storage.setItem(
    key,
    JSON.stringify({ savedAt: Date.now(), record: { schema: "old" } }),
  );
  library.save(record(), "own", 80);
  assert(storage.getItem(key));
  assert.equal(library.list().length, 1);
});
test("a quota failure at capacity never prunes existing recoverable games", () => {
  const storage = new MemoryStorage();
  let clock = Date.now();
  const library = new MatchLibrary(storage, () => ++clock);
  for (let i = 0; i < MAX_SAVED; i++)
    library.save(record(`own-${i}`), "own", 80);
  const before = [...storage.data.entries()];
  storage.setItem = () => {
    throw Error("Quota exceeded");
  };
  assert.throws(() => library.save(record("newest"), "own", 80), /Quota/);
  assert.deepEqual([...storage.data.entries()], before);
});
