/** Development diagnostics, not promotion or model-ranking authority. */
import { applyMove, createGame, legalMoves, replayStepper, refereeManifest, sha256, type GameState } from "./runtime";
import { isRuleComplete, isExhibitionLimit } from "./outcome";
import { parsePolicy, policyMove, seeded, WorkBudget, type Policy } from "./self-improvement";

export const STRENGTH_VERSION = "builderwars.strength-development.v1";
export const OPPONENTS = ["seeded-random-v1", "immediate-tactics-v1"] as const;
export type Opponent = typeof OPPONENTS[number];
export type Tactics = { legal: string[]; wins: string[]; safe: string[]; assessed: boolean };

/** Referee-derived mate/win-in-one and avoidable loss on the next reply only.
 * No evaluation engine, material heuristic or claim that a 'safe' move is good.
 */
export function tacticalChoices(state: GameState, budget: WorkBudget): Tactics {
  budget.tick();
  if (state.over) throw Error("Cannot assess a finished game.");
  const legal = legalMoves(state), wins: string[] = [], safe: string[] = [];
  let assessed = true;
  for (const move of legal) {
    budget.tick();
    const next = applyMove(state, move);
    if (isExhibitionLimit(next)) { assessed = false; continue; }
    if (isRuleComplete(next)) {
      if (next.winner === state.turn) wins.push(move);
      if (next.winner === state.turn || next.winner === null) safe.push(move);
      continue;
    }
    let loses = false;
    for (const reply of legalMoves(next)) {
      budget.tick();
      const after = applyMove(next, reply);
      if (isExhibitionLimit(after)) assessed = false;
      if (isRuleComplete(after) && after.winner === next.turn) loses = true;
    }
    if (!loses) safe.push(move);
  }
  return { legal, wins, safe, assessed };
}

export function gradeTactic(tactics: Tactics, chosen: string) {
  const legal = tactics.legal.includes(chosen);
  return {
    legal,
    assessed: legal && tactics.assessed,
    winOpportunity: legal && tactics.assessed && tactics.wins.length > 0,
    missedWin: legal && tactics.assessed && tactics.wins.length > 0 && !tactics.wins.includes(chosen),
    defenseOpportunity: legal && tactics.assessed && !tactics.wins.length && tactics.safe.length > 0 && tactics.safe.length < tactics.legal.length,
    avoidableLoss: legal && tactics.assessed && !tactics.wins.length && tactics.safe.length > 0 && !tactics.safe.includes(chosen),
  };
}

export function fixedOpponentMove(state: GameState, opponent: Opponent, seed: number, budget: WorkBudget): string {
  budget.tick();
  if (state.over) throw Error("Cannot play a finished game.");
  const random = seeded(seed), legal = legalMoves(state);
  if (opponent === "seeded-random-v1") return legal[Math.floor(random() * legal.length)];
  if (opponent !== "immediate-tactics-v1") throw Error("Unknown frozen opponent.");
  const tactics = tacticalChoices(state, budget);
  if (!tactics.assessed) throw Error("Unresolved exhibition boundary; no tactical-opponent result.");
  const choices = tactics.wins.length ? tactics.wins : tactics.safe.length ? tactics.safe : tactics.legal;
  // Fixed canonical tie-break: not trained and not an elite search engine.
  return choices[0];
}

export type StrengthGame = {
  opponent: Opponent; policySeat: number; seed: number; moves: string[];
  complete: boolean; capped: boolean; winner: number | null;
  decisions: number; assessed: number; winOpportunities: number; missedWins: number;
  defenseOpportunities: number; avoidableLosses: number; illegalMoves: number;
};

/** Public development seeds are not hidden admission data. No champion mutation. */
export async function strengthSuite(rawPolicy: Policy, seeds: number[], maxPlies: number, budget: WorkBudget) {
  const policy = await parsePolicy(rawPolicy);
  if (!Array.isArray(seeds) || !seeds.length || seeds.length > 64 || new Set(seeds).size !== seeds.length
    || !seeds.every(s => Number.isInteger(s) && s >= 0 && s <= 0xffffffff)) throw Error("Invalid development seeds.");
  // Two-ply tactical lookahead must remain below the referee's 400-ply limit.
  if (!Number.isInteger(maxPlies) || maxPlies < 1 || maxPlies > 398) throw Error("Invalid strength ply cap (1..398).");
  const games: StrengthGame[] = [];
  for (const opponent of OPPONENTS) for (const seed of seeds) for (const policySeat of [0, 1]) {
    const step = replayStepper(policy.rules), random = seeded(seed);
    let state = createGame(policy.rules);
    const row: StrengthGame = { opponent, policySeat, seed, moves: [], complete: false, capped: false, winner: null,
      decisions: 0, assessed: 0, winOpportunities: 0, missedWins: 0, defenseOpportunities: 0, avoidableLosses: 0, illegalMoves: 0 };
    while (!state.over && state.moves.length < maxPlies) {
      budget.tick();
      let move: string;
      if (state.turn === policySeat) {
        // Separate RNG stream for policy choices; never let grader search consume it.
        move = policyMove(state, policy, random, budget);
        const grade = gradeTactic(tacticalChoices(state, budget), move);
        row.decisions++;
        row.illegalMoves += Number(!grade.legal);
        row.assessed += Number(grade.assessed);
        row.winOpportunities += Number(grade.winOpportunity);
        row.missedWins += Number(grade.missedWin);
        row.defenseOpportunities += Number(grade.defenseOpportunity);
        row.avoidableLosses += Number(grade.avoidableLoss);
        if (!grade.legal) throw Error("Illegal policy response; no successful strength report.");
      } else {
        move = fixedOpponentMove(state, opponent, (seed + state.moves.length) >>> 0, budget);
      }
      state = step(move);
    }
    row.moves = [...state.moves];
    row.complete = isRuleComplete(state);
    row.capped = !row.complete;
    row.winner = row.complete ? state.winner : null;
    games.push(row);
  }
  const groups = OPPONENTS.flatMap(opponent => [0, 1].map(policySeat => {
    const rows = games.filter(g => g.opponent === opponent && g.policySeat === policySeat);
    const total = (key: "decisions" | "assessed" | "winOpportunities" | "missedWins" | "defenseOpportunities" | "avoidableLosses" | "illegalMoves") => rows.reduce((n, g) => n + g[key], 0);
    const capped = rows.filter(g => g.capped).length;
    const winOpportunities = total("winOpportunities"), defenseOpportunities = total("defenseOpportunities");
    return { opponent, policySeat, games: rows.length, completed: rows.length - capped, capped,
      score: capped ? null : rows.reduce((n, g) => n + (g.winner === null ? 0.5 : g.winner === policySeat ? 1 : 0), 0) / rows.length,
      decisions: total("decisions"), assessedDecisions: total("assessed"), illegalMoves: total("illegalMoves"),
      winOpportunities, missedWins: total("missedWins"), defenseOpportunities, avoidableLosses: total("avoidableLosses"),
      missedWinRate: winOpportunities ? total("missedWins") / winOpportunities : null,
      avoidableLossRate: defenseOpportunities ? total("avoidableLosses") / defenseOpportunities : null,
    };
  }));
  const body = { schema: STRENGTH_VERSION, partition: "public-development-only", policy: policy.digest,
    rules: policy.rules, referee: refereeManifest.digest, seeds: [...seeds], maxPlies, opponents: [...OPPONENTS],
    groups, games, promotion: "not-authorized", providerCalls: 0,
    limitations: ["No unseen-position certification or performance confidence interval.",
      "Repeated deterministic tactical-opponent games are not independent skill evidence.",
      "Immediate tactical accuracy is not full-game optimality or chess-engine strength.",
      "When a win is available, a non-winning choice is a missed win, not also an avoidable loss.",
      "Rates use assessed opportunities, including observed prefixes of capped games; outcome score is null for any capped group."] };
  return { ...body, digest: await sha256(JSON.stringify(body)) };
}
