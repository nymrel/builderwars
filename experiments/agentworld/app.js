(function () {
  'use strict';
  const E = globalThis.Agentworld, $ = (id) => document.getElementById(id);
  const KEY = 'builderwars.agentworld.experimental.v1';
  let cfg = { seed: 20260920, mode: 'cooperative' }, state = E.create(cfg), actions = [];
  let revision = 0, importSequence = 0;
  let timer = null, dirtyEditor = false, autosave = true, lastStored = null, storageConflict = false;
  const names = { 'amber-1': 'Amber 01', 'amber-2': 'Amber 02', 'tide-1': 'Tide 01', 'tide-2': 'Tide 02' };
  const codes = { 'amber-1': 'A1', 'amber-2': 'A2', 'tide-1': 'T1', 'tide-2': 'T2' };
  function message(text, error = false) { $('message').textContent = text; $('message').classList.toggle('error', error); }
  function el(tag, className, text) { const n = document.createElement(tag); if (className) n.className = className; if (text !== undefined) n.textContent = text; return n; }
  function pause() { if (timer !== null) window.clearInterval(timer); timer = null; $('play').textContent = 'Watch crews'; }
  function save() {
    if (!autosave || storageConflict) return;
    try {
      if (window.localStorage.getItem(KEY) !== lastStored) {
        pause(); storageConflict = true; autosave = false; $('autosave').checked = false;
        $('save-status').textContent = 'Saved checkpoint changed. This tab will not overwrite it.';
        message('Saved checkpoint changed outside this tab. Export or reload before saving.', true); render(); return;
      }
      const text = JSON.stringify(E.pack(cfg, actions));
      window.localStorage.setItem(KEY, text); lastStored = text;
      $('save-status').textContent = 'Saved in this browser only.';
    } catch { $('save-status').textContent = 'Storage unavailable. This run is in memory only; export to keep it.'; }
  }
  function render() {
    $('turn').textContent = `${state.turn} / ${E.LIMIT}`;
    const delivered = state.scores.amber + state.scores.tide;
    $('delivered').textContent = `${delivered} / 16`; $('remaining').textContent = E.remaining(state);
    $('amber-score').textContent = state.scores.amber; $('tide-score').textContent = state.scores.tide;
    $('progress').setAttribute('aria-valuenow', String(delivered)); $('progress-fill').style.width = `${delivered / 16 * 100}%`;
    $('world-status').textContent = state.status === 'running' ? (timer === null ? 'Paused' : 'Scripted run') : state.status === 'complete' ? 'Complete' : 'Turn cap reached';
    $('goal-title').textContent = cfg.mode === 'cooperative' ? 'Shared mission' : 'Crew comparison';
    $('goal-copy').textContent = cfg.mode === 'cooperative' ? 'Together, deliver all 16 supplies. Crew totals are descriptive, not a ranking.' : 'Compare deliveries in this one seeded run. Not a balanced evaluation or official ranking.';
    $('next').textContent = state.status === 'running' ? `Next: ${names[E.active(state)]}` : 'World finished · replay or start again';
    for (const id of ['step', 'batch', 'play', 'sample-action', 'apply-action']) $(id).disabled = state.status !== 'running';
    const board = document.createDocumentFragment();
    for (let y = 0; y < E.SIZE; y++) for (let x = 0; x < E.SIZE; x++) {
      const cell = el('div', 'cell'), supply = state.supplies.find((s) => s.x === x && s.y === y && s.amount > 0);
      const base = state.bases.find((b) => b.x === x && b.y === y), agents = state.agents.filter((a) => a.x === x && a.y === y);
      let label = `Cell ${x}, ${y}`;
      if (supply) { cell.classList.add('supply'); cell.append(el('span', 'terrain', `□ ${supply.amount}`)); label += `, ${supply.amount} supplies`; }
      if (base) { cell.classList.add(`base-${base.team}`); cell.append(el('span', 'terrain', '⌂')); label += `, ${base.team} base`; }
      if (agents.length) { const pieces = el('div', 'pieces'); for (const a of agents) { const piece = el('span', `piece ${a.team}`, codes[a.id] + (a.carry ? '+' : '')); if (state.status === 'running' && a.id === E.active(state)) piece.classList.add('active'); pieces.append(piece); label += `, ${names[a.id]}${a.carry ? ' carrying supply' : ''}`; } cell.append(pieces); }
      cell.title = label; cell.setAttribute('aria-hidden', 'true'); board.append(cell);
    }
    $('world').replaceChildren(board);
    $('agents').replaceChildren(...state.agents.map((a) => {
      const row = el('div', 'agent'), title = el('div'); title.append(el('strong', '', names[a.id]), el('div', 'subtle', `Cell ${a.x}, ${a.y} · scripted baseline`));
      row.append(el('div', `avatar ${a.team}`, codes[a.id]), title, el('div', 'status', a.carry ? 'Carrying\nsupply' : a.id === E.active(state) && state.status === 'running' ? 'Next turn' : 'Empty')); return row;
    }));
    $('journal-count').textContent = `${actions.length} accepted actions`;
    $('log').replaceChildren(...actions.slice(-12).reverse().map((a) => {
      const row = el('li'); row.append(el('time', '', String(a.turn + 1).padStart(3, '0')), el('span', '', `${names[a.actor]} · ${a.type}${a.direction ? ' ' + a.direction : ''}`), el('span', 'source', a.source)); return row;
    }));
    if (!actions.length) $('log').append(el('li', 'empty', 'Start the crews. Every accepted action will be recorded here.'));
    const focusedManual = $('manual').contains(document.activeElement) ? document.activeElement.textContent : null;
    $('manual').replaceChildren(...E.legal(state, 'manual').map((a) => { const button = el('button', '', a.type === 'move' ? a.direction : a.type); button.addEventListener('click', () => { pause(); accept(a); }); return button; }));
    if (focusedManual !== null) (Array.from($('manual').children).find((button) => button.textContent === focusedManual) || $('manual').firstElementChild || $('verify')).focus({ preventScroll: true });
    $('legal-json').textContent = JSON.stringify(E.legal(state, 'manual'), null, 2);
    if (!dirtyEditor && document.activeElement !== $('action-json')) sample();
  }
  function sample() { $('action-json').value = state.status === 'running' ? JSON.stringify({ ...E.scripted(state), source: 'manual' }, null, 2) : ''; dirtyEditor = false; }
  function accept(action) {
    try {
      const next = E.step(state, action); actions.push(JSON.parse(JSON.stringify(action))); state = next; revision++;
      $('proof').textContent = 'Not replayed';
      if (state.status !== 'running') { pause(); message(state.status === 'complete' ? 'Mission complete. All supplies delivered. Verify or export this exact run.' : 'The 240-turn limit is reached. Undelivered supplies remain; this is a capped run.'); }
      else message(`${names[action.actor]}: ${action.type}${action.direction ? ' ' + action.direction : ''}. Accepted turn ${state.turn}.`);
      render(); save(); return true;
    } catch (error) { pause(); message(error.message, true); render(); return false; }
  }
  function download(value, filename) {
    const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }));
    const a = document.createElement('a'); a.href = url; a.download = filename; a.click(); window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  $('play').addEventListener('click', () => {
    if (timer !== null) { pause(); render(); message('Auto-play paused. Manual stepping is still available.'); return; }
    timer = window.setInterval(() => { if (!accept(E.scripted(state))) pause(); }, 220);
    $('play').textContent = 'Pause crews'; render(); message('Running scripted actors. No AI provider is connected.');
  });
  $('step').addEventListener('click', () => { pause(); accept(E.scripted(state)); });
  $('batch').addEventListener('click', () => { pause(); for (let i = 0; i < 16 && state.status === 'running'; i++) if (!accept(E.scripted(state))) break; });
  $('new').addEventListener('click', () => {
    pause(); render();
    try {
      const nextCfg = { seed: Number($('seed').value), mode: $('mode').value }; const next = E.create(nextCfg);
      if (actions.length && !window.confirm('Replace this tab’s run? Export its replay first to keep it.')) return;
      if (storageConflict) { autosave = false; $('autosave').checked = false; }
      cfg = nextCfg; state = next; actions = []; revision++; dirtyEditor = false; $('proof').textContent = 'Not replayed';
      render(); save(); message('New world created. Same seed and actions reproduce the same world.');
    } catch (error) { message(error.message, true); }
  });
  $('verify').addEventListener('click', () => {
    pause();
    try {
      E.verify({ schema: E.REPLAY, config: cfg, actions, finalState: state });
      $('proof').textContent = 'Local replay pass'; message('Local replay pass: rules and final state match. This does not attest an actor, provider, or independent execution.');
    } catch (error) { message(error.message, true); }
    render();
  });
  $('export').addEventListener('click', () => { pause(); render(); download(E.pack(cfg, actions), `agentworld-${cfg.seed}-turn-${state.turn}.json`); });
  $('import').addEventListener('change', async (event) => {
    const importRequest = ++importSequence;
    pause(); render(); const file = event.target.files[0]; if (!file) return;
    const importRevision = revision;
    try {
      if (file.size > E.MAX_BYTES) throw new Error('Replay exceeds the 128 KiB limit.');
      const text = await file.text();
      if (importRequest !== importSequence) return;
      const verified = E.verify(E.parse(text));
      if (revision !== importRevision) throw new Error('World changed while reading the file; select the replay again.');
      // A file read yields. Pause again and confirm against the current tab, not the pre-read state.
      pause();
      if (actions.length && !window.confirm('The replay is valid. Replace the current tab’s run?')) return;
      if (storageConflict) { autosave = false; $('autosave').checked = false; }
      cfg = verified.config; actions = verified.actions; state = verified.state; revision++; dirtyEditor = false;
      $('seed').value = cfg.seed; $('mode').value = cfg.mode; $('proof').textContent = 'Local replay pass';
      render(); save(); message('Imported after local replay validation. Actor source labels remain self-declared.');
    } catch (error) { if (importRequest === importSequence) message(`Import refused: ${error.message}`, true); }
    finally { if (importRequest === importSequence) { event.target.value = ''; render(); } }
  });
  $('autosave').addEventListener('change', () => {
    if (storageConflict && $('autosave').checked) { $('autosave').checked = false; message('Another tab owns the saved checkpoint. Reload to adopt it or export this tab first.', true); return; }
    autosave = $('autosave').checked;
    if (autosave) save(); else $('save-status').textContent = 'Memory only. An earlier saved checkpoint may remain until removed.';
  });
  $('clear').addEventListener('click', () => {
    pause(); render();
    if (!window.confirm('Remove the saved session for this browser? The current tab stays in memory and can still be exported.')) return;
    try { window.localStorage.removeItem(KEY); lastStored = null; autosave = false; storageConflict = false; $('autosave').checked = false; $('save-status').textContent = 'Saved session removed. Current run is in memory only.'; message('Saved session removed; automatic saving is off.'); }
    catch { message('The browser refused storage access. The current run remains in memory.', true); }
  });
  $('action-json').addEventListener('input', () => { dirtyEditor = true; });
  $('sample-action').addEventListener('click', sample);
  $('apply-action').addEventListener('click', () => { pause(); try { if (accept(E.parse($('action-json').value))) { dirtyEditor = false; sample(); } } catch (error) { message(error.message, true); render(); } });
  $('observation').addEventListener('click', () => { pause(); render(); download({ rules: E.RULES, state, activeActor: state.status === 'running' ? E.active(state) : null, legalActions: E.legal(state, 'manual'), boundary: 'Local experimental state; no credentials, external code, identity attestation or hosted execution.' }, `agentworld-observation-${state.turn}.json`); });
  document.addEventListener('visibilitychange', () => { if (document.hidden && timer !== null) { pause(); render(); message('Auto-play paused because the page is hidden.'); } });
  window.addEventListener('pagehide', pause);
  window.addEventListener('storage', (event) => {
    if (event.key === KEY && event.newValue !== lastStored) { pause(); storageConflict = true; autosave = false; $('autosave').checked = false; $('save-status').textContent = 'Another tab changed the saved run. This tab will not overwrite it.'; message('Cross-tab checkpoint change detected. Export this tab or reload to adopt the saved run.', true); render(); }
  });
  try {
    const stored = window.localStorage.getItem(KEY);
    if (stored) { const verified = E.verify(E.parse(stored)); cfg = verified.config; state = verified.state; actions = verified.actions; lastStored = stored; $('seed').value = cfg.seed; $('mode').value = cfg.mode; $('proof').textContent = 'Local replay pass'; message('Saved session restored after local replay validation. Auto-play is paused.'); }
  } catch { autosave = false; $('autosave').checked = false; $('save-status').textContent = 'Saved session unreadable or storage unavailable. Existing data was not overwritten.'; message('Starting in memory: stored data could not be safely restored.', true); }
  render();
})();
