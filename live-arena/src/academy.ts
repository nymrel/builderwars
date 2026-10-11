import { RULES, validateRules } from "./runtime";
import { freeAgents } from "./sharing";

// A quiet, numbered learning workspace in the existing green/lime palette.
// Content: run a baseline, inspect evidence, change a rule, connect a model.
// Interaction: explicit lesson actions, native disclosures and existing focus/hover feedback.
export const academyMarkup = `
  <p class="eyebrow">BUILDERWARS ACADEMY</p><h1>Play. Inspect. Improve.</h1>
  <p class="subtitle">Run a free experiment, then change one thing.</p>
  <p id="academy-status" class="notice" role="status">No key or account needed for these exercises. Starting one replaces your current board; saved matches remain in your library.</p>
  <div class="lessons">
    <article><span>01</span><div><h2>Run your first comparison</h2>
      <p>Tactician searches two plies ahead. Wildcard picks a random legal move. Watch two Connect Four games, with each opponent starting once.</p>
      <button id="academy-pair" class="primary">Run free comparison ↗</button>
      <p class="muted">2 games · 80-ply cap per game · built-in opponents only. This clears connected contenders and their keys from the active matchup.</p>
    </div></article>
    <article><span>02</span><div><h2>Read the evidence</h2>
      <p>Check completed games, wins, draws and failures in Evals. Open Arena to replay the last game and export its evidence. Two games are practice, not a reliable ranking.</p>
      <button data-tab="evals">Inspect comparison</button>
      <details><summary>What would count as improvement?</summary>
        <p>Keep a baseline version. Change one strategy or harness setting. Compare both versions against the same opponents, rules and budgets, in both seats. Reserve separate test games that you did not use to make the change.</p>
        <p>Repeat enough games to estimate uncertainty, and include failures and cost. Promote a candidate only after it beats your acceptance threshold. This playground does not automatically train weights, rewrite agents or promote versions.</p>
      </details>
    </div></article>
    <article><span>03</span><div><h2>Create a small rule variant</h2>
      <p>Load a 3 × 4 board with gravity and three in a row to win. Review it in Forge, then select Create & play and Start match. Export the rules to reuse them.</p>
      <button id="academy-variant">Prepare free creator exercise</button>
      <p class="muted">Uses free built-ins. No arbitrary code runs. A new rule set is a different experiment, not evidence of improvement at Connect Four or chess.</p>
    </div></article>
    <article><span>04</span><div><h2>Bring a model or harness</h2>
      <p>A model generates decisions. An agent adds instructions and tools. A harness supplies the game state, validates moves and manages the run. Record versions for all three when you compare.</p>
      <button id="learn-connect">Connect models ↗</button>
      <details><summary>Connection and evaluation limits</summary>
        <p>OpenRouter uses your own API key and its current catalog of supported reasoning efforts. Your key stays in this tab’s memory and goes directly to OpenRouter. Free routes still require a key and may have limits. Effort labels are requests, not equal compute across providers.</p>
        <p>Your CORS-enabled HTTPS harness accepts <code>builderwars.move.v1</code> and returns a legal <code>move</code>. A supported local client can use the local bridge on your machine. This is not universal subscription sign-in.</p>
        <p>Fixed models do not learn weights just by playing more games. Engine-assisted chess, model-only chess and explicitly trained agents need separate comparisons. None of these exercises proves world-class performance.</p>
        <a href="https://github.com/nymrel/builderwars/blob/main/live-arena/README.md" target="_blank" rel="noopener">Harness and local runner guide ↗</a>
      </details>
    </div></article>
    <article><span>05</span><div><h2>Agent Readiness Check</h2>
      <p>Before a match, confirm a contender can answer real request shapes: ten fixed referee positions, one reply each, validated by the same rules a match uses. Invalid replies are reported and never retried or replaced by a bot.</p>
      <div class="settings-row"><label>Contender<select id="readiness-agent"></select></label><label>Position suite<select id="readiness-suite"><option value="tictactoe">Tic-tac-toe · 10 fixed positions</option><option value="nim">Nim · 10 fixed positions</option></select></label></div>
      <button id="academy-readiness" class="primary">Run readiness check ↗</button>
      <button id="readiness-stop" hidden>Stop check</button>
      <p id="readiness-status" class="notice" role="status" aria-live="polite">No model request is sent until you run a check. Built-in contenders answer locally; connected contenders use your own provider access.</p>
      <div id="readiness-output"></div>
      <details><summary>What a readiness receipt proves</summary>
        <p>Passing proves the contender returned a schema-valid, legal move for each fixed position within the time cap — protocol readiness only. It does not prove strategic strength, model identity, provider execution, or any ranking, and one suite is not a leaderboard. Timeouts are latency evidence, not strategy evidence.</p>
      </details>
      <p class="muted">Connected contenders are billed by your provider: 10 requests per run at your Tokens/move setting. Results stay in this tab until you download the receipt.</p>
    </div></article>
  </div>`;

export function freeAcademyRecipe(variant = false) {
  return {
    rules: variant ? validateRules({ kind: "custom", name: "Academy Three", rows: 3, cols: 4, connect: 3, gravity: true }) : { ...RULES.connect4 },
    agents: freeAgents(), moveLimit: 80, maxTokens: 2048, games: 2,
  };
}
