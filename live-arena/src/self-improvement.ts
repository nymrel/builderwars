/** Local, outcome-trained value policies. No network, model weights, or referee mutations. */
import { createGame, applyMove, legalMoves, replayStepper, validateRules, sha256, refereeManifest, type GameState, type Rules } from "./runtime";
import { isRuleComplete } from "./outcome";

export const POLICY_SCHEMA = "builderwars.learned-value.v1";
export const FEATURE_VERSION = "board-features.v1";
export const FEATURE_COUNT = 22;
export type Policy = {
  schema: typeof POLICY_SCHEMA; features: typeof FEATURE_VERSION; referee: string;
  rules: Rules; revision: number; parent: string | null; weights: number[];
  training: { seed: number; episodes: number; completed: number; capped: number };
  digest: string;
};
export type Episode = {
  seed: number; opening: string[]; moves: string[]; winner: number | null;
  exit: "complete" | "capped"; reason: string; policies: [string, string];
};
type Trace = { x: number[]; seat: number; ply: number };
type Random = () => number;
const hash = /^[a-f0-9]{64}$/;
const clamp = (n: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, n));
function integer(n: unknown, min: number, max: number, label: string): asserts n is number {
  if (!Number.isInteger(n) || (n as number) < min || (n as number) > max) throw Error(`Invalid ${label}.`);
}
export function seeded(seed: number): Random {
  integer(seed, 0, 0xffffffff, "seed");
  let value = seed >>> 0;
  return () => {
    value = (value + 0x6d2b79f5) >>> 0;
    let t = value;
    t = Math.imul(t ^ t >>> 15, t | 1);
    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}
export class WorkBudget {
  used = 0;
  readonly deadline: number;
  constructor(readonly maxNodes = 500000, milliseconds = 120000, readonly signal?: AbortSignal) {
    integer(maxNodes, 1, 2000000, "node budget");
    integer(milliseconds, 1, 300000, "time budget");
    this.deadline = performance.now() + milliseconds;
  }
  tick() {
    this.signal?.throwIfAborted();
    if (++this.used > this.maxNodes || performance.now() >= this.deadline) throw Error("Improvement work budget exhausted; no promotion.");
  }
}
function rulesKey(rules: Rules) { return JSON.stringify(validateRules(rules)); }
function own(piece: string, seat: number) { return piece[0]?.toLowerCase() === (seat === 0 ? "w" : "b"); }

/** Fixed representation, learned coefficients. These features are not a chess engine. */
export function boardFeatures(s: GameState, seat: number): number[] {
  const x = Array<number>(FEATURE_COUNT).fill(0), { rows, cols, connect } = s.rules;
  s.cells.forEach((piece, index) => {
    if (!piece) return;
    const side = own(piece, seat) ? 0 : 1;
    if (!["w", "b"].includes(piece[0].toLowerCase())) throw Error("Unknown referee piece encoding.");
    if (s.rules.kind === "chess" && (piece.length !== 2 || !"pnbrqk".includes(piece[1]))) throw Error("Unknown chess piece encoding.");
    const type = s.rules.kind === "chess" ? "pnbrqk".indexOf(piece[1])
      : s.rules.kind === "checkers" && piece === piece.toUpperCase() ? 1 : 0;
    x[side * 6 + type] += 1 / 16;
    const row = Math.floor(index / cols), col = index % cols;
    x[18 + side] += (1 - Math.abs(col - (cols - 1) / 2) / cols) / s.cells.length;
    const pieceSeat = piece[0].toLowerCase() === "w" ? 0 : 1;
    x[20 + side] += (pieceSeat === 0 ? rows - 1 - row : row) / (rows * s.cells.length);
  });
  if (connect >= 3) {
    for (let row = 0; row < rows; row++) for (let col = 0; col < cols; col++) {
      for (const [dr, dc] of [[0, 1], [1, 0], [1, 1], [1, -1]]) {
        const er = row + dr * (connect - 1), ec = col + dc * (connect - 1);
        if (er < 0 || er >= rows || ec < 0 || ec >= cols) continue;
        let a = 0, b = 0;
        for (let i = 0; i < connect; i++) {
          const piece = s.cells[(row + dr * i) * cols + col + dc * i];
          if (piece) { if (own(piece, seat)) a++; else b++; }
        }
        if (a && !b) x[12 + Math.min(a, 3) - 1] += 1 / 20;
        if (b && !a) x[15 + Math.min(b, 3) - 1] += 1 / 20;
      }
    }
  }
  return x.map(value => clamp(value, 0, 1));
}
function estimate(weights: readonly number[], x: number[]) {
  return Math.tanh(weights.reduce((sum, weight, i) => sum + weight * x[i], 0));
}
export async function sealPolicy(body: Omit<Policy, "digest">): Promise<Policy> {
  const clean = structuredClone(body);
  const digest = await sha256(JSON.stringify(clean));
  return Object.freeze({ ...clean, rules: Object.freeze(clean.rules), training: Object.freeze(clean.training), weights: Object.freeze(clean.weights) as unknown as number[], digest });
}
export async function baselinePolicy(rules: Rules): Promise<Policy> {
  return sealPolicy({ schema: POLICY_SCHEMA, features: FEATURE_VERSION, referee: refereeManifest.digest,
    rules: validateRules(rules), revision: 0, parent: null, weights: Array(FEATURE_COUNT).fill(0),
    training: { seed: 0, episodes: 0, completed: 0, capped: 0 } });
}
export async function parsePolicy(raw: unknown): Promise<Policy> {
  if (!raw || typeof raw !== "object" || JSON.stringify(raw).length > 16000) throw Error("Invalid policy artifact.");
  const p = raw as Policy;
  if (p.schema !== POLICY_SCHEMA || p.features !== FEATURE_VERSION || p.referee !== refereeManifest.digest
    || !Array.isArray(p.weights) || p.weights.length !== FEATURE_COUNT || !p.weights.every(w => Number.isFinite(w) && Math.abs(w) <= 8)
    || !hash.test(p.digest) || !(p.parent === null || typeof p.parent === "string" && hash.test(p.parent))) throw Error("Unsupported policy or referee.");
  integer(p.revision, 0, 1000000, "policy revision");
  if (!p.training || typeof p.training !== "object") throw Error("Missing training record.");
  if (Object.keys(p.training).sort().join() !== "capped,completed,episodes,seed") throw Error("Unsupported training fields.");
  integer(p.training.seed, 0, 0xffffffff, "training seed");
  for (const k of ["episodes", "completed", "capped"] as const) integer(p.training[k], 0, 1000000, k);
  if (p.training.completed + p.training.capped !== p.training.episodes) throw Error("Inconsistent training counts.");
  const result = await sealPolicy({ schema: POLICY_SCHEMA, features: FEATURE_VERSION, referee: p.referee,
    rules: validateRules(p.rules), revision: p.revision, parent: p.parent, weights: [...p.weights], training: { ...p.training } });
  if (result.digest !== p.digest || Object.keys(p).sort().join() !== Object.keys(result).sort().join()) throw Error("Policy digest mismatch.");
  return result;
}

/** One-ply lookahead is explicit assistance; the value coefficients are trained. */
export function policyMove(s: GameState, policy: Pick<Policy, "rules" | "weights">, rng: Random, budget: WorkBudget, epsilon = 0): string {
  budget.tick();
  if (!Number.isFinite(epsilon) || epsilon < 0 || epsilon > 1) throw Error("Invalid exploration probability.");
  if (rulesKey(s.rules) !== rulesKey(policy.rules)) throw Error("Policy belongs to different rules.");
  const legal = legalMoves(s);
  if (!legal.length) throw Error("No legal moves.");
  if (rng() < epsilon) return legal[Math.floor(rng() * legal.length)];
  let best = -Infinity, choices: string[] = [];
  for (const move of legal) {
    budget.tick();
    const next = applyMove(s, move);
    const score = isRuleComplete(next) ? next.winner === null ? 0 : next.winner === s.turn ? 1 : -1
      : estimate(policy.weights, boardFeatures(next, s.turn));
    if (score > best + 1e-12) { best = score; choices = [move]; }
    else if (Math.abs(score - best) < 1e-12) choices.push(move);
  }
  return choices[Math.floor(rng() * choices.length)];
}
export function playEpisode(rules: Rules, policies: [Policy | null, Policy | null], seed: number,
  budget: WorkBudget, maxPlies = 100, openingPlies = 0, exploration = 0): { episode: Episode; trace: Trace[] } {
  integer(maxPlies, 1, 400, "ply cap"); integer(openingPlies, 0, Math.min(12, maxPlies - 1), "opening length");
  const rng = seeded(seed), step = replayStepper(rules), trace: Trace[] = [], opening: string[] = [];
  let state = createGame(rules);
  while (!state.over && state.moves.length < maxPlies) {
    budget.tick();
    const seat = state.turn, legal = legalMoves(state), inOpening = state.moves.length < openingPlies;
    const move = inOpening || !policies[seat] ? legal[Math.floor(rng() * legal.length)]
      : policyMove(state, policies[seat]!, rng, budget, exploration);
    state = step(move);
    if (inOpening) opening.push(move);
    else if (policies[seat]) trace.push({ x: boardFeatures(state, seat), seat, ply: state.moves.length });
  }
  const complete = isRuleComplete(state);
  return { episode: { seed, opening, moves: [...state.moves], winner: complete ? state.winner : null,
    exit: complete ? "complete" : "capped", reason: complete ? state.reason : "Training/evaluation ply cap",
    policies: policies.map(p => p?.digest ?? "seeded-random") as [string, string] }, trace };
}

export type TrainOptions = { seed: number; episodes: number; maxPlies: number; learningRate: number; exploration: number; excludedSeeds?: readonly number[] };
/** Completed episode returns change numeric parameters; evaluation never calls this. */
export async function trainPolicy(parent: Policy, options: TrainOptions, budget: WorkBudget,
  onEpisode?: (episode: Episode) => void): Promise<Policy> {
  const frozenParent = await parsePolicy(parent);
  integer(options.episodes, 1, 10000, "training episodes"); integer(options.seed, 0, 0xffffffff, "training seed");
  if (!(options.learningRate > 0 && options.learningRate <= 0.2) || !(options.exploration >= 0.05 && options.exploration <= 1)) throw Error("Invalid optimizer settings.");
  const rng = seeded(options.seed), weights = [...frozenParent.weights], usedSeeds = new Set(options.excludedSeeds ?? []);
  let completed = 0, capped = 0;
  for (let i = 0; i < options.episodes; i++) {
    const current = await sealPolicy({ ...withoutDigest(frozenParent), weights: [...weights] });
    // Mix self-play with an unchanged random opponent to avoid a single-policy trap.
    const opponents: [Policy | null, Policy | null] = i % 3 === 0 ? [current, null] : i % 3 === 1 ? [null, current] : [current, current];
    let episodeSeed = Math.floor(rng() * 4294967296);
    while (usedSeeds.has(episodeSeed)) { budget.tick(); episodeSeed = Math.floor(rng() * 4294967296); }
    usedSeeds.add(episodeSeed);
    const { episode, trace } = playEpisode(frozenParent.rules, opponents, episodeSeed, budget, options.maxPlies, 0, options.exploration);
    onEpisode?.(episode);
    if (episode.exit === "capped") { capped++; continue; }
    completed++;
    for (const point of trace) {
      const reward = episode.winner === null ? 0 : episode.winner === point.seat ? 1 : -1;
      const target = reward * 0.99 ** (episode.moves.length - point.ply);
      const predicted = estimate(weights, point.x), error = target - predicted;
      for (let k = 0; k < weights.length; k++) weights[k] = clamp(weights[k] + options.learningRate * error * (1 - predicted * predicted) * point.x[k], -8, 8);
    }
  }
  return sealPolicy({ ...withoutDigest(frozenParent), revision: frozenParent.revision + 1, parent: frozenParent.digest, weights,
    training: { seed: options.seed, episodes: options.episodes, completed, capped } });
}
function withoutDigest({ digest: _digest, ...body }: Policy) { return body; }

export type EvaluationPlan = { schema: "builderwars.promotion-plan.v1"; rules: Rules; referee: string;
  incumbent: string; seeds: number[]; maxPlies: number; openingPlies: number; minimumGain: number; alpha: number; digest: string };
/** Commit this plan before training. Independent seed streams, NOT unseen-position certification. */
export async function evaluationPlan(parent: Policy, seed: number, pairs = 128, maxPlies = 100): Promise<EvaluationPlan> {
  integer(pairs, 16, 512, "evaluation pairs"); integer(maxPlies, 3, 400, "evaluation ply cap");
  const rng = seeded(seed), seeds = new Set<number>();
  while (seeds.size < pairs) seeds.add(Math.floor(rng() * 4294967296));
  const body = { schema: "builderwars.promotion-plan.v1" as const, rules: parent.rules, referee: parent.referee,
    incumbent: parent.digest, seeds: [...seeds], maxPlies, openingPlies: 2, minimumGain: 0.05, alpha: 0.05 };
  return { ...body, digest: await sha256(JSON.stringify(body)) };
}
export type PromotionResult = { schema: "builderwars.promotion-result.v1"; plan: string; incumbent: string; candidate: string;
  decision: "promote" | "retain"; reason: string; pairs: number; candidateScore: number | null; incumbentScore: number | null;
  meanGain: number | null; lowerGainBound: number | null; capped: number; games: Episode[]; deltas: number[] };
export async function evaluateCandidate(parent: Policy, candidate: Policy, plan: EvaluationPlan, budget: WorkBudget): Promise<PromotionResult> {
  await parsePolicy(parent); await parsePolicy(candidate);
  const { digest, ...body } = plan;
  if (digest !== await sha256(JSON.stringify(body)) || plan.schema !== "builderwars.promotion-plan.v1" || plan.incumbent !== parent.digest
    || candidate.parent !== parent.digest || candidate.revision !== parent.revision + 1 || candidate.referee !== parent.referee || rulesKey(candidate.rules) !== rulesKey(parent.rules)
    || rulesKey(plan.rules) !== rulesKey(parent.rules) || plan.referee !== parent.referee) throw Error("Evaluation custody mismatch.");
  integer(plan.seeds.length, 16, 512, "evaluation pairs");
  if (new Set(plan.seeds).size !== plan.seeds.length || plan.alpha !== 0.05 || plan.minimumGain !== 0.05 || plan.openingPlies !== 2) throw Error("Invalid promotion gate.");
  const games: Episode[] = [], deltas: number[] = [];
  let candidateScore = 0, incumbentScore = 0, capped = 0;
  for (const seed of plan.seeds) {
    let candidatePair = 0, incumbentPair = 0;
    for (const seat of [0, 1]) for (const contender of [parent, candidate]) {
      // Common random numbers/opening, not identical moves after positions diverge.
      const seats: [Policy | null, Policy | null] = seat === 0 ? [contender, null] : [null, contender];
      const { episode } = playEpisode(parent.rules, seats, seed, budget, plan.maxPlies, plan.openingPlies);
      games.push(episode);
      if (episode.exit === "capped") { capped++; continue; }
      const score = episode.winner === null ? 0.5 : episode.winner === seat ? 1 : 0;
      if (contender === parent) incumbentPair += score / 2; else candidatePair += score / 2;
    }
    candidateScore += candidatePair; incumbentScore += incumbentPair;
    deltas.push(candidatePair - incumbentPair);
  }
  const n = deltas.length, meanGain = (candidateScore - incumbentScore) / n;
  // Hoeffding for bounded paired deltas [-1,1], treating seed-pairs as the units.
  const lowerGainBound = meanGain - Math.sqrt(2 * Math.log(1 / plan.alpha) / n);
  const promote = !capped && candidate.training.completed > 0 && lowerGainBound > plan.minimumGain;
  return { schema: "builderwars.promotion-result.v1", plan: digest, incumbent: parent.digest, candidate: candidate.digest,
    decision: promote ? "promote" : "retain", reason: capped ? "Capped games invalidate promotion; incumbent retained."
      : promote ? "Passed this local seeded-random opponent gate; not industry rank or independent certification."
      : "Insufficient demonstrated gain at the fixed threshold; incumbent retained.", pairs: n,
    candidateScore: capped ? null : candidateScore / n, incumbentScore: capped ? null : incumbentScore / n,
    meanGain: capped ? null : meanGain, lowerGainBound: capped ? null : lowerGainBound, capped, games,
    deltas: capped ? [] : deltas };
}
