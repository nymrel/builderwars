/** Explicit two-ply numeric harness. Never substitutes for the older one-ply executor. */
import { applyMove, legalMoves, type GameState } from "./runtime";
import { isRuleComplete, isExhibitionLimit } from "./outcome";
import { boardFeatures, WorkBudget } from "./self-improvement";

export const STRATEGIC_FEATURE_VERSION = "board-features.strategic.v1";
export const STRATEGIC_FEATURE_COUNT = 26;
export const STRATEGIC_MODEL = "builderwars/strategic-value-v1";
export const STRATEGIC_TEACHER = "bounded-material-lines-three-ply-v1";
export type SearchLeaf = { features: number[] | null; terminal: number | null };
export type SearchChoice = { move: string; leaves: SearchLeaf[] };

/** Fixed features; only coefficients are learned. Checkers king progress is proximity
 * rather than forward rank, avoiding a men-only feature applied to backward kings.
 */
export function strategicFeatures(state: GameState, seat: number) {
  const x = [...boardFeatures(state, seat), 0, 0, 0, 0];
  if (state.rules.kind !== "checkers") return x;
  x[20] = 0; x[21] = 0;
  for (const side of [0, 1]) {
    const color = seat === side ? "w" : "b", own: number[] = [], enemies: number[] = [], kings: number[] = [];
    state.cells.forEach((p, i) => {
      if (!p) return;
      if (p.toLowerCase() !== color) { enemies.push(i); return; }
      own.push(i);
      if (p === p.toUpperCase()) kings.push(i);
      else {
        const row = Math.floor(i / 8);
        x[20 + side] += (color === "w" ? 7 - row : row) / 512;
        if (row === (color === "w" ? 7 : 0)) x[24 + side] += 1 / 8;
      }
    });
    if (kings.length && enemies.length) x[22 + side] = kings.reduce((sum, k) => sum + 1 - Math.min(...enemies.map(e =>
      Math.abs(Math.floor(k / 8) - Math.floor(e / 8)) + Math.abs(k % 8 - e % 8))) / 14, 0) / kings.length;
  }
  return x;
}
function leaf(state: GameState, seat: number, budget: WorkBudget): SearchLeaf {
  budget.tick();
  // The referee's cap is unfinished play, not a draw. A search horizon may
  // reach it even while the root still has a legal move; use a heuristic leaf.
  if (isExhibitionLimit(state)) return { features: strategicFeatures(state, seat), terminal: null };
  if (isRuleComplete(state)) return { features: null, terminal: state.winner === null ? 0 : state.winner === seat ? 1 : -1 };
  return { features: strategicFeatures(state, seat), terminal: null };
}
export function leafValue(value: SearchLeaf, weights: readonly number[]) {
  if (value.terminal !== null) return value.terminal;
  // Strictly inside terminal +/-1 even when tanh numerically saturates.
  return 0.98 * Math.tanh(weights.reduce((sum, w, i) => sum + w * value.features![i], 0));
}
export function leafGradient(value: SearchLeaf, weights: readonly number[]) {
  if (value.terminal !== null) return Array<number>(STRATEGIC_FEATURE_COUNT).fill(0);
  const prediction = Math.tanh(weights.reduce((sum, w, i) => sum + w * value.features![i], 0));
  return value.features!.map(x => 0.98 * (1 - prediction * prediction) * x);
}
export function twoPlyChoices(state: GameState, budget: WorkBudget): SearchChoice[] {
  if (state.over || !["tictactoe", "connect4", "custom", "checkers"].includes(state.rules.kind) || (state.rules.kind !== "checkers" && state.cells.length > 42)) throw Error("Unsupported strategic position.");
  return legalMoves(state).map(move => {
    budget.tick(); const next = applyMove(state, move);
    if (next.over) return { move, leaves: [leaf(next, state.turn, budget)] };
    // This referee encodes a complete checkers capture chain as ONE move.
    if (next.turn === state.turn) throw Error("Strategic referee turn invariant changed.");
    return { move, leaves: legalMoves(next).map(reply => { budget.tick(); return leaf(applyMove(next, reply), state.turn, budget); }) };
  });
}
export function worstLeaf(choice: SearchChoice, weights: readonly number[], budget?: WorkBudget) {
  let worst = choice.leaves[0], value = Infinity;
  for (const current of choice.leaves) { budget?.tick(); const score = leafValue(current, weights); if (score < value) { value = score; worst = current; } }
  if (!worst) throw Error("Empty search branch.");
  return { leaf: worst, value };
}
export function strategicMove(state: GameState, weights: readonly number[], random: () => number, budget: WorkBudget) {
  if (weights.length !== STRATEGIC_FEATURE_COUNT || weights.some(w => !Number.isFinite(w) || Math.abs(w) > 8)) throw Error("Invalid strategic coefficients.");
  const choices = twoPlyChoices(state, budget); let best = -Infinity, moves: string[] = [];
  for (const choice of choices) {
    const value = worstLeaf(choice, weights, budget).value;
    if (value > best + 1e-12) { best = value; moves = [choice.move]; }
    else if (Math.abs(value - best) <= 1e-12) moves.push(choice.move);
  }
  const draw = random();
  if (!(draw >= 0 && draw < 1)) throw Error("Invalid strategic random stream.");
  return moves[Math.floor(draw * moves.length)];
}

/** Public teacher, deliberately distinct from both fixed evaluation opponents.
 * Depth-three heuristic preference is NOT a solved position or referee truth.
 */
export function teacherWeights(state: GameState) {
  const w = Array<number>(STRATEGIC_FEATURE_COUNT).fill(0);
  if (state.rules.kind === "checkers") {
    w[0] = 3; w[1] = 5; w[6] = -3; w[7] = -5;
    w[18] = 0.3; w[19] = -0.3; w[20] = 0.8; w[21] = -0.8;
    w[22] = 0.35; w[23] = -0.35; w[24] = 0.12; w[25] = -0.12;
  } else {
    w[12] = 0.2; w[13] = 3; w[14] = 6; w[15] = -0.2; w[16] = -3; w[17] = -6;
    w[18] = 0.3; w[19] = -0.3;
  }
  return w;
}
export function teacherScores(state: GameState, budget: WorkBudget) {
  if (state.over) throw Error("Teacher needs an unfinished position.");
  const weights = teacherWeights(state), seat = state.turn;
  function search(position: GameState, depth: number, alpha: number, beta: number): number {
    budget.tick();
    if (position.over || depth === 0) return leafValue(leaf(position, seat, budget), weights);
    const maximize = position.turn === seat; let best = maximize ? -Infinity : Infinity;
    for (const move of legalMoves(position)) {
      const value = search(applyMove(position, move), depth - 1, alpha, beta);
      best = maximize ? Math.max(best, value) : Math.min(best, value);
      if (maximize) alpha = Math.max(alpha, best); else beta = Math.min(beta, best);
      if (alpha >= beta) break;
    }
    return best;
  }
  return legalMoves(state).map(move => ({ move, value: search(applyMove(state, move), 2, -Infinity, Infinity) }));
}
