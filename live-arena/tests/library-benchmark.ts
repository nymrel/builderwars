/** Optional local benchmark: compare old full-replay refresh with cached refresh. */
import { performance } from "node:perf_hooks";
import { MatchLibrary, canResume } from "../src/library";
import {
  RULES,
  createGame,
  applyMove,
  legalMoves,
  moveLabel,
} from "../src/games";
import { replay, type RecordData } from "../src/records";
const data = new Map<string, string>();
const storage = {
  get length() {
    return data.size;
  },
  key: (i: number) => [...data.keys()][i] ?? null,
  getItem: (key: string) => data.get(key) ?? null,
  setItem: (key: string, value: string) => {
    data.set(key, value);
  },
  removeItem: (key: string) => {
    data.delete(key);
  },
};
let fixture: RecordData;
for (let seed = 1; ; seed++) {
  let state = createGame(RULES.chess),
    random = seed;
  fixture = {
    schema: "builderwars.exhibition.v1",
    id: "bench",
    createdAt: new Date().toISOString(),
    rules: RULES.chess,
    agents: [0, 1].map((i) => ({
      name: `Bot ${i}`,
      kind: "bot",
      model: "random",
      effort: "default",
      strategy: "",
    })),
    events: [],
    status: "Paused",
  };
  while (!state.over && state.moves.length < 80) {
    random = (Math.imul(random, 1664525) + 1013904223) >>> 0;
    const moves = legalMoves(state),
      move = moves[random % moves.length];
    const event = {
      ply: state.moves.length + 1,
      seat: state.turn,
      move,
      label: moveLabel(move, state),
      elapsed: 1,
      tokens: null,
      cost: 0,
      model: "random",
      comment: "",
    };
    state = applyMove(state, move);
    fixture.events.push(event);
  }
  if (fixture.events.length === 80) break;
}
const library = new MatchLibrary(storage);
for (let i = 0; i < 20; i++)
  library.save({ ...fixture!, id: `bench-${i}` }, "own", 100);
library.list().forEach(canResume);
let start = performance.now();
for (let pass = 0; pass < 2; pass++)
  for (const text of data.values()) replay(JSON.parse(text).record);
const oldRefreshMs = performance.now() - start;
start = performance.now();
library.save({ ...fixture!, id: "bench-19" }, "own", 100);
library.list().forEach(canResume);
const cachedRefreshMs = performance.now() - start;
console.log(
  JSON.stringify({
    matches: 20,
    pliesEach: 80,
    oldFullReplayRefreshMs: Math.round(oldRefreshMs),
    cachedSaveAndRefreshMs: Math.round(cachedRefreshMs),
    relativeSpeedup: +(oldRefreshMs / cachedRefreshMs).toFixed(1),
  }),
);
