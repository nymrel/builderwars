/** Explicit local CLI; no background processes, downloads, credentials or model calls. */
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { RULES, createGame, replayStepper, legalMoves, validateRules } from "../src/runtime";
import { openVersionSession, rulesKey, type Version } from "../src/frontier-version";
import { parseMoveInput } from "./self-improve";
import { FrontierStore } from "./frontier-store";

export async function versionMove(raw: unknown, version: Version) {
  if (!raw || typeof raw !== "object" || JSON.stringify(raw).length > 64000) throw Error("Invalid bounded versioned move request.");
  const request = raw as Record<string, any>;
  if (request.schema !== "builderwars.move.v1" || rulesKey(validateRules(request.game)) !== rulesKey(version.config.rules)
    || (request.version !== undefined && request.version !== version.digest) || !Array.isArray(request.moves) || request.moves.length > 397
    || !request.moves.every((m: unknown) => typeof m === "string" && m.length <= 100)) throw Error("Move request/version mismatch.");
  let state = createGame(version.config.rules); const step = replayStepper(version.config.rules);
  for (const move of request.moves) state = step(move);
  if (state.over || request.turn !== state.turn || JSON.stringify(request.position) !== JSON.stringify(state.fen || state.cells)
    || JSON.stringify(request.legalMoves) !== JSON.stringify(legalMoves(state))) throw Error("Move request contradicts authoritative replay.");
  if (version.config.harness.kind !== "linear-value") throw Error("This CLI only executes its bundled numeric harness.");
  const session = await openVersionSession(version);
  try { return { ...await session.move(state), comment: "Frozen local tactical-value version; one-ply assistance, not LLM weight training." }; }
  finally { session.cancel(); }
}
export async function frontier(args: string[], input?: string) {
  const [command, ...rest] = args;
  const allowed: Record<string, string[]> = {
    init: ["--store", "--id", "--game", "--training", "--development", "--admission", "--attempts"],
    run: ["--store", "--id", "--passes", "--rate", "--margin"],
    admit: ["--store", "--id", "--slot"], status: ["--store", "--id"], close: ["--store", "--id"], move: ["--store", "--version"],
  };
  if (!allowed[command]) throw Error("Choose init, run, admit, status, close or move.");
  const values = new Map<string, string>();
  for (let i = 0; i < rest.length; i += 2) {
    if (!allowed[command].includes(rest[i]) || !rest[i + 1] || rest[i + 1].startsWith("--") || values.has(rest[i])) throw Error("Unknown, duplicate or incomplete frontier option.");
    values.set(rest[i], rest[i + 1]);
  }
  const store = new FrontierStore(values.get("--store")), id = values.get("--id") ?? "";
  const number = (key: string, fallback: number) => Number(values.get(key) ?? fallback);
  if (command === "init") {
    const game = values.get("--game") ?? "tictactoe";
    if (!Object.hasOwn(RULES, game)) throw Error("Choose a built-in game.");
    return store.initialize(id, RULES[game], { training: number("--training", 32), development: number("--development", 16), admission: number("--admission", 16), attempts: number("--attempts", 2) });
  }
  if (command === "run") return store.run(id, { passes: number("--passes", 8), rate: number("--rate", 0.2), margin: number("--margin", 0.1) });
  if (command === "admit") return store.admit(id, number("--slot", 0));
  if (command === "status") return store.status(id);
  if (command === "close") return store.close(id);
  if (input === undefined) throw Error("Move mode requires bounded JSON on stdin.");
  return versionMove(parseMoveInput(input), await store.loadVersion(values.get("--version") ?? ""));
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  (async () => {
    let input: string | undefined;
    if (process.argv[2] === "move") {
      input = "";
      for await (const chunk of process.stdin) { input += chunk.toString(); if (Buffer.byteLength(input) > 64000) throw Error("Move input too large."); }
    }
    console.log(JSON.stringify(await frontier(process.argv.slice(2), input), null, 2));
  })().catch(error => { console.error(error instanceof Error ? error.message : "Frontier command failed."); process.exitCode = 1; });
}
