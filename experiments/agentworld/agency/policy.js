/* Behavioral agency experiment: deterministic local policy, not a model or a claim of free will. */
(function (root) {
  'use strict';
  const E = root.Agentworld;
  if (!E) throw new Error('Load the Agentworld engine before the agency policy.');
  const VERSION = 'builderwars.agentworld.agency.policy.v0.1';
  const SCHEMA = 'builderwars.agentworld.agency.v0.1';
  const MAX_ENERGY = 6, GOALS = ['help', 'explore', 'rest'];
  const PROFILES = [
    { id: 'amber-1', name: 'Mara', role: 'Builder', description: 'Usually delivers supplies; declines suggested exploration.',
      cycle: ['help', 'help', 'help', 'explore'], restAt: 1, accepts: ['help', 'rest'] },
    { id: 'tide-1', name: 'Kite', role: 'Scout', description: 'Usually explores; declines suggested delivery work.',
      cycle: ['explore', 'explore', 'explore', 'help'], restAt: 2, accepts: ['explore', 'rest'] },
    { id: 'amber-2', name: 'Moss', role: 'Steward', description: 'Helps with deliveries and recovers earlier than companions.',
      cycle: ['help', 'help', 'explore'], restAt: 3, accepts: ['help', 'rest'] },
    { id: 'tide-2', name: 'Rune', role: 'Wanderer', description: 'Alternates exploration and deliveries; open to every suggestion.',
      cycle: ['explore', 'help', 'explore', 'help', 'help'], restAt: 2, accepts: ['help', 'explore', 'rest'] }
  ];
  for (const p of PROFILES) { Object.freeze(p.cycle); Object.freeze(p.accepts); Object.freeze(p); }
  Object.freeze(PROFILES);
  const copy = (v) => JSON.parse(JSON.stringify(v));
  const fail = (message) => { throw new Error(message); };
  const same = (a, b) => E.canonical(a) === E.canonical(b);
  function keys(value, fields) {
    if (!value || typeof value !== 'object' || Array.isArray(value) ||
        ![Object.prototype, null].includes(Object.getPrototypeOf(value)) ||
        Reflect.ownKeys(value).length !== fields.length || fields.some((key) =>
          !Object.prototype.hasOwnProperty.call(value, key) || !('value' in Object.getOwnPropertyDescriptor(value, key)))) {
      fail('Unexpected or missing fields.');
    }
  }
  function config(input) {
    keys(input, ['seed', 'mode']);
    if (input.mode !== 'cooperative') fail('Agency supports cooperative worlds only.');
    return E.create(input).config;
  }
  function requestValue(value) {
    if (value !== null && !GOALS.includes(value)) fail('Suggestion must be null, help, explore, or rest.');
    return value;
  }
  function requestList(values) {
    if (!Array.isArray(values) || values.length > E.LIMIT ||
        Reflect.ownKeys(values).length !== values.length + 1) fail('Suggestion log must contain at most 240 turns.');
    for (let i = 0; i < values.length; i++) {
      if (!Object.getOwnPropertyDescriptor(values, String(i))?.hasOwnProperty('value')) fail('Suggestion log must be plain data.');
      requestValue(values[i]);
    }
  }
  // Reject values canonical JSON would omit (symbols, hidden fields, accessors), as well as cycles.
  function plainData(input) {
    let count = 0;
    function visit(value, depth) {
      if (++count > 25000 || depth > 12) fail('Session exceeds its data bounds.');
      if (value === null || typeof value === 'boolean' || Number.isSafeInteger(value)) return;
      if (typeof value === 'string' && value.length <= 512) return;
      if (!value || typeof value !== 'object') fail('Session must contain only bounded JSON data.');
      const array = Array.isArray(value), fields = Object.keys(value), own = Reflect.ownKeys(value);
      if (!([Object.prototype, null].includes(Object.getPrototypeOf(value)) || (array && Object.getPrototypeOf(value) === Array.prototype)) ||
          own.length !== fields.length + (array ? 1 : 0) || (array && (value.length > 1024 || fields.length !== value.length))) fail('Session must contain plain objects and dense arrays.');
      for (const field of fields) {
        if (!('value' in Object.getOwnPropertyDescriptor(value, field))) fail('Session accessors are not allowed.');
        visit(value[field], depth + 1);
      }
    }
    visit(input, 0);
  }
  function create(input) {
    const world = E.create(config(input));
    return { world, actors: PROFILES.map((p, i) => ({ id: p.id, energy: MAX_ENERGY,
      goal: p.cycle[0], visited: [`${world.agents[i].x},${world.agents[i].y}`], turnsTaken: 0, suggestion: null })),
      history: [], requests: [] };
  }
  function explore(world, actor) {
    const body = world.agents.find((a) => a.id === actor.id), visited = new Set(actor.visited), targets = [];
    for (let x = 0; x < E.SIZE; x++) for (let y = 0; y < E.SIZE; y++) {
      if (!visited.has(`${x},${y}`)) targets.push({ x, y });
    }
    const distance = (p) => Math.abs(body.x - p.x) + Math.abs(body.y - p.y);
    targets.sort((a, b) => distance(a) - distance(b) || a.x - b.x || a.y - b.y);
    if (!targets.length) return E.scripted(world);
    const target = targets[0];
    const direction = target.x > body.x ? 'east' : target.x < body.x ? 'west' : target.y > body.y ? 'south' : 'north';
    return E.legal(world).find((action) => action.direction === direction);
  }
  // Only internal, reconstructed sessions reach this transition. No caller-owned object is changed.
  function transition(session, request) {
    if (session.world.status !== 'running') fail('World is finished; start a new run.');
    const next = session, id = E.active(next.world);
    const actor = next.actors.find((a) => a.id === id), body = next.world.agents.find((a) => a.id === id);
    const profile = PROFILES.find((p) => p.id === id), energyBefore = actor.energy;
    let response = 'none', explanation = '';
    if (request !== null) {
      let refusal = '';
      if (actor.energy <= 1 && request !== 'rest') refusal = 'recovery takes priority';
      else if (body.carry && request !== 'help' && !(actor.energy <= 1 && request === 'rest')) refusal = 'delivery commitment takes priority';
      else if (!profile.accepts.includes(request)) refusal = 'profile prefers other suggestions';
      if (refusal) { response = 'declined'; explanation = `Declined ${request}: ${refusal}. `; }
      else {
        response = 'accepted'; actor.suggestion = { goal: request, turnsLeft: 3 };
        explanation = `Accepted ${request} for up to 3 own turns. `;
      }
    }
    let commitment, reason;
    if (actor.energy <= 1) {
      actor.goal = 'rest'; commitment = 'recovery'; reason = 'Energy at 1 or less: recovery overrides other goals.';
    } else if (body.carry) {
      actor.goal = 'help'; commitment = 'delivery'; reason = 'Carrying supply: return to base and deliver before changing projects.';
    } else if (actor.suggestion) {
      actor.goal = actor.suggestion.goal; commitment = 'suggestion';
      reason = `Following accepted ${actor.goal}; ${actor.suggestion.turnsLeft} own turns left including this one.`;
    } else {
      actor.goal = actor.energy <= profile.restAt ? 'rest' : profile.cycle[actor.turnsTaken % profile.cycle.length];
      commitment = 'initiative'; reason = actor.goal === 'rest' ? 'Self-chosen recovery at this profile\'s energy threshold.' : 'Self-chosen goal from this profile\'s preference cycle.';
    }
    if (actor.goal === 'explore' && actor.visited.length === E.SIZE * E.SIZE) {
      actor.goal = 'help'; reason = 'All cells already visited; helping with supplies instead.';
    }
    const action = actor.goal === 'rest' ? E.legal(next.world)[0] : actor.goal === 'explore' ? explore(next.world, actor) : E.scripted(next.world);
    next.world = E.step(next.world, action);
    actor.energy = action.type === 'wait' ? Math.min(MAX_ENERGY, actor.energy + 3) : actor.energy - 1;
    actor.turnsTaken++;
    const moved = next.world.agents.find((a) => a.id === id), cell = `${moved.x},${moved.y}`;
    if (!actor.visited.includes(cell)) actor.visited.push(cell);
    if (actor.suggestion) {
      actor.suggestion.turnsLeft--;
      if (actor.suggestion.turnsLeft === 0 || (actor.suggestion.goal === 'rest' && actor.energy === MAX_ENERGY)) actor.suggestion = null;
    }
    next.requests.push(request);
    next.history.push({ turn: action.turn, actor: id, goal: actor.goal, request, response,
      reason: explanation + reason, action, energyBefore, energyAfter: actor.energy, commitment });
    return next;
  }
  function reconstruct(input, requests) {
    requestList(requests);
    let session = create(input);
    for (let i = 0; i < requests.length; i++) session = transition(session, requests[i]);
    return session;
  }
  function checked(session) {
    keys(session, ['world', 'actors', 'history', 'requests']);
    plainData(session);
    if (!session.world || typeof session.world !== 'object') fail('Missing world.');
    const expected = reconstruct(session.world.config, session.requests);
    if (!same(session, expected)) fail('Session does not match its deterministic suggestion log.');
    return expected;
  }
  function advance(session, request = null) {
    requestValue(request);
    return transition(checked(session), request);
  }
  function pack(session) {
    const valid = checked(session);
    return { schema: SCHEMA, policy: VERSION, config: copy(valid.world.config), requests: copy(valid.requests),
      finalWorld: copy(valid.world), finalActors: copy(valid.actors) };
  }
  function verify(text) {
    const packet = E.parse(text);
    keys(packet, ['schema', 'policy', 'config', 'requests', 'finalWorld', 'finalActors']);
    if (packet.schema !== SCHEMA || packet.policy !== VERSION) fail('Unsupported agency replay or policy version.');
    const session = reconstruct(packet.config, packet.requests);
    if (!same(packet.finalWorld, session.world) || !same(packet.finalActors, session.actors)) fail('Agency replay does not match its claimed final state.');
    return session;
  }
  root.AgentworldAgency = Object.freeze({ VERSION, MAX_ENERGY, PROFILES, create, advance, pack, verify });
})(globalThis);
