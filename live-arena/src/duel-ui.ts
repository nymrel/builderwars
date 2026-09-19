import { DuelRoom, type DuelView } from "./duel";
import { RULES, replay, square, nimHeaps, encodeReplay } from "./runtime";
import { decide, type Agent, type Model } from "./models";
import { publicLinkOrigin } from "./public-links";
import { duelInviteId, duelSetupBrief, duelPublicState } from "./duel-setup";

const esc = (value: string) => value.replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);
export const duelMarkup = `<section id="duel" class="view" hidden aria-labelledby="duel-title">
  <p class="eyebrow">TWO FRIENDS. TWO AGENTS. ONE BOARD.</p><h1 id="duel-title">Let your agents<br>settle it.</h1>
  <p class="subtitle">Choose an agent, send your friend an invite, and watch them play. Try it free—no account needed.</p>
  <ol class="duel-progress" aria-label="Duel setup progress"><li id="duel-step-agent">1. Choose your agent</li><li id="duel-step-invite">2. Invite a friend</li><li id="duel-step-play">3. Both press Ready</li></ol>
  <p id="duel-status" class="notice duel-notice" role="status" aria-live="polite">Start with a free agent, or connect one you already use.</p>
  <div id="duel-incoming-card" class="duel-incoming-card" hidden><strong>You’re invited.</strong> Choose your agent below, then join to see your friend’s game. <button id="duel-new">Set up my own duel instead</button></div>
  <div class="duel-layout"><div class="workspace-form duel-setup">
    <section class="duel-step"><h2>1. Choose your agent</h2>
    <p id="duel-agent" class="duel-agent-summary"></p>
    <p id="duel-agent-locked" class="muted" hidden>Leave or stop this duel to change your agent.</p>
    <div class="duel-choice-actions"><button id="duel-free">Use a free agent</button><button id="duel-configure">Connect my agent</button><button id="duel-assistant">Ask ChatGPT or Claude to help ↗</button></div>
    <label>Name on the board<input id="duel-name" maxlength="64" autocomplete="off" placeholder="My agent"></label>
    <p class="muted">The free agent is ready now. Your own model uses your existing connection and provider account.</p></section>
    <section class="duel-step"><h2>2. Meet your opponent</h2><div id="duel-create-fields">
    <label>What should they play?<select id="duel-game">${Object.entries(RULES).map(([key, value]) => `<option value="${key}">${value.name}</option>`).join("")}</select></label>
    <details id="duel-advanced"><summary>Game length and model usage</summary><p class="muted">The game stops at this total move limit. Token limits are requested per model turn; your provider or local client controls actual usage.</p>
    <div class="settings-row"><label>Total move limit<input id="duel-limit" type="number" min="2" max="400" value="80"></label>
    <label>Tokens per model turn<input id="duel-tokens" type="number" min="256" max="16384" value="2048"></label></div></details>
    <button id="duel-create" class="primary">Create invitation ↗</button><p class="muted">Creating an invite does not start the game.</p></div>
    <div id="duel-invitation" hidden><label>Your invitation link<input id="duel-link" readonly></label><button id="duel-copy" class="primary">Copy invite for your friend</button><p class="muted">Send it in your usual chat. Keep this tab open while your friend joins.</p></div>
    <div id="duel-join-fields"><label>Already have an invite?<input id="duel-incoming" placeholder="Paste your friend’s BuilderWars link" autocomplete="off"></label><button id="duel-join">Join my friend’s duel</button></div>
    <div id="duel-lobby" hidden><p id="duel-you"></p><p id="duel-friend"></p></div></section>
    <section class="duel-step"><h2>3. Ready when you both are</h2><p id="duel-terms">You’ll see the game and limits here before anything starts.</p>
    <button id="duel-ready" class="primary" disabled>Ready — let my agent play</button>
    <button id="duel-leave" hidden>Leave / stop duel</button>
    <p id="duel-usage" class="muted">Free agents have no model charges. Each person presses Ready to allow their agent to play this one game.</p></section>
  </div><div class="duel-stage"><div id="duel-board" class="duel-empty">Your agent <span>⚔</span> Their agent</div>
    <p id="duel-score" class="subtitle">A friendly rivalry starts with an invite.</p>
    <div class="result-actions"><button id="duel-replay" disabled>Copy replay link</button><button id="duel-download" disabled>Download replay</button></div>
    <p class="muted">Keep both tabs open. You can stop at any time. Refreshing or leaving ends your connection.</p>
    <details class="duel-details"><summary>How connections and results work</summary><p>Both devices check every move. Agent identities are self-reported; games are exhibitions, not certified rankings. Keys and private prompts stay on your device. Direct connections can reveal your IP to your opponent; some networks block them.</p><p>Invitations are live rooms, not scheduled matches. Share the invite only with your intended opponent.</p></details>
    <a class="duel-guide-link" href="https://builderwars.com/duels" target="_blank" rel="noopener">Quick guide for people and assistants ↗</a>
  </div></div>
  <script id="duel-agent-state" type="application/json">{}</script>
  <dialog id="duel-help-dialog" aria-labelledby="duel-help-title"><div class="dialog-heading"><h2 id="duel-help-title">Let your assistant handle setup</h2><button id="duel-help-close" aria-label="Close assistant instructions">×</button></div>
    <p>Copy this message into ChatGPT, Claude, or your coding agent. An assistant with browser tools can follow the setup with you. Otherwise, it can guide you step by step.</p>
    <p class="muted">This asks for setup help. It does not automatically connect a chat subscription as a player. Your assistant will use a supported connection you already have, or help you try a free agent.</p>
    <label>Message for your assistant<textarea id="duel-help-text" rows="9" readonly spellcheck="false"></textarea></label>
    <p id="duel-help-status" role="status" class="muted">No keys, connection tokens or private strategy are included. If you’re joining, this message includes your invitation link.</p>
    <button id="duel-help-copy" class="primary">Copy message</button> <a href="https://builderwars.com/duel-agent.md" target="_blank" rel="noopener">Read the assistant workflow ↗</a>
  </dialog></section>`;

export function mountDuel(options: { agent: () => Agent; models: () => Model[]; configure: () => void; useFree: () => void; rename: (name: string) => void;
  enter: () => void; ensure: (agent: Agent) => void; share: (text: string, message: string) => Promise<void>;
  download: (name: string, value: unknown) => Promise<unknown> }) {
  const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
  let invite = "", incomingId = "", working = false, wasActive = false;
  const room = new DuelRoom((state, agent, tokens, signal) => {
    options.ensure(agent); return decide(state, agent, tokens, signal, options.models());
  }, render);
  function render(view: DuelView = room.view()) {
    const ended = wasActive && !view.active;
    if (ended) {
      incomingId = ""; invite = "";
      $<HTMLInputElement>("duel-incoming").value = "";
      if (location.hash.startsWith("#duel=")) history.replaceState(null, "", `${location.pathname}${location.search}#duel`);
    }
    wasActive = view.active;
    $("duel-status").textContent = view.status;
    if (ended && !$("duel").hidden) $("duel-status").scrollIntoView({ block: "nearest" });
    const agent = options.agent();
    $("duel-agent").textContent = view.active && view.seat === 0 && view.offer
      ? `${view.offer.agent.name} · ${view.offer.agent.model || "Your harness"}`
      : `${agent.name} · ${agent.kind === "bot" ? "Free built-in agent" : agent.kind === "human" ? "Choose an agent below" : agent.model || "Your harness"}`;
    const publicState = duelPublicState(view, $<HTMLSelectElement>("duel-game").value,
      Number($<HTMLInputElement>("duel-limit").value), Number($<HTMLInputElement>("duel-tokens").value), !!incomingId);
    $("duel-agent-state").textContent = JSON.stringify(publicState);
    $("duel").dataset.duelPhase = publicState.phase;
    const locked = view.active && (view.seat === 0 || view.ready);
    $("duel-agent-locked").hidden = !locked;
    if (document.activeElement !== $("duel-name")) $<HTMLInputElement>("duel-name").value = agent.name;
    for (const id of ["duel-name", "duel-free", "duel-configure", "duel-assistant"]) $(id).toggleAttribute("disabled", locked);
    $("duel-incoming-card").hidden = !incomingId || view.active;
    $("duel-create-fields").hidden = view.active || !!incomingId;
    $("duel-lobby").hidden = !view.active || !view.offer;
    $("duel-you").textContent = view.ready ? "✓ You’re ready" : "○ You haven’t pressed Ready yet";
    $("duel-friend").textContent = !view.opponentConnected ? "○ Waiting for your friend to join" : view.opponentReady ? "✓ Your friend is ready" : "○ Your friend joined · Ready not yet confirmed";
    $("duel-step-agent").classList.toggle("done", view.active);
    $("duel-step-invite").classList.toggle("done", view.opponentConnected);
    $("duel-step-play").classList.toggle("done", !!view.record);
    $("duel-usage").textContent = agent.kind === "bot" ? "Your built-in agent is free. Your friend uses their own connection. Both people press Ready to allow this one game."
      : "Ready allows your agent’s turns in this game, up to the displayed limits. Your provider may charge for model calls. Your keys and private prompts stay on your device.";
    $("duel-join-fields").hidden = view.active;
    $("duel-invitation").hidden = !view.active || !invite;
    $("duel-leave").hidden = !view.active;
    $<HTMLButtonElement>("duel-configure").disabled = view.active && (view.seat === 0 || view.ready);
    $<HTMLButtonElement>("duel-ready").disabled = !view.active || !view.offer || view.ready;
    $("duel-ready").textContent = view.ready ? "You’re ready ✓" : "Ready — let my agent play";
    $("duel-terms").textContent = view.offer
      ? `${RULES[view.offer.game].name} · up to ${view.offer.moveLimit} moves. ${view.offer.maxTokens} requested tokens per model turn. ${view.seat === 0 ? "Your agent plays first." : "Your friend’s agent plays first."}`
      : "You’ll see the game and limits here before anything starts.";
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
    try { await action(); } catch (error) { report((error as Error).message); }
    finally { working = false; for (const id of ["duel-create", "duel-join"]) $<HTMLButtonElement>(id).disabled = false; }
  }
  function report(message: string) { $("duel-status").textContent = message; $("duel-status").scrollIntoView({ block: "nearest" }); }
  $("duel-configure").onclick = options.configure;
  $("duel-free").onclick = () => { options.useFree(); render(); $("duel-status").textContent = "Your free agent is ready. Create an invitation or join your friend."; };
  $("duel-name").onchange = () => { options.rename($<HTMLInputElement>("duel-name").value.trim() || "My agent"); render(); };
  for (const id of ["duel-game", "duel-limit", "duel-tokens"]) $(id).addEventListener("change", () => render());
  $("duel-new").onclick = () => { incomingId = ""; $<HTMLInputElement>("duel-incoming").value = ""; history.replaceState(null, "", `${location.pathname}${location.search}#duel`); render(); };
  $("duel-assistant").onclick = () => {
    try {
      const view = room.view(), offer = view.active ? view.offer : null;
      const rawInvite = $<HTMLInputElement>("duel-incoming").value.trim();
      const inviteId = rawInvite ? duelInviteId(rawInvite, location.origin) : undefined;
      $<HTMLTextAreaElement>("duel-help-text").value = duelSetupBrief({ game: offer?.game ?? $<HTMLSelectElement>("duel-game").value,
        moveLimit: offer?.moveLimit ?? Number($<HTMLInputElement>("duel-limit").value),
        maxTokens: offer?.maxTokens ?? Number($<HTMLInputElement>("duel-tokens").value), inviteId, joined: view.active && view.seat === 1 && !!offer });
      $<HTMLDialogElement>("duel-help-dialog").showModal();
    } catch (error) { report((error as Error).message); }
  };
  $("duel-help-close").onclick = () => $<HTMLDialogElement>("duel-help-dialog").close();
  $("duel-help-copy").onclick = async () => {
    try { await options.share($<HTMLTextAreaElement>("duel-help-text").value, "Assistant message copied."); $("duel-help-status").textContent = "Copied. Paste this message into your assistant’s conversation."; }
    catch { $("duel-help-status").textContent = "Copy wasn’t available. Select the message below and copy it manually."; $<HTMLTextAreaElement>("duel-help-text").select(); }
  };
  $("agent-dialog").addEventListener("close", () => render());
  $("duel-create").onclick = () => void attempt(async () => {
    options.ensure(options.agent()); invite = "";
    const id = await room.host(options.agent(), $<HTMLSelectElement>("duel-game").value,
      Number($<HTMLInputElement>("duel-limit").value), Number($<HTMLInputElement>("duel-tokens").value));
    invite = `${publicLinkOrigin(location.origin)}/#duel=${id}`;
    $<HTMLInputElement>("duel-link").value = invite; render();
  });
  $("duel-copy").onclick = () => void attempt(async () => {
    try { await options.share(invite, "Duel invitation copied."); $("duel-status").textContent = "Invitation copied. Send it to your friend."; }
    catch { report("Copy wasn’t available. Select your invitation, copy it and send it to your friend."); $<HTMLInputElement>("duel-link").select(); }
  });
  $("duel-join").onclick = () => void attempt(async () => {
    const id = duelInviteId($<HTMLInputElement>("duel-incoming").value, location.origin);
    incomingId = id; invite = ""; await room.join(id);
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
    if (!id) { render(); return; }
    if (!/^[a-zA-Z0-9_-]{1,100}$/.test(id)) { $("duel-status").textContent = "This invitation looks incomplete. Ask your friend for a fresh link."; return; }
    incomingId = id;
    // Loading an invite never connects or starts inference without a click.
    $<HTMLInputElement>("duel-incoming").value = `${publicLinkOrigin(location.origin)}/#duel=${id}`;
    render();
    $("duel-status").textContent = "You’ve been challenged. Use the free agent or connect your own, then join your friend.";
  } };
}
