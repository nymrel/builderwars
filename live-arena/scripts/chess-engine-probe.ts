/** Explicit offline engine conformance smoke; never calls a provider. */
import { mkdir } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { pathToFileURL } from "node:url";
import { analyzeChess, STOCKFISH_19, ENGINE_LIMITS } from "./chess-engine";
import { writeOnce } from "./frontier-compare";
export async function probeEngine(file: string, output: string) {
  const root = resolve(output); await mkdir(dirname(root), { recursive: true }); await mkdir(root);
  const pin = { file: resolve(file), sha256: STOCKFISH_19.windowsBinarySha256, name: STOCKFISH_19.name };
  await writeOnce(resolve(root, "plan.json"), { schema: "builderwars.stockfish-probe.v1", engine: STOCKFISH_19,
    limits: ENGINE_LIMITS, providerCalls: 0, purpose: "Local engine/referee conformance, not contender strength or model training" });
  try {
    const positions = [[], ["f2f3", "e7e5", "g2g4"],
      ["e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6", "b5a4", "g8f6", "e1g1", "f8e7", "f1e1", "b7b5", "a4b3", "d7d6"]];
    const receipts = [];
    for (const history of positions) receipts.push(await analyzeChess(pin, history));
    if (receipts[1].bestMove !== "d8h4") throw Error("Engine missed the referee-verified mate-in-one smoke fixture.");
    const result = { status: "passed", engine: STOCKFISH_19, receipts, providerCalls: 0, promotion: "not-authorized" };
    await writeOnce(resolve(root, "result.json"), result); return result;
  } catch (error) {
    await writeOnce(resolve(root, "failed.json"), { status: "failed", error: error instanceof Error ? error.message : "Engine probe failed", promotion: "not-authorized" }); throw error;
  }
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const [file, output, ...extra] = process.argv.slice(2);
  if (!file || !output || extra.length) { console.error("Use chess-engine-probe.ts ABSOLUTE_ENGINE_FILE NEW_OUTPUT_DIRECTORY"); process.exitCode = 1; }
  else probeEngine(file, output).then(result => console.log(JSON.stringify({ status: result.status, engine: result.engine.name,
    positions: result.receipts.length, moves: result.receipts.map(r => r.bestMove), providerCalls: 0 })))
    .catch(error => { console.error(error instanceof Error ? error.message : "Engine probe failed"); process.exitCode = 1; });
}
