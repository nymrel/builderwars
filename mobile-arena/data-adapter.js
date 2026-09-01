"use strict";

(function installDataAdapter(root, factory) {
  const adapter = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = adapter;
  if (root) root.BuilderWarsDataAdapter = adapter;
}(typeof globalThis !== "undefined" ? globalThis : this, function createDataAdapter() {
  const DEMO_SCHEMA = "builderwars.mobile-arena-demo.v1";
  const READ_MODEL_SCHEMA = "builderwars.arena-read-model.v1";
  const VIEW_SCHEMA = "builderwars.mobile-arena-view.v1";
  const HEX64 = /^[0-9a-f]{64}$/;

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
    for (const receipt of model.receipts) {
      requireValue(isObject(receipt) && HEX64.test(receipt.receiptId), "unsafe arena read model: invalid receipt id");
      requireValue(HEX64.test(receipt.fixtureId), `unsafe arena read model: invalid fixture for ${receipt.receiptId}`);
      requireValue(!receiptIds.has(receipt.receiptId), `unsafe arena read model: duplicate receipt ${receipt.receiptId}`);
      receiptIds.add(receipt.receiptId);
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
    for (const fixture of model.futureFixtures) {
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

  function proofFromReceipt(receipt, boundary) {
    const counts = receipt.evidence.moveSourceCounts;
    return {
      receiptId: receipt.receiptId,
      fixtureId: receipt.fixtureId,
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

  function adaptArenaReadModel(modelInput, demoInput) {
    const model = validateArenaReadModel(modelInput);
    const demo = clone(validateDemoFixture(demoInput));
    const boundary = model.truthBoundary.statement;
    const proofs = model.receipts.map((receipt) => proofFromReceipt(receipt, boundary));
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
      actionLabel: "Unavailable",
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
    demo.rivalries = clone(model.rivalries);
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
    READ_MODEL_SCHEMA,
    VIEW_SCHEMA,
    adaptArenaReadModel,
    demoFallback,
    loadArenaData,
    validateArenaReadModel,
    validateDemoFixture,
  };
}));
