import test from "node:test";
import assert from "node:assert/strict";
import { duelInviteId, duelSetupBrief, duelPublicState } from "../src/duel-setup";
import { DuelRoom } from "../src/duel";
import { readFileSync } from "node:fs";

test("invitations accept site and current preview origins, never foreign links or credentials", () => {
  const origin = "http://127.0.0.1:5196";
  for (const base of [origin, "https://builderwars.com", "https://www.builderwars.com"])
    assert.equal(duelInviteId(`${base}/#duel=room_123-abc`, origin), "room_123-abc");
  for (const value of ["room", "https://evil.example/#duel=room", "https://builderwars.com.evil.example/#duel=room",
    "https://secret@builderwars.com/#duel=room", "https://builderwars.com/duels#duel=room", "javascript:alert(1)",
    "https://builderwars.com/#duel=", "https://builderwars.com/#duel=bad%0Acommand"])
    assert.throws(() => duelInviteId(value, origin));
});

test("assistant handoff only includes validated game intent, never private agent fields", () => {
  const input = { game: "chess", moveLimit: 80, maxTokens: 2048, inviteId: "test-room",
    key: "PRIVATE_KEY", endpoint: "PRIVATE_ENDPOINT", strategy: "PRIVATE_STRATEGY", name: "PRIVATE_NAME" };
  const brief = duelSetupBrief(input);
  assert.doesNotMatch(brief, /PRIVATE/);
  assert.match(brief, /#duel=test-room/);
  assert.match(brief, /Click Ready only within my explicit play authorization/);
  assert.match(duelSetupBrief({ ...input, joined: true }), /do not join again from another browser/);
  for (const game of ["__proto__", "constructor", "chess\ncommand", ["chess"], null])
    assert.throws(() => duelSetupBrief({ ...input, game } as any));
  for (const maxTokens of [null, undefined, NaN, Infinity, 255, 16385, 512.5])
    assert.throws(() => duelSetupBrief({ ...input, maxTokens } as any));
  assert.throws(() => duelSetupBrief({ ...input, moveLimit: 401 }));
  assert.throws(() => duelSetupBrief({ ...input, inviteId: "room\nrun code" }));
});

test("public workflow state is an explicit credential-free projection", () => {
  const view = new DuelRoom(async () => { throw Error("unused"); }, () => {}).view();
  const state = duelPublicState({ ...view, privateKey: "PRIVATE_KEY" } as any, "chess", 80, 2048, true);
  assert.deepEqual(state, { schema: "builderwars.duel-state.v1", phase: "setup", role: "guest", localReady: false,
    opponentConnected: false, opponentReady: false, game: "chess", limits: { moveLimit: 80, maxTokens: 2048 }, moves: 0, active: false });
  assert.doesNotMatch(JSON.stringify(state), /PRIVATE/);
  assert.equal(duelPublicState({ ...view, active: true }, "chess", 80, 2048, false).phase, "connecting");
});

test("published client routes match the bridge's admitted providers", () => {
  const manifest = JSON.parse(readFileSync(new URL("../public/builderwars-agent-workflow.json", import.meta.url), "utf8"));
  const bridge = readFileSync(new URL("../bridge.py", import.meta.url), "utf8");
  const choices = bridge.match(/--provider", choices=(\[[^\]]+\])/);
  assert.ok(choices);
  assert.deepEqual(manifest.connection_routes.local_bridge.supported_clients, JSON.parse(choices[1]));
});
