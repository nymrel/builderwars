"use strict";

(function installDataAdapter(root, factory) {
  const adapter = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = adapter;
  if (root) root.BuilderWarsDataAdapter = adapter;
}(typeof globalThis !== "undefined" ? globalThis : this, function createDataAdapter() {
  const DEMO_SCHEMA = "builderwars.mobile-arena-demo.v1";
  const READ_MODEL_SCHEMA = "builderwars.arena-read-model.v1";
  const VIEW_SCHEMA = "builderwars.mobile-arena-view.v1";
  const QUALIFICATION_SCHEMA = "builderwars.mobile-qualification-preview.v1";
  const LEARNING_SCHEMA = "builderwars.mobile-receipt-learning.v1";
  const RUNBACK_PROPOSAL_SCHEMA = "builderwars.mobile-runback-proposal.v1";
  const PORTABLE_RUNBACK_SCHEMA = "builderwars.mobile-runback-portable.v1";
  const PORTABLE_REVIEW_SCHEMA = "builderwars.mobile-runback-review.v1";
  const PORTABLE_REVIEW_EXCHANGE_SCHEMA = "builderwars.mobile-runback-review-exchange.v1";
  const PORTABLE_REVIEW_CORRECTION_SCHEMA = "builderwars.mobile-runback-review-correction.v1";
  const PORTABLE_REVIEW_CORRECTION_EXCHANGE_SCHEMA = "builderwars.mobile-runback-review-correction-exchange.v1";
  const PORTABLE_REVIEW_COMPARISON_SCHEMA = "builderwars.mobile-private-review-comparison.v1";
  const PRIVATE_REVIEW_LEARNING_SCHEMA = "builderwars.mobile-private-review-learning.v1";
  const PRIVATE_BLUEPRINT_DELTA_SCHEMA = "builderwars.mobile-private-inspection-blueprint-delta.v1";
  const PRIVATE_BLUEPRINT_DELTA_REVIEW_SCHEMA = "builderwars.mobile-private-inspection-blueprint-delta-review.v1";
  const PREVIEW_RESOURCE_CLASS = "local-preview-no-compute-v1";
  const PORTABLE_RUNBACK_MAX_LENGTH = 32768;
  const PORTABLE_REVIEW_MAX_RECORDS = 64;
  const PORTABLE_REVIEW_EXCHANGE_MAX_LENGTH = 262144;
  const PORTABLE_REVIEW_CORRECTION_MAX_RECORDS = 64;
  const PORTABLE_REVIEW_CORRECTION_EXCHANGE_MAX_LENGTH = 524288;
  const PORTABLE_REVIEW_COMPARISON_MAX_ENTRIES = PORTABLE_REVIEW_MAX_RECORDS * 2;
  const PORTABLE_REVIEW_COMPARISON_MAX_LENGTH = 1572864;
  const PRIVATE_REVIEW_LEARNING_MAX_ENTRIES = PORTABLE_REVIEW_COMPARISON_MAX_ENTRIES;
  const PRIVATE_REVIEW_LEARNING_MAX_LENGTH = 2097152;
  const PRIVATE_BLUEPRINT_DELTA_MAX_LENGTH = 2621440;
  const PRIVATE_BLUEPRINT_DELTA_REVIEW_MAX_LENGTH = 3145728;
  const SAFE_JSON_NODE_LIMIT = 16384;
  const PORTABLE_REVIEW_COMPARISON_NODE_LIMIT = 49152;
  const PRIVATE_REVIEW_LEARNING_NODE_LIMIT = 65536;
  const PRIVATE_BLUEPRINT_DELTA_NODE_LIMIT = 73728;
  const PRIVATE_BLUEPRINT_DELTA_REVIEW_NODE_LIMIT = 81920;
  const HEX64 = /^[0-9a-f]{64}$/;
  const CHALLENGE_ID = /^challenge_[0-9a-f]{16}$/;
  const DANGEROUS_KEYS = new Set(["__proto__", "constructor", "prototype"]);
  const RUNBACK_EXECUTION_BLOCKERS = Object.freeze([
    "explicit_rules_digest_not_bound",
    "qualification_not_run",
    "sanctioned_runner_not_bound",
    "local_blueprint_version_not_committed",
  ]);
  const RUNBACK_RULES_STATEMENT = "The bounded mobile read model does not carry an explicit historical rules digest. A sanctioned runback must bind one before qualification.";
  const RUNBACK_PROPOSAL_BOUNDARY = "This versioned object is a local, still-unplayed proposal. It preserves parent receipt and challenge lineage, but it does not qualify, execute, attest, rank, publish, or spend.";
  const PORTABLE_RUNBACK_BOUNDARY = "This canonical envelope carries a local, still-unplayed proposal plus a SHA-256 integrity checksum. The checksum detects accidental or unacknowledged content changes; it is not a signature, does not authenticate an author or provider, and grants no qualification, execution, registry, ranking, publication, or spending authority.";
  const PORTABLE_REVIEW_BOUNDARY = "This append-only local review record binds one verified portable proposal to an unattested reviewer label and a bounded private decision. Its SHA-256 chain is integrity evidence, not a signature or identity claim. It cannot bind missing rules, qualify, execute, attest, register, rank, publish, or spend.";
  const PORTABLE_REVIEW_EXCHANGE_BOUNDARY = "This canonical packet supports independent local inspection of one still-unplayed proposal and its private review journal. Its SHA-256 digests detect changed content but are not signatures or identity claims. Import is memory-only and cannot apply a blueprint, bind rules, qualify, execute, attest, register, rank, publish, spend, or call a provider.";
  const PORTABLE_REVIEW_CORRECTION_BOUNDARY = "This append-only private correction record preserves its immutable target review and proposal lineage while recording one corrected private decision or withdrawal. Its SHA-256 links are integrity evidence, not signatures, reviewer identity, approval, or authority. It cannot rewrite history, apply a blueprint, bind rules, qualify, execute, attest, register, rank, publish, spend, or call a provider.";
  const PORTABLE_REVIEW_CORRECTION_EXCHANGE_BOUNDARY = "This canonical packet supports independent local inspection of one still-unplayed proposal, its immutable private reviews, and their append-only correction history. Its SHA-256 digests are not signatures or identity claims. Import is memory-only and cannot rewrite a review, apply a blueprint, bind rules, qualify, execute, attest, register, rank, publish, spend, or call a provider.";
  const PORTABLE_REVIEW_COMPARISON_BOUNDARY = "This canonical receipt independently reverifies and compares two private correction packets for the exact same still-unplayed proposal. It reports digest-bound review-state differences without choosing a winner, merging histories, resolving a dispute, authenticating identity, applying a blueprint, binding rules, qualifying, executing, registering, ranking, publishing, spending, or calling a provider.";
  const PRIVATE_REVIEW_LEARNING_BOUNDARY = "This canonical receipt independently reverifies one private comparison and maps each digest-bound comparison class to one fixed inspection-only lesson. It preserves Packet A, Packet B, and every source digest without declaring either state correct, creating consensus, granting approval or progress, adopting a blueprint, merging histories, resolving a dispute, authenticating identity, binding rules, qualifying, executing, registering, ranking, publishing, spending, or calling a provider.";
  const PRIVATE_BLUEPRINT_DELTA_BOUNDARY = "This canonical receipt independently reverifies one comparison-linked learning receipt and maps one exact digest-bound inspection lesson to one fixed allowlisted guard requirement. It preserves the parent proposal, Packet A, Packet B, and every source digest. The requirement remains uncommitted and unplayed, does not declare a correct packet, and cannot create consensus, approval, progress, blueprint adoption, identity, merge, resolution, rules, qualification, execution, registry, ranking, publication, spending, or provider authority.";
  const PRIVATE_BLUEPRINT_DELTA_REVIEW_BOUNDARY = "This canonical receipt independently reverifies one private inspection-to-blueprint guard proposal and records exactly one immutable private local review. An accept-for-revision decision may create only a proposed uncommitted local revision candidate; it does not adopt the guard, edit the parent proposal, declare correctness, create consensus, grant approval or progress, authenticate identity, merge or resolve histories, bind rules, qualify, play, execute, register, rank, publish, spend, or call a provider.";
  const ALLOWED_BASE_MODELS = new Set(["Arena Small", "Arena Reason", "Local runner (not paired)"]);
  const ALLOWED_HARNESS_STYLES = new Set(["Validate every move", "Budget-aware planner", "Human review checkpoints", "Naive control"]);
  const RUNBACK_DELTAS = Object.freeze([
    { id: "require_strict_validation", guardKey: "strictValidation", label: "Require strict move validation", rationale: "Retain legal-move refusal in the next local blueprint version." },
    { id: "require_fallback_disclosure", guardKey: "fallbackDisclosure", label: "Require fallback disclosure", rationale: "Make every fallback move visible before any future result is reviewed." },
    { id: "require_human_checkpoints", guardKey: "humanCheckpoints", label: "Require human checkpoints", rationale: "Declare a bounded review checkpoint before any future execution request." },
  ]);
  const PORTABLE_REVIEW_REASONS = Object.freeze({
    accept_for_blueprint_revision: Object.freeze(["receipt_guided_guard_change"]),
    defer: Object.freeze(["needs_explicit_rules_binding", "insufficient_public_evidence"]),
    reject: Object.freeze(["duplicate_or_stale_proposal", "unsafe_or_out_of_scope"]),
  });
  const PORTABLE_REVIEW_CORRECTION_REASONS = Object.freeze({
    correct_decision: Object.freeze(["clerical_decision_error", "new_private_evidence", "unsafe_scope_discovered"]),
    withdraw_review: Object.freeze(["duplicate_review", "reviewer_requested_withdrawal", "unsafe_scope_discovered"]),
  });
  const PRIVATE_REVIEW_INSPECTION_LESSONS = Object.freeze({
    inspect_evidence: Object.freeze({
      label: "Inspect visible evidence",
      guidance: "Compare only evidence carried by Packet A and Packet B. Do not infer missing evidence, author identity, or correctness.",
    }),
    inspect_rules_binding: Object.freeze({
      label: "Inspect rules binding",
      guidance: "Confirm whether an explicit rules digest is bound before qualification. Matching private states do not bind rules or create authority.",
    }),
    inspect_correction_lineage: Object.freeze({
      label: "Inspect correction lineage",
      guidance: "Trace each immutable review and append-only correction head. Do not choose a correct branch or merge the histories.",
    }),
  });
  const PRIVATE_REVIEW_CLASS_LESSON = Object.freeze({
    identical_effective_state: "inspect_rules_binding",
    changed_effective_state: "inspect_correction_lineage",
    left_only_review: "inspect_evidence",
    right_only_review: "inspect_evidence",
  });
  const PRIVATE_REVIEW_LESSON_DELTA = Object.freeze({
    inspect_evidence: "require_fallback_disclosure",
    inspect_rules_binding: "require_human_checkpoints",
    inspect_correction_lineage: "require_strict_validation",
  });
  const PRIVATE_BLUEPRINT_DELTA_BLOCKERS = Object.freeze([
    "lesson_does_not_establish_correctness",
    "local_blueprint_version_not_committed",
    "explicit_rules_digest_not_bound",
    "qualification_not_run",
    "fixture_not_activated",
    "sanctioned_runner_not_bound",
    "registry_not_requested",
    "publication_not_requested",
  ]);
  const PRIVATE_BLUEPRINT_DELTA_REVIEW_REASONS = Object.freeze({
    accept_for_revision: Object.freeze(["guard_matches_verified_lesson", "guard_closes_local_safety_gap"]),
    defer: Object.freeze(["needs_explicit_rules_binding", "needs_additional_private_evidence", "needs_operator_revision_review"]),
    reject: Object.freeze(["lesson_guard_mismatch", "duplicate_or_unnecessary_guard", "unsafe_or_out_of_scope"]),
  });
  const PRIVATE_BLUEPRINT_DELTA_REVIEW_BLOCKERS = Object.freeze([
    "reviewer_identity_unattested",
    "lesson_does_not_establish_correctness",
    "local_revision_not_committed",
    "explicit_rules_digest_not_bound",
    "qualification_not_run",
    "fixture_not_activated",
    "sanctioned_runner_not_bound",
    "registry_not_requested",
    "publication_not_requested",
  ]);
  const PORTABLE_REVIEW_BLOCKERS = Object.freeze([
    "reviewer_identity_unattested",
    "explicit_rules_digest_not_bound",
    "qualification_not_run",
    "sanctioned_runner_not_bound",
    "local_blueprint_version_not_committed",
    "registry_not_requested",
    "publication_not_requested",
  ]);

  function requireValue(predicate, message) {
    if (!predicate) throw new Error(message);
  }

  function isObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function assertSafeKeys(value, path = "value", depth = 0, state = { nodes: 0 }, nodeLimit = SAFE_JSON_NODE_LIMIT) {
    requireValue(depth <= 32, "unsafe portable runback: nesting limit exceeded");
    state.nodes += 1;
    requireValue(state.nodes <= nodeLimit, "unsafe portable runback: node limit exceeded");
    if (Array.isArray(value)) {
      value.forEach((item, index) => assertSafeKeys(item, `${path}[${index}]`, depth + 1, state, nodeLimit));
      return;
    }
    if (!isObject(value)) return;
    for (const key of Object.keys(value)) {
      requireValue(!DANGEROUS_KEYS.has(key), `unsafe portable runback: prohibited key at ${path}.${key}`);
      assertSafeKeys(value[key], `${path}.${key}`, depth + 1, state, nodeLimit);
    }
  }

  function requireExactKeys(value, expected, context) {
    requireValue(isObject(value), `unsafe portable runback: ${context} must be an object`);
    const actual = Object.keys(value).sort();
    const wanted = [...expected].sort();
    requireValue(actual.length === wanted.length && actual.every((key, index) => key === wanted[index]), `unsafe portable runback: ${context} fields drift`);
  }

  function canonicalJSON(value) {
    if (value === null || typeof value === "boolean" || typeof value === "string") return JSON.stringify(value);
    if (typeof value === "number") {
      requireValue(Number.isFinite(value), "unsafe portable runback: non-finite number");
      return JSON.stringify(value);
    }
    if (Array.isArray(value)) return `[${value.map((item) => canonicalJSON(item)).join(",")}]`;
    requireValue(isObject(value), "unsafe portable runback: unsupported JSON value");
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJSON(value[key])}`).join(",")}}`;
  }

  async function sha256Hex(value) {
    requireValue(typeof TextEncoder !== "undefined" && globalThis.crypto?.subtle, "unsafe portable runback: SHA-256 unavailable");
    const digest = await globalThis.crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
    return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
  }

  function equalHex(left, right) {
    if (typeof left !== "string" || typeof right !== "string" || left.length !== right.length) return false;
    let difference = 0;
    for (let index = 0; index < left.length; index += 1) difference |= left.charCodeAt(index) ^ right.charCodeAt(index);
    return difference === 0;
  }

  function nonNegativeInteger(value) {
    return Number.isInteger(value) && value >= 0;
  }

  function validateDemoFixture(fixture) {
    requireValue(isObject(fixture), "unsafe demo fixture: expected object");
    requireValue(fixture.schemaVersion === DEMO_SCHEMA, "unsafe demo fixture: schema drift");
    requireValue(fixture.demoOnly === true, "unsafe demo fixture: demoOnly must remain true");
    requireValue(fixture.sourceStatus === "local_fixture_not_live", "unsafe demo fixture: source status drift");
    for (const field of ["watchlist", "tape", "channels", "leaderboard", "quickMatches", "freeModels", "lessons", "automations"]) {
      requireValue(Array.isArray(fixture[field]), `unsafe demo fixture: ${field} must be an array`);
    }
    requireValue(isObject(fixture.featured) && isObject(fixture.featured.proof), "unsafe demo fixture: featured proof missing");
    const proof = fixture.featured.proof;
    requireValue(proof.modelAttested === false, "unsafe demo fixture: model attestation must stay false");
    requireValue(proof.providerAttested === false, "unsafe demo fixture: provider attestation must stay false");
    requireValue(proof.runtimeAttested === false, "unsafe demo fixture: runtime attestation must stay false");
    requireValue(proof.registryState === "pending_registry_commit", "unsafe demo fixture: registry boundary drift");
    return fixture;
  }

  function validateArenaReadModel(model) {
    requireValue(isObject(model), "unsafe arena read model: expected object");
    requireValue(model.schemaVersion === READ_MODEL_SCHEMA, "unsafe arena read model: schema drift");
    requireValue(model.projectionVersion === "1", "unsafe arena read model: projection drift");
    requireValue(typeof model.readModelDigest === "string" && HEX64.test(model.readModelDigest), "unsafe arena read model: digest missing");
    requireValue(isObject(model.source), "unsafe arena read model: source missing");
    requireValue(model.source.status === "tracked_local_publication_artifact_not_hosted", "unsafe arena read model: source status drift");
    requireValue(model.source.publicationPolicy === "explicit_reviewed_allowlist_only", "unsafe arena read model: publication policy drift");
    requireValue(isObject(model.truthBoundary), "unsafe arena read model: truth boundary missing");
    for (const field of ["live", "hosted", "authenticated", "modelAttested", "providerAttested", "runtimeAttested"]) {
      requireValue(model.truthBoundary[field] === false, `unsafe arena read model: ${field} must stay false`);
    }
    requireValue(Array.isArray(model.receipts) && model.receipts.length > 0, "unsafe arena read model: receipts missing");
    requireValue(isObject(model.summary), "unsafe arena read model: summary missing");
    requireValue(model.summary.receiptCount === model.receipts.length, "unsafe arena read model: receipt count mismatch");
    requireValue(model.summary.verifiedReceiptCount === model.receipts.length, "unsafe arena read model: unverified receipt count");
    requireValue(model.summary.modelAttestedReceiptCount === 0, "unsafe arena read model: model attestation count drift");

    const receiptIds = new Set();
    const receiptById = new Map();
    for (const receipt of model.receipts) {
      requireValue(isObject(receipt) && HEX64.test(receipt.receiptId), "unsafe arena read model: invalid receipt id");
      requireValue(HEX64.test(receipt.fixtureId), `unsafe arena read model: invalid fixture for ${receipt.receiptId}`);
      requireValue(!receiptIds.has(receipt.receiptId), `unsafe arena read model: duplicate receipt ${receipt.receiptId}`);
      receiptIds.add(receipt.receiptId);
      receiptById.set(receipt.receiptId, receipt);
      requireValue(Array.isArray(receipt.entrants) && receipt.entrants.length >= 2, `unsafe arena read model: entrants missing for ${receipt.receiptId}`);
      requireValue(isObject(receipt.proof), `unsafe arena read model: proof missing for ${receipt.receiptId}`);
      requireValue(receipt.proof.publicationApproved === true, `unsafe arena read model: unpublished receipt ${receipt.receiptId}`);
      requireValue(receipt.proof.replayVerdict === "PASS", `unsafe arena read model: replay failed for ${receipt.receiptId}`);
      requireValue(receipt.proof.engineDigestMatch === true, `unsafe arena read model: engine mismatch for ${receipt.receiptId}`);
      requireValue(receipt.proof.verifierSnapshotMatch === true, `unsafe arena read model: verifier mismatch for ${receipt.receiptId}`);
      requireValue(isObject(receipt.evidence), `unsafe arena read model: evidence missing for ${receipt.receiptId}`);
      for (const field of ["modelAttested", "providerAttested", "runtimeAttested"]) {
        requireValue(receipt.evidence[field] === false, `unsafe arena read model: ${field} drift for ${receipt.receiptId}`);
      }
      requireValue(isObject(receipt.evidence.moveSourceCounts), `unsafe arena read model: move counts missing for ${receipt.receiptId}`);
      for (const field of ["model", "scripted", "fallback", "other"]) {
        requireValue(nonNegativeInteger(receipt.evidence.moveSourceCounts[field]), `unsafe arena read model: invalid ${field} count for ${receipt.receiptId}`);
      }
      requireValue(isObject(receipt.outcome) && HEX64.test(receipt.outcome.winnerEntrantId), `unsafe arena read model: outcome missing for ${receipt.receiptId}`);
      requireValue(receipt.entrants.some((entrant) => entrant.entrantId === receipt.outcome.winnerEntrantId), `unsafe arena read model: winner is not an entrant for ${receipt.receiptId}`);
      requireValue(receipt.entrants.every((entrant) => entrant.harnessVersionContentDerived === true && HEX64.test(entrant.harnessVersionId)), `unsafe arena read model: harness version drift for ${receipt.receiptId}`);
    }

    requireValue(Array.isArray(model.channels), "unsafe arena read model: channels missing");
    requireValue(Array.isArray(model.rivalries), "unsafe arena read model: rivalries missing");
    requireValue(Array.isArray(model.futureFixtures), "unsafe arena read model: future fixtures missing");
    const rivalryReceiptIds = new Set();
    for (const rivalry of model.rivalries) {
      requireValue(HEX64.test(rivalry.rivalryId), "unsafe arena read model: invalid rivalry id");
      requireValue(Array.isArray(rivalry.entrantIds) && rivalry.entrantIds.length === 2, `unsafe arena read model: rivalry entrants missing for ${rivalry.rivalryId}`);
      requireValue(rivalry.entrantIds.every((entrantId) => HEX64.test(entrantId)), `unsafe arena read model: invalid rivalry entrant for ${rivalry.rivalryId}`);
      requireValue(Array.isArray(rivalry.meetings) && rivalry.meetingCount === rivalry.meetings.length && rivalry.meetingCount > 0, `unsafe arena read model: rivalry meeting count drift for ${rivalry.rivalryId}`);
      for (const [meetingIndex, meeting] of rivalry.meetings.entries()) {
        requireValue(receiptIds.has(meeting.receiptId), `unsafe arena read model: unknown rivalry receipt ${meeting.receiptId}`);
        requireValue(!rivalryReceiptIds.has(meeting.receiptId), `unsafe arena read model: duplicate rivalry receipt ${meeting.receiptId}`);
        rivalryReceiptIds.add(meeting.receiptId);
        const receipt = receiptById.get(meeting.receiptId);
        requireValue(meeting.meetingNumber === meetingIndex + 1, `unsafe arena read model: rivalry meeting order drift for ${rivalry.rivalryId}`);
        requireValue(receipt.game.name === meeting.game, `unsafe arena read model: rivalry game drift for ${meeting.receiptId}`);
        requireValue(receipt.outcome.winnerEntrantId === meeting.winnerEntrantId, `unsafe arena read model: rivalry outcome drift for ${meeting.receiptId}`);
        requireValue(receipt.entrants.every((entrant) => rivalry.entrantIds.includes(entrant.entrantId)), `unsafe arena read model: rivalry entrant drift for ${meeting.receiptId}`);
        requireValue(rivalry.entrantIds.includes(meeting.winnerEntrantId), `unsafe arena read model: rivalry winner drift for ${meeting.receiptId}`);
        requireValue(isObject(meeting.runback), `unsafe arena read model: rivalry runback missing for ${meeting.receiptId}`);
        requireValue(meeting.runback.parentReceiptId === meeting.receiptId, `unsafe arena read model: rivalry parent drift for ${meeting.receiptId}`);
        requireValue(meeting.runback.status === "unplayed_challenge", `unsafe arena read model: rivalry runback activated for ${meeting.receiptId}`);
        requireValue(HEX64.test(meeting.runback.fixtureId), `unsafe arena read model: invalid rivalry runback fixture for ${meeting.receiptId}`);
        requireValue(CHALLENGE_ID.test(meeting.runback.challengeId), `unsafe arena read model: invalid rivalry challenge for ${meeting.receiptId}`);
      }
    }
    requireValue(rivalryReceiptIds.size === receiptIds.size, "unsafe arena read model: receipt missing rivalry runback lineage");
    for (const fixture of model.futureFixtures) {
      requireValue(HEX64.test(fixture.fixtureId), "unsafe arena read model: invalid future fixture id");
      requireValue(isObject(fixture.game) && typeof fixture.game.name === "string" && fixture.game.version === "1", `unsafe arena read model: future fixture game drift for ${fixture.fixtureId}`);
      requireValue(typeof fixture.rulesWeekId === "string" && fixture.rulesWeekId.length > 0, `unsafe arena read model: future fixture rules missing for ${fixture.fixtureId}`);
      requireValue(HEX64.test(fixture.rulesDigest), `unsafe arena read model: future fixture rules digest missing for ${fixture.fixtureId}`);
      requireValue(fixture.activationStatus === "proposed_not_activated", "unsafe arena read model: activated future fixture");
      requireValue(fixture.status === "unplayed", "unsafe arena read model: future fixture status drift");
    }
    return model;
  }

  function evidenceLabel(evidenceClass) {
    return ({
      model_influenced_unattested: "model-influenced · unattested",
      scripted_reference: "scripted reference",
      fallback_only_reference: "fallback-only reference",
      other_unattested_reference: "other source · unattested",
    })[evidenceClass] || "unattested reference";
  }

  function gameLabel(value) {
    return String(value || "unknown").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  function symbolFor(value) {
    const parts = String(value || "BW").split(/[_\s-]+/).filter(Boolean);
    return parts.slice(0, 3).map((part) => part[0]).join("").toUpperCase().padEnd(2, "W");
  }

  function proofFromReceipt(receipt, boundary, runback) {
    const counts = receipt.evidence.moveSourceCounts;
    return {
      receiptId: receipt.receiptId,
      fixtureId: receipt.fixtureId,
      game: clone(receipt.game),
      headline: receipt.headline,
      artifactPath: receipt.proof.artifactPath,
      replayVerdict: receipt.proof.replayVerdict,
      engineDigestMatch: receipt.proof.engineDigestMatch,
      verifierSnapshotMatch: receipt.proof.verifierSnapshotMatch,
      publicationApproved: receipt.proof.publicationApproved,
      evidenceClass: receipt.evidence.class,
      evidenceLabel: evidenceLabel(receipt.evidence.class),
      moveSourceCounts: { ...counts },
      harnessVersionBound: receipt.entrants.every((entrant) => entrant.harnessVersionContentDerived === true),
      modelAttested: false,
      providerAttested: false,
      runtimeAttested: false,
      registryState: "no_authoritative_registry_commit",
      runback: clone(runback),
      boundary,
    };
  }

  function featuredFromReceipt(receipt, proof) {
    const winner = receipt.entrants.find((entrant) => entrant.entrantId === receipt.outcome.winnerEntrantId);
    const opponent = receipt.entrants.find((entrant) => entrant.entrantId !== receipt.outcome.winnerEntrantId) || receipt.entrants[0];
    return {
      id: receipt.receiptId,
      channel: gameLabel(receipt.game.name),
      status: "reviewed_receipt",
      statusLabel: "Reviewed receipt",
      clock: `${gameLabel(receipt.game.name)} v${receipt.game.version}`,
      title: `${winner.name} vs ${opponent.name}`,
      subtitle: `${receipt.resultLine}. ${proof.evidenceLabel}.`,
      scoreAriaLabel: `Verified outcome: ${winner.name} won over ${opponent.name}`,
      left: { name: winner.name, score: "W", accent: "lime" },
      right: { name: opponent.name, score: "L", accent: "ivory" },
      proof,
      runbackAvailable: false,
      runbackLabel: "Runback pending",
    };
  }

  function buildReceiptBoard(receipts) {
    const entrants = new Map();
    for (const receipt of receipts) {
      for (const entrant of receipt.entrants) {
        const current = entrants.get(entrant.entrantId) || {
          id: entrant.entrantId,
          name: entrant.name,
          receipts: 0,
          wins: 0,
          harnessVersions: new Set(),
        };
        current.receipts += 1;
        if (entrant.entrantId === receipt.outcome.winnerEntrantId) current.wins += 1;
        current.harnessVersions.add(entrant.harnessVersionId);
        entrants.set(entrant.entrantId, current);
      }
    }
    return [...entrants.values()]
      .sort((left, right) => left.name.localeCompare(right.name))
      .map((entrant) => ({
        id: entrant.id,
        position: "—",
        name: entrant.name,
        kind: `${entrant.harnessVersions.size} content-bound harness version${entrant.harnessVersions.size === 1 ? "" : "s"}`,
        record: `${entrant.wins} reviewed win${entrant.wins === 1 ? "" : "s"} · not ranked`,
        metric: `${entrant.receipts}R`,
        verified: entrant.receipts,
      }));
  }

  function buildRivalryViews(rivalries, receipts) {
    const entrantNames = new Map();
    for (const receipt of receipts) {
      for (const entrant of receipt.entrants) entrantNames.set(entrant.entrantId, entrant.name);
    }
    return rivalries.map((rivalry) => {
      const wins = new Map(rivalry.entrantIds.map((entrantId) => [entrantId, 0]));
      for (const meeting of rivalry.meetings) wins.set(meeting.winnerEntrantId, wins.get(meeting.winnerEntrantId) + 1);
      const names = rivalry.entrantIds.map((entrantId) => entrantNames.get(entrantId) || "Unknown entrant");
      const lastMeeting = rivalry.meetings[rivalry.meetings.length - 1];
      return {
        rivalryId: rivalry.rivalryId,
        competition: gameLabel(rivalry.competition),
        title: names.join(" vs "),
        meetingCount: rivalry.meetingCount,
        record: rivalry.entrantIds.map((entrantId, index) => `${names[index]} ${wins.get(entrantId)}`).join(" · "),
        gameCount: new Set(rivalry.meetings.map((meeting) => meeting.game)).size,
        pendingRunbackCount: rivalry.meetings.filter((meeting) => meeting.runback.status === "unplayed_challenge").length,
        latestReceiptId: lastMeeting.receiptId,
        latestGame: gameLabel(lastMeeting.game),
        runbackStatus: "unplayed_challenge",
      };
    });
  }

  function validateQualificationBlueprint(blueprint) {
    requireValue(isObject(blueprint), "unsafe qualification preview: blueprint missing");
    requireValue(blueprint.localOnly === true, "unsafe qualification preview: blueprint must stay local only");
    requireValue(typeof blueprint.agentName === "string" && blueprint.agentName.trim().length > 0 && blueprint.agentName.trim().length <= 36, "unsafe qualification preview: invalid agent name");
    requireValue(ALLOWED_BASE_MODELS.has(blueprint.baseModel), "unsafe qualification preview: unknown demo base");
    requireValue(ALLOWED_HARNESS_STYLES.has(blueprint.harnessStyle), "unsafe qualification preview: unknown harness style");
    for (const field of ["strictValidation", "fallbackDisclosure", "humanCheckpoints"]) {
      requireValue(typeof blueprint[field] === "boolean", `unsafe qualification preview: ${field} must be boolean`);
    }
    return blueprint;
  }

  function buildQualificationPreview(blueprintInput, fixture, sourceMode) {
    const blueprint = validateQualificationBlueprint(blueprintInput);
    requireValue(sourceMode === "verified_corpus", "unsafe qualification preview: verified corpus required");
    requireValue(isObject(fixture) && fixture.previewAllowed === true && fixture.enabled === false, "unsafe qualification preview: fixture is not preview-only");
    requireValue(HEX64.test(fixture.id), "unsafe qualification preview: invalid fixture id");
    requireValue(isObject(fixture.game) && typeof fixture.game.name === "string" && fixture.game.version === "1", "unsafe qualification preview: game binding missing");
    requireValue(typeof fixture.rulesWeekId === "string" && fixture.rulesWeekId.length > 0 && HEX64.test(fixture.rulesDigest), "unsafe qualification preview: rules binding missing");
    requireValue(fixture.activationStatus === "proposed_not_activated" && fixture.fixtureStatus === "unplayed", "unsafe qualification preview: fixture activation drift");
    requireValue(fixture.resourceClass === PREVIEW_RESOURCE_CLASS, "unsafe qualification preview: resource class drift");

    const localGuardsReady = blueprint.strictValidation && blueprint.fallbackDisclosure;
    const readinessChecks = [
      { id: "local-blueprint", label: "Local-only blueprint", status: "ready", ready: true },
      { id: "strict-validation", label: "Strict move validation", status: blueprint.strictValidation ? "ready" : "needs attention", ready: blueprint.strictValidation },
      { id: "fallback-disclosure", label: "Fallback disclosure", status: blueprint.fallbackDisclosure ? "ready" : "needs attention", ready: blueprint.fallbackDisclosure },
      { id: "fixture-binding", label: "Pinned game and rules", status: "preview bound", ready: true },
    ];
    return {
      schemaVersion: QUALIFICATION_SCHEMA,
      previewOnly: true,
      qualificationStatus: "not_run",
      executionStatus: "disabled",
      publicationStatus: "not_requested",
      readiness: localGuardsReady ? "blueprint_ready_for_future_attempt" : "blueprint_needs_guard_changes",
      previewKey: [
        "local-preview",
        fixture.id,
        encodeURIComponent(blueprint.agentName.trim()),
        encodeURIComponent(blueprint.baseModel),
        encodeURIComponent(blueprint.harnessStyle),
        blueprint.strictValidation ? 1 : 0,
        blueprint.fallbackDisclosure ? 1 : 0,
        blueprint.humanCheckpoints ? 1 : 0,
      ].join(":"),
      blueprint: {
        agentName: blueprint.agentName.trim(),
        declaredBase: blueprint.baseModel,
        harnessStyle: blueprint.harnessStyle,
        localOnly: true,
      },
      fixture: {
        fixtureId: fixture.id,
        title: fixture.title,
        game: clone(fixture.game),
        rulesWeekId: fixture.rulesWeekId,
        rulesDigest: fixture.rulesDigest,
        activationStatus: fixture.activationStatus,
        status: fixture.fixtureStatus,
      },
      resourceClass: {
        id: PREVIEW_RESOURCE_CLASS,
        label: "Local preview · no compute",
        computeAllowed: false,
        networkAllowed: false,
      },
      readinessChecks,
      executionBlockers: ["qualification_not_run", "fixture_not_activated", "sanctioned_runner_not_bound"],
      attestations: {
        identity: false,
        model: false,
        provider: false,
        runtime: false,
        registry: false,
        publication: false,
      },
      boundary: "This deterministic preview binds a local blueprint to proposed game, rules, and no-compute resource metadata only. It does not qualify, execute, authenticate, attest, rank, publish, or spend.",
    };
  }

  function validateReceiptProofForLearning(proof, sourceMode) {
    requireValue(sourceMode === "verified_corpus", "unsafe receipt learning: verified corpus required");
    requireValue(isObject(proof) && HEX64.test(proof.receiptId), "unsafe receipt learning: reviewed receipt missing");
    requireValue(proof.replayVerdict === "PASS" && proof.publicationApproved === true, "unsafe receipt learning: reviewed proof required");
    requireValue(isObject(proof.game) && typeof proof.game.name === "string" && proof.game.version === "1", "unsafe receipt learning: game binding missing");
    requireValue(isObject(proof.moveSourceCounts), "unsafe receipt learning: evidence counts missing");
    for (const field of ["model", "scripted", "fallback", "other"]) {
      requireValue(nonNegativeInteger(proof.moveSourceCounts[field]), `unsafe receipt learning: invalid ${field} count`);
    }
    requireValue(isObject(proof.runback), "unsafe receipt learning: runback lineage missing");
    requireValue(proof.runback.parentReceiptId === proof.receiptId, "unsafe receipt learning: runback parent drift");
    requireValue(proof.runback.status === "unplayed_challenge", "unsafe receipt learning: runback already activated");
    requireValue(HEX64.test(proof.runback.fixtureId) && CHALLENGE_ID.test(proof.runback.challengeId), "unsafe receipt learning: runback identifiers missing");
    return proof;
  }

  function buildReceiptLearningAction(proofInput, sourceMode) {
    const proof = validateReceiptProofForLearning(proofInput, sourceMode);
    const counts = proof.moveSourceCounts;
    let observation;
    let recommendedDeltaId;
    if (counts.fallback > 0) {
      observation = `${counts.fallback} fallback move${counts.fallback === 1 ? "" : "s"} were disclosed in this reviewed receipt.`;
      recommendedDeltaId = "require_fallback_disclosure";
    } else if (counts.model > 0 && proof.modelAttested === false) {
      observation = `${counts.model} move${counts.model === 1 ? "" : "s"} carried a model-source label, while model identity remained unattested.`;
      recommendedDeltaId = "require_strict_validation";
    } else if (counts.scripted > 0) {
      observation = `${counts.scripted} scripted move${counts.scripted === 1 ? "" : "s"} formed a deterministic reference, not model evidence.`;
      recommendedDeltaId = "require_human_checkpoints";
    } else {
      observation = `${counts.other} move${counts.other === 1 ? "" : "s"} remained in the other/unattested evidence class.`;
      recommendedDeltaId = "require_fallback_disclosure";
    }
    return {
      schemaVersion: LEARNING_SCHEMA,
      status: "review_only",
      receipt: {
        receiptId: proof.receiptId,
        fixtureId: proof.fixtureId,
        headline: proof.headline,
        game: clone(proof.game),
        replayVerdict: proof.replayVerdict,
        evidenceLabel: proof.evidenceLabel,
        moveSourceCounts: clone(counts),
      },
      observation,
      recommendedDeltaId,
      allowedDeltas: clone(RUNBACK_DELTAS),
      runback: clone(proof.runback),
      boundary: "This learning action summarizes a reviewed receipt and offers local blueprint deltas. It does not infer hidden reasoning, prove model identity, award progress, or activate a runback.",
    };
  }

  function buildRunbackProposal(learningInput, blueprintInput, deltaId, sourceMode) {
    requireValue(sourceMode === "verified_corpus", "unsafe runback proposal: verified corpus required");
    requireValue(isObject(learningInput) && learningInput.schemaVersion === LEARNING_SCHEMA && learningInput.status === "review_only", "unsafe runback proposal: learning action missing");
    requireValue(isObject(learningInput.receipt) && HEX64.test(learningInput.receipt.receiptId), "unsafe runback proposal: parent receipt missing");
    requireValue(isObject(learningInput.runback) && learningInput.runback.parentReceiptId === learningInput.receipt.receiptId, "unsafe runback proposal: parent lineage drift");
    requireValue(learningInput.runback.status === "unplayed_challenge", "unsafe runback proposal: runback already activated");
    requireValue(HEX64.test(learningInput.runback.fixtureId) && CHALLENGE_ID.test(learningInput.runback.challengeId), "unsafe runback proposal: runback identifiers missing");
    const blueprint = validateQualificationBlueprint(blueprintInput);
    const delta = RUNBACK_DELTAS.find((candidate) => candidate.id === deltaId);
    requireValue(delta, "unsafe runback proposal: unknown blueprint delta");
    const currentValue = blueprint[delta.guardKey];
    const proposalKey = [
      "local-runback-v1",
      learningInput.receipt.receiptId,
      learningInput.runback.fixtureId,
      learningInput.runback.challengeId,
      encodeURIComponent(learningInput.receipt.game.name),
      learningInput.receipt.game.version,
      delta.id,
      currentValue ? 1 : 0,
      encodeURIComponent(blueprint.agentName.trim()),
      encodeURIComponent(blueprint.baseModel),
      encodeURIComponent(blueprint.harnessStyle),
    ].join(":");
    return {
      schemaVersion: RUNBACK_PROPOSAL_SCHEMA,
      proposalVersion: 1,
      proposalKey,
      runbackStatus: "unplayed_proposal",
      qualificationStatus: "not_run",
      executionStatus: "disabled",
      publicationStatus: "not_requested",
      parentReceipt: {
        receiptId: learningInput.receipt.receiptId,
        fixtureId: learningInput.receipt.fixtureId,
        replayVerdict: learningInput.receipt.replayVerdict,
      },
      runbackLineage: clone(learningInput.runback),
      gameBinding: clone(learningInput.receipt.game),
      rulesBinding: {
        status: "blocked_missing_explicit_rules_digest",
        rulesDigest: null,
        statement: RUNBACK_RULES_STATEMENT,
      },
      blueprint: {
        agentName: blueprint.agentName.trim(),
        declaredBase: blueprint.baseModel,
        harnessStyle: blueprint.harnessStyle,
        localOnly: true,
      },
      blueprintDelta: {
        id: delta.id,
        guardKey: delta.guardKey,
        label: delta.label,
        rationale: delta.rationale,
        from: currentValue,
        to: true,
        changeStatus: currentValue ? "already_declared" : "proposed_change",
      },
      executionBlockers: [...RUNBACK_EXECUTION_BLOCKERS],
      attestations: { identity: false, model: false, provider: false, runtime: false, registry: false, publication: false },
      boundary: RUNBACK_PROPOSAL_BOUNDARY,
    };
  }

  function validateRunbackProposal(proposalInput) {
    assertSafeKeys(proposalInput, "proposal");
    requireExactKeys(proposalInput, [
      "schemaVersion", "proposalVersion", "proposalKey", "runbackStatus", "qualificationStatus", "executionStatus", "publicationStatus",
      "parentReceipt", "runbackLineage", "gameBinding", "rulesBinding", "blueprint", "blueprintDelta", "executionBlockers", "attestations", "boundary",
    ], "proposal");
    requireValue(proposalInput.schemaVersion === RUNBACK_PROPOSAL_SCHEMA && proposalInput.proposalVersion === 1, "unsafe portable runback: proposal schema drift");
    requireValue(proposalInput.runbackStatus === "unplayed_proposal", "unsafe portable runback: proposal is not unplayed");
    requireValue(proposalInput.qualificationStatus === "not_run", "unsafe portable runback: qualification status drift");
    requireValue(proposalInput.executionStatus === "disabled", "unsafe portable runback: execution status drift");
    requireValue(proposalInput.publicationStatus === "not_requested", "unsafe portable runback: publication status drift");
    requireValue(proposalInput.boundary === RUNBACK_PROPOSAL_BOUNDARY, "unsafe portable runback: proposal boundary drift");

    requireExactKeys(proposalInput.parentReceipt, ["receiptId", "fixtureId", "replayVerdict"], "parent receipt");
    requireValue(HEX64.test(proposalInput.parentReceipt.receiptId) && HEX64.test(proposalInput.parentReceipt.fixtureId), "unsafe portable runback: parent receipt binding missing");
    requireValue(proposalInput.parentReceipt.replayVerdict === "PASS", "unsafe portable runback: parent replay was not verified");

    requireExactKeys(proposalInput.runbackLineage, ["challengeId", "fixtureId", "parentReceiptId", "status"], "runback lineage");
    requireValue(CHALLENGE_ID.test(proposalInput.runbackLineage.challengeId) && HEX64.test(proposalInput.runbackLineage.fixtureId), "unsafe portable runback: runback identifiers missing");
    requireValue(proposalInput.runbackLineage.parentReceiptId === proposalInput.parentReceipt.receiptId, "unsafe portable runback: runback parent drift");
    requireValue(proposalInput.runbackLineage.status === "unplayed_challenge", "unsafe portable runback: challenge is not unplayed");

    requireExactKeys(proposalInput.gameBinding, ["format", "name", "version"], "game binding");
    requireValue(typeof proposalInput.gameBinding.name === "string" && proposalInput.gameBinding.name.length > 0 && proposalInput.gameBinding.name.length <= 80, "unsafe portable runback: game name missing");
    requireValue(proposalInput.gameBinding.version === "1", "unsafe portable runback: game version drift");
    requireValue(proposalInput.gameBinding.format === null || (typeof proposalInput.gameBinding.format === "string" && proposalInput.gameBinding.format.length <= 80), "unsafe portable runback: game format drift");

    requireExactKeys(proposalInput.rulesBinding, ["status", "rulesDigest", "statement"], "rules binding");
    requireValue(proposalInput.rulesBinding.status === "blocked_missing_explicit_rules_digest" && proposalInput.rulesBinding.rulesDigest === null, "unsafe portable runback: rules blocker drift");
    requireValue(proposalInput.rulesBinding.statement === RUNBACK_RULES_STATEMENT, "unsafe portable runback: rules statement drift");

    requireExactKeys(proposalInput.blueprint, ["agentName", "declaredBase", "harnessStyle", "localOnly"], "blueprint");
    requireValue(typeof proposalInput.blueprint.agentName === "string" && proposalInput.blueprint.agentName.trim() === proposalInput.blueprint.agentName && proposalInput.blueprint.agentName.length > 0 && proposalInput.blueprint.agentName.length <= 36, "unsafe portable runback: agent name drift");
    requireValue(ALLOWED_BASE_MODELS.has(proposalInput.blueprint.declaredBase), "unsafe portable runback: unknown declared base");
    requireValue(ALLOWED_HARNESS_STYLES.has(proposalInput.blueprint.harnessStyle), "unsafe portable runback: unknown harness style");
    requireValue(proposalInput.blueprint.localOnly === true, "unsafe portable runback: blueprint escaped local boundary");

    requireExactKeys(proposalInput.blueprintDelta, ["id", "guardKey", "label", "rationale", "from", "to", "changeStatus"], "blueprint delta");
    const delta = RUNBACK_DELTAS.find((candidate) => candidate.id === proposalInput.blueprintDelta.id);
    requireValue(delta && proposalInput.blueprintDelta.guardKey === delta.guardKey && proposalInput.blueprintDelta.label === delta.label && proposalInput.blueprintDelta.rationale === delta.rationale, "unsafe portable runback: blueprint delta drift");
    requireValue(typeof proposalInput.blueprintDelta.from === "boolean" && proposalInput.blueprintDelta.to === true, "unsafe portable runback: blueprint change drift");
    requireValue(proposalInput.blueprintDelta.changeStatus === (proposalInput.blueprintDelta.from ? "already_declared" : "proposed_change"), "unsafe portable runback: blueprint change status drift");

    requireValue(Array.isArray(proposalInput.executionBlockers) && proposalInput.executionBlockers.length === RUNBACK_EXECUTION_BLOCKERS.length, "unsafe portable runback: execution blockers drift");
    requireValue(proposalInput.executionBlockers.every((blocker, index) => blocker === RUNBACK_EXECUTION_BLOCKERS[index]), "unsafe portable runback: execution blockers drift");
    requireExactKeys(proposalInput.attestations, ["identity", "model", "provider", "runtime", "registry", "publication"], "attestations");
    requireValue(Object.values(proposalInput.attestations).every((value) => value === false), "unsafe portable runback: attestation must remain false");

    const expectedProposalKey = [
      "local-runback-v1",
      proposalInput.parentReceipt.receiptId,
      proposalInput.runbackLineage.fixtureId,
      proposalInput.runbackLineage.challengeId,
      encodeURIComponent(proposalInput.gameBinding.name),
      proposalInput.gameBinding.version,
      proposalInput.blueprintDelta.id,
      proposalInput.blueprintDelta.from ? 1 : 0,
      encodeURIComponent(proposalInput.blueprint.agentName),
      encodeURIComponent(proposalInput.blueprint.declaredBase),
      encodeURIComponent(proposalInput.blueprint.harnessStyle),
    ].join(":");
    requireValue(proposalInput.proposalKey === expectedProposalKey, "unsafe portable runback: proposal key drift");
    return proposalInput;
  }

  async function createPortableRunbackEnvelope(proposalInput) {
    const proposal = clone(validateRunbackProposal(proposalInput));
    const payloadDigest = await sha256Hex(canonicalJSON(proposal));
    const envelope = {
      schemaVersion: PORTABLE_RUNBACK_SCHEMA,
      payload: proposal,
      integrity: { algorithm: "sha256", payloadDigest },
      boundary: PORTABLE_RUNBACK_BOUNDARY,
    };
    return { envelope: clone(envelope), serialized: canonicalJSON(envelope) };
  }

  async function verifyPortableRunbackEnvelope(serializedInput) {
    requireValue(typeof serializedInput === "string" && serializedInput.length > 0 && serializedInput.length <= PORTABLE_RUNBACK_MAX_LENGTH, "unsafe portable runback: input length rejected");
    let envelope;
    try {
      envelope = JSON.parse(serializedInput);
    } catch {
      throw new Error("unsafe portable runback: invalid JSON");
    }
    assertSafeKeys(envelope, "envelope");
    requireExactKeys(envelope, ["schemaVersion", "payload", "integrity", "boundary"], "envelope");
    requireValue(envelope.schemaVersion === PORTABLE_RUNBACK_SCHEMA, "unsafe portable runback: envelope schema drift");
    requireValue(envelope.boundary === PORTABLE_RUNBACK_BOUNDARY, "unsafe portable runback: envelope boundary drift");
    requireExactKeys(envelope.integrity, ["algorithm", "payloadDigest"], "integrity");
    requireValue(envelope.integrity.algorithm === "sha256" && HEX64.test(envelope.integrity.payloadDigest), "unsafe portable runback: integrity metadata drift");
    requireValue(serializedInput === canonicalJSON(envelope), "unsafe portable runback: envelope must use canonical JSON");
    const proposal = clone(validateRunbackProposal(envelope.payload));
    const computedDigest = await sha256Hex(canonicalJSON(proposal));
    requireValue(equalHex(computedDigest, envelope.integrity.payloadDigest), "unsafe portable runback: payload digest mismatch");
    return {
      schemaVersion: PORTABLE_RUNBACK_SCHEMA,
      verificationStatus: "verified_local_unplayed_proposal",
      payloadDigest: computedDigest,
      proposal,
      boundary: PORTABLE_RUNBACK_BOUNDARY,
    };
  }

  async function validateVerifiedPortableResult(resultInput) {
    assertSafeKeys(resultInput, "verified portable result");
    requireExactKeys(resultInput, ["schemaVersion", "verificationStatus", "payloadDigest", "proposal", "boundary"], "verified portable result");
    requireValue(resultInput.schemaVersion === PORTABLE_RUNBACK_SCHEMA, "unsafe portable review: verified schema drift");
    requireValue(resultInput.verificationStatus === "verified_local_unplayed_proposal", "unsafe portable review: proposal was not independently verified");
    requireValue(HEX64.test(resultInput.payloadDigest), "unsafe portable review: envelope digest missing");
    requireValue(resultInput.boundary === PORTABLE_RUNBACK_BOUNDARY, "unsafe portable review: verification boundary drift");
    const proposal = clone(validateRunbackProposal(resultInput.proposal));
    const computedDigest = await sha256Hex(canonicalJSON(proposal));
    requireValue(equalHex(computedDigest, resultInput.payloadDigest), "unsafe portable review: verified payload digest mismatch");
    return { proposal, payloadDigest: computedDigest };
  }

  function reviewProposalBinding(verified) {
    return {
      envelopeDigest: verified.payloadDigest,
      proposalKey: verified.proposal.proposalKey,
      parentReceiptId: verified.proposal.parentReceipt.receiptId,
      challengeId: verified.proposal.runbackLineage.challengeId,
      runbackFixtureId: verified.proposal.runbackLineage.fixtureId,
    };
  }

  function proposedBlueprintRevision(verified, binding, sequence) {
    return {
      status: "proposed_uncommitted_revision",
      revisionKey: `local-blueprint-revision-v1:${binding.envelopeDigest}:${sequence}:${encodeURIComponent(verified.proposal.blueprintDelta.id)}`,
      parentProposalKey: binding.proposalKey,
      agentName: verified.proposal.blueprint.agentName,
      declaredBase: verified.proposal.blueprint.declaredBase,
      harnessStyle: verified.proposal.blueprint.harnessStyle,
      acceptedDelta: clone(verified.proposal.blueprintDelta),
      localOnly: true,
      committed: false,
    };
  }

  async function validatePortableRunbackReview(recordInput, verified, previousDigest, expectedSequence) {
    assertSafeKeys(recordInput, "portable review");
    requireExactKeys(recordInput, [
      "schemaVersion", "reviewVersion", "sequence", "reviewStatus", "decision", "reasonCode", "reviewer", "proposalBinding",
      "previousReviewDigest", "blueprintRevision", "blockers", "attestations", "boundary", "reviewDigest",
    ], "portable review");
    requireValue(recordInput.schemaVersion === PORTABLE_REVIEW_SCHEMA && recordInput.reviewVersion === 1, "unsafe portable review: schema drift");
    requireValue(recordInput.sequence === expectedSequence, "unsafe portable review: sequence drift");
    requireValue(recordInput.reviewStatus === "private_local_review", "unsafe portable review: private status drift");
    const allowedReasons = PORTABLE_REVIEW_REASONS[recordInput.decision];
    requireValue(Array.isArray(allowedReasons), "unsafe portable review: unknown decision");
    requireValue(allowedReasons.includes(recordInput.reasonCode), "unsafe portable review: decision reason drift");

    requireExactKeys(recordInput.reviewer, ["label", "identityAttested", "localOnly"], "reviewer");
    requireValue(typeof recordInput.reviewer.label === "string" && recordInput.reviewer.label.trim() === recordInput.reviewer.label && recordInput.reviewer.label.length > 0 && recordInput.reviewer.label.length <= 36, "unsafe portable review: reviewer label drift");
    requireValue(recordInput.reviewer.identityAttested === false && recordInput.reviewer.localOnly === true, "unsafe portable review: reviewer boundary drift");

    const expectedBinding = reviewProposalBinding(verified);
    requireExactKeys(recordInput.proposalBinding, ["envelopeDigest", "proposalKey", "parentReceiptId", "challengeId", "runbackFixtureId"], "review proposal binding");
    for (const key of Object.keys(expectedBinding)) requireValue(recordInput.proposalBinding[key] === expectedBinding[key], `unsafe portable review: ${key} drift`);
    requireValue(recordInput.previousReviewDigest === previousDigest, "unsafe portable review: append-only chain drift");

    if (recordInput.decision === "accept_for_blueprint_revision") {
      requireExactKeys(recordInput.blueprintRevision, [
        "status", "revisionKey", "parentProposalKey", "agentName", "declaredBase", "harnessStyle", "acceptedDelta", "localOnly", "committed",
      ], "blueprint revision");
      const expectedRevision = proposedBlueprintRevision(verified, expectedBinding, expectedSequence);
      requireValue(canonicalJSON(recordInput.blueprintRevision) === canonicalJSON(expectedRevision), "unsafe portable review: proposed blueprint revision drift");
    } else {
      requireValue(recordInput.blueprintRevision === null, "unsafe portable review: non-accept decision created a blueprint revision");
    }

    requireValue(Array.isArray(recordInput.blockers) && recordInput.blockers.length === PORTABLE_REVIEW_BLOCKERS.length, "unsafe portable review: blockers drift");
    requireValue(recordInput.blockers.every((blocker, index) => blocker === PORTABLE_REVIEW_BLOCKERS[index]), "unsafe portable review: blockers drift");
    requireExactKeys(recordInput.attestations, [
      "identity", "model", "provider", "runtime", "rules", "qualification", "execution", "registry", "ranking", "publication", "spending",
    ], "review attestations");
    requireValue(Object.values(recordInput.attestations).every((value) => value === false), "unsafe portable review: attestation must remain false");
    requireValue(recordInput.boundary === PORTABLE_REVIEW_BOUNDARY, "unsafe portable review: boundary drift");
    requireValue(HEX64.test(recordInput.reviewDigest), "unsafe portable review: review digest missing");
    const digestPayload = clone(recordInput);
    delete digestPayload.reviewDigest;
    const computedDigest = await sha256Hex(canonicalJSON(digestPayload));
    requireValue(equalHex(computedDigest, recordInput.reviewDigest), "unsafe portable review: review digest mismatch");
    return clone(recordInput);
  }

  async function verifyPortableRunbackReviewJournal(reviewInput, verifiedPortableInput) {
    requireValue(Array.isArray(reviewInput) && reviewInput.length <= PORTABLE_REVIEW_MAX_RECORDS, "unsafe portable review: journal length rejected");
    assertSafeKeys(reviewInput, "portable review journal");
    const verified = await validateVerifiedPortableResult(verifiedPortableInput);
    const reviews = [];
    let previousDigest = null;
    for (let index = 0; index < reviewInput.length; index += 1) {
      const review = await validatePortableRunbackReview(reviewInput[index], verified, previousDigest, index + 1);
      reviews.push(review);
      previousDigest = review.reviewDigest;
    }
    return {
      schemaVersion: PORTABLE_REVIEW_SCHEMA,
      verificationStatus: "verified_private_local_review_journal",
      envelopeDigest: verified.payloadDigest,
      reviewCount: reviews.length,
      latestReviewDigest: previousDigest,
      reviews,
      boundary: PORTABLE_REVIEW_BOUNDARY,
    };
  }

  async function appendPortableRunbackReview(verifiedPortableInput, reviewInput, existingReviewInput = []) {
    assertSafeKeys(reviewInput, "portable review input");
    requireExactKeys(reviewInput, ["reviewerLabel", "decision", "reasonCode"], "portable review input");
    requireValue(typeof reviewInput.reviewerLabel === "string" && reviewInput.reviewerLabel.trim() === reviewInput.reviewerLabel && reviewInput.reviewerLabel.length > 0 && reviewInput.reviewerLabel.length <= 36, "unsafe portable review: reviewer label drift");
    const allowedReasons = PORTABLE_REVIEW_REASONS[reviewInput.decision];
    requireValue(Array.isArray(allowedReasons), "unsafe portable review: unknown decision");
    requireValue(allowedReasons.includes(reviewInput.reasonCode), "unsafe portable review: decision reason drift");
    const verified = await validateVerifiedPortableResult(verifiedPortableInput);
    const journal = await verifyPortableRunbackReviewJournal(existingReviewInput, verifiedPortableInput);
    requireValue(journal.reviewCount < PORTABLE_REVIEW_MAX_RECORDS, "unsafe portable review: journal length rejected");
    const sequence = journal.reviewCount + 1;
    const proposalBinding = reviewProposalBinding(verified);
    const record = {
      schemaVersion: PORTABLE_REVIEW_SCHEMA,
      reviewVersion: 1,
      sequence,
      reviewStatus: "private_local_review",
      decision: reviewInput.decision,
      reasonCode: reviewInput.reasonCode,
      reviewer: { label: reviewInput.reviewerLabel, identityAttested: false, localOnly: true },
      proposalBinding,
      previousReviewDigest: journal.latestReviewDigest,
      blueprintRevision: reviewInput.decision === "accept_for_blueprint_revision" ? proposedBlueprintRevision(verified, proposalBinding, sequence) : null,
      blockers: [...PORTABLE_REVIEW_BLOCKERS],
      attestations: {
        identity: false, model: false, provider: false, runtime: false, rules: false, qualification: false,
        execution: false, registry: false, ranking: false, publication: false, spending: false,
      },
      boundary: PORTABLE_REVIEW_BOUNDARY,
    };
    const reviewDigest = await sha256Hex(canonicalJSON(record));
    const sealed = { ...record, reviewDigest };
    await verifyPortableRunbackReviewJournal([...journal.reviews, sealed], verifiedPortableInput);
    return clone(sealed);
  }

  function proposedCorrectionBlueprintRevision(verified, binding, targetReview, sequence) {
    return {
      status: "proposed_uncommitted_correction_revision",
      revisionKey: `local-blueprint-correction-v1:${binding.envelopeDigest}:${targetReview.reviewDigest}:${sequence}:${encodeURIComponent(verified.proposal.blueprintDelta.id)}`,
      parentProposalKey: binding.proposalKey,
      targetReviewDigest: targetReview.reviewDigest,
      agentName: verified.proposal.blueprint.agentName,
      declaredBase: verified.proposal.blueprint.declaredBase,
      harnessStyle: verified.proposal.blueprint.harnessStyle,
      acceptedDelta: clone(verified.proposal.blueprintDelta),
      localOnly: true,
      committed: false,
    };
  }

  async function validatePortableRunbackReviewCorrection(recordInput, verified, reviewByDigest, previousDigest, latestByTarget, expectedSequence) {
    assertSafeKeys(recordInput, "portable review correction");
    requireExactKeys(recordInput, [
      "schemaVersion", "correctionVersion", "sequence", "correctionStatus", "action", "reasonCode", "correctedDecision",
      "reviewer", "proposalBinding", "targetReview", "previousCorrectionDigest", "supersedesCorrectionDigest",
      "blueprintRevision", "blockers", "attestations", "boundary", "correctionDigest",
    ], "portable review correction");
    requireValue(recordInput.schemaVersion === PORTABLE_REVIEW_CORRECTION_SCHEMA && recordInput.correctionVersion === 1, "unsafe portable review correction: schema drift");
    requireValue(recordInput.sequence === expectedSequence, "unsafe portable review correction: sequence drift");
    requireValue(recordInput.correctionStatus === "private_local_correction", "unsafe portable review correction: private status drift");
    const allowedReasons = PORTABLE_REVIEW_CORRECTION_REASONS[recordInput.action];
    requireValue(Array.isArray(allowedReasons), "unsafe portable review correction: unknown action");
    requireValue(allowedReasons.includes(recordInput.reasonCode), "unsafe portable review correction: action reason drift");

    requireExactKeys(recordInput.reviewer, ["label", "identityAttested", "localOnly"], "correction reviewer");
    requireValue(typeof recordInput.reviewer.label === "string" && recordInput.reviewer.label.trim() === recordInput.reviewer.label && recordInput.reviewer.label.length > 0 && recordInput.reviewer.label.length <= 36, "unsafe portable review correction: reviewer label drift");
    requireValue(recordInput.reviewer.identityAttested === false && recordInput.reviewer.localOnly === true, "unsafe portable review correction: reviewer boundary drift");

    const expectedBinding = reviewProposalBinding(verified);
    requireExactKeys(recordInput.proposalBinding, ["envelopeDigest", "proposalKey", "parentReceiptId", "challengeId", "runbackFixtureId"], "correction proposal binding");
    for (const key of Object.keys(expectedBinding)) requireValue(recordInput.proposalBinding[key] === expectedBinding[key], `unsafe portable review correction: ${key} drift`);

    requireExactKeys(recordInput.targetReview, ["sequence", "reviewDigest"], "correction target review");
    requireValue(Number.isInteger(recordInput.targetReview.sequence) && recordInput.targetReview.sequence > 0, "unsafe portable review correction: target sequence drift");
    requireValue(HEX64.test(recordInput.targetReview.reviewDigest), "unsafe portable review correction: target digest drift");
    const targetReview = reviewByDigest.get(recordInput.targetReview.reviewDigest);
    requireValue(targetReview && targetReview.sequence === recordInput.targetReview.sequence, "unsafe portable review correction: immutable target review missing");

    requireValue(recordInput.previousCorrectionDigest === previousDigest, "unsafe portable review correction: append-only chain drift");
    const superseded = latestByTarget.get(targetReview.reviewDigest) || null;
    requireValue(recordInput.supersedesCorrectionDigest === (superseded?.correctionDigest || null), "unsafe portable review correction: supersession link drift");
    const currentDecision = superseded
      ? (superseded.action === "correct_decision" ? superseded.correctedDecision : null)
      : targetReview.decision;

    if (recordInput.action === "correct_decision") {
      requireValue(Array.isArray(PORTABLE_REVIEW_REASONS[recordInput.correctedDecision]), "unsafe portable review correction: corrected decision drift");
      requireValue(recordInput.correctedDecision !== currentDecision, "unsafe portable review correction: corrected decision is unchanged");
    } else {
      requireValue(recordInput.correctedDecision === null, "unsafe portable review correction: withdrawal decision drift");
      requireValue(currentDecision !== null, "unsafe portable review correction: review already withdrawn");
    }

    if (recordInput.action === "correct_decision" && recordInput.correctedDecision === "accept_for_blueprint_revision") {
      requireExactKeys(recordInput.blueprintRevision, [
        "status", "revisionKey", "parentProposalKey", "targetReviewDigest", "agentName", "declaredBase", "harnessStyle",
        "acceptedDelta", "localOnly", "committed",
      ], "correction blueprint revision");
      const expectedRevision = proposedCorrectionBlueprintRevision(verified, expectedBinding, targetReview, expectedSequence);
      requireValue(canonicalJSON(recordInput.blueprintRevision) === canonicalJSON(expectedRevision), "unsafe portable review correction: proposed correction revision drift");
    } else {
      requireValue(recordInput.blueprintRevision === null, "unsafe portable review correction: correction created an unauthorized revision");
    }

    requireValue(Array.isArray(recordInput.blockers) && recordInput.blockers.length === PORTABLE_REVIEW_BLOCKERS.length, "unsafe portable review correction: blockers drift");
    requireValue(recordInput.blockers.every((blocker, index) => blocker === PORTABLE_REVIEW_BLOCKERS[index]), "unsafe portable review correction: blockers drift");
    requireExactKeys(recordInput.attestations, [
      "identity", "model", "provider", "runtime", "rules", "qualification", "execution", "registry", "ranking", "publication", "spending",
    ], "correction attestations");
    requireValue(Object.values(recordInput.attestations).every((value) => value === false), "unsafe portable review correction: attestation must remain false");
    requireValue(recordInput.boundary === PORTABLE_REVIEW_CORRECTION_BOUNDARY, "unsafe portable review correction: boundary drift");
    requireValue(HEX64.test(recordInput.correctionDigest), "unsafe portable review correction: correction digest missing");
    const digestPayload = clone(recordInput);
    delete digestPayload.correctionDigest;
    const computedDigest = await sha256Hex(canonicalJSON(digestPayload));
    requireValue(equalHex(computedDigest, recordInput.correctionDigest), "unsafe portable review correction: correction digest mismatch");
    return clone(recordInput);
  }

  async function verifyPortableRunbackReviewCorrectionJournal(correctionInput, verifiedPortableInput, reviewInput) {
    requireValue(Array.isArray(correctionInput) && correctionInput.length <= PORTABLE_REVIEW_CORRECTION_MAX_RECORDS, "unsafe portable review correction: journal length rejected");
    assertSafeKeys(correctionInput, "portable review correction journal");
    const verified = await validateVerifiedPortableResult(verifiedPortableInput);
    const reviewJournal = await verifyPortableRunbackReviewJournal(reviewInput, verifiedPortableInput);
    const reviewByDigest = new Map(reviewJournal.reviews.map((review) => [review.reviewDigest, review]));
    const latestByTarget = new Map();
    const correctionCounts = new Map();
    const corrections = [];
    let previousDigest = null;
    for (let index = 0; index < correctionInput.length; index += 1) {
      const correction = await validatePortableRunbackReviewCorrection(
        correctionInput[index], verified, reviewByDigest, previousDigest, latestByTarget, index + 1,
      );
      corrections.push(correction);
      previousDigest = correction.correctionDigest;
      latestByTarget.set(correction.targetReview.reviewDigest, correction);
      correctionCounts.set(correction.targetReview.reviewDigest, (correctionCounts.get(correction.targetReview.reviewDigest) || 0) + 1);
    }
    const effectiveReviews = reviewJournal.reviews.map((review) => {
      const correction = latestByTarget.get(review.reviewDigest) || null;
      return {
        reviewSequence: review.sequence,
        reviewDigest: review.reviewDigest,
        originalDecision: review.decision,
        effectiveStatus: correction
          ? (correction.action === "withdraw_review" ? "withdrawn_by_private_correction" : "corrected_by_private_correction")
          : "original_private_review",
        effectiveDecision: correction
          ? (correction.action === "correct_decision" ? correction.correctedDecision : null)
          : review.decision,
        latestCorrectionDigest: correction?.correctionDigest || null,
        correctionCount: correctionCounts.get(review.reviewDigest) || 0,
      };
    });
    return {
      schemaVersion: PORTABLE_REVIEW_CORRECTION_SCHEMA,
      verificationStatus: "verified_private_local_review_correction_journal",
      envelopeDigest: verified.payloadDigest,
      reviewHeadDigest: reviewJournal.latestReviewDigest,
      correctionCount: corrections.length,
      latestCorrectionDigest: previousDigest,
      corrections,
      effectiveReviews,
      boundary: PORTABLE_REVIEW_CORRECTION_BOUNDARY,
    };
  }

  async function appendPortableRunbackReviewCorrection(verifiedPortableInput, reviewInput, correctionInput, existingCorrectionInput = []) {
    assertSafeKeys(correctionInput, "portable review correction input");
    requireExactKeys(correctionInput, ["reviewerLabel", "targetReviewDigest", "action", "correctedDecision", "reasonCode"], "portable review correction input");
    requireValue(typeof correctionInput.reviewerLabel === "string" && correctionInput.reviewerLabel.trim() === correctionInput.reviewerLabel && correctionInput.reviewerLabel.length > 0 && correctionInput.reviewerLabel.length <= 36, "unsafe portable review correction: reviewer label drift");
    requireValue(HEX64.test(correctionInput.targetReviewDigest), "unsafe portable review correction: target digest drift");
    const allowedReasons = PORTABLE_REVIEW_CORRECTION_REASONS[correctionInput.action];
    requireValue(Array.isArray(allowedReasons) && allowedReasons.includes(correctionInput.reasonCode), "unsafe portable review correction: action reason drift");
    if (correctionInput.action === "correct_decision") {
      requireValue(Array.isArray(PORTABLE_REVIEW_REASONS[correctionInput.correctedDecision]), "unsafe portable review correction: corrected decision drift");
    } else {
      requireValue(correctionInput.action === "withdraw_review" && correctionInput.correctedDecision === null, "unsafe portable review correction: withdrawal decision drift");
    }

    const verified = await validateVerifiedPortableResult(verifiedPortableInput);
    const reviewJournal = await verifyPortableRunbackReviewJournal(reviewInput, verifiedPortableInput);
    const correctionJournal = await verifyPortableRunbackReviewCorrectionJournal(existingCorrectionInput, verifiedPortableInput, reviewJournal.reviews);
    requireValue(correctionJournal.correctionCount < PORTABLE_REVIEW_CORRECTION_MAX_RECORDS, "unsafe portable review correction: journal length rejected");
    const targetReview = reviewJournal.reviews.find((review) => review.reviewDigest === correctionInput.targetReviewDigest);
    requireValue(targetReview, "unsafe portable review correction: immutable target review missing");
    const priorForTarget = [...correctionJournal.corrections].reverse().find((correction) => correction.targetReview.reviewDigest === targetReview.reviewDigest) || null;
    const sequence = correctionJournal.correctionCount + 1;
    const proposalBinding = reviewProposalBinding(verified);
    const record = {
      schemaVersion: PORTABLE_REVIEW_CORRECTION_SCHEMA,
      correctionVersion: 1,
      sequence,
      correctionStatus: "private_local_correction",
      action: correctionInput.action,
      reasonCode: correctionInput.reasonCode,
      correctedDecision: correctionInput.correctedDecision,
      reviewer: { label: correctionInput.reviewerLabel, identityAttested: false, localOnly: true },
      proposalBinding,
      targetReview: { sequence: targetReview.sequence, reviewDigest: targetReview.reviewDigest },
      previousCorrectionDigest: correctionJournal.latestCorrectionDigest,
      supersedesCorrectionDigest: priorForTarget?.correctionDigest || null,
      blueprintRevision: correctionInput.action === "correct_decision" && correctionInput.correctedDecision === "accept_for_blueprint_revision"
        ? proposedCorrectionBlueprintRevision(verified, proposalBinding, targetReview, sequence)
        : null,
      blockers: [...PORTABLE_REVIEW_BLOCKERS],
      attestations: {
        identity: false, model: false, provider: false, runtime: false, rules: false, qualification: false,
        execution: false, registry: false, ranking: false, publication: false, spending: false,
      },
      boundary: PORTABLE_REVIEW_CORRECTION_BOUNDARY,
    };
    const correctionDigest = await sha256Hex(canonicalJSON(record));
    const sealed = { ...record, correctionDigest };
    await verifyPortableRunbackReviewCorrectionJournal([...correctionJournal.corrections, sealed], verifiedPortableInput, reviewJournal.reviews);
    return clone(sealed);
  }

  async function createPortableRunbackReviewExchange(serializedProposalInput, reviewInput) {
    const verifiedProposal = await verifyPortableRunbackEnvelope(serializedProposalInput);
    const journal = await verifyPortableRunbackReviewJournal(reviewInput, verifiedProposal);
    const proposalEnvelope = JSON.parse(serializedProposalInput);
    const payload = {
      proposalEnvelope: clone(proposalEnvelope),
      reviews: clone(journal.reviews),
    };
    const payloadDigest = await sha256Hex(canonicalJSON(payload));
    const packet = {
      schemaVersion: PORTABLE_REVIEW_EXCHANGE_SCHEMA,
      exchangeVersion: 1,
      payload,
      integrity: {
        algorithm: "sha256",
        payloadDigest,
        proposalPayloadDigest: verifiedProposal.payloadDigest,
        reviewHeadDigest: journal.latestReviewDigest,
      },
      boundary: PORTABLE_REVIEW_EXCHANGE_BOUNDARY,
    };
    const serialized = canonicalJSON(packet);
    requireValue(serialized.length <= PORTABLE_REVIEW_EXCHANGE_MAX_LENGTH, "unsafe portable review exchange: packet length rejected");
    return { packet: clone(packet), serialized };
  }

  async function verifyPortableRunbackReviewExchange(serializedInput) {
    requireValue(typeof serializedInput === "string" && serializedInput.length > 0 && serializedInput.length <= PORTABLE_REVIEW_EXCHANGE_MAX_LENGTH, "unsafe portable review exchange: input length rejected");
    let packet;
    try {
      packet = JSON.parse(serializedInput);
    } catch {
      throw new Error("unsafe portable review exchange: invalid JSON");
    }
    assertSafeKeys(packet, "portable review exchange");
    requireExactKeys(packet, ["schemaVersion", "exchangeVersion", "payload", "integrity", "boundary"], "portable review exchange");
    requireValue(packet.schemaVersion === PORTABLE_REVIEW_EXCHANGE_SCHEMA && packet.exchangeVersion === 1, "unsafe portable review exchange: schema drift");
    requireValue(packet.boundary === PORTABLE_REVIEW_EXCHANGE_BOUNDARY, "unsafe portable review exchange: boundary drift");
    requireValue(serializedInput === canonicalJSON(packet), "unsafe portable review exchange: packet must use canonical JSON");

    requireExactKeys(packet.payload, ["proposalEnvelope", "reviews"], "portable review exchange payload");
    requireExactKeys(packet.integrity, ["algorithm", "payloadDigest", "proposalPayloadDigest", "reviewHeadDigest"], "portable review exchange integrity");
    requireValue(packet.integrity.algorithm === "sha256", "unsafe portable review exchange: integrity algorithm drift");
    requireValue(HEX64.test(packet.integrity.payloadDigest) && HEX64.test(packet.integrity.proposalPayloadDigest), "unsafe portable review exchange: integrity digest drift");
    requireValue(packet.integrity.reviewHeadDigest === null || HEX64.test(packet.integrity.reviewHeadDigest), "unsafe portable review exchange: review head digest drift");

    const proposalSerialized = canonicalJSON(packet.payload.proposalEnvelope);
    const proposalVerification = await verifyPortableRunbackEnvelope(proposalSerialized);
    const journal = await verifyPortableRunbackReviewJournal(packet.payload.reviews, proposalVerification);
    requireValue(equalHex(proposalVerification.payloadDigest, packet.integrity.proposalPayloadDigest), "unsafe portable review exchange: proposal digest binding mismatch");
    requireValue(journal.latestReviewDigest === packet.integrity.reviewHeadDigest, "unsafe portable review exchange: review head binding mismatch");
    const computedPayloadDigest = await sha256Hex(canonicalJSON(packet.payload));
    requireValue(equalHex(computedPayloadDigest, packet.integrity.payloadDigest), "unsafe portable review exchange: payload digest mismatch");

    return {
      schemaVersion: PORTABLE_REVIEW_EXCHANGE_SCHEMA,
      verificationStatus: "verified_private_local_review_exchange",
      packetDigest: computedPayloadDigest,
      proposalSerialized,
      proposalVerification,
      journal,
      boundary: PORTABLE_REVIEW_EXCHANGE_BOUNDARY,
    };
  }

  async function createPortableRunbackReviewCorrectionExchange(serializedProposalInput, reviewInput, correctionInput) {
    const reviewExchange = await createPortableRunbackReviewExchange(serializedProposalInput, reviewInput);
    const reviewVerification = await verifyPortableRunbackReviewExchange(reviewExchange.serialized);
    const correctionJournal = await verifyPortableRunbackReviewCorrectionJournal(
      correctionInput, reviewVerification.proposalVerification, reviewVerification.journal.reviews,
    );
    const payload = {
      reviewExchangePacket: clone(reviewExchange.packet),
      corrections: clone(correctionJournal.corrections),
    };
    const payloadDigest = await sha256Hex(canonicalJSON(payload));
    const packet = {
      schemaVersion: PORTABLE_REVIEW_CORRECTION_EXCHANGE_SCHEMA,
      exchangeVersion: 1,
      payload,
      integrity: {
        algorithm: "sha256",
        payloadDigest,
        reviewExchangePayloadDigest: reviewExchange.packet.integrity.payloadDigest,
        correctionHeadDigest: correctionJournal.latestCorrectionDigest,
      },
      boundary: PORTABLE_REVIEW_CORRECTION_EXCHANGE_BOUNDARY,
    };
    const serialized = canonicalJSON(packet);
    requireValue(serialized.length <= PORTABLE_REVIEW_CORRECTION_EXCHANGE_MAX_LENGTH, "unsafe portable review correction exchange: packet length rejected");
    return { packet: clone(packet), serialized };
  }

  async function verifyPortableRunbackReviewCorrectionExchange(serializedInput) {
    requireValue(typeof serializedInput === "string" && serializedInput.length > 0 && serializedInput.length <= PORTABLE_REVIEW_CORRECTION_EXCHANGE_MAX_LENGTH, "unsafe portable review correction exchange: input length rejected");
    let packet;
    try {
      packet = JSON.parse(serializedInput);
    } catch {
      throw new Error("unsafe portable review correction exchange: invalid JSON");
    }
    assertSafeKeys(packet, "portable review correction exchange");
    requireExactKeys(packet, ["schemaVersion", "exchangeVersion", "payload", "integrity", "boundary"], "portable review correction exchange");
    requireValue(packet.schemaVersion === PORTABLE_REVIEW_CORRECTION_EXCHANGE_SCHEMA && packet.exchangeVersion === 1, "unsafe portable review correction exchange: schema drift");
    requireValue(packet.boundary === PORTABLE_REVIEW_CORRECTION_EXCHANGE_BOUNDARY, "unsafe portable review correction exchange: boundary drift");
    requireValue(serializedInput === canonicalJSON(packet), "unsafe portable review correction exchange: packet must use canonical JSON");
    requireExactKeys(packet.payload, ["reviewExchangePacket", "corrections"], "portable review correction exchange payload");
    requireExactKeys(packet.integrity, ["algorithm", "payloadDigest", "reviewExchangePayloadDigest", "correctionHeadDigest"], "portable review correction exchange integrity");
    requireValue(packet.integrity.algorithm === "sha256", "unsafe portable review correction exchange: integrity algorithm drift");
    requireValue(HEX64.test(packet.integrity.payloadDigest) && HEX64.test(packet.integrity.reviewExchangePayloadDigest), "unsafe portable review correction exchange: integrity digest drift");
    requireValue(packet.integrity.correctionHeadDigest === null || HEX64.test(packet.integrity.correctionHeadDigest), "unsafe portable review correction exchange: correction head digest drift");

    const reviewExchangeSerialized = canonicalJSON(packet.payload.reviewExchangePacket);
    const reviewExchangeVerification = await verifyPortableRunbackReviewExchange(reviewExchangeSerialized);
    const correctionJournal = await verifyPortableRunbackReviewCorrectionJournal(
      packet.payload.corrections,
      reviewExchangeVerification.proposalVerification,
      reviewExchangeVerification.journal.reviews,
    );
    requireValue(equalHex(reviewExchangeVerification.packetDigest, packet.integrity.reviewExchangePayloadDigest), "unsafe portable review correction exchange: review exchange digest binding mismatch");
    requireValue(correctionJournal.latestCorrectionDigest === packet.integrity.correctionHeadDigest, "unsafe portable review correction exchange: correction head binding mismatch");
    const computedPayloadDigest = await sha256Hex(canonicalJSON(packet.payload));
    requireValue(equalHex(computedPayloadDigest, packet.integrity.payloadDigest), "unsafe portable review correction exchange: payload digest mismatch");

    return {
      schemaVersion: PORTABLE_REVIEW_CORRECTION_EXCHANGE_SCHEMA,
      verificationStatus: "verified_private_local_review_correction_exchange",
      packetDigest: computedPayloadDigest,
      reviewExchangeSerialized,
      proposalSerialized: reviewExchangeVerification.proposalSerialized,
      proposalVerification: reviewExchangeVerification.proposalVerification,
      journal: reviewExchangeVerification.journal,
      correctionJournal,
      boundary: PORTABLE_REVIEW_CORRECTION_EXCHANGE_BOUNDARY,
    };
  }

  function comparisonState(effectiveReview) {
    return {
      reviewSequence: effectiveReview.reviewSequence,
      originalDecision: effectiveReview.originalDecision,
      effectiveStatus: effectiveReview.effectiveStatus,
      effectiveDecision: effectiveReview.effectiveDecision,
      latestCorrectionDigest: effectiveReview.latestCorrectionDigest,
      correctionCount: effectiveReview.correctionCount,
    };
  }

  function comparisonPacketSummary(verification) {
    return {
      packetDigest: verification.packetDigest,
      reviewHeadDigest: verification.journal.latestReviewDigest,
      correctionHeadDigest: verification.correctionJournal.latestCorrectionDigest,
      reviewCount: verification.journal.reviewCount,
      correctionCount: verification.correctionJournal.correctionCount,
    };
  }

  function buildPortablePrivateReviewComparison(leftVerification, rightVerification) {
    requireValue(
      equalHex(leftVerification.proposalVerification.payloadDigest, rightVerification.proposalVerification.payloadDigest),
      "unsafe portable private review comparison: proposal mismatch",
    );
    const leftByDigest = new Map(leftVerification.correctionJournal.effectiveReviews.map((review) => [review.reviewDigest, review]));
    const rightByDigest = new Map(rightVerification.correctionJournal.effectiveReviews.map((review) => [review.reviewDigest, review]));
    const reviewDigests = [...new Set([...leftByDigest.keys(), ...rightByDigest.keys()])].sort();
    requireValue(reviewDigests.length <= PORTABLE_REVIEW_COMPARISON_MAX_ENTRIES, "unsafe portable private review comparison: entry count rejected");
    const entries = reviewDigests.map((reviewDigest) => {
      const leftReview = leftByDigest.get(reviewDigest) || null;
      const rightReview = rightByDigest.get(reviewDigest) || null;
      const left = leftReview ? comparisonState(leftReview) : null;
      const right = rightReview ? comparisonState(rightReview) : null;
      let presence;
      let classification;
      if (left && right) {
        presence = "both";
        classification = canonicalJSON(left) === canonicalJSON(right)
          ? "identical_effective_state"
          : "changed_effective_state";
      } else if (left) {
        presence = "left_only";
        classification = "left_only_review";
      } else {
        presence = "right_only";
        classification = "right_only_review";
      }
      return { reviewDigest, presence, classification, left, right };
    });
    const summary = {
      distinctReviewCount: entries.length,
      sharedReviewCount: entries.filter((entry) => entry.presence === "both").length,
      leftOnlyReviewCount: entries.filter((entry) => entry.presence === "left_only").length,
      rightOnlyReviewCount: entries.filter((entry) => entry.presence === "right_only").length,
      identicalEffectiveStateCount: entries.filter((entry) => entry.classification === "identical_effective_state").length,
      changedEffectiveStateCount: entries.filter((entry) => entry.classification === "changed_effective_state").length,
    };
    return {
      proposalPayloadDigest: leftVerification.proposalVerification.payloadDigest,
      left: comparisonPacketSummary(leftVerification),
      right: comparisonPacketSummary(rightVerification),
      entries,
      summary,
      authority: {
        identity: false,
        merge: false,
        resolution: false,
        rules: false,
        qualification: false,
        execution: false,
        registry: false,
        ranking: false,
        publication: false,
        spending: false,
      },
    };
  }

  async function createPortablePrivateReviewComparison(leftSerializedInput, rightSerializedInput) {
    const leftVerification = await verifyPortableRunbackReviewCorrectionExchange(leftSerializedInput);
    const rightVerification = await verifyPortableRunbackReviewCorrectionExchange(rightSerializedInput);
    const comparison = buildPortablePrivateReviewComparison(leftVerification, rightVerification);
    const payload = {
      leftCorrectionExchangePacket: JSON.parse(leftSerializedInput),
      rightCorrectionExchangePacket: JSON.parse(rightSerializedInput),
      comparison,
    };
    const payloadDigest = await sha256Hex(canonicalJSON(payload));
    const packet = {
      schemaVersion: PORTABLE_REVIEW_COMPARISON_SCHEMA,
      comparisonVersion: 1,
      payload,
      integrity: {
        algorithm: "sha256",
        payloadDigest,
        leftPacketDigest: leftVerification.packetDigest,
        rightPacketDigest: rightVerification.packetDigest,
        proposalPayloadDigest: comparison.proposalPayloadDigest,
      },
      boundary: PORTABLE_REVIEW_COMPARISON_BOUNDARY,
    };
    const serialized = canonicalJSON(packet);
    requireValue(serialized.length <= PORTABLE_REVIEW_COMPARISON_MAX_LENGTH, "unsafe portable private review comparison: packet length rejected");
    return { packet: clone(packet), serialized };
  }

  async function verifyPortablePrivateReviewComparison(serializedInput) {
    requireValue(typeof serializedInput === "string" && serializedInput.length > 0 && serializedInput.length <= PORTABLE_REVIEW_COMPARISON_MAX_LENGTH, "unsafe portable private review comparison: input length rejected");
    let packet;
    try {
      packet = JSON.parse(serializedInput);
    } catch {
      throw new Error("unsafe portable private review comparison: invalid JSON");
    }
    assertSafeKeys(packet, "portable private review comparison", 0, { nodes: 0 }, PORTABLE_REVIEW_COMPARISON_NODE_LIMIT);
    requireExactKeys(packet, ["schemaVersion", "comparisonVersion", "payload", "integrity", "boundary"], "portable private review comparison");
    requireValue(packet.schemaVersion === PORTABLE_REVIEW_COMPARISON_SCHEMA && packet.comparisonVersion === 1, "unsafe portable private review comparison: schema drift");
    requireValue(packet.boundary === PORTABLE_REVIEW_COMPARISON_BOUNDARY, "unsafe portable private review comparison: boundary drift");
    requireValue(serializedInput === canonicalJSON(packet), "unsafe portable private review comparison: packet must use canonical JSON");
    requireExactKeys(packet.payload, ["leftCorrectionExchangePacket", "rightCorrectionExchangePacket", "comparison"], "portable private review comparison payload");
    requireExactKeys(packet.integrity, ["algorithm", "payloadDigest", "leftPacketDigest", "rightPacketDigest", "proposalPayloadDigest"], "portable private review comparison integrity");
    requireValue(packet.integrity.algorithm === "sha256", "unsafe portable private review comparison: integrity algorithm drift");
    requireValue(
      HEX64.test(packet.integrity.payloadDigest)
        && HEX64.test(packet.integrity.leftPacketDigest)
        && HEX64.test(packet.integrity.rightPacketDigest)
        && HEX64.test(packet.integrity.proposalPayloadDigest),
      "unsafe portable private review comparison: integrity digest drift",
    );

    const leftSerialized = canonicalJSON(packet.payload.leftCorrectionExchangePacket);
    const rightSerialized = canonicalJSON(packet.payload.rightCorrectionExchangePacket);
    const leftVerification = await verifyPortableRunbackReviewCorrectionExchange(leftSerialized);
    const rightVerification = await verifyPortableRunbackReviewCorrectionExchange(rightSerialized);
    const expectedComparison = buildPortablePrivateReviewComparison(leftVerification, rightVerification);
    requireValue(canonicalJSON(packet.payload.comparison) === canonicalJSON(expectedComparison), "unsafe portable private review comparison: comparison projection mismatch");
    requireValue(equalHex(leftVerification.packetDigest, packet.integrity.leftPacketDigest), "unsafe portable private review comparison: left packet digest binding mismatch");
    requireValue(equalHex(rightVerification.packetDigest, packet.integrity.rightPacketDigest), "unsafe portable private review comparison: right packet digest binding mismatch");
    requireValue(equalHex(expectedComparison.proposalPayloadDigest, packet.integrity.proposalPayloadDigest), "unsafe portable private review comparison: proposal digest binding mismatch");
    const computedPayloadDigest = await sha256Hex(canonicalJSON(packet.payload));
    requireValue(equalHex(computedPayloadDigest, packet.integrity.payloadDigest), "unsafe portable private review comparison: payload digest mismatch");
    return {
      schemaVersion: PORTABLE_REVIEW_COMPARISON_SCHEMA,
      verificationStatus: "verified_private_local_review_comparison",
      packetDigest: computedPayloadDigest,
      leftSerialized,
      rightSerialized,
      leftVerification,
      rightVerification,
      comparison: clone(expectedComparison),
      boundary: PORTABLE_REVIEW_COMPARISON_BOUNDARY,
    };
  }

  function privateReviewLearningSide(packetRole, state) {
    if (!state) return null;
    return {
      packetRole,
      originalDecision: state.originalDecision,
      effectiveStatus: state.effectiveStatus,
      effectiveDecision: state.effectiveDecision,
      latestCorrectionDigest: state.latestCorrectionDigest,
      correctionCount: state.correctionCount,
    };
  }

  function privateReviewLearningPacketSource(packetRole, packetSummary) {
    return {
      packetRole,
      correctionExchangePacketDigest: packetSummary.packetDigest,
      reviewHeadDigest: packetSummary.reviewHeadDigest,
      correctionHeadDigest: packetSummary.correctionHeadDigest,
      reviewCount: packetSummary.reviewCount,
      correctionCount: packetSummary.correctionCount,
    };
  }

  function buildPortablePrivateReviewLearning(comparisonVerification) {
    requireValue(
      isObject(comparisonVerification)
        && comparisonVerification.schemaVersion === PORTABLE_REVIEW_COMPARISON_SCHEMA
        && comparisonVerification.verificationStatus === "verified_private_local_review_comparison",
      "unsafe private review learning: verified comparison required",
    );
    const comparison = comparisonVerification.comparison;
    requireValue(comparison.entries.length <= PRIVATE_REVIEW_LEARNING_MAX_ENTRIES, "unsafe private review learning: entry count rejected");
    const lessons = comparison.entries.map((entry) => {
      const lessonId = PRIVATE_REVIEW_CLASS_LESSON[entry.classification];
      const lesson = PRIVATE_REVIEW_INSPECTION_LESSONS[lessonId];
      requireValue(lesson, "unsafe private review learning: unsupported comparison class");
      return {
        reviewDigest: entry.reviewDigest,
        presence: entry.presence,
        classification: entry.classification,
        lessonId,
        lessonLabel: lesson.label,
        inspectionGuidance: lesson.guidance,
        left: privateReviewLearningSide("packet_a", entry.left),
        right: privateReviewLearningSide("packet_b", entry.right),
      };
    });
    const lessonCount = (lessonId) => lessons.filter((entry) => entry.lessonId === lessonId).length;
    return {
      sourceDigests: {
        comparisonPacketDigest: comparisonVerification.packetDigest,
        proposalPayloadDigest: comparison.proposalPayloadDigest,
        left: privateReviewLearningPacketSource("packet_a", comparison.left),
        right: privateReviewLearningPacketSource("packet_b", comparison.right),
      },
      lessons,
      summary: {
        entryCount: lessons.length,
        inspectEvidenceCount: lessonCount("inspect_evidence"),
        inspectRulesBindingCount: lessonCount("inspect_rules_binding"),
        inspectCorrectionLineageCount: lessonCount("inspect_correction_lineage"),
      },
      authority: {
        consensus: false,
        approval: false,
        progress: false,
        blueprintAdoption: false,
        identity: false,
        merge: false,
        resolution: false,
        rules: false,
        qualification: false,
        execution: false,
        registry: false,
        ranking: false,
        publication: false,
        spending: false,
        provider: false,
      },
    };
  }

  async function createPortablePrivateReviewLearning(serializedComparisonInput) {
    const comparisonVerification = await verifyPortablePrivateReviewComparison(serializedComparisonInput);
    const learning = buildPortablePrivateReviewLearning(comparisonVerification);
    const payload = {
      comparisonReceipt: JSON.parse(serializedComparisonInput),
      learning,
    };
    const payloadDigest = await sha256Hex(canonicalJSON(payload));
    const packet = {
      schemaVersion: PRIVATE_REVIEW_LEARNING_SCHEMA,
      learningVersion: 1,
      payload,
      integrity: {
        algorithm: "sha256",
        payloadDigest,
        comparisonPacketDigest: comparisonVerification.packetDigest,
        leftPacketDigest: learning.sourceDigests.left.correctionExchangePacketDigest,
        rightPacketDigest: learning.sourceDigests.right.correctionExchangePacketDigest,
        proposalPayloadDigest: learning.sourceDigests.proposalPayloadDigest,
      },
      boundary: PRIVATE_REVIEW_LEARNING_BOUNDARY,
    };
    const serialized = canonicalJSON(packet);
    requireValue(serialized.length <= PRIVATE_REVIEW_LEARNING_MAX_LENGTH, "unsafe private review learning: packet length rejected");
    return { packet: clone(packet), serialized };
  }

  async function verifyPortablePrivateReviewLearning(serializedInput) {
    requireValue(typeof serializedInput === "string" && serializedInput.length > 0 && serializedInput.length <= PRIVATE_REVIEW_LEARNING_MAX_LENGTH, "unsafe private review learning: input length rejected");
    let packet;
    try {
      packet = JSON.parse(serializedInput);
    } catch {
      throw new Error("unsafe private review learning: invalid JSON");
    }
    assertSafeKeys(packet, "private review learning", 0, { nodes: 0 }, PRIVATE_REVIEW_LEARNING_NODE_LIMIT);
    requireExactKeys(packet, ["schemaVersion", "learningVersion", "payload", "integrity", "boundary"], "private review learning");
    requireValue(packet.schemaVersion === PRIVATE_REVIEW_LEARNING_SCHEMA && packet.learningVersion === 1, "unsafe private review learning: schema drift");
    requireValue(packet.boundary === PRIVATE_REVIEW_LEARNING_BOUNDARY, "unsafe private review learning: boundary drift");
    requireValue(serializedInput === canonicalJSON(packet), "unsafe private review learning: packet must use canonical JSON");
    requireExactKeys(packet.payload, ["comparisonReceipt", "learning"], "private review learning payload");
    requireExactKeys(packet.integrity, ["algorithm", "payloadDigest", "comparisonPacketDigest", "leftPacketDigest", "rightPacketDigest", "proposalPayloadDigest"], "private review learning integrity");
    requireValue(packet.integrity.algorithm === "sha256", "unsafe private review learning: integrity algorithm drift");
    requireValue(
      HEX64.test(packet.integrity.payloadDigest)
        && HEX64.test(packet.integrity.comparisonPacketDigest)
        && HEX64.test(packet.integrity.leftPacketDigest)
        && HEX64.test(packet.integrity.rightPacketDigest)
        && HEX64.test(packet.integrity.proposalPayloadDigest),
      "unsafe private review learning: integrity digest drift",
    );

    const comparisonSerialized = canonicalJSON(packet.payload.comparisonReceipt);
    const comparisonVerification = await verifyPortablePrivateReviewComparison(comparisonSerialized);
    const expectedLearning = buildPortablePrivateReviewLearning(comparisonVerification);
    requireValue(canonicalJSON(packet.payload.learning) === canonicalJSON(expectedLearning), "unsafe private review learning: learning projection mismatch");
    requireValue(equalHex(comparisonVerification.packetDigest, packet.integrity.comparisonPacketDigest), "unsafe private review learning: comparison packet digest binding mismatch");
    requireValue(equalHex(expectedLearning.sourceDigests.left.correctionExchangePacketDigest, packet.integrity.leftPacketDigest), "unsafe private review learning: left packet digest binding mismatch");
    requireValue(equalHex(expectedLearning.sourceDigests.right.correctionExchangePacketDigest, packet.integrity.rightPacketDigest), "unsafe private review learning: right packet digest binding mismatch");
    requireValue(equalHex(expectedLearning.sourceDigests.proposalPayloadDigest, packet.integrity.proposalPayloadDigest), "unsafe private review learning: proposal digest binding mismatch");
    const computedPayloadDigest = await sha256Hex(canonicalJSON(packet.payload));
    requireValue(equalHex(computedPayloadDigest, packet.integrity.payloadDigest), "unsafe private review learning: payload digest mismatch");
    return {
      schemaVersion: PRIVATE_REVIEW_LEARNING_SCHEMA,
      verificationStatus: "verified_private_local_review_learning",
      packetDigest: computedPayloadDigest,
      comparisonSerialized,
      comparisonVerification,
      learning: clone(expectedLearning),
      boundary: PRIVATE_REVIEW_LEARNING_BOUNDARY,
    };
  }

  function privateBlueprintDeltaAuthority() {
    return {
      correctness: false,
      consensus: false,
      approval: false,
      progress: false,
      blueprintAdoption: false,
      identity: false,
      merge: false,
      resolution: false,
      rules: false,
      qualification: false,
      execution: false,
      registry: false,
      ranking: false,
      publication: false,
      spending: false,
      provider: false,
    };
  }

  function buildPortablePrivateBlueprintDelta(learningVerification, selectedReviewDigest) {
    requireValue(
      isObject(learningVerification)
        && learningVerification.schemaVersion === PRIVATE_REVIEW_LEARNING_SCHEMA
        && learningVerification.verificationStatus === "verified_private_local_review_learning",
      "unsafe private blueprint delta: verified learning required",
    );
    requireValue(typeof selectedReviewDigest === "string" && HEX64.test(selectedReviewDigest), "unsafe private blueprint delta: selected review digest rejected");
    const lesson = learningVerification.learning.lessons.find((candidate) => candidate.reviewDigest === selectedReviewDigest);
    requireValue(lesson, "unsafe private blueprint delta: selected lesson missing");
    const deltaId = PRIVATE_REVIEW_LESSON_DELTA[lesson.lessonId];
    const delta = RUNBACK_DELTAS.find((candidate) => candidate.id === deltaId);
    requireValue(delta, "unsafe private blueprint delta: lesson delta unavailable");

    const leftProposalVerification = learningVerification.comparisonVerification.leftVerification.proposalVerification;
    const rightProposalVerification = learningVerification.comparisonVerification.rightVerification.proposalVerification;
    requireValue(
      equalHex(leftProposalVerification.payloadDigest, rightProposalVerification.payloadDigest)
        && equalHex(leftProposalVerification.payloadDigest, learningVerification.learning.sourceDigests.proposalPayloadDigest),
      "unsafe private blueprint delta: parent proposal digest mismatch",
    );
    const parentProposal = leftProposalVerification.proposal;
    requireValue(canonicalJSON(parentProposal) === canonicalJSON(rightProposalVerification.proposal), "unsafe private blueprint delta: parent proposal mismatch");
    const parentCarriesSelectedGuard = parentProposal.blueprintDelta.id === delta.id;
    const currentValue = parentCarriesSelectedGuard ? parentProposal.blueprintDelta.from : null;
    const currentValueStatus = parentCarriesSelectedGuard ? "carried_by_parent_proposal" : "not_carried_by_parent_proposal";
    const changeStatus = currentValue === true
      ? "already_declared_requirement"
      : currentValue === false
        ? "proposed_change"
        : "proposed_requirement_only";
    const proposalKey = [
      "private-inspection-blueprint-delta-v1",
      learningVerification.packetDigest,
      leftProposalVerification.payloadDigest,
      selectedReviewDigest,
      lesson.lessonId,
      delta.id,
      currentValueStatus,
      currentValue === null ? "unknown" : currentValue ? 1 : 0,
    ].join(":");
    return {
      proposalStatus: "proposed_uncommitted_guard_delta",
      proposalKey,
      selectedLesson: {
        reviewDigest: lesson.reviewDigest,
        presence: lesson.presence,
        classification: lesson.classification,
        lessonId: lesson.lessonId,
        lessonLabel: lesson.lessonLabel,
        deltaId: delta.id,
      },
      parentProposalBinding: {
        proposalPayloadDigest: leftProposalVerification.payloadDigest,
        proposalKey: parentProposal.proposalKey,
        parentReceiptId: parentProposal.parentReceipt.receiptId,
        challengeId: parentProposal.runbackLineage.challengeId,
        runbackFixtureId: parentProposal.runbackLineage.fixtureId,
      },
      packetRoles: { left: "packet_a", right: "packet_b" },
      sourceDigests: clone(learningVerification.learning.sourceDigests),
      blueprintIdentity: {
        agentName: parentProposal.blueprint.agentName,
        declaredBase: parentProposal.blueprint.declaredBase,
        harnessStyle: parentProposal.blueprint.harnessStyle,
        localOnly: true,
      },
      guardDelta: {
        id: delta.id,
        guardKey: delta.guardKey,
        label: delta.label,
        rationale: delta.rationale,
        currentValue,
        currentValueStatus,
        targetValue: true,
        changeStatus,
      },
      state: {
        committed: false,
        played: false,
        qualificationStatus: "not_run",
        executionStatus: "disabled",
        publicationStatus: "not_requested",
      },
      blockers: [...PRIVATE_BLUEPRINT_DELTA_BLOCKERS],
      authority: privateBlueprintDeltaAuthority(),
    };
  }

  async function createPortablePrivateBlueprintDelta(serializedLearningInput, selectedReviewDigest) {
    const learningVerification = await verifyPortablePrivateReviewLearning(serializedLearningInput);
    const proposal = buildPortablePrivateBlueprintDelta(learningVerification, selectedReviewDigest);
    const payload = {
      learningReceipt: JSON.parse(serializedLearningInput),
      proposal,
    };
    const payloadDigest = await sha256Hex(canonicalJSON(payload));
    const sourceDigests = proposal.sourceDigests;
    const packet = {
      schemaVersion: PRIVATE_BLUEPRINT_DELTA_SCHEMA,
      proposalVersion: 1,
      payload,
      integrity: {
        algorithm: "sha256",
        payloadDigest,
        learningPacketDigest: learningVerification.packetDigest,
        comparisonPacketDigest: sourceDigests.comparisonPacketDigest,
        parentProposalPayloadDigest: sourceDigests.proposalPayloadDigest,
        leftPacketDigest: sourceDigests.left.correctionExchangePacketDigest,
        rightPacketDigest: sourceDigests.right.correctionExchangePacketDigest,
        selectedReviewDigest,
      },
      boundary: PRIVATE_BLUEPRINT_DELTA_BOUNDARY,
    };
    const serialized = canonicalJSON(packet);
    requireValue(serialized.length <= PRIVATE_BLUEPRINT_DELTA_MAX_LENGTH, "unsafe private blueprint delta: packet length rejected");
    return { packet: clone(packet), serialized };
  }

  async function verifyPortablePrivateBlueprintDelta(serializedInput) {
    requireValue(typeof serializedInput === "string" && serializedInput.length > 0 && serializedInput.length <= PRIVATE_BLUEPRINT_DELTA_MAX_LENGTH, "unsafe private blueprint delta: input length rejected");
    let packet;
    try {
      packet = JSON.parse(serializedInput);
    } catch {
      throw new Error("unsafe private blueprint delta: invalid JSON");
    }
    assertSafeKeys(packet, "private blueprint delta", 0, { nodes: 0 }, PRIVATE_BLUEPRINT_DELTA_NODE_LIMIT);
    requireExactKeys(packet, ["schemaVersion", "proposalVersion", "payload", "integrity", "boundary"], "private blueprint delta");
    requireValue(packet.schemaVersion === PRIVATE_BLUEPRINT_DELTA_SCHEMA && packet.proposalVersion === 1, "unsafe private blueprint delta: schema drift");
    requireValue(packet.boundary === PRIVATE_BLUEPRINT_DELTA_BOUNDARY, "unsafe private blueprint delta: boundary drift");
    requireValue(serializedInput === canonicalJSON(packet), "unsafe private blueprint delta: packet must use canonical JSON");
    requireExactKeys(packet.payload, ["learningReceipt", "proposal"], "private blueprint delta payload");
    requireExactKeys(packet.integrity, [
      "algorithm", "payloadDigest", "learningPacketDigest", "comparisonPacketDigest", "parentProposalPayloadDigest",
      "leftPacketDigest", "rightPacketDigest", "selectedReviewDigest",
    ], "private blueprint delta integrity");
    requireValue(packet.integrity.algorithm === "sha256", "unsafe private blueprint delta: integrity algorithm drift");
    for (const key of [
      "payloadDigest", "learningPacketDigest", "comparisonPacketDigest", "parentProposalPayloadDigest",
      "leftPacketDigest", "rightPacketDigest", "selectedReviewDigest",
    ]) requireValue(HEX64.test(packet.integrity[key]), `unsafe private blueprint delta: ${key} drift`);

    const learningSerialized = canonicalJSON(packet.payload.learningReceipt);
    const learningVerification = await verifyPortablePrivateReviewLearning(learningSerialized);
    const expectedProposal = buildPortablePrivateBlueprintDelta(learningVerification, packet.integrity.selectedReviewDigest);
    requireValue(canonicalJSON(packet.payload.proposal) === canonicalJSON(expectedProposal), "unsafe private blueprint delta: proposal projection mismatch");
    const sourceDigests = expectedProposal.sourceDigests;
    requireValue(equalHex(learningVerification.packetDigest, packet.integrity.learningPacketDigest), "unsafe private blueprint delta: learning packet digest binding mismatch");
    requireValue(equalHex(sourceDigests.comparisonPacketDigest, packet.integrity.comparisonPacketDigest), "unsafe private blueprint delta: comparison packet digest binding mismatch");
    requireValue(equalHex(sourceDigests.proposalPayloadDigest, packet.integrity.parentProposalPayloadDigest), "unsafe private blueprint delta: parent proposal digest binding mismatch");
    requireValue(equalHex(sourceDigests.left.correctionExchangePacketDigest, packet.integrity.leftPacketDigest), "unsafe private blueprint delta: left packet digest binding mismatch");
    requireValue(equalHex(sourceDigests.right.correctionExchangePacketDigest, packet.integrity.rightPacketDigest), "unsafe private blueprint delta: right packet digest binding mismatch");
    const computedPayloadDigest = await sha256Hex(canonicalJSON(packet.payload));
    requireValue(equalHex(computedPayloadDigest, packet.integrity.payloadDigest), "unsafe private blueprint delta: payload digest mismatch");
    return {
      schemaVersion: PRIVATE_BLUEPRINT_DELTA_SCHEMA,
      verificationStatus: "verified_private_local_blueprint_delta_proposal",
      packetDigest: computedPayloadDigest,
      learningSerialized,
      learningVerification,
      proposal: clone(expectedProposal),
      boundary: PRIVATE_BLUEPRINT_DELTA_BOUNDARY,
    };
  }

  function privateBlueprintDeltaReviewProposalBinding(deltaVerification) {
    const proposal = deltaVerification.proposal;
    return {
      proposalPacketDigest: deltaVerification.packetDigest,
      proposalKey: proposal.proposalKey,
      learningPacketDigest: deltaVerification.learningVerification.packetDigest,
      comparisonPacketDigest: proposal.sourceDigests.comparisonPacketDigest,
      parentProposalPayloadDigest: proposal.parentProposalBinding.proposalPayloadDigest,
      selectedReviewDigest: proposal.selectedLesson.reviewDigest,
      guardDeltaId: proposal.guardDelta.id,
    };
  }

  function proposedPrivateBlueprintDeltaRevisionCandidate(deltaVerification, binding) {
    const proposal = deltaVerification.proposal;
    return {
      status: "proposed_uncommitted_local_revision_candidate",
      revisionKey: [
        "private-guard-revision-candidate-v1",
        binding.proposalPacketDigest,
        binding.selectedReviewDigest,
        encodeURIComponent(binding.guardDeltaId),
      ].join(":"),
      parentProposalKey: proposal.parentProposalBinding.proposalKey,
      parentProposalPayloadDigest: binding.parentProposalPayloadDigest,
      selectedReviewDigest: binding.selectedReviewDigest,
      guardDelta: clone(proposal.guardDelta),
      localOnly: true,
      committed: false,
      adopted: false,
      played: false,
    };
  }

  async function buildPortablePrivateBlueprintDeltaReviewRecord(deltaVerification, reviewInput) {
    requireValue(
      isObject(deltaVerification)
        && deltaVerification.schemaVersion === PRIVATE_BLUEPRINT_DELTA_SCHEMA
        && deltaVerification.verificationStatus === "verified_private_local_blueprint_delta_proposal",
      "unsafe private blueprint delta review: verified proposal required",
    );
    assertSafeKeys(reviewInput, "private blueprint delta review input");
    requireExactKeys(reviewInput, ["reviewerLabel", "decision", "reasonCode"], "private blueprint delta review input");
    requireValue(
      typeof reviewInput.reviewerLabel === "string"
        && reviewInput.reviewerLabel.trim() === reviewInput.reviewerLabel
        && reviewInput.reviewerLabel.length > 0
        && reviewInput.reviewerLabel.length <= 36,
      "unsafe private blueprint delta review: reviewer label drift",
    );
    const allowedReasons = PRIVATE_BLUEPRINT_DELTA_REVIEW_REASONS[reviewInput.decision];
    requireValue(Array.isArray(allowedReasons), "unsafe private blueprint delta review: unknown decision");
    requireValue(allowedReasons.includes(reviewInput.reasonCode), "unsafe private blueprint delta review: decision reason drift");
    const proposalBinding = privateBlueprintDeltaReviewProposalBinding(deltaVerification);
    const review = {
      reviewStatus: "private_local_guard_proposal_review",
      decision: reviewInput.decision,
      reasonCode: reviewInput.reasonCode,
      reviewer: {
        label: reviewInput.reviewerLabel,
        identityAttested: false,
        localOnly: true,
      },
      proposalBinding,
      localRevisionCandidate: reviewInput.decision === "accept_for_revision"
        ? proposedPrivateBlueprintDeltaRevisionCandidate(deltaVerification, proposalBinding)
        : null,
      blockers: [...PRIVATE_BLUEPRINT_DELTA_REVIEW_BLOCKERS],
      authority: privateBlueprintDeltaAuthority(),
      boundary: PRIVATE_BLUEPRINT_DELTA_REVIEW_BOUNDARY,
    };
    const reviewDigest = await sha256Hex(canonicalJSON(review));
    return { ...review, reviewDigest };
  }

  async function createPortablePrivateBlueprintDeltaReview(serializedProposalInput, reviewInput) {
    const deltaVerification = await verifyPortablePrivateBlueprintDelta(serializedProposalInput);
    const review = await buildPortablePrivateBlueprintDeltaReviewRecord(deltaVerification, reviewInput);
    const payload = {
      blueprintDeltaProposal: JSON.parse(serializedProposalInput),
      review,
    };
    const payloadDigest = await sha256Hex(canonicalJSON(payload));
    const sourceDigests = deltaVerification.proposal.sourceDigests;
    const packet = {
      schemaVersion: PRIVATE_BLUEPRINT_DELTA_REVIEW_SCHEMA,
      reviewVersion: 1,
      payload,
      integrity: {
        algorithm: "sha256",
        payloadDigest,
        proposalPacketDigest: deltaVerification.packetDigest,
        learningPacketDigest: deltaVerification.learningVerification.packetDigest,
        comparisonPacketDigest: sourceDigests.comparisonPacketDigest,
        parentProposalPayloadDigest: sourceDigests.proposalPayloadDigest,
        leftPacketDigest: sourceDigests.left.correctionExchangePacketDigest,
        rightPacketDigest: sourceDigests.right.correctionExchangePacketDigest,
        selectedReviewDigest: deltaVerification.proposal.selectedLesson.reviewDigest,
        reviewDigest: review.reviewDigest,
      },
      boundary: PRIVATE_BLUEPRINT_DELTA_REVIEW_BOUNDARY,
    };
    const serialized = canonicalJSON(packet);
    requireValue(serialized.length <= PRIVATE_BLUEPRINT_DELTA_REVIEW_MAX_LENGTH, "unsafe private blueprint delta review: packet length rejected");
    return { packet: clone(packet), serialized };
  }

  async function verifyPortablePrivateBlueprintDeltaReview(serializedInput) {
    requireValue(
      typeof serializedInput === "string"
        && serializedInput.length > 0
        && serializedInput.length <= PRIVATE_BLUEPRINT_DELTA_REVIEW_MAX_LENGTH,
      "unsafe private blueprint delta review: input length rejected",
    );
    let packet;
    try {
      packet = JSON.parse(serializedInput);
    } catch {
      throw new Error("unsafe private blueprint delta review: invalid JSON");
    }
    assertSafeKeys(packet, "private blueprint delta review", 0, { nodes: 0 }, PRIVATE_BLUEPRINT_DELTA_REVIEW_NODE_LIMIT);
    requireExactKeys(packet, ["schemaVersion", "reviewVersion", "payload", "integrity", "boundary"], "private blueprint delta review");
    requireValue(packet.schemaVersion === PRIVATE_BLUEPRINT_DELTA_REVIEW_SCHEMA && packet.reviewVersion === 1, "unsafe private blueprint delta review: schema drift");
    requireValue(packet.boundary === PRIVATE_BLUEPRINT_DELTA_REVIEW_BOUNDARY, "unsafe private blueprint delta review: boundary drift");
    requireValue(serializedInput === canonicalJSON(packet), "unsafe private blueprint delta review: packet must use canonical JSON");
    requireExactKeys(packet.payload, ["blueprintDeltaProposal", "review"], "private blueprint delta review payload");
    requireExactKeys(packet.integrity, [
      "algorithm", "payloadDigest", "proposalPacketDigest", "learningPacketDigest", "comparisonPacketDigest",
      "parentProposalPayloadDigest", "leftPacketDigest", "rightPacketDigest", "selectedReviewDigest", "reviewDigest",
    ], "private blueprint delta review integrity");
    requireValue(packet.integrity.algorithm === "sha256", "unsafe private blueprint delta review: integrity algorithm drift");
    for (const key of [
      "payloadDigest", "proposalPacketDigest", "learningPacketDigest", "comparisonPacketDigest", "parentProposalPayloadDigest",
      "leftPacketDigest", "rightPacketDigest", "selectedReviewDigest", "reviewDigest",
    ]) requireValue(HEX64.test(packet.integrity[key]), `unsafe private blueprint delta review: ${key} drift`);

    const blueprintDeltaSerialized = canonicalJSON(packet.payload.blueprintDeltaProposal);
    const deltaVerification = await verifyPortablePrivateBlueprintDelta(blueprintDeltaSerialized);
    const review = packet.payload.review;
    requireValue(isObject(review), "unsafe private blueprint delta review: review drift");
    requireValue(isObject(review.reviewer), "unsafe private blueprint delta review: reviewer drift");
    const expectedReview = await buildPortablePrivateBlueprintDeltaReviewRecord(deltaVerification, {
      reviewerLabel: review.reviewer.label,
      decision: review.decision,
      reasonCode: review.reasonCode,
    });
    requireValue(canonicalJSON(review) === canonicalJSON(expectedReview), "unsafe private blueprint delta review: review projection mismatch");
    const sourceDigests = deltaVerification.proposal.sourceDigests;
    requireValue(equalHex(deltaVerification.packetDigest, packet.integrity.proposalPacketDigest), "unsafe private blueprint delta review: proposal packet digest binding mismatch");
    requireValue(equalHex(deltaVerification.learningVerification.packetDigest, packet.integrity.learningPacketDigest), "unsafe private blueprint delta review: learning packet digest binding mismatch");
    requireValue(equalHex(sourceDigests.comparisonPacketDigest, packet.integrity.comparisonPacketDigest), "unsafe private blueprint delta review: comparison packet digest binding mismatch");
    requireValue(equalHex(sourceDigests.proposalPayloadDigest, packet.integrity.parentProposalPayloadDigest), "unsafe private blueprint delta review: parent proposal digest binding mismatch");
    requireValue(equalHex(sourceDigests.left.correctionExchangePacketDigest, packet.integrity.leftPacketDigest), "unsafe private blueprint delta review: left packet digest binding mismatch");
    requireValue(equalHex(sourceDigests.right.correctionExchangePacketDigest, packet.integrity.rightPacketDigest), "unsafe private blueprint delta review: right packet digest binding mismatch");
    requireValue(equalHex(deltaVerification.proposal.selectedLesson.reviewDigest, packet.integrity.selectedReviewDigest), "unsafe private blueprint delta review: selected review digest binding mismatch");
    requireValue(equalHex(expectedReview.reviewDigest, packet.integrity.reviewDigest), "unsafe private blueprint delta review: review digest binding mismatch");
    const computedPayloadDigest = await sha256Hex(canonicalJSON(packet.payload));
    requireValue(equalHex(computedPayloadDigest, packet.integrity.payloadDigest), "unsafe private blueprint delta review: payload digest mismatch");
    return {
      schemaVersion: PRIVATE_BLUEPRINT_DELTA_REVIEW_SCHEMA,
      verificationStatus: "verified_private_local_blueprint_delta_review",
      packetDigest: computedPayloadDigest,
      blueprintDeltaSerialized,
      blueprintDeltaVerification: deltaVerification,
      review: clone(expectedReview),
      boundary: PRIVATE_BLUEPRINT_DELTA_REVIEW_BOUNDARY,
    };
  }

  function adaptArenaReadModel(modelInput, demoInput) {
    const model = validateArenaReadModel(modelInput);
    const demo = clone(validateDemoFixture(demoInput));
    const boundary = model.truthBoundary.statement;
    const runbackByReceipt = new Map(model.rivalries.flatMap((rivalry) => rivalry.meetings.map((meeting) => [meeting.receiptId, meeting.runback])));
    const proofs = model.receipts.map((receipt) => proofFromReceipt(receipt, boundary, runbackByReceipt.get(receipt.receiptId)));
    const proofById = new Map(proofs.map((proof) => [proof.receiptId, proof]));
    const featuredReceipt = model.receipts.find((receipt) => receipt.evidence.class === "model_influenced_unattested") || model.receipts[0];

    demo.schemaVersion = VIEW_SCHEMA;
    demo.demoOnly = false;
    demo.sourceMode = "verified_corpus";
    demo.sourceStatus = model.source.status;
    demo.sourceMeta = {
      badge: "LOCAL CORPUS",
      label: "reviewed receipts",
      datasetDigest: model.source.datasetDigest,
      readModelDigest: model.readModelDigest,
      receiptCount: model.receipts.length,
      hosted: false,
      live: false,
      authenticated: false,
      fallbackReason: null,
    };
    demo.truthBoundary = clone(model.truthBoundary);
    demo.account = { displayName: "Local Builder", tier: "Read-only corpus", creditsRemaining: 0, creditsLabel: "live credits · disabled" };
    demo.proofReceipts = proofs;
    demo.featured = featuredFromReceipt(featuredReceipt, proofById.get(featuredReceipt.receiptId));
    demo.tape = model.receipts.map((receipt, index) => ({
      time: `R${String(index + 1).padStart(2, "0")}`,
      type: "proof",
      channel: gameLabel(receipt.game.name),
      headline: receipt.headline,
      detail: `${receipt.proof.replayVerdict} replay · ${evidenceLabel(receipt.evidence.class)}`,
      tone: receipt.evidence.class === "model_influenced_unattested" ? "up" : "neutral",
      receiptId: receipt.receiptId,
    }));
    demo.channels = model.channels.map((channel, index) => ({
      id: `game-${channel.game}`,
      name: gameLabel(channel.game),
      description: `${channel.publishedReceiptCount} reviewed receipt${channel.publishedReceiptCount === 1 ? "" : "s"} · read only`,
      evidenceCount: channel.publishedReceiptCount,
      viewers: null,
      status: channel.status,
      followed: index < 2,
    }));
    demo.leaderboard = buildReceiptBoard(model.receipts);
    demo.quickMatches = model.futureFixtures.map((fixture) => ({
      id: fixture.fixtureId,
      mode: gameLabel(fixture.format),
      title: fixture.matchup.map((entrant) => entrant.name).join(" vs "),
      duration: `Week ${fixture.week}`,
      cost: "proposed · not activated",
      ranked: false,
      enabled: false,
      previewAllowed: true,
      actionLabel: "Preview",
      game: clone(fixture.game),
      rulesWeekId: fixture.rulesWeekId,
      rulesDigest: fixture.rulesDigest,
      activationStatus: fixture.activationStatus,
      fixtureStatus: fixture.status,
      resourceClass: PREVIEW_RESOURCE_CLASS,
    }));
    demo.watchlist = model.channels.map((channel) => ({
      id: `watch-${channel.game}`,
      symbol: symbolFor(channel.game),
      name: gameLabel(channel.game),
      kind: "Reviewed game",
      rating: channel.publishedReceiptCount,
      metricLabel: `${channel.publishedReceiptCount} receipt${channel.publishedReceiptCount === 1 ? "" : "s"}`,
      delta: null,
      trend: null,
    }));
    demo.rivalries = buildRivalryViews(model.rivalries, model.receipts);
    return demo;
  }

  function demoFallback(demoInput, reason = "verified_read_model_unavailable_or_invalid") {
    const demo = clone(validateDemoFixture(demoInput));
    demo.sourceMode = "demo_fixture_fallback";
    demo.sourceMeta = {
      badge: "DEMO FALLBACK",
      label: "simulated fixture",
      datasetDigest: null,
      readModelDigest: null,
      receiptCount: 0,
      hosted: false,
      live: false,
      authenticated: false,
      fallbackReason: reason,
    };
    demo.truthBoundary = {
      live: false,
      hosted: false,
      authenticated: false,
      modelAttested: false,
      providerAttested: false,
      runtimeAttested: false,
      statement: "This is a bounded local demo fixture. It is not a public receipt, live match, provider/model attestation, ranked result, or registry commit.",
    };
    demo.proofReceipts = [{ ...demo.featured.proof, headline: demo.featured.title, boundary: demo.truthBoundary.statement }];
    demo.featured.statusLabel = "Simulated fixture";
    demo.featured.runbackAvailable = false;
    demo.featured.runbackLabel = "Runback demo";
    demo.rivalries = [];
    return demo;
  }

  async function fetchJSON(fetchImpl, path, label) {
    const response = await fetchImpl(path, { cache: "no-store" });
    if (!response || response.ok !== true) throw new Error(`${label} request failed`);
    return response.json();
  }

  async function loadArenaData(fetchImpl = fetch) {
    const demo = await fetchJSON(fetchImpl, "data/demo-state.json", "demo fixture");
    validateDemoFixture(demo);
    try {
      const model = await fetchJSON(fetchImpl, "data/arena-read-model.v1.json", "verified read model");
      return adaptArenaReadModel(model, demo);
    } catch {
      return demoFallback(demo);
    }
  }

  return {
    DEMO_SCHEMA,
    LEARNING_SCHEMA,
    PORTABLE_RUNBACK_MAX_LENGTH,
    PORTABLE_RUNBACK_SCHEMA,
    PORTABLE_REVIEW_EXCHANGE_MAX_LENGTH,
    PORTABLE_REVIEW_EXCHANGE_SCHEMA,
    PORTABLE_REVIEW_CORRECTION_EXCHANGE_MAX_LENGTH,
    PORTABLE_REVIEW_CORRECTION_EXCHANGE_SCHEMA,
    PORTABLE_REVIEW_CORRECTION_MAX_RECORDS,
    PORTABLE_REVIEW_CORRECTION_REASONS,
    PORTABLE_REVIEW_CORRECTION_SCHEMA,
    PORTABLE_REVIEW_COMPARISON_MAX_ENTRIES,
    PORTABLE_REVIEW_COMPARISON_MAX_LENGTH,
    PORTABLE_REVIEW_COMPARISON_SCHEMA,
    PRIVATE_BLUEPRINT_DELTA_MAX_LENGTH,
    PRIVATE_BLUEPRINT_DELTA_SCHEMA,
    PRIVATE_BLUEPRINT_DELTA_REVIEW_MAX_LENGTH,
    PRIVATE_BLUEPRINT_DELTA_REVIEW_REASONS,
    PRIVATE_BLUEPRINT_DELTA_REVIEW_SCHEMA,
    PRIVATE_REVIEW_LESSON_DELTA,
    PRIVATE_REVIEW_INSPECTION_LESSONS,
    PRIVATE_REVIEW_LEARNING_MAX_ENTRIES,
    PRIVATE_REVIEW_LEARNING_MAX_LENGTH,
    PRIVATE_REVIEW_LEARNING_SCHEMA,
    PORTABLE_REVIEW_MAX_RECORDS,
    PORTABLE_REVIEW_REASONS,
    PORTABLE_REVIEW_SCHEMA,
    QUALIFICATION_SCHEMA,
    PREVIEW_RESOURCE_CLASS,
    READ_MODEL_SCHEMA,
    RUNBACK_PROPOSAL_SCHEMA,
    VIEW_SCHEMA,
    adaptArenaReadModel,
    appendPortableRunbackReview,
    appendPortableRunbackReviewCorrection,
    buildQualificationPreview,
    buildReceiptLearningAction,
    buildRunbackProposal,
    createPortablePrivateBlueprintDelta,
    createPortablePrivateBlueprintDeltaReview,
    createPortablePrivateReviewComparison,
    createPortablePrivateReviewLearning,
    createPortableRunbackEnvelope,
    createPortableRunbackReviewExchange,
    createPortableRunbackReviewCorrectionExchange,
    demoFallback,
    loadArenaData,
    validateArenaReadModel,
    validateDemoFixture,
    validateRunbackProposal,
    verifyPortableRunbackEnvelope,
    verifyPortableRunbackReviewCorrectionExchange,
    verifyPortableRunbackReviewCorrectionJournal,
    verifyPortableRunbackReviewExchange,
    verifyPortableRunbackReviewJournal,
    verifyPortablePrivateBlueprintDelta,
    verifyPortablePrivateBlueprintDeltaReview,
    verifyPortablePrivateReviewComparison,
    verifyPortablePrivateReviewLearning,
  };
}));
