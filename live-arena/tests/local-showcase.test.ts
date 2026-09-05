import test from "node:test";
import assert from "node:assert/strict";
import { createGame, RULES, applyMove, replay, decodeReplay } from "../src/runtime";
import { ENDPOINT, MODEL, LIMITS, requestFor, runComparison, tacticalObservations } from "../scripts/local-showcase";

const response = (move: string, extra = {}) => new Response(JSON.stringify({ model: "runtime-reported-model",
  choices: [{ message: { content: JSON.stringify({ move }) } }], ...extra }), { status: 200 });

test("local showcase: plain vs tactical observes authoritative positions without selecting moves", () => {
  let state = createGame(RULES.tictactoe);
  for (const move of ["0", "3", "1", "4"]) state = applyMove(state, move);
  const before = structuredClone(state), observations = tacticalObservations(state);
  assert.deepEqual(observations.immediateWins, ["2"]);
  assert.deepEqual(observations.noImmediateOpponentWin, ["2", "5"]);
  assert.deepEqual(state, before);
  const plain = requestFor(state, "plain"), tactical = requestFor(state, "tactical");
  assert(!plain.messages[0].content.includes("tactical observations"));
  assert(tactical.messages[0].content.includes('"immediateWins":["2"]'));
  assert.equal(plain.model, MODEL);
  assert.deepEqual({ ...plain, messages: [] }, { ...tactical, messages: [] });
  assert.equal(plain.messages.length, 1);
  assert.equal(plain.max_tokens, 64);
  assert.equal(plain.temperature, 0);
  assert.equal(plain.seed, 42);
  assert.equal(plain.cache_prompt, false);
});

test("local showcase: exactly two swapped games, at most 18 calls; complete sanitized arena replays", async () => {
  const draw = ["0", "1", "2", "4", "3", "5", "7", "6", "8"];
  let calls = 0;
  const result = await runComparison({ fetchImpl: async (input, options) => {
    assert.equal(input, ENDPOINT);
    assert.equal(options?.redirect, "error");
    assert.equal(options?.credentials, "omit");
    assert.deepEqual(options?.headers, { "Content-Type": "application/json" });
    const body = JSON.parse(String(options?.body));
    assert.equal(body.model, MODEL);
    assert.equal(body.max_tokens, 64);
    return response(draw[calls++ % 9], { usage: { prompt_tokens: 100, completion_tokens: 5, total_tokens: 105 } });
  } });
  assert.equal(calls, 18);
  assert.equal(result.completedGames, 2);
  assert.equal(result.failedGames, 0);
  assert.deepEqual(result.games.map(game => game.harnesses), [["plain", "tactical"], ["tactical", "plain"]]);
  assert.equal(result.inputTokens, 1800);
  assert.equal(result.outputTokens, 90);
  assert.equal(result.dollarCost, null);
  assert.equal(result.electricityCost, null);
  for (const game of result.games) {
    assert.equal(replay(game.record).state.over, true);
    assert.equal(game.winnerHarness, null);
    const decoded = await decodeReplay(game.replayUrl.split("#replay=")[1]);
    assert.equal(decoded.record.events.length, 9);
    assert(decoded.record.agents.every(agent => agent.strategy === ""));
    assert(!JSON.stringify(decoded.record).includes("127.0.0.1"));
    assert.equal(decoded.record.events[0].model, `declared/${MODEL}`);
    assert.equal(decoded.record.agents[0].model, MODEL);
  }
});

test("local showcase: runtime Windows and Unix model paths stay private, absent from replay records and URLs", async () => {
  for (const path of ["C:\\Users\\private-user\\models\\local-qwen.gguf", "/home/private-user/models/local-qwen.gguf"]) {
    const result = await runComparison({ limits: { maxCalls: 1 }, fetchImpl: async () => response("0", { model: path }) });
    assert.equal(result.calls[0].responseModel, path);
    assert.equal(JSON.parse(result.calls[0].responseText!).model, path);
    assert(result.replayEventModelMeaning.includes("not runtime attestation"));
    for (const game of result.games) {
      assert(!JSON.stringify(game.record).includes("private-user"));
      assert(!JSON.stringify(game.record).includes(".gguf"));
      assert(!game.replayUrl.includes("private-user"));
      const publicReplay = await decodeReplay(game.replayUrl.split("#replay=")[1]);
      assert(!JSON.stringify(publicReplay.record).includes("private-user"));
      assert(!JSON.stringify(publicReplay.record).includes(".gguf"));
      assert(publicReplay.record.events.every(event => event.model === `declared/${MODEL}`));
    }
  }
});

test("local showcase: malformed and illegal outputs abort each game without repair or retry", async () => {
  for (const bad of [new Response(JSON.stringify({ choices: [{ message: { content: "not JSON" } }] })), response("9")]) {
    let calls = 0;
    const result = await runComparison({ fetchImpl: async () => { calls++; return bad.clone(); } });
    assert.equal(calls, 2);
    assert.equal(result.failedGames, 2);
    assert(result.games.every(game => game.record.events.length === 0 && !replay(game.record).state.over));
    assert(result.calls.every(call => call.failure && call.responseText));
    assert.equal(result.inputTokens, null);
    assert.equal(result.outputTokens, null);
  }
});

test("local showcase: redirect, HTTP error and over-budget response fail closed", async () => {
  for (const mock of [() => new Response("", { status: 302, headers: { location: "https://example.com" } }),
    () => new Response("runtime unavailable", { status: 503 }),
    () => response("0", { usage: { completion_tokens: 65 } })]) {
    let calls = 0;
    const result = await runComparison({ fetchImpl: async () => { calls++; return mock(); } });
    assert.equal(calls, 2);
    assert.equal(result.failedGames, 2);
    assert(result.games.every(game => game.record.events.length === 0));
  }
});

test("local showcase: accepted moves survive a later illegal response as valid partial replays", async () => {
  const seen: string[] = [];
  const result = await runComparison({ fetchImpl: async () => response("0"),
    onRequest: async call => { seen.push(`request-${call.number}`); },
    onCall: async call => { seen.push(`response-${call.number}`); },
  });
  assert.equal(result.inferenceCalls, 4);
  assert.equal(result.failedGames, 2);
  for (const game of result.games) {
    assert.equal(game.record.events.length, 1);
    assert.equal(replay(game.record).state.over, false);
    assert.equal((await decodeReplay(game.replayUrl.split("#replay=")[1])).record.events.length, 1);
  }
  assert.deepEqual(seen, ["request-1", "response-1", "request-2", "response-2", "request-3", "response-3", "request-4", "response-4"]);
});

test("local showcase: total calls and wall time cannot be raised or exceeded by new requests", async () => {
  let calls = 0;
  const mock: typeof fetch = async () => response(String(calls++));
  await assert.rejects(runComparison({ fetchImpl: mock, limits: { maxCalls: 19 } }), /only be reduced/);
  assert.equal(calls, 0);
  const capped = await runComparison({ fetchImpl: mock, limits: { maxCalls: 1 } });
  assert.equal(calls, 1);
  assert.equal(capped.cappedGames, 2);
  let time = 0;
  const timed = await runComparison({ now: () => time, limits: { totalMs: 10 }, fetchImpl: async () => {
    time = 11; return response("0");
  } });
  assert.equal(timed.inferenceCalls, 1);
  assert.equal(timed.failedGames, 1);
  assert.equal(timed.cappedGames, 1);
  assert.equal(timed.games[0].record.events.length, 0);
  time = 0;
  const diskDelay = await runComparison({ now: () => time, limits: { totalMs: 10 },
    onRequest: async () => { time = 11; }, fetchImpl: async () => { throw Error("Must never dispatch"); } });
  assert.equal(diskDelay.inferenceCalls, 0);
  assert.equal(diskDelay.cappedGames, 2);
  assert.equal(LIMITS.maxCalls, 18);
});

test("local showcase: hanging requests abort within per-call deadline and remain failed", async () => {
  let aborts = 0;
  const result = await runComparison({ limits: { perCallMs: 5 }, fetchImpl: async (_input, options) =>
    new Promise<Response>((_resolve, reject) => {
      options!.signal!.addEventListener("abort", () => { aborts++; reject(Error("aborted")); }, { once: true });
    }),
  });
  assert.equal(result.failedGames, 2);
  assert.equal(result.inferenceCalls, 2);
  assert.equal(aborts, 2);
  assert(result.calls.every(call => call.failure === "Inference deadline exceeded"));
});
