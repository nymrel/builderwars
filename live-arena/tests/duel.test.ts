import test from "node:test";
import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import { DuelRoom, duelAgent, readOffer, acceptDuelMove } from "../src/duel";
import { legalMoves, RULES, replay, type RecordData } from "../src/runtime";
import type { Agent } from "../src/models";

const agent: Agent = { name: "My agent", kind: "bot", model: "random", effort: "default", strategy: "PRIVATE_PROMPT", endpoint: "http://private", key: "PRIVATE_KEY" };
const initial = (): RecordData => ({ schema: "builderwars.exhibition.v1", id: "duel-test", createdAt: "2026-09-19", rules: RULES.tictactoe,
  agents: [duelAgent(agent), duelAgent(agent)], events: [], status: "Playing" });
const first = () => ({ ...initial(), events: [{ move: "0", ply: 1, seat: 0 as const, label: "a1", comment: "", elapsed: 1, model: "random", tokens: null, cost: 0 }] });
test("duel metadata removes credentials, endpoints and private prompts", () => {
  const shared = duelAgent(agent);
  assert.deepEqual(Object.keys(shared).sort(), ["effort", "kind", "model", "name", "strategy"]);
  assert.equal(shared.strategy, "");
  assert.doesNotMatch(JSON.stringify(shared), /PRIVATE|http/);
  assert.throws(() => duelAgent({ ...agent, kind: "human" }));
  assert.throws(() => readOffer({ game: "__proto__", moveLimit: 80, maxTokens: 2048, agent: shared }));
  assert.throws(() => readOffer({ game: "chess", moveLimit: 401, maxTokens: 2048, agent: shared }));
  assert.throws(() => readOffer({ game: "chess", moveLimit: 80, maxTokens: null, agent: shared }));
  assert.throws(() => readOffer({ game: "chess", moveLimit: 80, agent: shared }));
  assert.throws(() => readOffer({ game: ["chess"], moveLimit: 80, maxTokens: 2048, agent: shared }));
});
test("only one legal move by the agreed seat extends an immutable history", () => {
  const accepted = acceptDuelMove(initial(), first(), 0, 80);
  assert.equal(accepted.events.length, 1);
  assert.throws(() => acceptDuelMove(initial(), first(), 1, 80));
  assert.throws(() => acceptDuelMove(initial(), { ...first(), id: "replacement" }, 0, 80));
  assert.throws(() => acceptDuelMove(initial(), { ...first(), agents: [duelAgent({ ...agent, name: "Intruder" }), duelAgent(agent)] }, 0, 80));
  assert.throws(() => acceptDuelMove(initial(), { ...first(), events: [{ ...first().events[0], move: "99" }] }, 0, 80));
  assert.throws(() => acceptDuelMove(accepted, accepted, 1, 80));
  assert.throws(() => acceptDuelMove(accepted, accepted, 1, 1));
});
test("fractional latency and cost survive the next peer move without changing history", () => {
  const one = replay({ ...first(), events: [{ ...first().events[0], elapsed: 1.125, cost: 0.0003 }] }).record;
  const two = { ...one, events: [...one.events, { ...one.events[0], move: "1", ply: 2, seat: 1 as const }] };
  assert.equal(acceptDuelMove(one, two, 1, 80).events.length, 2);
  const rewritten = structuredClone(two); rewritten.events[0].cost = 0.0004;
  assert.throws(() => acceptDuelMove(one, rewritten, 1, 80));
});

class Channel extends EventEmitter {
  open = false;
  metadata: unknown;
  other!: Channel;
  sent: unknown[] = [];
  send(data: unknown) { this.sent.push(structuredClone(data)); queueMicrotask(() => { if (this.other.open) this.other.emit("data", structuredClone(data)); }); }
  close() { if (!this.open) return; this.open = false; this.emit("close"); this.other.close(); }
}
function network() {
  const peers = new Map<string, FakePeer>();
  const channels: Channel[] = [];
  class FakePeer extends EventEmitter {
    id = `peer-${peers.size}`;
    constructor() { super(); peers.set(this.id, this); queueMicrotask(() => this.emit("open", this.id)); }
    connect(id: string, options?: { metadata?: unknown }) {
      const a = new Channel(), b = new Channel(); a.other = b; b.other = a; channels.push(a, b);
      b.metadata = options?.metadata;
      queueMicrotask(() => {
        peers.get(id)?.emit("connection", b);
        a.open = b.open = true; b.emit("open"); a.emit("open");
      });
      return a;
    }
    destroy() { peers.delete(this.id); }
  }
  return { create: () => new FakePeer() as any, channels, peers };
}
const flush = () => new Promise(resolve => setTimeout(resolve, 20));
async function until(check: () => boolean) {
  const deadline = Date.now() + 8000;
  while (!check() && Date.now() < deadline) await flush();
  assert.ok(check(), "condition completed before timeout");
}
test("two devices require both Ready clicks, play legal turns and preserve matching replays", async () => {
  const net = network(); let calls = 0;
  const choose = async (state: any) => { calls++; return { move: legalMoves(state)[0], comment: "PRIVATE_COMMENT", elapsed: 1, model: "builtin/random", tokens: null, cost: 0 }; };
  const host = new DuelRoom(choose, () => {}, net.create), guest = new DuelRoom(choose, () => {}, net.create);
  try {
    const id = await host.host(agent, "tictactoe", 80, 2048);
    await guest.join(id); await flush();
    assert.ok(guest.view().offer); assert.equal(calls, 0);
    net.peers.get(id)!.emit("error", { type: "webrtc" });
    assert.equal(host.view().active, true, "unrelated signaling error keeps the admitted channel alive");
    guest.ready({ ...agent, name: "Rival" }); await flush();
    assert.equal(host.view().opponentReady, true);
    assert.equal(calls, 0); assert.equal(host.view().record, null);
    host.ready(agent);
    await until(() => !!guest.view().record && replay(guest.view().record).state.over);
    assert.deepEqual(host.view().record, guest.view().record);
    assert.equal(calls, host.view().record!.events.length);
    assert.doesNotMatch(JSON.stringify(net.channels.flatMap(c => c.sent)), /PRIVATE|http:\/\/private/);
    const before = calls; guest.ready(agent); await flush(); assert.equal(calls, before);
    const result = host.view().status;
    guest.close(); await flush(); assert.equal(host.view().status, result);
  } finally { host.close(); guest.close(); }
});
test("host can be ready before guest arrives and the agreed move cap stops calls", async () => {
  const net = network(); let calls = 0;
  const choose = async (state: any) => { calls++; return { move: legalMoves(state)[0], comment: "", elapsed: 1, model: "random", tokens: null, cost: 0 }; };
  const host = new DuelRoom(choose, () => {}, net.create), guest = new DuelRoom(choose, () => {}, net.create);
  try {
    const id = await host.host(agent, "tictactoe", 2, 256); host.ready(agent);
    await guest.join(id); await flush();
    assert.equal(guest.view().opponentReady, true);
    guest.ready(agent);
    await until(() => guest.view().record?.events.length === 2);
    assert.equal(calls, 2); assert.match(host.view().status, /no winner/);
    guest.close(); await flush(); assert.equal(host.view().active, false);
    assert.equal(host.view().record?.events.length, 2);
  } finally { host.close(); guest.close(); }
});

test("readiness updates are negotiated without breaking older open clients", async () => {
  const net = network();
  const host = new DuelRoom(async () => { throw Error("No play authorized"); }, () => {}, net.create);
  const guest = new DuelRoom(async () => { throw Error("No play authorized"); }, () => {}, net.create);
  try {
    await guest.join(await host.host(agent, "chess", 80, 2048)); await flush();
    host.ready(agent); await flush();
    assert.equal(guest.view().opponentReady, true);
    assert.equal(guest.view().record, null);
    guest.close(); host.close();
    assert.equal(host.view().offer, null, "closed unused rooms do not retain stale limits");
    await guest.join(await host.host(agent, "chess", 80, 2048)); await flush();
    net.channels.at(-1)!.metadata = undefined; // Older guest has no capability metadata.
    host.ready(agent); await flush();
    assert.equal(guest.view().active, true);
    assert.equal(net.channels.at(-1)!.sent.some((v: any) => v.type === "host-ready"), false);
  } finally { host.close(); guest.close(); }
});
test("disconnect aborts pending inference and ignores its late answer", async () => {
  const net = network(); let signal: AbortSignal | undefined; let release: (value: any) => void = () => {};
  const choose = async (_s: any, _a: Agent, _t: number, nextSignal: AbortSignal) => {
    signal = nextSignal; return new Promise<any>(resolve => { release = resolve; });
  };
  const host = new DuelRoom(choose, () => {}, net.create), guest = new DuelRoom(choose, () => {}, net.create);
  try {
    const id = await host.host(agent, "chess", 80, 2048); await guest.join(id); await flush();
    host.ready(agent); guest.ready(agent); await until(() => !!signal);
    guest.close(); await flush(); assert.ok(signal!.aborted);
    assert.equal(host.view().record!.status, "Duel stopped · incomplete");
    release({ move: "e2e4", comment: "", elapsed: 1, model: "random", tokens: null, cost: 0 });
    await flush(); assert.equal(host.view().record!.events.length, 0);
  } finally { host.close(); guest.close(); }
});
