import test from "node:test";
import assert from "node:assert/strict";
import { matchLimits, limitsLabel } from "../src/resources";
test("match resource snapshots are immutable and bounded", () => {
  const limits = matchLimits(20, 1024);
  assert.equal(Object.isFrozen(limits), true);
  assert.throws(() => Object.assign(limits, { moveLimit: 400 }));
  assert.equal(limits.moveLimit, 20);
  for (const pair of [[1, 1024], [401, 1024], [20, 255], [20, 16385], [NaN, 1024], [20, 1.5]])
    assert.throws(() => matchLimits(pair[0], pair[1]));
});
test("unknown imported token limits stay unknown", () => {
  assert.match(limitsLabel(matchLimits(80, null)), /unknown/);
  assert.match(limitsLabel(matchLimits(80, null, false)), /original move limit unknown/);
  assert.match(limitsLabel(null), /unavailable/);
  assert.match(limitsLabel(matchLimits(20, 512)), /512 requested/);
});
