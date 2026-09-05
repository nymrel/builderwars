"""Strict provider catalog — facts only, six entries, fail closed.

Each entry carries only non-secret facts a BuildWars customer needs to plan a
connection: how the transport works, what THEY run locally to authenticate,
what THEY can run locally to check status, where credentials live, whether a
model id is required, which entrant backend kind serves it, honest
limitations, and the machine-readable policy fields (connection mode,
provider class, harness class, local/hosted route status, prohibited routes,
evidence date, official sources).

The catalog never contains, references, or implies custody of any credential,
and never prints absolute auth paths or account identifiers. Unknown provider
ids raise; there is no "generic" fallback because an unknown provider is
exactly where terms-ambiguous subscription proxying would sneak in. Unknown
catalog fields, transports, backend kinds, provider classes, harness classes,
or hosted-route statuses also raise — the vocabulary is closed and drift
between this catalog and docs/AGENTWARS_PROVIDER_POLICY.v2.json is rejected
by bin/check_provider_hub.py.

The catalog records customer-operated clients and flows, including known routes
that current policy disables. BuildWars does not assert any plan entitlement or
permission beyond what each provider's current documentation states; customers
are responsible for their own provider terms. No entry claims that all hosted
routing is prohibited or that all local orchestration is permitted.

Verified facts this catalog encodes (evidence date 2026-08-27):

* OpenAI: local Codex clients support ``codex login`` with ChatGPT for
  subscription access. OpenAI also publishes ``codex exec``, the Codex SDK,
  and app-server as product integration surfaces while keeping model access
  and managed services separate. The customer path delegates to the locally
  authenticated Codex CLI; it never scrapes or copies credential files.
* Anthropic: current legal documentation permits a product or service to run
  the unmodified Claude Code binary under the Anthropic Commercial Terms when
  each end user authenticates through Claude Code with their own API key,
  Claude subscription, or supported cloud credential and is billed directly.
  It separately forbids a third-party Claude login surface, credential/session
  token custody, request routing through those credentials, and resale or
  intermediation. BuildWars therefore delegates only to a customer-installed,
  unmodified local ``claude`` binary; public enablement remains protected by
  the applicable Commercial Terms and branding-acceptance gate.
* OpenCode: provider auth is local (``opencode auth login`` / ``opencode auth
  list``). It is a route-dependent harness: a selected route attests nothing
  about subscription entitlement, billing, or model identity.
* OpenRouter: OAuth PKCE S256 exchanges a one-time code for a user-controlled
  key that stays in the customer runner. Hosted key custody is architecturally
  supported by that flow but is NOT implemented here. Usage bills the user's
  own OpenRouter account and may incur user-owned API charges.
* Hermes: provider setup is local through ``hermes model``. Nous documents
  ``hermes setup --portal`` and ``hermes portal info`` for its own subscription
  gateway. One-shot execution uses ``hermes --oneshot``. Like OpenCode, Hermes
  is route-dependent; its label never proves the upstream provider, model, or
  billing route.
* Custom agent: an explicit customer-supplied local prompt/stdout command,
  declared as a repeatable JSON argv vector, behind BOTH runtime-intent
  capabilities. It is NOT an arena/1 JSONL
  entrant slot; a true arena/1 entrant is registered directly as a manifest
  command outside the model harness.
"""

import re
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

_PROVIDER_CLASSES = frozenset(
    {
        "official_local_client_delegation",
        "route_dependent_harness",
        "direct_api_customer_key",
        "customer_command",
    }
)

_HARNESS_CLASSES = frozenset(
    {
        "official_first_party_cli",
        "third_party_local_harness",
        "none",
    }
)

_HOSTED_ROUTE_STATUSES = frozenset(
    {
        "not_offered",
        "architecturally_supported_not_implemented",
    }
)

# Customer-facing semantics, deliberately distinct from implementation
# transports. The vocabulary is shared by the catalog, provider-link v2
# envelope, CLI output, policy twin, and eventual UI. ``local_api_key`` is a
# reserved closed value selected by no provider. ``unsupported`` remains a
# fail-closed state selected by no currently executable provider.
CONNECTION_MODES = (
    "web_oauth_pkce",
    "local_subscription_session",
    "local_native_client_session",
    "local_provider_session",
    "local_api_key",
    "local_runtime",
    "unsupported",
)
_CONNECTION_MODES = frozenset(CONNECTION_MODES)

_EVIDENCE_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
PROVIDER_POLICY_SCHEMA_VERSION = "agentwars.provider-policy.v2"
PROVIDER_POLICY_EVIDENCE_DATE = "2026-08-27"

_ENTRY_KEYS = frozenset(
    {
        "display_name",
        "connection_mode",
        "connection_transport",
        "auth_plan",
        "status_plan",
        "credential_custody",
        "model_required",
        "backend_kind",
        "limitations",
        "provider_class",
        "harness_class",
        "local_execution",
        "hosted_route_status",
        "prohibited_routes",
        "evidence_date",
        "official_sources",
    }
)

_CATALOG = {
    "chatgpt_codex": {
        "display_name": "ChatGPT / Codex (local Codex CLI)",
        "connection_mode": "local_subscription_session",
        "connection_transport": "local_cli_subprocess",
        "auth_plan": [
            "Install the Codex CLI yourself.",
            "Run `codex login` and complete ChatGPT sign-in in your own browser.",
            "Confirm with `codex login status`.",
        ],
        "status_plan": "You run `codex login status` locally; BuildWars never reads its output file or any Codex credential store.",
        "credential_custody": "customer_only",
        "model_required": False,
        "backend_kind": "codex_exec",
        "provider_class": "official_local_client_delegation",
        "harness_class": "official_first_party_cli",
        "local_execution": True,
        "hosted_route_status": "not_offered",
        "prohibited_routes": (
            "openai_api_key_env_injection",
            "codex_credential_store_copy",
            "hosted_subscription_proxy",
        ),
        "evidence_date": PROVIDER_POLICY_EVIDENCE_DATE,
        "official_sources": (
            "https://learn.chatgpt.com/docs/auth",
            "https://developers.openai.com/blog/codex-as-a-platform",
            "https://help.openai.com/en/articles/8156019-is-api-usage-included-in-chatgpt-subscriptions-even-if-i-have-a-paid-chatgpt-account",
        ),
        "limitations": (
            "Subscription access is official local client delegation only: the "
            "locally authenticated Codex CLI answers; BuildWars never proxies a "
            "hosted ChatGPT session.",
            "The child environment is a fixed OS/auth-path/locale/TLS allowlist, so no "
            "host API-key variable can silently fall back to API billing, but "
            "BuildWars cannot attest cached auth method, entitlement, quota, or billing.",
            "BuildWars cannot attest which account or model answered.",
            "Cloud API keys are a separate surface and are never required here.",
        ),
    },
    "claude_code": {
        "display_name": "Claude Code (historical evidence only)",
        "connection_mode": "unsupported",
        "connection_transport": "local_cli_subprocess",
        "auth_plan": [
            "No new Claude Code connection or execution route is available in this candidate.",
            "Historical `claude_code` identifiers remain readable so retained evidence can be parsed and displayed without invoking Claude Code.",
            "A future route requires a new independently reviewed provider-policy decision before any executable admission can reopen.",
        ],
        "status_plan": "Held. BuildWars does not invoke Claude Code, implement Claude login, receive credentials or session material, proxy subscription requests, or mutate an Anthropic account.",
        "credential_custody": "customer_only",
        "model_required": False,
        "backend_kind": "claude_print",
        "provider_class": "official_local_client_delegation",
        "harness_class": "official_first_party_cli",
        "local_execution": False,
        "hosted_route_status": "not_offered",
        "prohibited_routes": (
            "claude_code_binary_modification",
            "claude_code_credential_store_copy",
            "buildwars_claude_login_surface",
            "hosted_claude_subscription_proxy",
            "claude_credential_or_session_intermediation",
            "claude_subscription_resale",
            "claude_auth_method_restriction",
            "anthropic_subscription_via_opencode",
            "anthropic_subscription_via_hermes",
        ),
        "evidence_date": PROVIDER_POLICY_EVIDENCE_DATE,
        "official_sources": (
            "https://code.claude.com/docs/en/authentication",
            "https://code.claude.com/docs/en/legal-and-compliance",
            "https://code.claude.com/docs/en/cli-reference",
        ),
        "limitations": (
            "The identifier is retained only for historical evidence compatibility; it is excluded from executable provider ids and rejected by new link, capability, job, prepared-match, and backend admission.",
            "BuildWars never offers Claude login, copies or intermediates credentials/session tokens, routes a hosted subscription request, pays on the user's behalf, resells Claude access, or invokes the Claude Code binary in this candidate.",
            "BuildWars cannot attest the account, auth method, plan entitlement, billing route, quota, selected model, model identity, harness identity, runtime identity, person, or answer provenance for retained historical claims.",
            "OpenCode and Hermes Claude-subscription routes remain disabled because those harnesses are not the unmodified Claude Code binary covered by this route.",
        ),
    },
    "opencode": {
        "display_name": "OpenCode",
        "connection_mode": "local_provider_session",
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
        "provider_class": "route_dependent_harness",
        "harness_class": "third_party_local_harness",
        "local_execution": True,
        "hosted_route_status": "not_offered",
        "prohibited_routes": (
            "anthropic_subscription_via_this_harness",
            "undocumented_route_attestation",
        ),
        "evidence_date": PROVIDER_POLICY_EVIDENCE_DATE,
        "official_sources": (
            "https://opencode.ai/docs/providers/",
            "https://code.claude.com/docs/en/legal-and-compliance",
        ),
        "limitations": (
            "Requires an explicit provider/model identifier; variant defaults to max when omitted.",
            "OpenCode's current docs explicitly say its third-party Claude subscription plugin path is prohibited; BuildWars does not offer a substitute Claude subscription adapter.",
            "Route-dependent harness: the selected route may use a subscription, API key, free quota, or other billing path; BuildWars cannot attest which.",
            "An OpenCode label never attests model identity, subscription entitlement, billing, or provider permission.",
        ),
    },
    "openrouter": {
        "display_name": "OpenRouter",
        "connection_mode": "web_oauth_pkce",
        "connection_transport": "local_pkce_http_exchange",
        "auth_plan": [
            "Start PKCE from your own BuildWars runner (never from a shared machine).",
            "Approve access in your browser at openrouter.ai.",
            "Your runner exchanges the one-time code for YOUR key and uses it only on your machine.",
            "The provider-side key may remain active after local use; review or revoke it in your OpenRouter dashboard.",
        ],
        "status_plan": "BuildWars keeps no key. A locally supplied or PKCE-created key is used only in your runner environment (OPENROUTER_API_KEY), but the provider-side key may remain active until you revoke it in your OpenRouter dashboard.",
        "credential_custody": "customer_only",
        "model_required": True,
        "backend_kind": "openrouter_chat",
        "provider_class": "direct_api_customer_key",
        "harness_class": "none",
        "local_execution": True,
        "hosted_route_status": "architecturally_supported_not_implemented",
        "prohibited_routes": (
            "hosted_key_custody",
            "platform_key_escrow",
        ),
        "evidence_date": PROVIDER_POLICY_EVIDENCE_DATE,
        "official_sources": (
            "https://openrouter.ai/docs/guides/overview/auth/oauth",
        ),
        "limitations": (
            "Key custodied by you; BuildWars stores nothing and receives nothing. Hosted PKCE key custody is architecturally supported by OpenRouter's flow but is NOT implemented in this candidate.",
            "Discarding the key from the runner does not revoke the provider-side key. OpenRouter's key deletion API requires a separate management-key route, which this candidate does not request or custody; use the OpenRouter dashboard to review or revoke the created key.",
            "Per-token cost is yours under your OpenRouter account.",
        ),
    },
    "hermes": {
        "display_name": "Hermes",
        "connection_mode": "local_provider_session",
        "connection_transport": "local_cli_subprocess",
        "auth_plan": [
            "Install Hermes yourself.",
            "For a Nous Portal subscription, run `hermes setup --portal` on a fresh install or choose Nous Portal in `hermes model`.",
            "For another supported provider, use `hermes model` and follow that provider's current terms.",
        ],
        "status_plan": "For Nous Portal, you run `hermes portal info`; for other routes, inspect Hermes locally. BuildWars never reads the auth store or attests the billing route.",
        "credential_custody": "customer_only",
        "model_required": True,
        "backend_kind": "hermes_oneshot",
        "provider_class": "route_dependent_harness",
        "harness_class": "third_party_local_harness",
        "local_execution": True,
        "hosted_route_status": "not_offered",
        "prohibited_routes": (
            "upstream_consumer_subscription_without_provider_authorization",
            "undocumented_route_attestation",
        ),
        "evidence_date": PROVIDER_POLICY_EVIDENCE_DATE,
        "official_sources": (
            "https://hermes-agent.nousresearch.com/docs/integrations/providers",
            "https://hermes-agent.nousresearch.com/docs/integrations/nous-portal",
            "https://code.claude.com/docs/en/legal-and-compliance",
        ),
        "limitations": (
            "One-shot execution via `hermes --oneshot` with explicit provider/model, safe mode, and only the non-mutating `clarify` toolset.",
            "No fallback claim: a failed shot is a failed shot.",
            "Nous Portal is a documented Nous subscription route. Other Hermes configuration may represent an upstream subscription, API key, free quota, or separately billed access; BuildWars cannot attest which.",
            "BuildWars disables upstream consumer-subscription routes through Hermes unless that upstream provider authorizes the product pattern; a Hermes or Nous label cannot override upstream terms.",
            "A Hermes label never proves a provider subscription or model identity.",
        ),
    },
    "custom_agent": {
        "display_name": "Custom agent command",
        "connection_mode": "local_runtime",
        "connection_transport": "customer_command_stdio",
        "auth_plan": [
            "Write your own local prompt/stdout program.",
            "Declare it as an explicit repeatable JSON argv vector.",
        ],
        "status_plan": "You run your own command; BuildWars has nothing to check.",
        "credential_custody": "customer_only",
        "model_required": False,
        "backend_kind": "custom_cli",
        "provider_class": "customer_command",
        "harness_class": "none",
        "local_execution": True,
        "hosted_route_status": "not_offered",
        "prohibited_routes": (
            "arena_1_jsonl_slot",
            "implicit_construction",
        ),
        "evidence_date": PROVIDER_POLICY_EVIDENCE_DATE,
        "official_sources": (),
        "limitations": (
            "Explicit escape hatch: the declared argv runs locally, receives the "
            "prompt on stdin, and its final stdout text is parsed as the answer.",
            "Double-gated: requires BOTH explicit runtime-intent capabilities; default construction fails before subprocess resolution.",
            "This is NOT an arena/1 JSONL entrant slot; a true arena/1 entrant is "
            "registered directly as a manifest command outside the model harness.",
            "The intent capabilities are not isolation. A direct local invocation can reach whatever its OS user can reach; public or shared arbitrary execution stays disabled until a separate OS isolation boundary exists.",
        ),
    },
}


EXECUTABLE_PROVIDER_IDS = tuple(
    provider_id
    for provider_id in PROVIDER_IDS
    if _CATALOG[provider_id]["local_execution"] is True
)


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
        "connection_mode": entry["connection_mode"],
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


def connection_mode_for(provider_id):
    return get_provider(provider_id)["connection_mode"]


def backend_kind_for(provider_id):
    return get_provider(provider_id)["backend_kind"]


def model_required_for(provider_id):
    return get_provider(provider_id)["model_required"]


def local_execution_available_for(provider_id):
    """Whether current provider policy permits constructing this local route."""
    return get_provider(provider_id)["local_execution"] is True


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


def _require_text(value, field):
    if (
        not isinstance(value, str)
        or not value.strip()
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise RuntimeError(f"catalog integrity: {field} must be non-empty text")


def _freeze(entry):
    """Validate one entry against the CLOSED policy vocabulary, then freeze.

    Unknown fields, transports, backend kinds, provider classes, harness
    classes, or hosted-route statuses raise here — catalog drift fails loudly
    instead of silently widening the contract.
    """
    if frozenset(entry) != _ENTRY_KEYS:
        missing = sorted(_ENTRY_KEYS - frozenset(entry))
        unknown = sorted(frozenset(entry) - _ENTRY_KEYS)
        raise RuntimeError(
            f"catalog integrity: field drift (missing={missing}, unknown={unknown})"
        )
    for field in (
        "display_name",
        "connection_mode",
        "connection_transport",
        "status_plan",
        "credential_custody",
        "backend_kind",
        "provider_class",
        "harness_class",
        "hosted_route_status",
        "evidence_date",
    ):
        _require_text(entry[field], field)
    auth_plan = entry["auth_plan"]
    if not isinstance(auth_plan, list) or len(auth_plan) < 2:
        raise RuntimeError("catalog integrity: auth_plan must have at least two steps")
    for step in auth_plan:
        _require_text(step, "auth_plan step")
    limitations = entry["limitations"]
    if not isinstance(limitations, tuple) or not limitations:
        raise RuntimeError("catalog integrity: limitations must be a non-empty tuple")
    for limitation in limitations:
        _require_text(limitation, "limitation")
    if not isinstance(entry["model_required"], bool):
        raise RuntimeError("catalog integrity: model_required must be boolean")
    if entry["connection_transport"] not in _TRANSPORTS:
        raise RuntimeError(f"catalog integrity: bad transport for {entry!r}")
    if entry["connection_mode"] not in _CONNECTION_MODES:
        raise RuntimeError(
            f"catalog integrity: bad connection mode {entry['connection_mode']!r}"
        )
    if entry["connection_mode"] == "local_api_key":
        raise RuntimeError(
            "catalog integrity: no current provider may select reserved local_api_key"
        )
    if entry["credential_custody"] != "customer_only":
        raise RuntimeError("catalog integrity: custody must always be customer_only")
    if entry["backend_kind"] not in _BACKEND_KINDS:
        raise RuntimeError(f"catalog integrity: bad backend kind {entry['backend_kind']!r}")
    if entry["provider_class"] not in _PROVIDER_CLASSES:
        raise RuntimeError(
            f"catalog integrity: bad provider class {entry['provider_class']!r}"
        )
    if entry["harness_class"] not in _HARNESS_CLASSES:
        raise RuntimeError(
            f"catalog integrity: bad harness class {entry['harness_class']!r}"
        )
    if entry["connection_mode"] == "unsupported":
        if entry["local_execution"] is not False:
            raise RuntimeError(
                "catalog integrity: unsupported routes must disable local execution"
            )
    elif entry["local_execution"] is not True:
        raise RuntimeError(
            "catalog integrity: executable routes must be explicitly customer-local"
        )
    if entry["hosted_route_status"] not in _HOSTED_ROUTE_STATUSES:
        raise RuntimeError(
            f"catalog integrity: bad hosted route status {entry['hosted_route_status']!r}"
        )
    routes = entry["prohibited_routes"]
    if (
        not isinstance(routes, tuple)
        or len(set(routes)) != len(routes)
        or any(
            not isinstance(route, str)
            or re.fullmatch(r"[a-z0-9_]+", route) is None
            for route in routes
        )
    ):
        raise RuntimeError(
            "catalog integrity: prohibited routes must be unique snake-case strings"
        )
    sources = entry["official_sources"]
    if (
        not isinstance(sources, tuple)
        or len(set(sources)) != len(sources)
        or any(
            not isinstance(url, str)
            or not url.startswith("https://")
            or any(ord(char) < 33 or ord(char) > 126 for char in url)
            for url in sources
        )
    ):
        raise RuntimeError(
            "catalog integrity: official sources must be unique https URLs"
        )
    if (
        entry["evidence_date"] != PROVIDER_POLICY_EVIDENCE_DATE
        or not _EVIDENCE_DATE_RE.fullmatch(entry["evidence_date"])
    ):
        raise RuntimeError(
            "catalog integrity: evidence date must be "
            f"{PROVIDER_POLICY_EVIDENCE_DATE}"
        )
    return _freeze_value(dict(entry))
