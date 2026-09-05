import test from "node:test";
import assert from "node:assert/strict";
import { checkConnection, validateConnection, decide, forgetConnectionCheck, type Agent, type Model } from "../src/models";
import { createGame, RULES } from "../src/runtime";
const models: Model[] = [{ id: "test/model", name: "Synthetic model", reasoning: { supported_efforts: ["low", "high"] } }];
const agent = (): Agent => ({ kind: "openrouter", name: "Test", model: "test/model", effort: "high", key: "synthetic-only", endpoint: "", strategy: "" });
const signal = () => new AbortController().signal;
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

test("preflight checks authentication without inference and strips account data", async t => {
  const calls: string[] = [];
  t.mock.method(globalThis, "fetch", async (url: RequestInfo | URL, init: RequestInit = {}) => {
    calls.push(String(url));
    assert.equal(init.method, "GET"); assert.equal(init.redirect, "error"); assert.equal(init.credentials, "omit"); assert.equal(init.cache, "no-store");
    return json({ data: { is_free_tier: true, label: "PRIVATE", creator_user_id: "PRIVATE", limit_remaining: 0 } });
  });
  const result = await checkConnection(agent(), models, signal());
  assert.equal(result.checked, true);
  assert.match(result.message, /no remaining configured allowance/);
  assert(!JSON.stringify(result).includes("PRIVATE"));
  assert.deepEqual(calls, ["https://openrouter.ai/api/v1/key"]);
});
test("invalid model, effort, endpoint and missing local token fail before any network", async t => {
  t.mock.method(globalThis, "fetch", () => { throw Error("Unexpected fetch"); });
  assert.throws(() => validateConnection({ ...agent(), effort: "xhigh" }, models), /effort/);
  assert.throws(() => validateConnection({ ...agent(), model: "missing" }, models), /catalog/);
  assert.throws(() => validateConnection({ ...agent(), key: "" }, models), /key/);
  assert.throws(() => validateConnection({ ...agent(), kind: "harness", endpoint: "http://127.0.0.1:8765/move", key: "" }, models), /token/);
  assert.throws(() => validateConnection({ ...agent(), kind: "harness", endpoint: "https://user:secret@example.com/move" }, models));
  const result = await checkConnection({ ...agent(), kind: "harness", endpoint: "https://example.com/move" }, models, signal());
  assert.equal(result.checked, false); assert.match(result.message, /unchecked/);
});
test("auth/rate/server/malformed/oversize failures block inference and expose no payload", async t => {
  for (const status of [401, 429, 500]) {
    const calls: string[] = [];
    const mock = t.mock.method(globalThis, "fetch", async (url: RequestInfo | URL) => { calls.push(String(url)); return json({ error: "PRIVATE" }, status); });
    await assert.rejects(decide(createGame(RULES.connect4), agent(), 256, signal(), models), e => (e as Error).message.includes(String(status)) && !(e as Error).message.includes("PRIVATE"));
    assert.equal(calls.length, 1); assert(calls[0].endsWith("/key")); mock.mock.restore();
  }
  let mock = t.mock.method(globalThis, "fetch", async () => json({ data: { is_free_tier: false, is_management_key: true } }));
  await assert.rejects(checkConnection(agent(), models, signal()), /management/); mock.mock.restore();
  mock = t.mock.method(globalThis, "fetch", async () => new Response("x".repeat(64001)));
  await assert.rejects(checkConnection(agent(), models, signal()), /size/); mock.mock.restore();
  mock = t.mock.method(globalThis, "fetch", async () => json({ data: {} }));
  await assert.rejects(checkConnection(agent(), models, signal()), /Invalid/);
});
test("cancellation after a late preflight response cannot start inference or warm cache", async t => {
  const controller = new AbortController();
  let requests = 0;
  t.mock.method(globalThis, "fetch", async () => { requests++; controller.abort(); return json({ data: { is_free_tier: true } }); });
  await assert.rejects(decide(createGame(RULES.connect4), agent(), 256, controller.signal, models), { name: "AbortError" });
  assert.equal(requests, 1);
});
test("successful probes cache only for same credentials and can be forgotten", async t => {
  let calls = 0;
  t.mock.method(globalThis, "fetch", async () => { calls++; return json({ data: { is_free_tier: true } }); });
  const a = agent();
  await checkConnection(a, models, signal(), false); await checkConnection(a, models, signal(), false);
  assert.equal(calls, 1);
  a.key = "new-synthetic";
  await checkConnection(a, models, signal(), false); assert.equal(calls, 2);
  forgetConnectionCheck(a);
  await checkConnection(a, models, signal(), false); assert.equal(calls, 3);
  const later = Date.now() + 61000;
  t.mock.method(Date, "now", () => later);
  await checkConnection(a, models, signal(), false); assert.equal(calls, 4);
});
test("local health checks reject busy/exhausted/malformed sessions without /move", async t => {
  const a = { ...agent(), kind: "harness" as const, endpoint: "http://127.0.0.1:8765/move" };
  for (const body of [{ schema: "builderwars.bridge.health.v1", remainingCalls: 0, busy: false }, { schema: "builderwars.bridge.health.v1", remainingCalls: 1, busy: true }, { schema: "wrong" }]) {
    const mock = t.mock.method(globalThis, "fetch", async (url: RequestInfo | URL) => { assert.equal(String(url), "http://127.0.0.1:8765/health"); return json(body); });
    await assert.rejects(checkConnection(a, models, signal())); mock.mock.restore();
  }
});
test("missing response model is unreported, not the requested declaration", async t => {
  t.mock.method(globalThis, "fetch", async (url: RequestInfo | URL) => String(url).endsWith("/key") ? json({ data: { is_free_tier: true } }) : json({ choices: [{ message: { content: '{"move":"0"}' } }] }));
  const decision = await decide(createGame(RULES.connect4), agent(), 256, signal(), models);
  assert.equal(decision.model, "provider/unreported");
  assert.equal(decision.cost, null);
});
test("preflight deadline prevents inference even when a response arrives late", async t => {
  t.mock.method(AbortSignal, "timeout", () => AbortSignal.abort(new DOMException("Synthetic deadline", "TimeoutError")));
  let calls = 0;
  t.mock.method(globalThis, "fetch", async () => { calls++; return json({ data: { is_free_tier: true } }); });
  await assert.rejects(decide(createGame(RULES.connect4), agent(), 256, signal(), models), { name: "ConnectionCheckTimeout", message: "Connection check timed out after 15 seconds. No model invoked." });
  assert.equal(calls, 1);
});
test("late success cannot validate mutated credentials or undo forgetting", async t => {
  for (const mode of ["mutate", "forget", "force"]) {
    const a = agent();
    let calls = 0, resolveFirst!: (response: Response) => void;
    const mock = t.mock.method(globalThis, "fetch", async () => {
      calls++;
      if (calls === 1) return new Promise<Response>(resolve => { resolveFirst = resolve; });
      return json({ data: { is_free_tier: true } });
    });
    const first = checkConnection(a, models, signal(), false);
    if (mode === "mutate") a.key = "changed-synthetic";
    if (mode === "forget") forgetConnectionCheck(a);
    if (mode === "force") await checkConnection(a, models, signal(), true);
    resolveFirst(json({ data: { is_free_tier: true } }));
    await assert.rejects(first, /Connection changed/);
    await checkConnection(a, models, signal(), false);
    assert.equal(calls, 2);
    mock.mock.restore();
  }
});
