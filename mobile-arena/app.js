"use strict";

const state = {
  data: null,
  activeView: "arena",
  followingFirst: false,
  lastFocus: null,
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const escapeHTML = (value) => String(value).replace(/[&<>'"]/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
}[character]));

function nextModalFocusIndex(currentIndex, count, shiftKey) {
  if (!Number.isInteger(count) || count <= 0) return -1;
  if (!Number.isInteger(currentIndex) || currentIndex < 0 || currentIndex >= count) return shiftKey ? count - 1 : 0;
  return (currentIndex + (shiftKey ? -1 : 1) + count) % count;
}

function restoreModalFocus(lastFocus, contains = (node) => document.contains(node)) {
  if (!lastFocus || typeof lastFocus.focus !== "function" || !contains(lastFocus)) return false;
  lastFocus.focus();
  return true;
}

function sparkline(values, positive) {
  const width = 110;
  const height = 20;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(1, max - min);
  const points = values.map((value, index) => {
    const x = (index / (values.length - 1)) * width;
    const y = height - 2 - ((value - min) / span) * (height - 4);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  const color = positive ? "#caff4d" : "#ff6b61";
  return `<svg class="sparkline" viewBox="0 0 ${width} ${height}" role="img" aria-label="${positive ? "upward" : "downward"} seven-point demo trend"><polyline points="${points}" fill="none" stroke="${color}" stroke-width="1.6" vector-effect="non-scaling-stroke"/></svg>`;
}

function renderWatchlist() {
  $("#watchlist").innerHTML = state.data.watchlist.map((item) => `
    <div class="watch-item" role="listitem">
      <div class="watch-top"><span class="watch-symbol">${escapeHTML(item.symbol)}</span><span class="watch-kind">${escapeHTML(item.kind)}</span></div>
      <div class="watch-bottom"><span class="watch-rating">${item.rating}</span><span class="delta ${item.delta >= 0 ? "up" : "down"}">${item.delta >= 0 ? "+" : ""}${item.delta}</span></div>
      ${sparkline(item.trend, item.delta >= 0)}
    </div>`).join("");
}

function renderFeatured() {
  const match = state.data.featured;
  $("#featured-match").innerHTML = `
    <div class="match-meta"><span class="live-dot">Sim live</span><span class="source-label">${escapeHTML(match.clock)}</span></div>
    <div class="match-title"><p class="eyebrow">${escapeHTML(match.channel)}</p><h2>${escapeHTML(match.title)}</h2><p class="match-subtitle">${escapeHTML(match.subtitle)}</p></div>
    <div class="scoreline" aria-label="Demo score ${match.left.score} to ${match.right.score}">
      <div class="score-side"><span class="score-name">${escapeHTML(match.left.name)}</span><strong class="score accent">${match.left.score}</strong></div>
      <span class="score-separator">—</span>
      <div class="score-side"><span class="score-name">${escapeHTML(match.right.name)}</span><strong class="score">${match.right.score}</strong></div>
    </div>
    <div class="match-actions"><button class="primary-button" type="button" data-proof-open="featured">Inspect proof</button><button class="secondary-button" type="button" data-demo-runback>Runback demo</button></div>`;
}

function renderTape() {
  $("#tape").innerHTML = state.data.tape.map((row) => `
    <div class="tape-row">
      <span class="tape-time">${escapeHTML(row.time)}</span>
      <div><p class="row-title">${escapeHTML(row.headline)}</p><p class="row-detail">${escapeHTML(row.channel)} · ${escapeHTML(row.detail)}</p></div>
      <span class="tone-dot ${escapeHTML(row.tone)}" aria-hidden="true"></span>
    </div>`).join("");
}

function renderChannels() {
  const rows = [...state.data.channels];
  if (state.followingFirst) rows.sort((a, b) => Number(b.followed) - Number(a.followed));
  $("#channels").innerHTML = rows.map((channel) => `
    <div class="channel-row" data-channel-id="${escapeHTML(channel.id)}">
      <div><p class="row-title">${escapeHTML(channel.name)}</p><p class="row-detail">${escapeHTML(channel.description)} · ${channel.viewers} demo viewers</p></div>
      <button class="follow-button ${channel.followed ? "is-followed" : ""}" type="button" data-follow="${escapeHTML(channel.id)}" aria-pressed="${channel.followed}">${channel.followed ? "Following" : "Follow"}</button>
    </div>`).join("");
}

function renderLeaderboard() {
  $("#leaderboard").innerHTML = state.data.leaderboard.map((row) => `
    <div class="leader-row">
      <span class="rank">${String(row.rank).padStart(2, "0")}</span>
      <div><p class="row-title">${escapeHTML(row.name)}</p><p class="row-detail">${escapeHTML(row.kind)} · ${escapeHTML(row.record)}</p></div>
      <div class="leader-metric"><strong class="leader-rating">${row.rating}</strong><span class="leader-proof">${row.verified} demo proofs</span></div>
    </div>`).join("");
}

function renderCompete() {
  $("#credit-readout").innerHTML = `<strong>${state.data.account.creditsRemaining}</strong>${escapeHTML(state.data.account.creditsLabel)}`;
  $("#quick-matches").innerHTML = state.data.quickMatches.map((match) => `
    <div class="quick-row">
      <div><span class="mode-label">${escapeHTML(match.mode)}</span><p class="row-title">${escapeHTML(match.title)}</p><p class="row-detail">${escapeHTML(match.duration)} · ${escapeHTML(match.cost)} · unranked</p></div>
      <button class="queue-button" type="button" data-queue="${escapeHTML(match.id)}">Enter demo</button>
    </div>`).join("");
  $("#free-models").innerHTML = state.data.freeModels.map((model) => `
    <div class="model-row"><div><p class="row-title">${escapeHTML(model.name)}</p><p class="row-detail">${escapeHTML(model.source)} · quota ${model.quota}</p></div><span class="model-status ${model.enabled ? "" : "disabled"}">${model.enabled ? escapeHTML(model.latency) : "Unavailable"}</span></div>`).join("");
}

function renderLessons() {
  $("#lessons").innerHTML = state.data.lessons.map((lesson) => `
    <button class="lesson-row" type="button" data-lesson="${escapeHTML(lesson.id)}">
      <span class="lesson-step ${lesson.progress === 100 ? "complete" : ""}">${lesson.progress === 100 ? "✓" : lesson.step}</span>
      <span><span class="row-title">${escapeHTML(lesson.title)}</span><span class="row-detail">${escapeHTML(lesson.level)} · ${escapeHTML(lesson.duration)}</span></span>
      <span class="progress-line" aria-label="${lesson.progress}% complete"><span style="width:${lesson.progress}%"></span></span>
    </button>`).join("");
}

function blueprintFromForm() {
  const form = new FormData($("#builder-form"));
  return {
    agentName: String(form.get("agentName") || "Untitled Agent").trim().slice(0, 36),
    baseModel: String(form.get("baseModel")),
    harnessStyle: String(form.get("harnessStyle")),
    strictValidation: form.has("strictValidation"),
    fallbackDisclosure: form.has("fallbackDisclosure"),
    humanCheckpoints: form.has("humanCheckpoints"),
    localOnly: true,
  };
}

function hydrateLocalBlueprint() {
  const raw = localStorage.getItem("builderwars.mobile-arena.blueprint.v1");
  if (!raw || raw.length > 2048) return;
  try {
    const blueprint = JSON.parse(raw);
    if (!blueprint || blueprint.localOnly !== true || typeof blueprint.agentName !== "string") return;
    const name = blueprint.agentName.trim().slice(0, 36);
    if (name) $("#agent-name").value = name;
    const baseOptions = [...$("#base-model").options].map((option) => option.value);
    if (baseOptions.includes(blueprint.baseModel)) $("#base-model").value = blueprint.baseModel;
    const harnessOptions = [...$("#harness-style").options].map((option) => option.value);
    if (harnessOptions.includes(blueprint.harnessStyle)) $("#harness-style").value = blueprint.harnessStyle;
    for (const key of ("strictValidation", "fallbackDisclosure", "humanCheckpoints")) {
      if (typeof blueprint[key] === "boolean") $(`[name="${key}"]`).checked = blueprint[key];
    }
  } catch {
    localStorage.removeItem("builderwars.mobile-arena.blueprint.v1");
  }
}

function renderBlueprint() {
  const blueprint = blueprintFromForm();
  const safeName = blueprint.agentName || "Untitled Agent";
  $("#preview-title").textContent = safeName;
  $(".blueprint-mark span").textContent = safeName.split(/\s+/).slice(0, 2).map((part) => part[0] || "").join("").toUpperCase() || "UA";
  $("#blueprint-details").innerHTML = `
    <div><dt>Demo base</dt><dd>${escapeHTML(blueprint.baseModel)}</dd></div>
    <div><dt>Harness</dt><dd>${escapeHTML(blueprint.harnessStyle)}</dd></div>
    <div><dt>Move validation</dt><dd>${blueprint.strictValidation ? "Strict" : "Off"}</dd></div>
    <div><dt>Human checkpoints</dt><dd>${blueprint.humanCheckpoints ? "Declared" : "None"}</dd></div>`;
  return blueprint;
}

function renderAutomations() {
  $("#automations").innerHTML = state.data.automations.map((automation) => `
    <div class="automation-row"><div><p class="row-title">${escapeHTML(automation.name)}</p><p class="row-detail">${escapeHTML(automation.schedule)} · ${escapeHTML(automation.scope)}</p></div><label class="switch-row" aria-label="Toggle ${escapeHTML(automation.name)}"><input type="checkbox" data-automation="${escapeHTML(automation.id)}" ${automation.enabled ? "checked" : ""}></label></div>`).join("");
}

function renderProof() {
  const proof = state.data.featured.proof;
  const rows = [
    ["Replay", proof.replayVerdict, "pass"],
    ["Registry", "Pending registry commit", "pending"],
    ["Harness version", proof.harnessVersionBound ? "Bound in demo fixture" : "Not bound", proof.harnessVersionBound ? "pass" : ""],
    ["Model attested", proof.modelAttested ? "Yes" : "No", ""],
    ["Provider attested", proof.providerAttested ? "Yes" : "No", ""],
    ["Runtime attested", proof.runtimeAttested ? "Yes" : "No", ""],
    ["Human interventions", proof.humanInterventions, ""],
    ["Fallback moves", proof.fallbackMoves, ""],
    ["Receipt", proof.receiptId, ""],
  ];
  $("#proof-content").innerHTML = `<div class="proof-grid">${rows.map(([label, value, tone]) => `<div class="proof-row"><span>${escapeHTML(label)}</span><strong class="${tone}">${escapeHTML(value)}</strong></div>`).join("")}</div><div class="proof-boundary"><strong>Demo boundary:</strong> this fixture demonstrates the product language only. It is not a public receipt, live match, provider/model attestation, ranked result, or registry commit.</div>`;
}

function showView(name, updateHash = true) {
  if (!$("#view-" + name)) return;
  state.activeView = name;
  $$(".view").forEach((view) => {
    const active = view.dataset.view === name;
    view.hidden = !active;
    view.classList.toggle("is-active", active);
  });
  $$('[data-nav]').forEach((control) => {
    const active = control.dataset.nav === name;
    control.classList.toggle("is-active", active);
    if (control.classList.contains("nav-item")) {
      if (active) control.setAttribute("aria-current", "page");
      else control.removeAttribute("aria-current");
    }
  });
  if (updateHash) history.replaceState(null, "", `#${name}`);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function openSheet(sheet) {
  state.lastFocus = document.activeElement;
  $$(".bottom-sheet").forEach((candidate) => { candidate.hidden = candidate !== sheet; });
  $("#app-shell").inert = true;
  $("#sheet-backdrop").hidden = false;
  sheet.hidden = false;
  document.body.style.overflow = "hidden";
  const focusable = $("button", sheet);
  if (focusable) focusable.focus();
}

function closeSheets() {
  $$(".bottom-sheet").forEach((sheet) => { sheet.hidden = true; });
  $("#sheet-backdrop").hidden = true;
  $("#app-shell").inert = false;
  document.body.style.overflow = "";
  restoreModalFocus(state.lastFocus);
}

function trapSheetFocus(event) {
  if (event.key !== "Tab") return;
  const sheet = $(".bottom-sheet:not([hidden])");
  if (!sheet) return;
  const focusables = $$('button:not([disabled]), input:not([disabled]), select:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])', sheet)
    .filter((element) => !element.hidden && element.getAttribute("aria-hidden") !== "true");
  if (focusables.length === 0) {
    event.preventDefault();
    sheet.focus();
    return;
  }
  const currentIndex = focusables.indexOf(document.activeElement);
  const nextIndex = nextModalFocusIndex(currentIndex, focusables.length, event.shiftKey);
  event.preventDefault();
  focusables[nextIndex].focus();
}

let toastTimer;
function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.hidden = false;
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => { toast.hidden = true; }, 3600);
}

function bindEvents() {
  document.addEventListener("click", (event) => {
    const nav = event.target.closest("[data-nav]");
    if (nav) { event.preventDefault(); showView(nav.dataset.nav); return; }
    const proof = event.target.closest("[data-proof-open]");
    if (proof) { renderProof(); openSheet($("#proof-sheet")); return; }
    if (event.target.closest("[data-sheet-close]") || event.target === $("#sheet-backdrop")) { closeSheets(); return; }
    const follow = event.target.closest("[data-follow]");
    if (follow) {
      const channel = state.data.channels.find((item) => item.id === follow.dataset.follow);
      if (channel) { channel.followed = !channel.followed; renderChannels(); showToast(channel.followed ? `Following ${channel.name} in this demo.` : `Removed ${channel.name} from this demo watchlist.`); }
      return;
    }
    const queue = event.target.closest("[data-queue]");
    if (queue) { showToast("Demo entry created. No model, provider, quota, or ranked queue was used."); return; }
    if (event.target.closest("[data-demo-runback]")) { showToast("Runback preview only — verified replay remains pending registry commit."); return; }
    const lesson = event.target.closest("[data-lesson]");
    if (lesson) {
      const row = state.data.lessons.find((item) => item.id === lesson.dataset.lesson);
      if (row) { $("#lesson-focus h2").textContent = row.title; $("#lesson-focus p:not(.eyebrow)").textContent = `${row.level} lab · ${row.duration}. Progress is stored only in this demo fixture.`; }
    }
  });

  $("#notifications-button").addEventListener("click", () => openSheet($("#automations-sheet")));
  $("#profile-button").addEventListener("click", () => showToast("Local Builder profile · no account is connected."));
  $("#watch-filter").addEventListener("click", () => { state.followingFirst = !state.followingFirst; $("#watch-filter").textContent = state.followingFirst ? "Default order" : "Following first"; renderChannels(); });
  $("#builder-form").addEventListener("input", renderBlueprint);
  $("#builder-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const blueprint = renderBlueprint();
    localStorage.setItem("builderwars.mobile-arena.blueprint.v1", JSON.stringify(blueprint));
    showToast("Blueprint saved locally. It was not uploaded, paired, executed, or published.");
  });
  $("#automations").addEventListener("change", (event) => {
    const input = event.target.closest("[data-automation]");
    if (!input) return;
    const row = state.data.automations.find((item) => item.id === input.dataset.automation);
    if (row) row.enabled = input.checked;
    showToast("Local demo preference updated. No background automation is running.");
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeSheets();
    else trapSheetFocus(event);
  });
}

function renderAll() {
  renderWatchlist();
  renderFeatured();
  renderTape();
  renderChannels();
  renderLeaderboard();
  renderCompete();
  renderLessons();
  renderBlueprint();
  renderAutomations();
}

async function boot() {
  try {
    const response = await fetch("data/demo-state.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`fixture request failed: ${response.status}`);
    const data = await response.json();
    if (data.demoOnly !== true || data.sourceStatus !== "local_fixture_not_live") throw new Error("unsafe fixture truth boundary");
    state.data = data;
    hydrateLocalBlueprint();
    renderAll();
    bindEvents();
    showView(location.hash.slice(1) || "arena", false);
    if ("serviceWorker" in navigator && location.protocol.startsWith("http")) navigator.serviceWorker.register("sw.js").catch(() => {});
  } catch (error) {
    $("#workspace").innerHTML = `<section class="view is-active"><p class="eyebrow">Demo unavailable</p><h1>Local fixture could not load.</h1><p class="match-subtitle">Serve this directory with a local HTTP server, then refresh. No live service fallback will be attempted.</p><pre class="fine-print">${escapeHTML(error.message)}</pre></section>`;
  }
}

if (typeof document !== "undefined") boot();
if (typeof module !== "undefined" && module.exports) {
  module.exports = { nextModalFocusIndex, restoreModalFocus };
}
