import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, rm, readFile, writeFile, readdir, symlink } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { exportExhibition } from "../scripts/export-exhibition";
import { runChessContest, CHESS_PLAYERS, type ChessPort } from "../scripts/frontier-chess";
import { analyzeChess } from "../scripts/chess-engine";
import { createGame, replayStepper, RULES, legalMoves, sha256, createProof, refereeManifest } from "../src/runtime";
import { readExhibition } from "../src/exhibition";

const source = "a".repeat(64), binary = "b".repeat(64);
const port: ChessPort = async (player, prompt) => ({ requestedModel: CHESS_PLAYERS[player].model,
  move: /Legal UCI moves: (\S+)/.exec(prompt)![1], comment: "private-comment-do-not-publish", resolvedModel: null,
  identityEvidence: "unreported", inputTokens: 10, outputTokens: 2, listCostUsd: 0.001, elapsedMilliseconds: 7, toolsUsed: false });
async function fixture(root: string, name: string, client: ChessPort = port, engineFailure = false, maxCalls = 4) {
  const path = join(root, name);
  await runChessContest({ file: join(root, "NONEXISTENT-NO-ENGINE-EXECUTION"), sha256: binary, name: "Stockfish 19" }, path, client,
    { maxCalls }, { source: async () => source, binaryDigest: async () => binary,
      analyze: (async (_pin, history) => {
        if (engineFailure) throw Error("private-engine-path");
        let state = createGame(RULES.chess); const step = replayStepper(RULES.chess);
        for (const move of history) state = step(move);
        return { lines: [{ rank: 1, score: { kind: "cp", value: 0 }, moves: [legalMoves(state)[0]] }] };
      }) as typeof analyzeChess });
  return path;
}
async function mutate(path: string, name: string, change: (value: any) => void) {
  const file = join(path, name), raw = JSON.parse(await readFile(file, "utf8")); change(raw); await writeFile(file, JSON.stringify(raw));
}
async function hashes(path: string) {
  return Promise.all((await readdir(path)).sort().map(async name => [name, await sha256(await readFile(join(path, name)))]));
}

test("offline exporter verifies both pairings, preserves historical digests and omits private text", async () => {
  const root = await mkdtemp(join(tmpdir(), "bw-export-test-"));
  try {
    const input = await fixture(root, "run"), before = await hashes(input);
    for (const game of [1, 2]) {
      const destination = join(root, `public-${game}.json`), result = await exportExhibition(input, game, destination);
      assert.deepEqual(await readExhibition(JSON.parse(await readFile(destination, "utf8"))), result);
      assert.equal(result.source.runner, source); assert.equal(result.source.result, await sha256(await readFile(join(input, "result.json"))));
      assert.equal(result.source.originalProof, await sha256(await readFile(join(input, `game-${game}.proof.jsonl`))));
      assert.equal(result.gameAttempts, 2); assert.equal(result.exit, "capped"); assert.equal(result.record.events.length, 2);
      assert.equal(result.record.status, "Unfinished match"); assert.deepEqual(result.decisions.map(d => [d.inputTokens, d.outputTokens]), [[10, 2], [10, 2]]);
      const text = JSON.stringify(result);
      for (const secret of ["private-comment", "Position FEN", "NONEXISTENT", "Engine analysis", "strategy sentence"]) assert.ok(!text.includes(secret));
      assert.ok(result.record.agents.every(a => a.strategy === "")); assert.ok(result.record.events.every(e => e.comment === ""));
      await assert.rejects(exportExhibition(input, game, destination), /EEXIST/);
    }
    assert.deepEqual(await hashes(input), before);
  } finally { await rm(root, { recursive: true, force: true }); }
});

test("failed zero-move games retain truthful attempts and never publish failure text", async () => {
  const root = await mkdtemp(join(tmpdir(), "bw-export-failed-"));
  try {
    for (const engineFailure of [false, true]) {
      const input = await fixture(root, `run-${engineFailure}`, async () => { throw Error("private-client-error"); }, engineFailure);
      const result = await exportExhibition(input, 1, join(root, `public-${engineFailure}.json`));
      assert.equal(result.exit, "failed"); assert.equal(result.record.events.length, 0); assert.equal(result.gameAttempts, engineFailure ? 0 : 1);
      assert.ok(result.players.every(p => p.resolvedModel === null && p.identityEvidence === "unreported"));
      assert.ok(!JSON.stringify(result).includes("private-"));
    }
  } finally { await rm(root, { recursive: true, force: true }); }
});

test("completed games retain reported family identity and unknown usage without inventing measurements", async () => {
  const root = await mkdtemp(join(tmpdir(), "bw-export-complete-"));
  try {
    const resolved = { astra: "gpt-6-astra", fable: "claude-fable-5-1", grok: "grok-4.6-high", gemini: "gemini-3.1-pro-high" };
    const mating: ChessPort = async (player, prompt, ms) => {
      const reply = await port(player, prompt, ms), history = /Full UCI history: ([^\n]+)/.exec(prompt)![1];
      const ply = history === "initial position" ? 0 : history.split(" ").length;
      return { ...reply, move: ["f2f3", "e7e5", "g2g4", "d8h4"][ply], resolvedModel: resolved[player], identityEvidence: "client-reported",
        inputTokens: null, outputTokens: 2, listCostUsd: null };
    };
    const input = await fixture(root, "run", mating, false, 8);
    for (const game of [1, 2]) {
      const result = await exportExhibition(input, game, join(root, `game-${game}.json`));
      assert.equal(result.exit, "complete"); assert.equal(result.gameAttempts, 4); assert.equal(result.record.events.length, 4);
      assert.ok(result.players.every(p => p.resolvedModel === resolved[p.route] && p.identityEvidence === "client-reported"));
      assert.ok(result.decisions.every(d => d.inputTokens === null && d.outputTokens === 2));
      assert.ok(result.record.events.every(e => e.tokens === null && e.cost === null));
    }
  } finally { await rm(root, { recursive: true, force: true }); }
});

test("exporter rejects receipt linkage, replay, usage, identity and proof tampering", async () => {
  const root = await mkdtemp(join(tmpdir(), "bw-export-tamper-"));
  const cases: [string, (path: string) => Promise<void>][] = [
    ["plan", p => mutate(p, "plan.json", v => { v.source = "c".repeat(64); })],
    ["result-source", p => mutate(p, "result.json", v => { v.source = "c".repeat(64); })],
    ["request-prompt", p => mutate(p, "request-001.json", v => { v.prompt += "changed"; })],
    ["request-number", p => mutate(p, "request-001.json", v => { v.number = 2; })],
    ["response-request", p => mutate(p, "response-001.json", v => { v.request = "c".repeat(64); })],
    ["response-usage", p => mutate(p, "response-001.json", v => { v.decision.inputTokens++; })],
    ["response-identity", p => mutate(p, "response-001.json", v => { v.decision.resolvedModel = "gpt-6-astra"; v.decision.identityEvidence = "client-reported"; })],
    ["calls-move", p => mutate(p, "result.json", v => { v.calls[0].decision.move = "e2e4"; })],
    ["attempts", p => mutate(p, "result.json", v => { v.providerAttempts++; })],
    ["summary-plies", p => mutate(p, "result.json", v => { v.games[1].plies++; })],
    ["whole-run-failure", async p => { await writeFile(join(p, "failed.json"), "{}"); }],
    ["missing-response", async p => { await rm(join(p, "response-001.json")); }],
    ["proof", async p => { await writeFile(join(p, "game-1.proof.jsonl"), "{}\n"); }],
    ["coherent-replay-usage", async p => {
      await mutate(p, "game-1.json", v => { v.events[0].tokens++; });
      const record = JSON.parse(await readFile(join(p, "game-1.json"), "utf8"));
      await writeFile(join(p, "game-1.proof.jsonl"), await createProof(record, refereeManifest.digest, 80, "reverified_import"));
    }],
  ];
  try {
    for (const [name, change] of cases) {
      const input = await fixture(root, name); await change(input);
      const destination = join(root, `${name}.json`);
      await assert.rejects(exportExhibition(input, 1, destination), { name: "Error" }, name);
      await assert.rejects(readFile(destination), /ENOENT/);
    }
  } finally { await rm(root, { recursive: true, force: true }); }
});

test("exporter rejects oversized/nonregular receipts, linked roots and unsafe selections", async t => {
  const root = await mkdtemp(join(tmpdir(), "bw-export-path-"));
  try {
    const input = await fixture(root, "run");
    await assert.rejects(exportExhibition(input, 3, join(root, "invalid.json")), /game 1 or 2/);
    const original = await readFile(join(input, "request-001.json"));
    await writeFile(join(input, "request-001.json"), "x".repeat(1_500_001));
    await assert.rejects(exportExhibition(input, 1, join(root, "oversized.json")), /bounded regular/);
    await writeFile(join(input, "request-001.json"), original);
    const linked = join(root, "linked"); await symlink(input, linked, "junction");
    await assert.rejects(exportExhibition(linked, 1, join(root, "linked.json")), /regular directories/);
    // File links can require Windows developer mode; the directory-link check above is unconditional.
    await rm(join(input, "request-001.json")); await writeFile(join(root, "request.json"), original);
    try { await symlink(join(root, "request.json"), join(input, "request-001.json"), "file"); }
    catch (error) { if ((error as NodeJS.ErrnoException).code !== "EPERM") throw error; t.diagnostic("File symlink creation unavailable on this host."); return; }
    await assert.rejects(exportExhibition(input, 1, join(root, "file-link.json")), /non-symlink/);
  } finally { await rm(root, { recursive: true, force: true }); }
});
