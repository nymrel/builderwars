/** Bounded local round robins. Replay proves legal outcomes, not an authenticated execution. */
import {
  RULES, createGame, applyMove, legalMoves, moveLabel, botMove, replay,
  type RecordData,
} from "./runtime";
import { seeded } from "./self-improvement";

export type LocalGame = "tictactoe" | "connect4" | "nim";
export type LocalAgent = { id: string; name: string; policy: "first-legal" | "seeded-random" | "tactician" };
export type CompetitionPlan = {
  schema: "builderwars.local-competition-plan.v1";
  id: string;
  createdAt: string;
  agents: LocalAgent[];
  games: LocalGame[];
  seeds: number[];
  maxPlies: number;
};
export type Fixture = { id: string; game: LocalGame; seed: number; agents: [string, string] };
export type StandingRow = LocalAgent & {
  rank: number; played: number; completed: number; capped: number;
  wins: number; draws: number; losses: number; points: number; firstSeat: number; secondSeat: number;
};
const gameNames = ["tictactoe", "connect4", "nim"];
const policies = ["first-legal", "seeded-random", "tactician"];
const slug = /^[a-z][a-z0-9-]{0,31}$/;
const cappedStatus = "Unfinished match";

function exactObject(raw: unknown, keys: string[], label: string): Record<string, unknown> {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)
    || Object.keys(raw).length !== keys.length || keys.some(key => !Object.hasOwn(raw, key)))
    throw Error(`Invalid ${label}; use exactly the documented fields.`);
  return raw as Record<string, unknown>;
}
function integer(raw: unknown, min: number, max: number, label: string): number {
  if (typeof raw !== "number" || !Number.isInteger(raw) || raw < min || raw > max)
    throw Error(`Invalid ${label}.`);
  return raw;
}
export function validateCompetitionPlan(raw: unknown): CompetitionPlan {
  const plan = exactObject(raw, ["schema", "id", "createdAt", "agents", "games", "seeds", "maxPlies"], "competition plan");
  if (plan.schema !== "builderwars.local-competition-plan.v1" || typeof plan.id !== "string" || !slug.test(plan.id))
    throw Error("Invalid competition schema or ID.");
  if (typeof plan.createdAt !== "string" || plan.createdAt.length !== 24
    || !Number.isFinite(Date.parse(plan.createdAt)) || new Date(plan.createdAt).toISOString() !== plan.createdAt)
    throw Error("Use a canonical ISO creation timestamp.");
  if (!Array.isArray(plan.agents) || plan.agents.length < 3 || plan.agents.length > 8)
    throw Error("Use 3–8 local contenders.");
  const agents = plan.agents.map(rawAgent => {
    const agent = exactObject(rawAgent, ["id", "name", "policy"], "local contender");
    if (typeof agent.id !== "string" || !slug.test(agent.id) || typeof agent.name !== "string"
      || agent.name.length < 1 || agent.name.length > 64 || agent.name.trim() !== agent.name
      || /[\u0000-\u001f\u007f]/.test(agent.name)
      || Array.from(agent.name).some(char => { const cp = char.codePointAt(0)!; return cp >= 0xd800 && cp <= 0xdfff; })
      || typeof agent.policy !== "string" || !policies.includes(agent.policy))
      throw Error("Invalid local contender ID, name or policy.");
    return { id: agent.id, name: agent.name, policy: agent.policy as LocalAgent["policy"] };
  });
  if (new Set(agents.map(a => a.id)).size !== agents.length || new Set(agents.map(a => a.name)).size !== agents.length)
    throw Error("Contender IDs and names must be unique.");
  if (!Array.isArray(plan.games) || plan.games.length < 1 || plan.games.length > 3
    || plan.games.some(game => typeof game !== "string" || !gameNames.includes(game))
    || new Set(plan.games).size !== plan.games.length)
    throw Error("Choose 1–3 unique standard games: tictactoe, connect4, nim.");
  if (!Array.isArray(plan.seeds) || plan.seeds.length < 1 || plan.seeds.length > 8)
    throw Error("Use 1–8 unique uint32 seeds.");
  const seeds = plan.seeds.map(seed => integer(seed, 0, 0xffffffff, "competition seed"));
  if (new Set(seeds).size !== seeds.length) throw Error("Competition seeds must be unique.");
  return {
    schema: "builderwars.local-competition-plan.v1", id: plan.id, createdAt: plan.createdAt,
    agents, games: [...plan.games] as LocalGame[], seeds,
    maxPlies: integer(plan.maxPlies, 2, 400, "move limit"),
  };
}
export function competitionSchedule(rawPlan: CompetitionPlan): Fixture[] {
  const plan = validateCompetitionPlan(rawPlan), fixtures: Fixture[] = [];
  for (const game of plan.games) for (let a = 0; a < plan.agents.length; a++)
    for (let b = a + 1; b < plan.agents.length; b++) for (let s = 0; s < plan.seeds.length; s++)
      for (const swap of [0, 1]) fixtures.push({
        id: `${plan.id}-${game}-${s}-${a}-${b}-${swap}`, game, seed: plan.seeds[s],
        agents: swap ? [plan.agents[b].id, plan.agents[a].id] : [plan.agents[a].id, plan.agents[b].id],
      });
  return fixtures;
}
function checkedFixture(plan: CompetitionPlan, raw: Fixture): Fixture {
  const fixture = exactObject(raw, ["id", "game", "seed", "agents"], "fixture");
  const expected = competitionSchedule(plan).find(item => item.id === fixture.id);
  if (!expected || expected.game !== fixture.game || expected.seed !== fixture.seed
    || !Array.isArray(fixture.agents) || fixture.agents.length !== 2
    || fixture.agents.some((id, seat) => id !== expected.agents[seat]))
    throw Error("Fixture does not belong to this competition schedule.");
  return expected;
}
/** FNV-1a stream identity, then existing Mulberry32: independent of seat or execution order. */
function contenderRandom(game: LocalGame, seed: number, id: string) {
  let hash = 2166136261;
  for (const char of `${game}/${seed}/${id}`) hash = Math.imul(hash ^ char.charCodeAt(0), 16777619) >>> 0;
  return seeded(hash);
}
export function playCompetitionMatch(rawPlan: CompetitionPlan, rawFixture: Fixture): RecordData {
  const plan = validateCompetitionPlan(rawPlan), fixture = checkedFixture(plan, rawFixture);
  const agents = fixture.agents.map(id => plan.agents.find(agent => agent.id === id)!);
  const random = agents.map(agent => contenderRandom(fixture.game, fixture.seed, agent.id));
  let state = createGame(RULES[fixture.game]);
  const record: RecordData = {
    schema: "builderwars.exhibition.v1", id: fixture.id, createdAt: plan.createdAt, rules: state.rules,
    agents: agents.map(agent => ({ name: agent.name, kind: "bot", model: agent.id, effort: "default", strategy: "" })),
    events: [], status: "Playing",
  };
  while (!state.over && record.events.length < plan.maxPlies) {
    const seat = state.turn, agent = agents[seat], moves = legalMoves(state);
    const move = agent.policy === "first-legal" ? moves[0]
      : agent.policy === "seeded-random" ? moves[Math.floor(random[seat]() * moves.length)]
      : botMove(state, "tactician");
    const label = moveLabel(move, state);
    state = applyMove(state, move);
    // Timing is deliberately unmeasured (0), not a latency claim. No model tokens or paid calls.
    record.events.push({ move, label, seat, ply: record.events.length + 1, elapsed: 0,
      model: agent.id, tokens: null, cost: 0, comment: "" });
  }
  record.status = state.over ? state.reason : cappedStatus;
  return replay(record).record;
}
export function competitionStandings(rawPlan: CompetitionPlan, records: RecordData[]): { game: LocalGame; rows: StandingRow[] }[] {
  const plan = validateCompetitionPlan(rawPlan), fixtures = competitionSchedule(plan);
  if (!Array.isArray(records) || records.length !== fixtures.length) throw Error("Missing or extra competition matches.");
  const byId = new Map(fixtures.map(fixture => [fixture.id, fixture]));
  const seen = new Set<string>();
  const standings = plan.games.map(game => ({ game, rows: plan.agents.map(agent => ({
    ...agent, rank: 0, played: 0, completed: 0, capped: 0, wins: 0, draws: 0, losses: 0,
    points: 0, firstSeat: 0, secondSeat: 0,
  })) }));
  for (const raw of records) {
    const { record, state } = replay(raw), fixture = byId.get(record.id);
    if (!fixture || seen.has(record.id)) throw Error("Unknown or duplicated competition match.");
    seen.add(record.id);
    if (JSON.stringify(record.rules) !== JSON.stringify(RULES[fixture.game]) || record.createdAt !== plan.createdAt
      || record.events.length > plan.maxPlies || (!state.over && record.events.length !== plan.maxPlies)
      || record.status !== (state.over ? state.reason : cappedStatus))
      throw Error("Competition match rules, limit or completion evidence disagrees.");
    const rows = standings.find(group => group.game === fixture.game)!.rows;
    const agents = fixture.agents.map(id => rows.find(row => row.id === id)!);
    for (const seat of [0, 1]) {
      const agent = agents[seat], declared = record.agents[seat];
      if (declared.name !== agent.name || declared.model !== agent.id || declared.strategy !== ""
        || declared.kind !== "bot" || declared.effort !== "default")
        throw Error("Competition contender declarations disagree.");
    }
    if (record.events.some(event => event.model !== agents[event.seat].id || event.tokens !== null
      || event.cost !== 0 || event.elapsed !== 0 || event.comment !== ""))
      throw Error("Competition move declarations disagree.");
    for (const seat of [0, 1]) {
      const row = agents[seat]; row.played++; if (seat === 0) row.firstSeat++; else row.secondSeat++;
      if (!state.over) { row.capped++; continue; }
      row.completed++;
      if (state.winner === null) { row.draws++; row.points += 0.5; }
      else if (state.winner === seat) { row.wins++; row.points++; }
      else row.losses++;
    }
  }
  for (const group of standings) {
    group.rows.sort((a, b) => b.points - a.points || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
    group.rows.forEach((row, index, rows) => {
      row.rank = index && rows[index - 1].points === row.points ? rows[index - 1].rank : index + 1;
    });
  }
  return standings;
}
