import test from "node:test";
import assert from "node:assert/strict";
import { FileTransfer, CACHE_TTL, CACHE_MAX_FILES, EXPORT_LIMITS, boundedResponse, transferMessage, type NativeFilePort, type CacheEntry } from "../src/file-transfer";
const now = 1788580000000, id = "11111111-1111-4111-8111-111111111111";
function fixture() {
  const files: { name: string; data: string }[] = [], removed: string[] = [], shares: unknown[] = [];
  const entries: CacheEntry[] = [];
  const port: NativeFilePort = {
    list: async () => entries,
    write: async (name, data) => { files.push({ name, data }); return `file:///cache/${name}`; },
    remove: async name => { removed.push(name); },
    share: async value => { shares.push(value); return "sheet-closed"; },
  };
  const service = new FileTransfer({ native: async () => port, webDownload: () => assert.fail("Native used web download"), now: () => now, id: () => id });
  return { files, removed, shares, entries, port, service };
}
test("native export preserves exact bytes and retains handed-off files", async () => {
  const f = fixture(), bytes = new Uint8Array([0, 13, 10, 255, 226, 130, 172]);
  assert.equal(await f.service.export("builderwars-proof.jsonl", new Blob([bytes]), "proof"), "sheet-closed");
  assert.deepEqual(Buffer.from(f.files[0].data, "base64"), Buffer.from(bytes));
  assert.equal(f.removed.length, 0);
  assert.deepEqual(f.shares[0], { files: [`file:///cache/${now}-${id}-builderwars-proof.jsonl`] });
  assert.match(transferMessage("sheet-closed"), /not confirmed/);
});
test("unsafe names and oversized bytes fail before bridge writes", async () => {
  const f = fixture();
  for (const name of ["../secret.json", "foo/bar.json", "foo\\bar.json", "file://a.json", ".hidden.json", "a..json"])
    await assert.rejects(f.service.export(name, new Blob(["x"]), "replay"), /filename/);
  await assert.rejects(f.service.export("profile.json", new Blob([new Uint8Array(EXPORT_LIMITS.profile + 1)]), "profile"), /size limit/);
  assert.equal(f.files.length, 0); assert.equal(f.shares.length, 0);
});
test("cancelled or unshared files clean up; ambiguous handoffs remain retained", async () => {
  const f = fixture();
  f.port.share = async () => "cancelled";
  assert.equal(await f.service.export("x.json", new Blob(["{}"]), "replay"), "cancelled");
  assert.equal(f.removed.length, 1);
  f.port.share = async () => { throw Error("ambiguous"); };
  await assert.rejects(f.service.export("x.json", new Blob(["{}"]), "replay"), /ambiguous/);
  assert.equal(f.removed.length, 1);
  f.port.write = async () => { throw Error("write failure"); };
  await assert.rejects(f.service.export("x.json", new Blob(["{}"]), "replay"), /write failure/);
  assert.equal(f.removed.length, 2);
});
test("cache cleanup is narrow, age-gated and fails closed on insufficient room", async () => {
  const f = fixture(), owned = `${now}-${id}-old.json`;
  f.entries.push({ name: owned, type: "file", size: 10, mtime: now - CACHE_TTL }, { name: "../private.json", type: "file", size: 10, mtime: 0 });
  await f.service.export("new.json", new Blob(["{}"]), "replay");
  assert.deepEqual(f.removed, [owned]);
  const full = fixture();
  full.entries.push(...Array.from({ length: CACHE_MAX_FILES }, () => ({ name: owned, type: "file", size: 10, mtime: now })));
  await assert.rejects(full.service.export("new.json", new Blob(["{}"]), "replay"), /temporarily full/);
  assert.equal(full.files.length, 0); assert.equal(full.removed.length, 0);
  full.entries.forEach(entry => entry.mtime = 0);
  full.port.remove = async () => { throw Error("denied"); };
  await assert.rejects(full.service.export("new.json", new Blob(["{}"]), "replay"), /temporarily full/);
});
test("one sheet at a time and foreground loss before handoff cannot resume it", async () => {
  const f = fixture();
  let finish!: (result: "sheet-closed") => void;
  f.port.share = () => new Promise(resolve => { finish = resolve; });
  const sharing = f.service.shareText("public link");
  await new Promise(resolve => setTimeout(resolve, 0));
  await assert.rejects(f.service.export("x.json", new Blob(["{}"]), "replay"), /Finish the current/);
  finish("sheet-closed"); await sharing;
  let active = true;
  const stopped = new FileTransfer({ native: async () => f.port, webDownload() {}, active: () => active, now: () => now, id: () => id });
  f.port.write = async () => { active = false; return "file:///cache/owned"; };
  await assert.rejects(stopped.export("x.json", new Blob(["{}"]), "replay"), /Return to the app/);
  assert.equal(f.removed.length, 1);
});
test("web downloads preserve bytes without native access and asset reads are bounded", async () => {
  let saved: Blob | undefined;
  const service = new FileTransfer({ webDownload: (_name, blob) => { saved = blob; } });
  assert.equal(await service.export("test.json", new Blob(["é\n"]), "replay"), "download-requested");
  assert.equal(await saved!.text(), "é\n");
  assert.equal(await (await boundedResponse(new Response("abc\n"), 4)).text(), "abc\n");
  await assert.rejects(boundedResponse(new Response("12345"), 4), /size limit/);
});
test("background then foreground invalidates file and text preparation epochs", async () => {
  const f = fixture();
  let epoch = 0;
  const service = new FileTransfer({ native: async () => f.port, webDownload() {}, active: () => true, epoch: () => epoch, now: () => now, id: () => id });
  f.port.write = async () => { epoch++; return "file:///cache/owned"; };
  await assert.rejects(service.export("x.json", new Blob(["{}"]), "replay"), /backgrounded/);
  assert.equal(f.removed.length, 1); assert.equal(f.shares.length, 0);
  const text = new FileTransfer({ native: async () => { epoch++; return f.port; }, webDownload() {}, active: () => true, epoch: () => epoch });
  await assert.rejects(text.shareText("public"), /backgrounded/);
  assert.equal(f.shares.length, 0);
  const check = service.preparationGuard(); epoch++;
  assert.throws(check, /backgrounded/);
});
