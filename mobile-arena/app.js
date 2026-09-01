"use strict";

const state = {
  data: null,
  activeView: "arena",
  followingFirst: false,
  activeLesson: null,
  selectedProofId: null,
  starterGuideVisible: true,
  starterGuidePersistenceAvailable: true,
  blueprintStored: false,
  blueprintPersistenceAvailable: true,
  blueprintRemovalArmed: false,
  qualificationPreview: null,
  learningAction: null,
  runbackProposal: null,
  portableRunback: null,
  portableImportText: "",
  portableVerification: null,
  portableReviews: [],
  portableReviewerLabel: "",
  portableReviewDecision: "accept_for_blueprint_revision",
  portableReviewReason: "receipt_guided_guard_change",
  portableReviewMessage: null,
  portableReviewExchange: null,
  portableReviewExchangeImportText: "",
  portableReviewExchangeVerification: null,
  portableReviewCorrections: [],
  portableCorrectionReviewerLabel: "",
  portableCorrectionTargetDigest: "",
  portableCorrectionAction: "correct_decision",
  portableCorrectionDecision: "defer",
  portableCorrectionReason: "clerical_decision_error",
  portableReviewCorrectionMessage: null,
  portableReviewCorrectionExchange: null,
  portableReviewCorrectionExchangeImportText: "",
  portableReviewCorrectionExchangeVerification: null,
  portableReviewComparisonLeftText: "",
  portableReviewComparisonRightText: "",
  portableReviewComparisonReceipt: null,
  portableReviewComparisonImportText: "",
  portableReviewComparisonVerification: null,
  privateReviewLearningReceipt: null,
  privateReviewLearningImportText: "",
  privateReviewLearningVerification: null,
  privateBlueprintDeltaReceipt: null,
  privateBlueprintDeltaImportText: "",
  privateBlueprintDeltaVerification: null,
  privateBlueprintDeltaReviewReceipt: null,
  privateBlueprintDeltaReviewImportText: "",
  privateBlueprintDeltaReviewVerification: null,
  privateBlueprintDeltaReviewerLabel: "",
  privateBlueprintDeltaReviewDecision: "accept_for_revision",
  privateBlueprintDeltaReviewReason: "guard_matches_verified_lesson",
  privateBlueprintRevisionDraftReceipt: null,
  privateBlueprintRevisionDraftImportText: "",
  privateBlueprintRevisionDraftVerification: null,
  privateBlueprintDraftReviewReceipt: null,
  privateBlueprintDraftReviewImportText: "",
  privateBlueprintDraftReviewVerification: null,
  privateBlueprintDraftReviewerLabel: "",
  privateBlueprintDraftReviewDecision: "accept_for_commit_candidate",
  privateBlueprintDraftReviewReason: "draft_lineage_verified",
  privateBlueprintGuardCompletionReceipt: null,
  privateBlueprintGuardCompletionImportText: "",
  privateBlueprintGuardCompletionVerification: null,
  privateBlueprintGuardCompletionReviewerLabel: "",
  privateBlueprintGuardCompletionReason: "complete_explicit_unknown_guards",
  privateBlueprintGuardCompletionValues: {},
  privateBlueprintGuardCompletionProvenance: {},
  privateBlueprintGuardCompletionReviewReceipt: null,
  privateBlueprintGuardCompletionReviewImportText: "",
  privateBlueprintGuardCompletionReviewVerification: null,
  privateBlueprintGuardCompletionReviewReviewerLabel: "",
  privateBlueprintGuardCompletionReviewDecision: "accept_for_commit_review",
  privateBlueprintGuardCompletionReviewReason: "completion_lineage_verified",
  privateBlueprintOperatorReviewPacketReceipt: null,
  privateBlueprintOperatorReviewPacketImportText: "",
  privateBlueprintOperatorReviewPacketVerification: null,
  lastFocus: null,
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const VIEW_NAMES = ["arena", "watch", "compete", "learn", "build"];
const BLUEPRINT_STORAGE_KEY = "builderwars.mobile-arena.blueprint.v1";
const STARTER_GUIDE_STORAGE_KEY = "builderwars.mobile-arena.starter-guide.v1";
const STARTER_GUIDE_COMPLETE = "complete";
const BLUEPRINT_MAX_LENGTH = 2048;
const BLUEPRINT_GUARD_KEYS = ["strictValidation", "fallbackDisclosure", "humanCheckpoints"];
const PORTABLE_REVIEW_DECISION_LABELS = {
  accept_for_blueprint_revision: "Accept for blueprint revision only",
  defer: "Defer private review",
  reject: "Reject private proposal",
};
const PORTABLE_REVIEW_REASON_LABELS = {
  receipt_guided_guard_change: "Receipt-guided guard change",
  needs_explicit_rules_binding: "Needs explicit rules binding",
  insufficient_public_evidence: "Insufficient public evidence",
  duplicate_or_stale_proposal: "Duplicate or stale proposal",
  unsafe_or_out_of_scope: "Unsafe or out of scope",
};
const PORTABLE_REVIEW_CORRECTION_ACTION_LABELS = {
  correct_decision: "Correct private decision",
  withdraw_review: "Withdraw original review",
};
const PORTABLE_REVIEW_CORRECTION_REASON_LABELS = {
  clerical_decision_error: "Clerical decision error",
  new_private_evidence: "New private evidence",
  unsafe_scope_discovered: "Unsafe scope discovered",
  duplicate_review: "Duplicate review",
  reviewer_requested_withdrawal: "Reviewer-requested withdrawal",
};
const PRIVATE_BLUEPRINT_DELTA_REVIEW_DECISION_LABELS = {
  accept_for_revision: "Accept for local revision only",
  defer: "Defer guard proposal",
  reject: "Reject guard proposal",
};
const PRIVATE_BLUEPRINT_DELTA_REVIEW_REASON_LABELS = {
  guard_matches_verified_lesson: "Guard matches verified lesson",
  guard_closes_local_safety_gap: "Guard closes a local safety gap",
  needs_explicit_rules_binding: "Needs explicit rules binding",
  needs_additional_private_evidence: "Needs additional private evidence",
  needs_operator_revision_review: "Needs operator revision review",
  lesson_guard_mismatch: "Lesson and guard do not match",
  duplicate_or_unnecessary_guard: "Duplicate or unnecessary guard",
  unsafe_or_out_of_scope: "Unsafe or out of scope",
};
const PRIVATE_BLUEPRINT_DRAFT_REVIEW_DECISION_LABELS = {
  accept_for_commit_candidate: "Accept for local commit candidate",
  defer: "Defer blueprint draft",
  reject: "Reject blueprint draft",
};
const PRIVATE_BLUEPRINT_DRAFT_REVIEW_REASON_LABELS = {
  draft_lineage_verified: "Draft lineage verified",
  guard_change_preserved: "Reviewed guard change preserved",
  required_guard_values_unknown: "Required guard values remain unknown",
  needs_operator_commit_review: "Needs operator commit review",
  needs_additional_private_evidence: "Needs additional private evidence",
  draft_not_needed: "Draft is not needed",
  guard_change_not_approved: "Guard change is not approved",
  unsafe_or_out_of_scope: "Unsafe or out of scope",
};
const PRIVATE_BLUEPRINT_GUARD_COMPLETION_REASON_LABELS = {
  complete_explicit_unknown_guards: "Complete explicit unknown guards",
  declare_fixture_specific_safety_posture: "Declare fixture-specific safety posture",
  record_private_guard_requirement: "Record private guard requirement",
};
const PRIVATE_BLUEPRINT_GUARD_COMPLETION_PROVENANCE_LABELS = {
  local_reviewer_declared: "Local reviewer declared",
  fixture_specific_requirement: "Fixture-specific requirement",
  private_evidence_reviewed_locally: "Private evidence reviewed locally",
};
const PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_DECISION_LABELS = {
  accept_for_commit_review: "Accept for operator commit review only",
  defer: "Defer guard completion",
  reject: "Reject guard completion",
};
const PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_REASON_LABELS = {
  completion_lineage_verified: "Completion lineage verified",
  explicit_guard_values_reviewed: "Explicit guard values reviewed",
  needs_operator_commit_review: "Needs operator commit review",
  needs_additional_private_evidence: "Needs additional private evidence",
  guard_value_provenance_unattested: "Guard-value provenance remains unattested",
  guard_completion_not_approved: "Guard completion is not approved",
  known_guard_preservation_failed: "Known-guard preservation failed",
  unsafe_or_out_of_scope: "Unsafe or out of scope",
};
const PRIVATE_BLUEPRINT_GUARD_LABELS = {
  strictValidation: "Strict validation",
  fallbackDisclosure: "Fallback disclosure",
  humanCheckpoints: "Human checkpoints",
};
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

function portableVerificationMarkup() {
  const verification = state.portableVerification;
  if (verification?.status === "verified") {
    return `<div class="portable-status verified" role="status" tabindex="-1"><strong>Verified locally · still unplayed</strong><span>SHA-256 ${escapeHTML(verification.result.payloadDigest)}</span><span>Parent ${escapeHTML(verification.result.proposal.parentReceipt.receiptId)}</span><span>Challenge ${escapeHTML(verification.result.proposal.runbackLineage.challengeId)} · ${escapeHTML(verification.result.proposal.gameBinding.name)} v${escapeHTML(verification.result.proposal.gameBinding.version)}</span></div>`;
  }
  if (verification?.status === "invalid") {
    return `<div class="portable-status invalid" role="alert" tabindex="-1"><strong>Import refused</strong><span>${escapeHTML(verification.message)}</span><span>No proposal was adopted, qualified, executed, or published.</span></div>`;
  }
  return `<div class="portable-status neutral" role="status" tabindex="-1"><strong>Nothing imported</strong><span>Paste an exact canonical envelope to verify its local checksum and still-unplayed contract.</span></div>`;
}

function resetPortableReviewExchangeState({ keepImportText = false } = {}) {
  state.portableReviewExchange = null;
  if (!keepImportText) state.portableReviewExchangeImportText = "";
  state.portableReviewExchangeVerification = null;
}

function resetPortableReviewCorrectionExchangeState({ keepImportText = false } = {}) {
  state.portableReviewCorrectionExchange = null;
  if (!keepImportText) state.portableReviewCorrectionExchangeImportText = "";
  state.portableReviewCorrectionExchangeVerification = null;
}

function resetPrivateBlueprintGuardCompletionReviewState({ keepImportText = false, keepReviewerLabel = false } = {}) {
  state.privateBlueprintGuardCompletionReviewReceipt = null;
  if (!keepImportText) state.privateBlueprintGuardCompletionReviewImportText = "";
  state.privateBlueprintGuardCompletionReviewVerification = null;
  if (!keepReviewerLabel) state.privateBlueprintGuardCompletionReviewReviewerLabel = "";
  resetPrivateBlueprintOperatorReviewPacketState();
}

function resetPrivateBlueprintOperatorReviewPacketState({ keepImportText = false } = {}) {
  state.privateBlueprintOperatorReviewPacketReceipt = null;
  if (!keepImportText) state.privateBlueprintOperatorReviewPacketImportText = "";
  state.privateBlueprintOperatorReviewPacketVerification = null;
}

function resetPrivateBlueprintGuardCompletionState({ keepImportText = false, keepReviewerLabel = false, keepSelections = false } = {}) {
  state.privateBlueprintGuardCompletionReceipt = null;
  if (!keepImportText) state.privateBlueprintGuardCompletionImportText = "";
  state.privateBlueprintGuardCompletionVerification = null;
  if (!keepReviewerLabel) state.privateBlueprintGuardCompletionReviewerLabel = "";
  if (!keepSelections) {
    state.privateBlueprintGuardCompletionValues = {};
    state.privateBlueprintGuardCompletionProvenance = {};
  }
  resetPrivateBlueprintGuardCompletionReviewState();
}

function resetPrivateBlueprintDraftReviewState({ keepImportText = false, keepReviewerLabel = false } = {}) {
  state.privateBlueprintDraftReviewReceipt = null;
  if (!keepImportText) state.privateBlueprintDraftReviewImportText = "";
  state.privateBlueprintDraftReviewVerification = null;
  if (!keepReviewerLabel) state.privateBlueprintDraftReviewerLabel = "";
  resetPrivateBlueprintGuardCompletionState();
}

function resetPrivateBlueprintRevisionDraftState({ keepImportText = false } = {}) {
  state.privateBlueprintRevisionDraftReceipt = null;
  if (!keepImportText) state.privateBlueprintRevisionDraftImportText = "";
  state.privateBlueprintRevisionDraftVerification = null;
  resetPrivateBlueprintDraftReviewState();
}

function resetPrivateBlueprintDeltaReviewState({ keepImportText = false, keepReviewerLabel = false } = {}) {
  state.privateBlueprintDeltaReviewReceipt = null;
  if (!keepImportText) state.privateBlueprintDeltaReviewImportText = "";
  state.privateBlueprintDeltaReviewVerification = null;
  if (!keepReviewerLabel) state.privateBlueprintDeltaReviewerLabel = "";
  resetPrivateBlueprintRevisionDraftState();
}

function resetPrivateBlueprintDeltaState({ keepImportText = false } = {}) {
  state.privateBlueprintDeltaReceipt = null;
  if (!keepImportText) state.privateBlueprintDeltaImportText = "";
  state.privateBlueprintDeltaVerification = null;
  resetPrivateBlueprintDeltaReviewState();
}

function resetPrivateReviewLearningState({ keepImportText = false } = {}) {
  state.privateReviewLearningReceipt = null;
  if (!keepImportText) state.privateReviewLearningImportText = "";
  state.privateReviewLearningVerification = null;
  resetPrivateBlueprintDeltaState();
}

function resetPortableReviewCorrectionState({ keepReviewerLabel = false } = {}) {
  state.portableReviewCorrections = [];
  if (!keepReviewerLabel) state.portableCorrectionReviewerLabel = "";
  state.portableCorrectionTargetDigest = "";
  state.portableCorrectionAction = "correct_decision";
  state.portableCorrectionDecision = "defer";
  state.portableCorrectionReason = "clerical_decision_error";
  state.portableReviewCorrectionMessage = null;
  resetPortableReviewCorrectionExchangeState();
}

function resetPortableReviewState({ keepReviewerLabel = false } = {}) {
  state.portableReviews = [];
  if (!keepReviewerLabel) state.portableReviewerLabel = "";
  state.portableReviewDecision = "accept_for_blueprint_revision";
  state.portableReviewReason = "receipt_guided_guard_change";
  state.portableReviewMessage = null;
  resetPortableReviewExchangeState();
  resetPortableReviewCorrectionState({ keepReviewerLabel });
}

function portableReviewReasonOptions(decision) {
  const reasons = dataAdapter?.PORTABLE_REVIEW_REASONS?.[decision] || [];
  return reasons.map((reason) => `<option value="${escapeHTML(reason)}" ${reason === state.portableReviewReason ? "selected" : ""}>${escapeHTML(PORTABLE_REVIEW_REASON_LABELS[reason] || reason)}</option>`).join("");
}

function latestPortableCorrection(reviewDigest) {
  return [...state.portableReviewCorrections].reverse().find((correction) => correction.targetReview.reviewDigest === reviewDigest) || null;
}

function portableReviewCorrectionSummary(review) {
  const correction = latestPortableCorrection(review.reviewDigest);
  if (!correction) return `<span class="portable-review-effective original">Current private interpretation: original decision</span>`;
  if (correction.action === "withdraw_review") {
    return `<span class="portable-review-effective corrected">Current private interpretation: withdrawn by correction ${correction.sequence}</span>`;
  }
  return `<span class="portable-review-effective corrected">Current private interpretation: ${escapeHTML(PORTABLE_REVIEW_DECISION_LABELS[correction.correctedDecision] || correction.correctedDecision)} · correction ${correction.sequence}</span>`;
}

function portableReviewMarkup() {
  const verification = state.portableVerification;
  if (verification?.status !== "verified") return "";
  const decisionOptions = Object.entries(PORTABLE_REVIEW_DECISION_LABELS).map(([decision, label]) => `<option value="${escapeHTML(decision)}" ${decision === state.portableReviewDecision ? "selected" : ""}>${escapeHTML(label)}</option>`).join("");
  const journal = state.portableReviews.length
    ? `<ol class="portable-review-journal" aria-label="Private append-only review journal">${state.portableReviews.map((review) => `<li class="portable-review-record" data-portable-review-record="${review.sequence}" tabindex="-1"><div><span class="mode-label">Review ${review.sequence} · private · original preserved</span><strong>${escapeHTML(PORTABLE_REVIEW_DECISION_LABELS[review.decision] || review.decision)}</strong><small>${escapeHTML(PORTABLE_REVIEW_REASON_LABELS[review.reasonCode] || review.reasonCode)} · reviewer ${escapeHTML(review.reviewer.label)} (unattested)</small></div><code>${escapeHTML(review.reviewDigest)}</code>${portableReviewCorrectionSummary(review)}<span>${review.blueprintRevision ? "Original proposed uncommitted blueprint revision · no execution authority" : "No original blueprint revision created"}</span></li>`).join("")}</ol>`
    : `<div class="portable-review-empty"><strong>No private reviews appended.</strong><span>The verified proposal remains unchanged and still unplayed.</span></div>`;
  const message = state.portableReviewMessage
    ? `<div class="portable-review-status ${state.portableReviewMessage.status}" role="${state.portableReviewMessage.status === "invalid" ? "alert" : "status"}" tabindex="-1"><strong>${escapeHTML(state.portableReviewMessage.title)}</strong><span>${escapeHTML(state.portableReviewMessage.detail)}</span></div>`
    : "";
  return `<section class="portable-review" aria-labelledby="portable-review-title"><div><p class="eyebrow">Private review journal</p><h4 id="portable-review-title">Append a bounded local decision.</h4><p>The reviewer label is not authenticated. Acceptance proposes a local blueprint revision only; it does not approve a runback.</p></div><div class="portable-review-form" role="group" aria-describedby="portable-review-boundary"><label for="portable-reviewer-label">Unattested local reviewer label</label><input id="portable-reviewer-label" type="text" maxlength="36" autocomplete="off" value="${escapeHTML(state.portableReviewerLabel)}" placeholder="Example: local reviewer"><label for="portable-review-decision">Decision</label><select id="portable-review-decision" data-portable-review-decision>${decisionOptions}</select><label for="portable-review-reason">Bounded reason</label><select id="portable-review-reason" data-portable-review-reason>${portableReviewReasonOptions(state.portableReviewDecision)}</select><button class="secondary-button" type="button" data-portable-review-submit>Append private review</button></div>${message}${journal}<div class="learning-boundary" id="portable-review-boundary">Append-only means prior local records are hash-linked and cannot be edited in place. The chain is not a signature and grants no rules, qualification, runner, registry, ranking, publication, or spending authority.</div></section>`;
}

function portableCorrectionReasonOptions(action) {
  const reasons = dataAdapter?.PORTABLE_REVIEW_CORRECTION_REASONS?.[action] || [];
  return reasons.map((reason) => `<option value="${escapeHTML(reason)}" ${reason === state.portableCorrectionReason ? "selected" : ""}>${escapeHTML(PORTABLE_REVIEW_CORRECTION_REASON_LABELS[reason] || reason)}</option>`).join("");
}

function effectivePortableReviewDecision(review) {
  const correction = latestPortableCorrection(review.reviewDigest);
  if (!correction) return review.decision;
  return correction.action === "correct_decision" ? correction.correctedDecision : null;
}

function ensurePortableCorrectionSelection() {
  const selectedReview = state.portableReviews.find((review) => review.reviewDigest === state.portableCorrectionTargetDigest) || state.portableReviews[0] || null;
  state.portableCorrectionTargetDigest = selectedReview?.reviewDigest || "";
  if (selectedReview && state.portableCorrectionAction === "correct_decision") {
    const effectiveDecision = effectivePortableReviewDecision(selectedReview);
    if (state.portableCorrectionDecision === effectiveDecision) {
      state.portableCorrectionDecision = Object.keys(PORTABLE_REVIEW_DECISION_LABELS).find((decision) => decision !== effectiveDecision) || "defer";
    }
  }
}

function portableReviewCorrectionMarkup() {
  if (state.portableVerification?.status !== "verified" || state.portableReviews.length === 0) return "";
  ensurePortableCorrectionSelection();
  const targetOptions = state.portableReviews.map((review) => `<option value="${escapeHTML(review.reviewDigest)}" ${review.reviewDigest === state.portableCorrectionTargetDigest ? "selected" : ""}>Review ${review.sequence} · ${escapeHTML(PORTABLE_REVIEW_DECISION_LABELS[review.decision] || review.decision)} · ${escapeHTML(review.reviewDigest.slice(0, 12))}…</option>`).join("");
  const actionOptions = Object.entries(PORTABLE_REVIEW_CORRECTION_ACTION_LABELS).map(([action, label]) => `<option value="${escapeHTML(action)}" ${action === state.portableCorrectionAction ? "selected" : ""}>${escapeHTML(label)}</option>`).join("");
  const decisionOptions = Object.entries(PORTABLE_REVIEW_DECISION_LABELS).map(([decision, label]) => `<option value="${escapeHTML(decision)}" ${decision === state.portableCorrectionDecision ? "selected" : ""}>${escapeHTML(label)}</option>`).join("");
  const message = state.portableReviewCorrectionMessage
    ? `<div class="portable-review-status ${state.portableReviewCorrectionMessage.status}" role="${state.portableReviewCorrectionMessage.status === "invalid" ? "alert" : "status"}" tabindex="-1"><strong>${escapeHTML(state.portableReviewCorrectionMessage.title)}</strong><span>${escapeHTML(state.portableReviewCorrectionMessage.detail)}</span></div>`
    : "";
  const journal = state.portableReviewCorrections.length
    ? `<ol class="portable-correction-journal" aria-label="Private append-only review correction journal">${state.portableReviewCorrections.map((correction) => `<li class="portable-review-record portable-correction-record" data-portable-review-correction-record="${correction.sequence}" tabindex="-1"><div><span class="mode-label">Correction ${correction.sequence} · private</span><strong>${correction.action === "withdraw_review" ? "Withdraw original review" : `Correct to ${escapeHTML(PORTABLE_REVIEW_DECISION_LABELS[correction.correctedDecision] || correction.correctedDecision)}`}</strong><small>Target review ${correction.targetReview.sequence} · ${escapeHTML(PORTABLE_REVIEW_CORRECTION_REASON_LABELS[correction.reasonCode] || correction.reasonCode)} · reviewer ${escapeHTML(correction.reviewer.label)} (unattested)</small></div><code>${escapeHTML(correction.correctionDigest)}</code><span>${correction.supersedesCorrectionDigest ? `Supersedes correction ${escapeHTML(correction.supersedesCorrectionDigest.slice(0, 12))}… without deleting it` : "First correction for this immutable review"}</span><span>${correction.blueprintRevision ? "Proposed uncommitted correction revision · no execution authority" : "No correction blueprint revision created"}</span></li>`).join("")}</ol>`
    : `<div class="portable-review-empty"><strong>No corrections appended.</strong><span>Original private reviews remain unchanged.</span></div>`;
  return `<section class="portable-review portable-review-correction" aria-labelledby="portable-review-correction-title"><div><p class="eyebrow">Private correction history</p><h4 id="portable-review-correction-title">Correct without rewriting.</h4><p>Every record targets an immutable review digest. A later correction may supersede an earlier correction, but neither record is deleted or authenticated.</p></div><div class="portable-review-form" role="group" aria-describedby="portable-review-correction-boundary"><label for="portable-correction-reviewer-label">Unattested correction reviewer label</label><input id="portable-correction-reviewer-label" type="text" maxlength="36" autocomplete="off" value="${escapeHTML(state.portableCorrectionReviewerLabel)}" placeholder="Example: local reviewer"><label for="portable-correction-target">Immutable target review</label><select id="portable-correction-target" data-portable-correction-target>${targetOptions}</select><label for="portable-correction-action">Correction action</label><select id="portable-correction-action" data-portable-correction-action>${actionOptions}</select>${state.portableCorrectionAction === "correct_decision" ? `<label for="portable-correction-decision">Corrected private decision</label><select id="portable-correction-decision" data-portable-correction-decision>${decisionOptions}</select>` : ""}<label for="portable-correction-reason">Bounded correction reason</label><select id="portable-correction-reason" data-portable-correction-reason>${portableCorrectionReasonOptions(state.portableCorrectionAction)}</select><button class="secondary-button" type="button" data-portable-review-correction-submit>Append private correction</button></div>${message}${journal}<div class="learning-boundary" id="portable-review-correction-boundary">The original review and every prior correction remain visible and hash-bound. This private interpretation cannot authenticate a reviewer, apply a blueprint, bind rules, qualify, execute, register, rank, publish, spend, or call a provider.</div></section>`;
}

function portableReviewExchangeStatusMarkup() {
  const verification = state.portableReviewExchangeVerification;
  if (verification?.status === "verified") {
    const result = verification.result;
    return `<div class="portable-status verified portable-review-exchange-status" role="status" tabindex="-1"><strong>Review packet verified · private inspection only</strong><span>SHA-256 ${escapeHTML(result.packetDigest)}</span><span>${result.journal.reviewCount} review${result.journal.reviewCount === 1 ? "" : "s"} · head ${escapeHTML(result.journal.latestReviewDigest || "empty journal")}</span><span>No blueprint was applied and no authority was granted.</span></div>`;
  }
  if (verification?.status === "invalid") {
    return `<div class="portable-status invalid portable-review-exchange-status" role="alert" tabindex="-1"><strong>Review packet refused</strong><span>${escapeHTML(verification.message)}</span><span>No proposal, review, or blueprint inspection state was retained.</span></div>`;
  }
  return `<div class="portable-status neutral portable-review-exchange-status" role="status" tabindex="-1"><strong>No review packet imported</strong><span>A fresh recipient can paste one canonical packet and independently recheck its proposal, journal chain, and packet digest.</span></div>`;
}

function portableReviewExchangeMarkup() {
  const prepared = state.portableReviewExchange;
  const canPrepare = state.portableVerification?.status === "verified";
  return `<section class="portable-review-exchange" aria-labelledby="portable-review-exchange-title"><div><p class="eyebrow">Portable private review packet</p><h4 id="portable-review-exchange-title">Carry the proposal and exact journal together.</h4><p>The packet is canonical, size-bounded, and independently verifiable from an empty Receipt Lab. It remains memory-only inspection data.</p></div>${canPrepare ? `<button class="secondary-button" type="button" data-portable-review-exchange-prepare>${prepared ? "Refresh review packet" : "Prepare review packet"}</button>` : ""}${prepared ? `<label for="portable-review-exchange-export">Canonical review packet · read only</label><textarea id="portable-review-exchange-export" class="portable-textarea" rows="7" readonly spellcheck="false">${escapeHTML(prepared.serialized)}</textarea><p class="portable-digest">Packet SHA-256 ${escapeHTML(prepared.packet.integrity.payloadDigest)}</p>` : ""}<label for="portable-review-exchange-import">Paste canonical review packet JSON</label><textarea id="portable-review-exchange-import" class="portable-textarea" rows="7" maxlength="262144" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Paste builderwars.mobile-runback-review-exchange.v1 JSON">${escapeHTML(state.portableReviewExchangeImportText)}</textarea><button class="secondary-button" type="button" data-portable-review-exchange-verify>Verify review packet</button>${portableReviewExchangeStatusMarkup()}<div class="learning-boundary">Import only reconstructs a private inspection view in page memory. It cannot authenticate reviewers, apply a blueprint, bind rules, qualify, execute, register, rank, publish, spend, or call a provider.</div></section>`;
}

function portableReviewCorrectionExchangeStatusMarkup() {
  const verification = state.portableReviewCorrectionExchangeVerification;
  if (verification?.status === "verified") {
    const result = verification.result;
    return `<div class="portable-status verified portable-review-correction-exchange-status" role="status" tabindex="-1"><strong>Correction packet verified · immutable history preserved</strong><span>SHA-256 ${escapeHTML(result.packetDigest)}</span><span>${result.journal.reviewCount} original review${result.journal.reviewCount === 1 ? "" : "s"} · ${result.correctionJournal.correctionCount} correction${result.correctionJournal.correctionCount === 1 ? "" : "s"}</span><span>No review was rewritten, no blueprint was applied, and no authority was granted.</span></div>`;
  }
  if (verification?.status === "invalid") {
    return `<div class="portable-status invalid portable-review-correction-exchange-status" role="alert" tabindex="-1"><strong>Correction packet refused</strong><span>${escapeHTML(verification.message)}</span><span>No proposal, review, correction, or blueprint inspection state was retained.</span></div>`;
  }
  return `<div class="portable-status neutral portable-review-correction-exchange-status" role="status" tabindex="-1"><strong>No correction packet imported</strong><span>A fresh recipient can paste one canonical packet and independently recheck its proposal, immutable reviews, supersession links, correction chain, and packet digest.</span></div>`;
}

function portableReviewCorrectionExchangeMarkup() {
  const prepared = state.portableReviewCorrectionExchange;
  const canPrepare = state.portableVerification?.status === "verified" && state.portableReviewCorrections.length > 0;
  return `<section class="portable-review-exchange portable-review-correction-exchange" aria-labelledby="portable-review-correction-exchange-title"><div><p class="eyebrow">Portable correction packet</p><h4 id="portable-review-correction-exchange-title">Carry immutable reviews and corrections together.</h4><p>The nested review packet and exact correction history are canonical, size-bounded, and independently verifiable from an empty Receipt Lab.</p></div>${canPrepare ? `<button class="secondary-button" type="button" data-portable-review-correction-exchange-prepare>${prepared ? "Refresh correction packet" : "Prepare correction packet"}</button>` : ""}${prepared ? `<label for="portable-review-correction-exchange-export">Canonical correction packet · read only</label><textarea id="portable-review-correction-exchange-export" class="portable-textarea" rows="8" readonly spellcheck="false">${escapeHTML(prepared.serialized)}</textarea><p class="portable-digest">Packet SHA-256 ${escapeHTML(prepared.packet.integrity.payloadDigest)}</p>` : ""}<label for="portable-review-correction-exchange-import">Paste canonical correction packet JSON</label><textarea id="portable-review-correction-exchange-import" class="portable-textarea" rows="8" maxlength="524288" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Paste builderwars.mobile-runback-review-correction-exchange.v1 JSON">${escapeHTML(state.portableReviewCorrectionExchangeImportText)}</textarea><button class="secondary-button" type="button" data-portable-review-correction-exchange-verify>Verify correction packet</button>${portableReviewCorrectionExchangeStatusMarkup()}<div class="learning-boundary">Import reconstructs only memory-local inspection history. It cannot authenticate reviewers, rewrite an original review, apply a blueprint, bind rules, qualify, execute, register, rank, publish, spend, or call a provider.</div></section>`;
}

function portableReviewComparisonStatusMarkup() {
  const verification = state.portableReviewComparisonVerification;
  if (verification?.status === "verified") {
    const result = verification.result;
    const summary = result.comparison.summary;
    return `<div class="portable-status verified portable-review-comparison-status" role="status" tabindex="-1"><strong>Comparison receipt verified · read only</strong><span>SHA-256 ${escapeHTML(result.packetDigest)}</span><span>${summary.sharedReviewCount} shared · ${summary.changedEffectiveStateCount} changed effective state · ${summary.leftOnlyReviewCount} Packet A only · ${summary.rightOnlyReviewCount} Packet B only</span><span>No packet won, no histories merged, and no dispute or authority was resolved.</span></div>`;
  }
  if (verification?.status === "invalid") {
    return `<div class="portable-status invalid portable-review-comparison-status" role="alert" tabindex="-1"><strong>Comparison receipt refused</strong><span>${escapeHTML(verification.message)}</span><span>No verified comparison, merge, resolution, blueprint, or authority state was retained.</span></div>`;
  }
  return `<div class="portable-status neutral portable-review-comparison-status" role="status" tabindex="-1"><strong>No comparison verified</strong><span>Paste two correction packets for the same proposal, or paste one canonical comparison receipt. Both histories are independently rechecked.</span></div>`;
}

function portableReviewComparisonEntriesMarkup() {
  const entries = state.portableReviewComparisonVerification?.status === "verified"
    ? state.portableReviewComparisonVerification.result.comparison.entries
    : [];
  if (entries.length === 0) return "";
  const visibleEntries = entries.slice(0, 12);
  const label = (entry) => ({
    identical_effective_state: "Identical effective state",
    changed_effective_state: "Changed effective state",
    left_only_review: "Packet A only",
    right_only_review: "Packet B only",
  }[entry.classification] || entry.classification);
  const decision = (side) => side
    ? (side.effectiveDecision === null ? "Withdrawn" : PORTABLE_REVIEW_DECISION_LABELS[side.effectiveDecision] || side.effectiveDecision)
    : "Absent";
  return `<ol class="portable-comparison-list" aria-label="Digest-bound private review-state differences">${visibleEntries.map((entry) => `<li class="portable-comparison-record"><div><span class="mode-label">${escapeHTML(label(entry))}</span><code>${escapeHTML(entry.reviewDigest)}</code></div><div class="portable-comparison-sides"><span><strong>Packet A</strong>${escapeHTML(decision(entry.left))}</span><span><strong>Packet B</strong>${escapeHTML(decision(entry.right))}</span></div></li>`).join("")}</ol>${entries.length > visibleEntries.length ? `<p class="portable-digest">${entries.length - visibleEntries.length} additional digest-bound entries remain inside the verified receipt.</p>` : ""}`;
}

function portableReviewComparisonMarkup() {
  const prepared = state.portableReviewComparisonReceipt;
  return `<section class="portable-review-exchange portable-review-comparison" aria-labelledby="portable-review-comparison-title"><div><p class="eyebrow">Private review-state comparison</p><h4 id="portable-review-comparison-title">Compare two packets without choosing a winner.</h4><p>Both correction packets must bind the exact same proposal. The receipt reports digest-bound differences and one-sided reviews without merging histories or resolving which packet is authoritative.</p></div><div class="portable-comparison-inputs"><label for="portable-review-comparison-left">Packet A · canonical correction packet</label><textarea id="portable-review-comparison-left" class="portable-textarea" rows="7" maxlength="524288" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Paste Packet A builderwars.mobile-runback-review-correction-exchange.v1 JSON">${escapeHTML(state.portableReviewComparisonLeftText)}</textarea><label for="portable-review-comparison-right">Packet B · canonical correction packet</label><textarea id="portable-review-comparison-right" class="portable-textarea" rows="7" maxlength="524288" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Paste Packet B builderwars.mobile-runback-review-correction-exchange.v1 JSON">${escapeHTML(state.portableReviewComparisonRightText)}</textarea><button class="secondary-button" type="button" data-portable-review-comparison-create>Create read-only comparison receipt</button></div>${prepared ? `<label for="portable-review-comparison-export">Canonical comparison receipt · read only</label><textarea id="portable-review-comparison-export" class="portable-textarea" rows="9" readonly spellcheck="false">${escapeHTML(prepared.serialized)}</textarea><p class="portable-digest">Comparison SHA-256 ${escapeHTML(prepared.packet.integrity.payloadDigest)}</p>` : ""}<label for="portable-review-comparison-import">Paste canonical comparison receipt JSON</label><textarea id="portable-review-comparison-import" class="portable-textarea" rows="9" maxlength="1572864" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Paste builderwars.mobile-private-review-comparison.v1 JSON">${escapeHTML(state.portableReviewComparisonImportText)}</textarea><button class="secondary-button" type="button" data-portable-review-comparison-verify>Verify comparison receipt</button>${portableReviewComparisonStatusMarkup()}${portableReviewComparisonEntriesMarkup()}<div class="learning-boundary">Comparison is independent, memory-only inspection. It cannot choose a winner, merge histories, resolve a dispute, authenticate identity, apply a blueprint, bind rules, qualify, execute, register, rank, publish, spend, or call a provider.</div></section>`;
}

function privateReviewLearningStatusMarkup() {
  const verification = state.privateReviewLearningVerification;
  if (verification?.status === "verified") {
    const result = verification.result;
    const summary = result.learning.summary;
    return `<div class="portable-status verified private-review-learning-status" role="status" tabindex="-1"><strong>Inspection learning receipt verified · no progress awarded</strong><span>SHA-256 ${escapeHTML(result.packetDigest)}</span><span>${summary.entryCount} digest-bound lesson${summary.entryCount === 1 ? "" : "s"} · ${summary.inspectEvidenceCount} evidence · ${summary.inspectRulesBindingCount} rules binding · ${summary.inspectCorrectionLineageCount} correction lineage</span><span>Packet A and Packet B remain roles. Neither packet was declared correct or authoritative.</span></div>`;
  }
  if (verification?.status === "invalid") {
    return `<div class="portable-status invalid private-review-learning-status" role="alert" tabindex="-1"><strong>Inspection learning receipt refused</strong><span>${escapeHTML(verification.message)}</span><span>No verified lesson, progress, consensus, blueprint, merge, resolution, or authority state was retained.</span></div>`;
  }
  return `<div class="portable-status neutral private-review-learning-status" role="status" tabindex="-1"><strong>No inspection learning receipt verified</strong><span>Verify a private comparison to prepare one, or paste one canonical learning receipt. The embedded comparison and both packet histories are rechecked.</span></div>`;
}

function privateReviewLearningEntriesMarkup() {
  const lessons = state.privateReviewLearningVerification?.status === "verified"
    ? state.privateReviewLearningVerification.result.learning.lessons
    : [];
  if (lessons.length === 0) return "";
  const visibleLessons = lessons.slice(0, 12);
  const decision = (side) => {
    if (!side) return "Absent";
    const value = side.effectiveDecision === null ? "Withdrawn" : PORTABLE_REVIEW_DECISION_LABELS[side.effectiveDecision] || side.effectiveDecision;
    return `${value} · ${side.latestCorrectionDigest ? `correction ${side.latestCorrectionDigest.slice(0, 12)}…` : "original state"}`;
  };
  return `<ol class="portable-comparison-list private-review-learning-list" aria-label="Digest-bound private comparison inspection lessons">${visibleLessons.map((entry) => `<li class="portable-comparison-record private-review-learning-record"><div><span class="mode-label">${escapeHTML(entry.lessonLabel)}</span><strong>${escapeHTML(entry.classification.replaceAll("_", " "))}</strong><code>${escapeHTML(entry.reviewDigest)}</code><small>${escapeHTML(entry.inspectionGuidance)}</small><button class="secondary-button" type="button" data-private-blueprint-delta-create="${escapeHTML(entry.reviewDigest)}">Propose guard requirement</button></div><div class="portable-comparison-sides"><span><strong>Packet A</strong>${escapeHTML(decision(entry.left))}</span><span><strong>Packet B</strong>${escapeHTML(decision(entry.right))}</span></div></li>`).join("")}</ol>${lessons.length > visibleLessons.length ? `<p class="portable-digest">${lessons.length - visibleLessons.length} additional inspection lessons remain inside the verified receipt.</p>` : ""}`;
}

function privateReviewLearningMarkup() {
  const prepared = state.privateReviewLearningReceipt;
  const canPrepare = state.portableReviewComparisonVerification?.status === "verified";
  return `<section class="portable-review-exchange private-review-learning" aria-labelledby="private-review-learning-title"><div><p class="eyebrow">Comparison-linked learning</p><h4 id="private-review-learning-title">Turn differences into inspection, not consensus.</h4><p>Each comparison class maps deterministically to evidence, rules-binding, or correction-lineage inspection. The mapping cannot choose a correct packet or award progress.</p></div>${canPrepare ? `<button class="secondary-button" type="button" data-private-review-learning-create>${prepared ? "Refresh inspection receipt" : "Create inspection receipt"}</button>` : ""}${prepared ? `<label for="private-review-learning-export">Canonical inspection learning receipt · read only</label><textarea id="private-review-learning-export" class="portable-textarea" rows="10" readonly spellcheck="false">${escapeHTML(prepared.serialized)}</textarea><p class="portable-digest">Inspection receipt SHA-256 ${escapeHTML(prepared.packet.integrity.payloadDigest)}</p>` : ""}<label for="private-review-learning-import">Paste canonical inspection learning receipt JSON</label><textarea id="private-review-learning-import" class="portable-textarea" rows="10" maxlength="2097152" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Paste builderwars.mobile-private-review-learning.v1 JSON">${escapeHTML(state.privateReviewLearningImportText)}</textarea><button class="secondary-button" type="button" data-private-review-learning-verify>Verify inspection receipt</button>${privateReviewLearningStatusMarkup()}${privateReviewLearningEntriesMarkup()}<div class="learning-boundary">Inspection is deterministic and memory-only. It cannot create consensus, approval, progress, blueprint adoption, identity, merge, resolution, rules, qualification, execution, registry, ranking, publication, spending, or provider authority.</div></section>`;
}

function privateBlueprintDeltaStatusMarkup() {
  const verification = state.privateBlueprintDeltaVerification;
  if (verification?.status === "verified") {
    const result = verification.result;
    const proposal = result.proposal;
    const guard = proposal.guardDelta;
    const current = guard.currentValue === null ? "not carried by parent proposal" : guard.currentValue ? "already declared" : "declared false";
    return `<div class="portable-status verified private-blueprint-delta-status" role="status" tabindex="-1"><strong>Guard proposal verified · uncommitted and unplayed</strong><span>SHA-256 ${escapeHTML(result.packetDigest)}</span><span>${escapeHTML(proposal.selectedLesson.lessonLabel)} → ${escapeHTML(guard.label)}</span><span>Current guard: ${escapeHTML(current)} · target requirement: true · ${escapeHTML(guard.changeStatus.replaceAll("_", " "))}</span><span>Parent proposal ${escapeHTML(proposal.parentProposalBinding.proposalPayloadDigest)} · Packet A and Packet B remain neutral roles.</span></div>`;
  }
  if (verification?.status === "invalid") {
    return `<div class="portable-status invalid private-blueprint-delta-status" role="alert" tabindex="-1"><strong>Guard proposal refused</strong><span>${escapeHTML(verification.message)}</span><span>No blueprint change, commitment, progress, qualification, play, execution, or authority state was retained.</span></div>`;
  }
  return `<div class="portable-status neutral private-blueprint-delta-status" role="status" tabindex="-1"><strong>No guard proposal verified</strong><span>Choose one verified inspection lesson above, or paste one canonical guard proposal. The full ancestry is independently rechecked.</span></div>`;
}

function privateBlueprintDeltaReviewReasonOptions(decision) {
  const reasons = dataAdapter?.PRIVATE_BLUEPRINT_DELTA_REVIEW_REASONS?.[decision] || [];
  return reasons.map((reasonCode) => `<option value="${escapeHTML(reasonCode)}" ${reasonCode === state.privateBlueprintDeltaReviewReason ? "selected" : ""}>${escapeHTML(PRIVATE_BLUEPRINT_DELTA_REVIEW_REASON_LABELS[reasonCode] || reasonCode)}</option>`).join("");
}

function privateBlueprintDeltaReviewStatusMarkup() {
  const verification = state.privateBlueprintDeltaReviewVerification;
  if (verification?.status === "verified") {
    const result = verification.result;
    const review = result.review;
    const candidate = review.localRevisionCandidate;
    return `<div class="portable-status verified private-blueprint-delta-review-status" role="status" tabindex="-1"><strong>Guard review verified · immutable private decision</strong><span>SHA-256 ${escapeHTML(result.packetDigest)}</span><span>${escapeHTML(PRIVATE_BLUEPRINT_DELTA_REVIEW_DECISION_LABELS[review.decision] || review.decision)} · ${escapeHTML(PRIVATE_BLUEPRINT_DELTA_REVIEW_REASON_LABELS[review.reasonCode] || review.reasonCode)}</span><span>Reviewer ${escapeHTML(review.reviewer.label)} · identity unattested · ${candidate ? "uncommitted local revision candidate proposed" : "no revision candidate created"}</span><span>No guard was adopted, committed, played, qualified, executed, ranked, or published.</span></div>`;
  }
  if (verification?.status === "invalid") {
    return `<div class="portable-status invalid private-blueprint-delta-review-status" role="alert" tabindex="-1"><strong>Guard review refused</strong><span>${escapeHTML(verification.message)}</span><span>No review, revision candidate, adoption, progress, execution, or authority state was retained.</span></div>`;
  }
  return `<div class="portable-status neutral private-blueprint-delta-review-status" role="status" tabindex="-1"><strong>No guard review verified</strong><span>Review one verified proposal or paste one canonical review receipt. The proposal and its complete ancestry are independently rechecked.</span></div>`;
}

function privateBlueprintRevisionDraftStatusMarkup() {
  const verification = state.privateBlueprintRevisionDraftVerification;
  if (verification?.status === "verified") {
    const result = verification.result;
    const draft = result.draft;
    const guard = draft.appliedGuard;
    const unknown = draft.unknownGuardKeys.length ? draft.unknownGuardKeys.join(", ") : "none";
    return `<div class="portable-status verified private-blueprint-revision-draft-status" role="status" tabindex="-1"><strong>Local blueprint revision draft verified · never adopted</strong><span>SHA-256 ${escapeHTML(result.packetDigest)}</span><span>${escapeHTML(guard.label)} applied as true · exact accepted review ${escapeHTML(draft.lineage.acceptedReviewDigest)}</span><span>Unknown guard values preserved: ${escapeHTML(unknown)} · no values invented</span><span>Draft remains local, uncommitted, unadopted, unqualified, unplayed, unexecuted, unregistered, and unpublished.</span></div>`;
  }
  if (verification?.status === "invalid") {
    return `<div class="portable-status invalid private-blueprint-revision-draft-status" role="alert" tabindex="-1"><strong>Blueprint revision draft refused</strong><span>${escapeHTML(verification.message)}</span><span>No draft, adoption, progress, qualification, execution, registry, publication, or authority state was retained.</span></div>`;
  }
  return `<div class="portable-status neutral private-blueprint-revision-draft-status" role="status" tabindex="-1"><strong>No blueprint revision draft verified</strong><span>Create one only from an accepted guard review, or paste one canonical draft receipt. Defer and reject reviews fail closed.</span></div>`;
}

function privateBlueprintDraftReviewReasonOptions(decision) {
  const reasons = dataAdapter?.PRIVATE_BLUEPRINT_DRAFT_REVIEW_REASONS?.[decision] || [];
  return reasons.map((reasonCode) => `<option value="${escapeHTML(reasonCode)}" ${reasonCode === state.privateBlueprintDraftReviewReason ? "selected" : ""}>${escapeHTML(PRIVATE_BLUEPRINT_DRAFT_REVIEW_REASON_LABELS[reasonCode] || reasonCode)}</option>`).join("");
}

function privateBlueprintDraftReviewStatusMarkup() {
  const verification = state.privateBlueprintDraftReviewVerification;
  if (verification?.status === "verified") {
    const result = verification.result;
    const review = result.review;
    const candidate = review.localCommitCandidate;
    const candidateStatus = candidate
      ? `<span>Candidate ${escapeHTML(candidate.commitReadinessStatus.replaceAll("_", " "))} · unknown guards: ${escapeHTML(candidate.unknownGuardKeys.length ? candidate.unknownGuardKeys.join(", ") : "none")}</span><span>Candidate is local, uncommitted, unadopted, and not commit-ready.</span>`
      : `<span>No commit candidate was created.</span>`;
    return `<div class="portable-status verified private-blueprint-draft-review-status" role="status" tabindex="-1"><strong>Blueprint draft review verified · immutable private decision</strong><span>SHA-256 ${escapeHTML(result.packetDigest)}</span><span>${escapeHTML(PRIVATE_BLUEPRINT_DRAFT_REVIEW_DECISION_LABELS[review.decision] || review.decision)} · ${escapeHTML(PRIVATE_BLUEPRINT_DRAFT_REVIEW_REASON_LABELS[review.reasonCode] || review.reasonCode)}</span><span>Reviewer ${escapeHTML(review.reviewer.label)} · identity unattested</span>${candidateStatus}<span>No blueprint was committed, adopted, qualified, played, executed, registered, ranked, or published.</span></div>`;
  }
  if (verification?.status === "invalid") {
    return `<div class="portable-status invalid private-blueprint-draft-review-status" role="alert" tabindex="-1"><strong>Blueprint draft review refused</strong><span>${escapeHTML(verification.message)}</span><span>No review, commit candidate, readiness, adoption, progress, execution, or authority state was retained.</span></div>`;
  }
  return `<div class="portable-status neutral private-blueprint-draft-review-status" role="status" tabindex="-1"><strong>No blueprint draft review verified</strong><span>Review one verified local draft or paste one canonical receipt. Unknown guard values remain explicit and block commit readiness.</span></div>`;
}

function privateBlueprintGuardCompletionCandidate() {
  const review = state.privateBlueprintDraftReviewVerification?.status === "verified"
    ? state.privateBlueprintDraftReviewVerification.result.review
    : null;
  return review?.decision === "accept_for_commit_candidate" && review.localCommitCandidate
    ? review.localCommitCandidate
    : null;
}

function ensurePrivateBlueprintGuardCompletionSelections() {
  const candidate = privateBlueprintGuardCompletionCandidate();
  const unknownKeys = candidate?.unknownGuardKeys || [];
  const allowed = new Set(unknownKeys);
  for (const guardKey of Object.keys(state.privateBlueprintGuardCompletionValues)) {
    if (!allowed.has(guardKey)) delete state.privateBlueprintGuardCompletionValues[guardKey];
  }
  for (const guardKey of Object.keys(state.privateBlueprintGuardCompletionProvenance)) {
    if (!allowed.has(guardKey)) delete state.privateBlueprintGuardCompletionProvenance[guardKey];
  }
  for (const guardKey of unknownKeys) {
    if (!(guardKey in state.privateBlueprintGuardCompletionValues)) state.privateBlueprintGuardCompletionValues[guardKey] = "";
    if (!state.privateBlueprintGuardCompletionProvenance[guardKey]) state.privateBlueprintGuardCompletionProvenance[guardKey] = "local_reviewer_declared";
  }
}

function privateBlueprintGuardCompletionStatusMarkup() {
  const verification = state.privateBlueprintGuardCompletionVerification;
  if (verification?.status === "verified") {
    const result = verification.result;
    const proposal = result.completionProposal;
    const values = proposal.guardCompletions.map((completion) => `${PRIVATE_BLUEPRINT_GUARD_LABELS[completion.guardKey] || completion.guardKey}: ${completion.value} · ${PRIVATE_BLUEPRINT_GUARD_COMPLETION_PROVENANCE_LABELS[completion.provenance.code] || completion.provenance.code}`).join("; ");
    return `<div class="portable-status verified private-blueprint-guard-completion-status" role="status" tabindex="-1"><strong>Guard completion verified · review still required</strong><span>SHA-256 ${escapeHTML(result.packetDigest)}</span><span>${escapeHTML(values)}</span><span>${escapeHTML(proposal.state.commitReadinessStatus.replaceAll("_", " "))} · reviewer identity and value provenance remain unattested</span><span>Proposal is local, uncommitted, unadopted, not commit-ready, unqualified, unplayed, unexecuted, unregistered, and unpublished.</span></div>`;
  }
  if (verification?.status === "invalid") {
    return `<div class="portable-status invalid private-blueprint-guard-completion-status" role="alert" tabindex="-1"><strong>Guard completion refused</strong><span>${escapeHTML(verification.message)}</span><span>No completed proposal, readiness, commitment, adoption, progress, execution, or authority state was retained.</span></div>`;
  }
  return `<div class="portable-status neutral private-blueprint-guard-completion-status" role="status" tabindex="-1"><strong>No guard completion verified</strong><span>Supply one explicit boolean and bounded local provenance code for every unknown guard. The result still requires a separate completion review.</span></div>`;
}

function privateBlueprintGuardCompletionReviewReasonOptions(decision) {
  const reasons = dataAdapter?.PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_REASONS?.[decision] || [];
  return reasons.map((reasonCode) => `<option value="${escapeHTML(reasonCode)}" ${reasonCode === state.privateBlueprintGuardCompletionReviewReason ? "selected" : ""}>${escapeHTML(PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_REASON_LABELS[reasonCode] || reasonCode)}</option>`).join("");
}

function privateBlueprintGuardCompletionReviewStatusMarkup() {
  const verification = state.privateBlueprintGuardCompletionReviewVerification;
  if (verification?.status === "verified") {
    const result = verification.result;
    const review = result.review;
    const candidate = review.localCommitReviewCandidate;
    const candidateStatus = candidate
      ? `<span>Local candidate reviewed for operator commit decision · not commit-ready</span><span>${escapeHTML(candidate.commitReadinessStatus.replaceAll("_", " "))} · operator review ${escapeHTML(candidate.operatorReviewStatus.replaceAll("_", " "))}</span>`
      : `<span>No operator commit-review candidate was created.</span>`;
    return `<div class="portable-status verified private-blueprint-guard-completion-review-status" role="status" tabindex="-1"><strong>Guard-completion review verified · immutable private decision</strong><span>SHA-256 ${escapeHTML(result.packetDigest)}</span><span>${escapeHTML(PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_DECISION_LABELS[review.decision] || review.decision)} · ${escapeHTML(PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_REASON_LABELS[review.reasonCode] || review.reasonCode)}</span><span>Reviewer ${escapeHTML(review.reviewer.label)} · identity unattested · guard-value provenance unattested</span>${candidateStatus}<span>No blueprint was committed, adopted, qualified, activated, played, executed, registered, ranked, or published.</span></div>`;
  }
  if (verification?.status === "invalid") {
    return `<div class="portable-status invalid private-blueprint-guard-completion-review-status" role="alert" tabindex="-1"><strong>Guard-completion review refused</strong><span>${escapeHTML(verification.message)}</span><span>The verified upstream completion remains available. No review, candidate, readiness, commitment, adoption, progress, execution, or authority state was retained.</span></div>`;
  }
  return `<div class="portable-status neutral private-blueprint-guard-completion-review-status" role="status" tabindex="-1"><strong>No guard-completion review verified</strong><span>Review one verified complete proposal or paste one canonical review receipt. Accept only prepares a local candidate for a later operator decision.</span></div>`;
}

function privateBlueprintOperatorReviewPacketStatusMarkup() {
  const verification = state.privateBlueprintOperatorReviewPacketVerification;
  if (verification?.status === "verified") {
    const result = verification.result;
    const packet = result.operatorReviewPacket;
    const diff = packet.exactDiff.fields.map((field) => {
      const before = field.beforeValue === null ? "unknown" : String(field.beforeValue);
      return `${PRIVATE_BLUEPRINT_GUARD_LABELS[field.guardKey] || field.guardKey}: ${before} → ${field.afterValue} (${field.changeStatus.replaceAll("_", " ")})`;
    }).join("; ");
    return `<div class="portable-status verified private-blueprint-operator-review-packet-status" role="status" tabindex="-1"><strong>Operator packet verified · decision not run</strong><span>SHA-256 ${escapeHTML(result.packetDigest)}</span><span>Candidate ${escapeHTML(packet.candidateBinding.candidateDigest)}</span><span>${escapeHTML(diff)}</span><span>${packet.validationPlan.steps.length} validation steps · all evidence not run · rollback discard-only</span><span>Packet and candidate remain local, uncommitted, unadopted, not commit-ready, unqualified, unplayed, unexecuted, unregistered, and unpublished.</span></div>`;
  }
  if (verification?.status === "invalid") {
    return `<div class="portable-status invalid private-blueprint-operator-review-packet-status" role="alert" tabindex="-1"><strong>Operator packet refused</strong><span>${escapeHTML(verification.message)}</span><span>The verified upstream completion review remains available. No operator decision, validation, commitment, adoption, readiness, execution, or authority state was retained.</span></div>`;
  }
  return `<div class="portable-status neutral private-blueprint-operator-review-packet-status" role="status" tabindex="-1"><strong>No operator packet verified</strong><span>Prepare one only from an accepted completion review, or paste one canonical packet. Preparation decides nothing and runs no validation.</span></div>`;
}

function privateBlueprintOperatorReviewPacketMarkup() {
  const prepared = state.privateBlueprintOperatorReviewPacketReceipt;
  const review = state.privateBlueprintGuardCompletionReviewVerification?.status === "verified"
    ? state.privateBlueprintGuardCompletionReviewVerification.result.review
    : null;
  const canPrepare = review?.decision === "accept_for_commit_review" && Boolean(review.localCommitReviewCandidate);
  return `<section class="portable-review-exchange private-blueprint-operator-review-packet" aria-labelledby="private-blueprint-operator-review-packet-title"><div><p class="eyebrow">Local operator handoff</p><h4 id="private-blueprint-operator-review-packet-title">Prepare one packet. Decide nothing.</h4><p>Reverify the accepted completion review, expose the exact original-to-candidate guard diff, list every validation as not run, and keep rollback discard-only.</p></div>${canPrepare ? `<button class="secondary-button" type="button" data-private-blueprint-operator-review-packet-create>Prepare local operator packet</button>` : `<p class="portable-digest">An accepted completion review with a local candidate is required. Defer and reject fail closed.</p>`}${prepared ? `<label for="private-blueprint-operator-review-packet-export">Canonical operator-review packet · read only</label><textarea id="private-blueprint-operator-review-packet-export" class="portable-textarea" rows="20" readonly spellcheck="false">${escapeHTML(prepared.serialized)}</textarea><p class="portable-digest">Operator packet SHA-256 ${escapeHTML(prepared.packet.integrity.payloadDigest)}</p>` : ""}<label for="private-blueprint-operator-review-packet-import">Paste canonical operator-review packet JSON</label><textarea id="private-blueprint-operator-review-packet-import" class="portable-textarea" rows="20" maxlength="8388608" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Paste builderwars.mobile-private-blueprint-operator-review-packet.v1 JSON">${escapeHTML(state.privateBlueprintOperatorReviewPacketImportText)}</textarea><button class="secondary-button" type="button" data-private-blueprint-operator-review-packet-verify>Verify operator packet</button>${privateBlueprintOperatorReviewPacketStatusMarkup()}<div class="learning-boundary">This packet is a local review aid only. It cannot attest an operator or reviewer, run validation, approve a change, make a candidate commit-ready, commit or adopt a blueprint, bind rules, qualify, activate, play, execute, register, rank, publish, spend, or call a provider.</div></section>`;
}

function privateBlueprintGuardCompletionReviewMarkup() {
  const prepared = state.privateBlueprintGuardCompletionReviewReceipt;
  const canReview = state.privateBlueprintGuardCompletionVerification?.status === "verified";
  const decisionOptions = Object.entries(PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_DECISION_LABELS).map(([decision, label]) => `<option value="${escapeHTML(decision)}" ${decision === state.privateBlueprintGuardCompletionReviewDecision ? "selected" : ""}>${escapeHTML(label)}</option>`).join("");
  return `<section class="portable-review private-blueprint-guard-completion-review" aria-labelledby="private-blueprint-guard-completion-review-title"><div><p class="eyebrow">Private completion review</p><h4 id="private-blueprint-guard-completion-review-title">Review one completion. Commit nothing.</h4><p>Accept may prepare only a local candidate for a later operator commit decision. Defer and reject prepare no candidate. Every outcome preserves unattested identity and provenance.</p></div>${canReview ? `<div class="portable-review-form" role="group" aria-describedby="private-blueprint-guard-completion-review-boundary"><label for="private-blueprint-guard-completion-review-reviewer-label">Unattested reviewer label</label><input id="private-blueprint-guard-completion-review-reviewer-label" type="text" maxlength="36" autocomplete="off" value="${escapeHTML(state.privateBlueprintGuardCompletionReviewReviewerLabel)}" placeholder="Example: local referee"><label for="private-blueprint-guard-completion-review-decision">Private decision</label><select id="private-blueprint-guard-completion-review-decision" data-private-blueprint-guard-completion-review-decision>${decisionOptions}</select><label for="private-blueprint-guard-completion-review-reason">Bounded reason</label><select id="private-blueprint-guard-completion-review-reason" data-private-blueprint-guard-completion-review-reason>${privateBlueprintGuardCompletionReviewReasonOptions(state.privateBlueprintGuardCompletionReviewDecision)}</select><button class="secondary-button" type="button" data-private-blueprint-guard-completion-review-create>Record immutable completion review</button></div>` : `<p class="portable-digest">Verify one complete guard-completion proposal before recording a review.</p>`}${prepared ? `<label for="private-blueprint-guard-completion-review-export">Canonical completion-review receipt · read only</label><textarea id="private-blueprint-guard-completion-review-export" class="portable-textarea" rows="18" readonly spellcheck="false">${escapeHTML(prepared.serialized)}</textarea><p class="portable-digest">Completion-review SHA-256 ${escapeHTML(prepared.packet.integrity.payloadDigest)}</p>` : ""}<label for="private-blueprint-guard-completion-review-import">Paste canonical completion-review receipt JSON</label><textarea id="private-blueprint-guard-completion-review-import" class="portable-textarea" rows="18" maxlength="7340032" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Paste builderwars.mobile-private-blueprint-guard-completion-review.v1 JSON">${escapeHTML(state.privateBlueprintGuardCompletionReviewImportText)}</textarea><button class="secondary-button" type="button" data-private-blueprint-guard-completion-review-verify>Verify completion review</button>${privateBlueprintGuardCompletionReviewStatusMarkup()}${privateBlueprintOperatorReviewPacketMarkup()}<div class="learning-boundary" id="private-blueprint-guard-completion-review-boundary">This immutable local review cannot attest identity or provenance, make a candidate commit-ready, commit or adopt a blueprint, declare correctness, create consensus or approval, award progress, mutate lineage, bind rules, qualify, activate, play, execute, register, rank, publish, spend, or call a provider.</div></section>`;
}

function privateBlueprintGuardCompletionMarkup() {
  const prepared = state.privateBlueprintGuardCompletionReceipt;
  const candidate = privateBlueprintGuardCompletionCandidate();
  ensurePrivateBlueprintGuardCompletionSelections();
  const reasonOptions = (dataAdapter?.PRIVATE_BLUEPRINT_GUARD_COMPLETION_REASONS || []).map((reasonCode) => `<option value="${escapeHTML(reasonCode)}" ${reasonCode === state.privateBlueprintGuardCompletionReason ? "selected" : ""}>${escapeHTML(PRIVATE_BLUEPRINT_GUARD_COMPLETION_REASON_LABELS[reasonCode] || reasonCode)}</option>`).join("");
  const guardFields = (candidate?.unknownGuardKeys || []).map((guardKey) => {
    const selectedValue = state.privateBlueprintGuardCompletionValues[guardKey];
    const selectedProvenance = state.privateBlueprintGuardCompletionProvenance[guardKey];
    const provenanceOptions = (dataAdapter?.PRIVATE_BLUEPRINT_GUARD_COMPLETION_PROVENANCE_CODES || []).map((code) => `<option value="${escapeHTML(code)}" ${code === selectedProvenance ? "selected" : ""}>${escapeHTML(PRIVATE_BLUEPRINT_GUARD_COMPLETION_PROVENANCE_LABELS[code] || code)}</option>`).join("");
    return `<div class="portable-review-form private-blueprint-guard-completion-entry"><strong>${escapeHTML(PRIVATE_BLUEPRINT_GUARD_LABELS[guardKey] || guardKey)}</strong><label for="private-blueprint-guard-completion-value-${escapeHTML(guardKey)}">Explicit boolean value</label><select id="private-blueprint-guard-completion-value-${escapeHTML(guardKey)}" data-private-blueprint-guard-completion-value="${escapeHTML(guardKey)}"><option value="" ${selectedValue === "" ? "selected" : ""}>Choose true or false</option><option value="true" ${selectedValue === true ? "selected" : ""}>True</option><option value="false" ${selectedValue === false ? "selected" : ""}>False</option></select><label for="private-blueprint-guard-completion-provenance-${escapeHTML(guardKey)}">Local provenance</label><select id="private-blueprint-guard-completion-provenance-${escapeHTML(guardKey)}" data-private-blueprint-guard-completion-provenance="${escapeHTML(guardKey)}">${provenanceOptions}</select></div>`;
  }).join("");
  const blocked = state.privateBlueprintDraftReviewVerification?.status === "verified" && !candidate
    ? `<p class="portable-digest">Only an accepted blueprint-draft review with an explicit local candidate can propose guard completion.</p>`
    : "";
  return `<section class="portable-review-exchange private-blueprint-guard-completion" aria-labelledby="private-blueprint-guard-completion-title"><div><p class="eyebrow">Explicit guard completion</p><h4 id="private-blueprint-guard-completion-title">Close every unknown. Claim no readiness.</h4><p>Complete exactly the candidate's unknown guard set with explicit booleans and local, identity-unattested provenance. Known and applied guards cannot change.</p></div>${candidate ? `<div role="group" aria-describedby="private-blueprint-guard-completion-boundary"><label for="private-blueprint-guard-completion-reviewer-label">Unattested reviewer label</label><input id="private-blueprint-guard-completion-reviewer-label" type="text" maxlength="36" autocomplete="off" value="${escapeHTML(state.privateBlueprintGuardCompletionReviewerLabel)}" placeholder="Example: local reviewer"><label for="private-blueprint-guard-completion-reason">Bounded reason</label><select id="private-blueprint-guard-completion-reason" data-private-blueprint-guard-completion-reason>${reasonOptions}</select>${guardFields}<button class="secondary-button" type="button" data-private-blueprint-guard-completion-create>Propose explicit guard completion</button></div>` : blocked}${prepared ? `<label for="private-blueprint-guard-completion-export">Canonical guard-completion proposal · read only</label><textarea id="private-blueprint-guard-completion-export" class="portable-textarea" rows="16" readonly spellcheck="false">${escapeHTML(prepared.serialized)}</textarea><p class="portable-digest">Guard completion SHA-256 ${escapeHTML(prepared.packet.integrity.payloadDigest)}</p>` : ""}<label for="private-blueprint-guard-completion-import">Paste canonical guard-completion proposal JSON</label><textarea id="private-blueprint-guard-completion-import" class="portable-textarea" rows="16" maxlength="6291456" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Paste builderwars.mobile-private-blueprint-guard-completion-proposal.v1 JSON">${escapeHTML(state.privateBlueprintGuardCompletionImportText)}</textarea><button class="secondary-button" type="button" data-private-blueprint-guard-completion-verify>Verify guard completion</button>${privateBlueprintGuardCompletionStatusMarkup()}${privateBlueprintGuardCompletionReviewMarkup()}<div class="learning-boundary" id="private-blueprint-guard-completion-boundary">This local proposal cannot attest identity or provenance, declare correctness, create consensus or approval, award progress, become commit-ready, commit or adopt a blueprint, mutate source lineage, bind rules, qualify, play, execute, register, rank, publish, spend, or call a provider.</div></section>`;
}

function privateBlueprintDraftReviewMarkup() {
  const prepared = state.privateBlueprintDraftReviewReceipt;
  const canReview = state.privateBlueprintRevisionDraftVerification?.status === "verified";
  const decisionOptions = Object.entries(PRIVATE_BLUEPRINT_DRAFT_REVIEW_DECISION_LABELS).map(([decision, label]) => `<option value="${escapeHTML(decision)}" ${decision === state.privateBlueprintDraftReviewDecision ? "selected" : ""}>${escapeHTML(label)}</option>`).join("");
  return `<section class="portable-review private-blueprint-draft-review" aria-labelledby="private-blueprint-draft-review-title"><div><p class="eyebrow">Private blueprint-draft review</p><h4 id="private-blueprint-draft-review-title">Review the draft. Commit nothing.</h4><p>Accept can create only an uncommitted, unadopted local candidate. Unknown guard values remain explicit and block commit readiness. Defer and reject create no candidate.</p></div>${canReview ? `<div class="portable-review-form" role="group" aria-describedby="private-blueprint-draft-review-boundary"><label for="private-blueprint-draft-reviewer-label">Unattested reviewer label</label><input id="private-blueprint-draft-reviewer-label" type="text" maxlength="36" autocomplete="off" value="${escapeHTML(state.privateBlueprintDraftReviewerLabel)}" placeholder="Example: local reviewer"><label for="private-blueprint-draft-review-decision">Private decision</label><select id="private-blueprint-draft-review-decision" data-private-blueprint-draft-review-decision>${decisionOptions}</select><label for="private-blueprint-draft-review-reason">Bounded reason</label><select id="private-blueprint-draft-review-reason" data-private-blueprint-draft-review-reason>${privateBlueprintDraftReviewReasonOptions(state.privateBlueprintDraftReviewDecision)}</select><button class="secondary-button" type="button" data-private-blueprint-draft-review-create>Record immutable draft review</button></div>` : ""}${prepared ? `<label for="private-blueprint-draft-review-export">Canonical blueprint draft review · read only</label><textarea id="private-blueprint-draft-review-export" class="portable-textarea" rows="14" readonly spellcheck="false">${escapeHTML(prepared.serialized)}</textarea><p class="portable-digest">Blueprint draft review SHA-256 ${escapeHTML(prepared.packet.integrity.payloadDigest)}</p>` : ""}<label for="private-blueprint-draft-review-import">Paste canonical blueprint draft review JSON</label><textarea id="private-blueprint-draft-review-import" class="portable-textarea" rows="14" maxlength="5242880" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Paste builderwars.mobile-private-blueprint-revision-draft-review.v1 JSON">${escapeHTML(state.privateBlueprintDraftReviewImportText)}</textarea><button class="secondary-button" type="button" data-private-blueprint-draft-review-verify>Verify blueprint draft review</button>${privateBlueprintDraftReviewStatusMarkup()}${privateBlueprintGuardCompletionMarkup()}<div class="learning-boundary" id="private-blueprint-draft-review-boundary">This immutable private review cannot authenticate a reviewer, declare correctness, create consensus or approval, invent guard values, award progress, commit or adopt a blueprint, bind rules, qualify, play, execute, register, rank, publish, spend, or call a provider.</div></section>`;
}

function privateBlueprintRevisionDraftMarkup() {
  const prepared = state.privateBlueprintRevisionDraftReceipt;
  const review = state.privateBlueprintDeltaReviewVerification?.status === "verified"
    ? state.privateBlueprintDeltaReviewVerification.result.review
    : null;
  const canCreate = review?.decision === "accept_for_revision" && review.localRevisionCandidate;
  const blockedByDecision = review && !canCreate
    ? `<p class="portable-digest">This ${escapeHTML(PRIVATE_BLUEPRINT_DELTA_REVIEW_DECISION_LABELS[review.decision] || review.decision)} review cannot create a draft.</p>`
    : "";
  return `<section class="portable-review-exchange private-blueprint-revision-draft" aria-labelledby="private-blueprint-revision-draft-title"><div><p class="eyebrow">Versioned local blueprint draft</p><h4 id="private-blueprint-revision-draft-title">Apply one reviewed guard. Invent nothing else.</h4><p>The draft copies the bound parent blueprint and changes only the accepted allowlisted guard. Missing guard values stay explicitly unknown.</p></div>${canCreate ? `<button class="secondary-button" type="button" data-private-blueprint-revision-draft-create>${prepared ? "Refresh local revision draft" : "Create local revision draft"}</button>` : blockedByDecision}${prepared ? `<label for="private-blueprint-revision-draft-export">Canonical blueprint revision draft · read only</label><textarea id="private-blueprint-revision-draft-export" class="portable-textarea" rows="14" readonly spellcheck="false">${escapeHTML(prepared.serialized)}</textarea><p class="portable-digest">Blueprint revision draft SHA-256 ${escapeHTML(prepared.packet.integrity.payloadDigest)}</p>` : ""}<label for="private-blueprint-revision-draft-import">Paste canonical blueprint revision draft JSON</label><textarea id="private-blueprint-revision-draft-import" class="portable-textarea" rows="14" maxlength="4194304" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Paste builderwars.mobile-private-blueprint-revision-draft.v1 JSON">${escapeHTML(state.privateBlueprintRevisionDraftImportText)}</textarea><button class="secondary-button" type="button" data-private-blueprint-revision-draft-verify>Verify blueprint revision draft</button>${privateBlueprintRevisionDraftStatusMarkup()}${privateBlueprintDraftReviewMarkup()}<div class="learning-boundary">This local draft cannot authenticate identity, declare correctness, create consensus or approval, award progress, mutate its parent, commit or adopt a blueprint, bind rules, qualify, play, execute, register, rank, publish, spend, or call a provider.</div></section>`;
}

function privateBlueprintDeltaReviewMarkup() {
  const prepared = state.privateBlueprintDeltaReviewReceipt;
  const canReview = state.privateBlueprintDeltaVerification?.status === "verified";
  const decisionOptions = Object.entries(PRIVATE_BLUEPRINT_DELTA_REVIEW_DECISION_LABELS).map(([decision, label]) => `<option value="${escapeHTML(decision)}" ${decision === state.privateBlueprintDeltaReviewDecision ? "selected" : ""}>${escapeHTML(label)}</option>`).join("");
  return `<section class="portable-review private-blueprint-delta-review" aria-labelledby="private-blueprint-delta-review-title"><div><p class="eyebrow">Private guard-proposal review</p><h4 id="private-blueprint-delta-review-title">Record one decision. Adopt nothing.</h4><p>Accept-for-revision can create only an uncommitted local candidate. Defer and reject create no candidate. Every decision stays private and identity-unattested.</p></div>${canReview ? `<div class="portable-review-form" role="group" aria-describedby="private-blueprint-delta-review-boundary"><label for="private-blueprint-delta-reviewer-label">Unattested reviewer label</label><input id="private-blueprint-delta-reviewer-label" type="text" maxlength="36" autocomplete="off" value="${escapeHTML(state.privateBlueprintDeltaReviewerLabel)}" placeholder="Example: local reviewer"><label for="private-blueprint-delta-review-decision">Private decision</label><select id="private-blueprint-delta-review-decision" data-private-blueprint-delta-review-decision>${decisionOptions}</select><label for="private-blueprint-delta-review-reason">Bounded reason</label><select id="private-blueprint-delta-review-reason" data-private-blueprint-delta-review-reason>${privateBlueprintDeltaReviewReasonOptions(state.privateBlueprintDeltaReviewDecision)}</select><button class="secondary-button" type="button" data-private-blueprint-delta-review-create>Record immutable guard review</button></div>` : ""}${prepared ? `<label for="private-blueprint-delta-review-export">Canonical guard review receipt · read only</label><textarea id="private-blueprint-delta-review-export" class="portable-textarea" rows="12" readonly spellcheck="false">${escapeHTML(prepared.serialized)}</textarea><p class="portable-digest">Guard review SHA-256 ${escapeHTML(prepared.packet.integrity.payloadDigest)}</p>` : ""}<label for="private-blueprint-delta-review-import">Paste canonical guard review receipt JSON</label><textarea id="private-blueprint-delta-review-import" class="portable-textarea" rows="12" maxlength="3145728" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Paste builderwars.mobile-private-inspection-blueprint-delta-review.v1 JSON">${escapeHTML(state.privateBlueprintDeltaReviewImportText)}</textarea><button class="secondary-button" type="button" data-private-blueprint-delta-review-verify>Verify guard review receipt</button>${privateBlueprintDeltaReviewStatusMarkup()}${privateBlueprintRevisionDraftMarkup()}<div class="learning-boundary" id="private-blueprint-delta-review-boundary">This immutable private review cannot authenticate a reviewer, declare correctness, create consensus or approval, award progress, adopt or commit a guard, edit the parent, bind rules, qualify, play, execute, register, rank, publish, spend, or call a provider.</div></section>`;
}

function privateBlueprintDeltaMarkup() {
  const prepared = state.privateBlueprintDeltaReceipt;
  return `<section class="portable-review-exchange private-blueprint-delta" aria-labelledby="private-blueprint-delta-title"><div><p class="eyebrow">Inspection-to-blueprint proposal</p><h4 id="private-blueprint-delta-title">Propose one guard. Adopt nothing.</h4><p>A fixed lesson mapping can propose strict validation, fallback disclosure, or a human checkpoint. It cannot choose a packet, edit the parent proposal, commit a blueprint, or activate a runback.</p></div>${prepared ? `<label for="private-blueprint-delta-export">Canonical guard proposal · read only</label><textarea id="private-blueprint-delta-export" class="portable-textarea" rows="11" readonly spellcheck="false">${escapeHTML(prepared.serialized)}</textarea><p class="portable-digest">Guard proposal SHA-256 ${escapeHTML(prepared.packet.integrity.payloadDigest)}</p>` : ""}<label for="private-blueprint-delta-import">Paste canonical guard proposal JSON</label><textarea id="private-blueprint-delta-import" class="portable-textarea" rows="11" maxlength="2621440" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Paste builderwars.mobile-private-inspection-blueprint-delta.v1 JSON">${escapeHTML(state.privateBlueprintDeltaImportText)}</textarea><button class="secondary-button" type="button" data-private-blueprint-delta-verify>Verify guard proposal</button>${privateBlueprintDeltaStatusMarkup()}${privateBlueprintDeltaReviewMarkup()}<div class="learning-boundary">This is a memory-only, proposed requirement. It remains uncommitted and unplayed and cannot create correctness, consensus, approval, progress, blueprint adoption, identity, merge, resolution, rules, qualification, execution, registry, ranking, publication, spending, or provider authority.</div></section>`;
}

function portableRunbackMarkup({ canPrepare = false } = {}) {
  const portable = state.portableRunback;
  return `<div class="portable-runback" aria-labelledby="portable-runback-title"><div><p class="eyebrow">Portable proposal</p><h4 id="portable-runback-title">Carry or inspect exact unplayed runback JSON.</h4><p>A local SHA-256 checksum detects changed content. It is not a signature or provider attestation.</p></div>${canPrepare ? `<button class="secondary-button" type="button" data-portable-prepare>${portable ? "Refresh portable JSON" : "Prepare portable JSON"}</button>` : ""}${portable ? `<label for="portable-runback-export">Canonical export · read only</label><textarea id="portable-runback-export" class="portable-textarea" rows="6" readonly spellcheck="false">${escapeHTML(portable.serialized)}</textarea><p class="portable-digest">SHA-256 ${escapeHTML(portable.envelope.integrity.payloadDigest)}</p>` : ""}<label for="portable-runback-import">Paste canonical proposal JSON</label><textarea id="portable-runback-import" class="portable-textarea" rows="6" maxlength="32768" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Paste builderwars.mobile-runback-portable.v1 JSON">${escapeHTML(state.portableImportText)}</textarea><button class="secondary-button" type="button" data-portable-verify>Verify pasted proposal</button>${portableVerificationMarkup()}${portableReviewMarkup()}${portableReviewCorrectionMarkup()}${portableReviewExchangeMarkup()}${portableReviewCorrectionExchangeMarkup()}${portableReviewComparisonMarkup()}${privateReviewLearningMarkup()}${privateBlueprintDeltaMarkup()}<div class="learning-boundary">Verification is local inspection only. It cannot authenticate origin, bind missing rules, activate a runner, change registry state, rank a result, publish, or spend.</div></div>`;
}

function renderReceiptLearning() {
  const container = $("#receipt-learning");
  if (!container) return;
  const action = state.learningAction;
  if (!action) {
    container.innerHTML = `<div class="empty-state receipt-learning-empty"><strong>Open a reviewed receipt to learn, or inspect a portable proposal.</strong><span>The lab summarizes visible evidence and offers bounded blueprint deltas. It never reads private reasoning.</span></div>${portableRunbackMarkup()}`;
    return;
  }
  const counts = action.receipt.moveSourceCounts;
  const deltaControls = action.allowedDeltas.map((delta) => `
    <button class="learning-delta ${delta.id === action.recommendedDeltaId ? "recommended" : ""}" type="button" data-runback-delta="${escapeHTML(delta.id)}">
      <span>${escapeHTML(delta.label)}</span><small>${escapeHTML(delta.rationale)}${delta.id === action.recommendedDeltaId ? " · receipt-guided" : ""}</small>
    </button>`).join("");
  const proposal = state.runbackProposal;
  let proposalMarkup = portableRunbackMarkup();
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
    proposalMarkup = `<div class="runback-proposal" id="runback-proposal"><div class="qualification-status"><span>Version 1 · local only</span><strong>Still unplayed</strong></div><div class="proof-grid">${rows.map(([label, value, tone]) => `<div class="proof-row"><span>${escapeHTML(label)}</span><strong class="${tone}">${escapeHTML(value)}</strong></div>`).join("")}</div><div class="proposal-blockers"><strong>Execution blockers</strong><span>${escapeHTML(proposal.executionBlockers.join(" · "))}</span></div><div class="proof-boundary"><strong>Proposal boundary:</strong> ${escapeHTML(proposal.boundary)} ${escapeHTML(proposal.rulesBinding.statement)}</div>${portableRunbackMarkup({ canPrepare: true })}<button class="text-button" type="button" data-runback-blueprint>Review local blueprint</button></div>`;
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

function hydrateStarterGuide() {
  state.starterGuideVisible = true;
  state.starterGuidePersistenceAvailable = true;
  try {
    const stored = localStorage.getItem(STARTER_GUIDE_STORAGE_KEY);
    if (stored === STARTER_GUIDE_COMPLETE) state.starterGuideVisible = false;
    else if (stored !== null) localStorage.removeItem(STARTER_GUIDE_STORAGE_KEY);
  } catch {
    state.starterGuidePersistenceAvailable = false;
  }
}

function renderStarterGuide() {
  const panel = $("#starter-panel");
  const showButton = $("#starter-guide-button");
  if (!panel || !showButton) return;
  panel.hidden = !state.starterGuideVisible;
  showButton.setAttribute("aria-expanded", String(state.starterGuideVisible));
  const persistence = $("#starter-persistence");
  if (persistence) {
    persistence.textContent = state.starterGuidePersistenceAvailable
      ? "Guide completion is remembered only in this browser."
      : "Browser storage is unavailable. The guide still works, but dismissal lasts only until refresh.";
  }
}

function completeStarterGuide() {
  state.starterGuideVisible = false;
  let persisted = false;
  try {
    localStorage.setItem(STARTER_GUIDE_STORAGE_KEY, STARTER_GUIDE_COMPLETE);
    persisted = true;
  } catch {
    state.starterGuidePersistenceAvailable = false;
  }
  renderStarterGuide();
  return persisted;
}

function showStarterGuide() {
  state.starterGuideVisible = true;
  showView("arena");
  renderStarterGuide();
  $("#starter-panel")?.focus?.({ preventScroll: true });
}

function hydrateLocalBlueprint() {
  state.blueprintStored = false;
  state.blueprintPersistenceAvailable = true;
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
    state.blueprintStored = true;
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
    state.blueprintStored = false;
    state.blueprintPersistenceAvailable = false;
    try { localStorage.removeItem(BLUEPRINT_STORAGE_KEY); } catch {}
  }
}

let blueprintRemovalTimer;

function renderSessionSheet() {
  const sourceStatus = $("#session-source-status");
  const blueprintStatus = $("#session-blueprint-status");
  const starterStatus = $("#session-starter-status");
  const storageStatus = $("#session-storage-status");
  const removeButton = $("[data-session-remove-blueprint]");
  if (!sourceStatus || !blueprintStatus || !starterStatus || !storageStatus || !removeButton) return;

  sourceStatus.textContent = state.data?.sourceMode === "verified_corpus"
    ? "Reviewed local corpus"
    : "Bounded demo fixture";
  blueprintStatus.textContent = state.blueprintPersistenceAvailable
    ? (state.blueprintStored ? "Saved in this browser" : "Not saved")
    : "Unavailable to inspect";
  starterStatus.textContent = state.starterGuideVisible ? "Open locally" : "Completed locally";
  storageStatus.textContent = state.blueprintPersistenceAvailable && state.starterGuidePersistenceAvailable
    ? "Available · browser only"
    : "Unavailable · page session only";

  removeButton.disabled = !state.blueprintStored || !state.blueprintPersistenceAvailable;
  removeButton.classList.toggle("is-armed", state.blueprintRemovalArmed);
  removeButton.textContent = state.blueprintRemovalArmed
    ? "Confirm remove blueprint"
    : "Remove saved blueprint";
}

function disarmBlueprintRemoval({ render = true } = {}) {
  window.clearTimeout(blueprintRemovalTimer);
  blueprintRemovalTimer = undefined;
  state.blueprintRemovalArmed = false;
  if (render) renderSessionSheet();
}

function restartStarterGuideFromSession() {
  disarmBlueprintRemoval({ render: false });
  try {
    localStorage.removeItem(STARTER_GUIDE_STORAGE_KEY);
  } catch {
    state.starterGuidePersistenceAvailable = false;
  }
  closeSheets({ restoreFocus: false });
  showStarterGuide();
  showToast(state.starterGuidePersistenceAvailable
    ? "Starter guide restarted in this browser. No account or remote preference was created."
    : "Starter guide restarted for this page. Browser storage is unavailable; nothing was uploaded.");
}

function armOrRemoveLocalBlueprint() {
  if (!state.blueprintStored || !state.blueprintPersistenceAvailable) return;
  if (!state.blueprintRemovalArmed) {
    state.blueprintRemovalArmed = true;
    renderSessionSheet();
    $("[data-session-remove-blueprint]")?.focus?.({ preventScroll: true });
    showToast("Removal armed. Press again to remove this browser-only blueprint. Nothing remote will change.");
    window.clearTimeout(blueprintRemovalTimer);
    blueprintRemovalTimer = window.setTimeout(() => disarmBlueprintRemoval(), 8000);
    return;
  }

  try {
    localStorage.removeItem(BLUEPRINT_STORAGE_KEY);
    if (localStorage.getItem(BLUEPRINT_STORAGE_KEY) !== null) throw new Error("browser storage retained blueprint");
    state.blueprintStored = false;
    disarmBlueprintRemoval({ render: false });
    $("#builder-form").reset();
    renderBlueprint();
    renderSessionSheet();
    showToast("Browser-only blueprint removed. Reviewed receipts and tracked source files were not deleted.");
  } catch {
    state.blueprintPersistenceAvailable = false;
    disarmBlueprintRemoval({ render: false });
    renderSessionSheet();
    showToast("Blueprint could not be removed from this browser. Nothing remote was changed.");
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
    state.portableRunback = null;
    state.portableImportText = "";
    state.portableVerification = null;
    resetPortableReviewState();
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
    state.portableRunback = null;
    state.portableImportText = "";
    state.portableVerification = null;
    resetPortableReviewState();
    renderReceiptLearning();
    return true;
  } catch {
    return false;
  }
}

async function preparePortableRunback() {
  if (!state.runbackProposal || !dataAdapter?.createPortableRunbackEnvelope) return false;
  try {
    state.portableRunback = await dataAdapter.createPortableRunbackEnvelope(state.runbackProposal);
    state.portableVerification = null;
    resetPortableReviewState({ keepReviewerLabel: true });
    renderReceiptLearning();
    return true;
  } catch {
    state.portableRunback = null;
    state.portableVerification = { status: "invalid", message: "The current proposal failed strict portable validation." };
    resetPortableReviewState({ keepReviewerLabel: true });
    renderReceiptLearning();
    return false;
  }
}

async function verifyPortableRunback(serializedInput) {
  state.portableImportText = String(serializedInput || "").slice(0, dataAdapter?.PORTABLE_RUNBACK_MAX_LENGTH || 32768);
  try {
    const priorDigest = state.portableVerification?.status === "verified" ? state.portableVerification.result.payloadDigest : null;
    const result = await dataAdapter.verifyPortableRunbackEnvelope(serializedInput);
    if (priorDigest !== result.payloadDigest) resetPortableReviewState({ keepReviewerLabel: true });
    state.portableVerification = { status: "verified", result };
    renderReceiptLearning();
    return true;
  } catch (error) {
    state.portableVerification = { status: "invalid", message: error?.message || "Portable proposal validation failed." };
    resetPortableReviewState({ keepReviewerLabel: true });
    renderReceiptLearning();
    return false;
  }
}

async function appendPortableReview() {
  const verification = state.portableVerification;
  if (verification?.status !== "verified" || !dataAdapter?.appendPortableRunbackReview) return false;
  try {
    const review = await dataAdapter.appendPortableRunbackReview(verification.result, {
      reviewerLabel: state.portableReviewerLabel.trim(),
      decision: state.portableReviewDecision,
      reasonCode: state.portableReviewReason,
    }, state.portableReviews);
    const nextReviews = [...state.portableReviews, review];
    if (state.portableReviewCorrections.length > 0) {
      await dataAdapter.verifyPortableRunbackReviewCorrectionJournal(
        state.portableReviewCorrections, verification.result, nextReviews,
      );
    }
    state.portableReviews = nextReviews;
    state.portableReviewerLabel = state.portableReviewerLabel.trim();
    resetPortableReviewExchangeState();
    resetPortableReviewCorrectionExchangeState();
    state.portableReviewCorrectionMessage = null;
    state.portableReviewMessage = {
      status: "verified",
      title: `Private review ${review.sequence} appended`,
      detail: review.blueprintRevision
        ? "A proposed uncommitted blueprint revision was created. Qualification and execution remain disabled."
        : "No blueprint revision was created. The proposal remains still unplayed.",
    };
    renderReceiptLearning();
    return true;
  } catch (error) {
    state.portableReviewMessage = {
      status: "invalid",
      title: "Private review refused",
      detail: error?.message || "The review record failed strict local validation.",
    };
    renderReceiptLearning();
    return false;
  }
}

async function preparePortableReviewExchange() {
  const verification = state.portableVerification;
  if (verification?.status !== "verified" || !dataAdapter?.createPortableRunbackReviewExchange) return false;
  try {
    state.portableReviewExchange = await dataAdapter.createPortableRunbackReviewExchange(state.portableImportText, state.portableReviews);
    state.portableReviewExchangeVerification = null;
    renderReceiptLearning();
    return true;
  } catch (error) {
    state.portableReviewExchange = null;
    state.portableReviewExchangeVerification = { status: "invalid", message: error?.message || "Portable review packet preparation failed." };
    renderReceiptLearning();
    return false;
  }
}

async function verifyPortableReviewExchange(serializedInput) {
  const importedText = String(serializedInput || "").slice(0, dataAdapter?.PORTABLE_REVIEW_EXCHANGE_MAX_LENGTH || 262144);
  try {
    const result = await dataAdapter.verifyPortableRunbackReviewExchange(serializedInput);
    state.runbackProposal = null;
    state.portableRunback = null;
    state.portableImportText = result.proposalSerialized;
    state.portableVerification = { status: "verified", result: result.proposalVerification };
    state.portableReviews = result.journal.reviews;
    state.portableReviewMessage = null;
    resetPortableReviewCorrectionState({ keepReviewerLabel: true });
    state.portableReviewExchange = null;
    state.portableReviewExchangeImportText = importedText;
    state.portableReviewExchangeVerification = { status: "verified", result };
    renderReceiptLearning();
    return true;
  } catch (error) {
    state.portableVerification = null;
    state.portableImportText = "";
    resetPortableReviewState({ keepReviewerLabel: true });
    state.portableReviewExchangeImportText = importedText;
    state.portableReviewExchangeVerification = { status: "invalid", message: error?.message || "Portable review packet validation failed." };
    renderReceiptLearning();
    return false;
  }
}

async function appendPortableReviewCorrection() {
  const verification = state.portableVerification;
  if (verification?.status !== "verified" || !dataAdapter?.appendPortableRunbackReviewCorrection) return false;
  try {
    const correction = await dataAdapter.appendPortableRunbackReviewCorrection(
      verification.result,
      state.portableReviews,
      {
        reviewerLabel: state.portableCorrectionReviewerLabel.trim(),
        targetReviewDigest: state.portableCorrectionTargetDigest,
        action: state.portableCorrectionAction,
        correctedDecision: state.portableCorrectionAction === "correct_decision" ? state.portableCorrectionDecision : null,
        reasonCode: state.portableCorrectionReason,
      },
      state.portableReviewCorrections,
    );
    state.portableReviewCorrections = [...state.portableReviewCorrections, correction];
    state.portableCorrectionReviewerLabel = state.portableCorrectionReviewerLabel.trim();
    resetPortableReviewCorrectionExchangeState();
    state.portableReviewCorrectionMessage = {
      status: "verified",
      title: `Private correction ${correction.sequence} appended`,
      detail: correction.action === "withdraw_review"
        ? "The original review remains immutable and is now privately interpreted as withdrawn."
        : correction.blueprintRevision
          ? "The corrected acceptance created only a proposed, uncommitted correction revision. Qualification and execution remain disabled."
          : "The original review remains immutable; only its current private interpretation changed.",
    };
    renderReceiptLearning();
    return true;
  } catch (error) {
    state.portableReviewCorrectionMessage = {
      status: "invalid",
      title: "Private correction refused",
      detail: error?.message || "The correction record failed strict local validation.",
    };
    renderReceiptLearning();
    return false;
  }
}

async function preparePortableReviewCorrectionExchange() {
  const verification = state.portableVerification;
  if (verification?.status !== "verified" || state.portableReviewCorrections.length === 0 || !dataAdapter?.createPortableRunbackReviewCorrectionExchange) return false;
  try {
    state.portableReviewCorrectionExchange = await dataAdapter.createPortableRunbackReviewCorrectionExchange(
      state.portableImportText,
      state.portableReviews,
      state.portableReviewCorrections,
    );
    state.portableReviewCorrectionExchangeVerification = null;
    renderReceiptLearning();
    return true;
  } catch (error) {
    state.portableReviewCorrectionExchange = null;
    state.portableReviewCorrectionExchangeVerification = { status: "invalid", message: error?.message || "Portable correction packet preparation failed." };
    renderReceiptLearning();
    return false;
  }
}

async function verifyPortableReviewCorrectionExchange(serializedInput) {
  const importedText = String(serializedInput || "").slice(0, dataAdapter?.PORTABLE_REVIEW_CORRECTION_EXCHANGE_MAX_LENGTH || 524288);
  try {
    const result = await dataAdapter.verifyPortableRunbackReviewCorrectionExchange(serializedInput);
    state.runbackProposal = null;
    state.portableRunback = null;
    state.portableImportText = result.proposalSerialized;
    state.portableVerification = { status: "verified", result: result.proposalVerification };
    state.portableReviews = result.journal.reviews;
    state.portableReviewMessage = null;
    state.portableReviewExchange = null;
    state.portableReviewExchangeImportText = result.reviewExchangeSerialized;
    state.portableReviewExchangeVerification = null;
    state.portableReviewCorrections = result.correctionJournal.corrections;
    state.portableReviewCorrectionMessage = null;
    state.portableReviewCorrectionExchange = null;
    state.portableReviewCorrectionExchangeImportText = importedText;
    state.portableReviewCorrectionExchangeVerification = { status: "verified", result };
    ensurePortableCorrectionSelection();
    renderReceiptLearning();
    return true;
  } catch (error) {
    state.runbackProposal = null;
    state.portableRunback = null;
    state.portableVerification = null;
    state.portableImportText = "";
    resetPortableReviewState({ keepReviewerLabel: true });
    state.portableReviewCorrectionExchangeImportText = importedText;
    state.portableReviewCorrectionExchangeVerification = { status: "invalid", message: error?.message || "Portable correction packet validation failed." };
    renderReceiptLearning();
    return false;
  }
}

async function createPortableReviewComparison() {
  if (!dataAdapter?.createPortablePrivateReviewComparison || !dataAdapter?.verifyPortablePrivateReviewComparison) return false;
  resetPrivateReviewLearningState();
  try {
    const receipt = await dataAdapter.createPortablePrivateReviewComparison(
      state.portableReviewComparisonLeftText,
      state.portableReviewComparisonRightText,
    );
    const result = await dataAdapter.verifyPortablePrivateReviewComparison(receipt.serialized);
    state.portableReviewComparisonReceipt = receipt;
    state.portableReviewComparisonImportText = receipt.serialized;
    state.portableReviewComparisonVerification = { status: "verified", result };
    renderReceiptLearning();
    return true;
  } catch (error) {
    state.portableReviewComparisonReceipt = null;
    state.portableReviewComparisonImportText = "";
    state.portableReviewComparisonVerification = { status: "invalid", message: error?.message || "Private review comparison failed." };
    renderReceiptLearning();
    return false;
  }
}

async function verifyPortableReviewComparison(serializedInput) {
  const importedText = String(serializedInput || "").slice(0, dataAdapter?.PORTABLE_REVIEW_COMPARISON_MAX_LENGTH || 1572864);
  resetPrivateReviewLearningState();
  try {
    const result = await dataAdapter.verifyPortablePrivateReviewComparison(serializedInput);
    state.portableReviewComparisonReceipt = null;
    state.portableReviewComparisonLeftText = result.leftSerialized;
    state.portableReviewComparisonRightText = result.rightSerialized;
    state.portableReviewComparisonImportText = importedText;
    state.portableReviewComparisonVerification = { status: "verified", result };
    renderReceiptLearning();
    return true;
  } catch (error) {
    state.portableReviewComparisonReceipt = null;
    state.portableReviewComparisonVerification = { status: "invalid", message: error?.message || "Private review comparison receipt validation failed." };
    state.portableReviewComparisonImportText = importedText;
    renderReceiptLearning();
    return false;
  }
}

async function createPrivateReviewLearning() {
  if (!dataAdapter?.createPortablePrivateReviewLearning || !dataAdapter?.verifyPortablePrivateReviewLearning) return false;
  resetPrivateBlueprintDeltaState();
  const comparisonSerialized = state.portableReviewComparisonVerification?.status === "verified"
    ? state.portableReviewComparisonImportText
    : "";
  try {
    const receipt = await dataAdapter.createPortablePrivateReviewLearning(comparisonSerialized);
    const result = await dataAdapter.verifyPortablePrivateReviewLearning(receipt.serialized);
    state.privateReviewLearningReceipt = receipt;
    state.privateReviewLearningImportText = receipt.serialized;
    state.privateReviewLearningVerification = { status: "verified", result };
    renderReceiptLearning();
    return true;
  } catch (error) {
    state.privateReviewLearningReceipt = null;
    state.privateReviewLearningImportText = "";
    state.privateReviewLearningVerification = { status: "invalid", message: error?.message || "Private review inspection learning failed." };
    renderReceiptLearning();
    return false;
  }
}

async function verifyPrivateReviewLearning(serializedInput) {
  const importedText = String(serializedInput || "").slice(0, dataAdapter?.PRIVATE_REVIEW_LEARNING_MAX_LENGTH || 2097152);
  resetPrivateBlueprintDeltaState();
  try {
    const result = await dataAdapter.verifyPortablePrivateReviewLearning(serializedInput);
    state.privateReviewLearningReceipt = null;
    state.privateReviewLearningImportText = importedText;
    state.privateReviewLearningVerification = { status: "verified", result };
    state.portableReviewComparisonReceipt = null;
    state.portableReviewComparisonImportText = result.comparisonSerialized;
    state.portableReviewComparisonVerification = { status: "verified", result: result.comparisonVerification };
    state.portableReviewComparisonLeftText = result.comparisonVerification.leftSerialized;
    state.portableReviewComparisonRightText = result.comparisonVerification.rightSerialized;
    renderReceiptLearning();
    return true;
  } catch (error) {
    state.privateReviewLearningReceipt = null;
    state.privateReviewLearningImportText = importedText;
    state.privateReviewLearningVerification = { status: "invalid", message: error?.message || "Private review inspection learning receipt validation failed." };
    renderReceiptLearning();
    return false;
  }
}

async function createPrivateBlueprintDelta(selectedReviewDigest) {
  if (!dataAdapter?.createPortablePrivateBlueprintDelta || !dataAdapter?.verifyPortablePrivateBlueprintDelta) return false;
  resetPrivateBlueprintDeltaReviewState({ keepReviewerLabel: true });
  const learningSerialized = state.privateReviewLearningVerification?.status === "verified"
    ? state.privateReviewLearningImportText
    : "";
  try {
    const receipt = await dataAdapter.createPortablePrivateBlueprintDelta(learningSerialized, selectedReviewDigest);
    const result = await dataAdapter.verifyPortablePrivateBlueprintDelta(receipt.serialized);
    state.privateBlueprintDeltaReceipt = receipt;
    state.privateBlueprintDeltaImportText = receipt.serialized;
    state.privateBlueprintDeltaVerification = { status: "verified", result };
    renderReceiptLearning();
    return true;
  } catch (error) {
    state.privateBlueprintDeltaReceipt = null;
    state.privateBlueprintDeltaImportText = "";
    state.privateBlueprintDeltaVerification = { status: "invalid", message: error?.message || "Private guard proposal failed." };
    renderReceiptLearning();
    return false;
  }
}

async function verifyPrivateBlueprintDelta(serializedInput) {
  const importedText = String(serializedInput || "").slice(0, dataAdapter?.PRIVATE_BLUEPRINT_DELTA_MAX_LENGTH || 2621440);
  resetPrivateBlueprintDeltaReviewState({ keepReviewerLabel: true });
  try {
    const result = await dataAdapter.verifyPortablePrivateBlueprintDelta(serializedInput);
    const learningVerification = result.learningVerification;
    state.privateBlueprintDeltaReceipt = null;
    state.privateBlueprintDeltaImportText = importedText;
    state.privateBlueprintDeltaVerification = { status: "verified", result };
    state.privateReviewLearningReceipt = null;
    state.privateReviewLearningImportText = result.learningSerialized;
    state.privateReviewLearningVerification = { status: "verified", result: learningVerification };
    state.portableReviewComparisonReceipt = null;
    state.portableReviewComparisonImportText = learningVerification.comparisonSerialized;
    state.portableReviewComparisonVerification = { status: "verified", result: learningVerification.comparisonVerification };
    state.portableReviewComparisonLeftText = learningVerification.comparisonVerification.leftSerialized;
    state.portableReviewComparisonRightText = learningVerification.comparisonVerification.rightSerialized;
    renderReceiptLearning();
    return true;
  } catch (error) {
    state.privateBlueprintDeltaReceipt = null;
    state.privateBlueprintDeltaImportText = importedText;
    state.privateBlueprintDeltaVerification = { status: "invalid", message: error?.message || "Private guard proposal validation failed." };
    renderReceiptLearning();
    return false;
  }
}

async function createPrivateBlueprintDeltaReview() {
  if (!dataAdapter?.createPortablePrivateBlueprintDeltaReview || !dataAdapter?.verifyPortablePrivateBlueprintDeltaReview) return false;
  const proposalSerialized = state.privateBlueprintDeltaVerification?.status === "verified"
    ? state.privateBlueprintDeltaImportText
    : "";
  resetPrivateBlueprintRevisionDraftState();
  try {
    const receipt = await dataAdapter.createPortablePrivateBlueprintDeltaReview(proposalSerialized, {
      reviewerLabel: state.privateBlueprintDeltaReviewerLabel,
      decision: state.privateBlueprintDeltaReviewDecision,
      reasonCode: state.privateBlueprintDeltaReviewReason,
    });
    const result = await dataAdapter.verifyPortablePrivateBlueprintDeltaReview(receipt.serialized);
    state.privateBlueprintDeltaReviewReceipt = receipt;
    state.privateBlueprintDeltaReviewImportText = receipt.serialized;
    state.privateBlueprintDeltaReviewVerification = { status: "verified", result };
    renderReceiptLearning();
    return true;
  } catch (error) {
    state.privateBlueprintDeltaReviewReceipt = null;
    state.privateBlueprintDeltaReviewImportText = "";
    state.privateBlueprintDeltaReviewVerification = { status: "invalid", message: error?.message || "Private guard review failed." };
    renderReceiptLearning();
    return false;
  }
}

async function verifyPrivateBlueprintDeltaReview(serializedInput) {
  const importedText = String(serializedInput || "").slice(0, dataAdapter?.PRIVATE_BLUEPRINT_DELTA_REVIEW_MAX_LENGTH || 3145728);
  resetPrivateBlueprintRevisionDraftState();
  try {
    const result = await dataAdapter.verifyPortablePrivateBlueprintDeltaReview(serializedInput);
    const deltaVerification = result.blueprintDeltaVerification;
    const learningVerification = deltaVerification.learningVerification;
    state.privateBlueprintDeltaReviewReceipt = null;
    state.privateBlueprintDeltaReviewImportText = importedText;
    state.privateBlueprintDeltaReviewVerification = { status: "verified", result };
    state.privateBlueprintDeltaReviewerLabel = result.review.reviewer.label;
    state.privateBlueprintDeltaReviewDecision = result.review.decision;
    state.privateBlueprintDeltaReviewReason = result.review.reasonCode;
    state.privateBlueprintDeltaReceipt = null;
    state.privateBlueprintDeltaImportText = result.blueprintDeltaSerialized;
    state.privateBlueprintDeltaVerification = { status: "verified", result: deltaVerification };
    state.privateReviewLearningReceipt = null;
    state.privateReviewLearningImportText = deltaVerification.learningSerialized;
    state.privateReviewLearningVerification = { status: "verified", result: learningVerification };
    state.portableReviewComparisonReceipt = null;
    state.portableReviewComparisonImportText = learningVerification.comparisonSerialized;
    state.portableReviewComparisonVerification = { status: "verified", result: learningVerification.comparisonVerification };
    state.portableReviewComparisonLeftText = learningVerification.comparisonVerification.leftSerialized;
    state.portableReviewComparisonRightText = learningVerification.comparisonVerification.rightSerialized;
    renderReceiptLearning();
    return true;
  } catch (error) {
    state.privateBlueprintDeltaReviewReceipt = null;
    state.privateBlueprintDeltaReviewImportText = importedText;
    state.privateBlueprintDeltaReviewVerification = { status: "invalid", message: error?.message || "Private guard review validation failed." };
    renderReceiptLearning();
    return false;
  }
}

async function createPrivateBlueprintRevisionDraft() {
  if (!dataAdapter?.createPortablePrivateBlueprintRevisionDraft || !dataAdapter?.verifyPortablePrivateBlueprintRevisionDraft) return false;
  const reviewSerialized = state.privateBlueprintDeltaReviewVerification?.status === "verified"
    ? state.privateBlueprintDeltaReviewImportText
    : "";
  try {
    const receipt = await dataAdapter.createPortablePrivateBlueprintRevisionDraft(reviewSerialized);
    const result = await dataAdapter.verifyPortablePrivateBlueprintRevisionDraft(receipt.serialized);
    state.privateBlueprintRevisionDraftReceipt = receipt;
    state.privateBlueprintRevisionDraftImportText = receipt.serialized;
    state.privateBlueprintRevisionDraftVerification = { status: "verified", result };
    renderReceiptLearning();
    return true;
  } catch (error) {
    state.privateBlueprintRevisionDraftReceipt = null;
    state.privateBlueprintRevisionDraftImportText = "";
    state.privateBlueprintRevisionDraftVerification = { status: "invalid", message: error?.message || "Private blueprint revision draft failed." };
    renderReceiptLearning();
    return false;
  }
}

async function verifyPrivateBlueprintRevisionDraft(serializedInput) {
  const importedText = String(serializedInput || "").slice(0, dataAdapter?.PRIVATE_BLUEPRINT_REVISION_DRAFT_MAX_LENGTH || 4194304);
  try {
    const result = await dataAdapter.verifyPortablePrivateBlueprintRevisionDraft(serializedInput);
    const reviewVerification = result.acceptedReviewVerification;
    const deltaVerification = reviewVerification.blueprintDeltaVerification;
    const learningVerification = deltaVerification.learningVerification;
    state.privateBlueprintRevisionDraftReceipt = null;
    state.privateBlueprintRevisionDraftImportText = importedText;
    state.privateBlueprintRevisionDraftVerification = { status: "verified", result };
    state.privateBlueprintDeltaReviewReceipt = null;
    state.privateBlueprintDeltaReviewImportText = result.acceptedReviewSerialized;
    state.privateBlueprintDeltaReviewVerification = { status: "verified", result: reviewVerification };
    state.privateBlueprintDeltaReviewerLabel = reviewVerification.review.reviewer.label;
    state.privateBlueprintDeltaReviewDecision = reviewVerification.review.decision;
    state.privateBlueprintDeltaReviewReason = reviewVerification.review.reasonCode;
    state.privateBlueprintDeltaReceipt = null;
    state.privateBlueprintDeltaImportText = reviewVerification.blueprintDeltaSerialized;
    state.privateBlueprintDeltaVerification = { status: "verified", result: deltaVerification };
    state.privateReviewLearningReceipt = null;
    state.privateReviewLearningImportText = deltaVerification.learningSerialized;
    state.privateReviewLearningVerification = { status: "verified", result: learningVerification };
    state.portableReviewComparisonReceipt = null;
    state.portableReviewComparisonImportText = learningVerification.comparisonSerialized;
    state.portableReviewComparisonVerification = { status: "verified", result: learningVerification.comparisonVerification };
    state.portableReviewComparisonLeftText = learningVerification.comparisonVerification.leftSerialized;
    state.portableReviewComparisonRightText = learningVerification.comparisonVerification.rightSerialized;
    renderReceiptLearning();
    return true;
  } catch (error) {
    state.privateBlueprintRevisionDraftReceipt = null;
    state.privateBlueprintRevisionDraftImportText = importedText;
    state.privateBlueprintRevisionDraftVerification = { status: "invalid", message: error?.message || "Private blueprint revision draft validation failed." };
    renderReceiptLearning();
    return false;
  }
}

async function createPrivateBlueprintDraftReview() {
  if (!dataAdapter?.createPortablePrivateBlueprintDraftReview || !dataAdapter?.verifyPortablePrivateBlueprintDraftReview) return false;
  resetPrivateBlueprintGuardCompletionState({ keepReviewerLabel: true });
  const draftSerialized = state.privateBlueprintRevisionDraftVerification?.status === "verified"
    ? state.privateBlueprintRevisionDraftImportText
    : "";
  try {
    const receipt = await dataAdapter.createPortablePrivateBlueprintDraftReview(draftSerialized, {
      reviewerLabel: state.privateBlueprintDraftReviewerLabel,
      decision: state.privateBlueprintDraftReviewDecision,
      reasonCode: state.privateBlueprintDraftReviewReason,
    });
    const result = await dataAdapter.verifyPortablePrivateBlueprintDraftReview(receipt.serialized);
    state.privateBlueprintDraftReviewReceipt = receipt;
    state.privateBlueprintDraftReviewImportText = receipt.serialized;
    state.privateBlueprintDraftReviewVerification = { status: "verified", result };
    renderReceiptLearning();
    return true;
  } catch (error) {
    state.privateBlueprintDraftReviewReceipt = null;
    state.privateBlueprintDraftReviewImportText = "";
    state.privateBlueprintDraftReviewVerification = { status: "invalid", message: error?.message || "Private blueprint draft review failed." };
    renderReceiptLearning();
    return false;
  }
}

async function verifyPrivateBlueprintDraftReview(serializedInput) {
  const importedText = String(serializedInput || "").slice(0, dataAdapter?.PRIVATE_BLUEPRINT_DRAFT_REVIEW_MAX_LENGTH || 5242880);
  resetPrivateBlueprintGuardCompletionState({ keepReviewerLabel: true });
  try {
    const result = await dataAdapter.verifyPortablePrivateBlueprintDraftReview(serializedInput);
    const draftVerification = result.draftVerification;
    const reviewVerification = draftVerification.acceptedReviewVerification;
    const deltaVerification = reviewVerification.blueprintDeltaVerification;
    const learningVerification = deltaVerification.learningVerification;
    state.privateBlueprintDraftReviewReceipt = null;
    state.privateBlueprintDraftReviewImportText = importedText;
    state.privateBlueprintDraftReviewVerification = { status: "verified", result };
    state.privateBlueprintDraftReviewerLabel = result.review.reviewer.label;
    state.privateBlueprintDraftReviewDecision = result.review.decision;
    state.privateBlueprintDraftReviewReason = result.review.reasonCode;
    state.privateBlueprintRevisionDraftReceipt = null;
    state.privateBlueprintRevisionDraftImportText = result.draftSerialized;
    state.privateBlueprintRevisionDraftVerification = { status: "verified", result: draftVerification };
    state.privateBlueprintDeltaReviewReceipt = null;
    state.privateBlueprintDeltaReviewImportText = draftVerification.acceptedReviewSerialized;
    state.privateBlueprintDeltaReviewVerification = { status: "verified", result: reviewVerification };
    state.privateBlueprintDeltaReviewerLabel = reviewVerification.review.reviewer.label;
    state.privateBlueprintDeltaReviewDecision = reviewVerification.review.decision;
    state.privateBlueprintDeltaReviewReason = reviewVerification.review.reasonCode;
    state.privateBlueprintDeltaReceipt = null;
    state.privateBlueprintDeltaImportText = reviewVerification.blueprintDeltaSerialized;
    state.privateBlueprintDeltaVerification = { status: "verified", result: deltaVerification };
    state.privateReviewLearningReceipt = null;
    state.privateReviewLearningImportText = deltaVerification.learningSerialized;
    state.privateReviewLearningVerification = { status: "verified", result: learningVerification };
    state.portableReviewComparisonReceipt = null;
    state.portableReviewComparisonImportText = learningVerification.comparisonSerialized;
    state.portableReviewComparisonVerification = { status: "verified", result: learningVerification.comparisonVerification };
    state.portableReviewComparisonLeftText = learningVerification.comparisonVerification.leftSerialized;
    state.portableReviewComparisonRightText = learningVerification.comparisonVerification.rightSerialized;
    renderReceiptLearning();
    return true;
  } catch (error) {
    state.privateBlueprintDraftReviewReceipt = null;
    state.privateBlueprintDraftReviewImportText = importedText;
    state.privateBlueprintDraftReviewVerification = { status: "invalid", message: error?.message || "Private blueprint draft review validation failed." };
    renderReceiptLearning();
    return false;
  }
}

function applyPrivateBlueprintGuardCompletionVerification(result, importedText, { receipt = null } = {}) {
  const draftReviewVerification = result.draftReviewVerification;
  const draftVerification = draftReviewVerification.draftVerification;
  const reviewVerification = draftVerification.acceptedReviewVerification;
  const deltaVerification = reviewVerification.blueprintDeltaVerification;
  const learningVerification = deltaVerification.learningVerification;
  state.privateBlueprintGuardCompletionReceipt = receipt;
  state.privateBlueprintGuardCompletionImportText = importedText;
  state.privateBlueprintGuardCompletionVerification = { status: "verified", result };
  state.privateBlueprintGuardCompletionReviewerLabel = result.completionProposal.reviewer.label;
  state.privateBlueprintGuardCompletionReason = result.completionProposal.reasonCode;
  state.privateBlueprintGuardCompletionValues = {};
  state.privateBlueprintGuardCompletionProvenance = {};
  for (const completion of result.completionProposal.guardCompletions) {
    state.privateBlueprintGuardCompletionValues[completion.guardKey] = completion.value;
    state.privateBlueprintGuardCompletionProvenance[completion.guardKey] = completion.provenance.code;
  }
  state.privateBlueprintDraftReviewReceipt = null;
  state.privateBlueprintDraftReviewImportText = result.draftReviewSerialized;
  state.privateBlueprintDraftReviewVerification = { status: "verified", result: draftReviewVerification };
  state.privateBlueprintDraftReviewerLabel = draftReviewVerification.review.reviewer.label;
  state.privateBlueprintDraftReviewDecision = draftReviewVerification.review.decision;
  state.privateBlueprintDraftReviewReason = draftReviewVerification.review.reasonCode;
  state.privateBlueprintRevisionDraftReceipt = null;
  state.privateBlueprintRevisionDraftImportText = draftReviewVerification.draftSerialized;
  state.privateBlueprintRevisionDraftVerification = { status: "verified", result: draftVerification };
  state.privateBlueprintDeltaReviewReceipt = null;
  state.privateBlueprintDeltaReviewImportText = draftVerification.acceptedReviewSerialized;
  state.privateBlueprintDeltaReviewVerification = { status: "verified", result: reviewVerification };
  state.privateBlueprintDeltaReviewerLabel = reviewVerification.review.reviewer.label;
  state.privateBlueprintDeltaReviewDecision = reviewVerification.review.decision;
  state.privateBlueprintDeltaReviewReason = reviewVerification.review.reasonCode;
  state.privateBlueprintDeltaReceipt = null;
  state.privateBlueprintDeltaImportText = reviewVerification.blueprintDeltaSerialized;
  state.privateBlueprintDeltaVerification = { status: "verified", result: deltaVerification };
  state.privateReviewLearningReceipt = null;
  state.privateReviewLearningImportText = deltaVerification.learningSerialized;
  state.privateReviewLearningVerification = { status: "verified", result: learningVerification };
  state.portableReviewComparisonReceipt = null;
  state.portableReviewComparisonImportText = learningVerification.comparisonSerialized;
  state.portableReviewComparisonVerification = { status: "verified", result: learningVerification.comparisonVerification };
  state.portableReviewComparisonLeftText = learningVerification.comparisonVerification.leftSerialized;
  state.portableReviewComparisonRightText = learningVerification.comparisonVerification.rightSerialized;
}

async function createPrivateBlueprintGuardCompletion() {
  if (!dataAdapter?.createPortablePrivateBlueprintGuardCompletion || !dataAdapter?.verifyPortablePrivateBlueprintGuardCompletion) return false;
  resetPrivateBlueprintGuardCompletionReviewState({ keepReviewerLabel: true });
  const candidate = privateBlueprintGuardCompletionCandidate();
  const draftReviewSerialized = state.privateBlueprintDraftReviewVerification?.status === "verified"
    ? state.privateBlueprintDraftReviewImportText
    : "";
  if (!candidate) return false;
  ensurePrivateBlueprintGuardCompletionSelections();
  const guardCompletions = candidate.unknownGuardKeys.map((guardKey) => ({
    guardKey,
    value: state.privateBlueprintGuardCompletionValues[guardKey],
    provenanceCode: state.privateBlueprintGuardCompletionProvenance[guardKey],
  }));
  try {
    const receipt = await dataAdapter.createPortablePrivateBlueprintGuardCompletion(draftReviewSerialized, {
      reviewerLabel: state.privateBlueprintGuardCompletionReviewerLabel,
      reasonCode: state.privateBlueprintGuardCompletionReason,
      guardCompletions,
    });
    const result = await dataAdapter.verifyPortablePrivateBlueprintGuardCompletion(receipt.serialized);
    applyPrivateBlueprintGuardCompletionVerification(result, receipt.serialized, { receipt });
    renderReceiptLearning();
    return true;
  } catch (error) {
    state.privateBlueprintGuardCompletionReceipt = null;
    state.privateBlueprintGuardCompletionImportText = "";
    state.privateBlueprintGuardCompletionVerification = { status: "invalid", message: error?.message || "Private blueprint guard completion failed." };
    renderReceiptLearning();
    return false;
  }
}

async function verifyPrivateBlueprintGuardCompletion(serializedInput) {
  const importedText = String(serializedInput || "").slice(0, dataAdapter?.PRIVATE_BLUEPRINT_GUARD_COMPLETION_MAX_LENGTH || 6291456);
  resetPrivateBlueprintGuardCompletionReviewState({ keepReviewerLabel: true });
  try {
    const result = await dataAdapter.verifyPortablePrivateBlueprintGuardCompletion(serializedInput);
    applyPrivateBlueprintGuardCompletionVerification(result, importedText);
    renderReceiptLearning();
    return true;
  } catch (error) {
    state.privateBlueprintGuardCompletionReceipt = null;
    state.privateBlueprintGuardCompletionImportText = importedText;
    state.privateBlueprintGuardCompletionVerification = { status: "invalid", message: error?.message || "Private blueprint guard completion validation failed." };
    renderReceiptLearning();
    return false;
  }
}

async function createPrivateBlueprintGuardCompletionReview() {
  if (!dataAdapter?.createPortablePrivateBlueprintGuardCompletionReview || !dataAdapter?.verifyPortablePrivateBlueprintGuardCompletionReview) return false;
  resetPrivateBlueprintOperatorReviewPacketState();
  const completionSerialized = state.privateBlueprintGuardCompletionVerification?.status === "verified"
    ? state.privateBlueprintGuardCompletionImportText
    : "";
  try {
    const receipt = await dataAdapter.createPortablePrivateBlueprintGuardCompletionReview(completionSerialized, {
      reviewerLabel: state.privateBlueprintGuardCompletionReviewReviewerLabel,
      decision: state.privateBlueprintGuardCompletionReviewDecision,
      reasonCode: state.privateBlueprintGuardCompletionReviewReason,
    });
    const result = await dataAdapter.verifyPortablePrivateBlueprintGuardCompletionReview(receipt.serialized);
    state.privateBlueprintGuardCompletionReviewReceipt = receipt;
    state.privateBlueprintGuardCompletionReviewImportText = receipt.serialized;
    state.privateBlueprintGuardCompletionReviewVerification = { status: "verified", result };
    renderReceiptLearning();
    return true;
  } catch (error) {
    state.privateBlueprintGuardCompletionReviewReceipt = null;
    state.privateBlueprintGuardCompletionReviewImportText = "";
    state.privateBlueprintGuardCompletionReviewVerification = { status: "invalid", message: error?.message || "Private guard-completion review failed." };
    renderReceiptLearning();
    return false;
  }
}

async function verifyPrivateBlueprintGuardCompletionReview(serializedInput) {
  const importedText = String(serializedInput || "").slice(0, dataAdapter?.PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_MAX_LENGTH || 7340032);
  resetPrivateBlueprintOperatorReviewPacketState();
  try {
    const result = await dataAdapter.verifyPortablePrivateBlueprintGuardCompletionReview(serializedInput);
    applyPrivateBlueprintGuardCompletionVerification(result.guardCompletionVerification, result.guardCompletionSerialized);
    state.privateBlueprintGuardCompletionReviewReceipt = null;
    state.privateBlueprintGuardCompletionReviewImportText = importedText;
    state.privateBlueprintGuardCompletionReviewVerification = { status: "verified", result };
    state.privateBlueprintGuardCompletionReviewReviewerLabel = result.review.reviewer.label;
    state.privateBlueprintGuardCompletionReviewDecision = result.review.decision;
    state.privateBlueprintGuardCompletionReviewReason = result.review.reasonCode;
    renderReceiptLearning();
    return true;
  } catch (error) {
    state.privateBlueprintGuardCompletionReviewReceipt = null;
    state.privateBlueprintGuardCompletionReviewImportText = importedText;
    state.privateBlueprintGuardCompletionReviewVerification = { status: "invalid", message: error?.message || "Private guard-completion review validation failed." };
    renderReceiptLearning();
    return false;
  }
}

async function createPrivateBlueprintOperatorReviewPacket() {
  if (!dataAdapter?.createPortablePrivateBlueprintOperatorReviewPacket || !dataAdapter?.verifyPortablePrivateBlueprintOperatorReviewPacket) return false;
  const reviewSerialized = state.privateBlueprintGuardCompletionReviewVerification?.status === "verified"
    ? state.privateBlueprintGuardCompletionReviewImportText
    : "";
  try {
    const receipt = await dataAdapter.createPortablePrivateBlueprintOperatorReviewPacket(reviewSerialized);
    const result = await dataAdapter.verifyPortablePrivateBlueprintOperatorReviewPacket(receipt.serialized);
    state.privateBlueprintOperatorReviewPacketReceipt = receipt;
    state.privateBlueprintOperatorReviewPacketImportText = receipt.serialized;
    state.privateBlueprintOperatorReviewPacketVerification = { status: "verified", result };
    renderReceiptLearning();
    return true;
  } catch (error) {
    state.privateBlueprintOperatorReviewPacketReceipt = null;
    state.privateBlueprintOperatorReviewPacketImportText = "";
    state.privateBlueprintOperatorReviewPacketVerification = { status: "invalid", message: error?.message || "Private blueprint operator packet failed." };
    renderReceiptLearning();
    return false;
  }
}

async function verifyPrivateBlueprintOperatorReviewPacket(serializedInput) {
  const importedText = String(serializedInput || "").slice(0, dataAdapter?.PRIVATE_BLUEPRINT_OPERATOR_REVIEW_PACKET_MAX_LENGTH || 8388608);
  try {
    const result = await dataAdapter.verifyPortablePrivateBlueprintOperatorReviewPacket(serializedInput);
    const reviewVerification = result.acceptedReviewVerification;
    applyPrivateBlueprintGuardCompletionVerification(reviewVerification.guardCompletionVerification, reviewVerification.guardCompletionSerialized);
    state.privateBlueprintGuardCompletionReviewReceipt = null;
    state.privateBlueprintGuardCompletionReviewImportText = result.acceptedReviewSerialized;
    state.privateBlueprintGuardCompletionReviewVerification = { status: "verified", result: reviewVerification };
    state.privateBlueprintGuardCompletionReviewReviewerLabel = reviewVerification.review.reviewer.label;
    state.privateBlueprintGuardCompletionReviewDecision = reviewVerification.review.decision;
    state.privateBlueprintGuardCompletionReviewReason = reviewVerification.review.reasonCode;
    state.privateBlueprintOperatorReviewPacketReceipt = null;
    state.privateBlueprintOperatorReviewPacketImportText = importedText;
    state.privateBlueprintOperatorReviewPacketVerification = { status: "verified", result };
    renderReceiptLearning();
    return true;
  } catch (error) {
    state.privateBlueprintOperatorReviewPacketReceipt = null;
    state.privateBlueprintOperatorReviewPacketImportText = importedText;
    state.privateBlueprintOperatorReviewPacketVerification = { status: "invalid", message: error?.message || "Private blueprint operator packet validation failed." };
    renderReceiptLearning();
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
  if (!$("#session-sheet")?.hidden) disarmBlueprintRemoval({ render: false });
  const route = parseArenaRoute(location.hash);
  if (!$("#proof-sheet").hidden && route?.receiptId) {
    if (history.state?.overlay === "receipt") {
      closeSheets();
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
  document.addEventListener("click", async (event) => {
    if (event.target.closest("[data-starter-show]")) {
      showStarterGuide();
      return;
    }
    if (event.target.closest("[data-starter-dismiss]")) {
      const persisted = completeStarterGuide();
      showToast(persisted
        ? "Starter guide hidden in this browser. No account or remote preference was created."
        : "Starter guide hidden for this page. Browser storage is unavailable; nothing was uploaded.");
      return;
    }
    if (event.target.closest("[data-session-restart-starter]")) {
      restartStarterGuideFromSession();
      return;
    }
    if (event.target.closest("[data-session-remove-blueprint]")) {
      armOrRemoveLocalBlueprint();
      return;
    }
    const starterAction = event.target.closest("[data-starter-action]");
    if (starterAction) {
      completeStarterGuide();
      if (starterAction.dataset.starterAction === "proof") {
        if (!openReceiptProof("featured")) showToast("Reviewed proof is unavailable in this bounded source.");
      } else if (starterAction.dataset.starterAction === "compete") {
        showView("compete");
        $("#quick-matches .queue-button")?.focus?.({ preventScroll: true });
      } else if (starterAction.dataset.starterAction === "build") {
        showView("build");
        $("#agent-name")?.focus?.({ preventScroll: true });
      }
      return;
    }
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
    if (event.target.closest("[data-portable-prepare]")) {
      const prepared = await preparePortableRunback();
      if (prepared) {
        $("#portable-runback-export")?.focus({ preventScroll: true });
        showToast("Canonical local JSON prepared. Its checksum is not an identity or provider signature.");
      } else {
        showToast("Portable preparation failed closed. Nothing was uploaded, executed, or published.");
      }
      return;
    }
    if (event.target.closest("[data-portable-verify]")) {
      const input = $("#portable-runback-import");
      const verified = await verifyPortableRunback(input?.value || "");
      $(verified ? ".portable-status.verified" : ".portable-status.invalid")?.focus?.({ preventScroll: true });
      showToast(verified
        ? "Checksum and still-unplayed contract verified locally. No authority was granted."
        : "Import refused. No proposal was adopted, executed, or published.");
      return;
    }
    if (event.target.closest("[data-portable-review-submit]")) {
      const appended = await appendPortableReview();
      $(appended ? `[data-portable-review-record="${state.portableReviews.length}"]` : ".portable-review-status.invalid")?.focus?.({ preventScroll: true });
      showToast(appended
        ? "Private review appended. Any blueprint revision remains proposed, uncommitted, and unplayed."
        : "Private review refused. No proposal, blueprint, or authority changed.");
      return;
    }
    if (event.target.closest("[data-portable-review-correction-submit]")) {
      const appended = await appendPortableReviewCorrection();
      $(appended ? `[data-portable-review-correction-record="${state.portableReviewCorrections.length}"]` : ".portable-review-correction .portable-review-status.invalid")?.focus?.({ preventScroll: true });
      showToast(appended
        ? "Private correction appended. The original review remains immutable and no authority was granted."
        : "Private correction refused. No review, blueprint, or authority changed.");
      return;
    }
    if (event.target.closest("[data-portable-review-exchange-prepare]")) {
      const prepared = await preparePortableReviewExchange();
      $(prepared ? "#portable-review-exchange-export" : ".portable-review-exchange-status.invalid")?.focus?.({ preventScroll: true });
      showToast(prepared
        ? "Canonical private review packet prepared. It grants no identity or execution authority."
        : "Review packet preparation failed closed. Nothing was uploaded, applied, or published.");
      return;
    }
    if (event.target.closest("[data-portable-review-exchange-verify]")) {
      const input = $("#portable-review-exchange-import");
      const verified = await verifyPortableReviewExchange(input?.value || "");
      $(verified ? ".portable-review-exchange-status.verified" : ".portable-review-exchange-status.invalid")?.focus?.({ preventScroll: true });
      showToast(verified
        ? "Proposal, review chain, and packet digest verified locally. No blueprint was applied."
        : "Review packet refused. No proposal, review, blueprint, or authority was retained.");
      return;
    }
    if (event.target.closest("[data-portable-review-correction-exchange-prepare]")) {
      const prepared = await preparePortableReviewCorrectionExchange();
      $(prepared ? "#portable-review-correction-exchange-export" : ".portable-review-correction-exchange-status.invalid")?.focus?.({ preventScroll: true });
      showToast(prepared
        ? "Canonical correction packet prepared. Immutable reviews remain preserved and no authority was granted."
        : "Correction packet preparation failed closed. Nothing was uploaded, rewritten, applied, or published.");
      return;
    }
    if (event.target.closest("[data-portable-review-correction-exchange-verify]")) {
      const input = $("#portable-review-correction-exchange-import");
      const verified = await verifyPortableReviewCorrectionExchange(input?.value || "");
      $(verified ? ".portable-review-correction-exchange-status.verified" : ".portable-review-correction-exchange-status.invalid")?.focus?.({ preventScroll: true });
      showToast(verified
        ? "Proposal, immutable reviews, correction history, and packet digest verified locally. Nothing was rewritten."
        : "Correction packet refused. No proposal, review, correction, blueprint, or authority was retained.");
      return;
    }
    if (event.target.closest("[data-portable-review-comparison-create]")) {
      const created = await createPortableReviewComparison();
      $(created ? ".portable-review-comparison-status.verified" : ".portable-review-comparison-status.invalid")?.focus?.({ preventScroll: true });
      showToast(created
        ? "Both correction packets were reverified and compared. No winner, merge, or resolution authority was created."
        : "Comparison refused. No verified comparison, merge, resolution, or authority state was retained.");
      return;
    }
    if (event.target.closest("[data-portable-review-comparison-verify]")) {
      const input = $("#portable-review-comparison-import");
      const verified = await verifyPortableReviewComparison(input?.value || "");
      $(verified ? ".portable-review-comparison-status.verified" : ".portable-review-comparison-status.invalid")?.focus?.({ preventScroll: true });
      showToast(verified
        ? "Comparison receipt and both source histories verified locally. Nothing was merged or resolved."
        : "Comparison receipt refused. No verified comparison or authority state was retained.");
      return;
    }
    if (event.target.closest("[data-private-review-learning-create]")) {
      const created = await createPrivateReviewLearning();
      $(created ? ".private-review-learning-status.verified" : ".private-review-learning-status.invalid")?.focus?.({ preventScroll: true });
      showToast(created
        ? "Comparison and source histories reverified. Inspection lessons created without correctness, progress, or authority."
        : "Inspection learning refused. No verified lesson, progress, consensus, or authority state was retained.");
      return;
    }
    if (event.target.closest("[data-private-review-learning-verify]")) {
      const input = $("#private-review-learning-import");
      const verified = await verifyPrivateReviewLearning(input?.value || "");
      $(verified ? ".private-review-learning-status.verified" : ".private-review-learning-status.invalid")?.focus?.({ preventScroll: true });
      showToast(verified
        ? "Inspection receipt, comparison, and both source histories verified locally. No packet was declared correct."
        : "Inspection receipt refused. No verified lesson or authority state was retained.");
      return;
    }
    const privateDeltaTrigger = event.target.closest("[data-private-blueprint-delta-create]");
    if (privateDeltaTrigger) {
      const created = await createPrivateBlueprintDelta(privateDeltaTrigger.dataset.privateBlueprintDeltaCreate || "");
      $(created ? ".private-blueprint-delta-status.verified" : ".private-blueprint-delta-status.invalid")?.focus?.({ preventScroll: true });
      showToast(created
        ? "Exact lesson and parent proposal reverified. One guard requirement was proposed without commitment, play, progress, or authority."
        : "Guard proposal refused. No blueprint change, commitment, play, progress, or authority state was retained.");
      return;
    }
    if (event.target.closest("[data-private-blueprint-delta-verify]")) {
      const input = $("#private-blueprint-delta-import");
      const verified = await verifyPrivateBlueprintDelta(input?.value || "");
      $(verified ? ".private-blueprint-delta-status.verified" : ".private-blueprint-delta-status.invalid")?.focus?.({ preventScroll: true });
      showToast(verified
        ? "Guard proposal and full inspection ancestry verified locally. Nothing was committed, played, qualified, or adopted."
        : "Guard proposal refused. No verified proposal or authority state was retained.");
      return;
    }
    if (event.target.closest("[data-private-blueprint-delta-review-create]")) {
      const created = await createPrivateBlueprintDeltaReview();
      $(created ? ".private-blueprint-delta-review-status.verified" : ".private-blueprint-delta-review-status.invalid")?.focus?.({ preventScroll: true });
      showToast(created
        ? "Immutable private guard review recorded. Any revision candidate remains local, uncommitted, unadopted, and unplayed."
        : "Guard review refused. No review, revision candidate, adoption, progress, or authority state was retained.");
      return;
    }
    if (event.target.closest("[data-private-blueprint-delta-review-verify]")) {
      const input = $("#private-blueprint-delta-review-import");
      const verified = await verifyPrivateBlueprintDeltaReview(input?.value || "");
      $(verified ? ".private-blueprint-delta-review-status.verified" : ".private-blueprint-delta-review-status.invalid")?.focus?.({ preventScroll: true });
      showToast(verified
        ? "Guard review, proposal, and full ancestry verified locally. No guard was adopted, committed, played, or executed."
        : "Guard review refused. No verified review or authority state was retained.");
      return;
    }
    if (event.target.closest("[data-private-blueprint-revision-draft-create]")) {
      const created = await createPrivateBlueprintRevisionDraft();
      $(created ? ".private-blueprint-revision-draft-status.verified" : ".private-blueprint-revision-draft-status.invalid")?.focus?.({ preventScroll: true });
      showToast(created
        ? "Accepted review and full ancestry reverified. One local blueprint draft was derived without commitment, adoption, qualification, play, or authority."
        : "Blueprint revision draft refused. No draft, adoption, progress, execution, or authority state was retained.");
      return;
    }
    if (event.target.closest("[data-private-blueprint-revision-draft-verify]")) {
      const input = $("#private-blueprint-revision-draft-import");
      const verified = await verifyPrivateBlueprintRevisionDraft(input?.value || "");
      $(verified ? ".private-blueprint-revision-draft-status.verified" : ".private-blueprint-revision-draft-status.invalid")?.focus?.({ preventScroll: true });
      showToast(verified
        ? "Blueprint draft, accepted review, guard proposal, and full ancestry verified locally. Nothing was committed, adopted, qualified, played, or executed."
        : "Blueprint revision draft refused. No verified draft or authority state was retained.");
      return;
    }
    if (event.target.closest("[data-private-blueprint-draft-review-create]")) {
      const created = await createPrivateBlueprintDraftReview();
      $(created ? ".private-blueprint-draft-review-status.verified" : ".private-blueprint-draft-review-status.invalid")?.focus?.({ preventScroll: true });
      showToast(created
        ? "Immutable blueprint draft review recorded. Any commit candidate remains local, uncommitted, unadopted, and not commit-ready."
        : "Blueprint draft review refused. No review, commit candidate, readiness, adoption, progress, or authority state was retained.");
      return;
    }
    if (event.target.closest("[data-private-blueprint-draft-review-verify]")) {
      const input = $("#private-blueprint-draft-review-import");
      const verified = await verifyPrivateBlueprintDraftReview(input?.value || "");
      $(verified ? ".private-blueprint-draft-review-status.verified" : ".private-blueprint-draft-review-status.invalid")?.focus?.({ preventScroll: true });
      showToast(verified
        ? "Blueprint draft review and full ancestry verified locally. No blueprint was committed, adopted, qualified, played, executed, or published."
        : "Blueprint draft review refused. No verified review, commit candidate, or authority state was retained.");
      return;
    }
    if (event.target.closest("[data-private-blueprint-guard-completion-create]")) {
      const created = await createPrivateBlueprintGuardCompletion();
      $(created ? ".private-blueprint-guard-completion-status.verified" : ".private-blueprint-guard-completion-status.invalid")?.focus?.({ preventScroll: true });
      showToast(created
        ? "Every explicit unknown guard received a boolean and local provenance. The proposal still requires review and is not commit-ready."
        : "Guard completion refused. No completed proposal, readiness, commitment, adoption, progress, or authority state was retained.");
      return;
    }
    if (event.target.closest("[data-private-blueprint-guard-completion-verify]")) {
      const input = $("#private-blueprint-guard-completion-import");
      const verified = await verifyPrivateBlueprintGuardCompletion(input?.value || "");
      $(verified ? ".private-blueprint-guard-completion-status.verified" : ".private-blueprint-guard-completion-status.invalid")?.focus?.({ preventScroll: true });
      showToast(verified
        ? "Guard completion and full ancestry verified locally. It remains uncommitted, unadopted, and not commit-ready."
        : "Guard completion refused. No verified proposal, readiness, or authority state was retained.");
      return;
    }
    if (event.target.closest("[data-private-blueprint-guard-completion-review-create]")) {
      const created = await createPrivateBlueprintGuardCompletionReview();
      $(created ? ".private-blueprint-guard-completion-review-status.verified" : ".private-blueprint-guard-completion-review-status.invalid")?.focus?.({ preventScroll: true });
      showToast(created
        ? "Immutable completion review recorded. Accept only prepares a local candidate for later operator review; nothing is commit-ready."
        : "Completion review refused. The verified upstream completion remains available and no review or authority state was retained.");
      return;
    }
    if (event.target.closest("[data-private-blueprint-guard-completion-review-verify]")) {
      const input = $("#private-blueprint-guard-completion-review-import");
      const verified = await verifyPrivateBlueprintGuardCompletionReview(input?.value || "");
      $(verified ? ".private-blueprint-guard-completion-review-status.verified" : ".private-blueprint-guard-completion-review-status.invalid")?.focus?.({ preventScroll: true });
      showToast(verified
        ? "Completion review and full ancestry verified locally. No blueprint was committed, adopted, qualified, played, executed, or published."
        : "Completion review refused. The verified upstream completion remains available and no review or candidate state was retained.");
      return;
    }
    if (event.target.closest("[data-private-blueprint-operator-review-packet-create]")) {
      const created = await createPrivateBlueprintOperatorReviewPacket();
      $(created ? ".private-blueprint-operator-review-packet-status.verified" : ".private-blueprint-operator-review-packet-status.invalid")?.focus?.({ preventScroll: true });
      showToast(created
        ? "Local operator packet prepared. Exact diff is visible; validation and operator decision remain not run."
        : "Operator packet refused. The verified upstream completion review remains available and no decision or authority state was retained.");
      return;
    }
    if (event.target.closest("[data-private-blueprint-operator-review-packet-verify]")) {
      const input = $("#private-blueprint-operator-review-packet-import");
      const verified = await verifyPrivateBlueprintOperatorReviewPacket(input?.value || "");
      $(verified ? ".private-blueprint-operator-review-packet-status.verified" : ".private-blueprint-operator-review-packet-status.invalid")?.focus?.({ preventScroll: true });
      showToast(verified
        ? "Operator packet and full ancestry verified locally. Validation and operator decision remain not run."
        : "Operator packet refused. The verified upstream completion review remains available and no decision or candidate authority was retained.");
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

  document.addEventListener("input", (event) => {
    if (event.target.matches("#portable-reviewer-label")) {
      state.portableReviewerLabel = event.target.value.slice(0, 36);
      state.portableReviewMessage = null;
    }
    if (event.target.matches("#portable-review-exchange-import")) {
      state.portableReviewExchangeImportText = event.target.value.slice(0, dataAdapter?.PORTABLE_REVIEW_EXCHANGE_MAX_LENGTH || 262144);
      state.portableReviewExchangeVerification = null;
    }
    if (event.target.matches("#portable-correction-reviewer-label")) {
      state.portableCorrectionReviewerLabel = event.target.value.slice(0, 36);
      state.portableReviewCorrectionMessage = null;
    }
    if (event.target.matches("#portable-review-correction-exchange-import")) {
      state.portableReviewCorrectionExchangeImportText = event.target.value.slice(0, dataAdapter?.PORTABLE_REVIEW_CORRECTION_EXCHANGE_MAX_LENGTH || 524288);
      state.portableReviewCorrectionExchangeVerification = null;
    }
    if (event.target.matches("#portable-review-comparison-left")) {
      state.portableReviewComparisonLeftText = event.target.value.slice(0, dataAdapter?.PORTABLE_REVIEW_CORRECTION_EXCHANGE_MAX_LENGTH || 524288);
      state.portableReviewComparisonReceipt = null;
      state.portableReviewComparisonVerification = null;
      resetPrivateReviewLearningState();
    }
    if (event.target.matches("#portable-review-comparison-right")) {
      state.portableReviewComparisonRightText = event.target.value.slice(0, dataAdapter?.PORTABLE_REVIEW_CORRECTION_EXCHANGE_MAX_LENGTH || 524288);
      state.portableReviewComparisonReceipt = null;
      state.portableReviewComparisonVerification = null;
      resetPrivateReviewLearningState();
    }
    if (event.target.matches("#portable-review-comparison-import")) {
      state.portableReviewComparisonImportText = event.target.value.slice(0, dataAdapter?.PORTABLE_REVIEW_COMPARISON_MAX_LENGTH || 1572864);
      state.portableReviewComparisonVerification = null;
      resetPrivateReviewLearningState();
    }
    if (event.target.matches("#private-review-learning-import")) {
      state.privateReviewLearningImportText = event.target.value.slice(0, dataAdapter?.PRIVATE_REVIEW_LEARNING_MAX_LENGTH || 2097152);
      state.privateReviewLearningReceipt = null;
      state.privateReviewLearningVerification = null;
      resetPrivateBlueprintDeltaState();
    }
    if (event.target.matches("#private-blueprint-delta-import")) {
      state.privateBlueprintDeltaImportText = event.target.value.slice(0, dataAdapter?.PRIVATE_BLUEPRINT_DELTA_MAX_LENGTH || 2621440);
      state.privateBlueprintDeltaReceipt = null;
      state.privateBlueprintDeltaVerification = null;
      resetPrivateBlueprintDeltaReviewState({ keepReviewerLabel: true });
    }
    if (event.target.matches("#private-blueprint-delta-reviewer-label")) {
      state.privateBlueprintDeltaReviewerLabel = event.target.value.slice(0, 36);
      state.privateBlueprintDeltaReviewReceipt = null;
      state.privateBlueprintDeltaReviewVerification = null;
      resetPrivateBlueprintRevisionDraftState();
    }
    if (event.target.matches("#private-blueprint-delta-review-import")) {
      state.privateBlueprintDeltaReviewImportText = event.target.value.slice(0, dataAdapter?.PRIVATE_BLUEPRINT_DELTA_REVIEW_MAX_LENGTH || 3145728);
      state.privateBlueprintDeltaReviewReceipt = null;
      state.privateBlueprintDeltaReviewVerification = null;
      resetPrivateBlueprintRevisionDraftState();
    }
    if (event.target.matches("#private-blueprint-revision-draft-import")) {
      state.privateBlueprintRevisionDraftImportText = event.target.value.slice(0, dataAdapter?.PRIVATE_BLUEPRINT_REVISION_DRAFT_MAX_LENGTH || 4194304);
      state.privateBlueprintRevisionDraftReceipt = null;
      state.privateBlueprintRevisionDraftVerification = null;
      resetPrivateBlueprintDraftReviewState({ keepReviewerLabel: true });
    }
    if (event.target.matches("#private-blueprint-draft-reviewer-label")) {
      state.privateBlueprintDraftReviewerLabel = event.target.value.slice(0, 36);
      state.privateBlueprintDraftReviewReceipt = null;
      state.privateBlueprintDraftReviewVerification = null;
      resetPrivateBlueprintGuardCompletionState({ keepReviewerLabel: true });
    }
    if (event.target.matches("#private-blueprint-draft-review-import")) {
      state.privateBlueprintDraftReviewImportText = event.target.value.slice(0, dataAdapter?.PRIVATE_BLUEPRINT_DRAFT_REVIEW_MAX_LENGTH || 5242880);
      state.privateBlueprintDraftReviewReceipt = null;
      state.privateBlueprintDraftReviewVerification = null;
      resetPrivateBlueprintGuardCompletionState({ keepReviewerLabel: true });
    }
    if (event.target.matches("#private-blueprint-guard-completion-reviewer-label")) {
      state.privateBlueprintGuardCompletionReviewerLabel = event.target.value.slice(0, 36);
      state.privateBlueprintGuardCompletionReceipt = null;
      state.privateBlueprintGuardCompletionVerification = null;
      resetPrivateBlueprintGuardCompletionReviewState({ keepReviewerLabel: true });
    }
    if (event.target.matches("#private-blueprint-guard-completion-import")) {
      state.privateBlueprintGuardCompletionImportText = event.target.value.slice(0, dataAdapter?.PRIVATE_BLUEPRINT_GUARD_COMPLETION_MAX_LENGTH || 6291456);
      state.privateBlueprintGuardCompletionReceipt = null;
      state.privateBlueprintGuardCompletionVerification = null;
      resetPrivateBlueprintGuardCompletionReviewState({ keepReviewerLabel: true });
    }
    if (event.target.matches("#private-blueprint-guard-completion-review-reviewer-label")) {
      state.privateBlueprintGuardCompletionReviewReviewerLabel = event.target.value.slice(0, 36);
      state.privateBlueprintGuardCompletionReviewReceipt = null;
      state.privateBlueprintGuardCompletionReviewVerification = null;
      resetPrivateBlueprintOperatorReviewPacketState();
    }
    if (event.target.matches("#private-blueprint-guard-completion-review-import")) {
      state.privateBlueprintGuardCompletionReviewImportText = event.target.value.slice(0, dataAdapter?.PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_MAX_LENGTH || 7340032);
      state.privateBlueprintGuardCompletionReviewReceipt = null;
      state.privateBlueprintGuardCompletionReviewVerification = null;
      resetPrivateBlueprintOperatorReviewPacketState();
    }
    if (event.target.matches("#private-blueprint-operator-review-packet-import")) {
      state.privateBlueprintOperatorReviewPacketImportText = event.target.value.slice(0, dataAdapter?.PRIVATE_BLUEPRINT_OPERATOR_REVIEW_PACKET_MAX_LENGTH || 8388608);
      state.privateBlueprintOperatorReviewPacketReceipt = null;
      state.privateBlueprintOperatorReviewPacketVerification = null;
    }
  });
  document.addEventListener("change", (event) => {
    if (event.target.matches("[data-portable-review-decision]")) {
      const decision = event.target.value;
      const reasons = dataAdapter?.PORTABLE_REVIEW_REASONS?.[decision] || [];
      state.portableReviewDecision = decision;
      state.portableReviewReason = reasons[0] || "";
      const reasonSelect = $("[data-portable-review-reason]");
      if (reasonSelect) reasonSelect.innerHTML = portableReviewReasonOptions(decision);
      state.portableReviewMessage = null;
      return;
    }
    if (event.target.matches("[data-portable-review-reason]")) {
      state.portableReviewReason = event.target.value;
      state.portableReviewMessage = null;
      return;
    }
    if (event.target.matches("[data-portable-correction-target]")) {
      state.portableCorrectionTargetDigest = event.target.value;
      state.portableReviewCorrectionMessage = null;
      ensurePortableCorrectionSelection();
      renderReceiptLearning();
      $("[data-portable-correction-target]")?.focus?.({ preventScroll: true });
      return;
    }
    if (event.target.matches("[data-portable-correction-action]")) {
      state.portableCorrectionAction = event.target.value;
      const reasons = dataAdapter?.PORTABLE_REVIEW_CORRECTION_REASONS?.[state.portableCorrectionAction] || [];
      state.portableCorrectionReason = reasons[0] || "";
      state.portableReviewCorrectionMessage = null;
      ensurePortableCorrectionSelection();
      renderReceiptLearning();
      $("[data-portable-correction-action]")?.focus?.({ preventScroll: true });
      return;
    }
    if (event.target.matches("[data-portable-correction-decision]")) {
      state.portableCorrectionDecision = event.target.value;
      state.portableReviewCorrectionMessage = null;
      return;
    }
    if (event.target.matches("[data-portable-correction-reason]")) {
      state.portableCorrectionReason = event.target.value;
      state.portableReviewCorrectionMessage = null;
      return;
    }
    if (event.target.matches("[data-private-blueprint-delta-review-decision]")) {
      const decision = event.target.value;
      const reasons = dataAdapter?.PRIVATE_BLUEPRINT_DELTA_REVIEW_REASONS?.[decision] || [];
      state.privateBlueprintDeltaReviewDecision = decision;
      state.privateBlueprintDeltaReviewReason = reasons[0] || "";
      state.privateBlueprintDeltaReviewReceipt = null;
      state.privateBlueprintDeltaReviewVerification = null;
      resetPrivateBlueprintRevisionDraftState();
      const reasonSelect = $("[data-private-blueprint-delta-review-reason]");
      if (reasonSelect) reasonSelect.innerHTML = privateBlueprintDeltaReviewReasonOptions(decision);
      return;
    }
    if (event.target.matches("[data-private-blueprint-delta-review-reason]")) {
      state.privateBlueprintDeltaReviewReason = event.target.value;
      state.privateBlueprintDeltaReviewReceipt = null;
      state.privateBlueprintDeltaReviewVerification = null;
      resetPrivateBlueprintRevisionDraftState();
      return;
    }
    if (event.target.matches("[data-private-blueprint-draft-review-decision]")) {
      const decision = event.target.value;
      const reasons = dataAdapter?.PRIVATE_BLUEPRINT_DRAFT_REVIEW_REASONS?.[decision] || [];
      state.privateBlueprintDraftReviewDecision = decision;
      state.privateBlueprintDraftReviewReason = reasons[0] || "";
      state.privateBlueprintDraftReviewReceipt = null;
      state.privateBlueprintDraftReviewVerification = null;
      resetPrivateBlueprintGuardCompletionState({ keepReviewerLabel: true });
      const reasonSelect = $("[data-private-blueprint-draft-review-reason]");
      if (reasonSelect) reasonSelect.innerHTML = privateBlueprintDraftReviewReasonOptions(decision);
      return;
    }
    if (event.target.matches("[data-private-blueprint-draft-review-reason]")) {
      state.privateBlueprintDraftReviewReason = event.target.value;
      state.privateBlueprintDraftReviewReceipt = null;
      state.privateBlueprintDraftReviewVerification = null;
      resetPrivateBlueprintGuardCompletionState({ keepReviewerLabel: true });
      return;
    }
    if (event.target.matches("[data-private-blueprint-guard-completion-reason]")) {
      state.privateBlueprintGuardCompletionReason = event.target.value;
      state.privateBlueprintGuardCompletionReceipt = null;
      state.privateBlueprintGuardCompletionVerification = null;
      resetPrivateBlueprintGuardCompletionReviewState({ keepReviewerLabel: true });
      return;
    }
    if (event.target.matches("[data-private-blueprint-guard-completion-value]")) {
      const guardKey = event.target.dataset.privateBlueprintGuardCompletionValue;
      state.privateBlueprintGuardCompletionValues[guardKey] = event.target.value === "true" ? true : event.target.value === "false" ? false : "";
      state.privateBlueprintGuardCompletionReceipt = null;
      state.privateBlueprintGuardCompletionVerification = null;
      resetPrivateBlueprintGuardCompletionReviewState({ keepReviewerLabel: true });
      return;
    }
    if (event.target.matches("[data-private-blueprint-guard-completion-provenance]")) {
      const guardKey = event.target.dataset.privateBlueprintGuardCompletionProvenance;
      state.privateBlueprintGuardCompletionProvenance[guardKey] = event.target.value;
      state.privateBlueprintGuardCompletionReceipt = null;
      state.privateBlueprintGuardCompletionVerification = null;
      resetPrivateBlueprintGuardCompletionReviewState({ keepReviewerLabel: true });
      return;
    }
    if (event.target.matches("[data-private-blueprint-guard-completion-review-decision]")) {
      const decision = event.target.value;
      const reasons = dataAdapter?.PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_REASONS?.[decision] || [];
      state.privateBlueprintGuardCompletionReviewDecision = decision;
      state.privateBlueprintGuardCompletionReviewReason = reasons[0] || "";
      state.privateBlueprintGuardCompletionReviewReceipt = null;
      state.privateBlueprintGuardCompletionReviewVerification = null;
      resetPrivateBlueprintOperatorReviewPacketState();
      const reasonSelect = $("[data-private-blueprint-guard-completion-review-reason]");
      if (reasonSelect) reasonSelect.innerHTML = privateBlueprintGuardCompletionReviewReasonOptions(decision);
      return;
    }
    if (event.target.matches("[data-private-blueprint-guard-completion-review-reason]")) {
      state.privateBlueprintGuardCompletionReviewReason = event.target.value;
      state.privateBlueprintGuardCompletionReviewReceipt = null;
      state.privateBlueprintGuardCompletionReviewVerification = null;
      resetPrivateBlueprintOperatorReviewPacketState();
    }
  });

  $("#notifications-button").addEventListener("click", () => openSheet($("#automations-sheet")));
  $("#profile-button").addEventListener("click", () => {
    renderSessionSheet();
    openSheet($("#session-sheet"));
  });
  $("#watch-filter").addEventListener("click", () => { state.followingFirst = !state.followingFirst; $("#watch-filter").textContent = state.followingFirst ? "Default order" : "Following first"; renderChannels(); });
  $("#builder-form").addEventListener("input", renderBlueprint);
  $("#builder-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const blueprint = renderBlueprint();
    try {
      const serialized = JSON.stringify(blueprint);
      localStorage.setItem(BLUEPRINT_STORAGE_KEY, serialized);
      if (localStorage.getItem(BLUEPRINT_STORAGE_KEY) !== serialized) throw new Error("browser storage did not retain blueprint");
      state.blueprintStored = true;
      state.blueprintPersistenceAvailable = true;
      renderSessionSheet();
      showToast("Blueprint saved locally. Preview a proposed fixture next; no qualification or execution occurred.");
    } catch {
      state.blueprintStored = false;
      state.blueprintPersistenceAvailable = false;
      renderSessionSheet();
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
  renderStarterGuide();
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
  renderSessionSheet();
  renderAutomations();
}

async function boot() {
  try {
    if (!dataAdapter) throw new Error("local data adapter unavailable");
    state.data = await dataAdapter.loadArenaData(fetch);
    hydrateStarterGuide();
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
