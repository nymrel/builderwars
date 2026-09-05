/** Supervised tactical calibration. This is not outcome training or provider weight training. */
import { applyMove, sha256 } from "./runtime";
import { boardFeatures, policyMove, seeded, WorkBudget } from "./self-improvement";
import { tacticalChoices, gradeTactic } from "./strength";
import { createVersion, parseVersion, identityKey, integer, freeze, rulesKey, exact, type Version } from "./frontier-version";
import { parseBundle, caseState, type CaseBundle } from "./frontier-cases";

export type PracticeOptions = { passes: number; rate: number; margin: number };
export function validatePracticeOptions(options: PracticeOptions) {
  exact(options, ["passes", "rate", "margin"], "practice options");
  integer(options.passes, 1, 32, "practice passes");
  if (!Number.isFinite(options.rate) || options.rate <= 0 || options.rate > 1 || !Number.isFinite(options.margin) || options.margin <= 0 || options.margin > 1) throw Error("Invalid practice optimizer settings.");
}
export function assertPracticeCandidate(parent: Version, candidate: Version, training: string) {
  const comparison = structuredClone(candidate.config);
  comparison.value = parent.config.value;
  if (candidate.parent !== parent.digest || candidate.revision !== parent.revision + 1 || candidate.provenance.method !== "tactical-pairwise-v1"
    || candidate.provenance.source !== training || JSON.stringify(comparison) !== JSON.stringify(parent.config)) throw Error("Practice changed configuration outside numeric calibration.");
}
export async function scoreCases(version: Version, bundle: CaseBundle, budget: WorkBudget) {
  const candidate = await parseVersion(version), c = candidate.config;
  if (!c.value || c.harness.kind !== "linear-value" || rulesKey(c.rules) !== rulesKey(bundle.rules)
    || c.referee !== bundle.referee || await identityKey(c.runtime) !== bundle.identity) throw Error("Case evaluation identity/rules mismatch.");
  const rows = bundle.cases.map(row => {
    const state = caseState(c.rules, row.history, budget);
    const move = policyMove(state, { rules: c.rules, weights: c.value!.weights }, seeded(((c.sampling.seed ?? 0) + state.moves.length) >>> 0), budget);
    const grade = gradeTactic(tacticalChoices(state, budget), move);
    return { case: row.digest, group: row.group, seat: state.turn, move, ...grade };
  });
  const seats = [0, 1].map(seat => {
    const subset = rows.filter(row => row.seat === seat), count = (key: "winOpportunity" | "missedWin" | "defenseOpportunity" | "avoidableLoss") => subset.filter(r => r[key]).length;
    const wins = count("winOpportunity"), defense = count("defenseOpportunity");
    return { seat, cases: subset.length, assessed: subset.filter(r => r.assessed).length, illegal: subset.filter(r => !r.legal).length,
      winOpportunities: wins, missedWins: count("missedWin"), defenseOpportunities: defense, avoidableLosses: count("avoidableLoss"),
      missedWinRate: wins ? count("missedWin") / wins : null, avoidableLossRate: defense ? count("avoidableLoss") / defense : null };
  });
  return freeze({ version: candidate.digest, bundle: bundle.digest, partition: bundle.partition, identity: bundle.identity, referee: bundle.referee, seats, rows });
}

export async function practice(rawParent: Version, rawTraining: CaseBundle, expectedTrainingDigest: string, options: PracticeOptions, budget: WorkBudget) {
  const parent = await parseVersion(rawParent), training = await parseBundle(rawTraining, parent, budget);
  if (training.partition !== "training" || training.digest !== expectedTrainingDigest) throw Error("Optimizer may receive only the committed training partition.");
  if (!parent.config.value || parent.config.harness.kind !== "linear-value") throw Error("This learner calibrates only local numeric preferences.");
  validatePracticeOptions(options);
  const weights = [...parent.config.value.weights], updates: { pass: number; case: string; preferred: string; rejected: string; changed: number }[] = [];
  const errors = training.cases.filter(row => row.sourceError).map(row => ({ case: row.digest, sourceVersion: parent.digest, identity: training.identity, move: row.sourceMove, kind: row.kind }));
  if (!errors.length) throw Error("No recorded training errors; retain the incumbent without fabricating practice.");
  const before = await scoreCases(parent, training, budget);
  for (let pass = 0; pass < options.passes; pass++) for (const row of training.cases) {
    budget.tick();
    const state = caseState(parent.config.rules, row.history, budget), tactics = tacticalChoices(state, budget);
    const preferred = tactics.wins.length ? tactics.wins : tactics.safe;
    if (!tactics.assessed || !preferred.length) throw Error("Unresolved practice label.");
    const rejected = tactics.legal.filter(move => !preferred.includes(move));
    for (const good of preferred) for (const bad of rejected) {
      budget.tick();
      const a = boardFeatures(applyMove(state, good), state.turn), b = boardFeatures(applyMove(state, bad), state.turn);
      const difference = a.map((value, i) => value - b[i]);
      const prediction = weights.reduce((sum, w, i) => sum + w * difference[i], 0);
      if (prediction >= options.margin) continue;
      let changed = 0;
      for (let i = 0; i < weights.length; i++) {
        const next = Math.max(-8, Math.min(8, weights[i] + options.rate * difference[i]));
        if (next !== weights[i]) changed++;
        weights[i] = next;
      }
      if (changed) {
        if (updates.length >= 10000) throw Error("Practice update-record budget exhausted; no candidate.");
        updates.push({ pass, case: row.digest, preferred: good, rejected: bad, changed });
      }
    }
  }
  if (!updates.length) throw Error("Practice produced no numeric update; retain incumbent.");
  const configuration = structuredClone(parent.config); configuration.value!.weights = weights;
  const candidate = await createVersion(configuration, parent, { method: "tactical-pairwise-v1", source: training.digest, identities: [training.identity] });
  const after = await scoreCases(candidate, training, budget);
  const body = { schema: "builderwars.tactical-practice.v1", parent: parent.digest, candidate: candidate.digest, partition: "training",
    training: training.digest, identity: training.identity, referee: parent.config.referee, options: { ...options }, errors, updates, before, after,
    providerCalls: 0, promotion: "not-authorized", limitation: "Lower supervised training error is not proof of stronger play or hidden-case performance." };
  return { candidate, receipt: freeze({ ...body, digest: await sha256(JSON.stringify(body)) }) };
}
