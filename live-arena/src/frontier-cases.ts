/** Referee-verified connect/checkers cases. Isolation concerns target-position groups. */
import { applyMove, createGame, replayStepper, legalMoves, sha256, type GameState, type Rules } from "./runtime";
import { policyMove, seeded, WorkBudget } from "./self-improvement";
import { tacticalChoices, gradeTactic } from "./strength";
import { exact, freeze, integer, isDigest, parseVersion, identityKey, rulesKey, type Version } from "./frontier-version";

export const CASE_SCHEMA = "builderwars.frontier-cases.v1";
export type PositionCase = { history: string[]; group: string; sourceMove: string; sourceError: boolean; kind: "win" | "defense"; digest: string };
export type CaseBundle = { schema: typeof CASE_SCHEMA; partition: "training" | "development" | "admission";
  sourceVersion: string; identity: string; rules: Rules; referee: string; cases: PositionCase[]; digest: string };
export function supportsCases(rules: Rules) { return rules.kind === "checkers" || (["tictactoe", "connect4", "custom"].includes(rules.kind) && rules.rows * rules.cols <= 42); }

export function caseState(rules: Rules, history: string[], budget?: WorkBudget) {
  if (!supportsCases(rules) || !Array.isArray(history) || history.length < 2 || history.length > (rules.kind === "checkers" ? 200 : 40)
    || !history.every(m => typeof m === "string" && m.length <= (rules.kind === "checkers" ? 100 : 2))) throw Error("Unsupported bounded case history.");
  const step = replayStepper(rules);
  let state = createGame(rules);
  for (const move of history) { budget?.tick(); state = step(move); }
  if (state.over) throw Error("A tactical case must be unfinished.");
  return state;
}

/** Ignore move order and draw clocks: conservative grouping of history-equivalent boards.
 * Gravity permits horizontal reflection only; square non-gravity boards use D4.
 */
export async function positionGroup(state: GameState): Promise<string> {
  if (!supportsCases(state.rules)) throw Error("Position grouping supports connect games and checkers only.");
  if (state.rules.kind === "checkers") {
    // Horizontal reflection changes dark-square parity and is NOT a symmetry.
    // A half-turn with colors/seat swapped preserves moves, promotion and kings.
    // Ignore quiet/repetition clocks conservatively: history variants stay grouped.
    const colors: Record<string, string> = { w: "b", b: "w", W: "B", B: "W", "": "" };
    const swapped = [...state.cells].reverse().map(p => colors[p]);
    if (swapped.some(p => p === undefined)) throw Error("Unknown checkers piece encoding.");
    const boards = [JSON.stringify([state.turn, state.cells]), JSON.stringify([1 - state.turn, swapped])].sort();
    return sha256(JSON.stringify([rulesKey(state.rules), boards[0]]));
  }
  const { rows, cols, gravity } = state.rules;
  const transforms: ((r: number, c: number) => [number, number])[] = [
    (r, c) => [r, c], (r, c) => [r, cols - 1 - c],
  ];
  if (!gravity) {
    transforms.push((r, c) => [rows - 1 - r, c], (r, c) => [rows - 1 - r, cols - 1 - c]);
    if (rows === cols) transforms.push((r, c) => [c, r], (r, c) => [c, cols - 1 - r], (r, c) => [rows - 1 - c, r], (r, c) => [rows - 1 - c, cols - 1 - r]);
  }
  const boards = transforms.map(transform => {
    const cells = Array<string>(rows * cols).fill("");
    state.cells.forEach((piece, index) => { const [r, c] = transform(Math.floor(index / cols), index % cols); cells[r * cols + c] = piece; });
    return JSON.stringify(cells);
  }).sort();
  return sha256(JSON.stringify([rulesKey(state.rules), state.turn, boards[0]]));
}

export async function observeCase(version: Version, history: string[], budget: WorkBudget): Promise<PositionCase | null> {
  const c = version.config;
  if (c.harness.kind !== "linear-value" || !c.value) throw Error("Case sampler requires the bundled numeric harness.");
  const state = caseState(c.rules, history, budget), tactics = tacticalChoices(state, budget);
  const sourceMove = policyMove(state, { rules: c.rules, weights: c.value.weights }, seeded(((c.sampling.seed ?? 0) + history.length) >>> 0), budget);
  const grade = gradeTactic(tactics, sourceMove);
  if (!grade.assessed || (!grade.winOpportunity && !grade.defenseOpportunity)) return null;
  const body = { history: [...history], group: await positionGroup(state), sourceMove,
    sourceError: grade.missedWin || grade.avoidableLoss, kind: (grade.winOpportunity ? "win" : "defense") as PositionCase["kind"] };
  return freeze({ ...body, digest: await sha256(JSON.stringify(body)) });
}
export async function createBundle(partition: CaseBundle["partition"], version: Version, cases: PositionCase[], budget: WorkBudget): Promise<CaseBundle> {
  const source = await parseVersion(version);
  if (!["training", "development", "admission"].includes(partition) || !Array.isArray(cases)) throw Error("Invalid partition.");
  integer(cases.length, 1, 256, "case count");
  const validated: PositionCase[] = [], groups = new Set<string>();
  for (const row of cases) {
    exact(row, ["history", "group", "sourceMove", "sourceError", "kind", "digest"], "case");
    const check = await observeCase(source, row.history, budget);
    if (!check || JSON.stringify(check) !== JSON.stringify(row) || groups.has(check.group)) throw Error("Case label, digest or group custody mismatch.");
    groups.add(check.group); validated.push(check);
  }
  const body = { schema: CASE_SCHEMA as typeof CASE_SCHEMA, partition, sourceVersion: source.digest, identity: await identityKey(source.config.runtime),
    rules: source.config.rules, referee: source.config.referee, cases: validated };
  return freeze({ ...body, digest: await sha256(JSON.stringify(body)) });
}
export async function parseBundle(raw: unknown, source: Version, budget: WorkBudget): Promise<CaseBundle> {
  exact(raw, ["schema", "partition", "sourceVersion", "identity", "rules", "referee", "cases", "digest"], "case bundle");
  if (JSON.stringify(raw).length > 512000 || raw.schema !== CASE_SCHEMA || !isDigest(raw.digest)) throw Error("Invalid case bundle.");
  const result = await createBundle(raw.partition, source, raw.cases, budget);
  if (JSON.stringify(result) !== JSON.stringify(raw)) throw Error("Case bundle custody mismatch.");
  return result;
}

/** Includes public prefixes and the recorded source move, not just target boards. */
export async function exposedGroups(bundle: CaseBundle, budget: WorkBudget): Promise<Set<string>> {
  const groups = new Set<string>();
  for (const row of bundle.cases) {
    const step = replayStepper(bundle.rules); let state = createGame(bundle.rules);
    groups.add(await positionGroup(state));
    for (const move of [...row.history, row.sourceMove]) { budget.tick(); state = step(move); groups.add(await positionGroup(state)); }
  }
  return groups;
}
export async function validateIsolation(training: CaseBundle, development: CaseBundle, finalSuites: CaseBundle[], budget: WorkBudget) {
  if (training.partition !== "training" || development.partition !== "development" || !finalSuites.length || finalSuites.some(b => b.partition !== "admission")) throw Error("Wrong partition custody.");
  for (const bundle of [development, ...finalSuites]) if (bundle.sourceVersion !== training.sourceVersion || bundle.identity !== training.identity
    || bundle.referee !== training.referee || rulesKey(bundle.rules) !== rulesKey(training.rules)) throw Error("Partition source mismatch.");
  const blocked = await exposedGroups(training, budget);
  if (development.cases.some(c => blocked.has(c.group))) throw Error("Development target leaked through training or its symmetry/history equivalent.");
  for (const key of await exposedGroups(development, budget)) blocked.add(key);
  for (const suite of finalSuites) {
    if (suite.cases.some(c => blocked.has(c.group))) throw Error("Admission target leaked or reused across final suites.");
    for (const row of suite.cases) blocked.add(row.group);
  }
}

export async function samplePartitions(rawVersion: Version, seed: number, counts: { training: number; development: number; admission: number; attempts: number }, budget: WorkBudget,
  prior: { public: Set<string>; reserved: Set<string> } = { public: new Set(), reserved: new Set() }) {
  const source = await parseVersion(rawVersion), rules = source.config.rules;
  if (!supportsCases(rules)) throw Error("Tactical practice supports bounded connect games and checkers.");
  integer(seed, 0, 0xffffffff, "sampler seed");
  for (const n of [counts.training, counts.development, counts.admission]) integer(n, 4, 128, "partition case count");
  integer(counts.attempts, 1, 4, "attempt count");
  const random = seeded(seed), blocked = new Set<string>(prior.reserved), bundles: CaseBundle[] = [];
  const partitions: [CaseBundle["partition"], number][] = [["training", counts.training], ["development", counts.development],
    ...Array.from({ length: counts.attempts }, () => ["admission", counts.admission] as [CaseBundle["partition"], number])];
  for (const [partition, count] of partitions) {
    const rows: PositionCase[] = [], selected = new Set<string>();
    for (let attempt = 0; rows.length < count && attempt < 20000; attempt++) {
      budget.tick();
      let state = createGame(rules);
      const length = 2 + Math.floor(random() * (rules.kind === "checkers" ? 159 : Math.min(26, rules.rows * rules.cols - 3)));
      for (let ply = 0; ply < length && !state.over; ply++) {
        budget.tick(); const legal = legalMoves(state); state = applyMove(state, legal[Math.floor(random() * legal.length)]);
      }
      if (state.over) continue;
      const group = await positionGroup(state);
      if (blocked.has(group) || selected.has(group)) continue;
      const row = await observeCase(source, state.moves, budget);
      if (!row) continue;
      if (partition !== "admission" && prior.reserved.size) {
        const step = replayStepper(rules); let prefix = createGame(rules), leaked = false;
        for (const move of [...row.history, row.sourceMove]) {
          budget.tick(); prefix = step(move);
          if (prior.reserved.has(await positionGroup(prefix))) { leaked = true; break; }
        }
        if (leaked) continue;
      }
      rows.push(row); selected.add(group);
    }
    if (rows.length !== count) throw Error("Insufficient isolated cases within the bounded sampler; no campaign created.");
    const bundle = await createBundle(partition, source, rows, budget);
    bundles.push(bundle);
    if (partition !== "admission") for (const key of await exposedGroups(bundle, budget)) blocked.add(key);
    else for (const row of rows) blocked.add(row.group);
    if (partition === "development") for (const key of prior.public) blocked.add(key);
  }
  const [training, development, ...admission] = bundles;
  await validateIsolation(training, development, admission, budget);
  return { training, development, admission };
}
