import type { GameState } from "./games";

// The referee sets `over` for both rule terminals and its hard safety stop.
// Interpret only the recomputed referee state, never the record's status text.
export function isExhibitionLimit(state: Pick<GameState, "over" | "reason">) {
  return state.over && state.reason === "400-ply exhibition limit";
}
export function isRuleComplete(state: Pick<GameState, "over" | "reason">) {
  return state.over && !isExhibitionLimit(state);
}
