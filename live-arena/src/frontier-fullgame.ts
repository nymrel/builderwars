/** Paired full-game measurements. Fixed-budget evidence, not an open leaderboard. */
import { applyMove, createGame, legalMoves, replayStepper, sha256, type GameState, type Rules } from "./runtime";
import { isRuleComplete, isExhibitionLimit } from "./outcome";
import { positionGroup } from "./frontier-cases";
import { policyMove, seeded, WorkBudget } from "./self-improvement";
import { tacticalChoices, gradeTactic, fixedOpponentMove } from "./strength";
import { parseVersion, freeze, integer, numericVersionMove, assertComparableSuccessor, type Version } from "./frontier-version";

export const FULLGAME_PROTOCOL = "builderwars.paired-fullgame.v1";
export const FULLGAME_OPPONENTS = ["immediate-tactics-v1", "material-two-ply-v1"] as const;
export type FullgameOpponent = typeof FULLGAME_OPPONENTS[number];
export function gameFamily(rules: Rules) {
  if (rules.kind === "checkers") return "checkers";
  if (["tictactoe", "connect4", "custom"].includes(rules.kind) && rules.rows * rules.cols <= 42) return "connect";
  throw Error("This bounded full-game protocol supports connect games and checkers.");
}

/** Frozen hand-authored material/center evaluator. No training data or candidate weights. */
export function frozenMaterial(state: GameState, seat: number) {
  if (isExhibitionLimit(state)) throw Error("Exhibition cap is not a material-search draw.");
  if (isRuleComplete(state)) return state.winner === null ? 0 : state.winner === seat ? 100000 : -100000;
  return state.cells.reduce((total, piece, i) => {
    if (!piece) return total;
    const own = piece.toLowerCase() === (seat === 0 ? "w" : "b");
    const material = state.rules.kind === "checkers" ? piece === piece.toUpperCase() ? 190 : 100 : 0;
    return total + (own ? 1 : -1) * (material + 4 - Math.abs(i % state.rules.cols - (state.rules.cols - 1) / 2));
  }, 0);
}
export function fullgameOpponentMove(state: GameState, opponent: FullgameOpponent, budget: WorkBudget) {
  gameFamily(state.rules);
  if (opponent === "immediate-tactics-v1") return fixedOpponentMove(state, opponent, 0, budget);
  if (opponent !== "material-two-ply-v1" || state.over) throw Error("Invalid frozen opponent/position.");
  const legal = legalMoves(state); let best = -Infinity, chosen = legal[0];
  for (const move of legal) {
    budget.tick(); const next = applyMove(state, move);
    let value = frozenMaterial(next, state.turn);
    if (!next.over) {
      value = Infinity;
      for (const reply of legalMoves(next)) { budget.tick(); value = Math.min(value, frozenMaterial(applyMove(next, reply), state.turn)); }
    }
    if (value > best) { best = value; chosen = move; }
  }
  return chosen;
}

/** Uniform PRNG-defined opening length, then uniform legal moves. No rejection sampling.
 * A trial seed is the random unit. Repeated openings are allowed and are not novel states.
 */
export function fullgameOpening(rules: Rules, seed: number) {
  gameFamily(rules); integer(seed, 0, 0xffffffff, "trial seed");
  const rng = seeded(seed), max = rules.kind === "checkers" ? 8 : rules.rows * rules.cols === 9 ? 4 : 6;
  const length = Math.floor(rng() * (max + 1));
  let state = createGame(rules); const moves: string[] = [];
  for (let i = 0; i < length; i++) {
    if (state.over) throw Error("Protocol opening reached a terminal state; do not silently resample.");
    const legal = legalMoves(state), move = legal[Math.floor(rng() * legal.length)];
    state = applyMove(state, move); moves.push(move);
  }
  if (state.over) throw Error("Protocol opening is terminal; no full-game sample.");
  return moves;
}

export type FullgameRow = {
  version: string; opponent: FullgameOpponent; seat: number; opening: string[]; moves: string[];
  exit: "complete" | "capped"; reason: string; winner: number | null; score: number | null;
  decisions: number; assessed: number; illegal: number; winOpportunities: number; missedWins: number;
  defenseOpportunities: number; avoidableLosses: number;
  inferenceNodes: number; opponentNodes: number; graderNodes: number;
  milliseconds: number; maxDecisionMilliseconds: number; providerCalls: 0;
};
export type FullgameBlock = { schema: typeof FULLGAME_PROTOCOL; seed: number; parent: string; candidate: string; games: FullgameRow[] };

function play(version: Version, opponent: FullgameOpponent, seat: number, opening: string[], maxPlies: number, deadline: number, signal?: AbortSignal): FullgameRow {
  const c = version.config, started = performance.now();
  const remaining = Math.max(1, Math.ceil(deadline - started));
  const inference = new WorkBudget(c.limits.nodes, Math.min(c.limits.milliseconds, remaining), signal);
  // Search/grading is explicitly outside the contender's identical inference allowance.
  const opposition = new WorkBudget(2000000, remaining, signal), grader = new WorkBudget(2000000, remaining, signal);
  const step = replayStepper(c.rules); let state = createGame(c.rules);
  for (const move of opening) { inference.tick(); state = step(move); }
  const row: FullgameRow = { version: version.digest, opponent, seat, opening: [...opening], moves: [], exit: "capped", reason: "Full-game ply cap",
    winner: null, score: null, decisions: 0, assessed: 0, illegal: 0, winOpportunities: 0, missedWins: 0, defenseOpportunities: 0, avoidableLosses: 0,
    inferenceNodes: 0, opponentNodes: 0, graderNodes: 0, milliseconds: 0, maxDecisionMilliseconds: 0, providerCalls: 0 };
  while (!state.over && state.moves.length < maxPlies) {
    signal?.throwIfAborted();
    if (performance.now() >= deadline) throw Error("Full-game block deadline exhausted; no successful sample.");
    let move: string;
    if (state.turn === seat) {
      if (row.decisions >= c.limits.maxCalls) throw Error("Version call allowance exhausted; no complete full-game block.");
      const decisionStarted = performance.now();
      // Exactly the bundled version executor's inference rule, including its fixed RNG.
      move = numericVersionMove(version, state, inference);
      row.maxDecisionMilliseconds = Math.max(row.maxDecisionMilliseconds, performance.now() - decisionStarted);
      const grade = gradeTactic(tacticalChoices(state, grader), move);
      row.decisions++; row.assessed += Number(grade.assessed); row.illegal += Number(!grade.legal);
      row.winOpportunities += Number(grade.winOpportunity); row.missedWins += Number(grade.missedWin);
      row.defenseOpportunities += Number(grade.defenseOpportunity); row.avoidableLosses += Number(grade.avoidableLoss);
      if (!grade.legal) throw Error("Illegal version move; full-game attempt must fail closed.");
    } else move = fullgameOpponentMove(state, opponent, opposition);
    state = step(move);
  }
  row.moves = [...state.moves]; row.inferenceNodes = inference.used; row.opponentNodes = opposition.used; row.graderNodes = grader.used;
  row.milliseconds = performance.now() - started;
  if (isRuleComplete(state)) {
    row.exit = "complete"; row.reason = state.reason; row.winner = state.winner;
    row.score = state.winner === null ? 0.5 : state.winner === seat ? 1 : 0;
  }
  return row;
}

/** One independent sampling unit contains all paired seat/opponent comparisons.
 * Randomize ONLY execution order by seed parity, never models/configuration or scores.
 */
export async function fullgameBlock(rawParent: Version, rawCandidate: Version, seed: number, maxPlies = 398, signal?: AbortSignal, milliseconds = 300000): Promise<FullgameBlock> {
  integer(milliseconds, 1, 300000, "block deadline"); const deadline = performance.now() + milliseconds;
  const parent = await parseVersion(rawParent), candidate = await parseVersion(rawCandidate);
  if (parent.config.harness.kind === "model" || !parent.config.value || !candidate.provenance.source) throw Error("Full-game numeric version required.");
  assertComparableSuccessor(parent, candidate);
  gameFamily(parent.config.rules); integer(maxPlies, 9, 398, "full-game ply cap");
  const opening = fullgameOpening(parent.config.rules, seed), games: FullgameRow[] = [];
  const versions = seed % 2 ? [candidate, parent] : [parent, candidate];
  for (const opponent of FULLGAME_OPPONENTS) for (const seat of [0, 1]) for (const version of versions) {
    signal?.throwIfAborted(); games.push(play(version, opponent, seat, opening, maxPlies, deadline, signal));
  }
  if (performance.now() >= deadline) throw Error("Full-game block deadline exhausted; no successful sample.");
  return freeze({ schema: FULLGAME_PROTOCOL, seed, parent: parent.digest, candidate: candidate.digest, games });
}

export type FullgameGate = { trials: number; alpha: number; minimumGain: number; minimumScore: number; maximumSeatRegression: number };
export const FULLGAME_GATE: Readonly<FullgameGate> = Object.freeze({ trials: 2048, alpha: 0.0125, minimumGain: 0.05, minimumScore: 0.5, maximumSeatRegression: 0 });
/** One-sided Hoeffding, bounded independent seed-block averages. No asymptotic claim. */
export function lowerBound(mean: number, trials: number, alpha: number, width: number) {
  integer(trials, 1, 8192, "confidence sample count");
  if (!Number.isFinite(mean) || !(alpha > 0 && alpha < 1) || !Number.isFinite(alpha) || !(width > 0 && width <= 2)) throw Error("Invalid confidence inputs.");
  return mean - width * Math.sqrt(Math.log(1 / alpha) / (2 * trials));
}
function validGate(gate: FullgameGate) {
  integer(gate.trials, 16, 8192, "fixed trial count");
  if (!(gate.alpha > 0 && gate.alpha <= 0.05) || !Number.isFinite(gate.alpha)
    || !(gate.minimumGain >= 0.05 && gate.minimumGain <= 1) || !(gate.minimumScore >= 0.5 && gate.minimumScore <= 1)
    || gate.maximumSeatRegression !== 0) throw Error("Unsupported full-game gate; do not relax thresholds after outcomes.");
}
export function summarizeFullgames(blocks: FullgameBlock[], gate: FullgameGate, partition: "development" | "admission") {
  validGate(gate);
  if (!["development", "admission"].includes(partition) || blocks.length !== gate.trials) throw Error("Incomplete fixed-size full-game sample.");
  const parent = blocks[0]?.parent, candidate = blocks[0]?.candidate;
  if (!parent || !candidate || parent === candidate) throw Error("Missing distinct frozen versions.");
  const total = (rows: FullgameRow[], key: "decisions" | "assessed" | "illegal" | "winOpportunities" | "missedWins" | "defenseOpportunities" | "avoidableLosses" | "inferenceNodes" | "opponentNodes" | "graderNodes" | "milliseconds") => rows.reduce((n, r) => n + r[key], 0);
  for (const block of blocks) {
    if (block.schema !== FULLGAME_PROTOCOL || block.parent !== parent || block.candidate !== candidate || block.games.length !== 8) throw Error("Mixed or incomplete paired block.");
    integer(block.seed, 0, 0xffffffff, "trial seed");
    const keys = new Set(block.games.map(r => `${r.version}/${r.opponent}/${r.seat}`));
    for (const version of [parent, candidate]) for (const opponent of FULLGAME_OPPONENTS) for (const seat of [0, 1]) if (!keys.has(`${version}/${opponent}/${seat}`)) throw Error("Missing paired stratum.");
    for (const row of block.games) {
      if (!["complete", "capped"].includes(row.exit) || (row.exit === "complete" ? ![0, 0.5, 1].includes(row.score as number) : row.score !== null)
        || ![null, 0, 1].includes(row.winner) || (row.exit === "complete" && row.score !== (row.winner === null ? 0.5 : row.winner === row.seat ? 1 : 0))) throw Error("Invalid full-game outcome.");
      for (const value of [row.decisions, row.assessed, row.illegal, row.winOpportunities, row.missedWins, row.defenseOpportunities, row.avoidableLosses, row.inferenceNodes, row.opponentNodes, row.graderNodes]) integer(value, 0, 2000000, "full-game counter");
      if (row.assessed > row.decisions || row.missedWins > row.winOpportunities || row.avoidableLosses > row.defenseOpportunities
        || row.winOpportunities + row.defenseOpportunities > row.assessed || row.providerCalls !== 0
        || !Number.isFinite(row.milliseconds) || row.milliseconds < 0 || !Number.isFinite(row.maxDecisionMilliseconds) || row.maxDecisionMilliseconds < 0) throw Error("Invalid full-game metric.");
    }
  }
  // Ten simultaneous score endpoints: overall gain/floor plus four stratum gains/floors.
  const alphaEndpoint = gate.alpha / 10, failures: string[] = [];
  const all = blocks.flatMap(b => b.games), capped = all.filter(r => r.exit !== "complete").length;
  if (capped) failures.push("incomplete-games");
  if (all.some(r => r.illegal || r.assessed !== r.decisions)) failures.push("illegal-or-unassessed");
  const groups = FULLGAME_OPPONENTS.flatMap(opponent => [0, 1].map(seat => {
    const rows = all.filter(r => r.opponent === opponent && r.seat === seat);
    const oldRows = rows.filter(r => r.version === parent), newRows = rows.filter(r => r.version === candidate);
    const complete = rows.every(r => r.exit === "complete"), score = (rs: FullgameRow[]) => rs.reduce((n, r) => n + (r.score ?? 0), 0) / rs.length;
    const gain = complete ? score(newRows) - score(oldRows) : null;
    const candidateScore = complete ? score(newRows) : null;
    const lowerGain = gain === null ? null : lowerBound(gain, gate.trials, alphaEndpoint, 2);
    const lowerScore = candidateScore === null ? null : lowerBound(candidateScore, gate.trials, alphaEndpoint, 1);
    const tactics = (rs: FullgameRow[]) => ({ decisions: total(rs, "decisions"), assessed: total(rs, "assessed"), illegal: total(rs, "illegal"),
      winOpportunities: total(rs, "winOpportunities"), missedWins: total(rs, "missedWins"), defenseOpportunities: total(rs, "defenseOpportunities"), avoidableLosses: total(rs, "avoidableLosses") });
    const before = tactics(oldRows), after = tactics(newRows);
    if (lowerGain === null || lowerGain < -gate.maximumSeatRegression) failures.push(`${opponent}/seat${seat}/regression-not-excluded`);
    // Hard sampled tactical veto, NOT a claim of zero population error or equal trajectories.
    if (after.missedWins || after.avoidableLosses) failures.push(`${opponent}/seat${seat}/tactical-error`);
    return { opponent, seat, gamesPerVersion: gate.trials, before, after, incumbentScore: complete ? score(oldRows) : null, candidateScore, meanGain: gain, lowerGain, lowerScore };
  }));
  const deltas = capped ? [] : blocks.map(b => b.games.reduce((sum, r) => sum + (r.version === candidate ? 1 : -1) * r.score!, 0) / 4);
  const meanGain = capped ? null : deltas.reduce((n, d) => n + d, 0) / gate.trials;
  const candidateScore = capped ? null : all.filter(r => r.version === candidate).reduce((n, r) => n + r.score!, 0) / (4 * gate.trials);
  const lowerGain = meanGain === null ? null : lowerBound(meanGain, gate.trials, alphaEndpoint, 2);
  const lowerScore = candidateScore === null ? null : lowerBound(candidateScore, gate.trials, alphaEndpoint, 1);
  if (lowerGain === null || lowerGain <= gate.minimumGain) failures.push("minimum-gain-not-proven");
  // A fixed 0.5 floor is an OBSERVED balanced-seat floor, not a population claim.
  // Requiring every seat's confidence bound >=0.5 would confuse first-seat
  // advantage with strength and reject exactly non-losing deterministic draws.
  if (candidateScore === null || candidateScore < gate.minimumScore) failures.push("overall-observed-floor-not-met");
  for (const opponent of FULLGAME_OPPONENTS) {
    const seats = groups.filter(g => g.opponent === opponent);
    if (seats.some(g => g.candidateScore === null) || seats.reduce((n, g) => n + (g.candidateScore ?? 0), 0) / 2 < gate.minimumScore) failures.push(`${opponent}/balanced-observed-floor-not-met`);
  }
  return freeze({ schema: FULLGAME_PROTOCOL, partition, parent, candidate, gate: { ...gate }, alphaEndpoint,
    samplingUnit: "Independent random trial seed; eight correlated games form one block, not eight samples.",
    trials: gate.trials, completedGames: all.length - capped, capped, groups, meanGain, candidateScore, lowerGain, lowerScore,
    qualification: failures.length ? "fail" : "pass", failures,
    promotion: "not-authorized", reason: partition === "development" ? "Public diagnostics never promote." : "Campaign-level provenance, replica and tactical-holdout gates still required.",
    work: [parent, candidate].map(version => { const rows = all.filter(r => r.version === version); return { version, inferenceNodes: total(rows, "inferenceNodes"),
      opponentNodes: total(rows, "opponentNodes"), graderNodes: total(rows, "graderNodes"), milliseconds: total(rows, "milliseconds"),
      maxDecisionMilliseconds: Math.max(...rows.map(r => r.maxDecisionMilliseconds)), providerCalls: 0 }; }),
    limitations: ["Conditional performance on this fixed opening/opponent distribution only.", "No unseen-position, novel-opponent, provider-base-model or global-ranking claim.",
      "Matched inference allowances and algorithms, not identical visited positions, work or wall time.", "Sampled zero-tactical-error veto does not prove zero future errors."] });
}

export async function fullgameDigest(value: unknown) { return sha256(JSON.stringify(value)); }
/** All exposed replay prefixes, not just the starting position. */
export async function fullgamePublicGroups(rules: Rules, block: FullgameBlock) {
  const groups = new Set<string>();
  for (const row of block.games) {
    const step = replayStepper(rules); let state = createGame(rules);
    groups.add(await positionGroup(state));
    for (const move of row.moves) { state = step(move); groups.add(await positionGroup(state)); }
  }
  return groups;
}
