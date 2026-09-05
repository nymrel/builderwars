/** Node-only trusted-runner custody. Create-only files are not a hostile-user sandbox. */
import { mkdir, open, readFile, lstat, readdir } from "node:fs/promises";
import { resolve, parse } from "node:path";
import { randomBytes, randomUUID, createHash } from "node:crypto";
import { sha256, refereeManifest, type Rules } from "../src/runtime";
import { FEATURE_COUNT, FEATURE_VERSION, WorkBudget } from "../src/self-improvement";
import { createVersion, parseVersion, exact, freeze, integer, isDigest, identityKey, type Version } from "../src/frontier-version";
import { samplePartitions, exposedGroups, parseBundle, type CaseBundle } from "../src/frontier-cases";
import { practice, scoreCases, validatePracticeOptions, assertPracticeCandidate, type PracticeOptions } from "../src/frontier-practice";

type Counts = { training: number; development: number; admission: number; attempts: number };
type Manifest = { schema: "builderwars.frontier-campaign.v1"; id: string; source: string; incumbent: string; identity: string;
  training: string; development: string; suites: string[]; attempts: number; alphaTotal: number; alphaPerAttempt: number; minimumGain: number; digest: string };
type Plan = { schema: "builderwars.frontier-attempt.v1"; campaign: string; manifest: string; slot: number; suite: string;
  source: string; incumbent: string; identity: string; training: string; development: string; options: PracticeOptions; alpha: number; minimumGain: number; digest: string };
const slug = (id: string) => { if (!/^[a-z][a-z0-9-]{0,63}$/.test(id)) throw Error("Use a short campaign slug."); return id; };
const canonical = (value: unknown) => JSON.stringify(value, null, 2) + "\n";

async function directory(path: string) {
  await mkdir(path, { recursive: true });
  await inspectDirectory(path);
}
async function inspectDirectory(path: string) {
  const stat = await lstat(path);
  if (!stat.isDirectory() || stat.isSymbolicLink()) throw Error("Store directories cannot be links.");
}
async function save(path: string, data: unknown) {
  const encoded = canonical(data);
  if (Buffer.byteLength(encoded, "utf8") > 2000000) throw Error("Store artifact exceeds the two-megabyte limit.");
  const handle = await open(path, "wx");
  try { await handle.writeFile(encoded, "utf8"); await handle.sync(); }
  finally { await handle.close(); }
}
async function load(path: string, maxBytes = 2000000): Promise<any> {
  const stat = await lstat(path);
  if (!stat.isFile() || stat.isSymbolicLink() || stat.size > maxBytes) throw Error("Invalid bounded store artifact.");
  return JSON.parse(await readFile(path, "utf8"));
}
async function exists(path: string) {
  try { await lstat(path); return true; } catch (e) { if ((e as NodeJS.ErrnoException).code === "ENOENT") return false; throw e; }
}
function slotName(slot: number) { integer(slot, 1, 4, "attempt slot"); return String(slot).padStart(2, "0"); }
async function seal<T extends object>(body: T) { return freeze({ ...body, digest: await sha256(JSON.stringify(body)) }); }
async function verifyDigest(raw: any) {
  if (!raw || !isDigest(raw.digest)) throw Error("Missing artifact digest.");
  const { digest, ...body } = raw;
  if (await sha256(JSON.stringify(body)) !== digest) throw Error("Artifact digest mismatch.");
}

/** Full local execution/learning source binding. A source change requires a new campaign. */
export async function frontierSource() {
  const paths = ["../src/frontier-version.ts", "../src/frontier-cases.ts", "../src/frontier-practice.ts", "../src/strength.ts",
    "../src/self-improvement.ts", "../src/outcome.ts", "../src/runtime.ts", "./self-improve.ts", "./frontier-store.ts", "./frontier.ts", "../package-lock.json"];
  const sources: Record<string, string> = {};
  for (const path of paths) sources[path] = createHash("sha256").update(await readFile(new URL(path, import.meta.url))).digest("hex");
  const refereeBytes = await readFile(new URL(`../public/${refereeManifest.file}`, import.meta.url));
  if (createHash("sha256").update(refereeBytes).digest("hex") !== refereeManifest.digest) throw Error("Referee artifact does not match its digest.");
  return sha256(JSON.stringify({ referee: refereeManifest.digest, sources, node: process.version }));
}
export async function localBaseline(rules: Rules) {
  const source = await frontierSource();
  return createVersion({ rules, referee: refereeManifest.digest,
    runtime: { provider: "local", requestedModel: "builderwars/linear-value-v1", resolvedModel: "builderwars/linear-value-v1", evidence: "bundled-code", reasoning: "none" },
    harness: { kind: "linear-value", source, protocol: "builderwars.linear-value.v1" }, prompt: "", memory: { mode: "none", content: "" },
    tools: [{ id: "one-ply-value", source, parameters: await sha256(JSON.stringify({ depth: 1 })) }],
    sampling: { temperature: null, seed: 0 }, value: { features: FEATURE_VERSION, weights: Array(FEATURE_COUNT).fill(0) },
    limits: { nodes: 2000000, milliseconds: 300000, maxTokens: 512, maxCalls: 400 } });
}

export class FrontierStore {
  readonly root: string;
  constructor(root = "output/frontier", private readonly samplerSeed = () => randomBytes(4).readUInt32LE()) {
    this.root = resolve(root);
    if (this.root === parse(this.root).root) throw Error("Choose a dedicated frontier store directory.");
  }
  private path(...segments: string[]) { return resolve(this.root, ...segments); }
  private campaign(id: string) { return this.path("campaigns", slug(id)); }
  private async prepare() {
    await directory(this.root);
    const marker = this.path("store.json");
    if (!await exists(marker)) {
      // Refuse to turn an unrelated nonempty directory into a store.
      if ((await readdir(this.root)).length) throw Error("Directory is not an initialized frontier store.");
      await save(marker, { schema: "builderwars.frontier-store.v1", id: randomUUID(), trust: "local-trusted-runner" });
    }
    const meta = await load(marker, 1000);
    if (meta.schema !== "builderwars.frontier-store.v1" || meta.trust !== "local-trusted-runner") throw Error("Unsupported store marker.");
    for (const name of ["campaigns", "versions", "groups", "vault", "spent"]) await directory(this.path(name));
  }
  private async version(digest: string) {
    if (!isDigest(digest)) throw Error("Invalid version reference.");
    return parseVersion(await load(this.path("versions", `${digest}.json`), 32000));
  }
  private async putVersion(raw: Version) {
    const version = await parseVersion(raw), file = this.path("versions", `${version.digest}.json`);
    try { await save(file, version); }
    catch (e) { if ((e as NodeJS.ErrnoException).code !== "EEXIST" || canonical(await load(file)) !== canonical(version)) throw e; }
  }
  private async register(group: string, kind: "public" | "admission", owner: string) {
    if (!isDigest(group)) throw Error("Invalid position group.");
    const file = this.path("groups", `${group}.json`), record = { group, kind, owner };
    try { await save(file, record); }
    catch (e) {
      if ((e as NodeJS.ErrnoException).code !== "EEXIST") throw e;
      const previous = await load(file, 1000);
      if (previous.group !== group || previous.kind !== "public" || kind !== "public") throw Error("Position group already reserved or exposed in this store.");
    }
  }
  private async exposure() {
    const result = { public: new Set<string>(), reserved: new Set<string>() };
    const names = await readdir(this.path("groups"));
    if (names.length > 20000) throw Error("Store group inventory exceeds this runner's bound.");
    for (const name of names) {
      if (!/^[a-f0-9]{64}\.json$/.test(name)) throw Error("Invalid group inventory.");
      const entry = await load(this.path("groups", name), 1000);
      if (`${entry.group}.json` !== name || !["public", "admission"].includes(entry.kind)) throw Error("Invalid group marker.");
      result[entry.kind === "public" ? "public" : "reserved"].add(entry.group);
    }
    return result;
  }
  async initialize(id: string, rules: Rules, counts: Counts = { training: 32, development: 16, admission: 16, attempts: 2 }) {
    await this.prepare();
    const root = this.campaign(id); await mkdir(root); // An interrupted initialization is never overwritten.
    try {
      const source = await localBaseline(rules), budget = new WorkBudget(2000000, 300000), seed = this.samplerSeed();
      const partitions = await samplePartitions(source, seed, counts, budget, await this.exposure());
      for (const part of [partitions.training, partitions.development]) for (const group of await exposedGroups(part, budget)) await this.register(group, "public", id);
      for (const suite of partitions.admission) for (const row of suite.cases) await this.register(row.group, "admission", suite.digest);
      await this.putVersion(source);
      await save(resolve(root, "training.json"), partitions.training); await save(resolve(root, "development.json"), partitions.development);
      for (const suite of partitions.admission) await save(this.path("vault", `${suite.digest}.json`), suite);
      await save(this.path("vault", `${id}-sampler.json`), { seed, counts, source: source.digest, sourceHash: source.config.harness.source });
      await directory(resolve(root, "attempts"));
      const body = { schema: "builderwars.frontier-campaign.v1" as const, id, source: source.config.harness.source, incumbent: source.digest,
        identity: await identityKey(source.config.runtime), training: partitions.training.digest, development: partitions.development.digest,
        suites: partitions.admission.map(s => s.digest), attempts: counts.attempts, alphaTotal: 0.05, alphaPerAttempt: 0.05 / counts.attempts, minimumGain: 0.05 };
      const manifest = await seal(body); await save(resolve(root, "manifest.json"), manifest);
      return { manifest, samplerNodes: budget.used, finalPayloads: "withheld in local evaluator vault; not sandboxed from the machine owner" };
    } catch (error) {
      await save(resolve(root, "initialization-failed.json"), { status: "failed", error: error instanceof Error ? error.message : "Initialization failed", reservedGroups: "Any partial reservations remain burned; never silently reused." });
      throw error;
    }
  }
  private async manifest(id: string, requireExecutor = true): Promise<Manifest> {
    await this.prepare();
    await inspectDirectory(this.campaign(id));
    const value = await load(resolve(this.campaign(id), "manifest.json"), 16000);
    exact(value, ["schema", "id", "source", "incumbent", "identity", "training", "development", "suites", "attempts", "alphaTotal", "alphaPerAttempt", "minimumGain", "digest"], "campaign manifest");
    await verifyDigest(value); integer(value.attempts, 1, 4, "campaign attempts");
    if (value.schema !== "builderwars.frontier-campaign.v1" || value.id !== id || ![value.source, value.incumbent, value.identity, value.training, value.development].every(isDigest)
      || !Array.isArray(value.suites) || value.suites.length !== value.attempts || !value.suites.every(isDigest) || new Set(value.suites).size !== value.suites.length
      || value.alphaTotal !== 0.05 || value.alphaPerAttempt !== 0.05 / value.attempts || value.minimumGain !== 0.05) throw Error("Invalid campaign contract.");
    if (requireExecutor && value.source !== await frontierSource()) throw Error("Execution source changed; this campaign cannot run under a different harness.");
    return freeze(value) as Manifest; // Exact fields, digest and every contract value validated above.
  }
  private async plan(id: string, slot: number, requireExecutor = true) {
    const manifest = await this.manifest(id, requireExecutor), root = resolve(this.campaign(id), "attempts", slotName(slot));
    await inspectDirectory(root);
    const plan = await load(resolve(root, "plan.json"), 16000) as Plan;
    exact(plan, ["schema", "campaign", "manifest", "slot", "suite", "source", "incumbent", "identity", "training", "development", "options", "alpha", "minimumGain", "digest"], "attempt plan");
    await verifyDigest(plan);
    if (plan.schema !== "builderwars.frontier-attempt.v1" || plan.campaign !== id || plan.manifest !== manifest.digest || plan.slot !== slot
      || plan.suite !== manifest.suites[slot - 1] || plan.source !== manifest.source || plan.incumbent !== manifest.incumbent || plan.identity !== manifest.identity
      || plan.training !== manifest.training || plan.development !== manifest.development || plan.alpha !== manifest.alphaPerAttempt || plan.minimumGain !== manifest.minimumGain) throw Error("Attempt plan custody mismatch.");
    const spent = await load(this.path("spent", `${plan.suite}.json`), 1000);
    if (spent.campaign !== id || spent.slot !== slot || spent.suite !== plan.suite) throw Error("Final-suite consumption custody mismatch.");
    return { manifest, root, plan };
  }
  async run(id: string, options: PracticeOptions = { passes: 8, rate: 0.2, margin: 0.1 }) {
    validatePracticeOptions(options);
    const selectedOptions = freeze({ ...options });
    const manifest = await this.manifest(id);
    if (await exists(resolve(this.campaign(id), "closed.json"))) throw Error("Campaign is closed.");
    let slot = 0, root = "";
    for (let n = 1; n <= manifest.attempts; n++) {
      const candidate = resolve(this.campaign(id), "attempts", slotName(n));
      try { await mkdir(candidate); slot = n; root = candidate; break; }
      catch (e) { if ((e as NodeJS.ErrnoException).code !== "EEXIST") throw e; }
    }
    if (!slot) throw Error("Campaign attempt budget exhausted, including interrupted reservations.");
    const budget = new WorkBudget(2000000, 300000);
    try {
      await save(this.path("spent", `${manifest.suites[slot - 1]}.json`), { campaign: id, slot, suite: manifest.suites[slot - 1] });
      const plan = await seal({ schema: "builderwars.frontier-attempt.v1" as const, campaign: id, manifest: manifest.digest, slot, suite: manifest.suites[slot - 1],
        source: manifest.source, incumbent: manifest.incumbent, identity: manifest.identity, training: manifest.training, development: manifest.development,
        options: selectedOptions, alpha: manifest.alphaPerAttempt, minimumGain: manifest.minimumGain });
      await save(resolve(root, "plan.json"), plan); // Always before optimizer execution.
      const parent = await this.version(manifest.incumbent);
      const training = await parseBundle(await load(resolve(this.campaign(id), "training.json")), parent, budget);
      if (training.digest !== manifest.training) throw Error("Training commitment mismatch.");
      const learned = await practice(parent, training, manifest.training, plan.options, budget);
      await save(resolve(root, "practice.json"), learned.receipt); await this.putVersion(learned.candidate);
      await save(resolve(root, "candidate.json"), { version: learned.candidate.digest, parent: parent.digest, practice: learned.receipt.digest });
      await save(resolve(root, "rollback.json"), { incumbent: parent.digest, candidate: learned.candidate.digest, selected: parent.digest, reason: "No whole-game admission; incumbent retained." });
      const development = await parseBundle(await load(resolve(this.campaign(id), "development.json")), parent, budget);
      if (development.digest !== manifest.development) throw Error("Development commitment mismatch.");
      const baseline = await scoreCases(parent, development, budget), candidate = await scoreCases(learned.candidate, development, budget);
      const receipt = await seal({ status: "ready-for-admission", campaign: id, slot, plan: plan.digest, candidate: learned.candidate.digest,
        baseline, development: candidate, nodes: budget.used, providerCalls: 0, promotion: "not-authorized" });
      await save(resolve(root, "development-result.json"), receipt);
      return receipt;
    } catch (error) {
      await save(resolve(root, "failure.json"), { status: "failed", slot, decision: "retain", error: error instanceof Error ? error.message : "Run failed", nodes: budget.used, attempt: "spent" });
      throw error;
    }
  }
  async admit(id: string, slot: number) {
    const { root, plan, manifest } = await this.plan(id, slot);
    if (await exists(resolve(this.campaign(id), "closed.json")) || await exists(resolve(root, "failure.json"))) throw Error("Campaign/attempt cannot enter admission.");
    const binding = await load(resolve(root, "candidate.json"), 1000), ready = await load(resolve(root, "development-result.json"));
    const practiceReceipt = await load(resolve(root, "practice.json")); await verifyDigest(practiceReceipt);
    const parent = await this.version(plan.incumbent), candidate = await this.version(binding.version);
    assertPracticeCandidate(parent, candidate, plan.training);
    if (candidate.parent !== parent.digest || candidate.provenance.source !== plan.training || candidate.provenance.identities[0] !== manifest.identity
      || candidate.config.harness.source !== plan.source || ready.candidate !== candidate.digest || ready.plan !== plan.digest || binding.parent !== parent.digest) throw Error("Frozen candidate custody mismatch.");
    if (practiceReceipt.digest !== binding.practice || practiceReceipt.candidate !== candidate.digest || practiceReceipt.parent !== parent.digest
      || practiceReceipt.training !== plan.training || practiceReceipt.identity !== manifest.identity || JSON.stringify(practiceReceipt.options) !== JSON.stringify(plan.options)
      || ready.status !== "ready-for-admission") throw Error("Candidate practice/plan provenance mismatch.");
    await verifyDigest(ready);
    // Atomic one-shot marker before reading even one final case. Crash means spent.
    await save(resolve(root, "evaluation-started.json"), { candidate: candidate.digest, suite: plan.suite, plan: plan.digest });
    const budget = new WorkBudget(2000000, 300000);
    try {
      const suite = await parseBundle(await load(this.path("vault", `${plan.suite}.json`)), parent, budget);
      if (suite.partition !== "admission" || suite.digest !== plan.suite) throw Error("Final-suite commitment mismatch.");
      const before = await scoreCases(parent, suite, budget), after = await scoreCases(candidate, suite, budget);
      const audit = await seal({ plan: plan.digest, suite: suite.digest, before, after });
      await save(this.path("vault", `${id}-${slotName(slot)}-evaluation.json`), audit);
      const pass = after.seats.every(s => s.cases >= 4 && s.assessed === s.cases && s.illegal === 0 && s.missedWins === 0 && s.avoidableLosses === 0);
      const result = await seal({ status: "completed", campaign: id, slot, candidate: candidate.digest, plan: plan.digest, suite: suite.digest,
        tacticalQualification: pass ? "pass" : "fail", before: before.seats, after: after.seats, audit: audit.digest, nodes: budget.used, providerCalls: 0,
        promotion: "not-authorized", reason: "Tactical qualification alone cannot promote; whole-game strength and uncertainty gates remain required.",
        identity: manifest.identity, alphaReserved: plan.alpha, uncertainty: "No population bound claimed from this finite tactical fixture suite." });
      await save(resolve(root, "admission-result.json"), result); return result;
    } catch (error) {
      await save(resolve(root, "admission-failed.json"), { status: "failed", decision: "retain", error: error instanceof Error ? error.message : "Admission failed", suite: plan.suite, consumed: true });
      throw error;
    }
  }
  async status(id: string) {
    const manifest = await this.manifest(id, false), rows = [];
    for (let slot = 1; slot <= manifest.attempts; slot++) {
      const root = resolve(this.campaign(id), "attempts", slotName(slot));
      let state = "unclaimed";
      if (await exists(root)) {
        await inspectDirectory(root);
        if (await exists(resolve(root, "admission-result.json"))) {
          state = "invalid-completion";
          try {
            const result = await load(resolve(root, "admission-result.json")), { plan } = await this.plan(id, slot, false);
            const binding = await load(resolve(root, "candidate.json")), started = await load(resolve(root, "evaluation-started.json"));
            await verifyDigest(result);
            if (result.status === "completed" && result.campaign === id && result.slot === slot && result.plan === plan.digest
              && result.suite === plan.suite && result.candidate === binding.version && started.candidate === binding.version
              && result.promotion === "not-authorized") state = "completed";
          } catch { /* A partial or corrupted result is never a completion receipt. */ }
        } else state = await exists(resolve(root, "evaluation-started.json")) ? "admission-spent-without-result"
          : await exists(resolve(root, "failure.json")) ? "failed-spent" : await exists(resolve(root, "development-result.json")) ? "ready-for-admission" : "reserved-or-interrupted";
      }
      rows.push({ slot, state });
    }
    return { manifest, attempts: rows, executionCompatible: manifest.source === await frontierSource(), closed: await exists(resolve(this.campaign(id), "closed.json")), scope: "Historical local-store receipts only; no global admission authority." };
  }
  async loadVersion(digest: string) {
    await this.prepare();
    const version = await this.version(digest);
    if (version.config.harness.source !== await frontierSource()) throw Error("Version belongs to another executor source.");
    return version;
  }
  async close(id: string) {
    const manifest = await this.manifest(id, false); // Retirement must remain possible after a source/runtime upgrade.
    await save(resolve(this.campaign(id), "closed.json"), { manifest: manifest.digest, reason: "Explicit retirement rejects new training/admission; in-flight operations retain their existing bounds.", at: new Date().toISOString() });
    return { id, retired: true, suites: "Remain reserved/burned; closing never makes final cases reusable." };
  }
}
