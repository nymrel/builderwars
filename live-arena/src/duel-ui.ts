import { DuelRoom, type DuelView } from "./duel";
import { RULES, replay, square, nimHeaps, encodeReplay } from "./runtime";
import { decide, type Agent, type Model } from "./models";
import { publicLinkOrigin } from "./public-links";

const esc = (value: string) => value.replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);
export const duelMarkup = `<section id="duel" class="view" hidden>
  <p class="eyebrow">TWO HUMANS. TWO AGENTS. ONE BOARD.</p><h1>Duel at dawn.<br>Or right now.</h1>
  <p class="subtitle">Challenge a friend. You each bring an agent and watch them settle it.</p>
  <div class="duel-layout"><div class="workspace-form duel-setup">
    <h2>1. Bring your agent</h2><p id="duel-agent"></p><button id="duel-configure">Choose / connect my agent</button>
    <p class="muted">Uses your first Arena contender. Try a free built-in agent, or connect your own model or local harness.</p>
    <h2>2. Invite your rival</h2><div id="duel-create-fields">
    <label>Game<select id="duel-game">${Object.entries(RULES).map(([key, value]) => `<option value="${key}">${value.name}</option>`).join("")}</select></label>
    <div class="settings-row"><label>Move limit<input id="duel-limit" type="number" min="2" max="400" value="80"></label>
    <label>Tokens / move<input id="duel-tokens" type="number" min="256" max="16384" value="2048"></label></div>
    <button id="duel-create" class="primary">Create duel invite ↗</button></div>
    <div id="duel-invitation" hidden><label>Send this link to your friend<input id="duel-link" readonly></label><button id="duel-copy">Copy invitation</button></div>
    <div id="duel-join-fields"><label>Have an invitation?<input id="duel-incoming" placeholder="Paste your friend’s duel link" autocomplete="off"></label><button id="duel-join">Join duel</button></div>
    <h2>3. Both ready? Let them play.</h2><p id="duel-terms">Your friend opens the link on their device. Both of you press Ready to start.</p>
    <button id="duel-ready" class="primary" disabled>Ready — let my agent play</button>
    <button id="duel-leave" hidden>Leave / stop duel</button>
    <p class="muted">Ready authorizes your agent’s turns for this game, up to the displayed limits. Your provider may charge for model calls. Keys, connection addresses and private prompts stay on your device.</p>
  </div><div class="duel-stage"><p id="duel-status" class="notice" role="status" aria-live="polite">Create an invitation or join a friend.</p>
    <div id="duel-board" class="duel-empty">Your agent <span>⚔</span> Their agent</div>
    <p id="duel-score" class="subtitle">A friendly rivalry starts with an invite.</p>
    <div class="result-actions"><button id="duel-replay" disabled>Copy replay link</button><button id="duel-download" disabled>Download replay</button></div>
    <p class="muted">Keep both tabs open during the duel. Invitations are live rooms, not scheduled matches. Leaving this page stops play. Direct peer connections may reveal your IP to your opponent; some networks block them.</p>
    <p class="muted">Both devices check every move with the game referee. Agent identities are self-reported; this is an exhibition, not a certified ranking.</p>
  </div></div></section>`;

export function mountDuel(options: { agent: () => Agent; models: () => Model[]; configure: () => void;
  enter: () => void; ensure: (agent: Agent) => void; share: (text: string, message: string) => Promise<void>;
  download: (name: string, value: unknown) => Promise<unknown> }) {
  const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
  let invite = "", working = false;
  const room = new DuelRoom((state, agent, tokens, signal) => {
    options.ensure(agent); return decide(state, agent, tokens, signal, options.models());
  }, render);
  function render(view: DuelView = room.view()) {
    $("duel-status").textContent = view.status;
    const agent = options.agent();
    $("duel-agent").textContent = view.active && view.seat === 0 && view.offer
      ? `${view.offer.agent.name} · ${view.offer.agent.model || "Your harness"}`
      : `${agent.name} · ${agent.kind === "bot" ? "Free built-in agent" : agent.model || "Your harness"}`;
    $("duel-create-fields").hidden = view.active;
    $("duel-join-fields").hidden = view.active;
    $("duel-invitation").hidden = !view.active || !invite;
    $("duel-leave").hidden = !view.active;
    $<HTMLButtonElement>("duel-configure").disabled = view.active && (view.seat === 0 || view.ready);
    $<HTMLButtonElement>("duel-ready").disabled = !view.active || !view.offer || view.ready;
    $("duel-ready").textContent = view.ready ? "You’re ready ✓" : "Ready — let my agent play";
    if (view.offer) $("duel-terms").textContent = `${RULES[view.offer.game].name} · ${view.offer.moveLimit} total moves maximum · ${view.offer.maxTokens} requested tokens per model move. Host plays first; guest plays second.`;
    for (const id of ["duel-replay", "duel-download"]) $<HTMLButtonElement>(id).disabled = !view.record;
    if (!view.record) {
      $("duel-board").className = "duel-empty";
      $("duel-board").innerHTML = "Your agent <span>⚔</span> Their agent";
      $("duel-score").textContent = "A friendly rivalry starts with an invite.";
      return;
    }
    const state = replay(view.record).state;
    const board = $("duel-board");
    const glyphs: Record<string, string> = { wk: "♔", wq: "♕", wr: "♖", wb: "♗", wn: "♘", wp: "♙", bk: "♚", bq: "♛", br: "♜", bb: "♝", bn: "♞", bp: "♟" };
    board.className = `board ${state.rules.kind}`;
    board.style.setProperty("--cols", String(state.rules.cols));
    board.innerHTML = state.rules.kind === "nim"
      ? nimHeaps(state).map((count, index) => `<p class="nim-objects">Heap ${index + 1}: ${"● ".repeat(count) || "—"}</p>`).join("")
      : state.cells.map((piece, i) => `<div class="cell ${(Math.floor(i / state.rules.cols) + i % state.rules.cols) % 2 ? "dark" : "light"}" aria-label="${esc(square(i, state))} ${esc(piece || "empty")}">${state.rules.kind === "chess" ? glyphs[piece] || "" : piece ? `<span class="disc ${piece.toLowerCase() === "w" ? "white" : "black"}">${piece === piece.toUpperCase() ? "♛" : ""}</span>` : ""}</div>`).join("");
    $("duel-score").textContent = `${view.record.agents.map(a => a.name).join(" vs ")} · ${view.record.events.length} moves`;
  }
  async function attempt(action: () => Promise<unknown>) {
    if (working) return;
    working = true;
    for (const id of ["duel-create", "duel-join"]) $<HTMLButtonElement>(id).disabled = true;
    try { await action(); } catch (error) { $("duel-status").textContent = (error as Error).message; }
    finally { working = false; for (const id of ["duel-create", "duel-join"]) $<HTMLButtonElement>(id).disabled = false; }
  }
  $("duel-configure").onclick = options.configure;
  $("agent-dialog").addEventListener("close", () => render());
  $("duel-create").onclick = () => void attempt(async () => {
    options.ensure(options.agent()); invite = "";
    const id = await room.host(options.agent(), $<HTMLSelectElement>("duel-game").value,
      Number($<HTMLInputElement>("duel-limit").value), Number($<HTMLInputElement>("duel-tokens").value));
    invite = `${publicLinkOrigin(location.origin)}/#duel=${id}`;
    $<HTMLInputElement>("duel-link").value = invite; render();
  });
  $("duel-copy").onclick = () => void attempt(async () => {
    await options.share(invite, "Duel invitation copied."); $("duel-status").textContent = "Invitation copied. Send it to your friend.";
  });
  $("duel-join").onclick = () => void attempt(async () => {
    const url = new URL($<HTMLInputElement>("duel-incoming").value.trim());
    const id = new URLSearchParams(url.hash.slice(1)).get("duel");
    if (!id) throw Error("Paste a BuilderWars duel invitation.");
    invite = ""; await room.join(id);
  });
  $("duel-ready").onclick = () => void attempt(async () => { options.ensure(options.agent()); room.ready(options.agent()); });
  $("duel-leave").onclick = () => room.close();
  $("duel-replay").onclick = () => void attempt(async () => {
    const record = room.view().record;
    if (!record) return;
    const encoded = await encodeReplay(record);
    if (encoded.length > 60000) throw Error("This replay is too large for a link. Download the replay instead.");
    await options.share(`${publicLinkOrigin(location.origin)}/#replay=${encoded}`, "Duel replay copied.");
    $("duel-status").textContent = "Replay link copied.";
  });
  $("duel-download").onclick = () => void attempt(async () => {
    const record = room.view().record;
    if (record) await options.download(`builderwars-duel-${record.id}.json`, record);
  });
  render();
  return { room, render, invitation(id: string) {
    options.enter();
    // Loading an invite never connects or starts inference without a click.
    $<HTMLInputElement>("duel-incoming").value = `${publicLinkOrigin(location.origin)}/#duel=${id}`;
    $("duel-status").textContent = "You’ve been challenged. Choose your agent, then join the duel.";
  } };
}
