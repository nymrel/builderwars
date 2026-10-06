import { labBaseline, makeLabRun, readLabVersion, validateLabPlan, validateLabRun, validateLabVersion, validateLabImport, labReplay,
  LAB_MAX_BYTES, LAB_MAX_RUNS, labSource, type LabRun } from "./browser-lab-core";
import { parseVersion, type Version } from "./frontier-version";
import { replay, sha256 as cryptoDigest, type RecordData } from "./runtime";

const KEY = "builderwars.browser-lab.archive.v1";
type StoragePort = Pick<Storage, "getItem" | "setItem" | "removeItem"> & { flush?: () => Promise<unknown> };
type Archive = { schema: typeof KEY; selected: string | null; selections: string[]; versions: Version[]; runs: LabRun[] };
const empty = (): Archive => ({ schema: KEY, selected: null, selections: [], versions: [], runs: [] });
const esc = (s: unknown) => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);
const percent = (n: number | null | undefined) => n == null ? "—" : `${(n * 100).toFixed(1)}%`;
export const labMarkup = `<section id="lab" class="view" hidden>
  <div class="hub-page-heading"><p class="eyebrow">BUILDERWARS LAB · LOCAL & FREE</p><h1>Make the next version earn it.</h1><p class="subtitle">Train a small local policy. Freeze the conditions. Compare it with its previous version.<br>Keep the evidence, then choose what to play.</p></div>
  <div class="lab-steps"><div><span>01</span><h2>Learn from mistakes</h2><p>Calibrate numeric parameters on referee-checked tactical positions.</p></div><div><span>02</span><h2>Run a fair comparison</h2><p>Both versions face the same openings and frozen opponents, in both seats.</p></div><div><span>03</span><h2>Choose your contender</h2><p>Inspect the result. Select a version yourself. Roll back whenever you need.</p></div></div>
  <div class="lab-workspace"><form id="lab-form" class="workspace-form"><h2>Start an experiment</h2><label>Game<select id="lab-game"><option value="connect4">Connect Four</option><option value="tictactoe">Tic-tac-toe</option></select></label><label>Comparison size<select id="lab-trials"><option value="16">Quick · 128 games / 16 seed blocks</option><option value="32">Extended · 256 games / 32 seed blocks</option><option value="64">Deep · 512 games / 64 seed blocks</option></select></label><details><summary>Reproduce an experiment</summary><label>Seed · leave blank for a fresh experiment<input id="lab-seed" type="number" min="0" max="4294967295" step="1" placeholder="Fresh random seed"></label><p class="muted">The plan and immutable versions are saved before training. Public seeds are development data.</p></details><p id="lab-incumbent" class="muted">Your first experiment starts from a fixed baseline.</p><div class="form-actions"><button id="lab-start" class="primary" type="submit">Train and compare ↗</button><button id="lab-cancel" type="button" disabled>Cancel work</button></div><p class="muted">Runs on this device in a worker. No provider calls or charges. Work stops after 90 seconds or when the app goes into the background.</p></form>
  <div class="lab-report"><h2>Your experiment</h2><p id="lab-status" role="status" aria-live="polite">Ready when you are. No work starts until you choose Train and compare.</p><progress id="lab-progress" max="1" value="0" aria-label="Completed paired comparison blocks"></progress><div id="lab-summary"><p class="muted">Observed gains and conservative uncertainty will appear here. A small experiment may not establish an improvement.</p></div></div></div>
  <div class="lab-toolbar"><h2>Your immutable versions</h2><div><button id="lab-import">Import Lab version</button><input id="lab-file" type="file" accept="application/json,.json" hidden><button id="lab-rollback" disabled>Roll back selection</button></div></div><div id="lab-versions"></div>
  <div class="lab-toolbar"><h2>Experiment history</h2><div><button id="lab-archive-export">Export complete archive</button><button id="lab-clear">Clear Lab data</button></div></div><div id="lab-history"></div>
  <div class="lab-disclosure"><h2>Know what was measured.</h2><p>This Lab calibrates a 22-parameter local value policy with one-ply search. It does not train a language model. Eight correlated games form one statistical seed block. Public development results never certify or automatically promote a contender.</p><p>Training and development tactical targets are separated by position/symmetry groups. Full games can revisit training positions. Opponents are declared tactical and two-ply baselines, not expert engines. This device keeps up to six experiments; export evidence before clearing.</p><a href="/developers">Build your own agent ↗</a> · <a href="/circuits">Explore the public circuit ↗</a></div>
</section>`;

export function mountLab(options: { storage: () => StoragePort | undefined; ensure: () => void;
  export: (name: string, data: unknown) => Promise<unknown>; use: (version: Version) => Promise<void>; replay: (record: RecordData) => void }) {
  const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
  let archive = empty(), worker: Worker | null = null, busy = false, working = false, epoch = 0, current: LabRun | undefined;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let chain = Promise.resolve(), startup = true, unavailable = false;
  const status = (message: string) => { $("lab-status").textContent = message; };
  async function save(next = archive) {
    const port = options.storage(), raw = JSON.stringify(next);
    if (!port) throw Error("Lab saving is unavailable. Enable device storage before starting an experiment.");
    if (raw.length > LAB_MAX_BYTES) throw Error("Lab archive is full. Export your evidence, then clear it before running more work.");
    const previous = port.getItem(KEY);
    try { port.setItem(KEY, raw); await port.flush?.(); }
    catch (error) { try { if (previous === null) port.removeItem(KEY); else port.setItem(KEY, previous); } catch { /* Preserve the original failure. */ } throw error; }
  }
  const executable = (v: Version) => v.config.harness.source === labSource.digest;
  const addVersion = (version: Version) => {
    if (!archive.versions.some(v => v.digest === version.digest)) archive.versions.push(version);
  };
  function render() {
    $("lab-start").toggleAttribute("disabled", startup || busy || unavailable);
    $("lab-cancel").toggleAttribute("disabled", !working);
    for (const id of ["lab-game", "lab-trials", "lab-seed", "lab-import", "lab-clear"]) $(id).toggleAttribute("disabled", busy || startup || (unavailable && id !== "lab-clear"));
    $("lab-rollback").toggleAttribute("disabled", busy || archive.selections.length < 2);
    const selected = archive.versions.find(v => v.digest === archive.selected);
    const sameGame = selected && executable(selected) && selected.config.rules.kind === $<HTMLSelectElement>("lab-game").value;
    $("lab-incumbent").textContent = sameGame ? `Incumbent: r${selected!.revision} · ${selected!.digest.slice(0, 12)}. The selected version stays unchanged during an experiment.` : "This game starts from a new fixed baseline. Other saved versions remain in your archive.";
    $<HTMLProgressElement>("lab-progress").max = current?.plan.trials ?? 1;
    $<HTMLProgressElement>("lab-progress").value = current?.blocks.length ?? 0;
    if (current?.summary && current.plan.source === labSource.digest) {
      const s = current.summary, d = current.development;
      const errors = (score: NonNullable<LabRun["development"]>["before"]) => score.seats.reduce((n, seat) => n + seat.missedWins + seat.avoidableLosses, 0);
      $("lab-summary").innerHTML = `<div class="lab-metrics"><div><span>CANDIDATE SCORE</span><strong>${percent(s.candidateScore)}</strong></div><div><span>OBSERVED GAIN</span><strong>${s.meanGain == null ? "—" : `${s.meanGain >= 0 ? "+" : ""}${(s.meanGain * 100).toFixed(1)} pp`}</strong></div><div><span>LOWER GAIN BOUND</span><strong>${s.lowerGain == null ? "—" : `${(s.lowerGain * 100).toFixed(1)} pp`}</strong></div></div><p>${s.completedGames} rule-complete games · ${s.trials} seed blocks · ${s.capped} capped · 0 provider calls.</p>${d ? `<p>Development tactical errors: ${errors(d.before)} → ${errors(d.after)} across ${d.after.rows.length} isolated target positions.</p>` : ""}<p class="lab-verdict">${s.qualification === "pass" ? "Development checks passed. Independent competition qualification is still required." : "This experiment does not establish an improvement under the predeclared checks. Your incumbent is retained."}</p><details><summary>Conditions and evidence</summary><p>Equal configuration and inference allowances; candidate changes numeric parameters only. Win = 1, draw = 0.5, loss = 0. Confidence uses paired seed blocks and conservative simultaneous lower bounds.</p><p>${esc(s.failures.join(" · ") || "No development gate failures.")}</p><p>Plan ${esc(current.plan.digest)} · source ${esc(labSource.digest)}</p></details><div class="form-actions"><button data-lab-export="${esc(current.id)}">Export experiment</button><button data-lab-replay="${esc(current.id)}">Replay a candidate game ↗</button></div>`;
    } else if (current) {
      $("lab-summary").innerHTML = `<p>${current.blocks.length} / ${current.plan.trials} paired blocks saved.</p><p>${esc(current.plan.source !== labSource.digest ? "Historical build: preserved as saved evidence. Export to inspect; this build does not reverify or execute this run." : current.error ?? "The incumbent stays selected. Failed and cancelled experiments stay in the history.")}</p><button data-lab-export="${esc(current.id)}">Export saved evidence</button>`;
    }
    $("lab-versions").innerHTML = archive.versions.length ? `<div class="results-table-wrap"><table class="results-table"><thead><tr><th scope="col">VERSION</th><th scope="col">GAME</th><th scope="col">SELECTION</th><th scope="col">ACTIONS</th></tr></thead><tbody>${archive.versions.map(v => `<tr><td><strong>Local policy r${v.revision}</strong><small class="mono">${esc(v.digest.slice(0, 16))}</small></td><td>${esc(v.config.rules.name)}</td><td>${v.digest === archive.selected ? "Selected incumbent" : v.parent ? "Candidate / prior version" : "Fixed baseline"}</td><td><div class="form-actions"><button data-lab-select="${esc(v.digest)}" ${busy || !executable(v) || v.digest === archive.selected ? "disabled" : ""}>Select</button><button data-lab-use="${esc(v.digest)}" ${busy || !executable(v) ? "disabled" : ""}>Use in Arena ↗</button><button data-lab-version-export="${esc(v.digest)}">Export</button></div></td></tr>`).join("")}</tbody></table></div>` : '<div class="results-empty"><p>Run an experiment or import a compatible Lab version to create your first contender.</p></div>';
    $("lab-history").innerHTML = archive.runs.length ? `<div class="lab-history-list">${[...archive.runs].reverse().map(run => `<article><div><strong>${esc(run.parent.config.rules.name)} · ${esc(run.status)}</strong><p>${run.blocks.length}/${run.plan.trials} blocks · seed ${run.plan.seed} · ${esc(new Date(run.createdAt).toLocaleString())}</p></div><div><button data-lab-show="${esc(run.id)}">Inspect</button><button data-lab-export="${esc(run.id)}">Export</button></div></article>`).join("")}</div>` : '<p class="muted">Experiments stay on this device. Nothing is uploaded.</p>';
  }
  async function initialize() {
    try {
      const raw = options.storage()?.getItem(KEY);
      if (raw) {
        if (raw.length > LAB_MAX_BYTES) throw Error("Saved Lab archive exceeds its limit. Export or remove it through browser/device storage.");
        const a = JSON.parse(raw) as Archive;
        if (a.schema !== KEY || !Array.isArray(a.versions) || a.versions.length > 64 || !Array.isArray(a.runs) || a.runs.length > LAB_MAX_RUNS
          || !Array.isArray(a.selections) || a.selections.length > 64 || !(a.selected === null || typeof a.selected === "string")) throw Error("Saved Lab archive is malformed; it was left untouched.");
        a.versions = await Promise.all(a.versions.map(readLabVersion));
        if (a.selected && !a.versions.some(v => v.digest === a.selected)) throw Error("Selected Lab version is unavailable.");
        for (const run of a.runs) {
          if (run.plan?.source === labSource.digest) await validateLabRun(run);
          else {
            if (run.schema !== "builderwars.browser-lab.v1" || typeof run.id !== "string" || typeof run.createdAt !== "string" || !run.plan || !Array.isArray(run.blocks)) throw Error("Malformed historical experiment.");
            const { digest, ...body } = run.plan;
            if (digest !== await cryptoDigest(JSON.stringify(body))) throw Error("Historical plan digest mismatch.");
            await readLabVersion(run.parent); if (run.candidate) await readLabVersion(run.candidate);
          }
          if (!Array.isArray(run.blocks) || run.blocks.length > run.plan.trials || !["prepared", "sampling", "training", "evaluating", "completed", "failed", "cancelled", "interrupted"].includes(run.status)) throw Error("Malformed saved experiment.");
          if (run.candidate && run.plan.source === labSource.digest) await validateLabVersion(run.candidate);
          if (["prepared", "sampling", "training", "evaluating"].includes(run.status)) {
            run.status = "interrupted"; run.error = "Interrupted before completion. No work was restarted. Start a fresh experiment.";
          }
        }
        archive = a; current = archive.runs.at(-1); await save();
        if (current) status(current.status === "completed" ? "Saved comparison restored. No work has restarted." : current.error ?? `Saved ${current.status} experiment.`);
      }
    } catch (error) { unavailable = true; status((error as Error).message + " Existing saved data was left untouched. Free Arena play remains available."); }
    finally { startup = false; render(); }
  }
  function stopWorker() { clearTimeout(timer); worker?.terminate(); worker = null; }
  function finish() { stopWorker(); working = false; busy = false; render(); }
  function exclusive(action: () => Promise<void>) {
    if (busy || startup) return;
    busy = true; ++epoch; render();
    chain = chain.then(action).catch(error => status((error as Error).message)).finally(finish);
  }
  async function fail(message: string, expectedEpoch: number) {
    if (expectedEpoch !== epoch) return;
    ++epoch; stopWorker(); working = false; render();
    if (current && current.status !== "completed") { current.status = "failed"; current.error = message; }
    try { await save(); } catch (error) { message += ` Saving failed: ${(error as Error).message}`; }
    status(message + " Your incumbent remains selected."); finish();
  }
  function cancel(message = "Cancelled by you. Saved partial evidence is retained; no complete comparison is claimed.") {
    if (!working) return;
    ++epoch; stopWorker(); working = false; render();
    chain = chain.then(async () => {
      if (current && current.status !== "completed") { current.status = "cancelled"; current.error = message; }
      try { await save(); status(message); } catch (error) { status(`${message} Saving failed: ${(error as Error).message}`); }
      finish();
    });
  }
  $("lab-form").onsubmit = event => {
    event.preventDefault();
    if (busy || startup || unavailable) return;
    busy = true; working = true; current = undefined; render();
    const generation = ++epoch;
    chain = chain.then(async () => {
      options.ensure();
      if (archive.runs.length >= LAB_MAX_RUNS || archive.versions.length >= 62) throw Error("Your Lab archive is full. Export experiments and versions before clearing it.");
      const game = $<HTMLSelectElement>("lab-game").value;
      const selected = archive.versions.find(v => v.digest === archive.selected && executable(v) && v.config.rules.kind === game);
      const parent = selected ?? await labBaseline(game);
      const seedText = $<HTMLInputElement>("lab-seed").value;
      const seed = seedText === "" ? crypto.getRandomValues(new Uint32Array(1))[0] : Number(seedText);
      const run = await makeLabRun(parent, seed, Number($<HTMLSelectElement>("lab-trials").value));
      if (generation !== epoch) return;
      const next = structuredClone(archive); next.runs.push(run);
      if (!next.versions.some(v => v.digest === parent.digest)) next.versions.push(parent);
      if (!selected) { next.selected = parent.digest; next.selections.push(parent.digest); }
      await save(next); // No worker work until the plan and incumbent are durably saved.
      archive = next; current = run;
      if (generation !== epoch) { run.status = "cancelled"; run.error = "Cancelled during preparation; no worker work started."; await save(); render(); return; }
      worker = new Worker(new URL("./browser-lab-worker.ts", import.meta.url), { type: "module", name: "builderwars-local-lab" });
      const owned = worker;
      timer = setTimeout(() => { if (generation === epoch) cancel("The 90-second work limit was reached. Partial evidence is retained; no complete comparison is claimed."); }, 90000);
      worker.onerror = () => { stopWorker(); chain = chain.then(() => fail("The local worker failed. Reload or export the saved plan and try a fresh experiment.", generation)); };
      worker.onmessage = event => {
        chain = chain.then(async () => {
          if (generation !== epoch || !current) return;
          if (event.data.type === "ready") {
            owned.postMessage({ type: "start", run: current });
            status("Plan saved. Starting local work.");
          } else if (event.data.type === "checkpoint") {
            const next = event.data.run as LabRun;
            if (next.id !== current.id || next.plan.digest !== current.plan.digest) throw Error("Worker checkpoint custody mismatch.");
            current = next; archive.runs[archive.runs.length - 1] = next;
            if (next.candidate) addVersion(await validateLabVersion(next.candidate));
            await save();
            if (generation !== epoch) return;
            status(next.status === "completed" ? "Comparison completed. The incumbent is unchanged. Inspect the evidence before selecting a candidate." : `${next.status === "sampling" ? "Finding isolated tactical cases" : next.status === "training" ? "Calibrating local numeric parameters" : "Comparing frozen versions"} · ${next.blocks.length}/${next.plan.trials} paired blocks saved.`);
            render(); owned.postMessage({ type: "ack" });
          } else if (event.data.type === "error") { clearTimeout(timer); await fail(event.data.message, generation); }
          else if (event.data.type === "done") { clearTimeout(timer); finish(); }
        }).catch(error => fail((error as Error).message, generation));
      };
      status("Plan saved. Loading the pinned local worker.");
    }).catch(error => fail((error as Error).message, generation));
  };
  $("lab-cancel").onclick = () => cancel();
  $<HTMLSelectElement>("lab-game").onchange = render;
  $("lab-import").onclick = () => $<HTMLInputElement>("lab-file").click();
  $<HTMLInputElement>("lab-file").onchange = async event => {
    const input = event.target as HTMLInputElement, file = input.files?.[0];
    if (!file || busy || startup || unavailable) return;
    exclusive(async () => {
    try {
      options.ensure(); if (file.size > 24000) throw Error("Import a single bounded Lab version, up to 24KB.");
      const version = await validateLabImport(JSON.parse(await file.text()));
      if (archive.versions.length >= 64) throw Error("Version archive is full; export before clearing.");
      const next = structuredClone(archive); if (!next.versions.some(v => v.digest === version.digest)) next.versions.push(version); await save(next); archive = next; status("Version imported. It is not selected and no work has started."); render();
    } catch (error) { status((error as Error).message); }
    finally { input.value = ""; }
    });
  };
  $("lab").addEventListener("click", event => {
    const button = (event.target as HTMLElement).closest<HTMLButtonElement>("button");
    if (!button) return;
    void (async () => {
      if (button.dataset.labSelect && !busy) {
        exclusive(async () => {
        const v = await validateLabVersion(archive.versions.find(v => v.digest === button.dataset.labSelect));
        const next = structuredClone(archive); next.selected = v.digest; next.selections.push(v.digest); next.selections = next.selections.slice(-64);
        await save(next); archive = next; status("Version selected for local development. This is your choice, not certified promotion."); render();
        });
      } else if (button.dataset.labUse && !busy) {
        await options.use(await validateLabVersion(archive.versions.find(v => v.digest === button.dataset.labUse)));
      } else if (button.dataset.labVersionExport) {
        const version = await readLabVersion(archive.versions.find(v => v.digest === button.dataset.labVersionExport));
        await options.export(`builderwars-lab-version-${version.digest.slice(0, 16)}.json`, version);
      } else if (button.dataset.labExport) {
        const run = archive.runs.find(r => r.id === button.dataset.labExport); if (!run) return;
        await options.export(`builderwars-lab-experiment-${run.id}.json`, structuredClone(run));
      } else if (button.dataset.labShow && !busy) {
        current = archive.runs.find(r => r.id === button.dataset.labShow); render(); status(`Inspecting ${current?.status} experiment. No work has restarted.`);
      } else if (button.dataset.labReplay) {
        const run = archive.runs.find(r => r.id === button.dataset.labReplay); if (!run?.candidate) return;
        const game = run.blocks[0]?.games.findIndex(g => g.version === run.candidate!.digest);
        if (game == null || game < 0) return;
        options.replay(replay(labReplay(run, 0, game)).record);
      }
    })().catch(error => status((error as Error).message));
  });
  $("lab-rollback").onclick = () => {
    if (busy || archive.selections.length < 2) return;
    exclusive(async () => { const next = structuredClone(archive); next.selections.pop(); next.selected = next.selections.at(-1) ?? null; await save(next); archive = next; status("Prior selection restored. Versions and experiments remain in the archive."); render(); });
  };
  $("lab-archive-export").onclick = () => void (async () => {
    const raw = options.storage()?.getItem(KEY);
    if (!raw) throw Error("No saved Lab archive is available.");
    if (raw.length > LAB_MAX_BYTES) throw Error("Archive exceeds the export bound; use browser/device storage recovery.");
    await options.export("builderwars-lab-archive.json", {schema:"builderwars.lab-archive-export.v1", originalBytes:raw});
    status("Complete original archive exported. Historical evidence remains saved on this device.");
  })().catch(error => status((error as Error).message));
  $("lab-clear").onclick = () => {
    if (busy || !confirm("Clear all Lab experiments, versions and selections on this device? Export the evidence first. Arena matches and practice memory are separate.")) return;
    exclusive(async () => { const port = options.storage(); if (!port) throw Error("Device storage is unavailable; saved data could not be cleared."); port.removeItem(KEY); await port.flush?.(); archive = empty(); current = undefined; unavailable = false; $("lab-summary").textContent = "Ready for a fresh experiment."; status("Lab data cleared. No work has started."); render(); });
  };
  document.addEventListener("visibilitychange", () => { if (document.hidden) cancel("Work stopped when the app went into the background. No work restarts automatically."); });
  render(); void initialize();
  return { cancel };
}
