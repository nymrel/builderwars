import test from "node:test";
import assert from "node:assert/strict";
import { makeProfile, readProfile, disconnectedProfile, compareProfiles } from "../src/profiles";
import type { Agent } from "../src/models";
const a: Agent = { name: "Builder", kind: "bot", model: "tactician", effort: "default", strategy: "Keep my draft", key: "PRIVATE_KEY", endpoint: "https://PRIVATE_ENDPOINT.example" };

test("versioned and legacy profiles round trip without connection material", () => {
  const p = makeProfile(a);
  assert.deepEqual(readProfile(JSON.stringify(p)), p);
  assert.deepEqual(readProfile(JSON.stringify(p.agent)), p);
  assert(!JSON.stringify(p).includes("PRIVATE"));
  assert.equal(p.agent.strategy, a.strategy); // explicit local export, not a public share
  assert.equal(disconnectedProfile(p).key, "");
  assert.equal(disconnectedProfile(p).endpoint, "");
});
test("untrusted imports fail closed on unknown fields, versions, shape, size and bots", () => {
  const p = makeProfile(a);
  for (const raw of [null, [], {}, { ...p, schema: "future" }, { ...p, key: "x" },
    { ...p, agent: { ...p.agent, endpoint: "https://secret.example" } },
    { ...p, agent: { ...p.agent, model: "claimed-frontier" } },
    { ...p, agent: { ...p.agent, strategy: 42 } },
    { ...p, agent: { ...p.agent, name: " " } },
    { ...p, agent: { ...p.agent, strategy: "a".repeat(1001) } }])
    assert.throws(() => readProfile(JSON.stringify(raw)));
  assert.throws(() => readProfile(" ".repeat(8193)));
  assert.throws(() => readProfile('{"__proto__": {}, "name":"x"}'));
});
test("comparison counts settings, not labels or connection credentials", () => {
  assert.deepEqual(compareProfiles(a, { ...a, name: "Renamed" }), { changed: [], renamed: true });
  assert.deepEqual(compareProfiles(a, { ...a, model: "random" }).changed, ["model"]);
  assert.deepEqual(compareProfiles(a, { ...a, model: "random", strategy: "Try" }).changed, ["model", "strategy"]);
});
