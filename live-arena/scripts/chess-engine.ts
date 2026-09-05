/** Customer-local UCI analysis. Stockfish is an explicitly separate assistant,
 * never a replacement referee, provider model, or claimed learned weight update. */
import { spawn } from "node:child_process";
import { createReadStream } from "node:fs";
import { lstat } from "node:fs/promises";
import { createHash } from "node:crypto";
import { isAbsolute } from "node:path";
import { RULES, createGame, replayStepper, legalMoves, applyMove, refereeManifest, sha256, type GameState } from "../src/runtime";
import { freeze, integer, isDigest } from "../src/frontier-version";

export const CHESS_ENGINE_PROTOCOL = "builderwars.local-uci-analysis.v1";
export const STOCKFISH_19 = Object.freeze({ name: "Stockfish 19", release: "sf_19",
  source: "edb0d9db6731067ec50ce619ff372b463bc4dd5d", license: "GPL-3.0",
  releaseUrl: "https://github.com/official-stockfish/Stockfish/releases/tag/sf_19",
  windowsArchiveSha256: "3c8bf1f9ea66a09350a40df4f632288285ac206d99f33ab5842c408fc30b48a7",
  windowsBinarySha256: "45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0" });
export type EnginePin = { file: string; sha256: string; name: string };
export type EngineLimits = { nodes: number; multiPV: number; milliseconds: number };
export const ENGINE_LIMITS: Readonly<EngineLimits> = Object.freeze({ nodes: 20000, multiPV: 3, milliseconds: 5000 });
export type EngineLine = { rank: number; depth: number; nodes: number; score: { kind: "cp" | "mate"; value: number }; moves: string[] };
export function chessPosition(history: string[]) {
  if (!Array.isArray(history) || history.length > 398 || history.some(m => typeof m !== "string" || !/^[a-h][1-8][a-h][1-8][qrbn]?$/.test(m))) throw Error("Invalid bounded chess history.");
  const step = replayStepper(RULES.chess); let state = createGame(RULES.chess);
  for (const move of history) state = step(move);
  if (state.over) throw Error("Chess analysis requires a live position.");
  return state;
}
export async function binaryDigest(file: string) {
  if (!isAbsolute(file)) throw Error("Engine needs an explicit absolute executable path.");
  const stat = await lstat(file);
  if (!stat.isFile() || stat.isSymbolicLink() || stat.size > 150000000) throw Error("Invalid bounded engine executable.");
  const hash = createHash("sha256");
  for await (const chunk of createReadStream(file)) hash.update(chunk);
  return hash.digest("hex");
}
/** Only final exact PV scores are retained; aspiration bounds are not exact scores. */
export function parseEngineLine(line: string, state: GameState): EngineLine | null {
  if (!line.startsWith("info ") || /\b(lowerbound|upperbound)\b/.test(line)) return null;
  const depth = /\bdepth (\d+)\b/.exec(line), rank = /\bmultipv (\d+)\b/.exec(line), nodes = /\bnodes (\d+)\b/.exec(line);
  const score = /\bscore (cp|mate) (-?\d+)\b/.exec(line), pv = /\bpv ([a-h][1-8][a-h][1-8][qrbn]?(?: .*)?)$/.exec(line);
  if (!depth || !nodes || !score || !pv) return null;
  const moves = pv[1].split(" "); if (moves.length > 128) throw Error("Engine variation exceeds bound.");
  let next = state;
  for (const move of moves) { if (!legalMoves(next).includes(move)) throw Error("Engine variation contradicts the pinned referee."); next = applyMove(next, move); }
  const value = Number(score[2]); if (!Number.isSafeInteger(value) || Math.abs(value) > 1000000) throw Error("Invalid engine score.");
  const row: EngineLine = { rank: Number(rank?.[1] ?? 1), depth: Number(depth[1]), nodes: Number(nodes[1]), score: { kind: score[1] as "cp" | "mate", value }, moves };
  integer(row.rank, 1, 5, "engine PV rank"); integer(row.depth, 0, 300, "engine depth"); integer(row.nodes, 0, 10000000, "engine nodes");
  return row;
}

export async function analyzeChess(pin: EnginePin, history: string[], limits: EngineLimits = ENGINE_LIMITS, signal?: AbortSignal) {
  const state = chessPosition(history), settings = { ...limits }, engine = { ...pin };
  integer(settings.nodes, 100, 1000000, "engine node budget"); integer(settings.multiPV, 1, 5, "engine PV count"); integer(settings.milliseconds, 1, 10000, "engine deadline");
  if (!isDigest(engine.sha256) || !engine.name || engine.name.length > 100 || /[\r\n]/.test(engine.name)) throw Error("Invalid engine pin.");
  signal?.throwIfAborted();
  if (await binaryDigest(engine.file) !== engine.sha256) throw Error("Engine executable digest mismatch.");
  signal?.throwIfAborted();
  const started = performance.now();
  const result = await new Promise<{ name: string; bestMove: string; lines: EngineLine[] }>((resolve, reject) => {
    const child = spawn(engine.file, [], { shell: false, windowsHide: true, stdio: ["pipe", "pipe", "pipe"] });
    let phase = "uci", pending = "", bytes = 0, name = "", done = false;
    const options = new Set<string>(), lines = new Map<number, EngineLine>();
    const timer = setTimeout(() => finish(Error("Engine deadline exhausted; no replacement move.")), settings.milliseconds);
    const abort = () => finish(Error("Engine analysis cancelled."));
    signal?.addEventListener("abort", abort, { once: true });
    function finish(error?: Error, bestMove?: string) {
      if (done) return; done = true; clearTimeout(timer); signal?.removeEventListener("abort", abort);
      child.stdin.destroy(); child.kill();
      const complete = () => error ? reject(error) : resolve({ name, bestMove: bestMove!, lines: [...lines.values()].sort((a, b) => a.rank - b.rank) });
      if (child.exitCode !== null || child.signalCode !== null) complete(); else child.once("close", complete);
    }
    child.on("error", () => finish(Error("Engine process could not start.")));
    child.on("close", () => { if (!done) finish(Error("Engine exited before a complete analysis.")); });
    child.stdin.on("error", () => finish(Error("Engine input closed unexpectedly.")));
    child.stderr.on("data", (chunk: Buffer) => { bytes += chunk.length; if (bytes > 262144) finish(Error("Engine output limit exhausted.")); });
    child.stdout.on("data", (chunk: Buffer) => {
      if (done) return; bytes += chunk.length;
      if (bytes > 262144) return finish(Error("Engine output limit exhausted."));
      pending += chunk.toString("utf8");
      try {
        let end: number;
        while ((end = pending.indexOf("\n")) >= 0 && !done) {
          const line = pending.slice(0, end).trim(); pending = pending.slice(end + 1);
          if (phase === "uci") {
            if (line.startsWith("id name ")) name = line.slice(8);
            const option = /^option name (.*?) type /.exec(line); if (option) options.add(option[1]);
            if (line === "uciok") {
              if (name !== engine.name || ["Threads", "Hash", "MultiPV"].some(key => !options.has(key))) throw Error("Engine identity/options do not match the declared UCI contract.");
              phase = "ready";
              child.stdin.write(`setoption name Threads value 1\nsetoption name Hash value 16\nsetoption name MultiPV value ${settings.multiPV}\nucinewgame\nisready\n`);
            }
          } else if (phase === "ready" && line === "readyok") {
            phase = "search";
            child.stdin.write(`position startpos${history.length ? " moves " + history.join(" ") : ""}\ngo nodes ${settings.nodes}\n`);
          } else if (phase === "search") {
            const row = parseEngineLine(line, state);
            if (row && row.rank <= settings.multiPV) {
              const previous = lines.get(row.rank); if (!previous || row.depth >= previous.depth) lines.set(row.rank, row);
            }
            if (line.startsWith("bestmove ")) {
              const move = line.split(" ")[1];
              if (!legalMoves(state).includes(move) || !lines.get(1) || lines.get(1)!.moves[0] !== move) throw Error("Engine best move/PV fails referee validation.");
              finish(undefined, move);
            }
          }
        }
      } catch (error) { finish(error instanceof Error ? error : Error("Invalid engine response.")); }
    });
    child.stdin.write("uci\n");
  });
  const body = { schema: CHESS_ENGINE_PROTOCOL, engine: { name: result.name, binarySha256: engine.sha256 }, referee: refereeManifest.digest,
    history: [...history], fen: state.fen, turn: state.turn, limits: settings, threads: 1, hashMiB: 16, freshProcess: true,
    bestMove: result.bestMove, lines: result.lines, milliseconds: performance.now() - started,
    scorePerspective: "side-to-move", assistance: "external-engine-analysis-not-provider-weight-training", adjudication: "none" };
  return freeze({ ...body, digest: await sha256(JSON.stringify(body)) });
}
