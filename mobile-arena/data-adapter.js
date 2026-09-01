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
  const PREVIEW_RESOURCE_CLASS = "local-preview-no-compute-v1";
  const HEX64 = /^[0-9a-f]{64}$/;
  const CHALLENGE_ID = /^challenge_[0-9a-f]{16}$/;
  const ALLOWED_BASE_MODELS = new Set(["Arena Small", "Arena Reason", "Local runner (not paired)"]);
  const ALLOWED_HARNESS_STYLES = new Set(["Validate every move", "Budget-aware planner", "Human review checkpoints", "Naive control"]);
  const RUNBACK_DELTAS = Object.freeze([
    { id: "require_strict_validation", guardKey: "strictValidation", label: "Require strict move validation", rationale: "Retain legal-move refusal in the next local blueprint version." },
    { id: "require_fallback_disclosure", guardKey: "fallbackDisclosure", label: "Require fallback disclosure", rationale: "Make every fallback move visible before any future result is reviewed." },
    { id: "require_human_checkpoints", guardKey: "humanCheckpoints", label: "Require human checkpoints", rationale: "Declare a bounded review checkpoint before any future execution request." },
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
        statement: "The bounded mobile read model does not carry an explicit historical rules digest. A sanctioned runback must bind one before qualification.",
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
      executionBlockers: [
        "explicit_rules_digest_not_bound",
        "qualification_not_run",
        "sanctioned_runner_not_bound",
        "local_blueprint_version_not_committed",
      ],
      attestations: { identity: false, model: false, provider: false, runtime: false, registry: false, publication: false },
      boundary: "This versioned object is a local, still-unplayed proposal. It preserves parent receipt and challenge lineage, but it does not qualify, execute, attest, rank, publish, or spend.",
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
    QUALIFICATION_SCHEMA,
    PREVIEW_RESOURCE_CLASS,
    READ_MODEL_SCHEMA,
    RUNBACK_PROPOSAL_SCHEMA,
    VIEW_SCHEMA,
    adaptArenaReadModel,
    buildQualificationPreview,
    buildReceiptLearningAction,
    buildRunbackProposal,
    demoFallback,
    loadArenaData,
    validateArenaReadModel,
    validateDemoFixture,
  };
}));
