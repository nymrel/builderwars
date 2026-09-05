import test from "node:test";
import assert from "node:assert/strict";
import { publicLinkOrigin } from "../src/public-links";

test("packaged local origins share the canonical website, not phone-local addresses", () => {
  for (const origin of ["capacitor://localhost", "https://localhost", "http://localhost"])
    assert.equal(publicLinkOrigin(origin), "https://builderwars.com");
});
test("explicit browser preview origins remain independently testable", () => {
  for (const origin of ["https://builderwars.com", "http://127.0.0.1:5178", "http://localhost:5178", "https://candidate.vercel.app"])
    assert.equal(publicLinkOrigin(origin), origin);
});
test("unknown schemes and embedded credential/path material never become share bases", () => {
  for (const origin of ["file:///app", "javascript:alert(1)", "capacitor://evil", "https://user:pass@example.com", "https://example.com/private", "https://example.com/?key=x", "null"])
    assert.throws(() => publicLinkOrigin(origin));
});
