/** Cancellable, source-bound local work. Checkpoints must be saved before continuing. */
import { validateLabPlan, validateLabVersion, labSummary, type LabRun } from "./browser-lab-core";
import { samplePartitions } from "./frontier-cases";
import { practice, scoreCases } from "./frontier-practice";
import { fullgameBlock } from "./frontier-fullgame";
import { WorkBudget } from "./self-improvement";

const scope = self as unknown as { postMessage(data: unknown): void; onmessage: ((event: MessageEvent) => void) | null };
let acknowledge: (() => void) | null = null, active = false;
async function checkpoint(run: LabRun) {
  await new Promise<void>(resolve => { acknowledge = resolve; scope.postMessage({ type: "checkpoint", run }); });
}
scope.onmessage = event => {
  if (event.data?.type === "ack") { acknowledge?.(); acknowledge = null; return; }
  if (event.data?.type !== "start" || active) return;
  active = true;
  void execute(structuredClone(event.data.run)).catch(error => scope.postMessage({ type: "error", message: error instanceof Error ? error.message : "Local experiment failed." }));
};
// Top-level referee loading is asynchronous. Do not let early start messages be lost.
scope.postMessage({ type: "ready" });
async function execute(run: LabRun) {
  await validateLabPlan(run);
  if (run.status !== "prepared" || run.blocks.length || run.candidate) throw Error("A spent experiment cannot restart. Create a fresh plan.");
  run.status = "sampling"; await checkpoint(run);
  const budget = new WorkBudget(2000000, 60000);
  run.partitions = await samplePartitions(run.parent, run.plan.seed,
    { training: run.plan.caseCount, development: run.plan.caseCount, admission: 4, attempts: 1 }, budget);
  // All browser cases are inspectable development artifacts, including unused reserved bundles.
  run.status = "training"; await checkpoint(run);
  const trained = await practice(run.parent, run.partitions.training, run.partitions.training.digest,
    { passes: run.plan.passes, rate: 0.2, margin: 0.2 }, budget);
  run.candidate = await validateLabVersion(trained.candidate); run.practice = trained.receipt;
  run.development = { before: await scoreCases(run.parent, run.partitions.development, budget),
    after: await scoreCases(run.candidate, run.partitions.development, budget) };
  run.status = "evaluating"; await checkpoint(run);
  for (const seed of run.plan.seeds) {
    run.blocks.push(await fullgameBlock(run.parent, run.candidate, seed, run.plan.maxPlies, undefined, 10000));
    await checkpoint(run);
  }
  run.summary = labSummary(run); run.status = "completed"; await checkpoint(run);
  scope.postMessage({ type: "done" });
}
