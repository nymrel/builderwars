/** Explicit tab-local development, never admission or provider-weight training. */
import { applyMove, botMove, createGame, moveLabel, sha256, refereeManifest, type Rules, type RecordData } from './runtime';
import { decide, publicAgent, type Agent, type Model } from './models';
import { createVersion, parseVersion, openVersionSession, freeze, integer, type Version, type VersionConfig } from './frontier-version';
import { assertBrowserVersion, connectedVersionConfig, browserVersionTransport } from './model-version-transport';
import { PracticeMemory, supportsLearning } from './learning';
import { isRuleComplete } from './outcome';
import source from './model-version-manifest';

export const DEVELOPMENT_SCHEMA = 'builderwars.model-development.v1';
const MAX_VERSIONS = 24, MAX_ATTEMPTS = 12;
export const DEFAULT_VERSION_LIMITS = { nodes: 2000000, milliseconds: 300000, maxTokens: 1024, maxCalls: 24 } as const;
type Call = { version: string | null; game: number; ply: number; exit: 'pending' | 'accepted' | 'failed' | 'cancelled';
  model: string | null; tokens: number | null; outputTokens: number | null; cost: number | null };
export type DevelopmentGame = { version: string; seat: number; record: RecordData; exit: 'complete' | 'capped' | 'failed' | 'cancelled' };
export type DevelopmentAttempt = { schema: typeof DEVELOPMENT_SCHEMA; id: string; kind: 'probe' | 'practice' | 'compare';
  source: string; referee: string; startedAt: string; finishedAt: string; exit: 'complete' | 'failed' | 'cancelled';
  versions: Version[]; candidate: string | null; probe: ReturnType<typeof publicAgent> | null;
  limits: { games: number; maxPlies: number; maxCalls: number; milliseconds: number; maxTokens: number };
  calls: Call[]; games: DevelopmentGame[]; message: string; digest: string };
type AttemptDraft = Omit<DevelopmentAttempt, 'digest'>;
const opponent: Agent = { name: 'Frozen Tactician', kind: 'bot', model: 'tactician', effort: 'default', strategy: '', endpoint: '', key: '' };
const policyAgent = (a: Agent, v: Version): Agent => ({ ...a, strategy: v.config.prompt });
function safeFailure(aborted: boolean) {
  // Do not export arbitrary remote error text, endpoints, prompts or secrets.
  return aborted ? 'Cancelled or timed out. Submitted requests may still be billed; no retry.'
    : 'Connection, identity, move or resource validation failed. No retry; reported usage may be incomplete.';
}
export function developmentTotals(attempt: DevelopmentAttempt) {
  const sum = (key: 'cost' | 'tokens' | 'outputTokens') => !attempt.calls.length || attempt.calls.some(c => c[key] === null)
    ? null : attempt.calls.reduce((n, c) => n + c[key]!, 0);
  return { calls: attempt.calls.length, accepted: attempt.calls.filter(c => c.exit === 'accepted').length,
    complete: attempt.games.filter(g => g.exit === 'complete').length,
    capped: attempt.games.filter(g => g.exit === 'capped').length, cost: sum('cost'), tokens: sum('tokens'), outputTokens: sum('outputTokens') };
}

export class ModelDevelopment {
  private saved: Version[] = [];
  private results: DevelopmentAttempt[] = [];
  private selected: string | null = null;
  private history: string[] = [];
  private operation: AbortController | null = null;
  private status = 'No version yet. Connect a model, then explicitly probe and freeze it.';
  constructor(private changed: () => void = () => {}, private beforeStart: () => void = () => {}) {}
  get busy() { return this.operation !== null; }
  get message() { return this.status; }
  get versions(): readonly Version[] { return [...this.saved]; }
  get attempts(): readonly DevelopmentAttempt[] { return [...this.results]; }
  get active() { return this.saved.find(v => v.digest === this.selected) ?? null; }
  get canRollback() { return !this.busy && this.history.length > 0; }
  private tell(message: string) { this.status = message; this.changed(); }
  private idle() { if (this.busy) throw Error('Cancel or finish the active operation first.'); }
  private room() { if (this.saved.length >= MAX_VERSIONS) throw Error('This tab holds 24 versions. Download them before starting a new tab.'); }
  private add(version: Version) { if (!this.saved.some(v => v.digest === version.digest)) { this.room(); this.saved.push(version); } }
  async importVersion(raw: unknown) {
    this.idle(); const version = await parseVersion(raw); this.idle();
    this.add(version); this.tell('Version imported, disconnected and not selected. No inference started.'); return version;
  }
  select(digest: string) {
    this.idle(); const version = this.saved.find(v => v.digest === digest);
    if (!version) throw Error('Version is not in this workspace.');
    assertBrowserVersion(version);
    if (this.selected && this.selected !== digest) this.history.push(this.selected);
    this.history = this.history.slice(-24); this.selected = digest;
    this.tell('Selected for development operations. No inference started; Arena contenders are unchanged.');
  }
  rollback() {
    this.idle(); const previous = this.history.at(-1);
    if (!previous) throw Error('No previous selected version in this tab.');
    const version = this.saved.find(v => v.digest === previous)!; assertBrowserVersion(version);
    this.history.pop(); this.selected = previous;
    this.tell('Previous version selected. Existing results and provider charges are unchanged.');
  }
  async fork(prompt: string, memory: string) {
    this.idle(); this.room(); const parent = this.active;
    if (!parent) throw Error('Select a baseline first.');
    const candidate = await createVersion({ ...parent.config, prompt,
      memory: { mode: memory ? 'frozen' : 'none', content: memory } }, parent, { method: 'manual', source: null, identities: [] });
    this.idle(); if (this.active?.digest !== parent.digest) throw Error('Selection changed; save the candidate again.');
    this.add(candidate); this.tell('Manual candidate saved, not selected or promoted. Model weights are unchanged.'); return candidate;
  }
  cancel() { this.operation?.abort(); if (this.busy) this.tell('Cancelling local acceptance. A submitted provider request may still finish or be billed.'); }
  private begin(kind: DevelopmentAttempt['kind'], versions: Version[], games: number, maxPlies: number, limits: VersionConfig['limits']) {
    this.idle();
    this.beforeStart();
    if (this.results.length >= MAX_ATTEMPTS) throw Error('This tab holds 12 attempts. Download results before starting a new tab.');
    const abort = new AbortController(); this.operation = abort;
    const draft: AttemptDraft = { schema: DEVELOPMENT_SCHEMA, id: crypto.randomUUID(), kind, source: source.digest, referee: refereeManifest.digest,
      startedAt: new Date().toISOString(), finishedAt: '', exit: 'failed', versions: [...versions], candidate: null, probe: null,
      limits: { games, maxPlies, maxCalls: kind === 'probe' ? 1 : games * limits.maxCalls, milliseconds: limits.milliseconds, maxTokens: limits.maxTokens },
      calls: [], games: [], message: '' };
    const signal = AbortSignal.any([abort.signal, AbortSignal.timeout(limits.milliseconds)]);
    this.tell(`${kind === 'probe' ? 'Probing' : kind === 'practice' ? 'Practicing' : 'Comparing'} with fixed limits. Cancel is available.`);
    return { abort, signal, draft };
  }
  private async finish(draft: AttemptDraft) {
    draft.finishedAt = new Date().toISOString();
    const body = structuredClone(draft);
    this.results.push(freeze({ ...body, digest: await sha256(JSON.stringify(body)) }));
    this.operation = null; this.tell(draft.message);
  }
  async probe(agent: Agent, rules: Rules, models: Model[], limits: VersionConfig['limits'] = DEFAULT_VERSION_LIMITS) {
    this.idle(); this.room();
    if (!['harness', 'openrouter'].includes(agent.kind)) throw Error('Connect a model in Arena seat 1 first.');
    // Validate all declared configuration before permitting the one paid request.
    const privateAgent = structuredClone(agent), frozenModels = structuredClone(models), frozenRules = structuredClone(rules);
    limits = freeze(structuredClone(limits));
    await createVersion(connectedVersionConfig(privateAgent, frozenRules, privateAgent.model, limits));
    const { signal, draft } = this.begin('probe', [], 0, 1, limits);
    draft.probe = publicAgent(privateAgent);
    const call: Call = { version: null, game: 0, ply: 0, exit: 'pending', model: null, tokens: null, outputTokens: null, cost: null };
    try {
      signal.throwIfAborted(); draft.calls.push(call);
      // No ambient practice memory: this exact strategy is the frozen baseline.
      const decision = await decide(createGame(frozenRules), privateAgent, limits.maxTokens, signal, frozenModels);
      signal.throwIfAborted();
      call.model = decision.model; call.tokens = decision.tokens; call.outputTokens = decision.outputTokens ?? null; call.cost = decision.cost;
      const version = await createVersion(connectedVersionConfig(privateAgent, frozenRules, decision.model, limits));
      assertBrowserVersion(version); signal.throwIfAborted();
      if (call.outputTokens !== null && call.outputTokens > limits.maxTokens) throw Error('Probe exceeded declared token limit.');
      call.version = version.digest; call.exit = 'accepted'; this.add(version); draft.versions.push(version); draft.candidate = version.digest;
      if (this.selected && this.selected !== version.digest) this.history.push(this.selected);
      this.selected = version.digest; draft.exit = 'complete'; draft.message = 'Baseline frozen from one returned move identity. Selected for development only; this is not strength evidence.';
    } catch { call.exit = signal.aborted ? 'cancelled' : 'failed'; draft.exit = signal.aborted ? 'cancelled' : 'failed'; draft.message = safeFailure(signal.aborted); }
    finally { await this.finish(draft); }
    return this.results.at(-1)!;
  }
  async run(kind: 'practice' | 'compare', agent: Agent, models: Model[], maxPlies = 40) {
    this.idle(); integer(maxPlies, 4, 80, 'development ply cap');
    const selected = this.active; if (!selected) throw Error('Select a frozen version first.');
    assertBrowserVersion(selected);
    if (kind === 'practice' && !supportsLearning(selected.config.rules)) throw Error('Automatic memory practice currently supports connect games only. Chess/checkers use manual candidates and comparison.');
    if (kind === 'practice') this.room();
    const parent = kind === 'compare' ? this.saved.find(v => v.digest === selected.parent) : selected;
    if (!parent) throw Error('Import/select a candidate and its exact parent before comparison.');
    assertBrowserVersion(parent);
    // Public development may compare prompt/memory changes only; all resource,
    // provider, identity, sampling, referee and harness settings remain matched.
    const config = structuredClone(selected.config); config.prompt = parent.config.prompt; config.memory = parent.config.memory;
    if (JSON.stringify(config) !== JSON.stringify(parent.config)) throw Error('Comparison requires identical execution settings except strategy and memory.');
    if (selected.config.limits.maxCalls < Math.ceil(maxPlies / 2)) throw Error('Ply cap exceeds the per-game version call allowance. Lower the ply cap.');
    const versions = kind === 'compare' ? [parent, selected] : [selected];
    const privateAgent = structuredClone(agent), frozenModels = structuredClone(models);
    // Check connection matching before begin(), without a health or inference call.
    for (const v of versions) {
      if (privateAgent.kind !== v.config.runtime.provider || privateAgent.model !== v.config.runtime.requestedModel || privateAgent.effort !== v.config.runtime.reasoning)
        throw Error('Connect the selected version’s provider, model and effort in Arena seat 1.');
    }
    const { signal, draft } = this.begin(kind, versions, versions.length * 2, maxPlies, selected.config.limits);
    const practice = new PracticeMemory();
    let currentGame: DevelopmentGame | undefined;
    try {
      for (const seat of [0, 1]) for (const version of versions) {
        signal.throwIfAborted();
        const players = seat === 0 ? [policyAgent(privateAgent, version), opponent] : [opponent, policyAgent(privateAgent, version)];
        let state = createGame(version.config.rules);
        const record: RecordData = { schema: 'builderwars.exhibition.v1', id: crypto.randomUUID(), createdAt: new Date().toISOString(),
          rules: version.config.rules, agents: players.map(publicAgent), events: [], status: 'Running development game' };
        currentGame = { version: version.digest, seat, record, exit: 'failed' }; draft.games.push(currentGame);
        const session = await openVersionSession(version, browserVersionTransport(privateAgent, frozenModels));
        try {
          while (!state.over && state.moves.length < maxPlies) {
            signal.throwIfAborted(); const turn = state.turn, labelState = state, started = performance.now();
            let move: string, model = 'builtin/tactician', tokens: number | null = 0, cost: number | null = 0;
            if (turn === seat) {
              if (draft.calls.length >= draft.limits.maxCalls) throw Error('Aggregate call cap exhausted.');
              const call: Call = { version: version.digest, game: draft.games.length, ply: state.moves.length, exit: 'pending', model: null, tokens: null, outputTokens: null, cost: null };
              draft.calls.push(call);
              try {
                const result = await session.move(state, signal); signal.throwIfAborted();
                move = result.move; model = result.model; tokens = result.tokens; cost = result.cost;
                Object.assign(call, { exit: 'accepted', model, tokens, cost, outputTokens: result.outputTokens });
              } catch { call.exit = signal.aborted ? 'cancelled' : 'failed'; throw Error('Development request rejected.'); }
            } else move = botMove(state, 'tactician');
            signal.throwIfAborted(); state = applyMove(state, move);
            record.events.push({ move, model, tokens, cost, elapsed: performance.now() - started, comment: '', seat: turn, ply: state.moves.length, label: moveLabel(move, labelState) });
            this.tell(`${kind === 'practice' ? 'Practice' : 'Compare'} game ${draft.games.length}/${draft.limits.games}, ply ${state.moves.length}/${maxPlies}; ${draft.calls.length} model requests submitted.`);
            // Yield between local opponent moves, allowing visible cancellation.
            await new Promise(resolve => setTimeout(resolve, 0));
          }
          currentGame.exit = isRuleComplete(state) ? 'complete' : 'capped'; record.status = currentGame.exit === 'complete' ? state.reason : 'Development ply cap; no result';
          if (kind === 'practice' && currentGame.exit === 'complete') await practice.remember(record, players);
        } finally { session.cancel(); }
      }
      signal.throwIfAborted();
      if (kind === 'practice') {
        const context = await practice.context(policyAgent(privateAgent, selected), selected.config.rules, 'frozen-evaluation');
        signal.throwIfAborted();
        if (context) {
          // The immutable result ID binds provenance without a circular candidate/result hash.
          const candidate = await createVersion({ ...selected.config, memory: { mode: 'frozen', content: context.prompt } }, selected,
            { method: 'manual', source: await sha256(draft.id), identities: [] });
          signal.throwIfAborted(); this.add(candidate); draft.versions.push(candidate); draft.candidate = candidate.digest;
        }
      }
      draft.exit = 'complete';
      draft.message = kind === 'compare' ? 'Public development comparison finished. Inspect complete/capped games; no held-out admission or automatic promotion.'
        : draft.candidate ? 'Practice memory candidate saved, not selected. Only this run’s completed games supplied lessons; no provider weights changed.'
        : 'Practice finished without qualifying recorded mistakes. No candidate created; incumbent retained.';
    } catch {
      if (currentGame && currentGame.exit === 'failed') { currentGame.exit = signal.aborted ? 'cancelled' : 'failed'; currentGame.record.status = safeFailure(signal.aborted); }
      draft.exit = signal.aborted ? 'cancelled' : 'failed'; draft.message = safeFailure(signal.aborted);
    } finally { await this.finish(draft); }
    return this.results.at(-1)!;
  }
}
