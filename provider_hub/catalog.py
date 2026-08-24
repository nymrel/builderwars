"""Strict provider catalog — facts only, six entries, fail closed.

Each entry carries only non-secret facts a BuildWars customer needs to plan a
connection: how the transport works, what THEY run locally to authenticate,
what THEY can run locally to check status, where credentials live, whether a
model id is required, which entrant backend kind serves it, and honest
limitations.

The catalog never contains, references, or implies custody of any credential.
Unknown provider ids raise; there is no "generic" fallback because an unknown
provider is exactly where terms-ambiguous subscription proxying would sneak in.

These are customer-operated, provider-supported local clients and flows.
BuildWars does not assert any plan entitlement or permission beyond what each
provider's current documentation states; customers are responsible for their
own provider terms. No entry claims that all hosted routing is prohibited or
that all local orchestration is permitted.

Verified facts this catalog encodes (2026-08):

* OpenAI: local Codex clients support ``codex login`` with ChatGPT for
  subscription access. The cloud API is a separate API-key surface. The
  customer subscription path delegates to the locally authenticated Codex CLI;
  it never scrapes or copies ``~/.codex/auth.json``.
* Anthropic: Claude Code supports browser login on eligible plans. This catalog
  delegates to the locally authenticated ``claude`` CLI and never copies its
  credentials. Current OpenCode documentation separately warns against its
  third-party Claude subscription plugin path.
* OpenCode: provider auth is local (``opencode auth login`` / ``opencode auth
  list``).
* OpenRouter: OAuth PKCE S256 exchanges a one-time code for a user-controlled
  key that stays in the customer runner. Usage bills the user's own OpenRouter
  account and may incur user-owned API charges.
* Hermes: provider setup/auth is local (``hermes model``, ``hermes auth``);
  one-shot execution via ``hermes --oneshot``.
* Custom agent: an explicit customer-supplied local prompt/stdout command,
  declared as a repeatable JSON argv vector. It is NOT an arena/1 JSONL
  entrant slot; a true arena/1 entrant is registered directly as a manifest
  command outside the model harness.
"""

import types

PROVIDER_IDS = (
    "chatgpt_codex",
    "claude_code",
    "opencode",
    "openrouter",
    "hermes",
    "custom_agent",
)

_TRANSPORTS = frozenset(
    {
        "local_cli_subprocess",
        "local_cli_auth_delegation",
        "local_pkce_http_exchange",
        "customer_command_stdio",
    }
)

_BACKEND_KINDS = frozenset(
    {
        "codex_exec",
        "claude_print",
        "opencode_run",
        "openrouter_chat",
        "hermes_oneshot",
        "custom_cli",
    }
)

_CATALOG = {
    "chatgpt_codex": {
        "display_name": "ChatGPT / Codex (local Codex CLI)",
        "connection_transport": "local_cli_subprocess",
        "auth_plan": [
            "Install the Codex CLI yourself.",
            "Run `codex login` and complete ChatGPT sign-in in your own browser.",
            "Confirm with `codex login status`.",
        ],
        "status_plan": "You run `codex login status` locally; BuildWars never reads its output file or ~/.codex/auth.json.",
        "credential_custody": "customer_only",
        "model_required": False,
        "backend_kind": "codex_exec",
        "limitations": (
            "Uses the auth method selected in your local Codex installation.",
            "The adapter removes OPENAI_API_KEY from its child environment, but cannot attest cached auth method, entitlement, quota, or billing.",
            "BuildWars cannot attest which account or model answered.",
            "Cloud API keys are a separate surface and are never required here.",
        ),
    },
    "claude_code": {
        "display_name": "Claude Code (local claude CLI)",
        "connection_transport": "local_cli_auth_delegation",
        "auth_plan": [
            "Install Claude Code yourself.",
            "Run `claude` once and complete browser login on your eligible Claude plan.",
        ],
        "status_plan": "You check login state in your local Claude Code session; BuildWars never copies or reads CLI credentials.",
        "credential_custody": "customer_only",
        "model_required": False,
        "backend_kind": "claude_print",
        "limitations": (
            "Runs `claude -p` non-interactively with sessions and customization disabled.",
            "No fallback model is configured; an overloaded primary fails the call.",
            "This path invokes Anthropic's own CLI rather than copying its auth material into BuildWars or OpenCode.",
            "The adapter removes ANTHROPIC_API_KEY from its child environment, but cannot attest cached auth method, entitlement, quota, or billing.",
            "BuildWars cannot attest which account or model answered.",
        ),
    },
    "opencode": {
        "display_name": "OpenCode",
        "connection_transport": "local_cli_subprocess",
        "auth_plan": [
            "Install OpenCode yourself.",
            "Run `opencode auth login` for whichever provider you hold access to.",
            "List connected providers with `opencode auth list`.",
        ],
        "status_plan": "You run `opencode auth list` locally; BuildWars never inspects OpenCode's auth store.",
        "credential_custody": "customer_only",
        "model_required": True,
        "backend_kind": "opencode_run",
        "limitations": (
            "Requires an explicit provider/model identifier; variant defaults to max when omitted.",
            "OpenCode's current docs warn that its third-party Claude subscription plugin path is not supported; use the separate claude_code adapter for Claude Code plan access.",
            "The selected OpenCode provider may use a subscription, API key, or other billing path; BuildWars cannot attest which.",
        ),
    },
    "openrouter": {
        "display_name": "OpenRouter",
        "connection_transport": "local_pkce_http_exchange",
        "auth_plan": [
            "Start PKCE from your own BuildWars runner (never from a shared machine).",
            "Approve access in your browser at openrouter.ai.",
            "Your runner exchanges the one-time code for YOUR key; it stays on your machine.",
        ],
        "status_plan": "Your key lives only in your runner environment (OPENROUTER_API_KEY); rotate or revoke anytime in your OpenRouter dashboard.",
        "credential_custody": "customer_only",
        "model_required": True,
        "backend_kind": "openrouter_chat",
        "limitations": (
            "Key custodied by you; BuildWars stores nothing and receives nothing.",
            "Per-token cost is yours under your OpenRouter account.",
        ),
    },
    "hermes": {
        "display_name": "Hermes",
        "connection_transport": "local_cli_subprocess",
        "auth_plan": [
            "Install Hermes yourself.",
            "Configure providers with `hermes model` and authenticate with `hermes auth`.",
        ],
        "status_plan": "You inspect Hermes' own local config; BuildWars never reads it.",
        "credential_custody": "customer_only",
        "model_required": True,
        "backend_kind": "hermes_oneshot",
        "limitations": (
            "One-shot execution via `hermes --oneshot` with explicit provider/model, safe mode, and only the non-mutating `clarify` toolset.",
            "No fallback claim: a failed shot is a failed shot.",
            "Hermes provider configuration may represent subscription access or separately billed API access; BuildWars cannot attest which.",
        ),
    },
    "custom_agent": {
        "display_name": "Custom agent command",
        "connection_transport": "customer_command_stdio",
        "auth_plan": [
            "Write your own local prompt/stdout program.",
            "Declare it as an explicit repeatable JSON argv vector.",
        ],
        "status_plan": "You run your own command; BuildWars has nothing to check.",
        "credential_custody": "customer_only",
        "model_required": False,
        "backend_kind": "custom_cli",
        "limitations": (
            "Explicit escape hatch: the declared argv runs locally, receives the "
            "prompt on stdin, and its final stdout text is parsed as the answer.",
            "This is NOT an arena/1 JSONL entrant slot; a true arena/1 entrant is "
            "registered directly as a manifest command outside the model harness.",
            "Whatever your command can reach is your responsibility; the arena sandbox policy still applies to the process.",
        ),
    },
}


class ProviderError(ValueError):
    """Unknown or malformed provider reference. Fails closed."""


def get_provider(provider_id):
    """Return the immutable catalog entry or raise ProviderError."""
    if not isinstance(provider_id, str):
        raise ProviderError(f"provider id must be a string, got {type(provider_id).__name__}")
    entry = _CATALOG.get(provider_id)
    if entry is None:
        raise ProviderError(
            f"unknown provider {provider_id!r}; supported ids: {', '.join(PROVIDER_IDS)}"
        )
    return _freeze(entry)


def connect_plan(provider_id):
    """Return the numbered customer-owned connection plan for one provider."""
    entry = get_provider(provider_id)
    steps = [f"{i}. {step}" for i, step in enumerate(entry["auth_plan"], start=1)]
    return {
        "provider": provider_id,
        "display_name": entry["display_name"],
        "steps": tuple(steps),
        "custody": (
            f"Credential custody: {entry['credential_custody']}. "
            "BuildWars never receives, stores, or sees any provider credential."
        ),
        "status": entry["status_plan"],
        "limitations": entry["limitations"],
    }


def public_catalog():
    """Read-only listing of every provider, canonical order."""
    return tuple((pid, _freeze(_CATALOG[pid])) for pid in PROVIDER_IDS)


def transport_for(provider_id):
    return get_provider(provider_id)["connection_transport"]


def backend_kind_for(provider_id):
    return get_provider(provider_id)["backend_kind"]


def model_required_for(provider_id):
    return get_provider(provider_id)["model_required"]


def _freeze_value(value):
    """Recursively freeze catalog data into MappingProxyType/tuple shapes."""
    if isinstance(value, dict):
        return types.MappingProxyType(
            {key: _freeze_value(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, set):
        return frozenset(value)
    return value


def _freeze(entry):
    if entry["connection_transport"] not in _TRANSPORTS:
        raise RuntimeError(f"catalog integrity: bad transport for {entry!r}")
    if entry["credential_custody"] != "customer_only":
        raise RuntimeError("catalog integrity: custody must always be customer_only")
    if entry["backend_kind"] not in _BACKEND_KINDS:
        raise RuntimeError(f"catalog integrity: bad backend kind {entry['backend_kind']!r}")
    return _freeze_value(dict(entry))
