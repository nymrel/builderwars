/** Declared local baselines. The perfect solver is qualified by an independent bitboard oracle. */
import { createGame, applyMove, legalMoves, botMove, RULES, type GameState } from "./runtime";

const memo = new Map<string, number>();
function minimax(state: GameState, seat: number): number {
  if (state.over) return state.winner === null ? 0 : state.winner === seat ? 1 : -1;
  const key = `${seat}/${state.turn}/${state.cells.map(c => c || ".").join("")}`;
  const cached = memo.get(key); if (cached !== undefined) return cached;
  const scores = legalMoves(state).map(move => minimax(applyMove(state, move), seat));
  const score = state.turn === seat ? Math.max(...scores) : Math.min(...scores);
  memo.set(key, score); return score;
}
export function perfectTicTacToeMove(state: GameState) {
  if (state.rules.kind !== "tictactoe" || state.over) throw Error("The tic-tac-toe oracle only plays unfinished standard tic-tac-toe.");
  const legal = legalMoves(state), seat = state.turn;
  let best = -Infinity, selected = legal[0];
  for (const move of legal) {
    const score = minimax(applyMove(state, move), seat);
    if (score > best) { best = score; selected = move; }
  }
  return selected;
}
export function circuitMove(state: GameState, id: string, random: () => number) {
  const legal = legalMoves(state); if (!legal.length) throw Error("No legal circuit move.");
  if (id === "random-v1") return legal[Math.floor(random() * legal.length)];
  if (id === "tactics-v1") return botMove(state, "tactician");
  if (id === "perfect-ttt-v1") return perfectTicTacToeMove(state);
  throw Error("Unknown circuit contender.");
}

// Independent representation and terminal calculation: no referee score or search result is used.
const wins = [0b000000111, 0b000111000, 0b111000000, 0b001001001, 0b010010010, 0b100100100, 0b100010001, 0b001010100];
const oracleMemo = new Map<string, number>();
function oracle(first: number, second: number, turn: number, root: number): number {
  const has = (bits: number) => wins.some(line => (bits & line) === line);
  if (has(first)) return root === 0 ? 1 : -1;
  if (has(second)) return root === 1 ? 1 : -1;
  if ((first | second) === 511) return 0;
  const key = `${first}/${second}/${turn}/${root}`;
  const cached = oracleMemo.get(key); if (cached !== undefined) return cached;
  const scores: number[] = [];
  for (let i = 0; i < 9; i++) if (!((first | second) & (1 << i))) scores.push(oracle(turn === 0 ? first | (1 << i) : first, turn === 1 ? second | (1 << i) : second, 1 - turn, root));
  const score = turn === root ? Math.max(...scores) : Math.min(...scores); oracleMemo.set(key, score); return score;
}
export function qualifyTicTacToeOracle() {
  const queue = [createGame(RULES.tictactoe)], seen = new Set<string>(); let assessed = 0, failures = 0;
  for (let i = 0; i < queue.length; i++) {
    const state = queue[i], key = state.cells.map(c => c || ".").join("");
    if (seen.has(key)) continue; seen.add(key); if (state.over) continue;
    let first = 0, second = 0;
    state.cells.forEach((c, j) => { if (c === "w") first |= 1 << j; else if (c === "b") second |= 1 << j; });
    const move = perfectTicTacToeMove(state), index = Number(move), expected = oracle(first, second, state.turn, state.turn);
    const actual = oracle(state.turn === 0 ? first | (1 << index) : first, state.turn === 1 ? second | (1 << index) : second, 1 - state.turn, state.turn);
    if (!legalMoves(state).includes(move) || actual !== expected) failures++;
    assessed++; for (const legal of legalMoves(state)) queue.push(applyMove(state, legal));
  }
  if (seen.size !== 5478 || failures || oracle(0, 0, 0, 0) !== 0) throw Error("Independent tic-tac-toe qualification failed.");
  return { schema: "builderwars.tictactoe-oracle-qualification.v1", reachableStates: seen.size, assessedNonterminalStates: assessed,
    illegalOrSuboptimalMoves: failures, initialPositionValue: "draw", method: "Exhaustive reachable-state comparison against independent bitboard minimax", scope: "standard tic-tac-toe only" };
}
