import test from "node:test";
import assert from "node:assert/strict";
import { unknownDeclarations, readDeclarations, makeMatchPackage, readMatchFile } from "../src/match-package";
import { RULES, refereeManifest, type RecordData } from "../src/runtime";
import { matchLimits } from "../src/resources";

function record(): RecordData {
  return { schema: "builderwars.exhibition.v1", id: "package-test", createdAt: new Date().toISOString(), rules: RULES.tictactoe,
    agents: [0, 1].map(i => ({ name: `Seat ${i}`, kind: "bot", model: "random", effort: "default", strategy: "PRIVATE_STRATEGY" })),
    events: [{ ply: 1, seat: 0, move: "0", label: "0", elapsed: 1, cost: null, tokens: null, model: "random", comment: "PRIVATE_COMMENT" }],
    status: "PRIVATE_STATUS" };
}
test("public packages round trip distinct seat declarations, resources and legal replay", () => {
  const declarations = readDeclarations(unknownDeclarations().map((d, i) => ({ ...d, builderId: `builder-${i}`, agentId: `agent-${i}`, agentRevision: "r2", harnessId: "harness", harnessRevision: "abc123", providerId: "declared-provider", modelRevision: "2026-09" })));
  const raw = record() as any;
  raw.agents[0].key = "PRIVATE_KEY"; raw.agents[0].endpoint = "https://PRIVATE.example";
  const pkg = makeMatchPackage(raw, declarations, matchLimits(4, 512));
  assert(!JSON.stringify(pkg).includes("PRIVATE"));
  const imported = readMatchFile(JSON.parse(JSON.stringify(pkg)));
  assert.deepEqual(imported.declarations, declarations);
  assert.deepEqual(imported.limits, matchLimits(4, 512));
  assert.equal(imported.parsed.record.events.length, 1);
  assert.equal(pkg.verification.verifierDigest, refereeManifest.digest);
  assert.equal(pkg.verification.modelAttested, false);
  assert.equal(pkg.seed, null);
  assert(Object.isFrozen(imported.declarations));
  assert(Object.isFrozen(imported.declarations[0]));
  assert.equal(raw.agents[0].strategy, "PRIVATE_STRATEGY");
});
test("legacy files and explicitly unknown package budgets stay unknown", () => {
  const legacy = readMatchFile(record());
  assert.equal(legacy.limits, null);
  assert.deepEqual(legacy.declarations, unknownDeclarations());
  const pkg = makeMatchPackage(record(), unknownDeclarations(), matchLimits(80, null, false));
  assert.deepEqual(readMatchFile(pkg).limits, matchLimits(80, null, false));
});
test("known resource caps cannot contradict recorded plies", () => {
  const game = record();
  game.events.push({ ...game.events[0], ply: 2, seat: 1, move: "1" }, { ...game.events[0], ply: 3, seat: 0, move: "2" });
  assert.throws(() => makeMatchPackage(game, unknownDeclarations(), matchLimits(2, 512)), /exceeds declared/);
  const pkg = makeMatchPackage(game, unknownDeclarations(), matchLimits(4, 512));
  assert.throws(() => readMatchFile({ ...pkg, resources: matchLimits(2, 512) }), /exceeds declared/);
  assert.throws(() => readMatchFile({ ...pkg, resources: matchLimits(2, null, false) }), /exceeds declared/);
  assert.throws(() => makeMatchPackage(game, unknownDeclarations(), matchLimits(2, null, false)), /exceeds declared/);
});
test("package metadata cannot elevate execution claims, introduce secrets or bypass replay", () => {
  const pkg = makeMatchPackage(record(), unknownDeclarations(), null);
  for (const raw of [null, [], {}, { ...pkg, schema: "future" }, { ...pkg, key: "secret" },
    { ...pkg, seed: 123 }, { ...pkg, fixture: "custom-position" },
    { ...pkg, verification: { ...pkg.verification, modelAttested: true } },
    { ...pkg, verification: { ...pkg.verification, verifierDigest: "0".repeat(64) } },
    { ...pkg, resources: { moveLimit: 4, maxTokens: 512, moveLimitKnown: "yes" } },
    { ...pkg, declarations: [{ ...pkg.declarations[0], endpoint: "https://private.example" }, pkg.declarations[1]] },
    { ...pkg, declarations: [{ ...pkg.declarations[0], agentId: "https://private.example" }, pkg.declarations[1]] },
    { ...pkg, declarations: [{ ...pkg.declarations[0], agentId: "x".repeat(97) }, pkg.declarations[1]] },
    { ...pkg, record: { ...pkg.record, events: [{ ...pkg.record.events[0], move: "99" }] } },
  ]) assert.throws(() => readMatchFile(raw));
});
