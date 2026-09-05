/** Offline, create-only conversion. Never starts an engine or a model client. */
import { constants } from "node:fs";
import { lstat, open } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { isDeepStrictEqual } from "node:util";
import { createGame, replayStepper, legalMoves, replay, createProof, refereeManifest, RULES, sha256 } from "../src/runtime";
import { safeReplay } from "../src/sharing";
import { sealExhibition, EXHIBITION_SCHEMA, type Exhibition } from "../src/exhibition";
import { CHESS_CONTEST, CHESS_PLAYERS, CHESS_LIMITS, validateChessDecision, type ChessPlayer, type ChessDecision } from "./frontier-chess";
import { ENGINE_LIMITS } from "./chess-engine";

const MAX_FILE = 1_500_000;
const pairings: [ChessPlayer, ChessPlayer][] = [["astra", "fable"], ["grok", "gemini"]];
function requireThat(condition: unknown, message: string): asserts condition { if (!condition) throw Error(message); }
function object(value: unknown): Record<string, any> {
  requireThat(value && typeof value === "object" && !Array.isArray(value), "Invalid receipt object.");
  return value as Record<string, any>;
}
function same(actual: unknown, expected: unknown, message: string) { requireThat(isDeepStrictEqual(actual, expected), message); }
function digest(value: unknown) { requireThat(typeof value === "string" && /^[a-f0-9]{64}$/.test(value), "Invalid historical source digest."); }
async function directory(path: string): Promise<void> {
  const info = await lstat(path);
  requireThat(info.isDirectory() && !info.isSymbolicLink(), "Receipt paths must use regular directories, not links.");
  const parent = dirname(path); if (parent !== path) await directory(parent);
}
async function exists(path: string) {
  try { await lstat(path); return true; } catch (error) { if ((error as NodeJS.ErrnoException).code === "ENOENT") return false; throw error; }
}
async function readBounded(path: string) {
  const before = await lstat(path);
  requireThat(before.isFile() && !before.isSymbolicLink() && before.size <= MAX_FILE, "Receipt must be a bounded regular non-symlink file.");
  const handle = await open(path, constants.O_RDONLY | (constants.O_NOFOLLOW ?? 0));
  try {
    const opened = await handle.stat();
    requireThat(opened.isFile() && opened.size <= MAX_FILE && opened.dev === before.dev && opened.ino === before.ino, "Receipt changed while opening.");
    const bytes = Buffer.alloc(MAX_FILE + 1);
    let length = 0;
    while (length < bytes.length) {
      const { bytesRead } = await handle.read(bytes, length, bytes.length - length, null);
      if (!bytesRead) break; length += bytesRead;
    }
    const after = await lstat(path), final = await handle.stat();
    requireThat(length <= MAX_FILE && !after.isSymbolicLink() && after.dev === opened.dev && after.ino === opened.ino
      && final.size === opened.size && final.mtimeMs === opened.mtimeMs, "Receipt changed or exceeded its size limit.");
    return bytes.subarray(0, length);
  } finally { await handle.close(); }
}
const decode = (bytes: Uint8Array) => new TextDecoder("utf-8", { fatal: true }).decode(bytes);

export async function exportExhibition(input: string, selectedGame: number, output: string): Promise<Exhibition> {
  requireThat(selectedGame === 1 || selectedGame === 2, "Select game 1 or 2.");
  const root = resolve(input), destination = resolve(output);
  await directory(root); await directory(dirname(destination));
  requireThat(!await exists(resolve(root, "failed.json")), "Whole-run failure receipt prevents export.");
  const read = (name: string) => readBounded(resolve(root, name));
  const json = async (name: string) => object(JSON.parse(decode(await read(name))));
  const plan = await json("plan.json"), resultBytes = await read("result.json"), result = object(JSON.parse(decode(resultBytes)));
  requireThat(plan.schema === CHESS_CONTEST && result.schema === CHESS_CONTEST, "Unsupported contest receipts.");
  digest(plan.source); same(result.source, plan.source, "Runner source linkage mismatch.");
  const planDigest = await sha256(JSON.stringify(plan));
  same(result.plan, planDigest, "Plan digest mismatch.");
  same(plan.referee, refereeManifest.digest, "Referee digest mismatch.");
  same(plan.rules, RULES.chess, "Unexpected exhibition rules.");
  same(plan.players, CHESS_PLAYERS, "Unexpected frontier routes.");
  same(plan.pairings, pairings, "Unexpected exhibition pairings.");
  same(plan.engineLimits, ENGINE_LIMITS, "Unexpected engine limits.");
  requireThat(object(plan.engine).name === "Stockfish 19", "Unsupported declared advisor."); digest(plan.engine.binarySha256);
  const limits = object(plan.limits);
  same(Object.keys(limits).sort(), Object.keys(CHESS_LIMITS).sort(), "Unexpected contest limit fields.");
  for (const [key, cap] of Object.entries(CHESS_LIMITS)) requireThat(Number.isSafeInteger(limits[key]) && limits[key] >= (key === "maxPliesPerGame" ? 2 : 1) && limits[key] <= cap, "Invalid contest limits.");
  requireThat(Array.isArray(result.calls) && result.calls.length <= limits.maxCalls && Array.isArray(result.games) && result.games.length === 2, "Invalid contest counts.");
  same(result.providerAttempts, result.calls.length, "Attempt count mismatch.");
  same(result.acceptedDecisions, result.calls.filter((c: any) => c?.decision !== undefined).length, "Accepted count mismatch.");
  requireThat(result.independentModelIdentity === false && result.providerWeightTraining === false && result.promotion === "not-authorized" && result.publication === "not-performed", "Unsupported execution or publication claim.");
  const calls = result.calls.map(object);
  for (const call of calls) {
    requireThat(call.game === 1 || call.game === 2, "Invalid call game.");
    requireThat(pairings[call.game - 1].includes(call.player), "Invalid call player."); digest(call.request);
    requireThat((call.decision !== undefined) !== (typeof call.failure === "string"), "Call must have exactly one decision or failure.");
  }
  let exported: Exhibition | undefined;
  // Verify both summaries: shared run counts must not contradict a sibling game.
  for (const game of [1, 2]) {
    const summary = object(result.games[game - 1]), raw = await json(`game-${game}.json`);
    const { record, state: finalState } = replay(raw);
    same(raw, record, "Replay contains unexpected or normalized fields.");
    same(record.rules, RULES.chess, "Replay rules differ from plan.");
    requireThat(new RegExp(`^frontier-chess-${game}-[0-9]+$`).test(record.id) && record.createdAt === plan.createdAt
      && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(record.createdAt), "Unexpected replay identity.");
    for (const [seat, route] of pairings[game - 1].entries()) {
      const agent = record.agents[seat]; same({ name: agent.name, model: agent.model, effort: agent.effort }, CHESS_PLAYERS[route], "Replay player differs from plan.");
      requireThat(agent.kind === "harness", "Unexpected replay player kind.");
    }
    same(summary.game, game, "Game summary order mismatch."); same(summary.players, pairings[game - 1], "Summary pairing mismatch.");
    same(summary.plies, record.events.length, "Summary ply mismatch."); same(summary.reason, record.status, "Summary reason mismatch.");
    requireThat(summary.modelAttested === false && ["complete", "capped", "failed"].includes(summary.exit), "Unsupported game result.");
    same(summary.exit === "complete", finalState.over, "Completion contradicts replay.");
    same(summary.winner, finalState.over ? finalState.winner : null, "Winner contradicts replay.");
    const proofBytes = await read(`game-${game}.proof.jsonl`);
    same(decode(proofBytes), await createProof(record, refereeManifest.digest, limits.maxPliesPerGame, "reverified_import"), "Original proof does not match replay and limits.");
    const gameCalls = calls.map((call, index) => ({ call, number: index + 1 })).filter(({ call }) => call.game === game);
    let state = createGame(RULES.chess), accepted = 0, failed = false;
    const step = replayStepper(RULES.chess), identities = new Map<ChessPlayer, ChessDecision>();
    const decisions: Exhibition["decisions"] = [];
    for (const { call, number } of gameCalls) {
      requireThat(!failed && !state.over, "Call follows a failed or completed game.");
      const player = pairings[game - 1][state.turn]; same(call.player, player, "Call turn mismatch.");
      const prefix = String(number).padStart(3, "0"), request = await json(`request-${prefix}.json`);
      same([request.number, request.game, request.player, request.request], [number, game, player, call.request], "Request linkage mismatch.");
      requireThat(typeof request.prompt === "string", "Missing original prompt."); same(await sha256(request.prompt), call.request, "Request prompt digest mismatch.");
      if (call.decision === undefined) {
        failed = true; requireThat(!await exists(resolve(root, `response-${prefix}.json`)), "Failed call has an accepted response."); continue;
      }
      const decision = validateChessDecision(call.decision, player, legalMoves(state));
      const response = await json(`response-${prefix}.json`);
      same([response.number, response.request, response.decision], [number, call.request, call.decision], "Response linkage mismatch.");
      const previous = identities.get(player);
      if (previous) same([decision.resolvedModel, decision.identityEvidence], [previous.resolvedModel, previous.identityEvidence], "Identity changed during exhibition.");
      identities.set(player, decision);
      const event = record.events[accepted]; requireThat(event, "Decision has no replay event.");
      same([event.ply, event.seat, event.move, event.comment, event.model, event.elapsed, event.tokens, event.cost],
        [accepted + 1, state.turn, decision.move, decision.comment, decision.resolvedModel ?? `unreported:${decision.requestedModel}`,
          decision.elapsedMilliseconds, decision.inputTokens === null || decision.outputTokens === null ? null : decision.inputTokens + decision.outputTokens, decision.listCostUsd], "Decision differs from replay move, identity or usage.");
      decisions.push({ ply: ++accepted, requestDigest: call.request, inputTokens: decision.inputTokens, outputTokens: decision.outputTokens });
      state = step(decision.move);
    }
    same(accepted, record.events.length, "Replay contains an unreceipted move.");
    const failurePath = resolve(root, `game-${game}-failure.json`), hasFailure = await exists(failurePath);
    same(hasFailure, summary.exit === "failed", "Failure marker contradicts summary.");
    if (hasFailure) {
      const marker = await json(`game-${game}-failure.json`);
      requireThat(typeof marker.failure === "string" && marker.plies === accepted && marker.retry === false && marker.fallback === false, "Invalid game failure marker.");
      if (failed) same(marker.failure, gameCalls.at(-1)!.call.failure, "Failure receipt linkage mismatch.");
    }
    requireThat(!failed || hasFailure, "Failed call lacks a failure marker.");
    const payload: Omit<Exhibition, "digest"> = {
      schema: EXHIBITION_SCHEMA, record: safeReplay(record),
      source: { runner: plan.source, plan: planDigest, result: await sha256(resultBytes), originalProof: await sha256(proofBytes), referee: refereeManifest.digest },
      engine: { name: plan.engine.name, binarySha256: plan.engine.binarySha256, nodes: 20000, threads: 1, hashMiB: 16, multiPv: 3 },
      limits: { maxCalls: limits.maxCalls, maxPliesPerGame: limits.maxPliesPerGame, perCallMs: limits.perCallMs, totalMs: limits.totalMs },
      game, gameAttempts: gameCalls.length, exit: summary.exit,
      players: pairings[game - 1].map(route => ({ route, requestedModel: CHESS_PLAYERS[route].model,
        resolvedModel: identities.get(route)?.resolvedModel ?? null, identityEvidence: identities.get(route)?.identityEvidence ?? "unreported" })) as Exhibition["players"],
      decisions, verification: "replay-integrity-not-execution-attestation" as const,
    };
    const checked = await sealExhibition(payload);
    if (game === selectedGame) exported = checked;
  }
  requireThat(exported, "Selected exhibition is unavailable.");
  requireThat(!await exists(resolve(root, "failed.json")), "Whole-run failure receipt prevents export.");
  await directory(dirname(destination));
  const handle = await open(destination, "wx", 0o600);
  try { await handle.writeFile(JSON.stringify(exported, null, 2) + "\n"); await handle.sync(); } finally { await handle.close(); }
  return exported;
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const [root, game, output, ...extra] = process.argv.slice(2);
  if (!root || !["1", "2"].includes(game) || !output || extra.length) {
    console.error("Usage: export-exhibition.ts RECEIPT_DIRECTORY GAME_1_OR_2 NEW_OUTPUT_JSON"); process.exitCode = 1;
  } else exportExhibition(root, Number(game), output).then(value => console.log(`Exported game ${value.game}: ${value.exit}; replay integrity only.`))
    .catch(() => { console.error("Export rejected: inconsistent, unsafe, missing receipts or existing destination. No source artifacts changed."); process.exitCode = 1; });
}
