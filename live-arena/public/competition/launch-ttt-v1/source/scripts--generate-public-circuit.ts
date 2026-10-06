/** Generate and independently check actual, bounded local baseline games. No provider calls. */
import { mkdir, readFile, writeFile, copyFile, access } from "node:fs/promises";
import { resolve } from "node:path";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import { RULES, createGame, applyMove, moveLabel, replay, createProof, verifyProof, refereeManifest, sha256, type RecordData } from "../src/runtime";
import { seeded } from "../src/self-improvement";
import { safeReplay } from "../src/sharing";
import { makeMatchPackage, unknownDeclarations } from "../src/match-package";
import { matchLimits } from "../src/resources";
import { circuitMove, qualifyTicTacToeOracle } from "../src/competition-baselines";
import { circuitStandings, type Circuit, type CircuitAgent } from "../src/public-circuit";

const root = fileURLToPath(new URL("../", import.meta.url)), id = process.argv.includes("--id") ? process.argv[process.argv.indexOf("--id") + 1] : "launch-ttt-v1", base = `competition/${id}`;
if (!/^[a-z][a-z0-9-]{0,79}$/.test(id)) throw Error("Use a new bounded public cohort ID.");
const digestBytes = (b: Uint8Array) => createHash("sha256").update(b).digest("hex");
const sourcePaths = ["src/competition-baselines.ts", "src/public-circuit.ts", "scripts/generate-public-circuit.ts", "src/self-improvement.ts", "package-lock.json"];
const sources = await Promise.all(sourcePaths.map(async path => ({ path, digest: digestBytes(await readFile(resolve(root, path))) })));
const sourceDigest = await sha256(JSON.stringify({ referee: refereeManifest.digest, sources }));
const agents: CircuitAgent[] = [
  { id: "random-v1", name: "Seeded Wildcard", description: "Uniform legal moves from a declared PRNG seed.", version: "", source: sourceDigest, assistance: "Authoritative legal-move list; no lookahead", parameters: "Mulberry32; one random draw per decision" },
  { id: "tactics-v1", name: "Tactician", description: "The browser's frozen two-ply tactical baseline.", version: "", source: sourceDigest, assistance: "Legal moves, two-ply search, fixed material/center evaluation", parameters: "Deterministic canonical tie-break; no learning" },
  { id: "perfect-ttt-v1", name: "Tic-tac-toe Oracle", description: "Full minimax over standard tic-tac-toe, independently checked on every reachable unfinished position.", version: "", source: sourceDigest, assistance: "Legal moves and exhaustive minimax search", parameters: "Deterministic canonical tie-break; standard tic-tac-toe only" },
];
for (const agent of agents) agent.version = await sha256(JSON.stringify({ id: agent.id, source: sourceDigest, parameters: agent.parameters }));
const folder = resolve(root, "public", base);
try { await access(resolve(folder, "manifest.json")); if (!process.argv.includes("--replace-unpublished")) throw Error("This immutable cohort already exists. Choose a new cohort ID; never overwrite published evidence."); } catch (error) { if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error; }
const seeds = [20261006, 817263, 341729, 991337];
await mkdir(resolve(folder, "matches"), { recursive: true }); await mkdir(resolve(folder, "source"), { recursive: true }); await mkdir(resolve(folder, "referee"), { recursive: true });
const qualification = qualifyTicTacToeOracle();
const circuit: Circuit = { schema: "builderwars.public-circuit.v1", id, title: "The Launch Circuit", description: "A complete, replayable standard tic-tac-toe round robin between three declared local baselines. Bring your own contender to the open practice challenge.",
  createdAt: "2026-10-06T00:00:00.000Z", rules: RULES.tictactoe, status: "completed", referee: { ...refereeManifest,
    file: `${base}/referee/${refereeManifest.digest}.mjs`, verifier: `${base}/referee/verify-${refereeManifest.digest}.mjs` },
  source: { digest: sourceDigest, files: sources }, agents, matches: [], seeds, scoring: { win: 1, draw: 0.5, loss: 0, capped: "void", failed: "void" }, qualification };
const records: RecordData[] = [];
for (let a = 0; a < agents.length; a++) for (let b = a + 1; b < agents.length; b++) for (let k = 0; k < seeds.length; k++) for (const swap of [0, 1]) {
  const seats = swap ? [agents[b], agents[a]] : [agents[a], agents[b]], matchId = `${id}-${a}${b}-${k}-${swap}`;
  const random = seeded(seeds[k]); let state = createGame(circuit.rules);
  const record: RecordData = { schema: "builderwars.exhibition.v1", id: matchId, createdAt: circuit.createdAt, rules: circuit.rules,
    agents: seats.map(agent => ({ name: agent.name, kind: "bot", model: agent.id, effort: "default", strategy: "" })), events: [], status: "Playing" };
  while (!state.over && record.events.length < 9) {
    const seat = state.turn, start = performance.now(), move = circuitMove(state, seats[seat].id, random), elapsed = performance.now() - start;
    const label = moveLabel(move, state); state = applyMove(state, move);
    record.events.push({ move, label, seat, ply: record.events.length + 1, elapsed, model: `local/${seats[seat].id}@${seats[seat].version}`, tokens: null, cost: 0, comment: "" });
  }
  if (!state.over) throw Error("A circuit game was capped; publication refused.");
  record.status = state.reason;
  const clean = safeReplay(replay(record).record), declarations = unknownDeclarations().map((row, seat) => ({ ...row,
    builderId: "builderwars", agentId: seats[seat].id, agentRevision: seats[seat].version, harnessId: seats[seat].id, harnessRevision: sourceDigest, providerId: "bundled-local" }));
  const packet = makeMatchPackage(clean, declarations, matchLimits(9, null, true));
  const proof = await createProof(clean, refereeManifest.digest, 9, "reverified_import"); await verifyProof(proof, refereeManifest.digest);
  const json = JSON.stringify(packet, null, 2) + "\n", proofPath = `${base}/matches/${matchId}.jsonl`, packetPath = `${base}/matches/${matchId}.json`;
  await writeFile(resolve(root, "public", packetPath), json); await writeFile(resolve(root, "public", proofPath), proof);
  circuit.matches.push({ id: matchId, agents: seats.map(a => a.id) as [string, string], seed: seeds[k], path: packetPath,
    digest: digestBytes(Buffer.from(json)), proof: proofPath, proofDigest: digestBytes(Buffer.from(proof)) }); records.push(clean);
}
const standings = circuitStandings(circuit, records, { replay });
for (const file of [refereeManifest.file, refereeManifest.verifier]) await copyFile(resolve(root, "public", file), resolve(folder, "referee", file.split("/").at(-1)!));
for (const file of sourcePaths) await copyFile(resolve(root, file), resolve(folder, "source", file.replaceAll("/", "--")));
await writeFile(resolve(folder, "manifest.json"), JSON.stringify(circuit, null, 2) + "\n");
await writeFile(resolve(folder, "receipt.json"), JSON.stringify({ schema: "builderwars.public-circuit-receipt.v1", source: sourceDigest, referee: refereeManifest.digest,
  scheduled: 24, completed: 24, failed: 0, capped: 0, providerCalls: 0, qualification, standings,
  attestation: "Operator-published local execution receipt and replay verification; no independent execution or remote model attestation", createdAt: new Date().toISOString() }, null, 2) + "\n");
console.log(JSON.stringify({ publishedMatches: records.length, source: sourceDigest, qualification, standings: standings.map(r => ({ agent: r.name, points: r.points, wins: r.wins, draws: r.draws, losses: r.losses })) }, null, 2));
