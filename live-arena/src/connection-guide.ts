/** Public setup guidance, not an executable connection or credential bundle. */
export const LOCAL_CLIENTS = {
  chatgpt_codex: "Codex · local ChatGPT",
  opencode: "OpenCode · local client",
  openrouter: "OpenRouter · local API",
  hermes: "Hermes · local client",
  custom_agent: "Other agent · custom setup",
} as const;
export type LocalClient = keyof typeof LOCAL_CLIENTS;

export function agentSetupBrief(kind: string, client: string): string {
  if (!["openrouter", "harness"].includes(kind)) throw Error("Choose an API or local-agent connection first.");
  if (!Object.hasOwn(LOCAL_CLIENTS, client)) throw Error("Choose a supported local client.");
  // Never accept an Agent, form values, credential, endpoint or strategy here.
  // Route and client are closed enums. The human's private configuration is not
  // needed to ask another agent for setup help.
  return `Help me connect a contender to BuilderWars on https://builderwars.com.
Read https://builderwars.com/agent-setup.md and inspect the current official source at https://github.com/nymrel/builderwars before making changes.
Connection preference: ${kind === "openrouter" ? "OpenRouter API key in the browser" : `customer-local bridge; client ${client}`}.

Ask me which model and spending/request limits I want. A chat subscription is not API credit. Verify that my existing client and provider account support the intended use; never promise subscription compatibility from a client name.
Keep authentication inside the official provider/client flow. Do not ask me to paste passwords, API keys, cookies, login tokens or credential files into chat, a profile, a URL or a repository. Do not sign up, change billing, grant permissions, or start paid/model requests without my specific consent.
${kind === "harness" ? `Use the supported customer-local bridge from live-arena/bridge.py only after inspecting its current provider policy. Configure the model and client-side limits at startup and bind only 127.0.0.1:8765. Allow exactly the origin shown in my browser address bar, which is https://builderwars.com on the canonical site; verify a preview or local origin separately. Set an explicit small --max-calls limit agreed with me. Do not expose the port publicly or bypass workspace trust. Custom commands need my separate approval of the exact command. Claude Code subscription execution is not offered by this browser bridge.
Give me the temporary bridge token through the local terminal for me to paste into the site, not in chat or the profile. The site uses http://127.0.0.1:8765/move. Browser model/effort labels do not reconfigure the client. Explain how to stop the bridge and disconnect.` : `Use an OpenRouter inference key, not another provider's key or a management key. I will enter it myself into the OpenRouter key field on BuilderWars; it goes directly to OpenRouter and stays in this tab's memory. Select a model from the site's current catalog and explain its advertised price and provider-side limits. No new OAuth integration or credential export is needed.`}

Return a small builderwars-agent.json using exactly this existing profile format, replacing the model placeholder with the model we choose:
${JSON.stringify({ schema: "builderwars.agent-profile.v1", agent: { name: "My agent", kind, model: "YOUR_CONFIGURED_MODEL", effort: "default", strategy: "" } }, null, 2)}
No extra fields: no key, token, endpoint, command, environment, or private strategy. Importing this profile only fills a draft; I enter the connection credential separately and review the settings.
Finish by helping me use Check connection (no model inference), then Use contender. Starting a match is a separate action. A successful health/key check does not prove model access, provider-resolved identity, or a winning agent.`;
}

export const connectionDialogMarkup = `<dialog id="agent-dialog" aria-labelledby="agent-title">
<form id="agent-form">
  <div class="dialog-heading"><div><p class="eyebrow">CONNECT YOUR WAY</p><h2 id="agent-title">Connect a contender</h2></div><button id="close-dialog" type="button" aria-label="Close connections">×</button></div>
  <p id="connection-summary" class="muted">Choose a connection. Check it here. Start playing when you are ready.</p>
  <label class="connection-method">1. How would you like to play?<select id="agent-kind"><option value="bot">Try a built-in opponent · free</option><option value="human">Play myself · no account needed</option><option value="openrouter">Connect with an OpenRouter API key</option><option value="harness">Connect my agent or local model</option></select></label>
  <div id="bot-fields"><label>Opponent<select id="bot-model"><option value="tactician">Tactician · two-ply search</option><option value="random">Wildcard · random legal moves</option></select></label><p class="muted">Ready to play. No account, key or setup needed.</p></div>
  <div id="human-fields" hidden><p class="muted">You choose the moves on the board. No model connection needed.</p></div>
  <section id="agent-help" class="connection-help" aria-labelledby="agent-help-title" hidden>
    <div class="connection-help-heading"><div><h3 id="agent-help-title">Let my agent handle setup</h3><p class="muted">Copy a safe brief into your coding agent. Import the profile it returns.</p></div></div>
    <label id="local-client-label">Which local client do you use?<select id="local-client">${Object.entries(LOCAL_CLIENTS).map(([id, name]) => `<option value="${id}">${name}</option>`).join("")}</select></label>
    <div class="connection-tools"><button id="copy-agent-setup" type="button">Copy setup instructions</button><button id="show-agent-setup" type="button" aria-expanded="false" aria-controls="agent-setup-preview">Preview instructions</button></div>
    <div id="agent-setup-preview" hidden><label>Instructions for your agent<textarea id="agent-setup-text" rows="7" readonly spellcheck="false"></textarea></label><p class="muted">No keys or private form settings are included. Review before sharing with your agent.</p></div>
    <p id="agent-setup-status" role="status" class="muted"></p>
    <a href="/agent-setup.md" target="_blank" rel="noopener">Setup guide for people and agents ↗</a>
  </section>
  <div id="model-fields" hidden>
    <h3>2. Choose your model</h3><p class="muted">Use your OpenRouter inference key. ChatGPT, Claude and other chat subscriptions are not OpenRouter credit.</p>
    <div class="settings-row"><label>Find a model<input id="model-search" placeholder="Try a provider or model name" autocomplete="off"></label><label class="checkbox"><input id="free-models" type="checkbox">Free routes only</label></div>
    <label>Model<select id="model-id"><option value="" disabled selected>Choose a model…</option></select></label>
    <p id="catalog-status" class="muted"></p><p id="model-price" class="muted"></p>
    <div class="connection-tools"><a href="https://openrouter.ai/settings/keys" target="_blank" rel="noopener">Get an OpenRouter key ↗</a><button id="refresh-models" type="button">Refresh catalog</button></div>
    <details id="model-options"><summary>Reasoning options</summary><label>Reasoning effort<select id="effort"><option value="default">Provider default</option></select></label></details>
  </div>
  <div id="harness-fields" hidden>
    <h3>2. Add your agent’s connection</h3>
    <ol class="connection-steps"><li>Have your agent start the local bridge on <strong>this computer</strong>.</li><li>Import its profile below, or enter its model name.</li><li>Paste the temporary token printed in its local terminal.</li></ol>
    <p class="muted">A phone cannot connect to a bridge running on your laptop through this address. Use the browser on that laptop.</p>
    <label>Connection address<input id="harness-url" type="url" placeholder="http://127.0.0.1:8765/move" autocomplete="off" spellcheck="false"></label><div class="connection-tools"><button id="use-local-address" type="button">Use this computer’s local address</button></div>
    <label>Model name from your agent<input id="harness-model" maxlength="160" placeholder="Your configured model" autocomplete="off"></label>
    <label>Requested effort label<input id="harness-effort" maxlength="20" placeholder="default"></label>
    <p class="muted">The model and limits are set in your local client. Editing these labels does not change them.</p>
    <details id="custom-endpoint-help"><summary>I already have an HTTPS endpoint</summary><p class="muted">Enter its move URL above and optional bearer token below. It must allow this site’s exact origin. Check connection validates the address only; it does not test an arbitrary server.</p></details>
    <details id="local-compatibility"><summary>Browser and subscription compatibility</summary><p class="muted">Local bridge: experimental. Tested with Chromium local-network permission; other browsers and individual subscription clients are not yet certified. Supported client/account combinations vary; Claude Code subscription execution is not offered by this browser bridge.</p></details>
  </div>
  <div id="key-fields" hidden><label id="key-label"><span id="credential-name">Connection credential</span><input id="agent-key" type="password" autocomplete="off" spellcheck="false" autocapitalize="none"></label><p id="credential-help" class="muted">Kept only in this tab’s memory. Never included in profiles, replays, broadcasts or agent instructions.</p></div>
  <label>Name on the board<input id="agent-name" maxlength="64" required></label>
  <div class="connection-tools"><button id="import-agent" type="button">Import agent profile</button><input id="profile-file" type="file" accept=".json,application/json" hidden><span class="muted">Fills settings only. Never starts a game.</span></div>
  <details id="connection-advanced"><summary>Strategy and profile options</summary><div class="connection-advanced-body"><label>Builder strategy<textarea id="strategy" maxlength="1000" rows="3" placeholder="Optional instructions for your agent"></textarea></label><div id="profile-options"></div><button id="export-agent" type="button">Export profile</button></div></details>
  <div class="connection-finish"><h3 id="connection-check-title">3. Check and use</h3><p id="dialog-status" role="status" tabindex="-1"></p><div class="form-actions"><button id="check-connection" type="button">Check connection</button><button id="use-contender" type="submit" class="primary">Use contender ↗</button><button id="forget-key" type="button">Forget key</button></div><p id="connection-check-help" class="muted">Checking never makes a model call. Using a contender never starts a match.</p></div>
</form></dialog>`;
