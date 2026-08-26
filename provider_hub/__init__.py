"""BuildWars customer provider hub — customer side only.

This package lets a BuildWars customer inspect six known provider/harness
routes, then plan, pair, and route only the currently executable ones into an
AgentWars entrant while every provider credential stays in customer custody.
Known-but-disabled routes remain visible so policy cannot silently become an
execution path.

Nothing here ever touches ``arena/**``. The engine cannot import this package
and this package never imports the engine; ``bin/check_provider_hub.py``
enforces that boundary mechanically.

Layers:

  ids        random, non-enumerable public identifiers
  secrets    redacted secret wrapper (never repr'd, never JSON serialized)
  catalog    strict six-provider fact catalog + connect plans
  schemas    versioned customer/runner envelopes, strict and float-free
  signing    HMAC-SHA256 runner pairing signatures (constant-time verify)
  pkce       OpenRouter OAuth PKCE S256 primitives, offline-testable
"""

from provider_hub.catalog import (
    CONNECTION_MODES,
    EXECUTABLE_PROVIDER_IDS,
    PROVIDER_IDS,
    ProviderError,
    connection_mode_for,
    connect_plan,
    get_provider,
    local_execution_available_for,
    public_catalog,
)
from provider_hub.ids import ID_PREFIXES, id_is_valid, new_id
from provider_hub.secrets import SecretValue, redact
from provider_hub.schemas import (
    SCHEMA_NAMES,
    SchemaError,
    bind_result_to_job,
    decode_strict,
    encode_canonical,
    validate_envelope,
)
from provider_hub.signing import (
    InMemoryReplayGuard,
    PairingKey,
    SigningError,
    generate_pairing_key,
    sign_payload,
    verify_signature,
)
from provider_hub.pkce import (
    PkceError,
    build_authorize_url,
    challenge_from_verifier,
    exchange,
    new_callback_path,
    new_verifier,
    parse_callback,
    parse_exchange_response,
    validate_redirect_uri,
)

__all__ = [
    "ID_PREFIXES",
    "InMemoryReplayGuard",
    "CONNECTION_MODES",
    "EXECUTABLE_PROVIDER_IDS",
    "PROVIDER_IDS",
    "PairingKey",
    "PkceError",
    "ProviderError",
    "SCHEMA_NAMES",
    "SchemaError",
    "SecretValue",
    "SigningError",
    "bind_result_to_job",
    "build_authorize_url",
    "challenge_from_verifier",
    "connection_mode_for",
    "connect_plan",
    "decode_strict",
    "encode_canonical",
    "exchange",
    "generate_pairing_key",
    "get_provider",
    "id_is_valid",
    "new_id",
    "new_callback_path",
    "new_verifier",
    "local_execution_available_for",
    "parse_callback",
    "parse_exchange_response",
    "public_catalog",
    "redact",
    "sign_payload",
    "validate_envelope",
    "validate_redirect_uri",
    "verify_signature",
]
