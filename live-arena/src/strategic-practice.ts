/** Bounded search-preference distillation into numeric coefficients, not provider weights. */
import { applyMove, createGame, legalMoves, replayStepper, sha256, type Rules } from "./runtime";
import { seeded, WorkBudget } from "./self-improvement";
import { caseState, positionGroup } from "./frontier-cases";
import { createVersion, parseVersion, numericVersionMove, identityKey, freeze, exact, integer, rulesKey, type Version } from "./frontier-version";
import { validatePracticeOptions, type PracticeOptions } from "./frontier-practice";
import { gradeTactic, tacticalChoices } from "./strength";
import { STRATEGIC_TEACHER, teacherScores, teacherWeights, twoPlyChoices, worstLeaf, leafGradient, type SearchChoice } from "./strategic-value";

export type StrategicCase = { history: string[]; group: string; sourceMove: string; sourceError: boolean;
  scores: { move: string; value: number }[]; digest: string };
export type StrategicBundle = { schema: "builderwars.search-practice-cases.v1"; partition: "training" | "development";
  sourceVersion: string; identity: string; rules: Rules; referee: string;
  teacher: { id: typeof STRATEGIC_TEACHER; depth: 3; source: string; weights: number[] };
  cases: StrategicCase[]; digest: string };
const bestMoves = (row: StrategicCase) => { const best = Math.max(...row.scores.map(s => s.value)); return row.scores.filter(s => best - s.value <= 1e-9).map(s => s.move); };

async function observe(source: Version, history: string[], budget: WorkBudget): Promise<StrategicCase> {
  const state = caseState(source.config.rules, history, budget), scores = teacherScores(state, budget);
  const sourceMove = numericVersionMove(source, state, budget), best = Math.max(...scores.map(s => s.value));
  const body = { history: [...history], group: await positionGroup(state), sourceMove,
    sourceError: best - scores.find(s => s.move === sourceMove)!.value > 1e-9, scores };
  return freeze({ ...body, digest: await sha256(JSON.stringify(body)) });
}
export async function makeStrategicBundle(partition: StrategicBundle["partition"], rawSource: Version, cases: StrategicCase[], budget: WorkBudget): Promise<StrategicBundle> {
  const source = await parseVersion(rawSource);
  if (source.config.harness.kind !== "strategic-value" || !["training", "development"].includes(partition)) throw Error("Strategic case source/partition mismatch.");
  integer(cases.length, 4, 128, "strategic case count"); const groups = new Set<string>();
  for (const row of cases) {
    exact(row, ["history", "group", "sourceMove", "sourceError", "scores", "digest"], "strategic case");
    const check = await observe(source, row.history, budget);
    if (JSON.stringify(check) !== JSON.stringify(row) || groups.has(row.group)) throw Error("Strategic case label/group custody mismatch.");
    groups.add(row.group);
  }
  const body = { schema: "builderwars.search-practice-cases.v1" as const, partition, sourceVersion: source.digest,
    identity: await identityKey(source.config.runtime), rules: source.config.rules, referee: source.config.referee,
    teacher: { id: STRATEGIC_TEACHER as typeof STRATEGIC_TEACHER, depth: 3 as const, source: source.config.harness.source, weights: teacherWeights(createGame(source.config.rules)) }, cases: [...cases] };
  return freeze({ ...body, digest: await sha256(JSON.stringify(body)) });
}
export async function parseStrategicBundle(raw: unknown, source: Version, budget: WorkBudget) {
  exact(raw, ["schema", "partition", "sourceVersion", "identity", "rules", "referee", "teacher", "cases", "digest"], "strategic bundle");
  if (JSON.stringify(raw).length > 512000 || !Array.isArray(raw.cases)) throw Error("Strategic bundle size/type mismatch.");
  const checked = await makeStrategicBundle(raw.partition, source, raw.cases, budget);
  if (JSON.stringify(checked) !== JSON.stringify(raw)) throw Error("Strategic bundle digest/source mismatch.");
  return checked;
}
export async function sampleStrategicCases(rawSource: Version, seed: number, count: number, partition: StrategicBundle["partition"], budget: WorkBudget,
  excludedTargets: ReadonlySet<string> = new Set(), protectedTargets: ReadonlySet<string> = new Set()) {
  const source = await parseVersion(rawSource);
  if (source.config.harness.kind !== "strategic-value") throw Error("Strategic sampler needs the declared two-ply harness.");
  integer(seed, 0, 0xffffffff, "strategic data seed"); integer(count, 4, 128, "strategic case count");
  const rng = seeded(seed), rules = source.config.rules, selected = new Set<string>(), cases: StrategicCase[] = [];
  for (let attempt = 0; cases.length < count && attempt < 5000; attempt++) {
    budget.tick(); let state = createGame(rules);
    const length = 2 + Math.floor(rng() * (rules.kind === "checkers" ? 119 : Math.min(26, rules.rows * rules.cols - 3)));
    for (let ply = 0; ply < length && !state.over; ply++) {
      budget.tick(); const legal = legalMoves(state); state = applyMove(state, legal[Math.floor(rng() * legal.length)]);
    }
    if (state.over || legalMoves(state).length < 2) continue;
    const group = await positionGroup(state);
    if (selected.has(group) || excludedTargets.has(group)) continue;
    const row = await observe(source, state.moves, budget);
    if (bestMoves(row).length === row.scores.length) continue; // No heuristic preference to teach.
    if (protectedTargets.size && [...await historyGroups(rules, [...row.history, row.sourceMove], budget)].some(g => protectedTargets.has(g))) continue;
    cases.push(row); selected.add(group);
  }
  if (cases.length !== count) throw Error("Insufficient strategic cases inside the sampler budget.");
  return makeStrategicBundle(partition, source, cases, budget);
}
async function historyGroups(rules: Rules, history: string[], budget: WorkBudget) {
  const groups = new Set<string>(), step = replayStepper(rules); let state = createGame(rules);
  groups.add(await positionGroup(state));
  for (const move of history) { budget.tick(); state = step(move); groups.add(await positionGroup(state)); }
  return groups;
}
export async function strategicExposedGroups(bundle: StrategicBundle, budget: WorkBudget) {
  const groups = new Set<string>();
  for (const row of bundle.cases) for (const group of await historyGroups(bundle.rules, [...row.history, row.sourceMove], budget)) groups.add(group);
  return groups;
}
export async function scoreStrategicCases(rawVersion: Version, bundle: StrategicBundle, budget: WorkBudget) {
  const version = await parseVersion(rawVersion), c = version.config;
  if (c.harness.kind !== "strategic-value" || c.harness.source !== bundle.teacher.source || c.referee !== bundle.referee
    || rulesKey(c.rules) !== rulesKey(bundle.rules) || await identityKey(c.runtime) !== bundle.identity) throw Error("Strategic score custody mismatch.");
  const rows = bundle.cases.map(row => {
    const state = caseState(c.rules, row.history, budget), move = numericVersionMove(version, state, budget);
    const regret = Math.max(...row.scores.map(s => s.value)) - row.scores.find(s => s.move === move)!.value;
    return { case: row.digest, seat: state.turn, move, teacherPreferenceError: regret > 1e-9, heuristicRegret: regret,
      ...gradeTactic(tacticalChoices(state, budget), move) };
  });
  return freeze({ version: version.digest, bundle: bundle.digest, partition: bundle.partition,
    seats: [0, 1].map(seat => { const subset = rows.filter(r => r.seat === seat); return { seat, cases: subset.length,
      preferenceErrors: subset.filter(r => r.teacherPreferenceError).length, meanHeuristicRegret: subset.length ? subset.reduce((n, r) => n + r.heuristicRegret, 0) / subset.length : null,
      illegal: subset.filter(r => !r.legal).length, missedWins: subset.filter(r => r.missedWin).length, avoidableLosses: subset.filter(r => r.avoidableLoss).length }; }), rows });
}

export async function practiceStrategic(rawParent: Version, rawTraining: StrategicBundle, expectedDigest: string, options: PracticeOptions, budget: WorkBudget) {
  const parent = await parseVersion(rawParent), training = await parseStrategicBundle(rawTraining, parent, budget);
  if (training.partition !== "training" || training.digest !== expectedDigest) throw Error("Strategic learner accepts only committed training data.");
  validatePracticeOptions(options);
  const before = await scoreStrategicCases(parent, training, budget), weights = [...parent.config.value!.weights];
  const errors = training.cases.filter(r => r.sourceError).map(r => ({ case: r.digest, move: r.sourceMove, label: "bounded-teacher-preference-not-game-oracle" }));
  if (!errors.length) throw Error("No recorded teacher-preference errors; no fabricated strategic practice.");
  const choices = new Map<string, SearchChoice[]>();
  for (const row of training.cases) choices.set(row.digest, twoPlyChoices(caseState(parent.config.rules, row.history, budget), budget));
  const updates: { pass: number; case: string; preferred: string; rejected: string; changed: number }[] = [];
  for (let pass = 0; pass < options.passes; pass++) for (const row of training.cases) {
    const set = choices.get(row.digest)!, preferred = bestMoves(row);
    for (const good of set.filter(c => preferred.includes(c.move))) for (const bad of set.filter(c => !preferred.includes(c.move))) {
      budget.tick(); const a = worstLeaf(good, weights, budget), b = worstLeaf(bad, weights, budget);
      if (a.value - b.value >= options.margin) continue;
      const da = leafGradient(a.leaf, weights), db = leafGradient(b.leaf, weights); let changed = 0;
      for (let i = 0; i < weights.length; i++) {
        const next = Math.max(-8, Math.min(8, weights[i] + options.rate * (da[i] - db[i])));
        if (next !== weights[i]) changed++; weights[i] = next;
      }
      if (changed) { if (updates.length >= 8000) throw Error("Strategic update-record budget exhausted."); updates.push({ pass, case: row.digest, preferred: good.move, rejected: bad.move, changed }); }
    }
  }
  if (!updates.length) throw Error("Strategic practice made no numeric update.");
  const config = structuredClone(parent.config); config.value!.weights = weights;
  const candidate = await createVersion(config, parent, { method: "search-pairwise-v1", source: training.digest, identities: [training.identity] });
  const after = await scoreStrategicCases(candidate, training, budget);
  const body = { schema: "builderwars.search-preference-practice.v1", parent: parent.digest, candidate: candidate.digest, training: training.digest,
    identity: training.identity, teacher: training.teacher, options: { ...options }, errors, updates, before, after, providerCalls: 0, promotion: "not-authorized",
    limitation: "Numeric minimax preference fitting to a bounded heuristic teacher; neither provider weight training nor proof of stronger play." };
  return { candidate, receipt: freeze({ ...body, digest: await sha256(JSON.stringify(body)) }) };
}
