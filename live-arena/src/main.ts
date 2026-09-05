import "./style.css";
import { Capacitor } from "@capacitor/core";
import { App } from "@capacitor/app";
import { FileTransfer, webDownload, transferMessage, boundedResponse, EXPORT_LIMITS, type ExportKind } from "./file-transfer";
import { bindNativeLifecycle, validateNativeEndpoint } from "./native-lifecycle";
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
  checkConnection,
  validateConnection,
  forgetConnectionCheck,
  type Agent,
  type Model,
} from "./models";
import { Broadcast } from "./broadcast";
import { keyboardCell } from "./board-keyboard";
import { academyMarkup, freeAcademyRecipe } from "./academy";
import { summarizeSeries, type SeriesAttempt } from "./evaluation";
import { isExhibitionLimit } from "./outcome";
import { PracticeMemory, MEMORY_KEY, supportsLearning, scoreTactics, type MemorySnapshot, type MemoryContext } from "./learning";
import { DeviceStorage } from "./device-storage";
import { matchLimits as validateMatchLimits, limitsLabel, type MatchLimits } from "./resources";
import { publicLinkOrigin } from "./public-links";
import { makeProfile, readProfile, disconnectedProfile, compareProfiles, PROFILE_MAX_BYTES } from "./profiles";
import { connectionDialogMarkup, agentSetupBrief } from "./connection-guide";
import { MatchLibrary, canResume, type SavedMatch } from "./library";
import { DECLARATION_FIELDS, readDeclaration, readDeclarations, unknownDeclarations, makeMatchPackage, readMatchFile, type MatchDeclarations } from "./match-package";
import { makeSetup, encodeSetup, decodeSetup, safeReplay, summarizeMatch, resultImage, entrantLabel,
  freeAgents, configuredAgents, type MatchSetup, type MatchSummary } from "./sharing";
import {
  replay,
  encodeReplay,
  decodeReplay,
  type RecordData,
  createProof,
  verifyProof,
  refereeManifest,
  PROOF_LIMIT,
} from "./runtime";

const $ = <T extends HTMLElement = HTMLElement>(id: string) =>
  document.getElementById(id) as T;
const isNativeApp = Capacitor.isNativePlatform();
let deviceStorage: DeviceStorage | undefined;
let deviceStorageFailed = false;
if (isNativeApp) {
  try {
    const { nativeCheckpointPort } = await import("./native-checkpoint-port");
    deviceStorage = await DeviceStorage.open(nativeCheckpointPort, localStorage);
  } catch { deviceStorageFailed = true; }
}
const fileTransfer = new FileTransfer({
  native: isNativeApp ? async () => (await import("./file-transfer-native")).nativeFilePort : undefined,
  webDownload, active: () => nativeReady && nativeActive, epoch: () => nativeEpoch,
});
let nativeReady = !isNativeApp, nativeActive = true;
let nativeEpoch = 0;
let disposeNative: (() => Promise<void>) | undefined;
function ensureDeviceReady(agent?: Agent) {
  if (isNativeApp && (!nativeReady || !nativeActive))
    throw Error("Mobile lifecycle protection is not ready. Return to the app or restart it before playing.");
  if (agent) validateNativeEndpoint(agent.kind, agent.endpoint, isNativeApp);
}
async function exportPublicFile(name: string, blob: Blob, kind: ExportKind) {
  if (isNativeApp) {
    ensureDeviceReady();
    if (running || pending || seriesRemaining) stop("Paused for file export");
  }
  const outcome = await fileTransfer.export(name, blob, kind);
  notify(transferMessage(outcome));
  return outcome;
}
function exportJson(name: string, value: unknown, kind: ExportKind) {
  // Serialize now, before a native share sheet can pause or mutate the match.
  return exportPublicFile(name, new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }), kind);
}
async function copyOrNativeShare(text: string, copiedMessage: string) {
  if (isNativeApp) {
    ensureDeviceReady();
    if (running || pending || seriesRemaining) stop("Paused for sharing");
    notify(transferMessage(await fileTransfer.shareText(text)));
  } else { await navigator.clipboard.writeText(text); notify(copiedMessage); }
}
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
  seriesAttempts: SeriesAttempt[] = [],
  pace = 500;
let seriesLimits: { moveLimit: number; maxTokens: number } | null = null;
let practiceMemory: PracticeMemory;
try { practiceMemory = new PracticeMemory(isNativeApp ? deviceStorage : localStorage); } catch { practiceMemory = new PracticeMemory(); }
let learningPending: Promise<unknown> = Promise.resolve();
let learningEpoch = 0;
let seriesMemory: MemorySnapshot | undefined;
let seriesMemoryEnabled = false;
// Match IDs are designated when created here, never inferred from imported labels.
const practiceMatches = new WeakSet<RecordData>();
const learningReceipts: { recordId: string; ply: number; mode: MemoryContext["mode"]; digest: string; sources: string[] }[] = [];
let currentLimits: MatchLimits | null = null;
let contenderDeclarations = unknownDeclarations(), currentDeclarations = unknownDeclarations();
const attemptDeclarations = new WeakMap<RecordData, MatchDeclarations>();
function captureAttempt(exit: SeriesAttempt["exit"]) {
  const snapshot = structuredClone(record);
  attemptDeclarations.set(snapshot, currentDeclarations);
  seriesAttempts.push({ record: snapshot, exit });
}
let seriesRules: Rules | null = null;
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
let nativeSavingMove = false;
try {
  const storage = isNativeApp ? deviceStorage : localStorage;
  if (storage) library = new MatchLibrary(storage);
} catch {
  /* Storage is optional. */
}
function freshRecord(): RecordData {
  const next: RecordData = {
    schema: "builderwars.exhibition.v1",
    id: crypto.randomUUID(),
    createdAt: new Date().toISOString(),
    rules: { ...rules },
    agents: agents.map(publicAgent),
    events: [],
    status: "Ready",
  };
  if (!seriesRemaining) practiceMatches.add(next);
  return next;
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
<section id="academy" class="view" hidden>${academyMarkup}</section>
<footer><span>BuilderWars · An open playground by Nymrel</span><span>Play • Create • Replay</span></footer></main></div>
${connectionDialogMarkup}`;

function notify(message: string) {
  $("notice").textContent = message;
}
$("academy-status").insertAdjacentHTML("afterend", `<div class="workspace-form"><h2>Practice memory</h2><p>Completed practice matches send connected contenders lessons about immediate wins and preventable one-move losses. Supports Connect Four, tic-tac-toe and custom connect boards up to 42 cells. Chess, checkers and built-in opponents retain their current policies.</p><p id="learning-status" role="status"></p><button id="clear-learning">Clear practice memory</button><p class="muted">Lessons stay on this device and are sent with your next model or harness request. Model weights stay fixed; delivery does not prove the model followed a lesson. Imported replays and evaluation games never add lessons.</p></div>`);
$("run-series").insertAdjacentHTML("beforebegin", '<label class="checkbox"><input id="eval-memory" type="checkbox">Use a frozen copy of practice memory for this evaluation</label><p class="muted">Unchecked runs the baseline with no practice memory. Both modes keep evaluation outcomes out of training.</p>');
function renderLearning(message = "") {
  const storage = deviceStorage?.status;
  const durability = storage === "saving" ? "Saving device memory…" : storage === "cleanup-pending" ? "Current memory saved; older device copies could not be erased. Retry Clear to finish removal." :
    practiceMemory.persistent && (!isNativeApp || storage === "saved") ? "Saved on this device." : "Memory is available in this tab; device saving is unavailable or unconfirmed.";
  $("learning-status").textContent = `${practiceMemory.episodeCount} contender-game reviews retained. ${durability} ${message}`;
}
$("clear-learning").onclick = async () => {
  learningEpoch++;
  practiceMemory.clear();
  if ((isNativeApp && !deviceStorage) || !practiceMemory.persistent) {
    renderLearning("Cleared in this tab only. Device removal is unconfirmed; existing device data may remain.");
    return;
  }
  deviceStorage?.removeItem(MEMORY_KEY);
  renderLearning();
  try {
    await deviceStorage?.flush();
    renderLearning(deviceStorage?.status === "cleanup-pending" ? "Removal is incomplete. Retry Clear." : "Cleared. An evaluation already in progress retains its frozen snapshot.");
  } catch { renderLearning("Cleared in this tab only. Device removal failed; retry Clear."); }
};
renderLearning();
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
  contenderDeclarations = unknownDeclarations();
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
    const encoded = encodeSetup(makeSetup(record, currentLimits?.moveLimit ?? numberInput("move-limit", 2, 400), currentLimits?.maxTokens ?? numberInput("max-tokens", 256, 16384)));
    await copyOrNativeShare(`${publicLinkOrigin(location.origin)}/#setup=${encoded}`, "Setup link copied. Opening it shows a preview and never starts model calls. Keys, prompts and harness addresses are excluded.");
  } catch (error) { notify((error as Error).message); }
}
$("export").insertAdjacentHTML("afterend", '<button id="share-setup-settings">Share current setup</button>');
$("copy-setup").onclick = () => void shareSetup();
$("share-setup-settings").onclick = () => void shareSetup();
$("result-image").onclick = async () => {
  if (imageExporting) return;
  imageExporting = true; renderResult();
  const snapshot = structuredClone(record);
  const check = fileTransfer.preparationGuard();
  try {
    const blob = await resultImage(snapshot);
    check();
    await exportPublicFile(`builderwars-result-${snapshot.id}.png`, blob, "image");
  } catch (error) { notify((error as Error).message); }
  finally { imageExporting = false; renderResult(); }
};
$("copy-caption").onclick = async () => {
  const check = fileTransfer.preparationGuard();
  try {
    const snapshot = safeReplay(record), summary = summarizeMatch(snapshot);
    const encoded = await encodeReplay(snapshot);
    check();
    if (encoded.length > 60000) throw Error("Replay is too large for a link. Download match JSON instead.");
    const caption = `BuilderWars: ${summary.title} in ${summary.record.rules.name} (${summary.plies} plies).\nExhibition; rules replayed, model identity/execution not attested.\nReplay and try a free rematch: ${publicLinkOrigin(location.origin)}/#replay=${encoded}`;
    await copyOrNativeShare(caption, "Result caption and replay link copied. Review before posting; no post has been published.");
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
  $("match-library").setAttribute("aria-busy", String(deviceStorage?.status === "saving"));
  $("save-disclosure").textContent =
    "Device saving is unavailable. Download a match to keep it.";
  $("library-status").textContent =
    "Device storage is unavailable or full. Your current game still works; download its JSON to keep it. Existing device data has not been replaced by a fallback.";
}
async function saveCurrent(candidate = record) {
  if (!library || (nativeSavingMove && candidate === record)) return false;
  if (savedSource === "watch" && !watchId) return false;
  try {
    const limit = currentLimits?.moveLimit ?? Number($<HTMLInputElement>("move-limit").value);
    const saved = library.save(
      candidate,
      savedSource,
      Number.isInteger(limit) && limit >= 2 && limit <= 400 ? limit : 80,
      savedSource === "watch" ? watchId : "",
      currentLimits?.maxTokens ?? undefined,
      currentLimits?.moveLimitKnown === true,
      currentDeclarations,
      currentLimits !== null,
    );
    if (!saved && library.enabled() && candidate.events.length) {
      $("library-status").textContent =
        "Your saved games take priority. Download this replay or forget an older game to make room.";
      return false;
    }
    if (saved && deviceStorage) await deviceStorage.flush();
    if (!libraryRenderTimer)
      libraryRenderTimer = setTimeout(() => {
        libraryRenderTimer = null;
        renderLibrary();
      }, 150);
    return saved;
  } catch {
    libraryFailure();
    return false;
  }
}
function renderLibrary() {
  $("match-library").setAttribute("aria-busy", String(deviceStorage?.status === "saving"));
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
    if (deviceStorage?.status === "saving") $("library-status").textContent = "Saving native checkpoint… Do not close the app until saving finishes.";
    else if (deviceStorage?.status === "cleanup-pending") $("library-status").textContent = "Current checkpoint saved; older device copies could not be erased. Retry Forget to finish removal.";
    else if (deviceStorage?.status === "unavailable") libraryFailure();
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
          button.disabled = running || pending || deviceStorage?.status === "saving";
          button.onclick = async () => {
            if (running || pending || deviceStorage?.status === "saving") return;
            const entry =
              entries[Number(button.getAttribute(`data-saved-${action}`))];
            try {
              if (action === "delete") {
                library!.remove(entry.key);
                const saving = deviceStorage?.flush();
                renderLibrary();
                await saving;
                renderLibrary();
              } else if (action === "resume") resumeSaved(entry);
              else {
                openReplay(replay(entry.record), false, entry.resourceSnapshotPresent || entry.moveLimitKnown || entry.maxTokens !== undefined ? validateMatchLimits(entry.moveLimit, entry.maxTokens ?? null, entry.moveLimitKnown === true) : null, entry.declarations);
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
  currentLimits = validateMatchLimits(entry.moveLimit, entry.maxTokens ?? null, entry.moveLimitKnown === true);
  currentDeclarations = readDeclarations(entry.declarations ?? unknownDeclarations());
  contenderDeclarations = currentDeclarations;
  $("proof-status").textContent = "Recovered record. Any new proof is a reverified snapshot, not original engine or model provenance.";
  state = parsed.state;
  rules = state.rules;
  // Recover into a new record so two tabs never overwrite the same continuation.
  record.id = crypto.randomUUID();
  agents = record.agents.map((a) => ({ ...a, endpoint: "", key: "" }));
  record.status = "Recovered · paused";
  $<HTMLInputElement>("move-limit").value = String(entry.moveLimit);
  if (entry.maxTokens !== undefined) $<HTMLInputElement>("max-tokens").value = String(entry.maxTokens);
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
$("save-matches").onchange = async () => {
  try {
    library?.setEnabled($<HTMLInputElement>("save-matches").checked);
    const saving = deviceStorage?.flush();
    renderLibrary();
    await saving;
    renderLibrary();
  } catch {
    libraryFailure();
  }
};
$("forget-matches").onclick = async () => {
  if (nativeSavingMove) return;
  if (
    !window.confirm(
      "Forget saved matches on this browser and turn automatic saving off? Download anything you want to keep first.",
    )
  )
    return;
  try {
    library?.forget();
    deviceStorage?.forgetLegacyMatches();
    const saving = deviceStorage?.flush();
    renderLibrary();
    await saving;
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
$("move-limit").closest("details")!.insertAdjacentHTML("beforeend", '<p id="resource-status" class="muted" role="status"></p>');
$("agent-dialog").setAttribute("aria-labelledby", "agent-title");
$("board").setAttribute("aria-label", "Game board. Use arrow keys to move between squares, Home or End within a row, and Enter or Space to play.");
let boardFocus = 0;
$("board").addEventListener("focusin", (event) => {
  const cell = (event.target as HTMLElement).closest<HTMLButtonElement>("[data-cell]");
  if (!cell) return;
  boardFocus = Number(cell.dataset.cell);
  $("board").querySelectorAll<HTMLButtonElement>("[data-cell]").forEach((button) => {
    button.tabIndex = button === cell ? 0 : -1;
  });
});
$("board").addEventListener("keydown", (event) => {
  if (event.altKey || event.ctrlKey || event.metaKey) return;
  const buttons = [...$("board").querySelectorAll<HTMLButtonElement>("[data-cell]")];
  const next = keyboardCell(buttons.indexOf(event.target as HTMLButtonElement), event.key, state.rules.cols, buttons.length);
  if (next === null) return;
  event.preventDefault();
  buttons[next].focus();
});
$("notice").insertAdjacentHTML(
  "beforebegin",
  '<div id="replay-controls" hidden><label id="replay-label" for="replay-position">Replay position</label><input id="replay-position" type="range" min="0" value="0"><button id="replay-prev">← Previous</button><button id="replay-next">Next →</button></div>',
);
$("move-history").insertAdjacentHTML(
  "beforebegin",
  '<label>Human chess promotion<select id="promotion"><option value="q">Queen</option><option value="r">Rook</option><option value="b">Bishop</option><option value="n">Knight</option></select></label>',
);
$("strategy").insertAdjacentHTML(
  "afterend",
  '<small class="muted">Builder strategy is included in local JSON exports and live broadcasts, but omitted from new public replay links. Never paste secrets here.</small>',
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
function openReplay(parsed: ReturnType<typeof replay>, save = true, limits: MatchLimits | null = null, declarations = unknownDeclarations()) {
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
  currentLimits = limits;
  currentDeclarations = readDeclarations(declarations);
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
  const active = document.activeElement as HTMLElement | null;
  const focusedCell = active?.dataset.cell;
  const focusedSeat = active?.dataset.seat;
  renderResult();
  document
    .querySelectorAll<HTMLButtonElement>(
      "[data-saved-replay], [data-saved-resume], [data-saved-delete]",
    )
    .forEach((button) => {
      button.disabled = running || pending || deviceStorage?.status === "saving";
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
      return `<button data-cell="${i}" class="cell ${(Math.floor(i / cols) + (i % cols)) % 2 ? "dark" : "light"} ${selected === i ? "selected" : ""} ${highlight ? "last" : ""} ${target ? "target" : ""}" aria-label="${esc(coord)} ${esc(p || "empty")}" aria-disabled="${spectating || pending || state.over || agents[state.turn].kind !== "human"}">${piece}<span class="coord">${coord}</span></button>`;
    })
    .join("");
  document
    .querySelectorAll<HTMLButtonElement>("[data-cell]")
    .forEach((b) => {
      if (boardFocus >= state.cells.length) boardFocus = 0;
      b.tabIndex = Number(b.dataset.cell) === boardFocus ? 0 : -1;
      b.onclick = () => humanClick(Number(b.dataset.cell));
    });
  $("game-title").textContent = state.rules.name;
  $("ply").textContent = `PLY ${String(state.moves.length).padStart(2, "0")}`;
  $("match-status").textContent = isExhibitionLimit(state) ? "Move limit reached" : state.over
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
  $("resource-status").textContent = currentLimits
    ? `This match: ${limitsLabel(currentLimits)}. Limits stay fixed through pause/resume. Edited fields apply to a new rematch or evaluation. Requested tokens are not a guaranteed provider compute or dollar cap.`
    : spectating ? "Imported replay: original resource limits are unavailable. New setup links or reverified proofs use explicitly selected limits, not historical resource evidence."
      : "Limits lock at the first attempted move. After that, edits apply only to a new rematch or evaluation.";
  $("match-attribution").textContent = currentDeclarations.map((d, seat) =>
    `${seat === 0 ? "White / first" : "Black / second"}: ${DECLARATION_FIELDS.map(field => `${declarationLabels[field]}: ${d[field] ?? "unknown"}`).join(" · ")}`
  ).join("\n");
  $("seats").innerHTML = record.agents
    .map(
      (a, i) =>
        `<button class="seat ${state.turn === i && !state.over ? "on-turn" : ""}" data-seat="${i}" ${spectating || running ? "disabled" : ""}><span class="avatar ${i ? "dark-avatar" : ""}">${spectating ? "?" : a.kind === "human" ? "You" : a.kind === "bot" ? "BW" : a.kind === "openrouter" ? "AI" : "{ }"}</span><span><strong>${esc(a.name)}</strong><small>${esc(spectating ? entrantLabel(a) : a.kind === "bot" ? ["tactician", "random"].includes(a.model) ? "Built-in · free" : entrantLabel(a) : a.kind === "human" ? "Human player" : a.model || "Choose model")}</small><small>${i === 0 ? "White / first" : "Black / second"}${a.kind === "openrouter" ? ` · ${esc(a.effort)} effort` : ""}</small></span><span class="seat-edit">↗</span></button>`,
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
  const replacement = focusedCell !== undefined
    ? $("board").querySelector<HTMLButtonElement>(`[data-cell="${Number(focusedCell)}"]`)
    : focusedSeat !== undefined ? $("seats").querySelector<HTMLButtonElement>(`[data-seat="${Number(focusedSeat)}"]`) : null;
  if (replacement && !replacement.disabled) replacement.focus({ preventScroll: true });
}
function interruptSeries(exit: "failed" | "stopped" = "stopped") {
  if (!seriesRemaining) return;
  captureAttempt(exit);
  seriesRemaining = 0;
  renderSeries();
}
function stop(message = "Paused", preserveSeries = false) {
  if (!preserveSeries) interruptSeries();
  running = false;
  controller?.abort();
  controller = null;
  pending = nativeSavingMove;
  runId++;
  record.status = message;
  render();
  broadcast.publish(record);
  if (!spectating) saveCurrent();
}
function reset(preserveSeries = false) {
  stop("Ready", preserveSeries);
  replayPly = null;
  state = createGame(rules);
  record = freshRecord();
  currentLimits = null;
  currentDeclarations = readDeclarations(contenderDeclarations);
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
function getMatchLimits(): MatchLimits {
  return currentLimits ??= seriesRemaining && seriesLimits
    ? validateMatchLimits(seriesLimits.moveLimit, seriesLimits.maxTokens)
    : validateMatchLimits(numberInput("move-limit", 2, 400), numberInput("max-tokens", 256, 16384));
}
async function commit(
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
  const previous = record, generation = runId, wasPending = pending;
  const nextState = applyMove(state, move);
  const nextRecord: RecordData = { ...record, events: [...record.events, {
    ...details,
    move,
    ply: nextState.moves.length,
    seat,
    label,
  }], status: nextState.over ? nextState.reason : "Playing" };
  let saved = true;
  const nativeReview = !!deviceStorage && nextState.over && practiceMatches.has(previous) && supportsLearning(nextState.rules);
  let reviewed = 0;
  if (deviceStorage && (library?.enabled() || nativeReview)) {
    nativeSavingMove = true;
    pending = true;
    render();
    try {
      if (nativeReview) {
        const contenders = structuredClone(agents), epoch = learningEpoch;
        learningPending = learningPending.then(async () => {
          if (epoch === learningEpoch) reviewed = await practiceMemory.remember(nextRecord, contenders);
        });
        await learningPending;
      }
      if (library?.enabled()) saved = await saveCurrent(nextRecord);
      else await deviceStorage.flush();
    } catch { saved = false; libraryFailure(); }
    finally { nativeSavingMove = false; pending = runId === generation ? wasPending : false; }
    // A rematch/import may supersede the old record while native I/O is pending.
    if (record !== previous) { render(); return; }
    if (runId !== generation) nextRecord.status = previous.status;
  }
  if (practiceMatches.has(previous)) { practiceMatches.delete(previous); practiceMatches.add(nextRecord); }
  state = nextState;
  record = nextRecord;
  selected = -1;
  render();
  broadcast.publish(record);
  if (!deviceStorage) void saveCurrent();
  if (!saved) notify("Move played, but device saving failed. Download the match to keep it.");
  if (state.over)
  {
    if (practiceMatches.has(record) && supportsLearning(state.rules)) {
      practiceMatches.delete(record);
      if (nativeReview) renderLearning(saved ? `${reviewed} tactical mistakes recorded from the latest completed practice game.` : "Practice review retained in this tab; device save is unconfirmed.");
      else {
      const finished = structuredClone(record), contenders = structuredClone(agents), epoch = learningEpoch;
      learningPending = learningPending.then(() => epoch === learningEpoch ? practiceMemory.remember(finished, contenders) : 0)
        .then(async added => {
          if (epoch !== learningEpoch) return;
          renderLearning();
          try { await deviceStorage?.flush(); }
          catch { if (epoch === learningEpoch) renderLearning("Practice review retained in this tab; device save failed."); return; }
          if (epoch === learningEpoch) renderLearning(`${added} tactical mistakes recorded from the latest completed practice game.`);
        })
        .catch(() => { if (epoch === learningEpoch) renderLearning("This game did not qualify for practice memory."); });
      }
    }
    notify(
      (isExhibitionLimit(state) ? `${state.reason}. No rule-complete result.` : `${state.reason}. ${state.winner === null ? "Draw." : record.agents[state.winner].name + " wins."}`) + (saved ? "" : " Device saving failed; download this match to keep it."),
    );
  }
}
async function oneMove() {
  if (
    pending ||
    spectating ||
    state.over ||
    agents[state.turn].kind === "human"
  )
    return;
  ensureDeviceReady(agents[state.turn]);
  const limits = getMatchLimits();
  if (state.moves.length >= limits.moveLimit)
    throw Error("Exhibition move limit reached. Start a rematch.");
  const id = runId,
    config = agents[state.turn],
    tokens = limits.maxTokens ?? 2048; // Legacy recovery is restricted to human/built-in seats.
  controller = new AbortController();
  pending = true;
  render();
  try {
    await learningPending;
    if (id !== runId) return;
    const memory = await practiceMemory.context(config, state.rules,
      seriesRemaining ? "frozen-evaluation" : "practice",
      seriesRemaining ? seriesMemory ?? { schema: "builderwars.practice-memory.v1", episodes: [] } : undefined);
    if (id !== runId) return;
    const decision = await decide(
      state,
      config,
      tokens,
      controller.signal,
      models,
      memory,
    );
    if (id !== runId) return;
    if (memory) {
      learningReceipts.push({ recordId: record.id, ply: state.moves.length + 1, mode: memory.mode, digest: memory.digest, sources: memory.sources });
      if (learningReceipts.length > 4000) learningReceipts.shift();
      renderLearning(`Last accepted request included ${memory.sources.length} prior practice game(s), context ${memory.digest.slice(0, 12)}. Behavior improvement remains unmeasured.`);
    }
    await commit(decision.move, decision);
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
    stop();
    return;
  }
  if (pending) return;
  let moveLimit: number;
  try {
    ensureDeviceReady(agents[state.turn]);
    moveLimit = getMatchLimits().moveLimit;
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
      interruptSeries("failed");
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
async function humanClick(i: number) {
  if (
    pending ||
    spectating ||
    state.over ||
    agents[state.turn].kind !== "human"
  )
    return;
  try {
    ensureDeviceReady();
    if (state.moves.length >= getMatchLimits().moveLimit) {
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
  await commit(move, {
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
  contenderDeclarations = unknownDeclarations();
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
  fillDeclarationForm(contenderDeclarations[seat]);
  importedSelection = null;
  cancelConnectionProbe();
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
  $<HTMLSelectElement>("model-id").value = "";
  $("agent-setup-preview").hidden = true;
  $("show-agent-setup").setAttribute("aria-expanded", "false");
  $<HTMLDetailsElement>("connection-advanced").open = false;
  $<HTMLDetailsElement>("model-options").open = false;
  connectionFields();
  profileComparison();
  $<HTMLDialogElement>("agent-dialog").showModal();
}
let importedSelection: { model: string; effort: string } | null = null;
function connectionFields(loadCatalog = true) {
  const kind = $<HTMLSelectElement>("agent-kind").value;
  $("bot-fields").hidden = kind !== "bot";
  $("human-fields").hidden = kind !== "human";
  $("agent-help").hidden = !["openrouter", "harness"].includes(kind);
  $("local-client-label").hidden = kind !== "harness";
  $("model-fields").hidden = kind !== "openrouter";
  $("harness-fields").hidden = kind !== "harness";
  $("key-fields").hidden = !["openrouter", "harness"].includes(kind);
  $("forget-key").hidden = !["openrouter", "harness"].includes(kind);
  $("credential-name").textContent = kind === "openrouter" ? "Your OpenRouter API key" : "Temporary local token / endpoint bearer token";
  $("credential-help").textContent = kind === "openrouter"
    ? "Sent directly to OpenRouter, not BuilderWars hosting. Kept only in this tab’s memory; never exported. Other providers’ API keys do not belong here."
    : "Use the temporary token from your local terminal, not your provider’s login or API key. For your own HTTPS endpoint, use its bearer token. Kept only in this tab’s memory; never exported.";
  $("connection-summary").textContent = `${selectedSeat === 0 ? "White / first" : "Black / second"} seat. ${kind === "bot" || kind === "human" ? "No account needed. Choose Use contender, then start from the board." : "Your connection stays private. Start a match separately when you are ready."}`;
  $("connection-check-title").textContent = kind === "bot" || kind === "human" ? "Ready when you are" : "3. Check and use";
  updateAgentSetup();
  if (kind === "openrouter") {
    if (!models.length && loadCatalog) void loadModels();
    else filterModels();
  }
}
$<HTMLSelectElement>("agent-kind").onchange = () => {
  importedSelection = null;
  $<HTMLInputElement>("agent-key").value = "";
  $<HTMLSelectElement>("model-id").value = "";
  const name = $<HTMLInputElement>("agent-name"), kind = $<HTMLSelectElement>("agent-kind").value;
  if (["Tactician", "Wildcard", "Contender", "My model", "My agent", "Human"].includes(name.value))
    name.value = kind === "openrouter" ? "My model" : kind === "harness" ? "My agent" : kind === "human" ? "Human" : $<HTMLSelectElement>("bot-model").value === "random" ? "Wildcard" : "Tactician";
  if (kind === "harness" && ["tactician", "random", "human"].includes($<HTMLInputElement>("harness-model").value))
    $<HTMLInputElement>("harness-model").value = "";
  connectionFields();
};
function updateAgentSetup() {
  const kind = $<HTMLSelectElement>("agent-kind").value;
  $<HTMLTextAreaElement>("agent-setup-text").value = ["openrouter", "harness"].includes(kind)
    ? agentSetupBrief(kind, $<HTMLSelectElement>("local-client").value) : "";
  $("agent-setup-status").textContent = "";
}
$<HTMLSelectElement>("local-client").onchange = (event) => { event.stopPropagation(); updateAgentSetup(); };
$<HTMLSelectElement>("local-client").oninput = (event) => event.stopPropagation();
$("show-agent-setup").onclick = () => {
  const preview = $("agent-setup-preview"); preview.hidden = !preview.hidden;
  $("show-agent-setup").setAttribute("aria-expanded", String(!preview.hidden));
};
$("copy-agent-setup").onclick = async () => {
  updateAgentSetup();
  try {
    await navigator.clipboard.writeText($<HTMLTextAreaElement>("agent-setup-text").value);
    $("agent-setup-status").textContent = "Instructions copied. Paste them into your agent. No keys or private settings included.";
  } catch {
    $("agent-setup-preview").hidden = false;
    $("show-agent-setup").setAttribute("aria-expanded", "true");
    $<HTMLTextAreaElement>("agent-setup-text").focus();
    $<HTMLTextAreaElement>("agent-setup-text").select();
    $("agent-setup-status").textContent = "Clipboard unavailable. Copy the selected instructions above.";
  }
};
$<HTMLInputElement>("harness-url").oninput = () => {
  $<HTMLInputElement>("agent-key").value = "";
};
$("use-local-address").onclick = () => {
  cancelConnectionProbe();
  $<HTMLInputElement>("harness-url").value = "http://127.0.0.1:8765/move";
  $<HTMLInputElement>("agent-key").value = "";
  $("dialog-status").textContent = "Local address restored. Paste the temporary token from your bridge terminal.";
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
      importedSelection?.model || $<HTMLSelectElement>("model-id").value || (agents[selectedSeat].kind === "openrouter" ? agents[selectedSeat].model : "");
  const available = models.filter(
    (m) =>
      (!q || (m.id + " " + m.name).toLowerCase().includes(q)) &&
      (!free || (m.pricing?.prompt === "0" && m.pricing?.completion === "0")),
  );
  $("model-id").innerHTML = '<option value="" disabled selected>Choose a model…</option>' + available
    .map((m) => `<option value="${esc(m.id)}">${esc(m.name)}</option>`)
    .join("");
  if (available.some((m) => m.id === prior))
    $<HTMLSelectElement>("model-id").value = prior;
  else if (importedSelection) {
    const option = new Option(`${prior} · not in current catalog`, prior);
    $<HTMLSelectElement>("model-id").add(option);
    $<HTMLSelectElement>("model-id").value = prior;
  }
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
  if (importedSelection) {
    if (!efforts.includes(importedSelection.effort))
      $<HTMLSelectElement>("effort").add(new Option(`${importedSelection.effort} · unconfirmed`, importedSelection.effort));
    $<HTMLSelectElement>("effort").value = importedSelection.effort;
  }
  $("model-price").textContent = model?.pricing
    ? `Catalog price per 1M tokens: $${(Number(model.pricing.prompt) * 1e6).toFixed(2)} input / $${(Number(model.pricing.completion) * 1e6).toFixed(2)} output. Additional provider charges may apply.`
    : "Choose a model.";
}
$("refresh-models").onclick = () => void loadModels();
$<HTMLInputElement>("model-search").oninput = filterModels;
$<HTMLInputElement>("free-models").onchange = filterModels;
$<HTMLSelectElement>("model-id").onchange = () => { importedSelection = null; updateEfforts(); };
$<HTMLSelectElement>("effort").onchange = () => { importedSelection = null; };
$("close-dialog").onclick = () => $<HTMLDialogElement>("agent-dialog").close();
$("forget-key").onclick = () => {
  cancelConnectionProbe();
  forgetConnectionCheck(agents[selectedSeat]);
  agents[selectedSeat].key = "";
  $<HTMLInputElement>("agent-key").value = "";
  $("dialog-status").textContent = "Key removed from this contender.";
};
function agentFromForm(): Agent {
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
  return a;
}
let connectionProbe: AbortController | null = null;
let connectionGeneration = 0;
function cancelConnectionProbe() {
  connectionProbe?.abort(); connectionProbe = null; connectionGeneration++;
  $("check-connection").removeAttribute("disabled");
  $("dialog-status").textContent = "";
}
$("agent-form").addEventListener("input", cancelConnectionProbe);
$("agent-form").addEventListener("change", cancelConnectionProbe);
$("agent-dialog").addEventListener("close", cancelConnectionProbe);
$("profile-options").insertAdjacentHTML("beforeend", '<p id="profile-comparison" class="muted" aria-live="polite"></p><p class="muted">Profile files include your name, model settings and strategy text. Keys and endpoints are excluded. Inspect strategy text for secrets before exporting or sharing. Import only edits this draft; it never starts play.</p>');
function profileComparison() {
  const result = compareProfiles(agents[selectedSeat], agentFromForm());
  const labels: Record<string, string> = { kind: "connection type", model: "model / opponent", effort: "effort", strategy: "strategy" };
  $("profile-comparison").textContent = result.changed.length
    ? `${result.changed.length} setting${result.changed.length === 1 ? "" : "s"} changed from the saved contender: ${result.changed.map(k => labels[k]).join(", ")}. ${result.changed.length === 1 ? "One-change draft." : "Change one setting at a time for a clearer experiment."} This comparison does not check endpoints, keys, external harness versions or game resources; it is not performance evidence.`
    : `No behavior settings changed.${result.renamed ? " Display name changed." : ""} Keys and endpoints are not compared.`;
}
$("agent-form").addEventListener("input", profileComparison);
$("agent-form").addEventListener("change", profileComparison);
const declarationLabels: Record<typeof DECLARATION_FIELDS[number], string> = {
  builderId: "Builder ID", agentId: "Agent ID", agentRevision: "Agent revision",
  harnessId: "Harness ID", harnessRevision: "Harness revision", providerId: "Execution provider ID", modelRevision: "Model revision",
};
$("profile-options").insertAdjacentHTML("beforeend", `<details id="declaration-fields"><summary>Public attribution (optional)</summary><p class="muted">Self-declared identifiers, not verified identities. Leave unknown values blank. Never enter keys, private addresses or other secrets. Match packages retain these fields; agent profiles and replay links do not.</p>${DECLARATION_FIELDS.map(field => `<label>${declarationLabels[field]}<input id="declaration-${field}" maxlength="96" autocomplete="off" spellcheck="false"></label>`).join("")}</details>`);
function fillDeclarationForm(value: MatchDeclarations[number]) {
  for (const field of DECLARATION_FIELDS) $<HTMLInputElement>(`declaration-${field}`).value = value[field] ?? "";
}
function declarationFromForm() {
  return readDeclaration(Object.fromEntries(DECLARATION_FIELDS.map(field => [field, $<HTMLInputElement>(`declaration-${field}`).value.trim() || null])));
}
$("export").insertAdjacentHTML("afterend", '<button id="export-package">Download match package</button><p class="muted">Match package: public attribution, requested limits, replay and verifier digest. Strategies and comments are omitted. Model execution and identity are not attested.</p>');
$("export-package").insertAdjacentHTML("afterend", '<section aria-label="Match attribution"><h3>Match attribution · self-declared</h3><p id="match-attribution" class="muted" style="overflow-wrap:anywhere;white-space:pre-line"></p></section>');
$("export-package").onclick = async () => {
  try { await exportJson(`builderwars-${record.id}.package.json`, makeMatchPackage(record, currentDeclarations, currentLimits), "replay"); }
  catch (error) { notify((error as Error).message); }
};
$("import-agent").onclick = () => $<HTMLInputElement>("profile-file").click();
$<HTMLInputElement>("profile-file").onchange = async (event) => {
  event.stopPropagation();
  const input = $<HTMLInputElement>("profile-file"), file = input.files?.[0];
  input.value = "";
  if (!file) return;
  cancelConnectionProbe();
  const generation = connectionGeneration, seat = selectedSeat, snapshot = JSON.stringify(agentFromForm());
  try {
    if (file.size > PROFILE_MAX_BYTES) throw Error("Profile exceeds 8 KB.");
    const candidate = disconnectedProfile(readProfile(await file.text()));
    if (generation !== connectionGeneration || seat !== selectedSeat || snapshot !== JSON.stringify(agentFromForm()) || !$<HTMLDialogElement>("agent-dialog").open) return;
    if (!confirm("Replace this connection draft? Its key and endpoint will be cleared. The saved contender and match stay unchanged until you choose Use contender.")) return;
    $<HTMLInputElement>("agent-name").value = candidate.name;
    $<HTMLSelectElement>("agent-kind").value = candidate.kind;
    $<HTMLSelectElement>("bot-model").value = candidate.model;
    $<HTMLInputElement>("agent-key").value = "";
    $<HTMLInputElement>("harness-url").value = "";
    $<HTMLInputElement>("harness-model").value = candidate.model;
    $<HTMLInputElement>("harness-effort").value = candidate.effort;
    $<HTMLTextAreaElement>("strategy").value = candidate.strategy;
    fillDeclarationForm(unknownDeclarations()[0]);
    $<HTMLInputElement>("model-search").value = "";
    $<HTMLInputElement>("free-models").checked = false;
    importedSelection = candidate.kind === "openrouter" ? { model: candidate.model, effort: candidate.effort } : null;
    connectionFields(false);
    profileComparison();
    $("dialog-status").textContent = "Profile imported into this draft. Keys and endpoints cleared. Remote models need current catalog validation and your own connection before use. No game or model request started.";
  } catch (error) {
    if (generation === connectionGeneration) $("dialog-status").textContent = (error as Error).message;
  }
};
$("check-connection").onclick = async () => {
  cancelConnectionProbe();
  const generation = connectionGeneration;
  const a = agentFromForm(), snapshot = JSON.stringify(a);
  const controller = connectionProbe = new AbortController();
  $("check-connection").setAttribute("disabled", "");
  $("dialog-status").textContent = "Checking connection without model inference…";
  try {
    ensureDeviceReady(a);
    const result = await checkConnection(a, models, controller.signal);
    if (generation === connectionGeneration && snapshot === JSON.stringify(agentFromForm()) && $<HTMLDialogElement>("agent-dialog").open) $("dialog-status").textContent = result.message;
  } catch (error) {
    if (generation === connectionGeneration) $("dialog-status").textContent = (error as Error).name === "TimeoutError" ? "Connection check timed out after 15 seconds. No model invoked." : (error as Error).message;
  } finally {
    if (generation === connectionGeneration) { connectionProbe = null; $("check-connection").removeAttribute("disabled"); }
  }
};
$<HTMLFormElement>("agent-form").onsubmit = (e) => {
  e.preventDefault();
  const a = agentFromForm();
  let declaration: MatchDeclarations[number];
  try { ensureDeviceReady(a); validateConnection(a, models); declaration = declarationFromForm(); }
  catch (error) { $("dialog-status").textContent = (error as Error).message; return; }
  if (running || pending || spectating) { $("dialog-status").textContent = "Pause the match before replacing a contender."; return; }
  if (record.events.length && !state.over && !confirm("Use this contender and reset the unfinished match? Export the current match first if you want to keep it.")) return;
  cancelConnectionProbe();
  agents[selectedSeat] = a;
  contenderDeclarations = readDeclarations(contenderDeclarations.map((d, seat) => seat === selectedSeat ? declaration : d));
  $<HTMLDialogElement>("agent-dialog").close();
  reset();
};
$("export-agent").onclick = async () => {
  try { const outcome = await exportJson("builderwars-agent.json", makeProfile(agentFromForm()), "profile"); $("dialog-status").textContent = transferMessage(outcome); }
  catch (error) { $("dialog-status").textContent = (error as Error).message; }
};
$("export").onclick = async () => {
  try { await exportJson(`builderwars-${record.id}.json`, replay(record).record, "replay"); }
  catch (error) { notify((error as Error).message); }
};
$("export-proof").onclick = async () => {
  if (rules.kind !== "connect4" || proofExporting) return;
  const snapshot = structuredClone(record);
  const origin = proofOrigin;
  const check = fileTransfer.preparationGuard();
  proofExporting = true;
  render();
  try {
    const limit = currentLimits?.moveLimit ?? Math.max(snapshot.events.length, numberInput("move-limit", 2, 400));
    const text = await createProof(snapshot, refereeManifest.digest, limit, origin);
    const verified = await verifyProof(text, refereeManifest.digest);
    check();
    await exportPublicFile(`builderwars-${snapshot.id}.jsonl`, new Blob([text], { type: "application/x-ndjson" }), "proof");
    if (record.id === snapshot.id) $("proof-status").textContent = `${verified.state.over ? "Completed result" : "Incomplete snapshot"} reproduced at ${snapshot.events.length} plies. Keep the matching verifier. Model identity and execution are not attested.`;
  } catch (error) {
    $("proof-status").textContent = (error as Error).message;
  } finally {
    proofExporting = false;
    render();
  }
};
if (isNativeApp) {
  for (const [id, label] of Object.entries({ "export": "Save / share replay", "export-package": "Save / share match package", "export-agent": "Save / share profile", "export-proof": "Save / share proof", "download-verifier": "Save / share matching verifier", "export-rules": "Save / share rules", "export-series": "Save / share evaluation", "result-image": "Save / share result image", "copy-caption": "Share caption and replay", "copy-setup": "Share setup" })) $(id).textContent = label;
  let verifierExporting = false;
  $("download-verifier").onclick = async event => {
    event.preventDefault();
    if (verifierExporting) return;
    verifierExporting = true;
    const check = fileTransfer.preparationGuard();
    try {
      ensureDeviceReady();
      const response = await fetch(`/${refereeManifest.verifier}`, { redirect: "error", signal: AbortSignal.timeout(15000) });
      const blob = await boundedResponse(response, EXPORT_LIMITS.verifier);
      check();
      await exportPublicFile(`builderwars-verifier-${refereeManifest.digest}.mjs`, blob, "verifier");
    } catch (error) { $("proof-status").textContent = (error as Error).message; }
    finally { verifierExporting = false; }
  };
}
let fileImportGeneration = 0, creatorDraftRevision = 0;
$("creator").addEventListener("input", () => creatorDraftRevision++);
$("creator").addEventListener("change", () => creatorDraftRevision++);
function importGuard() {
  const ticket = ++fileImportGeneration, generation = runId, id = record.id, plies = record.events.length, watching = spectating;
  if (running || pending) throw Error("Pause the current match before importing.");
  return () => {
    if (ticket !== fileImportGeneration || generation !== runId || id !== record.id || plies !== record.events.length || watching !== spectating || running || pending)
      throw Error("The match changed during import. Import again when paused.");
  };
}
$<HTMLInputElement>("import-proof").onchange = async (event) => {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  const generation = runId;
  const matchId = record.id;
  const moveCount = record.events.length;
  try {
    const check = importGuard();
    if (running || pending) throw Error("Pause the current match before importing proof.");
    if (file.size > PROOF_LIMIT) throw Error("Proof exceeds size limit.");
    const text = new TextDecoder("utf-8", { fatal: true }).decode(await file.arrayBuffer());
    const verified = await verifyProof(text, refereeManifest.digest);
    check();
    if (generation !== runId || matchId !== record.id || moveCount !== record.events.length || running || pending) throw Error("The match changed during verification. Import again when paused.");
    if (verified.record.rules.kind !== "connect4") throw Error("This release supports Connect Four proof imports. Use the matching offline verifier for other formats.");
    openReplay(verified, false);
    // Read only after exact referee verification; this does not trust an unverified header.
    currentLimits = validateMatchLimits(JSON.parse(text.split("\n")[0]).body.maxPlies, null);
    saveCurrent(); render();
    $("proof-status").textContent = `${verified.record.status} · ${verified.record.events.length} plies reproduced by the matching referee. Names and models remain unverified declarations.`;
  } catch (error) {
    $("proof-status").textContent = (error as Error).message;
  } finally {
    input.value = "";
  }
};
async function shareReplay() {
  const check = fileTransfer.preparationGuard();
  try {
    const encoded = await encodeReplay(safeReplay(record));
    check();
    if (encoded.length > 60000)
      throw Error(
        "This match is too large for a URL. Download and share its JSON file.",
      );
    const link = `${publicLinkOrigin(location.origin)}/#replay=${encoded}`;
    await copyOrNativeShare(link,
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
  return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(await f.arrayBuffer()));
}
$<HTMLInputElement>("import").onchange = async (e) => {
  const input = e.target as HTMLInputElement;
  if (!input.files?.[0]) return;
  try {
    const check = importGuard();
    const imported = readMatchFile(await readFile(input));
    check();
    openReplay(imported.parsed, true, imported.limits, imported.declarations);
  } catch (e) {
    notify((e as Error).message);
  } finally { input.value = ""; }
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
$("export-rules").onclick = async () => {
  try {
    await exportJson("builderwars-game.json", creatorRules(), "rules");
  } catch (e) {
    notify((e as Error).message);
    tab("arena");
  }
};
$<HTMLInputElement>("import-rules").onchange = async (e) => {
  const input = e.target as HTMLInputElement;
  if (!input.files?.[0]) return;
  try {
    const check = importGuard(), draft = creatorDraftRevision;
    if (spectating) throw Error("Leave spectator mode first.");
    const imported = validateRules(await readFile(input));
    check();
    if (draft !== creatorDraftRevision) throw Error("The rules draft changed during import. Import again to replace it.");
    rules = imported;
    reset();
    tab("arena");
  } catch (e) {
    notify((e as Error).message);
    tab("arena");
  } finally { input.value = ""; }
};
function finishSeriesGame() {
  captureAttempt("finished");
  seriesRemaining--;
  renderSeries();
  if (seriesRemaining > 0) {
    agents = [agents[1], agents[0]];
    contenderDeclarations = readDeclarations([contenderDeclarations[1], contenderDeclarations[0]]);
    reset(true);
    void play();
  } else {
    notify(
      `Evaluation ended: ${seriesAttempts.length} attempts. Open Evals for completed results and limits.`,
    );
  }
}
function renderSeries() {
  const summary = summarizeSeries(seriesAttempts, seriesTotal);
  const tactics = scoreTactics(seriesAttempts.map(a => a.record));
  const entrants = seriesAttempts[0]?.record.agents;
  const number = (value: number | null, digits = 0) => value === null ? "Unknown" : value.toFixed(digits);
  $("series-results").innerHTML = `<h2>${summary.recorded} / ${seriesTotal} attempts recorded</h2>
    <p id="series-conditions">${seriesRules ? `${esc(seriesRules.name)} · ${esc(seriesRules.kind)} · ${seriesRules.rows} × ${seriesRules.cols}${seriesRules.connect ? ` · connect ${seriesRules.connect} · ${seriesRules.gravity ? "gravity" : "no gravity"}` : ""}` : "Rules unavailable"}. ${limitsLabel(seriesLimits)}. Each game starts from the standard initial position; seats swap. Built-in randomness is unseeded; model sampling and external harness versions are not controlled or attested. This is a paired exhibition, not a matched-seed benchmark.</p>
    <p>Practice memory: ${seriesMemoryEnabled ? "frozen at series start" : "off (baseline)"}. Evaluation outcomes never update memory.</p>
    <p class="muted">Rule engine: builderwars-board-js/1 · <span title="${refereeManifest.digest}">${refereeManifest.digest.slice(0, 12)}…</span>. Full digest is included in the evaluation export.</p>
    <p>${summary.completed} rule-complete games · ${summary.completePairs} complete pairs · ${summary.draws} draws</p>
    <p>Tactical review: ${tactics.reviewedGames} complete connect games; ${tactics.excludedGames} unsupported, incomplete or invalid attempts excluded. ${tactics.contenders.map((c, i) => `${i ? "B" : "A"}: ${c.missedWins} missed wins, ${c.avoidableLosses} avoidable immediate losses across ${c.decisions} decisions`).join(". ")}.</p>
    <p>${summary.capped} capped · ${summary.failed} failed · ${summary.stopped} stopped. ${seriesRemaining > 0 ? "Series in progress." : "Series not running."}</p>
    ${entrants ? `<p>Wins: A — ${esc(entrants[0].name)}: ${summary.wins[0]}; B — ${esc(entrants[1].name)}: ${summary.wins[1]}. A starts odd games; B starts even games.</p>` : ""}
    <div class="results-table">${summary.games.map(g => `<p><span>Game ${g.number}</span><strong>${esc(g.outcome)}</strong><small>${g.plies} plies</small></p>`).join("")}</div>
    <p class="muted">Accepted moves only: ${summary.acceptedPlies} plies · mean latency ${number(summary.acceptedMeanLatency)} ms · reported tokens ${number(summary.acceptedReportedTokens)} · reported cost ${summary.acceptedReportedCost === null ? "Unknown" : "$" + number(summary.acceptedReportedCost, 4)}. Failed or rejected calls may incur unrecorded usage. This is not a billing total.</p>
    <p class="muted">Seat order and declared contenders are stored per game; move-level model labels are provider/harness reports, not identity attestations. Small samples, different rules or unequal budgets do not establish a general ranking or prove learning.</p>
    <p class="muted">Results stay in this tab. Export before reloading or starting another series.</p>`;
  $("academy-status").textContent = `${summary.completed} rule-complete games in the current evaluation, ${summary.completePairs} complete pairs. Inspect Evals before drawing a conclusion. No automatic training or promotion occurred.`;
}
function runSeries() {
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
  let nextLimits: { moveLimit: number; maxTokens: number }, nextTotal: number;
  try {
    nextLimits = { moveLimit: numberInput("move-limit", 2, 400), maxTokens: numberInput("max-tokens", 256, 16384) };
    nextTotal = numberInput("series-length", 2, 10);
    if (![2, 4, 10].includes(nextTotal)) throw Error("Choose 2, 4 or 10 games.");
  } catch (error) {
    notify((error as Error).message); tab("arena"); return;
  }
  seriesLimits = nextLimits;
  seriesMemoryEnabled = $<HTMLInputElement>("eval-memory").checked;
  seriesMemory = seriesMemoryEnabled ? practiceMemory.snapshot() : undefined;
  seriesRules = structuredClone(rules);
  seriesTotal = nextTotal;
  seriesRemaining = seriesTotal;
  seriesAttempts = [];
  renderSeries();
  reset(true);
  tab("arena");
  void play();
}
$("run-series").onclick = runSeries;
$("export-series").onclick = async () => {
  try { await exportJson("builderwars-evaluation.json", {
    schema: "builderwars.evaluation.v1",
    games: seriesAttempts.map(a => a.record),
    matchPackages: seriesAttempts.map(a => makeMatchPackage(a.record, attemptDeclarations.get(a.record) ?? unknownDeclarations(), seriesLimits ? validateMatchLimits(seriesLimits.moveLimit, seriesLimits.maxTokens) : null)),
    attempts: seriesAttempts.map(a => ({ recordId: a.record.id, exit: a.exit })),
    requestedGames: seriesTotal,
    limits: seriesLimits,
    rules: seriesRules,
    fixture: "standard-initial-position",
    randomness: "unseeded-and-not-controlled",
    ruleEngine: { version: "builderwars-board-js/1", digest: refereeManifest.digest },
    summary: summarizeSeries(seriesAttempts, seriesTotal),
    inProgress: seriesRemaining > 0,
    seatSwap: true,
    learning: { mode: seriesMemoryEnabled ? "frozen-practice-memory" : "baseline-no-memory", updatesFromEvaluation: false,
      snapshot: seriesMemory ?? null,
      tactics: scoreTactics(seriesAttempts.map(a => a.record)),
      acceptedRequestContexts: learningReceipts.filter(r => seriesAttempts.some(a => a.record.id === r.recordId)) },
  }, "evaluation"); }
  catch (error) { notify((error as Error).message); }
};
function prepareAcademy(variant: boolean) {
  if (running || pending || spectating) {
    $("academy-status").textContent = "Pause the current match or leave spectator mode before starting an exercise.";
    return false;
  }
  const recipe = freeAcademyRecipe(variant);
  joinGeneration++;
  broadcast.close(); broadcastLink = ""; watchId = "";
  $("stop-broadcast").hidden = true;
  $("watch-link").textContent = "Start broadcasting to create a spectator link.";
  history.replaceState(null, "", location.pathname + location.search);
  agents = recipe.agents;
  contenderDeclarations = unknownDeclarations();
  rules = recipe.rules;
  $<HTMLInputElement>("move-limit").value = String(recipe.moveLimit);
  $<HTMLInputElement>("max-tokens").value = String(recipe.maxTokens);
  reset();
  return true;
}
$("academy-pair").onclick = () => {
  if (!prepareAcademy(false)) return;
  $<HTMLSelectElement>("series-length").value = "2";
  runSeries();
};
$("academy-variant").onclick = () => {
  if (!prepareAcademy(true)) return;
  $<HTMLInputElement>("creator-name").value = rules.name;
  $<HTMLInputElement>("creator-rows").value = String(rules.rows);
  $<HTMLInputElement>("creator-cols").value = String(rules.cols);
  $<HTMLInputElement>("creator-connect").value = String(rules.connect);
  $<HTMLInputElement>("creator-gravity").checked = rules.gravity;
  tab("forge");
};
async function goLive() {
  if (startingBroadcast) return;
  if (spectating) {
    notify("Spectators cannot rebroadcast this match.");
    return;
  }
  startingBroadcast = true;
  try {
    ensureDeviceReady();
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
      broadcastLink = `${publicLinkOrigin(location.origin)}/#watch=${id}`;
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
  ensureDeviceReady();
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
  currentLimits = null;
  currentDeclarations = unknownDeclarations();
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
    ? `${publicLinkOrigin(location.origin)}/?stream=1#watch=${watchId}`
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
  void disposeNative?.();
});
if (new URLSearchParams(location.search).get("stream") === "1")
  document.body.classList.add("stream-view");
render();
renderLibrary();
if (deviceStorageFailed) notify("Native saving could not open. Existing device data was left untouched. You can play and download games, but new games and lessons are not saved on this device.");
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
        if (location.hash !== hash) return;
        if ((running || pending || (savedSource === "own" && record.events.length > 0 && !state.over)) &&
            !window.confirm("Open this shared replay instead of your current match? Export first if you need a copy; device storage may be unavailable.")) {
          history.replaceState(null, "", location.pathname + location.search);
          notify("Replay dismissed. Your current match is unchanged.");
          return;
        }
        openReplay(parsed, false);
      })
      .catch((e) => {
        if (location.hash === hash) notify(`Replay rejected: ${e.message}`);
      });
}
function suspendNative() {
  if (!nativeActive) return;
  nativeEpoch++;
  nativeActive = false;
  stop("Paused when app left foreground");
  cancelConnectionProbe();
  agents.forEach(forgetConnectionCheck);
  joinGeneration++;
  saveCurrent();
  broadcast.close();
  broadcastLink = "";
  $("stop-broadcast").hidden = true;
  $("watch-link").textContent = "Broadcast stopped while app was inactive. Start a new broadcast explicitly.";
}
if (isNativeApp) {
  try {
    disposeNative = await bindNativeLifecycle(App, suspendNative, () => {
      nativeActive = true;
      notify("App resumed paused. Press Start to continue, or reconnect in Watch. No model call restarted automatically.");
    });
    nativeReady = true;
  } catch {
    suspendNative();
    notify("Mobile lifecycle protection failed to initialize. Restart the app. No model requests can start.");
  }
}
loadFragment();
window.addEventListener("hashchange", loadFragment);
