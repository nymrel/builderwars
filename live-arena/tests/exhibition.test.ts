import test from "node:test";
import assert from "node:assert/strict";
import { readExhibition, validateExhibition, sealExhibition, exhibitionDescription } from "../src/exhibition";
import { exhibitionFixture } from "./fixtures/exhibition";
import { MatchLibrary, canResume } from "../src/library";

test("exhibitions preserve unknown identity, assistance and immutable content through round trips", async () => {
  const value = await exhibitionFixture();
  assert.deepEqual(await readExhibition(JSON.parse(JSON.stringify(value))), value);
  assert.equal(value.players[0].resolvedModel, null);
  assert.equal(value.record.events[0].cost, null);
  assert.match(exhibitionDescription(value), /no winner.*Stockfish 19.*not independently attested/);
  assert.ok(Object.isFrozen(value.record.events));
  assert.throws(() => { value.engine.nodes = 40000; });
});
test("cap, failed zero-ply route and rule-terminal results remain distinct", async () => {
  const failed = await exhibitionFixture([], 2, "failed");
  assert.match(exhibitionDescription(failed), /Failed run.*0 accepted moves \/ 1 attempted/);
  assert.equal(failed.players[1].resolvedModel, null);
  const mate = await exhibitionFixture(["f2f3", "e7e5", "g2g4", "d8h4"], 1, "complete");
  assert.match(exhibitionDescription(mate), /Completed game/);
  assert.throws(() => validateExhibition({ ...failed, exit: "complete" }), /contradicts/);
  assert.throws(() => validateExhibition({ ...mate, exit: "capped" }), /contradicts/);
});
test("modified content, secret fields, false identity and usage disagreement fail closed", async () => {
  const original = await exhibitionFixture();
  const modified = structuredClone(original); modified.source.runner = "9".repeat(64);
  await assert.rejects(readExhibition(modified), /digest mismatch/);
  for (const change of [
    (v: any) => { v.secret = "private"; },
    (v: any) => { v.players[0].key = "private"; },
    (v: any) => { v.record.agents[0].strategy = "private"; },
    (v: any) => { v.record.events[0].comment = "private"; },
    (v: any) => { v.players[0].resolvedModel = "claude-fable-5-1"; v.players[0].identityEvidence = "provider-response"; },
    (v: any) => { v.decisions[0].outputTokens = 999; },
    (v: any) => { v.record.events[0].move = "e2e5"; },
    (v: any) => { v.engine.nodes = 20001; },
    (v: any) => { v.verification = "model-attested"; },
    (v: any) => { v.gameAttempts = 0; },
  ]) {
    const v = structuredClone(original); change(v);
    assert.throws(() => validateExhibition(v));
  }
  const empty = await exhibitionFixture([], 2, "failed");
  await assert.rejects(sealExhibition({ ...empty, players: [{ ...empty.players[0], resolvedModel: "grok-4.6", identityEvidence: "client-reported" }, empty.players[1]] }), /No accepted decision/);
});
class MemoryStorage {
  data = new Map<string, string>();
  get length() { return this.data.size; }
  key(i: number) { return [...this.data.keys()][i] ?? null; }
  getItem(key: string) { return this.data.get(key) ?? null; }
  setItem(key: string, value: string) { this.data.set(key, value); }
  removeItem(key: string) { this.data.delete(key); }
}
test("library retains zero-ply failures and full packages, rejects detached/malformed metadata", async () => {
  const storage = new MemoryStorage(), library = new MatchLibrary(storage), value = await exhibitionFixture([], 2, "failed");
  assert.equal(library.save(value.record, "replay", 80, "", undefined, true, undefined, true, value), true);
  let entries = new MatchLibrary(storage).list();
  assert.equal(entries.length, 1); assert.equal(canResume(entries[0]), false);
  assert.deepEqual(await readExhibition(entries[0].exhibition), value);
  const paused = { ...value.record, status: "Paused" };
  assert.equal(library.save(paused, "replay", 80, "", undefined, true, undefined, true, value), true);
  assert.throws(() => library.save({ ...value.record, id: "unrelated" }, "replay", 80, "", undefined, true, undefined, true, value), /does not match/);
  assert.throws(() => library.save(value.record, "own", 80, "", undefined, true, undefined, true, value), /does not match/);
  entries = new MatchLibrary(storage).list();
  const raw = JSON.parse(storage.getItem(entries[0].key)!); raw.exhibition.engine.key = "private";
  storage.setItem(entries[0].key, JSON.stringify(raw));
  assert.equal(new MatchLibrary(storage).list().length, 0);
});
