"use strict";

const state = {
  data: null,
  activeView: "arena",
  followingFirst: false,
  activeLesson: null,
  selectedProofId: null,
  qualificationPreview: null,
  learningAction: null,
  runbackProposal: null,
  lastFocus: null,
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const VIEW_NAMES = ["arena", "watch", "compete", "learn", "build"];
const BLUEPRINT_STORAGE_KEY = "builderwars.mobile-arena.blueprint.v1";
const BLUEPRINT_MAX_LENGTH = 2048;
const BLUEPRINT_GUARD_KEYS = ["strictValidation", "fallbackDisclosure", "humanCheckpoints"];
const RECEIPT_ROUTE_ID = /^[A-Za-z0-9_-]{1,80}$/;
const escapeHTML = (value) => String(value).replace(/[&<>'"]/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
}[character]));
const dataAdapter = typeof BuilderWarsDataAdapter !== "undefined" ? BuilderWarsDataAdapter : null;

function formatArenaRoute(view, receiptId = null) {
  const safeView = VIEW_NAMES.includes(view) ? view : "arena";
  if (!receiptId) return `#${safeView}`;
  if (!RECEIPT_ROUTE_ID.test(String(receiptId))) return `#${safeView}`;
  return `#${safeView}/receipt/${receiptId}`;
}

function parseArenaRoute(hash) {
  const parts = String(hash || "").replace(/^#/, "").split("/");
  if (!VIEW_NAMES.includes(parts[0])) return null;
  if (parts.length === 1) return { view: parts[0], receiptId: null };
  if (parts.length === 3 && parts[1] === "receipt" && RECEIPT_ROUTE_ID.test(parts[2])) {
    return { view: parts[0], receiptId: parts[2] };
  }
  return null;
}

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
      <div class="watch-bottom"><span class="watch-rating">${item.rating}</span>${item.delta === null ? `<span class="watch-evidence">${escapeHTML(item.metricLabel)}</span>` : `<span class="delta ${item.delta >= 0 ? "up" : "down"}">${item.delta >= 0 ? "+" : ""}${item.delta}</span>`}</div>
      ${Array.isArray(item.trend) ? sparkline(item.trend, item.delta >= 0) : `<span class="receipt-track" aria-label="Reviewed receipt count">verified local corpus</span>`}
    </div>`).join("");
}

function renderFeatured() {
  const match = state.data.featured;
  const verified = state.data.sourceMode === "verified_corpus";
  $("#featured-match").innerHTML = `
    <div class="match-meta"><span class="${verified ? "receipt-dot" : "live-dot"}">${escapeHTML(match.statusLabel || "Sim live")}</span><span class="source-label">${escapeHTML(match.clock)}</span></div>
    <div class="match-title"><p class="eyebrow">${escapeHTML(match.channel)}</p><h2>${escapeHTML(match.title)}</h2><p class="match-subtitle">${escapeHTML(match.subtitle)}</p></div>
    <div class="scoreline" aria-label="${escapeHTML(match.scoreAriaLabel || `Demo score ${match.left.score} to ${match.right.score}`)}">
      <div class="score-side"><span class="score-name">${escapeHTML(match.left.name)}</span><strong class="score accent">${match.left.score}</strong></div>
      <span class="score-separator">—</span>
      <div class="score-side"><span class="score-name">${escapeHTML(match.right.name)}</span><strong class="score">${match.right.score}</strong></div>
    </div>
    <div class="match-actions"><a class="primary-button" href="${formatArenaRoute("arena", match.proof.receiptId)}" data-proof-open="${escapeHTML(match.proof.receiptId || "featured")}">Inspect proof</a><button class="secondary-button" type="button" data-runback-preview ${match.runbackAvailable ? "" : "aria-disabled=\"true\""}>${escapeHTML(match.runbackLabel || "Runback preview")}</button></div>`;
  $("#featured-match").setAttribute("aria-label", verified ? "Featured reviewed receipt" : "Featured simulated match");
}

function renderTape() {
  $("#tape").innerHTML = state.data.tape.map((row) => `
    <div class="tape-row">
      <span class="tape-time">${escapeHTML(row.time)}</span>
      <div><p class="row-title">${escapeHTML(row.headline)}</p><p class="row-detail">${escapeHTML(row.channel)} · ${escapeHTML(row.detail)}</p></div>
      ${row.receiptId ? `<a class="proof-link" href="${formatArenaRoute("arena", row.receiptId)}" data-proof-open="${escapeHTML(row.receiptId)}" aria-label="Inspect proof for ${escapeHTML(row.headline)}">Proof</a>` : `<span class="tone-dot ${escapeHTML(row.tone)}" aria-hidden="true"></span>`}
    </div>`).join("");
}

function renderChannels() {
  const rows = [...state.data.channels];
  if (state.followingFirst) rows.sort((a, b) => Number(b.followed) - Number(a.followed));
  $("#channels").innerHTML = rows.map((channel) => `
    <div class="channel-row" data-channel-id="${escapeHTML(channel.id)}">
      <div><p class="row-title">${escapeHTML(channel.name)}</p><p class="row-detail">${escapeHTML(channel.description)}${Number.isInteger(channel.viewers) ? ` · ${channel.viewers} demo viewers` : ""}</p></div>
      <button class="follow-button ${channel.followed ? "is-followed" : ""}" type="button" data-follow="${escapeHTML(channel.id)}" aria-pressed="${channel.followed}">${channel.followed ? "Following" : "Follow"}</button>
    </div>`).join("");
}

function renderLeaderboard() {
  $("#leaderboard").innerHTML = state.data.leaderboard.map((row) => `
    <div class="leader-row">
      <span class="rank">${row.position || String(row.rank).padStart(2, "0")}</span>
      <div><p class="row-title">${escapeHTML(row.name)}</p><p class="row-detail">${escapeHTML(row.kind)} · ${escapeHTML(row.record)}</p></div>
      <div class="leader-metric"><strong class="leader-rating">${escapeHTML(row.metric || row.rating)}</strong><span class="leader-proof">${row.verified} ${state.data.sourceMode === "verified_corpus" ? "reviewed receipts" : "demo proofs"}</span></div>
    </div>`).join("");
}

function renderRivalries() {
  const container = $("#rivalries");
  if (!container) return;
  if (!state.data.rivalries?.length) {
    container.innerHTML = `<div class="empty-state"><strong>No reviewed rivalries in this source.</strong><span>Demo fallback does not invent rivalry history.</span></div>`;
    return;
  }
  container.innerHTML = state.data.rivalries.map((rivalry) => `
    <div class="rivalry-row">
      <div><span class="mode-label">${escapeHTML(rivalry.competition)}</span><p class="row-title">${escapeHTML(rivalry.title)}</p><p class="row-detail">${escapeHTML(rivalry.record)} · ${rivalry.meetingCount} reviewed meeting${rivalry.meetingCount === 1 ? "" : "s"} · ${rivalry.pendingRunbackCount} pending runback${rivalry.pendingRunbackCount === 1 ? "" : "s"}</p></div>
      <a class="proof-link" href="${formatArenaRoute("watch", rivalry.latestReceiptId)}" data-proof-open="${escapeHTML(rivalry.latestReceiptId)}" aria-label="Inspect latest reviewed receipt for ${escapeHTML(rivalry.title)}">Latest</a>
    </div>`).join("");
}

function renderCompete() {
  $("#credit-readout").innerHTML = `<strong>${state.data.account.creditsRemaining}</strong>${escapeHTML(state.data.account.creditsLabel)}`;
  $("#quick-matches").innerHTML = state.data.quickMatches.map((match) => `
    <div class="quick-row">
      <div><span class="mode-label">${escapeHTML(match.mode)}</span><p class="row-title">${escapeHTML(match.title)}</p><p class="row-detail">${escapeHTML(match.duration)} · ${escapeHTML(match.cost)} · unranked</p></div>
      ${match.previewAllowed ? `<button class="queue-button preview" type="button" data-qualification-preview="${escapeHTML(match.id)}">${escapeHTML(match.actionLabel)}</button>` : `<button class="queue-button" type="button" data-queue="${escapeHTML(match.id)}">${escapeHTML(match.actionLabel || "Enter demo")}</button>`}
    </div>`).join("");
  $("#free-models").innerHTML = state.data.freeModels.map((model) => `
    <div class="model-row"><div><p class="row-title">${escapeHTML(model.name)}</p><p class="row-detail">${escapeHTML(model.source)} · quota ${model.quota}</p></div><span class="model-status ${model.enabled ? "" : "disabled"}">${model.enabled ? escapeHTML(model.latency) : "Unavailable"}</span></div>`).join("");
}

function renderLessons() {
  if (!state.activeLesson) {
    state.activeLesson = state.data.lessons.find((lesson) => lesson.progress > 0 && lesson.progress < 100)?.id
      || state.data.lessons[0]?.id
      || null;
  }
  $("#lessons").innerHTML = state.data.lessons.map((lesson) => `
    <button class="lesson-row ${lesson.id === state.activeLesson ? "is-active" : ""}" type="button" data-lesson="${escapeHTML(lesson.id)}" ${lesson.id === state.activeLesson ? 'aria-current="step"' : ""}>
      <span class="lesson-step ${lesson.progress === 100 ? "complete" : ""}">${lesson.progress === 100 ? "✓" : lesson.step}</span>
      <span class="lesson-copy"><span class="row-title">${escapeHTML(lesson.title)}</span><span class="row-detail">${escapeHTML(lesson.level)} · ${escapeHTML(lesson.duration)}</span></span>
      <span class="progress-line" aria-label="${lesson.progress}% complete"><span style="width:${lesson.progress}%"></span></span>
    </button>`).join("");
}

function renderReceiptLearning() {
  const container = $("#receipt-learning");
  if (!container) return;
  const action = state.learningAction;
  if (!action) {
    container.innerHTML = `<div class="empty-state receipt-learning-empty"><strong>Open a reviewed receipt to begin.</strong><span>The lab will summarize visible evidence and offer bounded blueprint deltas. It never reads private reasoning.</span></div>`;
    return;
  }
  const counts = action.receipt.moveSourceCounts;
  const deltaControls = action.allowedDeltas.map((delta) => `
    <button class="learning-delta ${delta.id === action.recommendedDeltaId ? "recommended" : ""}" type="button" data-runback-delta="${escapeHTML(delta.id)}">
      <span>${escapeHTML(delta.label)}</span><small>${escapeHTML(delta.rationale)}${delta.id === action.recommendedDeltaId ? " · receipt-guided" : ""}</small>
    </button>`).join("");
  const proposal = state.runbackProposal;
  let proposalMarkup = "";
  if (proposal) {
    const rows = [
      ["Status", "Unplayed proposal", "pending"],
      ["Parent receipt", proposal.parentReceipt.receiptId, "mono"],
      ["Challenge", proposal.runbackLineage.challengeId, "mono"],
      ["Runback fixture", proposal.runbackLineage.fixtureId, "mono"],
      ["Game", `${proposal.gameBinding.name} v${proposal.gameBinding.version}`, ""],
      ["Rules", "Blocked · explicit digest missing", "pending"],
      ["Blueprint delta", proposal.blueprintDelta.label, ""],
      ["Change", proposal.blueprintDelta.changeStatus === "already_declared" ? "Already declared · retain" : "Proposed false → true", ""],
      ["Qualification", "Not run", "pending"],
      ["Execution", "Disabled", "pending"],
      ["Attestations", "Identity/model/provider/runtime/registry/publication: all false", ""],
    ];
    proposalMarkup = `<div class="runback-proposal" id="runback-proposal"><div class="qualification-status"><span>Version 1 · local only</span><strong>Still unplayed</strong></div><div class="proof-grid">${rows.map(([label, value, tone]) => `<div class="proof-row"><span>${escapeHTML(label)}</span><strong class="${tone}">${escapeHTML(value)}</strong></div>`).join("")}</div><div class="proposal-blockers"><strong>Execution blockers</strong><span>${escapeHTML(proposal.executionBlockers.join(" · "))}</span></div><div class="proof-boundary"><strong>Proposal boundary:</strong> ${escapeHTML(proposal.boundary)} ${escapeHTML(proposal.rulesBinding.statement)}</div><button class="text-button" type="button" data-runback-blueprint>Review local blueprint</button></div>`;
  }
  container.innerHTML = `<div class="learning-receipt"><span class="mode-label">${escapeHTML(action.receipt.game.name)} v${escapeHTML(action.receipt.game.version)}</span><h3>${escapeHTML(action.receipt.headline)}</h3><code>${escapeHTML(action.receipt.receiptId)}</code><p>${escapeHTML(action.observation)}</p><p class="row-detail">Visible sources · model ${counts.model} · scripted ${counts.scripted} · fallback ${counts.fallback} · other ${counts.other}</p><div class="learning-boundary">${escapeHTML(action.boundary)}</div></div><div class="learning-deltas"><p class="eyebrow">Choose one declared blueprint delta</p>${deltaControls}</div>${proposalMarkup}`;
}

function updateConnectionStatus() {
  const status = $("#connection-status");
  if (!status || !state.data) return;
  const online = navigator.onLine;
  const verified = state.data.sourceMode === "verified_corpus";
  status.dataset.state = online ? "ready" : "offline";
  const sourceName = verified ? "verified corpus" : "demo fallback";
  $("#connection-copy").textContent = online ? `${sourceName} ready` : `Offline · ${sourceName} ready`;
  status.setAttribute(
    "aria-label",
    online
      ? `Browser reports online. Local ${sourceName} loaded. No provider is connected.`
      : `Browser reports offline. Local ${sourceName} remains available. No provider is connected.`,
  );
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
  try {
    const raw = localStorage.getItem(BLUEPRINT_STORAGE_KEY);
    if (!raw) return;
    if (raw.length > BLUEPRINT_MAX_LENGTH) {
      localStorage.removeItem(BLUEPRINT_STORAGE_KEY);
      return;
    }
    const blueprint = JSON.parse(raw);
    if (!blueprint || blueprint.localOnly !== true || typeof blueprint.agentName !== "string") {
      localStorage.removeItem(BLUEPRINT_STORAGE_KEY);
      return;
    }
    const name = blueprint.agentName.trim().slice(0, 36);
    if (name) $("#agent-name").value = name;
    const baseOptions = [...$("#base-model").options].map((option) => option.value);
    if (baseOptions.includes(blueprint.baseModel)) $("#base-model").value = blueprint.baseModel;
    const harnessOptions = [...$("#harness-style").options].map((option) => option.value);
    if (harnessOptions.includes(blueprint.harnessStyle)) $("#harness-style").value = blueprint.harnessStyle;
    for (const key of BLUEPRINT_GUARD_KEYS) {
      if (typeof blueprint[key] === "boolean") $(`[name="${key}"]`).checked = blueprint[key];
    }
  } catch {
    try { localStorage.removeItem(BLUEPRINT_STORAGE_KEY); } catch {}
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
  const qualificationStatus = $("#blueprint-qualification-status");
  if (qualificationStatus) {
    qualificationStatus.textContent = blueprint.strictValidation && blueprint.fallbackDisclosure
      ? "Preview ready · not run"
      : "Guards needed · not run";
    qualificationStatus.classList.toggle("ready", blueprint.strictValidation && blueprint.fallbackDisclosure);
  }
  return blueprint;
}

function renderAutomations() {
  $("#automations").innerHTML = state.data.automations.map((automation) => `
    <div class="automation-row"><div><p class="row-title">${escapeHTML(automation.name)}</p><p class="row-detail">${escapeHTML(automation.schedule)} · ${escapeHTML(automation.scope)}</p></div><label class="switch-row" aria-label="Toggle ${escapeHTML(automation.name)}"><input type="checkbox" data-automation="${escapeHTML(automation.id)}" ${automation.enabled ? "checked" : ""}></label></div>`).join("");
}

function resolveProof(proofId) {
  if (!proofId || proofId === "featured") return state.data.featured.proof;
  return state.data.proofReceipts?.find((proof) => proof.receiptId === proofId) || null;
}

function renderProof(proofId = "featured") {
  const proof = resolveProof(proofId);
  if (!proof) return false;
  state.selectedProofId = proof.receiptId || null;
  $("#proof-title").textContent = proof.headline || "What this result proves";
  let rows;
  if (state.data.sourceMode === "verified_corpus") {
    const counts = proof.moveSourceCounts;
    rows = [
      ["Replay", proof.replayVerdict, proof.replayVerdict === "PASS" ? "pass" : ""],
      ["Publication allowlist", proof.publicationApproved ? "Approved" : "Not approved", proof.publicationApproved ? "pass" : ""],
      ["Engine digest", proof.engineDigestMatch ? "Match" : "Mismatch", proof.engineDigestMatch ? "pass" : ""],
      ["Verifier snapshot", proof.verifierSnapshotMatch ? "Match" : "Mismatch", proof.verifierSnapshotMatch ? "pass" : ""],
      ["Evidence class", proof.evidenceLabel, ""],
      ["Move sources", `model ${counts.model} · scripted ${counts.scripted} · fallback ${counts.fallback} · other ${counts.other}`, ""],
      ["Harness version", proof.harnessVersionBound ? "Content-bound" : "Not bound", proof.harnessVersionBound ? "pass" : ""],
      ["Registry", "No authoritative commit", "pending"],
      ["Model attested", proof.modelAttested ? "Yes" : "No", ""],
      ["Provider attested", proof.providerAttested ? "Yes" : "No", ""],
      ["Runtime attested", proof.runtimeAttested ? "Yes" : "No", ""],
      ["Receipt", proof.receiptId, ""],
      ["Fixture", proof.fixtureId, ""],
      ["Replay artifact", proof.artifactPath, ""],
    ];
  } else {
    rows = [
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
  }
  const boundaryLabel = state.data.sourceMode === "verified_corpus" ? "Verified-corpus boundary" : "Demo boundary";
  const address = formatArenaRoute(state.activeView, proof.receiptId);
  $("#proof-content").innerHTML = `<div class="proof-grid">${rows.map(([label, value, tone]) => `<div class="proof-row"><span>${escapeHTML(label)}</span><strong class="${tone}">${escapeHTML(value)}</strong></div>`).join("")}</div><div class="proof-address"><span>Local proof address</span><code>${escapeHTML(address)}</code></div><div class="proof-boundary"><strong>${boundaryLabel}:</strong> ${escapeHTML(proof.boundary || state.data.truthBoundary.statement)}</div>`;
  const learningButton = $("#proof-learning-button");
  learningButton.hidden = !(state.data.sourceMode === "verified_corpus" && proof.runback);
  learningButton.dataset.proofLearn = proof.receiptId || "";
  return true;
}

function openReceiptProof(proofId, { updateHistory = true } = {}) {
  const proof = resolveProof(proofId);
  if (!proof || !renderProof(proof.receiptId)) {
    showToast("That receipt is not present in this bounded local source.");
    return false;
  }
  if (updateHistory) {
    const address = formatArenaRoute(state.activeView, proof.receiptId);
    if (location.hash !== address) {
      history.pushState({ view: state.activeView, overlay: "receipt", receiptId: proof.receiptId }, "", address);
    }
  }
  if ($("#proof-sheet").hidden) openSheet($("#proof-sheet"));
  return true;
}

function renderQualificationPreview(fixtureId) {
  const fixture = state.data.quickMatches.find((match) => match.id === fixtureId);
  if (!fixture || !dataAdapter?.buildQualificationPreview) return false;
  let preview;
  try {
    preview = dataAdapter.buildQualificationPreview(blueprintFromForm(), fixture, state.data.sourceMode);
  } catch {
    return false;
  }
  state.qualificationPreview = preview;
  $("#qualification-title").textContent = fixture.title;
  const rows = [
    ["Qualification", "Not run", "pending"],
    ["Execution", "Disabled", "pending"],
    ["Blueprint", preview.blueprint.agentName, ""],
    ["Declared demo base", preview.blueprint.declaredBase, ""],
    ["Game", `${preview.fixture.game.name} v${preview.fixture.game.version}`, ""],
    ["Rules week", preview.fixture.rulesWeekId, ""],
    ["Rules digest", preview.fixture.rulesDigest, "mono"],
    ["Resource class", preview.resourceClass.label, ""],
    ["Fixture", "Proposed · not activated", "pending"],
    ["Attestations", "Identity/model/provider/runtime/registry/publication: all false", ""],
  ];
  const checks = preview.readinessChecks.map((check) => `<li class="qualification-check ${check.ready ? "ready" : "needs-attention"}"><span>${check.ready ? "✓" : "!"}</span><div><strong>${escapeHTML(check.label)}</strong><small>${escapeHTML(check.status)}</small></div></li>`).join("");
  $("#qualification-content").innerHTML = `<div class="qualification-status"><span>Deterministic local preview</span><strong>${preview.readiness === "blueprint_ready_for_future_attempt" ? "Blueprint guards ready" : "Blueprint guards need attention"}</strong></div><div class="proof-grid">${rows.map(([label, value, tone]) => `<div class="proof-row"><span>${escapeHTML(label)}</span><strong class="${tone}">${escapeHTML(value)}</strong></div>`).join("")}</div><ul class="qualification-checks" aria-label="Qualification preview checks">${checks}</ul><div class="proof-boundary"><strong>Preview boundary:</strong> ${escapeHTML(preview.boundary)}</div>`;
  return true;
}

function prepareReceiptLearning(receiptId) {
  const proof = resolveProof(receiptId);
  if (!proof || !dataAdapter?.buildReceiptLearningAction) return false;
  try {
    state.learningAction = dataAdapter.buildReceiptLearningAction(proof, state.data.sourceMode);
    state.runbackProposal = null;
    renderReceiptLearning();
    return true;
  } catch {
    return false;
  }
}

function prepareRunbackProposal(deltaId) {
  if (!state.learningAction || !dataAdapter?.buildRunbackProposal) return false;
  try {
    state.runbackProposal = dataAdapter.buildRunbackProposal(state.learningAction, blueprintFromForm(), deltaId, state.data.sourceMode);
    renderReceiptLearning();
    return true;
  } catch {
    return false;
  }
}

function showView(name, updateHistory = true) {
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
  const address = formatArenaRoute(name);
  if (updateHistory && location.hash !== address) history.pushState({ view: name }, "", address);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function syncViewFromLocation({ replaceInvalid = false } = {}) {
  const route = parseArenaRoute(location.hash);
  if (route) {
    showView(route.view, false);
    if (route.receiptId) {
      if (!openReceiptProof(route.receiptId, { updateHistory: false })) {
        closeSheets({ restoreFocus: false });
        history.replaceState({ view: route.view }, "", formatArenaRoute(route.view));
      }
    } else if (!$("#proof-sheet").hidden) {
      closeSheets({ restoreFocus: false });
    }
    return;
  }
  const target = location.hash.slice(1);
  if (target && document.getElementById(target)) return;
  showView("arena", false);
  if (replaceInvalid) history.replaceState({ view: "arena" }, "", formatArenaRoute("arena"));
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

function closeSheets({ restoreFocus = true } = {}) {
  $$(".bottom-sheet").forEach((sheet) => { sheet.hidden = true; });
  $("#sheet-backdrop").hidden = true;
  $("#app-shell").inert = false;
  document.body.style.overflow = "";
  state.selectedProofId = null;
  if (restoreFocus) restoreModalFocus(state.lastFocus);
}

function dismissActiveSheet() {
  const route = parseArenaRoute(location.hash);
  if (!$("#proof-sheet").hidden && route?.receiptId) {
    if (history.state?.overlay === "receipt") {
      history.back();
      return;
    }
    history.replaceState({ view: route.view }, "", formatArenaRoute(route.view));
  }
  closeSheets();
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

function renderSourceChrome() {
  const verified = state.data.sourceMode === "verified_corpus";
  document.body.dataset.sourceMode = state.data.sourceMode;
  $("#source-badge").textContent = state.data.sourceMeta.badge;
  $("#source-badge").title = verified
    ? "Reviewed local receipts; not hosted, authenticated, or live"
    : "Verified corpus unavailable or invalid; bounded demo fixture loaded";
  $("#tape-source-label").textContent = verified ? "reviewed receipts" : "simulated fixture";
  $("#channels-source-label").textContent = verified ? "receipt channels" : "demo audiences";
  $("#standings-title").textContent = verified ? "Receipt board" : "Harness board";
  $("#standings-help").textContent = verified ? "Why this is not a ranking" : "How ranking works";
  $("#quick-source-label").textContent = verified ? "proposed · inactive" : "unranked demo";
  $("#learn-proof-button").textContent = verified ? "Inspect a reviewed receipt" : "Inspect the demo receipt";
  $("#credit-readout").setAttribute("aria-label", verified ? "No live credits. Competition entry is disabled." : "Simulated demo credits");
}

function bindEvents() {
  document.addEventListener("click", (event) => {
    const nav = event.target.closest("[data-nav]");
    if (nav) { event.preventDefault(); showView(nav.dataset.nav); return; }
    const proof = event.target.closest("[data-proof-open]");
    if (proof) { event.preventDefault(); openReceiptProof(proof.dataset.proofOpen); return; }
    if (event.target.closest("[data-sheet-close]") || event.target === $("#sheet-backdrop")) { dismissActiveSheet(); return; }
    const follow = event.target.closest("[data-follow]");
    if (follow) {
      const channel = state.data.channels.find((item) => item.id === follow.dataset.follow);
      if (channel) {
        channel.followed = !channel.followed;
        renderChannels();
        const suffix = state.data.sourceMode === "verified_corpus" ? "in this local view" : "in this demo";
        showToast(channel.followed ? `Following ${channel.name} ${suffix}.` : `Removed ${channel.name} from this local watchlist.`);
      }
      return;
    }
    const queue = event.target.closest("[data-queue]");
    if (queue) {
      showToast(state.data.sourceMode === "verified_corpus"
        ? "This proposed fixture is not activated. No queue, model, provider, or credit was used."
        : "Demo entry created. No model, provider, quota, or ranked queue was used.");
      return;
    }
    const qualification = event.target.closest("[data-qualification-preview]");
    if (qualification) {
      if (renderQualificationPreview(qualification.dataset.qualificationPreview)) openSheet($("#qualification-sheet"));
      else showToast("Qualification preview is unavailable in this bounded source. Nothing was executed.");
      return;
    }
    const proofLearning = event.target.closest("[data-proof-learn]");
    if (proofLearning) {
      const receiptId = proofLearning.dataset.proofLearn || state.selectedProofId;
      if (!prepareReceiptLearning(receiptId)) {
        showToast("Receipt learning is unavailable in this bounded source.");
        return;
      }
      closeSheets({ restoreFocus: false });
      showView("learn");
      $("#receipt-learning-title").focus({ preventScroll: true });
      $("#receipt-learning").scrollIntoView({ block: "start", behavior: "smooth" });
      return;
    }
    const runbackDelta = event.target.closest("[data-runback-delta]");
    if (runbackDelta) {
      if (prepareRunbackProposal(runbackDelta.dataset.runbackDelta)) {
        $("#runback-proposal").scrollIntoView({ block: "nearest", behavior: "smooth" });
      } else {
        showToast("The runback proposal failed closed. Nothing was executed or saved.");
      }
      return;
    }
    if (event.target.closest("[data-runback-blueprint]")) {
      showView("build");
      $("#agent-name").focus();
      return;
    }
    if (event.target.closest("[data-qualification-edit]")) {
      closeSheets({ restoreFocus: false });
      showView("build");
      $("#agent-name").focus();
      return;
    }
    if (event.target.closest("[data-runback-preview]")) {
      showToast(state.data.sourceMode === "verified_corpus"
        ? "Runback lineage is visible, but no authoritative runback is activated."
        : "Runback preview only — verified replay remains pending registry commit.");
      return;
    }
    const lesson = event.target.closest("[data-lesson]");
    if (lesson) {
      const row = state.data.lessons.find((item) => item.id === lesson.dataset.lesson);
      if (row) {
        state.activeLesson = row.id;
        $$('[data-lesson]').forEach((control) => {
          const active = control.dataset.lesson === row.id;
          control.classList.toggle("is-active", active);
          if (active) control.setAttribute("aria-current", "step");
          else control.removeAttribute("aria-current");
        });
        $("#lesson-focus h2").textContent = row.title;
        $("#lesson-focus p:not(.eyebrow)").textContent = `${row.level} lab · ${row.duration}. Progress is stored only in this demo fixture.`;
      }
    }
  });

  $("#notifications-button").addEventListener("click", () => openSheet($("#automations-sheet")));
  $("#profile-button").addEventListener("click", () => showToast("Local Builder profile · no account, identity, or provider is connected."));
  $("#watch-filter").addEventListener("click", () => { state.followingFirst = !state.followingFirst; $("#watch-filter").textContent = state.followingFirst ? "Default order" : "Following first"; renderChannels(); });
  $("#builder-form").addEventListener("input", renderBlueprint);
  $("#builder-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const blueprint = renderBlueprint();
    try {
      localStorage.setItem(BLUEPRINT_STORAGE_KEY, JSON.stringify(blueprint));
      showToast("Blueprint saved locally. Preview a proposed fixture next; no qualification or execution occurred.");
    } catch {
      showToast("Blueprint could not be saved in this browser. Nothing was uploaded or executed.");
    }
  });
  $("#automations").addEventListener("change", (event) => {
    const input = event.target.closest("[data-automation]");
    if (!input) return;
    const row = state.data.automations.find((item) => item.id === input.dataset.automation);
    if (row) row.enabled = input.checked;
    showToast("Local demo preference updated. No background automation is running.");
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") dismissActiveSheet();
    else trapSheetFocus(event);
  });
  window.addEventListener("online", updateConnectionStatus);
  window.addEventListener("offline", updateConnectionStatus);
  window.addEventListener("popstate", () => syncViewFromLocation({ replaceInvalid: true }));
  window.addEventListener("hashchange", () => syncViewFromLocation({ replaceInvalid: true }));
}

function renderAll() {
  renderSourceChrome();
  renderWatchlist();
  renderFeatured();
  renderTape();
  renderChannels();
  renderLeaderboard();
  renderRivalries();
  renderCompete();
  renderLessons();
  renderReceiptLearning();
  renderBlueprint();
  renderAutomations();
}

async function boot() {
  try {
    if (!dataAdapter) throw new Error("local data adapter unavailable");
    state.data = await dataAdapter.loadArenaData(fetch);
    hydrateLocalBlueprint();
    renderAll();
    bindEvents();
    updateConnectionStatus();
    syncViewFromLocation({ replaceInvalid: true });
    if ("serviceWorker" in navigator && location.protocol.startsWith("http")) navigator.serviceWorker.register("sw.js").catch(() => {});
  } catch (error) {
    const status = $("#connection-status");
    if (status) {
      status.dataset.state = "error";
      $("#connection-copy").textContent = "Local sources unavailable";
      status.setAttribute("aria-label", "The verified local corpus and bounded demo fallback could not load. No live service fallback was attempted.");
    }
    $("#workspace").innerHTML = `<section class="view is-active"><p class="eyebrow">Arena unavailable</p><h1>Local sources could not load.</h1><p class="match-subtitle">Serve this directory with a local HTTP server, then refresh. No live service fallback will be attempted.</p><pre class="fine-print">${escapeHTML(error.message)}</pre></section>`;
  }
}

if (typeof document !== "undefined") boot();
if (typeof module !== "undefined" && module.exports) {
  module.exports = { formatArenaRoute, nextModalFocusIndex, parseArenaRoute, restoreModalFocus };
}
