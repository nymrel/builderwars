export type MatchLimits = Readonly<{ moveLimit: number; maxTokens: number | null; moveLimitKnown?: boolean }>;

export function matchLimits(moveLimit: number, maxTokens: number | null, moveLimitKnown = true): MatchLimits {
  if (!Number.isInteger(moveLimit) || moveLimit < 2 || moveLimit > 400)
    throw Error("Choose a move limit between 2 and 400.");
  if (maxTokens !== null && (!Number.isInteger(maxTokens) || maxTokens < 256 || maxTokens > 16384))
    throw Error("Choose requested tokens per move between 256 and 16384.");
  return Object.freeze({ moveLimit, maxTokens, moveLimitKnown });
}
export function limitsLabel(limits: MatchLimits | null): string {
  return limits
    ? `${limits.moveLimit} plies maximum${limits.moveLimitKnown === false ? " for recovery (original move limit unknown)" : ""} · ${limits.maxTokens === null ? "original token limit unknown" : `${limits.maxTokens} requested tokens per model move`}`
    : "Original resource settings unavailable";
}
