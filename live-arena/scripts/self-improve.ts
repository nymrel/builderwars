/** Explicit local training command. No provider access, network requests or background scheduling. */
import { randomBytes, randomUUID } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { pathToFileURL } from "node:url";
import { RULES, validateRules, createGame, replayStepper, legalMoves, sha256 } from "../src/runtime";
import { baselinePolicy, parsePolicy, trainPolicy, evaluationPlan, evaluateCandidate, policyMove, seeded, WorkBudget, type Policy, type Episode, type PromotionResult } from "../src/self-improvement";

function numberOption(args: string[], name: string, fallback: number) {
  const i = args.indexOf(name);
  if (i === -1) return fallback;
  const result = Number(args[i + 1]);
  if (!Number.isInteger(result)) throw Error(`Invalid ${name}.`);
  return result;
}
function stringOption(args: string[], name: string, fallback = "") {
  const i = args.indexOf(name);
  if (i === -1) return fallback;
  if (!args[i + 1] || args[i + 1].startsWith("--")) throw Error(`Missing ${name}.`);
  return args[i + 1];
}
async function save(path: string, data: unknown) {
  await writeFile(path, JSON.stringify(data, null, 2) + "\n", { flag: "wx" });
}
export async function saveChampion(output: string, parent: Policy, candidate: Policy, result: PromotionResult) {
  if (result.incumbent !== parent.digest || result.candidate !== candidate.digest || !["promote", "retain"].includes(result.decision)) throw Error("Champion custody mismatch.");
  const champion = result.decision === "promote" ? candidate : parent;
  await save(resolve(output, "champion.json"), champion);
  await save(resolve(output, "rollback.json"), { previous: parent.digest, file: "incumbent.json", promoted: result.decision === "promote" });
  return champion;
}
export function parseMoveInput(input: string): unknown {
  if (Buffer.byteLength(input) > 64000) throw Error("Move input too large.");
  const data = input.trimStart().startsWith("{") ? input : input.slice(input.indexOf("\n") + 1);
  return JSON.parse(data);
}
/** Customer-local bridge adapter: replays history and rejects contradictory position data. */
export async function learnedMove(raw: unknown, rawPolicy: unknown) {
  const policy = await parsePolicy(rawPolicy);
  if (!raw || typeof raw !== "object" || JSON.stringify(raw).length > 64000) throw Error("Invalid bounded move request.");
  const request = raw as Record<string, any>, rules = validateRules(request.game);
  if (JSON.stringify(rules) !== JSON.stringify(policy.rules) || !Array.isArray(request.moves) || request.moves.length > 399
    || !request.moves.every((m: unknown) => typeof m === "string" && m.length <= 100)) throw Error("Game/history does not match this policy.");
  const step = replayStepper(rules);
  let state = createGame(rules);
  for (const move of request.moves) state = step(move);
  if (state.over || request.turn !== state.turn || JSON.stringify(request.position) !== JSON.stringify(state.fen || state.cells)
    || JSON.stringify(request.legalMoves) !== JSON.stringify(legalMoves(state))) throw Error("Request contradicts authoritative replay.");
  const seed = parseInt((await sha256(JSON.stringify([policy.digest, state.moves]))).slice(0, 8), 16);
  const move = policyMove(state, policy, seeded(seed), new WorkBudget(2000, 5000));
  return { move, comment: `Outcome-trained local value policy r${policy.revision}; one-ply search.`,
    model: `local-learned-value/${policy.digest}`, tokens: null, policyDigest: policy.digest };
}

export async function runTraining(args: string[]) {
  const known = new Set(["--game", "--episodes", "--pairs", "--max-plies", "--seconds", "--nodes", "--seed", "--parent", "--output"]);
  for (let i = 0; i < args.length; i += 2) if (!known.has(args[i]) || !args[i + 1]) throw Error("Unknown or incomplete training option.");
  const game = stringOption(args, "--game", "tictactoe");
  const rules = game === "custom" ? validateRules({ kind: "custom", name: "Learning Three", rows: 3, cols: 4, connect: 3, gravity: true }) : RULES[game];
  if (!rules) throw Error("Choose chess, checkers, connect4, tictactoe or custom.");
  const seed = numberOption(args, "--seed", randomBytes(4).readUInt32LE());
  const episodes = numberOption(args, "--episodes", 600), pairs = numberOption(args, "--pairs", 128);
  const maxPlies = numberOption(args, "--max-plies", 100);
  const budget = new WorkBudget(numberOption(args, "--nodes", 500000), numberOption(args, "--seconds", 120) * 1000);
  const parentPath = stringOption(args, "--parent");
  const parent = parentPath ? await parsePolicy(JSON.parse(await readFile(resolve(parentPath), "utf8"))) : await baselinePolicy(rules);
  if (JSON.stringify(parent.rules) !== JSON.stringify(validateRules(rules))) throw Error("Parent belongs to different game rules.");
  // Random reserved stream is committed before optimization. A new invocation gets a new suite.
  const plan = await evaluationPlan(parent, randomBytes(4).readUInt32LE(), pairs, maxPlies);
  const output = resolve(stringOption(args, "--output", "output/self-improvement"), `${game}-${Date.now()}-${randomUUID()}`);
  await mkdir(dirname(output), { recursive: true });
  await mkdir(output); // Never reuse or overwrite an earlier run, plan or champion receipt.
  await save(resolve(output, "plan.json"), plan);
  await save(resolve(output, "incumbent.json"), parent);
  const options = { seed, episodes, maxPlies, learningRate: 0.08, exploration: 0.25, excludedSeeds: plan.seeds };
  await save(resolve(output, "training-config.json"), options);
  await save(resolve(output, "source.json"), {
    module: await sha256(await readFile(new URL("../src/self-improvement.ts", import.meta.url), "utf8")),
    runner: await sha256(await readFile(new URL("./self-improve.ts", import.meta.url), "utf8")),
    referee: parent.referee, classification: "local source-file digests; not independent execution attestation",
  });
  const training: Episode[] = [], started = performance.now();
  try {
    const candidate = await trainPolicy(parent, options, budget, e => training.push(e));
    await save(resolve(output, "candidate.json"), candidate);
    // Claim this exact evaluation once before looking at results. Crash = spent suite.
    await save(resolve(output, "evaluation-spent.json"), { plan: plan.digest, candidate: candidate.digest });
    const result = await evaluateCandidate(parent, candidate, plan, budget);
    await save(resolve(output, "evaluation.json"), result);
    const champion = await saveChampion(output, parent, candidate, result);
    const receipt = { status: "completed", classification: "local outcome-trained linear value policy; assisted-agent class, not LLM weight training",
      game, output, parent: parent.digest, candidate: candidate.digest, champion: champion.digest, plan: plan.digest,
      decision: result.decision, reason: result.reason, training: candidate.training, pairs,
      candidateScore: result.candidateScore, incumbentScore: result.incumbentScore, lowerGainBound: result.lowerGainBound,
      capped: result.capped, nodes: budget.used, elapsedMs: performance.now() - started, providerCalls: 0,
      limits: { maxNodes: budget.maxNodes, maxPlies },
      limitation: "Single seeded-random opponent distribution. Reserved random streams, not unseen-state or industry-strength certification. No production promotion." };
    await save(resolve(output, "receipt.json"), receipt);
    return receipt;
  } catch (error) {
    await save(resolve(output, "failure.json"), { status: "failed", champion: parent.digest, decision: "retain",
      reason: error instanceof Error ? error.message : "Unknown failure", nodes: budget.used, elapsedMs: performance.now() - started, providerCalls: 0 });
    throw Error(`Run stopped without promotion. Evidence: ${output}. ${error instanceof Error ? error.message : "Failure"}`);
  } finally {
    await writeFile(resolve(output, "training-games.jsonl"), training.map(e => JSON.stringify(e)).join("\n") + "\n", { flag: "wx" });
  }
}
async function main() {
  const args = process.argv.slice(2);
  if (args[0] === "--move" && args.length === 2) {
    let input = "";
    for await (const chunk of process.stdin) {
      input += chunk.toString();
      if (Buffer.byteLength(input) > 64000) throw Error("Move input too large.");
    }
    // Existing bridge wraps the JSON in one fixed instruction line. No execution of that text.
    const policy = JSON.parse(await readFile(resolve(args[1]), "utf8"));
    console.log(JSON.stringify(await learnedMove(parseMoveInput(input), policy)));
  } else console.log(JSON.stringify(await runTraining(args), null, 2));
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main().catch(error => { console.error(error instanceof Error ? error.message : "Training failed."); process.exitCode = 1; });
}
