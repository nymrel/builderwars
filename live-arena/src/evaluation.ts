import { replay, type RecordData } from "./runtime";
import { isExhibitionLimit, isRuleComplete } from "./outcome";

export type SeriesAttempt = { record: RecordData; exit: "finished" | "failed" | "stopped" };

/** Rule outcomes are recomputed, never inferred from a status label. */
export function summarizeSeries(attempts: SeriesAttempt[], requested: number) {
  const games = attempts.map(({ record, exit }, index) => {
    const checked = replay(record);
    const complete = isRuleComplete(checked.state);
    const capped = isExhibitionLimit(checked.state) || (!complete && exit === "finished");
    const winner = complete ? checked.state.winner : null;
    return {
      number: index + 1, complete, capped, exit,
      outcome: complete ? winner === null ? "Draw" : `${record.agents[winner].name} wins` : capped ? "Move limit" : exit === "failed" ? "Connection / move failure" : "Stopped",
      // The runner swaps seats after each finished attempt; it stops on failure/cancel.
      winnerEntrant: winner === null ? null : (winner + index % 2) % 2,
      plies: record.events.length,
    };
  });
  const events = attempts.flatMap(a => a.record.events);
  const total = (field: "cost" | "tokens") => {
    if (!events.length || events.some(e => e[field] === null)) return null;
    const value = events.reduce((sum, e) => sum + e[field]!, 0);
    return Number.isFinite(value) ? value : null;
  };
  const elapsed = events.reduce((sum, e) => sum + e.elapsed, 0);
  return {
    requested, recorded: attempts.length,
    completed: games.filter(g => g.complete).length,
    draws: games.filter(g => g.complete && g.winnerEntrant === null).length,
    capped: games.filter(g => g.capped).length,
    failed: attempts.filter(a => a.exit === "failed").length,
    stopped: attempts.filter(a => a.exit === "stopped").length,
    wins: [0, 1].map(i => games.filter(g => g.winnerEntrant === i).length),
    // An unmatched successful game is not a completed seat-swapped pair.
    completePairs: games.reduce((n, g, i) => n + (i % 2 === 1 && g.complete && games[i - 1].complete ? 1 : 0), 0),
    acceptedPlies: events.length,
    acceptedMeanLatency: events.length && Number.isFinite(elapsed) ? elapsed / events.length : null,
    acceptedReportedCost: total("cost"), acceptedReportedTokens: total("tokens"),
    games,
  };
}
