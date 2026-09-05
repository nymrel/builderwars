/** Explicitly synthetic fixtures; never used as real provider evidence. */
import { RULES, replayStepper, createGame, moveLabel, refereeManifest, type RecordData } from "../../src/runtime";
import { safeReplay } from "../../src/sharing";
import { sealExhibition, EXHIBITION_SCHEMA, type Exhibition } from "../../src/exhibition";
export async function exhibitionFixture(moves = ["e2e4", "c7c5"], game: 1 | 2 = 1, exit: Exhibition["exit"] = "capped") {
  const players: Exhibition["players"] = game === 1
    ? [{ route: "astra", requestedModel: "gpt-6-astra", resolvedModel: null, identityEvidence: "unreported" },
      { route: "fable", requestedModel: "fable", resolvedModel: moves.length > 1 ? "claude-fable-5-1" : null, identityEvidence: moves.length > 1 ? "provider-response" : "unreported" }]
    : [{ route: "grok", requestedModel: "cursor-grok-4.6-high", resolvedModel: null, identityEvidence: "unreported" },
      { route: "gemini", requestedModel: "gemini-3.1-pro-high", resolvedModel: null, identityEvidence: "unreported" }];
  const record: RecordData = { schema: "builderwars.exhibition.v1", id: `synthetic-exhibition-${game}`, createdAt: "2026-09-05T00:00:00.000Z", rules: RULES.chess,
    agents: players.map(p => ({ name: `Synthetic ${p.route}`, kind: "harness", model: p.requestedModel, effort: "high", strategy: "" })), events: [], status: "Fixture" };
  let state = createGame(RULES.chess); const step = replayStepper(RULES.chess);
  for (const move of moves) {
    const p = players[state.turn];
    record.events.push({ ply: record.events.length + 1, seat: state.turn as 0 | 1, move, label: moveLabel(move, state), comment: "", model: p.resolvedModel ?? `unreported:${p.requestedModel}`, elapsed: 10, tokens: 12, cost: state.turn ? 0.01 : null });
    state = step(move);
  }
  return sealExhibition({ schema: EXHIBITION_SCHEMA, record: safeReplay(record),
    source: { runner: "1".repeat(64), plan: "2".repeat(64), result: "3".repeat(64), originalProof: "4".repeat(64), referee: refereeManifest.digest },
    engine: { name: "Stockfish 19", binarySha256: "5".repeat(64), nodes: 20000, threads: 1, hashMiB: 16, multiPv: 3 },
    limits: { maxCalls: 24, maxPliesPerGame: 80, perCallMs: 120000, totalMs: 900000 }, game,
    gameAttempts: moves.length + (exit === "failed" ? 1 : 0), exit, players,
    decisions: moves.map((_, i) => ({ ply: i + 1, requestDigest: "6".repeat(64), inputTokens: 10, outputTokens: 2 })),
    verification: "replay-integrity-not-execution-attestation" });
}
