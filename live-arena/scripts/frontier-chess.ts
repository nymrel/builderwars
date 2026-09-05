/** Personal, consented chess exhibition through customer-local native clients.
 * Does not enable a hosted/product provider adapter or publish anything. */
import { spawn } from "node:child_process";
import { mkdir, readFile, open } from "node:fs/promises";
import { createHash } from "node:crypto";
import { resolve, dirname } from "node:path";
import { pathToFileURL } from "node:url";
import { fileURLToPath } from "node:url";
import { RULES, createGame, replayStepper, legalMoves, moveLabel, replay, createProof, refereeManifest, sha256, type RecordData } from "../src/runtime";
import { integer, freeze } from "../src/frontier-version";
import { isRuleComplete } from "../src/outcome";
import { analyzeChess, STOCKFISH_19, ENGINE_LIMITS, binaryDigest, type EnginePin } from "./chess-engine";
import { writeOnce } from "./frontier-compare";

export const CHESS_CONTEST = "builderwars.frontier-chess-exhibition.v1";
export const CHESS_PLAYERS = Object.freeze({
  astra: { name: "Astra via Codex", model: "gpt-6-astra", effort: "high" },
  fable: { name: "Fable via Claude Code", model: "fable", effort: "high" },
  grok: { name: "Grok via Cursor", model: "cursor-grok-4.6-high", effort: "high" },
  gemini: { name: "Gemini via Antigravity", model: "gemini-3.1-pro-high", effort: "high" },
});
export type ChessPlayer = keyof typeof CHESS_PLAYERS;
export type ChessDecision = { move: string; comment: string; requestedModel: string; resolvedModel: string | null;
  identityEvidence: "provider-response" | "client-reported" | "unreported"; inputTokens: number | null; outputTokens: number | null;
  listCostUsd: number | null; elapsedMilliseconds: number; toolsUsed: boolean };
export type ChessPort = (player: ChessPlayer, prompt: string, milliseconds: number) => Promise<ChessDecision>;
export type ChessLimits = { maxCalls: number; maxPliesPerGame: number; perCallMs: number; totalMs: number };
export const CHESS_LIMITS: Readonly<ChessLimits> = Object.freeze({ maxCalls: 24, maxPliesPerGame: 80, perCallMs: 120000, totalMs: 900000 });
const pairings: readonly (readonly [ChessPlayer, ChessPlayer])[] = [["astra", "fable"], ["grok", "gemini"]];

export function validateChessDecision(raw: unknown, player: ChessPlayer, legal: string[]): ChessDecision {
  if (!raw || typeof raw !== "object" || JSON.stringify(raw).length > 8000) throw Error("Invalid native-client decision.");
  const d = raw as ChessDecision;
  if (d.requestedModel !== CHESS_PLAYERS[player].model || !legal.includes(d.move) || typeof d.comment !== "string" || d.comment.length > 180
    || !["provider-response", "client-reported", "unreported"].includes(d.identityEvidence) || d.toolsUsed !== false
    || !(d.resolvedModel === null || (typeof d.resolvedModel === "string" && /^[a-zA-Z0-9._:/-]{1,160}$/.test(d.resolvedModel)))
    || ((d.resolvedModel === null) !== (d.identityEvidence === "unreported"))) throw Error("Illegal move, tool use or inconsistent model identity.");
  const expectedFamily = { astra: /^(gpt-6-astra)(?:$|[-/])/, fable: /^claude-fable-5-1(?:$|-)/,
    grok: /^(?:cursor-)?grok-4\.6(?:$|-)/, gemini: /^gemini-3\.1-pro(?:$|-)/ }[player];
  if (d.resolvedModel !== null && !expectedFamily.test(d.resolvedModel)) throw Error("Reported model is outside the selected frontier route; no substitution.");
  for (const value of [d.inputTokens, d.outputTokens]) if (value !== null) integer(value, 0, 1000000, "reported token count");
  if (d.listCostUsd !== null && (!Number.isFinite(d.listCostUsd) || d.listCostUsd < 0 || d.listCostUsd > 100)) throw Error("Invalid reported list cost.");
  if (!Number.isFinite(d.elapsedMilliseconds) || d.elapsedMilliseconds < 0 || d.elapsedMilliseconds > CHESS_LIMITS.perCallMs + 5000) throw Error("Invalid call duration.");
  return freeze({ ...d });
}
export async function chessContestSource() {
  const sources: Record<string, string> = {};
  for (const file of ["./frontier-chess.ts", "./chess-engine.ts", "./native-frontier.py", "../src/outcome.ts", "../src/runtime.ts", "../package-lock.json"]) {
    sources[file] = createHash("sha256").update(await readFile(new URL(file, import.meta.url))).digest("hex");
  }
  return sha256(JSON.stringify({ sources, referee: refereeManifest.digest, node: process.version }));
}
export function nativeFailureMessage(stderr: string): string {
  const fallback = "Native client failed or reached a resource limit; no fallback move.";
  if (stderr.length > 4096) return fallback;
  try {
    const raw = JSON.parse(stderr);
    if (raw?.code === "workspace-trust-required") return "Native client requires workspace trust; no approval bypass or fallback move.";
    if (raw?.code === "authentication-required") return "Native client requires authentication; no credential changes or fallback move.";
  } catch { /* Never expose unstructured child output. */ }
  return fallback;
}
export const nativeChessPort: ChessPort = (player, prompt, milliseconds) => new Promise((resolveCall, reject) => {
  const child = spawn("python", [fileURLToPath(new URL("./native-frontier.py", import.meta.url)), player],
    { shell: false, windowsHide: true, detached: process.platform !== "win32", stdio: ["pipe", "pipe", "pipe"] });
  let bytes = 0, data = "", stderr = "", stderrBytes = 0, failed = false, aborting = false;
  function abortTree() {
    failed = true;
    if (aborting || !child.pid || child.exitCode !== null || child.signalCode !== null) return;
    aborting = true;
    if (process.platform === "win32") {
      // The PID is from this still-live owned process handle, never a scanned name.
      const stop = spawn("taskkill", ["/PID", String(child.pid), "/T", "/F"], { windowsHide: true, stdio: "ignore" });
      stop.on("error", () => child.kill());
    } else { try { process.kill(-child.pid, "SIGKILL"); } catch { child.kill("SIGKILL"); } }
  }
  // Python owns the native-client process tree and enforces the inner deadline.
  const timer = setTimeout(abortTree, milliseconds + 15000);
  child.stdout.on("data", (chunk: Buffer) => { bytes += chunk.length; if (bytes > 16000) abortTree(); else data += chunk.toString("utf8"); });
  child.stderr.on("data", (chunk: Buffer) => {
    stderrBytes += chunk.length;
    // The wrapper emits only fixed diagnostics. Still bound and allowlist it;
    // no raw error text, accounts or tokens may enter a receipt.
    if (stderrBytes <= 4096) stderr += chunk.toString("utf8"); else stderr = "";
  });
  child.on("error", () => { clearTimeout(timer); reject(Error("Native-client wrapper unavailable.")); });
  child.on("close", code => {
    clearTimeout(timer);
    if (code !== 0 || failed) return reject(Error(nativeFailureMessage(stderrBytes <= 4096 ? stderr : "")));
    try { resolveCall(JSON.parse(data)); } catch { reject(Error("Native client returned malformed decision metadata.")); }
  });
  child.stdin.on("error", () => {});
  child.stdin.end(JSON.stringify({ prompt, milliseconds }));
});

export async function runChessContest(rawEngine: EnginePin, output: string, port: ChessPort = nativeChessPort,
  overrides: Partial<ChessLimits> = {}, services = { analyze: analyzeChess, source: chessContestSource, binaryDigest }) {
  const engine = freeze({ ...rawEngine });
  const limits = { ...CHESS_LIMITS, ...overrides };
  for (const key of Object.keys(CHESS_LIMITS) as (keyof typeof CHESS_LIMITS)[]) integer(limits[key], 1, CHESS_LIMITS[key], key);
  if (limits.maxPliesPerGame < 2) throw Error("Exhibition requires at least two plies.");
  const root = resolve(output); await mkdir(dirname(root), { recursive: true }); await mkdir(root);
  const source = await services.source(), started = performance.now(), deadline = started + limits.totalMs;
  const createdAt = new Date().toISOString(), identity = new Map<ChessPlayer, string>();
  const games = pairings.map((players, i) => ({ players, step: replayStepper(RULES.chess), state: createGame(RULES.chess), failure: null as string | null,
    record: { schema: "builderwars.exhibition.v1", id: `frontier-chess-${i + 1}-${Date.now()}`, createdAt, rules: RULES.chess,
      agents: players.map(player => ({ name: CHESS_PLAYERS[player].name, kind: "harness", model: CHESS_PLAYERS[player].model,
        effort: "high", strategy: "Declared Stockfish 19 advisor: identical 20,000-node / 3-PV analysis each turn; model chooses the move. Identity is reported separately, never independently attested." })), events: [], status: "Unfinished engine-assisted chess exhibition" } as RecordData }));
  const plan = { schema: CHESS_CONTEST, source, createdAt, rules: RULES.chess, referee: refereeManifest.digest, players: CHESS_PLAYERS, pairings,
    engine: { binarySha256: engine.sha256, name: engine.name }, engineLimits: ENGINE_LIMITS, limits,
    authority: "Operator-requested personal customer-local research; not hosted/provider-adapter enablement or external publication",
    assistance: "Equal disclosed Stockfish analysis; frontier model selects every recorded move. No replacement moves, retries, secret engine play or provider weight training.",
    scope: "Two fixed pairings, one seat assignment each; no Elo, ranking, training-uplift or fair round-robin claim." };
  await writeOnce(resolve(root, "plan.json"), plan);
  const calls: { player: ChessPlayer; game: number; decision?: ChessDecision; failure?: string; request: string }[] = [];
  try {
    while (calls.length < limits.maxCalls && performance.now() < deadline) {
      let active = false;
      // Alternate games so all four routes can participate before exhausting the call cap.
      for (let index = 0; index < games.length; index++) {
        const game = games[index];
        if (game.failure || game.state.over || game.record.events.length >= limits.maxPliesPerGame) continue;
        if (calls.length >= limits.maxCalls || performance.now() >= deadline) break;
        active = true;
        const player = game.players[game.state.turn], number = calls.length + 1, prefix = String(number).padStart(3, "0");
        try {
          if (source !== await services.source()) throw Error("Contest source changed before inference; dispatch stopped.");
          const advice = await services.analyze(engine, game.state.moves, { ...ENGINE_LIMITS, milliseconds: Math.max(1, Math.min(ENGINE_LIMITS.milliseconds, Math.floor(deadline - performance.now()))) });
          const legal = legalMoves(game.state);
          const prompt = `You are playing a real, local engine-assisted chess exhibition as ${game.state.turn === 0 ? "White" : "Black"}. Your opponent is a different frontier model. Choose your own best move to win. Do not call tools, read files, browse, or give private reasoning.\nPosition FEN: ${game.state.fen}\nFull UCI history: ${game.state.moves.join(" ") || "initial position"}\nLegal UCI moves: ${legal.join(" ")}\nEqual disclosed advisor for both players: Stockfish 19, Threads=1, Hash=16MiB, MultiPV=3, go nodes 20000, fresh process. Scores are from your side's perspective, not certain outcomes. Engine analysis: ${JSON.stringify(advice.lines.map(l => ({ rank: l.rank, score: l.score, moves: l.moves.slice(0, 8) })))}\nReturn only JSON {"move":"one legal UCI move","comment":"one short public strategy sentence"}. You may choose any legal move; there is no automatic engine substitution.`;
          const request = await sha256(prompt);
          const call: typeof calls[number] = { player, game: index + 1, request }; calls.push(call);
          await writeOnce(resolve(root, `request-${prefix}.json`), { number, game: index + 1, player, request, prompt, advice });
          const remaining = Math.floor(deadline - performance.now()); if (remaining < 1) throw Error("Contest deadline exhausted before dispatch.");
          const decision = validateChessDecision(await port(player, prompt, Math.min(limits.perCallMs, remaining)), player, legal);
          if (performance.now() >= deadline) throw Error("Contest deadline expired; late result not applied.");
          const binding = `${decision.identityEvidence}/${decision.resolvedModel}`;
          if (identity.has(player) && identity.get(player) !== binding) throw Error("Client-reported model identity changed during the contest.");
          identity.set(player, binding); call.decision = decision;
          await writeOnce(resolve(root, `response-${prefix}.json`), { number, request, decision });
          const event = { ply: game.record.events.length + 1, seat: game.state.turn as 0 | 1, move: decision.move, label: moveLabel(decision.move, game.state),
            comment: decision.comment, model: decision.resolvedModel ?? `unreported:${decision.requestedModel}`, elapsed: decision.elapsedMilliseconds,
            tokens: decision.inputTokens !== null && decision.outputTokens !== null ? decision.inputTokens + decision.outputTokens : null, cost: decision.listCostUsd };
          game.state = game.step(decision.move); game.record.events.push(event);
          console.error(`Chess game ${index + 1}, ply ${event.ply}: ${CHESS_PLAYERS[player].name} played ${event.label} (${decision.identityEvidence}).`);
        } catch (error) {
          game.failure = error instanceof Error ? error.message : "Exhibition move failed";
          const call = calls.at(-1); if (call?.player === player && call.game === index + 1 && !call.decision) call.failure = game.failure;
          await writeOnce(resolve(root, `game-${index + 1}-failure.json`), { failure: game.failure, plies: game.record.events.length, retry: false, fallback: false });
          console.error(`Chess game ${index + 1} stopped: ${game.failure}`);
        }
      }
      if (!active) break;
    }
    if (source !== await services.source() || await services.binaryDigest(engine.file) !== engine.sha256) throw Error("Contest source or engine changed during execution.");
    const summaries = [];
    for (let i = 0; i < games.length; i++) {
      const game = games[i], complete = isRuleComplete(game.state), exit = game.failure ? "failed" : complete ? "complete" : "capped";
      game.record.status = complete ? game.state.reason : game.failure ? "Failed local exhibition; no result" : "Unfinished exhibition; resource cap reached";
      replay(game.record);
      await writeOnce(resolve(root, `game-${i + 1}.json`), game.record);
      const proof = await createProof(game.record, refereeManifest.digest, limits.maxPliesPerGame, "reverified_import");
      const handle = await open(resolve(root, `game-${i + 1}.proof.jsonl`), "wx"); try { await handle.writeFile(proof); await handle.sync(); } finally { await handle.close(); }
      summaries.push({ game: i + 1, players: game.players, exit, plies: game.record.events.length, winner: complete ? game.state.winner : null, reason: game.record.status,
        modelAttested: false, proofScope: "Referee replay integrity; not provider identity or independent execution attestation." });
    }
    const result = { schema: CHESS_CONTEST, source, plan: await sha256(JSON.stringify(plan)), games: summaries, calls,
      elapsedMilliseconds: performance.now() - started, providerAttempts: calls.length, acceptedDecisions: calls.filter(c => c.decision).length,
      promotion: "not-authorized", publication: "not-performed", independentModelIdentity: false, providerWeightTraining: false };
    await writeOnce(resolve(root, "result.json"), result); return result;
  } catch (error) {
    await writeOnce(resolve(root, "failed.json"), { status: "failed", error: error instanceof Error ? error.message : "Contest failed", promotion: "not-authorized" }); throw error;
  }
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const [consent, engine, output, ...extra] = process.argv.slice(2);
  if (consent !== "--consented-native-exhibition" || !engine || !output || extra.length) {
    console.error("Use --consented-native-exhibition ABSOLUTE_STOCKFISH19_EXE NEW_OUTPUT_DIRECTORY. Calls official customer-local clients; up to 24 attempts / 15 minutes."); process.exitCode = 1;
  } else runChessContest({ file: resolve(engine), sha256: STOCKFISH_19.windowsBinarySha256, name: STOCKFISH_19.name }, output)
    .then(result => console.log(JSON.stringify({ games: result.games, providerAttempts: result.providerAttempts, acceptedDecisions: result.acceptedDecisions })))
    .catch(error => { console.error(error instanceof Error ? error.message : "Exhibition failed"); process.exitCode = 1; });
}
