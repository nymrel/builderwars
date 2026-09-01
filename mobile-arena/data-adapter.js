"use strict";

(function installDataAdapter(root, factory) {
  const adapter = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = adapter;
  if (root) root.BuilderWarsDataAdapter = adapter;
}(typeof globalThis !== "undefined" ? globalThis : this, function createDataAdapter() {
  const DEMO_SCHEMA = "builderwars.mobile-arena-demo.v1";
  const READ_MODEL_SCHEMA = "builderwars.arena-read-model.v1";
  const READ_MODEL_DIGEST_PIN = "c29a4c2d08f18bb3e60c6a0bc57f285057e0b2a38a8c4fde6a3cdadc21a94e89";
  const VIEW_SCHEMA = "builderwars.mobile-arena-view.v1";
  const TESTER_FEEDBACK_SCHEMA = "agentwars.tester-feedback-rubric/1";
  const TESTER_FEEDBACK_DRAFT_SCHEMA = "builderwars.mobile-tester-feedback-draft/1";
  const TESTER_FEEDBACK_DRAFT_MAX_LENGTH = 16384;
  const QUALIFICATION_SCHEMA = "builderwars.mobile-qualification-preview.v1";
  const LOCAL_EXHIBITION_QUALIFICATION_SCHEMA = "builderwars.mobile-local-exhibition-qualification.v1";
  const LOCAL_EXHIBITION_RECEIPT_SCHEMA = "builderwars.mobile-local-exhibition-receipt-candidate.v1";
  const LOCAL_EXHIBITION_VERIFICATION_SCHEMA = "builderwars.mobile-local-exhibition-verification.v1";
  const LOCAL_EXHIBITION_LEARNING_SCHEMA = "builderwars.mobile-local-exhibition-learning.v1";
  const LOCAL_EXHIBITION_RUNBACK_SCHEMA = "builderwars.mobile-local-exhibition-runback.v1";
  const LOCAL_EXHIBITION_PROOF_SHARE_SCHEMA = "builderwars.mobile-local-exhibition-proof-share.v1";
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
  const PRIVATE_BLUEPRINT_REVISION_DRAFT_SCHEMA = "builderwars.mobile-private-blueprint-revision-draft.v1";
  const PRIVATE_BLUEPRINT_DRAFT_REVIEW_SCHEMA = "builderwars.mobile-private-blueprint-revision-draft-review.v1";
  const PRIVATE_BLUEPRINT_GUARD_COMPLETION_SCHEMA = "builderwars.mobile-private-blueprint-guard-completion-proposal.v1";
  const PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_SCHEMA = "builderwars.mobile-private-blueprint-guard-completion-review.v1";
  const PRIVATE_BLUEPRINT_OPERATOR_REVIEW_PACKET_SCHEMA = "builderwars.mobile-private-blueprint-operator-review-packet.v1";
  const PREVIEW_RESOURCE_CLASS = "local-preview-no-compute-v1";
  const LOCAL_EXHIBITION_RESOURCE_CLASS = "browser-memory-deterministic-no-model-v1";
  const LOCAL_EXHIBITION_RULES_DIGEST = "feb22f090c5bc115d8fc939f02b4a17f8ae8894f7bde99ee9ec7385199d83ab0";
  const LOCAL_EXHIBITION_FIXTURE_ID = "c799e667cec7e3d57f1083953061da0e231ee72369a4dfe449d229c29ab701fb";
  const LOCAL_EXHIBITION_RULES = Object.freeze({
    schemaVersion: "builderwars.local-nim-rules.v1",
    game: Object.freeze({ name: "nim", version: "1" }),
    initialHeaps: Object.freeze([1, 3, 5]),
    normalPlay: true,
    moveKeys: Object.freeze(["heap", "take"]),
    maxTurns: 9,
    strategies: Object.freeze({
      blueprint_solver: "nim_xor_zero_else_first_legal_v1",
      blueprint_naive: "first_legal_v1",
      reference: "first_legal_v1",
    }),
  });
  const PORTABLE_RUNBACK_MAX_LENGTH = 32768;
  const LOCAL_EXHIBITION_PROOF_SHARE_MAX_LENGTH = 131072;
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
  const PRIVATE_BLUEPRINT_REVISION_DRAFT_MAX_LENGTH = 4194304;
  const PRIVATE_BLUEPRINT_DRAFT_REVIEW_MAX_LENGTH = 5242880;
  const PRIVATE_BLUEPRINT_GUARD_COMPLETION_MAX_LENGTH = 6291456;
  const PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_MAX_LENGTH = 7340032;
  const PRIVATE_BLUEPRINT_OPERATOR_REVIEW_PACKET_MAX_LENGTH = 8388608;
  const SAFE_JSON_NODE_LIMIT = 16384;
  const PORTABLE_REVIEW_COMPARISON_NODE_LIMIT = 49152;
  const PRIVATE_REVIEW_LEARNING_NODE_LIMIT = 65536;
  const PRIVATE_BLUEPRINT_DELTA_NODE_LIMIT = 73728;
  const PRIVATE_BLUEPRINT_DELTA_REVIEW_NODE_LIMIT = 81920;
  const PRIVATE_BLUEPRINT_REVISION_DRAFT_NODE_LIMIT = 102400;
  const PRIVATE_BLUEPRINT_DRAFT_REVIEW_NODE_LIMIT = 131072;
  const PRIVATE_BLUEPRINT_GUARD_COMPLETION_NODE_LIMIT = 163840;
  const PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_NODE_LIMIT = 196608;
  const PRIVATE_BLUEPRINT_OPERATOR_REVIEW_PACKET_NODE_LIMIT = 229376;
  const HEX64 = /^[0-9a-f]{64}$/;
  const CHALLENGE_ID = /^challenge_[0-9a-f]{16}$/;
  const DANGEROUS_KEYS = new Set(["__proto__", "constructor", "prototype"]);
  const TESTER_FEEDBACK_CATEGORIES = Object.freeze([
    Object.freeze({ categoryId: "orientation_clarity", prompt: "I knew what to do next." }),
    Object.freeze({ categoryId: "truth_boundary_comprehension", prompt: "I understood what was live, local, verified, and unattested." }),
    Object.freeze({ categoryId: "receipt_replay_trust", prompt: "The proof and replay made the result understandable and trustworthy." }),
    Object.freeze({ categoryId: "build_compete_clarity", prompt: "Building, qualifying, and competing felt coherent." }),
    Object.freeze({ categoryId: "share_runback_clarity", prompt: "Sharing and starting a runback were understandable." }),
    Object.freeze({ categoryId: "recovery_cleanup_confidence", prompt: "Revocation, deletion, cleanup, and recovery were clear." }),
    Object.freeze({ categoryId: "accessibility_usability", prompt: "The experience was usable on my device and access needs." }),
    Object.freeze({ categoryId: "return_intent", prompt: "I would return for another eligible competition." }),
  ]);
  const TESTER_FEEDBACK_BLOCKER_CLASSES = Object.freeze([
    "access", "authentication", "pairing", "passport", "build", "qualification", "match",
    "proof", "replay", "review", "publication", "share", "runback", "cleanup", "deletion",
    "rollback", "accessibility", "safety", "provider_boundary", "none",
  ]);
  const TESTER_FEEDBACK_SEVERE_ISSUE_CLASSES = Object.freeze([
    "security", "privacy", "uncontained_execution", "unreplayable_result", "unbounded_cost",
    "accessibility_blocker", "truth_overclaim", "none",
  ]);
  const TESTER_FEEDBACK_AUTHORITY_FIELDS = Object.freeze([
    "humanConsentAttested", "humanIdentityAttested", "authenticatedJourneyCompleted",
    "providerMatchCompleted", "independentReviewCompleted", "boundedPublicationCompleted",
    "accountDeletionCompleted", "productionRollbackCompleted", "operatorActionExecuted",
    "launchAuthorized", "publicLaunch",
  ]);
  const TESTER_FEEDBACK_DRAFT_BOUNDARY = "This canonical browser-memory draft contains structured selections only. It is not submitted, stored, consent evidence, human feedback evidence, identity evidence, a support request, an operator action, or launch authority.";
  const LOCAL_EXHIBITION_BOUNDARY = "This receipt candidate proves only deterministic scripted Nim play and independent local replay in this browser memory. The declared demo base was not used. It does not authenticate identity, attest a model, call a provider, spend, register, rank, publish, or authorize production.";
  const LOCAL_EXHIBITION_PROOF_SHARE_BOUNDARY = "This canonical private share candidate carries one embedded local exhibition receipt, independent replay verification, observation-only learning object, and unplayed runback. Its SHA-256 digest and local proof locator support integrity checking and embedded resolution only; they are not a signature, public URL, identity, model, provider, runtime, registry, ranking, publication, spending, or production authority.";
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
  const PRIVATE_BLUEPRINT_REVISION_DRAFT_BOUNDARY = "This canonical receipt independently reverifies one accepted private guard-proposal review and derives exactly one versioned local blueprint-revision draft. The draft copies the bound parent blueprint identity and applies only the exact reviewed allowlisted guard while preserving every other guard as carried or unknown. It remains uncommitted, unadopted, unqualified, unplayed, unexecuted, and unpublished; it cannot authenticate identity, declare correctness, create consensus, grant approval or progress, mutate the parent, bind rules, activate a fixture, execute, register, rank, publish, spend, or call a provider.";
  const PRIVATE_BLUEPRINT_DRAFT_REVIEW_BOUNDARY = "This canonical receipt independently reverifies one versioned local blueprint-revision draft and records exactly one immutable private local review. Accept-for-commit-candidate may derive only an uncommitted, unadopted local candidate. Explicit unknown guard values remain unknown and force commit readiness blocked; no decision authenticates identity, declares correctness, creates consensus, grants approval or progress, mutates the draft or parent, binds rules, qualifies, plays, executes, registers, ranks, publishes, spends, or calls a provider.";
  const PRIVATE_BLUEPRINT_GUARD_COMPLETION_BOUNDARY = "This canonical proposal independently reverifies one accepted private blueprint-draft review candidate and supplies boolean values only for that candidate's exact explicitly unknown guard keys. Every supplied value carries bounded local identity-unattested provenance. The proposal preserves all known and applied guard values and remains uncommitted, unadopted, not commit-ready, unqualified, unplayed, unexecuted, unregistered, and unpublished; it cannot attest provenance or identity, declare correctness, create consensus, grant approval or progress, mutate source lineage, bind rules, execute, spend, or call a provider.";
  const PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_BOUNDARY = "This canonical receipt independently reverifies one complete private guard-completion proposal and records exactly one immutable private local review. Accept-for-commit-review may derive only a local candidate for a later operator commit decision. It does not attest reviewer identity or guard-value provenance, make the candidate commit-ready, commit or adopt a blueprint, declare correctness, create consensus, grant approval or progress, mutate source lineage, bind rules, qualify, activate, play, execute, register, rank, publish, spend, or call a provider.";
  const PRIVATE_BLUEPRINT_OPERATOR_REVIEW_PACKET_BOUNDARY = "This canonical packet independently reverifies one accepted private guard-completion review and prepares its exact local candidate, original-to-candidate guard diff, unrun validation plan, discard-only rollback, and smallest later operator decision. Preparation is not an operator review, identity or provenance attestation, approval, commit, adoption, qualification, activation, play, execution, registry request, ranking, publication, spending authorization, or provider call.";
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
  const PRIVATE_BLUEPRINT_REVISION_DRAFT_BLOCKERS = Object.freeze([
    "reviewer_identity_unattested",
    "lesson_does_not_establish_correctness",
    "unreviewed_guard_values_not_carried",
    "local_draft_not_committed",
    "local_draft_not_adopted",
    "explicit_rules_digest_not_bound",
    "qualification_not_run",
    "fixture_not_activated",
    "sanctioned_runner_not_bound",
    "registry_not_requested",
    "publication_not_requested",
  ]);
  const PRIVATE_BLUEPRINT_DRAFT_REVIEW_REASONS = Object.freeze({
    accept_for_commit_candidate: Object.freeze(["draft_lineage_verified", "guard_change_preserved"]),
    defer: Object.freeze(["required_guard_values_unknown", "needs_operator_commit_review", "needs_additional_private_evidence"]),
    reject: Object.freeze(["draft_not_needed", "guard_change_not_approved", "unsafe_or_out_of_scope"]),
  });
  const PRIVATE_BLUEPRINT_DRAFT_REVIEW_BLOCKERS = Object.freeze([
    "reviewer_identity_unattested",
    "lesson_does_not_establish_correctness",
    "unknown_guard_values_block_commit_readiness",
    "local_commit_candidate_not_committed",
    "local_commit_candidate_not_adopted",
    "operator_commit_review_not_attested",
    "explicit_rules_digest_not_bound",
    "qualification_not_run",
    "fixture_not_activated",
    "sanctioned_runner_not_bound",
    "registry_not_requested",
    "publication_not_requested",
  ]);
  const PRIVATE_BLUEPRINT_GUARD_COMPLETION_REASONS = Object.freeze([
    "complete_explicit_unknown_guards",
    "declare_fixture_specific_safety_posture",
    "record_private_guard_requirement",
  ]);
  const PRIVATE_BLUEPRINT_GUARD_COMPLETION_PROVENANCE_CODES = Object.freeze([
    "local_reviewer_declared",
    "fixture_specific_requirement",
    "private_evidence_reviewed_locally",
  ]);
  const PRIVATE_BLUEPRINT_GUARD_COMPLETION_BLOCKERS = Object.freeze([
    "reviewer_identity_unattested",
    "guard_value_provenance_unattested",
    "guard_completion_not_reviewed_for_commit",
    "local_guard_completion_not_committed",
    "local_guard_completion_not_adopted",
    "operator_commit_review_not_attested",
    "explicit_rules_digest_not_bound",
    "qualification_not_run",
    "fixture_not_activated",
    "sanctioned_runner_not_bound",
    "registry_not_requested",
    "publication_not_requested",
  ]);
  const PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_REASONS = Object.freeze({
    accept_for_commit_review: Object.freeze(["completion_lineage_verified", "explicit_guard_values_reviewed"]),
    defer: Object.freeze(["needs_operator_commit_review", "needs_additional_private_evidence", "guard_value_provenance_unattested"]),
    reject: Object.freeze(["guard_completion_not_approved", "known_guard_preservation_failed", "unsafe_or_out_of_scope"]),
  });
  const PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_BLOCKERS = Object.freeze([
    "reviewer_identity_unattested",
    "guard_value_provenance_unattested",
    "operator_commit_review_not_attested",
    "local_blueprint_not_committed",
    "local_blueprint_not_adopted",
    "explicit_rules_digest_not_bound",
    "qualification_not_run",
    "fixture_not_activated",
    "sanctioned_runner_not_bound",
    "registry_not_requested",
    "publication_not_requested",
  ]);
  const PRIVATE_BLUEPRINT_OPERATOR_REVIEW_PACKET_BLOCKERS = Object.freeze([
    "operator_identity_unattested",
    "operator_decision_not_recorded",
    "reviewer_identity_unattested",
    "guard_value_provenance_unattested",
    "candidate_validation_not_run",
    "local_blueprint_not_committed",
    "local_blueprint_not_adopted",
    "explicit_rules_digest_not_bound",
    "qualification_not_run",
    "fixture_not_activated",
    "sanctioned_runner_not_bound",
    "registry_not_requested",
    "publication_not_requested",
  ]);
  const PRIVATE_BLUEPRINT_OPERATOR_REVIEW_VALIDATION_STEPS = Object.freeze([
    Object.freeze({ id: "focused_operator_packet", command: "python bin/check_mobile_arena_private_blueprint_operator_review_packet.py" }),
    Object.freeze({ id: "integrated_mobile_exchange", command: "python bin/check_mobile_arena_exchange.py" }),
    Object.freeze({ id: "replay_verifier_parity", command: "python bin/build_verifier.py --check" }),
    Object.freeze({ id: "provider_boundary", command: "python bin/check_provider_hub.py" }),
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

  async function verifyArenaReadModelIntegrity(modelInput) {
    const model = validateArenaReadModel(modelInput);
    requireValue(
      typeof TextEncoder !== "undefined" && globalThis.crypto?.subtle,
      "unsafe arena read model: SHA-256 unavailable",
    );
    requireValue(
      equalHex(model.readModelDigest, READ_MODEL_DIGEST_PIN),
      "unsafe arena read model: digest pin mismatch",
    );
    const digestPayload = Object.fromEntries(
      Object.entries(model).filter(([key]) => key !== "readModelDigest"),
    );
    const computedDigest = await sha256Hex(canonicalJSON(digestPayload));
    requireValue(
      equalHex(computedDigest, model.readModelDigest),
      "unsafe arena read model: digest mismatch",
    );
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

  function localExhibitionFixtureView() {
    return {
      id: LOCAL_EXHIBITION_FIXTURE_ID,
      mode: "Practice",
      title: "Your blueprint vs deterministic reference",
      duration: "9 moves max",
      cost: "local · no model",
      ranked: false,
      enabled: false,
      previewAllowed: true,
      exhibitionAllowed: true,
      actionLabel: "Practice",
      game: { name: "nim", version: "1" },
      rulesWeekId: "nim-local-exhibition-v1",
      rulesDigest: LOCAL_EXHIBITION_RULES_DIGEST,
      activationStatus: "local_exhibition_available",
      fixtureStatus: "unplayed",
      resourceClass: LOCAL_EXHIBITION_RESOURCE_CLASS,
    };
  }

  function localExhibitionStrategy(harnessStyle) {
    if (harnessStyle === "Validate every move") return LOCAL_EXHIBITION_RULES.strategies.blueprint_solver;
    if (harnessStyle === "Naive control") return LOCAL_EXHIBITION_RULES.strategies.blueprint_naive;
    return null;
  }

  function validateLocalExhibitionFixture(fixture) {
    requireValue(isObject(fixture) && fixture.exhibitionAllowed === true && fixture.previewAllowed === true && fixture.enabled === false, "unsafe local exhibition: fixture unavailable");
    requireValue(fixture.id === LOCAL_EXHIBITION_FIXTURE_ID, "unsafe local exhibition: fixture id drift");
    requireValue(isObject(fixture.game) && fixture.game.name === "nim" && fixture.game.version === "1", "unsafe local exhibition: game binding drift");
    requireValue(fixture.rulesWeekId === "nim-local-exhibition-v1" && fixture.rulesDigest === LOCAL_EXHIBITION_RULES_DIGEST, "unsafe local exhibition: rules binding drift");
    requireValue(fixture.activationStatus === "local_exhibition_available" && fixture.fixtureStatus === "unplayed", "unsafe local exhibition: lifecycle drift");
    requireValue(fixture.resourceClass === LOCAL_EXHIBITION_RESOURCE_CLASS, "unsafe local exhibition: resource class drift");
    requireValue(fixture.ranked === false, "unsafe local exhibition: ranked claim drift");
    return fixture;
  }

  function buildLocalExhibitionQualification(blueprintInput, fixtureInput, sourceMode) {
    const blueprint = validateQualificationBlueprint(blueprintInput);
    const fixture = validateLocalExhibitionFixture(fixtureInput);
    requireValue(sourceMode === "verified_corpus", "unsafe local exhibition: verified corpus required");
    const strategyId = localExhibitionStrategy(blueprint.harnessStyle);
    const executionBlockers = [];
    if (!blueprint.strictValidation) executionBlockers.push("strict_validation_required");
    if (!blueprint.fallbackDisclosure) executionBlockers.push("fallback_disclosure_required");
    if (!strategyId) executionBlockers.push("harness_style_not_supported_by_local_exhibition");
    const ready = executionBlockers.length === 0;
    return {
      schemaVersion: LOCAL_EXHIBITION_QUALIFICATION_SCHEMA,
      qualificationStatus: ready ? "qualified_local_exhibition" : "blocked_local_exhibition",
      executionStatus: ready ? "available_browser_memory_only" : "disabled",
      publicationStatus: "not_requested",
      qualificationKey: [
        "local-nim-exhibition-v1",
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
        declaredBaseUse: "metadata_only_not_used",
        harnessStyle: blueprint.harnessStyle,
        strategyId,
        strictValidation: blueprint.strictValidation,
        fallbackDisclosure: blueprint.fallbackDisclosure,
        humanCheckpoints: blueprint.humanCheckpoints,
        localOnly: true,
      },
      fixture: {
        fixtureId: fixture.id,
        title: fixture.title,
        game: clone(fixture.game),
        rulesWeekId: fixture.rulesWeekId,
        rulesDigest: fixture.rulesDigest,
        blueprintSeat: 0,
        referenceSeat: 1,
        ranked: false,
      },
      resourceClass: {
        id: LOCAL_EXHIBITION_RESOURCE_CLASS,
        label: "Browser memory · deterministic scripts · no model",
        computeClass: "bounded_local_javascript",
        networkAllowed: false,
        providerAllowed: false,
        modelAllowed: false,
        persistenceAllowed: false,
      },
      executionBlockers,
      attestations: { identity: false, model: false, provider: false, runtime: false, registry: false, publication: false },
      boundary: LOCAL_EXHIBITION_BOUNDARY,
    };
  }

  async function validateLocalExhibitionConstants() {
    const rulesDigest = await sha256Hex(canonicalJSON(LOCAL_EXHIBITION_RULES));
    requireValue(equalHex(rulesDigest, LOCAL_EXHIBITION_RULES_DIGEST), "unsafe local exhibition: canonical rules digest drift");
    const fixtureDigest = await sha256Hex(canonicalJSON({
      schemaVersion: "builderwars.local-exhibition-fixture.v1",
      game: { name: "nim", version: "1" },
      rulesDigest,
      resourceClass: LOCAL_EXHIBITION_RESOURCE_CLASS,
      blueprintSeat: 0,
      referenceSeat: 1,
    }));
    requireValue(equalHex(fixtureDigest, LOCAL_EXHIBITION_FIXTURE_ID), "unsafe local exhibition: canonical fixture digest drift");
  }

  function localNimLegalMoves(heaps) {
    const moves = [];
    for (let heap = 0; heap < heaps.length; heap += 1) {
      for (let take = 1; take <= heaps[heap]; take += 1) moves.push({ heap, take });
    }
    return moves;
  }

  function localNimMove(strategyId, heaps) {
    const legalMoves = localNimLegalMoves(heaps);
    requireValue(legalMoves.length > 0, "unsafe local exhibition: no legal move available");
    if (strategyId === LOCAL_EXHIBITION_RULES.strategies.blueprint_solver) {
      const target = heaps.reduce((value, heap) => value ^ heap, 0);
      if (target !== 0) {
        for (let heap = 0; heap < heaps.length; heap += 1) {
          const wanted = heaps[heap] ^ target;
          if (wanted < heaps[heap]) return { heap, take: heaps[heap] - wanted };
        }
      }
    } else {
      requireValue(strategyId === LOCAL_EXHIBITION_RULES.strategies.blueprint_naive || strategyId === LOCAL_EXHIBITION_RULES.strategies.reference, "unsafe local exhibition: unknown deterministic strategy");
    }
    return legalMoves[0];
  }

  function applyLocalNimMove(heapsInput, move) {
    requireValue(Array.isArray(heapsInput) && heapsInput.length === 3 && heapsInput.every(nonNegativeInteger), "unsafe local exhibition: invalid heap state");
    requireValue(isObject(move) && Object.keys(move).sort().join(",") === "heap,take", "unsafe local exhibition: invalid move shape");
    requireValue(Number.isInteger(move.heap) && Number.isInteger(move.take) && move.heap >= 0 && move.heap < heapsInput.length, "unsafe local exhibition: invalid move coordinates");
    requireValue(move.take >= 1 && move.take <= heapsInput[move.heap], "unsafe local exhibition: illegal move");
    const heaps = [...heapsInput];
    heaps[move.heap] -= move.take;
    return heaps;
  }

  function validateLocalExhibitionQualification(qualification) {
    assertSafeKeys(qualification, "local exhibition qualification");
    requireValue(isObject(qualification) && qualification.schemaVersion === LOCAL_EXHIBITION_QUALIFICATION_SCHEMA, "unsafe local exhibition: qualification schema drift");
    requireExactKeys(qualification, [
      "schemaVersion", "qualificationStatus", "executionStatus", "publicationStatus", "qualificationKey", "blueprint", "fixture",
      "resourceClass", "executionBlockers", "attestations", "boundary",
    ], "local exhibition qualification");
    requireValue(qualification.qualificationStatus === "qualified_local_exhibition" && qualification.executionStatus === "available_browser_memory_only", "unsafe local exhibition: qualification is not executable");
    requireValue(qualification.publicationStatus === "not_requested", "unsafe local exhibition: publication status drift");
    requireExactKeys(qualification.blueprint, [
      "agentName", "declaredBase", "declaredBaseUse", "harnessStyle", "strategyId", "strictValidation", "fallbackDisclosure",
      "humanCheckpoints", "localOnly",
    ], "local exhibition blueprint");
    requireValue(isObject(qualification.blueprint) && qualification.blueprint.localOnly === true && qualification.blueprint.declaredBaseUse === "metadata_only_not_used", "unsafe local exhibition: blueprint boundary drift");
    requireValue(typeof qualification.blueprint.agentName === "string" && qualification.blueprint.agentName.trim() === qualification.blueprint.agentName && qualification.blueprint.agentName.length > 0 && qualification.blueprint.agentName.length <= 36, "unsafe local exhibition: blueprint label drift");
    requireValue(ALLOWED_BASE_MODELS.has(qualification.blueprint.declaredBase) && ALLOWED_HARNESS_STYLES.has(qualification.blueprint.harnessStyle), "unsafe local exhibition: blueprint declaration drift");
    requireValue(qualification.blueprint.strictValidation === true && qualification.blueprint.fallbackDisclosure === true, "unsafe local exhibition: required guards missing");
    requireValue(typeof qualification.blueprint.humanCheckpoints === "boolean", "unsafe local exhibition: human checkpoint drift");
    requireValue(qualification.blueprint.strategyId === localExhibitionStrategy(qualification.blueprint.harnessStyle), "unsafe local exhibition: strategy binding drift");
    requireExactKeys(qualification.fixture, ["fixtureId", "title", "game", "rulesWeekId", "rulesDigest", "blueprintSeat", "referenceSeat", "ranked"], "local exhibition fixture");
    requireExactKeys(qualification.fixture.game, ["name", "version"], "local exhibition game");
    requireValue(isObject(qualification.fixture) && qualification.fixture.fixtureId === LOCAL_EXHIBITION_FIXTURE_ID && qualification.fixture.rulesDigest === LOCAL_EXHIBITION_RULES_DIGEST && qualification.fixture.ranked === false, "unsafe local exhibition: fixture binding drift");
    requireValue(qualification.fixture.title === "Your blueprint vs deterministic reference" && qualification.fixture.game.name === "nim" && qualification.fixture.game.version === "1", "unsafe local exhibition: fixture description drift");
    requireValue(qualification.fixture.rulesWeekId === "nim-local-exhibition-v1" && qualification.fixture.blueprintSeat === 0 && qualification.fixture.referenceSeat === 1, "unsafe local exhibition: fixture seat or rules drift");
    requireExactKeys(qualification.resourceClass, ["id", "label", "computeClass", "networkAllowed", "providerAllowed", "modelAllowed", "persistenceAllowed"], "local exhibition resource class");
    requireValue(isObject(qualification.resourceClass) && qualification.resourceClass.id === LOCAL_EXHIBITION_RESOURCE_CLASS, "unsafe local exhibition: resource binding drift");
    requireValue(qualification.resourceClass.label === "Browser memory · deterministic scripts · no model" && qualification.resourceClass.computeClass === "bounded_local_javascript", "unsafe local exhibition: resource description drift");
    requireValue(qualification.resourceClass.networkAllowed === false && qualification.resourceClass.providerAllowed === false && qualification.resourceClass.modelAllowed === false && qualification.resourceClass.persistenceAllowed === false, "unsafe local exhibition: resource authority drift");
    requireValue(Array.isArray(qualification.executionBlockers) && qualification.executionBlockers.length === 0, "unsafe local exhibition: unresolved blockers");
    requireExactKeys(qualification.attestations, ["identity", "model", "provider", "runtime", "registry", "publication"], "local exhibition attestations");
    requireValue(isObject(qualification.attestations) && Object.values(qualification.attestations).every((value) => value === false), "unsafe local exhibition: attestation drift");
    const expectedQualificationKey = [
      "local-nim-exhibition-v1",
      qualification.fixture.fixtureId,
      encodeURIComponent(qualification.blueprint.agentName),
      encodeURIComponent(qualification.blueprint.declaredBase),
      encodeURIComponent(qualification.blueprint.harnessStyle),
      1,
      1,
      qualification.blueprint.humanCheckpoints ? 1 : 0,
    ].join(":");
    requireValue(qualification.qualificationKey === expectedQualificationKey, "unsafe local exhibition: qualification key drift");
    requireValue(qualification.boundary === LOCAL_EXHIBITION_BOUNDARY, "unsafe local exhibition: qualification boundary drift");
    return qualification;
  }

  async function createLocalExhibitionReceipt(qualificationInput) {
    await validateLocalExhibitionConstants();
    const qualification = clone(validateLocalExhibitionQualification(qualificationInput));
    const qualificationDigest = await sha256Hex(canonicalJSON(qualification));
    let heaps = [...LOCAL_EXHIBITION_RULES.initialHeaps];
    let seat = 0;
    const transcript = [];
    while (heaps.some((heap) => heap > 0)) {
      requireValue(transcript.length < LOCAL_EXHIBITION_RULES.maxTurns, "unsafe local exhibition: move bound exceeded");
      const strategyId = seat === 0 ? qualification.blueprint.strategyId : LOCAL_EXHIBITION_RULES.strategies.reference;
      const move = localNimMove(strategyId, heaps);
      const before = [...heaps];
      heaps = applyLocalNimMove(heaps, move);
      transcript.push({
        turn: transcript.length,
        seat,
        actor: seat === 0 ? "local_blueprint" : "deterministic_reference",
        strategyId,
        before,
        move,
        after: [...heaps],
        moveSource: "deterministic_scripted",
      });
      if (heaps.every((heap) => heap === 0)) break;
      seat = 1 - seat;
    }
    const winnerSeat = transcript[transcript.length - 1].seat;
    const payload = {
      schemaVersion: LOCAL_EXHIBITION_RECEIPT_SCHEMA,
      receiptStatus: "local_receipt_candidate_unreviewed",
      receiptClass: "deterministic_browser_memory_exhibition",
      qualificationDigest,
      qualification,
      fixtureBinding: {
        fixtureId: LOCAL_EXHIBITION_FIXTURE_ID,
        game: { name: "nim", version: "1" },
        rulesDigest: LOCAL_EXHIBITION_RULES_DIGEST,
        resourceClass: LOCAL_EXHIBITION_RESOURCE_CLASS,
      },
      entrants: [
        { seat: 0, label: qualification.blueprint.agentName, labelStatus: "unattested_local_label", harnessStyle: qualification.blueprint.harnessStyle, strategyId: qualification.blueprint.strategyId },
        { seat: 1, label: "Deterministic reference", labelStatus: "tracked_local_reference", harnessStyle: "Reference control", strategyId: LOCAL_EXHIBITION_RULES.strategies.reference },
      ],
      initialState: { heaps: [...LOCAL_EXHIBITION_RULES.initialHeaps], toMove: 0 },
      transcript,
      result: { winnerSeat, winnerLabel: winnerSeat === 0 ? qualification.blueprint.agentName : "Deterministic reference", reason: "took_last_object", moveCount: transcript.length },
      evidence: {
        class: "deterministic_scripted_local_exhibition",
        moveSourceCounts: { deterministicScripted: transcript.length, model: 0, provider: 0, fallback: 0, human: 0 },
        declaredBaseUsed: false,
        hiddenReasoningInferred: false,
      },
      storageStatus: "browser_memory_only_not_persisted",
      registryStatus: "not_requested",
      publicationStatus: "not_requested",
      ranked: false,
      attestations: { identity: false, model: false, provider: false, runtime: false, registry: false, publication: false },
      boundary: LOCAL_EXHIBITION_BOUNDARY,
    };
    return { ...payload, candidateDigest: await sha256Hex(canonicalJSON(payload)) };
  }

  async function verifyLocalExhibitionReceipt(receiptInput) {
    await validateLocalExhibitionConstants();
    assertSafeKeys(receiptInput, "local exhibition receipt");
    requireValue(isObject(receiptInput) && receiptInput.schemaVersion === LOCAL_EXHIBITION_RECEIPT_SCHEMA, "unsafe local exhibition receipt: schema drift");
    requireValue(HEX64.test(receiptInput.candidateDigest), "unsafe local exhibition receipt: candidate digest missing");
    const unsigned = clone(receiptInput);
    delete unsigned.candidateDigest;
    const computedDigest = await sha256Hex(canonicalJSON(unsigned));
    requireValue(equalHex(computedDigest, receiptInput.candidateDigest), "unsafe local exhibition receipt: candidate digest mismatch");
    const reconstructed = await createLocalExhibitionReceipt(receiptInput.qualification);
    requireValue(canonicalJSON(reconstructed) === canonicalJSON(receiptInput), "unsafe local exhibition receipt: deterministic replay mismatch");
    return {
      schemaVersion: LOCAL_EXHIBITION_VERIFICATION_SCHEMA,
      verificationStatus: "verified_local_receipt_candidate",
      candidateDigest: receiptInput.candidateDigest,
      qualificationDigest: receiptInput.qualificationDigest,
      replayVerdict: "PASS",
      replayedMoveCount: receiptInput.transcript.length,
      modelMoveCount: 0,
      providerMoveCount: 0,
      registryStatus: "not_requested",
      publicationStatus: "not_requested",
      ranked: false,
      attestations: { identity: false, model: false, provider: false, runtime: false, registry: false, publication: false },
      boundary: LOCAL_EXHIBITION_BOUNDARY,
    };
  }

  async function createLocalExhibitionLearning(receiptInput, verificationInput) {
    const verification = await verifyLocalExhibitionReceipt(receiptInput);
    requireValue(canonicalJSON(verification) === canonicalJSON(verificationInput), "unsafe local exhibition learning: verification drift");
    const solverUsed = receiptInput.qualification.blueprint.strategyId === LOCAL_EXHIBITION_RULES.strategies.blueprint_solver;
    const payload = {
      schemaVersion: LOCAL_EXHIBITION_LEARNING_SCHEMA,
      learningStatus: "verified_local_observation_only",
      parentCandidateDigest: receiptInput.candidateDigest,
      replayVerdict: verification.replayVerdict,
      observation: `${receiptInput.result.winnerLabel} took the last object after ${receiptInput.result.moveCount} deterministic scripted moves.`,
      lessonId: solverUsed ? "inspect_xor_zero_strategy" : "compare_first_legal_control",
      guidance: solverUsed
        ? "Inspect the visible heap transitions where the blueprint restored XOR zero. This is game-state evidence, not model reasoning."
        : "Compare the visible first-legal control moves with the solver pattern before changing a future local harness.",
      recommendedRunback: { version: 1, seatSwap: true, rulesDigest: LOCAL_EXHIBITION_RULES_DIGEST, status: "unplayed" },
      hiddenReasoningInferred: false,
      authority: { identity: false, model: false, provider: false, registry: false, publication: false, production: false },
      boundary: "This learning object summarizes only verified visible moves from one local deterministic exhibition. It does not infer model reasoning, award progress, change a blueprint, or authorize another match.",
    };
    return { ...payload, learningDigest: await sha256Hex(canonicalJSON(payload)) };
  }

  async function createLocalExhibitionRunback(receiptInput, verificationInput, learningInput) {
    const verification = await verifyLocalExhibitionReceipt(receiptInput);
    requireValue(canonicalJSON(verification) === canonicalJSON(verificationInput), "unsafe local exhibition runback: verification drift");
    const learning = await createLocalExhibitionLearning(receiptInput, verificationInput);
    requireValue(canonicalJSON(learning) === canonicalJSON(learningInput), "unsafe local exhibition runback: learning drift");
    const payload = {
      schemaVersion: LOCAL_EXHIBITION_RUNBACK_SCHEMA,
      runbackVersion: 1,
      runbackStatus: "versioned_local_runback_unplayed",
      executionStatus: "not_run",
      parentCandidateDigest: receiptInput.candidateDigest,
      parentLearningDigest: learning.learningDigest,
      fixtureBinding: {
        parentFixtureId: LOCAL_EXHIBITION_FIXTURE_ID,
        game: { name: "nim", version: "1" },
        rulesDigest: LOCAL_EXHIBITION_RULES_DIGEST,
        resourceClass: LOCAL_EXHIBITION_RESOURCE_CLASS,
      },
      seatPlan: { blueprintSeat: 1, referenceSeat: 0, seatSwap: true },
      blueprint: clone(receiptInput.qualification.blueprint),
      storageStatus: "browser_memory_only_not_persisted",
      registryStatus: "not_requested",
      publicationStatus: "not_requested",
      ranked: false,
      attestations: { identity: false, model: false, provider: false, runtime: false, registry: false, publication: false },
      executionBlockers: ["explicit_user_runback_action_not_requested"],
      boundary: "This digest-bound version 1 runback preserves the exact parent, rules, resource class, blueprint, and swapped seats. It remains unplayed and grants no provider, model, identity, registry, ranking, publication, spending, or production authority.",
    };
    return { ...payload, runbackDigest: await sha256Hex(canonicalJSON(payload)) };
  }

  async function createLocalExhibitionProofShare(receiptInput, verificationInput, learningInput, runbackInput) {
    const verification = await verifyLocalExhibitionReceipt(receiptInput);
    requireValue(canonicalJSON(verification) === canonicalJSON(verificationInput), "unsafe local exhibition proof share: verification drift");
    const learning = await createLocalExhibitionLearning(receiptInput, verificationInput);
    requireValue(canonicalJSON(learning) === canonicalJSON(learningInput), "unsafe local exhibition proof share: learning drift");
    const runback = await createLocalExhibitionRunback(receiptInput, verificationInput, learningInput);
    requireValue(canonicalJSON(runback) === canonicalJSON(runbackInput), "unsafe local exhibition proof share: runback drift");
    const proofLocator = `builderwars-local-proof://receipt-candidate/${receiptInput.candidateDigest}`;
    const payload = {
      shareStatus: "local_private_proof_share_candidate",
      proofRef: {
        scheme: "builderwars-local-proof-v1",
        locator: proofLocator,
        resolutionMode: "embedded_canonical_payload_only",
        publicUrl: null,
      },
      lineage: {
        qualificationDigest: receiptInput.qualificationDigest,
        candidateDigest: receiptInput.candidateDigest,
        learningDigest: learning.learningDigest,
        runbackDigest: runback.runbackDigest,
      },
      claims: {
        builder: { label: "Browser-local builder", identityAttested: false },
        agent: { label: receiptInput.entrants[0].label, identityAttested: false },
        harness: {
          style: receiptInput.qualification.blueprint.harnessStyle,
          strategyId: receiptInput.qualification.blueprint.strategyId,
          claimStatus: "declared_local_deterministic",
        },
        model: {
          declaredBase: receiptInput.qualification.blueprint.declaredBase,
          usage: "metadata_only_not_used",
          attested: false,
        },
        game: clone(receiptInput.fixtureBinding.game),
        rules: { digest: receiptInput.fixtureBinding.rulesDigest },
        resource: { class: receiptInput.fixtureBinding.resourceClass },
      },
      proof: {
        receipt: clone(receiptInput),
        verification: clone(verification),
        learning: clone(learning),
        runback: clone(runback),
      },
      storageStatus: "caller_controlled_private_text_not_saved_by_app",
      registryStatus: "not_requested",
      publicationStatus: "not_requested",
      ranked: false,
      attestations: { identity: false, model: false, provider: false, runtime: false, registry: false, publication: false },
    };
    const envelope = {
      schemaVersion: LOCAL_EXHIBITION_PROOF_SHARE_SCHEMA,
      shareVersion: 1,
      payload,
      integrity: { algorithm: "SHA-256", payloadDigest: await sha256Hex(canonicalJSON(payload)) },
      boundary: LOCAL_EXHIBITION_PROOF_SHARE_BOUNDARY,
    };
    const serialized = canonicalJSON(envelope);
    requireValue(serialized.length <= LOCAL_EXHIBITION_PROOF_SHARE_MAX_LENGTH, "unsafe local exhibition proof share: output length rejected");
    return { envelope: clone(envelope), serialized };
  }

  async function verifyLocalExhibitionProofShare(serializedInput) {
    requireValue(typeof serializedInput === "string" && serializedInput.length > 0 && serializedInput.length <= LOCAL_EXHIBITION_PROOF_SHARE_MAX_LENGTH, "unsafe local exhibition proof share: input length rejected");
    let envelope;
    try {
      envelope = JSON.parse(serializedInput);
    } catch {
      throw new Error("unsafe local exhibition proof share: invalid JSON");
    }
    assertSafeKeys(envelope, "local exhibition proof share");
    requireExactKeys(envelope, ["schemaVersion", "shareVersion", "payload", "integrity", "boundary"], "local exhibition proof share");
    requireValue(envelope.schemaVersion === LOCAL_EXHIBITION_PROOF_SHARE_SCHEMA && envelope.shareVersion === 1, "unsafe local exhibition proof share: schema drift");
    requireValue(envelope.boundary === LOCAL_EXHIBITION_PROOF_SHARE_BOUNDARY, "unsafe local exhibition proof share: boundary drift");
    requireValue(serializedInput === canonicalJSON(envelope), "unsafe local exhibition proof share: envelope must use canonical JSON");
    requireExactKeys(envelope.payload, [
      "shareStatus", "proofRef", "lineage", "claims", "proof", "storageStatus", "registryStatus", "publicationStatus", "ranked", "attestations",
    ], "local exhibition proof share payload");
    requireExactKeys(envelope.integrity, ["algorithm", "payloadDigest"], "local exhibition proof share integrity");
    requireValue(envelope.integrity.algorithm === "SHA-256" && HEX64.test(envelope.integrity.payloadDigest), "unsafe local exhibition proof share: integrity drift");
    const computedPayloadDigest = await sha256Hex(canonicalJSON(envelope.payload));
    requireValue(equalHex(computedPayloadDigest, envelope.integrity.payloadDigest), "unsafe local exhibition proof share: payload digest mismatch");
    requireExactKeys(envelope.payload.proof, ["receipt", "verification", "learning", "runback"], "local exhibition proof share proof");
    const verification = await verifyLocalExhibitionReceipt(envelope.payload.proof.receipt);
    const learning = await createLocalExhibitionLearning(envelope.payload.proof.receipt, envelope.payload.proof.verification);
    const runback = await createLocalExhibitionRunback(envelope.payload.proof.receipt, envelope.payload.proof.verification, envelope.payload.proof.learning);
    requireValue(canonicalJSON(verification) === canonicalJSON(envelope.payload.proof.verification), "unsafe local exhibition proof share: embedded verification drift");
    requireValue(canonicalJSON(learning) === canonicalJSON(envelope.payload.proof.learning), "unsafe local exhibition proof share: embedded learning drift");
    requireValue(canonicalJSON(runback) === canonicalJSON(envelope.payload.proof.runback), "unsafe local exhibition proof share: embedded runback drift");
    const expected = await createLocalExhibitionProofShare(envelope.payload.proof.receipt, verification, learning, runback);
    requireValue(canonicalJSON(expected.envelope) === canonicalJSON(envelope), "unsafe local exhibition proof share: proof projection mismatch");
    return {
      verificationStatus: "verified_embedded_local_proof_share",
      proofResolution: "PASS",
      proofLocator: envelope.payload.proofRef.locator,
      payloadDigest: envelope.integrity.payloadDigest,
      candidateDigest: envelope.payload.lineage.candidateDigest,
      receipt: clone(envelope.payload.proof.receipt),
      verification: clone(verification),
      learning: clone(learning),
      runback: clone(runback),
      authority: { identity: false, model: false, provider: false, runtime: false, registry: false, publication: false, production: false },
      boundary: LOCAL_EXHIBITION_PROOF_SHARE_BOUNDARY,
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

  async function buildPortablePrivateBlueprintRevisionDraft(reviewVerification) {
    requireValue(
      isObject(reviewVerification)
        && reviewVerification.schemaVersion === PRIVATE_BLUEPRINT_DELTA_REVIEW_SCHEMA
        && reviewVerification.verificationStatus === "verified_private_local_blueprint_delta_review",
      "unsafe private blueprint revision draft: verified guard review required",
    );
    const review = reviewVerification.review;
    requireValue(
      review.decision === "accept_for_revision"
        && isObject(review.localRevisionCandidate)
        && review.localRevisionCandidate.status === "proposed_uncommitted_local_revision_candidate",
      "unsafe private blueprint revision draft: accepted review required",
    );
    const deltaVerification = reviewVerification.blueprintDeltaVerification;
    const proposal = deltaVerification.proposal;
    const comparisonVerification = deltaVerification.learningVerification.comparisonVerification;
    const leftParent = comparisonVerification.leftVerification.proposalVerification;
    const rightParent = comparisonVerification.rightVerification.proposalVerification;
    requireValue(
      equalHex(leftParent.payloadDigest, rightParent.payloadDigest)
        && equalHex(leftParent.payloadDigest, proposal.parentProposalBinding.proposalPayloadDigest),
      "unsafe private blueprint revision draft: parent proposal digest mismatch",
    );
    requireValue(canonicalJSON(leftParent.proposal) === canonicalJSON(rightParent.proposal), "unsafe private blueprint revision draft: parent proposal mismatch");
    const parentProposal = leftParent.proposal;
    const parentGuardValues = Object.fromEntries(RUNBACK_DELTAS.map((delta) => [delta.guardKey, null]));
    parentGuardValues[parentProposal.blueprintDelta.guardKey] = parentProposal.blueprintDelta.from;
    const revisedGuardValues = clone(parentGuardValues);
    revisedGuardValues[proposal.guardDelta.guardKey] = true;
    const unknownGuardKeys = Object.keys(revisedGuardValues).filter((guardKey) => revisedGuardValues[guardKey] === null).sort();
    const lineage = {
      acceptedReviewPacketDigest: reviewVerification.packetDigest,
      acceptedReviewDigest: review.reviewDigest,
      acceptedCandidateRevisionKey: review.localRevisionCandidate.revisionKey,
      guardProposalPacketDigest: deltaVerification.packetDigest,
      guardProposalKey: proposal.proposalKey,
      learningPacketDigest: deltaVerification.learningVerification.packetDigest,
      comparisonPacketDigest: proposal.sourceDigests.comparisonPacketDigest,
      parentProposalPayloadDigest: proposal.parentProposalBinding.proposalPayloadDigest,
      parentProposalKey: proposal.parentProposalBinding.proposalKey,
      selectedReviewDigest: proposal.selectedLesson.reviewDigest,
      guardDeltaId: proposal.guardDelta.id,
    };
    const record = {
      draftStatus: "proposed_uncommitted_local_blueprint_revision_draft",
      draftKey: [
        "private-blueprint-revision-draft-v1",
        reviewVerification.packetDigest,
        review.reviewDigest,
        proposal.guardDelta.id,
        proposal.parentProposalBinding.proposalPayloadDigest,
      ].join(":"),
      parentBlueprint: clone(parentProposal.blueprint),
      parentGuardValues,
      revisedBlueprint: {
        agentName: parentProposal.blueprint.agentName,
        declaredBase: parentProposal.blueprint.declaredBase,
        harnessStyle: parentProposal.blueprint.harnessStyle,
        localOnly: true,
        guardValues: revisedGuardValues,
      },
      appliedGuard: clone(proposal.guardDelta),
      unknownGuardKeys,
      lineage,
      state: {
        localOnly: true,
        committed: false,
        adopted: false,
        qualificationStatus: "not_run",
        played: false,
        executionStatus: "disabled",
        registryStatus: "not_requested",
        publicationStatus: "not_requested",
      },
      blockers: [...PRIVATE_BLUEPRINT_REVISION_DRAFT_BLOCKERS],
      authority: privateBlueprintDeltaAuthority(),
      boundary: PRIVATE_BLUEPRINT_REVISION_DRAFT_BOUNDARY,
    };
    const draftDigest = await sha256Hex(canonicalJSON(record));
    return { ...record, draftDigest };
  }

  async function createPortablePrivateBlueprintRevisionDraft(serializedReviewInput) {
    const acceptedReviewVerification = await verifyPortablePrivateBlueprintDeltaReview(serializedReviewInput);
    const draft = await buildPortablePrivateBlueprintRevisionDraft(acceptedReviewVerification);
    const payload = {
      acceptedReviewReceipt: JSON.parse(serializedReviewInput),
      draft,
    };
    const payloadDigest = await sha256Hex(canonicalJSON(payload));
    const proposal = acceptedReviewVerification.blueprintDeltaVerification.proposal;
    const packet = {
      schemaVersion: PRIVATE_BLUEPRINT_REVISION_DRAFT_SCHEMA,
      draftVersion: 1,
      payload,
      integrity: {
        algorithm: "sha256",
        payloadDigest,
        acceptedReviewPacketDigest: acceptedReviewVerification.packetDigest,
        acceptedReviewDigest: acceptedReviewVerification.review.reviewDigest,
        guardProposalPacketDigest: acceptedReviewVerification.blueprintDeltaVerification.packetDigest,
        parentProposalPayloadDigest: proposal.parentProposalBinding.proposalPayloadDigest,
        selectedReviewDigest: proposal.selectedLesson.reviewDigest,
        draftDigest: draft.draftDigest,
      },
      boundary: PRIVATE_BLUEPRINT_REVISION_DRAFT_BOUNDARY,
    };
    const serialized = canonicalJSON(packet);
    requireValue(serialized.length <= PRIVATE_BLUEPRINT_REVISION_DRAFT_MAX_LENGTH, "unsafe private blueprint revision draft: packet length rejected");
    return { packet: clone(packet), serialized };
  }

  async function verifyPortablePrivateBlueprintRevisionDraft(serializedInput) {
    requireValue(
      typeof serializedInput === "string"
        && serializedInput.length > 0
        && serializedInput.length <= PRIVATE_BLUEPRINT_REVISION_DRAFT_MAX_LENGTH,
      "unsafe private blueprint revision draft: input length rejected",
    );
    let packet;
    try {
      packet = JSON.parse(serializedInput);
    } catch {
      throw new Error("unsafe private blueprint revision draft: invalid JSON");
    }
    assertSafeKeys(packet, "private blueprint revision draft", 0, { nodes: 0 }, PRIVATE_BLUEPRINT_REVISION_DRAFT_NODE_LIMIT);
    requireExactKeys(packet, ["schemaVersion", "draftVersion", "payload", "integrity", "boundary"], "private blueprint revision draft");
    requireValue(packet.schemaVersion === PRIVATE_BLUEPRINT_REVISION_DRAFT_SCHEMA && packet.draftVersion === 1, "unsafe private blueprint revision draft: schema drift");
    requireValue(packet.boundary === PRIVATE_BLUEPRINT_REVISION_DRAFT_BOUNDARY, "unsafe private blueprint revision draft: boundary drift");
    requireValue(serializedInput === canonicalJSON(packet), "unsafe private blueprint revision draft: packet must use canonical JSON");
    requireExactKeys(packet.payload, ["acceptedReviewReceipt", "draft"], "private blueprint revision draft payload");
    requireExactKeys(packet.integrity, [
      "algorithm", "payloadDigest", "acceptedReviewPacketDigest", "acceptedReviewDigest", "guardProposalPacketDigest",
      "parentProposalPayloadDigest", "selectedReviewDigest", "draftDigest",
    ], "private blueprint revision draft integrity");
    requireValue(packet.integrity.algorithm === "sha256", "unsafe private blueprint revision draft: integrity algorithm drift");
    for (const key of [
      "payloadDigest", "acceptedReviewPacketDigest", "acceptedReviewDigest", "guardProposalPacketDigest",
      "parentProposalPayloadDigest", "selectedReviewDigest", "draftDigest",
    ]) requireValue(HEX64.test(packet.integrity[key]), `unsafe private blueprint revision draft: ${key} drift`);

    const acceptedReviewSerialized = canonicalJSON(packet.payload.acceptedReviewReceipt);
    const acceptedReviewVerification = await verifyPortablePrivateBlueprintDeltaReview(acceptedReviewSerialized);
    const expectedDraft = await buildPortablePrivateBlueprintRevisionDraft(acceptedReviewVerification);
    requireValue(canonicalJSON(packet.payload.draft) === canonicalJSON(expectedDraft), "unsafe private blueprint revision draft: draft projection mismatch");
    const proposal = acceptedReviewVerification.blueprintDeltaVerification.proposal;
    requireValue(equalHex(acceptedReviewVerification.packetDigest, packet.integrity.acceptedReviewPacketDigest), "unsafe private blueprint revision draft: accepted review packet digest binding mismatch");
    requireValue(equalHex(acceptedReviewVerification.review.reviewDigest, packet.integrity.acceptedReviewDigest), "unsafe private blueprint revision draft: accepted review digest binding mismatch");
    requireValue(equalHex(acceptedReviewVerification.blueprintDeltaVerification.packetDigest, packet.integrity.guardProposalPacketDigest), "unsafe private blueprint revision draft: guard proposal packet digest binding mismatch");
    requireValue(equalHex(proposal.parentProposalBinding.proposalPayloadDigest, packet.integrity.parentProposalPayloadDigest), "unsafe private blueprint revision draft: parent proposal digest binding mismatch");
    requireValue(equalHex(proposal.selectedLesson.reviewDigest, packet.integrity.selectedReviewDigest), "unsafe private blueprint revision draft: selected review digest binding mismatch");
    requireValue(equalHex(expectedDraft.draftDigest, packet.integrity.draftDigest), "unsafe private blueprint revision draft: draft digest binding mismatch");
    const computedPayloadDigest = await sha256Hex(canonicalJSON(packet.payload));
    requireValue(equalHex(computedPayloadDigest, packet.integrity.payloadDigest), "unsafe private blueprint revision draft: payload digest mismatch");
    return {
      schemaVersion: PRIVATE_BLUEPRINT_REVISION_DRAFT_SCHEMA,
      verificationStatus: "verified_private_local_blueprint_revision_draft",
      packetDigest: computedPayloadDigest,
      acceptedReviewSerialized,
      acceptedReviewVerification,
      draft: clone(expectedDraft),
      boundary: PRIVATE_BLUEPRINT_REVISION_DRAFT_BOUNDARY,
    };
  }

  function privateBlueprintDraftReviewBinding(draftVerification) {
    const draft = draftVerification.draft;
    return {
      draftPacketDigest: draftVerification.packetDigest,
      draftDigest: draft.draftDigest,
      draftKey: draft.draftKey,
      acceptedReviewPacketDigest: draft.lineage.acceptedReviewPacketDigest,
      acceptedReviewDigest: draft.lineage.acceptedReviewDigest,
      guardProposalPacketDigest: draft.lineage.guardProposalPacketDigest,
      parentProposalPayloadDigest: draft.lineage.parentProposalPayloadDigest,
      selectedReviewDigest: draft.lineage.selectedReviewDigest,
      appliedGuardId: draft.appliedGuard.id,
    };
  }

  async function proposedPrivateBlueprintCommitCandidate(draftVerification, binding) {
    const draft = draftVerification.draft;
    const hasUnknownGuards = draft.unknownGuardKeys.length > 0;
    const blockers = PRIVATE_BLUEPRINT_DRAFT_REVIEW_BLOCKERS.filter(
      (blocker) => hasUnknownGuards || blocker !== "unknown_guard_values_block_commit_readiness",
    );
    const record = {
      status: "proposed_uncommitted_local_blueprint_commit_candidate",
      candidateKey: [
        "private-blueprint-commit-candidate-v1",
        binding.draftPacketDigest,
        binding.draftDigest,
        encodeURIComponent(binding.appliedGuardId),
      ].join(":"),
      parentDraftKey: binding.draftKey,
      parentDraftDigest: binding.draftDigest,
      blueprint: clone(draft.revisedBlueprint),
      appliedGuard: clone(draft.appliedGuard),
      unknownGuardKeys: clone(draft.unknownGuardKeys),
      guardCompletionStatus: hasUnknownGuards ? "incomplete_unknown_guard_values" : "complete_guard_values",
      commitReadinessStatus: hasUnknownGuards ? "blocked_unknown_guard_values" : "requires_operator_commit_review",
      localOnly: true,
      committed: false,
      adopted: false,
      commitReady: false,
      qualificationStatus: "not_run",
      executionStatus: "disabled",
      registryStatus: "not_requested",
      publicationStatus: "not_requested",
      blockers,
      authority: privateBlueprintDeltaAuthority(),
      boundary: PRIVATE_BLUEPRINT_DRAFT_REVIEW_BOUNDARY,
    };
    const candidateDigest = await sha256Hex(canonicalJSON(record));
    return { ...record, candidateDigest };
  }

  async function buildPortablePrivateBlueprintDraftReviewRecord(draftVerification, reviewInput) {
    requireValue(
      isObject(draftVerification)
        && draftVerification.schemaVersion === PRIVATE_BLUEPRINT_REVISION_DRAFT_SCHEMA
        && draftVerification.verificationStatus === "verified_private_local_blueprint_revision_draft",
      "unsafe private blueprint draft review: verified revision draft required",
    );
    assertSafeKeys(reviewInput, "private blueprint draft review input");
    requireExactKeys(reviewInput, ["reviewerLabel", "decision", "reasonCode"], "private blueprint draft review input");
    requireValue(
      typeof reviewInput.reviewerLabel === "string"
        && reviewInput.reviewerLabel.trim() === reviewInput.reviewerLabel
        && reviewInput.reviewerLabel.length > 0
        && reviewInput.reviewerLabel.length <= 36,
      "unsafe private blueprint draft review: reviewer label drift",
    );
    const allowedReasons = PRIVATE_BLUEPRINT_DRAFT_REVIEW_REASONS[reviewInput.decision];
    requireValue(Array.isArray(allowedReasons), "unsafe private blueprint draft review: unknown decision");
    requireValue(allowedReasons.includes(reviewInput.reasonCode), "unsafe private blueprint draft review: decision reason drift");
    const draftBinding = privateBlueprintDraftReviewBinding(draftVerification);
    const localCommitCandidate = reviewInput.decision === "accept_for_commit_candidate"
      ? await proposedPrivateBlueprintCommitCandidate(draftVerification, draftBinding)
      : null;
    const hasUnknownGuards = draftVerification.draft.unknownGuardKeys.length > 0;
    const review = {
      reviewStatus: "private_local_blueprint_revision_draft_review",
      decision: reviewInput.decision,
      reasonCode: reviewInput.reasonCode,
      reviewer: {
        label: reviewInput.reviewerLabel,
        identityAttested: false,
        localOnly: true,
      },
      draftBinding,
      localCommitCandidate,
      state: {
        localOnly: true,
        committed: false,
        adopted: false,
        commitCandidateCreated: localCommitCandidate !== null,
        commitReadinessStatus: localCommitCandidate?.commitReadinessStatus || "not_requested",
        qualificationStatus: "not_run",
        played: false,
        executionStatus: "disabled",
        registryStatus: "not_requested",
        publicationStatus: "not_requested",
      },
      blockers: PRIVATE_BLUEPRINT_DRAFT_REVIEW_BLOCKERS.filter(
        (blocker) => hasUnknownGuards || blocker !== "unknown_guard_values_block_commit_readiness",
      ),
      authority: privateBlueprintDeltaAuthority(),
      boundary: PRIVATE_BLUEPRINT_DRAFT_REVIEW_BOUNDARY,
    };
    const reviewDigest = await sha256Hex(canonicalJSON(review));
    return { ...review, reviewDigest };
  }

  async function createPortablePrivateBlueprintDraftReview(serializedDraftInput, reviewInput) {
    const draftVerification = await verifyPortablePrivateBlueprintRevisionDraft(serializedDraftInput);
    const review = await buildPortablePrivateBlueprintDraftReviewRecord(draftVerification, reviewInput);
    const payload = {
      blueprintRevisionDraft: JSON.parse(serializedDraftInput),
      review,
    };
    const payloadDigest = await sha256Hex(canonicalJSON(payload));
    const binding = review.draftBinding;
    const packet = {
      schemaVersion: PRIVATE_BLUEPRINT_DRAFT_REVIEW_SCHEMA,
      reviewVersion: 1,
      payload,
      integrity: {
        algorithm: "sha256",
        payloadDigest,
        draftPacketDigest: binding.draftPacketDigest,
        draftDigest: binding.draftDigest,
        acceptedReviewPacketDigest: binding.acceptedReviewPacketDigest,
        guardProposalPacketDigest: binding.guardProposalPacketDigest,
        parentProposalPayloadDigest: binding.parentProposalPayloadDigest,
        selectedReviewDigest: binding.selectedReviewDigest,
        reviewDigest: review.reviewDigest,
        commitCandidateDigest: review.localCommitCandidate?.candidateDigest || null,
      },
      boundary: PRIVATE_BLUEPRINT_DRAFT_REVIEW_BOUNDARY,
    };
    const serialized = canonicalJSON(packet);
    requireValue(serialized.length <= PRIVATE_BLUEPRINT_DRAFT_REVIEW_MAX_LENGTH, "unsafe private blueprint draft review: packet length rejected");
    return { packet: clone(packet), serialized };
  }

  async function verifyPortablePrivateBlueprintDraftReview(serializedInput) {
    requireValue(
      typeof serializedInput === "string"
        && serializedInput.length > 0
        && serializedInput.length <= PRIVATE_BLUEPRINT_DRAFT_REVIEW_MAX_LENGTH,
      "unsafe private blueprint draft review: input length rejected",
    );
    let packet;
    try {
      packet = JSON.parse(serializedInput);
    } catch {
      throw new Error("unsafe private blueprint draft review: invalid JSON");
    }
    assertSafeKeys(packet, "private blueprint draft review", 0, { nodes: 0 }, PRIVATE_BLUEPRINT_DRAFT_REVIEW_NODE_LIMIT);
    requireExactKeys(packet, ["schemaVersion", "reviewVersion", "payload", "integrity", "boundary"], "private blueprint draft review");
    requireValue(packet.schemaVersion === PRIVATE_BLUEPRINT_DRAFT_REVIEW_SCHEMA && packet.reviewVersion === 1, "unsafe private blueprint draft review: schema drift");
    requireValue(packet.boundary === PRIVATE_BLUEPRINT_DRAFT_REVIEW_BOUNDARY, "unsafe private blueprint draft review: boundary drift");
    requireValue(serializedInput === canonicalJSON(packet), "unsafe private blueprint draft review: packet must use canonical JSON");
    requireExactKeys(packet.payload, ["blueprintRevisionDraft", "review"], "private blueprint draft review payload");
    requireExactKeys(packet.integrity, [
      "algorithm", "payloadDigest", "draftPacketDigest", "draftDigest", "acceptedReviewPacketDigest",
      "guardProposalPacketDigest", "parentProposalPayloadDigest", "selectedReviewDigest", "reviewDigest", "commitCandidateDigest",
    ], "private blueprint draft review integrity");
    requireValue(packet.integrity.algorithm === "sha256", "unsafe private blueprint draft review: integrity algorithm drift");
    for (const key of [
      "payloadDigest", "draftPacketDigest", "draftDigest", "acceptedReviewPacketDigest",
      "guardProposalPacketDigest", "parentProposalPayloadDigest", "selectedReviewDigest", "reviewDigest",
    ]) requireValue(HEX64.test(packet.integrity[key]), `unsafe private blueprint draft review: ${key} drift`);
    requireValue(packet.integrity.commitCandidateDigest === null || HEX64.test(packet.integrity.commitCandidateDigest), "unsafe private blueprint draft review: commitCandidateDigest drift");

    requireValue(isObject(packet.payload.review), "unsafe private blueprint draft review: review record drift");
    requireExactKeys(packet.payload.review, [
      "reviewStatus", "decision", "reasonCode", "reviewer", "draftBinding", "localCommitCandidate",
      "state", "blockers", "authority", "boundary", "reviewDigest",
    ], "private blueprint draft review record");
    requireValue(isObject(packet.payload.review.reviewer), "unsafe private blueprint draft review: reviewer drift");
    requireExactKeys(packet.payload.review.reviewer, ["label", "identityAttested", "localOnly"], "private blueprint draft review reviewer");
    const draftSerialized = canonicalJSON(packet.payload.blueprintRevisionDraft);
    const draftVerification = await verifyPortablePrivateBlueprintRevisionDraft(draftSerialized);
    const expectedReview = await buildPortablePrivateBlueprintDraftReviewRecord(draftVerification, {
      reviewerLabel: packet.payload.review.reviewer.label,
      decision: packet.payload.review.decision,
      reasonCode: packet.payload.review.reasonCode,
    });
    requireValue(canonicalJSON(packet.payload.review) === canonicalJSON(expectedReview), "unsafe private blueprint draft review: review projection mismatch");
    const binding = expectedReview.draftBinding;
    requireValue(equalHex(binding.draftPacketDigest, packet.integrity.draftPacketDigest), "unsafe private blueprint draft review: draft packet digest binding mismatch");
    requireValue(equalHex(binding.draftDigest, packet.integrity.draftDigest), "unsafe private blueprint draft review: draft digest binding mismatch");
    requireValue(equalHex(binding.acceptedReviewPacketDigest, packet.integrity.acceptedReviewPacketDigest), "unsafe private blueprint draft review: accepted review packet digest binding mismatch");
    requireValue(equalHex(binding.guardProposalPacketDigest, packet.integrity.guardProposalPacketDigest), "unsafe private blueprint draft review: guard proposal packet digest binding mismatch");
    requireValue(equalHex(binding.parentProposalPayloadDigest, packet.integrity.parentProposalPayloadDigest), "unsafe private blueprint draft review: parent proposal digest binding mismatch");
    requireValue(equalHex(binding.selectedReviewDigest, packet.integrity.selectedReviewDigest), "unsafe private blueprint draft review: selected review digest binding mismatch");
    requireValue(equalHex(expectedReview.reviewDigest, packet.integrity.reviewDigest), "unsafe private blueprint draft review: review digest binding mismatch");
    if (expectedReview.localCommitCandidate) {
      requireValue(equalHex(expectedReview.localCommitCandidate.candidateDigest, packet.integrity.commitCandidateDigest), "unsafe private blueprint draft review: commit candidate digest binding mismatch");
    } else {
      requireValue(packet.integrity.commitCandidateDigest === null, "unsafe private blueprint draft review: unexpected commit candidate digest");
    }
    const computedPayloadDigest = await sha256Hex(canonicalJSON(packet.payload));
    requireValue(equalHex(computedPayloadDigest, packet.integrity.payloadDigest), "unsafe private blueprint draft review: payload digest mismatch");
    return {
      schemaVersion: PRIVATE_BLUEPRINT_DRAFT_REVIEW_SCHEMA,
      verificationStatus: "verified_private_local_blueprint_revision_draft_review",
      packetDigest: computedPayloadDigest,
      draftSerialized,
      draftVerification,
      review: clone(expectedReview),
      boundary: PRIVATE_BLUEPRINT_DRAFT_REVIEW_BOUNDARY,
    };
  }

  function privateBlueprintGuardCompletionBinding(draftReviewVerification) {
    const review = draftReviewVerification.review;
    const candidate = review.localCommitCandidate;
    return {
      draftReviewPacketDigest: draftReviewVerification.packetDigest,
      draftReviewDigest: review.reviewDigest,
      commitCandidateDigest: candidate.candidateDigest,
      commitCandidateKey: candidate.candidateKey,
      draftPacketDigest: review.draftBinding.draftPacketDigest,
      draftDigest: review.draftBinding.draftDigest,
      acceptedReviewPacketDigest: review.draftBinding.acceptedReviewPacketDigest,
      acceptedReviewDigest: review.draftBinding.acceptedReviewDigest,
      guardProposalPacketDigest: review.draftBinding.guardProposalPacketDigest,
      parentProposalPayloadDigest: review.draftBinding.parentProposalPayloadDigest,
      selectedReviewDigest: review.draftBinding.selectedReviewDigest,
      appliedGuardId: review.draftBinding.appliedGuardId,
    };
  }

  function privateBlueprintGuardDefinition(guardKey) {
    return RUNBACK_DELTAS.find((guard) => guard.guardKey === guardKey) || null;
  }

  async function buildPortablePrivateBlueprintGuardCompletionRecord(draftReviewVerification, completionInput) {
    requireValue(
      isObject(draftReviewVerification)
        && draftReviewVerification.schemaVersion === PRIVATE_BLUEPRINT_DRAFT_REVIEW_SCHEMA
        && draftReviewVerification.verificationStatus === "verified_private_local_blueprint_revision_draft_review",
      "unsafe private blueprint guard completion: verified draft review required",
    );
    const review = draftReviewVerification.review;
    requireValue(
      review.decision === "accept_for_commit_candidate"
        && isObject(review.localCommitCandidate)
        && review.localCommitCandidate.status === "proposed_uncommitted_local_blueprint_commit_candidate",
      "unsafe private blueprint guard completion: accepted draft review required",
    );
    const candidate = review.localCommitCandidate;
    requireValue(candidate.commitReady === false && candidate.committed === false && candidate.adopted === false, "unsafe private blueprint guard completion: source candidate state drift");
    requireValue(Array.isArray(candidate.unknownGuardKeys) && candidate.unknownGuardKeys.length > 0, "unsafe private blueprint guard completion: explicit unknown guard keys required");
    assertSafeKeys(completionInput, "private blueprint guard completion input");
    requireExactKeys(completionInput, ["reviewerLabel", "reasonCode", "guardCompletions"], "private blueprint guard completion input");
    requireValue(
      typeof completionInput.reviewerLabel === "string"
        && completionInput.reviewerLabel.trim() === completionInput.reviewerLabel
        && completionInput.reviewerLabel.length > 0
        && completionInput.reviewerLabel.length <= 36,
      "unsafe private blueprint guard completion: reviewer label drift",
    );
    requireValue(PRIVATE_BLUEPRINT_GUARD_COMPLETION_REASONS.includes(completionInput.reasonCode), "unsafe private blueprint guard completion: reason drift");
    requireValue(Array.isArray(completionInput.guardCompletions), "unsafe private blueprint guard completion: guard completions drift");
    requireValue(completionInput.guardCompletions.length === candidate.unknownGuardKeys.length, "unsafe private blueprint guard completion: exact unknown guard set required");

    const guardCompletions = completionInput.guardCompletions.map((completion, index) => {
      assertSafeKeys(completion, "private blueprint guard completion entry");
      requireExactKeys(completion, ["guardKey", "value", "provenanceCode"], "private blueprint guard completion entry");
      const expectedGuardKey = candidate.unknownGuardKeys[index];
      requireValue(completion.guardKey === expectedGuardKey, "unsafe private blueprint guard completion: exact unknown guard order required");
      const guard = privateBlueprintGuardDefinition(completion.guardKey);
      requireValue(guard !== null && candidate.blueprint.guardValues[completion.guardKey] === null, "unsafe private blueprint guard completion: unknown guard binding drift");
      requireValue(typeof completion.value === "boolean", "unsafe private blueprint guard completion: boolean guard value required");
      requireValue(PRIVATE_BLUEPRINT_GUARD_COMPLETION_PROVENANCE_CODES.includes(completion.provenanceCode), "unsafe private blueprint guard completion: provenance code drift");
      return {
        guardKey: completion.guardKey,
        label: guard.label,
        value: completion.value,
        provenance: {
          code: completion.provenanceCode,
          reviewerLabel: completionInput.reviewerLabel,
          identityAttested: false,
          localOnly: true,
        },
      };
    });

    const completedBlueprint = clone(candidate.blueprint);
    for (const completion of guardCompletions) completedBlueprint.guardValues[completion.guardKey] = completion.value;
    const parentBinding = privateBlueprintGuardCompletionBinding(draftReviewVerification);
    const record = {
      proposalStatus: "proposed_uncommitted_local_blueprint_guard_completion",
      proposalKey: [
        "private-blueprint-guard-completion-v1",
        parentBinding.draftReviewPacketDigest,
        parentBinding.commitCandidateDigest,
        ...guardCompletions.map((completion) => `${encodeURIComponent(completion.guardKey)}=${completion.value}`),
      ].join(":"),
      reasonCode: completionInput.reasonCode,
      reviewer: {
        label: completionInput.reviewerLabel,
        identityAttested: false,
        localOnly: true,
      },
      parentBinding,
      sourceBlueprint: clone(candidate.blueprint),
      guardCompletions,
      completedBlueprint,
      remainingUnknownGuardKeys: [],
      guardCompletionStatus: "proposed_complete_guard_values",
      completionReviewStatus: "not_run",
      state: {
        localOnly: true,
        committed: false,
        adopted: false,
        commitReady: false,
        commitReadinessStatus: "requires_guard_completion_review",
        qualificationStatus: "not_run",
        played: false,
        executionStatus: "disabled",
        registryStatus: "not_requested",
        publicationStatus: "not_requested",
      },
      blockers: clone(PRIVATE_BLUEPRINT_GUARD_COMPLETION_BLOCKERS),
      authority: privateBlueprintDeltaAuthority(),
      boundary: PRIVATE_BLUEPRINT_GUARD_COMPLETION_BOUNDARY,
    };
    const completionDigest = await sha256Hex(canonicalJSON(record));
    return { ...record, completionDigest };
  }

  async function createPortablePrivateBlueprintGuardCompletion(serializedDraftReviewInput, completionInput) {
    const draftReviewVerification = await verifyPortablePrivateBlueprintDraftReview(serializedDraftReviewInput);
    const completionProposal = await buildPortablePrivateBlueprintGuardCompletionRecord(draftReviewVerification, completionInput);
    const binding = completionProposal.parentBinding;
    const payload = {
      acceptedDraftReviewReceipt: JSON.parse(serializedDraftReviewInput),
      completionProposal,
    };
    const payloadDigest = await sha256Hex(canonicalJSON(payload));
    const packet = {
      schemaVersion: PRIVATE_BLUEPRINT_GUARD_COMPLETION_SCHEMA,
      proposalVersion: 1,
      payload,
      integrity: {
        algorithm: "sha256",
        payloadDigest,
        draftReviewPacketDigest: binding.draftReviewPacketDigest,
        draftReviewDigest: binding.draftReviewDigest,
        commitCandidateDigest: binding.commitCandidateDigest,
        draftPacketDigest: binding.draftPacketDigest,
        draftDigest: binding.draftDigest,
        acceptedReviewPacketDigest: binding.acceptedReviewPacketDigest,
        acceptedReviewDigest: binding.acceptedReviewDigest,
        guardProposalPacketDigest: binding.guardProposalPacketDigest,
        parentProposalPayloadDigest: binding.parentProposalPayloadDigest,
        selectedReviewDigest: binding.selectedReviewDigest,
        completionDigest: completionProposal.completionDigest,
      },
      boundary: PRIVATE_BLUEPRINT_GUARD_COMPLETION_BOUNDARY,
    };
    const serialized = canonicalJSON(packet);
    requireValue(serialized.length <= PRIVATE_BLUEPRINT_GUARD_COMPLETION_MAX_LENGTH, "unsafe private blueprint guard completion: packet length rejected");
    return { packet: clone(packet), serialized };
  }

  async function verifyPortablePrivateBlueprintGuardCompletion(serializedInput) {
    requireValue(
      typeof serializedInput === "string"
        && serializedInput.length > 0
        && serializedInput.length <= PRIVATE_BLUEPRINT_GUARD_COMPLETION_MAX_LENGTH,
      "unsafe private blueprint guard completion: input length rejected",
    );
    let packet;
    try {
      packet = JSON.parse(serializedInput);
    } catch {
      throw new Error("unsafe private blueprint guard completion: invalid JSON");
    }
    assertSafeKeys(packet, "private blueprint guard completion", 0, { nodes: 0 }, PRIVATE_BLUEPRINT_GUARD_COMPLETION_NODE_LIMIT);
    requireExactKeys(packet, ["schemaVersion", "proposalVersion", "payload", "integrity", "boundary"], "private blueprint guard completion");
    requireValue(packet.schemaVersion === PRIVATE_BLUEPRINT_GUARD_COMPLETION_SCHEMA && packet.proposalVersion === 1, "unsafe private blueprint guard completion: schema drift");
    requireValue(packet.boundary === PRIVATE_BLUEPRINT_GUARD_COMPLETION_BOUNDARY, "unsafe private blueprint guard completion: boundary drift");
    requireValue(serializedInput === canonicalJSON(packet), "unsafe private blueprint guard completion: packet must use canonical JSON");
    requireExactKeys(packet.payload, ["acceptedDraftReviewReceipt", "completionProposal"], "private blueprint guard completion payload");
    requireExactKeys(packet.integrity, [
      "algorithm", "payloadDigest", "draftReviewPacketDigest", "draftReviewDigest", "commitCandidateDigest",
      "draftPacketDigest", "draftDigest", "acceptedReviewPacketDigest", "acceptedReviewDigest",
      "guardProposalPacketDigest", "parentProposalPayloadDigest", "selectedReviewDigest", "completionDigest",
    ], "private blueprint guard completion integrity");
    requireValue(packet.integrity.algorithm === "sha256", "unsafe private blueprint guard completion: integrity algorithm drift");
    for (const key of [
      "payloadDigest", "draftReviewPacketDigest", "draftReviewDigest", "commitCandidateDigest", "draftPacketDigest",
      "draftDigest", "acceptedReviewPacketDigest", "acceptedReviewDigest", "guardProposalPacketDigest",
      "parentProposalPayloadDigest", "selectedReviewDigest", "completionDigest",
    ]) requireValue(HEX64.test(packet.integrity[key]), `unsafe private blueprint guard completion: ${key} drift`);

    const completionProposal = packet.payload.completionProposal;
    requireValue(isObject(completionProposal), "unsafe private blueprint guard completion: proposal record drift");
    requireExactKeys(completionProposal, [
      "proposalStatus", "proposalKey", "reasonCode", "reviewer", "parentBinding", "sourceBlueprint",
      "guardCompletions", "completedBlueprint", "remainingUnknownGuardKeys", "guardCompletionStatus",
      "completionReviewStatus", "state", "blockers", "authority", "boundary", "completionDigest",
    ], "private blueprint guard completion proposal");
    requireValue(isObject(completionProposal.reviewer), "unsafe private blueprint guard completion: reviewer drift");
    requireExactKeys(completionProposal.reviewer, ["label", "identityAttested", "localOnly"], "private blueprint guard completion reviewer");
    requireValue(Array.isArray(completionProposal.guardCompletions), "unsafe private blueprint guard completion: guard completions drift");
    const draftReviewSerialized = canonicalJSON(packet.payload.acceptedDraftReviewReceipt);
    const draftReviewVerification = await verifyPortablePrivateBlueprintDraftReview(draftReviewSerialized);
    const expectedCompletion = await buildPortablePrivateBlueprintGuardCompletionRecord(draftReviewVerification, {
      reviewerLabel: completionProposal.reviewer.label,
      reasonCode: completionProposal.reasonCode,
      guardCompletions: completionProposal.guardCompletions.map((completion) => ({
        guardKey: completion.guardKey,
        value: completion.value,
        provenanceCode: completion.provenance?.code,
      })),
    });
    requireValue(canonicalJSON(completionProposal) === canonicalJSON(expectedCompletion), "unsafe private blueprint guard completion: proposal projection mismatch");
    const binding = expectedCompletion.parentBinding;
    for (const [integrityKey, bindingKey, message] of [
      ["draftReviewPacketDigest", "draftReviewPacketDigest", "draft review packet digest binding mismatch"],
      ["draftReviewDigest", "draftReviewDigest", "draft review digest binding mismatch"],
      ["commitCandidateDigest", "commitCandidateDigest", "commit candidate digest binding mismatch"],
      ["draftPacketDigest", "draftPacketDigest", "draft packet digest binding mismatch"],
      ["draftDigest", "draftDigest", "draft digest binding mismatch"],
      ["acceptedReviewPacketDigest", "acceptedReviewPacketDigest", "accepted review packet digest binding mismatch"],
      ["acceptedReviewDigest", "acceptedReviewDigest", "accepted review digest binding mismatch"],
      ["guardProposalPacketDigest", "guardProposalPacketDigest", "guard proposal packet digest binding mismatch"],
      ["parentProposalPayloadDigest", "parentProposalPayloadDigest", "parent proposal digest binding mismatch"],
      ["selectedReviewDigest", "selectedReviewDigest", "selected review digest binding mismatch"],
    ]) requireValue(equalHex(binding[bindingKey], packet.integrity[integrityKey]), `unsafe private blueprint guard completion: ${message}`);
    requireValue(equalHex(expectedCompletion.completionDigest, packet.integrity.completionDigest), "unsafe private blueprint guard completion: completion digest binding mismatch");
    const computedPayloadDigest = await sha256Hex(canonicalJSON(packet.payload));
    requireValue(equalHex(computedPayloadDigest, packet.integrity.payloadDigest), "unsafe private blueprint guard completion: payload digest mismatch");
    return {
      schemaVersion: PRIVATE_BLUEPRINT_GUARD_COMPLETION_SCHEMA,
      verificationStatus: "verified_private_local_blueprint_guard_completion_proposal",
      packetDigest: computedPayloadDigest,
      draftReviewSerialized,
      draftReviewVerification,
      completionProposal: clone(expectedCompletion),
      boundary: PRIVATE_BLUEPRINT_GUARD_COMPLETION_BOUNDARY,
    };
  }

  function privateBlueprintGuardCompletionReviewBinding(completionVerification) {
    const completion = completionVerification.completionProposal;
    return {
      completionPacketDigest: completionVerification.packetDigest,
      completionDigest: completion.completionDigest,
      completionKey: completion.proposalKey,
      draftReviewPacketDigest: completion.parentBinding.draftReviewPacketDigest,
      draftReviewDigest: completion.parentBinding.draftReviewDigest,
      commitCandidateDigest: completion.parentBinding.commitCandidateDigest,
      draftPacketDigest: completion.parentBinding.draftPacketDigest,
      acceptedReviewPacketDigest: completion.parentBinding.acceptedReviewPacketDigest,
      guardProposalPacketDigest: completion.parentBinding.guardProposalPacketDigest,
      parentProposalPayloadDigest: completion.parentBinding.parentProposalPayloadDigest,
      selectedReviewDigest: completion.parentBinding.selectedReviewDigest,
    };
  }

  async function proposedPrivateBlueprintCommitReviewCandidate(completionVerification, binding) {
    const completion = completionVerification.completionProposal;
    const record = {
      status: "proposed_local_blueprint_candidate_for_operator_commit_review",
      candidateKey: [
        "private-blueprint-operator-commit-review-candidate-v1",
        binding.completionPacketDigest,
        binding.completionDigest,
      ].join(":"),
      parentCompletionKey: binding.completionKey,
      parentCompletionDigest: binding.completionDigest,
      blueprint: clone(completion.completedBlueprint),
      guardCompletions: clone(completion.guardCompletions),
      guardCompletionStatus: "verified_complete_guard_values",
      completionReviewStatus: "accepted_for_operator_commit_review",
      commitReadinessStatus: "requires_operator_commit_review",
      operatorReviewStatus: "not_run",
      localOnly: true,
      committed: false,
      adopted: false,
      commitReady: false,
      qualificationStatus: "not_run",
      played: false,
      executionStatus: "disabled",
      registryStatus: "not_requested",
      publicationStatus: "not_requested",
      blockers: clone(PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_BLOCKERS),
      authority: privateBlueprintDeltaAuthority(),
      boundary: PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_BOUNDARY,
    };
    const candidateDigest = await sha256Hex(canonicalJSON(record));
    return { ...record, candidateDigest };
  }

  async function buildPortablePrivateBlueprintGuardCompletionReviewRecord(completionVerification, reviewInput) {
    requireValue(
      isObject(completionVerification)
        && completionVerification.schemaVersion === PRIVATE_BLUEPRINT_GUARD_COMPLETION_SCHEMA
        && completionVerification.verificationStatus === "verified_private_local_blueprint_guard_completion_proposal",
      "unsafe private blueprint guard completion review: verified guard completion required",
    );
    const completion = completionVerification.completionProposal;
    requireValue(
      completion.guardCompletionStatus === "proposed_complete_guard_values"
        && completion.completionReviewStatus === "not_run"
        && completion.remainingUnknownGuardKeys.length === 0
        && completion.state.commitReady === false
        && completion.state.committed === false
        && completion.state.adopted === false,
      "unsafe private blueprint guard completion review: complete unreviewed proposal required",
    );
    assertSafeKeys(reviewInput, "private blueprint guard completion review input");
    requireExactKeys(reviewInput, ["reviewerLabel", "decision", "reasonCode"], "private blueprint guard completion review input");
    requireValue(
      typeof reviewInput.reviewerLabel === "string"
        && reviewInput.reviewerLabel.trim() === reviewInput.reviewerLabel
        && reviewInput.reviewerLabel.length > 0
        && reviewInput.reviewerLabel.length <= 36,
      "unsafe private blueprint guard completion review: reviewer label drift",
    );
    const allowedReasons = PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_REASONS[reviewInput.decision];
    requireValue(Array.isArray(allowedReasons), "unsafe private blueprint guard completion review: unknown decision");
    requireValue(allowedReasons.includes(reviewInput.reasonCode), "unsafe private blueprint guard completion review: decision reason drift");
    const completionBinding = privateBlueprintGuardCompletionReviewBinding(completionVerification);
    const localCommitReviewCandidate = reviewInput.decision === "accept_for_commit_review"
      ? await proposedPrivateBlueprintCommitReviewCandidate(completionVerification, completionBinding)
      : null;
    const completionReviewStatus = reviewInput.decision === "accept_for_commit_review"
      ? "accepted_for_operator_commit_review"
      : reviewInput.decision === "defer"
        ? "deferred_private_review"
        : "rejected_private_review";
    const review = {
      reviewStatus: "private_local_blueprint_guard_completion_review",
      decision: reviewInput.decision,
      reasonCode: reviewInput.reasonCode,
      reviewer: {
        label: reviewInput.reviewerLabel,
        identityAttested: false,
        localOnly: true,
      },
      completionBinding,
      localCommitReviewCandidate,
      state: {
        localOnly: true,
        committed: false,
        adopted: false,
        commitReviewCandidateCreated: localCommitReviewCandidate !== null,
        completionReviewStatus,
        commitReadinessStatus: localCommitReviewCandidate?.commitReadinessStatus || "not_requested",
        operatorReviewStatus: "not_run",
        qualificationStatus: "not_run",
        played: false,
        executionStatus: "disabled",
        registryStatus: "not_requested",
        publicationStatus: "not_requested",
      },
      blockers: clone(PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_BLOCKERS),
      authority: privateBlueprintDeltaAuthority(),
      boundary: PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_BOUNDARY,
    };
    const reviewDigest = await sha256Hex(canonicalJSON(review));
    return { ...review, reviewDigest };
  }

  async function createPortablePrivateBlueprintGuardCompletionReview(serializedCompletionInput, reviewInput) {
    const completionVerification = await verifyPortablePrivateBlueprintGuardCompletion(serializedCompletionInput);
    const review = await buildPortablePrivateBlueprintGuardCompletionReviewRecord(completionVerification, reviewInput);
    const binding = review.completionBinding;
    const payload = {
      guardCompletionProposal: JSON.parse(serializedCompletionInput),
      review,
    };
    const payloadDigest = await sha256Hex(canonicalJSON(payload));
    const packet = {
      schemaVersion: PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_SCHEMA,
      reviewVersion: 1,
      payload,
      integrity: {
        algorithm: "sha256",
        payloadDigest,
        completionPacketDigest: binding.completionPacketDigest,
        completionDigest: binding.completionDigest,
        draftReviewPacketDigest: binding.draftReviewPacketDigest,
        commitCandidateDigest: binding.commitCandidateDigest,
        draftPacketDigest: binding.draftPacketDigest,
        acceptedReviewPacketDigest: binding.acceptedReviewPacketDigest,
        guardProposalPacketDigest: binding.guardProposalPacketDigest,
        parentProposalPayloadDigest: binding.parentProposalPayloadDigest,
        selectedReviewDigest: binding.selectedReviewDigest,
        reviewDigest: review.reviewDigest,
        candidateDigest: review.localCommitReviewCandidate?.candidateDigest || null,
      },
      boundary: PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_BOUNDARY,
    };
    const serialized = canonicalJSON(packet);
    requireValue(serialized.length <= PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_MAX_LENGTH, "unsafe private blueprint guard completion review: packet length rejected");
    return { packet: clone(packet), serialized };
  }

  async function verifyPortablePrivateBlueprintGuardCompletionReview(serializedInput) {
    requireValue(
      typeof serializedInput === "string"
        && serializedInput.length > 0
        && serializedInput.length <= PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_MAX_LENGTH,
      "unsafe private blueprint guard completion review: input length rejected",
    );
    let packet;
    try {
      packet = JSON.parse(serializedInput);
    } catch {
      throw new Error("unsafe private blueprint guard completion review: invalid JSON");
    }
    assertSafeKeys(packet, "private blueprint guard completion review", 0, { nodes: 0 }, PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_NODE_LIMIT);
    requireExactKeys(packet, ["schemaVersion", "reviewVersion", "payload", "integrity", "boundary"], "private blueprint guard completion review");
    requireValue(packet.schemaVersion === PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_SCHEMA && packet.reviewVersion === 1, "unsafe private blueprint guard completion review: schema drift");
    requireValue(packet.boundary === PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_BOUNDARY, "unsafe private blueprint guard completion review: boundary drift");
    requireValue(serializedInput === canonicalJSON(packet), "unsafe private blueprint guard completion review: packet must use canonical JSON");
    requireExactKeys(packet.payload, ["guardCompletionProposal", "review"], "private blueprint guard completion review payload");
    requireExactKeys(packet.integrity, [
      "algorithm", "payloadDigest", "completionPacketDigest", "completionDigest", "draftReviewPacketDigest",
      "commitCandidateDigest", "draftPacketDigest", "acceptedReviewPacketDigest", "guardProposalPacketDigest",
      "parentProposalPayloadDigest", "selectedReviewDigest", "reviewDigest", "candidateDigest",
    ], "private blueprint guard completion review integrity");
    requireValue(packet.integrity.algorithm === "sha256", "unsafe private blueprint guard completion review: integrity algorithm drift");
    for (const key of [
      "payloadDigest", "completionPacketDigest", "completionDigest", "draftReviewPacketDigest", "commitCandidateDigest",
      "draftPacketDigest", "acceptedReviewPacketDigest", "guardProposalPacketDigest", "parentProposalPayloadDigest",
      "selectedReviewDigest", "reviewDigest",
    ]) requireValue(HEX64.test(packet.integrity[key]), `unsafe private blueprint guard completion review: ${key} drift`);
    requireValue(packet.integrity.candidateDigest === null || HEX64.test(packet.integrity.candidateDigest), "unsafe private blueprint guard completion review: candidateDigest drift");

    requireValue(isObject(packet.payload.review), "unsafe private blueprint guard completion review: review record drift");
    requireExactKeys(packet.payload.review, [
      "reviewStatus", "decision", "reasonCode", "reviewer", "completionBinding", "localCommitReviewCandidate",
      "state", "blockers", "authority", "boundary", "reviewDigest",
    ], "private blueprint guard completion review record");
    requireValue(isObject(packet.payload.review.reviewer), "unsafe private blueprint guard completion review: reviewer drift");
    requireExactKeys(packet.payload.review.reviewer, ["label", "identityAttested", "localOnly"], "private blueprint guard completion review reviewer");
    const completionSerialized = canonicalJSON(packet.payload.guardCompletionProposal);
    const completionVerification = await verifyPortablePrivateBlueprintGuardCompletion(completionSerialized);
    const expectedReview = await buildPortablePrivateBlueprintGuardCompletionReviewRecord(completionVerification, {
      reviewerLabel: packet.payload.review.reviewer.label,
      decision: packet.payload.review.decision,
      reasonCode: packet.payload.review.reasonCode,
    });
    requireValue(canonicalJSON(packet.payload.review) === canonicalJSON(expectedReview), "unsafe private blueprint guard completion review: review projection mismatch");
    const binding = expectedReview.completionBinding;
    for (const [integrityKey, bindingKey, message] of [
      ["completionPacketDigest", "completionPacketDigest", "completion packet digest binding mismatch"],
      ["completionDigest", "completionDigest", "completion digest binding mismatch"],
      ["draftReviewPacketDigest", "draftReviewPacketDigest", "draft review packet digest binding mismatch"],
      ["commitCandidateDigest", "commitCandidateDigest", "commit candidate digest binding mismatch"],
      ["draftPacketDigest", "draftPacketDigest", "draft packet digest binding mismatch"],
      ["acceptedReviewPacketDigest", "acceptedReviewPacketDigest", "accepted review packet digest binding mismatch"],
      ["guardProposalPacketDigest", "guardProposalPacketDigest", "guard proposal packet digest binding mismatch"],
      ["parentProposalPayloadDigest", "parentProposalPayloadDigest", "parent proposal digest binding mismatch"],
      ["selectedReviewDigest", "selectedReviewDigest", "selected review digest binding mismatch"],
    ]) requireValue(equalHex(binding[bindingKey], packet.integrity[integrityKey]), `unsafe private blueprint guard completion review: ${message}`);
    requireValue(equalHex(expectedReview.reviewDigest, packet.integrity.reviewDigest), "unsafe private blueprint guard completion review: review digest binding mismatch");
    if (expectedReview.localCommitReviewCandidate) {
      requireValue(equalHex(expectedReview.localCommitReviewCandidate.candidateDigest, packet.integrity.candidateDigest), "unsafe private blueprint guard completion review: candidate digest binding mismatch");
    } else {
      requireValue(packet.integrity.candidateDigest === null, "unsafe private blueprint guard completion review: unexpected candidate digest");
    }
    const computedPayloadDigest = await sha256Hex(canonicalJSON(packet.payload));
    requireValue(equalHex(computedPayloadDigest, packet.integrity.payloadDigest), "unsafe private blueprint guard completion review: payload digest mismatch");
    return {
      schemaVersion: PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_SCHEMA,
      verificationStatus: "verified_private_local_blueprint_guard_completion_review",
      packetDigest: computedPayloadDigest,
      guardCompletionSerialized: completionSerialized,
      guardCompletionVerification: completionVerification,
      review: clone(expectedReview),
      boundary: PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_BOUNDARY,
    };
  }

  async function buildPortablePrivateBlueprintOperatorReviewPacketRecord(reviewVerification) {
    requireValue(
      isObject(reviewVerification)
        && reviewVerification.schemaVersion === PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_SCHEMA
        && reviewVerification.verificationStatus === "verified_private_local_blueprint_guard_completion_review",
      "unsafe private blueprint operator review packet: verified guard completion review required",
    );
    const review = reviewVerification.review;
    requireValue(
      review.decision === "accept_for_commit_review"
        && review.state.operatorReviewStatus === "not_run"
        && isObject(review.localCommitReviewCandidate)
        && review.localCommitReviewCandidate.status === "proposed_local_blueprint_candidate_for_operator_commit_review",
      "unsafe private blueprint operator review packet: accepted completion review required",
    );
    const candidate = review.localCommitReviewCandidate;
    requireValue(
      candidate.localOnly === true
        && candidate.commitReady === false
        && candidate.committed === false
        && candidate.adopted === false
        && candidate.operatorReviewStatus === "not_run"
        && candidate.qualificationStatus === "not_run"
        && candidate.played === false
        && candidate.executionStatus === "disabled"
        && candidate.registryStatus === "not_requested"
        && candidate.publicationStatus === "not_requested",
      "unsafe private blueprint operator review packet: local candidate state drift",
    );

    const completionVerification = reviewVerification.guardCompletionVerification;
    const completion = completionVerification.completionProposal;
    const draft = completionVerification.draftReviewVerification.draftVerification.draft;
    const sourceBlueprint = {
      agentName: draft.parentBlueprint.agentName,
      declaredBase: draft.parentBlueprint.declaredBase,
      harnessStyle: draft.parentBlueprint.harnessStyle,
      localOnly: true,
      guardValues: clone(draft.parentGuardValues),
    };
    const candidateBlueprint = clone(candidate.blueprint);
    requireValue(
      sourceBlueprint.agentName === candidateBlueprint.agentName
        && sourceBlueprint.declaredBase === candidateBlueprint.declaredBase
        && sourceBlueprint.harnessStyle === candidateBlueprint.harnessStyle
        && sourceBlueprint.localOnly === true
        && candidateBlueprint.localOnly === true,
      "unsafe private blueprint operator review packet: blueprint identity drift",
    );
    requireValue(
      Object.keys(candidateBlueprint.guardValues).sort().join("|") === RUNBACK_DELTAS.map((guard) => guard.guardKey).sort().join("|")
        && Object.values(candidateBlueprint.guardValues).every((value) => typeof value === "boolean"),
      "unsafe private blueprint operator review packet: complete boolean guard set required",
    );

    const completionByGuard = new Map(completion.guardCompletions.map((entry) => [entry.guardKey, entry]));
    const fields = RUNBACK_DELTAS.map((guard) => {
      const beforeValue = sourceBlueprint.guardValues[guard.guardKey];
      const afterValue = candidateBlueprint.guardValues[guard.guardKey];
      const changed = beforeValue !== afterValue;
      const sourceStage = guard.guardKey === draft.appliedGuard.guardKey
        ? "accepted_guard_revision"
        : completionByGuard.has(guard.guardKey)
          ? "reviewed_guard_completion"
          : "preserved_source_value";
      return {
        fieldPath: `guardValues.${guard.guardKey}`,
        guardKey: guard.guardKey,
        label: guard.label,
        beforeValue,
        afterValue,
        changeStatus: changed ? "proposed_change" : "preserved_value",
        sourceStage,
      };
    });
    const sourceBlueprintDigest = await sha256Hex(canonicalJSON(sourceBlueprint));
    const candidateBlueprintDigest = await sha256Hex(canonicalJSON(candidateBlueprint));
    const exactDiff = {
      sourceBlueprintDigest,
      candidateBlueprintDigest,
      fields,
      changedFieldPaths: fields.filter((field) => field.changeStatus === "proposed_change").map((field) => field.fieldPath),
      unchangedFieldPaths: [
        "agentName",
        "declaredBase",
        "harnessStyle",
        "localOnly",
        ...fields.filter((field) => field.changeStatus === "preserved_value").map((field) => field.fieldPath),
      ],
      changeCount: fields.filter((field) => field.changeStatus === "proposed_change").length,
    };
    const exactDiffDigest = await sha256Hex(canonicalJSON(exactDiff));
    const completionBinding = review.completionBinding;
    const candidateBinding = {
      completionReviewPacketDigest: reviewVerification.packetDigest,
      completionReviewDigest: review.reviewDigest,
      candidateDigest: candidate.candidateDigest,
      candidateKey: candidate.candidateKey,
      completionPacketDigest: completionBinding.completionPacketDigest,
      completionDigest: completionBinding.completionDigest,
      draftReviewPacketDigest: completionBinding.draftReviewPacketDigest,
      commitCandidateDigest: completionBinding.commitCandidateDigest,
      draftPacketDigest: completionBinding.draftPacketDigest,
      acceptedReviewPacketDigest: completionBinding.acceptedReviewPacketDigest,
      guardProposalPacketDigest: completionBinding.guardProposalPacketDigest,
      parentProposalPayloadDigest: completionBinding.parentProposalPayloadDigest,
      selectedReviewDigest: completionBinding.selectedReviewDigest,
    };
    const record = {
      packetStatus: "prepared_local_operator_review_packet",
      packetKey: [
        "private-blueprint-operator-review-packet-v1",
        reviewVerification.packetDigest,
        candidate.candidateDigest,
        exactDiffDigest,
      ].join(":"),
      candidateBinding,
      sourceBlueprint,
      candidateBlueprint,
      exactDiff,
      verifierEvidence: {
        verificationStatus: "verified_local_portable_lineage",
        nestedLineageReverified: true,
        acceptedDecisionVerified: true,
        candidateProjectionRecomputed: true,
        exactDiffRecomputed: true,
        canonicalPacketRequired: true,
        sourceBlueprintDigest,
        candidateBlueprintDigest,
        exactDiffDigest,
      },
      validationPlan: {
        status: "not_run",
        steps: PRIVATE_BLUEPRINT_OPERATOR_REVIEW_VALIDATION_STEPS.map((step) => ({
          id: step.id,
          command: step.command,
          evidenceStatus: "not_run",
        })),
      },
      rollbackPlan: {
        status: "discard_only_uncommitted_state",
        action: "Discard this packet and its local candidate. No repository, fixture, runtime, registry, or publication state was changed.",
        repositoryMutationStatus: "none",
        runtimeMutationStatus: "none",
      },
      operatorAction: {
        status: "not_run",
        requestedDecision: "review_exact_candidate_diff_validation_and_rollback",
        allowedOutcomes: ["approve_for_separate_commit_preparation", "defer", "reject"],
        identityAttested: false,
        approvalAttested: false,
      },
      state: {
        localOnly: true,
        operatorPacketPrepared: true,
        candidateValidationStatus: "not_run",
        operatorReviewStatus: "not_run",
        committed: false,
        adopted: false,
        commitReady: false,
        qualificationStatus: "not_run",
        played: false,
        executionStatus: "disabled",
        registryStatus: "not_requested",
        publicationStatus: "not_requested",
      },
      blockers: clone(PRIVATE_BLUEPRINT_OPERATOR_REVIEW_PACKET_BLOCKERS),
      authority: privateBlueprintDeltaAuthority(),
      boundary: PRIVATE_BLUEPRINT_OPERATOR_REVIEW_PACKET_BOUNDARY,
    };
    const operatorPacketDigest = await sha256Hex(canonicalJSON(record));
    return { ...record, operatorPacketDigest };
  }

  async function createPortablePrivateBlueprintOperatorReviewPacket(serializedReviewInput) {
    const acceptedReviewVerification = await verifyPortablePrivateBlueprintGuardCompletionReview(serializedReviewInput);
    const operatorReviewPacket = await buildPortablePrivateBlueprintOperatorReviewPacketRecord(acceptedReviewVerification);
    const payload = {
      acceptedGuardCompletionReviewReceipt: JSON.parse(serializedReviewInput),
      operatorReviewPacket,
    };
    const payloadDigest = await sha256Hex(canonicalJSON(payload));
    const binding = operatorReviewPacket.candidateBinding;
    const evidence = operatorReviewPacket.verifierEvidence;
    const packet = {
      schemaVersion: PRIVATE_BLUEPRINT_OPERATOR_REVIEW_PACKET_SCHEMA,
      packetVersion: 1,
      payload,
      integrity: {
        algorithm: "sha256",
        payloadDigest,
        completionReviewPacketDigest: binding.completionReviewPacketDigest,
        completionReviewDigest: binding.completionReviewDigest,
        candidateDigest: binding.candidateDigest,
        sourceBlueprintDigest: evidence.sourceBlueprintDigest,
        candidateBlueprintDigest: evidence.candidateBlueprintDigest,
        exactDiffDigest: evidence.exactDiffDigest,
        operatorPacketDigest: operatorReviewPacket.operatorPacketDigest,
      },
      boundary: PRIVATE_BLUEPRINT_OPERATOR_REVIEW_PACKET_BOUNDARY,
    };
    const serialized = canonicalJSON(packet);
    requireValue(serialized.length <= PRIVATE_BLUEPRINT_OPERATOR_REVIEW_PACKET_MAX_LENGTH, "unsafe private blueprint operator review packet: packet length rejected");
    return { packet: clone(packet), serialized };
  }

  async function verifyPortablePrivateBlueprintOperatorReviewPacket(serializedInput) {
    requireValue(
      typeof serializedInput === "string"
        && serializedInput.length > 0
        && serializedInput.length <= PRIVATE_BLUEPRINT_OPERATOR_REVIEW_PACKET_MAX_LENGTH,
      "unsafe private blueprint operator review packet: input length rejected",
    );
    let packet;
    try {
      packet = JSON.parse(serializedInput);
    } catch {
      throw new Error("unsafe private blueprint operator review packet: invalid JSON");
    }
    assertSafeKeys(packet, "private blueprint operator review packet", 0, { nodes: 0 }, PRIVATE_BLUEPRINT_OPERATOR_REVIEW_PACKET_NODE_LIMIT);
    requireExactKeys(packet, ["schemaVersion", "packetVersion", "payload", "integrity", "boundary"], "private blueprint operator review packet");
    requireValue(packet.schemaVersion === PRIVATE_BLUEPRINT_OPERATOR_REVIEW_PACKET_SCHEMA && packet.packetVersion === 1, "unsafe private blueprint operator review packet: schema drift");
    requireValue(packet.boundary === PRIVATE_BLUEPRINT_OPERATOR_REVIEW_PACKET_BOUNDARY, "unsafe private blueprint operator review packet: boundary drift");
    requireValue(serializedInput === canonicalJSON(packet), "unsafe private blueprint operator review packet: packet must use canonical JSON");
    requireExactKeys(packet.payload, ["acceptedGuardCompletionReviewReceipt", "operatorReviewPacket"], "private blueprint operator review packet payload");
    requireExactKeys(packet.integrity, [
      "algorithm", "payloadDigest", "completionReviewPacketDigest", "completionReviewDigest", "candidateDigest",
      "sourceBlueprintDigest", "candidateBlueprintDigest", "exactDiffDigest", "operatorPacketDigest",
    ], "private blueprint operator review packet integrity");
    requireValue(packet.integrity.algorithm === "sha256", "unsafe private blueprint operator review packet: integrity algorithm drift");
    for (const key of [
      "payloadDigest", "completionReviewPacketDigest", "completionReviewDigest", "candidateDigest",
      "sourceBlueprintDigest", "candidateBlueprintDigest", "exactDiffDigest", "operatorPacketDigest",
    ]) requireValue(HEX64.test(packet.integrity[key]), `unsafe private blueprint operator review packet: ${key} drift`);
    requireValue(isObject(packet.payload.operatorReviewPacket), "unsafe private blueprint operator review packet: packet record drift");
    requireExactKeys(packet.payload.operatorReviewPacket, [
      "packetStatus", "packetKey", "candidateBinding", "sourceBlueprint", "candidateBlueprint", "exactDiff",
      "verifierEvidence", "validationPlan", "rollbackPlan", "operatorAction", "state", "blockers", "authority",
      "boundary", "operatorPacketDigest",
    ], "private blueprint operator review packet record");

    const reviewSerialized = canonicalJSON(packet.payload.acceptedGuardCompletionReviewReceipt);
    const acceptedReviewVerification = await verifyPortablePrivateBlueprintGuardCompletionReview(reviewSerialized);
    const expectedOperatorPacket = await buildPortablePrivateBlueprintOperatorReviewPacketRecord(acceptedReviewVerification);
    requireValue(canonicalJSON(packet.payload.operatorReviewPacket) === canonicalJSON(expectedOperatorPacket), "unsafe private blueprint operator review packet: packet projection mismatch");
    const binding = expectedOperatorPacket.candidateBinding;
    const evidence = expectedOperatorPacket.verifierEvidence;
    for (const [integrityKey, expectedValue, message] of [
      ["completionReviewPacketDigest", binding.completionReviewPacketDigest, "completion review packet digest binding mismatch"],
      ["completionReviewDigest", binding.completionReviewDigest, "completion review digest binding mismatch"],
      ["candidateDigest", binding.candidateDigest, "candidate digest binding mismatch"],
      ["sourceBlueprintDigest", evidence.sourceBlueprintDigest, "source blueprint digest binding mismatch"],
      ["candidateBlueprintDigest", evidence.candidateBlueprintDigest, "candidate blueprint digest binding mismatch"],
      ["exactDiffDigest", evidence.exactDiffDigest, "exact diff digest binding mismatch"],
      ["operatorPacketDigest", expectedOperatorPacket.operatorPacketDigest, "operator packet digest binding mismatch"],
    ]) requireValue(equalHex(expectedValue, packet.integrity[integrityKey]), `unsafe private blueprint operator review packet: ${message}`);
    const computedPayloadDigest = await sha256Hex(canonicalJSON(packet.payload));
    requireValue(equalHex(computedPayloadDigest, packet.integrity.payloadDigest), "unsafe private blueprint operator review packet: payload digest mismatch");
    return {
      schemaVersion: PRIVATE_BLUEPRINT_OPERATOR_REVIEW_PACKET_SCHEMA,
      verificationStatus: "verified_private_local_blueprint_operator_review_packet",
      packetDigest: computedPayloadDigest,
      acceptedReviewSerialized: reviewSerialized,
      acceptedReviewVerification,
      operatorReviewPacket: clone(expectedOperatorPacket),
      boundary: PRIVATE_BLUEPRINT_OPERATOR_REVIEW_PACKET_BOUNDARY,
    };
  }

  async function adaptArenaReadModel(modelInput, demoInput) {
    const model = await verifyArenaReadModelIntegrity(modelInput);
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
    demo.quickMatches.push(localExhibitionFixtureView());
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

  function readModelFallbackReason(error) {
    const message = error instanceof Error ? error.message : "";
    if (message.includes("digest mismatch") || message.includes("digest pin mismatch")) {
      return "verified_read_model_digest_mismatch";
    }
    if (message.includes("SHA-256 unavailable")) return "verified_read_model_integrity_unavailable";
    return "verified_read_model_unavailable_or_invalid";
  }

  async function validateTesterFeedbackRubric(rubricInput) {
    assertSafeKeys(rubricInput, "testerFeedbackRubric");
    const rubric = clone(rubricInput);
    requireExactKeys(rubric, [
      "schemaVersion", "rubricStatus", "categories", "ratingScale", "blockerClasses",
      "severeIssueClasses", "freeTextPolicy", "identityFieldsAllowed", "humanFeedbackCollected",
      "productionAuthority", "rubricDigest",
    ], "tester feedback rubric");
    requireValue(rubric.schemaVersion === TESTER_FEEDBACK_SCHEMA, "unsafe tester feedback rubric: schema drift");
    requireValue(rubric.rubricStatus === "template_only_no_human_response", "unsafe tester feedback rubric: status drift");
    requireValue(Array.isArray(rubric.categories) && rubric.categories.length === TESTER_FEEDBACK_CATEGORIES.length, "unsafe tester feedback rubric: category count drift");
    rubric.categories.forEach((category, index) => {
      requireExactKeys(category, ["categoryId", "prompt"], "tester feedback category");
      requireValue(canonicalJSON(category) === canonicalJSON(TESTER_FEEDBACK_CATEGORIES[index]), "unsafe tester feedback rubric: category drift");
    });
    requireExactKeys(rubric.ratingScale, ["1", "2", "3", "4", "5"], "tester feedback rating scale");
    requireValue(canonicalJSON(rubric.ratingScale) === canonicalJSON({
      1: "strongly_disagree_or_blocked",
      2: "disagree_or_major_confusion",
      3: "mixed_or_recoverable_confusion",
      4: "agree_or_minor_friction",
      5: "strongly_agree_or_clear",
    }), "unsafe tester feedback rubric: rating scale drift");
    requireValue(canonicalJSON(rubric.blockerClasses) === canonicalJSON(TESTER_FEEDBACK_BLOCKER_CLASSES), "unsafe tester feedback rubric: blocker classes drift");
    requireValue(canonicalJSON(rubric.severeIssueClasses) === canonicalJSON(TESTER_FEEDBACK_SEVERE_ISSUE_CLASSES), "unsafe tester feedback rubric: severe issue classes drift");
    requireValue(rubric.freeTextPolicy === "redacted_bounded_private_artifact_not_in_public_receipt", "unsafe tester feedback rubric: free-text policy drift");
    requireValue(Array.isArray(rubric.identityFieldsAllowed) && rubric.identityFieldsAllowed.length === 0, "unsafe tester feedback rubric: identity fields must remain absent");
    requireValue(rubric.humanFeedbackCollected === false, "unsafe tester feedback rubric: human feedback cannot be pre-collected");
    requireExactKeys(rubric.productionAuthority, TESTER_FEEDBACK_AUTHORITY_FIELDS, "tester feedback production authority");
    requireValue(TESTER_FEEDBACK_AUTHORITY_FIELDS.every((field) => rubric.productionAuthority[field] === false), "unsafe tester feedback rubric: production authority must remain false");
    requireValue(typeof rubric.rubricDigest === "string" && HEX64.test(rubric.rubricDigest), "unsafe tester feedback rubric: digest malformed");
    const unsigned = clone(rubric);
    delete unsigned.rubricDigest;
    const computedDigest = await sha256Hex(canonicalJSON(unsigned));
    requireValue(equalHex(computedDigest, rubric.rubricDigest), "unsafe tester feedback rubric: digest mismatch");
    return rubric;
  }

  async function createTesterFeedbackDraft(rubricInput, ratingsInput, blockerClass, severeIssueClass) {
    const rubric = await validateTesterFeedbackRubric(rubricInput);
    requireExactKeys(ratingsInput, TESTER_FEEDBACK_CATEGORIES.map((category) => category.categoryId), "tester feedback ratings");
    const ratings = TESTER_FEEDBACK_CATEGORIES.map((category) => {
      const rating = ratingsInput[category.categoryId];
      requireValue(Number.isInteger(rating) && rating >= 1 && rating <= 5, "unsafe tester feedback draft: every category requires a rating from 1 to 5");
      return { categoryId: category.categoryId, rating };
    });
    requireValue(TESTER_FEEDBACK_BLOCKER_CLASSES.includes(blockerClass), "unsafe tester feedback draft: blocker class drift");
    requireValue(TESTER_FEEDBACK_SEVERE_ISSUE_CLASSES.includes(severeIssueClass), "unsafe tester feedback draft: severe issue class drift");
    const draft = {
      schemaVersion: TESTER_FEEDBACK_DRAFT_SCHEMA,
      draftStatus: "LOCAL_DRAFT_NOT_COLLECTED",
      rubricSchemaVersion: rubric.schemaVersion,
      rubricDigest: rubric.rubricDigest,
      ratings,
      blockerClass,
      severeIssueClass,
      identityFieldsAllowed: [],
      freeTextIncluded: false,
      storageMode: "browser_memory_only",
      transportStatus: "not_configured",
      submissionStatus: "not_submitted",
      humanFeedbackCollected: false,
      productionAuthority: Object.fromEntries(TESTER_FEEDBACK_AUTHORITY_FIELDS.map((field) => [field, false])),
      boundary: TESTER_FEEDBACK_DRAFT_BOUNDARY,
    };
    draft.draftDigest = await sha256Hex(canonicalJSON(draft));
    return { draft: clone(draft), serialized: canonicalJSON(draft) };
  }

  async function verifyTesterFeedbackDraft(serializedInput, rubricInput) {
    requireValue(typeof serializedInput === "string" && serializedInput.length > 0 && serializedInput.length <= TESTER_FEEDBACK_DRAFT_MAX_LENGTH, "unsafe tester feedback draft: bounded canonical JSON required");
    let draft;
    try {
      draft = JSON.parse(serializedInput);
    } catch {
      throw new Error("unsafe tester feedback draft: invalid JSON");
    }
    assertSafeKeys(draft, "testerFeedbackDraft");
    requireValue(serializedInput === canonicalJSON(draft), "unsafe tester feedback draft: canonical JSON required");
    requireExactKeys(draft, [
      "schemaVersion", "draftStatus", "rubricSchemaVersion", "rubricDigest", "ratings",
      "blockerClass", "severeIssueClass", "identityFieldsAllowed", "freeTextIncluded",
      "storageMode", "transportStatus", "submissionStatus", "humanFeedbackCollected",
      "productionAuthority", "boundary", "draftDigest",
    ], "tester feedback draft");
    const rubric = await validateTesterFeedbackRubric(rubricInput);
    requireValue(draft.schemaVersion === TESTER_FEEDBACK_DRAFT_SCHEMA && draft.draftStatus === "LOCAL_DRAFT_NOT_COLLECTED", "unsafe tester feedback draft: schema or status drift");
    requireValue(draft.rubricSchemaVersion === rubric.schemaVersion && equalHex(draft.rubricDigest, rubric.rubricDigest), "unsafe tester feedback draft: rubric binding drift");
    requireValue(Array.isArray(draft.ratings) && draft.ratings.length === TESTER_FEEDBACK_CATEGORIES.length, "unsafe tester feedback draft: rating count drift");
    draft.ratings.forEach((rating, index) => {
      requireExactKeys(rating, ["categoryId", "rating"], "tester feedback rating");
      requireValue(rating.categoryId === TESTER_FEEDBACK_CATEGORIES[index].categoryId, "unsafe tester feedback draft: rating order drift");
      requireValue(Number.isInteger(rating.rating) && rating.rating >= 1 && rating.rating <= 5, "unsafe tester feedback draft: rating value drift");
    });
    requireValue(TESTER_FEEDBACK_BLOCKER_CLASSES.includes(draft.blockerClass), "unsafe tester feedback draft: blocker class drift");
    requireValue(TESTER_FEEDBACK_SEVERE_ISSUE_CLASSES.includes(draft.severeIssueClass), "unsafe tester feedback draft: severe issue class drift");
    requireValue(Array.isArray(draft.identityFieldsAllowed) && draft.identityFieldsAllowed.length === 0 && draft.freeTextIncluded === false, "unsafe tester feedback draft: identity or free text added");
    requireValue(draft.storageMode === "browser_memory_only" && draft.transportStatus === "not_configured" && draft.submissionStatus === "not_submitted", "unsafe tester feedback draft: storage or transport drift");
    requireValue(draft.humanFeedbackCollected === false && draft.boundary === TESTER_FEEDBACK_DRAFT_BOUNDARY, "unsafe tester feedback draft: evidence boundary drift");
    requireExactKeys(draft.productionAuthority, TESTER_FEEDBACK_AUTHORITY_FIELDS, "tester feedback draft production authority");
    requireValue(TESTER_FEEDBACK_AUTHORITY_FIELDS.every((field) => draft.productionAuthority[field] === false), "unsafe tester feedback draft: production authority must remain false");
    requireValue(typeof draft.draftDigest === "string" && HEX64.test(draft.draftDigest), "unsafe tester feedback draft: digest malformed");
    const unsigned = clone(draft);
    delete unsigned.draftDigest;
    const computedDigest = await sha256Hex(canonicalJSON(unsigned));
    requireValue(equalHex(computedDigest, draft.draftDigest), "unsafe tester feedback draft: digest mismatch");
    return clone(draft);
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
      return await adaptArenaReadModel(model, demo);
    } catch (error) {
      return demoFallback(demo, readModelFallbackReason(error));
    }
  }

  async function loadTesterFeedbackRubric(fetchImpl = fetch) {
    const rubric = await fetchJSON(fetchImpl, "data/tester-feedback-rubric.v1.json", "tester feedback rubric");
    return validateTesterFeedbackRubric(rubric);
  }

  return {
    DEMO_SCHEMA,
    LEARNING_SCHEMA,
    TESTER_FEEDBACK_DRAFT_MAX_LENGTH,
    TESTER_FEEDBACK_DRAFT_SCHEMA,
    TESTER_FEEDBACK_SCHEMA,
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
    PRIVATE_BLUEPRINT_GUARD_COMPLETION_MAX_LENGTH,
    PRIVATE_BLUEPRINT_GUARD_COMPLETION_PROVENANCE_CODES,
    PRIVATE_BLUEPRINT_GUARD_COMPLETION_REASONS,
    PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_MAX_LENGTH,
    PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_REASONS,
    PRIVATE_BLUEPRINT_GUARD_COMPLETION_REVIEW_SCHEMA,
    PRIVATE_BLUEPRINT_GUARD_COMPLETION_SCHEMA,
    PRIVATE_BLUEPRINT_OPERATOR_REVIEW_PACKET_MAX_LENGTH,
    PRIVATE_BLUEPRINT_OPERATOR_REVIEW_PACKET_SCHEMA,
    PRIVATE_BLUEPRINT_DRAFT_REVIEW_MAX_LENGTH,
    PRIVATE_BLUEPRINT_DRAFT_REVIEW_REASONS,
    PRIVATE_BLUEPRINT_DRAFT_REVIEW_SCHEMA,
    PRIVATE_BLUEPRINT_REVISION_DRAFT_MAX_LENGTH,
    PRIVATE_BLUEPRINT_REVISION_DRAFT_SCHEMA,
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
    LOCAL_EXHIBITION_QUALIFICATION_SCHEMA,
    LOCAL_EXHIBITION_RECEIPT_SCHEMA,
    LOCAL_EXHIBITION_VERIFICATION_SCHEMA,
    LOCAL_EXHIBITION_LEARNING_SCHEMA,
    LOCAL_EXHIBITION_RUNBACK_SCHEMA,
    LOCAL_EXHIBITION_PROOF_SHARE_SCHEMA,
    LOCAL_EXHIBITION_PROOF_SHARE_MAX_LENGTH,
    LOCAL_EXHIBITION_RESOURCE_CLASS,
    LOCAL_EXHIBITION_RULES_DIGEST,
    LOCAL_EXHIBITION_FIXTURE_ID,
    READ_MODEL_SCHEMA,
    READ_MODEL_DIGEST_PIN,
    RUNBACK_PROPOSAL_SCHEMA,
    VIEW_SCHEMA,
    adaptArenaReadModel,
    appendPortableRunbackReview,
    appendPortableRunbackReviewCorrection,
    buildQualificationPreview,
    buildLocalExhibitionQualification,
    buildReceiptLearningAction,
    buildRunbackProposal,
    createLocalExhibitionLearning,
    createLocalExhibitionProofShare,
    createLocalExhibitionReceipt,
    createLocalExhibitionRunback,
    createTesterFeedbackDraft,
    createPortablePrivateBlueprintDelta,
    createPortablePrivateBlueprintDeltaReview,
    createPortablePrivateBlueprintGuardCompletion,
    createPortablePrivateBlueprintGuardCompletionReview,
    createPortablePrivateBlueprintOperatorReviewPacket,
    createPortablePrivateBlueprintDraftReview,
    createPortablePrivateBlueprintRevisionDraft,
    createPortablePrivateReviewComparison,
    createPortablePrivateReviewLearning,
    createPortableRunbackEnvelope,
    createPortableRunbackReviewExchange,
    createPortableRunbackReviewCorrectionExchange,
    demoFallback,
    loadArenaData,
    loadTesterFeedbackRubric,
    validateArenaReadModel,
    verifyArenaReadModelIntegrity,
    validateDemoFixture,
    validateRunbackProposal,
    validateTesterFeedbackRubric,
    verifyPortableRunbackEnvelope,
    verifyPortableRunbackReviewCorrectionExchange,
    verifyPortableRunbackReviewCorrectionJournal,
    verifyPortableRunbackReviewExchange,
    verifyPortableRunbackReviewJournal,
    verifyPortablePrivateBlueprintDelta,
    verifyPortablePrivateBlueprintDeltaReview,
    verifyPortablePrivateBlueprintGuardCompletion,
    verifyPortablePrivateBlueprintGuardCompletionReview,
    verifyPortablePrivateBlueprintOperatorReviewPacket,
    verifyPortablePrivateBlueprintDraftReview,
    verifyPortablePrivateBlueprintRevisionDraft,
    verifyPortablePrivateReviewComparison,
    verifyPortablePrivateReviewLearning,
    verifyTesterFeedbackDraft,
    verifyLocalExhibitionReceipt,
    verifyLocalExhibitionProofShare,
  };
}));
