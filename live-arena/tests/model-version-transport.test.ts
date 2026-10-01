import test from "node:test";
import assert from "node:assert/strict";
import { assertBrowserVersion, connectedVersionConfig, browserVersionTransport, MODEL_BROWSER_PROTOCOL } from "../src/model-version-transport";
import { createVersion, openVersionSession, type VersionConfig } from "../src/frontier-version";
import { createGame, RULES, gamePrompt } from "../src/runtime";
import { type Agent, type Model } from "../src/models";
import manifest from "../src/model-version-manifest";

const limits = { nodes: 10000, milliseconds: 30000, maxTokens: 256, maxCalls: 2 };
const agent = (): Agent => ({ kind: "openrouter", name: "Private display", model: "test/requested", effort: "high", strategy: "Frozen strategy.",
  key: "secret-credential-never-export", endpoint: "" });
const models = (): Model[] => [{ id: "test/requested", name: "Synthetic", reasoning: { supported_efforts: ["high"] } }];
const json = (value: unknown) => new Response(JSON.stringify(value), { status: 200 });
const response = (model: unknown = "test/resolved", usage: unknown = { total_tokens: 19, completion_tokens: 3 }) => ({
  model, usage, choices: [{ message: { content: '{"move":"0","comment":"Private provider comment"}' } }],
});
const config = (a = agent(), memory = "") => connectedVersionConfig(a, RULES.connect4, "test/resolved", limits, memory);

test("browser config freezes public execution fields without credentials, endpoint or display name", async () => {
  const a = { ...agent(), endpoint: "https://private-endpoint.example/move" }, c = config(a, "Frozen lesson.");
  assert.equal(c.harness.source, manifest.digest); assert.equal(c.harness.protocol, MODEL_BROWSER_PROTOCOL);
  assert.deepEqual(c.runtime, { provider: "openrouter", requestedModel: a.model, resolvedModel: "test/resolved", evidence: "provider-response", reasoning: "high" });
  assert.deepEqual(c.memory, { mode: "frozen", content: "Frozen lesson." });
  assert.ok(Object.isFrozen(c)); assert.ok(Object.isFrozen(c.limits));
  const v = await createVersion(c); assertBrowserVersion(v);
  for (const privateValue of [a.key, a.endpoint, a.name]) assert.ok(!JSON.stringify(v).includes(privateValue));
  a.strategy = "Changed"; a.model = "changed"; assert.equal(c.prompt, "Frozen strategy."); assert.equal(c.runtime.requestedModel, "test/requested");
  assert.throws(() => connectedVersionConfig({ ...a, kind: "bot" }, RULES.connect4, "test/resolved", limits), /connected model/);
  for (const missing of ["provider/unreported", "harness/unreported", "unreported:model", "unknown", "", "test/model\nsecret"])
    assert.throws(() => connectedVersionConfig(agent(), RULES.connect4, missing, limits), /reported model/);
});

test("unsupported source, protocol, identity, tools, sampling and limits fail before any request", async t => {
  let calls = 0; t.mock.method(globalThis, "fetch", () => { calls++; throw Error("Unexpected network"); });
  const changes: ((c: VersionConfig) => void)[] = [
    c => { c.harness.source = "0".repeat(64); }, c => { c.harness.protocol = "another-protocol"; },
    c => { c.harness.kind = "linear-value"; }, c => { c.runtime.evidence = "self-reported"; },
    c => { c.runtime.provider = "local"; }, c => { c.runtime.resolvedModel = null; },
    c => { c.runtime.resolvedModel = "provider/unreported"; }, c => { c.runtime.reasoning = "invented"; },
    c => { c.tools = [{ id: "hidden-tool", source: manifest.digest, parameters: manifest.digest }]; },
    c => { c.sampling.temperature = 0; }, c => { c.sampling.seed = 1; },
    c => { c.memory = { mode: "none", content: "silently ignored lesson" }; },
    c => { c.limits.maxCalls = 0; }, c => { c.limits.maxTokens = 8193; }, c => { c.limits.milliseconds = 300001; },
  ];
  const base = await createVersion(config());
  for (const change of changes) {
    const v = structuredClone(base); change(v.config); assert.throws(() => assertBrowserVersion(v));
  }
  const tampered = structuredClone(base); tampered.config.prompt = "changed without rehash";
  await assert.rejects(browserVersionTransport(agent(), models())(createGame(RULES.connect4), tampered, new AbortController().signal), /digest mismatch/);
  for (const changed of [{ ...agent(), model: "different" }, { ...agent(), effort: "low" }, { ...agent(), kind: "harness" as const, endpoint: "https://example.com/move" }]) {
    const available = [...models(), { id: "different", name: "Different", reasoning: { supported_efforts: ["high", "low"] } }];
    available[0].reasoning!.supported_efforts = ["high", "low"];
    const transport = browserVersionTransport(changed, available);
    await assert.rejects(transport(createGame(RULES.connect4), base, new AbortController().signal), /connected contender/);
  }
  assert.equal(calls, 0);
});

test("OpenRouter uses frozen strategy and memory with private snapshotted connection and exact output cap", async t => {
  const a = agent(), catalog = models(), version = await createVersion(config(a, "Only this frozen lesson."));
  a.strategy = "Mutable practice memory must not leak";
  const transport = browserVersionTransport(a, catalog), requests: { url: string; body?: any }[] = [];
  a.key = "changed-key"; a.model = "changed-model"; catalog[0].id = "changed-catalog";
  t.mock.method(globalThis, "fetch", async (url: RequestInfo | URL, init: RequestInit = {}) => {
    assert.equal((init.headers as Record<string, string>).Authorization, "Bearer secret-credential-never-export");
    assert.equal(init.credentials, "omit"); assert.equal(init.redirect, "error");
    const body = init.body ? JSON.parse(String(init.body)) : undefined; requests.push({ url: String(url), body });
    return String(url).endsWith("/key") ? json({ data: { is_free_tier: false } }) : json(response());
  });
  const state = createGame(RULES.connect4), session = await openVersionSession(version, transport), result = await session.move(state);
  assert.equal(requests.length, 2);
  assert.deepEqual(requests[1].body, { model: "test/requested", messages: [{ role: "user", content: gamePrompt(state, "Frozen strategy.") + "\n\nOnly this frozen lesson." }],
    max_tokens: 256, provider: { allow_fallbacks: false }, stream: false, reasoning: { effort: "high", exclude: true } });
  assert.equal(result.tokens, 19); assert.equal(result.outputTokens, 3); assert.equal(result.cost, null);
  assert.equal(session.receipts().length, 1);
  for (const secret of ["secret-credential", "changed-key", "Private provider comment", "Mutable practice"]) assert.ok(!JSON.stringify(session.receipts()).includes(secret));
});

test("harness carries only frozen strategy/memory and keeps independently missing usage unknown", async t => {
  const a: Agent = { ...agent(), kind: "harness", endpoint: "https://example.com/move" };
  const v = await createVersion(config(a, "Harness frozen lesson."));
  assert.equal(v.config.runtime.evidence, "self-reported");
  let calls = 0;
  t.mock.method(globalThis, "fetch", async (url: RequestInfo | URL, init: RequestInit = {}) => {
    calls++; assert.equal(String(url), "https://example.com/move");
    const body = JSON.parse(String(init.body));
    assert.equal(body.strategy, v.config.prompt); assert.equal(body.practiceMemory, "Harness frozen lesson.");
    assert.equal(body.maxTokens, 256); assert.equal(body.model, "test/requested"); assert.equal(body.effort, "high");
    assert.ok(!("key" in body)); assert.ok(!("endpoint" in body)); assert.ok(!("tools" in body));
    return json({ move: "0", model: "test/resolved", outputTokens: 3 });
  });
  const result = await (await openVersionSession(v, browserVersionTransport(a, []))).move(createGame(RULES.connect4));
  assert.equal(calls, 1); assert.equal(result.tokens, null); assert.equal(result.outputTokens, 3); assert.equal(result.cost, null);
});

test("missing identity, identity drift, output cap and inconsistent totals stop without fallback", async t => {
  const missing = response(); delete (missing as { model?: unknown }).model;
  for (const body of [missing, response("another/model"), response("provider/unreported"), response("m".repeat(161)), response("test/resolved", { total_tokens: 300, completion_tokens: 257 }),
    response("test/resolved", { total_tokens: 1, completion_tokens: 3 }), response("test/resolved", { completion_tokens: -1 }),
    response("test/resolved", { completion_tokens: 1.5 }), response("test/resolved", { completion_tokens: "3" })]) {
    let calls = 0;
    const mock = t.mock.method(globalThis, "fetch", async (url: RequestInfo | URL) => { calls++; return String(url).endsWith("/key") ? json({ data: { is_free_tier: true } }) : json(body); });
    const session = await openVersionSession(await createVersion(config()), browserVersionTransport(agent(), models()));
    await assert.rejects(session.move(createGame(RULES.connect4)));
    assert.equal(session.receipts().length, 0); assert.equal(calls, 2);
    await assert.rejects(session.move(createGame(RULES.connect4)), /stopped/); assert.equal(calls, 2);
    mock.mock.restore();
  }
  const mock = t.mock.method(globalThis, "fetch", async (url: RequestInfo | URL) => String(url).endsWith("/key") ? json({ data: { is_free_tier: true } }) : json(response("test/resolved", {})));
  const result = await (await openVersionSession(await createVersion(config()), browserVersionTransport(agent(), models()))).move(createGame(RULES.connect4));
  assert.equal(result.tokens, null); assert.equal(result.outputTokens, null); mock.mock.restore();
});

test("abort blocks dispatch or rejects a late response and cannot produce a receipt", async t => {
  let calls = 0;
  const cancelled = new AbortController(); cancelled.abort();
  const early = t.mock.method(globalThis, "fetch", () => { calls++; throw Error("Unexpected fetch"); });
  const transport = browserVersionTransport(agent(), models()), version = await createVersion(config());
  await assert.rejects(transport(createGame(RULES.connect4), version, cancelled.signal), { name: "AbortError" });
  assert.equal(calls, 0); early.mock.restore();
  const late = new AbortController();
  t.mock.method(globalThis, "fetch", async (url: RequestInfo | URL) => {
    calls++;
    if (String(url).endsWith("/key")) return json({ data: { is_free_tier: true } });
    late.abort(); return json(response());
  });
  const session = await openVersionSession(version, browserVersionTransport(agent(), models()));
  await assert.rejects(session.move(createGame(RULES.connect4), late.signal));
  assert.equal(session.receipts().length, 0); assert.equal(calls, 2);
  await assert.rejects(session.move(createGame(RULES.connect4)), /stopped/); assert.equal(calls, 2);
});
