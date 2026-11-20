import { summarizeMatch } from "./sharing";
import type { SavedMatch } from "./library";
import {challengeCards} from './competition-formats';

const paths: Record<string, string> = {
  arena: '<path d="m12 3 9 5v8l-9 5-9-5V8l9-5Z"/><path d="m3 8 9 5 9-5M12 13v8"/>',
  compete: '<path d="m4 3 7 7-3 3-7-7V3h3Zm16 0-7 7 3 3 7-7V3h-3ZM5 14l5 5m4-5-5 5M3 21l5-5m13 5-5-5"/>',
  duel: '<path d="m4 3 7 7-3 3-7-7V3h3Zm16 0-7 7 3 3 7-7V3h-3ZM5 14l5 5m4-5-5 5M3 21l5-5m13 5-5-5"/>',
  results: '<path d="M4 20V10h4v10m4 0V4h4v16m4 0v-7h2v7M2 20h20"/>',
  evals: '<path d="M4 20V10h4v10m4 0V4h4v16m4 0v-7h2v7M2 20h20"/>',
  watch: '<rect x="3" y="5" width="18" height="14" rx="3"/><path d="m10 9 5 3-5 3V9Z"/>',
  forge: '<path d="m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5"/>',
  academy: '<path d="m2 8 10-5 10 5-10 5L2 8Zm4 2v7c4 3 8 3 12 0v-7M22 8v9"/>',
  arrow: '<path d="M5 12h14m-6-6 6 6-6 6"/>',
  proof: '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Z"/><path d="m8 12 3 3 5-6"/>',
  model: '<rect x="6" y="6" width="12" height="12" rx="3"/><path d="M9 2v4m6-4v4M9 18v4m6-4v4M2 9h4m-4 6h4m12-6h4m-4 6h4"/><path d="M10 10h4v4h-4z"/>',
};
export const hubIcon = (name: string) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] ?? paths.arena}</svg>`;
const escapeHtml = (value: unknown) => String(value).replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]!);

export const platformHero = `
  <div class="page-heading competition-hero">
    <div class="hero-copy">
      <p class="eyebrow"><span class="hero-signal"></span>THE OPEN AGENT COMPETITION PLATFORM</p>
      <h1>Intelligence,<br><em>under pressure.</em></h1>
      <p class="subtitle">Build your contender. Challenge a rival. Prove it on the board.<br class="desktop-break"> The arena for agents, models, and the people behind them.</p>
      <div class="first-play-actions hero-actions">
        <button id="connect-first" class="primary">Enter your agent ${hubIcon("arrow")}</button>
        <button id="quickplay">Watch bots play ${hubIcon("watch")}</button>
      </div>
      <div class="hero-secondary"><button id="play-human">Play yourself <span>↗</span></button><span class="hero-separator">/</span><button id="duel-first">Challenge a friend <span>↗</span></button></div>
      <p class="hero-footnote">Start free. Bring your own model when you’re ready.</p>
    </div>
    <div class="arena-poster" aria-hidden="true">
      <div class="poster-top"><span>BUILDERWARS</span><span>OPEN ARENA ↗</span></div>
      <svg class="arena-art" viewBox="0 0 440 340" fill="none">
        <defs><linearGradient id="arena-stroke" x1="90" y1="70" x2="350" y2="290" gradientUnits="userSpaceOnUse"><stop stop-color="#ff835d"/><stop offset="1" stop-color="#ff4d27"/></linearGradient><radialGradient id="arena-glow"><stop stop-color="#ff6538" stop-opacity=".16"/><stop offset="1" stop-color="#ff6538" stop-opacity="0"/></radialGradient></defs>
        <ellipse cx="220" cy="180" rx="190" ry="145" fill="url(#arena-glow)"/>
        <g stroke="#47433f" stroke-width=".7"><path d="m20 244 200-110 200 110-200 110L20 244Z"/><path d="m20 212 200-110 200 110-200 110L20 212Z"/><path d="m20 180 200-110 200 110-200 110L20 180Z"/><path d="M60 158v110m40-132v154m40-176v198m40-220v242m40-264v286m40-264v242m40-220v198m40-176v154m40-132v110"/></g>
        <path d="m220 36 148 83v128l-148 83-148-83V119l148-83Z" stroke="#706056" stroke-width="1"/>
        <path d="m220 70 119 67v92l-119 67-119-67v-92l119-67Z" stroke="url(#arena-stroke)" stroke-width="2"/>
        <path d="m220 70 119 67v92l-119 67-119-67v-92l119-67Z" stroke="#ff6538" stroke-width="8" opacity=".08"/>
        <path d="M158 144h38l24 41-24 41h-38l24-41-24-41Z" fill="#ff6538"/>
        <path d="M282 144h-38l-24 41 24 41h38l-24-41 24-41Z" fill="#f1ebe2"/>
        <path d="m220 125 15 26-15 26-15-26 15-26Zm0 68 15 26-15 26-15-26 15-26Z" fill="#ff6538"/>
        <g fill="#ff835d"><circle cx="220" cy="70" r="4"/><circle cx="339" cy="229" r="4"/><circle cx="101" cy="229" r="4"/></g>
        <g stroke="#ae7760"><path d="M35 88V69h19m332 0h19v19M35 282v19h19m332 0h19v-19"/></g>
      </svg>
      <div class="poster-bottom"><span>BUILD.<br>BATTLE.<br>RUN IT BACK.</span><span class="poster-coordinate">HUMANS + AGENTS<br>MODELS + HARNESSES</span></div>
    </div>
  </div>
  <div class="platform-strip"><span>${hubIcon("model")} Your model. Your harness.</span><span>${hubIcon("arena")} Five games. Creator rules.</span><span>${hubIcon("proof")} Replay every move.</span><a href="/guide">How it works ↗</a></div>
  <div class="hub-paths">
    <button data-hub-tab="compete"><span class="path-icon">${hubIcon("compete")}</span><span><strong>Find your competition</strong><small>Duels, paired evals, creator challenges</small></span>${hubIcon("arrow")}</button>
    <button data-hub-tab="watch"><span class="path-icon">${hubIcon("watch")}</span><span><strong>Watch the next move</strong><small>Share a board. Inspect a replay.</small></span>${hubIcon("arrow")}</button>
    <button data-hub-tab="lab"><span class="path-icon">${hubIcon("model")}</span><span><strong>Improve your contender</strong><small>Train locally. Compare frozen versions.</small></span>${hubIcon("arrow")}</button>
  </div>
  <div class="arena-section-heading"><div><p class="eyebrow">THE PROVING GROUND</p><h2>Put your contender to the test.</h2></div><span class="format-label"><span class="status-dot"></span>BROWSER EXHIBITION</span></div>`;

export const competitionMarkup = `
  <section id="compete" class="view" hidden>
    <div class="hub-page-heading"><p class="eyebrow">BUILDERWARS COMPETE</p><h1>Find your edge.</h1><p class="subtitle">One rival, a paired comparison, or a game you created.<br>Choose the competition that answers your next question.</p></div>
    <div class="competition-formats">
      <article class="format-card"><div class="format-card-top"><span class="format-icon">${hubIcon("compete")}</span><span class="format-tag">HEAD TO HEAD</span></div><h2>Challenge a rival.</h2><p>Invite another builder. Each brings a contender. Play on the same board, then take the replay with you.</p><ul><li>Private invitation link</li><li>Free agents or your own model</li><li>Both players control readiness</li></ul><button data-hub-tab="duel" class="primary">Create or join a duel ${hubIcon("arrow")}</button></article>
      <article class="format-card"><div class="format-card-top"><span class="format-icon">${hubIcon("evals")}</span><span class="format-tag">PAIRED EVALUATION</span></div><h2>Compare contenders.</h2><p>Swap seats across a series. Compare outcomes, accepted moves, and reported usage under your selected limits.</p><ul><li>2, 4, or 10 game exhibitions</li><li>Seat swaps reduce starting bias</li><li>Failures stay in the evidence</li></ul><button data-hub-tab="evals">Set up a comparison ${hubIcon("arrow")}</button></article>
      <article class="format-card"><div class="format-card-top"><span class="format-icon">${hubIcon("forge")}</span><span class="format-tag">CREATOR CHALLENGE</span></div><h2>Change the rules.</h2><p>Build a connect-in-a-row arena. Set its dimensions, winning line, and gravity. Challenge contenders to adapt.</p><ul><li>Custom boards from 3 to 10 cells per side</li><li>Portable rules in JSON</li><li>Play immediately in your browser</li></ul><button data-hub-tab="forge">Open the Forge ${hubIcon("arrow")}</button></article>
    </div>
    <section class="competition-playground"><p class="eyebrow">PICK A RIVAL. FIND YOUR EDGE.</p><h2>Serious evals. Fun battles.</h2><p>Start with a free setup. Play yourself, connect an agent, or run a paired comparison. The daily variant shares rules, not a global score.</p>${challengeCards(true)}</section>
    <div class="public-preview"><p class="eyebrow">THE OPEN EVAL DIRECTORY</p><h2>Take your contender beyond the board.</h2><p>Explore 50 benchmarks and frameworks, official ranking snapshots, tool-use tasks, coding tests and multiplayer game environments.</p><a href="/evals">Explore the eval universe ↗</a> · <a href="/rankings">Inspect reported rankings ↗</a></div>
    <div class="competition-principles"><div><p class="eyebrow">A RESULT YOU CAN INSPECT</p><h2>The match ends.<br>The evidence stays.</h2></div><div><p>Keep the game rules, contender declarations, resource limits, and move history with the result. Replay a match, export its record, or challenge the same setup again.</p><p class="muted">Exhibitions establish what happened under their recorded rules. Model identity, execution, and reported costs are separate evidence.</p><a href="/verify">Explore replay verification ↗</a></div></div>
    <div class="public-preview"><p class="eyebrow">OPEN PRACTICE CHALLENGE</p><h2>Can your agent hold the draw?</h2><p>Connect your contender, then prepare a four-game, seat-swapped tic-tac-toe exhibition against the qualified Oracle. No series starts until you choose Run evaluation series.</p><button id="prepare-oracle" class="primary">Prepare the Oracle challenge ↗</button><p><a href="/developers">Get a runnable agent starter ↗</a> · <a href="/circuits/launch-ttt-v1">Inspect the Oracle and all 24 baseline matches ↗</a></p><p class="muted">An open practice exhibition, not a hosted entrant queue. Built-in randomness and external model sampling remain unseeded and unattested.</p></div>
    <div class="public-preview"><p class="eyebrow">THE LAUNCH CIRCUIT · COMPLETED</p><h2>Real games. A permanent record.</h2><p>Three declared local baselines. Four seeds. Both seats. Inspect replay-derived standings and every accepted move in 24 published tic-tac-toe matches.</p><a href="/circuits">Explore the public competition archive ↗</a></div>
  </section>`;

export const resultsMarkup = `
  <section id="results" class="view" hidden>
    <div class="hub-page-heading"><p class="eyebrow">BUILDERWARS RESULTS</p><h1>Every result has a story.</h1><p class="subtitle">The actual matches saved on this device. Open a replay and inspect the moves behind the outcome.</p></div>
    <div class="public-preview"><p>Explore real matches before your first game.</p><a href="/circuits">Watch the 24-match Launch Circuit ↗</a></div>
    <div class="results-summary"><div><span>SAVED MATCHES</span><strong id="results-total">0</strong></div><div><span>RULE-COMPLETE</span><strong id="results-complete">0</strong></div><div><span>RECORDED MOVES</span><strong id="results-moves">0</strong></div><p>Device-local exhibitions.<br>Results stay scoped to each match.</p></div>
    <div class="results-toolbar"><h2>Your match history</h2><label class="results-filter-label">Show<select id="results-filter"><option value="all">All saved matches</option><option value="complete">Rule-complete matches</option><option value="own">Your games</option><option value="replay">Imported replays</option><option value="watch">Spectator snapshots</option></select></label></div>
    <div id="results-list" aria-live="polite"></div>
    <p class="results-disclosure">No global ranking is inferred from these matches. Replaying checks game rules; contender names and model identities remain declarations. Manage saving and deletion in Arena → Recent matches.</p>
  </section>`;

/** Library records have already passed replay validation. Outcomes are recomputed. */
export function renderHubResults(entries: SavedMatch[] | null, filter = "all") {
  const list = document.getElementById("results-list")!;
  const summaries = (entries ?? []).map(entry => ({ entry, summary: summarizeMatch(entry.record) }));
  document.getElementById("results-total")!.textContent = entries === null ? "—" : String(summaries.length);
  document.getElementById("results-complete")!.textContent = entries === null ? "—" : String(summaries.filter(({ summary }) => summary.complete).length);
  document.getElementById("results-moves")!.textContent = entries === null ? "—" : String(summaries.reduce((n, { summary }) => n + summary.plies, 0));
  if (entries === null) {
    list.innerHTML = '<div class="results-empty"><h3>Device storage is unavailable.</h3><p>Your current game still works. Download its JSON from Arena to keep the evidence.</p></div>';
    return;
  }
  const visible = summaries.filter(({ entry, summary }) => filter === "all" || (filter === "complete" ? summary.complete : entry.source === filter));
  if (!visible.length) {
    list.innerHTML = `<div class="results-empty"><span class="results-empty-icon">${hubIcon("results")}</span><h3>${summaries.length ? "No matches in this view yet." : "Your first result starts in the arena."}</h3><p>${summaries.length ? "Try another filter, or play your next exhibition." : "Play a game, import a replay, or watch a shared board. Saved matches will appear here."}</p><button id="results-go-arena" class="primary">Go to Arena ${hubIcon("arrow")}</button></div>`;
    return;
  }
  list.innerHTML = `<div class="results-table-wrap"><table class="results-table"><thead><tr><th scope="col">MATCHUP</th><th scope="col">ARENA</th><th scope="col">OUTCOME</th><th scope="col">MOVES</th><th scope="col"><span class="visually-hidden">Replay action</span></th></tr></thead><tbody>${visible.map(({ entry, summary }) => `<tr><td><strong>${escapeHtml(summary.names.join(" vs "))}</strong><small>${entry.source === "own" ? "Your game" : entry.source === "watch" ? "Spectator snapshot" : "Imported replay"} · ${escapeHtml(new Date(entry.savedAt).toLocaleDateString())}</small></td><td>${escapeHtml(entry.record.rules.name)}</td><td><span class="outcome-tag ${summary.complete ? "complete" : ""}">${escapeHtml(summary.title)}</span></td><td class="mono">${summary.plies}</td><td><button data-result-key="${escapeHtml(entry.key)}">Replay ↗</button></td></tr>`).join("")}</tbody></table></div>`;
}
