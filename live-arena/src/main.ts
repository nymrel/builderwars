import "./style.css";
import {
  RULES,
  createGame,
  applyMove,
  legalMoves,
  moveLabel,
  square,
  validateRules,
  type Rules,
  type GameState,
} from "./runtime";
import {
  catalog,
  decide,
  publicAgent,
  supportedEfforts,
  type Agent,
  type Model,
} from "./models";
import { Broadcast } from "./broadcast";
import { MatchLibrary, canResume, type SavedMatch } from "./library";
import { makeSetup, encodeSetup, decodeSetup, safeReplay, summarizeMatch, resultImage,
  freeAgents, configuredAgents, type MatchSetup, type MatchSummary } from "./sharing";
import {
  replay,
  encodeReplay,
  decodeReplay,
  download,
  type RecordData,
  createProof,
  verifyProof,
  refereeManifest,
  PROOF_LIMIT,
} from "./runtime";

const $ = <T extends HTMLElement = HTMLElement>(id: string) =>
  document.getElementById(id) as T;
const esc = (s: unknown) =>
  String(s).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ]!,
  );
let agents: Agent[] = [
  {
    name: "Tactician",
    kind: "bot",
    model: "tactician",
    effort: "default",
    strategy: "",
    endpoint: "http://127.0.0.1:8765/move",
    key: "",
  },
  {
    name: "Wildcard",
    kind: "bot",
    model: "random",
    effort: "default",
    strategy: "",
    endpoint: "http://127.0.0.1:8765/move",
    key: "",
  },
];
let rules = { ...RULES.chess },
  state = createGame(rules),
  record: RecordData,
  models: Model[] = [],
  running = false,
  controller: AbortController | null = null,
  selected = -1,
  selectedSeat = 0,
  spectating = false,
  watchId = "",
  activeTab = "arena",
  runId = 0,
  broadcastLink = "",
  seriesRemaining = 0,
  seriesTotal = 0,
  seriesResults: RecordData[] = [],
  pace = 500;
const broadcast = new Broadcast();
let pending = false,
  replayPly: number | null = null,
  startingBroadcast = false;
let library: MatchLibrary | null = null;
let savedSource: SavedMatch["source"] = "own";
let proofOrigin: "browser_session" | "reverified_import" = "browser_session";
let proofExporting = false;
let pendingSetup: MatchSetup | null = null;
let summaryCache: { record: RecordData; plies: number; value: MatchSummary } | null = null;
let imageExporting = false;
let joinGeneration = 0;
let libraryRenderTimer: ReturnType<typeof setTimeout> | null = null;
try {
  library = new MatchLibrary(localStorage);
} catch {
  /* Storage is optional. */
}
function freshRecord(): RecordData {
  return {
    schema: "builderwars.exhibition.v1",
    id: crypto.randomUUID(),
    createdAt: new Date().toISOString(),
    rules: { ...rules },
    agents: agents.map(publicAgent),
    events: [],
    status: "Ready",
  };
}
record = freshRecord();
document.querySelector("#app")!.innerHTML = `
<header class="topbar"><a class="wordmark" href="/" aria-label="BuilderWars home"><img src="/mark.svg" alt="" width="30" height="30">BuilderWars<span class="alpha">PLAY ALPHA</span></a><div class="toplinks"><a href="https://github.com/nymrel/builderwars" target="_blank" rel="noopener">Open source ↗</a><button id="connections">Connect models <span>↗</span></button></div></header>
<div class="shell"><aside class="sidebar"><p class="nav-label">YOUR PLAYGROUND</p><nav aria-label="Main"><button data-tab="arena" class="active"><span>◈</span>Arena</button><button data-tab="forge"><span>⌘</span>Forge</button><button data-tab="evals"><span>▥</span>Evals</button><button data-tab="watch"><span>◉</span>Watch</button><button data-tab="academy"><span>◇</span>Academy</button></nav><div class="sidebar-bottom"><span class="status-dot"></span> Built for builders<p>By <a href="https://nymrel.com">Nymrel ↗</a></p><span class="muted">Agents. Humans. A level board.</span></div></aside>
<main><section id="arena" class="view"><div class="page-heading"><div><p class="eyebrow">THE NEXT MOVE IS YOURS</p><h1>Your agent. Your arena.</h1><p class="subtitle">Pick a game. Choose your contenders. Watch it unfold.</p></div><button id="quickplay" class="primary">Quick match <span>↗</span></button></div>
<div class="game-tabs" role="group" aria-label="Choose game">${Object.entries(
  RULES,
)
  .map(
    ([key, r], i) =>
      `<button data-game="${key}" class="${i === 0 ? "active" : ""}"><span>${["♞", "◉", "▦", "×"][i]}</span>${r.name}</button>`,
  )
  .join("")}<button id="create-game-shortcut">＋ Create game</button></div>
<div class="arena-layout"><div class="board-column"><div class="match-top"><span><span id="match-dot" class="status-dot"></span><strong id="game-title">Chess</strong> <span id="match-status">Ready to play</span></span><span id="ply">MOVE 00</span></div><div id="board" role="group" aria-label="Game board"></div><div class="board-toolbar"><button id="start" class="primary">▶ Start match</button><button id="step">Step</button><button id="reset">↻ Rematch</button><button id="flip">⇅ Flip</button><button id="share">Share replay ↗</button></div><p id="notice" class="notice" role="status" aria-live="polite">Free built-in opponents are ready. Connect a model whenever you like.</p><div class="telemetry"><div><span>PLIES</span><strong id="metric-moves">0</strong></div><div><span>MEAN LATENCY</span><strong id="metric-latency">—</strong></div><div><span>REPORTED TOKENS</span><strong id="metric-tokens">—</strong></div><div><span>REPORTED COST</span><strong id="metric-cost">$0.0000</strong></div></div><details class="match-settings"><summary>Match settings & move history</summary><div class="settings-row"><label>Move limit<input id="move-limit" type="number" value="80" min="2" max="400"></label><label>Tokens / move<input id="max-tokens" type="number" value="2048" min="256" max="16384" step="256"></label><label>Pace<select id="pace"><option value="500">Watchable</option><option value="100">Fast</option><option value="1200">Slow</option></select></label></div><p class="muted">Model usage is billed by your provider. Effort is requested; provider execution may vary. Results are exhibition evidence, not certified rankings.</p><div id="move-history"></div><button id="export">Download match JSON</button><label class="file-button">Import replay<input id="import" type="file" accept="application/json,.json"></label></details></div>
<aside class="match-panel"><div class="panel-heading"><h2>The contenders</h2><span>2 SEATS</span></div><div id="seats"></div><div class="panel-heading activity-title"><h2>At the board</h2><span id="feed-count">LIVE MOVES</span></div><div id="feed" class="feed"><div class="empty-feed"><span>⌁</span><p>Every move tells a story.</p><small>Start a match to see decisions, timing, and the position unfold.</small></div></div><button id="go-live" class="broadcast-button">◉ Broadcast this match</button><p id="broadcast-status" class="muted">Share a live board with up to 16 viewers. Keep this tab open.</p></aside></div></section>
<section id="forge" class="view" hidden><p class="eyebrow">BUILDERWARS FORGE</p><h1>Change the game.</h1><p class="subtitle">Create a connect-in-a-row game. Export its rules, then put your agents to work.</p><form id="creator" class="workspace-form"><label>Game name<input id="creator-name" value="Five in the Foundry" maxlength="48" required></label><div class="settings-row"><label>Rows<input id="creator-rows" type="number" min="3" max="10" value="8" required></label><label>Columns<input id="creator-cols" type="number" min="3" max="10" value="8" required></label><label>In a row to win<input id="creator-connect" type="number" min="3" max="10" value="5" required></label></div><label class="checkbox"><input id="creator-gravity" type="checkbox">Gravity: pieces fall to the bottom</label><div class="form-actions"><button class="primary" type="submit">Create & play ↗</button><button id="export-rules" type="button">Export game</button><label class="file-button">Import game<input id="import-rules" type="file" accept="application/json,.json"></label></div><p class="muted">Game definitions contain rules only. To build a new engine or evaluation adapter, start with the open creator SDK.</p><a href="https://github.com/nymrel/builderwars/tree/main/creator_sdk" target="_blank" rel="noopener">Explore the creator SDK ↗</a></form></section>
<section id="evals" class="view" hidden><p class="eyebrow">BUILDERWARS EVALS</p><h1>Run it back. Compare.</h1><p class="subtitle">A paired series swaps seats between games to reduce first-player advantage.</p><div class="workspace-form"><p>Uses the current game, contenders, move limit, and token limit from Arena.</p><label>Series length<select id="series-length"><option value="2">2 games · one pair</option><option value="4">4 games · two pairs</option><option value="10">10 games · five pairs</option></select></label><button id="run-series" class="primary">Run evaluation series ↗</button><p class="muted">A series may make up to games × move limit model requests. Built-in opponents are free. Model calls use your own provider account.</p><div id="series-results"><p>No series yet. Set your contenders, then run your first pair.</p></div><button id="export-series">Export evaluation</button></div></section>
<section id="watch" class="view" hidden><p class="eyebrow">BUILDERWARS WATCH</p><h1>Bring an audience.</h1><p class="subtitle">The board, moves, model labels and timing stream directly from the host’s browser.</p><div class="workspace-form"><button id="watch-broadcast" class="primary">Broadcast my match ↗</button><p id="watch-link">Start broadcasting to create a spectator link.</p><label>Join a broadcast<input id="join-link" placeholder="Paste a BuilderWars watch link"></label><button id="join">Watch match</button><button id="leave-watch" hidden>Leave spectator mode</button><div class="divider"></div><h2>Ready for your stream</h2><p>Open the clean board view and add it as an OBS browser or window source. Your model keys and connection settings stay outside the broadcast.</p><button id="clean-view">Open stream view ↗</button><p class="muted">Live board sharing uses PeerJS and WebRTC. Viewers receive your IP address as part of the peer connection. Some networks block these connections; replay links work after a match ends. Video publishing to Twitch or YouTube is controlled in your streaming app.</p></div></section>
<section id="academy" class="view" hidden><p class="eyebrow">BUILDERWARS ACADEMY</p><h1>Build. Play. Improve.</h1><div class="lessons"><article><span>01</span><div><h2>Start with a free match</h2><p>Quick match runs two built-in agents. Tactician looks ahead two plies; Wildcard chooses a legal move at random. Choose Human in a seat to play yourself.</p><button data-tab="arena">Enter Arena ↗</button></div></article><article><span>02</span><div><h2>Connect a frontier model</h2><p>Use your OpenRouter key to browse its current model catalog and supported reasoning efforts. Your key lives only in this tab’s memory and is sent directly to OpenRouter. Free-tier routes still require your own key and may have limits.</p><button id="learn-connect">Connect models ↗</button></div></article><article><span>03</span><div><h2>Bring your own harness</h2><p>Expose a CORS-enabled HTTPS endpoint accepting <code>builderwars.move.v1</code>. Return a legal <code>move</code> and an optional short public <code>comment</code>. Subscription clients run on your own machine through the local bridge.</p><pre>{ "move": "e2e4", "comment": "Control the center." }</pre><a href="https://github.com/nymrel/builderwars/blob/main/live-arena/README.md" target="_blank" rel="noopener">Harness & local runner guide ↗</a></div></article><article><span>04</span><div><h2>Evaluate the whole system</h2><p>Compare the same rules, move limits and token budgets. Swap seats. Repeat matches. Inspect invalid moves and latency alongside wins. A chess result measures this game and harness; it does not measure every model capability.</p><button data-tab="evals">Run a paired series ↗</button></div></article></div></section>
<footer><span>BuilderWars · An open playground by Nymrel</span><span>Play • Create • Replay</span></footer></main></div>
<dialog id="agent-dialog"><form id="agent-form"><div class="dialog-heading"><h2 id="agent-title">Connect a contender</h2><button id="close-dialog" type="button" aria-label="Close connections">×</button></div><label>Display name<input id="agent-name" maxlength="64" required></label><label>Connection<select id="agent-kind"><option value="bot">Built-in opponent · free</option><option value="human">Human · play on the board</option><option value="openrouter">OpenRouter · your models and key</option><option value="harness">Your harness / local subscription bridge</option></select></label><div id="bot-fields"><label>Opponent<select id="bot-model"><option value="tactician">Tactician · two-ply search</option><option value="random">Wildcard · random legal moves</option></select></label></div><div id="model-fields" hidden><div class="settings-row"><label>Find model<input id="model-search" placeholder="Search provider or model"></label><label class="checkbox"><input id="free-models" type="checkbox">Free routes</label></div><label>Model<select id="model-id"></select></label><p id="catalog-status" class="muted"></p><button id="refresh-models" type="button">Refresh catalog</button><label>Reasoning effort<select id="effort"><option>default</option></select></label><p id="model-price" class="muted"></p></div><div id="harness-fields" hidden><label>Move endpoint<input id="harness-url" type="url" placeholder="https://your-harness.example/move"></label><label>Model / harness label<input id="harness-model" maxlength="160" placeholder="Your configured model"></label><label>Requested effort<input id="harness-effort" maxlength="20" placeholder="default"></label><p class="muted">The endpoint must allow this site’s origin. Local bridge: http://127.0.0.1:8765/move. Its model is configured when you start it.</p></div><div id="key-fields" hidden><label id="key-label">Key / local connection token<input id="agent-key" type="password" autocomplete="off" spellcheck="false"></label><p class="muted">Kept in this tab’s memory. Never saved with profiles, replays or broadcasts.</p></div><label>Builder strategy<textarea id="strategy" maxlength="1000" rows="3" placeholder="A short strategy or system prompt for your agent"></textarea></label><p id="dialog-status" role="status"></p><div class="form-actions"><button type="submit" class="primary">Use contender ↗</button><button id="forget-key" type="button">Forget key</button><button id="export-agent" type="button">Export profile</button></div></form></dialog>`;

function notify(message: string) {
  $("notice").textContent = message;
}
// Visual thesis: a quiet scoreline and one board-led result image, no extra dashboard.
// Content: outcome, exact evidence level, then replay/share/runback actions.
// Interaction: reveal on pause/result, native setup dialog, existing button feedback.
$("notice").insertAdjacentHTML("beforebegin", `
  <section id="match-result" class="match-result" aria-labelledby="result-title" hidden>
    <p class="eyebrow">MATCH SNAPSHOT · EXHIBITION</p><h2 id="result-title"></h2>
    <p id="result-detail"></p><p id="result-evidence" class="muted"></p>
    <div class="result-actions"><button id="runback-free" class="primary">Run it back · free</button><button id="play-yourself">Play it yourself</button><button id="result-image">Download result image</button><button id="copy-caption">Copy result + replay</button><button id="copy-setup">Share this setup</button></div>
    <p class="muted">Images and links contain public names/model labels, not strategies, comments, keys or harness addresses. Attach the downloaded image to your post; a replay link alone has no match-specific social preview.</p>
  </section>`);
document.body.insertAdjacentHTML("beforeend", `
  <dialog id="setup-dialog" aria-labelledby="setup-title"><div class="dialog-heading"><h2 id="setup-title">Try this matchup</h2><button id="dismiss-setup" aria-label="Dismiss shared setup">×</button></div>
    <p id="setup-description"></p><p class="muted">This shared matchup has not started. Your current match stays unchanged until you choose an option. Free play uses built-in opponents. Preparing the original matchup clears connection keys and prompts; connect paid contenders yourself before starting.</p>
    <div class="result-actions"><button id="setup-free" class="primary">Play free</button><button id="setup-human">Play as human</button><button id="setup-configure">Prepare original matchup</button></div>
  </dialog>`);
function matchSummary() {
  if (!summaryCache || summaryCache.record !== record || summaryCache.plies !== record.events.length)
    summaryCache = { record, plies: record.events.length, value: summarizeMatch(record) };
  return summaryCache.value;
}
function renderResult() {
  $("match-result").hidden = record.events.length === 0 || running || pending;
  if (!record.events.length || running || pending) return;
  const summary = matchSummary();
  $("result-title").textContent = summary.title;
  $("result-detail").textContent = `${summary.record.rules.name} · ${summary.plies} plies · ${summary.reason}. Last move: ${summary.lastMove}. Reported decision time ${(summary.elapsedMs / 1000).toFixed(2)}s; accepted-move cost ${summary.cost === null ? "unknown" : `$${summary.cost.toFixed(4)}`}.`;
  $("result-evidence").textContent = `${summary.evidence}. One match is not a general model ranking.`;
  $("result-image").toggleAttribute("disabled", imageExporting);
}
function applySetup(setup: MatchSetup, mode: "free" | "human" | "configure") {
  stop();
  joinGeneration++;
  broadcast.close();
  broadcastLink = ""; watchId = ""; spectating = false;
  $("leave-watch").hidden = true; $("rejoin-watch").hidden = true; $("stop-broadcast").hidden = true;
  $("watch-link").textContent = "Start broadcasting to create a spectator link.";
  history.replaceState(null, "", location.pathname + location.search);
  rules = { ...setup.rules };
  agents = mode === "configure" ? configuredAgents(setup) : freeAgents(mode === "human");
  $<HTMLInputElement>("move-limit").value = String(setup.moveLimit);
  $<HTMLInputElement>("max-tokens").value = String(setup.maxTokens);
  reset(); tab("arena");
  if (mode === "configure") notify("Matchup prepared with no keys, prompts or harness address. Connect contenders, then explicitly start.");
  else { void play(); notify(mode === "human" ? "You play first. Pick a legal move on the board; Tactician is a free built-in opponent." : "New free exhibition. No paid model requests."); }
}
function runback(mode: "free" | "human") {
  if (running || pending) return;
  try {
    applySetup(makeSetup({ ...record, agents: freeAgents() }, numberInput("move-limit", 2, 400), numberInput("max-tokens", 256, 16384)), mode);
  } catch (error) { notify((error as Error).message); }
}
$("runback-free").onclick = () => runback("free");
$("play-yourself").onclick = () => runback("human");
$("dismiss-setup").onclick = () => $<HTMLDialogElement>("setup-dialog").close();
for (const [id, mode] of [["setup-free", "free"], ["setup-human", "human"], ["setup-configure", "configure"]] as const) {
  $(id).onclick = () => {
    if (!pendingSetup) return;
    const setup = pendingSetup;
    pendingSetup = null;
    $<HTMLDialogElement>("setup-dialog").close();
    applySetup(setup, mode);
  };
}
async function shareSetup() {
  try {
    const encoded = encodeSetup(makeSetup(record, numberInput("move-limit", 2, 400), numberInput("max-tokens", 256, 16384)));
    await navigator.clipboard.writeText(`${location.origin}/#setup=${encoded}`);
    notify("Setup link copied. Opening it shows a preview and never starts model calls. Keys, prompts and harness addresses are excluded.");
  } catch (error) { notify((error as Error).message); }
}
$("export").insertAdjacentHTML("afterend", '<button id="share-setup-settings">Share current setup</button>');
$("copy-setup").onclick = () => void shareSetup();
$("share-setup-settings").onclick = () => void shareSetup();
$("result-image").onclick = async () => {
  if (imageExporting) return;
  imageExporting = true; renderResult();
  const snapshot = structuredClone(record);
  try {
    const blob = await resultImage(snapshot);
    const url = URL.createObjectURL(blob), a = document.createElement("a");
    a.href = url; a.download = `builderwars-result-${snapshot.id}.png`; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    notify("Result image downloaded. Copy the replay caption to share alongside it. Nothing was posted.");
  } catch (error) { notify((error as Error).message); }
  finally { imageExporting = false; renderResult(); }
};
$("copy-caption").onclick = async () => {
  try {
    const snapshot = safeReplay(record), summary = summarizeMatch(snapshot);
    const encoded = await encodeReplay(snapshot);
    if (encoded.length > 60000) throw Error("Replay is too large for a link. Download match JSON instead.");
    const caption = `BuilderWars: ${summary.title} in ${summary.record.rules.name} (${summary.plies} plies).\nExhibition; rules replayed, model identity/execution not attested.\nReplay and try a free rematch: ${location.origin}/#replay=${encoded}`;
    await navigator.clipboard.writeText(caption);
    notify("Result caption and replay link copied. Review before posting; no post has been published.");
  } catch (error) { notify((error as Error).message); }
};
// Visual thesis: the board stays dominant in the existing green/lime workspace.
// Content: play free first; evidence is a secondary, plain-language disclosure.
// Interaction: native disclosure and existing focus/hover feedback, no ornamental motion.
$("quickplay").textContent = "Play free ↗";
$("quickplay").title = "Start a new game with two free built-in opponents. No model calls.";
document.querySelector(".page-heading .subtitle")!.textContent = "Play free with built-in opponents, or connect your own contender.";
$("notice").insertAdjacentHTML("afterend", `
  <details id="match-proof" class="match-settings">
    <summary>Verify this match</summary>
    <p class="muted">Reproduce moves and the result offline. Entrant names, models and usage are declarations—not independent identity, execution or billing proof.</p>
    <p id="proof-status" class="muted" role="status">Connect Four proof is available. Other games retain their standard replay export.</p>
    <button id="export-proof">Download proof (.jsonl)</button>
    <a id="download-verifier" class="file-button" download href="/${refereeManifest.verifier}">Download matching verifier</a>
    <label class="file-button">Verify a proof<input id="import-proof" type="file" accept=".jsonl,application/x-ndjson"></label>
    <p class="muted">Keep both downloads. With Node.js 22+, run <code>node verify-&lt;engine&gt;.mjs match.jsonl</code>. No packages or network needed. Older JSON replays remain supported; imported or recovered matches are marked as reverified.</p>
  </details>`);
// Visual thesis: retain the quiet green/lime workspace; history is a compact list.
// Content: one entry point, recent matches, exact retention, resume/replay actions.
// Interaction: native disclosure and existing button feedback; no new motion layer.
$("notice").insertAdjacentHTML(
  "afterend",
  `
  <p id="save-disclosure" class="muted">Played and watched matches save on this device. Manage saving in Recent matches.</p>
  <details id="match-library" class="match-settings">
    <summary>Recent matches <span id="library-count"></span></summary>
    <p class="muted">On this browser only · up to 20 matches for 30 days. Public strategies and comments are included; keys and endpoints are never saved. Shared-device users can turn saving off.</p>
    <label class="checkbox"><input id="save-matches" type="checkbox">Save recent matches on this device</label>
    <p id="library-status" class="muted" role="status"></p>
    <div id="library-list"></div>
    <button id="save-current-replay">Save current replay</button>
    <button id="forget-matches">Forget saved matches & turn saving off</button>
  </details>`,
);
$("join").insertAdjacentHTML(
  "afterend",
  '<button id="rejoin-watch" hidden>Reconnect to host</button>',
);

function libraryFailure() {
  $("save-disclosure").textContent =
    "Device saving is unavailable. Download a match to keep it.";
  $("library-status").textContent =
    "Browser storage is unavailable or full. Your current game still works; download its JSON to keep it.";
}
function saveCurrent() {
  if (!library) return;
  if (savedSource === "watch" && !watchId) return;
  try {
    const limit = Number($<HTMLInputElement>("move-limit").value);
    const saved = library.save(
      record,
      savedSource,
      Number.isInteger(limit) && limit >= 2 && limit <= 400 ? limit : 80,
      savedSource === "watch" ? watchId : "",
    );
    if (!saved && library.enabled() && record.events.length) {
      $("library-status").textContent =
        "Your saved games take priority. Download this replay or forget an older game to make room.";
      return;
    }
    if (!libraryRenderTimer)
      libraryRenderTimer = setTimeout(() => {
        libraryRenderTimer = null;
        renderLibrary();
      }, 150);
  } catch {
    libraryFailure();
  }
}
function renderLibrary() {
  if (!library) {
    libraryFailure();
    return;
  }
  try {
    const entries = library.list();
    $<HTMLInputElement>("save-matches").checked = library.enabled();
    $("save-disclosure").textContent = library.enabled()
      ? "Played and watched matches save on this device. Manage saving in Recent matches."
      : "Automatic saving is off on this device.";
    $("library-count").textContent = entries.length
      ? `· ${entries.length}`
      : "";
    $("library-status").textContent = library.enabled()
      ? "Games save after each accepted move. No account or cloud backup."
      : "Saving is off. Existing matches remain until you forget them.";
    $("library-list").innerHTML = entries.length
      ? entries
          .map(
            (entry, i) => `
      <article class="saved-match"><div><strong>${esc(entry.record.rules.name)}</strong>
      <small>${esc(entry.record.agents.map((a) => a.name).join(" vs "))}</small>
      <small>${entry.record.events.length} plies · ${esc(new Date(entry.savedAt).toLocaleString())} · ${entry.source === "watch" ? "Spectator snapshot" : entry.source === "replay" ? "Imported replay" : "Your game"}</small></div>
      <div class="saved-actions"><button data-saved-replay="${i}">Replay</button>${canResume(entry) ? `<button data-saved-resume="${i}">Resume</button>` : ""}<button data-saved-delete="${i}" aria-label="Forget ${esc(entry.record.rules.name)}">Forget</button></div></article>`,
          )
          .join("")
      : '<p class="muted">Your next played or watched match will appear here when saving is on.</p>';
    for (const action of ["replay", "resume", "delete"] as const) {
      document
        .querySelectorAll<HTMLButtonElement>(`[data-saved-${action}]`)
        .forEach((button) => {
          button.disabled = running || pending;
          button.onclick = () => {
            if (running || pending) return;
            const entry =
              entries[Number(button.getAttribute(`data-saved-${action}`))];
            try {
              if (action === "delete") {
                library!.remove(entry.key);
                renderLibrary();
              } else if (action === "resume") resumeSaved(entry);
              else {
                openReplay(replay(entry.record), false);
                tab("arena");
              }
            } catch (e) {
              notify((e as Error).message);
            }
          };
        });
    }
  } catch {
    libraryFailure();
  }
}
function resumeSaved(entry: SavedMatch) {
  if (!canResume(entry))
    throw Error(
      "This match is replay-only. Connected providers must be configured again in a new match.",
    );
  stop();
  joinGeneration++;
  broadcast.close();
  broadcastLink = "";
  watchId = "";
  seriesRemaining = 0;
  replayPly = null;
  spectating = false;
  savedSource = "own";
  const parsed = replay(entry.record);
  proofOrigin = "reverified_import";
  record = parsed.record;
  $("proof-status").textContent = "Recovered record. Any new proof is a reverified snapshot, not original engine or model provenance.";
  state = parsed.state;
  rules = state.rules;
  // Recover into a new record so two tabs never overwrite the same continuation.
  record.id = crypto.randomUUID();
  agents = record.agents.map((a) => ({ ...a, endpoint: "", key: "" }));
  record.status = "Recovered · paused";
  $<HTMLInputElement>("move-limit").value = String(entry.moveLimit);
  $("leave-watch").hidden = true;
  $("rejoin-watch").hidden = true;
  $("stop-broadcast").hidden = true;
  $("watch-link").textContent =
    "Start broadcasting to create a spectator link.";
  history.replaceState(null, "", location.pathname + location.search);
  selected = -1;
  render();
  renderLibrary();
  tab("arena");
  notify(
    "Recovered and paused. Start or Step to continue; no model requests were started.",
  );
}
$("save-matches").onchange = () => {
  try {
    library?.setEnabled($<HTMLInputElement>("save-matches").checked);
    renderLibrary();
  } catch {
    libraryFailure();
  }
};
$("forget-matches").onclick = () => {
  if (
    !window.confirm(
      "Forget saved matches on this browser and turn automatic saving off? Download anything you want to keep first.",
    )
  )
    return;
  try {
    library?.forget();
    renderLibrary();
  } catch {
    libraryFailure();
  }
};
$("save-current-replay").onclick = () => {
  if (!library?.enabled()) {
    notify("Turn on saving in Recent matches first.");
    return;
  }
  saveCurrent();
};
window.addEventListener("storage", () => {
  if (!libraryRenderTimer)
    libraryRenderTimer = setTimeout(() => {
      libraryRenderTimer = null;
      renderLibrary();
    }, 150);
});
document.querySelector(".telemetry div:last-child > span")!.textContent =
  "ACCEPTED MOVE COST";
$("move-limit").closest("details")!.querySelector("p")!.textContent =
  "Usage totals cover accepted moves only. Failed or cancelled requests may still incur charges. Set limits at your provider and check its billing. Effort is requested, not independently attested. Exhibitions are not certified rankings.";
$("notice").insertAdjacentHTML(
  "beforebegin",
  '<div id="replay-controls" hidden><label id="replay-label" for="replay-position">Replay position</label><input id="replay-position" type="range" min="0" value="0"><button id="replay-prev">← Previous</button><button id="replay-next">Next →</button></div>',
);
$("move-history").insertAdjacentHTML(
  "beforebegin",
  '<label>Human chess promotion<select id="promotion"><option value="q">Queen</option><option value="r">Rook</option><option value="b">Bishop</option><option value="n">Knight</option></select></label>',
);
$("harness-fields").insertAdjacentHTML(
  "beforeend",
  '<p class="muted">Local bridge: experimental. Tested with Chromium local-network permission; other browsers and individual subscription clients are not yet certified. Claude Code subscription execution is not offered.</p>',
);
$("strategy").insertAdjacentHTML(
  "afterend",
  '<small class="muted">Public builder strategy: included in exports, replay links and live broadcasts. Never paste secrets here.</small>',
);
$("watch-link").insertAdjacentHTML(
  "afterend",
  '<button id="stop-broadcast" hidden>Stop broadcasting</button>',
);
$("stop-broadcast").onclick = () => {
  broadcast.close();
  broadcastLink = "";
  $("stop-broadcast").hidden = true;
  $("go-live").textContent = "◉ Broadcast this match";
  $("watch-link").textContent = "Broadcast ended.";
  $("broadcast-status").textContent = "Not broadcasting.";
};
function seekReplay(ply: number) {
  replayPly = Math.max(0, Math.min(record.events.length, ply));
  state = createGame(record.rules);
  for (const e of record.events.slice(0, replayPly))
    state = applyMove(state, e.move);
  render();
}
$<HTMLInputElement>("replay-position").oninput = (e) =>
  seekReplay(Number((e.target as HTMLInputElement).value));
$("replay-prev").onclick = () => seekReplay((replayPly ?? 0) - 1);
$("replay-next").onclick = () => seekReplay((replayPly ?? 0) + 1);
function openReplay(parsed: ReturnType<typeof replay>, save = true) {
  stop();
  joinGeneration++;
  broadcast.close();
  broadcastLink = "";
  watchId = "";
  savedSource = "replay";
  proofOrigin = "reverified_import";
  $("proof-status").textContent = "Imported replay. Any new proof is a reverified snapshot, not original engine or model provenance.";
  $("rejoin-watch").hidden = true;
  history.replaceState(null, "", location.pathname + location.search);
  seriesRemaining = 0;
  rules = parsed.state.rules;
  state = parsed.state;
  record = parsed.record;
  replayPly = record.events.length;
  spectating = true;
  render();
  notify(
    "Every move verified. Use the replay slider to inspect the match. Leave spectator mode in Watch to play.",
  );
  $("leave-watch").hidden = false;
  if (save) saveCurrent();
}
function tab(name: string) {
  activeTab = name;
  document
    .querySelectorAll<HTMLElement>(".view")
    .forEach((v) => (v.hidden = v.id !== name));
  document
    .querySelectorAll("[data-tab]")
    .forEach((b) =>
      b.classList.toggle("active", b.getAttribute("data-tab") === name),
    );
}
document
  .querySelectorAll<HTMLButtonElement>("[data-tab]")
  .forEach((b) => (b.onclick = () => tab(b.dataset.tab!)));
let flipped = false;
const glyphs: Record<string, string> = {
  wk: "♔",
  wq: "♕",
  wr: "♖",
  wb: "♗",
  wn: "♘",
  wp: "♙",
  bk: "♚",
  bq: "♛",
  br: "♜",
  bb: "♝",
  bn: "♞",
  bp: "♟",
};
function render() {
  renderResult();
  document
    .querySelectorAll<HTMLButtonElement>(
      "[data-saved-replay], [data-saved-resume], [data-saved-delete]",
    )
    .forEach((button) => {
      button.disabled = running || pending;
    });
  const legal = legalMoves(state),
    rows = state.rules.rows,
    cols = state.rules.cols,
    indices = Array.from({ length: rows * cols }, (_, i) =>
      flipped ? rows * cols - 1 - i : i,
    );
  $("board").style.setProperty("--cols", String(cols));
  $("board").className = `board ${state.rules.kind}`;
  $("board").innerHTML = indices
    .map((i) => {
      const p = state.cells[i],
        coord = square(i, state),
        target = legal.some((m) =>
          state.rules.kind === "chess"
            ? selected >= 0 &&
              m.startsWith(square(selected, state)) &&
              m.slice(2, 4) === coord
            : state.rules.kind === "checkers"
              ? selected >= 0 &&
                m.startsWith(square(selected, state) + "-") &&
                m.split("-").at(-1) === coord
              : state.rules.gravity
                ? Number(m) === i % cols
                : Number(m) === i,
        ),
        last = record.events.at(-1)?.move || "",
        highlight =
          state.rules.kind === "chess"
            ? last.startsWith(coord) || last.slice(2, 4) === coord
            : state.rules.kind === "checkers"
              ? last.split("-").includes(coord)
              : false;
      const piece =
        state.rules.kind === "chess"
          ? glyphs[p] || ""
          : p
            ? `<span class="disc ${p.toLowerCase() === "w" ? "white" : "black"}">${p === p.toUpperCase() ? "♛" : ""}</span>`
            : "";
      return `<button data-cell="${i}" class="cell ${(Math.floor(i / cols) + (i % cols)) % 2 ? "dark" : "light"} ${selected === i ? "selected" : ""} ${highlight ? "last" : ""} ${target ? "target" : ""}" aria-label="${esc(coord)} ${esc(p || "empty")}" ${spectating || (running && agents[state.turn].kind !== "human") ? "disabled" : ""}>${piece}<span class="coord">${coord}</span></button>`;
    })
    .join("");
  document
    .querySelectorAll<HTMLButtonElement>("[data-cell]")
    .forEach((b) => (b.onclick = () => humanClick(Number(b.dataset.cell))));
  $("game-title").textContent = state.rules.name;
  $("ply").textContent = `PLY ${String(state.moves.length).padStart(2, "0")}`;
  $("match-status").textContent = state.over
    ? state.winner === null
      ? "Draw"
      : `${record.agents[state.winner].name} wins`
    : running
      ? `${record.agents[state.turn].name} ${agents[state.turn].kind === "human" ? "to move" : "is thinking"}`
      : record.status;
  $("match-dot").classList.toggle("pulsing", running);
  $("start").textContent = running ? "Ⅱ Pause" : "▶ Start match";
  $("start").toggleAttribute(
    "disabled",
    spectating || state.over || (pending && !running),
  );
  $("step").toggleAttribute(
    "disabled",
    spectating || running || pending || state.over,
  );
  $("quickplay").toggleAttribute("disabled", spectating || pending || running);
  $("export-proof").toggleAttribute("disabled", rules.kind !== "connect4" || proofExporting);
  $("reset").toggleAttribute("disabled", spectating);
  $("replay-controls").hidden = replayPly === null;
  $<HTMLInputElement>("replay-position").max = String(record.events.length);
  $<HTMLInputElement>("replay-position").value = String(
    replayPly ?? record.events.length,
  );
  $("replay-label").textContent =
    `Replay: ${replayPly ?? 0} / ${record.events.length} plies`;
  ["move-limit", "max-tokens"].forEach(
    (id) =>
      ($<HTMLInputElement>(id).disabled = running || pending || spectating),
  );
  $("seats").innerHTML = record.agents
    .map(
      (a, i) =>
        `<button class="seat ${state.turn === i && !state.over ? "on-turn" : ""}" data-seat="${i}" ${spectating || running ? "disabled" : ""}><span class="avatar ${i ? "dark-avatar" : ""}">${a.kind === "human" ? "You" : a.kind === "bot" ? "BW" : a.kind === "openrouter" ? "AI" : "{ }"}</span><span><strong>${esc(a.name)}</strong><small>${esc(a.kind === "bot" ? "Built-in · free" : a.kind === "human" ? "Human player" : a.model || "Choose model")}</small><small>${i === 0 ? "White / first" : "Black / second"}${a.kind === "openrouter" ? ` · ${esc(a.effort)} effort` : ""}</small></span><span class="seat-edit">↗</span></button>`,
    )
    .join("");
  document
    .querySelectorAll<HTMLButtonElement>("[data-seat]")
    .forEach((b) => (b.onclick = () => openAgent(Number(b.dataset.seat))));
  $("metric-moves").textContent = String(record.events.length);
  $("metric-latency").textContent = record.events.length
    ? `${(record.events.reduce((sum, e) => sum + e.elapsed, 0) / record.events.length / 1000).toFixed(2)}s`
    : "—";
  const tokens = record.events.filter((e) => e.tokens !== null);
  $("metric-tokens").textContent = tokens.length
    ? String(tokens.reduce((sum, e) => sum + e.tokens!, 0))
    : "—";
  $("metric-cost").textContent = record.events.some((e) => e.cost === null)
    ? "Unknown"
    : `$${record.events.reduce((sum, e) => sum + (e.cost || 0), 0).toFixed(4)}`;
  if (record.events.length)
    $("feed").innerHTML = record.events
      .slice(-30)
      .reverse()
      .map(
        (e) =>
          `<article class="feed-item"><span class="feed-ply">${String(e.ply).padStart(2, "0")}</span><div><strong>${esc(record.agents[e.seat].name)} <span>${esc(e.label)}</span></strong><p>${esc(e.comment || "Move accepted.")}</p><small>${(e.elapsed / 1000).toFixed(2)}s · ${esc(e.model)}</small></div></article>`,
      )
      .join("");
  else
    $("feed").innerHTML =
      '<div class="empty-feed"><span>⌁</span><p>Every move tells a story.</p><small>Start a match to see decisions, timing, and the position unfold.</small></div>';
  $("move-history").textContent = record.events
    .map((e) => `${e.ply}. ${e.label}`)
    .join("  ");
  document.querySelectorAll<HTMLButtonElement>("[data-game]").forEach((b) => {
    b.disabled = running || spectating;
    b.classList.toggle("active", b.dataset.game === rules.kind);
  });
}
function stop(message = "Paused") {
  running = false;
  controller?.abort();
  controller = null;
  pending = false;
  runId++;
  record.status = message;
  render();
  broadcast.publish(record);
  if (!spectating) saveCurrent();
}
function reset(preserveSeries = false) {
  if (!preserveSeries) seriesRemaining = 0;
  stop("Ready");
  replayPly = null;
  state = createGame(rules);
  record = freshRecord();
  savedSource = "own";
  proofOrigin = "browser_session";
  $("proof-status").textContent = "Connect Four proof is available. Other games retain their standard replay export.";
  selected = -1;
  render();
  notify("Ready. Start a match or click Step for one move.");
  broadcast.publish(record);
  renderLibrary();
}
function numberInput(id: string, min: number, max: number) {
  const n = Number($<HTMLInputElement>(id).value);
  if (!Number.isInteger(n) || n < min || n > max)
    throw Error(`Choose ${id.replaceAll("-", " ")} between ${min} and ${max}.`);
  return n;
}
function commit(
  move: string,
  details: {
    comment: string;
    elapsed: number;
    model: string;
    tokens: number | null;
    cost: number | null;
  },
) {
  const label = moveLabel(move, state),
    seat = state.turn;
  state = applyMove(state, move);
  record.events.push({
    ...details,
    move,
    ply: state.moves.length,
    seat,
    label,
  });
  selected = -1;
  record.status = state.over ? state.reason : "Playing";
  render();
  broadcast.publish(record);
  saveCurrent();
  if (state.over)
    notify(
      `${state.reason}. ${state.winner === null ? "Draw." : record.agents[state.winner].name + " wins."}`,
    );
}
async function oneMove() {
  if (
    pending ||
    spectating ||
    state.over ||
    agents[state.turn].kind === "human"
  )
    return;
  if (state.moves.length >= numberInput("move-limit", 2, 400))
    throw Error("Exhibition move limit reached. Start a rematch.");
  const id = runId,
    config = agents[state.turn],
    tokens = numberInput("max-tokens", 256, 16384);
  controller = new AbortController();
  pending = true;
  render();
  try {
    const decision = await decide(
      state,
      config,
      tokens,
      controller.signal,
      models,
    );
    if (id !== runId) return;
    commit(decision.move, decision);
  } finally {
    if (id === runId) {
      pending = false;
      controller = null;
      render();
    }
  }
}
async function play() {
  if (spectating || state.over) return;
  if (running) {
    seriesRemaining = 0;
    stop();
    return;
  }
  if (pending) return;
  let moveLimit: number;
  try {
    moveLimit = numberInput("move-limit", 2, 400);
    numberInput("max-tokens", 256, 16384);
  } catch (e) {
    notify((e as Error).message);
    return;
  }
  running = true;
  const id = ++runId;
  record.status = "Playing";
  render();
  broadcast.publish(record);
  while (running && id === runId && !state.over) {
    if (state.moves.length >= moveLimit) {
      running = false;
      record.status = "Move limit reached";
      broadcast.publish(record);
      saveCurrent();
      notify(
        "Exhibition move limit reached. Export this record or start a rematch.",
      );
      break;
    }
    if (agents[state.turn].kind === "human") {
      notify(`${agents[state.turn].name}: choose a piece and destination.`);
      return;
    }
    try {
      await oneMove();
    } catch (e) {
      if (id !== runId) return;
      seriesRemaining = 0;
      stop("Connection or move error");
      notify(
        (e as Error).name === "TimeoutError"
          ? "Model timed out after 120 seconds. The match is paused."
          : (e as Error).message,
      );
      return;
    }
    await new Promise((r) => setTimeout(r, pace));
  }
  if (id === runId) {
    running = false;
    render();
    renderLibrary();
    if (seriesRemaining > 0) finishSeriesGame();
  }
}
function humanClick(i: number) {
  if (
    pending ||
    spectating ||
    state.over ||
    agents[state.turn].kind !== "human"
  )
    return;
  try {
    if (state.moves.length >= numberInput("move-limit", 2, 400)) {
      notify("Move limit reached. Start a rematch.");
      return;
    }
  } catch (e) {
    notify((e as Error).message);
    return;
  }
  const legal = legalMoves(state),
    coord = square(i, state);
  let move: string | undefined;
  if (state.rules.kind === "chess" || state.rules.kind === "checkers") {
    if (selected >= 0) {
      const from = square(selected, state);
      const candidates = legal.filter((m) =>
        state.rules.kind === "chess"
          ? m.startsWith(from) && m.slice(2, 4) === coord
          : m.startsWith(from + "-") && m.split("-").at(-1) === coord,
      );
      move =
        candidates.find((m) =>
          m.endsWith($<HTMLSelectElement>("promotion").value),
        ) || candidates[0];
    }
    if (!move) {
      selected = i;
      render();
      return;
    }
  } else move = String(state.rules.gravity ? i % state.rules.cols : i);
  if (!move || !legal.includes(move)) {
    notify("Choose one of the highlighted legal moves.");
    return;
  }
  commit(move, {
    comment: "Human move.",
    elapsed: 0,
    model: "human",
    tokens: null,
    cost: 0,
  });
  if (state.over) {
    running = false;
    render();
  } else if (running) {
    running = false;
    void play();
  }
}
$("start").onclick = () => void play();
$("quickplay").onclick = () => {
  if (running || pending || spectating) return;
  agents = freeAgents();
  seriesRemaining = 0;
  reset();
  void play();
};
$("step").onclick = async () => {
  if (running || spectating || state.over) return;
  try {
    await oneMove();
  } catch (e) {
    if ((e as Error).name !== "AbortError") notify((e as Error).message);
  }
};
$("reset").onclick = () => {
  seriesRemaining = 0;
  reset();
};
$("flip").onclick = () => {
  flipped = !flipped;
  render();
};
document.querySelectorAll<HTMLButtonElement>("[data-game]").forEach(
  (b) =>
    (b.onclick = () => {
      if (running || spectating) return;
      rules = { ...RULES[b.dataset.game!] };
      reset();
    }),
);
$<HTMLSelectElement>("pace").onchange = (e) => {
  pace = Number((e.target as HTMLSelectElement).value);
};
$("connections").onclick = () => openAgent(0);
$("learn-connect").onclick = () => openAgent(0);
$("create-game-shortcut").onclick = () => tab("forge");
function openAgent(seat: number) {
  if (pending || running || spectating) {
    notify("Pause the match before editing contenders.");
    tab("arena");
    return;
  }
  selectedSeat = seat;
  const a = agents[seat];
  $("agent-title").textContent = `${seat === 0 ? "White" : "Black"} contender`;
  $<HTMLInputElement>("agent-name").value = a.name;
  $<HTMLSelectElement>("agent-kind").value = a.kind;
  $<HTMLSelectElement>("bot-model").value =
    a.model === "random" ? "random" : "tactician";
  $<HTMLInputElement>("agent-key").value = a.key;
  $<HTMLInputElement>("harness-url").value = a.endpoint;
  $<HTMLInputElement>("harness-model").value = a.model;
  $<HTMLInputElement>("harness-effort").value = a.effort;
  $<HTMLTextAreaElement>("strategy").value = a.strategy;
  $("dialog-status").textContent = "";
  $<HTMLInputElement>("model-search").value = "";
  $<HTMLInputElement>("free-models").checked = false;
  connectionFields();
  $<HTMLDialogElement>("agent-dialog").showModal();
}
function connectionFields() {
  const kind = $<HTMLSelectElement>("agent-kind").value;
  $("bot-fields").hidden = kind !== "bot";
  $("model-fields").hidden = kind !== "openrouter";
  $("harness-fields").hidden = kind !== "harness";
  $("key-fields").hidden = !["openrouter", "harness"].includes(kind);
  if (kind === "openrouter") {
    if (!models.length) void loadModels();
    else filterModels();
  }
}
$<HTMLSelectElement>("agent-kind").onchange = () => {
  $<HTMLInputElement>("agent-key").value = "";
  connectionFields();
};
$<HTMLInputElement>("harness-url").oninput = () => {
  $<HTMLInputElement>("agent-key").value = "";
};
async function loadModels() {
  $("catalog-status").textContent = "Loading current model catalog…";
  try {
    models = await catalog(AbortSignal.timeout(15000));
    $("catalog-status").textContent =
      `${models.length} models from OpenRouter. Availability depends on your account.`;
    filterModels();
  } catch (e) {
    $("catalog-status").textContent = (e as Error).message;
  }
}
function filterModels() {
  const q = $<HTMLInputElement>("model-search").value.toLowerCase(),
    free = $<HTMLInputElement>("free-models").checked,
    prior =
      $<HTMLSelectElement>("model-id").value || agents[selectedSeat].model;
  const available = models.filter(
    (m) =>
      (!q || (m.id + " " + m.name).toLowerCase().includes(q)) &&
      (!free || (m.pricing?.prompt === "0" && m.pricing?.completion === "0")),
  );
  $("model-id").innerHTML = available
    .map((m) => `<option value="${esc(m.id)}">${esc(m.name)}</option>`)
    .join("");
  if (available.some((m) => m.id === prior))
    $<HTMLSelectElement>("model-id").value = prior;
  updateEfforts();
}
function updateEfforts() {
  const model = models.find(
      (m) => m.id === $<HTMLSelectElement>("model-id").value,
    ),
    efforts = supportedEfforts(model);
  $("effort").innerHTML = efforts
    .map(
      (e) =>
        `<option value="${e}">${e === "default" ? "Provider default" : e}</option>`,
    )
    .join("");
  if (efforts.includes(agents[selectedSeat].effort))
    $<HTMLSelectElement>("effort").value = agents[selectedSeat].effort;
  $("model-price").textContent = model?.pricing
    ? `Catalog price per 1M tokens: $${(Number(model.pricing.prompt) * 1e6).toFixed(2)} input / $${(Number(model.pricing.completion) * 1e6).toFixed(2)} output. Additional provider charges may apply.`
    : "Choose a model.";
}
$("refresh-models").onclick = () => void loadModels();
$<HTMLInputElement>("model-search").oninput = filterModels;
$<HTMLInputElement>("free-models").onchange = filterModels;
$<HTMLSelectElement>("model-id").onchange = updateEfforts;
$("close-dialog").onclick = () => $<HTMLDialogElement>("agent-dialog").close();
$("forget-key").onclick = () => {
  agents[selectedSeat].key = "";
  $<HTMLInputElement>("agent-key").value = "";
  $("dialog-status").textContent = "Key removed from this contender.";
};
$<HTMLFormElement>("agent-form").onsubmit = (e) => {
  e.preventDefault();
  const kind = $<HTMLSelectElement>("agent-kind").value as Agent["kind"];
  const a: Agent = {
    name: $<HTMLInputElement>("agent-name").value.trim() || "Contender",
    kind,
    model:
      kind === "bot"
        ? $<HTMLSelectElement>("bot-model").value
        : kind === "openrouter"
          ? $<HTMLSelectElement>("model-id").value
          : kind === "human"
            ? "human"
            : $<HTMLInputElement>("harness-model").value,
    effort:
      kind === "openrouter"
        ? $<HTMLSelectElement>("effort").value
        : kind === "harness"
          ? $<HTMLInputElement>("harness-effort").value || "default"
          : "default",
    key: $<HTMLInputElement>("agent-key").value.trim(),
    endpoint: $<HTMLInputElement>("harness-url").value,
    strategy: $<HTMLTextAreaElement>("strategy").value,
  };
  if (kind === "openrouter" && (!a.model || !a.key)) {
    $("dialog-status").textContent =
      "Choose a model and add your OpenRouter key.";
    return;
  }
  agents[selectedSeat] = a;
  $<HTMLDialogElement>("agent-dialog").close();
  reset();
};
$("export-agent").onclick = () =>
  download("builderwars-agent.json", publicAgent(agents[selectedSeat]));
$("export").onclick = () => download(`builderwars-${record.id}.json`, record);
$("export-proof").onclick = async () => {
  if (rules.kind !== "connect4" || proofExporting) return;
  const snapshot = structuredClone(record);
  const origin = proofOrigin;
  proofExporting = true;
  render();
  try {
    const limit = numberInput("move-limit", 2, 400);
    const text = await createProof(snapshot, refereeManifest.digest, limit, origin);
    const verified = await verifyProof(text, refereeManifest.digest);
    const url = URL.createObjectURL(new Blob([text], { type: "application/x-ndjson" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `builderwars-${snapshot.id}.jsonl`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    if (record.id === snapshot.id) $("proof-status").textContent = `${verified.state.over ? "Completed result" : "Incomplete snapshot"} reproduced at ${snapshot.events.length} plies. Keep the matching verifier. Model identity and execution are not attested.`;
  } catch (error) {
    $("proof-status").textContent = (error as Error).message;
  } finally {
    proofExporting = false;
    render();
  }
};
$<HTMLInputElement>("import-proof").onchange = async (event) => {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  const generation = runId;
  const matchId = record.id;
  const moveCount = record.events.length;
  try {
    if (running || pending) throw Error("Pause the current match before importing proof.");
    if (file.size > PROOF_LIMIT) throw Error("Proof exceeds size limit.");
    const text = new TextDecoder("utf-8", { fatal: true }).decode(await file.arrayBuffer());
    const verified = await verifyProof(text, refereeManifest.digest);
    if (generation !== runId || matchId !== record.id || moveCount !== record.events.length || running || pending) throw Error("The match changed during verification. Import again when paused.");
    if (verified.record.rules.kind !== "connect4") throw Error("This release supports Connect Four proof imports. Use the matching offline verifier for other formats.");
    openReplay(verified);
    $("proof-status").textContent = `${verified.record.status} · ${verified.record.events.length} plies reproduced by the matching referee. Names and models remain unverified declarations.`;
  } catch (error) {
    $("proof-status").textContent = (error as Error).message;
  } finally {
    input.value = "";
  }
};
async function shareReplay() {
  try {
    const encoded = await encodeReplay(safeReplay(record));
    if (encoded.length > 60000)
      throw Error(
        "This match is too large for a URL. Download and share its JSON file.",
      );
    const link = `${location.origin}/#replay=${encoded}`;
    await navigator.clipboard.writeText(link);
    notify(
      "Replay link copied. Public names, model labels and moves are included; strategies, comments, keys and endpoints are excluded.",
    );
  } catch (e) {
    notify((e as Error).message);
  }
}
$("share").onclick = () => void shareReplay();
async function readFile(input: HTMLInputElement) {
  const f = input.files?.[0];
  if (!f) throw Error("Choose a JSON file.");
  if (f.size > 350000) throw Error("File exceeds 350 KB.");
  return JSON.parse(await f.text());
}
$<HTMLInputElement>("import").onchange = async (e) => {
  try {
    openReplay(replay(await readFile(e.target as HTMLInputElement)));
  } catch (e) {
    notify((e as Error).message);
  }
};
function creatorRules() {
  return validateRules({
    kind: "custom",
    name: $<HTMLInputElement>("creator-name").value,
    rows: Number($<HTMLInputElement>("creator-rows").value),
    cols: Number($<HTMLInputElement>("creator-cols").value),
    connect: Number($<HTMLInputElement>("creator-connect").value),
    gravity: $<HTMLInputElement>("creator-gravity").checked,
  });
}
$<HTMLFormElement>("creator").onsubmit = (e) => {
  e.preventDefault();
  try {
    if (spectating)
      throw Error("Leave spectator mode before creating a match.");
    rules = creatorRules();
    reset();
    tab("arena");
  } catch (e) {
    notify((e as Error).message);
    tab("arena");
  }
};
$("export-rules").onclick = () => {
  try {
    download("builderwars-game.json", creatorRules());
  } catch (e) {
    notify((e as Error).message);
    tab("arena");
  }
};
$<HTMLInputElement>("import-rules").onchange = async (e) => {
  try {
    if (spectating) throw Error("Leave spectator mode first.");
    rules = validateRules(await readFile(e.target as HTMLInputElement));
    reset();
    tab("arena");
  } catch (e) {
    notify((e as Error).message);
    tab("arena");
  }
};
function finishSeriesGame() {
  seriesResults.push(structuredClone(record));
  seriesRemaining--;
  renderSeries();
  if (seriesRemaining > 0) {
    agents = [agents[1], agents[0]];
    reset(true);
    void play();
  } else {
    notify(
      `Evaluation complete: ${seriesResults.length} games. Open Evals for results.`,
    );
  }
}
function renderSeries() {
  $("series-results").innerHTML =
    `<h2>${seriesResults.length} / ${seriesTotal} games complete</h2><div class="results-table">${seriesResults
      .map((r, i) => {
        const s = replay(r).state;
        return `<p><span>Game ${i + 1}</span><strong>${esc(s.over ? (s.winner === null ? "Draw" : r.agents[s.winner].name + " wins") : "Move limit")}</strong><small>${r.events.length} plies</small></p>`;
      })
      .join(
        "",
      )}</div><p class="muted">Seat order is stored in every match. Model names are reported by the connected provider or harness. These are local exhibitions.</p>`;
}
$("run-series").onclick = () => {
  if (running || pending || spectating) {
    notify("Pause or leave the current match first.");
    tab("arena");
    return;
  }
  if (agents.some((a) => a.kind === "human")) {
    notify("Use two automated contenders for an evaluation series.");
    tab("arena");
    return;
  }
  seriesTotal = Number($<HTMLSelectElement>("series-length").value);
  seriesRemaining = seriesTotal;
  seriesResults = [];
  renderSeries();
  reset(true);
  tab("arena");
  void play();
};
$("export-series").onclick = () =>
  download("builderwars-evaluation.json", {
    schema: "builderwars.evaluation.v1",
    games: seriesResults,
    seatSwap: true,
  });
async function goLive() {
  if (startingBroadcast) return;
  if (spectating) {
    notify("Spectators cannot rebroadcast this match.");
    return;
  }
  startingBroadcast = true;
  try {
    if (!broadcastLink) {
      const id = await broadcast.host(
        (n) => {
          $("broadcast-status").textContent =
            `Broadcasting · ${n} connected viewer${n === 1 ? "" : "s"} · keep this tab open`;
          $("go-live").textContent = "◉ Copy live link";
        },
        (message) => {
          $("broadcast-status").textContent = message;
          broadcastLink = "";
        },
      );
      broadcastLink = `${location.origin}/#watch=${id}`;
      broadcast.publish(record);
      $("watch-link").textContent = broadcastLink;
      $("stop-broadcast").hidden = false;
      $("broadcast-status").textContent =
        "Broadcast started. Keep this tab open for viewers.";
    }
    await navigator.clipboard.writeText(broadcastLink);
    notify(
      "Live spectator link copied. Connection metadata, public strategies and moves are shared; keys stay in this tab.",
    );
  } catch (e) {
    notify((e as Error).message);
  } finally {
    startingBroadcast = false;
  }
}
$("go-live").onclick = () => void goLive();
$("watch-broadcast").onclick = () => {
  tab("arena");
  void goLive();
};
async function join(id: string) {
  if (!/^[a-zA-Z0-9_-]{1,100}$/.test(id)) throw Error("Invalid broadcast id.");
  stop();
  const generation = ++joinGeneration;
  seriesRemaining = 0;
  replayPly = null;
  broadcastLink = "";
  spectating = true;
  watchId = id;
  savedSource = "watch";
  proofOrigin = "reverified_import";
  $("proof-status").textContent = "Spectator record. Any new proof is a reverified snapshot, not original engine or model provenance.";
  history.replaceState(
    null,
    "",
    `${location.pathname}${location.search}#watch=${id}`,
  );
  $("rejoin-watch").hidden = false;
  // A prior unrelated game must never look like a new host's board.
  state = createGame(RULES.chess);
  rules = state.rules;
  record = freshRecord();
  record.status = "Waiting for host";
  let cached = false;
  try {
    const entry = library
      ?.list()
      .find((item) => item.source === "watch" && item.watchId === id);
    if (entry) {
      const parsed = replay(entry.record);
      state = parsed.state;
      rules = state.rules;
      record = parsed.record;
      replayPly = record.events.length;
      cached = true;
    }
  } catch {
    libraryFailure();
  }
  $("leave-watch").hidden = false;
  tab("arena");
  render();
  notify(
    cached
      ? "Saved spectator position · reconnecting to host. This is not live yet."
      : "Connecting to live match…",
  );
  await broadcast.watch(
    id,
    (parsed) => {
      if (generation !== joinGeneration) return;
      record = parsed.record;
      state = parsed.state;
      rules = state.rules;
      replayPly = null;
      render();
      notify("Watching live · moves are checked as they arrive");
      saveCurrent();
    },
    (message) => {
      if (generation === joinGeneration) notify(message);
    },
    () => {
      if (generation !== joinGeneration) return;
      if (record.events.length) replayPly = record.events.length;
      render();
      notify(
        record.events.length
          ? "Host offline or unreachable · showing the last received position, not a live board. Reconnect in Watch; if the host restarted, ask for their new link."
          : "Host offline or unreachable. If they restarted their broadcast, ask for the new link.",
      );
    },
  );
}
$("rejoin-watch").onclick = () => {
  if (watchId) void join(watchId).catch((e) => notify(e.message));
};
$("join").onclick = () => {
  try {
    const url = new URL($<HTMLInputElement>("join-link").value);
    const id = new URLSearchParams(url.hash.slice(1)).get("watch");
    if (!id) throw Error("Paste a link containing a broadcast id.");
    void join(id).catch((e) => notify(e.message));
  } catch (e) {
    tab("arena");
    notify((e as Error).message);
  }
};
$("leave-watch").onclick = () => {
  joinGeneration++;
  broadcast.close();
  spectating = false;
  watchId = "";
  broadcastLink = "";
  $("leave-watch").hidden = true;
  $("rejoin-watch").hidden = true;
  history.replaceState(null, "", location.pathname);
  reset();
  tab("arena");
};
$("clean-view").onclick = () => {
  const url = watchId
    ? `${location.origin}/?stream=1#watch=${watchId}`
    : broadcastLink
      ? broadcastLink.replace("/#", "/?stream=1#")
      : "";
  if (!url) {
    tab("arena");
    notify("Start broadcasting first, then open the stream view.");
    return;
  }
  window.open(url, "_blank", "noopener");
};
window.addEventListener("beforeunload", () => {
  controller?.abort();
  broadcast.close();
  agents.forEach((a) => (a.key = ""));
});
if (new URLSearchParams(location.search).get("stream") === "1")
  document.body.classList.add("stream-view");
render();
renderLibrary();
function loadFragment() {
  const hash = location.hash;
  const fragment = new URLSearchParams(hash.slice(1));
  pendingSetup = null;
  $<HTMLDialogElement>("setup-dialog").close();
  if (fragment.has("setup")) {
    try {
      pendingSetup = decodeSetup(fragment.get("setup")!);
      const seats = pendingSetup.entrants.map(a => a.kind === "harness" ? "Harness (connect locally)" : `${a.model} · ${a.effort} effort`).join(" vs ");
      $("setup-description").textContent = `${pendingSetup.rules.name} · ${pendingSetup.moveLimit} move limit · ${pendingSetup.maxTokens} requested tokens/move. ${seats}`;
      $<HTMLDialogElement>("setup-dialog").showModal();
    } catch (error) { pendingSetup = null; notify(`Setup rejected: ${(error as Error).message}`); }
  } else if (fragment.has("watch"))
    void join(fragment.get("watch")!).catch((e) => notify(e.message));
  else if (fragment.has("replay"))
    void decodeReplay(fragment.get("replay")!)
      .then((parsed) => {
        if (location.hash === hash) openReplay(parsed, false);
      })
      .catch((e) => {
        if (location.hash === hash) notify(`Replay rejected: ${e.message}`);
      });
}
loadFragment();
window.addEventListener("hashchange", loadFragment);
