/* BuilderWars Agentworld experimental hive-memory ledger. Descriptive aggregation over verified replays only. */
(function (root) {
  'use strict';
  const A = root.Agentworld;
  if (!A) fail('Agentworld engine must load before the ledger.');
  const SCHEMA = 'builderwars.agentworld.hive-ledger.v0.1';
  const MAX_RUNS = 64, MAX_LABEL = 80, MAX_REFUSED = 64;
  const BOUNDARIES = Object.freeze([
    'Descriptive aggregate of the exact replays provided; not a ranking, rating, or evaluation.',
    'Only engine-verified replays are counted; every refused packet is listed with its reason.',
    'Actor source labels (scripted/manual) are self-declared and never attested here.',
    'Run fingerprints are non-cryptographic ordering identifiers, not security bindings.',
    'No network, storage, provider, or identity claims are made by this aggregate.'
  ]);

  function fail(message) { throw new Error(message); }

  function fingerprint(packet) {
    const text = A.canonical(packet);
    let hash = 0x811c9dc5;
    for (let i = 0; i < text.length; i++) {
      hash ^= text.charCodeAt(i);
      hash = Math.imul(hash, 0x01000193) >>> 0;
    }
    return hash.toString(16).padStart(8, '0');
  }

  function emptyActor() { return { deliveries: 0, collects: 0, moves: 0, waits: 0, runsAppeared: 0 }; }

  function tallyRun(entry) {
    const label = String((entry && entry.label) || '').slice(0, MAX_LABEL);
    const verified = A.verify(A.parse(String(entry.text)));
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
    return {
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
      fingerprint: fingerprint({ config: verified.config, actions: verified.actions })
    };
  }

  function tallyRuns(entries) {
    if (!Array.isArray(entries)) fail('Ledger input must be an array of {label, text} entries.');
    if (entries.length > MAX_RUNS) fail(`Ledger accepts at most ${MAX_RUNS} runs per aggregate.`);
    const runs = [], refused = [];
    for (const entry of entries) {
      const label = String((entry && entry.label) || '').slice(0, MAX_LABEL);
      try {
        runs.push(tallyRun({ label, text: entry.text }));
      } catch (error) {
        if (refused.length < MAX_REFUSED) refused.push({ label, reason: String(error.message || 'refused').slice(0, 160) });
      }
    }
    runs.sort((a, b) => a.seed - b.seed || (a.mode < b.mode ? -1 : a.mode > b.mode ? 1 : 0) ||
      (a.label < b.label ? -1 : a.label > b.label ? 1 : 0) || (a.fingerprint < b.fingerprint ? -1 : 1));
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
