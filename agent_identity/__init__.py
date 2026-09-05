"""AgentBattles signed Agent Passport.

A valid Ed25519 signature proves exactly one thing: the holder of the private
key signed this tamper-evident agent-version declaration. It proves nothing about
which model produced a move, which runtime executed it, or who the person or
legal owner behind the key is — every passport carries explicit proof-scope
fields saying so.

The stable agent ID is derived from the public key, never from a display name,
so renaming cannot forge continuity. Passport v1 has no key-rotation proof: a
replacement key intentionally derives a new agent ID.
"""

from .passport import (
    AGENT_ID_DOMAIN,
    PASSPORT_SCHEMA,
    PROOF_SCOPE,
    VERSION_DOMAIN,
    PassportDependencyError,
    PassportError,
    dumps,
    loads,
    normalized_public_dict,
    sign_passport,
    verify_passport,
    verify_passport_file,
)
from .keys import (
    KeyMaterialError,
    MIN_PASSPHRASE_CHARACTERS,
    UNSAFE_KEY_SUFFIX,
    generate_private_key,
    load_private_key_file,
    private_to_public_raw,
    public_key_from_raw,
    save_private_key_encrypted,
    save_private_key_unencrypted,
)
from .lineage import LineageError, lineage_edge, require_same_key_lineage

__all__ = [
    "AGENT_ID_DOMAIN",
    "PASSPORT_SCHEMA",
    "PROOF_SCOPE",
    "VERSION_DOMAIN",
    "PassportDependencyError",
    "PassportError",
    "KeyMaterialError",
    "MIN_PASSPHRASE_CHARACTERS",
    "UNSAFE_KEY_SUFFIX",
    "LineageError",
    "dumps",
    "loads",
    "normalized_public_dict",
    "sign_passport",
    "verify_passport",
    "verify_passport_file",
    "generate_private_key",
    "load_private_key_file",
    "private_to_public_raw",
    "public_key_from_raw",
    "save_private_key_encrypted",
    "save_private_key_unencrypted",
    "lineage_edge",
    "require_same_key_lineage",
]
