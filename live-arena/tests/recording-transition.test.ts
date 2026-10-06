import test from "node:test";
import assert from "node:assert/strict";
import { RecordingTransitions, recordingError, recordingRecoveryMessage } from "../src/recording-transition";
import { RULES, replay, createProof, verifyProof, refereeManifest, encodeReplay, decodeReplay } from "../src/runtime";
import { readMatchFile, makeMatchPackage, unknownDeclarations } from "../src/match-package";
import { MatchLibrary, LIBRARY_OPT_OUT, canResume } from "../src/library";
import { readExhibition } from "../src/exhibition";
import { exhibitionFixture } from "./fixtures/exhibition";
import type { RecordData } from "../src/records";

function fixture(id = "current"): RecordData {
  return { schema: "builderwars.exhibition.v1", id, createdAt: "2026-10-05T00:00:00Z", rules: RULES.connect4, status: "Paused",
    agents: [0, 1].map(i => ({ name: `Seat ${i}`, kind: "bot", model: "tactician", effort: "default", strategy: "" })),
    events: [{ ply: 1, seat: 0, move: "0", label: "", comment: "", model: "tactician", elapsed: 0, tokens: null, cost: null }] };
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(r => { resolve = r; });
  return { promise, resolve };
}
class Storage {
  data = new Map<string, string>();
  fail = false;
  get length() { return this.data.size; }
  key(i: number) { return [...this.data.keys()][i] ?? null; }
  getItem(key: string) { return this.data.get(key) ?? null; }
  setItem(key: string, value: string) { if (this.fail) throw Error("Quota exceeded"); this.data.set(key, value); }
  removeItem(key: string) { this.data.delete(key); }
}
function harness() {
  const storage = new Storage(), library = new MatchLibrary(storage);
  const h = {
    current: fixture(), settings: { moveLimit: 80, maxTokens: 2048 }, revision: 0, ticket: 0,
    busy: false, unfinished: true, saves: 0, prompts: [] as boolean[], commits: 0,
    consent: async () => true, save: async () => library.save(h.current, "own", 80),
    dismiss: () => {},
  };
  const transitions = new RecordingTransitions({
    guard: () => {
      const ticket = ++h.ticket, revision = h.revision, current = h.current, settings = JSON.stringify(h.settings);
      if (h.busy) throw Error("Pause the current match before importing.");
      return () => {
        if (ticket !== h.ticket || revision !== h.revision || current !== h.current || settings !== JSON.stringify(h.settings) || h.busy)
          throw Error("The match changed during import.");
      };
    },
    unfinished: () => h.unfinished,
    save: async () => { h.saves++; return h.save(); },
    confirm: async saved => { h.prompts.push(saved); return h.consent(); },
    dismissPrompt: () => h.dismiss(),
  });
  return { h, storage, library, open: <T>(prepare: () => T | Promise<T>, requested?: () => void) => transitions.open(prepare, value => {
    h.commits++; h.current = (value as { record: RecordData }).record;
  }, requested) };
}

test("validated replacement saves a resumable free match before consent and commits once", async () => {
  const { h, library, open } = harness(), incoming = fixture("incoming");
  h.consent = async () => {
    assert.equal(h.current.id, "current");
    assert.equal(library.list()[0].record.id, "current");
    assert.equal(canResume(library.list()[0]), true);
    return true;
  };
  assert.equal(await open(() => replay(incoming)), true);
  assert.equal(h.current.id, "incoming"); assert.equal(h.commits, 1);
  assert.deepEqual(h.prompts, [true]);
});

test("dismissal preserves the exact current record and settings", async () => {
  const { h, open } = harness(), current = h.current, settings = structuredClone(h.settings);
  h.consent = async () => false;
  assert.equal(await open(() => replay(fixture("incoming"))), false);
  assert.equal(h.current, current); assert.deepEqual(h.settings, settings); assert.equal(h.commits, 0);
});

test("illegal recording is rejected before saving or asking, with import-specific error", async () => {
  const { h, open } = harness(), current = h.current, bad = fixture("invalid");
  bad.events[0].move = "99";
  await assert.rejects(open(() => readMatchFile(bad).parsed), error => {
    assert.equal(recordingError("Recording import", error), "Recording import rejected: The recording contains an illegal move.");
    return true;
  });
  assert.equal(h.current, current); assert.equal(h.saves, 0); assert.deepEqual(h.prompts, []); assert.equal(h.commits, 0);
});

test("opt-out is respected and recovery warning never claims saving succeeded", async () => {
  const { h, storage, open } = harness(); storage.data.set(LIBRARY_OPT_OUT, "1");
  h.consent = async () => false;
  await open(() => replay(fixture("incoming")));
  assert.deepEqual(h.prompts, [false]); assert.equal(storage.getItem(LIBRARY_OPT_OUT), "1");
  assert.equal(storage.data.size, 1); assert.match(recordingRecoveryMessage(false), /Download/);
  assert.doesNotMatch(recordingRecoveryMessage(false), /Saved in Recent/);
});

test("quota failure keeps prior saves and requires informed consent to open", async () => {
  const { h, storage, library, open } = harness(); library.save(fixture("older"), "own", 80);
  const prior = [...storage.data]; storage.fail = true;
  assert.equal(await open(() => replay(fixture("incoming"))), true);
  assert.deepEqual(h.prompts, [false]); assert.deepEqual([...storage.data], prior);
  assert.equal(h.current.id, "incoming");
});

test("finished or empty workspace opens without saving or confirmation", async () => {
  const { h, open } = harness(); h.unfinished = false;
  await open(() => replay(fixture("incoming")));
  assert.equal(h.saves, 0); assert.deepEqual(h.prompts, []); assert.equal(h.commits, 1);
});

test("running or pending match refuses recording preparation without interruption", async () => {
  const { h, open } = harness(); h.busy = true; let prepared = false;
  await assert.rejects(open(() => { prepared = true; return replay(fixture()); }), /Pause/);
  assert.equal(prepared, false); assert.equal(h.busy, true); assert.equal(h.commits, 0);
});

test("match or settings changes during validation prevent all recovery/commit actions", async () => {
  for (const change of [(h: ReturnType<typeof harness>["h"]) => { h.current = fixture("new-game"); },
    (h: ReturnType<typeof harness>["h"]) => { h.settings.maxTokens = 4096; }]) {
    const { h, open } = harness(), read = deferred<ReturnType<typeof replay>>();
    const importing = open(() => read.promise); change(h); const latest = h.current;
    read.resolve(replay(fixture("incoming")));
    await assert.rejects(importing, /match changed/);
    assert.equal(h.current, latest); assert.equal(h.saves, 0); assert.equal(h.commits, 0);
  }
});

test("late native save cannot confirm or commit after lifecycle/settings changes", async () => {
  const { h, open } = harness(), save = deferred<boolean>(), started = deferred<void>();
  h.save = async () => { started.resolve(); return save.promise; };
  const importing = open(() => replay(fixture("incoming"))); await started.promise;
  h.revision++; save.resolve(true);
  await assert.rejects(importing, /match changed/);
  assert.deepEqual(h.prompts, []); assert.equal(h.commits, 0); assert.equal(h.current.id, "current");
});

test("a late acceptance cannot overwrite changed settings", async () => {
  const { h, open } = harness(), decision = deferred<boolean>(), shown = deferred<void>();
  h.consent = async () => { shown.resolve(); return decision.promise; };
  const importing = open(() => replay(fixture("incoming"))); await shown.promise;
  h.settings.moveLimit = 120; decision.resolve(true);
  await assert.rejects(importing, /match changed/);
  assert.equal(h.current.id, "current"); assert.equal(h.settings.moveLimit, 120); assert.equal(h.commits, 0);
});

test("superseding import wins; late older read and acceptance cannot commit", async () => {
  for (const stage of ["read", "consent"]) {
    const { h, open } = harness(), read = deferred<ReturnType<typeof replay>>(), decision = deferred<boolean>(), shown = deferred<void>();
    if (stage === "consent") h.consent = async () => { shown.resolve(); return decision.promise; };
    const old = open(() => stage === "read" ? read.promise : replay(fixture("old")));
    // Attach the rejection before superseding to avoid an unhandled rejection.
    const rejected = assert.rejects(old, /match changed/);
    if (stage === "consent") await shown.promise;
    h.dismiss = () => decision.resolve(false); h.consent = async () => true;
    await open(() => replay(fixture("newer")));
    read.resolve(replay(fixture("old"))); decision.resolve(true); await rejected;
    assert.equal(h.current.id, "newer"); assert.equal(h.commits, 1);
  }
});

test("changed replay URL is checked again after consent", async () => {
  const { h, open } = harness(); let hash = "requested";
  h.consent = async () => { hash = "different"; return true; };
  await assert.rejects(open(() => replay(fixture("incoming")), () => { if (hash !== "requested") throw Error("No longer requested"); }), /No longer requested/);
  assert.equal(h.current.id, "current"); assert.equal(h.commits, 0);
});

test("file, package, link, exact-referee proof and exhibition prepare through the same consent boundary", async () => {
  const record = fixture("incoming"), proof = await createProof(record, refereeManifest.digest, 80, "reverified_import"), encoded = await encodeReplay(record);
  const exhibition = await exhibitionFixture(["e2e4"], 2, "failed");
  const prepares = [
    () => readMatchFile(record).parsed,
    () => readMatchFile(makeMatchPackage(record, unknownDeclarations(), null)).parsed,
    () => decodeReplay(encoded),
    () => verifyProof(proof, refereeManifest.digest),
    async () => replay((await readExhibition(exhibition)).record),
  ];
  for (const prepare of prepares) {
    const { h, open } = harness(); h.consent = async () => false;
    assert.equal(await open(prepare), false);
    assert.deepEqual(h.prompts, [true]); assert.equal(h.current.id, "current"); assert.equal(h.commits, 0);
  }
});
