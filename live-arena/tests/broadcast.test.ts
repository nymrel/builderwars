import test from "node:test";
import assert from "node:assert/strict";
import { Broadcast } from "../src/broadcast";
import { RULES } from "../src/games";
import { replay, type RecordData } from "../src/records";

test("broadcast snapshots bind seats and public claims without retaining mutable input", () => {
  const a = { name: "builder", kind: "harness" as const, model: "declared/model", effort: "default", strategy: "",
    provenance: { builderId: "studio/builder", harnessId: "builder/nim", harnessRevision: "a".repeat(40), attestation: "self-declared" as const },
    key: "SECRET", endpoint: "https://private.example" };
  const r: RecordData = { schema: "builderwars.exhibition.v2", id: "broadcast", createdAt: "2026-09-05",
    rules: RULES.nim, agents: [a, { ...a, name: "opponent" }], events: [], status: "Ready" };
  const b = new Broadcast();
  let sent: any;
  b.viewers.add({ open: true, send: (value: unknown) => { sent = value; } } as any);
  b.publish(r);
  assert.equal(replay(sent.record).record.digest, b.record?.digest);
  assert(!JSON.stringify(sent).includes("SECRET"));
  assert(!JSON.stringify(sent).includes("private.example"));
  a.provenance.builderId = "changed-later";
  r.status = "changed-later";
  assert.equal(b.record?.agents[0].provenance?.builderId, "studio/builder");
  assert.equal(b.record?.status, "Ready");
});
