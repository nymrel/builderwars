/** Bounded public archive contract; scores are derived from pinned-referee replay. */
import type { RecordData } from "./records";
import type { Rules } from "./games";

export type CircuitAgent = { id: string; name: string; description: string; version: string; source: string; assistance: string; parameters: string };
export type CircuitMatch = { id: string; agents: [string, string]; seed: number; path: string; digest: string; proof: string; proofDigest: string };
export type Circuit = {
  schema: "builderwars.public-circuit.v1"; id: string; title: string; description: string; createdAt: string;
  rules: Rules; status: "completed"; referee: { digest: string; file: string; integrity: string; verifier: string };
  source: { digest: string; files: { path: string; digest: string }[] }; agents: CircuitAgent[]; matches: CircuitMatch[];
  seeds: number[]; scoring: { win: 1; draw: 0.5; loss: 0; capped: "void"; failed: "void" };
  qualification: { reachableStates: number; assessedNonterminalStates: number; illegalOrSuboptimalMoves: number; method: string; scope: string };
};
export type ReplayEngine = { replay(raw: unknown): { record: RecordData; state: { over: boolean; winner: number | null; reason: string } } };
export function circuitStandings(circuit: Circuit, records: RecordData[], engine: ReplayEngine) {
  if (circuit.schema !== "builderwars.public-circuit.v1" || records.length !== circuit.matches.length || circuit.agents.length !== 3
    || new Set(circuit.agents.map(a => a.id)).size !== circuit.agents.length || circuit.matches.length !== 24
    || new Set(circuit.matches.map(m => m.id)).size !== circuit.matches.length
    || circuit.seeds.length !== 4 || new Set(circuit.seeds).size !== 4 || circuit.seeds.some(s => !Number.isInteger(s) || s < 0 || s > 0xffffffff)
    || circuit.rules.kind !== "tictactoe" || JSON.stringify(circuit.scoring) !== JSON.stringify({win:1,draw:0.5,loss:0,capped:"void",failed:"void"})) throw Error("Incomplete or malformed public circuit.");
  const schedule = new Set<string>();
  const rows = circuit.agents.map(agent => ({ ...agent, played: 0, wins: 0, draws: 0, losses: 0, points: 0, firstSeat: 0, secondSeat: 0 }));
  for (let i = 0; i < circuit.matches.length; i++) {
    const m = circuit.matches[i], { record, state } = engine.replay(records[i]);
    if (!state.over || state.reason === "Move limit reached" || record.id !== m.id || JSON.stringify(record.rules) !== JSON.stringify(circuit.rules)) throw Error("Unverified or incomplete circuit match.");
    const agents = m.agents.map(id => rows.find(row => row.id === id));
    if (agents.some(a => !a) || m.agents[0] === m.agents[1] || !circuit.seeds.includes(m.seed)) throw Error("Invalid circuit matchup.");
    if (agents.some((a, seat) => record.agents[seat].name !== a!.name || record.agents[seat].model !== a!.id)) throw Error("Circuit contender declarations disagree.");
    const key = `${m.agents.join("/")}/${m.seed}`;
    if (schedule.has(key)) throw Error("Duplicated circuit schedule cell."); schedule.add(key);
    for (const seat of [0, 1]) {
      const row = agents[seat]!; row.played++; if (seat === 0) row.firstSeat++; else row.secondSeat++;
      if (state.winner === null) { row.draws++; row.points += 0.5; }
      else if (state.winner === seat) { row.wins++; row.points++; } else row.losses++;
    }
  }
  for (const a of circuit.agents) for (const b of circuit.agents) if (a.id !== b.id) for (const seed of circuit.seeds)
    if (!schedule.has(`${a.id}/${b.id}/${seed}`)) throw Error("Missing seat-swapped schedule cell.");
  return rows.sort((a, b) => b.points - a.points || a.id.localeCompare(b.id)).map((row, i, all) => ({ ...row,
    rank: i && all[i - 1].points === row.points ? all.findIndex(r => r.points === row.points) + 1 : i + 1 }));
}
