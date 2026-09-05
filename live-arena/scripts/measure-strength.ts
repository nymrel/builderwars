/** Bounded local development qualification, never a production promotion. */
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { randomUUID } from "node:crypto";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { RULES, sha256 } from "../src/runtime";
import { baselinePolicy, parsePolicy, WorkBudget } from "../src/self-improvement";
import { strengthSuite } from "../src/strength";

export async function measureStrength(args: string[]) {
  const known = new Set(["--game", "--policy", "--pairs", "--max-plies", "--nodes", "--seconds", "--output"]);
  const options = new Map<string, string>();
  for (let i = 0; i < args.length; i += 2) {
    if (!known.has(args[i]) || !args[i + 1] || args[i + 1].startsWith("--") || options.has(args[i])) throw Error("Unknown, duplicate or incomplete option.");
    options.set(args[i], args[i + 1]);
  }
  const game = options.get("--game") ?? "tictactoe";
  if (!Object.hasOwn(RULES, game)) throw Error("Choose a built-in game; a custom policy may be supplied without --game.");
  const policyPath = options.get("--policy");
  const policy = policyPath ? await parsePolicy(JSON.parse(await readFile(resolve(policyPath), "utf8"))) : await baselinePolicy(RULES[game]);
  if (policyPath && options.has("--game") && policy.rules.kind !== game) throw Error("Policy/game mismatch.");
  const pairs = Number(options.get("--pairs") ?? 16);
  if (!Number.isInteger(pairs) || pairs < 1 || pairs > 64) throw Error("Pairs must be 1..64.");
  const maxPlies = Number(options.get("--max-plies") ?? 100);
  if (!Number.isInteger(maxPlies) || maxPlies < 1 || maxPlies > 398) throw Error("Ply cap must be 1..398 (two-ply lookahead).");
  const nodes = Number(options.get("--nodes") ?? 500000), seconds = Number(options.get("--seconds") ?? 120);
  // WorkBudget validates finite integer nodes and milliseconds, including hard maxima.
  const budget = new WorkBudget(nodes, seconds * 1000);
  const output = resolve(options.get("--output") ?? "output/self-improvement", `strength-${Date.now()}-${randomUUID()}`);
  await mkdir(output, { recursive: true });
  const save = (file: string, data: unknown) => writeFile(resolve(output, file), JSON.stringify(data, null, 2) + "\n", { flag: "wx" });
  const source = {
    strength: await sha256(await readFile(new URL("../src/strength.ts", import.meta.url), "utf8")),
    policy: await sha256(await readFile(new URL("../src/self-improvement.ts", import.meta.url), "utf8")),
    outcome: await sha256(await readFile(new URL("../src/outcome.ts", import.meta.url), "utf8")),
    runner: await sha256(await readFile(new URL("./measure-strength.ts", import.meta.url), "utf8")),
  };
  const seeds = Array.from({ length: pairs }, (_, i) => 20260905 + i);
  await save("plan.json", { partition: "public-development-only", policy: policy.digest, seeds, maxPlies, budget: { nodes, seconds }, source });
  await save("policy.json", policy);
  try {
    const result = await strengthSuite(policy, seeds, maxPlies, budget);
    await save("report.json", result);
    return { output, digest: result.digest, groups: result.groups, nodes: budget.used, promotion: result.promotion };
  } catch (error) {
    await save("failure.json", { status: "failed", error: error instanceof Error ? error.message : "Unknown failure", nodes: budget.used, promotion: "not-authorized" });
    throw error;
  }
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  measureStrength(process.argv.slice(2)).then(result => console.log(JSON.stringify(result, null, 2))).catch(error => {
    console.error(error instanceof Error ? error.message : "Strength measurement failed."); process.exitCode = 1;
  });
}
