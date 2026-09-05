import test from "node:test";
import assert from "node:assert/strict";
import { RULES, createGame, replayStepper } from "../src/runtime";
import { localBaseline } from "../scripts/frontier-store";
import { createVersion, parseVersion, openVersionSession, type Version, type VersionDecision } from "../src/frontier-version";
import { versionMove } from "../scripts/frontier";

async function remote() {
  const base = await localBaseline(RULES.tictactoe), config = structuredClone(base.config);
  config.runtime = { provider: "openrouter", requestedModel: "fixture/alias", resolvedModel: "fixture/resolved-1", evidence: "provider-response", reasoning: "high" };
  config.harness.kind = "model"; config.harness.protocol = "fixture.model.v1";
  config.value = null; config.prompt = "Fixture strategy"; config.memory = { mode: "frozen", content: "Fixture memory" }; config.tools = [];
  return createVersion(config);
}
const answer = (): VersionDecision => ({ move: "0", model: "fixture/resolved-1", tokens: 1000, outputTokens: 10, cost: 0.01 });

test("versions bind all configuration, deep-freeze, preserve ancestry and reject unknown/invalid fields", async () => {
  const version = await remote(), original = JSON.stringify(version);
  assert.deepEqual(await parseVersion(JSON.parse(original)), version);
  assert.throws(() => { version.config.memory.content = "mutated"; }, TypeError);
  assert.throws(() => { version.config.runtime.reasoning = "low"; }, TypeError);
  const config = structuredClone(version.config); config.prompt = "new strategy";
  const child = await createVersion(config, version); config.prompt = "late mutation";
  assert.equal(child.revision, 1); assert.equal(child.parent, version.digest); assert.equal(child.config.prompt, "new strategy");
  assert.notEqual(child.digest, version.digest); assert.equal(JSON.stringify(version), original);
  for (const mutate of [
    (v: any) => { v.key = "not-allowed"; }, (v: any) => { v.config.endpoint = "https://user:password@invalid.example"; },
    (v: any) => { v.config.runtime.key = "not-allowed"; }, (v: any) => { v.config.limits.nodes = NaN; },
    (v: any) => { v.config.sampling.temperature = Infinity; }, (v: any) => { v.config.runtime.resolvedModel = null; },
    (v: any) => { v.config.referee = "0".repeat(64); }, (v: any) => { v.config.memory.content += "changed"; },
    (v: any) => { v.config.tools.push({ id: "x", source: "bad", parameters: "bad" }); },
  ]) { const bad = JSON.parse(original); mutate(bad); await assert.rejects(parseVersion(bad)); }
  const local = structuredClone((await localBaseline(RULES.tictactoe)).config);
  local.tools[0].parameters = "0".repeat(64);
  await assert.rejects(createVersion(local), /executor/);
});

test("a session pins every phase's identity and uses a frozen state/config, not caller mutations", async () => {
  const source = await remote(), mutable = structuredClone(source), state = createGame(RULES.tictactoe);
  let calls = 0;
  const session = await openVersionSession(mutable, async (snapshot, version) => {
    calls++; assert.equal(version.config.prompt, "Fixture strategy"); assert.equal(snapshot.cells[0], "");
    assert.throws(() => { snapshot.cells[0] = "w"; }, TypeError);
    assert.throws(() => { version.config.prompt = "mutated"; }, TypeError);
    return answer();
  });
  mutable.config.prompt = "external mutation";
  const result = await session.move(state);
  assert.equal(calls, 1); assert.equal(result.version, source.digest); assert.equal(result.model, source.config.runtime.resolvedModel);
  assert.equal(result.tokens, 1000); // Total tokens are not incorrectly compared to the output-token cap.
  assert.equal(session.receipts().length, 1); session.cancel();
  await assert.rejects(session.move(state), /stopped/);
});

test("identity drift, unknown identity, invalid usage and illegal output stop without hidden retries", async () => {
  const source = await remote();
  for (const result of [ { ...answer(), model: "fixture/other" }, { ...answer(), move: "wrong" }, { ...answer(), cost: NaN },
    { ...answer(), outputTokens: 9000 }, { ...answer(), tokens: 2 }, { ...answer(), secret: "extra-field" } ]) {
    let calls = 0;
    const session = await openVersionSession(source, async () => { calls++; return result; });
    await assert.rejects(session.move(createGame(RULES.tictactoe)));
    await assert.rejects(session.move(createGame(RULES.tictactoe)), /stopped/);
    assert.equal(calls, 1); assert.equal(session.receipts().length, 0);
  }
  const c = structuredClone(source.config); c.runtime.resolvedModel = null; c.runtime.evidence = "unreported";
  await assert.rejects(openVersionSession(await createVersion(c), async () => answer()), /identity/);
});

test("concurrent and cancelled transports cannot produce a late receipt or start another call", async () => {
  const version = await remote();
  let finish!: (r: VersionDecision) => void, calls = 0;
  const session = await openVersionSession(version, () => { calls++; return new Promise(resolve => { finish = resolve; }); });
  const first = session.move(createGame(RULES.tictactoe));
  const rejected = assert.rejects(first, /abort|stopped/i);
  await Promise.resolve();
  await assert.rejects(session.move(createGame(RULES.tictactoe)), /busy/);
  session.cancel(); await rejected; finish(answer()); await Promise.resolve();
  assert.equal(calls, 1); assert.equal(session.receipts().length, 0);
  const abort = new AbortController(); abort.abort();
  const unopened = await openVersionSession(version, async () => { calls++; return answer(); });
  await assert.rejects(unopened.move(createGame(RULES.tictactoe), abort.signal));
  assert.equal(calls, 1); unopened.cancel();
});

test("real local version execution rejects fabricated history, positions and version overrides", async () => {
  const version = await localBaseline(RULES.tictactoe), step = replayStepper(RULES.tictactoe);
  let state = createGame(RULES.tictactoe); for (const move of ["0", "3", "1", "4"]) state = step(move);
  const request = { schema: "builderwars.move.v1", game: state.rules, position: state.cells, turn: state.turn, moves: state.moves,
    legalMoves: ["2", "5", "6", "7", "8"], version: version.digest };
  const result = await versionMove(request, version);
  assert.equal(result.move, "2"); assert.equal(result.version, version.digest); assert.equal(result.model, "builderwars/linear-value-v1");
  assert.equal(result.outputTokens, 0); assert.equal(result.cost, 0);
  await assert.rejects(versionMove({ ...request, version: "0".repeat(64) }, version), /mismatch/);
  await assert.rejects(versionMove({ ...request, position: [] }, version), /replay/);
  await assert.rejects(versionMove({ ...request, moves: ["0", "0"] }, version));
  const session = await openVersionSession(version), fake = structuredClone(state); fake.quiet++;
  await assert.rejects(session.move(fake), /replay/); session.cancel();
});

test("non-cooperating transports still time out, and fixed call/node budgets cannot be extended", async () => {
  const base = await remote(), config = structuredClone(base.config); config.limits.milliseconds = 25;
  const keepAlive = setTimeout(() => {}, 1000);
  const slow = await openVersionSession(await createVersion(config), () => new Promise(() => {}));
  try { await assert.rejects(slow.move(createGame(RULES.tictactoe)), /abort|budget/i); }
  finally { clearTimeout(keepAlive); slow.cancel(); }
  const single = structuredClone(base.config); single.limits.maxCalls = 1;
  const session = await openVersionSession(await createVersion(single), async () => answer());
  await session.move(createGame(RULES.tictactoe));
  await assert.rejects(session.move(createGame(RULES.tictactoe)), /budget exhausted/); session.cancel();
  const local = structuredClone((await localBaseline(RULES.tictactoe)).config); local.limits.nodes = 1;
  const tiny = await openVersionSession(await createVersion(local));
  await assert.rejects(tiny.move(createGame(RULES.tictactoe)), /budget/);
  await assert.rejects(tiny.move(createGame(RULES.tictactoe)), /stopped/);
});
