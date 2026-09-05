import test from "node:test";
import assert from "node:assert/strict";
import { PracticeMemory, analyzePractice, scoreTactics, profileKey, MEMORY_KEY, MEMORY_SCHEMA } from "../src/learning";
import { decide, publicAgent, type Agent } from "../src/models";
import { RULES, createGame, gamePrompt, legalMoves, replay, type RecordData, type Rules } from "../src/runtime";

const contender = (changes: Partial<Agent> = {}): Agent => ({
  name: "Learner", kind: "openrouter", model: "test/model", effort: "default",
  strategy: "PRIVATE_STRATEGY_SENTINEL", key: "CREDENTIAL_SENTINEL", endpoint: "", ...changes,
});
const agents = () => [contender(), contender({ name: "Opponent", kind: "bot", model: "random" })];
const missedWin = ["0", "3", "1", "4", "8", "5"];
const missedBlock = ["0", "3", "8", "4", "1", "5"];
function fixture(moves = missedWin, rules: Rules = RULES.tictactoe, players = agents()): RecordData {
  return {
    schema: "builderwars.exhibition.v1", id: "practice-fixture", createdAt: "2026-09-05T00:00:00Z",
    rules, agents: players.map(publicAgent), status: "Untrusted result label",
    events: moves.map((move, i) => ({ ply: i + 1, seat: (i % 2) as 0 | 1, move,
      label: "", comment: "PRIVATE_COMMENT_SENTINEL", model: "reported/model", elapsed: 1, tokens: null, cost: null })),
  };
}
class Storage {
  values = new Map<string, string>();
  getItem(key: string) { return this.values.get(key) ?? null; }
  setItem(key: string, value: string) { this.values.set(key, value); }
  removeItem(key: string) { this.values.delete(key); }
}

test("completed replay identifies a missed row win with the actual winning square", () => {
  // At ply 5, X occupies 0 and 1; O occupies 3 and 4. X must win at 2.
  const result = analyzePractice(fixture());
  assert.equal(replay(result.record).state.winner, 1);
  assert.deepEqual(result.mistakes.find(m => m.ply === 5), {
    kind: "missed-win", ply: 5, seat: 0, played: "8", better: ["2"],
    position: ["w", "w", "", "b", "b", "", "", "", ""],
  });
});

test("preventable immediate loss identifies the unique blocking square", () => {
  // X has 0 and 8; O threatens 3-4-5. Playing 1 loses; playing 5 blocks.
  const mistakes = analyzePractice(fixture(missedBlock)).mistakes;
  assert.deepEqual(mistakes.find(m => m.ply === 5), {
    kind: "allowed-immediate-loss", ply: 5, seat: 0, played: "1", better: ["5"],
    position: ["w", "", "", "b", "b", "", "", "", "w"],
  });
});

test("a fork with two threats is not mislabeled as an avoidable immediate loss", () => {
  // At ply 6 X occupies 0, 6, 8, threatening both 3 and 7; O cannot stop both.
  const result = analyzePractice(fixture(["0", "4", "8", "2", "6", "3", "7"]));
  assert.equal(replay(result.record).state.winner, 0);
  assert.equal(result.mistakes.some(m => m.ply === 6), false);
});

test("tactical diagnostics attribute decisions and mistakes across paired seat swaps", () => {
  const first = fixture();
  // First game: A misses the win at 2; B earlier failed to block that square.
  // Second game: seats swap. A fails to block at 2, and B takes the win.
  const second = fixture(["0", "3", "1", "8", "2"], RULES.tictactoe, agents().reverse());
  second.id = "seat-swapped-game";
  const records = [first, second], before = structuredClone(records);
  const expected = {
    reviewedGames: 2, excludedGames: 0,
    contenders: [
      { decisions: 5, missedWins: 1, avoidableLosses: 1 },
      { decisions: 6, missedWins: 0, avoidableLosses: 1 },
    ],
  };
  assert.deepEqual(scoreTactics(records), expected);
  assert.deepEqual(records, before, "diagnostics must not modify replay evidence");
  const partial = fixture(["0", "3"]); partial.status = "Complete";
  const unsupported = fixture(["f2f3", "e7e5", "g2g4", "d8h4"], RULES.chess);
  const tampered = fixture(); tampered.events[1].move = "0";
  assert.deepEqual(scoreTactics([...records, partial, unsupported, tampered]), { ...expected, excludedGames: 3 });
  assert.deepEqual(scoreTactics([partial, unsupported, tampered]), {
    reviewedGames: 0, excludedGames: 3,
    contenders: [
      { decisions: 0, missedWins: 0, avoidableLosses: 0 },
      { decisions: 0, missedWins: 0, avoidableLosses: 0 },
    ],
  });
});

test("partial, illegal, altered-seat and unsupported completed games cannot train", async () => {
  const partial = fixture(["0", "3"]);
  partial.status = "Learner wins";
  const illegal = fixture(); illegal.events[1].move = "0";
  const alteredSeat = fixture(); alteredSeat.events[2].seat = 1;
  const chess = fixture(["f2f3", "e7e5", "g2g4", "d8h4"], RULES.chess);
  assert.equal(replay(chess).state.over, true);
  const memory = new PracticeMemory();
  for (const record of [partial, illegal, alteredSeat, chess]) {
    assert.throws(() => analyzePractice(record));
    await assert.rejects(memory.remember(record, agents()));
    assert.equal(memory.episodeCount, 0);
  }
});

test("duplicate games are ignored across reload and contain no credentials or raw text", async () => {
  const storage = new Storage(), memory = new PracticeMemory(storage), players = agents();
  assert((await memory.remember(fixture(), players)) > 0);
  const first = await memory.context(players[0], RULES.tictactoe, "practice");
  assert(first);
  assert.equal(memory.episodeCount, 1);
  const duplicate = fixture(); duplicate.events[0].comment = "different comment";
  assert.equal(await memory.remember(duplicate, players), 0);
  const serialized = storage.getItem(MEMORY_KEY)!;
  for (const sentinel of [players[0].key, players[0].strategy, "PRIVATE_COMMENT_SENTINEL", players[0].model, players[0].name]) {
    assert.equal(serialized.includes(sentinel), false, `must not persist ${sentinel}`);
  }
  const reloaded = new PracticeMemory(storage);
  assert.equal(reloaded.persistent, true);
  assert.equal(reloaded.episodeCount, 1);
  assert.equal(await reloaded.remember(duplicate, players), 0);
  assert.deepEqual(await reloaded.context(players[0], RULES.tictactoe, "practice"), first);
});

test("fresh practice games with identical moves remain distinct learning episodes", async () => {
  const memory = new PracticeMemory(), players = agents();
  const first = fixture(), next = fixture(); next.id = "fresh-second-game";
  const learned = await memory.remember(first, players);
  assert(learned > 0);
  assert.equal(await memory.remember(next, players), learned);
  assert.equal(memory.episodeCount, 2);
  const context = await memory.context(players[0], RULES.tictactoe, "practice");
  assert(context);
  assert.equal(context.sources.length, 2);
  assert.equal(await memory.remember(next, players), 0);
});

test("memory is isolated by model, strategy, effort, local endpoint and game rules", async () => {
  const learner = contender({ kind: "harness", endpoint: "https://local.example/move" });
  const players = [learner, agents()[1]], storage = new Storage(), memory = new PracticeMemory(storage);
  await memory.remember(fixture(missedWin, RULES.tictactoe, players), players);
  const baseline = await memory.context(learner, RULES.tictactoe, "practice");
  assert(baseline);
  for (const change of [{ model: "test/other" }, { strategy: "different" }, { effort: "high" }, { endpoint: "https://other.example/move" }]) {
    const other = { ...learner, ...change };
    assert.notEqual(await profileKey(other), await profileKey(learner));
    assert.equal(await memory.context(other, RULES.tictactoe, "practice"), undefined);
  }
  assert.equal(await memory.context(learner, RULES.connect4, "practice"), undefined);
  assert.equal(await memory.context(learner, { kind: "custom", name: "Different geometry", rows: 3, cols: 4, connect: 3, gravity: false }, "practice"), undefined);
  assert.equal(storage.getItem(MEMORY_KEY)!.includes(learner.endpoint), false);
  const rotatedKey = { ...learner, key: "ROTATED_CREDENTIAL" };
  assert.equal(await profileKey(rotatedKey), await profileKey(learner));
  assert.deepEqual(await memory.context(rotatedKey, RULES.tictactoe, "practice"), baseline);
});

test("learning follows the contender through seat swaps and excludes built-in opponents", async () => {
  const learner = contender(), bot = agents()[1], memory = new PracticeMemory();
  // O neglects the required block at 2 on ply 4 and X wins there.
  const players = [bot, learner];
  await memory.remember(fixture(["0", "3", "1", "8", "2"], RULES.tictactoe, players), players);
  assert.equal(memory.episodeCount, 1);
  const context = await memory.context(learner, RULES.tictactoe, "practice");
  assert(context);
  assert.match(context.prompt, /seat 1: allowed-immediate-loss/);
  assert.equal(await memory.context(bot, RULES.tictactoe, "practice"), undefined);
});

test("frozen evaluation snapshot survives further practice and memory clearing", async () => {
  const memory = new PracticeMemory(new Storage()), players = agents();
  await memory.remember(fixture(), players);
  const snapshot = memory.snapshot();
  const frozen = await memory.context(players[0], RULES.tictactoe, "frozen-evaluation", snapshot);
  assert(frozen);
  await memory.remember(fixture(missedBlock), players);
  const updated = await memory.context(players[0], RULES.tictactoe, "practice");
  assert(updated);
  assert.notEqual(updated.digest, frozen.digest);
  assert.deepEqual(await memory.context(players[0], RULES.tictactoe, "frozen-evaluation", snapshot), frozen);
  memory.clear();
  assert.equal(memory.episodeCount, 0);
  assert.equal(await memory.context(players[0], RULES.tictactoe, "practice"), undefined);
  assert.deepEqual(await memory.context(players[0], RULES.tictactoe, "frozen-evaluation", snapshot), frozen);
});

test("denied browser storage retains usable tab memory without throwing", async () => {
  const denied = { getItem() { throw Error("denied"); }, setItem() { throw Error("denied"); }, removeItem() { throw Error("denied"); } };
  const memory = new PracticeMemory(denied), players = agents();
  assert.equal(memory.persistent, false);
  assert((await memory.remember(fixture(), players)) > 0);
  assert(await memory.context(players[0], RULES.tictactoe, "practice"));
  assert.doesNotThrow(() => memory.clear());
  assert.equal(memory.episodeCount, 0);
});

test("clearing memory invalidates an in-flight practice update", async () => {
  const storage = new Storage(), memory = new PracticeMemory(storage), players = agents();
  await memory.remember(fixture(), players);
  const next = fixture(missedBlock); next.id = "pending-game";
  const pending = memory.remember(next, players);
  memory.clear();
  assert.equal(await pending, 0);
  assert.equal(memory.episodeCount, 0);
  assert.equal(storage.getItem(MEMORY_KEY), null);
  assert.equal(await memory.context(players[0], RULES.tictactoe, "practice"), undefined);
});

test("corrupt or oversized persisted snapshots are ignored", () => {
  for (const raw of ["not json", JSON.stringify({ schema: "wrong", episodes: [] }), "x".repeat(160001)]) {
    const storage = new Storage(); storage.setItem(MEMORY_KEY, raw);
    assert.equal(new PracticeMemory(storage).episodeCount, 0);
  }
});

test("maximum schema-valid local examples stay within the bridge memory bound", async (t) => {
  // Synthetic, untrusted local storage exercises payload limits only. These
  // maximal arrays are not replay-derived games or model-performance evidence.
  const learner = contender({ kind: "harness", endpoint: "http://127.0.0.1:8765/move" });
  const profile = await profileKey(learner), storage = new Storage();
  storage.setItem(MEMORY_KEY, JSON.stringify({
    schema: MEMORY_SCHEMA,
    episodes: ["a", "b", "c", "d"].map(letter => ({
      profile, source: letter.repeat(64), rules: JSON.stringify(["connect4", 6, 7, 4, true]),
      mistakes: [{ kind: "allowed-immediate-loss", ply: 42, seat: 1, played: "41",
        better: Array.from({ length: 42 }, (_, i) => String(i)),
        position: Array.from({ length: 42 }, (_, i) => i % 2 ? "b" : "w"),
      }],
    })),
  }));
  const memory = new PracticeMemory(storage);
  assert.equal(memory.episodeCount, 4, "all bounded storage examples must be admitted");
  const context = await memory.context(learner, RULES.connect4, "practice");
  assert(context);
  assert.equal(context.sources.length, 4);
  assert.equal(context.prompt.match(/Past ply 42/g)?.length, 4);
  assert(context.prompt.length <= 4000, `bridge accepts at most 4000 characters; got ${context.prompt.length}`);
  let calls = 0;
  t.mock.method(globalThis, "fetch", async (input: RequestInfo | URL, init?: RequestInit) => {
    if (String(input).endsWith("/health")) return Response.json({ schema: "builderwars.bridge.health.v1", remainingCalls: 1, busy: false });
    assert.equal(String(input), learner.endpoint);
    const body = JSON.parse(String(init?.body));
    assert.equal(typeof body.practiceMemory, "string");
    assert.equal(body.practiceMemory, context.prompt);
    assert(body.practiceMemory.length <= 4000);
    calls++;
    return Response.json({ move: "0", model: "mock/local" });
  });
  assert.equal((await decide(createGame(RULES.connect4), learner, 256, new AbortController().signal, [], context)).move, "0");
  assert.equal(calls, 1);
});

test("OpenRouter and local bridge receive lessons only when explicitly supplied", async (t) => {
  const memory = new PracticeMemory(), players = agents();
  await memory.remember(fixture(), players);
  const context = await memory.context(players[0], RULES.tictactoe, "practice");
  assert(context);
  const posts: { url: string; body: any }[] = [];
  t.mock.method(globalThis, "fetch", async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/key")) return Response.json({ data: { is_free_tier: true } });
    if (url.endsWith("/health")) return Response.json({ schema: "builderwars.bridge.health.v1", remainingCalls: 10, busy: false });
    assert.equal(init?.method, "POST");
    posts.push({ url, body: JSON.parse(String(init?.body)) });
    if (url.endsWith("/chat/completions")) return Response.json({ model: "test/model", choices: [{ message: { content: '{"move":"0"}' } }] });
    assert.equal(url, "http://127.0.0.1:8765/move");
    return Response.json({ move: "0", model: "test/local" });
  });
  const state = createGame(RULES.tictactoe), signal = new AbortController().signal;
  const models = [{ id: "test/model", name: "Test" }];
  for (const supplied of [undefined, context]) {
    assert.equal((await decide(state, players[0], 256, signal, models, supplied)).move, "0");
  }
  assert.deepEqual(posts[0].body, {
    model: "test/model", messages: [{ role: "user", content: gamePrompt(state, players[0].strategy) }],
    max_tokens: 256, provider: { allow_fallbacks: false }, stream: false,
  });
  assert.equal(posts[1].body.messages[0].content, `${gamePrompt(state, players[0].strategy)}\n\n${context.prompt}`);
  const harness = contender({ kind: "harness", endpoint: "http://127.0.0.1:8765/move" });
  for (const supplied of [undefined, context]) {
    assert.equal((await decide(state, harness, 256, signal, models, supplied)).move, "0");
  }
  const baseline = {
    schema: "builderwars.move.v1", game: state.rules, position: state.cells, turn: state.turn,
    moves: state.moves, legalMoves: legalMoves(state), model: harness.model, effort: harness.effort,
    strategy: harness.strategy, maxTokens: 256,
  };
  assert.deepEqual(posts[2].body, baseline);
  assert.deepEqual(posts[3].body, { ...baseline, practiceMemory: context.prompt });
  assert.equal(posts.length, 4, "one provider inference per decision, no automatic retry");
});
