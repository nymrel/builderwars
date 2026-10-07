/* BuilderWars Agentworld experimental hive-memory ledger. Descriptive aggregation over verified replays only. */
(function (root) {
  'use strict';
  const A = root.Agentworld;
  if (!A) fail('Agentworld engine must load before the ledger.');
  const SCHEMA = 'builderwars.agentworld.hive-ledger.v0.1';
  const MAX_RUNS = 64, MAX_LABEL = 80, MAX_REASON = 160;
  const BOUNDARIES = Object.freeze([
    'Descriptive aggregate of the exact replays provided; not a ranking, rating, or evaluation.',
    'Only distinct engine-verified replays are counted; every refused entry, including duplicates, is listed with its reason.',
    'Counts describe unique replay contents, not attested execution events; identical contents cannot distinguish separate executions.',
    'Actor source labels (scripted/manual) are self-declared and never attested here.',
    'Run fingerprints are non-cryptographic ordering identifiers, not security bindings; deduplication uses full canonical equality.',
    'No network, storage, provider, or identity claims are made by this aggregate.'
  ]);

  function fail(message) { throw new Error(message); }

  function hashCanonical(text) {
    let hash = 0x811c9dc5;
    for (let i = 0; i < text.length; i++) {
      hash ^= text.charCodeAt(i);
      hash = Math.imul(hash, 0x01000193) >>> 0;
    }
    return hash.toString(16).padStart(8, '0');
  }

  function fingerprint(packet) { return hashCanonical(A.canonical(packet)); }
  function compare(a, b) { return a < b ? -1 : a > b ? 1 : 0; }
  function labelOf(entry) { return entry && typeof entry.label === 'string' ? entry.label.slice(0, MAX_LABEL) : ''; }
  function reasonOf(error) { return String(error.message || 'Refused entry.').slice(0, MAX_REASON); }

  function emptyActor() { return { deliveries: 0, collects: 0, moves: 0, waits: 0, runsAppeared: 0 }; }

  function verifiedRun(entry) {
    if (!entry || typeof entry !== 'object' || Array.isArray(entry) ||
        (entry.label !== undefined && typeof entry.label !== 'string') ||
        Object.keys(entry).some((key) => !['label', 'text', 'error'].includes(key)) ||
        (Object.hasOwn(entry, 'text') === Object.hasOwn(entry, 'error'))) {
      fail('Ledger entry must contain replay text or a file-read error, with an optional string label.');
    }
    if (Object.hasOwn(entry, 'error')) {
      if (typeof entry.error !== 'string' || !entry.error) fail('File-read refusal requires a nonempty error string.');
      fail(entry.error);
    }
    if (typeof entry.text !== 'string') fail('Replay text must be a string.');
    const label = labelOf(entry);
    const verified = A.verify(A.parse(entry.text));
    const canonical = A.canonical({ config: verified.config, actions: verified.actions });
    const perActor = {};
    for (const id of A.ORDER) perActor[id] = emptyActor();
    const sources = { scripted: 0, manual: 0 };
    for (const action of verified.actions) {
      if (action.source !== 'scripted' && action.source !== 'manual') fail('Unknown action source in replay.');
      sources[action.source]++;
      const row = perActor[action.actor];
      if (!row) fail('Unknown actor in replay actions.');
      if (action.type === 'deliver') row.deliveries++;
      else if (action.type === 'collect') row.collects++;
      else if (action.type === 'move') row.moves++;
      else row.waits++;
    }
    const amberDeliveries = perActor['amber-1'].deliveries + perActor['amber-2'].deliveries;
    const tideDeliveries = perActor['tide-1'].deliveries + perActor['tide-2'].deliveries;
    if (amberDeliveries !== verified.state.scores.amber || tideDeliveries !== verified.state.scores.tide) {
      fail('Actor deliveries disagree with the verified final score.');
    }
    const run = {
      label,
      seed: verified.config.seed,
      mode: verified.config.mode,
      status: verified.state.status,
      turns: verified.state.turn,
      delivered: amberDeliveries + tideDeliveries,
      amber: amberDeliveries,
      tide: tideDeliveries,
      actions: verified.actions.length,
      sources,
      perActor,
      fingerprint: hashCanonical(canonical)
    };
    return { canonical, run };
  }

  function tallyRun(entry) { return verifiedRun(entry).run; }

  function tallyRuns(entries) {
    if (!Array.isArray(entries)) fail('Ledger input must be an array of {label, text} or {label, error} entries.');
    if (entries.length > MAX_RUNS) fail(`Ledger accepts at most ${MAX_RUNS} entries per aggregate.`);
    const verified = [], runs = [], refused = [];
    for (const entry of entries) {
      try {
        verified.push(verifiedRun(entry));
      } catch (error) {
        refused.push({ label: labelOf(entry), reason: reasonOf(error) });
      }
    }
    verified.sort((a, b) => a.run.seed - b.run.seed || compare(a.run.mode, b.run.mode) ||
      compare(a.run.label, b.run.label) || compare(a.run.fingerprint, b.run.fingerprint) || compare(a.canonical, b.canonical));
    // Full canonical equality is the dedup key; an FNV collision never collapses distinct replays.
    // Sorting first selects the smallest bounded label independently of input order.
    const seen = new Map();
    for (const { canonical, run } of verified) {
      if (seen.has(canonical)) {
        const representative = seen.get(canonical);
        refused.push({ label: run.label, reason: `Duplicate verified replay; counted once as ${JSON.stringify(representative || '(unnamed)')}.`.slice(0, MAX_REASON) });
      } else {
        seen.set(canonical, run.label);
        runs.push(run);
      }
    }
    refused.sort((a, b) => compare(a.label, b.label) || compare(a.reason, b.reason));
    const actors = {};
    for (const id of A.ORDER) actors[id] = emptyActor();
    const modes = {};
    const totals = { runs: runs.length, refused: refused.length, delivered: 0, turns: 0, actions: 0, sources: { scripted: 0, manual: 0 } };
    for (const run of runs) {
      for (const id of A.ORDER) {
        const from = run.perActor[id], to = actors[id];
        to.deliveries += from.deliveries; to.collects += from.collects;
        to.moves += from.moves; to.waits += from.waits;
        if (from.deliveries + from.collects + from.moves + from.waits > 0) to.runsAppeared++;
      }
      const mode = modes[run.mode] || (modes[run.mode] = { runs: 0, complete: 0, capped: 0, delivered: 0 });
      mode.runs++; mode.delivered += run.delivered;
      if (run.status === 'complete') mode.complete++;
      if (run.status === 'capped') mode.capped++;
      totals.delivered += run.delivered; totals.turns += run.turns; totals.actions += run.actions;
      totals.sources.scripted += run.sources.scripted; totals.sources.manual += run.sources.manual;
    }
    return Object.freeze({
      schema: SCHEMA,
      totals: Object.freeze(totals),
      runs: Object.freeze(runs.map((run) => Object.freeze(run))),
      refused: Object.freeze(refused.map((row) => Object.freeze(row))),
      actors: Object.freeze(actors),
      modes: Object.freeze(modes),
      boundaries: BOUNDARIES
    });
  }

  root.AgentworldLedger = Object.freeze({ SCHEMA, MAX_RUNS, MAX_LABEL, BOUNDARIES, tallyRun, tallyRuns, fingerprint });
})(globalThis);
