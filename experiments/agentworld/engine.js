/* BuilderWars Agentworld experimental engine. No network, providers, or executable entrants. */
(function (root) {
  'use strict';
  const RULES = 'builderwars.agentworld.relay.v0.1';
  const REPLAY = 'builderwars.agentworld.replay.v0.1';
  const SIZE = 8, LIMIT = 240, MAX_BYTES = 131072;
  const ORDER = ['amber-1', 'tide-1', 'amber-2', 'tide-2'];
  const DIRS = { north: [0, -1], east: [1, 0], south: [0, 1], west: [-1, 0] };
  const copy = (v) => JSON.parse(JSON.stringify(v));
  function fail(message) { throw new Error(message); }
  function object(v) { return v !== null && typeof v === 'object' && !Array.isArray(v); }
  function keys(v, required) {
    if (!object(v) || Object.keys(v).length !== required.length ||
        required.some((k) => !Object.prototype.hasOwnProperty.call(v, k))) fail('Unexpected or missing fields.');
  }
  function config(v) {
    keys(v, ['seed', 'mode']);
    if (!Number.isSafeInteger(v.seed) || v.seed < 1 || v.seed > 4294967295) fail('Seed must be an integer from 1 to 4294967295.');
    if (!['cooperative', 'crew-race'].includes(v.mode)) fail('Unknown world mode.');
    return copy(v);
  }
  function rng(seed) {
    let x = seed >>> 0;
    return () => { x ^= x << 13; x ^= x >>> 17; x ^= x << 5; return (x >>> 0) / 4294967296; };
  }
  function create(input) {
    const c = config(input), random = rng(c.seed), candidates = [];
    for (let x = 2; x <= 3; x++) for (let y = 0; y < SIZE; y++) candidates.push([x, y]);
    for (let i = candidates.length - 1; i > 0; i--) {
      const j = Math.floor(random() * (i + 1));
      [candidates[i], candidates[j]] = [candidates[j], candidates[i]];
    }
    const supplies = candidates.slice(0, 4).flatMap(([x, y], i) => [
      { id: `s${i}a`, x, y, amount: 2 }, { id: `s${i}b`, x: 7 - x, y: 7 - y, amount: 2 }
    ]);
    return { rules: RULES, config: c, turn: 0, status: 'running',
      bases: [{ team: 'amber', x: 0, y: 3 }, { team: 'tide', x: 7, y: 4 }],
      agents: [
        { id: 'amber-1', team: 'amber', x: 0, y: 2, carry: 0 },
        { id: 'tide-1', team: 'tide', x: 7, y: 5, carry: 0 },
        { id: 'amber-2', team: 'amber', x: 0, y: 4, carry: 0 },
        { id: 'tide-2', team: 'tide', x: 7, y: 3, carry: 0 }
      ], supplies, scores: { amber: 0, tide: 0 } };
  }
  function active(state) { return ORDER[state.turn % ORDER.length]; }
  function remaining(state) { return state.supplies.reduce((n, s) => n + s.amount, 0) + state.agents.reduce((n, a) => n + a.carry, 0); }
  function legal(state, source = 'scripted') {
    if (!['scripted', 'manual'].includes(source)) fail('Unknown input source.');
    if (state.status !== 'running') return [];
    const a = state.agents.find((v) => v.id === active(state));
    const base = { turn: state.turn, actor: a.id, source };
    const actions = [{ ...base, type: 'wait' }];
    for (const [direction, [dx, dy]] of Object.entries(DIRS)) {
      if (a.x + dx >= 0 && a.x + dx < SIZE && a.y + dy >= 0 && a.y + dy < SIZE) actions.push({ ...base, type: 'move', direction });
    }
    if (a.carry === 0 && state.supplies.some((s) => s.x === a.x && s.y === a.y && s.amount > 0)) actions.push({ ...base, type: 'collect' });
    if (a.carry === 1 && state.bases.some((b) => b.team === a.team && b.x === a.x && b.y === a.y)) actions.push({ ...base, type: 'deliver' });
    return actions;
  }
  function canonical(v) {
    if (Array.isArray(v)) return '[' + v.map(canonical).join(',') + ']';
    if (object(v)) return '{' + Object.keys(v).sort().map((k) => JSON.stringify(k) + ':' + canonical(v[k])).join(',') + '}';
    return JSON.stringify(v);
  }
  function step(state, action) {
    keys(action, action && action.type === 'move' ? ['turn', 'actor', 'source', 'type', 'direction'] : ['turn', 'actor', 'source', 'type']);
    if (state.status !== 'running') fail('World is finished; start a new run.');
    if (!Number.isSafeInteger(action.turn) || action.turn !== state.turn) fail('Stale or invalid turn.');
    if (action.actor !== active(state)) fail('Only the active actor may act.');
    if (!legal(state, action.source).some((a) => canonical(a) === canonical(action))) fail('Action is not legal in this state.');
    const next = copy(state), a = next.agents.find((v) => v.id === action.actor);
    if (action.type === 'move') { const [dx, dy] = DIRS[action.direction]; a.x += dx; a.y += dy; }
    if (action.type === 'collect') { next.supplies.find((s) => s.x === a.x && s.y === a.y && s.amount > 0).amount--; a.carry = 1; }
    if (action.type === 'deliver') { a.carry = 0; next.scores[a.team]++; }
    next.turn++;
    if (remaining(next) === 0) next.status = 'complete';
    else if (next.turn >= LIMIT) next.status = 'capped';
    return next;
  }
  function scripted(state) {
    const actions = legal(state);
    if (!actions.length) fail('No active turn.');
    const immediate = actions.find((a) => ['deliver', 'collect'].includes(a.type));
    if (immediate) return immediate;
    const actor = state.agents.find((a) => a.id === active(state));
    const distance = (p) => Math.abs(actor.x - p.x) + Math.abs(actor.y - p.y);
    const targets = actor.carry ? state.bases.filter((b) => b.team === actor.team) : state.supplies.filter((s) => s.amount > 0);
    targets.sort((a, b) => distance(a) - distance(b) || a.x - b.x || a.y - b.y);
    if (!targets.length) return actions[0];
    const target = targets[0];
    const direction = target.x > actor.x ? 'east' : target.x < actor.x ? 'west' : target.y > actor.y ? 'south' : 'north';
    return actions.find((a) => a.direction === direction) || actions[0];
  }
  function run(input, actions) {
    if (!Array.isArray(actions) || actions.length > LIMIT) fail('Replay exceeds the turn limit.');
    let state = create(input);
    for (const action of actions) state = step(state, action);
    return state;
  }
  function pack(input, actions) {
    return { schema: REPLAY, config: config(input), actions: copy(actions), finalState: run(input, actions) };
  }
  function verify(packet) {
    keys(packet, ['schema', 'config', 'actions', 'finalState']);
    if (packet.schema !== REPLAY) fail('Unsupported replay version.');
    const state = run(packet.config, packet.actions);
    if (canonical(state) !== canonical(packet.finalState)) fail('Replay does not match its claimed final state.');
    return { config: copy(packet.config), actions: copy(packet.actions), state };
  }
  // Small bounded JSON parser: rejects duplicate keys, non-integer numbers and deep nesting.
  // The wire contract needs only safe integers, strings, arrays, objects, booleans and null.
  function parse(text) {
    if (typeof text !== 'string' || new TextEncoder().encode(text).length > MAX_BYTES) fail('JSON exceeds the 128 KiB limit.');
    let i = 0;
    const ws = () => { while (i < text.length && /[\t\n\r ]/.test(text[i])) i++; };
    function string() {
      const start = i++;
      while (i < text.length) {
        if (text[i] === '\\') { i += 2; continue; }
        if (text[i++] === '"') {
          const value = JSON.parse(text.slice(start, i));
          if (value.length > 128) fail('JSON string exceeds its bound.');
          return value;
        }
      }
      fail('Unterminated JSON string.');
    }
    function value(depth) {
      if (depth > 12) fail('JSON nesting limit exceeded.');
      ws();
      if (text[i] === '"') return string();
      if (text[i] === '{') {
        i++; ws(); const out = Object.create(null), seen = new Set();
        if (text[i] === '}') { i++; return out; }
        while (i < text.length) {
          ws(); if (text[i] !== '"') fail('Expected an object key.');
          const key = string();
          if (seen.has(key)) fail('Duplicate JSON key.');
          seen.add(key); ws(); if (text[i++] !== ':') fail('Expected a colon.');
          out[key] = value(depth + 1); ws();
          if (text[i] === '}') { i++; return out; }
          if (text[i++] !== ',') fail('Expected an object separator.');
        }
        fail('Unterminated JSON object.');
      }
      if (text[i] === '[') {
        i++; ws(); const out = [];
        if (text[i] === ']') { i++; return out; }
        while (i < text.length) {
          if (out.length >= 1024) fail('JSON array exceeds its bound.');
          out.push(value(depth + 1)); ws();
          if (text[i] === ']') { i++; return out; }
          if (text[i++] !== ',') fail('Expected an array separator.');
        }
        fail('Unterminated JSON array.');
      }
      for (const [token, result] of [['true', true], ['false', false], ['null', null]]) {
        if (text.startsWith(token, i)) { i += token.length; return result; }
      }
      const match = /-?(?:0|[1-9][0-9]*)/.exec(text.slice(i));
      if (!match || match.index !== 0) fail('Expected a JSON value.');
      i += match[0].length;
      const number = Number(match[0]);
      if (!Number.isSafeInteger(number)) fail('JSON numbers must be safe integers.');
      return number;
    }
    const result = value(0); ws(); if (i !== text.length) fail('Unexpected trailing JSON.');
    return result;
  }
  root.Agentworld = Object.freeze({ RULES, REPLAY, SIZE, LIMIT, MAX_BYTES, ORDER: Object.freeze(ORDER), create, active, remaining, legal, step, scripted, run, pack, verify, parse, canonical });
})(globalThis);
