(function () {
  'use strict';
  const E = globalThis.Agentworld, $ = (id) => document.getElementById(id);
  const KEY = 'builderwars.agentworld.experimental.v1';
  let cfg = { seed: 20260920, mode: 'cooperative' }, state = E.create(cfg), actions = [];
  let revision = 0, importSequence = 0;
  let questRevision = -1, questProjection = null;
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
    renderQuests();
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
  function renderQuests() {
    if (questRevision !== revision) {
      questProjection = globalThis.AgentworldQuests.project(JSON.stringify({ schema: E.REPLAY, config: cfg, actions, finalState: state }));
      questRevision = revision;
    }
    const quests = questProjection.quests;
    const completed = quests.filter((quest) => quest.complete).length;
    const next = quests.findIndex((quest) => quest.applicable && !quest.complete);
    const summary = cfg.mode !== 'cooperative' ? 'Choose Cooperate for shared quests.'
      : state.status === 'capped' ? `${completed} / 3 quests complete · action limit reached`
      : `${completed} / 3 quests complete`;
    if ($('quest-status').textContent !== summary) $('quest-status').textContent = summary;
    const descriptions = ['Collect the first supply anywhere in this visit.', 'Bring at least one supply home with each crew.', 'Bring all 16 supplies home together.'];
    $('quests').replaceChildren(...quests.map((quest, index) => {
      const row = el('li', `quest${quest.complete ? ' complete' : quest.applicable && index === next && state.status !== 'capped' ? ' current' : ''}`);
      const progress = !quest.applicable ? 'Cooperative mode only' : quest.complete ? `Complete · turn ${quest.completedAtTurn}` : state.status === 'capped' ? 'Incomplete · action limit reached' : index === next ? 'Next objective' : 'Still ahead';
      row.append(el('span', 'quest-number', String(index + 1)), el('h3', '', quest.title), el('p', '', descriptions[index]), el('strong', 'quest-state', progress));
      return row;
    }));
    $('quest-outcome').textContent = cfg.mode !== 'cooperative' ? 'Crew comparison keeps its own result. Shared quests apply to a cooperative visit.'
      : state.status === 'complete' ? `Both crews finished: Amber ${state.scores.amber}, Tide ${state.scores.tide}, in ${state.turn} accepted turns. Your recording keeps the journey.`
      : state.status === 'capped' ? `${E.remaining(state)} supplies are still undelivered. Earlier milestones remain; Finish together is incomplete. Export this recording to keep the attempt.`
      : 'Progress follows the accepted actions in this recording. Opening it again restores the same milestones.';
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
  $('stop').addEventListener('click', () => { pause(); render(); message('Stopped watching. Your visit stays here; nothing advances until you choose another action.'); });
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
  const L = globalThis.AgentworldLedger;
  function renderLedger(aggregate) {
    const out = $('ledger-out');
    $('ledger-status').textContent = aggregate.totals.runs
      ? `Aggregate over ${aggregate.totals.runs} verified run${aggregate.totals.runs === 1 ? '' : 's'}; ${aggregate.totals.refused} refused.`
      : 'No runs accepted; nothing to aggregate.';
    if (!aggregate.totals.runs && !aggregate.totals.refused) { out.replaceChildren(); return; }
    const frag = document.createDocumentFragment();
    const totals = el('p', 'subtle', `Delivered ${aggregate.totals.delivered} supplies across ${aggregate.totals.actions} accepted actions. Source labels: ${aggregate.totals.sources.scripted} scripted, ${aggregate.totals.sources.manual} manual (self-declared).`);
    frag.append(totals);
    if (aggregate.totals.runs) {
      const actorHead = el('strong', '', 'Per-actor outcomes');
      const actorTable = el('table');
      const head = el('tr');
      for (const label of ['Actor', 'Deliveries', 'Collects', 'Moves', 'Waits', 'Runs']) head.append(el('th', '', label));
      actorTable.append(head);
      for (const id of E.ORDER) {
        const row = el('tr');
        for (const value of [names[id], aggregate.actors[id].deliveries, aggregate.actors[id].collects, aggregate.actors[id].moves, aggregate.actors[id].waits, aggregate.actors[id].runsAppeared]) row.append(el('td', '', String(value)));
        actorTable.append(row);
      }
      frag.append(actorHead, actorTable);
      const runTable = el('table');
      const runHead = el('tr');
      for (const label of ['Run', 'Seed', 'Mode', 'Outcome', 'Turns', 'Amber', 'Tide', 'Fingerprint']) runHead.append(el('th', '', label));
      runTable.append(runHead);
      for (const run of aggregate.runs) {
        const row = el('tr');
        for (const value of [run.label || '(unnamed)', run.seed, run.mode, run.status, run.turns, run.amber, run.tide, run.fingerprint]) row.append(el('td', '', String(value)));
        runTable.append(row);
      }
      frag.append(el('strong', '', 'Per-run outcomes'), runTable);
    }
    for (const refusal of aggregate.refused) frag.append(el('p', 'subtle', `Refused: ${refusal.label || '(unnamed)'} \u2014 ${refusal.reason}`));
    for (const boundary of aggregate.boundaries) frag.append(el('p', 'subtle', boundary));
    out.replaceChildren(frag);
  }
  let lastAggregate = null, ledgerSequence = 0;
  function clearLedger(text) {
    lastAggregate = null;
    $('ledger-out').replaceChildren();
    $('ledger-status').textContent = text;
    $('ledger-export').disabled = true;
  }
  $('ledger-export').disabled = true;
  $('ledger-import').addEventListener('change', () => {
    ledgerSequence++;
    clearLedger('Replay selection changed. Build hive memory for these files.');
  });
  $('ledger-build').addEventListener('click', async () => {
    const buildRequest = ++ledgerSequence;
    pause(); render();
    const files = Array.from($('ledger-import').files || []);
    clearLedger('No aggregate built for this selection.');
    if (!files.length) { message('Select one or more replay files before building hive memory.', true); return; }
    if (files.length > L.MAX_RUNS) { message(`Hive memory accepts at most ${L.MAX_RUNS} replays.`, true); return; }
    $('ledger-status').textContent = 'Reading and verifying selected replay files…';
    try {
      const entries = [];
      for (const file of files) {
        if (buildRequest !== ledgerSequence) return;
        if (file.size > E.MAX_BYTES) {
          entries.push({ label: file.name, error: 'Replay exceeds the 128 KiB limit; file was not read.' });
          continue;
        }
        try {
          const text = await file.text();
          if (buildRequest !== ledgerSequence) return;
          entries.push({ label: file.name, text });
        } catch {
          if (buildRequest !== ledgerSequence) return;
          entries.push({ label: file.name, error: 'Replay file could not be read.' });
        }
      }
      if (buildRequest !== ledgerSequence) return;
      const aggregate = L.tallyRuns(entries);
      lastAggregate = aggregate;
      renderLedger(aggregate);
      $('ledger-export').disabled = false;
      message(aggregate.totals.runs
        ? `Hive memory built from ${aggregate.totals.runs} verified run${aggregate.totals.runs === 1 ? '' : 's'}. Descriptive only \u2014 not a ranking.`
        : 'No replay passed verification; nothing was aggregated.', !aggregate.totals.runs);
    } catch (error) {
      if (buildRequest !== ledgerSequence) return;
      clearLedger('Hive memory could not be built for this selection.');
      message(error.message, true);
    }
  });
  $('ledger-export').addEventListener('click', () => {
    pause(); render();
    if (!lastAggregate) { message('Build hive memory before exporting it.', true); return; }
    download(lastAggregate, 'agentworld-hive-ledger.json');
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
