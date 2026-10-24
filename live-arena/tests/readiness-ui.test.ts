import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import ts from "typescript";

// Exercise the actual UI handlers without a DOM/browser or any provider traffic.
const source = readFileSync(new URL("../src/main.ts", import.meta.url), "utf8");
const ast = ts.createSourceFile("main.ts", source, ts.ScriptTarget.Latest, true);
function functionSource(name: string) {
  const node = ast.statements.find(node => ts.isFunctionDeclaration(node) && node.name?.text === name);
  assert.ok(node, `Missing ${name}`);
  return node.getText(ast);
}
const section = source.slice(source.indexOf("function readinessStatus("), source.indexOf("\nrefreshReadinessTargets();") + "\nrefreshReadinessTargets();".length);
const code = ts.transpileModule([
  ...["ensureExecutionReady", "oneMove", "play", "runSeries", "prepareAcademy"].map(functionSource), section,
].join("\n"), { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText;
class Element {
  value = ""; textContent = ""; options: Element[] = []; disabled = false; hidden = false;
  onclick?: () => Promise<void>;
  set innerHTML(_: string) { this.options = []; this.value = ""; }
  append(option: Element) { this.options.push(option); if (this.options.length === 1) this.value = option.value; }
}
function harness() {
  const nodes = new Map<string, Element>();
  const $ = (id: string) => { if (!nodes.has(id)) nodes.set(id, new Element()); return nodes.get(id)!; };
  const bot = { kind: "bot", name: "Tactician", model: "tactician" };
  const calls: unknown[] = [], messages: string[] = [];
  const context: any = {
    $, document: { createElement: () => new Element() }, AbortController,
    agents: [bot, { ...bot }], models: [], pending: false, running: false, spectating: false,
    state: { over: false, turn: 0, moves: [] },
    duelUI: { room: { view: () => ({ active: context.duelActive }) } },
    localLab: { active: () => context.labActive },
    ensureDeviceReady: () => {}, numberInput: () => 256,
    runReadinessCheck: (options: unknown) => { calls.push(options); return new Promise(() => {}); },
    notify: (message: string) => messages.push(message), tab: () => {},
    getMatchLimits: () => { throw Error("Unexpected match dispatch"); },
  };
  runInNewContext(code, context);
  return { context, $, calls, messages, run: () => $("academy-readiness").onclick!() };
}

test("readiness retains an unchanged identity but requires a new choice after replacement", () => {
  const { context, $ } = harness();
  assert.equal($("readiness-agent").value, "0");
  context.refreshReadinessTargets();
  assert.equal($("readiness-agent").value, "0");
  context.agents[0] = { kind: "harness", name: "Tactician", model: "new-model" };
  context.refreshReadinessTargets();
  assert.equal($("readiness-agent").value, "");
  assert.match($("readiness-agent").options[1].textContent, /harness.*new-model/);
  context.refreshReadinessTargets();
  assert.equal($("readiness-agent").value, "", "rerender must not accept the new contender");
});

test("a stale picker cannot dispatch a newly substituted contender on the same click", async () => {
  const { context, $, calls, run } = harness();
  context.agents[0] = { kind: "openrouter", name: "Tactician", model: "new-model" };
  await run();
  assert.equal(calls.length, 0);
  assert.equal($("readiness-agent").value, "");
  await run();
  assert.equal(calls.length, 0);
  $("readiness-agent").value = "0";
  void run();
  assert.equal(calls.length, 1);
  assert.equal((calls[0] as any).agent, context.agents[0]);
});

test("readiness excludes existing match, spectator, duel and Lab work", async () => {
  for (const busy of ["pending", "running", "spectating", "duelActive", "labActive"]) {
    const { context, calls, run } = harness();
    context[busy] = true;
    await run();
    assert.equal(calls.length, 0, busy);
  }
});

test("pending readiness blocks Start, Step, evaluation and exercises before dispatch", async () => {
  const { context, calls, messages, run } = harness();
  void run();
  await assert.rejects(context.oneMove(), /Stop the readiness check/);
  await context.play();
  context.runSeries();
  assert.equal(context.prepareAcademy(false), false);
  assert.equal(calls.length, 1);
  assert.equal(context.running, false);
  assert.equal(context.pending, false);
  assert.deepEqual(messages, [
    "Stop the readiness check in Academy before starting another run.",
    "Stop the readiness check in Academy before starting another run.",
  ]);
  assert.throws(() => context.ensureExecutionReady(), /Stop the readiness check/);
});
