import { ModelDevelopment, developmentTotals } from './model-development';
import { supportsLearning } from './learning';
import { replay, type Rules } from './runtime';
import { type Agent, type Model } from './models';
import type { ExportKind } from './file-transfer';

const esc = (s: unknown) => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);
export function mountModelDevelopment(host: HTMLElement, options: {
  connection: () => { agent: Agent; rules: Rules; models: Model[] };
  ready: () => void; connect: () => void;
  download: (name: string, data: unknown, kind: ExportKind) => Promise<unknown>;
}) {
  host.insertAdjacentHTML('beforeend', `<section class="workspace-form model-development" aria-labelledby="development-title">
    <div class="divider"></div><h2 id="development-title">Develop a model version</h2>
    <p>Freeze Arena seat 1’s connected model, make a strategy or memory candidate, then compare it with its parent.</p>
    <p class="muted">Separate from Arena play. No provider weights change. Public development games are not held-out admission or a certified ranking.</p>
    <button id="dev-connect">Connect Arena seat 1</button>
    <p id="dev-status" role="status" aria-live="polite"></p>
    <label>Versions in this tab<select id="dev-versions" aria-describedby="dev-version-info"><option value="">No saved versions</option></select></label>
    <p id="dev-version-info" class="muted"></p>
    <div class="form-actions"><button id="dev-select">Select version</button><button id="dev-rollback">Roll back selection</button><button id="dev-download-version">Download version</button><label class="file-button">Import version<input id="dev-import" type="file" accept="application/json,.json"></label></div>
    <details id="dev-edit"><summary>Edit a candidate</summary><p>Save changes as a new version. The current selection stays unchanged until you select the candidate.</p>
      <label>Strategy<textarea id="dev-strategy" maxlength="1000" rows="3"></textarea></label>
      <label>Frozen memory / reminders<textarea id="dev-memory" maxlength="4000" rows="4"></textarea></label>
      <button id="dev-fork">Save manual candidate</button>
    </details>
    <div class="settings-row"><label>Plies per game<select id="dev-plies"><option value="8">8 · short diagnostic</option><option value="20">20</option><option value="40" selected>40</option></select></label></div>
    <p id="dev-budget" class="muted"></p>
    <label class="checkbox"><input id="dev-consent" type="checkbox">I authorize the next operation to use my connected model account.</label>
    <div class="form-actions"><button id="dev-probe">Probe & freeze · 1 request</button><button id="dev-practice">Practice → memory candidate</button><button id="dev-compare" class="primary">Compare selected with parent</button><button id="dev-cancel">Cancel operation</button></div>
    <p id="dev-practice-scope" class="muted"></p>
    <p class="muted">One operation at a time. No automatic retries, selection or promotion. Cancel stops further local requests; an already submitted request may still be billed. Browser requests declare no extra tools; a connected backend’s internals remain unverified.</p>
    <details><summary>Retained attempts & replay files</summary><div id="dev-results"></div></details>
    <p class="muted">Tab-only workspace: download versions and results before closing. Imports restore no keys or endpoints and start no inference. Downloads include strategy/memory and full run evidence; review before sharing.</p>
  </section>`);
  const $ = <T extends HTMLElement = HTMLElement>(id: string) => host.querySelector<T>('#' + id)!;
  let signature = '', renderedResults = -1, editedVersion: string | null = null, uiBusy = false;
  const work = new ModelDevelopment(render, options.ready);
  function render() {
    const active = work.active, busy = work.busy || uiBusy, list = work.versions;
    $('dev-status').textContent = work.message;
    const nextSignature = list.map(v => v.digest).join() + ':' + active?.digest;
    if (nextSignature !== signature) {
      const selected = $<HTMLSelectElement>('dev-versions').value;
      $('dev-versions').innerHTML = list.length ? list.map(v => `<option value="${v.digest}">v${v.revision} · ${esc(v.config.rules.name)} · ${v.digest.slice(0, 10)}${v.digest === active?.digest ? ' · SELECTED' : ''}</option>`).join('') : '<option value="">No saved versions</option>';
      $<HTMLSelectElement>('dev-versions').value = list.some(v => v.digest === selected) ? selected : active?.digest ?? list.at(-1)?.digest ?? '';
      signature = nextSignature;
    }
    if (editedVersion !== active?.digest) {
      $<HTMLTextAreaElement>('dev-strategy').value = active?.config.prompt ?? '';
      $<HTMLTextAreaElement>('dev-memory').value = active?.config.memory.content ?? '';
      editedVersion = active?.digest ?? null;
    }
    $('dev-version-info').textContent = active
      ? `Selected v${active.revision} · ${active.config.rules.name} · requested ${active.config.runtime.requestedModel} · returned ${active.config.runtime.resolvedModel} (${active.config.runtime.evidence}). Source ${active.config.harness.source.slice(0, 12)}. No certified admission.`
      : 'Selection starts no inference. Imported versions must match this browser’s executor before they can run.';
    const calls = Math.ceil(Number($<HTMLSelectElement>('dev-plies').value) / 2), limits = active?.config.limits;
    $('dev-budget').textContent = `Probe: at most 1 model request. Practice: 2 games, at most ${2 * calls} model requests. Compare: 4 games, at most ${4 * calls} model requests. ${limits?.maxTokens ?? 1024} requested output tokens/call; ${Math.round((limits?.milliseconds ?? 300000) / 1000)} seconds per operation. Provider dollars and internal compute are not capped here.`;
    $('dev-practice-scope').textContent = active && !supportsLearning(active.config.rules)
      ? 'Chess/checkers: manual strategy/memory candidates and comparison are available. Automatic engine-informed practice is not yet implemented.'
      : 'Practice uses only this operation’s completed connect-game mistakes to propose frozen reminders. Capped/imported/comparison games never teach it. No mistakes means no candidate.';
    for (const id of ['dev-connect', 'dev-versions', 'dev-select', 'dev-download-version', 'dev-import', 'dev-strategy', 'dev-memory', 'dev-fork', 'dev-plies', 'dev-consent'])
      ($<HTMLInputElement>(id)).disabled = busy || (['dev-select', 'dev-download-version'].includes(id) && !list.length) || (['dev-fork', 'dev-strategy', 'dev-memory'].includes(id) && !active);
    $<HTMLButtonElement>('dev-rollback').disabled = busy || !work.canRollback;
    const consent = $<HTMLInputElement>('dev-consent').checked;
    $<HTMLButtonElement>('dev-probe').disabled = busy || !consent;
    $<HTMLButtonElement>('dev-practice').disabled = busy || !consent || !active || !supportsLearning(active.config.rules);
    $<HTMLButtonElement>('dev-compare').disabled = busy || !consent || !active?.parent;
    $<HTMLButtonElement>('dev-cancel').disabled = !work.busy;
    if (work.attempts.length !== renderedResults) {
      renderedResults = work.attempts.length;
      $('dev-results').innerHTML = work.attempts.length ? work.attempts.map((a, i) => {
        const totals = developmentTotals(a);
        return `<article class="development-attempt"><h3>${esc(a.kind)} · ${esc(a.exit)}</h3><p>${esc(a.message)}</p>
          <p>${totals.calls} requests recorded · ${totals.accepted} accepted · ${totals.complete} rule-complete games · ${totals.capped} capped</p>
          <p class="muted">Reported tokens: ${totals.tokens ?? 'Unknown'} · reported cost: ${totals.cost === null ? 'Unknown' : '$' + totals.cost.toFixed(4)}. Rejected requests may have unrecorded usage; not a billing total.</p>
          ${a.games.map(g => { const state = replay(g.record).state; return `<p>v${a.versions.find(v => v.digest === g.version)?.revision} · ${g.seat === 0 ? 'first' : 'second'} seat · ${g.record.events.length} plies · ${g.exit === 'complete' ? state.winner === null ? 'draw' : state.winner === g.seat ? 'model won' : 'Tactician won' : esc(g.exit) + ' · no result'}</p>`; }).join('')}
          <button data-dev-download="${i}">Download full attempt + replays</button></article>`;
      }).join('') : '<p>No attempts yet. Failed and cancelled operations will be retained here.</p>';
      host.querySelectorAll<HTMLButtonElement>('[data-dev-download]').forEach(button => button.onclick = () => void act(async () => {
        const attempt = work.attempts[Number(button.dataset.devDownload)];
        await options.download(`builderwars-development-${attempt.id}.json`, attempt, 'evaluation');
      }));
    }
    host.querySelectorAll<HTMLButtonElement>('[data-dev-download]').forEach(button => button.disabled = busy);
  }
  async function act(fn: () => unknown | Promise<unknown>) {
    if (uiBusy || work.busy) return;
    uiBusy = true; render();
    try { await fn(); } catch (error) { $('dev-status').textContent = error instanceof Error ? error.message : 'Operation failed.'; }
    finally { uiBusy = false; const message = $('dev-status').textContent; render(); $('dev-status').textContent = message; }
  }
  function run(kind: 'probe' | 'practice' | 'compare') {
    if (!$<HTMLInputElement>('dev-consent').checked || work.busy || uiBusy) return;
    $<HTMLInputElement>('dev-consent').checked = false;
    void act(async () => {
      options.ready(); const { agent, rules, models } = options.connection();
      if (kind === 'probe') await work.probe(agent, rules, models);
      else await work.run(kind, agent, models, Number($<HTMLSelectElement>('dev-plies').value));
    });
  }
  $('dev-connect').onclick = options.connect;
  $('dev-select').onclick = () => void act(() => work.select($<HTMLSelectElement>('dev-versions').value));
  $('dev-rollback').onclick = () => void act(() => work.rollback());
  $('dev-fork').onclick = () => void act(() => work.fork($<HTMLTextAreaElement>('dev-strategy').value, $<HTMLTextAreaElement>('dev-memory').value));
  $('dev-download-version').onclick = () => void act(async () => {
    const version = work.versions.find(v => v.digest === $<HTMLSelectElement>('dev-versions').value);
    if (version) await options.download(`builderwars-version-${version.digest}.json`, version, 'evaluation');
  });
  $<HTMLInputElement>('dev-import').onchange = event => void act(async () => {
    const input = event.target as HTMLInputElement, file = input.files?.[0]; input.value = '';
    if (!file) return;
    if (file.size > 32000) throw Error('Version file exceeds 32 KB.');
    await work.importVersion(JSON.parse(await file.text()));
  });
  $('dev-probe').onclick = () => run('probe'); $('dev-practice').onclick = () => run('practice'); $('dev-compare').onclick = () => run('compare');
  $('dev-cancel').onclick = () => work.cancel();
  $('dev-consent').onchange = render; $('dev-plies').onchange = render;
  render(); return work;
}
